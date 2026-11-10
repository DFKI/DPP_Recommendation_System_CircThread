"""Export the running Neo4j knowledge graph into the snapshot bundled with the repository.

The Recommendation Engine imports services/recommendation_engine/snapshot/graph_snapshot.json
automatically when it starts against an empty Neo4j database, so anyone who installs the
project gets the same knowledge graph, including the DPP templates (dynamic layer).

Run with the Docker Compose stack up:

    python scripts/export_neo4j_snapshot.py                    # http://localhost:8002
    python scripts/export_neo4j_snapshot.py --engine http://host:8002 --output other.json

To load the bundled snapshot into an existing installation, reset the database
(`docker compose down -v` removes all volumes) or replace the graph in place:

    docker compose exec recommendation-engine python -m app.graph_snapshot restore
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE_ROOT = REPO_ROOT / "services" / "recommendation_engine"
sys.path.insert(0, str(ENGINE_ROOT))

from app.graph_snapshot import SNAPSHOT_FILE, SNAPSHOT_FORMAT, write_snapshot  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", default="http://localhost:8002", help="Recommendation Engine base URL")
    parser.add_argument("--output", type=Path, default=SNAPSHOT_FILE, help="snapshot file to write")
    args = parser.parse_args()

    with urllib.request.urlopen(f"{args.engine.rstrip('/')}/graph/snapshot", timeout=120) as response:
        snapshot = json.load(response)
    if snapshot.get("format") != SNAPSHOT_FORMAT:
        print("Unexpected response from the Recommendation Engine", file=sys.stderr)
        return 1
    write_snapshot(snapshot, args.output)
    counts = ", ".join(f"{label} {count}" for label, count in snapshot["node_counts"].items())
    print(f"Wrote {len(snapshot['nodes'])} nodes ({counts}) and {snapshot['relationship_count']} relationships to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
