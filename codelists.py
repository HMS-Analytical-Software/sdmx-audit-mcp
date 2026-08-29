"""Tool implementations for creating/updating/reading FMR codelists.

``update_codelist`` performs an in-place merge: it fetches the current
codelist for the given id+version, merges in added/modified codes by code id,
and resubmits the complete codelist under the same id+version (no automatic
version bump).
"""

from __future__ import annotations

from fmr_client import FmrClient, SubmissionResult
from pysdmx.errors import NotFound
from pysdmx.model import Code, Codelist


def _code_to_dict(code: Code) -> dict:
    return {"id": code.id, "name": code.name, "description": code.description}


def _codelist_to_dict(codelist: Codelist) -> dict:
    return {
        "id": codelist.id,
        "agency": codelist.agency,
        "version": codelist.version,
        "name": codelist.name,
        "description": codelist.description,
        "codes": [_code_to_dict(c) for c in codelist.codes],
    }


def list_codelists(client: FmrClient, agency: str) -> list[dict]:
    """List all codelists maintained by ``agency``."""
    return [_codelist_to_dict(cl) for cl in client.list_codelists(agency)]


def get_codelist(
    client: FmrClient, agency: str, codelist_id: str, version: str = "+"
) -> dict:
    """Return a single codelist. Raises ``ValueError`` if it does not exist."""
    try:
        return _codelist_to_dict(client.get_codelist(agency, codelist_id, version))
    except NotFound as exc:
        raise ValueError(
            f"Codelist '{agency}:{codelist_id}({version})' not found."
        ) from exc


def create_codelist(
    client: FmrClient,
    agency: str,
    codelist_id: str,
    version: str,
    name: str,
    description: str | None = None,
    codes: list[dict] | None = None,
    dry_run: bool = False,
) -> dict:
    """Create a new codelist.

    Raises ``ValueError`` if a codelist with this id+version already exists
    (use ``update_codelist`` instead).
    """
    try:
        client.get_codelist(agency, codelist_id, version)
    except NotFound:
        pass
    else:
        raise ValueError(
            f"Codelist '{agency}:{codelist_id}({version})' already exists; "
            "use update_codelist to modify it."
        )

    new_codelist = Codelist(
        id=codelist_id,
        agency=agency,
        version=version,
        name=name,
        description=description,
        items=[
            Code(id=c["id"], name=c["name"], description=c.get("description"))
            for c in (codes or [])
        ],
    )
    return _submit_result(client.submit(new_codelist, dry_run=dry_run))


def update_codelist(
    client: FmrClient,
    agency: str,
    codelist_id: str,
    version: str,
    add_codes: list[dict] | None = None,
    modify_codes: list[dict] | None = None,
    dry_run: bool = False,
) -> dict:
    """Add and/or modify codes in an existing codelist, in place.

    ``add_codes`` entries must have ids not already present in the codelist.
    ``modify_codes`` entries must have ids that already exist. Raises
    ``ValueError`` for either violation, or if the codelist does not exist.
    """
    try:
        current = client.get_codelist(agency, codelist_id, version)
    except NotFound as exc:
        raise ValueError(
            f"Codelist '{agency}:{codelist_id}({version})' does not exist; "
            "use create_codelist to create it."
        ) from exc

    existing_ids = {c.id for c in current.codes}

    for c in add_codes or []:
        if c["id"] in existing_ids:
            raise ValueError(
                f"Code '{c['id']}' already exists in "
                f"'{agency}:{codelist_id}({version})'; use modify_codes instead."
            )
    modify_ids = {c["id"] for c in (modify_codes or [])}
    missing = modify_ids - existing_ids
    if missing:
        raise ValueError(
            f"Cannot modify non-existent code(s) {sorted(missing)} in "
            f"'{agency}:{codelist_id}({version})'."
        )

    modify_by_id = {c["id"]: c for c in (modify_codes or [])}
    merged_codes = [
        Code(
            id=c.id,
            name=modify_by_id[c.id].get("name", c.name)
            if c.id in modify_by_id
            else c.name,
            description=modify_by_id[c.id].get("description", c.description)
            if c.id in modify_by_id
            else c.description,
        )
        for c in current.codes
    ]
    merged_codes.extend(
        Code(id=c["id"], name=c["name"], description=c.get("description"))
        for c in (add_codes or [])
    )

    updated_codelist = Codelist(
        id=current.id,
        agency=current.agency,
        version=current.version,
        name=current.name,
        description=current.description,
        items=merged_codes,
    )
    return _submit_result(client.submit(updated_codelist, dry_run=dry_run))


def _submit_result(result: SubmissionResult) -> dict:
    return {
        "success": result.success,
        "dry_run": result.dry_run,
        "status_code": result.status_code,
        "message": result.message,
    }
