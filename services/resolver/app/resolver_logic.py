"""Core resolution logic – orchestrates provider selection, data retrieval, and recommendation.

Resolution pipeline (see README, "Request Processing Pipeline"):

1. Determine the product type (explicit parameter or lookup in the provider catalogue).
2. Ask the Recommendation Engine which DPP fields are relevant for the role and event.
3. Ask the Service Registry which providers can contribute these fields for this product
   (closed catalogues, identifier patterns, product types, data fields / categories).
4. Query only the selected providers, in parallel.
5. Merge the JSON fragments in registry order, record the providers of every value, and
   report conflicting values.
6. Let the Recommendation Engine filter the aggregated product data object.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from shared.config import settings

logger = logging.getLogger(__name__)

# Timeouts for inter-service calls
TIMEOUT = httpx.Timeout(10.0, connect=5.0)

EMPTY_VALUES = (None, [], {}, "")

# Product catalogue cache: product_id -> product_type, refreshed after CATALOGUE_TTL_SECONDS.
CATALOGUE_TTL_SECONDS = 60.0
_catalogue_cache: dict[str, Any] = {"timestamp": 0.0, "product_types": {}}


def _is_empty(value: Any) -> bool:
    return value in EMPTY_VALUES


# ─── Service Registry ──────────────────────────────────────────────────────────

async def list_registered_services() -> list[dict]:
    """Return all registered service endpoints (empty list if the registry is unreachable)."""
    url = f"{settings.SERVICE_REGISTRY_URL}/services"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error("Service Registry unreachable: %s", e)
            return []


async def discover_endpoints(product_type: str) -> list[dict]:
    """Query the Service Registry for endpoints that serve this product type."""
    url = f"{settings.SERVICE_REGISTRY_URL}/services/by-product-type/{product_type}"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error("Service Registry unreachable: %s", e)
            return []


async def select_providers(
    product_id: str,
    product_type: str | None,
    data_fields: list[str] | None = None,
    data_categories: list[str] | None = None,
) -> dict:
    """
    Ask the Service Registry which providers are needed for this request.

    Returns {"selected": [...], "excluded": [...], "category_filter_applied": bool}.
    Falls back to all registered providers (or the mock provider) if the registry cannot
    perform the selection.
    """
    url = f"{settings.SERVICE_REGISTRY_URL}/services/select"
    payload = {
        "product_id": product_id,
        "product_type": product_type,
        "data_fields": data_fields or [],
        "data_categories": data_categories or [],
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            selection = resp.json()
            if selection.get("selected"):
                return selection
        except httpx.HTTPError as e:
            logger.error("Provider selection failed, falling back to all providers: %s", e)

    endpoints = await (discover_endpoints(product_type) if product_type else list_registered_services())
    if not endpoints:
        logger.warning("No endpoints found for product_type=%s", product_type)
        endpoints = [{"base_url": settings.MOCK_PROVIDER_URL, "name": "fallback-mock"}]
    return {"selected": endpoints, "excluded": [], "category_filter_applied": False}


# ─── Providers ─────────────────────────────────────────────────────────────────

class ProviderUnavailableError(Exception):
    """A provider could not be reached or failed with a server error (5xx)."""


async def fetch_product_data(base_url: str, product_id: str) -> dict | None:
    """
    Fetch product data from a single provider endpoint.

    Returns None if the provider answers with a client error (e.g. 404 because it does not
    know the product): this is information, not a failure. Raises ProviderUnavailableError
    for network errors, timeouts, server errors and invalid responses.
    """
    url = f"{base_url}/products/{product_id}"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(url)
        except httpx.HTTPError as e:
            logger.error("Provider %s unreachable: %s", base_url, e)
            raise ProviderUnavailableError(f"unreachable: {type(e).__name__}") from e
    if resp.status_code >= 500:
        logger.error("Provider %s failed with HTTP %s for %s", base_url, resp.status_code, product_id)
        raise ProviderUnavailableError(f"HTTP {resp.status_code}")
    if resp.status_code >= 400:
        logger.info("Product %s not available at %s (HTTP %s)", product_id, base_url, resp.status_code)
        return None
    try:
        payload = resp.json()
    except ValueError as e:
        logger.error("Provider %s returned invalid JSON: %s", base_url, e)
        raise ProviderUnavailableError("invalid JSON response") from e
    return payload if isinstance(payload, dict) else None


async def fetch_product_list(base_url: str) -> list[dict]:
    """Fetch lightweight product list from a provider endpoint."""
    url = f"{base_url}/products"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError as e:
            logger.error("Failed to list products from %s: %s", base_url, e)
            return []

    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("products"), list):
        return [p for p in payload["products"] if isinstance(p, dict)]
    return []


async def list_available_products() -> dict:
    """List products from all registered providers (queried in parallel) and merge by product ID."""
    url = f"{settings.SERVICE_REGISTRY_URL}/services"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            endpoints = resp.json()
        except httpx.HTTPError:
            endpoints = [{"base_url": settings.MOCK_PROVIDER_URL, "name": "fallback-mock"}]

    product_lists = await asyncio.gather(
        *(fetch_product_list(endpoint.get("base_url", "")) for endpoint in endpoints)
    )

    products_by_id: dict[str, dict] = {}
    for endpoint, product_list in zip(endpoints, product_lists):
        provider_name = endpoint.get("name", endpoint.get("base_url", ""))
        for product in product_list:
            product_id = product.get("product_id")
            if not product_id:
                continue
            existing = products_by_id.setdefault(
                product_id,
                {
                    "product_id": product_id,
                    "product_type": product.get("product_type", "unknown"),
                    "manufacturer": product.get("manufacturer", ""),
                    "model": product.get("model", ""),
                    "sources": [],
                },
            )
            for key in ("product_type", "manufacturer", "model"):
                if product.get(key):
                    existing[key] = product[key]
            if provider_name not in existing["sources"]:
                existing["sources"].append(provider_name)

    products = sorted(products_by_id.values(), key=lambda p: p["product_id"])
    _catalogue_cache["product_types"] = {p["product_id"]: p["product_type"] for p in products}
    _catalogue_cache["timestamp"] = time.monotonic()
    return {"count": len(products), "products": products}


async def lookup_product_type(product_id: str) -> str | None:
    """Look up the product type of a known product in the (cached) provider catalogue."""
    if time.monotonic() - _catalogue_cache["timestamp"] > CATALOGUE_TTL_SECONDS:
        await list_available_products()
    product_type = _catalogue_cache["product_types"].get(product_id)
    return product_type if product_type and product_type != "unknown" else None


def merge_provider_data(results: list[tuple[dict, dict | None]]) -> dict:
    """
    Merge provider responses (in registry order) into one product data object.

    Internal fields (prefix "_") are ignored and empty values never overwrite non-empty
    ones. If several providers deliver different non-empty values for the same field, the
    value of the provider listed last in the registry is kept and the conflict is reported
    in "_conflicts". Every provider that delivered a non-empty value is recorded in
    "_field_sources".
    """
    aggregated: dict[str, Any] = {}
    field_sources: dict[str, list[str]] = {}
    contributions: dict[str, list[tuple[str, Any]]] = {}
    sources: list[str] = []

    for endpoint, data in results:
        if not data:
            continue
        provider_name = endpoint.get("name", endpoint.get("base_url", ""))
        for key, value in data.items():
            if key.startswith("_") or key == "data_sources":
                continue
            if _is_empty(value):
                aggregated.setdefault(key, value)
                continue
            aggregated[key] = value
            contributions.setdefault(key, []).append((provider_name, value))
            if provider_name not in field_sources.setdefault(key, []):
                field_sources[key].append(provider_name)
        sources.append(provider_name)

    conflicts = {}
    for key, values in contributions.items():
        distinct = []
        for _provider, value in values:
            if value not in distinct:
                distinct.append(value)
        if len(distinct) > 1:
            conflicts[key] = [{"provider": provider, "value": value} for provider, value in values]

    aggregated["data_sources"] = sources
    field_sources["data_sources"] = sources
    aggregated["_field_sources"] = field_sources
    aggregated["_conflicts"] = conflicts
    return aggregated


async def _query_providers(endpoints: list[dict], product_id: str) -> tuple[list[dict | None], list[dict[str, str]]]:
    """Query providers in parallel. A failing provider never aborts the resolution: its data
    is simply missing, and the failure is logged and reported in the provider selection."""
    outcomes = await asyncio.gather(
        *(fetch_product_data(endpoint.get("base_url", ""), product_id) for endpoint in endpoints),
        return_exceptions=True,
    )
    responses: list[dict | None] = []
    unavailable: list[dict[str, str]] = []
    for endpoint, outcome in zip(endpoints, outcomes):
        if isinstance(outcome, BaseException):
            if not isinstance(outcome, ProviderUnavailableError):
                logger.error("Unexpected error while querying %s: %s", endpoint.get("base_url"), outcome)
            unavailable.append({
                "name": endpoint.get("name", endpoint.get("base_url", "")),
                "reason": str(outcome) or type(outcome).__name__,
            })
            responses.append(None)
        else:
            responses.append(outcome)
    return responses, unavailable


def _canonical_identifier(product_id: str, responses: list[dict | None]) -> str | None:
    """Identifier under which a provider returned the product, if it differs from the request.

    E.g. the EPREL provider resolves the model identifier SN43HW04ME to the registration
    number 2613426, under which other providers hold data for the same product.
    """
    for response in responses:
        canonical = str((response or {}).get("product_id") or "")
        if canonical and canonical != product_id:
            return canonical
    return None


async def aggregate_product_data(
    product_id: str,
    product_type: str | None = None,
    data_fields: list[str] | None = None,
    data_categories: list[str] | None = None,
) -> dict:
    """
    Select the relevant providers, query them in parallel, and aggregate the product data.

    Without data_fields/data_categories (raw view, custom builds without terms), all
    providers that may know the product are queried. If a provider resolves the requested
    identifier to another identifier (alias such as an EPREL model identifier), the
    providers that know the resolved identifier are queried as well.
    """
    selection = await select_providers(product_id, product_type, data_fields, data_categories)
    endpoints = selection.get("selected", [])

    started = time.perf_counter()
    responses, unavailable = await _query_providers(endpoints, product_id)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    excluded = selection.get("excluded", [])
    filter_applied = selection.get("category_filter_applied", False)

    resolved_identifier = _canonical_identifier(product_id, responses)
    if resolved_identifier:
        follow_up = await select_providers(resolved_identifier, product_type, data_fields, data_categories)
        queried_urls = {endpoint.get("base_url") for endpoint in endpoints}
        extra = [e for e in follow_up.get("selected", []) if e.get("base_url") not in queried_urls]
        started = time.perf_counter()
        extra_responses, extra_unavailable = await _query_providers(extra, resolved_identifier)
        elapsed_ms = round(elapsed_ms + (time.perf_counter() - started) * 1000, 1)
        # Merge in the registry order of the follow-up selection ("last wins"); providers
        # that only matched the original identifier come first.
        by_url = {e.get("base_url"): (e, r) for e, r in zip(endpoints + extra, responses + extra_responses)}
        follow_up_urls = [e.get("base_url") for e in follow_up.get("selected", [])]
        ordered = [url for url in by_url if url not in follow_up_urls] + [u for u in follow_up_urls if u in by_url]
        endpoints = [by_url[url][0] for url in ordered]
        responses = [by_url[url][1] for url in ordered]
        unavailable += extra_unavailable
        queried_names = {endpoint.get("name") for endpoint in endpoints}
        excluded = [e for e in follow_up.get("excluded", []) if e.get("name") not in queried_names]
        filter_applied = filter_applied or follow_up.get("category_filter_applied", False)

    aggregated = merge_provider_data(list(zip(endpoints, responses)))
    queried = [endpoint.get("name", endpoint.get("base_url", "")) for endpoint in endpoints]
    unavailable_names = {entry["name"] for entry in unavailable}
    aggregated["_provider_selection"] = {
        "queried": queried,
        "responded": aggregated["data_sources"],
        "no_data": [name for name in queried
                    if name not in aggregated["data_sources"] and name not in unavailable_names],
        "unavailable": unavailable,
        "excluded": excluded,
        "category_filter_applied": filter_applied,
        "provider_requests_ms": elapsed_ms,
    }
    if resolved_identifier:
        aggregated["_provider_selection"]["resolved_identifier"] = resolved_identifier
    return aggregated


# ─── Recommendation Engine ─────────────────────────────────────────────────────

async def get_recommendation_plan(product_type: str, role: str | None, event: str | None) -> dict | None:
    """Ask the Recommendation Engine which fields are relevant for this context."""
    url = f"{settings.RECOMMENDATION_ENGINE_URL}/recommend/fields"
    payload = {"product_type": product_type, "role": role, "event": event}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error("Recommendation plan unavailable, querying all candidate providers: %s", e)
            return None


async def get_recommendation(
    product_data: dict[str, Any],
    product_type: str,
    role: str | None,
    event: str | None,
) -> dict | None:
    """Send product data to the Recommendation Engine for filtering."""
    url = f"{settings.RECOMMENDATION_ENGINE_URL}/recommend"
    payload = {
        "product_data": product_data,
        "product_type": product_type,
        "role": role,
        "event": event,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error("Recommendation Engine error: %s", e)
            return None


class TemplateValidationError(ValueError):
    """The Recommendation Engine rejected a DPP template (HTTP 4xx)."""


async def save_dpp_template(
    template_name: str,
    terms: list[str],
    role: str | None,
    event: str | None,
    product_type: str | None,
    user_id: str = "anonymous",
    custom_event: str | None = None,
    lifecycle_phase: str | None = None,
) -> dict | None:
    """
    Store a custom DPP template in the recommendation engine.

    Raises TemplateValidationError if the template is rejected (e.g. a lifecycle phase that
    contradicts the event); returns None if the Recommendation Engine is unreachable.
    """
    url = f"{settings.RECOMMENDATION_ENGINE_URL}/templates"
    payload = {
        "template_name": template_name,
        "terms": terms,
        "role": _clean_context_value(role),
        "event": _clean_context_value(event),
        "custom_event": _clean_context_value(custom_event),
        "lifecycle_phase": _clean_context_value(lifecycle_phase),
        "product_type": product_type,
        "user_id": user_id,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(url, json=payload)
        except httpx.HTTPError as e:
            logger.error("Failed to save DPP template: %s", e)
            return None
    if 400 <= resp.status_code < 500:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        raise TemplateValidationError(str(detail))
    if resp.status_code >= 500:
        logger.error("Failed to save DPP template: HTTP %s", resp.status_code)
        return None
    return resp.json()


# ─── Public operations ─────────────────────────────────────────────────────────

async def build_custom_dpp(
    product_id: str,
    terms: list[str],
    template_name: str = "Custom DPP Template",
    role: str | None = None,
    event: str | None = None,
    product_type: str | None = None,
    save_template: bool = True,
    user_id: str = "anonymous",
    custom_event: str | None = None,
    lifecycle_phase: str | None = None,
) -> dict:
    """Resolve selected vocabulary terms for a product and optionally store the template."""
    normalized_terms = sorted({term for term in terms if term})
    known_type = product_type or await lookup_product_type(product_id)
    raw_data = await aggregate_product_data(product_id, known_type, data_fields=normalized_terms or None)
    if not raw_data or raw_data.get("product_id") is None:
        return {
            "product_id": product_id,
            "error": "Product not found in any registered data source",
            "sources": [],
            "selected_fields": [],
        }

    actual_product_type = known_type or raw_data.get("product_type", "unknown")
    field_sources = raw_data.get("_field_sources", {})
    if not isinstance(field_sources, dict):
        field_sources = {}

    selected_fields = []
    filtered_data = {}
    for term in normalized_terms:
        value = raw_data.get(term)
        available = not _is_empty(value)
        if available:
            filtered_data[term] = value
        selected_fields.append({
            "field_name": term,
            "value": value if available else None,
            "available": available,
            "sources": field_sources.get(term, []) if available else [],
        })

    template = None
    if save_template:
        template = await save_dpp_template(
            template_name=template_name,
            terms=normalized_terms,
            role=role,
            event=event,
            product_type=actual_product_type,
            user_id=user_id,
            custom_event=custom_event,
            lifecycle_phase=lifecycle_phase,
        )

    return {
        "product_id": product_id,
        "product_type": actual_product_type,
        "template_name": template_name,
        "role": role,
        "event": event,
        "custom_event": (template or {}).get("custom_event", _clean_context_value(custom_event)),
        "lifecycle_phase": (template or {}).get("lifecycle_phase", _clean_context_value(lifecycle_phase)),
        "selected_terms": normalized_terms,
        "selected_fields": selected_fields,
        "passport": filtered_data,
        "template": template,
        "sources": raw_data.get("data_sources", []),
        "provider_selection": raw_data.get("_provider_selection"),
    }


async def resolve_product(
    product_id: str,
    role: str | None,
    event: str | None,
    product_type: str | None = None,
) -> dict:
    """
    Full resolution pipeline:
    1. Determine the product type and the fields relevant for role and event
    2. Select and query only the providers that can contribute these fields (in parallel)
    3. Aggregate the provider responses
    4. Filter the aggregated data through the Knowledge Graph recommendation
    """
    selected_role = _clean_context_value(role)
    selected_event = _clean_context_value(event)
    known_type = _clean_context_value(product_type) or await lookup_product_type(product_id)

    plan = None
    if known_type and (selected_role or selected_event):
        plan = await get_recommendation_plan(known_type, selected_role, selected_event)
    plan_fields = [f["field_name"] for f in plan.get("fields", [])] if plan else None
    plan_categories = sorted({f["category"] for f in plan.get("fields", [])}) if plan else None

    raw_data = await aggregate_product_data(product_id, known_type, plan_fields, plan_categories)

    if not raw_data or raw_data.get("product_id") is None:
        selection = (raw_data or {}).get("_provider_selection") or {}
        unavailable = selection.get("unavailable") or []
        if unavailable:
            # Not a missing product: the providers that hold relevant data could not be reached.
            error = "Product data currently unavailable: the providers holding relevant data could not be reached"
            error_reason = "providers_unavailable"
        else:
            error = "Product not found in any registered data source"
            error_reason = "not_found"
        return {
            "product_id": product_id,
            "product_type": known_type,
            "role": selected_role,
            "event": selected_event,
            "error": error,
            "error_reason": error_reason,
            "sources": [],
            "provider_selection": selection or None,
        }

    actual_product_type = known_type or raw_data.get("product_type", "unknown")
    recommendation = await get_recommendation(raw_data, actual_product_type, selected_role, selected_event)

    return {
        "product_id": product_id,
        "product_type": actual_product_type,
        "role": selected_role,
        "event": selected_event,
        "passport": recommendation.get("filtered_data", raw_data) if recommendation else raw_data,
        "recommendation": recommendation,
        "sources": raw_data.get("data_sources", []),
        "provider_selection": raw_data.get("_provider_selection"),
        "conflicts": raw_data.get("_conflicts", {}),
        "raw_data_available": True,
    }


def _clean_context_value(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
