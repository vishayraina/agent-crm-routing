from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional
import httpx

from src.domain.models import AppointmentSlot, Contact, ContactCreate, Order, Payment
from src.domain.errors import (
    CanonicalError,
    CanonicalException,
    EntityNotFoundError,
    PaymentFailedError,
    ProviderUnavailableError,
    SlotConflictError,
    ValidationError,
)


def parse_datetime(val: Any) -> datetime | None:
    """Helper to parse datetime from ISO string, epoch seconds, or epoch milliseconds."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, (int, float)):
        # If timestamp is in milliseconds (greater than 1e11)
        if val > 1e11:
            return datetime.fromtimestamp(val / 1000.0, tz=timezone.utc)
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(val, str):
        val_clean = val.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(val_clean)
        except Exception:
            return None
    return None


class BaseCRMAdapter(ABC):
    """Base abstract CRM provider adapter defining bidirectional mapping and dispatch."""

    crm_id: str

    def __init__(
        self,
        client: httpx.AsyncClient | httpx.Client | None = None,
        base_url: str | None = None,
    ) -> None:
        self.client = client
        self.base_url = base_url

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> httpx.Response:
        """Execute HTTP request against downstream provider with error normalization."""
        if self.client is None:
            raise ProviderUnavailableError(
                message=f"No downstream HTTP client configured for target CRM '{self.crm_id}'",
                target_crm=self.crm_id,
            )

        try:
            if isinstance(self.client, httpx.AsyncClient):
                response = await self.client.request(method, path, params=params, json=json)
            else:
                response = self.client.request(method, path, params=params, json=json)
        except Exception as exc:
            raise ProviderUnavailableError(
                message=f"Failed to communicate with provider CRM '{self.crm_id}': {exc}",
                target_crm=self.crm_id,
                details={"error": str(exc)},
            ) from exc

        if response.is_error:
            try:
                err_body = response.json()
            except Exception:
                err_body = {"raw": response.text}
            raise self.normalize_error(response.status_code, err_body)

        return response

    @abstractmethod
    def to_provider_contact(self, contact: ContactCreate) -> dict[str, Any]:
        """Convert canonical ContactCreate into provider schema."""
        ...

    @abstractmethod
    def from_provider_contact(self, data: dict[str, Any]) -> Contact:
        """Convert provider contact representation into canonical Contact model."""
        ...

    @abstractmethod
    def from_provider_order(self, data: dict[str, Any]) -> Order:
        """Convert provider order representation into canonical Order model."""
        ...

    @abstractmethod
    def to_provider_slot(self, slot: AppointmentSlot) -> dict[str, Any]:
        """Convert canonical AppointmentSlot into provider booking schema."""
        ...

    @abstractmethod
    def from_provider_slot(self, data: dict[str, Any]) -> AppointmentSlot:
        """Convert provider slot representation into canonical AppointmentSlot model."""
        ...

    @abstractmethod
    def to_provider_payment(self, payment: Payment) -> dict[str, Any]:
        """Convert canonical Payment into provider transaction schema."""
        ...

    @abstractmethod
    def from_provider_payment(self, data: dict[str, Any]) -> Payment:
        """Convert provider payment representation into canonical Payment model."""
        ...

    @abstractmethod
    def normalize_error(self, status_code: int, response_data: dict[str, Any] | str) -> CanonicalException:
        """Map provider-specific error response into a typed CanonicalException."""
        ...

    @abstractmethod
    async def get_contact(self, contact_id: Optional[str] = None, email: Optional[str] = None) -> Contact:
        """Fetch contact details by contact_id or email."""
        ...

    @abstractmethod
    async def create_contact(self, contact: ContactCreate) -> Contact:
        """Create a new contact in the provider CRM."""
        ...

    @abstractmethod
    async def get_order(self, order_id: str) -> Order:
        """Fetch order details by order_id."""
        ...

    @abstractmethod
    async def book_slot(self, slot: AppointmentSlot) -> AppointmentSlot:
        """Book an appointment slot on provider schedule."""
        ...

    @abstractmethod
    async def charge_payment(self, payment: Payment) -> Payment:
        """Charge a payment transaction in provider CRM."""
        ...

    # Synchronous helpers for callers operating outside an async event loop
    def get_contact_sync(self, contact_id: Optional[str] = None, email: Optional[str] = None) -> Contact:
        return asyncio.run(self.get_contact(contact_id=contact_id, email=email))

    def create_contact_sync(self, contact: ContactCreate) -> Contact:
        return asyncio.run(self.create_contact(contact))

    def get_order_sync(self, order_id: str) -> Order:
        return asyncio.run(self.get_order(order_id))

    def book_slot_sync(self, slot: AppointmentSlot) -> AppointmentSlot:
        return asyncio.run(self.book_slot(slot))

    def charge_payment_sync(self, payment: Payment) -> Payment:
        return asyncio.run(self.charge_payment(payment))
