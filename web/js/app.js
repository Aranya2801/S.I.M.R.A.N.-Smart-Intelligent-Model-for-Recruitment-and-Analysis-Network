/* S.I.M.R.A.N. — app.js
   startup + event bindings */

'use strict';

// ─── INIT ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Render initial job card
  renderJobs();

  // Bind buttons
  bindEvents();

  // Init slider
  initSlider();

  // Update char count on resume input
  const resumeTxt = document.getElementById('resumeTxt');
  if (resumeTxt) {
    resumeTxt.addEventListener('input', updateCharCount);
  }

  // Load dashboard stats
  updateDashboardStats();

  // Start on home page
  navTo('home');

  injectToastStyle();
  initSettings();
  renderLearnedWeights('learnedWeights');
  renderLearnedWeights('learnedWeightsSettings');
});

// bars for the shipped model's coefficients (Options step + Settings page)
const FEATURE_LABELS = {
  req_cov: 'Required skills covered', pref_cov: 'Nice-to-haves covered', req_evid: 'Skills backed by work',
  exp_short: 'Experience shortfall', exp_over: 'Overqualified', sen_under: 'Role above current level',
  sen_over: 'Role below current level', title_sim: 'Similar past titles', domain_sim: 'Domain fit', loc_ok: 'Location fit',
};
function renderLearnedWeights(id) {
  const el = document.getElementById(id);
  if (!el || typeof SIMRAN_DATA === 'undefined') return;
  const m = SIMRAN_DATA.model;
  const rows = m.features.map((f, i) => [f, m.coef[i]]).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const max = Math.max(...rows.map(r => Math.abs(r[1])));
  el.innerHTML = rows.map(([f, w]) => `
    <div class="weight-item">
      <span class="weight-lbl wide">${FEATURE_LABELS[f] || f}</span>
      <div class="weight-bar"><div class="weight-fill ${w < 0 ? 'neg' : ''}" style="width:${(100 * Math.abs(w) / max).toFixed(0)}%"></div></div>
      <span class="weight-pct">${w > 0 ? '+' : ''}${w.toFixed(2)}</span>
    </div>`).join('');
}

// ─── EVENT BINDINGS ──────────────────────────────────────────────
function bindEvents() {
  // Step 1 → Step 2
  const toJobsBtn = document.getElementById('toJobsBtn');
  if (toJobsBtn) {
    toJobsBtn.addEventListener('click', () => {
      const resume = document.getElementById('resumeTxt')?.value.trim();
      if (!resume) {
        showToast('Please paste your resume first');
        return;
      }
      if (resume.length < 100) {
        showToast('Resume seems too short — please add more detail');
        return;
      }
      goToStep(2);
    });
  }

  // Step 2 → Step 3
  const toOptionsBtn = document.getElementById('toOptionsBtn');
  if (toOptionsBtn) {
    toOptionsBtn.addEventListener('click', () => {
      collectJobData();
      const valid = jobs.filter(j => j.title && j.description);
      if (!valid.length) {
        showToast('Add at least one job with a title and description');
        return;
      }
      goToStep(3);
    });
  }

  // Step 3 → Run Analysis
  const analyzeBtn = document.getElementById('analyzeBtn');
  if (analyzeBtn) {
    analyzeBtn.addEventListener('click', runAnalysis);
  }

  // Add job
  const addJobBtn = document.getElementById('addJobBtn');
  if (addJobBtn) {
    addJobBtn.addEventListener('click', addJob);
  }

  // Sample resume
  const sampleResBtn = document.getElementById('sampleResBtn');
  if (sampleResBtn) {
    sampleResBtn.addEventListener('click', loadSampleResume);
  }

  // Sample jobs
  const sampleJobsBtn = document.getElementById('sampleJobsBtn');
  if (sampleJobsBtn) {
    sampleJobsBtn.addEventListener('click', loadSampleJobs);
  }

  // Clear jobs
  const clearJobsBtn = document.getElementById('clearJobsBtn');
  if (clearJobsBtn) {
    clearJobsBtn.addEventListener('click', () => {
      clearAllJobs();
      showToast('All jobs cleared');
    });
  }

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter to advance step
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      if (currentStep === 1) document.getElementById('toJobsBtn')?.click();
      else if (currentStep === 2) document.getElementById('toOptionsBtn')?.click();
      else if (currentStep === 3) document.getElementById('analyzeBtn')?.click();
    }
    // Escape to go back
    if (e.key === 'Escape' && currentStep > 1 && currentStep < 4) {
      backToStep(currentStep - 1);
    }
  });
}

// ─── TOAST STYLE INJECTION ───────────────────────────────────────
function injectToastStyle() {
  const style = document.createElement('style');
  style.textContent = `
    @keyframes toastIn {
      from { opacity:0; transform: translateY(10px); }
      to   { opacity:1; transform: translateY(0); }
    }
    .simran-toast {
      transition: opacity .3s;
    }
  `;
  document.head.appendChild(style);
}
