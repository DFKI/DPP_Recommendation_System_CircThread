"""Async Neo4j client wrapper for the Recommendation Engine."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Manages the async Neo4j driver lifecycle."""

    def __init__(self, uri: str, user: str, password: str):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """Initialize the Neo4j driver."""
        self._driver = AsyncGraphDatabase.driver(
            self._uri,
            auth=(self._user, self._password),
        )
        # Verify connectivity
        try:
            await self._driver.verify_connectivity()
            logger.info("Connected to Neo4j at %s", self._uri)
        except Exception as e:
            logger.error("Failed to connect to Neo4j: %s", e)
            raise

    async def close(self) -> None:
        """Close the Neo4j driver."""
        if self._driver:
            await self._driver.close()
            logger.info("Neo4j connection closed")

    @asynccontextmanager
    async def session(self):
        """Create an async session context manager."""
        if not self._driver:
            raise RuntimeError("Neo4j client not connected. Call connect() first.")
        async with self._driver.session() as session:
            yield session

    async def run_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict]:
        """Execute a Cypher query and return results as list of dicts."""
        async with self.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def run_write(self, query: str, parameters: dict[str, Any] | None = None) -> None:
        """Execute a write Cypher query."""
        async with self.session() as session:
            await session.run(query, parameters or {})
