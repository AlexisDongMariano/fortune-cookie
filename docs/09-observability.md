# 09 — Observability (Prometheus + Grafana)

> Goal: **you can see your app's traffic, errors, and latency in a dashboard**.
> This is the single most valuable SRE skill on a resume — every on-call rotation revolves around it.

---

## The three pillars (memorize this)

| Pillar | What | Tool in this project |
|--------|------|----------------------|
| **Metrics** | Numbers over time — request rate, CPU, errors | Prometheus |
| **Logs** | Individual events with text | stdout → later Loki (stretch) |
| **Traces** | A single request's path across services | out of scope (later: OpenTelemetry) |

We'll do metrics in this chapter. That's 80% of observability in real jobs.

---

## Mental model

```
FastAPI app ── exposes ──▶ /metrics (plain text)
                              ▲
                              │  scrapes every 15s
                              │
                        Prometheus ──── query ────▶ Grafana (dashboards)
                              │
                              └── fires ───▶ Alertmanager (stretch)
```

Prometheus **pulls**. Your app just exposes an endpoint.

---

## 1. Instrument the FastAPI app

Add to `backend/requirements.txt`:

```
prometheus-fastapi-instrumentator==7.0.0
```

Install:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
```

Edit `backend/app/main.py` to wire it up:

```python
from prometheus_fastapi_instrumentator import Instrumentator

# ...existing imports and app setup...

Instrumentator().instrument(app).expose(app)   # adds /metrics endpoint
```

Restart and check:

```bash
curl -s http://localhost:8000/metrics | head -40
```

You should see lines like:

```
# HELP http_requests_total ...
# TYPE http_requests_total counter
http_requests_total{handler="/api/fortunes/random",method="GET",status="2xx"} 3.0
```

That's Prometheus format. Congratulations — your app now emits metrics.

---

## 2. Add Prometheus + Grafana to docker-compose

Create `monitoring/prometheus.yml` in the repo:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: fortune-backend
    static_configs:
      - targets: ["backend:8000"]
```

Append to `docker-compose.yml`:

```yaml
  prometheus:
    image: prom/prometheus:v2.54.1
    restart: unless-stopped
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prom_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:11.2.0
    restart: unless-stopped
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin     # change for prod
      GF_USERS_ALLOW_SIGN_UP: "false"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

And add two volumes at the bottom:

```yaml
volumes:
  db_data:
  prom_data:
  grafana_data:
```

---

## 3. Auto-provision Grafana's Prometheus datasource

Create `monitoring/grafana/provisioning/datasources/datasource.yml`:

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
```

Now Grafana knows where to read from, without clicking around in the UI.

---

## 4. Fire it up

```bash
docker compose up -d
```

- Prometheus: http://localhost:9090 — Status → Targets should show `fortune-backend` = UP.
- Grafana: http://localhost:3000 — login `admin/admin`, skip the password change prompt.

Click the cookie a few times to generate some traffic.

---

## 5. Your first dashboard

In Grafana: **Dashboards → New → New dashboard → Add visualization → Prometheus**.

Panels to build (these 4 are the baseline — know them cold):

### Panel 1 — Request rate (req/s)

PromQL:
```
sum(rate(http_requests_total[1m])) by (handler)
```
Visualization: Time series.
Legend: `{{handler}}`.

### Panel 2 — Error rate (%)

```
100 * sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))
```
Unit: Percent. Thresholds: 1% yellow, 5% red.

### Panel 3 — p95 latency (seconds)

```
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, handler))
```
Legend: `{{handler}}`.

### Panel 4 — Traffic per endpoint (stacked)

```
sum(rate(http_requests_total[5m])) by (handler)
```
Visualization: Bar chart or stacked time series.

**Save the dashboard** (name: `Fortune Cookie`). Then:
- Click the share icon → **Export → Save to file**.
- Put the JSON at `monitoring/grafana/provisioning/dashboards/fortune.json`.

Auto-load it by creating `monitoring/grafana/provisioning/dashboards/dashboards.yml`:

```yaml
apiVersion: 1
providers:
  - name: default
    folder: ""
    type: file
    options:
      path: /etc/grafana/provisioning/dashboards
```

Restart: `docker compose restart grafana`. The dashboard now loads on any fresh Grafana.

---

## 6. The Four Golden Signals (Google SRE book)

You'll hear this phrase in every interview. Memorize:

1. **Latency** — how long requests take. (Panel 3.)
2. **Traffic** — how many requests. (Panels 1, 4.)
3. **Errors** — what fraction fail. (Panel 2.)
4. **Saturation** — how full the system is. (CPU, memory, DB connections.)

Your 4 panels cover 1–3. For saturation, add `node-exporter` (host metrics) — it's a 5-minute add:

```yaml
  node-exporter:
    image: prom/node-exporter:v1.8.2
    restart: unless-stopped
    ports: ["9100:9100"]
```

Then in `prometheus.yml`:

```yaml
  - job_name: node
    static_configs:
      - targets: ["node-exporter:9100"]
```

Import Grafana dashboard **1860** ("Node Exporter Full") for instant CPU/memory/disk graphs.

---

## 7. One alert (the minimum viable alert)

Create `monitoring/alerts.yml`:

```yaml
groups:
  - name: fortune
    rules:
      - alert: HighErrorRate
        expr: |
          100 * sum(rate(http_requests_total{status=~"5.."}[5m]))
          /   sum(rate(http_requests_total[5m])) > 5
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "Error rate above 5% for 5 minutes"
```

Wire it into `prometheus.yml`:

```yaml
rule_files:
  - /etc/prometheus/alerts.yml
```

And mount it in the compose file (add to the prometheus volumes):

```
./monitoring/alerts.yml:/etc/prometheus/alerts.yml:ro
```

You won't hook up a notification channel for this project (too much scope), but **an alert visible in the Prometheus UI is enough for the portfolio**. You can talk about Alertmanager + Slack/PagerDuty in interviews.

---

## 8. Deploy observability to the EC2

Copy the `monitoring/` folder to the EC2, make sure ports 9090 and 3000 are in the security group (only your IP!), and include them in `docker-compose.prod.yml`. **Never expose Grafana to the public internet without changing the default password.**

Better: bind them to `127.0.0.1` and reach them via SSH port-forwarding:

```bash
ssh -L 3000:localhost:3000 -L 9090:localhost:9090 ubuntu@<EC2_IP>
```

Now `http://localhost:3000` on your laptop is the EC2's Grafana.

---

## 9. What to show on your resume / in interviews

- Screenshot of your dashboard in the README.
- Can describe Prometheus pull vs push model.
- Can define the four golden signals.
- Can read and write basic PromQL (`rate`, `sum by`, `histogram_quantile`).
- Know what an SLO is ("99.9% of requests complete under 300 ms over a 30-day window").

That is a legitimately strong mid-level SRE talking point.

---

## Definition of Done

- [ ] `/metrics` endpoint returns data.
- [ ] Prometheus target `fortune-backend` is UP.
- [ ] Grafana dashboard shows traffic when you click the cookie.
- [ ] Dashboard JSON is committed.
- [ ] One alert defined and visible in Prometheus UI.

Next (stretch): [`10-kubernetes.md`](10-kubernetes.md).
