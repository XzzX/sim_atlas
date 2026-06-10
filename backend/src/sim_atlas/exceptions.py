class AINotConfiguredError(Exception):
    """Raised when an AI feature is invoked but the required settings are not configured."""


class MissingConfigError(Exception):
    """Raised when required configuration is missing and a template has been created for the user."""
