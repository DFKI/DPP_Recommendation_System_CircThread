"""Mock Data Provider – FastAPI application."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.product_data import get_product, get_all_products, get_products_by_type, search_products
from shared.vocabulary import categories_for_products, fields_for_products


app = FastAPI(
    title="Digital Product Memory Mock Data Provider",
    description="Simulated product data provider for the DPP prototype.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "mock-data-provider"}


def metadata() -> dict:
    products = [get_product(p["product_id"]) for p in get_all_products()]
    return {
        "name": "Digital Product Memory Mock Data Provider",
        "provider": "CircThread Data Hub (DFKI GmbH)",
        "description": "Base product data for the CircThread prototype products. Fields held by specialised providers are delegated to them.",
        "product_types": sorted({p["product_type"] for p in products}),
        "product_ids": sorted(p["product_id"] for p in products),
        "data_categories": categories_for_products(products),
        "data_fields": fields_for_products(products),
        "conditions": {"requires_auth": False, "contract": "GET /products/{product_id}"},
    }


@app.get("/.well-known/circthread-service")
async def well_known_metadata():
    return metadata()


@app.get("/metadata")
async def service_metadata():
    return metadata()


@app.get("/products")
async def list_products():
    """List all available products."""
    products = get_all_products()
    return {
        "count": len(products),
        "products": [
            {
                "product_id": p["product_id"],
                "product_type": p["product_type"],
                "manufacturer": p["manufacturer"],
                "model": p["model"],
            }
            for p in products
        ]
    }


@app.get("/products/type/{product_type}")
async def list_products_by_type(product_type: str):
    """List products filtered by type."""
    products = get_products_by_type(product_type)
    return {"count": len(products), "products": products}


@app.get("/products/search")
async def search(q: str = ""):
    """Search products by text query."""
    results = search_products(q)
    return {"count": len(results), "products": results}


@app.get("/products/{product_id}")
async def get_product_data(product_id: str):
    """Get full product data by ID."""
    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return product


@app.get("/products/{product_id}/summary")
async def get_product_summary(product_id: str):
    """Get a brief product summary."""
    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return {
        "product_id": product["product_id"],
        "product_type": product["product_type"],
        "manufacturer": product["manufacturer"],
        "model": product["model"],
        "energy_label": product.get("energy_label"),
        "repairability_score": product.get("repairability_score"),
        "recyclability_pct": product.get("recyclability_pct"),
    }
