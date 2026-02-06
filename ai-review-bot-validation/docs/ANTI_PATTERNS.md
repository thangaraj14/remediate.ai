# Common anti-patterns

Injected as knowledge for the AI-Review-Bot. Flag these in PRs when present.

1. **Hardcoded secrets or config**: URLs, API keys, timeouts in code instead of env/config.
2. **Bare except**: `except:` or `except Exception:` without logging or re-raise.
3. **Unvalidated input**: Using user or external input in queries or paths without validation.
4. **Blocking in async**: `time.sleep`, sync HTTP, or file I/O in async functions without justification.
5. **N+1 queries**: Loops that perform one query per item instead of batching.
6. **Silent failure**: Catching an error and continuing without logging or reporting.
