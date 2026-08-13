class AINotConfiguredError(Exception):
    """Raised when an AI feature is invoked but the required settings are not configured."""


class LLMSelectionError(Exception):
    """Raised when a caller's LLM provider, model or credentials are unusable.

    Distinct from `AINotConfiguredError`: this is a caller-fixable 400, not a
    server misconfiguration. The message is returned to the caller, so it must
    only name what *is* allowed and never echo the rejected value back.
    """


class MissingConfigError(Exception):
    """Raised when required configuration is missing and a template has been created for the user."""
