# sdmx-authoring-mcp

First-party Python MCP server exposing tools to create and update **agencies**
and **codelists** in the lab's Fusion Metadata Registry (FMR), backed by
server-side [`pysdmx`](https://pypi.org/project/pysdmx/). Runs directly with
`uv run server.py` (PEP 723 inline dependencies, no install step) - all files
are plain sibling modules, not an installed package.

## Contents

| File | Purpose |
| ---- | ------- |
| `config.py` | `pydantic-settings`-based configuration (FMR URLs/credentials, bind host/port). |
| `fmr_client.py` | Read access via `pysdmx.api.fmr.RegistryClient` (plus a direct REST call for codelist listing, which the client does not expose) and a `submit()` helper that serialises with `write_sdmx()` and POSTs to FMR's secure submission endpoint. |
| `agencies.py` | Agency list/create/update logic, including the id-normalisation needed because `pysdmx` returns fully-qualified agency ids (see below). |
| `codelists.py` | Codelist list/get/create/update logic (in-place code merge). |
| `server.py` | `FastMCP` (from the official `mcp` SDK, pinned `mcp<2` - v2 renamed this to `MCPServer` with a different API) server wiring the above as MCP tools, served over Streamable HTTP at `/mcp`. Run this directly. |
| `__main__.py` | Alternate entrypoint (`python -m sdmx_authoring_mcp` style) that also runs the Streamable HTTP server. |

## Why the official `mcp` SDK instead of `fastmcp`

This server uses the official
[`mcp`](https://github.com/modelcontextprotocol/python-sdk) Python SDK's
`mcp.server.fastmcp.FastMCP`, which supports Streamable HTTP transport
without an extra third-party dependency. Pinned to `mcp<2`: the installed-by-
default `mcp` 2.x renamed `FastMCP` to `MCPServer` with a different API.

## Agency id normalisation

`RegistryClient.get_agencies(parent_agency)` returns each `Agency.id` fully
qualified with its ancestor path (e.g. `BIS.CBS` for the `CBS` agency under
`BIS`), even though the underlying SDMX-ML stores just the short local id
(`CBS`). Resubmitting an `AgencyScheme` with the fully-qualified id fails
FMR's id-format validation (dots are not a valid SDMX id character). See
`agencies._short_id()` - all create/update logic normalises to the short id
before constructing artefacts for submission, and accepts either form as
input.

## In-place merge safety

`create_agency`/`update_agency`/`update_codelist` all fetch the current
artefact, merge the change in Python, and resubmit the complete artefact
(entire agency list, or entire code list). This was empirically verified
against the lab's local FMR: resubmitting the same `Codelist` id+version with
an expanded code list correctly results in the union of codes, not a
destructive replace - see the package tests.

## Local build & run

```bash
# Runs directly - dependencies are declared inline in server.py (PEP 723),
# uv installs them into an ephemeral environment on first run.
FMR_SDMX_URL=http://localhost:5000/sdmx/v2 \
FMR_SUBMIT_URL=http://localhost:5000/ws/secure/sdmxapi/rest/ \
FMR_ROOT_USER=demo \
FMR_ROOT_PASSWORD=password \
uv run server.py
```

Inside the aio-sandbox, `fmr` (the in-network service name) resolves on the
shared docker network; standalone runs need the labspace stack up and FMR
reachable at the URLs above (adjust host/port to match).

## Tests

```bash
uv run pytest
```

Tests call the tool-implementation functions (`agencies.py`/`codelists.py`)
directly against a live FMR instance (skipped if unreachable), rather than
driving the MCP JSON-RPC transport - the `FastMCP` tool-dispatch wrapper in
`server.py` is trivial and adds no behaviour worth re-testing through the
protocol layer.
