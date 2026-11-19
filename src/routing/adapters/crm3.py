from __future__ import annotations

import json
from typing import Any, Optional

from src.domain.models import AppointmentSlot, Contact, ContactCreate, Order, OrderItem, Payment
from src.domain.errors import (
    CanonicalException,
    EntityNotFoundError,
    PaymentFailedError,
    ProviderUnavailableError,
    SlotConflictError,
    ValidationError,
)
from src.routing.adapters.base import BaseCRMAdapter, parse_datetime


class CRM3Adapter(BaseCRMAdapter):
    """Adapter for CRM 3 (Generic Property-Bag)."""

    crm_id: str = "crm_3"

    def to_provider_contact(self, contact: ContactCreate) -> dict[str, Any]:
        return {
            "properties": {
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "email": contact.email,
                "phone": contact.phone or "",
                "company": contact.company or "",
            }
        }

    def from_provider_contact(self, data: dict[str, Any]) -> Contact:
        props = data.get("properties", {})
        created_at = parse_datetime(data.get("createdAt") or props.get("created_date"))

        return Contact(
            id=data.get("id", ""),
            first_name=props.get("first_name", ""),
            last_name=props.get("last_name", ""),
            email=props.get("email", ""),
            phone=props.get("phone") or None,
            company=props.get("company") or None,
            created_at=created_at,
        )

    def from_provider_order(self, data: dict[str, Any]) -> Order:
        props = data.get("properties", {})
        items: list[OrderItem] = []
        raw_items = props.get("items")
        if not raw_items and "items_json" in props:
            try:
                raw_items = json.loads(props["items_json"])
            except Exception:
                raw_items = []

        if isinstance(raw_items, list):
            for item in raw_items:
                price = item.get("unit_price") if "unit_price" in item else item.get("price", 0.0)
                items.append(
                    OrderItem(
                        item_id=item.get("item_id"),
                        name=item.get("name", ""),
                        quantity=item.get("quantity", 1),
                        unit_price=float(price),
                    )
                )

        total_amount = float(props.get("total_amount", 0.0))
        status = props.get("order_status", "pending")

        return Order(
            id=data.get("id", ""),
            contact_id=props.get("contact_id", ""),
            items=items,
            total_amount=total_amount,
            currency=props.get("currency", "USD"),
            status=status,
            shipping_address=props.get("shipping_address"),
        )

    def to_provider_slot(self, slot: AppointmentSlot) -> dict[str, Any]:
        return {
            "properties": {
                "slot_id": slot.id,
                "start_time": slot.start_time.isoformat(),
                "end_time": slot.end_time.isoformat(),
                "appointment_title": slot.title,
                "attendee_email": slot.attendee_email or "",
            }
        }

    def from_provider_slot(self, data: dict[str, Any]) -> AppointmentSlot:
        props = data.get("properties", {})
        slot_id = data.get("id") or str(props.get("slot_id", ""))
        start_time = parse_datetime(props.get("start_time"))
        end_time = parse_datetime(props.get("end_time"))
        status = props.get("appointment_status", "available")
        if status == "scheduled":
            status = "confirmed"

        return AppointmentSlot(
            id=slot_id,
            start_time=start_time,  # type: ignore[arg-type]
            end_time=end_time,      # type: ignore[arg-type]
            title=props.get("appointment_title", "Meeting"),
            attendee_email=props.get("attendee_email"),
            status=status,
        )

    def to_provider_payment(self, payment: Payment) -> dict[str, Any]:
        return {
            "properties": {
                "order_id": payment.order_id,
                "amount": str(payment.amount),
                "currency": payment.currency,
                "payment_method": payment.payment_method,
            }
        }

    def from_provider_payment(self, data: dict[str, Any]) -> Payment:
        props = data.get("properties", {})
        payment_id = data.get("id", "")
        amount = float(props.get("amount", 0.0))
        timestamp = parse_datetime(props.get("timestamp") or data.get("createdAt"))
        status = props.get("transaction_status", "completed")

        return Payment(
            id=payment_id,
            order_id=props.get("order_id", ""),
            amount=amount,
            currency=props.get("currency", "USD"),
            payment_method=props.get("payment_method", "credit_card"),
            status=status,
            transaction_timestamp=timestamp,
        )

    def normalize_error(self, status_code: int, response_data: dict[str, Any] | str) -> CanonicalException:
        details = response_data if isinstance(response_data, dict) else {"raw": str(response_data)}
        category = details.get("category") or ""
        msg = details.get("message") or f"CRM 3 error (status {status_code})"

        if status_code == 404 or category == "OBJECT_NOT_FOUND":
            return EntityNotFoundError(message=msg, target_crm=self.crm_id, details=details)
        if status_code == 409 or category == "APPOINTMENT_COLLISION":
            return SlotConflictError(message=msg, target_crm=self.crm_id, details=details)
        if status_code == 402 or category == "PAYMENT_REJECTED":
            return PaymentFailedError(message=msg, target_crm=self.crm_id, details=details)
        if status_code == 422:
            return ValidationError(message=msg, target_crm=self.crm_id, details=details)
        if status_code >= 500:
            return ProviderUnavailableError(message=msg, target_crm=self.crm_id, details=details)
        return CanonicalException(
            message=msg,
            error_type="CanonicalError",
            target_crm=self.crm_id,
            details=details,
        )

    async def get_contact(self, contact_id: Optional[str] = None, email: Optional[str] = None) -> Contact:
        if contact_id:
            res = await self._request("GET", f"/crm3/objects/contacts/{contact_id}")
            return self.from_provider_contact(res.json())
        if email:
            res = await self._request("GET", "/crm3/objects/contacts", params={"email": email})
            records = res.json()
            if not records:
                raise EntityNotFoundError(
                    message=f"Contact with email '{email}' not found in CRM 3",
                    target_crm=self.crm_id,
                )
            return self.from_provider_contact(records[0])
        raise ValidationError(
            message="Either contact_id or email must be provided for contact lookup",
            target_crm=self.crm_id,
        )

    async def create_contact(self, contact: ContactCreate) -> Contact:
        payload = self.to_provider_contact(contact)
        res = await self._request("POST", "/crm3/objects/contacts", json=payload)
        return self.from_provider_contact(res.json())

    async def get_order(self, order_id: str) -> Order:
        res = await self._request("GET", f"/crm3/objects/orders/{order_id}")
        return self.from_provider_order(res.json())

    async def book_slot(self, slot: AppointmentSlot) -> AppointmentSlot:
        payload = self.to_provider_slot(slot)
        res = await self._request("POST", "/crm3/objects/appointments", json=payload)
        return self.from_provider_slot(res.json())

    async def charge_payment(self, payment: Payment) -> Payment:
        payload = self.to_provider_payment(payment)
        res = await self._request("POST", "/crm3/objects/transactions", json=payload)
        return self.from_provider_payment(res.json())
