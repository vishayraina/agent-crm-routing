from __future__ import annotations

from typing import Any

GET_CONTACT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_contact",
        "description": "Fetch contact details by ID from the target CRM.",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "string",
                    "description": "Unique identifier of the contact to fetch.",
                },
                "email": {
                    "type": "string",
                    "description": "Optional email address of the contact to fetch.",
                },
            },
        },
    },
}

CREATE_CONTACT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "create_contact",
        "description": "Create a new contact record in the target CRM.",
        "parameters": {
            "type": "object",
            "properties": {
                "first_name": {
                    "type": "string",
                    "description": "First name of the contact.",
                },
                "last_name": {
                    "type": "string",
                    "description": "Last name of the contact.",
                },
                "email": {
                    "type": "string",
                    "description": "Email address of the contact.",
                },
                "phone": {
                    "type": "string",
                    "description": "Optional phone number of the contact.",
                },
                "company": {
                    "type": "string",
                    "description": "Optional company or organization name.",
                },
            },
            "required": ["first_name", "last_name", "email"],
        },
    },
}

CHECK_ORDER_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "check_order",
        "description": "Check order fulfillment, shipment status, and item details by order ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Unique identifier of the order to inspect.",
                },
            },
            "required": ["order_id"],
        },
    },
}

GET_ORDERS_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_orders",
        "description": "Fetch all orders associated with a contact ID from the target CRM.",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "string",
                    "description": "Unique identifier of the contact whose orders to fetch.",
                },
            },
            "required": ["contact_id"],
        },
    },
}

BOOK_SLOT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "book_slot",
        "description": "Book a specific appointment slot on a CRM calendar.",
        "parameters": {
            "type": "object",
            "properties": {
                "slot_id": {
                    "type": "string",
                    "description": "Unique identifier of the appointment slot.",
                },
                "attendee_email": {
                    "type": "string",
                    "description": "Email address of the attendee reserving the slot.",
                },
                "title": {
                    "type": "string",
                    "description": "Optional title or topic of the meeting.",
                },
            },
            "required": ["slot_id", "attendee_email"],
        },
    },
}

TAKE_PAYMENT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "take_payment",
        "description": "Charge and record a monetary payment against an order in the target CRM.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Unique identifier of the order being paid.",
                },
                "amount": {
                    "type": "number",
                    "description": "Monetary amount to charge.",
                },
                "currency": {
                    "type": "string",
                    "description": "Currency code (e.g. USD, EUR). Default is USD.",
                    "default": "USD",
                },
                "payment_method": {
                    "type": "string",
                    "description": "Payment method identifier (e.g. credit_card, bank_transfer). Default is credit_card.",
                    "default": "credit_card",
                },
            },
            "required": ["order_id", "amount"],
        },
    },
}

ALL_TOOLS: dict[str, dict[str, Any]] = {
    "get_contact": GET_CONTACT_TOOL,
    "create_contact": CREATE_CONTACT_TOOL,
    "check_order": CHECK_ORDER_TOOL,
    "get_orders": GET_ORDERS_TOOL,
    "book_slot": BOOK_SLOT_TOOL,
    "take_payment": TAKE_PAYMENT_TOOL,
}
