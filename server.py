# /// script
# dependencies = [
#     "mcp<2",
#     "pysdmx[xml]",
#     "httpx",
#     "pydantic-settings",
# ]
# ///
"""FastMCP server exposing agency and codelist authoring tools for the lab FMR.

Run directly with `uv run server.py` - agencies.py/codelists.py/config.py/
fmr_client.py are plain sibling modules (no package install needed).
"""

from __future__ import annotations

import agencies
import codelists
from config import get_settings
from fmr_client import FmrClient
from mcp.server.fastmcp import FastMCP

settings = get_settings()

mcp = FastMCP(
    name="sdmx-authoring",
    instructions=(
        "Create and update SDMX agencies and codelists in the lab's Fusion "
        "Metadata Registry (FMR). Agencies are organised per parent (e.g. the "
        "root scheme 'SDMX' lists top-level agencies such as BIS; 'BIS' in "
        "turn lists its own sub-agencies). Codelist updates merge codes into "
        "the existing id+version rather than creating a new version. Pass "
        "dry_run=true on any create/update tool to preview the SDMX message "
        "that would be submitted without changing the registry."
    ),
    host=settings.host,
    port=settings.port,
)


def _client() -> FmrClient:
    return FmrClient(settings)


@mcp.tool()
def list_agencies(parent_agency: str) -> list[dict]:
    """List the agencies maintained under ``parent_agency`` (e.g. 'SDMX' for
    top-level agencies, or an existing agency id such as 'BIS' for its
    sub-agencies).
    """
    return agencies.list_agencies(_client(), parent_agency)


@mcp.tool()
def create_agency(
    parent_agency: str,
    agency_id: str,
    name: str,
    description: str | None = None,
    contacts: list[dict] | None = None,
    dry_run: bool = False,
) -> dict:
    """Create a new agency under ``parent_agency``. Fails if it already exists."""
    return agencies.create_agency(
        _client(), parent_agency, agency_id, name, description, contacts, dry_run
    )


@mcp.tool()
def update_agency(
    parent_agency: str,
    agency_id: str,
    name: str | None = None,
    description: str | None = None,
    contacts: list[dict] | None = None,
    dry_run: bool = False,
) -> dict:
    """Update an existing agency under ``parent_agency``. Fails if it does not
    exist. Fields left unset keep their current value.
    """
    return agencies.update_agency(
        _client(), parent_agency, agency_id, name, description, contacts, dry_run
    )


@mcp.tool()
def list_codelists(agency: str) -> list[dict]:
    """List all codelists maintained by ``agency``."""
    return codelists.list_codelists(_client(), agency)


@mcp.tool()
def get_codelist(agency: str, codelist_id: str, version: str = "+") -> dict:
    """Return a single codelist (default ``version='+'`` resolves to the
    latest version).
    """
    return codelists.get_codelist(_client(), agency, codelist_id, version)


@mcp.tool()
def create_codelist(
    agency: str,
    codelist_id: str,
    version: str,
    name: str,
    description: str | None = None,
    codes: list[dict] | None = None,
    dry_run: bool = False,
) -> dict:
    """Create a new codelist. Fails if this id+version already exists."""
    return codelists.create_codelist(
        _client(), agency, codelist_id, version, name, description, codes, dry_run
    )


@mcp.tool()
def update_codelist(
    agency: str,
    codelist_id: str,
    version: str,
    add_codes: list[dict] | None = None,
    modify_codes: list[dict] | None = None,
    dry_run: bool = False,
) -> dict:
    """Add and/or modify codes in an existing codelist, in place (same
    id+version, no automatic version bump). Fails if the codelist does not
    exist, if an ``add_codes`` id already exists, or if a ``modify_codes`` id
    does not exist.
    """
    return codelists.update_codelist(
        _client(), agency, codelist_id, version, add_codes, modify_codes, dry_run
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
