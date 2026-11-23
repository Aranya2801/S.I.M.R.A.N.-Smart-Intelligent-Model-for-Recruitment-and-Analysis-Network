/* S.I.M.R.A.N. — analysis.js
 * Runs an analysis with whichever engine is picked in Settings:
 *   local  -> SimranEngine (engine.js), runs in the page, default
 *   claude -> Anthropic Messages API with the user's own key
 */
'use strict';

const LOAD_MESSAGES = [
  { msg: 'Parsing resume sections...', pct: 10 },
  { msg: 'Extracting skills and experience dates...', pct: 28 },
  { msg: 'Reading requirements vs nice-to-haves in each posting...', pct: 46 },
  { msg: 'Scoring each job...', pct: 68 },
  { msg: 'Ranking and collecting skill gaps...', pct: 88 },
  { msg: 'Almost done...', pct: 97 },
];

const SETTINGS_KEY = 'simran_settings_v3';
const DEFAULT_SETTINGS = { engine: 'local', apiKey: '', model: 'claude-sonnet-5-5' };

function loadSettings() {
  try { return { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}') }; }
  catch { return { ...DEFAULT_SETTINGS }; }
}
function saveSettings(s) {
  try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(s)); } catch { /* private mode etc */ }
}

async function runAnalysis() {
  collectJobData();
  let resume = document.getElementById('resumeTxt')?.value.trim();
  if (!resume) { showToast('Please enter your resume first'); goToStep(1); return; }

  const validJobs = jobs.filter(j => j.title && j.description);
  if (!validJobs.length) { showToast('Add at least one job with a title and description'); return; }

  const opts = {
    minScore:   parseInt(document.getElementById('minScore')?.value || '40', 10),
    prefRemote: document.getElementById('prefRemote')?.checked ?? false,
    prefSalary: document.getElementById('prefSalary')?.checked ?? true,
    prefStrict: document.getElementById('prefStrict')?.checked ?? false,
    blind:      document.getElementById('prefBlind')?.checked ?? true,
    lang:       document.getElementById('outputLang')?.value || 'English',
  };
  if (opts.blind) resume = redactResume(resume);

  const settings = loadSettings();
  goToStep(4);
  showLoading();

  try {
    let parsed;
    if (settings.engine === 'claude') {
      parsed = await runClaude(resume, validJobs, opts, settings);
    } else {
      await new Promise(r => setTimeout(r, 450)); // let the loader paint; the engine itself takes ~ms
      parsed = SimranEngine.analyze(resume, validJobs, opts);
    }
    hideLoading();
    if (!parsed.candidate_summary || !parsed.matched_jobs) throw new Error('Unexpected result shape');

    const all = parsed.matched_jobs || [];
    const scores = all.map(j => j.score);
    saveToHistory({
      label: `${parsed.candidate_summary.roles?.[0] || 'Analysis'} · ${validJobs.length} jobs`,
      engine: settings.engine,
      totalJobs: validJobs.length,
      highMatches: all.filter(j => j.match_level === 'High').length,
      medMatches: all.filter(j => j.match_level === 'Medium').length,
      avgScore: scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0,
      scores,
    });
    renderResults(parsed, validJobs.length);
  } catch (err) {
    hideLoading();
    showError(err.message);
  }
}

// Same idea as simran/redact.py, kept short.
function redactResume(text) {
  const lines = text.split('\n');
  const i = lines.findIndex(l => l.trim());
  if (i >= 0) {
    const parts = lines[i].split(/\s[—–|-]\s/);
    lines[i] = '[NAME]' + (parts.length > 1 ? ' — ' + parts.slice(1).join(' — ') : '');
  }
  return lines.join('\n')
    .replace(/[\w.+-]+@[\w-]+\.[\w.]+/g, '[EMAIL]')
    .replace(/\b(?:https?:\/\/|www\.)\S+|\b(?:github|linkedin|gitlab)\.com\/\S+/gi, '[URL]')
    .replace(/(?<!\d)(\+?\d[\d\s().-]{8,}\d)(?!\d)/g, m => (m.replace(/\D/g, '').length >= 10 ? '[PHONE]' : m))
    .replace(/\b(he|she|him|her|his|hers|mr|mrs|ms|miss)\b\.?/gi, '')
    .replace(/\b(women'?s?|female|male|men'?s|black|hispanic|latin[ao]x?|asian|muslim|christian|hindu|jewish|lgbtq?\+?)(?=\s+(in|of|engineers|society|club|association|network|students|coders|who))/gi, '[GROUP]');
}

async function runClaude(resume, validJobs, opts, settings) {
  if (!settings.apiKey) throw new Error('Claude mode needs an API key. Add one in Settings, or switch back to the local engine.');
  const body = {
    resume_text: resume,
    jobs: validJobs.map(j => ({ job_title: j.title, company: j.company, location: j.location, description: j.description, salary: j.salary })),
  };
  // The old version called the API with no key or version header, so every request was rejected.
  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': settings.apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
    },
    body: JSON.stringify({
      model: settings.model || DEFAULT_SETTINGS.model,
      max_tokens: 4096,
      system: buildSystemPrompt(opts),
      messages: [{ role: 'user', content: JSON.stringify(body) }],
    }),
  });
  if (!response.ok) {
    const e = await response.json().catch(() => ({}));
    if (response.status === 401) throw new Error('API key was rejected (401). Check it in Settings.');
    throw new Error(e.error?.message || `API error ${response.status}`);
  }
  const data = await response.json();
  const raw = (data.content || []).filter(b => b.type === 'text').map(b => b.text).join('');
  // models sometimes wrap the JSON in prose or fences; take the outermost object
  const a = raw.indexOf('{'), b = raw.lastIndexOf('}');
  if (a < 0 || b < a) throw new Error('Model reply did not contain JSON');
  return JSON.parse(raw.slice(a, b + 1));
}

let loadingInterval = null;

function showLoading() {
  const loadDiv = document.getElementById('loadDiv');
  document.getElementById('errDiv').style.display = 'none';
  document.getElementById('resDiv').style.display = 'none';
  if (loadDiv) loadDiv.style.display = '';
  let i = 0;
  const msgEl = document.getElementById('loadMsg');
  const fillEl = document.getElementById('progressFill');
  const pctEl = document.getElementById('progressPct');
  const paint = () => {
    const e = LOAD_MESSAGES[i];
    if (msgEl) msgEl.textContent = e.msg;
    if (fillEl) fillEl.style.width = e.pct + '%';
    if (pctEl) pctEl.textContent = e.pct + '%';
  };
  paint();
  const fast = loadSettings().engine === 'local';
  loadingInterval = setInterval(() => { i = Math.min(i + 1, LOAD_MESSAGES.length - 1); paint(); }, fast ? 80 : 2000);
}

function hideLoading() {
  clearInterval(loadingInterval);
  const loadDiv = document.getElementById('loadDiv');
  if (loadDiv) loadDiv.style.display = 'none';
}

function showError(msg) {
  const errDiv = document.getElementById('errDiv');
  const errMsg = document.getElementById('errMsg');
  if (errDiv) errDiv.style.display = '';
  if (errMsg) errMsg.textContent = msg;
}

// ---- settings page -------------------------------------------------------
function initSettings() {
  const s = loadSettings();
  const eng = document.querySelectorAll('input[name="engine"]');
  eng.forEach(r => { r.checked = r.value === s.engine; });
  const key = document.getElementById('apiKey');
  const model = document.getElementById('modelName');
  if (key) key.value = s.apiKey;
  if (model) model.value = s.model;
  const sync = () => {
    const engine = [...eng].find(r => r.checked)?.value || 'local';
    document.getElementById('claudeFields')?.classList.toggle('hidden', engine !== 'claude');
  };
  const badge = () => {
    const el = document.getElementById('engineBadge');
    if (el) el.textContent = loadSettings().engine === 'claude' ? 'Engine: Claude API' : 'Engine: local model v3';
  };
  eng.forEach(r => r.addEventListener('change', sync));
  document.getElementById('saveSettingsBtn')?.addEventListener('click', () => {
    saveSettings({
      engine: [...eng].find(r => r.checked)?.value || 'local',
      apiKey: key?.value.trim() || '',
      model: model?.value.trim() || DEFAULT_SETTINGS.model,
    });
    badge();
    showToast('Settings saved (stored only in this browser)');
  });
  sync();
  badge();
}
