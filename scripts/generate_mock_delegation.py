"""Regenerate services/mock_providers/app/delegation.py from the provider product data.

Run: python scripts/generate_mock_delegation.py
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTITY_FIELDS = {"product_id", "product_type", "manufacturer", "model", "brand_name", "serial_number"}


def _load(path: Path):
    # The Mock Provider imports `app.delegation`; provide a stub so that the raw product
    # data can be loaded without the generated module (which may be outdated or missing).
    stub = types.ModuleType("app.delegation")
    stub.DELEGATED_FIELDS = {}
    sys.modules.setdefault("app", types.ModuleType("app"))
    sys.modules["app.delegation"] = stub
    spec = importlib.util.spec_from_file_location(path.parent.parent.name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PRODUCTS


def _non_empty(value) -> bool:
    return value not in (None, [], {}, "")


def main() -> None:
    mock = _load(ROOT / "services/mock_providers/app/product_data.py")
    specialised = [
        _load(ROOT / "services/recycling_eol_provider/app/product_data.py"),
        _load(ROOT / "services/midlife_purchase_provider/app/product_data.py"),
        _load(ROOT / "services/repair_service_provider/app/product_data.py"),
    ]
    target = ROOT / "services/mock_providers/app/delegation.py"
    header, _, _ = target.read_text(encoding="utf-8").partition("DELEGATED_FIELDS")
    lines = [header.rstrip("\n"), "", "DELEGATED_FIELDS: dict[str, frozenset[str]] = {"]
    for product_id, product in mock.items():
        delegated = set()
        for provider in specialised:
            delegated |= {k for k, v in provider.get(product_id, {}).items() if _non_empty(v) and not k.startswith("_")}
        fields = sorted((delegated - IDENTITY_FIELDS) & set(product))
        lines.append(f'    "{product_id}": frozenset({{')
        lines.extend(f'        "{field}",' for field in fields)
        lines.append("    }),")
    lines += ["}", ""]
    target.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
