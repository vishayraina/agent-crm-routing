from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class CanonicalError(BaseModel):
    """Normalized Canonical Error response model.

    Used by the Routing Layer and Client SDK to communicate failures in a
    vendor-agnostic format so agent reasoning loops can self-heal without
    parsing provider-specific error formats.
    """
    error_type: str = Field(..., description="Machine-readable canonical error classification")
    message: str = Field(..., description="Human-readable explanation of the error")
    target_crm: str | None = Field(default=None, description="Identifier of the downstream target CRM (e.g. crm_1, crm_2, crm_3)")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional contextual metadata about the failure")

    def to_exception(self) -> CanonicalException:
        """Convert this error model into a typed Python exception."""
        return CanonicalException.from_canonical_error(self)


class CanonicalException(Exception):
    """Base exception class for all canonical CRM routing failures."""

    def __init__(
        self,
        message: str,
        error_type: str = "CanonicalError",
        target_crm: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.target_crm = target_crm
        self.details = details or {}

    def to_canonical_error(self) -> CanonicalError:
        """Serialize this exception into a CanonicalError Pydantic model."""
        return CanonicalError(
            error_type=self.error_type,
            message=self.message,
            target_crm=self.target_crm,
            details=self.details,
        )

    @classmethod
    def from_canonical_error(cls, error: CanonicalError) -> CanonicalException:
        """Create a typed CanonicalException subclass instance from a CanonicalError model."""
        error_type_mapping: dict[str, type[CanonicalException]] = {
            "EntityNotFoundError": EntityNotFoundError,
            "SlotConflictError": SlotConflictError,
            "PaymentFailedError": PaymentFailedError,
            "ValidationError": ValidationError,
            "ProviderUnavailableError": ProviderUnavailableError,
        }
        exc_cls = error_type_mapping.get(error.error_type)
        if exc_cls is not None:
            return exc_cls(
                message=error.message,
                target_crm=error.target_crm,
                details=error.details,
            )
        return CanonicalException(
            message=error.message,
            error_type=error.error_type,
            target_crm=error.target_crm,
            details=error.details,
        )


class EntityNotFoundError(CanonicalException):
    """Raised when a requested resource (e.g. Contact, Order) does not exist in the target CRM."""

    def __init__(
        self,
        message: str,
        target_crm: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_type="EntityNotFoundError",
            target_crm=target_crm,
            details=details,
        )


class SlotConflictError(CanonicalException):
    """Raised when an appointment slot booking fails due to overlap or prior reservation."""

    def __init__(
        self,
        message: str,
        target_crm: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_type="SlotConflictError",
            target_crm=target_crm,
            details=details,
        )


class PaymentFailedError(CanonicalException):
    """Raised when a monetary transaction is declined or encounters a processing failure."""

    def __init__(
        self,
        message: str,
        target_crm: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_type="PaymentFailedError",
            target_crm=target_crm,
            details=details,
        )


class ValidationError(CanonicalException):
    """Raised when input parameters fail canonical schema validation or provider business constraints."""

    def __init__(
        self,
        message: str,
        target_crm: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_type="ValidationError",
            target_crm=target_crm,
            details=details,
        )


class ProviderUnavailableError(CanonicalException):
    """Raised when downstream target CRM service is unreachable, timed out, or unavailable."""

    def __init__(
        self,
        message: str,
        target_crm: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_type="ProviderUnavailableError",
            target_crm=target_crm,
            details=details,
        )
