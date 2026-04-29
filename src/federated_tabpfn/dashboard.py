from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .project import default_paths
from .status import load_status


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_pilot_summary() -> dict[str, Any] | None:
    candidates = sorted(default_paths().results.glob("*/pilot-summary.json"), key=lambda path: path.stat().st_mtime)
    if not candidates:
        return None
    return _load_json_if_exists(candidates[-1])


def _active_direction() -> dict[str, Any] | None:
    return _load_json_if_exists(default_paths().reports / "generated" / "active-direction.json")


def _artifact_list(status: dict[str, Any]) -> list[str]:
    return list(status.get("artifacts", []))


def _dashboard_payload() -> dict[str, Any]:
    return {
        "status": load_status(),
        "pilot_summary": _latest_pilot_summary(),
        "active_direction": _active_direction(),
    }


def render_dashboard_html() -> str:
    payload = json.dumps(_dashboard_payload(), indent=2)
    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>federated-tabPFN Tracker</title>
  <style>
    :root {{
      --bg: #f6f1e8;
      --panel: rgba(255, 251, 245, 0.92);
      --ink: #1e1b18;
      --muted: #675f57;
      --accent: #0e6b5c;
      --accent-soft: #d7efe8;
      --warn: #8a5a00;
      --line: rgba(30, 27, 24, 0.12);
      --shadow: 0 18px 50px rgba(49, 38, 28, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, 'Iowan Old Style', 'Palatino Linotype', serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(14, 107, 92, 0.16), transparent 28%),
        radial-gradient(circle at top right, rgba(198, 152, 75, 0.22), transparent 26%),
        linear-gradient(180deg, #f5efe3 0%, var(--bg) 100%);
      min-height: 100vh;
    }}
    .shell {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: var(--shadow);
      padding: 20px 22px;
      backdrop-filter: blur(10px);
    }}
    h1, h2, h3, p {{ margin-top: 0; }}
    h1 {{ font-size: clamp(2rem, 4vw, 3.6rem); line-height: 0.95; letter-spacing: -0.04em; margin-bottom: 12px; }}
    h2 {{ font-size: 1rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin-bottom: 14px; }}
    h3 {{ font-size: 1.1rem; margin-bottom: 8px; }}
    .lede {{ color: var(--muted); font-size: 1rem; max-width: 46ch; }}
    .pill-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }}
    .pill {{
      border-radius: 999px;
      padding: 10px 14px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 0.92rem;
      border: 1px solid rgba(14, 107, 92, 0.12);
    }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
    .metric {{ border: 1px solid var(--line); border-radius: 18px; padding: 16px; background: rgba(255,255,255,0.55); }}
    .metric .label {{ display: block; color: var(--muted); font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px; }}
    .metric .value {{ font-size: 1.6rem; font-weight: 700; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
    .section-stack {{ display: grid; gap: 18px; }}
    .list {{ display: grid; gap: 10px; padding: 0; margin: 0; list-style: none; }}
    .list li {{ border: 1px solid var(--line); border-radius: 16px; padding: 14px; background: rgba(255,255,255,0.5); }}
    .small {{ color: var(--muted); font-size: 0.92rem; }}
    .toolbar {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }}
    button {{
      border: 0;
      border-radius: 999px;
      padding: 10px 14px;
      background: #1f3a34;
      color: #fffdf8;
      cursor: pointer;
      font: inherit;
    }}
    button.secondary {{ background: #e9dfcf; color: var(--ink); }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 0.88rem;
      line-height: 1.5;
      color: #1e2a27;
    }}
    .hidden {{ display: none; }}
    .empty {{ color: var(--muted); font-style: italic; }}
    @media (max-width: 900px) {{
      .hero, .grid, .metric-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class=\"shell\">
    <section class=\"hero\">
      <article class=\"panel\">
        <h2>Experiment Tracker</h2>
        <h1>federated<br>TabPFN</h1>
        <p class=\"lede\" id=\"objective\"></p>
        <div class=\"pill-row\" id=\"hero-pills\"></div>
      </article>
      <article class=\"panel\">
        <h2>Snapshot</h2>
        <div class=\"metric-grid\">
          <div class=\"metric\"><span class=\"label\">Overall</span><div class=\"value\" id=\"overall-status\"></div></div>
          <div class=\"metric\"><span class=\"label\">Phase</span><div class=\"value\" id=\"phase\"></div></div>
          <div class=\"metric\"><span class=\"label\">Updated</span><div class=\"value\" id=\"updated\"></div></div>
        </div>
      </article>
    </section>

    <section class=\"grid\">
      <div class=\"section-stack\">
        <article class=\"panel\">
          <h2>Direction</h2>
          <h3 id=\"direction-text\"></h3>
          <p class=\"small\" id=\"direction-meta\"></p>
        </article>
        <article class=\"panel\">
          <h2>Workers</h2>
          <ul class=\"list\" id=\"worker-list\"></ul>
        </article>
        <article class=\"panel\">
          <h2>Artifacts</h2>
          <ul class=\"list\" id=\"artifact-list\"></ul>
        </article>
      </div>
      <div class=\"section-stack\">
        <article class=\"panel\">
          <h2>Latest Summary</h2>
          <p id=\"latest-summary\"></p>
          <h3>Next Step</h3>
          <p id=\"next-step\"></p>
        </article>
        <article class=\"panel\">
          <h2>Pilot Metrics</h2>
          <ul class=\"list\" id=\"pilot-metrics\"></ul>
        </article>
        <article class=\"panel\">
          <h2>Inspect</h2>
          <div class=\"toolbar\">
            <button type=\"button\" data-target=\"status-json\">Status JSON</button>
            <button type=\"button\" data-target=\"pilot-json\">Pilot JSON</button>
            <button type=\"button\" data-target=\"direction-json\">Direction JSON</button>
            <button type=\"button\" class=\"secondary\" id=\"hide-inspector\">Hide</button>
          </div>
          <pre id=\"status-json\" class=\"hidden\"></pre>
          <pre id=\"pilot-json\" class=\"hidden\"></pre>
          <pre id=\"direction-json\" class=\"hidden\"></pre>
        </article>
      </div>
    </section>
  </div>
  <script>
    const payload = {payload};
    const status = payload.status || {{}};
    const pilot = payload.pilot_summary || null;
    const direction = payload.active_direction || status.active_direction || null;

    const setText = (id, value) => {{
      document.getElementById(id).textContent = value || 'n/a';
    }};

    setText('objective', status.objective);
    setText('overall-status', status.overall_status);
    setText('phase', status.phase);
    setText('updated', (status.updated_at || '').replace('T', '\n').replace('+00:00', ' UTC'));
    setText('latest-summary', status.latest_summary);
    setText('next-step', status.next_step);

    const pillRow = document.getElementById('hero-pills');
    [status.overall_status, status.phase, pilot ? ('pilot runtime ' + pilot.runtime_seconds + 's') : null].filter(Boolean).forEach((value) => {{
      const pill = document.createElement('span');
      pill.className = 'pill';
      pill.textContent = value;
      pillRow.appendChild(pill);
    }});

    setText('direction-text', direction ? direction.direction || direction.text : 'No active direction recorded.');
    setText('direction-meta', direction ? `${{direction.source || 'unknown source'}} | ${{direction.timestamp || 'unknown time'}}` : '');

    const workerList = document.getElementById('worker-list');
    const workers = status.workers || {{}};
    if (!Object.keys(workers).length) {{
      const item = document.createElement('li');
      item.className = 'empty';
      item.textContent = 'No worker updates recorded.';
      workerList.appendChild(item);
    }} else {{
      Object.entries(workers).forEach(([name, worker]) => {{
        const item = document.createElement('li');
        item.innerHTML = `<strong>${{name}}</strong><br><span class=\"small\">${{worker.status}}</span><p>${{worker.summary}}</p><p class=\"small\">Next: ${{worker.next_step}}</p>`;
        workerList.appendChild(item);
      }});
    }}

    const artifactList = document.getElementById('artifact-list');
    (status.artifacts || []).forEach((artifact) => {{
      const item = document.createElement('li');
      item.textContent = artifact;
      artifactList.appendChild(item);
    }});
    if (!(status.artifacts || []).length) {{
      const item = document.createElement('li');
      item.className = 'empty';
      item.textContent = 'No artifacts recorded yet.';
      artifactList.appendChild(item);
    }}

    const pilotMetrics = document.getElementById('pilot-metrics');
    if (!pilot) {{
      const item = document.createElement('li');
      item.className = 'empty';
      item.textContent = 'No pilot summary found yet.';
      pilotMetrics.appendChild(item);
    }} else {{
      [
        ['Run name', pilot.run_name],
        ['Selected baseline', pilot.selected_baseline],
        ['Datasets', (pilot.datasets || []).join(', ')],
        ['Baselines', (pilot.baselines || []).join(', ')],
        ['Clients / rounds', `${{pilot.num_clients}} / ${{pilot.num_rounds}}`],
        ['Runtime seconds', String(pilot.runtime_seconds)],
        ['Distributed accuracy', (((pilot.history || {{}}).metrics_distributed || {{}}).accuracy || []).map((row) => row[1]).join(', ') || 'n/a'],
        ['Distributed train loss', (((pilot.history || {{}}).metrics_distributed_fit || {{}}).train_loss || []).map((row) => row[1]).join(', ') || 'n/a'],
      ].forEach(([label, value]) => {{
        const item = document.createElement('li');
        item.innerHTML = `<strong>${{label}}</strong><br><span class=\"small\">${{value}}</span>`;
        pilotMetrics.appendChild(item);
      }});
    }}

    document.getElementById('status-json').textContent = JSON.stringify(status, null, 2);
    document.getElementById('pilot-json').textContent = JSON.stringify(pilot, null, 2);
    document.getElementById('direction-json').textContent = JSON.stringify(direction, null, 2);

    document.querySelectorAll('[data-target]').forEach((button) => {{
      button.addEventListener('click', () => {{
        document.querySelectorAll('pre').forEach((pre) => pre.classList.add('hidden'));
        document.getElementById(button.dataset.target).classList.remove('hidden');
      }});
    }});
    document.getElementById('hide-inspector').addEventListener('click', () => {{
      document.querySelectorAll('pre').forEach((pre) => pre.classList.add('hidden'));
    }});
  </script>
</body>
</html>
"""


def write_dashboard() -> Path:
    output_path = default_paths().reports / "generated" / "dashboard.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_dashboard_html(), encoding="utf-8")
    return output_path