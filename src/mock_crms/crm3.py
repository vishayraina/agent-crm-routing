import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.mock_crms import data

router = APIRouter(prefix="/crm3/objects", tags=["CRM 3 - Property Bag"])


class CRM3GenericRecordInput(BaseModel):
    properties: Dict[str, Any]


@router.get("/contacts")
def list_or_search_contacts(email: Optional[str] = Query(default=None)):
    contacts = list(data.crm3_data["contacts"].values())
    if email:
        matched = [
            c for c in contacts if c.get("properties", {}).get("email") == email
        ]
        return matched
    return contacts


@router.get("/contacts/{contact_id}")
def get_contact(contact_id: str):
    contact = data.crm3_data["contacts"].get(contact_id)
    if not contact:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": "error",
                "category": "OBJECT_NOT_FOUND",
                "message": f"Object {contact_id} of type contact does not exist",
                "details": {
                    "objectId": contact_id,
                    "objectType": "contact",
                },
            },
        )
    return contact


@router.post("/contacts", status_code=status.HTTP_201_CREATED)
def create_contact(payload: CRM3GenericRecordInput):
    contact_id = f"rec_{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    props = dict(payload.properties)
    props.setdefault("created_date", now_iso)
    record = {
        "id": contact_id,
        "objectType": "contact",
        "properties": props,
        "createdAt": now_iso,
        "updatedAt": now_iso,
    }
    data.crm3_data["contacts"][contact_id] = record
    return record


@router.get("/orders")
def list_or_search_orders(contact_id: Optional[str] = Query(default=None)):
    orders = list(data.crm3_data["orders"].values())
    if contact_id:
        orders = [
            o for o in orders
            if o.get("properties", {}).get("contact_id") == contact_id
        ]
    return orders


@router.get("/orders/{order_id}")
def get_order(order_id: str):
    order = data.crm3_data["orders"].get(order_id)
    if not order:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": "error",
                "category": "OBJECT_NOT_FOUND",
                "message": f"Object {order_id} of type order does not exist",
                "details": {
                    "objectId": order_id,
                    "objectType": "order",
                },
            },
        )
    return order


@router.post("/appointments", status_code=status.HTTP_201_CREATED)
def book_appointment(payload: CRM3GenericRecordInput):
    props = payload.properties
    slot_id = str(props.get("slot_id", f"slot_{uuid.uuid4().hex[:8]}"))

    if (
        slot_id in data.crm3_data["booked_slots"]
        or "conflict" in slot_id.lower()
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "status": "error",
                "category": "APPOINTMENT_COLLISION",
                "message": f"Appointment slot {slot_id} is in conflict with an existing appointment",
                "details": {
                    "conflictingSlotId": slot_id,
                },
            },
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    record_props = dict(props)
    record_props.setdefault("appointment_status", "scheduled")
    record = {
        "id": slot_id,
        "objectType": "appointment",
        "properties": record_props,
        "createdAt": now_iso,
    }
    data.crm3_data["booked_slots"].add(slot_id)
    data.crm3_data["slots"][slot_id] = record
    return record


@router.post("/transactions", status_code=status.HTTP_201_CREATED)
def process_transaction(payload: CRM3GenericRecordInput):
    props = payload.properties
    payment_method = str(props.get("payment_method", ""))
    order_id = str(props.get("order_id", ""))

    if (
        "declined" in payment_method.lower()
        or order_id == "rec_ord_declined"
    ):
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={
                "status": "error",
                "category": "PAYMENT_REJECTED",
                "message": "Transaction declined by gateway",
                "details": {
                    "failureReason": "card_declined",
                },
            },
        )

    txn_id = f"rec_txn_{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    record_props = dict(props)
    record_props.setdefault("transaction_status", "completed")
    record_props.setdefault("timestamp", now_iso)
    record = {
        "id": txn_id,
        "objectType": "transaction",
        "properties": record_props,
        "createdAt": now_iso,
    }
    data.crm3_data["payments"][txn_id] = record
    return record
