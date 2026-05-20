"""MongoDB connection — reuses the LibreChat database instance.

Collections created:
- ``ppt_tasks``: PPT generation task lifecycle
- ``ppt_templates``: uploaded PPT template library

Indexes are ensured once at startup via ``init_db()``.
"""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def init_db() -> AsyncIOMotorDatabase:
    """Initialise the MongoDB connection and ensure indexes.

    If MongoDB is unreachable at startup, the connection handle is still
    returned — Motor will automatically reconnect when the first real
    query is issued.  Index creation is best-effort.
    """
    global _client, _db
    import logging
    logger = logging.getLogger(__name__)

    _client = AsyncIOMotorClient(
        settings.mongo_uri,
        serverSelectionTimeoutMS=5000,  # fast-fail during startup
    )
    _db = _client.get_default_database()

    try:
        # Quick connectivity check
        await _client.admin.command("ping")
        logger.info("MongoDB connected successfully")

        # ---- ppt_tasks indexes ----
        await _db.ppt_tasks.create_index("task_id", unique=True)
        await _db.ppt_tasks.create_index("user_id")
        await _db.ppt_tasks.create_index("conversation_id")
        await _db.ppt_tasks.create_index("status")
        await _db.ppt_tasks.create_index("created_at")

        # ---- ppt_templates indexes ----
        await _db.ppt_templates.create_index("template_id", unique=True)
        await _db.ppt_templates.create_index("category")
        await _db.ppt_templates.create_index("created_at")

        logger.info("MongoDB indexes ensured")
    except Exception as e:
        logger.warning(
            "MongoDB not available at startup (will reconnect lazily): %s", e
        )

    return _db


def get_db() -> AsyncIOMotorDatabase:
    """Return the database handle.  Must be called after ``init_db()``."""
    if _db is None:
        raise RuntimeError("Database not initialised — call init_db() first")
    return _db


async def close_db() -> None:
    """Gracefully close the MongoDB connection."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
