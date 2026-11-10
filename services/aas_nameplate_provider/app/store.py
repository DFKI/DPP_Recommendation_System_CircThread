"""AAS-backed product store."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from app.aas_parser import parse_aas_nameplate


DATA_DIR = Path("/app/data")
DEFAULT_AAS_FILE = DATA_DIR / "example_digital_nameplate_aas.json"
INGESTED_AAS_FILE = DATA_DIR / "ingested_aas_documents.json"


class AasStore:
    """Loads AAS JSON documents and exposes parsed product passport fragments."""

    def __init__(self, aas_file: Path = DEFAULT_AAS_FILE, ingested_file: Path = INGESTED_AAS_FILE):
        self._aas_file = aas_file
        self._ingested_file = ingested_file
        self._products: dict[str, dict[str, Any]] = {}
        self._aas_documents: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def load(self) -> None:
        with open(self._aas_file, "r", encoding="utf-8") as f:
            aas = json.load(f)
        self.ingest(aas)
        if self._ingested_file.exists():
            with open(self._ingested_file, "r", encoding="utf-8") as f:
                for document in json.load(f).get("documents", []):
                    self.ingest(document, persist=False)

    def ingest(self, aas: dict[str, Any], persist: bool = True) -> dict[str, Any]:
        product = parse_aas_nameplate(aas)
        product_id = product["product_id"]
        with self._lock:
            self._products[product_id] = product
            self._aas_documents[product_id] = aas
            if persist:
                self._save_ingested_locked()
        return product

    def _save_ingested_locked(self) -> None:
        self._ingested_file.parent.mkdir(parents=True, exist_ok=True)
        documents = [
            document
            for product_id, document in self._aas_documents.items()
            if product_id != "SP-SUNPOWER-001"
        ]
        with open(self._ingested_file, "w", encoding="utf-8") as f:
            json.dump({"documents": documents}, f, indent=2)

    def list_products(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._products.values())

    def get_product(self, product_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._products.get(product_id)

    def get_aas(self, product_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._aas_documents.get(product_id)

    def product_types(self) -> list[str]:
        with self._lock:
            return sorted({p["product_type"] for p in self._products.values() if p.get("product_type")})
