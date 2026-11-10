"""JSON-file-based storage for the Service Registry."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from threading import Lock
from typing import Optional

from shared.models import (
    IDENTITY_FIELDS,
    NON_SELECTIVE_CATEGORIES,
    ServiceEndpoint,
    ServiceEndpointCreate,
    ServiceEndpointUpdate,
    ServiceSelectionResponse,
    ServiceStatus,
    normalize_categories,
)


DATA_DIR = Path("/app/data")
REGISTRY_FILE = DATA_DIR / "registry.json"
# Copy of the bundled registry outside the data volume (see Dockerfile). An existing
# `registry_data` volume hides the bundled /app/data/registry.json, so new or changed
# bundled providers are merged from this seed on every start.
SEED_FILE = Path("/app/seed/registry.json")

# Catalogue metadata of a bundled provider that is refreshed from the seed. User-managed
# settings (name, base_url, status) are kept.
SEED_MANAGED_KEYS = ("provider", "description", "product_types", "product_ids",
                     "data_categories", "data_fields", "conditions")


class RegistryStore:
    """Thread-safe JSON-file-backed service registry."""

    def __init__(self, filepath: Path = REGISTRY_FILE, seed_file: Path | None = SEED_FILE):
        self._filepath = filepath
        self._seed_file = seed_file
        self._services: list[dict] = []
        self._lock = Lock()

    def load(self) -> None:
        """Load registry from JSON file and merge the bundled seed providers."""
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        if self._filepath.exists():
            with open(self._filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._services = data.get("services", [])
        else:
            self._services = []
        merged = self._merge_seed()
        for service in self._services:
            service["data_categories"] = normalize_categories(service.get("data_categories"))
        if merged or not self._filepath.exists():
            self._save()

    def _merge_seed(self) -> bool:
        """Add missing bundled providers and refresh their catalogue metadata.

        Returns True if the registry changed.
        """
        if not self._seed_file or not self._seed_file.exists() or self._seed_file == self._filepath:
            return False
        with open(self._seed_file, "r", encoding="utf-8") as f:
            seed_services = json.load(f).get("services", [])
        by_id = {s.get("id"): s for s in self._services if s.get("id")}
        changed = False
        for seed in seed_services:
            existing = by_id.get(seed.get("id"))
            if existing is None:
                self._services.append(dict(seed))
                changed = True
                continue
            for key in SEED_MANAGED_KEYS:
                if key in seed and existing.get(key) != seed[key]:
                    existing[key] = seed[key]
                    changed = True
        return changed

    def _save(self) -> None:
        """Persist current state to JSON file."""
        with open(self._filepath, "w", encoding="utf-8") as f:
            json.dump({"services": self._services}, f, indent=2, ensure_ascii=False)

    def list_all(self) -> list[ServiceEndpoint]:
        """Return all registered services."""
        with self._lock:
            return [ServiceEndpoint(**s) for s in self._services]

    def get_by_id(self, service_id: str) -> Optional[ServiceEndpoint]:
        """Get a single service by ID."""
        with self._lock:
            for s in self._services:
                if s.get("id") == service_id:
                    return ServiceEndpoint(**s)
        return None

    def find_by_product_type(self, product_type: str) -> list[ServiceEndpoint]:
        """Find services that support a given product type."""
        with self._lock:
            results = []
            for s in self._services:
                if product_type in s.get("product_types", []):
                    if s.get("status", "active") == "active":
                        results.append(ServiceEndpoint(**s))
            return results

    def find_by_category(self, category: str) -> list[ServiceEndpoint]:
        """Find services that provide a given data category (legacy names are normalised)."""
        normalized = normalize_categories([category])
        category = normalized[0] if normalized else category
        with self._lock:
            results = []
            for s in self._services:
                if category in s.get("data_categories", []):
                    if s.get("status", "active") == "active":
                        results.append(ServiceEndpoint(**s))
            return results

    def select(
        self,
        product_id: str | None,
        product_type: str | None,
        data_categories: list[str] | None,
        data_fields: list[str] | None = None,
    ) -> ServiceSelectionResponse:
        """
        Select the providers that are needed for one resolution request.

        1. Product type: providers that declare product types must support it.
        2. Product identifier: providers with a closed catalogue (`product_ids`) are only
           selected if they list the identifier. Providers with an open catalogue are
           selected if the identifier matches their `identifier_pattern`, or if no
           closed-catalogue provider knows the identifier.
        3. Data fields: if the context requires specific fields, providers that declare
           `data_fields` are only selected if they serve at least one of them; providers
           that only declare `data_categories` are matched on category level. Identity
           fields as well as the identification and metadata categories are ignored here
           because every provider contributes them.
        """
        required = {c for c in normalize_categories(data_categories) if c not in NON_SELECTIVE_CATEGORIES}
        required_fields = {f for f in (data_fields or []) if f not in IDENTITY_FIELDS}
        with self._lock:
            active = [s for s in self._services if s.get("status", "active") == "active"]

        selected: list[ServiceEndpoint] = []
        excluded: list[dict[str, str]] = []

        def exclude(service: dict, reason: str) -> None:
            excluded.append({"id": service.get("id") or "", "name": service.get("name", ""), "reason": reason})

        candidates = []
        for service in active:
            types = service.get("product_types") or []
            if product_type and types and product_type not in types:
                exclude(service, f"product type '{product_type}' not supported")
                continue
            candidates.append(service)

        known_in_closed_catalogue = bool(product_id) and any(
            product_id in (s.get("product_ids") or []) for s in candidates
        )

        for service in candidates:
            if product_id:
                catalogue = service.get("product_ids") or []
                pattern = (service.get("conditions") or {}).get("identifier_pattern")
                if catalogue:
                    if product_id not in catalogue:
                        exclude(service, "identifier not in provider catalogue")
                        continue
                else:
                    matches = bool(pattern) and re.fullmatch(pattern, product_id) is not None
                    if known_in_closed_catalogue and not matches:
                        exclude(service, "identifier belongs to a closed catalogue of another provider")
                        continue
            fields = set(service.get("data_fields") or [])
            categories = set(service.get("data_categories") or [])
            if required_fields and fields:
                if not (fields & required_fields):
                    exclude(service, "no relevant data field")
                    continue
            elif required and categories and not (categories & required):
                exclude(service, "no relevant data category")
                continue
            selected.append(ServiceEndpoint(**service))

        return ServiceSelectionResponse(
            selected=selected,
            excluded=excluded,
            category_filter_applied=bool(required or required_fields),
        )

    def create(self, endpoint: ServiceEndpointCreate) -> ServiceEndpoint:
        """Register a new service endpoint."""
        with self._lock:
            service_data = endpoint.model_dump()
            service_data["data_categories"] = normalize_categories(service_data.get("data_categories"))
            service_data["id"] = str(uuid.uuid4())
            service_data["status"] = ServiceStatus.ACTIVE.value
            self._services.append(service_data)
            self._save()
            return ServiceEndpoint(**service_data)

    def update(self, service_id: str, update: ServiceEndpointUpdate) -> Optional[ServiceEndpoint]:
        """Update an existing service endpoint."""
        with self._lock:
            for i, s in enumerate(self._services):
                if s.get("id") == service_id:
                    update_data = update.model_dump(exclude_unset=True)
                    if update_data.get("data_categories") is not None:
                        update_data["data_categories"] = normalize_categories(update_data["data_categories"])
                    if "status" in update_data and update_data["status"] is not None:
                        update_data["status"] = update_data["status"].value if hasattr(update_data["status"], "value") else update_data["status"]
                    self._services[i].update(update_data)
                    self._save()
                    return ServiceEndpoint(**self._services[i])
        return None

    def delete(self, service_id: str) -> bool:
        """Remove a service endpoint."""
        with self._lock:
            for i, s in enumerate(self._services):
                if s.get("id") == service_id:
                    self._services.pop(i)
                    self._save()
                    return True
        return False
