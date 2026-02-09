# Anti-Patterns to Flag

The AI-Review-Bot should treat the following as **required** (must-fix) or **good to have** depending on severity.

## Security (required)

- **Hardcoded secrets**: API keys, passwords, tokens, or connection strings in source. Must use config/env.
- **SQL/command injection**: Concatenating user or external input into SQL or shell commands. Use parameterized queries or safe APIs.
- **Path traversal**: Using user input directly in file paths without validation/normalization (e.g. `base + userInput`).
- **Unvalidated input**: User data used in responses, redirects, or file operations without sanitization/validation.

## Correctness (required)

- **Null dereference**: Calling methods on values that may be null/None without checks (e.g. `.trim()`, `.get()` on possibly null).
- **Resource leaks**: Connections, file handles, or streams not closed in `finally` or try-with-resources; or closed only on success path.
- **Logic errors**: Wrong conditions (e.g. `>=` vs `>`), off-by-one, or missing edge cases that cause wrong behavior.

## Error handling (required)

- **Empty catch/except**: Catching exceptions with no logging, re-throw, or handling. At minimum log and optionally re-raise.
- **Swallowing exceptions**: Returning default value or continuing without logging; hides failures.

## Performance (required when obvious)

- **N+1**: One query or HTTP call per loop item instead of batching (e.g. `WHERE id IN (...)` or bulk API).
- **Blocking in async**: `sleep()` or blocking I/O in async code without justification.
- **Inefficient SQL**: `SELECT *` when only specific columns are needed; queries with no `LIMIT` on large tables; use of functions on indexed columns (e.g. `UPPER(column)`, `LOWER(column)`) that prevent index use; fetching full rows for a single column.

## Tests (good to have / required for new behavior)

- **Missing tests**: New or non-trivial behavior (new methods, branches, or public APIs) with no corresponding unit or integration tests. Ask the author to add tests.

## Java-specific

- **NullPointerException**: Calling methods on possibly null references without checks (e.g. `.trim()`, `.toLowerCase()`, `.getLine1()` on nullable return values). Use null checks, `Optional`, or safe navigation.

## Ruby-specific

- **Resource not closed in loop**: Opening files, connections, or other resources inside a loop without closing them (e.g. `File.open` without a block, or without `ensure`/closed in all paths). Prefer block form: `File.open(path) { |f| ... }`.
- **Unclosed block / syntax**: Missing `end` for blocks or method definitions; unbalanced blocks that can cause syntax or load errors. Suggest verifying all blocks are properly closed.

- Violations of repository style guide (naming, types, structure).
- Broad `except Exception` without logging.
- Production URLs or credentials that should be configurable.
