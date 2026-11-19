from __future__ import annotations

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


class CRM1Adapter(BaseCRMAdapter):
    """Adapter for CRM 1 (Flat REST snake_case)."""

    crm_id: str = "crm_1"

    def to_provider_contact(self, contact: ContactCreate) -> dict[str, Any]:
        return {
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "email": contact.email,
            "phone": contact.phone or "",
            "company": contact.company or "",
        }

    def from_provider_contact(self, data: dict[str, Any]) -> Contact:
        return Contact(
            id=data["id"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            phone=data.get("phone") or None,
            company=data.get("company") or None,
            created_at=parse_datetime(data.get("created_at")),
        )

    def from_provider_order(self, data: dict[str, Any]) -> Order:
        items: list[OrderItem] = []
        for raw_item in data.get("items", []):
            price = raw_item.get("unit_price") if "unit_price" in raw_item else raw_item.get("price", 0.0)
            items.append(
                OrderItem(
                    item_id=raw_item.get("item_id"),
                    name=raw_item.get("name", ""),
                    quantity=raw_item.get("quantity", 1),
                    unit_price=float(price),
                )
            )
        return Order(
            id=data["id"],
            contact_id=data["contact_id"],
            items=items,
            total_amount=float(data["total_amount"]),
            currency=data.get("currency", "USD"),
            status=data.get("status", "pending"),
            shipping_address=data.get("shipping_address"),
        )

    def to_provider_slot(self, slot: AppointmentSlot) -> dict[str, Any]:
        return {
            "slot_id": slot.id,
            "start_time": slot.start_time.isoformat(),
            "end_time": slot.end_time.isoformat(),
            "title": slot.title,
            "attendee_email": slot.attendee_email or "",
        }

    def from_provider_slot(self, data: dict[str, Any]) -> AppointmentSlot:
        return AppointmentSlot(
            id=data["id"],
            start_time=parse_datetime(data["start_time"]),
            end_time=parse_datetime(data["end_time"]),
            title=data.get("title", "Meeting"),
            attendee_email=data.get("attendee_email"),
            status=data.get("status", "available"),
        )

    def to_provider_payment(self, payment: Payment) -> dict[str, Any]:
        return {
            "order_id": payment.order_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_method": payment.payment_method,
        }

    def from_provider_payment(self, data: dict[str, Any]) -> Payment:
        status = data.get("status", "completed")
        if status == "succeeded":
            status = "completed"
        return Payment(
            id=data["id"],
            order_id=data["order_id"],
            amount=float(data["amount"]),
            currency=data.get("currency", "USD"),
            payment_method=data.get("payment_method", "credit_card"),
            status=status,
            transaction_timestamp=parse_datetime(data.get("transaction_timestamp")),
        )

    def normalize_error(self, status_code: int, response_data: dict[str, Any] | str) -> CanonicalException:
        details = response_data if isinstance(response_data, dict) else {"raw": str(response_data)}
        msg = details.get("message") or f"CRM 1 error (status {status_code})"

        if status_code == 404:
            return EntityNotFoundError(message=msg, target_crm=self.crm_id, details=details)
        if status_code == 409:
            return SlotConflictError(message=msg, target_crm=self.crm_id, details=details)
        if status_code == 402:
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
            res = await self._request("GET", f"/crm1/contacts/{contact_id}")
            return self.from_provider_contact(res.json())
        if email:
            res = await self._request("GET", "/crm1/contacts", params={"email": email})
            records = res.json()
            if not records:
                raise EntityNotFoundError(
                    message=f"Contact with email '{email}' not found in CRM 1",
                    target_crm=self.crm_id,
                )
            return self.from_provider_contact(records[0])
        raise ValidationError(
            message="Either contact_id or email must be provided for contact lookup",
            target_crm=self.crm_id,
        )

    async def create_contact(self, contact: ContactCreate) -> Contact:
        payload = self.to_provider_contact(contact)
        res = await self._request("POST", "/crm1/contacts", json=payload)
        return self.from_provider_contact(res.json())

    async def get_order(self, order_id: str) -> Order:
        res = await self._request("GET", f"/crm1/orders/{order_id}")
        return self.from_provider_order(res.json())

    async def book_slot(self, slot: AppointmentSlot) -> AppointmentSlot:
        payload = self.to_provider_slot(slot)
        res = await self._request("POST", "/crm1/slots/book", json=payload)
        return self.from_provider_slot(res.json())

    async def charge_payment(self, payment: Payment) -> Payment:
        payload = self.to_provider_payment(payment)
        res = await self._request("POST", "/crm1/payments/charge", json=payload)
        return self.from_provider_payment(res.json())
