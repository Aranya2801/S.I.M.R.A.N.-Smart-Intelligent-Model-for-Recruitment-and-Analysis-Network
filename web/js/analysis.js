/* ============================================
   S.I.M.R.A.N. v2.0 — analysis.js
   Anthropic API integration, loading states
============================================ */

'use strict';

// ─── LOADING MESSAGES ────────────────────────────────────────────
const LOAD_MESSAGES = [
  { msg: 'Initializing neural recruitment engine...', pct: 5 },
  { msg: 'Parsing resume — extracting skills and experience...', pct: 18 },
  { msg: 'Identifying candidate profile and roles...', pct: 30 },
  { msg: 'Analyzing job descriptions and requirements...', pct: 45 },
  { msg: 'Computing skill overlap matrices...', pct: 58 },
  { msg: 'Scoring match compatibility for each role...', pct: 70 },
  { msg: 'Estimating salary ranges from market data...', pct: 82 },
  { msg: 'Ranking jobs and generating recommendations...', pct: 92 },
  { msg: 'Finalizing insights and career advice...', pct: 98 },
];

// ─── MAIN ANALYSIS FUNCTION ──────────────────────────────────────
async function runAnalysis() {
  // Collect all form data
  collectJobData();

  const resume = document.getElementById('resumeTxt')?.value.trim();
  if (!resume) {
    showToast('Please enter your resume first');
    goToStep(1);
    return;
  }

  const validJobs = jobs.filter(j => j.title && j.description);
  if (!validJobs.length) {
    showToast('Add at least one job with a title and description');
    return;
  }

  // Read options
  const opts = {
    minScore:   parseInt(document.getElementById('minScore')?.value || '40'),
    prefRemote: document.getElementById('prefRemote')?.checked ?? true,
    prefSalary: document.getElementById('prefSalary')?.checked ?? true,
    prefStrict: document.getElementById('prefStrict')?.checked ?? false,
    lang:       document.getElementById('outputLang')?.value || 'English',
  };

  // Show step 4 / loading
  goToStep(4);
  showLoading();

  const systemPrompt = buildSystemPrompt(opts);

  const userPayload = {
    resume_text: resume,
    jobs: validJobs.map(j => ({
      job_title:   j.title,
      company:     j.company,
      location:    j.location,
      description: j.description,
      salary:      j.salary,
    }))
  };

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 4096,
        system: systemPrompt,
        messages: [{ role: 'user', content: JSON.stringify(userPayload) }]
      })
    });

    hideLoading();

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error?.message || `API error ${response.status}`);
    }

    const data = await response.json();
    const rawText = (data.content || [])
      .filter(b => b.type === 'text')
      .map(b => b.text)
      .join('');

    // Clean and parse JSON
    const cleaned = rawText.replace(/```json\s*/g, '').replace(/```\s*/g, '').trim();
    const parsed = JSON.parse(cleaned);

    // Validate structure
    if (!parsed.candidate_summary || !parsed.matched_jobs) {
      throw new Error('Invalid response structure from AI');
    }

    // Save to history
    const scores = (parsed.matched_jobs || []).map(j => j.score);
    const avgScore = scores.length ? Math.round(scores.reduce((a,b)=>a+b,0)/scores.length) : 0;
    const highMatches = (parsed.matched_jobs || []).filter(j => j.match_level === 'High').length;
    const medMatches  = (parsed.matched_jobs || []).filter(j => j.match_level === 'Medium').length;

    saveToHistory({
      label: `${parsed.candidate_summary.roles?.[0] || 'Analysis'} · ${validJobs.length} jobs`,
      totalJobs: validJobs.length,
      highMatches,
      medMatches,
      avgScore,
      scores,
    });

    // Render results
    renderResults(parsed, validJobs.length);

  } catch (err) {
    hideLoading();
    showError(err.message);
  }
}

// ─── LOADING STATE ───────────────────────────────────────────────
let loadingInterval = null;
let progressInterval = null;

function showLoading() {
  const loadDiv = document.getElementById('loadDiv');
  const errDiv  = document.getElementById('errDiv');
  const resDiv  = document.getElementById('resDiv');
  if (loadDiv) loadDiv.style.display = '';
  if (errDiv)  errDiv.style.display  = 'none';
  if (resDiv)  resDiv.style.display  = 'none';

  // Cycle through messages
  let msgIdx = 0;
  const msgEl = document.getElementById('loadMsg');
  const fillEl = document.getElementById('progressFill');
  const pctEl  = document.getElementById('progressPct');

  if (msgEl && LOAD_MESSAGES[0]) {
    msgEl.textContent = LOAD_MESSAGES[0].msg;
  }
  if (fillEl) fillEl.style.width = '5%';
  if (pctEl)  pctEl.textContent = '5%';

  loadingInterval = setInterval(() => {
    msgIdx = Math.min(msgIdx + 1, LOAD_MESSAGES.length - 1);
    const entry = LOAD_MESSAGES[msgIdx];
    if (msgEl)  msgEl.textContent = entry.msg;
    if (fillEl) fillEl.style.width = entry.pct + '%';
    if (pctEl)  pctEl.textContent  = entry.pct + '%';
  }, 2200);
}

function hideLoading() {
  clearInterval(loadingInterval);
  clearInterval(progressInterval);
  const loadDiv = document.getElementById('loadDiv');
  if (loadDiv) loadDiv.style.display = 'none';
}

// ─── ERROR STATE ─────────────────────────────────────────────────
function showError(msg) {
  const errDiv = document.getElementById('errDiv');
  const errMsg = document.getElementById('errMsg');
  if (errDiv) errDiv.style.display = '';
  if (errMsg) errMsg.textContent = msg;
}
