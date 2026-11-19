import pytest
from pydantic import ValidationError as PydanticValidationError

from src.domain.errors import (
    CanonicalError,
    CanonicalException,
    EntityNotFoundError,
    SlotConflictError,
    PaymentFailedError,
    ValidationError,
    ProviderUnavailableError,
)


def test_canonical_error_model():
    error_model = CanonicalError(
        error_type="EntityNotFoundError",
        message="Contact not found",
        target_crm="crm_1",
        details={"entity_id": "cnt_999", "entity_type": "contact"},
    )
    assert error_model.error_type == "EntityNotFoundError"
    assert error_model.message == "Contact not found"
    assert error_model.target_crm == "crm_1"
    assert error_model.details["entity_id"] == "cnt_999"

    dumped = error_model.model_dump()
    assert dumped["error_type"] == "EntityNotFoundError"
    assert dumped["message"] == "Contact not found"


def test_canonical_error_defaults():
    error_model = CanonicalError(
        error_type="GenericError",
        message="Something went wrong",
    )
    assert error_model.target_crm is None
    assert error_model.details == {}


def test_exception_hierarchy():
    # Verify inheritance
    exc = EntityNotFoundError(
        message="Contact cnt_1 not found",
        target_crm="crm_2",
        details={"entity_id": "cnt_1"},
    )
    assert isinstance(exc, CanonicalException)
    assert isinstance(exc, Exception)
    assert exc.error_type == "EntityNotFoundError"
    assert exc.message == "Contact cnt_1 not found"
    assert exc.target_crm == "crm_2"
    assert exc.details == {"entity_id": "cnt_1"}
    assert str(exc) == "Contact cnt_1 not found"


def test_typed_exceptions():
    slot_err = SlotConflictError(
        message="Slot already booked",
        target_crm="crm_3",
        details={"slot_id": "slot_123"},
    )
    assert slot_err.error_type == "SlotConflictError"
    assert slot_err.target_crm == "crm_3"

    pay_err = PaymentFailedError(
        message="Card declined: insufficient funds",
        target_crm="crm_1",
        details={"order_id": "ord_1", "decline_code": "card_declined"},
    )
    assert pay_err.error_type == "PaymentFailedError"

    val_err = ValidationError(
        message="Invalid email address format",
        target_crm="crm_2",
        details={"field": "email"},
    )
    assert val_err.error_type == "ValidationError"

    prov_err = ProviderUnavailableError(
        message="CRM 2 connection timed out",
        target_crm="crm_2",
        details={"status_code": 504},
    )
    assert prov_err.error_type == "ProviderUnavailableError"


def test_exception_to_canonical_error_conversion():
    exc = SlotConflictError("Time slot is no longer available", target_crm="crm_1", details={"slot_id": "s1"})
    canonical_err = exc.to_canonical_error()
    assert isinstance(canonical_err, CanonicalError)
    assert canonical_err.error_type == "SlotConflictError"
    assert canonical_err.message == "Time slot is no longer available"
    assert canonical_err.target_crm == "crm_1"
    assert canonical_err.details == {"slot_id": "s1"}


def test_canonical_error_to_exception_conversion():
    canonical_err = CanonicalError(
        error_type="PaymentFailedError",
        message="Fraud detection triggered",
        target_crm="crm_3",
        details={"risk_score": 95},
    )
    exc = canonical_err.to_exception()
    assert isinstance(exc, PaymentFailedError)
    assert isinstance(exc, CanonicalException)
    assert exc.message == "Fraud detection triggered"
    assert exc.target_crm == "crm_3"
    assert exc.details == {"risk_score": 95}

    # Unknown error type falls back to CanonicalException
    custom_err = CanonicalError(
        error_type="CustomUnknownError",
        message="Odd failure",
    )
    custom_exc = custom_err.to_exception()
    assert isinstance(custom_exc, CanonicalException)
    assert type(custom_exc) is CanonicalException
    assert custom_exc.error_type == "CustomUnknownError"


def test_catch_canonical_exception_in_try_except():
    def failing_call():
        raise EntityNotFoundError("Order ord_404 does not exist", target_crm="crm_1")

    with pytest.raises(CanonicalException) as exc_info:
        failing_call()

    assert exc_info.value.error_type == "EntityNotFoundError"
    assert exc_info.value.target_crm == "crm_1"
