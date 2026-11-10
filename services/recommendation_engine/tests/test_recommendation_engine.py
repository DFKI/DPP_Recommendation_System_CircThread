from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
for path in (SERVICE_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from app import knowledge_graph
from app.neo4j_client import Neo4jClient


def run(coro):
    return asyncio.run(coro)


class FakeNeo4jClient:
    def __init__(self, query_results: list[list[dict]] | None = None):
        self.query_results = list(query_results or [])
        self.queries: list[tuple[str, dict | None]] = []
        self.writes: list[tuple[str, dict | None]] = []

    async def run_query(self, query: str, parameters: dict | None = None) -> list[dict]:
        self.queries.append((query, parameters))
        if self.query_results:
            return self.query_results.pop(0)
        return []

    async def run_write(self, query: str, parameters: dict | None = None) -> None:
        self.writes.append((query, parameters))


class FakeResult:
    async def data(self) -> list[dict]:
        return [{"name": "consumer"}]


class FakeSession:
    def __init__(self):
        self.runs: list[tuple[str, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def run(self, query: str, parameters: dict):
        self.runs.append((query, parameters))
        return FakeResult()


class FakeDriver:
    def __init__(self):
        self.session_obj = FakeSession()
        self.verified = False
        self.closed = False

    async def verify_connectivity(self) -> None:
        self.verified = True

    async def close(self) -> None:
        self.closed = True

    def session(self):
        return self.session_obj


class RecommendationKnowledgeGraphTests(unittest.TestCase):
    def test_filter_product_data_uses_recommendations_and_field_sources(self) -> None:
        product_data = {
            "product_id": "P1",
            "product_type": "dishwasher",
            "manufacturer": "Siemens",
            "energy_label": {"class": "D"},
            "noise_db": 42,
            "_field_sources": {"energy_label": ["EPREL"], "noise_db": ["EPREL"]},
        }
        recommended = [
            {
                "field_name": "energy_label",
                "display_name": "Energy Label",
                "category": "sustainability",
                "priority": 1.0,
                "description": "EU label",
                "matched_roles": ["consumer"],
                "matched_events": ["purchase"],
                "filter_mode": "role_event",
            },
            {
                "field_name": "noise_db",
                "display_name": "Noise",
                "category": "technical",
                "priority": 0.8,
                "description": "Noise level",
            },
        ]

        core = {"fields": recommended, "filter_mode": "role_event", "fallback": None}
        suggestion = {"field_name": "purchase_price_eur", "display_name": "Price", "category": "economic",
                      "priority": 0.55, "recommendation_source": "contextual_similarity"}
        with (
            patch("app.knowledge_graph.get_core_recommendations", new=AsyncMock(return_value=core)),
            patch("app.knowledge_graph.get_suggestions", new=AsyncMock(return_value=[suggestion])),
        ):
            result = run(knowledge_graph.filter_product_data(
                FakeNeo4jClient(),
                product_data,
                "dishwasher",
                "consumer",
                "purchase",
            ))

        self.assertEqual(result["filter_mode"], "role_event")
        self.assertEqual(result["filtered_data"], {"energy_label": {"class": "D"}, "noise_db": 42})
        by_field = {field["field_name"]: field for field in result["recommended_fields"]}
        self.assertEqual(by_field["energy_label"]["sources"], ["EPREL"])
        self.assertEqual(by_field["energy_label"]["matched_roles"], ["consumer"])
        self.assertEqual(result["fields_shown"], 2)
        # extended-algorithm candidates are returned separately and do not enter the DPP view
        self.assertEqual([f["field_name"] for f in result["suggested_fields"]], ["purchase_price_eur"])
        self.assertNotIn("purchase_price_eur", result["filtered_data"])
        self.assertEqual(result["data_gaps"], [])

    def test_filter_product_data_falls_back_to_identification_fields(self) -> None:
        core = {"fields": [], "filter_mode": "generic", "fallback": None}
        with (
            patch("app.knowledge_graph.get_core_recommendations", new=AsyncMock(return_value=core)),
            patch("app.knowledge_graph.get_suggestions", new=AsyncMock(return_value=[])),
        ):
            result = run(knowledge_graph.filter_product_data(
                FakeNeo4jClient(),
                {
                    "product_id": "P1",
                    "product_type": "washing_machine",
                    "manufacturer": "Bosch",
                    "model": "WAN",
                },
                "washing_machine",
                None,
                None,
            ))

        self.assertEqual(result["filter_mode"], "basic_fallback")
        self.assertEqual(set(result["filtered_data"]), {"product_id", "product_type", "manufacturer", "model"})

    def test_empty_values_are_reported_as_data_gaps(self) -> None:
        recommended = [
            {"field_name": "repair_history", "display_name": "Repair History", "category": "maintenance",
             "priority": 1.0, "recommendation_source": "role_event"},
            {"field_name": "model", "display_name": "Model", "category": "identification",
             "priority": 0.9, "recommendation_source": "role_event"},
        ]
        core = {"fields": recommended, "filter_mode": "role_event", "fallback": None}
        with (
            patch("app.knowledge_graph.get_core_recommendations", new=AsyncMock(return_value=core)),
            patch("app.knowledge_graph.get_suggestions", new=AsyncMock(return_value=[])),
        ):
            result = run(knowledge_graph.filter_product_data(
                FakeNeo4jClient(),
                {"product_id": "P1", "model": "X", "repair_history": [], "_field_sources": {"model": ["A"]}},
                "washing_machine", "repairer", "repair",
            ))
        self.assertEqual(result["filtered_data"], {"model": "X"})
        self.assertEqual(result["data_gaps"], ["repair_history"])
        self.assertEqual(result["fields_shown"], 1)

    def test_core_recommendation_falls_back_to_role_mode_for_unmodelled_combination(self) -> None:
        role_row = {"field_name": "warranty_years", "display_name": "Warranty", "category": "economic",
                    "priority": 0.9, "recommendation_source": "role", "filter_mode": "role"}
        client = FakeNeo4jClient([[], [role_row], []])
        result = run(knowledge_graph.get_core_recommendations(client, "consumer", "recycling", "dishwasher"))
        self.assertEqual(result["filter_mode"], "role_fallback")
        self.assertEqual(result["fallback"], "role")
        self.assertEqual([f["field_name"] for f in result["fields"]], ["warranty_years"])
        self.assertEqual(client.queries[2][1]["role"], "consumer")
        self.assertEqual(client.queries[2][1]["event"], "recycling")

    def test_static_role_event_fields_are_labelled_role_event(self) -> None:
        client = FakeNeo4jClient()
        run(knowledge_graph.get_core_recommendations(client, "recycler", "recycling", "dishwasher"))
        self.assertIn('"role_event" AS recommendation_source', client.queries[0][0])

    def test_get_recommended_fields_queries_static_dynamic_and_external_mappings(self) -> None:
        client = FakeNeo4jClient([
            [
                {
                    "field_name": "energy_label",
                    "display_name": "Energy Label",
                    "category": "sustainability",
                    "category_display": "Sustainability",
                    "description": "EU label",
                    "priority": 1.0,
                    "matched_roles": ["consumer"],
                    "matched_events": ["purchase"],
                    "filter_mode": "role_event",
                }
            ],
            [
                {
                    "field_name": "warranty_years",
                    "display_name": "Warranty",
                    "category": "economic",
                    "category_display": "Economic",
                    "description": "Warranty",
                    "priority": 0.65,
                    "template_count": 2,
                    "recommendation_source": "dynamic_template",
                }
            ],
            [
                {"field_name": "energy_label", "external_mappings": [{"object_id": "schema:energyEfficiencyScale"}]},
            ],
        ])

        result = run(knowledge_graph.get_recommended_fields(client, "consumer", "purchase", "dishwasher"))

        self.assertEqual([row["field_name"] for row in result], ["energy_label", "warranty_years"])
        self.assertEqual(result[0]["external_mappings"], [{"object_id": "schema:energyEfficiencyScale"}])
        self.assertEqual(result[1]["external_mappings"], [])
        self.assertIn("Role {name: $role}", client.queries[0][0])
        self.assertEqual(client.queries[0][1], {"role": "consumer", "event": "purchase", "product_type": "dishwasher"})

    def test_create_dpp_template_rejects_empty_terms(self) -> None:
        with self.assertRaises(ValueError):
            run(knowledge_graph.create_dpp_template(FakeNeo4jClient(), "Empty", ["", None]))  # type: ignore[list-item]

    def test_create_dpp_template_writes_user_template_and_terms(self) -> None:
        client = FakeNeo4jClient(query_results=[[{"field_name": "energy_label", "template_count": 2}]])

        result = run(knowledge_graph.create_dpp_template(
            client,
            "Consumer label",
            ["energy_label", "energy_label", "manufacturer"],
            role="consumer",
            event="purchase",
            product_type="dishwasher",
            user_id="u1",
        ))

        self.assertEqual(result["terms"], ["energy_label", "manufacturer"])
        self.assertEqual(result["promoted_terms"], [{"field_name": "energy_label", "template_count": 2}])
        self.assertEqual(len(client.writes), 3)
        self.assertEqual(client.writes[0][1]["template_name"], "Consumer label")
        written_terms = [write[1]["term"] for write in client.writes[1:]]
        self.assertEqual(written_terms, ["energy_label", "manufacturer"])

    def test_create_dpp_template_stores_custom_context_and_pseudonymous_user(self) -> None:
        client = FakeNeo4jClient(query_results=[[]])

        result = run(knowledge_graph.create_dpp_template(
            client,
            "Inverter check",
            ["components"],
            role="repairer",
            product_type="solar_panel",
            user_id="alice@example.org",
            custom_event="  Inverter inspection ",
            lifecycle_phase="middle_of_life",
        ))

        params = client.writes[0][1]
        self.assertEqual(params["custom_event"], "Inverter inspection")
        self.assertEqual(params["lifecycle_phase"], "middle_of_life")
        self.assertIsNone(params["event"])
        # the client identifier itself is never written to Neo4j
        self.assertNotIn("alice@example.org", json.dumps(client.writes))
        self.assertEqual(params["user_id"], knowledge_graph.internal_user_id("alice@example.org"))
        self.assertEqual(result["custom_event"], "Inverter inspection")

    def test_internal_user_id_is_stable_pseudonymous_and_keeps_anonymous(self) -> None:
        first = knowledge_graph.internal_user_id("client-1")
        self.assertEqual(first, knowledge_graph.internal_user_id(" client-1 "))
        self.assertNotEqual(first, knowledge_graph.internal_user_id("client-2"))
        self.assertTrue(first.startswith("u-"))
        self.assertNotIn("client-1", first)
        self.assertEqual(knowledge_graph.internal_user_id("anonymous"), "anonymous")
        self.assertEqual(knowledge_graph.internal_user_id(""), "anonymous")
        self.assertEqual(knowledge_graph.internal_user_id(None), "anonymous")

    def test_template_context_derives_and_validates_lifecycle_phase(self) -> None:
        normalize = knowledge_graph.normalize_template_context
        self.assertEqual(normalize({"event": "maintenance", "lifecycle_phase": None})["lifecycle_phase"],
                         "middle_of_life")
        self.assertEqual(normalize({"event": None, "lifecycle_phase": "end_of_life"})["lifecycle_phase"],
                         "end_of_life")
        with self.assertRaises(ValueError):
            normalize({"event": "recycling", "lifecycle_phase": "beginning_of_life"})
        with self.assertRaises(ValueError):
            normalize({"lifecycle_phase": "afterlife"})
        with self.assertRaises(ValueError):
            normalize({"custom_event": "x" * 101})
        # partial update: a phase that contradicts the stored event is rejected
        with self.assertRaises(ValueError):
            normalize({"lifecycle_phase": "end_of_life"}, {"event": "maintenance"})
        # partial update: changing only the custom event name leaves the phase untouched
        self.assertEqual(normalize({"custom_event": "Check"}, {"event": "maintenance"}), {"custom_event": "Check"})
        # partial update: a new event moves the phase along
        self.assertEqual(normalize({"event": "recycling"}, {"event": "maintenance"}),
                         {"event": "recycling", "lifecycle_phase": "end_of_life"})

    def test_update_dpp_template_keeps_properties_that_are_not_sent(self) -> None:
        stored = {"id": "T1", "role": "repairer", "event": None, "product_type": "solar_panel",
                  "custom_event": "Inverter inspection", "lifecycle_phase": "middle_of_life"}
        client = FakeNeo4jClient(query_results=[[stored], []])

        result = run(knowledge_graph.update_dpp_template(
            client, "T1", "Renamed", ["components", "repair_history"], {"role": "repairer"},
        ))

        set_query, params = client.writes[0]
        self.assertIn("SET tpl += $changes", set_query)
        self.assertEqual(params["changes"], {"role": "repairer"})
        self.assertEqual(result["product_type"], "solar_panel")
        self.assertEqual(result["custom_event"], "Inverter inspection")
        self.assertEqual(result["terms"], ["components", "repair_history"])

    def test_update_dpp_template_returns_none_for_unknown_template(self) -> None:
        client = FakeNeo4jClient(query_results=[[]])
        self.assertIsNone(run(knowledge_graph.update_dpp_template(client, "missing", "x", ["a"], {})))
        self.assertEqual(client.writes, [])

    def test_dynamic_recommendations_match_templates_by_lifecycle_phase(self) -> None:
        client = FakeNeo4jClient(query_results=[[]])

        run(knowledge_graph.get_dynamic_recommended_fields(client, "solar_panel", "repairer", "maintenance"))

        query, params = client.queries[0]
        self.assertIn("t.lifecycle_phase = $phase", query)
        self.assertEqual(params["phase"], "middle_of_life")
        self.assertEqual(params["event"], "maintenance")

    def test_get_graph_statistics_counts_static_dynamic_and_relationships(self) -> None:
        client = FakeNeo4jClient([
            [{"count": 5}],
            [{"count": 6}],
            [{"count": 7}],
            [{"count": 8}],
            [{"count": 9}],
            [{"count": 10}],
            [{"count": 11}],
            [{"label": "DPPTemplate", "count": 2}, {"label": "TemplateTerm", "count": 4}],
            [{"count": 12}],
        ])

        stats = run(knowledge_graph.get_graph_statistics(client))

        self.assertEqual(stats["role_count"], 5)
        self.assertEqual(stats["datafield_count"], 8)
        self.assertEqual(stats["dpptemplate_count"], 2)
        self.assertEqual(stats["templateterm_count"], 4)
        self.assertEqual(stats["templateuser_count"], 0)
        self.assertEqual(stats["needs_relationships"], 12)


class Neo4jClientTests(unittest.TestCase):
    def test_connect_verifies_connectivity_and_close_closes_driver(self) -> None:
        driver = FakeDriver()

        with patch("app.neo4j_client.AsyncGraphDatabase.driver", return_value=driver) as driver_factory:
            client = Neo4jClient("bolt://neo4j:7687", "neo4j", "secret")
            run(client.connect())
            run(client.close())

        driver_factory.assert_called_once_with("bolt://neo4j:7687", auth=("neo4j", "secret"))
        self.assertTrue(driver.verified)
        self.assertTrue(driver.closed)

    def test_run_query_returns_records_from_async_session(self) -> None:
        driver = FakeDriver()
        client = Neo4jClient("bolt://neo4j:7687", "neo4j", "secret")
        client._driver = driver

        result = run(client.run_query("MATCH (r:Role) RETURN r.name AS name", {"limit": 1}))

        self.assertEqual(result, [{"name": "consumer"}])
        self.assertEqual(driver.session_obj.runs, [("MATCH (r:Role) RETURN r.name AS name", {"limit": 1})])

    def test_run_write_executes_query_without_fetching_records(self) -> None:
        driver = FakeDriver()
        client = Neo4jClient("bolt://neo4j:7687", "neo4j", "secret")
        client._driver = driver

        run(client.run_write("CREATE (:Role {name: $name})", {"name": "consumer"}))

        self.assertEqual(driver.session_obj.runs, [("CREATE (:Role {name: $name})", {"name": "consumer"})])

    def test_session_requires_connected_driver(self) -> None:
        client = Neo4jClient("bolt://neo4j:7687", "neo4j", "secret")

        with self.assertRaises(RuntimeError):
            run(client.run_query("MATCH (n) RETURN n"))


if __name__ == "__main__":
    unittest.main()
