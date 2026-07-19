"""Custom exceptions for FLSUN library."""


class FlsunError(Exception):
    """Base exception for all FLSUN errors."""
    pass


class FlsunConnectionError(FlsunError):
    """Raised when connection to printer fails."""
    pass


class FlsunCommandError(FlsunError):
    """Raised when a command fails or returns an error."""
    pass


class FlsunTimeoutError(FlsunError):
    """Raised when a command times out."""
    pass
