from __future__ import annotations

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


class OrdersNamespace:
    """Namespace helper for order operations."""

    def __init__(self, client: CrmClient) -> None:
        self._client = client

    def check(self, order_id: str, target_crm: str | None = None) -> Order:
        """Check order details and fulfillment status by order ID."""
        return self._client.check_order(order_id=order_id, target_crm=target_crm)

    def get(self, order_id: str, target_crm: str | None = None) -> Order:
        """Alias for check order."""
        return self.check(order_id=order_id, target_crm=target_crm)


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
        crm_target: str = "crm_1",
        app: Any = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url
        self.crm_target = crm_target

        if client is not None:
            # Handle httpx.Client configured with an ASGITransport by bridging to TestClient
            transport = getattr(client, "_transport", None)
            if transport is not None and hasattr(transport, "app") and not hasattr(transport, "handle_request"):
                target_base = str(client.base_url) if str(client.base_url) != "" else "http://testserver"
                self._client = TestClient(transport.app, base_url=target_base)
            else:
                self._client = client
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

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        if hasattr(self._client, "close"):
            self._client.close()

    def __enter__(self) -> CrmClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _handle_response(self, response: httpx.Response, target_crm: str) -> dict[str, Any]:
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

    # -------------------------------------------------------------------------
    # Direct Typed Methods (CrmClientProtocol)
    # -------------------------------------------------------------------------

    def get_contact(
        self,
        contact_id: str | None = None,
        email: str | None = None,
        target_crm: str | None = None,
    ) -> Contact:
        """Fetch contact details by contact ID or email."""
        effective_crm = target_crm or self.crm_target
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

        try:
            response = self._client.get(
                "/api/v1/contacts",
                params=params,
                headers={"X-CRM-Target": effective_crm},
            )
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(
                message=f"Request to routing layer failed: {exc}",
                target_crm=effective_crm,
                details={"error": str(exc)},
            ) from exc

        data = self._handle_response(response, target_crm=effective_crm)
        return Contact.model_validate(data)

    def create_contact(
        self,
        contact_data: dict[str, Any] | ContactCreate,
        target_crm: str | None = None,
    ) -> Contact:
        """Create a new contact in the target CRM."""
        effective_crm = target_crm or self.crm_target
        if isinstance(contact_data, ContactCreate):
            payload = contact_data.model_dump()
        elif isinstance(contact_data, dict):
            payload = contact_data
        else:
            raise ValidationError(
                message=f"Invalid contact_data type: {type(contact_data)}",
                target_crm=effective_crm,
            )

        try:
            response = self._client.post(
                "/api/v1/contacts",
                json=payload,
                headers={"X-CRM-Target": effective_crm},
            )
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(
                message=f"Request to routing layer failed: {exc}",
                target_crm=effective_crm,
                details={"error": str(exc)},
            ) from exc

        data = self._handle_response(response, target_crm=effective_crm)
        return Contact.model_validate(data)

    def check_order(
        self,
        order_id: str,
        target_crm: str | None = None,
    ) -> Order:
        """Fetch order details and shipment status by order ID."""
        effective_crm = target_crm or self.crm_target
        try:
            response = self._client.get(
                f"/api/v1/orders/{order_id}",
                headers={"X-CRM-Target": effective_crm},
            )
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(
                message=f"Request to routing layer failed: {exc}",
                target_crm=effective_crm,
                details={"error": str(exc)},
            ) from exc

        data = self._handle_response(response, target_crm=effective_crm)
        return Order.model_validate(data)

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
        effective_crm = target_crm or self.crm_target

        if start_time is None:
            start_dt = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)
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

        payload = {
            "id": slot_id,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "title": title or "Meeting",
            "attendee_email": attendee_email,
            "status": "booked",
        }

        try:
            response = self._client.post(
                "/api/v1/slots/book",
                json=payload,
                headers={"X-CRM-Target": effective_crm},
            )
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(
                message=f"Request to routing layer failed: {exc}",
                target_crm=effective_crm,
                details={"error": str(exc)},
            ) from exc

        data = self._handle_response(response, target_crm=effective_crm)
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
        effective_crm = target_crm or self.crm_target
        payload = {
            "id": payment_id or f"pay_{uuid.uuid4().hex[:8]}",
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "payment_method": payment_method,
            "status": "completed",
        }

        try:
            response = self._client.post(
                "/api/v1/payments/charge",
                json=payload,
                headers={"X-CRM-Target": effective_crm},
            )
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(
                message=f"Request to routing layer failed: {exc}",
                target_crm=effective_crm,
                details={"error": str(exc)},
            ) from exc

        data = self._handle_response(response, target_crm=effective_crm)
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

    def dispatch_tool_call(
        self,
        name: str,
        arguments: dict[str, Any],
        target_crm: str | None = None,
        return_dict: bool = False,
    ) -> Any:
        """Execute a tool invocation by name and arguments.

        On success, returns the canonical model (or serializable dictionary if return_dict=True).
        On CanonicalException, catches and returns structured error JSON.
        """
        effective_crm = target_crm or self.crm_target
        try:
            if name not in ALL_TOOLS:
                raise ValidationError(
                    message=f"Unknown tool '{name}'. Supported tools: {list(ALL_TOOLS.keys())}",
                    target_crm=effective_crm,
                    details={"tool_name": name, "supported_tools": list(ALL_TOOLS.keys())},
                )

            if name == "get_contact":
                contact_id = arguments.get("contact_id")
                email = arguments.get("email")
                if not contact_id and not email:
                    raise ValidationError(
                        message="Missing required parameter 'contact_id' or 'email' for get_contact",
                        target_crm=effective_crm,
                    )
                result = self.get_contact(
                    contact_id=contact_id,
                    email=email,
                    target_crm=effective_crm,
                )

            elif name == "create_contact":
                if "contact_data" in arguments and isinstance(arguments["contact_data"], dict):
                    contact_data = arguments["contact_data"]
                else:
                    contact_data = {
                        k: v for k, v in arguments.items()
                        if k in ("first_name", "last_name", "email", "phone", "company")
                    }
                    if not contact_data:
                        contact_data = arguments
                result = self.create_contact(
                    contact_data=contact_data,
                    target_crm=effective_crm,
                )

            elif name == "check_order":
                order_id = arguments.get("order_id")
                if not order_id:
                    raise ValidationError(
                        message="Missing required parameter 'order_id' for check_order",
                        target_crm=effective_crm,
                    )
                result = self.check_order(
                    order_id=order_id,
                    target_crm=effective_crm,
                )

            elif name == "book_slot":
                slot_id = arguments.get("slot_id")
                attendee_email = arguments.get("attendee_email")
                if not slot_id or not attendee_email:
                    raise ValidationError(
                        message="Missing required parameters 'slot_id' and/or 'attendee_email' for book_slot",
                        target_crm=effective_crm,
                    )
                result = self.book_slot(
                    slot_id=slot_id,
                    attendee_email=attendee_email,
                    title=arguments.get("title"),
                    target_crm=effective_crm,
                    start_time=arguments.get("start_time"),
                    end_time=arguments.get("end_time"),
                )

            elif name == "take_payment":
                order_id = arguments.get("order_id")
                amount = arguments.get("amount")
                if not order_id or amount is None:
                    raise ValidationError(
                        message="Missing required parameters 'order_id' and/or 'amount' for take_payment",
                        target_crm=effective_crm,
                    )
                try:
                    numeric_amount = float(amount)
                except (ValueError, TypeError) as conv_err:
                    raise ValidationError(
                        message=f"Invalid payment amount '{amount}': must be numeric",
                        target_crm=effective_crm,
                    ) from conv_err

                result = self.take_payment(
                    order_id=order_id,
                    amount=numeric_amount,
                    currency=arguments.get("currency", "USD"),
                    payment_method=arguments.get("payment_method", "credit_card"),
                    target_crm=effective_crm,
                )

            else:
                raise ValidationError(
                    message=f"Unhandled tool: {name}",
                    target_crm=effective_crm,
                )

            if return_dict:
                return result.model_dump()
            return result

        except CanonicalException as exc:
            return {
                "error": True,
                "error_type": exc.error_type,
                "message": exc.message,
                "target_crm": exc.target_crm or effective_crm,
                "details": exc.details,
            }
