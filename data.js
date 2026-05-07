/* ============================================
   S.I.M.R.A.N. v2.0 — data.js
   Sample data, constants, storage helpers
============================================ */

'use strict';

// ─── SAMPLE RESUME ────────────────────────────────────────────────
const SAMPLE_RESUME = `John Smith — Software Engineer | 4 Years Experience
Location: San Francisco, CA (Open to Remote)
Email: john.smith@email.com | GitHub: github.com/johnsmith

SKILLS
Languages: Python, JavaScript, TypeScript, SQL, Java (basic), Bash
Frameworks: React, Node.js, FastAPI, Django, Express, Next.js
Databases: PostgreSQL, MongoDB, Redis, Elasticsearch
Cloud & DevOps: AWS (EC2, S3, Lambda, RDS), Docker, Kubernetes, Terraform, GitHub Actions
Tools: Git, Jira, Figma, Postman, Datadog, PagerDuty

PROFESSIONAL EXPERIENCE

Software Engineer II — TechCorp Inc. (Jan 2022 – Present)
San Francisco, CA
- Architected and maintained RESTful APIs with Python/FastAPI serving 2M+ requests/day
- Built React dashboards used by 500+ internal stakeholders for analytics and reporting
- Reduced PostgreSQL query latency by 40% via indexing, query optimization, and connection pooling
- Led migration of 3 monolithic services to Kubernetes-based microservices on AWS
- Mentored 2 junior engineers; led weekly code review sessions
- Integrated Elasticsearch for full-text search across product catalog (8M+ records)

Junior Software Developer — StartupXYZ (Jun 2020 – Dec 2021)
Remote
- Developed responsive web UIs with React and TypeScript for B2C SaaS product
- Integrated Stripe Billing, Twilio SMS, and SendGrid Email APIs
- Wrote 85% test coverage using Jest and Pytest
- Maintained CI/CD pipelines with GitHub Actions deploying to AWS ECS

EDUCATION
B.S. Computer Science — UC Berkeley (2020) | GPA: 3.72 | Dean's List

PROJECTS
- simran-cli: Open-source API testing CLI in Python (700+ GitHub stars, 1,400+ npm downloads/week)
- CodeCollab: Real-time collaborative code editor (WebSockets + React + Node.js, 2,000+ users)
- Portfolio: johnsmith.dev — built with Next.js and deployed on Vercel

CERTIFICATIONS
- AWS Certified Developer – Associate (2023)
- Google Cloud Associate Cloud Engineer (2022)`;

// ─── SAMPLE JOBS ──────────────────────────────────────────────────
const SAMPLE_JOBS = [
  {
    title: "Senior Full Stack Engineer",
    company: "Stripe",
    location: "San Francisco, CA",
    description: `We are looking for a Senior Full Stack Engineer to join our Payments Infrastructure team.

Requirements:
- 5+ years of software engineering experience
- Strong proficiency in Python and React/TypeScript
- Experience with PostgreSQL, Redis, and distributed systems
- AWS infrastructure (EC2, Lambda, RDS, S3)
- Microservices architecture and Kubernetes
- REST API design and GraphQL

Nice to have:
- Experience with high-throughput payment systems
- Knowledge of PCI-DSS compliance
- Terraform for infrastructure as code

We build the financial infrastructure that powers the internet. Remote OK.`,
    salary: "$160,000 – $210,000"
  },
  {
    title: "Backend Engineer",
    company: "Airbnb",
    location: "San Francisco, CA",
    description: `Join Airbnb's Core Booking team to build systems that handle millions of reservations globally.

Requirements:
- 3–6 years of backend engineering experience
- Proficiency in Python or Java (we use both)
- Strong REST API design skills
- Experience with microservices and event-driven architecture
- Kubernetes, Docker, AWS
- SQL and NoSQL databases

Nice to have:
- Experience with distributed systems at scale
- Kafka or RabbitMQ messaging
- gRPC or GraphQL`,
    salary: "$140,000 – $185,000"
  },
  {
    title: "Frontend Engineer",
    company: "Figma",
    location: "Remote (US)",
    description: `Figma is looking for a Frontend Engineer to work on our design editor and collaboration tools.

Requirements:
- 3+ years of frontend engineering experience
- Deep React and TypeScript expertise
- Performance optimization (profiling, rendering, bundle size)
- Strong CSS and browser APIs knowledge

Nice to have:
- WebGL, Canvas, or SVG rendering
- Experience with collaborative/real-time applications (WebSockets, CRDTs)
- Accessibility (WCAG 2.1 AA)
- Design systems experience`,
    salary: "$130,000 – $170,000"
  },
  {
    title: "Data Scientist",
    company: "Meta",
    location: "Menlo Park, CA",
    description: `Meta is hiring a Data Scientist for the Ads Ranking team.

Requirements:
- Advanced degree (MS or PhD) in Statistics, CS, or related field
- Expertise in Python (pandas, scikit-learn, PyTorch or TensorFlow)
- Large-scale data processing (Spark, Hive, Presto)
- Causal inference and experimentation (A/B testing, uplift modeling)
- SQL proficiency

Nice to have:
- NLP or computer vision experience
- Experience with recommendation systems or ads ranking
- Publications in ML/AI conferences`,
    salary: "$165,000 – $230,000"
  },
  {
    title: "DevOps / Platform Engineer",
    company: "Dropbox",
    location: "San Francisco, CA",
    description: `Dropbox Platform team is growing! We need a DevOps engineer to build our internal developer platform.

Requirements:
- 3+ years DevOps or SRE experience
- Kubernetes (CKA certification preferred), Docker, Helm
- AWS or GCP — deep infrastructure knowledge
- Terraform and infrastructure as code
- CI/CD pipeline design (GitHub Actions, ArgoCD, Jenkins)
- Python or Go scripting

Nice to have:
- Prometheus, Grafana, Datadog monitoring
- Service mesh (Istio)
- Security hardening and compliance`,
    salary: "$130,000 – $165,000"
  },
  {
    title: "Full Stack Engineer",
    company: "Notion",
    location: "Remote",
    description: `Notion is hiring a Full Stack Engineer to work on our core editor and database product.

Requirements:
- 3+ years full-stack experience
- React, TypeScript, Node.js
- PostgreSQL and Redis
- REST APIs and good API design sense
- Collaborative, async-first work style

Nice to have:
- Experience with rich text editors (ProseMirror, Slate.js)
- Real-time collaboration features
- Performance optimization for large data sets`,
    salary: "$145,000 – $175,000"
  },
  {
    title: "Software Engineer, Infrastructure",
    company: "OpenAI",
    location: "San Francisco, CA",
    description: `OpenAI is looking for an Infrastructure Engineer to scale our training and inference systems.

Requirements:
- 4+ years of software engineering experience
- Strong Python and Bash scripting
- Kubernetes, Docker at scale
- AWS or Azure infrastructure
- Distributed systems fundamentals

Nice to have:
- GPU cluster management
- ML training pipeline experience
- gRPC, Protobuf`,
    salary: "$180,000 – $250,000"
  }
];

// ─── HISTORY STORAGE ─────────────────────────────────────────────
const STORAGE_KEY = 'simran_history_v2';

function saveToHistory(entry) {
  try {
    const existing = loadHistory();
    existing.unshift({ ...entry, id: Date.now(), timestamp: new Date().toISOString() });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(existing.slice(0, 20)));
  } catch(e) { /* localStorage not available in some contexts */ }
}

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch { return []; }
}

function clearHistory() {
  try {
    localStorage.removeItem(STORAGE_KEY);
    updateDashboardStats();
    renderHistory();
  } catch {}
}

// ─── AI SYSTEM PROMPT ─────────────────────────────────────────────
function buildSystemPrompt(options = {}) {
  const { minScore = 40, prefRemote = true, prefSalary = true, prefStrict = false, lang = 'English' } = options;

  return `You are S.I.M.R.A.N. v2.0 — Smart Intelligent Model for Recruitment and Analysis Network.
You are a highly accurate AI recruiting engine. Analyze a candidate's resume against job listings.

RESPONSE LANGUAGE: ${lang}
MINIMUM SCORE THRESHOLD: ${minScore} (exclude jobs below this score)
STRICT MODE: ${prefStrict ? 'ON — penalize overqualification (candidate >> job level)' : 'OFF'}
REMOTE BOOST: ${prefRemote ? 'ON — give +5 bonus to remote or hybrid jobs' : 'OFF'}
SALARY ESTIMATION: ${prefSalary ? 'ON — estimate missing salaries based on role, location, experience' : 'OFF — leave 0 if missing'}

SCORING WEIGHTS (total 100):
- Skills Match:    40% — exact skill overlap, tools, languages, frameworks
- Experience:      30% — years of exp vs. job requirement (± penalize gaps)
- Role Relevance:  20% — how closely candidate's roles match the job domain
- Location:        10% — geographic match, remote flexibility

MATCH LEVELS:
- score >= 80 → "High"
- score 50–79 → "Medium"
- score < 50  → "Low"

FILTERING RULES:
- Exclude jobs where skill overlap < 40%
- Exclude jobs below the minimum score threshold (${minScore})
- Missing core skills = heavy penalty (–10 to –20 pts each)
- Exact skill match = strong boost (+5 per exact match)
- Overqualified (>3 yrs above requirement) = –5 if strict mode ON

SALARY RULES:
- All salary values must be integers (yearly, no commas)
- If salary is provided, parse and use it
- If missing and estimation is ON, estimate based on role, location, experience, seniority
- Currency: use "USD" unless location suggests otherwise

OUTPUT: Return ONLY valid JSON. No markdown fences. No explanatory text. Nothing outside the JSON object.

JSON SCHEMA (return exactly this structure):
{
  "candidate_summary": {
    "name": "string or empty",
    "skills": ["string"],
    "experience_years": number,
    "roles": ["string"],
    "location": "string",
    "education": "string",
    "top_skills": ["string (top 5)"]
  },
  "matched_jobs": [
    {
      "job_title": "string",
      "company": "string",
      "location": "string",
      "score": number,
      "match_level": "High|Medium|Low",
      "salary_min": number,
      "salary_max": number,
      "currency": "string",
      "missing_skills": ["string"],
      "strengths": ["string"],
      "skill_match_pct": number,
      "reason": "string (2–3 sentences, precise)"
    }
  ],
  "top_recommendations": [
    {
      "job_title": "string",
      "company": "string",
      "score": number,
      "reason": "string"
    }
  ],
  "insights": {
    "total_jobs_analyzed": number,
    "total_matched": number,
    "high_matches": number,
    "medium_matches": number,
    "low_matches": number,
    "avg_score": number,
    "top_missing_skills": ["string"],
    "career_advice": "string (1–2 sentences)"
  }
}

Rules:
- Rank matched_jobs by score DESC
- Include at most 15 matched_jobs
- top_recommendations = top 3 picks only
- Be realistic and strict — do NOT inflate scores
- skill_match_pct = 0–100 (percentage of required skills candidate has)`;
}
