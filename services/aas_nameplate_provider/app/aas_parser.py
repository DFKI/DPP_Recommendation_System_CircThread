"""Parser for a small AAS Digital Nameplate JSON profile.

The parser accepts an AAS-like JSON document with a Nameplate submodel and
maps selected IDTA Digital Nameplate elements to Digital Product Memory passport fields.
"""

from __future__ import annotations

from typing import Any


NAMEPLATE_SEMANTIC_ID = "https://admin-shell.io/zvei/nameplate/2/0/Nameplate"


def parse_aas_nameplate(aas: dict[str, Any]) -> dict[str, Any]:
    """Extract Digital Product Memory passport data from an AAS Digital Nameplate."""
    submodel = _find_nameplate_submodel(aas)
    elements = _flatten_elements(submodel.get("submodelElements", []))

    product_id = _value(elements.get("URIOfTheProduct")) or _value(elements.get("ProductArticleNumberOfManufacturer"))
    manufacturer = _value(elements.get("ManufacturerName"))
    designation = _value(elements.get("ManufacturerProductDesignation"))
    product_type_label = _value(elements.get("ManufacturerProductType")) or _value(elements.get("ManufacturerProductFamily"))
    serial_number = _value(elements.get("SerialNumber"))
    manufacturing_date = _value(elements.get("DateOfManufacture"))
    country = _value(elements.get("CountryOfOrigin"))
    year = _value(elements.get("YearOfConstruction"))

    markings = _extract_markings(elements)
    certifications = [m["name"] for m in markings if m.get("name")]
    compliance = [
        f"{m['name']} ({m['system']})" if m.get("system") else m["name"]
        for m in markings
        if m.get("name")
    ]

    specifications = {
        "aas_submodel": "Digital Nameplate",
        "aas_template": "IDTA 02006-2-0",
    }
    if product_type_label:
        specifications["manufacturer_product_type"] = product_type_label
    if year:
        specifications["year_of_construction"] = year
    if country:
        specifications["country_of_origin"] = country

    return {
        "product_id": _normalize_product_id(product_id),
        "product_type": _infer_circthread_product_type(product_type_label, designation),
        "manufacturer": manufacturer or "",
        "model": designation or product_type_label or "",
        "serial_number": serial_number,
        "manufacturing_date": manufacturing_date or year,
        "manufacturing_location": country,
        "specifications": specifications,
        "certifications": certifications,
        "compliance": compliance,
        "data_sources": ["aas_digital_nameplate"],
        "last_updated": aas.get("lastUpdated") or "2026-05-11",
    }


def _find_nameplate_submodel(aas: dict[str, Any]) -> dict[str, Any]:
    submodels = aas.get("submodels", [])
    if isinstance(aas.get("submodel"), dict):
        submodels.append(aas["submodel"])

    for submodel in submodels:
        if not isinstance(submodel, dict):
            continue
        if submodel.get("idShort") == "Nameplate":
            return submodel
        semantic_values = _semantic_values(submodel.get("semanticId"))
        if NAMEPLATE_SEMANTIC_ID in semantic_values:
            return submodel

    raise ValueError("No Digital Nameplate submodel found in AAS input.")


def _flatten_elements(elements: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    flattened: dict[str, dict[str, Any]] = {}
    for element in elements:
        if not isinstance(element, dict):
            continue
        id_short = element.get("idShort")
        if id_short:
            flattened[id_short] = element
        children = element.get("value")
        if isinstance(children, list):
            flattened.update(_flatten_elements(children))
    return flattened


def _value(element: dict[str, Any] | None) -> Any:
    if not element:
        return None

    model_type = _model_type(element)
    raw_value = element.get("value")

    if model_type == "MultiLanguageProperty" and isinstance(raw_value, list):
        for item in raw_value:
            if item.get("language") == "en":
                return item.get("text")
        return raw_value[0].get("text") if raw_value else None

    if model_type == "Property":
        return raw_value

    if isinstance(raw_value, str):
        return raw_value

    return None


def _extract_markings(elements: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    markings_root = elements.get("Markings")
    if not markings_root or not isinstance(markings_root.get("value"), list):
        return []

    markings = []
    for marking_collection in markings_root["value"]:
        if not isinstance(marking_collection, dict):
            continue
        children = _flatten_elements(marking_collection.get("value", []))
        marking_name = _value(children.get("MarkingName")) or _value(children.get("DesignationOfCertificateOrApproval"))
        marking_system = _value(children.get("MarkingSystem")) or _value(children.get("CertificateOrApprovalSystem"))
        if marking_name:
            markings.append({"name": marking_name, "system": marking_system or ""})
    return markings


def _model_type(element: dict[str, Any]) -> str:
    model_type = element.get("modelType")
    if isinstance(model_type, dict):
        return model_type.get("name", "")
    return str(model_type or "")


def _semantic_values(semantic_id: Any) -> list[str]:
    if not isinstance(semantic_id, dict):
        return []
    keys = semantic_id.get("keys", [])
    values = []
    for key in keys:
        if isinstance(key, dict) and key.get("value"):
            values.append(str(key["value"]))
    return values


def _normalize_product_id(value: Any) -> str:
    if not value:
        return "unknown-aas-product"
    value = str(value)
    if value.startswith("urn:circthread:product:"):
        return value.rsplit(":", 1)[-1]
    return value


def _infer_circthread_product_type(product_type_label: Any, designation: Any) -> str:
    text = f"{product_type_label or ''} {designation or ''}".lower()
    if "solar" in text or "photovoltaic" in text:
        return "solar_panel"
    if "battery" in text or "storage" in text:
        return "lithium_battery"
    if "washing" in text:
        return "washing_machine"
    if "dishwasher" in text:
        return "dishwasher"
    if "boiler" in text or "heating" in text:
        return "boiler"
    return "unknown"
