"""Digital Product Memory provider starterkit.

This service demonstrates the minimum contract expected by the Resolver and
the metadata endpoints used by the Service Registry auto-discovery flow.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.product_data import (
    get_all_products,
    get_data_categories,
    get_product,
    get_product_types,
)


app = FastAPI(
    title="Digital Product Memory Provider Starterkit",
    description="Example provider that contributes repair and maintenance data.",
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
        "name": "Starterkit Repair Provider",
        "provider": "Digital Product Memory Example",
        "description": "Example provider contributing repair history, maintenance schedule, and component data.",
        "product_types": get_product_types(),
        "data_categories": get_data_categories(),
        "conditions": {
            "requires_auth": False,
            "contract": "GET /products/{product_id}",
            "metadata": [
                "/.well-known/circthread-service",
                "/metadata",
                "/openapi.json",
            ],
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "provider-starterkit"}


@app.get("/.well-known/circthread-service")
async def well_known_metadata():
    return service_metadata()


@app.get("/metadata")
async def metadata():
    return service_metadata()


@app.get("/products")
async def list_products():
    products = get_all_products()
    return {
        "count": len(products),
        "products": [
            {
                "product_id": product["product_id"],
                "product_type": product["product_type"],
                "available_fields": sorted(product.keys()),
            }
            for product in products
        ],
    }


@app.get("/products/{product_id}")
async def get_product_data(product_id: str):
    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return product
