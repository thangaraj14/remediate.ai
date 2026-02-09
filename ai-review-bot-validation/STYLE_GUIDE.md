# Engineering Style Guide

This document is injected into the AI-Review-Bot as repository-specific context. The agent should evaluate PRs against these standards.

## General principles

- **Clarity over cleverness**: Prefer readable, explicit code.
- **Fail fast**: Validate inputs and raise clear errors early.
- **No silent failures**: Avoid empty `except` blocks; log or re-raise.

## Python

- Use type hints for public functions and module boundaries.
- Prefer `pathlib.Path` over string paths.
- Use `snake_case` for functions and variables; `PascalCase` for classes.
- Maximum line length: 100 characters (configurable per repo).
- Prefer list/dict comprehensions only when they improve readability.

## Security

- Never log or expose secrets, tokens, or PII.
- Use parameterized queries / safe APIs for any user-controlled data.
- Validate and sanitize inputs at boundaries.

## Performance

- Avoid N+1 patterns; batch or cache when appropriate.
- Prefer lazy evaluation for large data when it reduces memory.

## Testing

- New behavior should have corresponding tests.
- Prefer small, focused unit tests; use integration tests for workflows.

## Anti-patterns we flag

- Hardcoded credentials or URLs that should be configurable.
- Broad `except Exception` without logging.
- Blocking I/O in async code or hot paths without justification.
