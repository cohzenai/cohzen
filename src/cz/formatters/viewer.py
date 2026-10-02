import json
import tempfile
import webbrowser
from pathlib import Path
from typing import List, Optional

from cz.execution.models import Execution, Span
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


def generate_execution_viewer_html(execution: Execution, spans: List[Span]) -> str:
    """Generate an interactive HTML visualizer for an execution run with waterfall and node inspector."""
    exec_data = execution.model_dump(mode="json")
    spans_data = [s.model_dump(mode="json") for s in spans]
    exec_json = json.dumps(exec_data, default=str)
    spans_json = json.dumps(spans_data, default=str)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>cz - Execution Waterfall & Trace: {execution.id}</title>
  <style>
    :root {{
      --bg-primary: #0b0f19;
      --bg-secondary: #111827;
      --bg-card: #182234;
      --bg-card-header: #1e293b;
      --border-color: #1f2937;
      --border-light: #334155;
      --text-main: #f9fafb;
      --text-muted: #9ca3af;
      --accent: #38bdf8;
      --green: #10b981;
      --red: #ef4444;
      --yellow: #f59e0b;
      --purple: #c084fc;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 0;
      background: var(--bg-primary);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    header {{
      padding: 16px 24px;
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
    }}
    .header-left {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}
    .brand {{
      font-size: 18px;
      font-weight: 800;
      color: var(--accent);
      letter-spacing: -0.5px;
    }}
    .exec-title {{
      font-size: 16px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .badge {{
      border-radius: 9999px;
      padding: 3px 10px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
    }}
    .badge-completed {{ background: rgba(16, 185, 129, 0.15); color: var(--green); border: 1px solid rgba(16, 185, 129, 0.3); }}
    .badge-failed {{ background: rgba(239, 68, 68, 0.15); color: var(--red); border: 1px solid rgba(239, 68, 68, 0.3); }}
    .badge-running {{ background: rgba(245, 158, 11, 0.15); color: var(--yellow); border: 1px solid rgba(245, 158, 11, 0.3); }}
    .badge-node {{ background: rgba(56, 189, 248, 0.15); color: var(--accent); border: 1px solid rgba(56, 189, 248, 0.3); }}
    .badge-llm {{ background: rgba(192, 132, 252, 0.15); color: var(--purple); border: 1px solid rgba(192, 132, 252, 0.3); }}
    .badge-tool {{ background: rgba(245, 158, 11, 0.15); color: var(--yellow); border: 1px solid rgba(245, 158, 11, 0.3); }}

    .header-stats {{
      display: flex;
      align-items: center;
      gap: 16px;
      font-size: 13px;
      color: var(--text-muted);
    }}
    .stat-val {{ color: var(--text-main); font-weight: 600; }}

    /* Layout */
    .app-body {{
      display: flex;
      flex: 1;
      overflow: hidden;
    }}
    .main-panel {{
      flex: 1;
      display: flex;
      flex-direction: column;
      border-right: 1px solid var(--border-color);
      overflow: hidden;
    }}
    .tabs-bar {{
      display: flex;
      background: #0d131f;
      border-bottom: 1px solid var(--border-color);
      padding: 0 16px;
      flex-shrink: 0;
    }}
    .tab-btn {{
      padding: 12px 18px;
      background: none;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      border-bottom: 2px solid transparent;
      transition: all 0.15s;
    }}
    .tab-btn.active {{
      color: var(--accent);
      border-bottom-color: var(--accent);
    }}
    .tab-content {{
      flex: 1;
      overflow-y: auto;
      padding: 20px;
    }}

    /* Waterfall */
    .timeline-scale {{
      display: flex;
      justify-content: space-between;
      color: var(--text-muted);
      font-size: 11px;
      padding: 8px 12px 8px 300px;
      border-bottom: 1px solid var(--border-light);
      margin-bottom: 8px;
    }}
    .waterfall-row {{
      display: flex;
      align-items: center;
      padding: 8px 12px;
      border-radius: 6px;
      cursor: pointer;
      transition: background 0.15s;
      border: 1px solid transparent;
      margin-bottom: 4px;
    }}
    .waterfall-row:hover {{
      background: rgba(255, 255, 255, 0.04);
    }}
    .waterfall-row.selected {{
      background: rgba(56, 189, 248, 0.08);
      border-color: rgba(56, 189, 248, 0.3);
    }}
    .span-info {{
      width: 290px;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      gap: 8px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .span-name {{
      font-weight: 600;
      font-size: 13px;
    }}
    .span-meta {{
      font-size: 11px;
      color: var(--text-muted);
      margin-left: auto;
      padding-right: 12px;
    }}
    .timeline-track {{
      flex: 1;
      height: 22px;
      position: relative;
      background: rgba(255, 255, 255, 0.02);
      border-radius: 4px;
      overflow: hidden;
    }}
    .timeline-bar {{
      position: absolute;
      top: 2px;
      bottom: 2px;
      border-radius: 3px;
      min-width: 4px;
      transition: width 0.2s;
    }}
    .bar-node {{ background: var(--accent); }}
    .bar-llm {{ background: var(--purple); }}
    .bar-tool {{ background: var(--yellow); }}
    .bar-graph {{ background: #3b82f6; }}
    .bar-failed {{ background: var(--red) !important; }}

    /* Inspector Drawer */
    .inspector-panel {{
      width: 460px;
      background: var(--bg-secondary);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      flex-shrink: 0;
    }}
    .inspector-header {{
      padding: 16px 20px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--bg-card-header);
    }}
    .inspector-title {{
      font-size: 15px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .inspector-content {{
      flex: 1;
      overflow-y: auto;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .section-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-light);
      border-radius: 8px;
      padding: 14px;
    }}
    .section-title {{
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--text-muted);
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    pre.code-box {{
      margin: 0;
      padding: 10px;
      background: #090d16;
      border-radius: 6px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      color: #e2e8f0;
      overflow-x: auto;
      max-height: 220px;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .copy-btn {{
      background: #334155;
      color: #f1f5f9;
      border: none;
      border-radius: 4px;
      padding: 3px 8px;
      font-size: 11px;
      cursor: pointer;
    }}
    .copy-btn:hover {{ background: #475569; }}
    .debug-banner {{
      background: rgba(56, 189, 248, 0.1);
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-radius: 8px;
      padding: 12px;
      font-size: 12px;
    }}
    .debug-cmd {{
      background: #000;
      color: #38bdf8;
      padding: 8px 10px;
      border-radius: 4px;
      font-family: monospace;
      margin-top: 6px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-left">
      <div class="brand">cz</div>
      <div class="exec-title">
        <span>Execution: <b>{execution.id}</b></span>
        <span class="badge badge-{execution.status}">{execution.status}</span>
      </div>
    </div>
    <div class="header-stats">
      <span>Graph: <b class="stat-val">{execution.graph_id}</b></span>
      <span>Duration: <b class="stat-val">{execution.duration_ms or 0:.0f}ms</b></span>
      <span>Spans: <b class="stat-val">{len(spans)}</b></span>
    </div>
  </header>

  <div class="app-body">
    <div class="main-panel">
      <div class="tabs-bar">
        <button class="tab-btn active" onclick="switchView('waterfall')">🌊 Waterfall Timeline</button>
        <button class="tab-btn" onclick="switchView('tree')">🌳 Execution Tree</button>
      </div>

      <div id="waterfallView" class="tab-content">
        <div id="timeScale" class="timeline-scale"></div>
        <div id="waterfallRows"></div>
      </div>

      <div id="treeView" class="tab-content" style="display: none;">
        <div id="treeContent"></div>
      </div>
    </div>

    <div class="inspector-panel">
      <div class="inspector-header">
        <div class="inspector-title" id="inspTitle">Select a span to inspect</div>
        <span id="inspBadge" class="badge badge-node" style="display: none;">NODE</span>
      </div>
      <div class="inspector-content" id="inspBody">
        <p style="color: var(--text-muted); font-size: 13px;">Click on any node, LLM call, or tool in the waterfall to view captured inputs, outputs, prompts, context, and run isolated node debugging.</p>
      </div>
    </div>
  </div>

  <script>
    const execution = {exec_json};
    const spans = {spans_json};
    let selectedSpan = null;

    // Determine time range
    const baseTime = spans.length > 0 ? Math.min(...spans.map(s => new Date(s.started_at).getTime())) : 0;
    const maxTime = spans.length > 0 ? Math.max(...spans.map(s => new Date(s.ended_at || s.started_at).getTime())) : 1000;
    const totalMs = Math.max(1, maxTime - baseTime);

    // Render Time Scale
    document.getElementById("timeScale").innerHTML = `
      <span>0ms</span>
      <span>${{Math.round(totalMs * 0.25)}}ms</span>
      <span>${{Math.round(totalMs * 0.50)}}ms</span>
      <span>${{Math.round(totalMs * 0.75)}}ms</span>
      <span>${{Math.round(totalMs)}}ms</span>
    `;

    function renderWaterfall() {{
      const container = document.getElementById("waterfallRows");
      container.innerHTML = "";

      spans.forEach((span, idx) => {{
        const startOffset = Math.max(0, new Date(span.started_at).getTime() - baseTime);
        const dur = span.duration_ms || 1;
        const leftPercent = Math.min(100, Math.max(0, (startOffset / totalMs) * 100));
        const widthPercent = Math.min(100 - leftPercent, Math.max(1, (dur / totalMs) * 100));

        const row = document.createElement("div");
        row.className = "waterfall-row";
        row.id = "span-row-" + span.id;
        row.onclick = () => selectSpan(span);

        let kindClass = "bar-" + span.kind;
        if (span.status === "failed") kindClass = "bar-failed";

        row.innerHTML = `
          <div class="span-info">
            <span class="badge badge-${{span.kind}}">${{span.kind.toUpperCase()}}</span>
            <span class="span-name">${{span.name}}</span>
            <span class="span-meta">+${{Math.round(startOffset)}}ms (${{Math.round(dur)}}ms)</span>
          </div>
          <div class="timeline-track">
            <div class="timeline-bar ${{kindClass}}" style="left: ${{leftPercent}}%; width: ${{widthPercent}}%;"></div>
          </div>
        `;
        container.appendChild(row);
      }});

      if (spans.length > 0) {{
        selectSpan(spans[0]);
      }}
    }}

    function selectSpan(span) {{
      selectedSpan = span;
      document.querySelectorAll(".waterfall-row").forEach(r => r.classList.remove("selected"));
      const activeRow = document.getElementById("span-row-" + span.id);
      if (activeRow) activeRow.classList.add("selected");

      document.getElementById("inspTitle").textContent = span.name;
      const badge = document.getElementById("inspBadge");
      badge.textContent = span.kind.toUpperCase();
      badge.className = "badge badge-" + span.kind;
      badge.style.display = "inline-block";

      const body = document.getElementById("inspBody");
      let html = "";

      if (span.reason) {{
        html += `
          <div class="section-card" style="border-color: rgba(56, 189, 248, 0.4);">
            <div class="section-title" style="color: var(--accent);">🧠 Rationale / Why</div>
            <div style="font-size: 13px; color: #bae6fd; font-style: italic;">"${{escapeHtml(span.reason)}}"</div>
          </div>
        `;
      }}

      if (span.error) {{
        html += `
          <div class="section-card" style="border-color: rgba(239, 68, 68, 0.4);">
            <div class="section-title" style="color: var(--red);">✗ Error</div>
            <pre class="code-box" style="color: #fca5a5;">${{escapeHtml(span.error)}}</pre>
          </div>
        `;
      }}

      // Isolated Node Debugger Callout (for nodes)
      if (span.kind === "node") {{
        const cmd = "cz node run " + span.name + " --from-run " + execution.id;
        html += `
          <div class="debug-banner">
            <div style="font-weight: 700; color: var(--accent); margin-bottom: 4px;">⚡ Debug This Node in Isolation</div>
            <div>Test and re-run this exact node with its captured input without compiling the whole graph:</div>
            <div class="debug-cmd">
              <span>${{cmd}}</span>
              <button class="copy-btn" onclick="navigator.clipboard.writeText('${{cmd}}'); this.textContent = 'Copied!';">Copy</button>
            </div>
          </div>
        `;
      }}

      // Input State / Arguments
      html += `
        <div class="section-card">
          <div class="section-title">
            <span>📥 Input Payload</span>
            <button class="copy-btn" onclick="navigator.clipboard.writeText(JSON.stringify(selectedSpan.input, null, 2)); this.textContent = 'Copied!';">Copy</button>
          </div>
          <pre class="code-box">${{escapeHtml(JSON.stringify(span.input, null, 2) || "None")}}</pre>
        </div>
      `;

      // Output State / Response
      html += `
        <div class="section-card">
          <div class="section-title">
            <span>📤 Output Result</span>
            <button class="copy-btn" onclick="navigator.clipboard.writeText(JSON.stringify(selectedSpan.output, null, 2)); this.textContent = 'Copied!';">Copy</button>
          </div>
          <pre class="code-box">${{escapeHtml(JSON.stringify(span.output, null, 2) || "None")}}</pre>
        </div>
      `;

      // Extra metadata / tokens
      if (span.metadata && Object.keys(span.metadata).length > 0) {{
        html += `
          <div class="section-card">
            <div class="section-title">Metadata & Context</div>
            <pre class="code-box">${{escapeHtml(JSON.stringify(span.metadata, null, 2))}}</pre>
          </div>
        `;
      }}

      body.innerHTML = html;
    }}

    function switchView(view) {{
      const wf = document.getElementById("waterfallView");
      const tr = document.getElementById("treeView");
      const btns = document.querySelectorAll(".tab-btn");
      if (view === "waterfall") {{
        wf.style.display = "block";
        tr.style.display = "none";
        btns[0].classList.add("active");
        btns[1].classList.remove("active");
      }} else {{
        wf.style.display = "none";
        tr.style.display = "block";
        btns[1].classList.add("active");
        btns[0].classList.remove("active");
        renderTree();
      }}
    }}

    function renderTree() {{
      const container = document.getElementById("treeContent");
      container.innerHTML = "<div style='font-size: 13px; line-height: 2;'><b>Execution Hierarchy:</b></div>";
      spans.forEach(s => {{
        container.innerHTML += `
          <div style="padding: 6px 12px; margin: 4px 0; background: var(--bg-card); border-radius: 6px; cursor: pointer;" onclick="selectSpan(spans.find(x => x.id === '${{s.id}}'))">
            <span class="badge badge-${{s.kind}}">${{s.kind.toUpperCase()}}</span>
            <b>${{s.name}}</b> <span style="color: var(--text-muted);">(${{Math.round(s.duration_ms || 0)}}ms)</span>
          </div>
        `;
      }});
    }}

    function escapeHtml(str) {{
      if (typeof str !== "string") str = JSON.stringify(str);
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }}

    renderWaterfall();
  </script>
</body>
</html>
"""
    return html


def open_execution_in_browser(execution: Execution, spans: List[Span]) -> Path:
    """Generate execution viewer HTML and launch in the default web browser."""
    html_content = generate_execution_viewer_html(execution, spans)
    temp_dir = Path(tempfile.gettempdir())
    viewer_file = temp_dir / f"cz_run_{execution.id}.html"
    viewer_file.write_text(html_content, encoding="utf-8")
    webbrowser.open(f"file://{viewer_file.resolve()}")
    return viewer_file

