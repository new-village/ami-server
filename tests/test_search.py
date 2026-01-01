"""Tests for the Search API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSearchByNodeId:
    """Tests for the search by node_id endpoint."""

    @pytest.mark.asyncio
    async def test_search_by_node_id_found(self, test_client, mock_neo4j_node):
        """Test searching for a node by node_id."""
        mock_result = MagicMock()
        mock_result.data = AsyncMock(return_value=[{"n": mock_neo4j_node}])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        with patch("app.routers.search.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await test_client.get("/api/v1/search/by-id/12345")

            assert response.status_code == 200
            data = response.json()
            assert "nodes" in data
            assert "total" in data

    @pytest.mark.asyncio
    async def test_search_by_node_id_not_found(self, test_client):
        """Test searching for a non-existent node."""
        mock_result = MagicMock()
        mock_result.data = AsyncMock(return_value=[])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        with patch("app.routers.search.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await test_client.get("/api/v1/search/by-id/99999999")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["nodes"] == []

    @pytest.mark.asyncio
    async def test_search_by_node_id_with_label(self, test_client, mock_neo4j_node):
        """Test searching with a specific label filter."""
        mock_result = MagicMock()
        mock_result.data = AsyncMock(return_value=[{"n": mock_neo4j_node}])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        with patch("app.routers.search.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await test_client.get("/api/v1/search/by-id/12345?label=法人")

            assert response.status_code == 200


class TestSearchByName:
    """Tests for the search by name endpoint."""

    @pytest.mark.asyncio
    async def test_search_by_name(self, test_client, mock_neo4j_node):
        """Test searching for nodes by name."""
        mock_result = MagicMock()
        mock_result.data = AsyncMock(return_value=[{"n": mock_neo4j_node}])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        with patch("app.routers.search.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await test_client.get("/api/v1/search/by-name?name=Test")

            assert response.status_code == 200
            data = response.json()
            assert "nodes" in data
            assert "total" in data

    @pytest.mark.asyncio
    async def test_search_by_name_requires_name_param(self, test_client):
        """Test that name parameter is required."""
        response = await test_client.get("/api/v1/search/by-name")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_search_by_name_with_limit(self, test_client, mock_neo4j_node):
        """Test searching with a custom limit."""
        mock_result = MagicMock()
        mock_result.data = AsyncMock(return_value=[{"n": mock_neo4j_node}])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        with patch("app.routers.search.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await test_client.get("/api/v1/search/by-name?name=Test&limit=50")

            assert response.status_code == 200


class TestSearchByProperty:
    """Tests for the search by property endpoint."""

    @pytest.mark.asyncio
    async def test_search_by_valid_property(self, test_client, mock_neo4j_node):
        """Test searching by a valid property."""
        mock_result = MagicMock()
        mock_result.data = AsyncMock(return_value=[{"n": mock_neo4j_node}])

        mock_session = MagicMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        with patch("app.routers.search.get_session") as mock_get_session:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_context

            response = await test_client.get(
                "/api/v1/search/by-property?property_name=countries&property_value=USA"
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_by_invalid_property(self, test_client):
        """Test that invalid property names are rejected."""
        response = await test_client.get(
            "/api/v1/search/by-property?property_name=invalid_prop&property_value=test"
        )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid property name" in data["detail"]


class TestGetLabels:
    """Tests for the get labels endpoint."""

    @pytest.mark.asyncio
    async def test_get_labels(self, test_client):
        """Test getting available node labels."""
        response = await test_client.get("/api/v1/search/labels")

        assert response.status_code == 200
        data = response.json()
        assert "labels" in data
        assert len(data["labels"]) == 4  # 4 node labels in schema
