"""Mid-of-life and purchase data provider."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.product_data import get_all_products, get_product
from shared.vocabulary import categories_for_products, fields_for_products


app = FastAPI(
    title="Digital Product Memory Midlife Purchase Provider",
    description="Provides purchase, use-phase, repairability, warranty, and maintenance data for selected products.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def metadata() -> dict:
    return {
        "name": "Midlife Purchase Provider",
        "provider": "Use Phase Data Hub",
        "description": "Provides purchase, energy label, repairability, maintenance, and warranty information.",
        "product_types": sorted({p["product_type"] for p in get_all_products()}),
        "product_ids": sorted(p["product_id"] for p in get_all_products()),
        "data_categories": categories_for_products(get_all_products()),
        "data_fields": fields_for_products(get_all_products()),
        "conditions": {
            "requires_auth": False,
            "lifecycle_focus": "mid_of_life_purchase",
            "contract": "GET /products/{product_id}",
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "midlife-purchase-provider"}


@app.get("/.well-known/circthread-service")
async def well_known_metadata():
    return metadata()


@app.get("/metadata")
async def service_metadata():
    return metadata()


@app.get("/products")
async def list_products():
    products = get_all_products()
    return {"count": len(products), "products": products}


@app.get("/products/{product_id}")
async def get_product_data(product_id: str):
    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return product
