import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from src.domain.models import AppointmentSlot, Contact, ContactCreate, Order, OrderItem, Payment
from src.domain.errors import (
    CanonicalError,
    CanonicalException,
    EntityNotFoundError,
    PaymentFailedError,
    ProviderUnavailableError,
    SlotConflictError,
    ValidationError,
)
from src.mock_crms.data import reset_mock_data
from src.routing.adapters.crm1 import CRM1Adapter
from src.routing.adapters.crm2 import CRM2Adapter
from src.routing.adapters.crm3 import CRM3Adapter
from src.routing.adapters.registry import get_adapter
from src.routing.app import create_routing_app, routing_app


@pytest.fixture(autouse=True)
def reset_state():
    reset_mock_data()
    yield


@pytest.fixture
def client():
    return TestClient(routing_app)


# ============================================================================
# Adapter Bidirectional Transformation Unit Tests
# ============================================================================


def test_crm1_adapter_transformations():
    adapter = CRM1Adapter()

    # Contact transform
    contact_create = ContactCreate(
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        phone="+1-555-0155",
        company="Acme Global",
    )
    provider_contact = adapter.to_provider_contact(contact_create)
    assert provider_contact["first_name"] == "Jane"
    assert provider_contact["last_name"] == "Doe"
    assert provider_contact["email"] == "jane.doe@example.com"
    assert provider_contact["phone"] == "+1-555-0155"
    assert provider_contact["company"] == "Acme Global"

    raw_contact_data = {
        "id": "cont_999",
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane.doe@example.com",
        "phone": "+1-555-0155",
        "company": "Acme Global",
        "created_at": "2026-11-01T12:00:00Z",
    }
    canonical_contact = adapter.from_provider_contact(raw_contact_data)
    assert canonical_contact.id == "cont_999"
    assert canonical_contact.first_name == "Jane"
    assert canonical_contact.email == "jane.doe@example.com"
    assert canonical_contact.created_at is not None

    # Order transform
    raw_order_data = {
        "id": "ord_999",
        "contact_id": "cont_999",
        "items": [
            {"item_id": "item_1", "name": "Item A", "quantity": 2, "price": 10.5}
        ],
        "total_amount": 21.0,
        "currency": "USD",
        "status": "shipped",
        "shipping_address": "123 Main St",
    }
    canonical_order = adapter.from_provider_order(raw_order_data)
    assert canonical_order.id == "ord_999"
    assert canonical_order.contact_id == "cont_999"
    assert canonical_order.total_amount == 21.0
    assert len(canonical_order.items) == 1
    assert canonical_order.items[0].unit_price == 10.5

    # Slot transform
    slot = AppointmentSlot(
        id="slot_999",
        start_time=datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 20, 11, 0, tzinfo=timezone.utc),
        title="Strategy Sync",
        attendee_email="jane.doe@example.com",
    )
    provider_slot = adapter.to_provider_slot(slot)
    assert provider_slot["slot_id"] == "slot_999"
    assert "2026-11-20T10:00:00" in provider_slot["start_time"]
    assert provider_slot["attendee_email"] == "jane.doe@example.com"

    # Payment transform
    payment = Payment(
        id="pay_999",
        order_id="ord_999",
        amount=21.0,
        currency="USD",
        payment_method="credit_card",
    )
    provider_payment = adapter.to_provider_payment(payment)
    assert provider_payment["order_id"] == "ord_999"
    assert provider_payment["amount"] == 21.0
    assert provider_payment["payment_method"] == "credit_card"


def test_crm1_adapter_error_normalization():
    adapter = CRM1Adapter()

    exc_404 = adapter.normalize_error(404, {"error": "contact_not_found", "message": "Contact 'cont_xyz' not found"})
    assert isinstance(exc_404, EntityNotFoundError)
    assert "cont_xyz" in exc_404.message
    assert exc_404.target_crm == "crm_1"

    exc_409 = adapter.normalize_error(409, {"error": "slot_already_booked", "message": "Slot is booked"})
    assert isinstance(exc_409, SlotConflictError)
    assert exc_409.target_crm == "crm_1"

    exc_402 = adapter.normalize_error(402, {"error": "card_declined", "message": "Declined"})
    assert isinstance(exc_402, PaymentFailedError)
    assert exc_402.target_crm == "crm_1"

    exc_422 = adapter.normalize_error(422, {"message": "Invalid input"})
    assert isinstance(exc_422, ValidationError)

    exc_500 = adapter.normalize_error(500, {"message": "Internal error"})
    assert isinstance(exc_500, ProviderUnavailableError)


def test_crm2_adapter_transformations():
    adapter = CRM2Adapter()

    # Contact transform
    contact_create = ContactCreate(
        first_name="Bob",
        last_name="Johnson",
        email="bob.johnson@example.com",
        phone="+1-555-0201",
        company="Beta Industries",
    )
    provider_contact = adapter.to_provider_contact(contact_create)
    info = provider_contact["contactInfo"]
    assert info["firstName"] == "Bob"
    assert info["lastName"] == "Johnson"
    assert info["emailAddress"] == "bob.johnson@example.com"
    assert info["phoneNumber"] == "+1-555-0201"
    assert info["organization"] == "Beta Industries"

    raw_contact_data = {
        "customerDetails": {
            "contactInfo": {
                "contactId": "cnt_201",
                "firstName": "Bob",
                "lastName": "Johnson",
                "emailAddress": "bob.johnson@example.com",
                "phoneNumber": "+1-555-0201",
                "organization": "Beta Industries",
            },
            "systemMetadata": {
                "createdEpochMs": 1763553600000,
            },
        }
    }
    canonical_contact = adapter.from_provider_contact(raw_contact_data)
    assert canonical_contact.id == "cnt_201"
    assert canonical_contact.first_name == "Bob"
    assert canonical_contact.company == "Beta Industries"
    assert canonical_contact.created_at is not None

    # Order transform
    raw_order_data = {
        "orderDetails": {
            "orderId": "ord_201",
            "customerId": "cnt_201",
            "lineItems": [
                {
                    "sku": "SKU-B200",
                    "productName": "Cloud Storage Subscription",
                    "quantity": 3,
                    "unitPrice": 150.0,
                }
            ],
            "orderTotal": 450.0,
            "currencyCode": "USD",
            "fulfillmentStatus": "PROCESSING",
            "deliveryAddress": "200 Enterprise Blvd, Austin, TX",
            "orderedEpochMs": 1763467200000,
        }
    }
    canonical_order = adapter.from_provider_order(raw_order_data)
    assert canonical_order.id == "ord_201"
    assert canonical_order.contact_id == "cnt_201"
    assert canonical_order.total_amount == 450.0
    assert canonical_order.status == "processing"
    assert len(canonical_order.items) == 1
    assert canonical_order.items[0].item_id == "SKU-B200"

    # Slot transform
    slot = AppointmentSlot(
        id="slot_201",
        start_time=datetime(2026, 11, 21, 14, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 21, 15, 0, tzinfo=timezone.utc),
        title="Technical Demo",
        attendee_email="bob.johnson@example.com",
    )
    provider_slot = adapter.to_provider_slot(slot)
    req = provider_slot["bookingRequest"]
    assert req["slotId"] == "slot_201"
    assert isinstance(req["startEpochMs"], int)
    assert req["meetingSubject"] == "Technical Demo"
    assert req["participantEmail"] == "bob.johnson@example.com"

    # Payment transform
    payment = Payment(
        id="txn_201",
        order_id="ord_201",
        amount=450.0,
        currency="USD",
        payment_method="tok_visa",
    )
    provider_payment = adapter.to_provider_payment(payment)
    charge_req = provider_payment["chargeRequest"]
    assert charge_req["orderId"] == "ord_201"
    assert charge_req["chargeAmount"] == 450.0
    assert charge_req["paymentSource"] == "tok_visa"


def test_crm2_adapter_error_normalization():
    adapter = CRM2Adapter()

    exc_404 = adapter.normalize_error(
        404,
        {
            "status": "FAILED",
            "responseCode": 404,
            "rpcError": {
                "code": "CONTACT_NOT_FOUND",
                "description": "Customer record was not found in CRM 2",
            },
        },
    )
    assert isinstance(exc_404, EntityNotFoundError)
    assert exc_404.target_crm == "crm_2"

    exc_409 = adapter.normalize_error(
        409,
        {
            "status": "FAILED",
            "responseCode": 409,
            "rpcError": {
                "code": "SLOT_CONFLICT",
                "description": "Schedule slot is already reserved",
            },
        },
    )
    assert isinstance(exc_409, SlotConflictError)
    assert exc_409.target_crm == "crm_2"

    exc_402 = adapter.normalize_error(
        402,
        {
            "status": "FAILED",
            "responseCode": 402,
            "rpcError": {
                "code": "PAYMENT_DECLINED",
                "description": "Transaction declined",
            },
        },
    )
    assert isinstance(exc_402, PaymentFailedError)
    assert exc_402.target_crm == "crm_2"


def test_crm3_adapter_transformations():
    adapter = CRM3Adapter()

    # Contact transform
    contact_create = ContactCreate(
        first_name="Carol",
        last_name="Williams",
        email="carol.williams@example.com",
        phone="+1-555-0301",
        company="Gamma Dynamics",
    )
    provider_contact = adapter.to_provider_contact(contact_create)
    props = provider_contact["properties"]
    assert props["first_name"] == "Carol"
    assert props["last_name"] == "Williams"
    assert props["email"] == "carol.williams@example.com"
    assert props["phone"] == "+1-555-0301"
    assert props["company"] == "Gamma Dynamics"

    raw_contact_data = {
        "id": "rec_301",
        "objectType": "contact",
        "properties": {
            "first_name": "Carol",
            "last_name": "Williams",
            "email": "carol.williams@example.com",
            "phone": "+1-555-0301",
            "company": "Gamma Dynamics",
            "created_date": "2026-11-03T11:20:00Z",
        },
        "createdAt": "2026-11-03T11:20:00Z",
    }
    canonical_contact = adapter.from_provider_contact(raw_contact_data)
    assert canonical_contact.id == "rec_301"
    assert canonical_contact.first_name == "Carol"
    assert canonical_contact.company == "Gamma Dynamics"
    assert canonical_contact.created_at is not None

    # Order transform
    raw_order_data = {
        "id": "rec_ord_301",
        "objectType": "order",
        "properties": {
            "contact_id": "rec_301",
            "items": [
                {
                    "item_id": "item_301",
                    "name": "Industrial Sensor",
                    "quantity": 1,
                    "price": 320.50,
                }
            ],
            "total_amount": "320.50",
            "currency": "USD",
            "order_status": "delivered",
            "shipping_address": "300 Industrial Parkway, Chicago, IL",
        },
    }
    canonical_order = adapter.from_provider_order(raw_order_data)
    assert canonical_order.id == "rec_ord_301"
    assert canonical_order.contact_id == "rec_301"
    assert canonical_order.total_amount == 320.50
    assert canonical_order.status == "delivered"
    assert len(canonical_order.items) == 1

    # Slot transform
    slot = AppointmentSlot(
        id="rec_slot_301",
        start_time=datetime(2026, 11, 22, 14, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 22, 15, 0, tzinfo=timezone.utc),
        title="Quarterly Review",
        attendee_email="carol.williams@example.com",
    )
    provider_slot = adapter.to_provider_slot(slot)
    slot_props = provider_slot["properties"]
    assert slot_props["slot_id"] == "rec_slot_301"
    assert slot_props["appointment_title"] == "Quarterly Review"
    assert slot_props["attendee_email"] == "carol.williams@example.com"

    # Payment transform
    payment = Payment(
        id="rec_txn_301",
        order_id="rec_ord_301",
        amount=320.50,
        currency="USD",
        payment_method="corporate_ach",
    )
    provider_payment = adapter.to_provider_payment(payment)
    txn_props = provider_payment["properties"]
    assert txn_props["order_id"] == "rec_ord_301"
    assert txn_props["amount"] == "320.5" or txn_props["amount"] == 320.5 or float(txn_props["amount"]) == 320.50
    assert txn_props["payment_method"] == "corporate_ach"


def test_crm3_adapter_error_normalization():
    adapter = CRM3Adapter()

    exc_404 = adapter.normalize_error(
        404,
        {
            "status": "error",
            "category": "OBJECT_NOT_FOUND",
            "message": "Object not found",
        },
    )
    assert isinstance(exc_404, EntityNotFoundError)
    assert exc_404.target_crm == "crm_3"

    exc_409 = adapter.normalize_error(
        409,
        {
            "status": "error",
            "category": "APPOINTMENT_COLLISION",
            "message": "Collision detected",
        },
    )
    assert isinstance(exc_409, SlotConflictError)
    assert exc_409.target_crm == "crm_3"

    exc_402 = adapter.normalize_error(
        402,
        {
            "status": "error",
            "category": "PAYMENT_REJECTED",
            "message": "Transaction declined",
        },
    )
    assert isinstance(exc_402, PaymentFailedError)
    assert exc_402.target_crm == "crm_3"


# ============================================================================
# Adapter Direct Execution Tests (with Mock CRM Downstream)
# ============================================================================


@pytest.mark.asyncio
async def test_crm1_adapter_operations():
    adapter = get_adapter("crm_1")

    # get_contact by id
    contact = await adapter.get_contact(contact_id="cont_101")
    assert contact.id == "cont_101"
    assert contact.first_name == "Alice"

    # get_contact by email
    contact_email = await adapter.get_contact(email="alice.smith@example.com")
    assert contact_email.id == "cont_101"

    # get_contact not found
    with pytest.raises(EntityNotFoundError) as exc_info:
        await adapter.get_contact(contact_id="cont_missing")
    assert exc_info.value.target_crm == "crm_1"

    # create_contact
    created = await adapter.create_contact(
        ContactCreate(
            first_name="New",
            last_name="User",
            email="new.user@crm1.com",
        )
    )
    assert created.id.startswith("cont_")
    assert created.email == "new.user@crm1.com"

    # get_order
    order = await adapter.get_order("ord_101")
    assert order.id == "ord_101"
    assert order.total_amount == 199.99

    # get_order not found
    with pytest.raises(EntityNotFoundError):
        await adapter.get_order("ord_missing")

    # book_slot
    slot = await adapter.book_slot(
        AppointmentSlot(
            id="slot_new_crm1",
            start_time=datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 11, 20, 10, 30, tzinfo=timezone.utc),
            title="Interview",
            attendee_email="new.user@crm1.com",
        )
    )
    assert slot.id == "slot_new_crm1"

    # book_slot conflict
    with pytest.raises(SlotConflictError):
        await adapter.book_slot(
            AppointmentSlot(
                id="slot_conflict",
                start_time=datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 11, 20, 10, 30, tzinfo=timezone.utc),
                title="Conflict",
                attendee_email="other@crm1.com",
            )
        )

    # charge_payment success
    payment = await adapter.charge_payment(
        Payment(
            id="temp_id",
            order_id="ord_101",
            amount=199.99,
            currency="USD",
            payment_method="card_visa",
        )
    )
    assert payment.id.startswith("pay_")
    assert payment.status in ("completed", "succeeded")

    # charge_payment decline
    with pytest.raises(PaymentFailedError):
        await adapter.charge_payment(
            Payment(
                id="temp_id",
                order_id="ord_declined",
                amount=100.0,
                currency="USD",
                payment_method="declined_card",
            )
        )


@pytest.mark.asyncio
async def test_crm2_adapter_operations():
    adapter = get_adapter("crm_2")

    # get_contact by id
    contact = await adapter.get_contact(contact_id="cnt_201")
    assert contact.id == "cnt_201"
    assert contact.first_name == "Bob"

    # get_contact by email
    contact_email = await adapter.get_contact(email="bob.johnson@example.com")
    assert contact_email.id == "cnt_201"

    # get_contact not found
    with pytest.raises(EntityNotFoundError) as exc_info:
        await adapter.get_contact(contact_id="cnt_missing")
    assert exc_info.value.target_crm == "crm_2"

    # create_contact
    created = await adapter.create_contact(
        ContactCreate(
            first_name="New",
            last_name="User",
            email="new.user@crm2.com",
        )
    )
    assert created.id.startswith("cnt_")
    assert created.email == "new.user@crm2.com"

    # get_order
    order = await adapter.get_order("ord_201")
    assert order.id == "ord_201"
    assert order.total_amount == 450.0

    # get_order not found
    with pytest.raises(EntityNotFoundError):
        await adapter.get_order("ord_missing")

    # book_slot
    slot = await adapter.book_slot(
        AppointmentSlot(
            id="slot_new_crm2",
            start_time=datetime(2026, 11, 21, 14, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 11, 21, 15, 0, tzinfo=timezone.utc),
            title="Demo",
            attendee_email="new.user@crm2.com",
        )
    )
    assert slot.id == "slot_new_crm2"

    # book_slot conflict
    with pytest.raises(SlotConflictError):
        await adapter.book_slot(
            AppointmentSlot(
                id="slot_conflict",
                start_time=datetime(2026, 11, 21, 14, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 11, 21, 15, 0, tzinfo=timezone.utc),
                title="Conflict Demo",
                attendee_email="other@crm2.com",
            )
        )

    # charge_payment success
    payment = await adapter.charge_payment(
        Payment(
            id="temp_id",
            order_id="ord_201",
            amount=450.0,
            currency="USD",
            payment_method="tok_mastercard",
        )
    )
    assert payment.id.startswith("txn_")
    assert payment.status in ("completed", "settled")

    # charge_payment decline
    with pytest.raises(PaymentFailedError):
        await adapter.charge_payment(
            Payment(
                id="temp_id",
                order_id="ord_declined",
                amount=100.0,
                currency="USD",
                payment_method="tok_declined",
            )
        )


@pytest.mark.asyncio
async def test_crm3_adapter_operations():
    adapter = get_adapter("crm_3")

    # get_contact by id
    contact = await adapter.get_contact(contact_id="rec_301")
    assert contact.id == "rec_301"
    assert contact.first_name == "Carol"

    # get_contact by email
    contact_email = await adapter.get_contact(email="carol.williams@example.com")
    assert contact_email.id == "rec_301"

    # get_contact not found
    with pytest.raises(EntityNotFoundError) as exc_info:
        await adapter.get_contact(contact_id="rec_missing")
    assert exc_info.value.target_crm == "crm_3"

    # create_contact
    created = await adapter.create_contact(
        ContactCreate(
            first_name="New",
            last_name="User",
            email="new.user@crm3.com",
        )
    )
    assert created.id.startswith("rec_")
    assert created.email == "new.user@crm3.com"

    # get_order
    order = await adapter.get_order("rec_ord_301")
    assert order.id == "rec_ord_301"
    assert order.total_amount == 320.50

    # get_order not found
    with pytest.raises(EntityNotFoundError):
        await adapter.get_order("rec_ord_missing")

    # book_slot
    slot = await adapter.book_slot(
        AppointmentSlot(
            id="rec_slot_new_crm3",
            start_time=datetime(2026, 11, 22, 14, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 11, 22, 15, 0, tzinfo=timezone.utc),
            title="Review",
            attendee_email="new.user@crm3.com",
        )
    )
    assert slot.id == "rec_slot_new_crm3"

    # book_slot conflict
    with pytest.raises(SlotConflictError):
        await adapter.book_slot(
            AppointmentSlot(
                id="slot_conflict",
                start_time=datetime(2026, 11, 22, 14, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 11, 22, 15, 0, tzinfo=timezone.utc),
                title="Conflict Session",
                attendee_email="other@crm3.com",
            )
        )

    # charge_payment success
    payment = await adapter.charge_payment(
        Payment(
            id="temp_id",
            order_id="rec_ord_301",
            amount=320.50,
            currency="USD",
            payment_method="ach_transfer",
        )
    )
    assert payment.id.startswith("rec_txn_")
    assert payment.status == "completed"

    # charge_payment decline
    with pytest.raises(PaymentFailedError):
        await adapter.charge_payment(
            Payment(
                id="temp_id",
                order_id="rec_ord_declined",
                amount=100.0,
                currency="USD",
                payment_method="declined_ach",
            )
        )


# ============================================================================
# Routing Layer FastAPI Service Tests (Canonical Endpoints & Targets)
# ============================================================================


@pytest.mark.parametrize("target_crm,contact_id,expected_name", [
    ("crm_1", "cont_101", "Alice"),
    ("crm_2", "cnt_201", "Bob"),
    ("crm_3", "rec_301", "Carol"),
])
def test_routing_get_contact_by_id_via_header(client, target_crm, contact_id, expected_name):
    headers = {"X-CRM-Target": target_crm}
    response = client.get(f"/api/v1/contacts?contact_id={contact_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == contact_id
    assert data["first_name"] == expected_name


@pytest.mark.parametrize("target_crm,email,expected_name", [
    ("crm_1", "alice.smith@example.com", "Alice"),
    ("crm_2", "bob.johnson@example.com", "Bob"),
    ("crm_3", "carol.williams@example.com", "Carol"),
])
def test_routing_get_contact_by_email_via_query_param(client, target_crm, email, expected_name):
    response = client.get(f"/api/v1/contacts?email={email}&crm_target={target_crm}")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["first_name"] == expected_name


def test_routing_get_contact_missing_criteria(client):
    response = client.get("/api/v1/contacts", headers={"X-CRM-Target": "crm_1"})
    assert response.status_code == 422
    data = response.json()
    assert data["error_type"] == "ValidationError"


def test_routing_get_contact_not_found_normalized_error(client):
    response = client.get("/api/v1/contacts?contact_id=nonexistent", headers={"X-CRM-Target": "crm_1"})
    assert response.status_code == 404
    data = response.json()
    assert data["error_type"] == "EntityNotFoundError"
    assert data["target_crm"] == "crm_1"
    assert "nonexistent" in data["message"]


@pytest.mark.parametrize("target_crm", ["crm_1", "crm_2", "crm_3"])
def test_routing_create_contact(client, target_crm):
    payload = {
        "first_name": "Test",
        "last_name": "Target",
        "email": f"test.target@{target_crm}.com",
        "phone": "+1-555-9999",
        "company": "Target Test Co",
    }
    response = client.post("/api/v1/contacts", json=payload, headers={"X-CRM-Target": target_crm})
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Test"
    assert data["email"] == f"test.target@{target_crm}.com"
    assert "id" in data


@pytest.mark.parametrize("target_crm,order_id,expected_total", [
    ("crm_1", "ord_101", 199.99),
    ("crm_2", "ord_201", 450.0),
    ("crm_3", "rec_ord_301", 320.50),
])
def test_routing_get_order_across_crms(client, target_crm, order_id, expected_total):
    response = client.get(f"/api/v1/orders/{order_id}", headers={"X-CRM-Target": target_crm})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == order_id
    assert data["total_amount"] == expected_total
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1


@pytest.mark.parametrize("target_crm,missing_order_id", [
    ("crm_1", "ord_missing_1"),
    ("crm_2", "ord_missing_2"),
    ("crm_3", "ord_missing_3"),
])
def test_routing_get_order_not_found(client, target_crm, missing_order_id):
    response = client.get(f"/api/v1/orders/{missing_order_id}", headers={"X-CRM-Target": target_crm})
    assert response.status_code == 404
    data = response.json()
    assert data["error_type"] == "EntityNotFoundError"
    assert data["target_crm"] == target_crm


@pytest.mark.parametrize("target_crm,slot_id", [
    ("crm_1", "slot_fastapi_1"),
    ("crm_2", "slot_fastapi_2"),
    ("crm_3", "slot_fastapi_3"),
])
def test_routing_book_slot_success(client, target_crm, slot_id):
    payload = {
        "id": slot_id,
        "start_time": "2026-11-20T10:00:00Z",
        "end_time": "2026-11-20T11:00:00Z",
        "title": "Onboarding Call",
        "attendee_email": "client@example.com",
    }
    response = client.post("/api/v1/slots/book", json=payload, headers={"X-CRM-Target": target_crm})
    assert response.status_code in (200, 201)
    data = response.json()
    assert data["id"] == slot_id
    assert data["attendee_email"] == "client@example.com"


@pytest.mark.parametrize("target_crm", ["crm_1", "crm_2", "crm_3"])
def test_routing_book_slot_conflict_error(client, target_crm):
    payload = {
        "id": "slot_conflict",
        "start_time": "2026-11-20T10:00:00Z",
        "end_time": "2026-11-20T11:00:00Z",
        "title": "Conflict Booking",
        "attendee_email": "client@example.com",
    }
    response = client.post("/api/v1/slots/book", json=payload, headers={"X-CRM-Target": target_crm})
    assert response.status_code == 409
    data = response.json()
    assert data["error_type"] == "SlotConflictError"
    assert data["target_crm"] == target_crm


@pytest.mark.parametrize("target_crm,order_id,amount,source", [
    ("crm_1", "ord_101", 199.99, "card_visa"),
    ("crm_2", "ord_201", 450.0, "tok_mastercard"),
    ("crm_3", "rec_ord_301", 320.50, "corporate_ach"),
])
def test_routing_charge_payment_success(client, target_crm, order_id, amount, source):
    payload = {
        "id": "pending_charge",
        "order_id": order_id,
        "amount": amount,
        "currency": "USD",
        "payment_method": source,
    }
    response = client.post("/api/v1/payments/charge", json=payload, headers={"X-CRM-Target": target_crm})
    assert response.status_code in (200, 201)
    data = response.json()
    assert data["order_id"] == order_id
    assert data["amount"] == amount
    assert data["id"] != "pending_charge"


@pytest.mark.parametrize("target_crm,order_id,declined_source", [
    ("crm_1", "ord_declined", "card_declined"),
    ("crm_2", "ord_declined", "tok_declined"),
    ("crm_3", "rec_ord_declined", "declined_ach"),
])
def test_routing_charge_payment_declined_error(client, target_crm, order_id, declined_source):
    payload = {
        "id": "pending_charge",
        "order_id": order_id,
        "amount": 100.0,
        "currency": "USD",
        "payment_method": declined_source,
    }
    response = client.post("/api/v1/payments/charge", json=payload, headers={"X-CRM-Target": target_crm})
    assert response.status_code == 402
    data = response.json()
    assert data["error_type"] == "PaymentFailedError"
    assert data["target_crm"] == target_crm


def test_routing_missing_target_crm(client):
    response = client.get("/api/v1/contacts?contact_id=cont_101")
    assert response.status_code == 422
    data = response.json()
    assert data["error_type"] == "ValidationError"
    assert "target crm must be specified" in data["message"].lower()


def test_routing_invalid_target_crm(client):
    response = client.get("/api/v1/contacts?contact_id=cont_101", headers={"X-CRM-Target": "crm_unknown"})
    assert response.status_code == 422
    data = response.json()
    assert data["error_type"] == "ValidationError"
    assert "unknown target crm" in data["message"].lower()


def test_routing_fastapi_request_validation_error(client):
    # Missing required field first_name in ContactCreate
    bad_payload = {"email": "missing.names@example.com"}
    response = client.post("/api/v1/contacts", json=bad_payload, headers={"X-CRM-Target": "crm_1"})
    assert response.status_code == 422
    data = response.json()
    assert data["error_type"] == "ValidationError"
    assert "validation" in data["message"].lower()
    assert "validation_errors" in data["details"]


def test_create_routing_app_injection():
    from src.mock_crms.app import mock_crms_app
    import httpx

    # Test with custom mock_app
    app_with_mock = create_routing_app(mock_app=mock_crms_app)
    c1 = TestClient(app_with_mock)
    r1 = c1.get("/api/v1/contacts?contact_id=cont_101", headers={"X-CRM-Target": "crm_1"})
    assert r1.status_code == 200

    # Test with custom base_url
    app_with_url = create_routing_app(base_url="http://custom-host:9999")
    assert app_with_url.state.downstream_client.base_url == httpx.URL("http://custom-host:9999")

    # Test with custom injected client
    custom_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=mock_crms_app),
        base_url="http://custom-test",
    )
    app_with_client = create_routing_app(downstream_client=custom_client)
    c2 = TestClient(app_with_client)
    r2 = c2.get("/api/v1/contacts?contact_id=cont_101", headers={"X-CRM-Target": "crm_1"})
    assert r2.status_code == 200


@pytest.mark.parametrize("target_crm,contact_id,expected_order_id,expected_total", [
    ("crm_1", "cont_101", "ord_101", 199.99),
    ("crm_2", "cnt_201", "ord_201", 450.00),
    ("crm_3", "rec_301", "rec_ord_301", 320.50),
])
def test_routing_get_orders_across_crms(client, target_crm, contact_id, expected_order_id, expected_total):
    response = client.get(
        f"/api/v1/orders?contact_id={contact_id}",
        headers={"X-CRM-Target": target_crm},
    )
    assert response.status_code == 200
    orders = response.json()
    assert isinstance(orders, list)
    assert len(orders) >= 1
    assert orders[0]["id"] == expected_order_id
    assert orders[0]["contact_id"] == contact_id
    assert orders[0]["total_amount"] == expected_total


def test_routing_get_orders_by_target_crm_query_param(client):
    response = client.get(
        "/api/v1/orders?contact_id=cont_101&target_crm=crm_1",
    )
    assert response.status_code == 200
    orders = response.json()
    assert isinstance(orders, list)
    assert orders[0]["id"] == "ord_101"


def test_vendor_credentials_managed_in_routing_layer():
    from src.routing.credentials import RoutingCredentialStore
    store = RoutingCredentialStore()
    assert store.get_credential("crm_1") == "key-crm1-secret"
    assert store.get_credential("crm_2") == "key-crm2-secret"
    assert store.get_credential("crm_3") == "key-crm3-secret"

    headers = store.get_auth_headers("crm_1")
    assert headers["Authorization"] == "Bearer key-crm1-secret"
    assert headers["X-Vendor-API-Key"] == "key-crm1-secret"

    # Verify adapter carries credential store
    adapter = CRM1Adapter()
    assert adapter.credential_store is not None
    auth = adapter.credential_store.get_auth_headers("crm_1")
    assert "Bearer key-crm1-secret" in auth["Authorization"]

