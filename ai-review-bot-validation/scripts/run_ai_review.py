#!/usr/bin/env python3
"""
AI-Review-Bot: Agno agent that reviews a PR diff and posts inline + summary feedback.

Usage:
  - In CI: set PR_DIFF_FILE, GITHUB_TOKEN, GITHUB_REPOSITORY, GITHUB_EVENT_PATH (or PR_NUMBER, HEAD_SHA).
  - Locally: PR_DIFF_FILE=/path/to/diff python scripts/run_ai_review.py --dry-run
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Repository root (script lives in scripts/)
REPO_ROOT = Path(__file__).resolve().parent.parent


def load_diff() -> str:
    """Load PR diff from file or stdin."""
    path = os.environ.get("PR_DIFF_FILE")
    if path and Path(path).exists():
        return Path(path).read_text()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def load_context() -> tuple[str, str, str]:
    """Load STYLE_GUIDE, ARCHITECTURE_IMPROVEMENTS, and ANTI_PATTERNS."""
    style = (REPO_ROOT / "STYLE_GUIDE.md").read_text()
    arch = (REPO_ROOT / "docs" / "ARCHITECTURE_IMPROVEMENTS.md").read_text()
    anti = (REPO_ROOT / "docs" / "ANTI_PATTERNS.md").read_text()
    return style, arch, anti


def build_system_prompt(style: str, arch: str, anti: str) -> str:
    """Build the Senior VCF Engineer persona and knowledge."""
    return f"""You are a Senior VCF Engineer performing a rigorous, professional code review.

## Repository knowledge

### Style guide
{style}

### Architecture / quality checklist
{arch}

### Anti-patterns to flag
{anti}

## Your task
Review the provided git diff. For each meaningful finding (style, security, performance, logic):
1. Produce up to 5 **inline comments** with: file path (as in the diff), line number (in the new file), and a short, actionable comment. Be specific and suggest a fix when possible.
2. Produce one **executive summary** that:
   - Grades the change on: Consistency, Quality, Security (use: Good / Needs improvement / Critical).
   - Lists the top 3 actionable improvements.

Respond with a single JSON object only, no markdown or extra text:
{{
  "inline_comments": [
    {{ "path": "<file path>", "line": <number>, "body": "<comment>" }}
  ],
  "summary": "<markdown summary with grades and top 3 items>"
}}
If there are no inline comments, use "inline_comments": [].
Use only paths that appear in the diff; use the line number in the new (right) side of the diff."""


def run_agent(diff: str, style: str, arch: str, anti: str) -> str:
    """Run Agno agent with Gemini and return raw response."""
    try:
        from agno.agent import Agent
        from agno.models.google import Gemini
    except ImportError as e:
        sys.exit(f"Install agno[google]: pip install 'agno[google]' — {e}")

    if not os.environ.get("GOOGLE_API_KEY"):
        sys.exit("Set GOOGLE_API_KEY to run the review agent.")

    model_id = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    agent = Agent(
        model=Gemini(id=model_id),
        instruction=build_system_prompt(style, arch, anti),
        markdown=False,
    )
    user_message = f"Review this git diff and respond with the JSON object only.\n\n```diff\n{diff}\n```"
    response = agent.run(user_message)
    # Agno returns RunOutput with .content
    if hasattr(response, "content") and response.content is not None:
        return response.content if isinstance(response.content, str) else str(response.content)
    if isinstance(response, str):
        return response
    return str(response)


def parse_json_response(raw: str) -> dict:
    """Extract JSON from agent response (handle markdown code block)."""
    raw = raw.strip()
    # Try to find JSON in a code block
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if match:
        raw = match.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: find first { ... }
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {"inline_comments": [], "summary": raw[:2000]}


def post_to_github(
    inline_comments: list[dict],
    summary: str,
    repo: str,
    pr_number: int,
    head_sha: str,
    token: str,
) -> None:
    """Post inline comments and summary to the PR."""
    import requests

    owner, repo_name = repo.split("/", 1)
    base = f"https://api.github.com/repos/{owner}/{repo_name}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    for c in inline_comments:
        path = c.get("path") or c.get("file")
        line = c.get("line")
        body = c.get("body") or c.get("comment")
        if not path or line is None or not body:
            continue
        r = requests.post(
            f"{base}/pulls/{pr_number}/comments",
            headers=headers,
            json={
                "commit_id": head_sha,
                "path": path,
                "line": int(line),
                "body": body[:65536],
                "side": "RIGHT",
            },
            timeout=30,
        )
        if not r.ok:
            print(f"Warning: failed to post comment on {path}:{line} — {r.status_code} {r.text[:200]}", file=sys.stderr)

    # Post summary as a single PR comment
    summary_body = f"## AI-Review-Bot — Executive summary\n\n{summary}"
    r = requests.post(
        f"{base}/issues/{pr_number}/comments",
        headers=headers,
        json={"body": summary_body[:65536]},
        timeout=30,
    )
    if not r.ok:
        print(f"Warning: failed to post summary comment — {r.status_code} {r.text[:200]}", file=sys.stderr)
    else:
        print("Posted summary comment to PR.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI-Review-Bot on a PR diff.")
    parser.add_argument("--dry-run", action="store_true", help="Print feedback only; do not post to GitHub.")
    args = parser.parse_args()

    diff = load_diff()
    if not diff.strip():
        print("No diff provided. Set PR_DIFF_FILE or pipe a diff to stdin.", file=sys.stderr)
        sys.exit(1)

    style, arch, anti = load_context()
    print("Running Agno agent (Gemini)...", file=sys.stderr)
    raw = run_agent(diff, style, arch, anti)
    data = parse_json_response(raw)

    inline = data.get("inline_comments") or []
    summary = data.get("summary") or "No summary generated."

    if args.dry_run:
        print("=== Inline comments ===")
        for c in inline:
            print(f"  {c.get('path', '?')}:{c.get('line', '?')} — {c.get('body', '')[:80]}...")
        print("\n=== Summary ===")
        print(summary)
        return

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    pr_number = os.environ.get("PR_NUMBER")
    head_sha = os.environ.get("HEAD_SHA")

    if not token or not repo or not pr_number or not head_sha:
        print("In CI, set GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER, HEAD_SHA.", file=sys.stderr)
        print("Falling back to dry-run output.", file=sys.stderr)
        print(json.dumps({"inline_comments": inline, "summary": summary}, indent=2))
        sys.exit(0)

    post_to_github(inline, summary, repo, int(pr_number), head_sha, token)
    print("Done.")


if __name__ == "__main__":
    main()
