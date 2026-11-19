from __future__ import annotations

from typing import Any, Optional
from fastapi import Depends, FastAPI, Header, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
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
from src.routing.adapters.registry import (
    get_adapter,
    get_default_downstream_client,
    normalize_target_crm,
)
from src.routing.credentials import RoutingCredentialStore, default_credential_store

HTTP_422_STATUS = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

ERROR_STATUS_MAP: dict[type[CanonicalException], int] = {
    EntityNotFoundError: status.HTTP_404_NOT_FOUND,
    SlotConflictError: status.HTTP_409_CONFLICT,
    PaymentFailedError: status.HTTP_402_PAYMENT_REQUIRED,
    ValidationError: HTTP_422_STATUS,
    ProviderUnavailableError: status.HTTP_502_BAD_GATEWAY,
}


def resolve_target_crm(
    x_crm_target: Optional[str] = Header(default=None, alias="X-CRM-Target"),
    target_crm: Optional[str] = Query(default=None),
    crm_target: Optional[str] = Query(default=None),
) -> str:
    """Dependency extracting and validating target CRM from header or query param."""
    raw_target = x_crm_target or target_crm or crm_target
    if not raw_target:
        raise ValidationError(
            message="Target CRM must be specified via 'X-CRM-Target' header or 'target_crm' query param",
            details={"supported_targets": ["crm_1", "crm_2", "crm_3"]},
        )

    target = normalize_target_crm(raw_target)
    if target not in ("crm_1", "crm_2", "crm_3"):
        raise ValidationError(
            message=f"Unknown target CRM '{raw_target}'. Supported targets: crm_1, crm_2, crm_3",
            target_crm=raw_target,
            details={"target_crm": raw_target, "supported_targets": ["crm_1", "crm_2", "crm_3"]},
        )

    return target


def create_routing_app(
    downstream_client: httpx.AsyncClient | httpx.Client | None = None,
    mock_app: Any = None,
    base_url: str | None = None,
    credential_store: RoutingCredentialStore | None = None,
) -> FastAPI:
    """Factory function creating the Central Routing Layer FastAPI application."""
    app = FastAPI(
        title="CRM Routing Layer",
        description="Centralized routing layer and adapter orchestration for heterogeneous CRMs",
        version="1.0.0",
    )

    if downstream_client is not None:
        app.state.downstream_client = downstream_client
    elif base_url is not None:
        app.state.downstream_client = httpx.AsyncClient(base_url=base_url)
    elif mock_app is not None:
        app.state.downstream_client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=mock_app),
            base_url="http://mock-crms",
        )
    else:
        app.state.downstream_client = get_default_downstream_client()

    app.state.credential_store = credential_store or default_credential_store

    def get_client(request: Request) -> httpx.AsyncClient | httpx.Client:
        return getattr(request.app.state, "downstream_client", None) or get_default_downstream_client()

    def get_credentials(request: Request) -> RoutingCredentialStore:
        return getattr(request.app.state, "credential_store", None) or default_credential_store

    @app.exception_handler(CanonicalException)
    async def canonical_exception_handler(request: Request, exc: CanonicalException) -> JSONResponse:
        status_code = ERROR_STATUS_MAP.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
        return JSONResponse(
            status_code=status_code,
            content=exc.to_canonical_error().model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        messages = [f"{'.'.join(str(loc) for loc in err.get('loc', []))}: {err.get('msg', '')}" for err in exc.errors()]
        canonical_err = ValidationError(
            message="Request validation failed: " + "; ".join(messages),
            details={"validation_errors": exc.errors()},
        )
        return JSONResponse(
            status_code=HTTP_422_STATUS,
            content=canonical_err.to_canonical_error().model_dump(),
        )

    # -------------------------------------------------------------------------
    # Canonical Endpoints
    # -------------------------------------------------------------------------

    @app.get("/api/v1/contacts", response_model=Contact)
    async def get_contact(
        request: Request,
        contact_id: Optional[str] = Query(default=None),
        email: Optional[str] = Query(default=None),
        target_crm: str = Depends(resolve_target_crm),
    ) -> Contact:
        client = get_client(request)
        creds = get_credentials(request)
        adapter = get_adapter(target_crm, client=client, credential_store=creds)
        return await adapter.get_contact(contact_id=contact_id, email=email)

    @app.post("/api/v1/contacts", response_model=Contact, status_code=status.HTTP_201_CREATED)
    async def create_contact(
        request: Request,
        payload: ContactCreate,
        target_crm: str = Depends(resolve_target_crm),
    ) -> Contact:
        client = get_client(request)
        creds = get_credentials(request)
        adapter = get_adapter(target_crm, client=client, credential_store=creds)
        return await adapter.create_contact(payload)

    @app.get("/api/v1/orders", response_model=list[Order])
    async def get_orders(
        request: Request,
        contact_id: str = Query(..., description="Contact ID to query orders for"),
        target_crm: str = Depends(resolve_target_crm),
    ) -> list[Order]:
        client = get_client(request)
        creds = get_credentials(request)
        adapter = get_adapter(target_crm, client=client, credential_store=creds)
        return await adapter.get_orders(contact_id=contact_id)

    @app.get("/api/v1/orders/{order_id}", response_model=Order)
    async def get_order(
        request: Request,
        order_id: str,
        target_crm: str = Depends(resolve_target_crm),
    ) -> Order:
        client = get_client(request)
        creds = get_credentials(request)
        adapter = get_adapter(target_crm, client=client, credential_store=creds)
        return await adapter.get_order(order_id)

    @app.post("/api/v1/slots/book", response_model=AppointmentSlot, status_code=status.HTTP_201_CREATED)
    async def book_slot(
        request: Request,
        slot: AppointmentSlot,
        target_crm: str = Depends(resolve_target_crm),
    ) -> AppointmentSlot:
        client = get_client(request)
        creds = get_credentials(request)
        adapter = get_adapter(target_crm, client=client, credential_store=creds)
        return await adapter.book_slot(slot)

    @app.post("/api/v1/payments/charge", response_model=Payment, status_code=status.HTTP_201_CREATED)
    async def charge_payment(
        request: Request,
        payment: Payment,
        target_crm: str = Depends(resolve_target_crm),
    ) -> Payment:
        client = get_client(request)
        creds = get_credentials(request)
        adapter = get_adapter(target_crm, client=client, credential_store=creds)
        return await adapter.charge_payment(payment)

    return app


# Default singleton instance configured with downstream mock CRMs
routing_app = create_routing_app()
