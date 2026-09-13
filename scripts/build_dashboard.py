"""Generate the project dashboard: what's in tools/, and the story of each
build cycle (search -> find -> why -> build -> proof it works).

Dogfoods the collection: the tool list comes from tools/collection-index's
own collect() function rather than re-scanning tools/ here.
"""
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "collection-index"))

from index import collect  # noqa: E402

CYCLES_PATH = ROOT / "special-projects" / "cycles.json"

DASHBOARD_CSS = """
.tool-list { list-style: none; padding: 0; }
.tool-list li { margin-bottom: 1rem; padding: 0.75rem 1rem; border: 1px solid currentColor; border-radius: 6px; opacity: 0.95; }
.tool-list code { font-family: monospace; }
.cycle { border-left: 3px solid currentColor; padding-left: 1rem; margin-bottom: 2rem; }
.cycle h3 { margin-bottom: 0.25rem; }
.cycle dl { margin: 0; }
.cycle dt { font-family: system-ui, sans-serif; font-weight: bold; margin-top: 0.75rem; font-size: 0.85rem; text-transform: uppercase; opacity: 0.7; }
.cycle dd { margin: 0.25rem 0 0 0; }
.cycle ul { margin: 0.25rem 0; }
"""


def _esc(text: str) -> str:
    return html.escape(str(text))


def render_tool_list(entries: list[dict]) -> str:
    if not entries:
        return "<p>No tools in the collection yet.</p>"
    items = []
    for e in entries:
        exposed = e.get("tools_exposed")
        exposed_html = f"<br><small>exposes: {_esc(', '.join(exposed))}</small>" if exposed else ""
        items.append(
            f"<li><strong>{_esc(e['name'])}</strong> "
            f"&mdash; {_esc(e['summary'])}<br>"
            f"<code>{_esc(e['path'])}</code> (created {_esc(e['created'])})"
            f"{exposed_html}</li>"
        )
    return f'<ul class="tool-list">\n{"".join(items)}\n</ul>'


def render_cycles(cycles: list[dict]) -> str:
    if not cycles:
        return "<p>No cycles recorded yet.</p>"
    blocks = []
    for c in reversed(cycles):  # newest first
        queries = "".join(f"<li><code>{_esc(q)}</code></li>" for q in c.get("search_queries", []))
        built = c.get("built", {})
        built_html = (
            f"<code>{_esc(built.get('path', built.get('tool', '')))}</code> &mdash; {_esc(built.get('description', ''))}"
            if built else "(nothing built this cycle)"
        )
        setup_html = (
            f"<dt>Setup</dt><dd>{_esc(c['setup'])}</dd>" if c.get("setup") else ""
        )
        blocks.append(
            f'<div class="cycle">\n'
            f"<h3>{_esc(c.get('date', ''))} &mdash; {_esc(c.get('run', 'cycle'))}</h3>\n"
            "<dl>\n"
            f"{setup_html}\n"
            f"<dt>Searched</dt><dd><ul>{queries}</ul></dd>\n"
            f"<dt>Found</dt><dd>{_esc(c.get('found', ''))}</dd>\n"
            f"<dt>Why this one</dt><dd>{_esc(c.get('why', ''))}</dd>\n"
            f"<dt>Built</dt><dd>{built_html}</dd>\n"
            f"<dt>Does it work</dt><dd>{_esc(c.get('works', ''))}</dd>\n"
            "</dl>\n</div>"
        )
    return "\n".join(blocks)


def build_dashboard_body() -> str:
    entries = collect(ROOT / "tools")
    cycles = json.loads(CYCLES_PATH.read_text(encoding="utf-8")) if CYCLES_PATH.exists() else []
    return (
        f"<style>{DASHBOARD_CSS}</style>\n"
        "<h1>Tools &amp; connectors dashboard</h1>\n"
        "<p>A growing collection of MCP connectors and tools, each built to answer a real, "
        "expressed need. Every cycle below records what was searched for, what was found, "
        "why that idea was picked, what got built, and the proof that it works.</p>\n"
        "<h2>The collection</h2>\n"
        f"{render_tool_list(entries)}\n"
        "<h2>Cycle history</h2>\n"
        f"{render_cycles(cycles)}\n"
    )
