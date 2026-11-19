from __future__ import annotations

from src.client.crm_client import (
    AppointmentsNamespace,
    ContactsNamespace,
    CrmClient,
    OrdersNamespace,
    PaymentsNamespace,
)

__all__ = [
    "CrmClient",
    "ContactsNamespace",
    "OrdersNamespace",
    "AppointmentsNamespace",
    "PaymentsNamespace",
]
