/* ============================================
   S.I.M.R.A.N. v2.0 — ui.js
   UI helpers, job card rendering, navigation
============================================ */

'use strict';

// ─── STATE ───────────────────────────────────────────────────────
let jobs = [{ title:'', company:'', location:'', description:'', salary:'' }];
let currentStep = 1;
let currentPage = 'home';

// ─── PAGE NAVIGATION ─────────────────────────────────────────────
function navTo(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const pg = document.getElementById('page-' + page);
  if (pg) pg.classList.add('active');

  const navEl = document.querySelector(`[data-page="${page}"]`);
  if (navEl) navEl.classList.add('active');

  currentPage = page;

  if (page === 'home') updateDashboardStats();
  if (page === 'history') renderHistory();
  if (page === 'analyze' && currentStep === 1) resetAnalysis();

  window.scrollTo(0,0);
}

// ─── STEP NAVIGATION ─────────────────────────────────────────────
function goToStep(n) {
  // Hide all step contents
  document.querySelectorAll('.step-content').forEach(s => s.classList.remove('active'));

  const sc = document.getElementById('sc' + n);
  if (sc) sc.classList.add('active');

  // Update step pills
  for (let i = 1; i <= 4; i++) {
    const pill = document.getElementById('sp' + i);
    if (!pill) continue;
    pill.className = 'step-pill';
    if (i === n) pill.classList.add('active');
    else if (i < n) pill.classList.add('done');
  }

  currentStep = n;
  window.scrollTo(0, 0);
}

function backToStep(n) { goToStep(n); }

// ─── JOB CARD RENDERING ──────────────────────────────────────────
function mkJobCard(idx, d = {}) {
  const div = document.createElement('div');
  div.className = 'jcard';
  div.id = 'jcard-' + idx;
  div.innerHTML = `
    <div class="jcard-hdr">
      <span class="jnum">Job #${idx + 1}</span>
      <button class="rm-btn" onclick="removeJob(${idx})">× Remove</button>
    </div>
    <div class="jgrid">
      <div class="fgrp">
        <span class="flbl">Job Title *</span>
        <input type="text" placeholder="e.g. Senior Engineer" value="${esc(d.title||'')}" data-f="title" data-i="${idx}">
      </div>
      <div class="fgrp">
        <span class="flbl">Company</span>
        <input type="text" placeholder="e.g. Google" value="${esc(d.company||'')}" data-f="company" data-i="${idx}">
      </div>
      <div class="fgrp">
        <span class="flbl">Location</span>
        <input type="text" placeholder="e.g. Remote / NYC" value="${esc(d.location||'')}" data-f="location" data-i="${idx}">
      </div>
    </div>
    <div class="fgrp" style="margin-bottom:10px">
      <span class="flbl">Job Description *</span>
      <textarea rows="4" placeholder="Paste the full job description — required skills, experience, responsibilities, qualifications..." data-f="description" data-i="${idx}">${esc(d.description||'')}</textarea>
    </div>
    <div class="fgrp">
      <span class="flbl">Salary (optional)</span>
      <input type="text" placeholder="e.g. $120,000 – $150,000/yr" value="${esc(d.salary||'')}" data-f="salary" data-i="${idx}">
    </div>
  `;
  return div;
}

function renderJobs() {
  const c = document.getElementById('jobsList');
  if (!c) return;
  c.innerHTML = '';
  jobs.forEach((j, i) => c.appendChild(mkJobCard(i, j)));
}

function addJob() {
  jobs.push({ title:'', company:'', location:'', description:'', salary:'' });
  renderJobs();
  // Scroll to new card
  setTimeout(() => {
    const last = document.getElementById('jcard-' + (jobs.length - 1));
    if (last) last.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 100);
}

function removeJob(idx) {
  if (jobs.length <= 1) {
    showToast('You need at least one job listing');
    return;
  }
  jobs.splice(idx, 1);
  renderJobs();
}

function collectJobData() {
  document.querySelectorAll('[data-f]').forEach(el => {
    const i = parseInt(el.dataset.i);
    if (jobs[i] !== undefined) {
      jobs[i][el.dataset.f] = el.value.trim();
    }
  });
}

// ─── SAMPLE DATA LOADERS ─────────────────────────────────────────
function loadSampleResume() {
  const ta = document.getElementById('resumeTxt');
  if (ta) {
    ta.value = SAMPLE_RESUME;
    updateCharCount();
  }
}

function loadSampleJobs() {
  jobs = SAMPLE_JOBS.map(j => ({ ...j }));
  renderJobs();
  showToast(`${SAMPLE_JOBS.length} sample jobs loaded`);
}

function clearAllJobs() {
  jobs = [{ title:'', company:'', location:'', description:'', salary:'' }];
  renderJobs();
}

// ─── CHAR COUNT ───────────────────────────────────────────────────
function updateCharCount() {
  const ta = document.getElementById('resumeTxt');
  const cc = document.getElementById('resumeCount');
  if (ta && cc) cc.textContent = ta.value.length.toLocaleString() + ' characters';
}

// ─── SLIDER ──────────────────────────────────────────────────────
function initSlider() {
  const slider = document.getElementById('minScore');
  const valEl  = document.getElementById('minScoreVal');
  if (!slider || !valEl) return;
  slider.addEventListener('input', () => { valEl.textContent = slider.value; });
}

// ─── DASHBOARD STATS ─────────────────────────────────────────────
function updateDashboardStats() {
  const history = loadHistory();
  const totalAnalyses = history.length;
  const totalJobs = history.reduce((a, h) => a + (h.totalJobs || 0), 0);
  const highMatches = history.reduce((a, h) => a + (h.highMatches || 0), 0);
  const allScores = history.flatMap(h => h.scores || []);
  const avgScore = allScores.length ? Math.round(allScores.reduce((a,b)=>a+b,0)/allScores.length) : null;

  setEl('statAnalyses', totalAnalyses);
  setEl('statHighMatches', highMatches);
  setEl('statJobs', totalJobs);
  setEl('statAvgScore', avgScore !== null ? avgScore : '—');

  renderHistory('historyCards', 3);
}

// ─── HISTORY RENDERING ───────────────────────────────────────────
function renderHistory(containerId = 'historyPage', limit = 50) {
  const c = document.getElementById(containerId);
  if (!c) return;

  const history = loadHistory();
  if (!history.length) {
    c.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📂</div>
        <div class="empty-title">No analyses yet</div>
        <div class="empty-sub">Run your first analysis to see it here</div>
        ${containerId === 'historyCards' ? `<button class="btn btn-primary" onclick="navTo('analyze')" style="margin-top:16px">Start Analysis →</button>` : ''}
      </div>`;
    return;
  }

  const items = history.slice(0, limit);
  c.innerHTML = items.map(h => {
    const date = new Date(h.timestamp).toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' });
    return `
      <div class="hist-card">
        <div class="hist-icon">🎯</div>
        <div class="hist-info">
          <div class="hist-title">${esc(h.label || 'Job Analysis')}</div>
          <div class="hist-meta">${date} · ${h.totalJobs || 0} jobs analyzed</div>
        </div>
        <div class="hist-stats">
          <div class="hist-stat">
            <span class="hist-stat-num" style="color:var(--accent)">${h.highMatches || 0}</span>
            <span class="hist-stat-lbl">High</span>
          </div>
          <div class="hist-stat">
            <span class="hist-stat-num" style="color:var(--gold)">${h.medMatches || 0}</span>
            <span class="hist-stat-lbl">Medium</span>
          </div>
          <div class="hist-stat">
            <span class="hist-stat-num">${h.avgScore || '—'}</span>
            <span class="hist-stat-lbl">Avg Score</span>
          </div>
        </div>
      </div>`;
  }).join('');
}

// ─── RESET ───────────────────────────────────────────────────────
function resetAnalysis() {
  jobs = [{ title:'', company:'', location:'', description:'', salary:'' }];
  renderJobs();
  const ta = document.getElementById('resumeTxt');
  if (ta) ta.value = '';
  updateCharCount();
  goToStep(1);
}

function newAnalysis() {
  navTo('analyze');
  resetAnalysis();
}

// ─── TOAST ───────────────────────────────────────────────────────
function showToast(msg) {
  const existing = document.querySelector('.simran-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'simran-toast';
  toast.textContent = msg;
  toast.style.cssText = `
    position:fixed;bottom:24px;right:24px;z-index:9999;
    background:var(--panel);border:1px solid var(--border2);
    color:var(--text);font-family:var(--mono);font-size:12px;
    padding:10px 18px;border-radius:8px;
    box-shadow:0 4px 20px rgba(0,0,0,.4);
    animation:toastIn .3s ease;letter-spacing:.04em;
  `;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2800);
}

// ─── UTILS ───────────────────────────────────────────────────────
function esc(str) {
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
