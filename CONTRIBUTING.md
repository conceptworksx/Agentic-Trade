# Contributing Guide

Thank you for contributing! This document outlines the branching strategy, workflow, and conventions every contributor must follow to keep the codebase clean and collaborative.

---

## Table of Contents

- [Branching Strategy](#branching-strategy)
- [Branch Naming Convention](#branch-naming-convention)
- [Development Workflow](#development-workflow)
- [Commit Message Format](#commit-message-format)
- [Pull Request Guidelines](#pull-request-guidelines)
- [After Your PR is Merged](#after-your-pr-is-merged)
- [Branch Cleanup](#branch-cleanup)
- [Secrets Handling](#secrets-handling)
- [Important Rules](#important-rules)

---

## Branching Strategy

```
main  →  production-ready, stable code
dev   →  active development branch
```

All new work **must** be done on a feature branch created from the latest `dev`.Direct commits to `main` or `dev` are not allowed.

---
## 🔗 Repository Setup

We use a fork-based workflow:

- `upstream` → original organization repository  
- `origin` → your forked repository  

All pushes should go to your fork (`origin`), and Pull Requests should target `upstream/dev`.

## Branch Naming Convention

Use the following format:

```
feature/<area>-<what-it-does>
```

**Examples:**

| Branch Name | Purpose |
|---|---|
| `feature/news-analysis` | News analysis module |
| `feature/news-sentiment` | Sentiment scoring for news |
| `feature/market-signal` | Market signal generation |

> Keep names lowercase, hyphen-separated, and descriptive enough to understand at a glance.

---

## Development Workflow

### 1. Sync your local `dev`

Always start from an up-to-date `dev`:

```bash
git checkout dev
git fetch upstream
git merge upstream/dev
```

### 2. Create a feature branch

```bash
git checkout -b feature/<branch-name>
```

### 3. Implement your changes

- Write your code
- Test locally before committing
- Keep changes focused — one feature or fix per branch

### 4. Commit your changes

Stage and commit with a descriptive message:

```bash
git add .
git commit -m "feat(<area>): short description of change"
```

See [Commit Message Format](#commit-message-format) for full conventions.

### 5. Sync before pushing *(important)*

Sync with the latest `dev` to catch any conflicts early:
```bash
git fetch upstream
git merge upstream/dev
```

Resolve any conflicts, then verify your changes still work as expected.

### 6. Push to your fork

```bash
git push origin feature/<branch-name>
```

### 7. Open a Pull Request

- **From:** `your-fork/feature/<branch-name>`
- **To:** `org-repo/dev`

Fill in the PR title and description following the [Pull Request Guidelines](#pull-request-guidelines).

---

## Commit Message Format

Follow the [Conventional Commits](https://www.conventionalcommits.org/) standard:

```
<type>(<area>): short description
```

| Type | When to use |
|---|---|
| `feat` | Adding a new feature |
| `fix` | Fixing a bug |
| `chore` | Refactoring, tooling, or config changes |
| `docs` | Documentation only changes |
| `test` | Adding or updating tests |

**Examples:**

```
feat(news): add news analysis agent
fix(news): handle missing article summary
chore(builder): refactor node setup logic
docs(api): update endpoint usage notes
```

> Keep the subject line under 72 characters. Use the commit body for additional context if needed.

---

## Pull Request Guidelines

### Title

Use the same format as commit messages:

```
feat(<area>): short description
```

### Description

Use bullet points to describe what changed:

```
- Added <X> to support <Y>
- Implemented <Z> integration
- Refactored <module> for clarity
```

### Checklist before requesting review

- [ ] Code tested locally
- [ ] No secrets or API keys committed
- [ ] Branch is synced with latest `upstream/dev`
- [ ] PR is focused — one feature or fix only
- [ ] PR title follows the commit convention
- [ ] Feature works end-to-end (if applicable)
---

## After Your PR is Merged

Sync your local `dev` with the upstream:

```bash
git checkout dev
git fetch upstream
git reset --hard upstream/dev
```

---

## Branch Cleanup

Once your PR is merged, clean up to keep the repo tidy.

**Delete local branch:**

```bash
git branch -d feature/<branch-name>
```

**Delete branch from your fork:**

```bash
git push origin --delete feature/<branch-name>
```

> Deleting a branch does **not** delete your work. All commits are preserved in `dev` and the PR history.

---

## Secrets Handling

**Never commit real credentials.** This includes API keys, tokens, passwords, or any sensitive configuration.

Use placeholders in example files:

```env
API_KEY=your_api_key_here
DATABASE_URL=your_database_url_here
```

Add a `.env.example` file to the repo, and make sure `.env` is listed in `.gitignore`.

If you accidentally commit a secret, treat it as **compromised immediately** — rotate it regardless of whether you've pushed it.

---

## Important Rules

### ❌ Never

- Commit directly to `main` or `dev`
- Push secrets, API keys, or tokens
- Create branches from other feature branches
- Submit PRs with unrelated changes bundled together

### ✅ Always

- Branch from `dev`
- Use clear, consistent branch and commit naming
- Sync with `upstream/dev` before pushing
- Keep PRs focused and minimal in scope
- Clean up branches after merge

---

## Quick Reference

```
sync dev → create branch → code → commit → sync → push → PR → merge → cleanup
```

---

*For questions or clarifications, open a discussion or reach out to a maintainer.*