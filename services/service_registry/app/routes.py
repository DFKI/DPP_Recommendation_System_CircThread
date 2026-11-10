"""Service Registry API routes."""

from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from shared.models import (
    ServiceEndpoint,
    ServiceEndpointCreate,
    ServiceEndpointUpdate,
    ServiceSelectionRequest,
    ServiceSelectionResponse,
    normalize_categories,
)


router = APIRouter(prefix="/services", tags=["Service Registry"])

TIMEOUT = httpx.Timeout(5.0, connect=2.0)
DISCOVERY_PATHS = [
    "/.well-known/circthread-service",
    "/metadata",
]

# Field-to-category assignment of the shared DPP vocabulary (identical to the DataCategory
# assignment seeded into the Knowledge Graph). Used to infer the categories of a discovered
# provider from its product list.
from shared.vocabulary import FIELD_CATEGORIES  # noqa: E402


class ServiceDiscoveryRequest(BaseModel):
    """Request body for discovering and optionally registering a provider."""

    base_url: str
    register: bool = Field(default=True)


class ServiceDiscoveryResponse(BaseModel):
    """Result of provider discovery."""

    discovered_from: str
    endpoint: ServiceEndpoint
    registered: bool
    warnings: list[str] = Field(default_factory=list)


def _get_store(request: Request):
    return request.app.state.store


def _normalize_base_url(base_url: str) -> str:
    parsed = urlsplit(base_url.strip().rstrip("/"))
    path = parsed.path.rstrip("/")
    for suffix in ("/docs", "/redoc", "/openapi.json", "/metadata", "/.well-known/circthread-service"):
        if path.endswith(suffix):
            path = path[: -len(suffix)].rstrip("/")
            break
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, str) and value:
        return [value]
    return []


def _infer_categories_from_product(product: dict[str, Any]) -> list[str]:
    categories = set()
    for key, value in product.items():
        category = FIELD_CATEGORIES.get(key)
        if category and value not in (None, [], {}, ""):
            categories.add(category)
    return sorted(categories)


def _extract_products(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if isinstance(payload, dict):
        products = payload.get("products")
        if isinstance(products, list):
            return [p for p in products if isinstance(p, dict)]
        if payload.get("product_id"):
            return [payload]
    return []


def _endpoint_from_metadata(base_url: str, metadata: dict[str, Any]) -> ServiceEndpointCreate:
    return ServiceEndpointCreate(
        name=metadata.get("name") or metadata.get("title") or "Discovered Digital Product Memory Provider",
        provider=metadata.get("provider") or metadata.get("organization") or "",
        description=metadata.get("description") or "",
        base_url=base_url,
        product_types=_as_list(metadata.get("product_types")),
        product_ids=_as_list(metadata.get("product_ids")),
        data_fields=_as_list(metadata.get("data_fields")),
        data_categories=normalize_categories(_as_list(metadata.get("data_categories"))),
        conditions=metadata.get("conditions") if isinstance(metadata.get("conditions"), dict) else {},
    )


async def _discover_metadata(client: httpx.AsyncClient, base_url: str) -> tuple[str, ServiceEndpointCreate] | None:
    for path in DISCOVERY_PATHS:
        try:
            response = await client.get(f"{base_url}{path}")
            if response.status_code == 404:
                continue
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return path, _endpoint_from_metadata(base_url, payload)
        except (httpx.HTTPError, ValueError):
            continue
    return None


async def _discover_openapi(client: httpx.AsyncClient, base_url: str) -> tuple[str, ServiceEndpointCreate] | None:
    try:
        response = await client.get(f"{base_url}/openapi.json")
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None

    info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
    product_types = _as_list(payload.get("x-circthread-product-types"))
    data_categories = _as_list(payload.get("x-circthread-data-categories"))
    paths = payload.get("paths") if isinstance(payload.get("paths"), dict) else {}

    conditions = {
        "requires_auth": False,
        "discovery": "openapi",
        "has_product_endpoint": any("/products/{product_id}" in path for path in paths),
    }

    endpoint = ServiceEndpointCreate(
        name=info.get("title") or "OpenAPI Provider",
        provider=info.get("x-provider", ""),
        description=info.get("description", ""),
        base_url=base_url,
        product_types=product_types,
        data_categories=normalize_categories(data_categories),
        conditions=conditions,
    )
    return "/openapi.json", endpoint


async def _infer_from_products(client: httpx.AsyncClient, base_url: str, endpoint: ServiceEndpointCreate) -> ServiceEndpointCreate:
    try:
        response = await client.get(f"{base_url}/products")
        response.raise_for_status()
        products = _extract_products(response.json())
    except (httpx.HTTPError, ValueError):
        return endpoint

    product_types = set(endpoint.product_types)
    data_categories = set(endpoint.data_categories)

    for product in products:
        if product.get("product_type"):
            product_types.add(str(product["product_type"]))
        data_categories.update(_infer_categories_from_product(product))

    return ServiceEndpointCreate(
        name=endpoint.name,
        provider=endpoint.provider,
        description=endpoint.description,
        base_url=endpoint.base_url,
        product_types=sorted(product_types),
        product_ids=endpoint.product_ids,
        data_fields=endpoint.data_fields,
        data_categories=normalize_categories(sorted(data_categories)),
        conditions=endpoint.conditions,
    )


@router.get("", response_model=list[ServiceEndpoint])
async def list_services(request: Request):
    """List all registered service endpoints."""
    store = _get_store(request)
    return store.list_all()


@router.post("/discover", response_model=ServiceDiscoveryResponse)
async def discover_service(discovery: ServiceDiscoveryRequest, request: Request):
    """
    Discover a provider from its base URL and optionally register it.

    Preferred providers expose `/.well-known/circthread-service` or `/metadata`.
    If no explicit metadata exists, the registry falls back to OpenAPI and
    `/products` to infer product types and data categories where possible.
    """
    base_url = _normalize_base_url(discovery.base_url)
    warnings: list[str] = []

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        discovered = await _discover_metadata(client, base_url)
        if discovered:
            discovered_from, endpoint_create = discovered
        else:
            discovered = await _discover_openapi(client, base_url)
            if discovered:
                discovered_from, endpoint_create = discovered
                warnings.append("No Digital Product Memory metadata endpoint found. Used OpenAPI fallback.")
            else:
                discovered_from = "fallback"
                endpoint_create = ServiceEndpointCreate(
                    name="Unknown Data Provider",
                    provider="",
                    description="Registered from base URL. Add /.well-known/circthread-service for richer metadata.",
                    base_url=base_url,
                    product_types=[],
                    data_categories=[],
                    conditions={"requires_auth": False, "discovery": "fallback"},
                )
                warnings.append("No metadata or OpenAPI document found. Registered minimal endpoint metadata.")

        endpoint_create = await _infer_from_products(client, base_url, endpoint_create)

    if not endpoint_create.product_types:
        warnings.append("No product types discovered. Add product_types to provider metadata.")
    if not endpoint_create.data_categories:
        warnings.append("No data categories discovered. Add data_categories to provider metadata or expose /products.")

    if discovery.register:
        store = _get_store(request)
        endpoint = store.create(endpoint_create)
        registered = True
    else:
        endpoint = ServiceEndpoint(id=None, status="active", **endpoint_create.model_dump())
        registered = False

    return ServiceDiscoveryResponse(
        discovered_from=discovered_from,
        endpoint=endpoint,
        registered=registered,
        warnings=warnings,
    )


@router.post("/select", response_model=ServiceSelectionResponse)
async def select_services(selection: ServiceSelectionRequest, request: Request):
    """
    Select the providers needed for a resolution request.

    The Resolver sends the product identifier, the product type (if known) and the data
    categories of the fields recommended for the current role and lifecycle event. Only
    providers that can contribute to this context are returned.
    """
    store = _get_store(request)
    return store.select(
        selection.product_id,
        selection.product_type,
        selection.data_categories,
        selection.data_fields,
    )


@router.get("/by-product-type/{product_type}", response_model=list[ServiceEndpoint])
async def get_services_by_product_type(product_type: str, request: Request):
    """Get active services that support a specific product type."""
    store = _get_store(request)
    return store.find_by_product_type(product_type)


@router.get("/by-category/{category}", response_model=list[ServiceEndpoint])
async def get_services_by_category(category: str, request: Request):
    """Get active services that provide a specific data category."""
    store = _get_store(request)
    return store.find_by_category(category)


@router.get("/{service_id}", response_model=ServiceEndpoint)
async def get_service(service_id: str, request: Request):
    """Get a single service endpoint by ID."""
    store = _get_store(request)
    service = store.get_by_id(service_id)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")
    return service


@router.post("", response_model=ServiceEndpoint, status_code=201)
async def register_service(endpoint: ServiceEndpointCreate, request: Request):
    """Register a new data provider service."""
    store = _get_store(request)
    return store.create(endpoint)


@router.put("/{service_id}", response_model=ServiceEndpoint)
async def update_service(service_id: str, update: ServiceEndpointUpdate, request: Request):
    """Update an existing service endpoint."""
    store = _get_store(request)
    service = store.update(service_id, update)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")
    return service


@router.delete("/{service_id}")
async def delete_service(service_id: str, request: Request):
    """Remove a service endpoint from the registry."""
    store = _get_store(request)
    deleted = store.delete(service_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")
    return {"message": f"Service '{service_id}' deleted"}
