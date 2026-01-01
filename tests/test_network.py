"""Tests for the Network Traversal API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def create_mock_path(nodes, relationships):
    """Create a mock Neo4j path object."""
    mock_path = MagicMock()
    mock_path.nodes = nodes
    mock_path.relationships = relationships
    return mock_path


def create_mock_node(element_id, labels, properties):
    """Create a mock Neo4j node."""
    mock_node = MagicMock()
    mock_node.element_id = element_id
    mock_node.labels = frozenset(labels)

    def mock_iter():
        return iter(properties.items())

    mock_node.__iter__ = mock_iter
    mock_node.items = lambda: properties.items()
    return mock_node


def create_mock_relationship(element_id, rel_type, start_node, end_node, properties):
    """Create a mock Neo4j relationship."""
    mock_rel = MagicMock()
    mock_rel.element_id = element_id
    mock_rel.type = rel_type
    mock_rel.start_node = start_node
    mock_rel.end_node = end_node

    def mock_iter():
        return iter(properties.items())

    mock_rel.__iter__ = mock_iter
    mock_rel.items = lambda: properties.items()
    return mock_rel


class TestNetworkTraverse:
    """Tests for the network traversal endpoint."""

    @pytest.mark.asyncio
    async def test_traverse_with_results(self, test_client):
        """Test traversing network with valid results."""
        node1 = create_mock_node("4:test:1", ["法人"], {"node_id": 12345, "name": "Company A"})
        node2 = create_mock_node("4:test:2", ["役員/株主"], {"node_id": 12346, "name": "Person B"})
        rel = create_mock_relationship("5:test:1", "役員", node2, node1, {"rel_type": "director"})
        mock_path = create_mock_path([node1, node2], [rel])

        mock_result = MagicMock()
        mock_result.data = AsyncMock(return_value=[{"path": mock_path}])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        with patch("app.routers.network.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await test_client.get("/api/v1/network/traverse/12345")

            assert response.status_code == 200
            data = response.json()
            assert "nodes" in data
            assert "links" in data
            assert len(data["nodes"]) == 2
            assert len(data["links"]) == 1

    @pytest.mark.asyncio
    async def test_traverse_node_not_found(self, test_client):
        """Test traversing from a non-existent node."""
        # First query returns no paths
        mock_result = MagicMock()
        mock_result.data = AsyncMock(return_value=[])

        # Check query also returns no results
        mock_check_result = MagicMock()
        mock_check_result.data = AsyncMock(return_value=[])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(side_effect=[mock_result, mock_check_result])
        mock_session.close = AsyncMock()

        with patch("app.routers.network.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await test_client.get("/api/v1/network/traverse/99999999")

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_traverse_with_custom_hops(self, test_client):
        """Test traversing with custom number of hops."""
        node1 = create_mock_node("4:test:1", ["法人"], {"node_id": 12345, "name": "Company A"})
        mock_path = create_mock_path([node1], [])

        mock_result = MagicMock()
        mock_result.data = AsyncMock(return_value=[{"path": mock_path}])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        with patch("app.routers.network.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await test_client.get("/api/v1/network/traverse/12345?hops=3")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_traverse_hops_limit_enforced(self, test_client):
        """Test that hops limit is enforced."""
        response = await test_client.get("/api/v1/network/traverse/12345?hops=10")

        # Should return 422 due to validation error (max 5)
        assert response.status_code == 422


class TestGetNeighbors:
    """Tests for the get neighbors endpoint."""

    @pytest.mark.asyncio
    async def test_get_neighbors(self, test_client):
        """Test getting neighbors of a node."""
        node1 = create_mock_node("4:test:1", ["法人"], {"node_id": 12345, "name": "Company A"})
        node2 = create_mock_node("4:test:2", ["役員/株主"], {"node_id": 12346, "name": "Person B"})
        rel = create_mock_relationship("5:test:1", "役員", node2, node1, {})
        mock_path = create_mock_path([node1, node2], [rel])

        mock_result = MagicMock()
        mock_result.data = AsyncMock(return_value=[{"path": mock_path}])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        with patch("app.routers.network.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await test_client.get("/api/v1/network/neighbors/12345")

            assert response.status_code == 200
            data = response.json()
            assert "nodes" in data
            assert "links" in data


class TestShortestPath:
    """Tests for the shortest path endpoint."""

    @pytest.mark.asyncio
    async def test_find_shortest_path(self, test_client):
        """Test finding shortest path between two nodes."""
        node1 = create_mock_node("4:test:1", ["法人"], {"node_id": 12345, "name": "Company A"})
        node2 = create_mock_node("4:test:2", ["役員/株主"], {"node_id": 12346, "name": "Person B"})
        rel = create_mock_relationship("5:test:1", "役員", node2, node1, {})
        mock_path = create_mock_path([node1, node2], [rel])

        mock_result = MagicMock()
        mock_result.data = AsyncMock(return_value=[{"path": mock_path}])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        with patch("app.routers.network.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await test_client.get(
                "/api/v1/network/shortest-path?start_node_id=12345&end_node_id=12346"
            )

            assert response.status_code == 200
            data = response.json()
            assert "nodes" in data
            assert "links" in data

    @pytest.mark.asyncio
    async def test_shortest_path_not_found(self, test_client):
        """Test when no path exists between nodes."""
        mock_result = MagicMock()
        mock_result.data = AsyncMock(return_value=[])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        with patch("app.routers.network.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await test_client.get(
                "/api/v1/network/shortest-path?start_node_id=12345&end_node_id=99999"
            )

            assert response.status_code == 404


class TestGetRelationshipTypes:
    """Tests for the get relationship types endpoint."""

    @pytest.mark.asyncio
    async def test_get_relationship_types(self, test_client):
        """Test getting available relationship types."""
        response = await test_client.get("/api/v1/network/relationship-types")

        assert response.status_code == 200
        data = response.json()
        assert "relationship_types" in data
        assert len(data["relationship_types"]) == 6  # 6 relationship types in schema
