"""Example product data for a custom Digital Product Memory provider.

Replace this module with calls to your real data source. The provider can
return partial product passports; the Resolver merges data from all matching
registered providers.
"""

PRODUCTS = {
    "WM-BOSCH-001": {
        "product_id": "WM-BOSCH-001",
        "product_type": "washing_machine",
        "repair_history": [
            {
                "date": "2025-04-12",
                "provider": "Starter Repair Service",
                "action": "Replaced door seal",
                "part_number": "BSH-DS-7710",
            },
            {
                "date": "2025-11-03",
                "provider": "Starter Repair Service",
                "action": "Cleaned drain pump and checked hoses",
                "part_number": "BSH-WP-3300",
            },
        ],
        "maintenance_schedule": [
            {"interval_months": 6, "task": "Inspect hoses and drain filter"},
            {"interval_months": 12, "task": "Check motor noise and drum bearings"},
        ],
        "components": [
            {
                "name": "Door Seal",
                "part_number": "BSH-DS-7710",
                "replaceable": True,
                "expected_lifetime_years": 8,
                "materials": [
                    {
                        "material": "EPDM Rubber",
                        "percentage": 100,
                        "recyclable": False,
                        "hazardous": False,
                    }
                ],
            }
        ],
        "last_updated": "2026-05-11",
    }
}


FIELD_CATEGORIES = {
    "specifications": "specifications",
    "energy_label": "energy_label",
    "materials": "materials",
    "hazardous_substances": "hazardous_substances",
    "components": "components",
    "certifications": "compliance",
    "compliance": "compliance",
    "maintenance_schedule": "maintenance",
    "repair_history": "maintenance",
    "purchase_price_eur": "economic",
    "residual_value_eur": "economic",
    "warranty_years": "economic",
    "disassembly_instructions": "end_of_life",
    "recycling_instructions": "end_of_life",
    "disposal_instructions": "end_of_life",
}


def get_product(product_id: str) -> dict | None:
    """Return one product passport fragment by product ID."""
    return PRODUCTS.get(product_id)


def get_all_products() -> list[dict]:
    """Return all product passport fragments known by this provider."""
    return list(PRODUCTS.values())


def get_product_types() -> list[str]:
    """Infer supported product types from the product data."""
    return sorted({p["product_type"] for p in PRODUCTS.values() if p.get("product_type")})


def get_data_categories() -> list[str]:
    """Infer advertised data categories from non-empty fields in products."""
    categories = set()
    for product in PRODUCTS.values():
        for field_name, category in FIELD_CATEGORIES.items():
            if product.get(field_name) not in (None, [], {}):
                categories.add(category)
    return sorted(categories)
