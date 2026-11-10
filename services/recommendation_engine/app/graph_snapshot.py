"""Export and import of the complete Neo4j knowledge graph as a portable JSON snapshot.

The snapshot bundled with the repository (services/recommendation_engine/snapshot/
graph_snapshot.json) ships the knowledge graph, including the dynamic template layer, to
anyone who installs the project: the Recommendation Engine imports it on start-up when the
Neo4j database is empty. The format is independent of the Neo4j store version, unlike a
`neo4j-admin database dump`.

Command line (inside the recommendation-engine container):

    python -m app.graph_snapshot export [path]    # write the current graph
    python -m app.graph_snapshot restore [path]   # replace the graph with a snapshot
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # the writer functions are also used by scripts/export_neo4j_snapshot.py
    from app.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

SNAPSHOT_FORMAT = "circthread-neo4j-snapshot"
SNAPSHOT_VERSION = 1
SNAPSHOT_FILE = Path(__file__).resolve().parents[1] / "snapshot" / "graph_snapshot.json"

_IMPORT_LABEL = "_SnapshotImport"
_IMPORT_KEY = "_snapshot_id"
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TEMPORAL_TYPES = ("DateTime", "Date", "Time")
_BATCH_SIZE = 500


# ───────────────────────────── value encoding ─────────────────────────────

def _encode(value: Any) -> Any:
    """Make a Neo4j property value JSON-serialisable; temporal values are tagged."""
    import neo4j.time

    for type_name in _TEMPORAL_TYPES:
        if isinstance(value, getattr(neo4j.time, type_name)):
            return {"$type": type_name, "value": value.iso_format()}
    if isinstance(value, list):
        return [_encode(v) for v in value]
    return value


def _decode(value: Any) -> Any:
    import neo4j.time

    if isinstance(value, dict) and value.get("$type") in _TEMPORAL_TYPES:
        return getattr(neo4j.time, value["$type"]).from_iso_format(value["value"])
    if isinstance(value, list):
        return [_decode(v) for v in value]
    return value


def _encode_props(props: dict) -> dict:
    return {key: _encode(props[key]) for key in sorted(props)}


def _decode_props(props: dict) -> dict:
    return {key: _decode(value) for key, value in props.items()}


def _identifier(name: str) -> str:
    if not _IDENTIFIER.match(name):
        raise ValueError(f"Invalid label or relationship type in snapshot: {name!r}")
    return f"`{name}`"


# ───────────────────────────── export ─────────────────────────────

async def export_graph(client: "Neo4jClient") -> dict:
    """Read the whole graph into a deterministic, JSON-serialisable snapshot."""
    nodes = await client.run_query(
        "MATCH (n) RETURN elementId(n) AS eid, labels(n) AS labels, properties(n) AS props"
    )
    rels = await client.run_query(
        """
        MATCH (a)-[r]->(b)
        RETURN elementId(a) AS start, elementId(b) AS end, type(r) AS type, properties(r) AS props
        """
    )

    def node_key(node: dict) -> str:
        return json.dumps([sorted(node["labels"]), _encode_props(node["props"])], sort_keys=True, default=str)

    ordered = sorted(nodes, key=node_key)
    ids = {node["eid"]: index for index, node in enumerate(ordered)}
    node_rows = [
        {"id": ids[node["eid"]], "labels": sorted(node["labels"]), "properties": _encode_props(node["props"])}
        for node in ordered
    ]
    rel_rows = sorted(
        (
            {"start": ids[rel["start"]], "end": ids[rel["end"]], "type": rel["type"],
             "properties": _encode_props(rel["props"])}
            for rel in rels
        ),
        key=lambda r: json.dumps([r["start"], r["type"], r["end"], r["properties"]], sort_keys=True),
    )
    counts: dict[str, int] = defaultdict(int)
    for row in node_rows:
        for label in row["labels"]:
            counts[label] += 1
    return {
        "format": SNAPSHOT_FORMAT,
        "version": SNAPSHOT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "node_counts": dict(sorted(counts.items())),
        "relationship_count": len(rel_rows),
        "nodes": node_rows,
        "relationships": rel_rows,
    }


def write_snapshot(snapshot: dict, path: Path = SNAPSHOT_FILE) -> None:
    """Write a snapshot with one node or relationship per line (readable diffs)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    header = {k: v for k, v in snapshot.items() if k not in ("nodes", "relationships")}
    lines = ["{"]
    for key, value in header.items():
        lines.append(f"  {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)},")
    for key in ("nodes", "relationships"):
        rows = snapshot[key]
        lines.append(f'  "{key}": [')
        lines.extend(
            "    " + json.dumps(row, ensure_ascii=False, sort_keys=True) + ("," if i < len(rows) - 1 else "")
            for i, row in enumerate(rows)
        )
        lines.append("  ]," if key == "nodes" else "  ]")
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_snapshot(path: Path = SNAPSHOT_FILE) -> dict | None:
    if not path.exists():
        return None
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if snapshot.get("format") != SNAPSHOT_FORMAT:
        raise ValueError(f"{path} is not a {SNAPSHOT_FORMAT} file")
    if snapshot.get("version", 0) > SNAPSHOT_VERSION:
        raise ValueError(f"Snapshot version {snapshot.get('version')} is not supported")
    return snapshot


# ───────────────────────────── import ─────────────────────────────

async def graph_is_empty(client: "Neo4jClient") -> bool:
    result = await client.run_query("MATCH (n) RETURN count(n) AS count")
    return not result or result[0]["count"] == 0


async def import_graph(client: "Neo4jClient", snapshot: dict, *, replace: bool = False) -> dict:
    """Create all nodes and relationships of a snapshot.

    Refuses to write into a non-empty graph unless `replace` is set, in which case the
    existing graph is deleted first. Uniqueness constraints are created afterwards by the
    caller (seed_data.ensure_constraints).
    """
    if not await graph_is_empty(client):
        if not replace:
            raise RuntimeError("Neo4j already contains data; use replace=True to overwrite it")
        await client.run_write("MATCH (n) CALL { WITH n DETACH DELETE n } IN TRANSACTIONS OF 1000 ROWS")

    await client.run_write(
        f"CREATE INDEX snapshot_import IF NOT EXISTS FOR (n:{_IMPORT_LABEL}) ON (n.{_IMPORT_KEY})"
    )
    await client.run_write("CALL db.awaitIndexes(60)")
    try:
        await _create_nodes_and_relationships(client, snapshot)
    except Exception:
        # Leave no partial graph behind, so that the caller can fall back to seeding.
        await client.run_write(
            f"MATCH (n:{_IMPORT_LABEL}) CALL {{ WITH n DETACH DELETE n }} IN TRANSACTIONS OF 1000 ROWS"
        )
        raise
    finally:
        await client.run_write("DROP INDEX snapshot_import IF EXISTS")
    logger.info("Imported graph snapshot: %d nodes, %d relationships",
                len(snapshot["nodes"]), len(snapshot["relationships"]))
    return {"nodes": len(snapshot["nodes"]), "relationships": len(snapshot["relationships"])}


async def _create_nodes_and_relationships(client: "Neo4jClient", snapshot: dict) -> None:
    by_labels: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for node in snapshot["nodes"]:
        by_labels[tuple(node["labels"])].append(
            {"id": node["id"], "props": _decode_props(node["properties"])}
        )
    for labels, rows in by_labels.items():
        label_expr = "".join(f":{_identifier(label)}" for label in (*labels, _IMPORT_LABEL))
        for start in range(0, len(rows), _BATCH_SIZE):
            await client.run_write(
                f"UNWIND $rows AS row CREATE (n{label_expr}) SET n = row.props, n.{_IMPORT_KEY} = row.id",
                {"rows": rows[start:start + _BATCH_SIZE]},
            )

    by_type: dict[str, list[dict]] = defaultdict(list)
    for rel in snapshot["relationships"]:
        by_type[rel["type"]].append(
            {"start": rel["start"], "end": rel["end"], "props": _decode_props(rel["properties"])}
        )
    for rel_type, rows in by_type.items():
        for start in range(0, len(rows), _BATCH_SIZE):
            await client.run_write(
                f"""
                UNWIND $rows AS row
                MATCH (a:{_IMPORT_LABEL} {{{_IMPORT_KEY}: row.start}})
                MATCH (b:{_IMPORT_LABEL} {{{_IMPORT_KEY}: row.end}})
                CREATE (a)-[r:{_identifier(rel_type)}]->(b)
                SET r = row.props
                """,
                {"rows": rows[start:start + _BATCH_SIZE]},
            )

    await client.run_write(f"MATCH (n:{_IMPORT_LABEL}) REMOVE n:{_IMPORT_LABEL}, n.{_IMPORT_KEY}")


# ───────────────────────────── command line ─────────────────────────────

async def _main(argv: list[str]) -> int:
    from app.neo4j_client import Neo4jClient
    from app.seed_data import ensure_constraints
    from shared.config import settings

    if not argv or argv[0] not in ("export", "restore"):
        print(__doc__)
        return 2
    path = Path(argv[1]) if len(argv) > 1 else SNAPSHOT_FILE
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    await client.connect()
    try:
        if argv[0] == "export":
            snapshot = await export_graph(client)
            write_snapshot(snapshot, path)
            print(f"Wrote {len(snapshot['nodes'])} nodes and {snapshot['relationship_count']} relationships to {path}")
        else:
            snapshot = load_snapshot(path)
            if snapshot is None:
                print(f"No snapshot at {path}")
                return 1
            result = await import_graph(client, snapshot, replace=True)
            await ensure_constraints(client)
            print(f"Restored {result['nodes']} nodes and {result['relationships']} relationships from {path}")
    finally:
        await client.close()
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(asyncio.run(_main(sys.argv[1:])))
