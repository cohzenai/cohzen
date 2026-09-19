"""Interactive HTML & browser visualizer for LangGraph architectures."""

from __future__ import annotations

import tempfile
import webbrowser
from pathlib import Path

from cz.formatters.mermaid import generate_graph_mermaid
from cz.scanner.models import ScanResult


def generate_viewer_html(result: ScanResult) -> str:
    """Generates a standalone, dark-themed HTML page embedding Mermaid.js with separate cards per graph."""
    graph_cards: list[str] = []

    if result.graphs:
        for idx, g in enumerate(result.graphs, start=1):
            g_markup = generate_graph_mermaid(g, scan_result=result)
            rel_file = Path(g.file_path).name

            badges = [f'<span class="badge">{rel_file}:{g.line_number}</span>']
            if g.state_schema:
                badges.append(f'<span class="badge badge-blue">Schema: {g.state_schema}</span>')
            if g.is_compiled and g.compile_info and g.compile_info.checkpointer:
                badges.append('<span class="badge badge-purple">💾 Checkpointer</span>')

            badges_html = "".join(badges)

            graph_cards.append(f"""
    <div class="graph-card">
      <div class="graph-card-header">
        <div class="graph-card-title">
          <span>Graph #{idx}: <b>{g.graph_var}</b> <span class="muted">({g.graph_class})</span></span>
        </div>
        <div class="card-badges">
          {badges_html}
        </div>
      </div>
      <div class="mermaid-box">
        <pre class="mermaid">
{g_markup}
        </pre>
      </div>
    </div>""")
    else:
        graph_cards.append("""
    <div class="graph-card empty">
      <p style="text-align: center; color: var(--text-muted); padding: 40px;">
        No LangGraph workflows detected in the scanned path.
      </p>
    </div>""")

    cards_html = "\n".join(graph_cards)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>cz - LangGraph Architecture Visualizer</title>
  <style>
    :root {{
      --bg-primary: #0b0f19;
      --bg-secondary: #111827;
      --bg-card-header: #1e293b;
      --border-color: #1f2937;
      --border-light: #374151;
      --text-main: #f9fafb;
      --text-muted: #9ca3af;
      --accent: #38bdf8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 24px;
      background: var(--bg-primary);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    .header {{
      max-width: 1200px;
      margin: 0 auto 28px auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--border-color);
    }}
    .title {{
      font-size: 22px;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .summary-badges {{
      display: flex;
      gap: 10px;
    }}
    .badge {{
      background: #1e293b;
      border: 1px solid #334155;
      color: var(--accent);
      border-radius: 9999px;
      padding: 5px 14px;
      font-size: 13px;
      font-weight: 600;
    }}
    .badge-blue {{
      color: #60a5fa !important;
      border-color: #2563eb !important;
    }}
    .badge-purple {{
      background: #3b0764 !important;
      color: #d8b4fe !important;
      border-color: #7e22ce !important;
    }}
    .muted {{
      color: var(--text-muted);
      font-weight: normal;
    }}
    .graphs-container {{
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 32px;
    }}
    .graph-card {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
    }}
    .graph-card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 24px;
      background: var(--bg-card-header);
      border-bottom: 1px solid var(--border-color);
    }}
    .graph-card-title {{
      font-size: 16px;
      font-weight: 600;
    }}
    .card-badges {{
      display: flex;
      gap: 8px;
    }}
    .mermaid-box {{
      padding: 32px;
      display: flex;
      justify-content: center;
      overflow-x: auto;
      background: #0f172a;
    }}
    .footer {{
      max-width: 1200px;
      margin: 40px auto 16px auto;
      text-align: center;
      color: var(--text-muted);
      font-size: 13px;
    }}
  </style>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'dark',
      flowchart: {{
        curve: 'basis',
        useMaxWidth: false
      }}
    }});
  </script>
</head>
<body>
  <div class="header">
    <div class="title">
      <span>🌐 cz LangGraph Architecture Visualizer</span>
    </div>
    <div class="summary-badges">
      <span class="badge">Graphs: {result.total_graphs}</span>
      <span class="badge">Nodes: {result.total_nodes}</span>
      <span class="badge">Edges: {result.total_edges}</span>
    </div>
  </div>

  <div class="graphs-container">
{cards_html}
  </div>

  <div class="footer">
    Generated by <b>cz</b> &bull; Static AST AI / Agentic Architecture Scanner
  </div>
</body>
</html>
"""
    return html


def open_in_browser(result: ScanResult) -> Path:
    """Generates the viewer HTML to a temporary file and opens it in the default web browser."""
    html_content = generate_viewer_html(result)
    temp_dir = Path(tempfile.gettempdir())
    viewer_file = temp_dir / "cz_graph_viewer.html"
    viewer_file.write_text(html_content, encoding="utf-8")
    webbrowser.open(f"file://{viewer_file.resolve()}")
    return viewer_file
