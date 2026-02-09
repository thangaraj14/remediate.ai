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
- Make a small code change (e.g. edit a file in `review/` or add any file).
- Push and open a PR against `main`.

### 4. Verify the flow

1. **Action runs**: In the PR, check the **Actions** tab; workflow `AI Review Bot` should run.
2. **Inline comments**: After the run, review the **Files changed** tab for inline comments from the bot.
3. **Summary comment**: Check the PR **Conversation** for a single comment with the executive summary (Consistency, Quality, Security).

## Project layout (this repo)

- **Repository root** (parent of this folder): `.github/workflows/`, `scripts/run_ai_review.py`, `requirements.txt`, `STYLE_GUIDE.md`, `docs/` (architecture + anti-patterns), **`ai-review.config.json`** (optional bot configuration).
- **This folder** (`ai-review-bot-validation/`): `review/` (sample code for the bot to review), this README.

## Configuration (per-project)

Admins can tune the AI Review Bot per repo by editing **`ai-review.config.json`** at the repository root. Omit the file to use defaults. This makes the template reusable across multiple projects.

| Key | Default | Description |
|-----|---------|-------------|
| `max_inline_comments` | `5` | Maximum number of inline comments to post on the PR. |
| `allow_good_to_have_inline` | `false` | If `true`, the bot may post some "good to have" suggestions as inline comments (not only in the summary). |
| `summary_grades` | `["Consistency", "Quality", "Security"]` | Dimensions to grade in the executive summary (e.g. add "Performance", "Tests"). |
| `max_required_in_summary` | `3` | Max bullets for "Required changes" in the summary. |
| `max_good_to_have_in_summary` | `3` | Max bullets for "Good to have" in the summary. |
| `required_description` | *(see below)* | Short description of what counts as "required" (injected into the prompt). |
| `good_to_have_description` | *(see below)* | Short description of what counts as "good to have". |
| `custom_instructions` | `""` | Optional extra instructions appended to the prompt (project-specific rules). |
| `model` | `""` | Gemini model id (e.g. `gemini-2.5-flash`). Empty = use env `GEMINI_MODEL` or default. |

Example `ai-review.config.json` for a stricter project:

```json
{
  "max_inline_comments": 3,
  "allow_good_to_have_inline": false,
  "summary_grades": ["Consistency", "Quality", "Security", "Tests"],
  "max_required_in_summary": 5,
  "max_good_to_have_in_summary": 3,
  "custom_instructions": "Focus on security and dependency hygiene. Flag any new external API calls."
}
```

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

## Validation checklist

After pushing and opening a PR, confirm:

- [ ] Workflow **AI Review Bot** appears under the Actions tab and runs on the PR.
- [ ] No workflow failure due to missing `GOOGLE_API_KEY` (add the secret if you want the bot to run).
- [ ] When the secret is set: a new **comment** appears on the PR with the executive summary (Consistency, Quality, Security).
- [ ] When the secret is set: **inline comments** appear on the **Files changed** tab on the relevant lines (if the agent produced any).

## License

Internal validation use.
