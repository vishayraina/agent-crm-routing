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


class CRM2Adapter(BaseCRMAdapter):
    """Adapter for CRM 2 (Nested camelCase RPC)."""

    crm_id: str = "crm_2"

    def to_provider_contact(self, contact: ContactCreate) -> dict[str, Any]:
        return {
            "contactInfo": {
                "firstName": contact.first_name,
                "lastName": contact.last_name,
                "emailAddress": contact.email,
                "phoneNumber": contact.phone or "",
                "organization": contact.company or "",
            }
        }

    def from_provider_contact(self, data: dict[str, Any]) -> Contact:
        details = data.get("customerDetails", data)
        info = details.get("contactInfo", details)
        metadata = details.get("systemMetadata", {})
        created_at = parse_datetime(metadata.get("createdEpochMs"))

        return Contact(
            id=info.get("contactId", ""),
            first_name=info.get("firstName", ""),
            last_name=info.get("lastName", ""),
            email=info.get("emailAddress", ""),
            phone=info.get("phoneNumber") or None,
            company=info.get("organization") or None,
            created_at=created_at,
        )

    def from_provider_order(self, data: dict[str, Any]) -> Order:
        details = data.get("orderDetails", data)
        items: list[OrderItem] = []
        for line_item in details.get("lineItems", []):
            item_id = line_item.get("sku") or line_item.get("item_id")
            name = line_item.get("productName") or line_item.get("name", "")
            qty = line_item.get("quantity", 1)
            unit_price = line_item.get("unitPrice") if "unitPrice" in line_item else line_item.get("price", 0.0)
            items.append(
                OrderItem(
                    item_id=item_id,
                    name=name,
                    quantity=qty,
                    unit_price=float(unit_price),
                )
            )

        status = details.get("fulfillmentStatus", "pending").lower()
        return Order(
            id=details["orderId"],
            contact_id=details["customerId"],
            items=items,
            total_amount=float(details["orderTotal"]),
            currency=details.get("currencyCode", "USD"),
            status=status,
            shipping_address=details.get("deliveryAddress"),
        )

    def to_provider_slot(self, slot: AppointmentSlot) -> dict[str, Any]:
        start_ms = int(slot.start_time.timestamp() * 1000)
        end_ms = int(slot.end_time.timestamp() * 1000)
        return {
            "bookingRequest": {
                "slotId": slot.id,
                "startEpochMs": start_ms,
                "endEpochMs": end_ms,
                "meetingSubject": slot.title,
                "participantEmail": slot.attendee_email or "",
            }
        }

    def from_provider_slot(self, data: dict[str, Any]) -> AppointmentSlot:
        result = data.get("bookingResult", data)
        start_time = parse_datetime(result.get("startEpochMs"))
        end_time = parse_datetime(result.get("endEpochMs"))
        status = result.get("bookingState", "available").lower()
        if status == "confirmed":
            status = "confirmed"

        return AppointmentSlot(
            id=result["bookingId"],
            start_time=start_time,  # type: ignore[arg-type]
            end_time=end_time,      # type: ignore[arg-type]
            title=result.get("meetingSubject", "Meeting"),
            attendee_email=result.get("participantEmail"),
            status=status,
        )

    def to_provider_payment(self, payment: Payment) -> dict[str, Any]:
        return {
            "chargeRequest": {
                "orderId": payment.order_id,
                "chargeAmount": payment.amount,
                "currencyCode": payment.currency,
                "paymentSource": payment.payment_method,
            }
        }

    def from_provider_payment(self, data: dict[str, Any]) -> Payment:
        result = data.get("chargeResult", data)
        status = result.get("chargeState", "completed").lower()
        if status == "settled":
            status = "completed"
        return Payment(
            id=result["transactionId"],
            order_id=result["orderId"],
            amount=float(result["amountCaptured"]),
            currency=result.get("currencyCode", "USD"),
            payment_method=result.get("paymentSource", "credit_card"),
            status=status,
            transaction_timestamp=parse_datetime(result.get("processedEpochMs")),
        )

    def normalize_error(self, status_code: int, response_data: dict[str, Any] | str) -> CanonicalException:
        details = response_data if isinstance(response_data, dict) else {"raw": str(response_data)}
        rpc_error = details.get("rpcError", {}) if isinstance(details.get("rpcError"), dict) else {}
        code = rpc_error.get("code") or details.get("code") or ""
        msg = rpc_error.get("description") or details.get("message") or f"CRM 2 error (status {status_code})"

        if status_code == 404 or code in ("CONTACT_NOT_FOUND", "ORDER_NOT_FOUND"):
            return EntityNotFoundError(message=msg, target_crm=self.crm_id, details=details)
        if status_code == 409 or code == "SLOT_CONFLICT":
            return SlotConflictError(message=msg, target_crm=self.crm_id, details=details)
        if status_code == 402 or code == "PAYMENT_DECLINED":
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
            res = await self._request("POST", "/crm2/api/v2/getContact", json={"contactId": contact_id})
            return self.from_provider_contact(res.json())
        if email:
            res = await self._request("POST", "/crm2/api/v2/getContact", json={"email": email})
            return self.from_provider_contact(res.json())
        raise ValidationError(
            message="Either contact_id or email must be provided for contact lookup",
            target_crm=self.crm_id,
        )

    async def create_contact(self, contact: ContactCreate) -> Contact:
        payload = self.to_provider_contact(contact)
        res = await self._request("POST", "/crm2/api/v2/createContact", json=payload)
        return self.from_provider_contact(res.json())

    async def get_order(self, order_id: str) -> Order:
        res = await self._request("POST", "/crm2/api/v2/fetchOrder", json={"orderId": order_id})
        return self.from_provider_order(res.json())

    async def get_orders(self, contact_id: str) -> list[Order]:
        res = await self._request("POST", "/crm2/api/v2/queryOrders", json={"customerId": contact_id})
        body = res.json()
        orders = body.get("orders", [])
        return [self.from_provider_order(o) for o in orders]

    async def book_slot(self, slot: AppointmentSlot) -> AppointmentSlot:
        payload = self.to_provider_slot(slot)
        res = await self._request("POST", "/crm2/api/v2/execBooking", json=payload)
        return self.from_provider_slot(res.json())

    async def charge_payment(self, payment: Payment) -> Payment:
        payload = self.to_provider_payment(payment)
        res = await self._request("POST", "/crm2/api/v2/processCharge", json=payload)
        return self.from_provider_payment(res.json())
