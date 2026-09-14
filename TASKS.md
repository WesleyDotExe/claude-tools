# Build task — Claude Tools

This repo is a growing, public collection of MCP servers and tools, each built to
solve a real problem people have. It is built by scheduled Claude runs, one cycle
at a time. Fully autonomous — no owner approval needed. Public and MIT-licensed, so
everything here is downloadable and documented for others to use.

## Each cycle: the loop

1. CHECK WHAT ALREADY EXISTS FIRST. Run the collection-index tool (dogfood it) and
   read the current tools/. Do NOT rebuild something that already exists. If a
   candidate overlaps an existing tool, pick a different problem OR extend/improve
   the existing tool instead of duplicating it. Name tools by capability so overlaps
   are obvious.

2. FIND SEVERAL candidate needs, not one. Web-search for real, expressed problems —
   especially gaps in what AI assistants / Claude can do ("I wish Claude could…",
   "is there an MCP for…", repetitive tasks people complain about). Record a SOURCE
   LINK for each: the page where the need was expressed. Link to the source and
   describe the problem in your OWN words; never copy/paste content from the page.

3. WEIGH THEM. For each: how common is it, how painful, how clearly is the need
   actually expressed by real people? Prefer widely-felt, sharply-articulated
   problems over niche or vague ones.

4. FEASIBILITY GATE. For each candidate ask honestly: can this be built as a working,
   keyless tool, FULLY (not a stub), in one session, and proven to work? Reject
   real-but-too-big problems in favour of ones you can finish well. A hollow
   half-solution to a big problem is worse than a complete solution to a smaller one.
   Build only keyless, credential-free tools. If an idea needs an API key or account,
   skip it and note it in progress/notes-for-owner.md.

5. PICK the best worth-to-feasibility candidate, and record WHY it was chosen over
   the others.

6. BUILD & USE IT under tools/<name>/. Run it, prove it works with a committed
   example/proof (if it's an MCP server, actually drive it with a client — don't
   just scaffold it). Where an existing tool helps you build or test this one, use
   it — the collection should increasingly build on itself.

7. DOCUMENT. Each tool gets its own README: what it does, how it works, how to run
   it. Include NO personal information about the owner anywhere (this repo is public).

8. SURFACE on the dashboard. Add this cycle to special-projects/cycles.json with:
   the searches, the source link(s), what was found, why this one was chosen over
   the others, a plain few-sentence OVERVIEW of what the tool does, and the proof it
   works. Rebuild the dashboard (scripts/build_site.py).

9. IF NOTHING CLEARS THE BAR, do NOT ship filler. Deepen, harden, test, or extend an
   existing tool this session instead. Continuation over completion.

## Mechanics
- Work on your own branch (claude/*), open a PR to main; the auto-merge workflow
  merges it once checks pass.
- Continuation over completion: leave the collection further along and more capable
  than you found it.
- End each session: update special-projects/current.md (state + next step) and
  progress/log.md (what you did, honest debt in progress/quality-debt.md).

## First things to create if missing
special-projects/current.md, progress/log.md, progress/quality-debt.md,
progress/notes-for-owner.md.
