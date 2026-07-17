from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.db.database import SessionLocal
from app.models.job import JobState
from app.repositories.job import JobRepository
from app.services.queue import QueueService

dashboard_app = FastAPI(title="QueueCTL Dashboard")


def get_repo():
    db = SessionLocal()
    return db, JobRepository(db)


@dashboard_app.get("/api/stats")
def api_stats():
    db, repo = get_repo()
    queue = QueueService()
    stats = repo.get_stats()
    stats["queue_size"] = queue.size()
    db.close()
    return stats


@dashboard_app.get("/api/jobs")
def api_jobs(state: str = None):
    db, repo = get_repo()
    if state:
        try:
            job_state = JobState(state)
            jobs = repo.list_by_state(job_state)
        except ValueError:
            jobs = repo.list_all()
    else:
        jobs = repo.list_all()

    result = []
    for job in jobs:
        result.append({
            "id": job.id,
            "command": job.command,
            "state": job.state.value,
            "priority": job.priority,
            "attempts": job.attempts,
            "max_retries": job.max_retries,
            "timeout": job.timeout,
            "duration_ms": job.duration_ms,
            "last_error": job.last_error,
            "created_at": str(job.created_at) if job.created_at else None,
            "started_at": str(job.started_at) if job.started_at else None,
            "completed_at": str(job.completed_at) if job.completed_at else None,
        })
    db.close()
    return result


@dashboard_app.get("/api/jobs/{job_id}")
def api_job_detail(job_id: str):
    db, repo = get_repo()
    job = repo.get_by_id(job_id)
    if not job:
        db.close()
        return {"error": "Job not found"}
    result = {
        "id": job.id,
        "command": job.command,
        "state": job.state.value,
        "priority": job.priority,
        "attempts": job.attempts,
        "max_retries": job.max_retries,
        "timeout": job.timeout,
        "duration_ms": job.duration_ms,
        "last_error": job.last_error,
        "stdout": job.stdout,
        "stderr": job.stderr,
        "created_at": str(job.created_at) if job.created_at else None,
        "started_at": str(job.started_at) if job.started_at else None,
        "completed_at": str(job.completed_at) if job.completed_at else None,
    }
    db.close()
    return result


@dashboard_app.get("/", response_class=HTMLResponse)
def dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QueueCTL Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: #0f1117;
    color: #e1e4e8;
    padding: 24px;
  }
  h1 {
    font-size: 22px;
    margin-bottom: 20px;
    color: #58a6ff;
  }
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }
  .stat-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
  }
  .stat-card .value {
    font-size: 28px;
    font-weight: 700;
  }
  .stat-card .label {
    font-size: 12px;
    color: #8b949e;
    margin-top: 4px;
    text-transform: uppercase;
  }
  .stat-card.pending .value { color: #d29922; }
  .stat-card.processing .value { color: #58a6ff; }
  .stat-card.completed .value { color: #3fb950; }
  .stat-card.failed .value { color: #f85149; }
  .stat-card.dead .value { color: #f0883e; }
  .stat-card.timed_out .value { color: #bc8cff; }
  .stat-card.queue .value { color: #79c0ff; }
  .stat-card.rate .value { color: #3fb950; }

  .controls {
    margin-bottom: 16px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .controls button {
    padding: 6px 14px;
    border: 1px solid #30363d;
    background: #21262d;
    color: #c9d1d9;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
  }
  .controls button:hover { background: #30363d; }
  .controls button.active { background: #58a6ff; color: #0d1117; border-color: #58a6ff; }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  th {
    text-align: left;
    padding: 10px 8px;
    border-bottom: 2px solid #30363d;
    color: #8b949e;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
  }
  td {
    padding: 8px;
    border-bottom: 1px solid #21262d;
  }
  tr:hover { background: #161b22; }
  tr { cursor: pointer; }

  .badge {
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
  }
  .badge.pending { background: #d29922; color: #0d1117; }
  .badge.processing { background: #58a6ff; color: #0d1117; }
  .badge.completed { background: #3fb950; color: #0d1117; }
  .badge.failed { background: #f85149; color: #fff; }
  .badge.dead { background: #f0883e; color: #0d1117; }
  .badge.timed_out { background: #bc8cff; color: #0d1117; }

  .modal-bg {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.7);
    z-index: 100;
    justify-content: center;
    align-items: center;
  }
  .modal-bg.open { display: flex; }
  .modal {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 24px;
    width: 90%;
    max-width: 700px;
    max-height: 80vh;
    overflow-y: auto;
  }
  .modal h2 { font-size: 16px; color: #58a6ff; margin-bottom: 12px; }
  .modal pre {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 12px;
    font-size: 12px;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 200px;
    overflow-y: auto;
    margin: 8px 0;
  }
  .modal .field { margin-bottom: 6px; }
  .modal .field span { color: #8b949e; }
  .modal .close-btn {
    float: right;
    cursor: pointer;
    color: #8b949e;
    font-size: 18px;
    background: none;
    border: none;
  }
  .modal .close-btn:hover { color: #fff; }

  .refresh-info {
    font-size: 11px;
    color: #484f58;
    margin-bottom: 16px;
  }
</style>
</head>
<body>

<h1>&#9881; QueueCTL Dashboard</h1>
<div class="refresh-info">Auto-refreshes every 5 seconds</div>

<div class="stats-grid" id="stats"></div>

<div class="controls" id="filters"></div>

<table>
  <thead>
    <tr>
      <th>ID</th>
      <th>Command</th>
      <th>State</th>
      <th>Priority</th>
      <th>Attempts</th>
      <th>Duration</th>
      <th>Created</th>
    </tr>
  </thead>
  <tbody id="jobs"></tbody>
</table>

<div class="modal-bg" id="modalBg" onclick="closeModal()">
  <div class="modal" onclick="event.stopPropagation()" id="modal"></div>
</div>

<script>
let currentFilter = null;

async function loadStats() {
  const r = await fetch('/api/stats');
  const d = await r.json();
  const c = d.counts;
  document.getElementById('stats').innerHTML = `
    <div class="stat-card queue"><div class="value">${d.queue_size}</div><div class="label">Queue</div></div>
    <div class="stat-card pending"><div class="value">${c.pending}</div><div class="label">Pending</div></div>
    <div class="stat-card processing"><div class="value">${c.processing}</div><div class="label">Processing</div></div>
    <div class="stat-card completed"><div class="value">${c.completed}</div><div class="label">Completed</div></div>
    <div class="stat-card failed"><div class="value">${c.failed}</div><div class="label">Failed</div></div>
    <div class="stat-card dead"><div class="value">${c.dead}</div><div class="label">Dead</div></div>
    <div class="stat-card timed_out"><div class="value">${c.timed_out}</div><div class="label">Timed Out</div></div>
    <div class="stat-card rate"><div class="value">${d.success_rate}%</div><div class="label">Success Rate</div></div>
  `;
}

async function loadJobs() {
  const url = currentFilter ? '/api/jobs?state=' + currentFilter : '/api/jobs';
  const r = await fetch(url);
  const jobs = await r.json();
  const tbody = document.getElementById('jobs');
  tbody.innerHTML = jobs.map(j => `
    <tr onclick="showDetail('${j.id}')">
      <td>${j.id.slice(0, 8)}...</td>
      <td>${j.command}</td>
      <td><span class="badge ${j.state}">${j.state}</span></td>
      <td>${j.priority}</td>
      <td>${j.attempts}/${j.max_retries}</td>
      <td>${j.duration_ms ? j.duration_ms + 'ms' : '-'}</td>
      <td>${j.created_at ? j.created_at.slice(0, 19) : '-'}</td>
    </tr>
  `).join('');
}

function buildFilters() {
  const states = ['all', 'pending', 'processing', 'completed', 'failed', 'dead', 'timed_out'];
  document.getElementById('filters').innerHTML = states.map(s => 
    `<button class="${(s === 'all' && !currentFilter) || s === currentFilter ? 'active' : ''}" 
      onclick="setFilter('${s}')">${s}</button>`
  ).join('');
}

function setFilter(s) {
  currentFilter = s === 'all' ? null : s;
  buildFilters();
  loadJobs();
}

async function showDetail(id) {
  const r = await fetch('/api/jobs/' + id);
  const j = await r.json();
  document.getElementById('modal').innerHTML = `
    <button class="close-btn" onclick="closeModal()">&times;</button>
    <h2>Job Detail</h2>
    <div class="field"><span>ID:</span> ${j.id}</div>
    <div class="field"><span>Command:</span> ${j.command}</div>
    <div class="field"><span>State:</span> <span class="badge ${j.state}">${j.state}</span></div>
    <div class="field"><span>Priority:</span> ${j.priority}</div>
    <div class="field"><span>Attempts:</span> ${j.attempts}/${j.max_retries}</div>
    <div class="field"><span>Timeout:</span> ${j.timeout || 'None'}</div>
    <div class="field"><span>Duration:</span> ${j.duration_ms ? j.duration_ms + 'ms' : 'N/A'}</div>
    <div class="field"><span>Started:</span> ${j.started_at || 'N/A'}</div>
    <div class="field"><span>Completed:</span> ${j.completed_at || 'N/A'}</div>
    ${j.last_error ? '<div class="field"><span>Error:</span></div><pre>' + j.last_error + '</pre>' : ''}
    ${j.stdout ? '<div class="field"><span>STDOUT:</span></div><pre>' + j.stdout + '</pre>' : ''}
    ${j.stderr ? '<div class="field"><span>STDERR:</span></div><pre>' + j.stderr + '</pre>' : ''}
  `;
  document.getElementById('modalBg').classList.add('open');
}

function closeModal() {
  document.getElementById('modalBg').classList.remove('open');
}

async function refresh() {
  await loadStats();
  await loadJobs();
}

buildFilters();
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>"""
