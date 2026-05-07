# S.I.M.R.A.N. v2.0
### Smart Intelligent Model for Recruitment and Analysis Network

> An advanced AI-powered job hunting assistant that matches your resume against job listings with realistic scoring, salary estimation, skill gap analysis, history tracking, and export — powered by Claude AI.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![AI Model](https://img.shields.io/badge/AI-Claude%20Sonnet%204-blue)](https://anthropic.com)
[![Version](https://img.shields.io/badge/version-2.0.0-orange)](https://github.com/Aranya2801/S.I.M.R.A.N.)

---

## 🚀 Live Demo

> Open `index.html` directly in your browser — **no server, no install needed.**
>
> Or deploy on **GitHub Pages** (Settings → Pages → main branch → root) for a free public URL.

---

## ✨ What's New in v2.0

| Feature | v1 | v2 |
|---|---|---|
| Multi-page layout (Dashboard, Analyze, History, Settings) | ❌ | ✅ |
| Analysis history (localStorage) | ❌ | ✅ |
| Dashboard with live stats | ❌ | ✅ |
| Score distribution chart | ❌ | ✅ |
| Filter + sort results | ❌ | ✅ |
| Skill match % bar per job | ❌ | ✅ |
| Export JSON / Copy report | ❌ | ✅ |
| Analysis options (min score, strict mode, language) | ❌ | ✅ |
| Career insights from AI | ❌ | ✅ |
| Top missing skills summary | ❌ | ✅ |
| Keyboard shortcuts | ❌ | ✅ |
| Responsive sidebar navigation | ❌ | ✅ |
| Loading progress bar | ❌ | ✅ |
| Modular multi-file architecture | ❌ | ✅ |

---

## 📁 Project Structure

```
S.I.M.R.A.N./
├── index.html              ← Main HTML (sidebar, pages, structure)
├── css/
│   ├── main.css            ← Core layout, variables, sidebar
│   ├── components.css      ← Buttons, cards, forms, inputs
│   ├── results.css         ← Loading, match cards, charts, export
│   └── animations.css      ← All keyframes and transitions
├── js/
│   ├── data.js             ← Sample data, history storage, AI system prompt
│   ├── ui.js               ← Navigation, job cards, toast, dashboard stats
│   ├── analysis.js         ← Anthropic API call, loading state
│   ├── results.js          ← Rendering results, filter/sort, export
│   └── app.js              ← App initializer and event bindings
├── assets/
│   └── favicon.svg         ← App icon
└── README.md
```

---

## 🎯 Features

### AI Match Scoring (0–100)
| Factor | Weight | Description |
|---|---|---|
| Skills Match | **40%** | Overlap between candidate skills and job requirements |
| Experience | **30%** | Years of experience vs. job requirement |
| Role Relevance | **20%** | How closely roles match the job domain |
| Location | **10%** | Geographic match or remote flexibility |

### Match Levels
- 🟢 **High** (≥ 80) — Strong candidate, apply with confidence
- 🟡 **Medium** (50–79) — Good fit, pair with a strong cover letter
- ⚪ **Low** (< 50) — Skill gap exists, consider upskilling first

### Analysis Options
- **Minimum Score Threshold** — filter out weak matches
- **Remote Boost** — add bonus to remote-friendly roles
- **Strict Mode** — penalize overqualification
- **Salary Estimation** — AI estimates missing salaries
- **Output Language** — results in English, Spanish, French, German, or Hindi

### Results
- Ranked match cards with score, salary, skill bars, strengths, gaps
- Score distribution chart
- Top 3 recommendations with reasoning
- Career advice from AI
- Export as JSON or copy as plain-text report

---

## 🛠 Setup

### Run Locally
```bash
git clone https://github.com/Aranya2801/S.I.M.R.A.N.-Smart-Intelligent-Model-for-Recruitment-and-Analysis-Network.git
cd S.I.M.R.A.N.
# Just open index.html in your browser
open index.html
```

### Deploy on GitHub Pages
1. Push all files to your repository
2. Go to **Settings → Pages**
3. Source: `Deploy from a branch` → `main` → `/ (root)`
4. Your app is live at `https://<username>.github.io/<repo-name>/`

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl/Cmd + Enter` | Advance to next step |
| `Escape` | Go back to previous step |

---

## 📋 Input Tips

**Resume:**
- Include all skills explicitly (don't assume AI knows your stack)
- Add dates so experience years can be calculated
- Mention your location and remote preferences
- Include certifications and notable projects

**Job Listings:**
- Paste the full job description for best results
- Adding salary info improves salary scoring accuracy
- Location field helps with geographic matching

---

## 🔒 Privacy

- **No data is stored on any server.** Your resume and job data are sent only to the Anthropic API for processing.
- Analysis history is stored locally in your browser's `localStorage` and never leaves your device.
- You can clear all history from the Settings page.

---

## ⚙️ Powered By

| Technology | Role |
|---|---|
| **Claude Sonnet 4** (`claude-sonnet-4-20250514`) | AI matching engine |
| **Vanilla HTML/CSS/JS** | Frontend — zero frameworks |
| **Google Fonts** (Space Mono, Syne, DM Sans) | Typography |
| **localStorage** | History persistence |

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

*Built with ❤️ by [Aranya2801](https://github.com/Aranya2801)*
