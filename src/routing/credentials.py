from __future__ import annotations

from typing import Dict, Optional


class RoutingCredentialStore:
    """Centralized credential storage and injection inside the Routing Layer.

    Manages third-party CRM API keys and tokens so they remain strictly
    within the Routing Layer and are never exposed to agent runtimes.
    """

    DEFAULT_CREDENTIALS: Dict[str, str] = {
        "crm_1": "key-crm1-secret",
        "crm_2": "key-crm2-secret",
        "crm_3": "key-crm3-secret",
    }

    def __init__(self, credentials: Optional[Dict[str, str]] = None) -> None:
        self._credentials: Dict[str, str] = dict(credentials or self.DEFAULT_CREDENTIALS)

    def get_credential(self, target_crm: str) -> Optional[str]:
        """Retrieve the API key or token for the specified target CRM."""
        return self._credentials.get(target_crm)

    def set_credential(self, target_crm: str, token: str) -> None:
        """Store or update a credential for a target CRM."""
        self._credentials[target_crm] = token

    def get_auth_headers(self, target_crm: str) -> Dict[str, str]:
        """Generate authentication headers to attach to outbound provider requests."""
        token = self.get_credential(target_crm)
        if not token:
            return {}
        return {
            "Authorization": f"Bearer {token}",
            "X-Vendor-API-Key": token,
        }


# Singleton credential store used by default
default_credential_store = RoutingCredentialStore()
