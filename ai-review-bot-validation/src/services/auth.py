"""
Placeholder auth helpers. Intentionally minimal for bot to review.
"""

# Anti-pattern: hardcoded placeholder (bot should suggest env/config)
DEFAULT_TIMEOUT = 30


def validate_token(token: str) -> bool:
    """Return True if token is non-empty. Do not use for real auth."""
    return bool(token and token.strip())
