"""Entrypoint: runs the SDMX authoring MCP server over Streamable HTTP."""

from server import mcp


def run() -> None:
    """Start the Streamable HTTP server (blocking)."""
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    run()
