# Contributing to Trade-Agentic

Welcome, and thanks for being part of this project. Please read this before you write a single line of code.

---

## Table of Contents
- [Project Structure](#project-structure)
- [Branch Strategy](#branch-strategy)
- [Getting Started](#getting-started)
- [Making a Contribution](#making-a-contribution)
- [Commit Messages](#commit-messages)
- [Pull Request Rules](#pull-request-rules)
- [Code Standards](#code-standards)
- [The Non-Negotiables](#the-non-negotiables)

---

## Project Structure

The project is built in 8 phases. Every phase has its own staging branch. Your work lives in feature branches cut from the relevant phase branch.

```
main                        ← stable releases only
dev                         ← integration branch
phase/N-name                ← phase staging branches
feat/phase-N/your-feature   ← your working branch
```

**Flow:** `your feature branch → phase branch → dev → main`

---

## Branch Strategy

### Branch Naming

| Type | Pattern | Example |
|---|---|---|
| Feature | `feat/phase-N/description` | `feat/phase-2/ibef-scraper` |
| Bug Fix | `fix/phase-N/description` | `fix/phase-3/yfinance-null` |
| Refactor | `refactor/description` | `refactor/base-agent-cleanup` |
| Docs | `docs/description` | `docs/rag-setup` |

### Always cut your branch from the correct phase branch
```bash
git checkout phase/2-rag-pipeline
git pull origin phase/2-rag-pipeline
git checkout -b feat/phase-2/your-feature
```

---

## Getting Started

### 1. Fork & Clone
```bash
git clone https://github.com/your-org/Trade-Agentic.git
cd Trade-Agentic
```

### 2. Set Up Environment
```bash
uv venv .venv
source .venv/bin/activate        
uv sync
cp .env.example .env          # fill in your API keys
```


---

## Making a Contribution

### Step-by-step

```bash
# 1. Sync the phase branch
git checkout phase/N-name
git pull origin phase/N-name

# 2. Create your feature branch
git checkout -b feat/phase-N/your-feature

# 3. Write code 

# 4. Stage and commit
git add .
git commit -m "feat(scope): what you did"

# 5. Push
git push origin feat/phase-N/your-feature

# 6. Open a PR on GitHub → base: phase/N-name
```

### Keeping your branch up to date
If the phase branch has moved ahead of your branch:
```bash
git fetch origin
git rebase origin/phase/N-name
git push origin feat/phase-N/your-feature --force-with-lease
```

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): short description
```

| Type | When to use |
|---|---|
| `feat` | New functionality |
| `fix` | Bug fix |
| `refactor` | Code cleanup, no behaviour change |
| `test` | Adding or updating tests |
| `docs` | Documentation only |
| `ci` | CI/CD config changes |

**Examples:**
```
feat(tools): add yfinance OHLCV fetcher
fix(rag): handle empty PDF pages in chunker
test(agents): add unit tests for bull researcher
docs(readme): update RAG pipeline setup steps
```

---

## Pull Request Rules

- **Title format:** `[Phase N] type: short description`
- **Base branch:** Always the phase branch, never `dev` or `main` directly
- **One feature = one PR.** Don't bundle unrelated changes.
- **Link the related Issue** in the PR description.
- **CI must pass** before requesting a review.
- **At least 1 approval** required before merging a feature → phase branch.
- **Squash and merge** is the merge method for feature → phase PRs.
- **Delete your branch** after it is merged.

### PR Description Template
```
## What this does
Brief description of the change.

## Related Issue
Closes #<issue-number>

## How to test
Steps to verify the change works.

## Notes
Anything reviewers should know.
```
---

## The Non-Negotiables

```
1. Never push directly to main or dev
2. Always branch from the correct phase branch
3. Never commit .env or any file containing secrets
4. CI checks must pass before requesting a review
5. Rebase to sync — do not merge upstream into your branch
6. One PR per feature — keep changes focused
7. Delete your branch after it is merged
```

---
