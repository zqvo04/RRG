class PipelineError(Exception):
    """Base exception for expected pipeline failures."""


class DataValidationError(PipelineError):
    """Raised when price bars do not meet the snapshot quality gate."""


class ProviderError(PipelineError):
    """Raised when a provider cannot return a valid time series."""

