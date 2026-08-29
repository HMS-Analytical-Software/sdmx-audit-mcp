"""Pytest fixtures for sdmx-authoring-mcp tests.

Tests drive the tool-implementation functions (agencies.py/codelists.py)
directly against a live FMR instance rather than the MCP transport - the
FastMCP tool-dispatch wrapper in server.py is trivial and adds no behaviour
worth re-testing through the protocol layer.

Tests are skipped if FMR is not reachable (e.g. the labspace stack is not
running), matching the pattern used by labspace/tests/integration.
"""

from __future__ import annotations

import os

import httpx
import pytest
from config import Settings
from fmr_client import FmrClient

BASE_HOST = os.getenv("BASE_HOST", "localhost")
FMR_TEST_USER = os.getenv("FMR_TEST_USER", "demo")
FMR_TEST_PASSWORD = os.getenv("FMR_TEST_PASSWORD", "password")


@pytest.fixture
def fmr_client() -> FmrClient:
    """An FmrClient pointed at the local dev FMR, skipped if unreachable."""
    settings = Settings(
        fmr_sdmx_url=f"http://{BASE_HOST}:5000/sdmx/v2",
        fmr_submit_url=f"http://{BASE_HOST}:5000/ws/secure/sdmxapi/rest/",
        fmr_root_user=FMR_TEST_USER,
        fmr_root_password=FMR_TEST_PASSWORD,
    )
    try:
        httpx.get(settings.fmr_sdmx_url, timeout=5.0)
    except httpx.TransportError:
        pytest.skip(f"FMR not reachable at {settings.fmr_sdmx_url}")
    return FmrClient(settings)
