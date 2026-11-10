"""Client and mapping helpers for the public EPREL product API."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import httpx


EPREL_API_BASE_URL = os.getenv("EPREL_API_BASE_URL", "https://eprel.ec.europa.eu/api")
EPREL_LANGUAGE = os.getenv("EPREL_LANGUAGE", "EN")
TIMEOUT = httpx.Timeout(15.0, connect=5.0)

PRODUCT_GROUP_TO_TYPE = {
    "dishwashers2019": "dishwasher",
    "washingmachines2019": "washing_machine",
    "washerdriers2019": "washing_machine",
}

PRODUCT_TYPE_TO_GROUPS = {
    "dishwasher": ["dishwashers2019"],
    "washing_machine": ["washingmachines2019"],
}

SEED_PRODUCT_IDS = [
    "2613426",
    "2219971",
]


class EprelNotFoundError(Exception):
    """Raised when EPREL has no public product for the requested registration."""


class EprelUpstreamError(Exception):
    """Raised when EPREL cannot be reached or returns an unexpected response."""


def supported_product_types() -> list[str]:
    return sorted(PRODUCT_TYPE_TO_GROUPS)


def supported_product_groups() -> list[str]:
    return sorted(PRODUCT_GROUP_TO_TYPE)


async def fetch_eprel_product(product_id: str) -> dict[str, Any]:
    """Fetch a product by EPREL registration number."""
    url = f"{EPREL_API_BASE_URL.rstrip('/')}/product/{product_id}"
    params = {"language": EPREL_LANGUAGE}
    headers = {"Accept": "application/json"}

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        try:
            response = await client.get(url, params=params, headers=headers)
        except httpx.HTTPError as exc:
            raise EprelUpstreamError(str(exc)) from exc

    if response.status_code == 404:
        raise EprelNotFoundError(product_id)
    if response.status_code >= 400:
        raise EprelUpstreamError(f"EPREL returned HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise EprelUpstreamError("EPREL returned non-JSON product data") from exc

    if not isinstance(payload, dict) or not payload.get("eprelRegistrationNumber"):
        raise EprelNotFoundError(product_id)
    return payload


async def fetch_eprel_product_by_identifier(identifier: str) -> dict[str, Any]:
    """Fetch a product by EPREL registration number or model identifier."""
    normalized = identifier.strip()
    if not normalized:
        raise EprelNotFoundError(identifier)

    if normalized.isdigit():
        return await fetch_eprel_product(normalized)

    product_id = await find_eprel_registration_by_model_identifier(normalized)
    return await fetch_eprel_product(product_id)


# Cache of model-identifier lookups: {identifier: (timestamp, registration number or None)}.
# Negative results are cached as well, so that repeated requests for identifiers that EPREL
# does not know do not trigger new upstream searches.
_MODEL_LOOKUP_CACHE: dict[str, tuple[float, str | None]] = {}
MODEL_LOOKUP_TTL_SECONDS = float(os.getenv("EPREL_MODEL_LOOKUP_TTL_SECONDS", "3600"))


async def find_eprel_registration_by_model_identifier(model_identifier: str) -> str:
    """Resolve an EPREL model identifier to a public registration number.

    The supported product groups are searched in parallel; results are cached.
    """
    normalized = model_identifier.strip()
    if not normalized:
        raise EprelNotFoundError(model_identifier)

    cached = _MODEL_LOOKUP_CACHE.get(normalized)
    if cached and time.monotonic() - cached[0] < MODEL_LOOKUP_TTL_SECONDS:
        if cached[1] is None:
            raise EprelNotFoundError(model_identifier)
        return cached[1]

    groups = supported_product_groups()
    results = await asyncio.gather(
        *(_search_products_by_model_identifier(group, normalized) for group in groups),
        return_exceptions=True,
    )
    upstream_errors = [r for r in results if isinstance(r, Exception)]
    for products in results:
        if isinstance(products, Exception):
            continue
        product_id = _registration_number(_best_model_identifier_match(products, normalized))
        if product_id:
            _MODEL_LOOKUP_CACHE[normalized] = (time.monotonic(), product_id)
            return product_id

    if upstream_errors and len(upstream_errors) == len(results):
        raise upstream_errors[0]
    _MODEL_LOOKUP_CACHE[normalized] = (time.monotonic(), None)
    raise EprelNotFoundError(model_identifier)


async def list_seed_products() -> list[dict[str, Any]]:
    """Return a small catalog of known EPREL records for resolver discovery."""
    products = []
    for product_id in SEED_PRODUCT_IDS:
        try:
            products.append(to_catalog_item(to_passport(await fetch_eprel_product(product_id))))
        except (EprelNotFoundError, EprelUpstreamError):
            products.append(_fallback_catalog_item(product_id))
    return products


def to_passport(raw: dict[str, Any]) -> dict[str, Any]:
    """Map EPREL's unstable field names to Digital Product Memory passport fields."""
    product_id = str(raw.get("eprelRegistrationNumber") or "")
    product_group = str(raw.get("productGroup") or "")
    product_type = PRODUCT_GROUP_TO_TYPE.get(product_group, product_group or "unknown")
    manufacturer = _first_text(
        raw.get("supplierOrTrademark"),
        raw.get("trademarkOwner"),
        _nested(raw, "organisation", "organisationName"),
        _nested(raw, "organisation", "organisationTitle"),
    )
    model = _first_text(raw.get("modelIdentifier"), product_id)

    dimensions = _dimensions(raw)
    energy_label = {
        "class": raw.get("energyClass"),
        "range": raw.get("energyClassRange"),
        "image": _asset_url(raw.get("energyClassImage")),
        "image_with_scale": _asset_url(raw.get("energyClassImageWithScale")),
        "product_information_sheet_url": _document_url(product_id, "fiches"),
        "energy_label_url": _document_url(product_id, "labels"),
        "qr_url": f"https://eprel.ec.europa.eu/qr/{product_id}" if product_id else None,
    }

    passport = {
        "product_id": product_id,
        "product_type": product_type,
        "manufacturer": manufacturer,
        "model": model,
        "energy_label": _drop_empty(energy_label),
        "energy_class": raw.get("energyClass"),
        "energy_class_range": raw.get("energyClassRange"),
        "supplier": _drop_empty({
            "name": _nested(raw, "organisation", "organisationName"),
            "website": _nested(raw, "organisation", "website"),
            "registrant_nature": raw.get("registrantNature"),
            "verification_status": raw.get("orgVerificationStatus"),
        }),
        "supplier_contact": _drop_empty({
            "service_name": _nested(raw, "contactDetails", "serviceName"),
            "email": _nested(raw, "contactDetails", "email"),
            "phone": _nested(raw, "contactDetails", "phone"),
            "website": _nested(raw, "contactDetails", "webSiteURL"),
            "country": _nested(raw, "contactDetails", "country"),
            "postal_code": _nested(raw, "contactDetails", "postalCode"),
            "city": _nested(raw, "contactDetails", "city"),
            "street": _join_address(raw.get("contactDetails")),
        }),
        "specifications": _drop_empty({
            "type": raw.get("type"),
            "rated_capacity": raw.get("ratedCapacity"),
            "dimensions": dimensions,
            "noise_db": raw.get("noise"),
            "noise_class": raw.get("noiseClass"),
            "water_consumption_l": raw.get("waterCons"),
            "programme_duration_min": _programme_duration(raw),
            "energy_consumption": _energy_consumption(raw),
            "power_standby_w": raw.get("powerStandbyMode"),
            "power_off_w": raw.get("powerOffMode"),
            "power_delay_start_w": raw.get("powerDelayStart"),
            "power_network_standby_w": raw.get("powerNetworkStandby"),
        }),
        "dimensions": dimensions,
        "water_consumption_l": raw.get("waterCons"),
        "noise_db": raw.get("noise"),
        "noise_class": raw.get("noiseClass"),
        "rated_capacity": raw.get("ratedCapacity"),
        "warranty_years": _months_to_years(raw.get("guaranteeDuration")),
        "compliance": _drop_empty({
            "eprel_registration_number": product_id,
            "eprel_version_number": raw.get("versionNumber"),
            "status": raw.get("status"),
            "implementing_act": raw.get("implementingAct"),
            "product_group": product_group,
            "product_model_core_id": raw.get("productModelCoreId"),
            "version_id": raw.get("versionId"),
        }),
        "market": _drop_empty({
            "availability": raw.get("availabilityInEUEEACountries"),
            "on_market_start_date": _date(raw.get("onMarketStartDate")),
            "on_market_end_date": _date(raw.get("onMarketEndDate")),
            "first_publication_date": _date(raw.get("firstPublicationDate")),
            "published_on_date": _date(raw.get("publishedOnDate")),
        }),
        "external_links": _drop_empty({
            "eprel_product_page": (
                f"https://eprel.ec.europa.eu/screen/product/{product_group}/{product_id}"
                if product_group and product_id else None
            ),
            "eprel_api": f"{EPREL_API_BASE_URL.rstrip('/')}/product/{product_id}",
            "supplier_energy_label_page": raw.get("webLinkSupplier"),
        }),
        "eprel": raw,
    }

    if product_type == "washing_machine":
        passport["specifications"]["spin_class"] = raw.get("spinClass")
        passport["specifications"]["spin_speed_rpm"] = raw.get("spinSpeedRated")
        passport["specifications"]["rinsing_effectiveness"] = raw.get("rinsingEffectiveness")
        passport["specifications"]["moisture_pct"] = raw.get("moisture")
        passport["washing_efficiency_index"] = raw.get("washingEfficiencyIndexV2") or raw.get("washingEfficiencyIndex")

    if product_type == "dishwasher":
        passport["specifications"]["cleaning_performance_index"] = (
            raw.get("cleaningPerformanceIndexV2") or raw.get("cleaningPerformanceIndex")
        )
        passport["specifications"]["drying_performance_index"] = (
            raw.get("dryingPerformanceIndexV2") or raw.get("dryingPerformanceIndex")
        )

    return _drop_empty(passport)


def to_catalog_item(passport: dict[str, Any]) -> dict[str, Any]:
    return {
        "product_id": passport.get("product_id"),
        "product_type": passport.get("product_type", "unknown"),
        "manufacturer": passport.get("manufacturer", ""),
        "model": passport.get("model", ""),
        "energy_label": passport.get("energy_class") or passport.get("energy_label", {}).get("class"),
    }


def _fallback_catalog_item(product_id: str) -> dict[str, Any]:
    product_type = "dishwasher" if product_id == "2613426" else "washing_machine"
    return {
        "product_id": product_id,
        "product_type": product_type,
        "manufacturer": "",
        "model": "",
    }


async def _search_products_by_model_identifier(product_group: str, model_identifier: str) -> list[dict[str, Any]]:
    url = f"{EPREL_API_BASE_URL.rstrip('/')}/products/{product_group}"
    params = {
        "_page": 1,
        "_limit": 25,
        "modelIdentifier": model_identifier,
        "includeOldProducts": "false",
        "language": EPREL_LANGUAGE,
    }
    headers = {
        "Accept": "application/json",
        "Referer": f"https://eprel.ec.europa.eu/screen/product/{product_group}",
    }

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        try:
            response = await client.get(url, params=params, headers=headers)
        except httpx.HTTPError as exc:
            raise EprelUpstreamError(str(exc)) from exc

    if response.status_code == 404:
        return []
    if response.status_code >= 400:
        raise EprelUpstreamError(f"EPREL returned HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise EprelUpstreamError("EPREL returned non-JSON product search data") from exc

    return _extract_product_search_items(payload)


def _extract_product_search_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ("products", "results", "items", "content", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    hits = payload.get("hits")
    if isinstance(hits, dict):
        hit_items = hits.get("hits")
        if isinstance(hit_items, list):
            return [
                item.get("_source", item)
                for item in hit_items
                if isinstance(item, dict) and isinstance(item.get("_source", item), dict)
            ]
    if isinstance(hits, list):
        return [item for item in hits if isinstance(item, dict)]

    return []


def _best_model_identifier_match(products: list[dict[str, Any]], model_identifier: str) -> dict[str, Any] | None:
    normalized = _normalize_identifier(model_identifier)
    for product in products:
        if _normalize_identifier(product.get("modelIdentifier")) == normalized:
            return product
    for product in products:
        if _normalize_identifier(product.get("modelIdentifier")).startswith(normalized):
            return product
    return products[0] if products else None


def _registration_number(product: dict[str, Any] | None) -> str | None:
    if not isinstance(product, dict):
        return None
    for key in ("eprelRegistrationNumber", "registrationNumber", "productId", "id"):
        value = product.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _normalize_identifier(value: Any) -> str:
    if value is None:
        return ""
    return "".join(str(value).upper().split())


def _first_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _drop_empty(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value not in (None, "", [], {})}


def _date(value: Any) -> str | None:
    if not isinstance(value, list) or len(value) < 3:
        return None
    try:
        return f"{int(value[0]):04d}-{int(value[1]):02d}-{int(value[2]):02d}"
    except (TypeError, ValueError):
        return None


def _dimensions(raw: dict[str, Any]) -> dict[str, Any]:
    return _drop_empty({
        "height_cm": raw.get("dimensionHeight"),
        "width_cm": raw.get("dimensionWidth"),
        "depth_cm": raw.get("dimensionDepth"),
    })


def _programme_duration(raw: dict[str, Any]) -> int | None:
    for key in ("programmeDuration", "programmeDurationRated", "programmeDurationHalf", "programmeDurationQuarter"):
        value = raw.get(key)
        if isinstance(value, int):
            return value
    return None


def _energy_consumption(raw: dict[str, Any]) -> dict[str, Any]:
    return _drop_empty({
        "kwh_per_100_cycles": raw.get("energyCons100") or raw.get("energyConsPer100Cycle"),
        "kwh_per_cycle": raw.get("energyCons") or raw.get("energyConsPerCycle"),
        "energy_efficiency_index": raw.get("energyEfficiencyIndex"),
    })


def _months_to_years(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    return round(value / 12, 2)


def _document_url(product_id: str, document_type: str) -> str | None:
    if not product_id:
        return None
    return f"{EPREL_API_BASE_URL.rstrip('/')}/product/{product_id}/{document_type}?language={EPREL_LANGUAGE}"


def _asset_url(filename: Any) -> str | None:
    if not isinstance(filename, str) or not filename:
        return None
    if filename.startswith("http"):
        return filename
    return f"https://eprel.ec.europa.eu/label/{filename}"


def _join_address(contact: Any) -> str | None:
    if not isinstance(contact, dict):
        return None
    parts = [
        contact.get("street"),
        contact.get("streetNumber"),
        contact.get("postalCode"),
        contact.get("city"),
    ]
    return " ".join(str(part).strip() for part in parts if part)
