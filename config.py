"""Runtime configuration for the SDMX authoring MCP server.

All settings are sourced from environment variables so the component
docker-compose can point them at the in-network FMR service without
rebuilding the image.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration.

    Attributes:
        host: Bind address for the Streamable HTTP transport.
        port: Bind port for the Streamable HTTP transport.
        fmr_sdmx_url: FMR's SDMX-REST structure query base URL (reads).
        fmr_submit_url: FMR's secure structure submission endpoint (writes).
        fmr_root_user: Username for HTTP Basic auth against fmr_submit_url.
        fmr_root_password: Password for HTTP Basic auth against fmr_submit_url.
        root_agency: The agency that maintains the top-level agency scheme
            (the one listing top-level agencies such as BIS, OECD, etc.).
    """

    model_config = SettingsConfigDict(env_prefix="")

    host: str = "0.0.0.0"  # nosec B104 - intentional bind-all inside a container
    port: int = 8000

    fmr_sdmx_url: str = "http://fmr:8179/sdmx/v2"
    fmr_submit_url: str = "http://fmr:8179/ws/secure/sdmxapi/rest/"
    fmr_root_user: str = "root"
    fmr_root_password: str = "password"  # noqa: S105 - dev placeholder, overridden via env var

    root_agency: str = "SDMX"


def get_settings() -> Settings:
    """Return a freshly-loaded Settings instance (re-reads the environment)."""
    return Settings()
