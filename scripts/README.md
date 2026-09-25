# scripts/

Repo-internal tooling. Not an MCP server and not a `tools/` entry — these
are dev-time helpers for building, testing, and reporting on the
collection itself, not something an external agent calls over MCP.

## Dashboard

- `build_dashboard.py` / `build_site.py` — render `_site/dashboard.html`
  from `special-projects/cycles.json` and `tools/collection-index`'s scan.
  Gitignored output; rebuild after every cycle instead of committing it:
  `python3 scripts/build_site.py`.

## MCP dev tooling

Building or proving any `tools/*` MCP server locally needs the `mcp`
package (and, in this container image, `cffi`) and a stdio client to
actually drive the server rather than just import it. Both needs were
rediscovered from scratch across several cycles before being fixed here
— see `special-projects/wishlist.md`'s `[build-env]` and `[mcp-proof]`
entries.

- **`mcp_dev_setup.sh`** — one-shot, idempotent preflight. Installs `mcp`
  and `cffi` via `pip install --user` if they aren't already importable.

  ```bash
  ./scripts/mcp_dev_setup.sh
  ```

- **`mcp_client.py`** — a small reusable stdio client for driving any
  server under `tools/*/server.py`, so proving a server works doesn't
  need a one-off throwaway script each cycle. Handles the extraction
  footgun directly: prefers a tool result's `structured_content`, falls
  back to parsing its text content block(s) as JSON.

  ```bash
  # list a server's tools
  python3 scripts/mcp_client.py list-tools tools/secure-random/server.py

  # call one tool
  python3 scripts/mcp_client.py call tools/secure-random/server.py \
      roll_dice '{"notation": "2d6+3"}'

  # run a whole session's worth of labeled calls from one JSON file,
  # in the same "--- label ---\n<value>" shape this repo's tools/*/proof
  # files already use -- optionally straight to a proof file with --out
  python3 scripts/mcp_client.py run tools/secure-random/server.py \
      calls.json --out tools/secure-random/proof/run_2026-XX-XX.txt
  ```

  `calls.json` is a JSON list of `{"label": str, "tool": str, "args":
  dict}` objects; the special tool name `"list_tools"` lists the
  server's tools instead of calling one. `run_calls()` is also importable
  directly for anything that wants typed results in Python rather than
  a printed transcript. See `mcp_client.py`'s own module docstring for
  the full API. Proof it works against two different existing servers:
  `proof/run_2026-09-25.txt`.

Neither script is a repo dependency — `mcp`/`cffi` stay dev-only, exactly
like each `tools/*/requirements.txt` already declares them as that tool's
own concern, not the collection's.
