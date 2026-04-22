# 03 — Feature Development (Programming Practice)

> Goal: **you code these yourself.** The MVP is a scaffold on purpose — holes to fill.
> Use the AI as a senior teammate: explain your plan first, then ask for feedback on your diff.

---

## How to approach each feature

For every feature below, follow this loop (write it on a sticky note):

```
1.  READ the existing code that's nearest to where the feature lives.
2.  PLAN in plain English in a scratch note:
       - what endpoints need to change
       - what the DB will look like after
       - what the UI will do
3.  IMPLEMENT the smallest slice that works end-to-end.
4.  TEST it manually (curl + clicking in the browser).
5.  COMMIT with a message like "feat: add favorites page".
6.  REVIEW: ask the AI "review this diff for correctness and style".
7.  REFACTOR if needed. Commit again.
```

**Don't skip step 2.** If you can't describe it, you can't build it.

---

## Tier 1 — Must do (pick all 3)

These are the starter features. They give you practice across all layers.

### 1. `♥ Favorites` page — **frontend + API**

**User story:** "As a user, I want to see only the fortunes I've hearted, on a dedicated page."

**Hints:**
- Backend: add `GET /api/fortunes?favorites_only=true` (query-param boolean).
- Edit `list_fortunes` in `routers/fortunes.py` to filter when flag is set.
- Frontend: add a tab or button that toggles `favoritesOnly` state and passes it through `api.js`.
- **Gotcha:** don't create a new endpoint for something that's just "the list with a filter". Prefer a query parameter.

**Stretch:**
- Add a count badge: `♥ Favorites (4)`.

---

### 2. Search — **API only (simple) or API + UI (real)**

**User story:** "Let me filter my history by keyword."

**Hints:**
- `GET /api/fortunes?q=smile`
- Backend: `.where(Fortune.message.ilike(f"%{q}%"))`  ← `ilike` = case-insensitive.
- Frontend: `<input>` with debounced state (trigger fetch 300ms after typing stops).
- **Write the API first; click it in Swagger UI; THEN wire the UI.**

**Stretch:**
- Persist search query in the URL (`?q=smile`) using `window.history.replaceState`.

---

### 3. "Add your own fortune" — **full CRUD thinking**

**User story:** "Let me submit a fortune that can appear in future draws."

**Hints:**
- `POST /api/fortunes` already exists — but it currently creates a row that `GET /random` ignores (because seed rows use id ≤ 1000).
- You have 2 options:
  - **Option A (quick fix):** remove the `id <= 1000` filter from `get_random_fortune` and add a `kind` column (`seed` vs `draw`).
  - **Option B (better):** refactor into 2 tables: `fortune_messages` and `fortune_draws` with a foreign key.
- **This is the refactor mentioned in `01-architecture.md`.** Doing Option B teaches you *migrations*.

**Stretch:**
- Add a profanity check (hand-rolled allow-list check, or the `better-profanity` Python package).

---

## Tier 2 — Stretch (pick any you fancy)

### 4. Pagination
- `GET /api/fortunes?limit=10&offset=20`
- Frontend: "Load more" button at the bottom.
- **Gotcha:** always order by something stable (`created_at DESC, id DESC`) or pages will shuffle.

### 5. Delete a fortune from your history
- `DELETE /api/fortunes/{id}`
- Trash-can icon in the UI. Confirm dialog.
- **Bonus:** soft-delete (add a `deleted_at` column).

### 6. Export as JSON
- `GET /api/fortunes/export` returns all draws as `application/json` with `Content-Disposition: attachment`.
- Button in the UI that clicks that URL.

### 7. Sound effect on crack
- Tiny `.mp3` in `frontend/public/`; play it from `FortuneCookie.jsx` using `new Audio()`.

### 8. Dark mode
- Tailwind has `dark:` variants. Add a toggle button. Persist in `localStorage`.

### 9. Rate limiting
- 10 random fortunes per minute per IP.
- `slowapi` package, or a handmade `dict`-based limiter. Great interview talking point.

### 10. Alembic migrations
- Install `alembic`, run `alembic init migrations`, autogenerate one migration, then *read what it generated*.
- This replaces `Base.metadata.create_all` for real projects.

---

## Tier 3 — Nice-to-have if you're flying

- **Infinite scroll** with IntersectionObserver.
- **Share button** — copy a deep link like `/?id=123` that auto-reveals that fortune.
- **Open Graph tags** so sharing the URL on Slack/Twitter shows the cookie image.
- **Basic E2E test** with Playwright (`npx playwright test`).

---

## Code-quality expectations (industry baseline)

When you submit a PR to your own repo, ask yourself:

| Check | Yes? |
|-------|------|
| Function names are verbs (`get_fortune`, `toggle_favorite`). Variable names are nouns. | |
| No duplicated logic between two files. If it's duplicated, extract. | |
| Any `try/except` actually handles something — not just swallows the error. | |
| No magic numbers; `limit=50` is OK, `id <= 1000` is borderline — add a comment. | |
| No committed secrets. `.env` is in `.gitignore`. | |
| Commit message reads like an English sentence. | |
| If it's a bug fix: the commit explains **what was wrong** and **why this fixes it**. | |

**Periodic AI code review prompt** (copy/paste):

> I just finished a change to `<file(s)>`. Please review for: (1) correctness,
> (2) naming clarity, (3) error handling, (4) any place I'm reinventing a wheel
> that a standard library covers, and (5) obvious security issues (SQL
> injection, secrets, XSS). Be blunt — I want to get better.

---

## Branching workflow (practice PRs on your own repo)

Even though it's your own repo, **work in branches**. Employers look at your PRs.

```bash
git checkout -b feat/favorites-page
# ... code ...
git commit -m "feat: add favorites page with filter"
git push -u origin feat/favorites-page
# then on GitHub: open a PR into main
```

Merge via "**Squash and merge**" — keeps `main` clean.

---

## Debugging checklist (read when stuck)

1. **Read the exact error message.** Copy it verbatim into your AI chat.
2. **Reproduce in the smallest way.** `curl` one endpoint. Open one browser tab.
3. **Which layer?** Is the bug in: React state? API route? SQL query? Print statements are fine.
4. **Check the browser console AND the terminal.** Both lie differently.
5. **Bisect.** Comment out half the code. Does the bug go away? Then it's in the commented half.
6. **Sleep on it.** Rested brain > stuck brain. Always true.

---

## Definition of Done for Week 2

- [ ] At least 3 Tier-1 features merged via PRs.
- [ ] Each PR got an AI review pass before merging.
- [ ] You've rebased at least once (`git pull --rebase`).
- [ ] You can explain, out loud, one bug you found and how you fixed it.

Next: [`04-cicd-guide.md`](04-cicd-guide.md).
