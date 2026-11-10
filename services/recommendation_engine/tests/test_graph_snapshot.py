"""Tests for the portable Neo4j graph snapshot and the bundled snapshot file."""

from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import neo4j.time

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
for path in (SERVICE_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from app import graph_snapshot, seed_data  # noqa: E402
from app import main as engine_main  # noqa: E402


def run(coro):
    return asyncio.run(coro)


class RecordingClient:
    """Minimal stand-in for Neo4jClient that returns queued query results."""

    def __init__(self, query_results: list[list[dict]] | None = None):
        self.query_results = list(query_results or [])
        self.queries: list[str] = []
        self.writes: list[tuple[str, dict | None]] = []

    async def run_query(self, query: str, parameters: dict | None = None) -> list[dict]:
        self.queries.append(query)
        return self.query_results.pop(0) if self.query_results else []

    async def run_write(self, query: str, parameters: dict | None = None) -> None:
        self.writes.append((query, parameters))


def sample_graph() -> tuple[list[dict], list[dict]]:
    created = neo4j.time.DateTime(2026, 11, 10, 12, 50, 25, 902000000, tzinfo=neo4j.time.timezone.utc) \
        if hasattr(neo4j.time, "timezone") else neo4j.time.DateTime.from_iso_format("2026-11-10T12:50:25.902000000+00:00")
    nodes = [
        {"eid": "4:x:2", "labels": ["DPPTemplate"], "props": {"id": "t-1", "name": "Demo", "created_at": created}},
        {"eid": "4:x:1", "labels": ["DataField"], "props": {"name": "repair_history", "category": "maintenance"}},
        {"eid": "4:x:3", "labels": ["TemplateTerm"], "props": {"name": "repair_history", "aliases": ["a", "b"]}},
    ]
    rels = [
        {"start": "4:x:2", "end": "4:x:3", "type": "REQUESTS", "props": {}},
        {"start": "4:x:3", "end": "4:x:1", "type": "REFERS_TO", "props": {"weight": 0.5}},
    ]
    return nodes, rels


class SnapshotFormatTests(unittest.TestCase):
    def test_export_is_deterministic_and_encodes_temporal_values(self) -> None:
        nodes, rels = sample_graph()
        first = run(graph_snapshot.export_graph(RecordingClient([nodes, rels])))
        second = run(graph_snapshot.export_graph(RecordingClient([list(reversed(nodes)), list(reversed(rels))])))
        self.assertEqual(first["nodes"], second["nodes"])
        self.assertEqual(first["relationships"], second["relationships"])
        template = next(n for n in first["nodes"] if n["labels"] == ["DPPTemplate"])
        self.assertEqual(template["properties"]["created_at"]["$type"], "DateTime")
        self.assertEqual(first["node_counts"], {"DPPTemplate": 1, "DataField": 1, "TemplateTerm": 1})

    def test_write_and_load_round_trip(self) -> None:
        nodes, rels = sample_graph()
        snapshot = run(graph_snapshot.export_graph(RecordingClient([nodes, rels])))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "graph.json"
            graph_snapshot.write_snapshot(snapshot, path)
            loaded = graph_snapshot.load_snapshot(path)
        self.assertEqual(loaded["nodes"], snapshot["nodes"])
        self.assertEqual(loaded["relationships"], snapshot["relationships"])
        decoded = graph_snapshot._decode_props(loaded["nodes"][0]["properties"])
        self.assertIsInstance(decoded["created_at"], neo4j.time.DateTime)

    def test_import_creates_nodes_then_relationships_and_cleans_up(self) -> None:
        nodes, rels = sample_graph()
        snapshot = run(graph_snapshot.export_graph(RecordingClient([nodes, rels])))
        client = RecordingClient([[{"count": 0}]])
        result = run(graph_snapshot.import_graph(client, snapshot))
        self.assertEqual(result, {"nodes": 3, "relationships": 2})
        statements = [query for query, _ in client.writes]
        self.assertTrue(any("CREATE (n:`DPPTemplate`:`_SnapshotImport`)" in q for q in statements))
        self.assertTrue(any("CREATE (a)-[r:`REFERS_TO`]->(b)" in q for q in statements))
        self.assertIn("REMOVE n:_SnapshotImport", statements[-2])
        self.assertIn("DROP INDEX snapshot_import", statements[-1])

    def test_import_refuses_non_empty_graph_unless_replace(self) -> None:
        snapshot = {"format": graph_snapshot.SNAPSHOT_FORMAT, "nodes": [], "relationships": []}
        with self.assertRaises(RuntimeError):
            run(graph_snapshot.import_graph(RecordingClient([[{"count": 5}]]), snapshot))
        client = RecordingClient([[{"count": 5}]])
        run(graph_snapshot.import_graph(client, snapshot, replace=True))
        self.assertIn("DETACH DELETE", client.writes[0][0])

    def test_invalid_labels_are_rejected(self) -> None:
        snapshot = {"nodes": [{"id": 0, "labels": ["Bad`) DETACH DELETE (x"], "properties": {}}], "relationships": []}
        client = RecordingClient([[{"count": 0}]])
        with self.assertRaises(ValueError):
            run(graph_snapshot.import_graph(client, snapshot))
        self.assertTrue(any("DETACH DELETE" in q and "_SnapshotImport" in q for q, _ in client.writes))

    def test_startup_imports_snapshot_only_into_empty_database(self) -> None:
        for empty, expected_imports in ((True, 1), (False, 0)):
            import_graph, seed = AsyncMock(), AsyncMock()
            with patch.multiple(
                engine_main,
                graph_is_empty=AsyncMock(return_value=empty),
                load_snapshot=lambda: {"nodes": [{"id": 0}], "relationships": []},
                import_graph=import_graph,
                ensure_constraints=AsyncMock(),
                check_seed_status=AsyncMock(return_value=True),
                check_static_layer_current=AsyncMock(return_value=True),
                check_sssom_seed_status=AsyncMock(return_value=True),
                seed_knowledge_graph=seed,
            ):
                run(engine_main.initialise_graph(RecordingClient()))
            self.assertEqual(import_graph.await_count, expected_imports)
            seed.assert_not_awaited()

    def test_startup_reseeds_outdated_static_layer(self) -> None:
        seed = AsyncMock()
        with patch.multiple(
            engine_main,
            graph_is_empty=AsyncMock(return_value=False),
            check_seed_status=AsyncMock(return_value=True),
            check_static_layer_current=AsyncMock(return_value=False),
            seed_knowledge_graph=seed,
        ):
            run(engine_main.initialise_graph(RecordingClient()))
        seed.assert_awaited_once()


class BundledSnapshotTests(unittest.TestCase):
    """The snapshot shipped with the repository must match the ontology in seed_data.py."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = graph_snapshot.load_snapshot()
        if cls.snapshot is None:
            raise unittest.SkipTest("no bundled snapshot")

    def nodes(self, label: str) -> list[dict]:
        return [n for n in self.snapshot["nodes"] if label in n["labels"]]

    def test_static_layer_matches_seed_data(self) -> None:
        fields = {(n["properties"]["name"], n["properties"]["category"]) for n in self.nodes("DataField")}
        self.assertEqual(fields, {(name, category) for name, _l, category, _d in seed_data.DATA_FIELDS})
        names = {n["id"]: n["properties"].get("name") for n in self.snapshot["nodes"]}
        needs = {
            (names[r["start"]], r["properties"]["event"], names[r["end"]], r["properties"]["priority"])
            for r in self.snapshot["relationships"] if r["type"] == "NEEDS"
        }
        expected = {
            (role, event, field, priority)
            for (role, event), priorities in seed_data.ROLE_EVENT_MAPPINGS.items()
            for field, priority in priorities.items()
        }
        self.assertEqual(needs, expected, "re-export the snapshot: python scripts/export_neo4j_snapshot.py")

    def test_template_layer_is_consistent(self) -> None:
        ids = {n["id"]: n for n in self.snapshot["nodes"]}
        for rel in self.snapshot["relationships"]:
            self.assertIn(rel["start"], ids)
            self.assertIn(rel["end"], ids)
        for user in self.nodes("TemplateUser"):
            self.assertRegex(user["properties"]["user_id"], r"^u-[0-9a-f]{24}$", "only pseudonymous user IDs")


if __name__ == "__main__":
    unittest.main()
