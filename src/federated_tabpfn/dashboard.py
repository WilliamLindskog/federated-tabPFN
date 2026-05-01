from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from .dataset_pilot import SUPPORTED_DATASET_BACKED_BASELINES
from .execution_plan import build_phase_plan
from .project import default_paths
from .results_summary import recent_result_rows, results_summary_payload, write_results_summary
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


def _load_config() -> dict[str, Any]:
    return yaml.safe_load((default_paths().configs / "pilot.yaml").read_text(encoding="utf-8"))


def _progress_payload() -> dict[str, Any]:
    config = _load_config()
    plan = build_phase_plan(config, "overall", supported_baselines=set(SUPPORTED_DATASET_BACKED_BASELINES))
    all_specs = plan.runnable + plan.skipped
    total = len(all_specs)
    completed = len(plan.skipped)
    remaining = len(plan.runnable)

    engineering_total = sum(1 for spec in all_specs if spec.dataset == "adult_engineering_slice")
    engineering_completed = sum(1 for spec in plan.skipped if spec.dataset == "adult_engineering_slice")
    paper_total = total - engineering_total
    paper_completed = completed - engineering_completed

    baseline_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"completed": 0, "total": 0})
    split_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"completed": 0, "total": 0})
    for spec in all_specs:
        baseline_counts[spec.baseline]["total"] += 1
        split_counts[spec.split_regime]["total"] += 1
    for spec in plan.skipped:
        baseline_counts[spec.baseline]["completed"] += 1
        split_counts[spec.split_regime]["completed"] += 1

    recent_rows = recent_result_rows(limit=12)
    accuracy_points = [
        {"label": row["run_name"], "value": row["accuracy"], "baseline": row["baseline"]}
        for row in reversed(recent_rows)
        if row.get("accuracy") is not None
    ]
    runtime_points = [
        {"label": row["run_name"], "value": row["runtime_seconds"], "baseline": row["baseline"]}
        for row in reversed(recent_rows)
        if row.get("runtime_seconds") is not None
    ]

    return {
        "overall": {"completed": completed, "total": total, "remaining": remaining},
        "engineering": {"completed": engineering_completed, "total": engineering_total},
        "paper": {"completed": paper_completed, "total": paper_total},
        "baseline_counts": baseline_counts,
        "split_counts": split_counts,
        "accuracy_points": accuracy_points,
        "runtime_points": runtime_points,
    }


def _dashboard_payload() -> dict[str, Any]:
    return {
        "status": load_status(),
        "pilot_summary": _latest_pilot_summary(),
        "active_direction": _active_direction(),
        "results_summary": results_summary_payload(limit=20),
        "progress": _progress_payload(),
    }


def render_dashboard_html() -> str:
    payload = json.dumps(_dashboard_payload(), indent=2)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="15">
  <title>federated-tabPFN Tracker</title>
  <style>
    :root {{
      --bg: #f6f1e8;
      --panel: rgba(255, 251, 245, 0.94);
      --ink: #1e1b18;
      --muted: #675f57;
      --accent: #0e6b5c;
      --accent-soft: #d7efe8;
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
      max-width: 1220px;
      margin: 0 auto;
      padding: 24px 16px 40px;
    }}
    .hero, .grid, .metric-grid, .mini-grid {{
      display: grid;
      gap: 16px;
    }}
    .hero {{ grid-template-columns: 1.35fr 1fr; margin-bottom: 16px; }}
    .grid {{ grid-template-columns: 1.1fr 1fr; }}
    .metric-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .mini-grid {{ grid-template-columns: 1fr 1fr; }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: var(--shadow);
      padding: 18px 20px;
      backdrop-filter: blur(10px);
    }}
    h1, h2, h3, p {{ margin-top: 0; }}
    h1 {{ font-size: clamp(2rem, 4vw, 3.4rem); line-height: 0.95; letter-spacing: -0.04em; margin-bottom: 10px; }}
    h2 {{ font-size: 0.98rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; }}
    h3 {{ font-size: 1.05rem; margin-bottom: 8px; }}
    .lede, .small {{ color: var(--muted); }}
    .lede {{ font-size: 1rem; max-width: 48ch; }}
    .pill-row, .chart-legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .pill, button {{
      border-radius: 999px;
      padding: 10px 14px;
      font: inherit;
    }}
    .pill {{
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 0.9rem;
      border: 1px solid rgba(14, 107, 92, 0.12);
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,0.55);
    }}
    .metric .label {{
      display: block;
      color: var(--muted);
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
    }}
    .metric .value {{ font-size: 1.5rem; font-weight: 700; }}
    .metric .subvalue {{ color: var(--muted); font-size: 0.88rem; margin-top: 4px; }}
    .progress-rail {{
      width: 100%;
      height: 12px;
      border-radius: 999px;
      background: rgba(30, 27, 24, 0.08);
      overflow: hidden;
      margin-top: 8px;
    }}
    .progress-fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--accent), #34a58f);
      border-radius: 999px;
    }}
    .kv {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      color: var(--muted);
      font-size: 0.9rem;
      margin-top: 8px;
    }}
    .list {{
      display: grid;
      gap: 10px;
      padding: 0;
      margin: 0;
      list-style: none;
    }}
    .list li {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px;
      background: rgba(255,255,255,0.5);
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    th, td {{ text-align: left; padding: 9px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ color: var(--muted); font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.08em; }}
    .chart-card {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,0.55);
      margin-bottom: 14px;
    }}
    .chart-card svg {{ width: 100%; height: 220px; display: block; }}
    .legend-pill {{ display: inline-flex; align-items: center; gap: 6px; color: var(--muted); font-size: 0.84rem; }}
    .legend-dot {{ width: 10px; height: 10px; border-radius: 999px; display: inline-block; }}
    .toolbar {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }}
    button {{
      border: 0;
      background: #1f3a34;
      color: #fffdf8;
      cursor: pointer;
    }}
    button.secondary {{ background: #e9dfcf; color: var(--ink); }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 0.85rem;
      line-height: 1.5;
      color: #1e2a27;
    }}
    .hidden {{ display: none; }}
    .empty {{ color: var(--muted); font-style: italic; }}
    @media (max-width: 900px) {{
      .hero, .grid, .metric-grid, .mini-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <article class="panel">
        <h2>Experiment Tracker</h2>
        <h1>federated<br>TabPFN</h1>
        <p class="lede" id="objective"></p>
        <div class="pill-row" id="hero-pills"></div>
        <div class="chart-card" style="margin-top:14px;">
          <h3>Recent Runs</h3>
          <table>
            <thead>
              <tr>
                <th>Dataset</th>
                <th>Baseline</th>
                <th>Split</th>
                <th>Accuracy</th>
                <th>Runtime</th>
              </tr>
            </thead>
            <tbody id="recent-runs"></tbody>
          </table>
        </div>
        <div class="chart-card">
          <h3>Paper Track</h3>
          <p class="small" id="paper-track-meta"></p>
          <ul class="list" id="paper-track-list"></ul>
        </div>
      </article>
      <article class="panel">
        <h2>Snapshot</h2>
        <div class="metric-grid">
          <div class="metric"><span class="label">Overall</span><div class="value" id="overall-status"></div></div>
          <div class="metric"><span class="label">Phase</span><div class="value" id="phase"></div></div>
          <div class="metric"><span class="label">Updated</span><div class="value" id="updated"></div></div>
        </div>
        <div class="metric-grid" style="margin-top:14px;">
          <div class="metric">
            <span class="label">Progress</span>
            <div class="value" id="overall-progress-value"></div>
            <div class="subvalue" id="overall-progress-sub"></div>
            <div class="progress-rail"><div class="progress-fill" id="overall-progress-bar"></div></div>
          </div>
          <div class="metric">
            <span class="label">Engineering</span>
            <div class="value" id="engineering-progress-value"></div>
            <div class="subvalue" id="engineering-progress-sub"></div>
            <div class="progress-rail"><div class="progress-fill" id="engineering-progress-bar"></div></div>
          </div>
          <div class="metric">
            <span class="label">Paper Track</span>
            <div class="value" id="paper-progress-value"></div>
            <div class="subvalue" id="paper-progress-sub"></div>
            <div class="progress-rail"><div class="progress-fill" id="paper-progress-bar"></div></div>
          </div>
        </div>
      </article>
    </section>

    <section class="grid">
      <div class="section-stack">
        <article class="panel">
          <h2>Progress by Baseline / Split</h2>
          <div class="mini-grid">
            <div><h3>Baselines</h3><ul class="list" id="baseline-progress"></ul></div>
            <div><h3>Splits</h3><ul class="list" id="split-progress"></ul></div>
          </div>
        </article>
        <article class="panel">
          <h2>Direction</h2>
          <h3 id="direction-text"></h3>
          <p class="small" id="direction-meta"></p>
        </article>
        <article class="panel">
          <h2>Workers</h2>
          <ul class="list" id="worker-list"></ul>
        </article>
      </div>
      <div class="section-stack">
        <article class="panel">
          <h2>Charts</h2>
          <div class="chart-card">
            <h3>Recent Accuracy</h3>
            <svg id="accuracy-chart" viewBox="0 0 520 220" preserveAspectRatio="none"></svg>
          </div>
          <div class="chart-card">
            <h3>Recent Runtime</h3>
            <svg id="runtime-chart" viewBox="0 0 520 220" preserveAspectRatio="none"></svg>
          </div>
          <div class="chart-legend" id="chart-legend"></div>
        </article>
        <article class="panel">
          <h2>Latest Summary</h2>
          <p id="latest-summary"></p>
          <h3>Next Step</h3>
          <p id="next-step"></p>
        </article>
        <article class="panel">
          <h2>Artifacts</h2>
          <ul class="list" id="artifact-list"></ul>
        </article>
        <article class="panel">
          <h2>Inspect</h2>
          <div class="toolbar">
            <button type="button" data-target="status-json">Status JSON</button>
            <button type="button" data-target="progress-json">Progress JSON</button>
            <button type="button" data-target="results-json">Results JSON</button>
            <button type="button" class="secondary" id="hide-inspector">Hide</button>
          </div>
          <pre id="status-json" class="hidden"></pre>
          <pre id="progress-json" class="hidden"></pre>
          <pre id="results-json" class="hidden"></pre>
        </article>
      </div>
    </section>
  </div>
  <script>
    const payload = {payload};
    const status = payload.status || {{}};
    const direction = payload.active_direction || status.active_direction || null;
    const resultsSummary = payload.results_summary || {{}};
    const progress = payload.progress || {{}};
    const palette = {{
      logistic_regression: '#7f56d9',
      random_forest: '#0e6b5c',
      xgboost: '#c47f00',
      tabpfn: '#b5487a',
    }};

    const setText = (id, value) => {{
      document.getElementById(id).textContent = value || 'n/a';
    }};
    const pct = (completed, total) => total ? Math.round((completed / total) * 100) : 0;

    setText('objective', status.objective);
    setText('overall-status', status.overall_status);
    setText('phase', status.phase);
    setText('updated', (status.updated_at || '').replace('T', ' ').replace('+00:00', ' UTC'));
    setText('latest-summary', status.latest_summary);
    setText('next-step', status.next_step);

    const pillRow = document.getElementById('hero-pills');
    [
      status.overall_status,
      status.phase,
      progress.overall ? `${{progress.overall.completed}}/${{progress.overall.total}} complete` : null,
      progress.paper ? `${{progress.paper.completed}} paper-track done` : null,
    ].filter(Boolean).forEach((value) => {{
      const pill = document.createElement('span');
      pill.className = 'pill';
      pill.textContent = value;
      pillRow.appendChild(pill);
    }});

    setText('direction-text', direction ? direction.direction || direction.text : 'No active direction recorded.');
    setText('direction-meta', direction ? `${{direction.source || 'unknown source'}} | ${{direction.timestamp || 'unknown time'}}` : '');

    [
      ['overall', 'overall-progress'],
      ['engineering', 'engineering-progress'],
      ['paper', 'paper-progress'],
    ].forEach(([key, prefix]) => {{
      const block = progress[key] || {{ completed: 0, total: 0, remaining: 0 }};
      const percent = pct(block.completed || 0, block.total || 0);
      setText(`${{prefix}}-value`, `${{block.completed || 0}} / ${{block.total || 0}}`);
      setText(`${{prefix}}-sub`, `${{percent}}% complete`);
      document.getElementById(`${{prefix}}-bar`).style.width = `${{percent}}%`;
    }});

    const renderProgressList = (targetId, counts) => {{
      const target = document.getElementById(targetId);
      target.innerHTML = '';
      Object.entries(counts || {{}}).sort().forEach(([name, info]) => {{
        const percent = pct(info.completed || 0, info.total || 0);
        const item = document.createElement('li');
        item.innerHTML = `
          <strong>${{name}}</strong>
          <div class="kv"><span>${{info.completed}} / ${{info.total}}</span><span>${{percent}}%</span></div>
          <div class="progress-rail"><div class="progress-fill" style="width:${{percent}}%"></div></div>
        `;
        target.appendChild(item);
      }});
      if (!target.children.length) {{
        const item = document.createElement('li');
        item.className = 'empty';
        item.textContent = 'No progress yet.';
        target.appendChild(item);
      }}
    }};
    renderProgressList('baseline-progress', progress.baseline_counts);
    renderProgressList('split-progress', progress.split_counts);

    const workerList = document.getElementById('worker-list');
    Object.entries(status.workers || {{}}).forEach(([name, worker]) => {{
      const item = document.createElement('li');
      item.innerHTML = `<strong>${{name}}</strong><br><span class="small">${{worker.status}}</span><p>${{worker.summary}}</p><p class="small">Next: ${{worker.next_step}}</p>`;
      workerList.appendChild(item);
    }});
    if (!workerList.children.length) {{
      const item = document.createElement('li');
      item.className = 'empty';
      item.textContent = 'No worker updates recorded.';
      workerList.appendChild(item);
    }}

    const artifactList = document.getElementById('artifact-list');
    (status.artifacts || []).slice(-12).reverse().forEach((artifact) => {{
      const item = document.createElement('li');
      item.textContent = artifact;
      artifactList.appendChild(item);
    }});
    if (!artifactList.children.length) {{
      const item = document.createElement('li');
      item.className = 'empty';
      item.textContent = 'No artifacts recorded yet.';
      artifactList.appendChild(item);
    }}

    const recentRunsBody = document.getElementById('recent-runs');
    const recentRuns = resultsSummary.recent_runs || [];
    recentRuns.slice(0, 10).forEach((run) => {{
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${{run.dataset}}</td>
        <td>${{run.baseline}}</td>
        <td>${{run.split_regime}}</td>
        <td>${{run.accuracy == null ? 'n/a' : run.accuracy.toFixed(3)}}</td>
        <td>${{run.runtime_seconds == null ? 'n/a' : run.runtime_seconds.toFixed(2) + 's'}}</td>
      `;
      recentRunsBody.appendChild(row);
    }});
    if (!recentRunsBody.children.length) {{
      const row = document.createElement('tr');
      row.innerHTML = '<td colspan="5" class="empty">No dataset-backed results found.</td>';
      recentRunsBody.appendChild(row);
    }}

    const paperTrack = (resultsSummary.study_registry || {{}}).paper_track || null;
    setText(
      'paper-track-meta',
      paperTrack ? `${{paperTrack.dataset_count}} datasets from the TabPFN paper-aligned numerical CC18 slice` : ''
    );
    const paperTrackList = document.getElementById('paper-track-list');
    if (paperTrack && paperTrack.datasets) {{
      paperTrack.datasets.slice(0, 8).forEach((dataset) => {{
        const item = document.createElement('li');
        item.innerHTML = `<strong>${{dataset.data_id}} | ${{dataset.name}}</strong><br><span class="small">n=${{dataset.n_instances}}, p=${{dataset.n_features}}, classes=${{dataset.n_classes}}</span>`;
        paperTrackList.appendChild(item);
      }});
    }}

    const buildLineChart = (svgId, points, formatter) => {{
      const svg = document.getElementById(svgId);
      svg.innerHTML = '';
      if (!points.length) {{
        svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#675f57">No data yet</text>';
        return;
      }}
      const width = 520, height = 220, left = 34, right = 18, top = 16, bottom = 28;
      const values = points.map((point) => point.value);
      const minValue = Math.min(...values);
      const maxValue = Math.max(...values);
      const span = Math.max(maxValue - minValue, 0.001);
      const xAt = (index) => left + ((width - left - right) * (points.length === 1 ? 0.5 : index / (points.length - 1)));
      const yAt = (value) => top + ((height - top - bottom) * (1 - ((value - minValue) / span)));

      const axis = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      axis.setAttribute('x1', String(left));
      axis.setAttribute('y1', String(height - bottom));
      axis.setAttribute('x2', String(width - right));
      axis.setAttribute('y2', String(height - bottom));
      axis.setAttribute('stroke', 'rgba(30,27,24,0.2)');
      svg.appendChild(axis);

      const yAxis = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      yAxis.setAttribute('x1', String(left));
      yAxis.setAttribute('y1', String(top));
      yAxis.setAttribute('x2', String(left));
      yAxis.setAttribute('y2', String(height - bottom));
      yAxis.setAttribute('stroke', 'rgba(30,27,24,0.2)');
      svg.appendChild(yAxis);

      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('fill', 'none');
      path.setAttribute('stroke', '#1f3a34');
      path.setAttribute('stroke-width', '2.4');
      path.setAttribute('d', points.map((point, index) => `${{index ? 'L' : 'M'}} ${{xAt(index)}} ${{yAt(point.value)}}`).join(' '));
      svg.appendChild(path);

      points.forEach((point, index) => {{
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', String(xAt(index)));
        circle.setAttribute('cy', String(yAt(point.value)));
        circle.setAttribute('r', '4.2');
        circle.setAttribute('fill', palette[point.baseline] || '#1f3a34');
        svg.appendChild(circle);
      }});

      const minLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      minLabel.setAttribute('x', '4');
      minLabel.setAttribute('y', String(height - bottom));
      minLabel.setAttribute('fill', '#675f57');
      minLabel.setAttribute('font-size', '11');
      minLabel.textContent = formatter(minValue);
      svg.appendChild(minLabel);

      const maxLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      maxLabel.setAttribute('x', '4');
      maxLabel.setAttribute('y', String(top + 4));
      maxLabel.setAttribute('fill', '#675f57');
      maxLabel.setAttribute('font-size', '11');
      maxLabel.textContent = formatter(maxValue);
      svg.appendChild(maxLabel);
    }};

    buildLineChart('accuracy-chart', progress.accuracy_points || [], (value) => value.toFixed(2));
    buildLineChart('runtime-chart', progress.runtime_points || [], (value) => `${{value.toFixed(1)}}s`);

    const legend = document.getElementById('chart-legend');
    Object.entries(palette).forEach(([baseline, color]) => {{
      const item = document.createElement('span');
      item.className = 'legend-pill';
      item.innerHTML = `<span class="legend-dot" style="background:${{color}}"></span>${{baseline}}`;
      legend.appendChild(item);
    }});

    document.getElementById('status-json').textContent = JSON.stringify(status, null, 2);
    document.getElementById('progress-json').textContent = JSON.stringify(progress, null, 2);
    document.getElementById('results-json').textContent = JSON.stringify(resultsSummary, null, 2);
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
    write_results_summary(limit=20)
    output_path.write_text(render_dashboard_html(), encoding="utf-8")
    return output_path
