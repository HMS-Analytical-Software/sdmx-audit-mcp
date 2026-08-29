"""Behavioral tests for codelist creation/update against a live FMR.

These exercise the full journey: create a codelist, reject a duplicate,
add and modify codes in place (same id+version), reject invalid add/modify
requests, list it back, and confirm dry_run previews without mutating FMR.
This also guards the "always resubmit the full merged artefact" design,
which was empirically verified to correctly union codes rather than
destructively replace them.
"""

import uuid

import codelists
import pytest

AGENCY = "BIS"


def _new_codelist_id() -> str:
    return f"CL_MCP_TEST_{uuid.uuid4().hex[:8].upper()}"


def test_create_update_codelist_workflow(fmr_client):
    """Create, duplicate-reject, and in-place update a codelist against FMR."""
    codelist_id = _new_codelist_id()

    created = codelists.create_codelist(
        fmr_client,
        AGENCY,
        codelist_id,
        "1.0",
        "MCP test codelist",
        codes=[{"id": "A", "name": "Alpha"}],
    )
    assert created["success"], created["message"]

    fetched = codelists.get_codelist(fmr_client, AGENCY, codelist_id, "1.0")
    assert [c["id"] for c in fetched["codes"]] == ["A"]

    with pytest.raises(ValueError, match="already exists"):
        codelists.create_codelist(fmr_client, AGENCY, codelist_id, "1.0", "dup")

    updated = codelists.update_codelist(
        fmr_client,
        AGENCY,
        codelist_id,
        "1.0",
        add_codes=[{"id": "B", "name": "Beta"}],
        modify_codes=[{"id": "A", "name": "Alpha Updated"}],
    )
    assert updated["success"], updated["message"]

    fetched = codelists.get_codelist(fmr_client, AGENCY, codelist_id, "1.0")
    codes_by_id = {c["id"]: c["name"] for c in fetched["codes"]}
    assert codes_by_id == {"A": "Alpha Updated", "B": "Beta"}

    listed = codelists.list_codelists(fmr_client, AGENCY)
    assert any(cl["id"] == codelist_id for cl in listed)

    with pytest.raises(ValueError, match="already exists"):
        codelists.update_codelist(
            fmr_client, AGENCY, codelist_id, "1.0", add_codes=[{"id": "A", "name": "x"}]
        )

    with pytest.raises(ValueError, match="non-existent"):
        codelists.update_codelist(
            fmr_client,
            AGENCY,
            codelist_id,
            "1.0",
            modify_codes=[{"id": "ZZZ", "name": "x"}],
        )

    with pytest.raises(ValueError, match="does not exist"):
        codelists.update_codelist(
            fmr_client,
            AGENCY,
            "NO_SUCH_CODELIST",
            "1.0",
            add_codes=[{"id": "A", "name": "x"}],
        )


def test_update_codelist_dry_run_does_not_mutate_registry(fmr_client):
    """A dry_run update_codelist call must not change codes in FMR."""
    codelist_id = _new_codelist_id()
    codelists.create_codelist(
        fmr_client, AGENCY, codelist_id, "1.0", "dry run codelist", codes=[]
    )

    result = codelists.update_codelist(
        fmr_client,
        AGENCY,
        codelist_id,
        "1.0",
        add_codes=[{"id": "C", "name": "Gamma"}],
        dry_run=True,
    )
    assert result["success"]
    assert result["dry_run"]

    fetched = codelists.get_codelist(fmr_client, AGENCY, codelist_id, "1.0")
    assert fetched["codes"] == []
