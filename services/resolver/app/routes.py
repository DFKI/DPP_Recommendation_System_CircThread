"""Resolver Service – API routes."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.resolver_logic import (
    TemplateValidationError,
    resolve_product,
    aggregate_product_data,
    list_available_products,
    build_custom_dpp,
    save_dpp_template,
)

router = APIRouter(tags=["Resolver"])


class CustomDppRequest(BaseModel):
    product_id: str | None = None
    template_name: str = "Custom DPP Template"
    terms: list[str] = Field(default_factory=list)
    role: str | None = None
    event: str | None = None
    product_type: str | None = None
    custom_event: str | None = Field(default=None, description="Name of a self-defined event, e.g. 'Inverter inspection'")
    lifecycle_phase: str | None = Field(default=None, description="beginning_of_life, middle_of_life or end_of_life")
    save_template: bool = True
    user_id: str = Field(default="anonymous", description="Client identifier; stored only as a pseudonymous hash")


@router.get("/products")
async def list_products():
    """
    List products discovered through all registered providers.

    This is the frontend-facing product catalog. It is intentionally resolved
    through the Service Registry instead of only using the mock provider.
    """
    return await list_available_products()


@router.post("/custom-dpp")
async def custom_dpp(request: CustomDppRequest):
    """
    Build a custom DPP by resolving user-selected vocabulary terms.

    The selected terms are optionally stored as a dynamic DPP template in Neo4j.
    Values are not stored in Neo4j; they are resolved from registered providers.
    """
    try:
        if request.product_id:
            return await build_custom_dpp(
                product_id=request.product_id,
                terms=request.terms,
                template_name=request.template_name,
                role=request.role,
                event=request.event,
                product_type=request.product_type,
                save_template=request.save_template,
                user_id=request.user_id,
                custom_event=request.custom_event,
                lifecycle_phase=request.lifecycle_phase,
            )

        template = None
        if request.save_template:
            template = await save_dpp_template(
                template_name=request.template_name,
                terms=request.terms,
                role=request.role,
                event=request.event,
                product_type=request.product_type,
                user_id=request.user_id,
                custom_event=request.custom_event,
                lifecycle_phase=request.lifecycle_phase,
            )
    except TemplateValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "template_name": request.template_name,
        "role": request.role,
        "event": request.event,
        "custom_event": (template or {}).get("custom_event", request.custom_event),
        "lifecycle_phase": (template or {}).get("lifecycle_phase", request.lifecycle_phase),
        "product_type": request.product_type,
        "selected_terms": sorted({term for term in request.terms if term}),
        "selected_fields": [],
        "passport": {},
        "template": template,
        "sources": [],
        "message": "Template saved without resolving product values.",
    }


@router.get("/resolve/{product_id}")
async def resolve(
    product_id: str,
    role: str | None = Query(default=None, description="Stakeholder role, or omit for any role"),
    event: str | None = Query(default=None, description="Lifecycle event, or omit for any event"),
    product_type: str = Query(default=None, description="Optional product type filter"),
):
    """
    Resolve a Digital Product Passport for a given product.

    The resolver:
    1. Discovers data providers via the Service Registry
    2. Aggregates product data from all available providers
    3. Filters data through the Recommendation Engine (Knowledge Graph)
    4. Returns only the fields relevant for the specified role and event
    """
    result = await resolve_product(product_id, role, event, product_type)
    return result


@router.get("/resolve/{product_id}/raw")
async def resolve_raw(
    product_id: str,
    product_type: str = Query(default=None, description="Optional product type filter"),
):
    """
    Get raw, unfiltered product data from all available providers.
    No role-based filtering is applied.
    """
    raw_data = await aggregate_product_data(product_id, product_type)
    return {
        "product_id": product_id,
        "raw_data": raw_data,
        "sources": raw_data.get("data_sources", []),
    }
