"""Reproducible functional validation of the DPP prototype.

Queries the running Resolver for every product in the provider catalogue and every
combination of the five roles and six lifecycle events, checks the validation
criteria described in Section 4.1 of the paper, and writes raw results and a summary.

Usage (stack must be running, e.g. via docker compose up):

    # Regular validation (functional_validation.csv, summary.json)
    python evaluation/run_functional_validation.py --resolver http://localhost:8001 --reps 5

    # Provider unavailability scenario: the named provider is made unreachable for the
    # duration of the run (its registry entry is redirected to a closed port and restored
    # afterwards). Results are written to functional_validation_outage_<provider>.csv and
    # summary_outage_<provider>.json and compared with the regular run, if present.
    python evaluation/run_functional_validation.py --simulate-outage "Recycling EOL Provider"
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import re
import statistics
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_FILE = REPO_ROOT / "services" / "recommendation_engine" / "app" / "seed_data.py"
ROLES = ["recycler", "consumer", "manufacturer", "repairer", "collector"]
EVENTS = ["purchase", "repair", "recycling", "maintenance", "disposal", "resale"]
STATIC_SOURCES = {"role_event"}
# Unreachable address used to simulate a stopped provider: inside the Resolver container
# nothing listens on port 9, so every request fails immediately with "connection refused".
UNREACHABLE_BASE_URL = "http://127.0.0.1:9"


def load_kg_definition() -> tuple[dict, dict]:
    """Read ROLE_EVENT_MAPPINGS and PRODUCT_TYPE_FIELDS from seed_data.py without Neo4j."""
    src = SEED_FILE.read_text(encoding="utf-8").split("async def seed_knowledge_graph")[0]
    src = src.replace("from app.neo4j_client import Neo4jClient", "")
    src = src.replace("from app.sssom import load_sssom_mapping_set", "")
    ns: dict = {"__file__": str(SEED_FILE), "__name__": "seed_data"}
    exec(src, ns)  # noqa: S102 - trusted file from this repository
    return ns["ROLE_EVENT_MAPPINGS"], ns["PRODUCT_TYPE_FIELDS"]


def non_empty(value) -> bool:
    return value not in (None, [], {}, "")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def fields_by_provider(fields: list[dict]) -> dict[str, int]:
    """Count the recommended fields with a value per contributing provider (cf. Table 4)."""
    counts: dict[str, int] = {}
    for field in fields:
        if non_empty(field.get("value")):
            for provider in field.get("sources") or []:
                counts[provider] = counts.get(provider, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


@contextmanager
def simulated_outage(client: httpx.Client, registry: str, provider: str):
    """Make one registered provider unreachable and restore its registry entry afterwards."""
    services = client.get(f"{registry}/services").json()
    matches = [s for s in services if provider.lower() in s.get("name", "").lower()]
    if len(matches) != 1:
        names = ", ".join(s.get("name", "") for s in services)
        raise SystemExit(f"--simulate-outage '{provider}' must match exactly one provider. Registered: {names}")
    service = matches[0]
    original = service["base_url"]
    client.put(f"{registry}/services/{service['id']}", json={"base_url": UNREACHABLE_BASE_URL}).raise_for_status()
    print(f"Simulating outage of '{service['name']}' ({original} -> {UNREACHABLE_BASE_URL})")
    try:
        yield service["name"]
    finally:
        client.put(f"{registry}/services/{service['id']}", json={"base_url": original}).raise_for_status()
        print(f"Restored '{service['name']}' ({original})")


def run_queries(client: httpx.Client, resolver: str, products: list[dict], reps: int,
                mappings: dict, product_type_fields: dict) -> list[dict]:
    # Fields available for a product across all providers (raw view, no role/event filtering).
    raw_available = {}
    for product in products:
        raw = client.get(f"{resolver}/resolve/{product['product_id']}/raw").json()["raw_data"]
        raw_available[product["product_id"]] = sum(
            1 for k, v in raw.items() if not k.startswith("_") and k != "data_sources" and non_empty(v)
        )

    rows = []
    for product, (role, event) in itertools.product(products, itertools.product(ROLES, EVENTS)):
        pid = product["product_id"]
        times, data, status = [], None, None
        for _ in range(reps):
            t0 = time.perf_counter()
            response = client.get(f"{resolver}/resolve/{pid}", params={"role": role, "event": event})
            times.append((time.perf_counter() - t0) * 1000)
            status = response.status_code
            try:
                data = response.json()
            except ValueError:
                data = {"error": "invalid JSON response"}
        # Critical failure: the pipeline itself failed (non-200 status or invalid response).
        # A graceful "no data" answer (product unknown or providers unavailable) is not one.
        if status != 200 or not isinstance(data, dict) or ("error" in data and "error_reason" not in data):
            outcome = "pipeline_error"
        elif "error" in data:
            outcome = data["error_reason"]
        else:
            outcome = "ok"
        rec = data.get("recommendation") or {}
        fields = rec.get("recommended_fields", [])
        suggestions = rec.get("suggested_fields", [])
        selection = data.get("provider_selection") or {}
        ptype = data.get("product_type")
        static = {f["field_name"]: f["priority"] for f in fields if f["recommendation_source"] in STATIC_SOURCES}
        modelled = (role, event) in mappings
        expected = {k: v for k, v in mappings.get((role, event), {}).items() if k in product_type_fields.get(ptype, [])}
        by_source: dict[str, int] = {}
        for f in fields + suggestions:
            by_source[f["recommendation_source"]] = by_source.get(f["recommendation_source"], 0) + 1
        rows.append({
            "product_id": pid,
            "product_type": ptype,
            "role": role,
            "event": event,
            "modelled_combination": modelled,
            "filter_mode": rec.get("filter_mode"),
            "http_status": status,
            "outcome": outcome,
            "c1_no_error": "error" not in data and bool(rec),
            "c2_static_matches_kg": static == expected if modelled else None,
            "c3_values_attributed": all(f["sources"] for f in fields if non_empty(f["value"])),
            "c4_gaps_reported": sorted(rec.get("data_gaps", [])) == sorted(f["field_name"] for f in fields if not non_empty(f["value"])),
            "providers_queried": len(selection.get("queried", [])),
            "providers_skipped": len(selection.get("excluded", [])),
            "providers_unavailable": ";".join(u["name"] for u in selection.get("unavailable", [])),
            "providers_with_data": ";".join(data.get("sources", [])),
            "fields_by_provider": json.dumps(fields_by_provider(fields)),
            "conflicting_fields": len(data.get("conflicts", {})),
            "fields_available": raw_available[pid],
            "fields_in_queried_providers": rec.get("total_fields_available"),
            "recommended": len(fields),
            "recommended_non_empty": sum(1 for f in fields if non_empty(f["value"])),
            "data_gaps": len(rec.get("data_gaps", [])),
            "suggestions": len(suggestions),
            "economic_in_view": sum(1 for f in fields if f["category"] == "economic" and non_empty(f["value"])),
            "by_source": json.dumps(by_source, sort_keys=True),
            "median_ms": round(statistics.median(times), 1),
            "provider_requests_ms": selection.get("provider_requests_ms"),
        })
    return rows


def summarise(rows: list[dict], products: list[dict]) -> dict:
    modelled = [r for r in rows if r["modelled_combination"]]
    unmodelled = [r for r in rows if not r["modelled_combination"]]
    med = statistics.median
    return {
        "queries": len(rows),
        "products": len(products),
        "c1_no_error": sum(r["c1_no_error"] for r in rows),
        "critical_failures": sum(1 for r in rows if r["outcome"] == "pipeline_error"),
        "outcomes": dict(sorted(Counter(r["outcome"] for r in rows).items())),
        "c3_values_attributed": sum(r["c3_values_attributed"] for r in rows),
        "c4_gaps_reported": sum(r["c4_gaps_reported"] for r in rows),
        "modelled_queries": len(modelled),
        "c2_static_matches_kg_modelled": sum(bool(r["c2_static_matches_kg"]) for r in modelled),
        "median_recommended_modelled": med(r["recommended"] for r in modelled),
        "range_recommended_modelled": [min(r["recommended"] for r in modelled), max(r["recommended"] for r in modelled)],
        "median_recommended_non_empty_modelled": med(r["recommended_non_empty"] for r in modelled),
        "median_fields_available": med(r["fields_available"] for r in modelled),
        "median_share_displayed_modelled": round(med(r["recommended_non_empty"] / r["fields_available"] for r in modelled), 3),
        "median_suggestions_modelled": med(r["suggestions"] for r in modelled),
        "unmodelled_queries": len(unmodelled),
        "unmodelled_filter_modes": sorted({r["filter_mode"] for r in unmodelled}),
        "median_recommended_non_empty_unmodelled": med(r["recommended_non_empty"] for r in unmodelled) if unmodelled else None,
        "median_providers_queried": med(r["providers_queried"] for r in rows),
        "median_providers_skipped": med(r["providers_skipped"] for r in rows),
        "queries_with_skipped_providers": sum(1 for r in rows if r["providers_skipped"] > 0),
        "queries_with_unavailable_providers": sum(1 for r in rows if r["providers_unavailable"]),
        "queries_with_conflicts": sum(1 for r in rows if r["conflicting_fields"] > 0),
        "median_response_ms": med(r["median_ms"] for r in rows),
        "p95_response_ms": sorted(r["median_ms"] for r in rows)[int(0.95 * (len(rows) - 1))],
        "median_provider_requests_ms": med(r["provider_requests_ms"] for r in rows if r["provider_requests_ms"] is not None),
    }


def compare_with_baseline(rows: list[dict], baseline_file: Path, provider: str) -> dict:
    """Add the data gaps of the regular run to each row and summarise the outage effect."""
    if not baseline_file.exists():
        return {"baseline": None}
    with open(baseline_file, newline="", encoding="utf-8") as fh:
        baseline = {(r["product_id"], r["role"], r["event"]): r for r in csv.DictReader(fh)}
    affected = []
    for row in rows:
        base = baseline.get((row["product_id"], row["role"], row["event"]))
        row["baseline_data_gaps"] = int(base["data_gaps"]) if base else None
        if base and row["data_gaps"] > int(base["data_gaps"]):
            affected.append(row)
    return {
        "baseline": baseline_file.name,
        "outage_provider": provider,
        "queries_with_additional_gaps": len(affected),
        "examples": [
            {
                "product_id": r["product_id"], "role": r["role"], "event": r["event"],
                "recommended": r["recommended"], "data_gaps": r["data_gaps"],
                "baseline_data_gaps": r["baseline_data_gaps"],
            }
            for r in affected
            if (r["product_id"], r["role"], r["event"]) in {
                ("WM-BOSCH-001", "recycler", "recycling"),
                ("WM-BOSCH-001", "repairer", "repair"),
                ("LB-LG-001", "recycler", "recycling"),
            }
        ],
    }


def write_results(out: Path, rows: list[dict], summary: dict, suffix: str = "") -> None:
    fieldnames = list(rows[0])
    with open(out / f"functional_validation{suffix}.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    (out / f"summary{suffix}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolver", default="http://localhost:8001")
    ap.add_argument("--registry", default="http://localhost:8003")
    ap.add_argument("--reps", type=int, default=5, help="repetitions per query for timing")
    ap.add_argument("--out", default=str(REPO_ROOT / "evaluation" / "results"))
    ap.add_argument("--simulate-outage", metavar="PROVIDER",
                    help="name (or unique part of the name) of a registered provider to make unreachable")
    args = ap.parse_args()

    mappings, product_type_fields = load_kg_definition()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(timeout=60)
    # The product catalogue is read before an outage starts, so that the same products
    # are queried in both runs.
    products = client.get(f"{args.resolver}/products").json()["products"]

    if not args.simulate_outage:
        rows = run_queries(client, args.resolver, products, args.reps, mappings, product_type_fields)
        write_results(out, rows, summarise(rows, products))
        return

    with simulated_outage(client, args.registry, args.simulate_outage) as provider_name:
        rows = run_queries(client, args.resolver, products, args.reps, mappings, product_type_fields)
    summary = summarise(rows, products)
    summary["outage"] = compare_with_baseline(rows, out / "functional_validation.csv", provider_name)
    write_results(out, rows, summary, suffix=f"_outage_{slug(provider_name)}")


if __name__ == "__main__":
    main()
