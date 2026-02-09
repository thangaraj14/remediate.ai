# AI-Review-Bot Validation Project

This repository is a **validation harness** for the AI-Review-Bot—an agentic automation layer that integrates into the GitHub CI/CD pipeline. It uses the [Agno](https://agno.com) framework with Gemini to provide contextual, high-reasoning feedback on every Pull Request.

## Executive Summary

- **Trigger**: `pull_request` (opened / synchronize) → GitHub Action runs.
- **Context**: Deep checkout + `git diff` isolation.
- **Brain**: Agno Agent with Senior Engineer persona + repository knowledge (STYLE_GUIDE, anti-patterns).
- **LLM**: Gemini 1.5 Pro/Flash for security, performance, and readability analysis.
- **Output**: Inline comments on the diff + executive summary comment on the PR.

## How to Validate the Flow

### 1. Push this repo to GitHub

```bash
git init
git add .
git commit -m "Initial AI-Review-Bot validation project"
git remote add origin https://github.com/YOUR_ORG/ai-review-bot-validation.git
git push -u origin main
```

### 2. Configure secrets

In **Settings → Secrets and variables → Actions**, add:

| Secret            | Description |
|-------------------|-------------|
| `GOOGLE_API_KEY`  | Google AI / Gemini API key ([create one](https://aistudio.google.com/apikey)) |
| `GITHUB_TOKEN`    | Usually provided by the workflow; for custom bots you may add a PAT with `repo` scope |

Optional: set **`GEMINI_MODEL`** in the workflow env (or repo variables) to override the default `gemini-2.5-flash` (e.g. `gemini-2.0-flash`, `gemini-2.5-pro`). See [Gemini models](https://ai.google.dev/gemini-api/docs/models).

The workflow uses the built-in `GITHUB_TOKEN`; the job has `pull-requests: write` so it can post comments without an extra Personal Access Token.

### 3. Open a Pull Request

- Create a branch: `git checkout -b feature/sample-change`
- Make a small code change (e.g. edit `src/services/calculator.py` or add a file).
- Push and open a PR against `main`.

### 4. Verify the flow

1. **Action runs**: In the PR, check the **Actions** tab; workflow `AI Review Bot` should run.
2. **Inline comments**: After the run, review the **Files changed** tab for inline comments from the bot.
3. **Summary comment**: Check the PR **Conversation** for a single comment with the executive summary (Consistency, Quality, Security).

## Project layout

```
.github/workflows/   # AI Review workflow (trigger, diff, run script, post feedback)
docs/                # Architecture checklist, anti-patterns
src/                 # Sample app (intentional patterns for the bot to review)
scripts/             # Agno-based review runner and GitHub API poster
STYLE_GUIDE.md       # Team style context injected into the agent
```

## Local run (optional)

To test the review script without GitHub:

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
export GOOGLE_API_KEY=your_key
# Provide diff via file or stdin
git diff main...HEAD > /tmp/pr.diff
PR_DIFF_FILE=/tmp/pr.diff python scripts/run_ai_review.py --dry-run
```

## Requirements

- Python 3.10+
- `agno[google]` for Gemini; see `requirements.txt`.

## Why are no review comments appearing?

If the workflow runs but no inline/summary comments are posted, check:

1. **Workflow is in this repo**  
   The AI Review Bot only runs when `.github/workflows/ai-review.yml` is in the **same repo** as the PR. If you opened a PR in a different repo (e.g. `remediate.ai`), copy this workflow plus `scripts/`, `requirements.txt`, and optional `STYLE_GUIDE.md` / `docs/` into that repo.

2. **GOOGLE_API_KEY is set**  
   In the PR’s **Actions** tab, open the “AI Review Bot” run. If you see  
   `::error::GOOGLE_API_KEY is not set...`, add the secret in **Settings → Secrets and variables → Actions** and re-run the workflow (or push a small commit).

3. **Workflow ran from the PR branch**  
   The workflow runs from the branch that has the PR. Ensure that branch contains `.github/workflows/ai-review.yml` (and `scripts/run_ai_review.py`, `requirements.txt`). If the workflow was only added on `main` after the PR was opened, push a commit to the PR branch or re-run the workflow.

4. **GitHub Enterprise**  
   The script uses `GITHUB_API_URL` (set in the workflow from `github.server_url`). If you use a different API base, set `GITHUB_API_URL` in the workflow env.

## Validation checklist

After pushing and opening a PR, confirm:

- [ ] Workflow **AI Review Bot** appears under the Actions tab and runs on the PR.
- [ ] No workflow failure due to missing `GOOGLE_API_KEY` (add the secret if you want the bot to run).
- [ ] When the secret is set: a new **comment** appears on the PR with the executive summary (Consistency, Quality, Security).
- [ ] When the secret is set: **inline comments** appear on the **Files changed** tab on the relevant lines (if the agent produced any).

## License

Internal validation use.
