"""Shared configuration for all Digital Product Memory microservices."""

import os


class Settings:
    """Central configuration loaded from environment variables."""

    # Neo4j
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    # Local development default only; production deployments must set NEO4J_PASSWORD.
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "circthread2024")

    # Service URLs
    SERVICE_REGISTRY_URL: str = os.getenv("SERVICE_REGISTRY_URL", "http://localhost:8003")
    RECOMMENDATION_ENGINE_URL: str = os.getenv("RECOMMENDATION_ENGINE_URL", "http://localhost:8002")
    MOCK_PROVIDER_URL: str = os.getenv("MOCK_PROVIDER_URL", "http://localhost:8010")

    # Salt for deriving the internal (pseudonymous) identifiers of template users. Client
    # identifiers are never stored in Neo4j; only a salted hash of them is kept.
    TEMPLATE_USER_SALT: str = os.getenv("TEMPLATE_USER_SALT", "circthread-dpp-template-users")

    # Service Ports
    RESOLVER_PORT: int = int(os.getenv("RESOLVER_PORT", "8001"))
    RECOMMENDATION_ENGINE_PORT: int = int(os.getenv("RECOMMENDATION_ENGINE_PORT", "8002"))
    SERVICE_REGISTRY_PORT: int = int(os.getenv("SERVICE_REGISTRY_PORT", "8003"))
    MOCK_PROVIDER_PORT: int = int(os.getenv("MOCK_PROVIDER_PORT", "8010"))


settings = Settings()
