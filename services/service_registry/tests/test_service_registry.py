from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
for path in (SERVICE_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from app.registry_store import RegistryStore
from app.routes import (
    _as_list,
    _endpoint_from_metadata,
    _extract_products,
    _infer_categories_from_product,
    _infer_from_products,
    _normalize_base_url,
)
from shared.models import ServiceEndpointCreate, ServiceEndpointUpdate, ServiceStatus


def run(coro):
    return asyncio.run(coro)


class RegistryStoreTests(unittest.TestCase):
    def test_store_crud_and_active_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RegistryStore(Path(tmpdir) / "registry.json")
            store.load()

            created = store.create(ServiceEndpointCreate(
                name="EPREL",
                provider="EU",
                base_url="http://eprel-provider:8024",
                product_types=["dishwasher"],
                data_categories=["energy_label"],
            ))

            self.assertEqual(len(store.list_all()), 1)
            self.assertEqual(store.get_by_id(created.id).name, "EPREL")
            self.assertEqual([s.id for s in store.find_by_product_type("dishwasher")], [created.id])
            self.assertEqual([s.id for s in store.find_by_category("energy_label")], [created.id])

            updated = store.update(created.id, ServiceEndpointUpdate(status=ServiceStatus.INACTIVE))
            self.assertEqual(updated.status, ServiceStatus.INACTIVE)
            self.assertEqual(store.find_by_product_type("dishwasher"), [])

            self.assertTrue(store.delete(created.id))
            self.assertIsNone(store.get_by_id(created.id))
            self.assertFalse(store.delete(created.id))

    def test_bundled_seed_is_merged_into_existing_registry_file(self) -> None:
        """An existing registry volume receives new bundled providers and their catalogue updates."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            registry, seed = Path(tmpdir) / "registry.json", Path(tmpdir) / "seed.json"
            registry.write_text(json.dumps({"services": [
                {"id": "eol", "name": "Renamed by user", "base_url": "http://custom:9", "status": "inactive",
                 "product_ids": ["OLD-1"], "data_fields": ["materials"], "data_categories": ["materials"]},
                {"id": "user-added", "name": "User", "base_url": "http://user", "data_categories": []},
            ]}), encoding="utf-8")
            seed.write_text(json.dumps({"services": [
                {"id": "eol", "name": "Recycling EOL Provider", "base_url": "http://recycling-eol-provider:8021",
                 "status": "active", "product_ids": ["OLD-1", "NEW-2"], "data_fields": ["materials", "battery_removal_instructions"],
                 "data_categories": ["materials", "end_of_life"]},
                {"id": "repair", "name": "Repair & Service Network Provider", "base_url": "http://repair:8025",
                 "status": "active", "product_ids": ["NEW-2"], "data_categories": ["maintenance"]},
            ]}), encoding="utf-8")

            store = RegistryStore(registry, seed_file=seed)
            store.load()

            services = {s.id: s for s in store.list_all()}
            self.assertEqual(list(services), ["eol", "user-added", "repair"])
            self.assertEqual(services["eol"].product_ids, ["OLD-1", "NEW-2"])
            self.assertEqual(sorted(services["eol"].data_categories), ["end_of_life", "materials"])
            # user-managed settings are kept
            self.assertEqual(services["eol"].name, "Renamed by user")
            self.assertEqual(services["eol"].base_url, "http://custom:9")
            self.assertEqual(services["eol"].status, ServiceStatus.INACTIVE)
            # the merge is persisted
            persisted = json.loads(registry.read_text(encoding="utf-8"))["services"]
            self.assertEqual([s["id"] for s in persisted], ["eol", "user-added", "repair"])

    def test_bundled_registry_lists_repair_service_provider(self) -> None:
        import json

        services = json.loads((SERVICE_ROOT / "data" / "registry.json").read_text(encoding="utf-8"))["services"]
        repair = next(s for s in services if s["id"] == "repair-service-provider-001")
        self.assertEqual(repair["base_url"], "http://repair-service-provider:8025")
        self.assertIn("2219971", repair["product_ids"])
        self.assertIn("maintenance", repair["data_categories"])


class RegistryDiscoveryHelperTests(unittest.TestCase):
    def test_normalize_base_url_strips_api_documentation_suffixes(self) -> None:
        self.assertEqual(_normalize_base_url(" http://service:8024/docs "), "http://service:8024")
        self.assertEqual(_normalize_base_url("http://service:8024/metadata"), "http://service:8024")
        self.assertEqual(
            _normalize_base_url("http://service:8024/base/.well-known/circthread-service"),
            "http://service:8024/base",
        )

    def test_extract_products_accepts_common_provider_shapes(self) -> None:
        self.assertEqual(_extract_products([{"product_id": "A"}, "bad"]), [{"product_id": "A"}])
        self.assertEqual(_extract_products({"products": [{"product_id": "B"}, 1]}), [{"product_id": "B"}])
        self.assertEqual(_extract_products({"product_id": "C"}), [{"product_id": "C"}])
        self.assertEqual(_extract_products({"unexpected": []}), [])

    def test_endpoint_from_metadata_and_category_inference(self) -> None:
        endpoint = _endpoint_from_metadata("http://service", {
            "name": "Provider",
            "provider": "Org",
            "description": "Desc",
            "product_types": "dishwasher",
            "data_categories": ["energy_label"],
            "conditions": {"requires_auth": False},
        })

        self.assertEqual(endpoint.name, "Provider")
        self.assertEqual(endpoint.product_types, ["dishwasher"])
        self.assertEqual(endpoint.data_categories, ["sustainability"])
        self.assertEqual(_as_list(None), [])
        self.assertEqual(
            _infer_categories_from_product({"materials": [{"name": "steel"}], "warranty_years": 2}),
            ["economic", "materials"],
        )

    def test_infer_from_products_adds_missing_product_types_and_categories(self) -> None:
        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {
                    "products": [
                        {
                            "product_id": "P1",
                            "product_type": "washing_machine",
                            "energy_label": {"class": "A"},
                            "warranty_years": 2,
                        }
                    ]
                }

        class FakeClient:
            async def get(self, url):
                self.url = url
                return FakeResponse()

        endpoint = ServiceEndpointCreate(
            name="Provider",
            base_url="http://provider",
            product_types=[],
            data_categories=[],
        )
        result = run(_infer_from_products(FakeClient(), "http://provider", endpoint))

        self.assertEqual(result.product_types, ["washing_machine"])
        self.assertEqual(result.data_categories, ["economic", "identification", "sustainability"])


class RegistrySelectionTests(unittest.TestCase):
    """Provider preselection used by the Resolver (POST /services/select)."""

    def _store(self, tmp: str) -> RegistryStore:
        store = RegistryStore(Path(tmp) / "registry.json")
        store.create(ServiceEndpointCreate(
            name="Base", base_url="http://base", product_types=["washing_machine"],
            product_ids=["WM-1"], data_fields=["product_id", "model", "weight_kg"],
            data_categories=["identification", "technical"],
        ))
        store.create(ServiceEndpointCreate(
            name="Recycling", base_url="http://eol", product_types=["washing_machine"],
            product_ids=["WM-1"], data_fields=["product_id", "materials", "disassembly_instructions"],
            data_categories=["identification", "materials", "end_of_life"],
        ))
        store.create(ServiceEndpointCreate(
            name="Purchase", base_url="http://mol", product_types=["washing_machine"],
            product_ids=["WM-1"], data_fields=["product_id", "purchase_price_eur", "energy_label"],
            data_categories=["identification", "economic", "sustainability"],
        ))
        store.create(ServiceEndpointCreate(
            name="EPREL", base_url="http://eprel", product_types=["washing_machine", "dishwasher"],
            data_categories=["identification", "sustainability"],
            conditions={"identifier_pattern": "^[0-9]+$"},
        ))
        return store

    def test_selects_only_providers_with_relevant_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            result = store.select("WM-1", "washing_machine", ["materials", "end_of_life"],
                                  ["product_id", "materials", "disassembly_instructions"])
        self.assertEqual([s.name for s in result.selected], ["Recycling"])
        reasons = {e["name"]: e["reason"] for e in result.excluded}
        self.assertEqual(reasons["Base"], "no relevant data field")
        self.assertEqual(reasons["EPREL"], "identifier belongs to a closed catalogue of another provider")
        self.assertTrue(result.category_filter_applied)

    def test_open_catalogue_provider_is_used_for_unknown_or_matching_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            numeric = store.select("2613426", None, [], [])
            model_id = store.select("SN43HW04ME", None, [], [])
        self.assertEqual([s.name for s in numeric.selected], ["EPREL"])
        self.assertEqual([s.name for s in model_id.selected], ["EPREL"])

    def test_without_context_all_providers_of_the_product_are_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            result = store.select("WM-1", "washing_machine", [], [])
        self.assertEqual([s.name for s in result.selected], ["Base", "Recycling", "Purchase"])
        self.assertFalse(result.category_filter_applied)

    def test_legacy_category_names_are_normalised(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            self.assertEqual([s.name for s in store.find_by_category("energy_label")], ["Purchase", "EPREL"])


if __name__ == "__main__":
    unittest.main()
