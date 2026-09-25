#!/usr/bin/env bash
# One-shot preflight for building/testing an MCP server in this repo.
#
# Every tools/<name> MCP server needs the `mcp` package to run its server.py
# and to be driven live for a proof/ transcript. In this container image,
# `mcp`'s dependency chain pulls in `cryptography`, whose optional C backend
# needs `cffi` -- without it, imports fail with a confusing
# `pyo3_runtime.PanicException` / `ModuleNotFoundError: No module named
# '_cffi_backend'` instead of a plain "missing dependency" message. This has
# been rediscovered from scratch across multiple build cycles (see
# special-projects/wishlist.md's [build-env] entry) because neither package
# is committed to the repo -- each tool declares its own requirements.txt,
# and `mcp`/`cffi` are dev-only, needed to *build and prove* a server, not to
# ship one.
#
# Usage: scripts/mcp_dev_setup.sh
# Idempotent: safe to re-run, skips work that's already done.

set -euo pipefail

check_import() {
    python3 -c "import $1" >/dev/null 2>&1
}

if check_import mcp && check_import cffi; then
    echo "mcp_dev_setup: mcp and cffi already importable, nothing to do."
    exit 0
fi

echo "mcp_dev_setup: installing mcp + cffi (pip install --user)..."
pip install --user --quiet mcp cffi

if check_import mcp && check_import cffi; then
    echo "mcp_dev_setup: done. mcp and cffi are importable."
else
    echo "mcp_dev_setup: install ran but import still fails -- check pip output above." >&2
    exit 1
fi
