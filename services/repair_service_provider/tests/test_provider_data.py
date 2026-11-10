"""Consistency checks for the bundled product data of the domain providers.

Covers the Repair & Service Network Provider and its interplay with the Mock, Recycling EOL,
and Midlife Purchase providers: every provider uses the shared vocabulary, describes the same
product identically, and the providers do not contradict each other.
"""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICES = REPO_ROOT / "services"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.vocabulary import FIELD_CATEGORIES  # noqa: E402

IDENTITY_FIELDS = ("product_id", "product_type", "manufacturer", "model")
# Conflicts that are part of the published evaluation (the resolver reports them) and are
# therefore kept: the Mock Provider lists an older model designation for the Vaillant boiler.
KNOWN_CONFLICTS = {("BL-VAILLANT-001", "model")}
EPREL_PRODUCTS = ("2219971", "2613426")


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_served_products() -> dict[str, dict[str, dict]]:
    """Products as each provider serves them (the Mock Provider applies its delegation)."""
    delegation = _load_module(SERVICES / "mock_providers/app/delegation.py", "mock_delegation")
    package = types.ModuleType("app")
    saved = {k: sys.modules.get(k) for k in ("app", "app.delegation")}
    sys.modules["app"], sys.modules["app.delegation"] = package, delegation
    try:
        mock = _load_module(SERVICES / "mock_providers/app/product_data.py", "mock_product_data")
    finally:
        for key, value in saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value
    providers = {"mock": {pid: mock.get_product(pid) for pid in mock.PRODUCTS}}
    for name, folder in (("eol", "recycling_eol_provider"), ("midlife", "midlife_purchase_provider"),
                         ("repair", "repair_service_provider")):
        module = _load_module(SERVICES / folder / "app/product_data.py", f"{name}_product_data")
        providers[name] = {pid: module.get_product(pid) for pid in module.PRODUCTS}
    return providers


def non_empty(value) -> bool:
    return value not in (None, "", [], {})


class ProviderDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.providers = load_served_products()

    def test_repair_provider_uses_shared_vocabulary(self) -> None:
        for product_id, product in self.providers["repair"].items():
            unknown = set(product) - set(FIELD_CATEGORIES)
            self.assertFalse(unknown, f"{product_id}: fields outside the shared vocabulary: {sorted(unknown)}")

    def test_extended_fields_use_shared_vocabulary(self) -> None:
        for name in ("mock", "eol", "midlife"):
            for product_id in EPREL_PRODUCTS:
                unknown = set(self.providers[name][product_id]) - set(FIELD_CATEGORIES)
                self.assertFalse(unknown, f"{name}/{product_id}: {sorted(unknown)}")

    def test_identity_is_consistent_across_providers(self) -> None:
        for product_id in self.providers["repair"]:
            for field in IDENTITY_FIELDS:
                if (product_id, field) in KNOWN_CONFLICTS:
                    continue
                values = {
                    name: data[product_id][field]
                    for name, data in self.providers.items()
                    if product_id in data and field in data[product_id]
                }
                self.assertEqual(len(set(values.values())), 1, f"{product_id}.{field}: {values}")

    def test_providers_do_not_contradict_each_other(self) -> None:
        product_ids = set().union(*(data.keys() for data in self.providers.values()))
        for product_id in sorted(product_ids):
            values: dict[str, dict[str, object]] = {}
            for name, data in self.providers.items():
                for field, value in (data.get(product_id) or {}).items():
                    if not field.startswith("_") and field != "data_sources" and non_empty(value):
                        values.setdefault(field, {})[name] = value
            for field, by_provider in values.items():
                if (product_id, field) in KNOWN_CONFLICTS:
                    continue
                distinct = {repr(v) for v in by_provider.values()}
                self.assertEqual(len(distinct), 1, f"{product_id}.{field} differs: {by_provider}")

    def test_sparse_reference_unit_stays_incomplete(self) -> None:
        """SP-SUNPOWER-002 is the deliberately incomplete passport of the evaluation."""
        self.assertNotIn("SP-SUNPOWER-002", self.providers["repair"])
        self.assertNotIn("SP-SUNPOWER-002", self.providers["mock"])

    def test_eprel_products_are_covered_by_all_domain_providers(self) -> None:
        for name in ("mock", "eol", "midlife", "repair"):
            for product_id in EPREL_PRODUCTS:
                self.assertIn(product_id, self.providers[name], f"{name} lacks {product_id}")


if __name__ == "__main__":
    unittest.main()
