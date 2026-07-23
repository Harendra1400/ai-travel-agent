"""Typed application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPServerSettings(BaseModel):
    """Connection metadata for one remote streamable-HTTP MCP server."""

    url: HttpUrl
    authorization_env_var: str | None = Field(
        default=None,
        pattern=r"^[A-Z][A-Z0-9_]*$",
    )
    granted_scopes: list[str] = Field(default_factory=list)


class MCPToolSettings(BaseModel):
    """Explicit allow-list entry and risk classification for one MCP tool."""

    server: str = Field(min_length=1, max_length=160)
    tool: str = Field(min_length=1, max_length=160)
    risk: Literal["read", "write", "financial"]
    required_scopes: list[str] = Field(default_factory=list)


class Settings(BaseSettings):
    """Configuration loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TRAVEL_AGENT_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AI Travel Agent API"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: str = (
        "postgresql+psycopg://travel_agent:travel_agent@localhost:5432/travel_agent"
    )
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_memory_collection: str = "travel_memories"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5.6-sol"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_max_output_tokens: int = Field(default=8000, ge=256, le=32_000)
    embedding_dimensions: int = Field(default=1536, gt=0, le=4096)
    mcp_servers: dict[str, MCPServerSettings] = Field(default_factory=dict)
    mcp_tools: list[MCPToolSettings] = Field(default_factory=list)
    mcp_timeout_seconds: float = Field(default=30, gt=0, le=120)
    mcp_max_response_bytes: int = Field(
        default=1_000_000,
        ge=1024,
        le=10_000_000,
    )
    approval_ttl_minutes: int = Field(default=30, gt=0, le=1440)
    readiness_timeout_seconds: float = Field(default=3, gt=0, le=30)
    auth_disabled: bool = True
    auth_issuer: str | None = None
    auth_audience: str | None = None
    auth_jwks_url: str | None = None
    cors_origins: list[str] = ["http://localhost:3000"]
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Refuse unsafe authentication settings in production."""
        if self.environment == "production" and self.auth_disabled:
            raise ValueError("Authentication cannot be disabled in production")
        if self.environment == "production" and "*" in self.allowed_hosts:
            raise ValueError("Wildcard trusted hosts are forbidden in production")
        if self.environment == "production" and "*" in self.cors_origins:
            raise ValueError("Wildcard CORS origins are forbidden in production")
        if not self.auth_disabled and not all(
            (self.auth_issuer, self.auth_audience, self.auth_jwks_url)
        ):
            raise ValueError(
                "OIDC issuer, audience, and JWKS URL are required when auth is enabled"
            )
        unknown_servers = {
            tool.server
            for tool in self.mcp_tools
            if tool.server not in self.mcp_servers
        }
        if unknown_servers:
            raise ValueError(
                "MCP tools reference unknown servers: "
                + ", ".join(sorted(unknown_servers))
            )
        missing_scopes = {
            f"{tool.server}/{tool.tool}": sorted(
                set(tool.required_scopes)
                - set(self.mcp_servers[tool.server].granted_scopes)
            )
            for tool in self.mcp_tools
            if tool.server in self.mcp_servers
            and not set(tool.required_scopes).issubset(
                self.mcp_servers[tool.server].granted_scopes
            )
        }
        if missing_scopes:
            raise ValueError(
                f"MCP server credentials lack required scopes: {missing_scopes}"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Build settings once per application process."""
    return Settings()
