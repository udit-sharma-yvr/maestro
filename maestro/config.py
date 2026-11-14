"""Env-driven configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MAESTRO_", extra="ignore")

    # LLM provider + cost-aware routing models.
    llm_provider: str = "anthropic"  # anthropic | openai | bedrock
    router_model: str = "claude-3-5-haiku-20241022"  # cheap: routing + simple answers
    agent_model: str = "claude-3-5-sonnet-20241022"  # strong: tool-use reasoning

    # MCP filesystem server is launched as a subprocess over stdio.
    mcp_server_cmd: str = "python"
    mcp_server_args: str = "-m mcp_tools.filesystem"

    # Directory the MCP filesystem tools are allowed to operate within.
    sandbox_root: Path = Path("sandbox")

    # Server bind.
    host: str = "127.0.0.1"
    port: int = 8000


settings = Settings()
