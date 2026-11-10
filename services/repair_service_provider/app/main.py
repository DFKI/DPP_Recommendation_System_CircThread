"""Repair and service network data provider."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.product_data import get_all_products, get_product
from shared.vocabulary import categories_for_products, fields_for_products


app = FastAPI(
    title="Digital Product Memory Repair & Service Network Provider",
    description=(
        "Provides repair, fault, service-contract, and refurbishment data recorded by an "
        "independent network of repairers and service partners."
    ),
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
    products = get_all_products()
    return {
        "name": "Repair & Service Network Provider",
        "provider": "CircThread Repair & Service Network",
        "description": (
            "Repair records, fault codes, service intervals, service contracts, spare-part "
            "sourcing, and refurbishment grading reported by independent repairers and "
            "authorised service partners."
        ),
        "product_types": sorted({p["product_type"] for p in products}),
        "product_ids": sorted(p["product_id"] for p in products),
        "data_categories": categories_for_products(products),
        "data_fields": fields_for_products(products),
        "conditions": {
            "requires_auth": False,
            "lifecycle_focus": "middle_of_life_repair_service",
            "contract": "GET /products/{product_id}",
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "repair-service-provider"}


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
