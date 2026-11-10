"""
Generate QR codes for all CircThread example products.

Each QR code encodes a JSON object: {"product_id": "...", "role": "...", "event": "..."}
role and event are optional tiers.

Output structure:
  qr_codes/
    product_only/          -> just product_id
    role_only/             -> product_id + role
    role_and_event/        -> product_id + role + event

Run: python scripts/generate_qr_codes.py
Requires: pip install qrcode[pil]
"""

import json
import os
from pathlib import Path

try:
    import qrcode
    from qrcode.image.styledpil import StyledPilImage
except ImportError:
    raise SystemExit(
        "Missing dependency. Install with:  pip install qrcode[pil]"
    )

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

PRODUCTS = [
    "WM-BOSCH-001",
    "DW-SIEMENS-001",
    "BL-VAILLANT-001",
    "SP-SUNPOWER-001",
    "LB-LG-001",
]

ROLES = ["consumer", "recycler", "manufacturer", "repairer", "collector"]

# Meaningful role+event combinations that reflect real use cases
ROLE_EVENT_PAIRS = [
    ("consumer",     "purchase"),
    ("repairer",     "repair"),
    ("recycler",     "recycling"),
    ("collector",    "resale"),
    ("manufacturer", "maintenance"),
    ("consumer",     "resale"),
    ("repairer",     "maintenance"),
    ("recycler",     "disposal"),
    ("collector",    "disposal"),
    ("manufacturer", "repair"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OUTPUT_ROOT = Path(__file__).parent.parent / "qr_codes"

DIRS = {
    "product_only":  OUTPUT_ROOT / "product_only",
    "role_only":     OUTPUT_ROOT / "role_only",
    "role_and_event": OUTPUT_ROOT / "role_and_event",
}


def make_qr(data: dict) -> qrcode.QRCode:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    qr = qrcode.QRCode(
        version=None,           # auto-size
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    return qr


def save_qr(data: dict, path: Path) -> None:
    qr = make_qr(data)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(str(path))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    for d in DIRS.values():
        d.mkdir(parents=True, exist_ok=True)

    generated = []

    # Tier 1 – product only
    for product_id in PRODUCTS:
        data = {"product_id": product_id}
        filename = f"{product_id}.png"
        path = DIRS["product_only"] / filename
        save_qr(data, path)
        generated.append(("product_only", filename, json.dumps(data, separators=(",", ":"))))

    # Tier 2 – product + role
    for product_id in PRODUCTS:
        for role in ROLES:
            data = {"product_id": product_id, "role": role}
            filename = f"{product_id}_{role}.png"
            path = DIRS["role_only"] / filename
            save_qr(data, path)
            generated.append(("role_only", filename, json.dumps(data, separators=(",", ":"))))

    # Tier 3 – product + role + event
    for product_id in PRODUCTS:
        for role, event in ROLE_EVENT_PAIRS:
            data = {"product_id": product_id, "role": role, "event": event}
            filename = f"{product_id}_{role}_{event}.png"
            path = DIRS["role_and_event"] / filename
            save_qr(data, path)
            generated.append(("role_and_event", filename, json.dumps(data, separators=(",", ":"))))

    # Summary
    col_w = [14, 48, 55]
    header = f"{'Subfolder':<{col_w[0]}}  {'Filename':<{col_w[1]}}  {'Encoded JSON':<{col_w[2]}}"
    print(f"\nGenerated {len(generated)} QR codes in {OUTPUT_ROOT}\n")
    print(header)
    print("-" * sum(col_w + [4]))
    for subfolder, filename, payload in generated:
        print(f"{subfolder:<{col_w[0]}}  {filename:<{col_w[1]}}  {payload}")
    print()


if __name__ == "__main__":
    main()
