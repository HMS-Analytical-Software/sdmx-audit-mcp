"""Thin wrapper around pysdmx for reading from and writing to the lab FMR.

Reads use ``pysdmx.api.fmr.RegistryClient`` (or a direct REST call for
collection-style listings the client does not expose). Writes serialise
``pysdmx.model`` objects with ``write_sdmx()`` and POST them to FMR's secure
structure submission endpoint using HTTP Basic auth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from config import Settings, get_settings
from pysdmx.api.fmr import RegistryClient
from pysdmx.errors import NotFound
from pysdmx.io import read_sdmx, write_sdmx
from pysdmx.io.format import Format
from pysdmx.model import Codelist


@dataclass
class SubmissionResult:
    """Outcome of submitting one or more maintainable artefacts to FMR.

    Attributes:
        success: Whether FMR reported every submitted artefact as successful.
        status_code: The HTTP status code of the submission request.
        message: The raw SDMX SubmitStructureResponse body (or serialised
            message, when ``dry_run`` was requested and nothing was posted).
        dry_run: Whether this result represents a preview (no POST was made).
    """

    success: bool
    status_code: int | None
    message: str
    dry_run: bool


class FmrClient:
    """Read/write access to the lab FMR for a single request/tool call."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._registry = RegistryClient(self._settings.fmr_sdmx_url)

    # --- Reads -----------------------------------------------------------

    def get_agencies(self, parent_agency: str) -> list[Any]:
        """Return the sub-agencies maintained under ``parent_agency``.

        Returns an empty list if no agency scheme exists yet for
        ``parent_agency`` (rather than raising), since this is a common,
        expected state before the first agency is created under it.
        """
        try:
            return list(self._registry.get_agencies(parent_agency))
        except NotFound:
            return []

    def get_codelist(
        self, agency: str, codelist_id: str, version: str = "+"
    ) -> Codelist:
        """Return a single codelist. Raises ``pysdmx.errors.NotFound`` if absent."""
        return self._registry.get_codes(agency, codelist_id, version)

    def list_codelists(self, agency: str) -> list[Codelist]:
        """Return all codelists maintained by ``agency``.

        ``RegistryClient`` has no wildcard listing method for codelists, so
        this queries the structure REST API directly and parses the response.
        """
        url = f"{self._settings.fmr_sdmx_url}/structure/codelist/{agency}/all/all"
        response = httpx.get(
            url,
            headers={"Accept": "application/vnd.sdmx.structure+xml;version=3.0.0"},
            timeout=30.0,
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        message = read_sdmx(response.text)
        return [s for s in (message.structures or []) if isinstance(s, Codelist)]

    # --- Writes ------------------------------------------------------------

    def submit(self, artefacts: Any, *, dry_run: bool) -> SubmissionResult:
        """Serialise ``artefacts`` and, unless ``dry_run``, submit them to FMR.

        Args:
            artefacts: A single maintainable pysdmx.model object, or a list of
                them (e.g. an ``AgencyScheme`` or ``Codelist``).
            dry_run: If True, only serialise and return the message; no HTTP
                request is made and FMR is not mutated.
        """
        sdmx_message = write_sdmx(
            artefacts,
            sdmx_format=Format.STRUCTURE_SDMX_ML_3_0,
            prettyprint=True,
        )

        if dry_run:
            return SubmissionResult(
                success=True,
                status_code=None,
                message=sdmx_message or "",
                dry_run=True,
            )

        response = httpx.post(
            self._settings.fmr_submit_url,
            content=sdmx_message,
            headers={"Content-Type": "application/xml"},
            auth=(self._settings.fmr_root_user, self._settings.fmr_root_password),
            timeout=30.0,
        )
        success = response.status_code == 200 and 'status="Success"' in response.text
        return SubmissionResult(
            success=success,
            status_code=response.status_code,
            message=response.text,
            dry_run=False,
        )
