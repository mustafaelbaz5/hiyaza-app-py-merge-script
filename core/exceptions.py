"""Custom exception hierarchy for core/ modules."""


class MergerError(Exception):
    """Base exception for all core merger errors."""


class ParseError(MergerError):
    """Raised when a source Excel file cannot be parsed."""


class DetectionError(MergerError):
    """Raised when association metadata cannot be detected."""


class CodeNotFoundError(MergerError):
    """Raised when a required reference code cannot be found."""
