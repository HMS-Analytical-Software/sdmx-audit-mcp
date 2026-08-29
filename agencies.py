"""Tool implementations for creating/updating/reading FMR agencies.

Agencies live in per-parent ``AgencyScheme`` artefacts (id ``AGENCIES``,
version ``1.0``, maintained by the parent agency itself) - e.g. the lab's
root scheme is ``SDMX:AGENCIES(1.0)`` and lists top-level agencies such as
``BIS``; ``BIS:AGENCIES(1.0)`` in turn lists BIS's own sub-agencies.

Create/update always fetch the current set of agencies for the parent, merge
the requested change in Python, and resubmit the *complete* scheme. This makes
correctness independent of whatever item-merge semantics FMR applies
server-side to a resubmitted maintainable artefact.

Id normalisation: pysdmx's ``get_agencies(parent)`` returns each agency's
``id`` fully qualified with its ancestor path (e.g. ``BIS.CBS`` for the 'CBS'
agency under 'BIS'), but FMR's submission API requires the short, local id
(``CBS``) when resubmitting an item under that same parent scheme. This
module normalises transparently: ``list_agencies`` returns fully-qualified
ids; ``create_agency``/``update_agency`` accept either the short id or the
fully-qualified one for ``agency_id``.
"""

from __future__ import annotations

from fmr_client import FmrClient, SubmissionResult
from pysdmx.model.__base import Agency, Contact
from pysdmx.model.organisation import AgencyScheme


def _short_id(qualified_id: str, parent_agency: str) -> str:
    """Strip a ``{parent_agency}.`` prefix from a fully-qualified agency id."""
    prefix = f"{parent_agency}."
    return qualified_id.removeprefix(prefix)


def _agency_to_dict(agency: Agency) -> dict:
    return {
        "id": agency.id,
        "name": agency.name,
        "description": agency.description,
        "contacts": [
            {
                "name": c.name,
                "department": c.department,
                "role": c.role,
                "emails": list(c.emails) if c.emails else [],
            }
            for c in (agency.contacts or [])
        ],
    }


def list_agencies(client: FmrClient, parent_agency: str) -> list[dict]:
    """List the agencies maintained under ``parent_agency``.

    Returned ``id`` values are fully qualified with the parent path (as
    returned by pysdmx), e.g. ``BIS.CBS``.
    """
    return [_agency_to_dict(a) for a in client.get_agencies(parent_agency)]


def _build_contacts(contacts: list[dict] | None) -> list[Contact]:
    return [
        Contact(
            name=c.get("name"),
            department=c.get("department"),
            role=c.get("role"),
            emails=c.get("emails"),
        )
        for c in (contacts or [])
    ]


def create_agency(
    client: FmrClient,
    parent_agency: str,
    agency_id: str,
    name: str,
    description: str | None = None,
    contacts: list[dict] | None = None,
    dry_run: bool = False,
) -> dict:
    """Create a new agency under ``parent_agency``.

    Raises ``ValueError`` if an agency with ``agency_id`` already exists under
    ``parent_agency`` (use ``update_agency`` instead).
    """
    short_id = _short_id(agency_id, parent_agency)
    existing = client.get_agencies(parent_agency)
    existing_short = [
        Agency(
            id=_short_id(a.id, parent_agency),
            name=a.name,
            description=a.description,
            contacts=a.contacts,
        )
        for a in existing
    ]
    if any(a.id == short_id for a in existing_short):
        raise ValueError(
            f"Agency '{short_id}' already exists under '{parent_agency}'; "
            "use update_agency to modify it."
        )

    new_agency = Agency(
        id=short_id,
        name=name,
        description=description,
        contacts=_build_contacts(contacts),
    )
    scheme = AgencyScheme(agency=parent_agency, items=[*existing_short, new_agency])
    return _submit_result(client.submit(scheme, dry_run=dry_run))


def update_agency(
    client: FmrClient,
    parent_agency: str,
    agency_id: str,
    name: str | None = None,
    description: str | None = None,
    contacts: list[dict] | None = None,
    dry_run: bool = False,
) -> dict:
    """Update an existing agency under ``parent_agency``.

    Raises ``ValueError`` if no agency with ``agency_id`` exists under
    ``parent_agency`` (use ``create_agency`` instead). Fields left as ``None``
    keep their current value.
    """
    short_id = _short_id(agency_id, parent_agency)
    existing = client.get_agencies(parent_agency)
    existing_short = [
        Agency(
            id=_short_id(a.id, parent_agency),
            name=a.name,
            description=a.description,
            contacts=a.contacts,
        )
        for a in existing
    ]
    current = next((a for a in existing_short if a.id == short_id), None)
    if current is None:
        raise ValueError(
            f"Agency '{short_id}' does not exist under '{parent_agency}'; "
            "use create_agency to create it."
        )

    updated = Agency(
        id=short_id,
        name=name if name is not None else current.name,
        description=description if description is not None else current.description,
        contacts=_build_contacts(contacts)
        if contacts is not None
        else current.contacts,
    )
    items = [updated if a.id == short_id else a for a in existing_short]
    scheme = AgencyScheme(agency=parent_agency, items=items)
    return _submit_result(client.submit(scheme, dry_run=dry_run))


def _submit_result(result: SubmissionResult) -> dict:
    return {
        "success": result.success,
        "dry_run": result.dry_run,
        "status_code": result.status_code,
        "message": result.message,
    }
