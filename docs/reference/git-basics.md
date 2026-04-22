# Git Basics — Daily Workflow Cheat Sheet

> You'll use 10 commands 95% of the time. Learn those. Ignore the rest until you need them.

---

## First-time setup

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
git config --global pull.rebase false          # merge-style pulls by default
```

Generate an SSH key and add it to GitHub so you stop typing passwords:

```bash
ssh-keygen -t ed25519 -C "you@example.com"
cat ~/.ssh/id_ed25519.pub      # paste to GitHub → Settings → SSH Keys
ssh -T git@github.com          # should say "Hi <you>!"
```

---

## The daily 10 commands

| Task | Command |
|------|---------|
| See what's changed | `git status` |
| See the actual changes | `git diff` |
| See staged changes | `git diff --cached` |
| Stage a file | `git add path/to/file` |
| Stage interactively (recommended) | `git add -p` |
| Commit | `git commit -m "feat: add favorites filter"` |
| Push | `git push` |
| Pull latest | `git pull` |
| Branch + switch | `git checkout -b feat/foo` |
| Switch back | `git checkout main` |

---

## Branching workflow (use this every time)

```bash
git checkout main
git pull
git checkout -b feat/favorites-page

# ...work, commit...
git push -u origin feat/favorites-page
# open a PR on GitHub → squash merge
```

After merging:

```bash
git checkout main
git pull
git branch -d feat/favorites-page   # delete local copy
```

---

## Commit messages (Conventional Commits — real industry standard)

```
<type>: <short summary>

<optional longer body>
```

Types to know: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`.

Examples:
- `feat: add favorites filter on history page`
- `fix: handle empty message in crack endpoint`
- `docs: clarify seed-vs-draw distinction`
- `chore: bump tailwind to 3.4.13`

---

## When you screw up

| Oops | Fix |
|------|-----|
| Committed to the wrong branch | `git log` → copy SHAs → `git checkout correct-branch` → `git cherry-pick <sha>` → go back and `git reset --hard HEAD~1` on the wrong branch |
| Committed something secret | **Rotate the secret first.** Then `git reset HEAD~1`, remove the file, recommit. If already pushed: `git push --force-with-lease`. Assume it's public — bots scrape pushes in seconds. |
| Want to undo the last commit but keep changes | `git reset --soft HEAD~1` |
| Want to undo the last commit and lose changes | `git reset --hard HEAD~1` |
| Working tree is a mess, want to start over | `git stash` (saves) or `git checkout .` (wipes) |
| Merge conflict | Open the file. Look for `<<<<<<<` markers. Keep the lines you want. Delete markers. `git add` + `git commit`. |
| Pulled and got a merge commit you don't want | `git pull --rebase` next time; to undo now, `git reset --hard origin/<branch>` |

---

## Rebase vs merge (the only thing you need to know)

- Small branch, feature just for you: `git pull --rebase` + rebase your feature onto `main` before merging. Keeps history linear.
- Shared long-lived branch: merge, don't rebase. Rewriting shared history is rude.

For this solo project: **always rebase, always squash merge.**

---

## Tags for releases (start doing this in Week 4)

```bash
git tag -a v0.1.0 -m "first deployable version"
git push origin v0.1.0
```

Your Docker image can then be tagged `fortune-backend:v0.1.0` instead of a SHA — cleaner for the "run the previous version" story.

---

## .gitignore — what NEVER to commit

- `node_modules/`, `.venv/` — regeneratable
- `.env`, `*.pem`, `*.key` — secrets
- `terraform.tfstate*` — state
- `dist/`, `build/` — build outputs
- `.DS_Store`, `Thumbs.db` — OS noise

Already handled by the scaffold's `.gitignore` files.

---

## One small habit that will save you

**`git status` before EVERY commit.** Read every line. If something's in the staging area that shouldn't be, unstage it now (`git restore --staged path`). This one habit prevents 90% of "oh no I committed the .env" moments.
