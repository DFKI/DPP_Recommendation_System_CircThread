from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from app import resolver_logic


def run(coro):
    return asyncio.run(coro)


class ResolverAggregationTests(unittest.TestCase):
    def test_aggregate_product_data_merges_providers_and_tracks_sources(self) -> None:
        endpoints = [
            {"base_url": "http://provider-a", "name": "Provider A"},
            {"base_url": "http://provider-b", "name": "Provider B"},
        ]
        selection = {"selected": endpoints, "excluded": [{"name": "Provider C", "reason": "no relevant data field"}],
                     "category_filter_applied": True}
        payloads = {
            ("http://provider-a", "P1"): {
                "product_id": "P1",
                "product_type": "washing_machine",
                "manufacturer": "Old Name",
                "energy_label": {"class": "B"},
                "warranty_years": 3,
                "_internal": "ignored",
            },
            ("http://provider-b", "P1"): {
                "product_id": "P1",
                "manufacturer": "New Name",
                "warranty_years": [],
                "empty_field": [],
            },
        }

        async def fake_fetch(base_url: str, product_id: str):
            return payloads[(base_url, product_id)]

        select = AsyncMock(return_value=selection)
        with (
            patch("app.resolver_logic.select_providers", new=select),
            patch("app.resolver_logic.fetch_product_data", side_effect=fake_fetch),
        ):
            result = run(resolver_logic.aggregate_product_data("P1", "washing_machine", ["warranty_years"], ["economic"]))

        select.assert_awaited_once_with("P1", "washing_machine", ["warranty_years"], ["economic"])
        self.assertEqual(result["manufacturer"], "New Name")
        self.assertEqual(result["energy_label"], {"class": "B"})
        # empty values never overwrite non-empty values of other providers
        self.assertEqual(result["warranty_years"], 3)
        self.assertNotIn("_internal", result)
        self.assertEqual(result["data_sources"], ["Provider A", "Provider B"])
        self.assertEqual(result["_field_sources"]["manufacturer"], ["Provider A", "Provider B"])
        self.assertEqual(result["_field_sources"]["warranty_years"], ["Provider A"])
        self.assertNotIn("empty_field", result["_field_sources"])
        self.assertEqual([c["value"] for c in result["_conflicts"]["manufacturer"]], ["Old Name", "New Name"])
        self.assertNotIn("product_id", result["_conflicts"])
        self.assertEqual(result["_provider_selection"]["queried"], ["Provider A", "Provider B"])
        self.assertEqual(result["_provider_selection"]["excluded"][0]["name"], "Provider C")

    def test_resolve_product_preselects_providers_from_recommendation_plan(self) -> None:
        plan = {"fields": [
            {"field_name": "materials", "category": "materials"},
            {"field_name": "disassembly_instructions", "category": "end_of_life"},
        ]}
        raw_data = {"product_id": "P1", "product_type": "washing_machine", "data_sources": ["EOL"],
                    "_provider_selection": {"queried": ["EOL"]}, "_conflicts": {}}
        aggregate = AsyncMock(return_value=raw_data)
        with (
            patch("app.resolver_logic.lookup_product_type", new=AsyncMock(return_value="washing_machine")),
            patch("app.resolver_logic.get_recommendation_plan", new=AsyncMock(return_value=plan)),
            patch("app.resolver_logic.aggregate_product_data", new=aggregate),
            patch("app.resolver_logic.get_recommendation", new=AsyncMock(return_value={"filtered_data": {}})),
        ):
            result = run(resolver_logic.resolve_product("P1", "recycler", "recycling", None))

        aggregate.assert_awaited_once_with(
            "P1", "washing_machine", ["materials", "disassembly_instructions"], ["end_of_life", "materials"]
        )
        self.assertEqual(result["provider_selection"], {"queried": ["EOL"]})

    def test_list_available_products_merges_catalog_entries(self) -> None:
        endpoints = [
            {"base_url": "http://provider-a", "name": "Provider A"},
            {"base_url": "http://provider-b", "name": "Provider B"},
        ]

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return endpoints

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            async def get(self, _url):
                return FakeResponse()

        product_lists = {
            "http://provider-a": [
                {"product_id": "P1", "product_type": "dishwasher", "manufacturer": "Siemens", "model": "A"},
            ],
            "http://provider-b": [
                {"product_id": "P1", "product_type": "dishwasher", "manufacturer": "Siemens", "model": "B"},
                {"product_id": "P2", "product_type": "washing_machine", "manufacturer": "Bosch", "model": "C"},
            ],
        }

        async def fake_fetch_list(base_url: str):
            return product_lists[base_url]

        with (
            patch("app.resolver_logic.httpx.AsyncClient", return_value=FakeClient()),
            patch("app.resolver_logic.fetch_product_list", side_effect=fake_fetch_list),
        ):
            result = run(resolver_logic.list_available_products())

        self.assertEqual(result["count"], 2)
        by_id = {product["product_id"]: product for product in result["products"]}
        self.assertEqual(by_id["P1"]["model"], "B")
        self.assertEqual(by_id["P1"]["sources"], ["Provider A", "Provider B"])
        self.assertEqual(by_id["P2"]["sources"], ["Provider B"])

    def test_resolve_product_returns_filtered_recommendation_when_available(self) -> None:
        raw_data = {
            "product_id": "P1",
            "product_type": "dishwasher",
            "manufacturer": "Siemens",
            "energy_label": {"class": "D"},
            "data_sources": ["EPREL"],
        }
        recommendation = {
            "filtered_data": {"manufacturer": "Siemens", "energy_label": {"class": "D"}},
            "recommended_fields": [],
        }

        with (
            patch("app.resolver_logic.lookup_product_type", new=AsyncMock(return_value=None)),
            patch("app.resolver_logic.aggregate_product_data", new=AsyncMock(return_value=raw_data)),
            patch("app.resolver_logic.get_recommendation", new=AsyncMock(return_value=recommendation)),
        ):
            result = run(resolver_logic.resolve_product("P1", " consumer ", " purchase ", None))

        self.assertEqual(result["product_type"], "dishwasher")
        self.assertEqual(result["role"], "consumer")
        self.assertEqual(result["event"], "purchase")
        self.assertEqual(result["passport"], recommendation["filtered_data"])
        self.assertEqual(result["sources"], ["EPREL"])

    def test_build_custom_dpp_marks_missing_selected_terms(self) -> None:
        raw_data = {
            "product_id": "P1",
            "product_type": "dishwasher",
            "manufacturer": "Siemens",
            "data_sources": ["EPREL"],
            "_field_sources": {"manufacturer": ["EPREL"]},
        }

        with (
            patch("app.resolver_logic.lookup_product_type", new=AsyncMock(return_value="dishwasher")),
            patch("app.resolver_logic.aggregate_product_data", new=AsyncMock(return_value=raw_data)),
            patch("app.resolver_logic.save_dpp_template", new=AsyncMock(return_value={"template_id": "T1"})),
        ):
            result = run(resolver_logic.build_custom_dpp("P1", ["manufacturer", "", "noise_db"], save_template=True))

        self.assertEqual(result["selected_terms"], ["manufacturer", "noise_db"])
        fields = {field["field_name"]: field for field in result["selected_fields"]}
        self.assertTrue(fields["manufacturer"]["available"])
        self.assertEqual(fields["manufacturer"]["sources"], ["EPREL"])
        self.assertFalse(fields["noise_db"]["available"])
        self.assertEqual(result["passport"], {"manufacturer": "Siemens"})


class FakeHttpResponse:
    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeHttpClient:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def get(self, _url):
        if self.error:
            raise self.error
        return self.response

    async def post(self, _url, json=None):  # noqa: A002 - mirrors httpx signature
        if self.error:
            raise self.error
        return self.response


class ProviderFailureTests(unittest.TestCase):
    """Provider failures must never abort the resolution (Section 3.2.3 / 4.1)."""

    endpoints = [
        {"base_url": "http://provider-a", "name": "Provider A"},
        {"base_url": "http://provider-b", "name": "Provider B"},
        {"base_url": "http://provider-c", "name": "Provider C"},
    ]

    def _aggregate(self, fake_fetch):
        selection = {"selected": self.endpoints, "excluded": [], "category_filter_applied": True}
        with (
            patch("app.resolver_logic.select_providers", new=AsyncMock(return_value=selection)),
            patch("app.resolver_logic.fetch_product_data", side_effect=fake_fetch),
        ):
            return run(resolver_logic.aggregate_product_data("P1", "washing_machine", ["materials"], ["materials"]))

    def test_unavailable_provider_does_not_abort_aggregation(self) -> None:
        async def fake_fetch(base_url: str, product_id: str):
            if base_url == "http://provider-b":
                raise resolver_logic.ProviderUnavailableError("unreachable: ConnectError")
            if base_url == "http://provider-c":
                return None  # provider does not know the product
            return {"product_id": product_id, "materials": ["steel"]}

        result = self._aggregate(fake_fetch)

        self.assertEqual(result["materials"], ["steel"])
        self.assertEqual(result["data_sources"], ["Provider A"])
        selection = result["_provider_selection"]
        self.assertEqual(selection["queried"], ["Provider A", "Provider B", "Provider C"])
        self.assertEqual(selection["responded"], ["Provider A"])
        self.assertEqual(selection["no_data"], ["Provider C"])
        self.assertEqual(selection["unavailable"], [{"name": "Provider B", "reason": "unreachable: ConnectError"}])

    def test_unexpected_provider_exception_is_reported_as_unavailable(self) -> None:
        async def fake_fetch(base_url: str, product_id: str):
            if base_url == "http://provider-a":
                raise RuntimeError("boom")
            return {"product_id": product_id}

        result = self._aggregate(fake_fetch)

        self.assertEqual(result["data_sources"], ["Provider B", "Provider C"])
        self.assertEqual(result["_provider_selection"]["unavailable"], [{"name": "Provider A", "reason": "boom"}])

    def test_conflicting_values_keep_the_last_registered_provider(self) -> None:
        values = {"http://provider-a": "A", "http://provider-b": "B", "http://provider-c": "C"}

        async def fake_fetch(base_url: str, product_id: str):
            return {"product_id": product_id, "warranty": values[base_url]}

        result = self._aggregate(fake_fetch)

        self.assertEqual(result["warranty"], "C")
        self.assertEqual(result["_field_sources"]["warranty"], ["Provider A", "Provider B", "Provider C"])
        self.assertEqual([c["provider"] for c in result["_conflicts"]["warranty"]],
                         ["Provider A", "Provider B", "Provider C"])

    def _resolve_without_data(self, fake_fetch):
        selection = {"selected": self.endpoints, "excluded": [], "category_filter_applied": False}
        with (
            patch("app.resolver_logic.lookup_product_type", new=AsyncMock(return_value=None)),
            patch("app.resolver_logic.select_providers", new=AsyncMock(return_value=selection)),
            patch("app.resolver_logic.fetch_product_data", side_effect=fake_fetch),
        ):
            return run(resolver_logic.resolve_product("P404", "consumer", "purchase", None))

    def test_product_is_not_found_only_if_no_provider_delivers_data(self) -> None:
        async def fake_fetch(base_url: str, product_id: str):
            return None

        result = self._resolve_without_data(fake_fetch)

        self.assertEqual(result["error"], "Product not found in any registered data source")
        self.assertEqual(result["error_reason"], "not_found")
        self.assertEqual(result["provider_selection"]["no_data"], ["Provider A", "Provider B", "Provider C"])

    def test_missing_data_due_to_unavailable_providers_is_not_reported_as_not_found(self) -> None:
        async def fake_fetch(base_url: str, product_id: str):
            if base_url == "http://provider-a":
                raise resolver_logic.ProviderUnavailableError("HTTP 503")
            return None

        result = self._resolve_without_data(fake_fetch)

        self.assertEqual(result["error_reason"], "providers_unavailable")
        self.assertIn("unavailable", result["error"])
        self.assertEqual(result["provider_selection"]["unavailable"][0]["name"], "Provider A")
        self.assertEqual(result["provider_selection"]["no_data"], ["Provider B", "Provider C"])

    def test_fetch_product_data_distinguishes_missing_product_from_unavailable_provider(self) -> None:
        cases = [
            (FakeHttpClient(FakeHttpResponse(200, {"product_id": "P1"})), {"product_id": "P1"}),
            (FakeHttpClient(FakeHttpResponse(404, {"detail": "not found"})), None),
            (FakeHttpClient(FakeHttpResponse(422, {"detail": "invalid id"})), None),
        ]
        for client, expected in cases:
            with patch("app.resolver_logic.httpx.AsyncClient", return_value=client):
                self.assertEqual(run(resolver_logic.fetch_product_data("http://p", "P1")), expected)

        failing = [
            FakeHttpClient(FakeHttpResponse(502, {"detail": "upstream"})),
            FakeHttpClient(FakeHttpResponse(200, ValueError("no json"))),
            FakeHttpClient(error=resolver_logic.httpx.ConnectError("refused")),
        ]
        for client in failing:
            with patch("app.resolver_logic.httpx.AsyncClient", return_value=client):
                with self.assertRaises(resolver_logic.ProviderUnavailableError):
                    run(resolver_logic.fetch_product_data("http://p", "P1"))


class IdentifierAliasTests(unittest.TestCase):
    """A provider may resolve an alias (EPREL model identifier) to the canonical identifier."""

    eprel = {"base_url": "http://eprel", "name": "EPREL"}
    mock = {"base_url": "http://mock", "name": "Mock"}
    repair = {"base_url": "http://repair", "name": "Repair"}

    def test_providers_of_the_resolved_identifier_are_queried(self) -> None:
        calls = []

        async def fake_select(product_id, *args):
            if product_id == "SN43HW04ME":
                return {"selected": [self.eprel], "excluded": [
                    {"name": "Mock", "reason": "identifier not in provider catalogue"}], "category_filter_applied": True}
            return {"selected": [self.mock, self.eprel, self.repair], "excluded": [], "category_filter_applied": True}

        async def fake_fetch(base_url, product_id):
            calls.append((base_url, product_id))
            if base_url == "http://eprel":
                return {"product_id": "2613426", "energy_class": "D"}
            if base_url == "http://mock":
                return {"product_id": product_id, "weight_kg": 41.0}
            return {"product_id": product_id, "repair_history": [{"date": "2026-09-22"}]}

        with (
            patch("app.resolver_logic.select_providers", side_effect=fake_select),
            patch("app.resolver_logic.fetch_product_data", side_effect=fake_fetch),
        ):
            result = run(resolver_logic.aggregate_product_data("SN43HW04ME", "dishwasher", ["weight_kg"], ["technical"]))

        self.assertEqual(calls, [("http://eprel", "SN43HW04ME"), ("http://mock", "2613426"), ("http://repair", "2613426")])
        self.assertEqual(result["product_id"], "2613426")
        self.assertEqual(result["weight_kg"], 41.0)
        self.assertEqual(result["energy_class"], "D")
        selection = result["_provider_selection"]
        self.assertEqual(selection["resolved_identifier"], "2613426")
        self.assertEqual(selection["queried"], ["Mock", "EPREL", "Repair"])
        self.assertEqual(selection["excluded"], [])

    def test_no_follow_up_when_identifier_is_unchanged(self) -> None:
        select = AsyncMock(return_value={"selected": [self.mock], "excluded": [], "category_filter_applied": False})

        async def fake_fetch(base_url, product_id):
            return {"product_id": product_id}

        with (
            patch("app.resolver_logic.select_providers", new=select),
            patch("app.resolver_logic.fetch_product_data", side_effect=fake_fetch),
        ):
            result = run(resolver_logic.aggregate_product_data("WM-BOSCH-001"))

        self.assertEqual(select.await_count, 1)
        self.assertNotIn("resolved_identifier", result["_provider_selection"])


class TemplateForwardingTests(unittest.TestCase):
    def test_build_custom_dpp_forwards_custom_event_and_phase(self) -> None:
        raw_data = {"product_id": "SP1", "product_type": "solar_panel", "data_sources": ["X"], "_field_sources": {}}
        save = AsyncMock(return_value={"template_id": "T1", "custom_event": "Inverter inspection",
                                       "lifecycle_phase": "middle_of_life"})
        with (
            patch("app.resolver_logic.lookup_product_type", new=AsyncMock(return_value="solar_panel")),
            patch("app.resolver_logic.aggregate_product_data", new=AsyncMock(return_value=raw_data)),
            patch("app.resolver_logic.save_dpp_template", new=save),
        ):
            result = run(resolver_logic.build_custom_dpp(
                "SP1", ["components"], role="repairer", custom_event="Inverter inspection",
                lifecycle_phase="middle_of_life", user_id="client-1",
            ))

        kwargs = save.await_args.kwargs
        self.assertEqual(kwargs["custom_event"], "Inverter inspection")
        self.assertEqual(kwargs["lifecycle_phase"], "middle_of_life")
        self.assertEqual(kwargs["user_id"], "client-1")
        self.assertEqual(kwargs["product_type"], "solar_panel")
        self.assertEqual(result["custom_event"], "Inverter inspection")
        self.assertEqual(result["lifecycle_phase"], "middle_of_life")

    def test_save_dpp_template_raises_validation_error_for_rejected_template(self) -> None:
        client = FakeHttpClient(FakeHttpResponse(400, {"detail": "Lifecycle phase does not match event"}))
        with patch("app.resolver_logic.httpx.AsyncClient", return_value=client):
            with self.assertRaises(resolver_logic.TemplateValidationError) as ctx:
                run(resolver_logic.save_dpp_template("T", ["a"], None, "recycling", None,
                                                     lifecycle_phase="beginning_of_life"))
        self.assertIn("does not match", str(ctx.exception))

    def test_save_dpp_template_returns_none_if_engine_unreachable(self) -> None:
        client = FakeHttpClient(error=resolver_logic.httpx.ConnectError("refused"))
        with patch("app.resolver_logic.httpx.AsyncClient", return_value=client):
            self.assertIsNone(run(resolver_logic.save_dpp_template("T", ["a"], None, None, None)))


if __name__ == "__main__":
    unittest.main()
