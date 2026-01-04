"""Tests for the Cypher API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def create_mock_node(element_id, labels, properties):
    """Create a mock Neo4j node."""
    mock_node = MagicMock()
    mock_node.element_id = element_id
    mock_node.labels = frozenset(labels)
    mock_node.__iter__ = lambda self: iter(properties.items())
    mock_node.items = lambda: properties.items()
    return mock_node


def create_mock_relationship(element_id, rel_type, start_node, end_node, properties):
    """Create a mock Neo4j relationship."""
    mock_rel = MagicMock()
    mock_rel.element_id = element_id
    mock_rel.type = rel_type
    mock_rel.start_node = start_node
    mock_rel.end_node = end_node
    mock_rel.items = lambda: properties.items()
    mock_rel.__iter__ = lambda self: iter(properties.items())
    # Remove labels attribute to differentiate from nodes
    del mock_rel.labels
    return mock_rel


class MockAsyncIterator:
    """Mock async iterator for Neo4j results."""
    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        # Create a mock record with values() method
        mock_record = MagicMock()
        if isinstance(item, dict):
            mock_record.values = MagicMock(return_value=list(item.values()))
        else:
            mock_record.values = MagicMock(return_value=[item])
        return mock_record


class TestExecuteCypher:
    """Tests for the execute Cypher endpoint."""

    @pytest.mark.asyncio
    async def test_execute_valid_query(self, authenticated_test_client):
        """Test executing a valid Cypher query returning nodes."""
        node1 = create_mock_node("4:test:1", ["entity"], {"node_id": 12345, "name": "Company A"})
        node2 = create_mock_node("4:test:2", ["officer"], {"node_id": 12346, "name": "Person B"})
        # Use the same node objects in the relationship to avoid duplication
        rel = create_mock_relationship("5:test:1", "役員", node2, node1, {})

        mock_result = MagicMock()
        mock_result.keys = MagicMock(return_value=["n", "r", "m"])
        mock_result.__aiter__ = lambda self: MockAsyncIterator([{"n": node1, "r": rel, "m": node2}])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        with patch("app.routers.cypher.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await authenticated_test_client.post(
                "/api/v1/cypher/execute",
                json={"query": "MATCH (n)-[r]-(m) RETURN n, r, m LIMIT 1"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "components" in data
            assert "total_nodes" in data
            assert "total_links" in data
            assert "component_count" in data
            # Should have at least 2 nodes and 1 link in 1 component
            # Note: relationship's start_node/end_node might add extra nodes
            assert data["total_nodes"] >= 2
            assert data["total_links"] == 1
            assert data["component_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_empty_query(self, authenticated_test_client):
        """Test that empty queries are rejected."""
        response = await authenticated_test_client.post(
            "/api/v1/cypher/execute",
            json={"query": ""}
        )

        assert response.status_code == 400
        data = response.json()
        assert "empty" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_execute_with_parameters(self, authenticated_test_client):
        """Test executing query with parameters."""
        mock_result = MagicMock()
        mock_result.keys = MagicMock(return_value=["n"])
        mock_result.__aiter__ = lambda self: MockAsyncIterator([])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        with patch("app.routers.cypher.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await authenticated_test_client.post(
                "/api/v1/cypher/execute",
                json={
                    "query": "MATCH (n {node_id: $id}) RETURN n",
                    "parameters": {"id": 12345}
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_nodes"] == 0
            assert data["component_count"] == 0

    @pytest.mark.asyncio
    async def test_execute_multiple_components(self, authenticated_test_client):
        """Test that disconnected nodes are returned as separate components."""
        # Two disconnected nodes
        node1 = create_mock_node("4:test:1", ["entity"], {"node_id": 12345, "name": "Company A"})
        node2 = create_mock_node("4:test:2", ["entity"], {"node_id": 12346, "name": "Company B"})

        mock_result = MagicMock()
        mock_result.keys = MagicMock(return_value=["n"])
        mock_result.__aiter__ = lambda self: MockAsyncIterator([{"n": node1}, {"n": node2}])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        with patch("app.routers.cypher.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await authenticated_test_client.post(
                "/api/v1/cypher/execute",
                json={"query": "MATCH (n:entity) RETURN n LIMIT 2"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_nodes"] == 2
            assert data["total_links"] == 0
            assert data["component_count"] == 2  # Two disconnected nodes

    @pytest.mark.asyncio
    async def test_execute_dangerous_query_rejected(self, authenticated_test_client):
        """Test that dangerous queries are rejected."""
        dangerous_queries = [
            "DELETE n",
            "MATCH (n) DELETE n",
            "DROP INDEX my_index",
        ]

        for query in dangerous_queries:
            response = await authenticated_test_client.post(
                "/api/v1/cypher/execute",
                json={"query": query}
            )

            assert response.status_code == 403, f"Query should be rejected: {query}"

    @pytest.mark.asyncio
    async def test_execute_requires_auth(self, test_client):
        """Test that execute endpoint requires authentication."""
        response = await test_client.post(
            "/api/v1/cypher/execute",
            json={"query": "MATCH (n) RETURN n LIMIT 1"}
        )

        assert response.status_code == 401


class TestGetSchema:
    """Tests for the get schema endpoint."""

    @pytest.mark.asyncio
    async def test_get_schema(self, authenticated_test_client):
        """Test getting database schema."""

        class MockAsyncIterator:
            def __init__(self, items):
                self.items = items
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        mock_labels_result = MagicMock()
        mock_labels_result.__aiter__ = lambda self: MockAsyncIterator([
            {"label": "entity"}, {"label": "officer"}
        ])

        mock_rels_result = MagicMock()
        mock_rels_result.__aiter__ = lambda self: MockAsyncIterator([
            {"relationshipType": "officer_of"}
        ])

        mock_props_result = MagicMock()
        mock_props_result.__aiter__ = lambda self: MockAsyncIterator([
            {"propertyKey": "name"}
        ])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(side_effect=[
            mock_labels_result,
            mock_rels_result,
            mock_props_result
        ])
        mock_session.close = AsyncMock()

        with patch("app.routers.cypher.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await authenticated_test_client.get("/api/v1/cypher/schema")

            assert response.status_code == 200
            data = response.json()
            assert "node_labels" in data
            assert "relationship_types" in data
            assert "property_keys" in data

    @pytest.mark.asyncio
    async def test_get_schema_requires_auth(self, test_client):
        """Test that schema endpoint requires authentication."""
        response = await test_client.get("/api/v1/cypher/schema")
        assert response.status_code == 401


class TestGetStats:
    """Tests for the get statistics endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats(self, authenticated_test_client):
        """Test getting database statistics."""
        mock_record = MagicMock()
        mock_record.__getitem__ = lambda self, key: {"nodeCount": 1000, "relationshipCount": 5000}[key]

        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value=mock_record)

        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        with patch("app.routers.cypher.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await authenticated_test_client.get("/api/v1/cypher/stats")

            assert response.status_code == 200
            data = response.json()
            assert "node_count" in data
            assert "relationship_count" in data

    @pytest.mark.asyncio
    async def test_get_stats_requires_auth(self, test_client):
        """Test that stats endpoint requires authentication."""
        response = await test_client.get("/api/v1/cypher/stats")
        assert response.status_code == 401
