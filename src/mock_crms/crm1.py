import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.mock_crms import data

router = APIRouter(prefix="/crm1", tags=["CRM 1 - Flat REST"])


class CRM1ContactCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None


class CRM1SlotBooking(BaseModel):
    slot_id: str
    start_time: str
    end_time: str
    title: str
    attendee_email: str


class CRM1PaymentCharge(BaseModel):
    order_id: str
    amount: float
    currency: str = "USD"
    payment_method: str


@router.get("/contacts")
def list_or_search_contacts(email: Optional[str] = Query(default=None)):
    contacts = list(data.crm1_data["contacts"].values())
    if email:
        matched = [c for c in contacts if c.get("email") == email]
        return matched
    return contacts


@router.get("/contacts/{contact_id}")
def get_contact(contact_id: str):
    contact = data.crm1_data["contacts"].get(contact_id)
    if not contact:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "contact_not_found",
                "message": f"Contact '{contact_id}' not found",
            },
        )
    return contact


@router.post("/contacts", status_code=status.HTTP_201_CREATED)
def create_contact(payload: CRM1ContactCreate):
    contact_id = f"cont_{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()
    record = {
        "id": contact_id,
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "email": payload.email,
        "phone": payload.phone or "",
        "company": payload.company or "",
        "created_at": created_at,
    }
    data.crm1_data["contacts"][contact_id] = record
    return record


@router.get("/orders")
def list_or_search_orders(contact_id: Optional[str] = Query(default=None)):
    orders = list(data.crm1_data["orders"].values())
    if contact_id:
        orders = [o for o in orders if o.get("contact_id") == contact_id]
    return orders


@router.get("/orders/{order_id}")
def get_order(order_id: str):
    order = data.crm1_data["orders"].get(order_id)
    if not order:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "order_not_found",
                "message": f"Order '{order_id}' not found",
            },
        )
    return order


@router.post("/slots/book", status_code=status.HTTP_201_CREATED)
def book_slot(payload: CRM1SlotBooking):
    if (
        payload.slot_id in data.crm1_data["booked_slots"]
        or "conflict" in payload.slot_id.lower()
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "slot_already_booked",
                "message": f"Slot '{payload.slot_id}' is already reserved by another attendee",
            },
        )

    slot_record = {
        "id": payload.slot_id,
        "start_time": payload.start_time,
        "end_time": payload.end_time,
        "title": payload.title,
        "attendee_email": payload.attendee_email,
        "status": "confirmed",
    }
    data.crm1_data["booked_slots"].add(payload.slot_id)
    data.crm1_data["slots"][payload.slot_id] = slot_record
    return slot_record


@router.post("/payments/charge")
def charge_payment(payload: CRM1PaymentCharge):
    if (
        "declined" in payload.payment_method.lower()
        or payload.order_id == "ord_declined"
        or payload.amount < 0
    ):
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={
                "error": "card_declined",
                "decline_code": "insufficient_funds",
                "message": "The payment was declined due to insufficient funds",
            },
        )

    payment_id = f"pay_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now(timezone.utc).isoformat()
    record = {
        "id": payment_id,
        "order_id": payload.order_id,
        "amount": payload.amount,
        "currency": payload.currency,
        "payment_method": payload.payment_method,
        "status": "succeeded",
        "transaction_timestamp": timestamp,
    }
    data.crm1_data["payments"][payment_id] = record
    return record
