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
    """Load STYLE_GUIDE, ARCHITECTURE_IMPROVEMENTS, and ANTI_PATTERNS; use fallbacks if missing."""
    fallback = "No repository-specific guide found. Apply general best practices: clarity, security, consistency."
    style_path = REPO_ROOT / "STYLE_GUIDE.md"
    arch_path = REPO_ROOT / "docs" / "ARCHITECTURE_IMPROVEMENTS.md"
    anti_path = REPO_ROOT / "docs" / "ANTI_PATTERNS.md"
    style = style_path.read_text() if style_path.exists() else fallback
    arch = arch_path.read_text() if arch_path.exists() else fallback
    anti = anti_path.read_text() if anti_path.exists() else fallback
    return style, arch, anti


def build_system_prompt(style: str, arch: str, anti: str) -> str:
    """Build the Senior Engineer persona and knowledge."""
    return f"""You are a Senior Engineer doing a minimal, high-signal code review.

## Repository knowledge

### Style guide
{style}

### Architecture / quality checklist
{arch}

### Anti-patterns to flag
{anti}

## Rules (strict)
- Comment **only on must-fix issues**: real bugs, security risks, or blocking quality problems. Do not add nitpicks, style-only suggestions, or optional improvements.
- Add **at most 3 inline comments**. If nothing must be fixed, return zero comments.
- Each comment: **one short sentence** with the fix (e.g. "Use env var for path." or "Catch NumberFormatException and log."). No preamble.
- **Summary**: 1–2 sentences only. Say whether the change is fine or list the one thing that must be fixed. No tables, no bullet lists, no extra detail.
- Do not pollute the PR. Less is more.

**Output format:** Reply with ONLY a single JSON object. No markdown code fences (no ```), no text before or after.
{{
  "inline_comments": [
    {{ "path": "<file path>", "line": <number>, "body": "<one short sentence>" }}
  ],
  "summary": "<1–2 sentences only>"
}}
If there are no must-fix issues, use "inline_comments": [] and set summary to e.g. "LGTM." or "No must-fix issues."
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

    # Default to a current stable model (gemini-1.5-flash is deprecated / not found in v1beta)
    model_id = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    agent = Agent(
        model=Gemini(id=model_id),
        instructions=build_system_prompt(style, arch, anti),
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
    """Extract JSON from agent response; always return dict with non-empty summary."""
    raw = (raw or "").strip()

    # If the API returned an error (e.g. model not found), surface it clearly
    if '"error"' in raw and '"code"' in raw and '"message"' in raw:
        try:
            err = json.loads(raw)
            msg = err.get("error", {}).get("message", raw[:500])
            return {
                "inline_comments": [],
                "summary": (
                    "**Gemini API error.** The review could not be completed.\n\n"
                    f"Message: {msg}\n\n"
                    "Common fixes: set `GEMINI_MODEL` to a current model (e.g. `gemini-2.5-flash`) "
                    "or check [Gemini models](https://ai.google.dev/gemini-api/docs/models)."
                ),
            }
        except (json.JSONDecodeError, TypeError):
            pass

    json_str = raw

    # Try to find JSON in a code block (greedy so nested braces are included)
    for pattern in (r"```(?:json)?\s*(\{.*\})\s*```", r"```\s*(\{.*\})\s*```"):
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
            break
    else:
        # No code block: use first { ... } (greedy to get full object)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            json_str = match.group(0)

    try:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            raise json.JSONDecodeError("Not a dict", "", 0)
        # Normalize: accept alternative keys for summary
        summary = (
            (data.get("summary") or data.get("executive_summary") or data.get("overall_summary"))
            or ""
        )
        if isinstance(summary, str) and summary.strip():
            data["summary"] = summary.strip()
        else:
            data["summary"] = _fallback_summary(raw)
        data["inline_comments"] = data.get("inline_comments") or []
        return data
    except (json.JSONDecodeError, TypeError):
        pass
    return {"inline_comments": [], "summary": _fallback_summary(raw)}


def _fallback_summary(raw: str) -> str:
    """Build a fallback summary when JSON parsing fails or summary is missing."""
    if not (raw or "").strip():
        return "The review agent did not return any output. Check Actions logs for errors."
    truncated = (raw.strip()[:1800] + "…") if len(raw) > 1800 else raw.strip()
    return (
        "**Summary could not be parsed as structured JSON.** Below is the raw agent output (truncated):\n\n"
        "---\n\n"
        + truncated
    )


def post_to_github(
    inline_comments: list[dict],
    summary_body: str,
    repo: str,
    pr_number: int,
    head_sha: str,
    token: str,
) -> None:
    """Post inline comments and summary to the PR."""
    import requests

    # Support GitHub Enterprise (e.g. GITHUB_API_URL = https://github.gwd.broadcom.net/api/v3)
    api_base = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    owner, repo_name = repo.split("/", 1)
    base = f"{api_base}/repos/{owner}/{repo_name}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    for c in inline_comments[:3]:
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
    r = requests.post(
        f"{base}/issues/{pr_number}/comments",
        headers=headers,
        json={"body": (summary_body or "").strip()[:65536]},
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
    summary_body = f"## AI-Review-Bot\n\n{summary}"

    if args.dry_run:
        print("=== Inline comments ===")
        for c in inline:
            print(f"  {c.get('path', '?')}:{c.get('line', '?')} — {c.get('body', '')[:80]}...")
        print("\n=== Summary (comment body) ===")
        print(summary_body)
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

    post_to_github(inline, summary_body, repo, int(pr_number), head_sha, token)
    print("Done.")


if __name__ == "__main__":
    main()
