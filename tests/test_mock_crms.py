import pytest
from fastapi.testclient import TestClient
from src.mock_crms.app import mock_crms_app
from src.mock_crms.data import reset_mock_data


@pytest.fixture(autouse=True)
def reset_state():
    reset_mock_data()
    yield


@pytest.fixture
def client():
    return TestClient(mock_crms_app)


# ============================================================================
# CRM 1: Flat REST snake_case Endpoints
# ============================================================================


def test_crm1_get_contact_by_id(client):
    response = client.get("/crm1/contacts/cont_101")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "cont_101"
    assert data["first_name"] == "Alice"
    assert data["last_name"] == "Smith"
    assert data["email"] == "alice.smith@example.com"
    assert data["phone"] == "+1-555-0101"
    assert data["company"] == "Acme Corp"
    assert "created_at" in data


def test_crm1_get_contact_by_email(client):
    response = client.get("/crm1/contacts", params={"email": "alice.smith@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["email"] == "alice.smith@example.com"


def test_crm1_get_contact_not_found(client):
    response = client.get("/crm1/contacts/cont_nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "contact_not_found"
    assert "cont_nonexistent" in data["message"]


def test_crm1_create_contact(client):
    payload = {
        "first_name": "David",
        "last_name": "Miller",
        "email": "david.miller@example.com",
        "phone": "+1-555-0199",
        "company": "Miller Consulting"
    }
    response = client.post("/crm1/contacts", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"].startswith("cont_")
    assert data["first_name"] == "David"
    assert data["email"] == "david.miller@example.com"
    assert "created_at" in data

    # Verify retrieval
    get_res = client.get(f"/crm1/contacts/{data['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["email"] == "david.miller@example.com"


def test_crm1_get_order(client):
    response = client.get("/crm1/orders/ord_101")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "ord_101"
    assert data["contact_id"] == "cont_101"
    assert data["total_amount"] == 199.99
    assert data["currency"] == "USD"
    assert data["status"] == "shipped"
    assert isinstance(data["items"], list)
    assert len(data["items"]) > 0


def test_crm1_get_order_not_found(client):
    response = client.get("/crm1/orders/ord_nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "order_not_found"
    assert "ord_nonexistent" in data["message"]


def test_crm1_book_slot_success(client):
    payload = {
        "slot_id": "slot_101",
        "start_time": "2026-11-20T10:00:00Z",
        "end_time": "2026-11-20T10:30:00Z",
        "title": "Initial Consultation",
        "attendee_email": "alice.smith@example.com"
    }
    response = client.post("/crm1/slots/book", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "slot_101"
    assert data["status"] == "confirmed"
    assert data["attendee_email"] == "alice.smith@example.com"


def test_crm1_book_slot_conflict(client):
    payload = {
        "slot_id": "slot_conflict",
        "start_time": "2026-11-20T10:00:00Z",
        "end_time": "2026-11-20T10:30:00Z",
        "title": "Conflicting Meeting",
        "attendee_email": "other@example.com"
    }
    response = client.post("/crm1/slots/book", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["error"] == "slot_already_booked"
    assert "already reserved" in data["message"] or "conflict" in data["message"]


def test_crm1_charge_payment_success(client):
    payload = {
        "order_id": "ord_101",
        "amount": 199.99,
        "currency": "USD",
        "payment_method": "card_ending_4242"
    }
    response = client.post("/crm1/payments/charge", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == "ord_101"
    assert data["amount"] == 199.99
    assert data["currency"] == "USD"
    assert data["status"] == "succeeded"
    assert "transaction_timestamp" in data


def test_crm1_charge_payment_declined(client):
    payload = {
        "order_id": "ord_101",
        "amount": 199.99,
        "currency": "USD",
        "payment_method": "card_declined"
    }
    response = client.post("/crm1/payments/charge", json=payload)
    assert response.status_code == 402
    data = response.json()
    assert data["error"] == "card_declined"
    assert data["decline_code"] == "insufficient_funds"


# ============================================================================
# CRM 2: Nested camelCase RPC Endpoints
# ============================================================================


def test_crm2_get_contact_by_id(client):
    payload = {"contactId": "cnt_201"}
    response = client.post("/crm2/api/v2/getContact", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    contact_info = data["customerDetails"]["contactInfo"]
    assert contact_info["contactId"] == "cnt_201"
    assert contact_info["firstName"] == "Bob"
    assert contact_info["lastName"] == "Johnson"
    assert contact_info["emailAddress"] == "bob.johnson@example.com"
    assert contact_info["phoneNumber"] == "+1-555-0201"
    assert contact_info["organization"] == "Beta Industries"
    assert isinstance(data["customerDetails"]["systemMetadata"]["createdEpochMs"], int)


def test_crm2_get_contact_by_email(client):
    payload = {"email": "bob.johnson@example.com"}
    response = client.post("/crm2/api/v2/getContact", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["customerDetails"]["contactInfo"]["emailAddress"] == "bob.johnson@example.com"


def test_crm2_get_contact_not_found(client):
    payload = {"contactId": "cnt_nonexistent"}
    response = client.post("/crm2/api/v2/getContact", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "FAILED"
    assert data["responseCode"] == 404
    assert data["rpcError"]["code"] == "CONTACT_NOT_FOUND"


def test_crm2_create_contact(client):
    payload = {
        "contactInfo": {
            "firstName": "Elena",
            "lastName": "Rostova",
            "emailAddress": "elena.rostova@example.com",
            "phoneNumber": "+1-555-0299",
            "organization": "Global Logistics"
        }
    }
    response = client.post("/crm2/api/v2/createContact", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "SUCCESS"
    new_id = data["customerDetails"]["contactInfo"]["contactId"]
    assert new_id.startswith("cnt_")
    assert data["customerDetails"]["contactInfo"]["firstName"] == "Elena"
    assert isinstance(data["customerDetails"]["systemMetadata"]["createdEpochMs"], int)


def test_crm2_fetch_order(client):
    payload = {"orderId": "ord_201"}
    response = client.post("/crm2/api/v2/fetchOrder", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    order_details = data["orderDetails"]
    assert order_details["orderId"] == "ord_201"
    assert order_details["customerId"] == "cnt_201"
    assert order_details["orderTotal"] == 450.0
    assert order_details["currencyCode"] == "USD"
    assert order_details["fulfillmentStatus"] == "PROCESSING"
    assert isinstance(order_details["lineItems"], list)
    assert isinstance(order_details["orderedEpochMs"], int)


def test_crm2_fetch_order_not_found(client):
    payload = {"orderId": "ord_nonexistent"}
    response = client.post("/crm2/api/v2/fetchOrder", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "FAILED"
    assert data["responseCode"] == 404
    assert data["rpcError"]["code"] == "ORDER_NOT_FOUND"


def test_crm2_exec_booking_success(client):
    payload = {
        "bookingRequest": {
            "slotId": "slot_201",
            "startEpochMs": 1763632800000,
            "endEpochMs": 1763636400000,
            "meetingSubject": "Technical Demo",
            "participantEmail": "bob.johnson@example.com"
        }
    }
    response = client.post("/crm2/api/v2/execBooking", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    booking_result = data["bookingResult"]
    assert booking_result["bookingId"] == "slot_201"
    assert booking_result["bookingState"] == "CONFIRMED"
    assert booking_result["participantEmail"] == "bob.johnson@example.com"


def test_crm2_exec_booking_conflict(client):
    payload = {
        "bookingRequest": {
            "slotId": "slot_conflict",
            "startEpochMs": 1763632800000,
            "endEpochMs": 1763636400000,
            "meetingSubject": "Conflict Demo",
            "participantEmail": "other@example.com"
        }
    }
    response = client.post("/crm2/api/v2/execBooking", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["status"] == "FAILED"
    assert data["responseCode"] == 409
    assert data["rpcError"]["code"] == "SLOT_CONFLICT"


def test_crm2_process_charge_success(client):
    payload = {
        "chargeRequest": {
            "orderId": "ord_201",
            "chargeAmount": 450.0,
            "currencyCode": "USD",
            "paymentSource": "tok_visa_biz"
        }
    }
    response = client.post("/crm2/api/v2/processCharge", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    charge_result = data["chargeResult"]
    assert charge_result["orderId"] == "ord_201"
    assert charge_result["amountCaptured"] == 450.0
    assert charge_result["chargeState"] == "SETTLED"
    assert isinstance(charge_result["processedEpochMs"], int)


def test_crm2_process_charge_declined(client):
    payload = {
        "chargeRequest": {
            "orderId": "ord_201",
            "chargeAmount": 450.0,
            "currencyCode": "USD",
            "paymentSource": "tok_declined"
        }
    }
    response = client.post("/crm2/api/v2/processCharge", json=payload)
    assert response.status_code == 402
    data = response.json()
    assert data["status"] == "FAILED"
    assert data["responseCode"] == 402
    assert data["rpcError"]["code"] == "PAYMENT_DECLINED"


# ============================================================================
# CRM 3: Property-Bag Generic Record Endpoints
# ============================================================================


def test_crm3_get_contact_by_id(client):
    response = client.get("/crm3/objects/contacts/rec_301")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "rec_301"
    assert data["objectType"] == "contact"
    props = data["properties"]
    assert props["first_name"] == "Carol"
    assert props["last_name"] == "Williams"
    assert props["email"] == "carol.williams@example.com"
    assert props["phone"] == "+1-555-0301"
    assert props["company"] == "Gamma Dynamics"
    assert "createdAt" in data


def test_crm3_get_contact_by_email(client):
    response = client.get("/crm3/objects/contacts", params={"email": "carol.williams@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["properties"]["email"] == "carol.williams@example.com"


def test_crm3_get_contact_not_found(client):
    response = client.get("/crm3/objects/contacts/rec_nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["category"] == "OBJECT_NOT_FOUND"
    assert "rec_nonexistent" in data["message"]


def test_crm3_create_contact(client):
    payload = {
        "properties": {
            "first_name": "Franklin",
            "last_name": "Castle",
            "email": "franklin.castle@example.com",
            "phone": "+1-555-0399",
            "company": "Vigilance Inc"
        }
    }
    response = client.post("/crm3/objects/contacts", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"].startswith("rec_")
    assert data["objectType"] == "contact"
    assert data["properties"]["first_name"] == "Franklin"
    assert data["properties"]["email"] == "franklin.castle@example.com"
    assert "createdAt" in data


def test_crm3_get_order(client):
    response = client.get("/crm3/objects/orders/rec_ord_301")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "rec_ord_301"
    assert data["objectType"] == "order"
    props = data["properties"]
    assert props["contact_id"] == "rec_301"
    assert float(props["total_amount"]) == 320.50
    assert props["currency"] == "USD"
    assert props["order_status"] == "delivered"
    assert "items" in props or "items_json" in props


def test_crm3_get_order_not_found(client):
    response = client.get("/crm3/objects/orders/rec_ord_nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["category"] == "OBJECT_NOT_FOUND"
    assert "rec_ord_nonexistent" in data["message"]


def test_crm3_book_appointment_success(client):
    payload = {
        "properties": {
            "slot_id": "rec_slot_301",
            "start_time": "2026-11-22T14:00:00Z",
            "end_time": "2026-11-22T15:00:00Z",
            "appointment_title": "Quarterly Strategy Review",
            "attendee_email": "carol.williams@example.com"
        }
    }
    response = client.post("/crm3/objects/appointments", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "rec_slot_301"
    assert data["objectType"] == "appointment"
    assert data["properties"]["appointment_status"] == "scheduled"
    assert data["properties"]["attendee_email"] == "carol.williams@example.com"


def test_crm3_book_appointment_conflict(client):
    payload = {
        "properties": {
            "slot_id": "slot_conflict",
            "start_time": "2026-11-22T14:00:00Z",
            "end_time": "2026-11-22T15:00:00Z",
            "appointment_title": "Conflicting Session",
            "attendee_email": "other@example.com"
        }
    }
    response = client.post("/crm3/objects/appointments", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["status"] == "error"
    assert data["category"] == "APPOINTMENT_COLLISION"
    assert "details" in data


def test_crm3_process_transaction_success(client):
    payload = {
        "properties": {
            "order_id": "rec_ord_301",
            "amount": "320.50",
            "currency": "USD",
            "payment_method": "corporate_ach"
        }
    }
    response = client.post("/crm3/objects/transactions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"].startswith("rec_txn_")
    assert data["objectType"] == "transaction"
    assert data["properties"]["order_id"] == "rec_ord_301"
    assert data["properties"]["transaction_status"] == "completed"


def test_crm3_process_transaction_declined(client):
    payload = {
        "properties": {
            "order_id": "rec_ord_301",
            "amount": "320.50",
            "currency": "USD",
            "payment_method": "declined_ach"
        }
    }
    response = client.post("/crm3/objects/transactions", json=payload)
    assert response.status_code == 402
    data = response.json()
    assert data["status"] == "error"
    assert data["category"] == "PAYMENT_REJECTED"
    assert data["details"]["failureReason"] == "card_declined"
