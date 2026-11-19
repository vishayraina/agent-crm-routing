from __future__ import annotations

from typing import Optional
import httpx

from src.domain.errors import ValidationError
from src.mock_crms.app import mock_crms_app
from src.routing.adapters.base import BaseCRMAdapter
from src.routing.adapters.crm1 import CRM1Adapter
from src.routing.adapters.crm2 import CRM2Adapter
from src.routing.adapters.crm3 import CRM3Adapter
from src.routing.credentials import RoutingCredentialStore

_DEFAULT_DOWNSTREAM_CLIENT: Optional[httpx.AsyncClient] = None


def get_default_downstream_client() -> httpx.AsyncClient:
    """Return a singleton AsyncClient connected in-memory to the mock CRMs ASGI application."""
    global _DEFAULT_DOWNSTREAM_CLIENT
    if _DEFAULT_DOWNSTREAM_CLIENT is None or _DEFAULT_DOWNSTREAM_CLIENT.is_closed:
        _DEFAULT_DOWNSTREAM_CLIENT = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=mock_crms_app),
            base_url="http://mock-crms",
        )
    return _DEFAULT_DOWNSTREAM_CLIENT


def normalize_target_crm(raw: str | None) -> str:
    """Normalize target CRM identifiers (e.g. crm_1, CRM-1, crm1) into standard crm_N format."""
    if not raw:
        return ""
    norm = raw.strip().lower().replace("-", "_")
    if norm in ("crm1", "crm_1"):
        return "crm_1"
    if norm in ("crm2", "crm_2"):
        return "crm_2"
    if norm in ("crm3", "crm_3"):
        return "crm_3"
    return norm


def get_adapter(
    target_crm: str,
    client: httpx.AsyncClient | httpx.Client | None = None,
    credential_store: RoutingCredentialStore | None = None,
) -> BaseCRMAdapter:
    """Resolve and instantiate a CRM provider adapter for the given target CRM."""
    norm_target = normalize_target_crm(target_crm)
    effective_client = client or get_default_downstream_client()

    if norm_target == "crm_1":
        return CRM1Adapter(client=effective_client, credential_store=credential_store)
    if norm_target == "crm_2":
        return CRM2Adapter(client=effective_client, credential_store=credential_store)
    if norm_target == "crm_3":
        return CRM3Adapter(client=effective_client, credential_store=credential_store)

    raise ValidationError(
        message=f"Unknown target CRM '{target_crm}'. Supported targets: crm_1, crm_2, crm_3",
        target_crm=target_crm,
        details={"target_crm": target_crm, "supported_targets": ["crm_1", "crm_2", "crm_3"]},
    )
