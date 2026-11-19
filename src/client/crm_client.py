from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
import uuid
import httpx
from fastapi.testclient import TestClient

from src.domain.contracts import CrmClientProtocol
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
from src.domain.tools import ALL_TOOLS


class ContactsNamespace:
    """Namespace helper for contact operations."""

    def __init__(self, client: CrmClient) -> None:
        self._client = client

    def get(
        self,
        contact_id: str | None = None,
        email: str | None = None,
        target_crm: str | None = None,
    ) -> Contact:
        """Fetch contact details by contact ID or email."""
        return self._client.get_contact(
            contact_id=contact_id,
            email=email,
            target_crm=target_crm,
        )

    async def get_async(
        self,
        contact_id: str | None = None,
        email: str | None = None,
        target_crm: str | None = None,
    ) -> Contact:
        """Fetch contact details asynchronously."""
        return await self._client.get_contact_async(
            contact_id=contact_id,
            email=email,
            target_crm=target_crm,
        )

    def create(
        self,
        contact_data: dict[str, Any] | ContactCreate,
        target_crm: str | None = None,
    ) -> Contact:
        """Create a new contact."""
        return self._client.create_contact(
            contact_data=contact_data,
            target_crm=target_crm,
        )

    async def create_async(
        self,
        contact_data: dict[str, Any] | ContactCreate,
        target_crm: str | None = None,
    ) -> Contact:
        """Create a new contact asynchronously."""
        return await self._client.create_contact_async(
            contact_data=contact_data,
            target_crm=target_crm,
        )


class OrdersNamespace:
    """Namespace helper for order operations."""

    def __init__(self, client: CrmClient) -> None:
        self._client = client

    def check(self, order_id: str, target_crm: str | None = None) -> Order:
        """Check order details and fulfillment status by order ID."""
        return self._client.check_order(order_id=order_id, target_crm=target_crm)

    async def check_async(self, order_id: str, target_crm: str | None = None) -> Order:
        """Check order details and fulfillment status asynchronously."""
        return await self._client.check_order_async(order_id=order_id, target_crm=target_crm)

    def get(self, order_id: str, target_crm: str | None = None) -> Order:
        """Alias for check order."""
        return self.check(order_id=order_id, target_crm=target_crm)

    def get_orders(self, contact_id: str, target_crm: str | None = None) -> list[Order]:
        """Fetch all orders for a contact ID."""
        return self._client.get_orders(contact_id=contact_id, target_crm=target_crm)

    def list(self, contact_id: str, target_crm: str | None = None) -> list[Order]:
        """Alias for get_orders."""
        return self.get_orders(contact_id=contact_id, target_crm=target_crm)

    async def get_orders_async(self, contact_id: str, target_crm: str | None = None) -> list[Order]:
        """Fetch all orders for a contact ID asynchronously."""
        return await self._client.get_orders_async(contact_id=contact_id, target_crm=target_crm)


class AppointmentsNamespace:
    """Namespace helper for appointment and calendar slot operations."""

    def __init__(self, client: CrmClient) -> None:
        self._client = client

    def book(
        self,
        slot_id: str,
        attendee_email: str,
        title: str | None = None,
        target_crm: str | None = None,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
    ) -> AppointmentSlot:
        """Book an appointment slot."""
        return self._client.book_slot(
            slot_id=slot_id,
            attendee_email=attendee_email,
            title=title,
            target_crm=target_crm,
            start_time=start_time,
            end_time=end_time,
        )

    async def book_async(
        self,
        slot_id: str,
        attendee_email: str,
        title: str | None = None,
        target_crm: str | None = None,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
    ) -> AppointmentSlot:
        """Book an appointment slot asynchronously."""
        return await self._client.book_slot_async(
            slot_id=slot_id,
            attendee_email=attendee_email,
            title=title,
            target_crm=target_crm,
            start_time=start_time,
            end_time=end_time,
        )


class PaymentsNamespace:
    """Namespace helper for payment and charge operations."""

    def __init__(self, client: CrmClient) -> None:
        self._client = client

    def take(
        self,
        order_id: str,
        amount: float,
        currency: str = "USD",
        payment_method: str = "credit_card",
        target_crm: str | None = None,
        payment_id: str | None = None,
    ) -> Payment:
        """Take a monetary payment against an order."""
        return self._client.take_payment(
            order_id=order_id,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            target_crm=target_crm,
            payment_id=payment_id,
        )

    async def take_async(
        self,
        order_id: str,
        amount: float,
        currency: str = "USD",
        payment_method: str = "credit_card",
        target_crm: str | None = None,
        payment_id: str | None = None,
    ) -> Payment:
        """Take a monetary payment against an order asynchronously."""
        return await self._client.take_payment_async(
            order_id=order_id,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            target_crm=target_crm,
            payment_id=payment_id,
        )

    def charge(
        self,
        order_id: str,
        amount: float,
        currency: str = "USD",
        payment_method: str = "credit_card",
        target_crm: str | None = None,
        payment_id: str | None = None,
    ) -> Payment:
        """Alias for taking a payment charge."""
        return self.take(
            order_id=order_id,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            target_crm=target_crm,
            payment_id=payment_id,
        )


class CrmClient(CrmClientProtocol):
    """Singular Client SDK for agentic applications to communicate with the Central Routing Layer."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        target_crm: str | None = None,
        crm_target: str | None = None,
        app: Any = None,
        client: httpx.Client | None = None,
        async_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url
        self.target_crm = target_crm or crm_target or "crm_1"
        self.crm_target = self.target_crm  # backward-compatible alias
        self._app = app
        self._async_client = async_client

        if client is not None:
            transport = getattr(client, "_transport", None)
            if transport is not None and hasattr(transport, "app") and not hasattr(transport, "handle_request"):
                target_base = str(client.base_url) if str(client.base_url) != "" else "http://testserver"
                self._client = TestClient(transport.app, base_url=target_base)
                if self._app is None:
                    self._app = transport.app
            else:
                self._client = client
                if hasattr(client, "app") and self._app is None:
                    self._app = getattr(client, "app")
        elif app is not None:
            target_base = base_url if base_url != "http://localhost:8000" else "http://testserver"
            self._client = TestClient(app, base_url=target_base)
        else:
            self._client = httpx.Client(base_url=base_url)

        # Namespaces
        self.contacts = ContactsNamespace(self)
        self.orders = OrdersNamespace(self)
        self.appointments = AppointmentsNamespace(self)
        self.payments = PaymentsNamespace(self)

    def _get_async_client(self) -> httpx.AsyncClient:
        """Obtain or lazily instantiate an AsyncClient matching the environment."""
        if self._async_client is not None and not self._async_client.is_closed:
            return self._async_client

        if self._app is not None:
            target_base = self.base_url if self.base_url != "http://localhost:8000" else "http://testserver"
            self._async_client = httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self._app),
                base_url=target_base,
            )
        elif hasattr(self._client, "app") and getattr(self._client, "app") is not None:
            self._async_client = httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self._client.app),
                base_url="http://testserver",
            )
        else:
            self._async_client = httpx.AsyncClient(base_url=self.base_url)

        return self._async_client

    def close(self) -> None:
        """Close the underlying synchronous HTTP client session."""
        if hasattr(self._client, "close"):
            self._client.close()
        if self._async_client is not None and not self._async_client.is_closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._async_client.aclose())
                else:
                    loop.run_until_complete(self._async_client.aclose())
            except Exception:
                pass

    async def aclose(self) -> None:
        """Close both sync and async HTTP client sessions."""
        if self._async_client is not None and not self._async_client.is_closed:
            await self._async_client.aclose()
        if hasattr(self._client, "close"):
            self._client.close()

    def __enter__(self) -> CrmClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    async def __aenter__(self) -> CrmClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.aclose()

    def _handle_response(self, response: httpx.Response, target_crm: str) -> Any:
        """Inspect HTTP response and return JSON payload or raise typed CanonicalException."""
        if response.is_success:
            return response.json()

        status_code = response.status_code
        try:
            data = response.json()
        except Exception:
            data = {}

        if isinstance(data, dict) and "error_type" in data:
            canonical_err = CanonicalError(
                error_type=data.get("error_type", "CanonicalError"),
                message=data.get("message", response.text),
                target_crm=data.get("target_crm") or target_crm,
                details=data.get("details", {}),
            )
            raise CanonicalException.from_canonical_error(canonical_err)

        message = data.get("detail") if isinstance(data, dict) and "detail" in data else response.text or f"HTTP {status_code} error"
        details = data if isinstance(data, dict) else {}

        if status_code == 404:
            raise EntityNotFoundError(message=str(message), target_crm=target_crm, details=details)
        elif status_code == 409:
            raise SlotConflictError(message=str(message), target_crm=target_crm, details=details)
        elif status_code == 402:
            raise PaymentFailedError(message=str(message), target_crm=target_crm, details=details)
        elif status_code in (400, 422):
            raise ValidationError(message=str(message), target_crm=target_crm, details=details)
        elif status_code in (502, 503, 504):
            raise ProviderUnavailableError(message=str(message), target_crm=target_crm, details=details)
        else:
            raise CanonicalException(
                message=str(message),
                error_type="CanonicalError",
                target_crm=target_crm,
                details=details,
            )

    def _request(
        self,
        method: str,
        path: str,
        *,
        target_crm: str,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        """Execute a synchronous HTTP request against the Central Routing Layer."""
        headers = {"X-CRM-Target": target_crm}
        kwargs: dict[str, Any] = {"headers": headers}
        if params is not None:
            kwargs["params"] = params
        if json is not None:
            kwargs["json"] = json

        try:
            client_fn = getattr(self._client, method.lower(), None)
            if client_fn is not None:
                response = client_fn(path, **kwargs)
            else:
                response = self._client.request(
                    method,
                    path,
                    **kwargs,
                )
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(
                message=f"Request to routing layer failed: {exc}",
                target_crm=target_crm,
                details={"error": str(exc)},
            ) from exc

        return self._handle_response(response, target_crm=target_crm)

    async def _request_async(
        self,
        method: str,
        path: str,
        *,
        target_crm: str,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        """Execute an asynchronous HTTP request against the Central Routing Layer."""
        headers = {"X-CRM-Target": target_crm}
        kwargs: dict[str, Any] = {"headers": headers}
        if params is not None:
            kwargs["params"] = params
        if json is not None:
            kwargs["json"] = json

        async_client = self._get_async_client()
        try:
            client_fn = getattr(async_client, method.lower(), None)
            if client_fn is not None:
                response = await client_fn(path, **kwargs)
            else:
                response = await async_client.request(
                    method,
                    path,
                    **kwargs,
                )
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(
                message=f"Request to routing layer failed: {exc}",
                target_crm=target_crm,
                details={"error": str(exc)},
            ) from exc

        return self._handle_response(response, target_crm=target_crm)

    def _prepare_slot_payload(
        self,
        slot_id: str,
        attendee_email: str,
        title: str | None = None,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
    ) -> dict[str, Any]:
        """Construct validated appointment slot payload avoiding hardcoded past dates."""
        if start_time is None:
            now = datetime.now(timezone.utc)
            start_dt = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        elif isinstance(start_time, str):
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        else:
            start_dt = start_time

        if end_time is None:
            end_dt = start_dt + timedelta(hours=1)
        elif isinstance(end_time, str):
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        else:
            end_dt = end_time

        return {
            "id": slot_id,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "title": title or "Meeting",
            "attendee_email": attendee_email,
            "status": "booked",
        }

    # -------------------------------------------------------------------------
    # Direct Typed Sync Methods (CrmClientProtocol)
    # -------------------------------------------------------------------------

    def get_contact(
        self,
        contact_id: str | None = None,
        email: str | None = None,
        target_crm: str | None = None,
    ) -> Contact:
        """Fetch contact details by contact ID or email."""
        effective_crm = target_crm or self.target_crm
        params: dict[str, str] = {}
        if contact_id:
            params["contact_id"] = contact_id
        if email:
            params["email"] = email

        if not params:
            raise ValidationError(
                message="Either 'contact_id' or 'email' must be provided to get_contact",
                target_crm=effective_crm,
            )

        data = self._request("GET", "/api/v1/contacts", target_crm=effective_crm, params=params)
        return Contact.model_validate(data)

    def create_contact(
        self,
        contact_data: dict[str, Any] | ContactCreate,
        target_crm: str | None = None,
    ) -> Contact:
        """Create a new contact in the target CRM."""
        effective_crm = target_crm or self.target_crm
        if isinstance(contact_data, ContactCreate):
            payload = contact_data.model_dump()
        elif isinstance(contact_data, dict):
            payload = contact_data
        else:
            raise ValidationError(
                message=f"Invalid contact_data type: {type(contact_data)}",
                target_crm=effective_crm,
            )

        data = self._request("POST", "/api/v1/contacts", target_crm=effective_crm, json=payload)
        return Contact.model_validate(data)

    def check_order(
        self,
        order_id: str,
        target_crm: str | None = None,
    ) -> Order:
        """Fetch order details and shipment status by order ID."""
        effective_crm = target_crm or self.target_crm
        data = self._request("GET", f"/api/v1/orders/{order_id}", target_crm=effective_crm)
        return Order.model_validate(data)

    def get_orders(
        self,
        contact_id: str,
        target_crm: str | None = None,
    ) -> list[Order]:
        """Fetch all orders associated with a contact ID."""
        effective_crm = target_crm or self.target_crm
        if not contact_id:
            raise ValidationError(
                message="Missing required parameter 'contact_id' for get_orders",
                target_crm=effective_crm,
            )
        data = self._request("GET", "/api/v1/orders", target_crm=effective_crm, params={"contact_id": contact_id})
        if isinstance(data, list):
            return [Order.model_validate(item) for item in data]
        return []

    def book_slot(
        self,
        slot_id: str,
        attendee_email: str,
        title: str | None = None,
        target_crm: str | None = None,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
    ) -> AppointmentSlot:
        """Book an appointment slot on a CRM calendar."""
        effective_crm = target_crm or self.target_crm
        payload = self._prepare_slot_payload(
            slot_id=slot_id,
            attendee_email=attendee_email,
            title=title,
            start_time=start_time,
            end_time=end_time,
        )
        data = self._request("POST", "/api/v1/slots/book", target_crm=effective_crm, json=payload)
        return AppointmentSlot.model_validate(data)

    def take_payment(
        self,
        order_id: str,
        amount: float,
        currency: str = "USD",
        payment_method: str = "credit_card",
        target_crm: str | None = None,
        payment_id: str | None = None,
    ) -> Payment:
        """Charge and record a payment against an order."""
        effective_crm = target_crm or self.target_crm
        payload = {
            "id": payment_id or f"pay_{uuid.uuid4().hex[:8]}",
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "payment_method": payment_method,
            "status": "completed",
        }
        data = self._request("POST", "/api/v1/payments/charge", target_crm=effective_crm, json=payload)
        return Payment.model_validate(data)

    # -------------------------------------------------------------------------
    # Direct Typed Async Methods (Dual-Surface Client SDK)
    # -------------------------------------------------------------------------

    async def get_contact_async(
        self,
        contact_id: str | None = None,
        email: str | None = None,
        target_crm: str | None = None,
    ) -> Contact:
        """Fetch contact details asynchronously."""
        effective_crm = target_crm or self.target_crm
        params: dict[str, str] = {}
        if contact_id:
            params["contact_id"] = contact_id
        if email:
            params["email"] = email

        if not params:
            raise ValidationError(
                message="Either 'contact_id' or 'email' must be provided to get_contact",
                target_crm=effective_crm,
            )

        data = await self._request_async("GET", "/api/v1/contacts", target_crm=effective_crm, params=params)
        return Contact.model_validate(data)

    async def create_contact_async(
        self,
        contact_data: dict[str, Any] | ContactCreate,
        target_crm: str | None = None,
    ) -> Contact:
        """Create a new contact in the target CRM asynchronously."""
        effective_crm = target_crm or self.target_crm
        if isinstance(contact_data, ContactCreate):
            payload = contact_data.model_dump()
        elif isinstance(contact_data, dict):
            payload = contact_data
        else:
            raise ValidationError(
                message=f"Invalid contact_data type: {type(contact_data)}",
                target_crm=effective_crm,
            )

        data = await self._request_async("POST", "/api/v1/contacts", target_crm=effective_crm, json=payload)
        return Contact.model_validate(data)

    async def check_order_async(
        self,
        order_id: str,
        target_crm: str | None = None,
    ) -> Order:
        """Fetch order details and shipment status asynchronously."""
        effective_crm = target_crm or self.target_crm
        data = await self._request_async("GET", f"/api/v1/orders/{order_id}", target_crm=effective_crm)
        return Order.model_validate(data)

    async def get_orders_async(
        self,
        contact_id: str,
        target_crm: str | None = None,
    ) -> list[Order]:
        """Fetch all orders associated with a contact ID asynchronously."""
        effective_crm = target_crm or self.target_crm
        if not contact_id:
            raise ValidationError(
                message="Missing required parameter 'contact_id' for get_orders",
                target_crm=effective_crm,
            )
        data = await self._request_async("GET", "/api/v1/orders", target_crm=effective_crm, params={"contact_id": contact_id})
        if isinstance(data, list):
            return [Order.model_validate(item) for item in data]
        return []

    async def book_slot_async(
        self,
        slot_id: str,
        attendee_email: str,
        title: str | None = None,
        target_crm: str | None = None,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
    ) -> AppointmentSlot:
        """Book an appointment slot asynchronously."""
        effective_crm = target_crm or self.target_crm
        payload = self._prepare_slot_payload(
            slot_id=slot_id,
            attendee_email=attendee_email,
            title=title,
            start_time=start_time,
            end_time=end_time,
        )
        data = await self._request_async("POST", "/api/v1/slots/book", target_crm=effective_crm, json=payload)
        return AppointmentSlot.model_validate(data)

    async def take_payment_async(
        self,
        order_id: str,
        amount: float,
        currency: str = "USD",
        payment_method: str = "credit_card",
        target_crm: str | None = None,
        payment_id: str | None = None,
    ) -> Payment:
        """Charge and record a payment asynchronously."""
        effective_crm = target_crm or self.target_crm
        payload = {
            "id": payment_id or f"pay_{uuid.uuid4().hex[:8]}",
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "payment_method": payment_method,
            "status": "completed",
        }
        data = await self._request_async("POST", "/api/v1/payments/charge", target_crm=effective_crm, json=payload)
        return Payment.model_validate(data)

    # -------------------------------------------------------------------------
    # Tool Declarations & Dispatcher
    # -------------------------------------------------------------------------

    def get_tools(self, tool_names: list[str] | None = None) -> list[dict[str, Any]]:
        """Return LLM function calling schema declarations for tools."""
        if tool_names is not None:
            return [ALL_TOOLS[name] for name in tool_names if name in ALL_TOOLS]
        return list(ALL_TOOLS.values())

    def get_tool_names(self) -> list[str]:
        """Return list of all registered tool names."""
        return list(ALL_TOOLS.keys())

    # Dispatcher Handlers
    def _dispatch_get_contact(self, args: dict[str, Any], target_crm: str) -> Contact:
        contact_id = args.get("contact_id")
        email = args.get("email")
        if not contact_id and not email:
            raise ValidationError(
                message="Missing required parameter 'contact_id' or 'email' for get_contact",
                target_crm=target_crm,
            )
        return self.get_contact(contact_id=contact_id, email=email, target_crm=target_crm)

    async def _dispatch_get_contact_async(self, args: dict[str, Any], target_crm: str) -> Contact:
        contact_id = args.get("contact_id")
        email = args.get("email")
        if not contact_id and not email:
            raise ValidationError(
                message="Missing required parameter 'contact_id' or 'email' for get_contact",
                target_crm=target_crm,
            )
        return await self.get_contact_async(contact_id=contact_id, email=email, target_crm=target_crm)

    def _dispatch_create_contact(self, args: dict[str, Any], target_crm: str) -> Contact:
        if "contact_data" in args and isinstance(args["contact_data"], dict):
            contact_data = args["contact_data"]
        else:
            contact_data = {
                k: v for k, v in args.items()
                if k in ("first_name", "last_name", "email", "phone", "company")
            }
            if not contact_data:
                contact_data = args
        return self.create_contact(contact_data=contact_data, target_crm=target_crm)

    async def _dispatch_create_contact_async(self, args: dict[str, Any], target_crm: str) -> Contact:
        if "contact_data" in args and isinstance(args["contact_data"], dict):
            contact_data = args["contact_data"]
        else:
            contact_data = {
                k: v for k, v in args.items()
                if k in ("first_name", "last_name", "email", "phone", "company")
            }
            if not contact_data:
                contact_data = args
        return await self.create_contact_async(contact_data=contact_data, target_crm=target_crm)

    def _dispatch_check_order(self, args: dict[str, Any], target_crm: str) -> Order:
        order_id = args.get("order_id")
        if not order_id:
            raise ValidationError(
                message="Missing required parameter 'order_id' for check_order",
                target_crm=target_crm,
            )
        return self.check_order(order_id=order_id, target_crm=target_crm)

    async def _dispatch_check_order_async(self, args: dict[str, Any], target_crm: str) -> Order:
        order_id = args.get("order_id")
        if not order_id:
            raise ValidationError(
                message="Missing required parameter 'order_id' for check_order",
                target_crm=target_crm,
            )
        return await self.check_order_async(order_id=order_id, target_crm=target_crm)

    def _dispatch_get_orders(self, args: dict[str, Any], target_crm: str) -> list[Order]:
        contact_id = args.get("contact_id")
        if not contact_id:
            raise ValidationError(
                message="Missing required parameter 'contact_id' for get_orders",
                target_crm=target_crm,
            )
        return self.get_orders(contact_id=contact_id, target_crm=target_crm)

    async def _dispatch_get_orders_async(self, args: dict[str, Any], target_crm: str) -> list[Order]:
        contact_id = args.get("contact_id")
        if not contact_id:
            raise ValidationError(
                message="Missing required parameter 'contact_id' for get_orders",
                target_crm=target_crm,
            )
        return await self.get_orders_async(contact_id=contact_id, target_crm=target_crm)

    def _dispatch_book_slot(self, args: dict[str, Any], target_crm: str) -> AppointmentSlot:
        slot_id = args.get("slot_id")
        attendee_email = args.get("attendee_email")
        if not slot_id or not attendee_email:
            raise ValidationError(
                message="Missing required parameters 'slot_id' and/or 'attendee_email' for book_slot",
                target_crm=target_crm,
            )
        return self.book_slot(
            slot_id=slot_id,
            attendee_email=attendee_email,
            title=args.get("title"),
            target_crm=target_crm,
            start_time=args.get("start_time"),
            end_time=args.get("end_time"),
        )

    async def _dispatch_book_slot_async(self, args: dict[str, Any], target_crm: str) -> AppointmentSlot:
        slot_id = args.get("slot_id")
        attendee_email = args.get("attendee_email")
        if not slot_id or not attendee_email:
            raise ValidationError(
                message="Missing required parameters 'slot_id' and/or 'attendee_email' for book_slot",
                target_crm=target_crm,
            )
        return await self.book_slot_async(
            slot_id=slot_id,
            attendee_email=attendee_email,
            title=args.get("title"),
            target_crm=target_crm,
            start_time=args.get("start_time"),
            end_time=args.get("end_time"),
        )

    def _dispatch_take_payment(self, args: dict[str, Any], target_crm: str) -> Payment:
        order_id = args.get("order_id")
        amount = args.get("amount")
        if not order_id or amount is None:
            raise ValidationError(
                message="Missing required parameters 'order_id' and/or 'amount' for take_payment",
                target_crm=target_crm,
            )
        try:
            numeric_amount = float(amount)
        except (ValueError, TypeError) as conv_err:
            raise ValidationError(
                message=f"Invalid payment amount '{amount}': must be numeric",
                target_crm=target_crm,
            ) from conv_err

        return self.take_payment(
            order_id=order_id,
            amount=numeric_amount,
            currency=args.get("currency", "USD"),
            payment_method=args.get("payment_method", "credit_card"),
            target_crm=target_crm,
        )

    async def _dispatch_take_payment_async(self, args: dict[str, Any], target_crm: str) -> Payment:
        order_id = args.get("order_id")
        amount = args.get("amount")
        if not order_id or amount is None:
            raise ValidationError(
                message="Missing required parameters 'order_id' and/or 'amount' for take_payment",
                target_crm=target_crm,
            )
        try:
            numeric_amount = float(amount)
        except (ValueError, TypeError) as conv_err:
            raise ValidationError(
                message=f"Invalid payment amount '{amount}': must be numeric",
                target_crm=target_crm,
            ) from conv_err

        return await self.take_payment_async(
            order_id=order_id,
            amount=numeric_amount,
            currency=args.get("currency", "USD"),
            payment_method=args.get("payment_method", "credit_card"),
            target_crm=target_crm,
        )

    def dispatch_tool_call(
        self,
        name: str,
        arguments: dict[str, Any],
        target_crm: str | None = None,
        return_dict: bool = False,
    ) -> Any:
        """Execute a tool invocation by name and arguments synchronously.

        On success, returns the canonical model (or serializable dictionary if return_dict=True).
        On CanonicalException, catches and returns structured error JSON.
        """
        effective_crm = target_crm or self.target_crm
        try:
            dispatchers = {
                "get_contact": self._dispatch_get_contact,
                "create_contact": self._dispatch_create_contact,
                "check_order": self._dispatch_check_order,
                "get_orders": self._dispatch_get_orders,
                "book_slot": self._dispatch_book_slot,
                "take_payment": self._dispatch_take_payment,
            }

            if name not in ALL_TOOLS or name not in dispatchers:
                raise ValidationError(
                    message=f"Unknown tool '{name}'. Supported tools: {list(ALL_TOOLS.keys())}",
                    target_crm=effective_crm,
                    details={"tool_name": name, "supported_tools": list(ALL_TOOLS.keys())},
                )

            handler = dispatchers[name]
            result = handler(arguments, effective_crm)

            if return_dict:
                if isinstance(result, list):
                    return [item.model_dump() if hasattr(item, "model_dump") else item for item in result]
                return result.model_dump() if hasattr(result, "model_dump") else result
            return result

        except CanonicalException as exc:
            return {
                "error": True,
                "error_type": exc.error_type,
                "message": exc.message,
                "target_crm": exc.target_crm or effective_crm,
                "details": exc.details,
            }

    async def dispatch_tool_call_async(
        self,
        name: str,
        arguments: dict[str, Any],
        target_crm: str | None = None,
        return_dict: bool = False,
    ) -> Any:
        """Execute a tool invocation by name and arguments asynchronously.

        On success, returns the canonical model (or serializable dictionary if return_dict=True).
        On CanonicalException, catches and returns structured error JSON.
        """
        effective_crm = target_crm or self.target_crm
        try:
            async_dispatchers = {
                "get_contact": self._dispatch_get_contact_async,
                "create_contact": self._dispatch_create_contact_async,
                "check_order": self._dispatch_check_order_async,
                "get_orders": self._dispatch_get_orders_async,
                "book_slot": self._dispatch_book_slot_async,
                "take_payment": self._dispatch_take_payment_async,
            }

            if name not in ALL_TOOLS or name not in async_dispatchers:
                raise ValidationError(
                    message=f"Unknown tool '{name}'. Supported tools: {list(ALL_TOOLS.keys())}",
                    target_crm=effective_crm,
                    details={"tool_name": name, "supported_tools": list(ALL_TOOLS.keys())},
                )

            handler = async_dispatchers[name]
            result = await handler(arguments, effective_crm)

            if return_dict:
                if isinstance(result, list):
                    return [item.model_dump() if hasattr(item, "model_dump") else item for item in result]
                return result.model_dump() if hasattr(result, "model_dump") else result
            return result

        except CanonicalException as exc:
            return {
                "error": True,
                "error_type": exc.error_type,
                "message": exc.message,
                "target_crm": exc.target_crm or effective_crm,
                "details": exc.details,
            }


class AsyncCrmClient:
    """Async Client SDK for agentic applications communicating with the Routing Layer."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        target_crm: str | None = None,
        crm_target: str | None = None,
        app: Any = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._sync_client = CrmClient(
            base_url=base_url,
            target_crm=target_crm,
            crm_target=crm_target,
            app=app,
            async_client=client,
        )

    @property
    def target_crm(self) -> str:
        return self._sync_client.target_crm

    @property
    def crm_target(self) -> str:
        return self._sync_client.crm_target

    async def get_contact(
        self,
        contact_id: str | None = None,
        email: str | None = None,
        target_crm: str | None = None,
    ) -> Contact:
        return await self._sync_client.get_contact_async(contact_id=contact_id, email=email, target_crm=target_crm)

    async def get_contact_async(
        self,
        contact_id: str | None = None,
        email: str | None = None,
        target_crm: str | None = None,
    ) -> Contact:
        return await self._sync_client.get_contact_async(contact_id=contact_id, email=email, target_crm=target_crm)

    async def create_contact(
        self,
        contact_data: dict[str, Any] | ContactCreate,
        target_crm: str | None = None,
    ) -> Contact:
        return await self._sync_client.create_contact_async(contact_data=contact_data, target_crm=target_crm)

    async def create_contact_async(
        self,
        contact_data: dict[str, Any] | ContactCreate,
        target_crm: str | None = None,
    ) -> Contact:
        return await self._sync_client.create_contact_async(contact_data=contact_data, target_crm=target_crm)

    async def check_order(
        self,
        order_id: str,
        target_crm: str | None = None,
    ) -> Order:
        return await self._sync_client.check_order_async(order_id=order_id, target_crm=target_crm)

    async def check_order_async(
        self,
        order_id: str,
        target_crm: str | None = None,
    ) -> Order:
        return await self._sync_client.check_order_async(order_id=order_id, target_crm=target_crm)

    async def get_orders(
        self,
        contact_id: str,
        target_crm: str | None = None,
    ) -> list[Order]:
        return await self._sync_client.get_orders_async(contact_id=contact_id, target_crm=target_crm)

    async def get_orders_async(
        self,
        contact_id: str,
        target_crm: str | None = None,
    ) -> list[Order]:
        return await self._sync_client.get_orders_async(contact_id=contact_id, target_crm=target_crm)

    async def book_slot(
        self,
        slot_id: str,
        attendee_email: str,
        title: str | None = None,
        target_crm: str | None = None,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
    ) -> AppointmentSlot:
        return await self._sync_client.book_slot_async(
            slot_id=slot_id,
            attendee_email=attendee_email,
            title=title,
            target_crm=target_crm,
            start_time=start_time,
            end_time=end_time,
        )

    async def book_slot_async(
        self,
        slot_id: str,
        attendee_email: str,
        title: str | None = None,
        target_crm: str | None = None,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
    ) -> AppointmentSlot:
        return await self._sync_client.book_slot_async(
            slot_id=slot_id,
            attendee_email=attendee_email,
            title=title,
            target_crm=target_crm,
            start_time=start_time,
            end_time=end_time,
        )

    async def take_payment(
        self,
        order_id: str,
        amount: float,
        currency: str = "USD",
        payment_method: str = "credit_card",
        target_crm: str | None = None,
        payment_id: str | None = None,
    ) -> Payment:
        return await self._sync_client.take_payment_async(
            order_id=order_id,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            target_crm=target_crm,
            payment_id=payment_id,
        )

    async def take_payment_async(
        self,
        order_id: str,
        amount: float,
        currency: str = "USD",
        payment_method: str = "credit_card",
        target_crm: str | None = None,
        payment_id: str | None = None,
    ) -> Payment:
        return await self._sync_client.take_payment_async(
            order_id=order_id,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            target_crm=target_crm,
            payment_id=payment_id,
        )

    async def dispatch_tool_call(
        self,
        name: str,
        arguments: dict[str, Any],
        target_crm: str | None = None,
        return_dict: bool = False,
    ) -> Any:
        return await self._sync_client.dispatch_tool_call_async(
            name=name,
            arguments=arguments,
            target_crm=target_crm,
            return_dict=return_dict,
        )

    async def dispatch_tool_call_async(
        self,
        name: str,
        arguments: dict[str, Any],
        target_crm: str | None = None,
        return_dict: bool = False,
    ) -> Any:
        return await self._sync_client.dispatch_tool_call_async(
            name=name,
            arguments=arguments,
            target_crm=target_crm,
            return_dict=return_dict,
        )

    def get_tools(self, tool_names: list[str] | None = None) -> list[dict[str, Any]]:
        return self._sync_client.get_tools(tool_names=tool_names)

    def get_tool_names(self) -> list[str]:
        return self._sync_client.get_tool_names()

    async def aclose(self) -> None:
        await self._sync_client.aclose()

    async def __aenter__(self) -> AsyncCrmClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.aclose()
