"""SSSOM parsing helpers for ontology mappings."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


DEFAULT_SSSOM_PATH = Path(__file__).resolve().parents[1] / "ontology" / "sssom_mappings.tsv"


def load_sssom_mapping_set(path: Path = DEFAULT_SSSOM_PATH) -> dict[str, Any]:
    """Load a small SSSOM TSV mapping set with YAML-style metadata comments."""
    if not path.exists():
        return {"metadata": {}, "mappings": []}

    metadata: dict[str, Any] = {}
    current_metadata_section: str | None = None
    rows: list[dict[str, Any]] = []
    header: list[str] | None = None

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n\r")
            if not line:
                continue

            if line.startswith("#"):
                parsed = _parse_metadata_line(line, current_metadata_section)
                if parsed:
                    key, value, current_metadata_section = parsed
                    if current_metadata_section and key != current_metadata_section:
                        section = metadata.setdefault(current_metadata_section, {})
                        if isinstance(section, dict):
                            section[key] = value
                    else:
                        metadata[key] = value
                continue

            if header is None:
                header = next(csv.reader([line], delimiter="\t"))
                continue

            values = next(csv.reader([line], delimiter="\t"))
            row = dict(zip(header, values, strict=False))
            if row.get("subject_id") and row.get("object_id"):
                row["confidence"] = _parse_confidence(row.get("confidence"))
                row["mapping_id"] = _mapping_id(row)
                rows.append(row)

    return {"metadata": metadata, "mappings": rows}


def _parse_metadata_line(line: str, current_section: str | None) -> tuple[str, Any, str | None] | None:
    raw_content = line[1:]
    leading_spaces = len(raw_content) - len(raw_content.lstrip(" "))
    is_nested = bool(current_section and leading_spaces > 1)
    content = raw_content.strip()
    if ":" not in content:
        return None

    key, value = content.split(":", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None

    if not value:
        return key, {}, key

    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]

    return key, value, current_section if is_nested else None


def _parse_confidence(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _mapping_id(row: dict[str, Any]) -> str:
    return "|".join([
        str(row.get("subject_id", "")),
        str(row.get("predicate_id", "")),
        str(row.get("object_id", "")),
    ])
