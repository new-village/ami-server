"""Main FastAPI application for ITO Server.

Network Investigation Backend API connecting to Neo4j Aura.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Neo4jConnection
from app.models import HealthResponse
from app.routers import search, network, cypher


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Manage application lifespan events.

    Handles Neo4j driver initialization and cleanup.
    """
    # Startup: Initialize Neo4j connection
    settings = get_settings()
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Connecting to Neo4j at {settings.NEO4J_URL}")

    # Verify connectivity on startup
    try:
        connected = await Neo4jConnection.verify_connectivity()
        if connected:
            print("✅ Successfully connected to Neo4j")
        else:
            print("⚠️ Could not verify Neo4j connection")
    except Exception as e:
        print(f"❌ Neo4j connection error: {e}")

    yield

    # Shutdown: Close Neo4j connection
    print("Shutting down, closing Neo4j connection...")
    await Neo4jConnection.close()
    print("✅ Neo4j connection closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="""
# ITO Server - Network Investigation Backend API

A FastAPI-based REST API that connects to Neo4j Aura and serves as a backend
for a network investigation web application.

## Features

- **Search API**: Find specific nodes by properties (node_id, name, etc.)
- **Network Traversal API**: Retrieve subgraphs with configurable hop depth
- **Cypher API**: Execute arbitrary Cypher queries

## Node Labels

- `役員/株主` (Officer): Officers and shareholders
- `法人` (Entity): Corporate entities
- `仲介者` (Intermediary): Intermediaries
- `住所` (Address): Addresses

## Relationship Types

- `役員`: Officer relationship
- `仲介`: Intermediary relationship
- `所在地`: Location relationship
- `登録住所`: Registered address relationship
- `同名人物`: Same name person
- `同一人物?`: Possibly same person
        """,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # Include routers
    app.include_router(search.router, prefix="/api/v1")
    app.include_router(network.router, prefix="/api/v1")
    app.include_router(cypher.router, prefix="/api/v1")

    return app


# Create the application instance
app = create_app()


@app.get("/", tags=["root"])
async def root() -> dict:
    """Root endpoint returning API information."""
    settings = get_settings()
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Health check endpoint for monitoring and load balancers."""
    settings = get_settings()

    try:
        db_connected = await Neo4jConnection.verify_connectivity()
        db_status = "connected" if db_connected else "disconnected"
    except Exception:
        db_status = "error"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
        version=settings.APP_VERSION,
    )


@app.get("/ready", tags=["health"])
async def readiness_check() -> dict:
    """Readiness check for Kubernetes/Cloud Run."""
    try:
        connected = await Neo4jConnection.verify_connectivity()
        if connected:
            return {"status": "ready"}
        else:
            return {"status": "not ready", "reason": "database disconnected"}
    except Exception as e:
        return {"status": "not ready", "reason": str(e)}


@app.get("/live", tags=["health"])
async def liveness_check() -> dict:
    """Liveness check for Kubernetes/Cloud Run."""
    return {"status": "alive"}
