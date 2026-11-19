from __future__ import annotations

from src.client.crm_client import (
    AppointmentsNamespace,
    AsyncCrmClient,
    ContactsNamespace,
    CrmClient,
    OrdersNamespace,
    PaymentsNamespace,
)

__all__ = [
    "CrmClient",
    "AsyncCrmClient",
    "ContactsNamespace",
    "OrdersNamespace",
    "AppointmentsNamespace",
    "PaymentsNamespace",
]
