from fastapi import FastAPI
from src.mock_crms.crm1 import router as crm1_router
from src.mock_crms.crm2 import router as crm2_router
from src.mock_crms.crm3 import router as crm3_router


def create_mock_crms_app() -> FastAPI:
    app = FastAPI(
        title="Mock CRMs API",
        description="Simulated heterogeneous CRM endpoints (CRM 1, CRM 2, CRM 3)",
        version="1.0.0",
    )
    app.include_router(crm1_router)
    app.include_router(crm2_router)
    app.include_router(crm3_router)
    return app


mock_crms_app = create_mock_crms_app()
