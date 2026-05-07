/* ============================================
   S.I.M.R.A.N. v2.0 — results.js
   All result rendering: profile, chart, cards
============================================ */

'use strict';

// Store last result globally for export/filter
let _lastResult = null;
let _allMatches = [];

// ─── MAIN RENDER ─────────────────────────────────────────────────
function renderResults(data, totalJobsInput) {
  _lastResult = data;
  _allMatches = data.matched_jobs || [];

  // Show results div
  const resDiv = document.getElementById('resDiv');
  if (resDiv) resDiv.style.display = '';

  renderProfileCard(data.candidate_summary, data.insights);
  renderScoreChart(data.matched_jobs || []);
  renderTopPicks(data.top_recommendations || [], data.matched_jobs || []);
  renderMatchCards(data.matched_jobs || []);
  renderInsightsBanner(data.insights);
}

// ─── PROFILE CARD ────────────────────────────────────────────────
function renderProfileCard(cs, insights) {
  const el = document.getElementById('profileCard');
  if (!el || !cs) return;

  const skills = (cs.skills || []).slice(0, 18);
  const topSkills = cs.top_skills || skills.slice(0, 5);
  const ins = insights || {};

  el.innerHTML = `
    <div class="card-label" style="margin-bottom:16px">
      Candidate Profile
      ${cs.name ? `<span style="color:var(--text);font-size:12px;margin-left:6px;font-family:var(--body)">${esc(cs.name)}</span>` : ''}
    </div>
    <div class="profile-grid">
      <div class="profile-stat">
        <div class="profile-stat-label">Experience</div>
        <div class="profile-stat-value">${cs.experience_years || '?'} <span style="font-size:14px;color:var(--muted2)">yrs</span></div>
      </div>
      <div class="profile-stat">
        <div class="profile-stat-label">Location</div>
        <div class="profile-stat-value" style="font-size:14px">${esc(cs.location || 'Not specified')}</div>
      </div>
      <div class="profile-stat">
        <div class="profile-stat-label">Roles</div>
        <div class="skill-tags">${(cs.roles || []).map(r => `<span class="skill-tag">${esc(r)}</span>`).join('')}</div>
      </div>
      <div class="profile-stat">
        <div class="profile-stat-label">Skills (${skills.length})</div>
        <div class="skill-tags">${skills.map((sk, i) => `<span class="skill-tag" style="animation-delay:${i*0.04}s">${esc(sk)}</span>`).join('')}</div>
      </div>
    </div>
    ${cs.education ? `<div style="margin-top:14px;padding-top:14px;border-top:1px solid var(--border);font-size:12px;color:var(--muted2);font-family:var(--mono)">🎓 ${esc(cs.education)}</div>` : ''}
    ${ins.career_advice ? `<div style="margin-top:12px;padding:11px 14px;background:rgba(0,170,255,.05);border:1px solid rgba(0,170,255,.15);border-radius:8px;font-size:12px;color:var(--accent2);line-height:1.6">💡 ${esc(ins.career_advice)}</div>` : ''}
  `;
}

// ─── SCORE DISTRIBUTION CHART ────────────────────────────────────
function renderScoreChart(jobs) {
  const el = document.getElementById('scoreChart');
  if (!el || !jobs.length) {
    const card = document.getElementById('scoreChartCard');
    if (card) card.style.display = 'none';
    return;
  }

  // Build bucket ranges: 0-9, 10-19, ... 90-100
  const buckets = Array(10).fill(0);
  jobs.forEach(j => {
    const b = Math.min(Math.floor(j.score / 10), 9);
    buckets[b]++;
  });

  const maxVal = Math.max(...buckets, 1);

  el.innerHTML = buckets.map((count, i) => {
    const score = i * 10;
    const heightPct = (count / maxVal) * 100;
    const level = score >= 80 ? 'high' : score >= 50 ? 'medium' : 'low';
    const label = `${score}–${score + 9}`;
    return `
      <div class="chart-bar-wrap" title="${count} job(s) scoring ${label}">
        <div class="chart-bar ${level}" style="height:${Math.max(heightPct, count?4:0)}%;width:100%"></div>
        <div class="chart-bar-val">${label}</div>
      </div>`;
  }).join('');
}

// ─── TOP PICKS ────────────────────────────────────────────────────
function renderTopPicks(tops, allJobs) {
  const picksHeading = document.getElementById('picksHeading');
  const picksGrid = document.getElementById('picksGrid');
  if (!picksGrid) return;

  if (!tops.length) {
    if (picksHeading) picksHeading.style.display = 'none';
    picksGrid.innerHTML = '';
    return;
  }

  if (picksHeading) picksHeading.style.display = '';

  const crowns = ['👑', '⭐', '🌟'];

  picksGrid.innerHTML = tops.slice(0, 3).map((t, i) => {
    const matchedJob = allJobs.find(j => j.job_title === t.job_title && j.company === t.company);
    const score = t.score || matchedJob?.score || '?';
    const sal = matchedJob ? fmtSalary(matchedJob.salary_min, matchedJob.salary_max, matchedJob.currency) : '';

    return `
      <div class="pick-card">
        <div class="pick-rank">#${i+1}</div>
        <div class="pick-crown">${crowns[i] || '🎯'}</div>
        <div class="pick-title">${esc(t.job_title || '')}</div>
        <div class="pick-co">${esc(t.company || '')}</div>
        <div class="pick-score">Score: <strong style="color:var(--accent)">${score}</strong>${sal ? ` · ${sal}` : ''}</div>
        <div class="pick-reason">${esc(t.reason || '')}</div>
      </div>`;
  }).join('');
}

// ─── INSIGHTS BANNER ─────────────────────────────────────────────
function renderInsightsBanner(ins) {
  const allJobsHeading = document.getElementById('allJobsHeading');
  if (!allJobsHeading || !ins) return;

  const missing = (ins.top_missing_skills || []).slice(0, 5);
  const missingStr = missing.map(s => `<span class="pill pill-r">${esc(s)}</span>`).join('');

  allJobsHeading.innerHTML = `
    All Matched Jobs
    <span class="count-pill">${ins.total_matched || _allMatches.length}</span>
    ${missing.length ? `<span style="margin-left:10px;font-size:12px;color:var(--muted2);font-family:var(--body);font-weight:400">Top gaps: ${missingStr}</span>` : ''}
  `;
}

// ─── MATCH CARDS ─────────────────────────────────────────────────
function renderMatchCards(jobs, filter = 'all', sortBy = 'score') {
  const el = document.getElementById('matchList');
  if (!el) return;

  let filtered = [...jobs];

  // Filter
  if (filter !== 'all') {
    filtered = filtered.filter(j => (j.match_level || '').toLowerCase() === filter);
  }

  // Sort
  if (sortBy === 'salary') {
    filtered.sort((a, b) => (b.salary_max || 0) - (a.salary_max || 0));
  } else {
    filtered.sort((a, b) => b.score - a.score);
  }

  if (!filtered.length) {
    el.innerHTML = `<div class="empty-state" style="padding:30px 0"><div class="empty-icon">🔍</div><div class="empty-title">No jobs match this filter</div></div>`;
    return;
  }

  el.innerHTML = filtered.map((job, idx) => {
    const lv = (job.match_level || 'low').toLowerCase();
    const strengths = (job.strengths || []).slice(0, 8);
    const missing   = (job.missing_skills || []).slice(0, 8);
    const skillPct  = job.skill_match_pct || 0;
    const salary    = fmtSalary(job.salary_min, job.salary_max, job.currency);

    return `
      <div class="mcard ${lv}" data-level="${lv}" data-score="${job.score}" data-salmax="${job.salary_max || 0}">
        <div class="mcard-hdr">
          <div class="m-left">
            <div class="m-rank">Rank #${idx + 1}</div>
            <div class="m-title">${esc(job.job_title || '')}</div>
            <div class="m-co">${esc(job.company || '')}${job.location ? ` · ${esc(job.location)}` : ''}</div>
          </div>
          <div class="m-right">
            <div class="score-circle ${lv}">
              <span class="sc-num">${job.score || 0}</span>
              <span class="sc-lbl">score</span>
            </div>
            <span class="mbadge ${lv}">${job.match_level || ''}</span>
          </div>
        </div>

        <div class="m-meta">
          <div class="meta-chip">💰 <span class="salary-val">${salary}</span></div>
          ${job.location ? `<div class="meta-chip">📍 ${esc(job.location)}</div>` : ''}
          ${skillPct ? `<div class="meta-chip">🎯 ${skillPct}% skill match</div>` : ''}
        </div>

        <!-- Skill match bar -->
        <div class="skill-match-bar">
          <span class="smb-label">Skill Match</span>
          <div class="smb-track">
            <div class="smb-fill" style="width:${skillPct}%;background:${lv==='high'?'var(--accent)':lv==='medium'?'var(--gold)':'var(--muted)'}"></div>
          </div>
          <span style="font-family:var(--mono);font-size:11px;color:var(--muted2)">${skillPct}%</span>
        </div>

        ${job.reason ? `<div class="m-reason">${esc(job.reason)}</div>` : ''}

        ${strengths.length ? `
          <div class="pills-row">
            <div class="pills-lbl">Strengths</div>
            ${strengths.map(s => `<span class="pill pill-g">${esc(s)}</span>`).join('')}
          </div>` : ''}

        ${missing.length ? `
          <div class="pills-row">
            <div class="pills-lbl">Skill Gaps</div>
            ${missing.map(s => `<span class="pill pill-r">${esc(s)}</span>`).join('')}
          </div>` : ''}
      </div>`;
  }).join('');
}

// ─── FILTER + SORT ───────────────────────────────────────────────
let _currentFilter = 'all';
let _currentSort   = 'score';

function filterJobs(filter, btn) {
  _currentFilter = filter;
  document.querySelectorAll('.filter-btn').forEach(b => {
    if (['all','high','medium','low'].includes(b.textContent.toLowerCase().split(' ')[0])) {
      b.classList.remove('active');
    }
  });
  if (btn) btn.classList.add('active');
  renderMatchCards(_allMatches, _currentFilter, _currentSort);
}

function sortJobs(sortBy, btn) {
  _currentSort = sortBy;
  document.querySelectorAll('.filter-btn').forEach(b => {
    if (b.textContent.includes('↓')) b.classList.remove('active');
  });
  if (btn) btn.classList.add('active');
  renderMatchCards(_allMatches, _currentFilter, _currentSort);
}

// ─── EXPORT ──────────────────────────────────────────────────────
function exportJSON() {
  if (!_lastResult) return;
  const blob = new Blob([JSON.stringify(_lastResult, null, 2)], { type: 'application/json' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = 'simran_results.json';
  a.click(); URL.revokeObjectURL(url);
  showToast('Results exported as JSON');
}

function copyReport() {
  if (!_lastResult) return;
  const cs = _lastResult.candidate_summary || {};
  const jobs = (_lastResult.matched_jobs || []).slice(0, 5);
  const ins = _lastResult.insights || {};

  let report = `S.I.M.R.A.N. Job Analysis Report\n`;
  report += `${'─'.repeat(40)}\n\n`;
  report += `CANDIDATE: ${cs.roles?.join(', ') || 'N/A'} | ${cs.experience_years} years experience\n`;
  report += `LOCATION: ${cs.location}\n`;
  report += `SKILLS: ${(cs.skills || []).slice(0,10).join(', ')}\n\n`;
  report += `RESULTS: ${ins.total_matched || jobs.length} matches found\n`;
  report += `High: ${ins.high_matches || 0} · Medium: ${ins.medium_matches || 0} · Avg Score: ${ins.avg_score || '?'}\n\n`;
  report += `TOP MATCHES:\n`;
  jobs.forEach((j, i) => {
    report += `${i+1}. ${j.job_title} @ ${j.company} — Score: ${j.score} (${j.match_level})\n`;
    report += `   Salary: ${fmtSalary(j.salary_min, j.salary_max, j.currency)}\n`;
    report += `   ${j.reason}\n\n`;
  });

  navigator.clipboard.writeText(report).then(() => {
    showToast('Report copied to clipboard!');
  }).catch(() => {
    showToast('Could not copy — try exporting JSON instead');
  });
}

// ─── SALARY FORMAT ───────────────────────────────────────────────
function fmtSalary(min, max, currency) {
  if (!min && !max) return 'Salary not listed';
  const sym = currency === 'USD' ? '$' : currency === 'GBP' ? '£' : currency === 'EUR' ? '€' : (currency || '');
  const fmt = n => n >= 1000 ? sym + (n / 1000).toFixed(0) + 'k' : sym + n;
  if (min && max) return `${fmt(min)} – ${fmt(max)} / yr`;
  if (min) return `${fmt(min)}+ / yr`;
  return `Up to ${fmt(max)} / yr`;
}
