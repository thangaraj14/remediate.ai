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

# Default config (used when ai-review.config.json is missing or invalid).
# See README.md#configuration and ai-review.config.example.json for all options.
DEFAULT_CONFIG = {
    "max_inline_comments": 5,
    "allow_good_to_have_inline": False,
    "post_inline_comments": True,
    "diff_max_lines": 0,
    "summary_grades": ["Consistency", "Quality", "Security"],
    "max_required_in_summary": 3,
    "max_good_to_have_in_summary": 3,
    "required_description": "Must-fix items (bugs, security issues, critical style/architecture violations, logic errors).",
    "good_to_have_description": "Optional improvements (readability, minor style, refactors).",
    "custom_instructions": "",
    "model": "",
}


def load_config() -> dict:
    """Load ai-review.config.json from repo root; merge with defaults."""
    config_path = REPO_ROOT / "ai-review.config.json"
    out = dict(DEFAULT_CONFIG)
    if not config_path.exists():
        return out
    try:
        data = json.loads(config_path.read_text())
        if isinstance(data, dict):
            for k, v in data.items():
                if k in out and v is not None:
                    out[k] = v
    except (json.JSONDecodeError, OSError):
        pass
    return out


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


def build_system_prompt(style: str, arch: str, anti: str, config: dict) -> str:
    """Build the Senior Engineer persona and repository knowledge from config."""
    max_inline = int(config.get("max_inline_comments", 5))
    allow_good_inline = config.get("allow_good_to_have_inline", False)
    grades = config.get("summary_grades") or ["Consistency", "Quality", "Security"]
    max_req = int(config.get("max_required_in_summary", 3))
    max_good = int(config.get("max_good_to_have_in_summary", 3))
    req_desc = config.get("required_description", DEFAULT_CONFIG["required_description"])
    good_desc = config.get("good_to_have_description", DEFAULT_CONFIG["good_to_have_description"])
    grades_str = ", ".join(grades)
    custom = (config.get("custom_instructions") or "").strip()

    inline_rule = (
        f"Produce up to {max_inline} **inline comments** only for **required** findings"
        if not allow_good_inline
        else f"Produce up to {max_inline} **inline comments** for **required** findings; you may also include **good to have** as inline if they are high value"
    )
    good_rule = (
        "Do **not** post good-to-have as inline comments; list them only in the summary."
        if not allow_good_inline
        else "You may post a few good-to-have as inline if especially useful; otherwise list in the summary."
    )

    prompt = f"""You are a Senior Engineer performing a rigorous, professional code review.

## Mandatory review use cases

For every diff, you **must** consider and flag issues in these areas. Treat violations as **required** (must-fix) unless they are purely stylistic and non-critical.

1. **Security**
   - Hardcoded secrets, API keys, credentials, or production URLs (must use config/env).
   - SQL/command injection: user or external input concatenated into queries or shell commands (require parameterized queries / safe APIs).
   - Unvalidated or unsanitized user input used in paths, queries, or responses (path traversal, XSS, injection).

2. **Correctness and robustness**
   - Null/None dereference risks (e.g. calling methods on possibly null values without checks).
   - Logic errors, wrong conditions, or missing edge cases that could cause runtime or business logic failures.
   - Resource leaks: connections, file handles, or streams not closed in finally/try-with-resources.

3. **Error handling**
   - Empty or silent catch/except blocks (must log or re-raise).
   - Swallowing exceptions without any logging or reporting.

4. **Performance**
   - N+1 patterns: one query or request per loop item instead of batching (e.g. WHERE id IN (...)).
   - Blocking I/O or sleep in async code without justification.

5. **Consistency and maintainability**
   - Violations of the repository Style guide and Architecture checklist below (naming, structure, patterns).
   - Critical style or architecture violations that affect readability, safety, or future maintenance.

Only after checking these dimensions, classify each finding as **Required** (must fix) or **Good to have** (optional improvement), and produce inline comments only for required/critical items (max {max_inline}).

## Repository knowledge

### Style guide
{style}

### Architecture / quality checklist
{arch}

### Anti-patterns to flag
{anti}

## Your task
Review the provided git diff. Classify findings into:
- **Required changes**: {req_desc} These may be posted as inline comments.
- **Good to have**: {good_desc} {good_rule}

Be selective—do not pollute the PR with excessive suggestions. Reserve inline comments for required/critical findings only (max {max_inline}). Put good-to-have items only in the summary unless otherwise allowed.

1. {inline_rule}: file path (as in the diff), line number (in the new file), short actionable comment. Be specific and suggest a fix when possible.
2. Produce one **executive summary** that:
   - Grades the change on: {grades_str} (use: Good / Needs improvement / Critical).
   - Lists **Required changes** (must fix) and **Good to have** (optional), each as a short bullet list (top {max_req} required, top {max_good} good-to-have at most).

**Output format:** Reply with ONLY a single JSON object. No markdown code fences (no ```), no explanation before or after. The "summary" field MUST be a non-empty string with grades plus "Required changes" and "Good to have" sections.
{{
  "inline_comments": [
    {{ "path": "<file path>", "line": <number>, "body": "<comment>" }}
  ],
  "summary": "<non-empty markdown: grades; Required changes (bullets); Good to have (bullets)>"
}}
If there are no inline comments, use "inline_comments": [].
Use only paths that appear in the diff; use the line number in the new (right) side of the diff."""
    if custom:
        prompt += f"\n\n## Additional instructions (project-specific)\n{custom}"
    return prompt


def run_agent(diff: str, style: str, arch: str, anti: str, config: dict) -> str:
    """Run Agno agent with Gemini and return raw response."""
    try:
        from agno.agent import Agent
        from agno.models.google import Gemini
    except ImportError as e:
        sys.exit(f"Install agno[google]: pip install 'agno[google]' — {e}")

    if not os.environ.get("GOOGLE_API_KEY"):
        sys.exit("Set GOOGLE_API_KEY to run the review agent.")

    model_id = (config.get("model") or os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    agent = Agent(
        model=Gemini(id=model_id),
        instructions=build_system_prompt(style, arch, anti, config),
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


def _extract_json_object(text: str) -> str | None:
    """Extract the first top-level {...} with balanced braces. Handles nested braces and double-quoted strings (JSON)."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    i = start
    in_string = False
    escape = False
    while i < len(text):
        c = text[i]
        if escape:
            escape = False
            i += 1
            continue
        if in_string:
            if c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        elif c == '"':
            in_string = True
        i += 1
    return None


def _fix_common_json_issues(s: str) -> str:
    """Remove trailing commas before ] or } so strict JSON parser accepts LLM output."""
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return s


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

    json_str = None

    # 1) Code block: take content between ``` and ```, then extract JSON object
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if code_block:
        block = code_block.group(1).strip()
        json_str = _extract_json_object(block) or (block if block.startswith("{") else None)
    if json_str is None:
        # 2) Balanced-brace extraction (handles summary text containing } or extra text)
        json_str = _extract_json_object(raw)
    if json_str is None:
        # 3) Fallback: first { to last } (greedy)
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            json_str = match.group(0)

    if json_str:
        json_str = _fix_common_json_issues(json_str)
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
    summary: str,
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

    config = load_config()
    diff_max_lines = int(config.get("diff_max_lines") or 0)
    if diff_max_lines > 0:
        lines = diff.splitlines()
        if len(lines) > diff_max_lines:
            diff = "\n".join(lines[:diff_max_lines]) + "\n\n... (diff truncated by diff_max_lines)\n"
            print(f"Diff truncated to {diff_max_lines} lines (diff_max_lines).", file=sys.stderr)

    style, arch, anti = load_context()
    print("Running Agno agent (Gemini)...", file=sys.stderr)
    raw = run_agent(diff, style, arch, anti, config)
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

    max_inline = int(config.get("max_inline_comments", 5))
    if len(inline) > max_inline:
        inline = inline[:max_inline]
    post_inline = config.get("post_inline_comments", True)
    if not post_inline:
        inline = []
    post_to_github(inline, summary, repo, int(pr_number), head_sha, token)
    print("Done.")


if __name__ == "__main__":
    main()
