"""Knowledge Graph query logic for role-based data field recommendations."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any
from uuid import uuid4

from app.neo4j_client import Neo4jClient
from shared.config import settings
from shared.vocabulary import LIFECYCLE_PHASES, phase_for_event

logger = logging.getLogger(__name__)


EMPTY_VALUES = (None, [], {}, "")

CORE_SOURCES = frozenset({"role_event", "role", "event", "static_generic", "dynamic_template"})
SUGGESTION_SOURCES = frozenset({"association_rule", "lifecycle_frequency", "role_preference", "contextual_similarity"})


def _sort_by_priority(fields: list[dict]) -> list[dict]:
    return sorted(fields, key=lambda f: (-(f.get("priority") or 0.0), f.get("field_name", "")))


async def _static_recommendations(
    client: Neo4jClient,
    role: str | None,
    event: str | None,
    product_type: str,
) -> list[dict]:
    """Query the static Knowledge Graph for one of the four filtering modes."""
    if role and event:
        query = """
        MATCH (r:Role {name: $role})-[needs:NEEDS {event: $event}]->(df:DataField)
        MATCH (pt:ProductType {name: $product_type})-[:HAS_FIELD]->(df)
        MATCH (df)-[:BELONGS_TO]->(dc:DataCategory)
        RETURN df.name AS field_name,
               df.display_name AS display_name,
               dc.name AS category,
               dc.display_name AS category_display,
               df.description AS description,
               needs.priority AS priority,
               [$role] AS matched_roles,
               [$event] AS matched_events,
               "role_event" AS filter_mode,
               "role_event" AS recommendation_source
        ORDER BY needs.priority DESC, df.name
        """
        return await client.run_query(query, {"role": role, "event": event, "product_type": product_type})
    if role:
        query = """
        MATCH (r:Role {name: $role})-[needs:NEEDS]->(df:DataField)
        MATCH (pt:ProductType {name: $product_type})-[:HAS_FIELD]->(df)
        MATCH (df)-[:BELONGS_TO]->(dc:DataCategory)
        WITH df, dc, max(needs.priority) AS priority, collect(DISTINCT needs.event) AS matched_events
        RETURN df.name AS field_name,
               df.display_name AS display_name,
               dc.name AS category,
               dc.display_name AS category_display,
               df.description AS description,
               priority,
               [$role] AS matched_roles,
               matched_events,
               "role" AS filter_mode,
               "role" AS recommendation_source
        ORDER BY priority DESC, df.name
        """
        return await client.run_query(query, {"role": role, "product_type": product_type})
    if event:
        query = """
        MATCH (r:Role)-[needs:NEEDS {event: $event}]->(df:DataField)
        MATCH (pt:ProductType {name: $product_type})-[:HAS_FIELD]->(df)
        MATCH (df)-[:BELONGS_TO]->(dc:DataCategory)
        WITH df, dc, max(needs.priority) AS priority, collect(DISTINCT r.name) AS matched_roles
        RETURN df.name AS field_name,
               df.display_name AS display_name,
               dc.name AS category,
               dc.display_name AS category_display,
               df.description AS description,
               priority,
               matched_roles,
               [$event] AS matched_events,
               "event" AS filter_mode,
               "event" AS recommendation_source
        ORDER BY priority DESC, df.name
        """
        return await client.run_query(query, {"event": event, "product_type": product_type})
    query = """
    MATCH (pt:ProductType {name: $product_type})-[:HAS_FIELD]->(df:DataField)
    MATCH (df)-[:BELONGS_TO]->(dc:DataCategory)
    RETURN df.name AS field_name,
           df.display_name AS display_name,
           dc.name AS category,
           dc.display_name AS category_display,
           df.description AS description,
           0.5 AS priority,
           [] AS matched_roles,
           [] AS matched_events,
           "generic" AS filter_mode,
           "static_generic" AS recommendation_source
    ORDER BY dc.name, df.name
    """
    return await client.run_query(query, {"product_type": product_type})


async def get_core_recommendations(
    client: Neo4jClient,
    role: str | None,
    event: str | None,
    product_type: str,
) -> dict:
    """
    Return the core recommendation for a context: static Knowledge Graph fields plus
    dynamic template fields, sorted by priority.

    If role and event are given but no NEEDS relationship is modelled for this
    combination, the role-only aggregation is used as an explicit fallback.
    """
    filter_mode = _filter_mode(role, event)
    fallback = None
    static = await _static_recommendations(client, role, event, product_type)
    if not static and role and event:
        static = await _static_recommendations(client, role, None, product_type)
        if static:
            fallback = "role"
            filter_mode = "role_fallback"

    results = list(static)
    existing = {r["field_name"] for r in results}
    for rec in await get_dynamic_recommended_fields(client, product_type, role, event):
        if rec["field_name"] not in existing:
            results.append(rec)
            existing.add(rec["field_name"])
    return {"fields": _sort_by_priority(results), "filter_mode": filter_mode, "fallback": fallback}


async def get_suggestions(
    client: Neo4jClient,
    role: str | None,
    event: str | None,
    product_type: str,
    exclude: set[str],
) -> list[dict]:
    """
    Run the four extended algorithms and return their candidates as separate suggestions.

    Suggestions are not merged into the role- and event-specific DPP view; they are
    returned in a dedicated list so that the role-specific selection stays unaffected.
    """
    seed_fields = sorted(exclude)
    suggestions: list[dict] = []
    seen = set(exclude)
    for rec_list in (
        await get_association_rule_recommendations(client, seed_fields, product_type),
        await get_lifecycle_frequency_recommendations(client, event, product_type),
        await get_role_preference_recommendations(client, role, product_type),
        await get_contextual_similarity_recommendations(client, seed_fields, product_type),
    ):
        for rec in rec_list:
            if rec["field_name"] not in seen:
                suggestions.append(rec)
                seen.add(rec["field_name"])
    return _sort_by_priority(suggestions)


async def get_recommended_fields(
    client: Neo4jClient,
    role: str | None,
    event: str | None,
    product_type: str,
    include_suggestions: bool = False,
) -> list[dict]:
    """
    Query the Knowledge Graph for recommended data fields (core recommendation).

    Returns fields sorted by priority (highest first). With include_suggestions=True,
    the candidates of the extended algorithms are appended after the core fields.
    """
    core = await get_core_recommendations(client, role, event, product_type)
    results = core["fields"]
    if include_suggestions:
        results = results + await get_suggestions(
            client, role, event, product_type, {r["field_name"] for r in results}
        )
    await attach_external_mappings(client, results)
    return results


async def get_association_rule_recommendations(
    client: Neo4jClient,
    seed_fields: list[str],
    product_type: str,
    min_confidence: float = 0.5,
    min_support: int = 2,
) -> list[dict]:
    """
    Recommend co-occurring fields via association rule learning over stored templates.

    For each field already in the recommendation context (seed_fields), find
    other fields that frequently appear together in the same DPP templates.
    Confidence = P(candidate | seed present in template); support = absolute
    co-occurrence count. Only candidates exceeding both thresholds are returned.
    """
    if not seed_fields:
        return []

    query = """
    MATCH (all_tpl:DPPTemplate)
    WITH count(DISTINCT all_tpl.id) AS total_templates

    MATCH (seed_tpl:DPPTemplate)-[:REQUESTS]->(seed_tt:TemplateTerm)
    WHERE seed_tt.name IN $seed_fields
    WITH total_templates,
         collect(DISTINCT seed_tpl.id) AS seed_ids,
         count(DISTINCT seed_tpl.id) AS seed_count

    MATCH (co_tpl:DPPTemplate)-[:REQUESTS]->(co_tt:TemplateTerm)
    WHERE co_tpl.id IN seed_ids
      AND NOT co_tt.name IN $seed_fields
    MATCH (df:DataField {name: co_tt.name})-[:BELONGS_TO]->(dc:DataCategory)
    MATCH (pt:ProductType {name: $product_type})-[:HAS_FIELD]->(df)
    WITH df, dc, total_templates, seed_count,
         count(DISTINCT co_tpl.id) AS co_count
    WHERE co_count >= $min_support AND seed_count > 0
    WITH df, dc, co_count, seed_count, total_templates,
         toFloat(co_count) / seed_count AS confidence,
         toFloat(co_count) / total_templates AS support
    WHERE confidence >= $min_confidence
    RETURN df.name AS field_name,
           df.display_name AS display_name,
           dc.name AS category,
           dc.display_name AS category_display,
           df.description AS description,
           0.5 + confidence * 0.3 AS priority,
           confidence,
           support,
           co_count AS co_occurrence_count,
           [] AS matched_roles,
           [] AS matched_events,
           "association_rule" AS recommendation_source
    ORDER BY confidence DESC, co_count DESC, df.name
    """
    return await client.run_query(query, {
        "seed_fields": seed_fields,
        "product_type": product_type,
        "min_confidence": min_confidence,
        "min_support": min_support,
    })


async def get_lifecycle_frequency_recommendations(
    client: Neo4jClient,
    event: str | None,
    product_type: str,
) -> list[dict]:
    """
    Recommend fields based on cross-role demand frequency within a life cycle phase.

    When an event is given, counts how many distinct roles require each field
    for that phase; a high ratio signals broad lifecycle relevance. Without an
    event, frequency is measured across all phases weighted by average priority.
    """
    if event:
        query = """
        MATCH (total_r:Role)
        WITH count(total_r) AS total_roles

        MATCH (r:Role)-[needs:NEEDS {event: $event}]->(df:DataField)
        MATCH (pt:ProductType {name: $product_type})-[:HAS_FIELD]->(df)
        MATCH (df)-[:BELONGS_TO]->(dc:DataCategory)
        WITH total_roles, df, dc, $event AS phase,
             count(DISTINCT r.name) AS role_count,
             avg(needs.priority) AS avg_priority
        WITH df, dc, phase, role_count, avg_priority,
             toFloat(role_count) / CASE WHEN total_roles > 0 THEN total_roles ELSE 1 END AS phase_frequency
        RETURN df.name AS field_name,
               df.display_name AS display_name,
               dc.name AS category,
               dc.display_name AS category_display,
               df.description AS description,
               phase_frequency * 0.8 + avg_priority * 0.2 AS priority,
               phase_frequency,
               role_count,
               phase,
               [] AS matched_roles,
               [$event] AS matched_events,
               "lifecycle_frequency" AS recommendation_source
        ORDER BY phase_frequency DESC, avg_priority DESC, df.name
        """
        params: dict = {"event": event, "product_type": product_type}
    else:
        query = """
        MATCH (tr:Role)-[tn:NEEDS]->()
        WITH count(DISTINCT tn.event + "|" + tr.name) AS total_demand

        MATCH (r:Role)-[needs:NEEDS]->(df:DataField)
        MATCH (pt:ProductType {name: $product_type})-[:HAS_FIELD]->(df)
        MATCH (df)-[:BELONGS_TO]->(dc:DataCategory)
        WITH total_demand, df, dc,
             count(DISTINCT needs.event + "|" + r.name) AS demand_count,
             count(DISTINCT needs.event) AS event_count,
             avg(needs.priority) AS avg_priority
        WITH df, dc, demand_count, event_count, avg_priority,
             toFloat(demand_count) / CASE WHEN total_demand > 0 THEN total_demand ELSE 1 END AS phase_frequency
        RETURN df.name AS field_name,
               df.display_name AS display_name,
               dc.name AS category,
               dc.display_name AS category_display,
               df.description AS description,
               phase_frequency * 0.6 + avg_priority * 0.4 AS priority,
               phase_frequency,
               event_count AS phases_present_in,
               null AS phase,
               [] AS matched_roles,
               [] AS matched_events,
               "lifecycle_frequency" AS recommendation_source
        ORDER BY phase_frequency DESC, avg_priority DESC, df.name
        """
        params = {"product_type": product_type}

    return await client.run_query(query, params)


async def get_role_preference_recommendations(
    client: Neo4jClient,
    role: str | None,
    product_type: str,
) -> list[dict]:
    """
    Recommend fields based on historical preferences expressed by a given role.

    Analyses DPP templates that were created with the specified role to surface
    fields that stakeholders in that role have most frequently selected in
    practice — capturing preferences beyond the static KG schema.
    """
    if not role:
        return []

    query = """
    MATCH (role_tpls:DPPTemplate {role: $role})
    WITH count(DISTINCT role_tpls.id) AS total_role_templates
    WHERE total_role_templates > 0

    MATCH (tpl:DPPTemplate {role: $role})-[:REQUESTS]->(tt:TemplateTerm)
    MATCH (df:DataField {name: tt.name})-[:BELONGS_TO]->(dc:DataCategory)
    MATCH (pt:ProductType {name: $product_type})-[:HAS_FIELD]->(df)
    WITH total_role_templates, df, dc,
         count(DISTINCT tpl.id) AS selection_count
    WITH df, dc, selection_count, total_role_templates,
         toFloat(selection_count) / total_role_templates AS preference_score
    RETURN df.name AS field_name,
           df.display_name AS display_name,
           dc.name AS category,
           dc.display_name AS category_display,
           df.description AS description,
           0.55 + preference_score * 0.25 AS priority,
           preference_score,
           selection_count,
           [$role] AS matched_roles,
           [] AS matched_events,
           "role_preference" AS recommendation_source
    ORDER BY preference_score DESC, selection_count DESC, df.name
    """
    return await client.run_query(query, {"role": role, "product_type": product_type})


async def get_contextual_similarity_recommendations(
    client: Neo4jClient,
    seed_fields: list[str],
    product_type: str,
    max_results: int = 10,
) -> list[dict]:
    """
    Recommend fields by contextual similarity to the current recommendation set.

    Uses shared DataCategory membership as the primary proximity signal: fields
    that belong to the same categories as already-recommended fields are considered
    contextually similar and surfaced as additional candidates.
    """
    if not seed_fields:
        return []

    query = """
    MATCH (seed_df:DataField)-[:BELONGS_TO]->(seed_cat:DataCategory)
    WHERE seed_df.name IN $seed_fields
    WITH collect(DISTINCT seed_cat.name) AS seed_categories

    MATCH (pt:ProductType {name: $product_type})-[:HAS_FIELD]->(candidate:DataField)
    MATCH (candidate)-[:BELONGS_TO]->(cat:DataCategory)
    WHERE cat.name IN seed_categories
      AND NOT candidate.name IN $seed_fields
    RETURN candidate.name AS field_name,
           candidate.display_name AS display_name,
           cat.name AS category,
           cat.display_name AS category_display,
           candidate.description AS description,
           0.55 AS priority,
           [] AS matched_roles,
           [] AS matched_events,
           "contextual_similarity" AS recommendation_source
    ORDER BY cat.name, candidate.name
    LIMIT $max_results
    """
    return await client.run_query(query, {
        "seed_fields": seed_fields,
        "product_type": product_type,
        "max_results": max_results,
    })


async def get_dynamic_recommended_fields(
    client: Neo4jClient,
    product_type: str,
    role: str | None = None,
    event: str | None = None,
    threshold: int = 2,
) -> list[dict]:
    """
    Return terms that occur in at least `threshold` different custom DPP templates.

    This models the dynamic recommendation subgraph: templates are stored as dynamic
    observations, but a term only becomes a recommendation signal after repeated use
    across different templates. Only templates whose stored context matches the request
    are counted: a template created for a role (or event) only counts for that role (or
    event); a template that is only assigned to a lifecycle phase (e.g. a self-defined
    maintenance context) counts for every event of that phase; templates without role,
    event or phase count for every context.
    """
    query = """
    MATCH (t:DPPTemplate)-[:REQUESTS]->(tt:TemplateTerm)
    WHERE ($role IS NULL OR t.role IS NULL OR t.role = $role)
      AND ($event IS NULL
           OR t.event = $event
           OR (t.event IS NULL AND (t.lifecycle_phase IS NULL OR t.lifecycle_phase = $phase)))
      AND (t.product_type IS NULL OR t.product_type = $product_type)
    MATCH (df:DataField {name: tt.name})-[:BELONGS_TO]->(dc:DataCategory)
    MATCH (pt:ProductType {name: $product_type})-[:HAS_FIELD]->(df)
    WITH df, dc, count(DISTINCT t.id) AS template_count
    WHERE template_count >= $threshold
    RETURN df.name AS field_name,
           df.display_name AS display_name,
           dc.name AS category,
           dc.display_name AS category_display,
           df.description AS description,
           CASE
             WHEN template_count >= 6 THEN 0.75
             WHEN template_count >= 4 THEN 0.70
             ELSE 0.65
           END AS priority,
           template_count AS template_count,
           "dynamic_template" AS recommendation_source
    ORDER BY template_count DESC, df.name
    """
    return await client.run_query(query, {
        "product_type": product_type,
        "role": role,
        "event": event,
        "phase": phase_for_event(event),
        "threshold": threshold,
    })


def _field_entry(rec: dict, value: Any, field_sources: dict) -> dict:
    return {
        "field_name": rec["field_name"],
        "display_name": rec["display_name"],
        "category": rec["category"],
        "priority": rec["priority"],
        "description": rec.get("description", ""),
        "value": value,
        "sources": field_sources.get(rec["field_name"], []) if value is not None else [],
        "recommendation_source": rec.get("recommendation_source", "static_generic"),
        "filter_mode": rec.get("filter_mode", "dynamic"),
        "matched_roles": rec.get("matched_roles", []),
        "matched_events": rec.get("matched_events", []),
        "template_count": rec.get("template_count"),
        "external_mappings": rec.get("external_mappings", []),
    }


async def filter_product_data(
    client: Neo4jClient,
    product_data: dict[str, Any],
    product_type: str,
    role: str | None,
    event: str | None,
) -> dict:
    """
    Filter product data based on Knowledge Graph recommendations.

    The role- and event-specific view (filtered_data, recommended_fields) is built from
    the core recommendation only. Candidates of the extended algorithms are returned
    separately in suggested_fields. Empty values ([], {}, "") are treated as data gaps.
    """
    core = await get_core_recommendations(client, role, event, product_type)
    recommended = core["fields"]

    if not recommended:
        logger.warning(
            "No KG mapping found for role=%s, event=%s, product_type=%s. Returning basic fields.",
            role, event, product_type
        )
        recommended = [
            {"field_name": "product_id", "display_name": "Product ID", "category": "identification",
             "category_display": "Product Identification", "description": "Unique product identifier", "priority": 1.0,
             "recommendation_source": "basic_fallback"},
            {"field_name": "product_type", "display_name": "Product Type", "category": "identification",
             "category_display": "Product Identification", "description": "Category of the product", "priority": 1.0,
             "recommendation_source": "basic_fallback"},
            {"field_name": "manufacturer", "display_name": "Manufacturer", "category": "identification",
             "category_display": "Product Identification", "description": "Producer of the product", "priority": 0.9,
             "recommendation_source": "basic_fallback"},
            {"field_name": "model", "display_name": "Model Name", "category": "identification",
             "category_display": "Product Identification", "description": "Commercial model designation", "priority": 0.9,
             "recommendation_source": "basic_fallback"},
        ]

    suggestions = await get_suggestions(
        client, role, event, product_type, {r["field_name"] for r in recommended}
    )
    await attach_external_mappings(client, recommended + suggestions)

    field_sources = product_data.get("_field_sources", {})
    if not isinstance(field_sources, dict):
        field_sources = {}

    def value_of(name: str) -> Any:
        value = product_data.get(name)
        return None if value in EMPTY_VALUES else value

    filtered_data = {}
    recommended_fields = []
    for rec in recommended:
        value = value_of(rec["field_name"])
        if value is not None:
            filtered_data[rec["field_name"]] = value
        recommended_fields.append(_field_entry(rec, value, field_sources))

    suggested_fields = [_field_entry(rec, value_of(rec["field_name"]), field_sources) for rec in suggestions]

    total_fields = len([k for k, v in product_data.items() if not k.startswith("_") and v not in EMPTY_VALUES])

    return {
        "product_id": product_data.get("product_id", "unknown"),
        "product_type": product_type,
        "role": role,
        "event": event,
        "filter_mode": core["filter_mode"] if core["fields"] else "basic_fallback",
        "fallback": core["fallback"],
        "recommended_fields": recommended_fields,
        "suggested_fields": suggested_fields,
        "filtered_data": filtered_data,
        "data_gaps": [f["field_name"] for f in recommended_fields if f["value"] is None],
        "total_fields_available": total_fields,
        "fields_shown": len(filtered_data),
    }


async def get_available_roles(client: Neo4jClient) -> list[dict]:
    """Get all available roles from the KG."""
    return await client.run_query(
        "MATCH (r:Role) RETURN r.name AS name, r.display_name AS display_name ORDER BY r.name"
    )


async def get_available_events(client: Neo4jClient) -> list[dict]:
    """Get all available events from the KG."""
    return await client.run_query(
        "MATCH (e:Event) RETURN e.name AS name, e.display_name AS display_name ORDER BY e.name"
    )


async def get_available_product_types(client: Neo4jClient) -> list[dict]:
    """Get all available product types from the KG."""
    return await client.run_query(
        "MATCH (pt:ProductType) RETURN pt.name AS name, pt.display_name AS display_name ORDER BY pt.name"
    )


async def get_vocabulary_terms(client: Neo4jClient) -> list[dict]:
    """Get all vocabulary terms available for DPP template creation."""
    query = """
    MATCH (df:DataField)-[:BELONGS_TO]->(dc:DataCategory)
    RETURN df.name AS field_name,
           df.display_name AS display_name,
           dc.name AS category,
           dc.display_name AS category_display,
           df.description AS description
    ORDER BY dc.name, df.display_name
    """
    terms = await client.run_query(query)
    await attach_external_mappings(client, terms)
    return terms


async def attach_external_mappings(client: Neo4jClient, terms: list[dict]) -> None:
    """Attach SSSOM external mappings to term dictionaries in-place."""
    field_names = [term["field_name"] for term in terms if term.get("field_name")]
    if not field_names:
        return

    mappings = await client.run_query(
        """
        MATCH (df:DataField)-[:REPRESENTS_TERM]->(subject:OntologyTerm)
        MATCH (mapping:SSSOMMapping)-[:HAS_SUBJECT]->(subject)
        MATCH (mapping)-[:HAS_OBJECT]->(object:OntologyTerm)
        WHERE df.name IN $field_names
        RETURN df.name AS field_name,
               collect({
                   subject_id: subject.curie,
                   subject_label: subject.label,
                   predicate_id: mapping.predicate_id,
                   object_id: object.curie,
                   object_label: object.label,
                   mapping_justification: mapping.mapping_justification,
                   mapping_tool: mapping.mapping_tool,
                   confidence: mapping.confidence
               }) AS external_mappings
        """,
        {"field_names": field_names},
    )
    by_field = {row["field_name"]: row["external_mappings"] for row in mappings}
    for term in terms:
        term["external_mappings"] = by_field.get(term.get("field_name"), [])


async def get_sssom_mappings(client: Neo4jClient) -> dict:
    """List the SSSOM mapping set and mappings stored in Neo4j."""
    mapping_sets = await client.run_query(
        """
        MATCH (ms:MappingSet)
        RETURN ms.mapping_set_id AS mapping_set_id,
               ms.mapping_set_version AS mapping_set_version,
               ms.mapping_set_description AS mapping_set_description,
               ms.creator_id AS creator_id,
               ms.creator_label AS creator_label,
               ms.license AS license,
               ms.curie_map AS curie_map
        ORDER BY ms.mapping_set_id
        """
    )
    for mapping_set in mapping_sets:
        raw_curie_map = mapping_set.get("curie_map")
        if isinstance(raw_curie_map, str):
            try:
                mapping_set["curie_map"] = json.loads(raw_curie_map)
            except json.JSONDecodeError:
                mapping_set["curie_map"] = {}

    mappings = await client.run_query(
        """
        MATCH (mapping:SSSOMMapping)-[:HAS_SUBJECT]->(subject:OntologyTerm)
        MATCH (mapping)-[:HAS_OBJECT]->(object:OntologyTerm)
        OPTIONAL MATCH (local)-[:REPRESENTS_TERM]->(subject)
        WITH mapping, subject, object,
             [term IN collect(DISTINCT CASE
                 WHEN local IS NULL THEN null
                 ELSE {
                     name: local.name,
                     label: local.display_name,
                     type: labels(local)[0]
                 }
             END) WHERE term IS NOT NULL] AS local_terms
        RETURN mapping.mapping_id AS mapping_id,
               subject.curie AS subject_id,
               subject.label AS subject_label,
               mapping.predicate_id AS predicate_id,
               object.curie AS object_id,
               object.label AS object_label,
               mapping.mapping_justification AS mapping_justification,
               mapping.mapping_tool AS mapping_tool,
               mapping.confidence AS confidence,
               local_terms
        ORDER BY subject.curie, object.curie
        """
    )
    return {"mapping_sets": mapping_sets, "mappings": mappings}


TEMPLATE_CONTEXT_KEYS = ("role", "event", "product_type", "custom_event", "lifecycle_phase")
CUSTOM_EVENT_MAX_LENGTH = 100
ANONYMOUS_USER = "anonymous"


def internal_user_id(user_id: str | None) -> str:
    """
    Derive the internal, pseudonymous identifier under which a template user is stored.

    The client-supplied identifier is never written to Neo4j; only a salted SHA-256 hash
    of it is kept, so templates of the same client can be grouped without storing who
    created them.
    """
    cleaned = (user_id or "").strip()
    if not cleaned or cleaned == ANONYMOUS_USER:
        return ANONYMOUS_USER
    digest = hashlib.sha256(f"{settings.TEMPLATE_USER_SALT}:{cleaned}".encode("utf-8")).hexdigest()
    return f"u-{digest[:24]}"


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def normalize_template_context(context: dict[str, Any], stored: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Validate and normalise the context of a DPP template.

    Only the keys present in `context` are returned (partial update semantics); `stored`
    holds the current values of an existing template for consistency checks.

    - custom_event: free-text name of a self-defined event (e.g. "Inverter inspection").
    - lifecycle_phase: one of LIFECYCLE_PHASES. If a predefined event is given without a
      phase, the phase of that event is derived; a phase that contradicts the event is
      rejected.
    """
    result = {key: _clean(context[key]) for key in TEMPLATE_CONTEXT_KEYS if key in context}

    custom_event = result.get("custom_event")
    if custom_event and len(custom_event) > CUSTOM_EVENT_MAX_LENGTH:
        raise ValueError(f"custom_event must not exceed {CUSTOM_EVENT_MAX_LENGTH} characters.")

    phase = result.get("lifecycle_phase")
    if phase and phase not in LIFECYCLE_PHASES:
        raise ValueError(f"Unknown lifecycle_phase '{phase}'. Allowed: {', '.join(LIFECYCLE_PHASES)}.")

    event = result["event"] if "event" in result else (stored or {}).get("event")
    event_phase = phase_for_event(event)
    if event_phase:
        if "lifecycle_phase" not in result or phase is None:
            if "event" in result or "lifecycle_phase" in result:
                result["lifecycle_phase"] = event_phase
        elif phase != event_phase:
            raise ValueError(
                f"Lifecycle phase '{phase}' does not match event '{event}' (phase '{event_phase}')."
            )
    return result


async def _write_template_terms(client: Neo4jClient, template_id: str, terms: list[str]) -> None:
    for term in terms:
        await client.run_write(
            """
            MATCH (tpl:DPPTemplate {id: $template_id})
            MERGE (tt:TemplateTerm {name: $term})
            ON CREATE SET tt.created_at = datetime()
            SET tt.last_seen_at = datetime()
            CREATE (tpl)-[:REQUESTS]->(tt)
            WITH tt
            MATCH (df:DataField {name: $term})
            MERGE (tt)-[:REFERS_TO]->(df)
            """,
            {"template_id": template_id, "term": term},
        )


async def create_dpp_template(
    client: Neo4jClient,
    template_name: str,
    terms: list[str],
    role: str | None = None,
    event: str | None = None,
    product_type: str | None = None,
    user_id: str = ANONYMOUS_USER,
    custom_event: str | None = None,
    lifecycle_phase: str | None = None,
) -> dict:
    """
    Store a custom DPP template in the dynamic Neo4j subgraph.

    A template records which fields are requested in which context: an optional role,
    a predefined event and/or a self-defined event name, a lifecycle phase and the product
    type. Product values are never stored. The creator is stored under an internal,
    pseudonymous identifier (see internal_user_id).
    """
    normalized_terms = sorted({t for t in terms if t})
    if not normalized_terms:
        raise ValueError("A DPP template must contain at least one term.")

    context = normalize_template_context({
        "role": role,
        "event": event,
        "product_type": product_type,
        "custom_event": custom_event,
        "lifecycle_phase": lifecycle_phase,
    })
    template_id = str(uuid4())
    await client.run_write(
        """
        MERGE (u:TemplateUser {user_id: $user_id})
        CREATE (tpl:DPPTemplate {
            id: $template_id,
            name: $template_name,
            role: $role,
            event: $event,
            custom_event: $custom_event,
            lifecycle_phase: $lifecycle_phase,
            product_type: $product_type,
            created_at: datetime()
        })
        CREATE (u)-[:OWNS]->(tpl)
        """,
        {
            "user_id": internal_user_id(user_id),
            "template_id": template_id,
            "template_name": template_name,
            **context,
        },
    )
    await _write_template_terms(client, template_id, normalized_terms)

    promoted_terms = await get_promoted_template_terms(client)
    return {
        "template_id": template_id,
        "template_name": template_name,
        "terms": normalized_terms,
        **context,
        "dynamic_threshold": 2,
        "promoted_terms": promoted_terms,
    }


def _filter_mode(role: str | None, event: str | None) -> str:
    if role and event:
        return "role_event"
    if role:
        return "role"
    if event:
        return "event"
    return "generic"


async def update_dpp_template(
    client: Neo4jClient,
    template_id: str,
    template_name: str,
    terms: list[str],
    context: dict[str, Any] | None = None,
) -> dict | None:
    """
    Update a stored DPP template and replace its selected terms.

    `context` contains only the context properties that should change (role, event,
    product_type, custom_event, lifecycle_phase); properties that are not passed keep
    their stored value. An explicit None clears a property.
    """
    normalized_terms = sorted({t for t in terms if t})
    if not normalized_terms:
        raise ValueError("A DPP template must contain at least one term.")

    existing = await client.run_query(
        """
        MATCH (tpl:DPPTemplate {id: $template_id})
        RETURN tpl.id AS id, tpl.role AS role, tpl.event AS event,
               tpl.product_type AS product_type, tpl.custom_event AS custom_event,
               tpl.lifecycle_phase AS lifecycle_phase
        """,
        {"template_id": template_id},
    )
    if not existing:
        return None
    stored = {key: existing[0].get(key) for key in TEMPLATE_CONTEXT_KEYS}
    changes = normalize_template_context(context or {}, stored)

    # SET tpl += $changes only touches the passed keys; null values remove a property.
    await client.run_write(
        """
        MATCH (tpl:DPPTemplate {id: $template_id})
        SET tpl.name = $template_name,
            tpl.updated_at = datetime()
        SET tpl += $changes
        WITH tpl
        OPTIONAL MATCH (tpl)-[r:REQUESTS]->(:TemplateTerm)
        DELETE r
        """,
        {"template_id": template_id, "template_name": template_name, "changes": changes},
    )
    await _write_template_terms(client, template_id, normalized_terms)

    promoted_terms = await get_promoted_template_terms(client)
    return {
        "template_id": template_id,
        "template_name": template_name,
        "terms": normalized_terms,
        **{**stored, **changes},
        "dynamic_threshold": 2,
        "promoted_terms": promoted_terms,
    }


async def delete_dpp_template(client: Neo4jClient, template_id: str) -> bool:
    """Delete one DPP template and cleanup orphan dynamic terms."""
    result = await client.run_query(
        """
        MATCH (tpl:DPPTemplate {id: $template_id})
        WITH tpl, tpl.name AS name
        DETACH DELETE tpl
        RETURN name
        """,
        {"template_id": template_id},
    )
    if not result:
        return False

    await client.run_write(
        """
        MATCH (tt:TemplateTerm)
        WHERE NOT (tt)<-[:REQUESTS]-(:DPPTemplate)
        DETACH DELETE tt
        """
    )
    # Data minimisation: a pseudonymous user without templates is not kept.
    await client.run_write(
        """
        MATCH (u:TemplateUser)
        WHERE NOT (u)-[:OWNS]->(:DPPTemplate)
        DETACH DELETE u
        """
    )
    return True


async def get_dpp_templates(client: Neo4jClient) -> list[dict]:
    """List stored dynamic DPP templates with their requested terms."""
    query = """
    MATCH (tpl:DPPTemplate)
    OPTIONAL MATCH (tpl)-[:REQUESTS]->(tt:TemplateTerm)
    WITH tpl, collect(tt.name) AS terms
    RETURN tpl.id AS template_id,
           tpl.name AS template_name,
           tpl.role AS role,
           tpl.event AS event,
           tpl.custom_event AS custom_event,
           tpl.lifecycle_phase AS lifecycle_phase,
           tpl.product_type AS product_type,
           toString(tpl.created_at) AS created_at,
           toString(tpl.updated_at) AS updated_at,
           terms
    ORDER BY created_at DESC
    """
    return await client.run_query(query)


async def get_promoted_template_terms(client: Neo4jClient, threshold: int = 2) -> list[dict]:
    """List terms that crossed the dynamic recommendation threshold."""
    query = """
    MATCH (tpl:DPPTemplate)-[:REQUESTS]->(tt:TemplateTerm)
    OPTIONAL MATCH (tt)-[:REFERS_TO]->(df:DataField)-[:BELONGS_TO]->(dc:DataCategory)
    WITH tt, df, dc, count(DISTINCT tpl.id) AS template_count
    WHERE template_count >= $threshold
    RETURN tt.name AS field_name,
           coalesce(df.display_name, tt.name) AS display_name,
           coalesce(dc.name, "unknown") AS category,
           template_count
    ORDER BY template_count DESC, tt.name
    """
    return await client.run_query(query, {"threshold": threshold})


async def get_graph_statistics(client: Neo4jClient) -> dict:
    """Get KG statistics for monitoring."""
    stats = {}
    for label in ["Role", "Event", "ProductType", "DataField", "DataCategory", "OntologyTerm", "SSSOMMapping"]:
        result = await client.run_query(f"MATCH (n:{label}) RETURN count(n) AS count")
        stats[label.lower() + "_count"] = result[0]["count"] if result else 0

    dynamic_stats = await client.run_query(
        """
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label IN ["DPPTemplate", "TemplateTerm", "TemplateUser"])
        UNWIND labels(n) AS label
        WITH label, count(*) AS count
        WHERE label IN ["DPPTemplate", "TemplateTerm", "TemplateUser"]
        RETURN label, count
        """
    )
    dynamic_counts = {row["label"].lower() + "_count": row["count"] for row in dynamic_stats}
    for label in ["dpptemplate_count", "templateterm_count", "templateuser_count"]:
        stats[label] = dynamic_counts.get(label, 0)

    # Count relationships
    rel_result = await client.run_query("MATCH ()-[r:NEEDS]->() RETURN count(r) AS count")
    stats["needs_relationships"] = rel_result[0]["count"] if rel_result else 0

    return stats
