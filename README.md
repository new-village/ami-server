# ITO Server

A FastAPI-based REST API backend for network investigation, connecting to Neo4j Aura database. Designed for deployment on Google Cloud Run.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Cloud Run                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      ITO Server                            │  │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │  │
│  │  │ Search  │  │ Network  │  │ Cypher   │  │  Health   │  │  │
│  │  │   API   │  │   API    │  │   API    │  │   Check   │  │  │
│  │  └────┬────┘  └────┬─────┘  └────┬─────┘  └───────────┘  │  │
│  │       │            │             │                        │  │
│  │       └────────────┼─────────────┘                        │  │
│  │                    │                                      │  │
│  │             ┌──────┴──────┐                               │  │
│  │             │  Neo4j      │                               │  │
│  │             │  Driver     │                               │  │
│  │             │  (Async)    │                               │  │
│  │             └──────┬──────┘                               │  │
│  └────────────────────┼──────────────────────────────────────┘  │
└───────────────────────┼─────────────────────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │   Neo4j Aura    │
              │    Database     │
              └─────────────────┘
```

## ✨ Features

### Core APIs

1. **Search Node API** (`/api/v1/search/`)
   - Find nodes by `node_id`
   - Search by name (partial match)
   - Search by any property
   - Filter by node label

2. **Network Traversal API** (`/api/v1/network/`)
   - Traverse network from a starting node
   - Configurable hop depth (1-5)
   - Find shortest path between nodes
   - Get immediate neighbors
   - Limit total returned entities

3. **Async Cypher API** (`/api/v1/cypher/`)
   - Execute arbitrary Cypher queries
   - Get database schema
   - Get database statistics

### Graph Schema

**Node Labels:**
- `役員/株主` (Officer): Officers and shareholders
- `法人` (Entity): Corporate entities
- `仲介者` (Intermediary): Intermediaries
- `住所` (Address): Addresses

**Relationship Types:**
- `役員`: Officer relationship
- `仲介`: Intermediary relationship
- `所在地`: Location relationship
- `登録住所`: Registered address relationship
- `同名人物`: Same name person
- `同一人物?`: Possibly same person

### Response Format

Subgraph results follow a structured JSON schema for easy integration with visualization libraries:

```json
{
  "nodes": [
    {
      "id": "4:abc:123",
      "node_id": 12345,
      "label": "法人",
      "properties": {
        "name": "Company Name",
        "status": "Active"
      }
    }
  ],
  "links": [
    {
      "id": "5:abc:456",
      "source": "4:abc:123",
      "target": "4:abc:789",
      "type": "役員",
      "properties": {}
    }
  ]
}
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Neo4j Aura database instance

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/new-village/ito-server.git
   cd ito-server
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or
   .venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Configure environment variables**
   
   Create a `.env` file:
   ```env
   NEO4J_URL=neo4j+s://your-instance.databases.neo4j.io
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your-password
   ```

5. **Run the server**
   ```bash
   uvicorn app.main:app --reload --port 8080
   ```

6. **Access the API**
   - Swagger UI: http://localhost:8080/docs
   - ReDoc: http://localhost:8080/redoc
   - OpenAPI JSON: http://localhost:8080/openapi.json

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_search.py -v
```

## 🐳 Docker

### Build Image

```bash
docker build -t ito-server .
```

### Run Container

```bash
docker run -p 8080:8080 \
  -e NEO4J_URL=neo4j+s://your-instance.databases.neo4j.io \
  -e NEO4J_USERNAME=neo4j \
  -e NEO4J_PASSWORD=your-password \
  ito-server
```

## ☁️ Google Cloud Run Deployment

### Using gcloud CLI

1. **Build and push to Container Registry**
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/ito-server
   ```

2. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy ito-server \
     --image gcr.io/YOUR_PROJECT_ID/ito-server \
     --platform managed \
     --region asia-northeast1 \
     --allow-unauthenticated \
     --set-secrets=NEO4J_URL=neo4j-url:latest,NEO4J_USERNAME=neo4j-username:latest,NEO4J_PASSWORD=neo4j-password:latest
   ```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NEO4J_URL` | Neo4j connection URL | Yes |
| `NEO4J_USERNAME` | Neo4j username | Yes |
| `NEO4J_PASSWORD` | Neo4j password | Yes |
| `DEBUG` | Enable debug mode | No (default: false) |
| `CORS_ORIGINS` | Allowed CORS origins | No (default: ["*"]) |

## 📖 API Documentation

### Search API

#### Search All Labels
```http
GET /api/v1/search?node_id={node_id}&limit={limit}
GET /api/v1/search?name={name}&limit={limit}
```

#### Search by Specific Label
```http
GET /api/v1/search/{label}?node_id={node_id}&limit={limit}
GET /api/v1/search/{label}?name={name}&limit={limit}
```

Available labels: `officer`, `entity`, `intermediary`, `address`

#### Get Available Labels
```http
GET /api/v1/search/labels
```

### Network API

#### Traverse Network
```http
GET /api/v1/network/traverse/{node_id}?hops={hops}&limit={limit}
```

#### Get Neighbors
```http
GET /api/v1/network/neighbors/{node_id}?relationship_type={type}&limit={limit}
```

#### Find Shortest Path
```http
GET /api/v1/network/shortest-path?start_node_id={id1}&end_node_id={id2}&max_hops={hops}
```

### Cypher API

#### Execute Query
```http
POST /api/v1/cypher/execute
Content-Type: application/json

{
  "query": "MATCH (n) RETURN n LIMIT 10",
  "parameters": {}
}
```

#### Get Schema
```http
GET /api/v1/cypher/schema
```

#### Get Statistics
```http
GET /api/v1/cypher/stats
```

### Health Endpoints

```http
GET /health    # Health check with database status
GET /ready     # Readiness check
GET /live      # Liveness check
```

## 🔧 Configuration

Configuration is managed via `pydantic-settings`. All settings can be overridden via environment variables.

| Setting | Default | Description |
|---------|---------|-------------|
| `APP_NAME` | "ITO Server" | Application name |
| `APP_VERSION` | "1.0.0" | Application version |
| `DEBUG` | false | Debug mode |
| `DEFAULT_HOPS` | 1 | Default traversal hops |
| `MAX_HOPS` | 5 | Maximum traversal hops |
| `DEFAULT_LIMIT` | 100 | Default result limit |
| `MAX_LIMIT` | 1000 | Maximum result limit |

## 📁 Project Structure

```
ito-server/
├── app/
│   ├── __init__.py
│   ├── config.py          # Configuration with pydantic-settings
│   ├── database.py        # Neo4j connection management
│   ├── main.py            # FastAPI application
│   ├── models.py          # Pydantic models
│   └── routers/
│       ├── __init__.py
│       ├── search.py      # Search API endpoints
│       ├── network.py     # Network traversal endpoints
│       └── cypher.py      # Cypher query endpoints
├── tests/
│   ├── __init__.py
│   ├── conftest.py        # Test fixtures
│   ├── test_main.py
│   ├── test_search.py
│   ├── test_network.py
│   └── test_cypher.py
├── schema/
│   └── neo4j_importer_model.json
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── README.md
```

## 📜 License

This project is licensed under the MIT License.
