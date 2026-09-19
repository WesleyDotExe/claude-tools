# Claude Tools

A growing collection of **MCP servers, connectors, and tools** — each built to solve a real, expressed problem, then tested and documented so anyone can use it.

> **Note:** This is an independent community project built for use *with* Claude and other MCP-compatible AI assistants. It is **not** an official Anthropic product.

## What this is

Each tool here follows the same discipline:

1. **A real need** — every tool starts from an actual problem people have expressed (a gap in what AI assistants can do, a repetitive task, a missing capability), not a guess.
2. **Built and proven** — each is implemented, run, and verified with a committed proof/example. If it's an MCP server, it has actually been driven by a client, not just scaffolded.
3. **Documented** — every tool has its own README explaining what it does, how it works, and how to run it.

The collection grows over time, and where it makes sense, new tools build on the ones already here.

## The tools

Each tool lives in its own folder under [`tools/`](tools/) with its own README.

- **[`time-arithmetic`](tools/time-arithmetic/)** — an MCP server for date and time math (durations, business-day offsets, timezone-aware calculations) — the kind of thing language models are notoriously unreliable at doing in their heads.
- **[`collection-index`](tools/collection-index/)** — a tool that reads this collection and summarizes what's in it; used to keep the collection self-documenting.
- **[`secure-random`](tools/secure-random/)** — an MCP server for cryptographically-secure randomness (dice, integers, passwords, tokens, UUIDs, weighted picks) plus chi-square tests to prove the output isn't biased — language models can't generate genuine randomness and reliably favor certain "random" answers.
- **[`discrete-probability`](tools/discrete-probability/)** — an MCP server for exact discrete-probability calculations (birthday-paradox collisions, dice-sum distributions, drawing without replacement, binomial trials, Bayes' theorem, a generalized Monty Hall problem), each answer optionally cross-checked against a real Monte Carlo simulation — language models are well-documented to do fine on standard probability questions but drop sharply on "counterintuitive" ones.
- **[`logic-grid-solver`](tools/logic-grid-solver/)** — an MCP server that exactly solves logic grid ("zebra") puzzles from a small structured clue vocabulary, proves whether the solution is unique, and independently re-verifies any proposed answer against the clues — language models are documented to solve these puzzles correctly as rarely as 8% of the time because they can't reliably cross-check every deduction against every other clue at once.
- **[`strips-planner`](tools/strips-planner/)** — an MCP server that exactly solves STRIPS-style planning problems (find a sequence of actions from an initial state to a goal) via real breadth-first search, proves the plan is shortest possible or that the goal is unreachable, and independently replays any candidate plan step by step — planning is a documented LLM failure mode distinct from calculation or constraint satisfaction: models can't reliably track a consistent world-state across many interdependent action effects.
- **[`graph-algorithms`](tools/graph-algorithms/)** — an MCP server for the classic graph algorithms (shortest path, topological sort, minimum spanning tree, max flow), each solved via one algorithm and independently checked via a second, structurally different one (e.g. Dijkstra solved, Bellman-Ford verified) — actively-benchmarked LLM failure territory as graphs grow past a handful of nodes, distinct from every other shape in this collection.

## Using a tool

Each tool's own README has the specifics, but in general:

1. Clone this repo, or download the individual tool folder.
2. Install its dependencies (each has a `requirements.txt`).
3. For MCP servers: point your MCP client (e.g. Claude Desktop) at the server per its README, or run it directly.

```bash
git clone https://github.com/WesleyDotExe/claude-tools.git
cd claude-tools/tools/time-arithmetic
pip install -r requirements.txt
# see this tool's README for how to run / connect it
```

## License

[MIT](LICENSE) — free to use, modify, and distribute. See each tool's README for any tool-specific notes.

## Contributing

Issues and suggestions for tools that would solve a real problem are welcome.
