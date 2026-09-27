# discrete-probability TS client example

A minimal Node/TypeScript client for the [`discrete-probability`](../../)
MCP server, built for an external TypeScript project to call
`compare_two_proportions` (or any of the server's other tools) without
hand-rolling stdio JSON-RPC or a Python client.

Built for `special-projects/wishlist.md`'s `[ai-tcg-caller]` entry: wiring
an external win-rate/balance-testing harness (a TypeScript project) as the
first real external caller of `compare_two_proportions`, instead of that
harness hand-rolling its own significance check or eyeballing a rate gap.

## Why this exists

`discrete-probability` is a Python MCP stdio server (see
`../../server.py`). Any MCP-aware host (Claude Code, an agent SDK, a
custom harness) can already call it directly if it speaks MCP. This
directory is for the case where the caller does **not** already have a
generic MCP client wired up and is a Node/TypeScript codebase -- it shows
exactly how little code that takes.

## Files

- `src/client.ts` -- the reusable part. `McpStdioSession` wraps
  `@modelcontextprotocol/sdk`'s `Client` + `StdioClientTransport`, and
  `session.callTool<T>(name, args)` returns a typed result, preferring
  `structuredContent` and falling back to parsing the text content block
  as JSON -- the same extraction rule
  [`scripts/mcp_client.py`](../../../../scripts/mcp_client.py) uses on the
  Python side, so both language clients agree on what a call returns. A
  tool error (`isError: true`) throws, it does not return silently.
- `src/types.ts` -- the TypeScript shape of `compare_two_proportions`'s
  result (kept in sync with `../../probkit.py`'s docstring/return value by
  hand; there is no generated schema to import from yet).
- `src/example.ts` -- runnable example: the exact "is a 2-point win-rate
  gap between a 300-seed run and a 900-seed run real or noise" scenario
  `[ai-tcg-caller]` describes.
- `src/prove.ts` -- proof script this cycle used to drive the live server
  (success path + a deliberate error case). `proof/run_2026-09-27.txt` is
  its captured output.

## Using this from your own TypeScript project

1. Make sure `python3` is on `PATH` and this repo is checked out somewhere
   your project can reference (or vendor just `tools/discrete-probability/`
   -- it has no dependency on the rest of this repo beyond
   `tools/secure-random`'s CSPRNG helper, which `probkit.py` imports
   directly by relative path; see `../../requirements.txt`).
2. Run `../../../../scripts/mcp_dev_setup.sh` once (or just
   `pip install --user mcp cffi`) so the Python server's own dependencies
   are importable. This is a dev/runtime dependency of the *server*, not
   of your TypeScript project.
3. `npm install @modelcontextprotocol/sdk` in your own project (this
   example's `package.json` pins the version last proven to work here).
4. Copy `src/client.ts` (and `src/types.ts` if you want the typed result)
   into your project, or depend on this directory directly if your build
   can reach it. Point `SERVER_SCRIPT` at your checkout's
   `tools/discrete-probability/server.py`.
5. Call it:

   ```ts
   import { callTool } from "./client.js";
   import type { CompareTwoProportionsResult } from "./types.js";

   const result = await callTool<CompareTwoProportionsResult>(
     "/path/to/claude-tools/tools/discrete-probability/server.py",
     "compare_two_proportions",
     { successes_a: 168, trials_a: 300, successes_b: 522, trials_b: 900, verify: true },
   );
   if (!result.significant) {
     // gap is within noise for these sample sizes -- don't act on it yet
   }
   ```

   For a harness making many calls in one run (e.g. checking several
   variant pairs), open one `McpStdioSession` and reuse it instead of
   paying process-spawn cost per call -- see `src/example.ts`.

### stderr

By default the spawned Python process's stderr is inherited (printed
alongside your own process's stderr) -- see `proof/run_2026-09-27.txt`'s
error-case transcript, which shows the server's own traceback this way.
Pass `stderr: "pipe"` through to `StdioClientTransport` in `client.ts` if
your harness wants to capture or suppress it instead.

## Running this example yourself

```sh
cd tools/discrete-probability/examples/ts-client
npm install
npm run example   # the win-rate scenario above
npm run prove     # success + error-path proof transcript
npm run build     # tsc type-check + emit to dist/
```

`node_modules/` and `dist/` are gitignored; only the source and the
committed proof transcript are checked in.
