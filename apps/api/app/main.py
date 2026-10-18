from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.app.modules.core.db import engine, create_db_and_tables
from apps.api.app.modules.core import models  # noqa: F401  (registers all tables)

from apps.api.app.modules.auth.router.auth import router as auth_router
from apps.api.app.modules.admin.router.packs import router as admin_packs_router
from apps.api.app.modules.admin.router.sources import router as admin_sources_router
from apps.api.app.modules.admin.router.clauses import router as admin_clauses_router
from apps.api.app.modules.information_collector.router.collector import router as ic_router
from apps.api.app.modules.rag.router.rag import router as rag_router
from apps.api.app.modules.contract_planner.router.planner import router as planner_router
from apps.api.app.modules.validation.router.validation import router as validation_router
from apps.api.app.modules.rendering.router.rendering import router as rendering_router
from apps.api.app.modules.contracts.router.contracts import router as contracts_router
from apps.api.app.modules.risks.router.risks import router as risks_router
from apps.api.app.modules.negotiation.router.negotiation import router as negotiation_router
from apps.api.app.modules.evaluation.router.evaluation import router as evaluation_router
from apps.api.app.modules.ai_providers.router import router as ai_providers_router

__all__ = ["app", "engine", "create_db_and_tables"]

app = FastAPI(
    title="Hannibal V2 API",
    description="Legal Contract Reasoning Engine",
    version="0.1.0",
    on_startup=[create_db_and_tables],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Hannibal V2 API", "version": "0.1.0"}


app.include_router(auth_router)
app.include_router(admin_packs_router)
app.include_router(admin_sources_router)
app.include_router(admin_clauses_router)
app.include_router(ic_router)
app.include_router(rag_router)
app.include_router(planner_router)
app.include_router(validation_router)
app.include_router(rendering_router)
app.include_router(contracts_router)
app.include_router(risks_router)
app.include_router(negotiation_router)
app.include_router(evaluation_router)
app.include_router(ai_providers_router)