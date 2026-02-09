# AI-Review-Bot Validation Project

This folder is a **validation harness** for the AI-Review-Bot—an agentic automation layer that integrates into the GitHub CI/CD pipeline. It uses the [Agno](https://agno.com) framework with Gemini to provide contextual, high-reasoning feedback on every Pull Request.

**In this repo**, the bot lives at **repository root**: workflow `.github/workflows/ai-review.yml`, `scripts/run_ai_review.py`, `requirements.txt`, `STYLE_GUIDE.md`, and `docs/` are at the parent directory. This folder holds only the validation sample code and this README.

## Executive Summary

- **Trigger**: `pull_request` (opened / synchronize) → GitHub Action runs.
- **Context**: Deep checkout + `git diff` isolation.
- **Brain**: Agno Agent with "Senior Engineer" persona + repository knowledge (STYLE_GUIDE, anti-patterns).
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

The workflow uses the built-in `GITHUB_TOKEN`; the job has `pull-requests: write` so it can post comments without an extra Personal Access Token.

### 3. Open a Pull Request

- Create a branch: `git checkout -b feature/sample-change`
- Make a small code change (e.g. edit `src/services/calculator.py` or add a file).
- Push and open a PR against `main`.

### 4. Verify the flow

1. **Action runs**: In the PR, check the **Actions** tab; workflow `AI Review Bot` should run.
2. **Inline comments**: After the run, review the **Files changed** tab for inline comments from the bot.
3. **Summary comment**: Check the PR **Conversation** for a single comment with the executive summary (Consistency, Quality, Security).

## Project layout (this repo)

- **Repository root** (parent of this folder): `.github/workflows/`, `scripts/run_ai_review.py`, `requirements.txt`, `STYLE_GUIDE.md`, `docs/` (architecture + anti-patterns).
- **This folder** (`ai-review-bot-validation/`): `src/` (sample app for the bot to review), `review/` (sample Java), this README.

## Local run (optional)

From the **repository root** (parent of this folder):

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
export GOOGLE_API_KEY=your_key
git diff main...HEAD > /tmp/pr.diff
PR_DIFF_FILE=/tmp/pr.diff python scripts/run_ai_review.py --dry-run
```

## Requirements

- Python 3.10+
- `agno[google]` for Gemini; see `requirements.txt`.

## Why are no review comments appearing?

If the workflow runs but no inline/summary comments are posted, check:

1. **Workflow is in this repo**  
   The AI Review Bot only runs when `.github/workflows/ai-review.yml` is in the **same repo** as the PR. In this repo the workflow and `scripts/run_ai_review.py`, `requirements.txt`, `STYLE_GUIDE.md`, and `docs/` live at the repository root.

2. **GOOGLE_API_KEY is set**  
   In the PR’s **Actions** tab, open the “AI Review Bot” run. If you see  
   `::error::GOOGLE_API_KEY is not set...`, add the secret in **Settings → Secrets and variables → Actions** and re-run the workflow (or push a small commit).

3. **Workflow ran from the PR branch**  
   The workflow runs from the branch that has the PR. Ensure that branch contains `.github/workflows/ai-review.yml` and the root `scripts/run_ai_review.py` and `requirements.txt`. If the workflow was only added on `main` after the PR was opened, push a commit to the PR branch or re-run the workflow.

4. **GitHub Enterprise**  
   The script uses `GITHUB_API_URL` (set in the workflow from `github.server_url`). If you use a different API base, set `GITHUB_API_URL` in the workflow env.

## Ensuring review comments get resolved

**In-repo check (code):** The **Require review resolved** check runs after the AI Review Bot (in the same workflow) and fails until all review threads are resolved. It uses `scripts/check_review_resolved.py` and the GitHub GraphQL API.

**How to get the check to re-run and turn green after you resolve all comments**

GitHub does not send any event when you click “Resolve conversation”, so the check will not re-run by itself. Use one of these:

1. **Push a commit (recommended)**  
   After resolving all threads, push any commit to the PR branch (e.g. `git commit --allow-empty -m "Resolved review comments" && git push`). The **Require review resolved** workflow runs on **push** for branches that have an open PR; the run is attached to your commit, so the check **appears and updates on the PR**. If all threads are resolved, the check passes.

2. **Manual re-run from Actions**  
   Go to **Actions** → **Require review resolved** → **Run workflow**. Choose the **PR branch** (e.g. `test-pr-10`) from the dropdown, enter the **PR number** (e.g. `11`), then click **Run workflow**. The run is for that branch, so the check shows on the PR.

3. **Add a comment**  
   Adding a comment on the PR (or replying to a review comment) also triggers the workflow, but runs triggered by comments are tied to the default branch, so the result **may not appear as a status check on the PR**. Prefer (1) or (2) if you need the check to update on the PR.

**Resolving the bot’s comments**  
Open the **Files changed** tab, find each AI comment thread, then fix the code and **Resolve conversation**, or reply (e.g. “Won’t fix”) and **Resolve conversation**. Then use (1) or (2) above to re-run the check.

**Branch protection (optional)**  
To block merge until the check passes, add **Require review resolved** (or the **check-resolved** job) as a required status check in **Settings** → **Branches** → branch protection.

## Validation checklist

After pushing and opening a PR, confirm:

- [ ] Workflow **AI Review Bot** appears under the Actions tab and runs on the PR.
- [ ] No workflow failure due to missing `GOOGLE_API_KEY` (add the secret if you want the bot to run).
- [ ] When the secret is set: a new **comment** appears on the PR with the executive summary (Consistency, Quality, Security).
- [ ] When the secret is set: **inline comments** appear on the **Files changed** tab on the relevant lines (if the agent produced any).

## License

Internal validation use.
