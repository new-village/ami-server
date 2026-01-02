"""Pytest configuration and fixtures for ITO Server tests."""

import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Set test environment variables before importing app
os.environ["NEO4J_URL"] = "neo4j://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "testpassword"


@pytest.fixture
def mock_neo4j_driver():
    """Create a mock Neo4j driver."""
    mock_driver = MagicMock()
    mock_driver.verify_connectivity = AsyncMock(return_value=True)
    mock_driver.close = AsyncMock()
    return mock_driver


@pytest.fixture
def mock_neo4j_session():
    """Create a mock Neo4j session."""
    mock_session = MagicMock()
    mock_session.close = AsyncMock()
    return mock_session


@pytest.fixture
def mock_neo4j_node():
    """Create a mock Neo4j node."""
    mock_node = MagicMock()
    mock_node.element_id = "4:test:123"
    mock_node.labels = frozenset(["entity"])
    mock_node.__iter__ = lambda self: iter({"node_id": 12345, "name": "Test Company"}.items())

    def mock_items():
        return {"node_id": 12345, "name": "Test Company"}.items()

    mock_node.items = mock_items
    return mock_node


@pytest.fixture
async def test_client(mock_neo4j_driver) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with mocked Neo4j connection."""
    with patch("app.database.AsyncGraphDatabase.driver", return_value=mock_neo4j_driver):
        with patch("app.database.Neo4jConnection._driver", mock_neo4j_driver):
            from app.main import app

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                yield client


@pytest.fixture
def sample_officer_node():
    """Sample officer node data."""
    return {
        "node_id": 10000001,
        "name": "John Doe",
        "countries": "United States",
        "country_codes": "USA",
        "sourceID": "Panama Papers",
        "valid_until": "2020-12-31",
        "note": "",
    }


@pytest.fixture
def sample_entity_node():
    """Sample entity node data."""
    return {
        "node_id": 20000001,
        "name": "Test Corporation Ltd",
        "original_name": "Test Corporation Limited",
        "former_name": "",
        "jurisdiction": "BVI",
        "jurisdiction_description": "British Virgin Islands",
        "company_type": "Standard International Company",
        "address": "123 Main Street, Road Town",
        "internal_id": 12345,
        "incorporation_date": "2010-01-15",
        "inactivation_date": "",
        "struck_off_date": "",
        "dorm_date": "",
        "status": "Active",
        "service_provider": "Mossack Fonseca",
        "ibcRUC": "",
        "country_codes": "VGB",
        "countries": "British Virgin Islands",
        "sourceID": "Panama Papers",
        "valid_until": "The Panama Papers data is current through 2015",
        "note": "",
    }


@pytest.fixture
def sample_subgraph_response():
    """Sample subgraph response data."""
    return {
        "nodes": [
            {
                "id": "4:test:1",
                "node_id": 10000001,
                "label": "役員/株主",
                "properties": {"name": "John Doe", "countries": "USA"},
            },
            {
                "id": "4:test:2",
                "node_id": 20000001,
                "label": "法人",
                "properties": {"name": "Test Corp", "status": "Active"},
            },
        ],
        "links": [
            {
                "id": "5:test:1",
                "source": "4:test:1",
                "target": "4:test:2",
                "type": "役員",
                "properties": {"rel_type": "director"},
            },
        ],
    }
