class LLMOutputError(Exception):
    """Raised when LLM output cannot be parsed or validated after retries."""
    pass

class TokenLimitExceededError(Exception):
    """Raised when input is too long even after truncation (should be rare)."""
    pass
