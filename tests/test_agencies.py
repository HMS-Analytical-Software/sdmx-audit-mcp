"""Behavioral tests for agency creation/update against a live FMR.

These exercise the full journey a caller (via the MCP tools) goes through:
discover existing agencies, create a new one, reject a duplicate, update it
in place (accepting either the short or fully-qualified id), and reject an
update to a non-existent agency. This also guards the id-normalisation fix
required because pysdmx's get_agencies() returns fully-qualified ids (e.g.
'BIS.CBS') that FMR's submission API rejects if resubmitted as-is.
"""

import uuid

import agencies
import pytest

PARENT_AGENCY = "BIS"


def test_create_update_agency_workflow(fmr_client):
    """Create, duplicate-reject, and update an agency end to end against FMR."""
    agency_id = f"MCP_TEST_{uuid.uuid4().hex[:8].upper()}"

    before = agencies.list_agencies(fmr_client, PARENT_AGENCY)
    assert not any(a["id"].endswith(agency_id) for a in before)

    created = agencies.create_agency(
        fmr_client, PARENT_AGENCY, agency_id, "MCP test agency"
    )
    assert created["success"], created["message"]

    after_create = agencies.list_agencies(fmr_client, PARENT_AGENCY)
    qualified_id = f"{PARENT_AGENCY}.{agency_id}"
    assert any(a["id"] == qualified_id for a in after_create)
    # Existing sub-agencies must be preserved by the fetch-merge-resubmit.
    assert len(after_create) == len(before) + 1

    with pytest.raises(ValueError, match="already exists"):
        agencies.create_agency(fmr_client, PARENT_AGENCY, agency_id, "dup")

    updated = agencies.update_agency(
        fmr_client, PARENT_AGENCY, qualified_id, description="updated via test"
    )
    assert updated["success"], updated["message"]

    after_update = agencies.list_agencies(fmr_client, PARENT_AGENCY)
    entry = next(a for a in after_update if a["id"] == qualified_id)
    assert entry["description"] == "updated via test"
    assert entry["name"] == "MCP test agency"  # untouched field is preserved

    with pytest.raises(ValueError, match="does not exist"):
        agencies.update_agency(fmr_client, PARENT_AGENCY, "NO_SUCH_AGENCY", name="x")


def test_create_agency_dry_run_does_not_mutate_registry(fmr_client):
    """A dry_run create_agency call must not create anything in FMR."""
    agency_id = f"MCP_TEST_{uuid.uuid4().hex[:8].upper()}"

    result = agencies.create_agency(
        fmr_client, PARENT_AGENCY, agency_id, "dry run agency", dry_run=True
    )
    assert result["success"]
    assert result["dry_run"]

    after = agencies.list_agencies(fmr_client, PARENT_AGENCY)
    qualified_id = f"{PARENT_AGENCY}.{agency_id}"
    assert not any(a["id"] == qualified_id for a in after)
