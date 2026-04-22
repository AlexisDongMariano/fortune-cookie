# 10 — Kubernetes (Optional Stretch)

> **This chapter is optional and comes last.** Don't touch it until Stages 01–09 are solid. Employers care *much more* about a fully shipped EC2/Docker/Terraform project than a half-built K8s one.
>
> Goal: run the same containers you built in Chapter 08 on a local Kubernetes cluster. No cloud K8s — that's a second project.

---

## Should I do this chapter?

Do it if:
- Weeks 1–5 are all green.
- You're applying for roles that mention Kubernetes in the JD.
- You have at least 4–6 more hours.

Skip if:
- You're low on time — polish the existing 9 chapters instead.
- You haven't used Docker comfortably yet.

---

## Mental model

```
Deployment ──manages──▶ ReplicaSet ──creates──▶ Pods (your containers)
                                                    ▲
Service ──routes traffic to──────────────────────────┘
Ingress ──exposes HTTP from outside──▶ Service
ConfigMap / Secret ──mounted as env / files──▶ Pods
PVC ──requests storage──▶ PV (for the DB)
```

All of this is **YAML**. Nothing more.

---

## Tooling

Install `kubectl` and a local cluster:

```bash
# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# kind (Kubernetes IN Docker — simplest local cluster)
go install sigs.k8s.io/kind@latest     # or download binary from GitHub releases

kind create cluster --name fortune
kubectl cluster-info
kubectl get nodes
```

If you prefer Minikube: `minikube start`. Same concepts, different tool.

---

## Layout

```
k8s/
├── namespace.yaml
├── db.yaml               Postgres (StatefulSet + Service + PVC)
├── backend.yaml          Deployment + Service
├── frontend.yaml         Deployment + Service
├── ingress.yaml          NGINX ingress
├── configmap.yaml        non-secret config
└── secret.yaml           DB password (use --from-literal, don't commit real values)
```

---

## 1. Namespace

`k8s/namespace.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: fortune
```

```bash
kubectl apply -f k8s/namespace.yaml
kubectl config set-context --current --namespace=fortune
```

---

## 2. Database (StatefulSet)

`k8s/db.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: db
spec:
  clusterIP: None
  ports: [{ port: 5432 }]
  selector: { app: db }
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: db
spec:
  serviceName: db
  replicas: 1
  selector: { matchLabels: { app: db } }
  template:
    metadata: { labels: { app: db } }
    spec:
      containers:
        - name: postgres
          image: postgres:16
          env:
            - { name: POSTGRES_USER, value: fortune }
            - { name: POSTGRES_DB, value: fortune }
            - name: POSTGRES_PASSWORD
              valueFrom: { secretKeyRef: { name: db-secret, key: password } }
          ports: [{ containerPort: 5432 }]
          volumeMounts:
            - { name: data, mountPath: /var/lib/postgresql/data }
  volumeClaimTemplates:
    - metadata: { name: data }
      spec:
        accessModes: ["ReadWriteOnce"]
        resources: { requests: { storage: 1Gi } }
```

---

## 3. Secret + ConfigMap

```bash
kubectl create secret generic db-secret \
  --from-literal=password='changeme_before_prod'

kubectl create configmap backend-config \
  --from-literal=DATABASE_URL='postgresql+psycopg2://fortune:changeme_before_prod@db:5432/fortune' \
  --from-literal=CORS_ORIGINS='http://fortune.local'
```

(In production: use Sealed Secrets or External Secrets Operator. Mention this in interviews.)

---

## 4. Backend + Frontend Deployments

`k8s/backend.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata: { name: backend }
spec:
  selector: { app: backend }
  ports: [{ port: 8000, targetPort: 8000 }]
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: backend }
spec:
  replicas: 2
  selector: { matchLabels: { app: backend } }
  template:
    metadata: { labels: { app: backend } }
    spec:
      containers:
        - name: api
          image: ghcr.io/<you>/fortune-backend:<sha>
          ports: [{ containerPort: 8000 }]
          envFrom:
            - configMapRef: { name: backend-config }
          readinessProbe:
            httpGet: { path: /healthz, port: 8000 }
            initialDelaySeconds: 2
            periodSeconds: 5
          livenessProbe:
            httpGet: { path: /healthz, port: 8000 }
            initialDelaySeconds: 15
            periodSeconds: 20
          resources:
            requests: { cpu: "50m",  memory: "64Mi" }
            limits:   { cpu: "500m", memory: "256Mi" }
```

`k8s/frontend.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata: { name: frontend }
spec:
  selector: { app: frontend }
  ports: [{ port: 80, targetPort: 80 }]
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: frontend }
spec:
  replicas: 2
  selector: { matchLabels: { app: frontend } }
  template:
    metadata: { labels: { app: frontend } }
    spec:
      containers:
        - name: web
          image: ghcr.io/<you>/fortune-frontend:<sha>
          ports: [{ containerPort: 80 }]
```

Note: the frontend image's nginx config already proxies `/api/` to host `backend` — in K8s, that hostname resolves to the backend Service. Same behavior as docker-compose. 

---

## 5. Ingress

Enable NGINX ingress in kind:

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=120s
```

`k8s/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fortune
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "false"
spec:
  ingressClassName: nginx
  rules:
    - host: fortune.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service: { name: frontend, port: { number: 80 } }
```

Add `127.0.0.1 fortune.local` to `/etc/hosts`, then open http://fortune.local.

---

## 6. Apply everything

```bash
kubectl apply -f k8s/
kubectl get pods -w        # watch them come up
kubectl logs -f deploy/backend
```

Open http://fortune.local — cookie, history, favorites, all running on K8s.

---

## 7. Useful kubectl muscle memory

```bash
kubectl get pods                         # list
kubectl describe pod <name>              # why is it broken?
kubectl logs -f deploy/backend           # tail logs
kubectl exec -it deploy/backend -- sh    # shell into a pod
kubectl rollout restart deploy/backend   # rolling restart
kubectl rollout undo deploy/backend      # rollback to previous ReplicaSet
kubectl top pod                          # CPU/mem (needs metrics-server)
kubectl port-forward svc/backend 8000    # tunnel a service locally
```

---

## 8. CI/CD for K8s (sketch, don't implement unless you have time)

- Add a GH Actions step: `kubectl --context=… set image deploy/backend api=ghcr.io/.../fortune-backend:$SHA`.
- Or use Helm: `helm upgrade --install fortune ./chart --set image.tag=$SHA`.
- Or use Argo CD / Flux for GitOps — a separate rabbit hole.

For a portfolio project, **local kind + `kubectl apply` is enough**. Say in interviews: "I'd do GitOps with Argo CD in a team setting."

---

## 9. What to put in the README

```markdown
### Kubernetes (optional)
Local cluster via `kind`. Run:
    kind create cluster --name fortune
    kubectl apply -f k8s/
Visit http://fortune.local.
```

Plus one screenshot of `kubectl get all` with all pods Running. That's a credible "I know K8s basics" artifact.

---

## Definition of Done

- [ ] `kubectl get pods -n fortune` shows all pods Running.
- [ ] http://fortune.local works end-to-end.
- [ ] You can explain Deployment vs StatefulSet vs Service vs Ingress.
- [ ] You've rolled back once (`kubectl rollout undo`).
- [ ] You did NOT skip observability to get here.

You're done. Go polish the README and update your resume.
