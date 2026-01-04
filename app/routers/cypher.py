"""Async Cypher Query API router for executing arbitrary queries."""

from collections import defaultdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db.neo4j import get_session
from app.models.user import User
from app.models.graph import GraphNode, GraphLink, SubgraphResponse
from app.auth.dependencies import get_current_active_user

router = APIRouter(prefix="/cypher", tags=["cypher"])


class CypherRequest(BaseModel):
    """Request model for Cypher query execution."""

    query: str = Field(..., description="Cypher query to execute")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Query parameters"
    )


class ConnectedComponentsResponse(BaseModel):
    """Response model for Cypher query results with connected components."""

    components: list[SubgraphResponse] = Field(
        default_factory=list,
        description="List of connected components, each containing nodes and links"
    )
    total_nodes: int = Field(default=0, description="Total number of nodes")
    total_links: int = Field(default=0, description="Total number of links")
    component_count: int = Field(default=0, description="Number of connected components")


def _serialize_neo4j_value(value: Any) -> Any:
    """Serialize Neo4j-specific types to JSON-compatible values.

    Args:
        value: A value from Neo4j query result.

    Returns:
        JSON-serializable value.
    """
    if value is None:
        return None

    # Handle Neo4j Node
    if hasattr(value, 'element_id') and hasattr(value, 'labels'):
        return {
            "_type": "node",
            "element_id": value.element_id,
            "labels": list(value.labels),
            "properties": dict(value),
        }

    # Handle Neo4j Relationship
    if hasattr(value, 'element_id') and hasattr(value, 'type'):
        return {
            "_type": "relationship",
            "element_id": value.element_id,
            "type": value.type,
            "start_node_element_id": value.start_node.element_id if value.start_node else None,
            "end_node_element_id": value.end_node.element_id if value.end_node else None,
            "properties": dict(value),
        }

    # Handle Neo4j Path
    if hasattr(value, 'nodes') and hasattr(value, 'relationships'):
        return {
            "_type": "path",
            "nodes": [_serialize_neo4j_value(n) for n in value.nodes],
            "relationships": [_serialize_neo4j_value(r) for r in value.relationships],
        }

    # Handle lists
    if isinstance(value, list):
        return [_serialize_neo4j_value(v) for v in value]

    # Handle dicts
    if isinstance(value, dict):
        return {k: _serialize_neo4j_value(v) for k, v in value.items()}

    # Return primitive values as-is
    return value


def _serialize_record(record: dict) -> dict:
    """Serialize a Neo4j record to a JSON-compatible dictionary.

    Args:
        record: A record from Neo4j query result.

    Returns:
        JSON-serializable dictionary.
    """
    return {key: _serialize_neo4j_value(value) for key, value in record.items()}


def _extract_graph_elements(value: Any, nodes: dict, links: dict) -> None:
    """Extract nodes and relationships from a Neo4j value recursively.

    Args:
        value: A value from Neo4j query result.
        nodes: Dictionary to store extracted nodes (keyed by element_id).
        links: Dictionary to store extracted links (keyed by element_id).
    """
    if value is None:
        return

    # Handle Neo4j Node
    if hasattr(value, 'element_id') and hasattr(value, 'labels'):
        if value.element_id not in nodes:
            properties = dict(value)
            node_id = properties.pop("node_id", 0)
            labels = list(value.labels)
            label = labels[0] if labels else "Unknown"
            nodes[value.element_id] = GraphNode(
                id=value.element_id,
                node_id=node_id,
                label=label,
                properties=properties,
            )
        return

    # Handle Neo4j Relationship
    if hasattr(value, 'element_id') and hasattr(value, 'type'):
        if value.element_id not in links:
            links[value.element_id] = GraphLink(
                id=value.element_id,
                source=value.start_node.element_id if value.start_node else "",
                target=value.end_node.element_id if value.end_node else "",
                type=value.type,
                properties=dict(value) if hasattr(value, 'items') else {},
            )
            # Also extract start and end nodes
            if value.start_node:
                _extract_graph_elements(value.start_node, nodes, links)
            if value.end_node:
                _extract_graph_elements(value.end_node, nodes, links)
        return

    # Handle Neo4j Path
    if hasattr(value, 'nodes') and hasattr(value, 'relationships'):
        for node in value.nodes:
            _extract_graph_elements(node, nodes, links)
        for rel in value.relationships:
            _extract_graph_elements(rel, nodes, links)
        return

    # Handle lists
    if isinstance(value, list):
        for item in value:
            _extract_graph_elements(item, nodes, links)
        return

    # Handle dicts
    if isinstance(value, dict):
        for v in value.values():
            _extract_graph_elements(v, nodes, links)
        return


def _find_connected_components(
    nodes: dict[str, GraphNode],
    links: dict[str, GraphLink]
) -> list[SubgraphResponse]:
    """Find connected components in the graph using Union-Find algorithm.

    Args:
        nodes: Dictionary of nodes keyed by element_id.
        links: Dictionary of links keyed by element_id.

    Returns:
        List of SubgraphResponse, each representing a connected component.
    """
    if not nodes:
        return []

    # Union-Find data structure
    parent: dict[str, str] = {node_id: node_id for node_id in nodes}

    def find(x: str) -> str:
        if parent[x] != x:
            parent[x] = find(parent[x])  # Path compression
        return parent[x]

    def union(x: str, y: str) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Build connections from links
    for link in links.values():
        source, target = link.source, link.target
        # Only union if both endpoints exist in our nodes
        if source in nodes and target in nodes:
            union(source, target)

    # Group nodes by their root
    components: dict[str, list[str]] = defaultdict(list)
    for node_id in nodes:
        root = find(node_id)
        components[root].append(node_id)

    # Build SubgraphResponse for each component
    result: list[SubgraphResponse] = []
    for component_node_ids in components.values():
        component_nodes = [nodes[nid] for nid in component_node_ids]
        component_node_set = set(component_node_ids)

        # Find links where both endpoints are in this component
        component_links = [
            link for link in links.values()
            if link.source in component_node_set and link.target in component_node_set
        ]

        result.append(SubgraphResponse(
            nodes=component_nodes,
            links=component_links,
        ))

    # Sort by component size (largest first)
    result.sort(key=lambda c: len(c.nodes), reverse=True)

    return result


@router.post(
    "/execute",
    response_model=ConnectedComponentsResponse,
    summary="Execute a Cypher query",
    description="Execute an arbitrary Cypher query and return results as connected components. Requires authentication.",
)
async def execute_cypher(
    request: CypherRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ConnectedComponentsResponse:
    """Execute an arbitrary Cypher query.

    Args:
        request: CypherRequest containing the query and optional parameters.
        current_user: The authenticated user (injected by dependency).

    Returns:
        ConnectedComponentsResponse with nodes and links grouped by connected components.

    Raises:
        HTTPException: If query execution fails.
    """
    # Basic query validation
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Block potentially dangerous operations in queries
    dangerous_keywords = ["DELETE", "DETACH DELETE", "DROP", "CREATE INDEX", "DROP INDEX", "CREATE CONSTRAINT", "DROP CONSTRAINT"]
    query_upper = query.upper()

    for keyword in dangerous_keywords:
        # Check if keyword appears as a statement (not just in a string)
        if keyword in query_upper:
            # Allow if it's just a MATCH...RETURN query that happens to contain DELETE in a property value
            if not any(query_upper.startswith(k) for k in ["MATCH", "OPTIONAL MATCH", "WITH", "UNWIND", "CALL", "RETURN"]):
                raise HTTPException(
                    status_code=403,
                    detail=f"Query contains forbidden operation: {keyword}. Only read operations are allowed."
                )
            # Additional check for DELETE/DROP as standalone operations
            if keyword in query_upper.split():
                raise HTTPException(
                    status_code=403,
                    detail=f"Query contains forbidden operation: {keyword}. Only read operations are allowed."
                )

    try:
        nodes: dict[str, GraphNode] = {}
        links: dict[str, GraphLink] = {}

        async with get_session() as session:
            result = await session.run(query, request.parameters)
            # Extract graph elements from all records
            async for record in result:
                for value in record.values():
                    _extract_graph_elements(value, nodes, links)

        # Find connected components
        components = _find_connected_components(nodes, links)

        return ConnectedComponentsResponse(
            components=components,
            total_nodes=len(nodes),
            total_links=len(links),
            component_count=len(components),
        )

    except Exception as e:
        error_message = str(e)
        # Sanitize error message to avoid exposing sensitive information
        if "authentication" in error_message.lower() or "password" in error_message.lower():
            error_message = "Database authentication error"

        raise HTTPException(
            status_code=500,
            detail=f"Query execution failed: {error_message}"
        )


@router.get(
    "/schema",
    summary="Get database schema",
    description="Retrieve the database schema including node labels, relationship types, and properties. Requires authentication.",
)
async def get_schema(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Get the database schema.

    Args:
        current_user: The authenticated user (injected by dependency).

    Returns:
        Dictionary containing node labels, relationship types, and their properties.
    """
    # Get node labels
    labels_query = "CALL db.labels()"

    # Get relationship types
    rel_types_query = "CALL db.relationshipTypes()"

    # Get property keys
    property_keys_query = "CALL db.propertyKeys()"

    try:
        async with get_session() as session:
            # Fetch labels
            labels_result = await session.run(labels_query)
            labels = [record["label"] async for record in labels_result]

            # Fetch relationship types
            rel_result = await session.run(rel_types_query)
            relationship_types = [record["relationshipType"] async for record in rel_result]

            # Fetch property keys
            props_result = await session.run(property_keys_query)
            property_keys = [record["propertyKey"] async for record in props_result]

        return {
            "node_labels": labels,
            "relationship_types": relationship_types,
            "property_keys": property_keys,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve schema: {str(e)}"
        )


@router.get(
    "/stats",
    summary="Get database statistics",
    description="Retrieve basic statistics about the database. Requires authentication.",
)
async def get_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Get basic database statistics.

    Args:
        current_user: The authenticated user (injected by dependency).

    Returns:
        Dictionary containing node and relationship counts.
    """
    stats_query = """
    MATCH (n)
    WITH count(n) AS nodeCount
    MATCH ()-[r]->()
    RETURN nodeCount, count(r) AS relationshipCount
    """

    try:
        async with get_session() as session:
            result = await session.run(stats_query)
            record = await result.single()

            if record:
                return {
                    "node_count": record["nodeCount"],
                    "relationship_count": record["relationshipCount"],
                }
            else:
                return {
                    "node_count": 0,
                    "relationship_count": 0,
                }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )
