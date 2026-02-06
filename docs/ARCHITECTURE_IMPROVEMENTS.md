# Architecture Improvements Checklist

The AI-Review-Bot validates its own suggestions against this checklist before posting. Feedback should be **actionable** and **accurate**.

## Consistency

- [ ] Naming matches project conventions (see STYLE_GUIDE).
- [ ] Formatting (indentation, quotes, line length) is consistent with the codebase.
- [ ] New code follows the same patterns as existing modules (e.g. error handling, logging).

## Quality

- [ ] Logic is clear and edge cases are considered.
- [ ] No unnecessary complexity; refactors improve readability.
- [ ] Dependencies are justified; no dead or redundant code.

## Security

- [ ] No sensitive data in logs, errors, or responses.
- [ ] Inputs are validated and output is safely encoded where relevant.
- [ ] No obvious injection or misuse of user-controlled data.

## Deliverable format

- Inline comments: one concern per comment; suggest a concrete fix where possible.
- Summary: grade each of Consistency, Quality, Security (e.g. Good / Needs improvement / Critical) and list top 3 actionable items.
