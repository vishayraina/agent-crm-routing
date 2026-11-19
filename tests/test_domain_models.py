from datetime import datetime, timezone
import pytest
from pydantic import ValidationError as PydanticValidationError

from src.domain.models import (
    Contact,
    ContactCreate,
    Order,
    OrderItem,
    AppointmentSlot,
    Payment,
)


def test_contact_model_instantiation():
    now = datetime.now(timezone.utc)
    contact = Contact(
        id="cnt_123",
        first_name="Alice",
        last_name="Smith",
        email="alice@example.com",
        phone="+1234567890",
        company="Acme Corp",
        created_at=now,
    )
    assert contact.id == "cnt_123"
    assert contact.first_name == "Alice"
    assert contact.last_name == "Smith"
    assert contact.email == "alice@example.com"
    assert contact.phone == "+1234567890"
    assert contact.company == "Acme Corp"
    assert contact.created_at == now


def test_contact_model_defaults_and_validation():
    contact = Contact(
        id="cnt_123",
        first_name="Bob",
        last_name="Jones",
        email="bob@example.com",
    )
    assert contact.phone is None
    assert contact.company is None
    assert contact.created_at is None

    # Missing required field
    with pytest.raises(PydanticValidationError):
        Contact(first_name="Incomplete")


def test_contact_create_model():
    create_dto = ContactCreate(
        first_name="Charlie",
        last_name="Brown",
        email="charlie@example.com",
        company="Peanuts Inc",
    )
    assert create_dto.first_name == "Charlie"
    assert create_dto.last_name == "Brown"
    assert create_dto.email == "charlie@example.com"
    assert create_dto.company == "Peanuts Inc"
    assert create_dto.phone is None


def test_order_model_with_items():
    items = [
        OrderItem(item_id="item_1", name="Widget A", quantity=2, unit_price=25.0),
        OrderItem(item_id="item_2", name="Gadget B", quantity=1, unit_price=50.0),
    ]
    order = Order(
        id="ord_999",
        contact_id="cnt_123",
        items=items,
        total_amount=100.0,
        currency="USD",
        status="shipped",
        shipping_address="123 Main St, Springfield",
    )
    assert order.id == "ord_999"
    assert order.contact_id == "cnt_123"
    assert len(order.items) == 2
    assert order.items[0].name == "Widget A"
    assert order.total_amount == 100.0
    assert order.currency == "USD"
    assert order.status == "shipped"
    assert order.shipping_address == "123 Main St, Springfield"


def test_order_model_defaults():
    order = Order(
        id="ord_100",
        contact_id="cnt_123",
        total_amount=50.0,
    )
    assert order.items == []
    assert order.currency == "USD"
    assert order.status == "pending"
    assert order.shipping_address is None


def test_appointment_slot_model():
    start = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 12, 1, 11, 0, tzinfo=timezone.utc)
    slot = AppointmentSlot(
        id="slot_001",
        start_time=start,
        end_time=end,
        title="Product Demo",
        attendee_email="lead@example.com",
        status="available",
    )
    assert slot.id == "slot_001"
    assert slot.start_time == start
    assert slot.end_time == end
    assert slot.title == "Product Demo"
    assert slot.attendee_email == "lead@example.com"
    assert slot.status == "available"


def test_appointment_slot_defaults():
    start = datetime(2026, 12, 1, 14, 0, tzinfo=timezone.utc)
    end = datetime(2026, 12, 1, 15, 0, tzinfo=timezone.utc)
    slot = AppointmentSlot(
        id="slot_002",
        start_time=start,
        end_time=end,
    )
    assert slot.title == "Meeting"
    assert slot.attendee_email is None
    assert slot.status == "available"


def test_payment_model():
    now = datetime.now(timezone.utc)
    payment = Payment(
        id="pay_777",
        order_id="ord_999",
        amount=100.0,
        currency="USD",
        payment_method="credit_card",
        status="completed",
        transaction_timestamp=now,
    )
    assert payment.id == "pay_777"
    assert payment.order_id == "ord_999"
    assert payment.amount == 100.0
    assert payment.currency == "USD"
    assert payment.payment_method == "credit_card"
    assert payment.status == "completed"
    assert payment.transaction_timestamp == now


def test_payment_model_defaults():
    payment = Payment(
        id="pay_888",
        order_id="ord_100",
        amount=50.0,
    )
    assert payment.currency == "USD"
    assert payment.payment_method == "credit_card"
    assert payment.status == "completed"
    assert payment.transaction_timestamp is None


def test_order_model_with_item_dicts():
    order = Order(
        id="ord_dict",
        contact_id="cnt_123",
        items=[{"name": "Widget A", "quantity": 3, "unit_price": 10.0}],
        total_amount=30.0,
    )
    assert len(order.items) == 1
    assert isinstance(order.items[0], OrderItem)
    assert order.items[0].name == "Widget A"
    assert order.items[0].quantity == 3
    assert order.items[0].unit_price == 10.0


def test_contact_datetime_parsing():
    contact = Contact(
        id="cnt_str_date",
        first_name="Alice",
        last_name="Wonderland",
        email="alice@wonderland.com",
        created_at="2026-05-15T08:30:00Z",
    )
    assert isinstance(contact.created_at, datetime)
    assert contact.created_at.year == 2026
    assert contact.created_at.month == 5


def test_models_json_serialization():
    now = datetime(2026, 11, 19, 12, 0, 0, tzinfo=timezone.utc)
    contact = Contact(
        id="cnt_test",
        first_name="Jane",
        last_name="Doe",
        email="jane@doe.com",
        created_at=now,
    )
    data = contact.model_dump()
    assert data["id"] == "cnt_test"
    assert data["first_name"] == "Jane"
    json_str = contact.model_dump_json()
    roundtrip = Contact.model_validate_json(json_str)
    assert roundtrip.id == contact.id
    assert roundtrip.email == contact.email
