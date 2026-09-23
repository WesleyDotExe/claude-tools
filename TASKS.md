# Build task — Claude Tools

This repo is a growing, public collection of MCP servers and tools, built by scheduled Claude runs, one cycle at a time. Fully autonomous — no owner approval needed. Public and MIT-licensed, so everything is downloadable and documented for others to use.

**North star: make the owner's own agent stack more capable.** Build the tools the agents keep wishing they had, wire them in so they can actually be called, and dogfood them. A tool no agent ever calls is not a success, however correct it is. Usefulness to real callers beats novelty or cleverness.

## Each cycle: the loop

1. CHECK WHAT ALREADY EXISTS FIRST. Run the collection-index tool (dogfood it) and read the current tools/. Do NOT rebuild something that already exists. If a candidate overlaps an existing tool, pick a different problem OR extend/improve the existing tool instead of duplicating it. Name tools by capability so overlaps are obvious.

2. START FROM OBSERVED NEED, not a web search. Read special-projects/wishlist.md — capability gaps recorded by the owner and by prior agent runs (this repo's, and the owner's other scheduled agents) when they hit friction. Build for the most-repeated, real item there. Web search is now ONLY to (a) confirm no existing tool already solves it and (b) check it is a genuine gap — not the primary idea source. If the wishlist is empty or nothing on it clears the bar, prefer hardening/extending/distributing an existing tool (rule 10) over inventing a need.

3. NAME THE CALLER. Before building, name the concrete caller and workflow: which agent or session will invoke this, doing what. If you cannot name a real caller, do NOT build a new tool — harden, document, or distribute an existing one instead.

4. FEASIBILITY GATE. Can this be built as a working, keyless tool, FULLY (not a stub), in one session, and proven to work? Reject real-but-too-big problems in favour of ones you can finish well. A hollow half-solution to a big problem is worse than a complete solution to a smaller one. Build only keyless, credential-free tools (this repo is public — no secrets, and the run must be able to test it). If an idea needs an API key or account, skip it and note it in progress/notes-for-owner.md.

5. PICK the best worth-to-feasibility candidate, and record WHY it was chosen over the others.

6. BUILD & USE IT under tools/<name>/. Run it, prove it works with a committed example/proof (if it is an MCP server, actually drive it with a client — do not just scaffold it). Where an existing tool helps you build or test this one, use it — the collection should increasingly build on itself.

7. MAKE IT CALLABLE. Each tool gets its own README: what it does, how it works, how to run it — AND a copy-paste MCP registration snippet (the config block to add it to an agent's MCP servers) so the owner's agents can actually load it. Include NO personal information about the owner anywhere (this repo is public).

8. SURFACE on the dashboard. Add this cycle to special-projects/cycles.json with: the wishlist item (or source) it addressed, the named caller, what was built, why this over the others, a plain few-sentence OVERVIEW, and the proof it works. Rebuild the dashboard (scripts/build_site.py).

9. CHECK USAGE. Each cycle, check whether prior tools have actually been called since they shipped, and note it in progress/log.md. A tool still unused after several cycles is a signal to improve its discoverability/registration or retire it — not a reason to add another.

10. IF NOTHING CLEARS THE BAR, do NOT ship filler. Deepen, harden, test, distribute, or extend an existing tool this session instead. Continuation over completion.

## Mechanics

- Work on your own branch (claude/*), open a PR to main; the auto-merge workflow merges it once checks pass.
- Continuation over completion: leave the collection further along and more capable than you found it.
- End EVERY session by appending to special-projects/wishlist.md any friction you hit this run that a future tool could remove: a calculation you did by hand, a multi-step you wished were one call, a check you could not make, a gotcha you re-discovered. This is what makes the collection compounding — it learns from real agent work.
- Also update special-projects/current.md (state + next step) and progress/log.md (what you did; honest debt in progress/quality-debt.md).

## First things to create if missing

special-projects/current.md, special-projects/wishlist.md, progress/log.md, progress/quality-debt.md, progress/notes-for-owner.md.
