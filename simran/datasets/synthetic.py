"""SIMRAN-Synth: a synthetic resume <-> job benchmark with graded relevance.

Why synthetic? There is no public resume/JD dataset with *graded, per-job*
relevance and ground-truth skills, and real resumes come with obvious privacy
problems. So the generator samples a latent candidate (role, years, true skills,
location) and a latent job, computes the label from those latent attributes,
and only then writes the text -- with the kinds of noise that break naive
matchers in practice:

  * skills written as aliases / odd casing ("k8s", "Postgres", "ReactJS")
  * out-of-vocabulary phrasings the taxonomy doesn't know ("kube", "pg")
  * implicit skills (true but never written down)
  * keyword stuffing (skills listed but not actually held)
  * negated mentions ("no hands-on experience with Kafka")
  * "our stack includes ..." boilerplate in JDs that isn't a requirement
  * JDs with no section headings at all

Labels come from the latent truth, never from the text, so a model only scores
well if it reads the text well. The label function *does* share the skill
taxonomy's notion of "related" skills with the features -- that's a real
limitation and it's discussed in docs/REPORT.md.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date

from ..taxonomy import load_taxonomy

TODAY = date(2026, 6, 1)   # fixed so experience years are reproducible

ROLES = {
    "backend": (["Backend Engineer", "Software Engineer, Backend", "Server-side Developer"],
                ["python", "java", "go", "postgresql", "rest api", "microservices", "docker", "redis",
                 "kafka", "aws", "sql", "distributed systems", "grpc"]),
    "frontend": (["Frontend Engineer", "UI Developer", "Front-End Developer"],
                 ["javascript", "typescript", "react", "css", "html", "redux", "webpack", "next.js",
                  "accessibility", "vue", "unit testing"]),
    "fullstack": (["Full Stack Engineer", "Full-Stack Developer", "Software Engineer, Product"],
                  ["javascript", "typescript", "react", "node.js", "postgresql", "rest api", "docker",
                   "express", "mongodb", "aws", "graphql"]),
    "data_science": (["Data Scientist", "Applied Scientist", "Decision Scientist"],
                     ["python", "sql", "pandas", "scikit-learn", "statistics", "a/b testing",
                      "machine learning", "xgboost", "tableau", "spark", "numpy"]),
    "ml_eng": (["Machine Learning Engineer", "ML Engineer", "AI Engineer"],
               ["python", "pytorch", "tensorflow", "deep learning", "mlops", "docker", "kubernetes",
                "nlp", "llm", "aws", "computer vision"]),
    "data_eng": (["Data Engineer", "Analytics Engineer", "Big Data Engineer"],
                 ["python", "sql", "spark", "airflow", "kafka", "etl", "snowflake", "dbt", "aws",
                  "bigquery", "hadoop"]),
    "devops": (["DevOps Engineer", "Site Reliability Engineer", "Platform Engineer"],
               ["kubernetes", "docker", "terraform", "aws", "ci/cd", "linux", "bash", "prometheus",
                "grafana", "helm", "ansible", "python", "go"]),
    "mobile": (["Mobile Engineer", "Android Developer", "iOS Developer"],
               ["kotlin", "swift", "android", "ios", "react native", "flutter", "rest api", "git",
                "unit testing"]),
    "security": (["Security Engineer", "Application Security Engineer", "Security Analyst"],
                 ["network security", "penetration testing", "siem", "owasp", "iam", "linux",
                  "python", "aws", "bash"]),
    "qa": (["QA Engineer", "SDET", "Test Automation Engineer"],
           ["selenium", "cypress", "unit testing", "python", "java", "ci/cd", "sql", "agile"]),
    "analyst": (["Data Analyst", "Business Intelligence Analyst", "Product Analyst"],
                ["sql", "excel", "tableau", "power bi", "python", "statistics", "a/b testing", "pandas"]),
}

# how much experience in role A transfers to a job in role B (symmetric)
_ADJ = {
    ("backend", "fullstack"): .6, ("frontend", "fullstack"): .6, ("data_science", "ml_eng"): .6,
    ("data_science", "analyst"): .6, ("data_eng", "backend"): .4, ("data_eng", "data_science"): .4,
    ("ml_eng", "data_eng"): .3, ("devops", "backend"): .4, ("security", "devops"): .4,
    ("mobile", "frontend"): .3, ("qa", "backend"): .2, ("qa", "frontend"): .2, ("data_eng", "analyst"): .3,
}


def adjacency(a: str, b: str) -> float:
    if a == b:
        return 1.0
    return _ADJ.get((a, b), _ADJ.get((b, a), 0.0))


GENERIC = ["git", "agile", "linux", "sql", "unit testing"]

# phrasings the taxonomy intentionally does NOT know about
OOV = {"kubernetes": "kube", "postgresql": "pg", "machine learning": "predictive modelling",
       "terraform": "HCL", "elasticsearch": "ELK", "ci/cd": "build pipelines",
       "statistics": "stats", "deep learning": "deep nets", "a/b testing": "split tests",
       "rest api": "HTTP APIs", "javascript": "vanilla JS", "aws": "the AWS console"}

CITIES = ["San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX", "Boston, MA",
          "Bangalore, India", "Hyderabad, India", "London, UK", "Berlin, Germany", "Toronto, Canada"]

# name pools used for the counterfactual fairness test. purely synthetic combos.
NAME_GROUPS = {
    "group_a": (["James", "Emily", "Michael", "Sarah", "David", "Laura"], ["Miller", "Anderson", "Clark", "Walker"]),
    "group_b": (["Lakisha", "Jamal", "Tyrone", "Aaliyah", "DeShawn", "Imani"], ["Washington", "Jefferson", "Banks", "Booker"]),
    "group_c": (["Priya", "Arjun", "Ananya", "Rahul", "Sneha", "Vikram"], ["Sharma", "Iyer", "Banerjee", "Reddy"]),
    "group_d": (["Wei", "Mei", "Jun", "Xiu", "Hao", "Lan"], ["Zhang", "Chen", "Wang", "Liu"]),
    "group_e": (["Carlos", "Sofia", "Diego", "Valentina", "Luis", "Camila"], ["Garcia", "Hernandez", "Lopez", "Ramirez"]),
}
# (neutral, same club with a group marker) -- the counterfactual only flips the marker
CLUB_PAIRS = [("Engineering Society", "Women in Engineering Society"),
              ("Engineers Society", "Black Engineers Society"),
              ("Coders Network", "Hispanic Coders Network"),
              ("Students Association", "Muslim Students Association")]
CLUBS_NEUTRAL = [a for a, _ in CLUB_PAIRS]
CLUBS_PROXY = [b for _, b in CLUB_PAIRS]

BULLET_TEMPLATES = [
    "Built {a} services using {b} and {c}",
    "Migrated legacy jobs to {a}, cutting run time by {n}%",
    "Owned the {a} integration end to end, including {b}",
    "Introduced {a} for the team and wrote internal docs on {b}",
    "Improved reliability of {a}-based pipelines; on-call for {b}",
    "Shipped features in {a} with {b}; reviewed PRs for {c}",
    "Prototyped a {a} + {b} proof of concept that went to production",
]
ABOUT = ["We're a Series B startup building tools for {x}.", "We help {x} teams move faster.",
         "Our customers range from two-person shops to the Fortune 500."]
DOMAINS = ["logistics", "healthcare billing", "developer tooling", "fintech", "e-commerce", "climate data"]


@dataclass
class Candidate:
    cid: int
    role: str
    years: float
    seniority: int
    skills: set[str]
    location: str
    open_remote: bool
    stuffer: bool
    name_group: str
    name: str
    text: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class Job:
    jid: int
    role: str
    title: str
    seniority: int
    years_min: int
    required: set[str]
    preferred: set[str]
    location: str
    remote: bool
    text: str = ""


class Generator:
    def __init__(self, seed: int = 13, stuff_rate: float = 0.15, oov_rate: float = 0.10,
                 implicit_rate: float = 0.08, proxy_club_rate: float = 0.0):
        self.rng = random.Random(seed)
        self.tax = load_taxonomy()
        self.stuff_rate, self.oov_rate, self.implicit_rate = stuff_rate, oov_rate, implicit_rate
        self.proxy_club_rate = proxy_club_rate

    # ---- helpers ----------------------------------------------------------
    def _pick_weighted(self, pool, k):
        # earlier items in a role's list are more "core" -> more likely
        w = [1.0 / (i + 2) ** 0.6 for i in range(len(pool))]
        out = []
        pool, w = list(pool), list(w)
        for _ in range(min(k, len(pool))):
            i = self.rng.choices(range(len(pool)), weights=w)[0]
            out.append(pool.pop(i))
            w.pop(i)
        return out

    def surface(self, skill: str) -> str:
        """How a skill gets written down."""
        r = self.rng.random()
        if skill in OOV and r < self.oov_rate:
            return OOV[skill]
        aliases = [a for a in self.tax.skills[skill]["aliases"]
                   if a not in self.tax.ambiguous and len(a) > 2]
        if aliases and r < 0.45:
            s = self.rng.choice(aliases)
        else:
            s = skill
        style = self.rng.random()
        if style < 0.5:
            return _pretty(s)
        if style < 0.8:
            return s
        return s.upper() if len(s) <= 5 else s.title()

    def _related_roles(self, role):
        return [r for r in ROLES if r != role and adjacency(role, r) > 0]

    # ---- candidates -------------------------------------------------------
    def candidate(self, cid: int, name_group: str | None = None) -> Candidate:
        rng = self.rng
        role = rng.choice(list(ROLES))
        years = round(min(16, max(0.3, rng.gammavariate(2.0, 2.4))), 1)
        sen = 1 if years < 2 else 2 if years < 5 else 3 if years < 9 else 4
        if rng.random() < 0.15:
            sen = max(1, min(4, sen + rng.choice([-1, 1])))
        core = ROLES[role][1]
        skills = set(self._pick_weighted(core, rng.randint(4, 9)))
        for r2 in rng.sample(self._related_roles(role), k=min(1, len(self._related_roles(role)))):
            skills |= set(rng.sample(ROLES[r2][1], rng.randint(0, 3)))
        skills |= set(rng.sample(GENERIC, rng.randint(1, 2)))
        group = name_group or rng.choice(list(NAME_GROUPS))
        first, last = NAME_GROUPS[group]
        name = f"{rng.choice(first)} {rng.choice(last)}"
        c = Candidate(cid, role, years, sen, skills, rng.choice(CITIES), rng.random() < 0.5,
                      rng.random() < self.stuff_rate, group, name)
        c.text = self._write_resume(c)
        return c

    def _write_resume(self, c: Candidate) -> str:
        rng = self.rng
        titles = ROLES[c.role][0]
        prefix = {1: "Junior ", 2: "", 3: "Senior ", 4: rng.choice(["Staff ", "Principal ", "Lead "])}
        # sorted(): set order depends on PYTHONHASHSEED, which broke reproducibility across runs
        written = [s for s in sorted(c.skills) if rng.random() > self.implicit_rate]
        evid = [s for s in written if rng.random() < 0.55]
        listed = [s for s in written if s not in evid or rng.random() < 0.7]
        if c.stuffer:
            fake = [s for s in rng.sample(list(self.tax.skills), 14) if s not in c.skills][:rng.randint(4, 8)]
            listed += fake
            c.extra["stuffed"] = fake
        rng.shuffle(listed)

        lines = [f"{c.name} — {prefix[c.seniority]}{rng.choice(titles)}",
                 f"Location: {c.location}" + (" (Open to Remote)" if c.open_remote else ""),
                 f"{c.name.lower().replace(' ', '.')}@mail.com | +1 415 555 {rng.randint(1000, 9999)}",
                 ""]
        if rng.random() < 0.6:
            lines += ["SUMMARY", f"{rng.choice(['Engineer', 'Practitioner', 'Developer'])} with a focus on "
                      f"{rng.choice(DOMAINS)}. Enjoy working close to the product.", ""]
        lines += ["SKILLS", ", ".join(self.surface(s) for s in listed), ""]

        # experience: split years into 1-3 stints ending today
        lines.append("EXPERIENCE")
        n_jobs = 1 if c.years < 2 else rng.randint(1, 3)
        cuts = sorted(rng.uniform(0, c.years) for _ in range(n_jobs - 1))
        bounds = [0.0] + cuts + [c.years]
        end_m = TODAY.year * 12 + TODAY.month - 1
        chunks = [evid[i::n_jobs] for i in range(n_jobs)]
        for k in range(n_jobs):
            start_m = end_m - round((bounds[n_jobs - k] - bounds[n_jobs - k - 1]) * 12)
            t = (prefix[c.seniority] if k == 0 else prefix[max(1, c.seniority - 1)]) + rng.choice(titles)
            end_s = "Present" if k == 0 else _fmt(end_m)
            lines.append(f"{t} — {rng.choice(['Acme', 'Northwind', 'Globex', 'Initech', 'Umbrella', 'Hooli'])} "
                         f"{rng.choice(['Labs', 'Inc.', 'Systems', 'Group'])} ({_fmt(start_m)} – {end_s})")
            mine = chunks[k]
            while mine:
                take, mine = mine[:3], mine[3:]
                take = [self.surface(s) for s in take] + ["the platform"] * 3
                tpl = rng.choice(BULLET_TEMPLATES)
                lines.append("- " + tpl.format(a=take[0], b=take[1], c=take[2], n=rng.randint(10, 60)))
            if rng.random() < 0.2:
                other = rng.choice([s for s in self.tax.skills if s not in c.skills])
                lines.append(f"- Partnered with the {_pretty(other)} team on cross-org planning")  # distractor
            end_m = start_m - rng.randint(0, 3)
        if rng.random() < 0.2:
            other = rng.choice([s for s in self.tax.skills if s not in c.skills])
            lines.append(f"- Read up on {_pretty(other)} but no hands-on experience with {_pretty(other)} yet")
        lines += ["", "EDUCATION", f"B.{rng.choice(['Tech', 'S.', 'E.'])} in "
                  f"{rng.choice(['Computer Science', 'Information Technology', 'Electrical Engineering', 'Mathematics'])}"]
        club = rng.choice(CLUBS_PROXY) if rng.random() < self.proxy_club_rate else rng.choice(CLUBS_NEUTRAL)
        c.extra["club"] = club
        lines += ["", "ACTIVITIES", f"Member, {club}"]
        return "\n".join(lines)

    # ---- jobs ---------------------------------------------------------------
    def job(self, jid: int, role: str | None = None) -> Job:
        rng = self.rng
        role = role or rng.choice(list(ROLES))
        sen = rng.choices([1, 2, 3, 4], weights=[2, 4, 3, 1])[0]
        years = {1: rng.choice([0, 1]), 2: rng.choice([2, 3]), 3: rng.choice([5, 6]), 4: rng.choice([8, 10])}[sen]
        core = ROLES[role][1]
        req = set(self._pick_weighted(core, rng.randint(3, 6)))
        rest = [s for s in core if s not in req]
        pref = set(rng.sample(rest, min(len(rest), rng.randint(1, 3))))
        remote = rng.random() < 0.35
        loc = "Remote" if remote else rng.choice(CITIES)
        title = {1: "Junior ", 2: "", 3: "Senior ", 4: "Staff "}[sen] + rng.choice(ROLES[role][0])
        j = Job(jid, role, title, sen, years, req, pref, loc, remote)
        j.text = self._write_job(j)
        return j

    def _write_job(self, j: Job) -> str:
        rng = self.rng
        about = rng.choice(ABOUT).format(x=rng.choice(DOMAINS))
        stack = rng.sample(list(self.tax.skills), 3)
        yrs = f"{j.years_min}+ years of experience" if j.years_min else "Some professional experience"
        req = [self.surface(s) for s in sorted(sorted(j.required), key=lambda _: rng.random())]
        pref = [self.surface(s) for s in sorted(j.preferred)]
        if rng.random() < 0.2:
            # heading-less prose posting
            return (f"{about} You'll work mostly with {', '.join(req[:-1])} and {req[-1]}. "
                    f"{yrs} in a similar role. Experience with {', '.join(pref)} is a plus. "
                    + ("Fully remote." if j.remote else f"Based in {j.location}."))
        lines = ["About us", about, f"Our stack includes {', '.join(_pretty(s) for s in stack)}.", "",
                 "Requirements"]
        lines.append(f"- {yrs}")
        while req:
            k = rng.randint(1, 3)
            chunk, req = req[:k], req[k:]
            lines.append("- Hands-on with " + " and ".join(chunk))
        lines += ["", "Nice to have"] + [f"- {p}" for p in pref]
        if j.remote:
            lines += ["", "This role is remote."]
        return "\n".join(lines)


def _pretty(s: str) -> str:
    special = {"postgresql": "PostgreSQL", "javascript": "JavaScript", "typescript": "TypeScript",
               "aws": "AWS", "gcp": "GCP", "sql": "SQL", "ci/cd": "CI/CD", "nlp": "NLP", "llm": "LLMs",
               "mlops": "MLOps", "iam": "IAM", "siem": "SIEM", "owasp": "OWASP", "etl": "ETL",
               "ios": "iOS", "node.js": "Node.js", "next.js": "Next.js", "rest api": "REST APIs",
               "graphql": "GraphQL", "mongodb": "MongoDB", "pytorch": "PyTorch", "tensorflow": "TensorFlow"}
    return special.get(s, s if any(ch in s for ch in "+#./") else s.title() if " " in s else s.capitalize())


def _fmt(m: int) -> str:
    return f"{'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()[m % 12]} {m // 12}"


# ---- labels -----------------------------------------------------------------

def relevance(c: Candidate, j: Job, rng: random.Random | None = None, noise: float = 0.05) -> int:
    """Graded label 0..3 from latent attributes only."""
    tax = load_taxonomy()

    def held(s):
        if s in c.skills:
            return 1.0
        return 0.5 if any(o in c.skills for o in tax.related.get(s, ())) else 0.0

    req = sum(held(s) for s in j.required) / len(j.required)
    pref = sum(held(s) for s in j.preferred) / len(j.preferred) if j.preferred else 0.5
    short = max(0.0, j.years_min - c.years)
    f_exp = math.exp(-short / 1.5)
    if c.years > j.years_min + 8:
        f_exp *= 0.8
    adj = adjacency(c.role, j.role)
    if j.remote:
        loc = 1.0 if c.open_remote else 0.6
    else:
        loc = 1.0 if j.location == c.location else (0.5 if c.open_remote else 0.2)
    u = 0.45 * req + 0.10 * pref + 0.20 * f_exp + 0.15 * adj + 0.10 * loc
    if rng is not None:
        u += rng.gauss(0, noise)
    label = 3 if u >= 0.80 else 2 if u >= 0.65 else 1 if u >= 0.45 else 0
    if req < 0.5 or short > 3:
        label = min(label, 1)     # hard requirements a recruiter wouldn't waive
    if loc <= 0.2:
        label = min(label, 2)
    return label


@dataclass
class Benchmark:
    candidates: list[Candidate]
    jobs: list[Job]
    slates: list[list[int]]         # per candidate, indices into jobs
    labels: list[list[int]]


def build_benchmark(n_candidates: int = 600, n_jobs: int = 900, slate: int = 30, seed: int = 13,
                    **gen_kw) -> Benchmark:
    g = Generator(seed=seed, **gen_kw)
    jobs = [g.job(i) for i in range(n_jobs)]
    by_role: dict[str, list[int]] = {}
    for i, j in enumerate(jobs):
        by_role.setdefault(j.role, []).append(i)
    cands, slates, labels = [], [], []
    lrng = random.Random(seed + 1)
    for cid in range(n_candidates):
        c = g.candidate(cid)
        same = g.rng.sample(by_role[c.role], 10)
        adj_roles = g._related_roles(c.role)
        near = [i for r in adj_roles for i in by_role[r]]
        near = g.rng.sample(near, min(8, len(near)))
        pool = [i for i in range(n_jobs) if i not in set(same) | set(near)]
        rest = g.rng.sample(pool, slate - len(same) - len(near))
        s = same + near + rest
        g.rng.shuffle(s)
        cands.append(c)
        slates.append(s)
        labels.append([relevance(c, jobs[i], lrng) for i in s])
    return Benchmark(cands, jobs, slates, labels)
