"""Digital Product Memory provider for public EPREL product data."""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.eprel_client import (
    EprelNotFoundError,
    EprelUpstreamError,
    fetch_eprel_product_by_identifier,
    list_seed_products,
    supported_product_groups,
    supported_product_types,
    to_catalog_item,
    to_passport,
)


app = FastAPI(
    title="Digital Product Memory EPREL Provider",
    description="Provides public product data from the EU EPREL product registry.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def service_metadata() -> dict:
    """Return self-description consumed by the Service Registry."""
    return {
        "name": "EU EPREL Provider",
        "provider": "European Commission EPREL",
        "description": "Maps public EPREL product registry records to Digital Product Memory passport fields.",
        "product_types": supported_product_types(),
        "data_categories": [
            "identification",
            "technical",
            "sustainability",
            "compliance",
            "economic",
        ],
        "conditions": {
            "requires_auth": False,
            "identifier_pattern": "^[0-9]+$",
            "contract": "GET /products/{eprel_registration_number_or_model_identifier}",
            "upstream": "https://eprel.ec.europa.eu/api/product/{id}",
            "lookup": "Numeric values are treated as EPREL registration numbers; other values are searched as model identifiers.",
            "supported_eprel_product_groups": supported_product_groups(),
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "eprel-provider"}


@app.get("/.well-known/circthread-service")
async def well_known_metadata():
    return service_metadata()


@app.get("/metadata")
async def metadata():
    return service_metadata()


@app.get("/products")
async def list_products():
    """List a small resolver catalog of known EPREL examples."""
    products = await list_seed_products()
    return {"count": len(products), "products": products}


@app.get("/products/{product_id}")
async def get_product_data(product_id: str, raw: bool = Query(default=False)):
    """Return a passport fragment for an EPREL registration number or model identifier."""
    try:
        product = await fetch_eprel_product_by_identifier(product_id)
    except EprelNotFoundError:
        raise HTTPException(status_code=404, detail=f"EPREL product '{product_id}' not found") from None
    except EprelUpstreamError as exc:
        raise HTTPException(status_code=502, detail=f"EPREL upstream error: {exc}") from exc

    if raw:
        return product
    return to_passport(product)


@app.get("/products/{product_id}/summary")
async def get_product_summary(product_id: str):
    try:
        passport = to_passport(await fetch_eprel_product_by_identifier(product_id))
    except EprelNotFoundError:
        raise HTTPException(status_code=404, detail=f"EPREL product '{product_id}' not found") from None
    except EprelUpstreamError as exc:
        raise HTTPException(status_code=502, detail=f"EPREL upstream error: {exc}") from exc
    return to_catalog_item(passport)
