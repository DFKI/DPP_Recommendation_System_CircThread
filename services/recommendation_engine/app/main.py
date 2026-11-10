"""Recommendation Engine – FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from shared.config import settings
from app.neo4j_client import Neo4jClient
from app.knowledge_graph import (
    attach_external_mappings,
    filter_product_data,
    get_core_recommendations,
    get_available_roles,
    get_available_events,
    get_available_product_types,
    get_vocabulary_terms,
    create_dpp_template,
    update_dpp_template,
    delete_dpp_template,
    get_dpp_templates,
    get_promoted_template_terms,
    get_graph_statistics,
    get_sssom_mappings,
    TEMPLATE_CONTEXT_KEYS,
)
from shared.vocabulary import EVENT_PHASES, LIFECYCLE_PHASES
from app.seed_data import (
    seed_knowledge_graph,
    seed_sssom_mappings,
    check_seed_status,
    check_sssom_seed_status,
    check_static_layer_current,
    ensure_constraints,
)
from app.graph_snapshot import export_graph, graph_is_empty, import_graph, load_snapshot


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Neo4j client and seed KG on startup."""
    client = Neo4jClient(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
    )
    await client.connect()
    app.state.neo4j = client

    await initialise_graph(client)

    yield

    await client.close()


async def initialise_graph(client: Neo4jClient) -> None:
    """Populate an empty database from the bundled snapshot, then make sure it is current.

    1. Empty database and bundled snapshot available: import the snapshot (static ontology
       layer and dynamic template layer, see app/graph_snapshot.py).
    2. Static layer missing or different from the ontology in seed_data.py (e.g. the
       snapshot is older than the code): re-seed the static layer; templates are kept.
    3. SSSOM mapping subgraph missing or outdated: re-seed it.
    """
    if await graph_is_empty(client):
        try:
            snapshot = load_snapshot()
        except (OSError, ValueError) as exc:
            logger.warning("Bundled graph snapshot could not be read: %s", exc)
            snapshot = None
        if snapshot and snapshot.get("nodes"):
            logger.info("Neo4j is empty. Importing bundled graph snapshot (%s)...", snapshot.get("exported_at"))
            try:
                await import_graph(client, snapshot)
            except Exception:
                logger.exception("Importing the bundled graph snapshot failed; seeding from the ontology instead.")
            await ensure_constraints(client)

    if not await check_seed_status(client):
        logger.info("Knowledge Graph is empty. Seeding...")
        await seed_knowledge_graph(client)
    elif not await check_static_layer_current(client):
        logger.info("Static Knowledge Graph layer differs from the ontology definition. Re-seeding...")
        await seed_knowledge_graph(client)
    else:
        logger.info("Knowledge Graph already seeded.")
        if not await check_sssom_seed_status(client):
            logger.info("SSSOM mappings are missing. Seeding SSSOM mapping subgraph...")
            await seed_sssom_mappings(client)


app = FastAPI(
    title="Digital Product Memory Recommendation Engine",
    description="Graph-based recommendation engine for role- and event-specific DPP data filtering.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request/Response Models ──────────────────────────────────────────────────

class RecommendRequest(BaseModel):
    product_data: dict[str, Any]
    product_type: str
    role: str | None = None
    event: str | None = None


class RecommendFieldsRequest(BaseModel):
    product_type: str
    role: str | None = None
    event: str | None = None


class DppTemplateRequest(BaseModel):
    template_name: str
    terms: list[str]
    role: str | None = None
    event: str | None = None
    product_type: str | None = None
    custom_event: str | None = None
    lifecycle_phase: str | None = None
    user_id: str = "anonymous"


class DppTemplateUpdateRequest(BaseModel):
    """Partial update: context properties that are not sent keep their stored value."""

    template_name: str
    terms: list[str]
    role: str | None = None
    event: str | None = None
    product_type: str | None = None
    custom_event: str | None = None
    lifecycle_phase: str | None = None


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    try:
        stats = await get_graph_statistics(app.state.neo4j)
        return {"status": "healthy", "service": "recommendation-engine", "graph": stats}
    except Exception:
        return {"status": "healthy", "service": "recommendation-engine", "graph": "not connected yet"}


@app.post("/recommend")
async def recommend(request: RecommendRequest):
    """
    Filter product data based on role and event using the Knowledge Graph.

    The KG determines which data fields are relevant and with what priority
    for the given stakeholder role and lifecycle event.
    """
    try:
        result = await filter_product_data(
            client=app.state.neo4j,
            product_data=request.product_data,
            product_type=request.product_type,
            role=request.role,
            event=request.event,
        )
        return result
    except Exception as e:
        logger.error("Recommendation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommend/fields")
async def recommend_fields(request: RecommendFieldsRequest):
    """
    Return the core recommendation (static Knowledge Graph plus dynamic templates) for a
    role, event and product type without product data.

    The Resolver uses this list to preselect the data providers that can contribute the
    recommended fields before any provider is queried.
    """
    try:
        core = await get_core_recommendations(
            app.state.neo4j, request.role, request.event, request.product_type
        )
        await attach_external_mappings(app.state.neo4j, core["fields"])
        return {
            "product_type": request.product_type,
            "role": request.role,
            "event": request.event,
            "filter_mode": core["filter_mode"],
            "fallback": core["fallback"],
            "fields": core["fields"],
        }
    except Exception as e:
        logger.error("Field recommendation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ontology/roles")
async def list_roles():
    """Get all available stakeholder roles."""
    roles = await get_available_roles(app.state.neo4j)
    return {"roles": roles}


@app.get("/ontology/events")
async def list_events():
    """Get all available lifecycle events."""
    events = await get_available_events(app.state.neo4j)
    return {"events": events}


@app.get("/ontology/lifecycle-phases")
async def list_lifecycle_phases():
    """Get the lifecycle phases and the predefined events that belong to each phase."""
    return {
        "lifecycle_phases": [
            {
                "name": name,
                "display_name": display_name,
                "events": sorted(event for event, phase in EVENT_PHASES.items() if phase == name),
            }
            for name, display_name in LIFECYCLE_PHASES.items()
        ]
    }


@app.get("/ontology/product-types")
async def list_product_types():
    """Get all available product types."""
    product_types = await get_available_product_types(app.state.neo4j)
    return {"product_types": product_types}


@app.get("/ontology/terms")
async def list_terms():
    """Get all vocabulary terms available for custom DPP templates."""
    terms = await get_vocabulary_terms(app.state.neo4j)
    return {"terms": terms}


@app.get("/ontology/mappings")
async def list_mappings():
    """Get SSSOM ontology mappings stored in the knowledge graph."""
    return await get_sssom_mappings(app.state.neo4j)


@app.post("/templates")
async def create_template(request: DppTemplateRequest):
    """Store a custom DPP template in the dynamic recommendation graph."""
    try:
        return await create_dpp_template(
            client=app.state.neo4j,
            template_name=request.template_name,
            terms=request.terms,
            role=request.role,
            event=request.event,
            product_type=request.product_type,
            user_id=request.user_id,
            custom_event=request.custom_event,
            lifecycle_phase=request.lifecycle_phase,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Template creation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/templates")
async def list_templates():
    """List custom DPP templates stored in the dynamic graph."""
    templates = await get_dpp_templates(app.state.neo4j)
    return {"templates": templates}


@app.put("/templates/{template_id}")
async def update_template(template_id: str, request: DppTemplateUpdateRequest):
    """Update a custom DPP template; context properties that are not sent are kept."""
    try:
        result = await update_dpp_template(
            client=app.state.neo4j,
            template_id=template_id,
            template_name=request.template_name,
            terms=request.terms,
            context={key: getattr(request, key) for key in TEMPLATE_CONTEXT_KEYS if key in request.model_fields_set},
        )
        if not result:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Template update failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/templates/{template_id}")
async def delete_template(template_id: str):
    """Delete a custom DPP template from the dynamic graph."""
    deleted = await delete_dpp_template(app.state.neo4j, template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return {"message": f"Template '{template_id}' deleted"}


@app.get("/templates/promoted-terms")
async def list_promoted_terms():
    """List terms used in at least two different DPP templates."""
    terms = await get_promoted_template_terms(app.state.neo4j)
    return {"terms": terms, "threshold": 2}


@app.get("/ontology/stats")
async def graph_stats():
    """Get Knowledge Graph statistics."""
    stats = await get_graph_statistics(app.state.neo4j)
    return {"statistics": stats}


@app.get("/graph/snapshot")
async def graph_snapshot():
    """Export the complete knowledge graph (static and template layer) as a JSON snapshot.

    `python scripts/export_neo4j_snapshot.py` stores it as the snapshot bundled with the
    repository, which is imported automatically into an empty Neo4j database.
    """
    return await export_graph(app.state.neo4j)


@app.post("/seed")
async def reseed_graph():
    """Force re-seed the Knowledge Graph (development only)."""
    try:
        await seed_knowledge_graph(app.state.neo4j)
        return {"message": "Knowledge Graph re-seeded successfully"}
    except Exception as e:
        logger.error("Re-seeding failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
