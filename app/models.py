"""Pydantic models for ITO Server API.

Defines schemas for nodes, links, and API responses based on
the Neo4j graph schema (schema/neo4j_importer_model.json).

Node Labels:
- 役員/株主 (Officer): Officers and shareholders
- 法人 (Entity): Corporate entities
- 仲介者 (Intermediary): Intermediaries
- 住所 (Address): Addresses

Relationship Types:
- 役員: Officer relationship
- 仲介: Intermediary relationship
- 所在地: Location relationship
- 登録住所: Registered address relationship
- 同名人物: Same name person
- 同一人物?: Possibly same person
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Enums for Node Labels and Relationship Types
# =============================================================================

class NodeLabel(str, Enum):
    """Available node labels in the graph schema."""

    OFFICER = "役員/株主"
    ENTITY = "法人"
    INTERMEDIARY = "仲介者"
    ADDRESS = "住所"


class RelationshipType(str, Enum):
    """Available relationship types in the graph schema."""

    OFFICER = "役員"
    INTERMEDIARY = "仲介"
    LOCATION = "所在地"
    REGISTERED_ADDRESS = "登録住所"
    SAME_NAME = "同名人物"
    POSSIBLY_SAME = "同一人物?"


# =============================================================================
# Node Models
# =============================================================================

class NodeBase(BaseModel):
    """Base model for all nodes."""

    node_id: int = Field(..., description="Unique node identifier")
    name: str | None = Field(None, description="Name of the node")


class OfficerNode(NodeBase):
    """Officer/Shareholder node (役員/株主)."""

    countries: str | None = None
    country_codes: str | None = None
    sourceID: str | None = None
    valid_until: str | None = None
    note: str | None = None


class EntityNode(NodeBase):
    """Corporate entity node (法人)."""

    original_name: str | None = None
    former_name: str | None = None
    jurisdiction: str | None = None
    jurisdiction_description: str | None = None
    company_type: str | None = None
    address: str | None = None
    internal_id: int | None = None
    incorporation_date: str | None = None
    inactivation_date: str | None = None
    struck_off_date: str | None = None
    dorm_date: str | None = None
    status: str | None = None
    service_provider: str | None = None
    ibcRUC: str | None = None
    country_codes: str | None = None
    countries: str | None = None
    sourceID: str | None = None
    valid_until: str | None = None
    note: str | None = None


class IntermediaryNode(NodeBase):
    """Intermediary node (仲介者)."""

    status: str | None = None
    internal_id: int | None = None
    address: str | None = None
    countries: str | None = None
    country_codes: str | None = None
    sourceID: str | None = None
    valid_until: str | None = None
    note: str | None = None


class AddressNode(NodeBase):
    """Address node (住所)."""

    address: str | None = None
    countries: str | None = None
    country_codes: str | None = None
    sourceID: str | None = None
    valid_until: str | None = None
    note: str | None = None


# =============================================================================
# Graph Response Models (for visualization)
# =============================================================================

class GraphNode(BaseModel):
    """Node representation for graph visualization."""

    id: str = Field(..., description="Unique identifier (element_id from Neo4j)")
    node_id: int = Field(..., description="Node ID property")
    label: str = Field(..., description="Node label (役員/株主, 法人, 仲介者, 住所)")
    properties: dict[str, Any] = Field(default_factory=dict, description="Node properties")


class GraphLink(BaseModel):
    """Link/Edge representation for graph visualization."""

    id: str = Field(..., description="Unique identifier (element_id from Neo4j)")
    source: str = Field(..., description="Source node element_id")
    target: str = Field(..., description="Target node element_id")
    type: str = Field(..., description="Relationship type")
    properties: dict[str, Any] = Field(default_factory=dict, description="Relationship properties")


class SubgraphResponse(BaseModel):
    """Response model for subgraph queries."""

    nodes: list[GraphNode] = Field(default_factory=list, description="List of nodes")
    links: list[GraphLink] = Field(default_factory=list, description="List of links/edges")


# =============================================================================
# Search Request/Response Models
# =============================================================================

class SearchRequest(BaseModel):
    """Request model for node search."""

    node_id: int | None = Field(None, description="Search by node_id")
    name: str | None = Field(None, description="Search by name (partial match)")
    label: NodeLabel | None = Field(None, description="Filter by node label")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results to return")


class SearchResponse(BaseModel):
    """Response model for node search."""

    nodes: list[GraphNode] = Field(default_factory=list)
    total: int = Field(default=0, description="Total number of results")


# =============================================================================
# Network Traversal Request/Response Models
# =============================================================================

class NetworkRequest(BaseModel):
    """Request model for network traversal."""

    node_id: int = Field(..., description="Starting node ID")
    label: NodeLabel | None = Field(None, description="Label of the starting node")
    hops: int = Field(default=1, ge=1, le=5, description="Number of hops to traverse")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum entities to return")


# =============================================================================
# Cypher Query Request/Response Models
# =============================================================================

class CypherRequest(BaseModel):
    """Request model for arbitrary Cypher queries."""

    query: str = Field(..., description="Cypher query to execute")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Query parameters")


class CypherResponse(BaseModel):
    """Response model for Cypher query results."""

    results: list[dict[str, Any]] = Field(default_factory=list, description="Raw query results")
    count: int = Field(default=0, description="Number of records returned")


# =============================================================================
# Health Check Response
# =============================================================================

class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Service status")
    database: str = Field(..., description="Database connection status")
    version: str = Field(..., description="API version")
