"""AAS Digital Nameplate provider for Digital Product Memory."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.store import AasStore
from shared.vocabulary import categories_for_products


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = AasStore()
    store.load()
    app.state.store = store
    yield


app = FastAPI(
    title="Digital Product Memory AAS Digital Nameplate Provider",
    description="Reads Asset Administration Shell Digital Nameplate data and exposes it as Digital Product Memory product passport fragments.",
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


def _store(request: Request) -> AasStore:
    return request.app.state.store


def service_metadata(request: Request) -> dict:
    store = _store(request)
    return {
        "name": "AAS Digital Nameplate Provider",
        "provider": "Digital Product Memory AAS Adapter",
        "description": "Reads AAS Digital Nameplate submodels based on IDTA 02006-2-0 and maps them to Digital Product Memory passport fields.",
        "product_types": store.product_types(),
        "data_categories": categories_for_products(store.list_products()),
        "conditions": {
            "requires_auth": False,
            "identifier_pattern": ".+",
            "input_format": "AAS JSON with Submodel idShort Nameplate",
            "submodel_template": "Digital Nameplate for Industrial Equipment (IDTA 02006-2-0)",
            "contract": "GET /products/{product_id}",
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "aas-digital-nameplate-provider"}


@app.get("/.well-known/circthread-service")
async def well_known_metadata(request: Request):
    return service_metadata(request)


@app.get("/metadata")
async def metadata(request: Request):
    return service_metadata(request)


@app.get("/products")
async def list_products(request: Request):
    products = _store(request).list_products()
    return {
        "count": len(products),
        "products": [
            {
                "product_id": p["product_id"],
                "product_type": p["product_type"],
                "manufacturer": p.get("manufacturer"),
                "model": p.get("model"),
                "available_fields": sorted(p.keys()),
            }
            for p in products
        ],
    }


@app.get("/products/{product_id}")
async def get_product_data(product_id: str, request: Request):
    product = _store(request).get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return product


@app.get("/aas/{product_id}")
async def get_raw_aas(product_id: str, request: Request):
    aas = _store(request).get_aas(product_id)
    if not aas:
        raise HTTPException(status_code=404, detail=f"AAS for product '{product_id}' not found")
    return aas


@app.post("/aas/ingest", status_code=201)
async def ingest_aas(aas: dict[str, Any], request: Request):
    try:
        product = _store(request).ingest(aas)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "message": "AAS ingested",
        "product_id": product["product_id"],
        "product_type": product["product_type"],
        "product": product,
    }
