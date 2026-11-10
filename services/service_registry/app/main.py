"""Service Registry – FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.registry_store import RegistryStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize registry store on startup."""
    app.state.store = RegistryStore()
    app.state.store.load()
    yield


app = FastAPI(
    title="Digital Product Memory Service Registry",
    description="Manages decentralized data provider endpoints for the Digital Product Passport ecosystem.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "service-registry"}
