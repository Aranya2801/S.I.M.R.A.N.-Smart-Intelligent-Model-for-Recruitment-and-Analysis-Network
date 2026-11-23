/* S.I.M.R.A.N. local engine
 *
 * Port of simran/parsing.py + simran/features.py + simran/model.py so the demo
 * runs fully in the browser (no API key, nothing leaves the page).
 * Keep it in sync with the python side -- tests/test_web_parity.py runs both
 * on the same inputs and fails if the scores drift.
 */
'use strict';

const SimranEngine = (() => {
  const D = (typeof SIMRAN_DATA !== 'undefined') ? SIMRAN_DATA : null;

  const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const PATTERNS = D ? D.patterns.map(([alias, canon]) => ({
    alias, canon, re: new RegExp('(?<![\\w+#.])' + esc(alias) + '(?![\\w+#]|\\.\\w)', 'g'),
  })) : [];
  const AMBIGUOUS = new Set(D ? D.ambiguous : []);

  const NEGATION = /\b(no|not|never|without|lack(?:ing)?|unfamiliar)\b[^.;\n]{0,35}$/i;
  const LIST_LINE = /^\s*[\w /&-]{2,30}:\s*\S|[,|•·].*[,|•·]/;
  const SENTENCE_START = /(^|[.!?]\s+|\n\s*[-*•]?\s*)$/;

  function ambiguousOk(text, s, e) {
    const ls = text.lastIndexOf('\n', s - 1) + 1;
    let le = text.indexOf('\n', e);
    if (le === -1) le = text.length;
    if (LIST_LINE.test(text.slice(ls, le))) return true;
    const w = text.slice(s, e);
    return w[0] !== w[0].toLowerCase() && !SENTENCE_START.test(text.slice(Math.max(0, s - 4), s));
  }

  function extract(text) {
    const low = text.toLowerCase();
    const found = {};
    const taken = [];
    for (const { alias, canon, re } of PATTERNS) {
      re.lastIndex = 0;
      let m;
      while ((m = re.exec(low)) !== null) {
        const s = m.index, e = s + m[0].length;
        if (taken.some(([ts, te]) => s < te && e > ts)) continue;
        if (NEGATION.test(low.slice(Math.max(0, s - 40), s))) continue;
        if (AMBIGUOUS.has(alias) && !ambiguousOk(text, s, e)) continue;
        taken.push([s, e]);
        (found[canon] = found[canon] || []).push(s);
      }
    }
    return found;
  }

  // ---- parsing ---------------------------------------------------------
  const MONTHS = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };
  const dt = n => `(?:(?<m${n}>jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\\.?\\s+)?(?<y${n}>(?:19|20)\\d{2})`;
  const RANGE_SRC = dt(1) + '\\s*(?:-|–|—|to)\\s*(?:' + dt(2) + '|(?<now>present|current|now|today))';
  const YEARS_STATED = /(\d{1,2})\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:\w+\s+){0,3}?experience/gi;
  const YEARS_REQ = /(\d{1,2})\s*(?:\+|plus)?\s*(?:(?:-|–|to)\s*(\d{1,2})\s*)?(?:years?|yrs?)/i;
  const PREF_HEAD = /^\s*(nice[ -]to[ -]have|preferred|bonus|pluses|a plus|good to have|desired)\b/i;
  const REQ_HEAD = /^\s*(requirements?|required|must[ -]have|qualifications|what you.?ll need|you have|minimum)\b/i;
  const ABOUT_HEAD = /^\s*(about (us|the company)|who we are|benefits|perks|our stack)\b/i;
  const EXP_HEAD = /^\s*(professional |work )?(experience|employment|work history)\s*:?\s*$/i;
  const OTHER_HEAD = /^\s*(skills|technical skills|education|projects|certifications?|summary|profile|awards|publications|activities)\b.*:?\s*$/i;
  const REMOTE = /\b(remote|work from home|wfh|distributed team|anywhere)\b/i;
  const OPEN_REMOTE = /(open to|prefer|seeking|available for)\s+(remote|relocation|hybrid)/i;
  const SENIORITY = [
    [4, ['principal', 'staff', 'head of', 'director', 'architect']],
    [3, ['senior', 'sr.', 'sr ', 'lead']],
    [1, ['junior', 'jr.', 'jr ', 'intern', 'graduate', 'entry level', 'entry-level', 'associate']],
  ];
  const TITLE_STOP = new Set(['engineer', 'developer', 'the', 'of', 'and', 'a', 'an', 'ii', 'iii', 'i', 'sr', 'jr',
    'senior', 'junior', 'lead', 'staff', 'principal', 'intern', '-', '/', ',']);

  function seniorityOf(title) {
    const t = ` ${title.toLowerCase()} `;
    for (const [lvl, words] of SENIORITY) if (words.some(w => t.includes(w))) return lvl;
    return 2;
  }

  // python's str.splitlines(keepends=True), close enough for \n and \r\n
  const linesKeep = t => t.match(/[^\n]*\n|[^\n]+$/g) || [];

  function experienceSpans(text) {
    const spans = [];
    let start = null, pos = 0;
    for (const line of linesKeep(text)) {
      if (EXP_HEAD.test(line)) start = pos + line.length;
      else if (start !== null && OTHER_HEAD.test(line)) { spans.push([start, pos]); start = null; }
      pos += line.length;
    }
    if (start !== null) spans.push([start, pos]);
    return spans;
  }

  const toMonths = (y, m) => parseInt(y, 10) * 12 + ((MONTHS[(m || 'jan').slice(0, 3).toLowerCase()] || 1) - 1);

  function experienceYears(text, today) {
    today = today || new Date();
    const now = today.getFullYear() * 12 + today.getMonth();
    const spans = [];
    const re = new RegExp(RANGE_SRC, 'gi');
    let m;
    while ((m = re.exec(text)) !== null) {
      const g = m.groups;
      const a = toMonths(g.y1, g.m1);
      let b = g.now ? now : toMonths(g.y2, g.m2) + 1;  // end month inclusive
      if (g.y2 && !g.m2) b += 11;
      if (b - a >= 0 && b - a < 600) spans.push([a, b]);
    }
    spans.sort((x, y) => x[0] - y[0] || x[1] - y[1]);
    let total = 0, cur = null;
    for (const [a, b] of spans) {
      if (cur && a <= cur[1]) cur = [cur[0], Math.max(cur[1], b)];
      else { if (cur) total += cur[1] - cur[0]; cur = [a, b]; }
    }
    if (cur) total += cur[1] - cur[0];
    let years = total / 12;
    const stated = [...text.matchAll(YEARS_STATED)].map(x => parseInt(x[1], 10));
    if (stated.length && years < 0.5) years = Math.max(...stated);
    return Math.floor(years * 10 + 0.5) / 10;
  }

  function resumeTitles(text) {
    const out = [];
    const rangeRe = new RegExp(RANGE_SRC, 'i');
    for (let line of text.split(/\r?\n/)) {
      line = line.trim();
      if ('-*•'.includes(line[0] || 'x')) continue;
      if (rangeRe.test(line) || /\s[—–|-]\s/.test(line.slice(0, 80))) {
        const head = line.split(/\s[—–|-]\s|\(|,/)[0].trim();
        if (head.length > 2 && head.length < 60 &&
            /engineer|developer|scientist|analyst|manager|architect|designer|lead|intern|consultant|administrator|sre|devops/i.test(head)) {
          out.push(head);
        }
      }
    }
    return out;
  }

  function parseResume(text, today) {
    const skills = extract(text);
    const spans = experienceSpans(text);
    const evidenced = new Set(Object.keys(skills).filter(s =>
      skills[s].some(o => spans.some(([a, b]) => a <= o && o < b))));
    const titles = resumeTitles(text);
    const loc = (text.match(/location\s*:\s*([^\n|(]+)/i) || [, ''])[1].trim().toLowerCase();
    return {
      text, skills, evidenced, titles, location: loc,
      years: experienceYears(text, today),
      seniority: titles.length ? seniorityOf(titles[0]) : 2,
      openToRemote: OPEN_REMOTE.test(text) || REMOTE.test(text.slice(0, 300)),
    };
  }

  function parseJob(title, description, location) {
    const required = new Set(), preferred = new Set();
    let mode = 'req', years = null;
    for (const line of (description || '').split(/\r?\n/)) {
      if (PREF_HEAD.test(line)) mode = 'pref';
      else if (REQ_HEAD.test(line)) mode = 'req';
      else if (ABOUT_HEAD.test(line)) mode = 'skip';
      if (mode === 'skip') continue;
      const found = Object.keys(extract(line));
      const target = (mode === 'pref' || /\b(nice to have|is a plus|a bonus|bonus points)\b/i.test(line)) ? preferred : required;
      found.forEach(s => target.add(s));
      if (mode === 'req' && years === null && /experience/i.test(line)) {
        const m = line.match(YEARS_REQ);
        if (m) years = parseFloat(m[1]);
      }
    }
    Object.keys(extract(title || '')).forEach(s => required.add(s));
    required.forEach(s => preferred.delete(s));
    const loc = (location || '').toLowerCase();
    return {
      title: title || '', text: description || '', required, preferred, yearsMin: years,
      seniority: seniorityOf(title || ''), location: loc,
      remote: REMOTE.test(loc) || REMOTE.test(description || ''),
    };
  }

  function titleTokens(t) {
    return new Set((t.toLowerCase().match(/[a-z+#./]+/g) || []).filter(x => !TITLE_STOP.has(x) && x.length > 1));
  }

  // ---- features ----------------------------------------------------------
  function skillCredit(skill, res) {
    const cr = D.model.credit;
    if (skill in res.skills) return res.evidenced.has(skill) ? [cr.evidenced, 'evidenced'] : [cr.listed, 'listed'];
    for (const o of (D.related[skill] || [])) if (o in res.skills) return [cr.related, 'related:' + o];
    return [0, 'missing'];
  }

  function coverage(skills, res, evidencedOnly) {
    if (!skills.size) return 0.5;
    let num = 0, den = 0;
    for (const s of skills) {
      const w = D.model.idf[s] ?? 1.0;
      num += w * (evidencedOnly ? (res.evidenced.has(s) ? 1 : 0) : skillCredit(s, res)[0]);
      den += w;
    }
    return num / den;
  }

  function catHist(skills) {
    const h = {};
    for (const s of skills) { const c = D.categories[s] || 'other'; h[c] = (h[c] || 0) + 1; }
    return h;
  }

  function cosine(a, b) {
    const ka = Object.keys(a), kb = Object.keys(b);
    if (!ka.length || !kb.length) return 0;
    let dot = 0;
    for (const k of ka) dot += a[k] * (b[k] || 0);
    const na = Math.sqrt(ka.reduce((t, k) => t + a[k] * a[k], 0));
    const nb = Math.sqrt(kb.reduce((t, k) => t + b[k] * b[k], 0));
    return dot / (na * nb);
  }

  const city = l => l.split(',')[0].trim();
  function locationOk(res, job) {
    if (job.remote) return (res.openToRemote || !res.location) ? 1.0 : 0.7;
    if (!job.location || !res.location) return 0.5;
    return city(job.location) === city(res.location) ? 1.0 : 0.0;
  }

  function coreFeatures(res, job) {
    const ymin = job.yearsMin;
    const short = ymin !== null ? Math.max(0, ymin - res.years) : 0;
    const over = ymin !== null ? Math.max(0, res.years - ymin - 5) : 0;
    const rt = new Set();
    res.titles.slice(0, 2).forEach(t => titleTokens(t).forEach(x => rt.add(x)));
    const jt = titleTokens(job.title);
    const inter = [...rt].filter(x => jt.has(x)).length;
    const uni = new Set([...rt, ...jt]).size;
    return {
      req_cov: coverage(job.required, res, false),
      pref_cov: coverage(job.preferred, res, false),
      req_evid: coverage(job.required, res, true),
      exp_short: Math.min(short, 5) / 5,
      exp_over: Math.min(over, 10) / 10,
      sen_under: Math.max(0, job.seniority - res.seniority) / 3,
      sen_over: Math.max(0, res.seniority - job.seniority) / 3,
      title_sim: rt.size && jt.size ? inter / uni : 0,
      domain_sim: cosine(catHist(new Set([...job.required, ...job.preferred])), catHist(Object.keys(res.skills))),
      loc_ok: locationOk(res, job),
    };
  }

  // [said when it helps, said when it hurts] -- same table as simran/model.py
  const READABLE = {
    req_cov: ['covers most required skills', 'missing several required skills'],
    pref_cov: ['has the nice-to-haves', 'few of the nice-to-haves'],
    req_evid: ['required skills show up in real work', 'required skills only in the skills list'],
    exp_short: ['meets the experience ask', 'short on years of experience'],
    exp_over: ['experience level fits', 'much more experienced than asked'],
    sen_under: ['seniority fits', 'role is more senior than current title'],
    sen_over: ['seniority fits', 'role is more junior than current title'],
    title_sim: ['past titles look like this role', 'past titles differ from this role'],
    domain_sim: ['skill profile fits the domain', 'skill profile is from a different domain'],
    loc_ok: ['location / remote works', "location doesn't line up"],
  };

  function score(res, job) {
    const M = D.model;
    const x = coreFeatures(res, job);
    let logit = M.intercept;
    const contrib = [];
    M.features.forEach((f, i) => {
      const c = ((x[f] - M.mean[i]) / M.scale[i]) * M.coef[i];
      logit += c;
      contrib.push([f, c, x[f]]);
    });
    contrib.sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
    return { score: 100 / (1 + Math.exp(-logit)), x, contrib };
  }

  // ---- glue for the existing results UI ------------------------------------
  function parseSalary(s) {
    if (!s) return [0, 0, 'USD'];
    const cur = /£/.test(s) ? 'GBP' : /€/.test(s) ? 'EUR' : /₹|inr|lpa/i.test(s) ? 'INR' : 'USD';
    const nums = (s.replace(/,/g, '').match(/\d+(?:\.\d+)?\s*[kK]?/g) || []).map(n =>
      /k/i.test(n) ? parseFloat(n) * 1000 : parseFloat(n)).filter(n => n > 0);
    if (/lpa|lakh/i.test(s)) return [nums[0] * 1e5 || 0, (nums[1] || nums[0]) * 1e5 || 0, 'INR'];
    return [nums[0] || 0, nums[1] || nums[0] || 0, cur];
  }

  function reasonText(r) {
    const pos = r.contrib.filter(c => c[1] > 0.15).slice(0, 2).map(c => READABLE[c[0]][0]);
    const neg = r.contrib.filter(c => c[1] < -0.15).slice(0, 2).map(c => READABLE[c[0]][1]);
    let s = '';
    if (pos.length) s += 'For: ' + pos.join(', ') + '. ';
    if (neg.length) s += 'Against: ' + neg.join(', ') + '.';
    return s.trim() || 'No single factor dominates this score.';
  }

  /* Same JSON shape the old LLM prompt returned, so results.js didn't need to change. */
  function analyze(resumeText, jobs, opts = {}) {
    if (!D) throw new Error('model-data.js is missing -- run scripts/export_web_assets.py');
    const res = parseResume(resumeText, opts.today);
    const matches = jobs.map(j => {
      const pj = parseJob(j.title, j.description, j.location);
      const r = score(res, pj);
      let s = r.score;
      // UI preferences. These sit on top of the model and are NOT part of the benchmark.
      if (opts.prefRemote && pj.remote) s += 5;
      if (opts.prefStrict && r.x.exp_over > 0) s -= 5;
      s = Math.max(0, Math.min(100, Math.round(s)));
      const all = new Set([...pj.required, ...pj.preferred]);
      const strengths = [], missing = [];
      let have = 0;
      for (const sk of all) {
        const [cr, how] = skillCredit(sk, res);
        if (cr > 0) {
          have += pj.required.has(sk) ? 1 : 0;
          strengths.push(how.startsWith('related:') ? `${sk} (via ${how.slice(8)})` : sk);
        } else if (pj.required.has(sk)) missing.push(sk);
      }
      const [smin, smax, cur] = parseSalary(j.salary);
      return {
        job_title: j.title, company: j.company || '', location: j.location || '',
        score: s, match_level: s >= 80 ? 'High' : s >= 50 ? 'Medium' : 'Low',
        salary_min: smin, salary_max: smax, currency: cur,
        missing_skills: missing, strengths,
        skill_match_pct: pj.required.size ? Math.round(100 * have / pj.required.size) : 0,
        reason: reasonText(r),
        _features: r.x,
      };
    });
    const kept = matches.filter(m => m.score >= (opts.minScore ?? 0)).sort((a, b) => b.score - a.score);
    const gaps = {};
    matches.forEach(m => m.missing_skills.forEach(g => { gaps[g] = (gaps[g] || 0) + 1; }));
    const topGaps = Object.entries(gaps).sort((a, b) => b[1] - a[1]).slice(0, 5).map(g => g[0]);
    const skills = Object.keys(res.skills);
    const scores = kept.map(m => m.score);
    const nameLine = (resumeText.split('\n').find(l => l.trim()) || '').split(/\s[—–|-]\s/)[0].trim();
    return {
      candidate_summary: {
        name: opts.blind ? '' : (nameLine.length < 40 ? nameLine : ''),
        skills, experience_years: res.years, roles: res.titles.slice(0, 3),
        location: res.location, education: '',
        top_skills: [...res.evidenced].slice(0, 5).concat(skills.filter(s => !res.evidenced.has(s))).slice(0, 5),
      },
      matched_jobs: kept,
      top_recommendations: kept.slice(0, 3).map(m => ({ job_title: m.job_title, company: m.company, score: m.score, reason: m.reason })),
      insights: {
        total_jobs_analyzed: jobs.length, total_matched: kept.length,
        high_matches: kept.filter(m => m.match_level === 'High').length,
        medium_matches: kept.filter(m => m.match_level === 'Medium').length,
        low_matches: kept.filter(m => m.match_level === 'Low').length,
        avg_score: scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0,
        top_missing_skills: topGaps,
        career_advice: topGaps.length
          ? `The gap that shows up most across these roles is ${topGaps.slice(0, 2).join(' and ')}. ` +
            `A small project that actually uses ${topGaps[0]} (and says so in a bullet, not just the skills list) would move the most scores.`
          : 'No recurring skill gaps across these roles -- focus on experience level and location fit.',
      },
    };
  }

  return { extract, parseResume, parseJob, coreFeatures, score, analyze, ready: !!D };
})();

if (typeof module !== 'undefined') module.exports = SimranEngine;
