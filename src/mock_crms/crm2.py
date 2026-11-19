import time
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.mock_crms import data

router = APIRouter(prefix="/crm2/api/v2", tags=["CRM 2 - Nested RPC"])


class CRM2GetContactRequest(BaseModel):
    contactId: Optional[str] = None
    email: Optional[str] = None


class CRM2ContactInfo(BaseModel):
    firstName: str
    lastName: str
    emailAddress: str
    phoneNumber: Optional[str] = None
    organization: Optional[str] = None


class CRM2CreateContactRequest(BaseModel):
    contactInfo: CRM2ContactInfo


class CRM2FetchOrderRequest(BaseModel):
    orderId: str


class CRM2QueryOrdersRequest(BaseModel):
    customerId: Optional[str] = None


class CRM2BookingDetail(BaseModel):
    slotId: str
    startEpochMs: int
    endEpochMs: int
    meetingSubject: str
    participantEmail: str


class CRM2ExecBookingRequest(BaseModel):
    bookingRequest: CRM2BookingDetail


class CRM2ChargeDetail(BaseModel):
    orderId: str
    chargeAmount: float
    currencyCode: str = "USD"
    paymentSource: str


class CRM2ProcessChargeRequest(BaseModel):
    chargeRequest: CRM2ChargeDetail


@router.post("/getContact")
def get_contact(payload: CRM2GetContactRequest):
    contact = None
    if payload.contactId:
        contact = data.crm2_data["contacts"].get(payload.contactId)
    elif payload.email:
        for c in data.crm2_data["contacts"].values():
            if c.get("contactInfo", {}).get("emailAddress") == payload.email:
                contact = c
                break

    if not contact:
        identifier = payload.contactId or payload.email or "unknown"
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": "FAILED",
                "responseCode": 404,
                "rpcError": {
                    "code": "CONTACT_NOT_FOUND",
                    "description": f"Customer record '{identifier}' was not found in CRM 2",
                },
            },
        )

    return {
        "status": "SUCCESS",
        "customerDetails": contact,
    }


@router.post("/createContact", status_code=status.HTTP_201_CREATED)
def create_contact(payload: CRM2CreateContactRequest):
    contact_id = f"cnt_{uuid.uuid4().hex[:8]}"
    now_epoch_ms = int(time.time() * 1000)
    record = {
        "contactInfo": {
            "contactId": contact_id,
            "firstName": payload.contactInfo.firstName,
            "lastName": payload.contactInfo.lastName,
            "emailAddress": payload.contactInfo.emailAddress,
            "phoneNumber": payload.contactInfo.phoneNumber or "",
            "organization": payload.contactInfo.organization or "",
        },
        "systemMetadata": {
            "createdEpochMs": now_epoch_ms,
        },
    }
    data.crm2_data["contacts"][contact_id] = record
    return {
        "status": "SUCCESS",
        "customerDetails": record,
    }


@router.post("/fetchOrder")
def fetch_order(payload: CRM2FetchOrderRequest):
    order = data.crm2_data["orders"].get(payload.orderId)
    if not order:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": "FAILED",
                "responseCode": 404,
                "rpcError": {
                    "code": "ORDER_NOT_FOUND",
                    "description": f"Order '{payload.orderId}' not located",
                },
            },
        )
    return {
        "status": "SUCCESS",
        "orderDetails": order,
    }


@router.post("/queryOrders")
def query_orders(payload: CRM2QueryOrdersRequest):
    orders = list(data.crm2_data["orders"].values())
    if payload.customerId:
        orders = [o for o in orders if o.get("customerId") == payload.customerId]
    return {
        "status": "SUCCESS",
        "orders": orders,
    }


@router.get("/orders")
def get_orders_rest(customerId: Optional[str] = None, contact_id: Optional[str] = None):
    cid = customerId or contact_id
    orders = list(data.crm2_data["orders"].values())
    if cid:
        orders = [o for o in orders if o.get("customerId") == cid]
    return {
        "status": "SUCCESS",
        "orders": orders,
    }


@router.post("/execBooking")
def exec_booking(payload: CRM2ExecBookingRequest):
    req = payload.bookingRequest
    if req.slotId in data.crm2_data["booked_slots"] or "conflict" in req.slotId.lower():
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "status": "FAILED",
                "responseCode": 409,
                "rpcError": {
                    "code": "SLOT_CONFLICT",
                    "description": f"The requested schedule slot '{req.slotId}' is already reserved by another appointment",
                },
            },
        )

    data.crm2_data["booked_slots"].add(req.slotId)
    booking_result = {
        "bookingId": req.slotId,
        "startEpochMs": req.startEpochMs,
        "endEpochMs": req.endEpochMs,
        "meetingSubject": req.meetingSubject,
        "participantEmail": req.participantEmail,
        "bookingState": "CONFIRMED",
    }
    data.crm2_data["slots"][req.slotId] = booking_result
    return {
        "status": "SUCCESS",
        "bookingResult": booking_result,
    }


@router.post("/processCharge")
def process_charge(payload: CRM2ProcessChargeRequest):
    req = payload.chargeRequest
    if (
        "declined" in req.paymentSource.lower()
        or req.orderId == "ord_declined"
        or req.chargeAmount < 0
    ):
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={
                "status": "FAILED",
                "responseCode": 402,
                "rpcError": {
                    "code": "PAYMENT_DECLINED",
                    "description": "The transaction was declined by the issuing institution",
                },
            },
        )

    txn_id = f"txn_{uuid.uuid4().hex[:8]}"
    now_epoch_ms = int(time.time() * 1000)
    charge_result = {
        "transactionId": txn_id,
        "orderId": req.orderId,
        "amountCaptured": req.chargeAmount,
        "currencyCode": req.currencyCode,
        "paymentSource": req.paymentSource,
        "chargeState": "SETTLED",
        "processedEpochMs": now_epoch_ms,
    }
    data.crm2_data["payments"][txn_id] = charge_result
    return {
        "status": "SUCCESS",
        "chargeResult": charge_result,
    }
