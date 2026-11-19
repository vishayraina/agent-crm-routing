import copy
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

_INITIAL_CRM1_DATA: Dict[str, Any] = {
    "contacts": {
        "cont_101": {
            "id": "cont_101",
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice.smith@example.com",
            "phone": "+1-555-0101",
            "company": "Acme Corp",
            "created_at": "2026-11-01T09:00:00Z",
        }
    },
    "orders": {
        "ord_101": {
            "id": "ord_101",
            "contact_id": "cont_101",
            "items": [
                {
                    "item_id": "item_1",
                    "name": "Widget Pro",
                    "quantity": 2,
                    "price": 99.995,
                }
            ],
            "total_amount": 199.99,
            "currency": "USD",
            "status": "shipped",
            "shipping_address": "100 Innovation Way, Suite 400, San Francisco, CA",
            "created_at": "2026-11-05T14:30:00Z",
        }
    },
    "booked_slots": {"slot_conflict"},
    "slots": {},
    "payments": {},
}

_INITIAL_CRM2_DATA: Dict[str, Any] = {
    "contacts": {
        "cnt_201": {
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
    },
    "orders": {
        "ord_201": {
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
    },
    "booked_slots": {"slot_conflict"},
    "slots": {},
    "payments": {},
}

_INITIAL_CRM3_DATA: Dict[str, Any] = {
    "contacts": {
        "rec_301": {
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
            "updatedAt": "2026-11-03T11:20:00Z",
        }
    },
    "orders": {
        "rec_ord_301": {
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
                "items_json": '[{"item_id": "item_301", "name": "Industrial Sensor", "quantity": 1, "price": 320.50}]',
                "total_amount": "320.50",
                "currency": "USD",
                "order_status": "delivered",
                "shipping_address": "300 Industrial Parkway, Chicago, IL",
            },
            "createdAt": "2026-11-10T16:00:00Z",
            "updatedAt": "2026-11-12T10:15:00Z",
        }
    },
    "booked_slots": {"slot_conflict", "rec_slot_conflict"},
    "slots": {},
    "payments": {},
}

crm1_data: Dict[str, Any] = copy.deepcopy(_INITIAL_CRM1_DATA)
crm2_data: Dict[str, Any] = copy.deepcopy(_INITIAL_CRM2_DATA)
crm3_data: Dict[str, Any] = copy.deepcopy(_INITIAL_CRM3_DATA)


def reset_mock_data() -> None:
    global crm1_data, crm2_data, crm3_data
    crm1_data = copy.deepcopy(_INITIAL_CRM1_DATA)
    crm2_data = copy.deepcopy(_INITIAL_CRM2_DATA)
    crm3_data = copy.deepcopy(_INITIAL_CRM3_DATA)
