"""PPT Engine — FastAPI application entry point.

Starts the API server with:
- Document conversion (MarkItDown)
- Template library management
- Task lifecycle (create / poll / download)
- MCP Server (SSE transport) for LibreChat Agent integration
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db, close_db
from app.deps import init_services

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Startup
    logger.info("PPT Engine starting — port=%d", settings.ppt_engine_port)
    db = await init_db()
    init_services(db)
    logger.info("MongoDB connected, services initialised")
    yield
    # Shutdown
    await close_db()
    logger.info("PPT Engine stopped")


app = FastAPI(
    title="PPT Engine",
    description="AI PPT Generation Microservice — MarkItDown + PPT Master + LiteLLM",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow LibreChat frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from app.routers.convert import router as convert_router
from app.routers.templates import router as templates_router
from app.routers.tasks import router as tasks_router

app.include_router(convert_router)
app.include_router(templates_router)
app.include_router(tasks_router)

# Mount MCP SSE routes for LibreChat Agent integration
from app.mcp.server import create_mcp_routes
for route in create_mcp_routes():
    app.routes.append(route)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "ppt-engine"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.ppt_engine_host,
        port=settings.ppt_engine_port,
        reload=True,
    )
