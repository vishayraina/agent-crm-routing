from src.routing.adapters.base import BaseCRMAdapter
from src.routing.adapters.crm1 import CRM1Adapter
from src.routing.adapters.crm2 import CRM2Adapter
from src.routing.adapters.crm3 import CRM3Adapter
from src.routing.adapters.registry import get_adapter, normalize_target_crm

__all__ = [
    "BaseCRMAdapter",
    "CRM1Adapter",
    "CRM2Adapter",
    "CRM3Adapter",
    "get_adapter",
    "normalize_target_crm",
]
