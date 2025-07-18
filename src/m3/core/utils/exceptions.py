from beartype import beartype


@beartype
class M3Error(Exception):
    ISSUE_REPORT_URL: str = (
        "https://github.com/rafiattrach/m3/issues/new?template=bug_report.yaml"
    )

    def __init__(self, message: str, details: str | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        base_msg = f"M3 Library Error: {self.message}"
        if self.details:
            base_msg += f"\nHere are some more details: {self.details}"
        base_msg += f"\nIf you think this is a bug, please report it at: {self.ISSUE_REPORT_URL}"
        return base_msg


@beartype
class M3ValidationError(M3Error):
    """General validation error for M3 configurations and setups."""


@beartype
class M3InitializationError(M3Error):
    """Raised when initialization fails (e.g., backend setup)."""


@beartype
class M3ConfigError(M3Error):
    """Raised for configuration-specific issues."""


@beartype
class M3PresetError(M3Error):
    """Raised when preset loading or application fails."""


@beartype
class M3BuildError(M3Error):
    """Raised during build process failures."""


@beartype
class AuthenticationError(M3Error):
    """Raised when authentication fails."""


@beartype
class TokenValidationError(M3Error):
    """Raised when token validation fails."""
