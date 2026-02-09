#!/usr/bin/env python3
"""
Check that all PR review comment threads are resolved.
Exits 0 if no unresolved threads, 1 otherwise. Used as a CI gate so merge is blocked
until all review conversations (including AI-Review-Bot comments) are resolved.

Usage (CI): set GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER (or GITHUB_EVENT_PATH).
  python scripts/check_review_resolved.py
"""

import json
import os
import sys

try:
    import requests
except ImportError:
    sys.exit("Install requests: pip install requests")


def get_graphql_url() -> str:
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    if api_url.endswith("/api/v3"):
        return api_url.replace("/api/v3", "") + "/api/graphql"
    return api_url + "/graphql"


def get_pr_number() -> int | None:
    pr = os.environ.get("PR_NUMBER")
    if pr is not None:
        try:
            return int(pr)
        except ValueError:
            pass
    path = os.environ.get("GITHUB_EVENT_PATH")
    if path and os.path.isfile(path):
        try:
            data = json.loads(open(path).read())
            return int(data.get("pull_request", {}).get("number", 0)) or None
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def fetch_unresolved_count(token: str, repo: str, pr_number: int, graphql_url: str) -> int:
    owner, repo_name = repo.split("/", 1)
    query = """
    query($owner: String!, $name: String!, $number: Int!, $after: String) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $number) {
          reviewThreads(first: 100, after: $after) {
            nodes { isResolved }
            pageInfo { hasNextPage endCursor }
          }
        }
      }
    }
    """
    total = 0
    cursor = None
    while True:
        variables = {"owner": owner, "name": repo_name, "number": pr_number, "after": cursor}
        r = requests.post(
            graphql_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
            },
            json={"query": query, "variables": variables},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            raise RuntimeError(data["errors"])

        pr_data = (data.get("data") or {}).get("repository") or {}
        pr_node = pr_data.get("pullRequest")
        if not pr_node:
            break
        threads = (pr_node.get("reviewThreads") or {}).get("nodes") or []
        page_info = (pr_node.get("reviewThreads") or {}).get("pageInfo") or {}
        for node in threads:
            if node.get("isResolved") is False:
                total += 1
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
        if not cursor:
            break
    return total


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    pr_number = get_pr_number()
    if not token or not repo:
        print("Set GITHUB_TOKEN and GITHUB_REPOSITORY.", file=sys.stderr)
        return 2
    if not pr_number:
        print("Set PR_NUMBER or GITHUB_EVENT_PATH (pull_request event).", file=sys.stderr)
        return 2

    graphql_url = get_graphql_url()
    try:
        unresolved = fetch_unresolved_count(token, repo, pr_number, graphql_url)
    except Exception as e:
        print(f"Failed to check review threads: {e}", file=sys.stderr)
        return 2

    if unresolved > 0:
        print(
            f"Unresolved review conversations: {unresolved}. "
            "Resolve all PR review comment threads before merging.",
            file=sys.stderr,
        )
        return 1
    print("All review conversations are resolved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
