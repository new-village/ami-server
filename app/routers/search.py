"""Search API router for finding nodes by properties."""

from fastapi import APIRouter, HTTPException, Query

from app.database import get_session
from app.models import (
    GraphNode,
    NodeLabel,
    SearchResponse,
)

router = APIRouter(prefix="/search", tags=["search"])


def _neo4j_node_to_graph_node(record: dict, node_key: str = "n") -> GraphNode:
    """Convert a Neo4j node record to a GraphNode model."""
    node = record[node_key]
    properties = dict(node)
    node_id = properties.pop("node_id", 0)

    # Get label from the node
    labels = list(node.labels)
    label = labels[0] if labels else "Unknown"

    return GraphNode(
        id=node.element_id,
        node_id=node_id,
        label=label,
        properties=properties,
    )


@router.get(
    "/by-id/{node_id}",
    response_model=SearchResponse,
    summary="Search node by node_id",
    description="Find a specific node by its node_id property across all node labels.",
)
async def search_by_node_id(
    node_id: int,
    label: NodeLabel | None = Query(None, description="Optional: filter by node label"),
) -> SearchResponse:
    """Search for a node by its node_id property.

    Args:
        node_id: The node_id to search for.
        label: Optional node label to filter results.

    Returns:
        SearchResponse with matching nodes.
    """
    if label:
        query = f"MATCH (n:`{label.value}`) WHERE n.node_id = $node_id RETURN n"
    else:
        query = "MATCH (n) WHERE n.node_id = $node_id RETURN n"

    async with get_session() as session:
        result = await session.run(query, {"node_id": node_id})
        records = await result.data()

    nodes = [_neo4j_node_to_graph_node(record) for record in records]

    return SearchResponse(nodes=nodes, total=len(nodes))


@router.get(
    "/by-name",
    response_model=SearchResponse,
    summary="Search nodes by name",
    description="Find nodes with names containing the search term (case-insensitive).",
)
async def search_by_name(
    name: str = Query(..., min_length=1, description="Name to search for"),
    label: NodeLabel | None = Query(None, description="Optional: filter by node label"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results to return"),
) -> SearchResponse:
    """Search for nodes by name (partial match).

    Args:
        name: The name to search for (case-insensitive partial match).
        label: Optional node label to filter results.
        limit: Maximum number of results to return.

    Returns:
        SearchResponse with matching nodes.
    """
    if label:
        query = f"""
        MATCH (n:`{label.value}`)
        WHERE toLower(n.name) CONTAINS toLower($name)
        RETURN n
        LIMIT $limit
        """
    else:
        query = """
        MATCH (n)
        WHERE n.name IS NOT NULL AND toLower(n.name) CONTAINS toLower($name)
        RETURN n
        LIMIT $limit
        """

    async with get_session() as session:
        result = await session.run(query, {"name": name, "limit": limit})
        records = await result.data()

    nodes = [_neo4j_node_to_graph_node(record) for record in records]

    return SearchResponse(nodes=nodes, total=len(nodes))


@router.get(
    "/by-property",
    response_model=SearchResponse,
    summary="Search nodes by any property",
    description="Find nodes by a specific property name and value.",
)
async def search_by_property(
    property_name: str = Query(..., description="Property name to search"),
    property_value: str = Query(..., description="Property value to match"),
    label: NodeLabel | None = Query(None, description="Optional: filter by node label"),
    exact_match: bool = Query(False, description="If true, perform exact match; otherwise partial match"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results to return"),
) -> SearchResponse:
    """Search for nodes by a specific property.

    Args:
        property_name: The property name to search.
        property_value: The property value to match.
        label: Optional node label to filter results.
        exact_match: Whether to perform exact or partial matching.
        limit: Maximum number of results to return.

    Returns:
        SearchResponse with matching nodes.
    """
    # Validate property name to prevent injection
    allowed_properties = {
        "node_id", "name", "countries", "country_codes", "sourceID",
        "valid_until", "note", "status", "address", "internal_id",
        "original_name", "former_name", "jurisdiction", "jurisdiction_description",
        "company_type", "incorporation_date", "inactivation_date",
        "struck_off_date", "dorm_date", "service_provider", "ibcRUC"
    }

    if property_name not in allowed_properties:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid property name. Allowed properties: {', '.join(sorted(allowed_properties))}"
        )

    if exact_match:
        if label:
            query = f"""
            MATCH (n:`{label.value}`)
            WHERE n.`{property_name}` = $value
            RETURN n
            LIMIT $limit
            """
        else:
            query = f"""
            MATCH (n)
            WHERE n.`{property_name}` = $value
            RETURN n
            LIMIT $limit
            """
    else:
        if label:
            query = f"""
            MATCH (n:`{label.value}`)
            WHERE toString(n.`{property_name}`) CONTAINS $value
            RETURN n
            LIMIT $limit
            """
        else:
            query = f"""
            MATCH (n)
            WHERE toString(n.`{property_name}`) CONTAINS $value
            RETURN n
            LIMIT $limit
            """

    async with get_session() as session:
        result = await session.run(query, {"value": property_value, "limit": limit})
        records = await result.data()

    nodes = [_neo4j_node_to_graph_node(record) for record in records]

    return SearchResponse(nodes=nodes, total=len(nodes))


@router.get(
    "/labels",
    summary="Get available node labels",
    description="Return all available node labels in the schema.",
)
async def get_labels() -> dict:
    """Get all available node labels.

    Returns:
        Dictionary with available labels and their descriptions.
    """
    return {
        "labels": [
            {"value": NodeLabel.OFFICER.value, "description": "Officers and shareholders (役員/株主)"},
            {"value": NodeLabel.ENTITY.value, "description": "Corporate entities (法人)"},
            {"value": NodeLabel.INTERMEDIARY.value, "description": "Intermediaries (仲介者)"},
            {"value": NodeLabel.ADDRESS.value, "description": "Addresses (住所)"},
        ]
    }
