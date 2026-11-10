"""Shared Pydantic models for all Digital Product Memory microservices."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# --- Enums ---

class Role(str, Enum):
    """Stakeholder roles in the Circular Economy."""
    RECYCLER = "recycler"
    CONSUMER = "consumer"
    MANUFACTURER = "manufacturer"
    REPAIRER = "repairer"
    COLLECTOR = "collector"


class Event(str, Enum):
    """Lifecycle events triggering DPP access."""
    PURCHASE = "purchase"
    REPAIR = "repair"
    RECYCLING = "recycling"
    MAINTENANCE = "maintenance"
    DISPOSAL = "disposal"
    RESALE = "resale"


class ProductType(str, Enum):
    """Supported product types in the prototype."""
    WASHING_MACHINE = "washing_machine"
    DISHWASHER = "dishwasher"
    BOILER = "boiler"
    SOLAR_PANEL = "solar_panel"
    LITHIUM_BATTERY = "lithium_battery"


class ServiceStatus(str, Enum):
    """Status of a registered service."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class DataCategory(str, Enum):
    """Canonical data categories shared by the Knowledge Graph and the Service Registry.

    The values are identical to the DataCategory nodes seeded into Neo4j, so that the
    Resolver can match the categories of recommended fields against the categories
    that providers declare in the registry.
    """
    IDENTIFICATION = "identification"
    TECHNICAL = "technical"
    COMPONENTS = "components"
    MATERIALS = "materials"
    SUSTAINABILITY = "sustainability"
    SAFETY = "safety"
    COMPLIANCE = "compliance"
    END_OF_LIFE = "end_of_life"
    ECONOMIC = "economic"
    MAINTENANCE = "maintenance"
    METADATA = "metadata"
    WATER = "water"
    PERFORMANCE = "performance"
    CONNECTIVITY = "connectivity"
    THERMAL = "thermal"
    ELECTRICAL = "electrical"
    BATTERY_HEALTH = "battery_health"
    PHOTOVOLTAIC = "photovoltaic"
    CIRCULAR_ECONOMY = "circular_economy"
    SUPPLY_CHAIN = "supply_chain"
    LOGISTICS = "logistics"
    SERVICE = "service"


# Category names used by earlier provider versions, mapped to the canonical vocabulary.
LEGACY_CATEGORY_ALIASES: dict[str, str] = {
    "specifications": DataCategory.TECHNICAL.value,
    "energy_label": DataCategory.SUSTAINABILITY.value,
    "hazardous_substances": DataCategory.SAFETY.value,
}

# Identity fields that every provider returns; they do not justify querying a provider.
IDENTITY_FIELDS: frozenset[str] = frozenset({
    "product_id", "product_type", "manufacturer", "model", "brand_name", "serial_number",
    "data_sources", "last_updated",
})

# Categories that every provider can contribute to (product identity, provenance).
# They are ignored when providers are preselected for a role-event context.
NON_SELECTIVE_CATEGORIES: frozenset[str] = frozenset({
    DataCategory.IDENTIFICATION.value,
    DataCategory.METADATA.value,
})


def normalize_categories(categories: list[str] | None) -> list[str]:
    """Map legacy category names to the canonical vocabulary and de-duplicate."""
    normalized = []
    for category in categories or []:
        value = LEGACY_CATEGORY_ALIASES.get(str(category), str(category))
        if value and value not in normalized:
            normalized.append(value)
    return sorted(normalized)


# --- Service Registry Models ---

class ServiceEndpoint(BaseModel):
    """A registered data provider endpoint.

    `product_ids` describes a closed product catalogue (the provider only knows these
    identifiers). Providers with an open catalogue (e.g. EPREL) leave it empty and may
    declare `conditions.identifier_pattern`, a regular expression for identifiers they
    can resolve. `data_fields` optionally lists the DPP fields the provider can serve;
    if present, it is used for a field-level preselection instead of `data_categories`.
    """
    id: Optional[str] = None
    name: str
    provider: str = ""
    description: str = ""
    base_url: str
    product_types: list[str] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list)
    data_fields: list[str] = Field(default_factory=list)
    data_categories: list[str] = Field(default_factory=list)
    conditions: dict[str, Any] = Field(default_factory=dict)
    status: ServiceStatus = ServiceStatus.ACTIVE


class ServiceEndpointCreate(BaseModel):
    """Schema for creating a new service endpoint."""
    name: str
    provider: str = ""
    description: str = ""
    base_url: str
    product_types: list[str] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list)
    data_fields: list[str] = Field(default_factory=list)
    data_categories: list[str] = Field(default_factory=list)
    conditions: dict[str, Any] = Field(default_factory=dict)


class ServiceEndpointUpdate(BaseModel):
    """Schema for updating a service endpoint."""
    name: Optional[str] = None
    provider: Optional[str] = None
    description: Optional[str] = None
    base_url: Optional[str] = None
    product_types: Optional[list[str]] = None
    product_ids: Optional[list[str]] = None
    data_fields: Optional[list[str]] = None
    data_categories: Optional[list[str]] = None
    conditions: Optional[dict[str, Any]] = None
    status: Optional[ServiceStatus] = None


class ServiceSelectionRequest(BaseModel):
    """Context for selecting the providers that are needed for one resolution request."""
    product_id: Optional[str] = None
    product_type: Optional[str] = None
    data_fields: list[str] = Field(default_factory=list)
    data_categories: list[str] = Field(default_factory=list)


class ServiceSelectionResponse(BaseModel):
    """Selected providers plus the reasons why other providers were not selected."""
    selected: list[ServiceEndpoint] = Field(default_factory=list)
    excluded: list[dict[str, str]] = Field(default_factory=list)
    category_filter_applied: bool = False


# --- Product Data Models ---

class MaterialComposition(BaseModel):
    """Material breakdown of a product."""
    material: str
    percentage: float
    recyclable: bool = True
    hazardous: bool = False


class EnergyLabel(BaseModel):
    """EU Energy Label data."""
    rating: str  # A, B, C, ...
    annual_consumption_kwh: Optional[float] = None
    noise_level_db: Optional[int] = None
    water_consumption_l: Optional[float] = None


class HazardousSubstance(BaseModel):
    """Hazardous substance information."""
    name: str
    cas_number: Optional[str] = None
    concentration_pct: Optional[float] = None
    regulation: Optional[str] = None  # e.g. "REACH", "RoHS"
    safety_instructions: Optional[str] = None


class Component(BaseModel):
    """Product component with repairability info."""
    name: str
    part_number: Optional[str] = None
    replaceable: bool = True
    expected_lifetime_years: Optional[float] = None
    materials: list[MaterialComposition] = Field(default_factory=list)


class ProductPassport(BaseModel):
    """Complete Digital Product Passport."""
    product_id: str
    product_type: str
    manufacturer: str = ""
    model: str = ""
    serial_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    manufacturing_location: Optional[str] = None

    # Technical
    specifications: dict[str, Any] = Field(default_factory=dict)
    components: list[Component] = Field(default_factory=list)
    materials: list[MaterialComposition] = Field(default_factory=list)
    weight_kg: Optional[float] = None
    dimensions: Optional[dict[str, float]] = None

    # Sustainability
    energy_label: Optional[EnergyLabel] = None
    repairability_score: Optional[float] = None  # 0-10
    recyclability_pct: Optional[float] = None
    carbon_footprint_kg_co2: Optional[float] = None
    expected_lifetime_years: Optional[float] = None

    # Safety & Compliance
    hazardous_substances: list[HazardousSubstance] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    compliance: list[str] = Field(default_factory=list)

    # End of Life
    disassembly_instructions: Optional[str] = None
    recycling_instructions: Optional[str] = None
    disposal_instructions: Optional[str] = None

    # Economic
    purchase_price_eur: Optional[float] = None
    residual_value_eur: Optional[float] = None
    warranty_years: Optional[float] = None

    # Maintenance
    maintenance_schedule: list[dict[str, Any]] = Field(default_factory=list)
    repair_history: list[dict[str, Any]] = Field(default_factory=list)

    # Metadata
    data_sources: list[str] = Field(default_factory=list)
    last_updated: Optional[str] = None


# --- Recommendation Engine Models ---

class RecommendationRequest(BaseModel):
    """Request to the Recommendation Engine."""
    product_data: dict[str, Any]
    product_type: str
    role: str
    event: str


class DataFieldRecommendation(BaseModel):
    """A single recommended data field."""
    field_name: str
    display_name: str
    category: str
    priority: float = Field(ge=0.0, le=1.0)
    description: str = ""
    value: Any = None


class RecommendationResponse(BaseModel):
    """Response from the Recommendation Engine."""
    product_id: str
    product_type: str
    role: str
    event: str
    recommended_fields: list[DataFieldRecommendation]
    filtered_data: dict[str, Any]
    total_fields_available: int
    fields_shown: int


# --- Resolver Models ---

class ResolverResponse(BaseModel):
    """Response from the Resolver Service."""
    product_id: str
    product_type: str
    role: str
    event: str
    passport: dict[str, Any]
    recommendation: Optional[RecommendationResponse] = None
    sources: list[str] = Field(default_factory=list)
    raw_data_available: bool = True
