from datetime import date

from simran.parsing import parse_job, parse_resume, total_experience_years

RESUME = """Asha Rao — Senior Backend Engineer
Location: Pune, India (open to remote)

SKILLS
Python, Kafka, Docker, MySQL

EXPERIENCE
Senior Backend Engineer — Foo Ltd (Mar 2022 – Present)
- Built event pipelines on Kafka and Python
Backend Developer — Bar Inc (Jan 2019 – Feb 2022)
- Kept the Docker images small

EDUCATION
B.Tech, 2018
"""


def test_experience_merges_ranges():
    # Jan 2019 -> Jun 2024 continuous = 5.4 years
    assert total_experience_years(RESUME, today=date(2024, 6, 1)) == 5.4


def test_overlapping_ranges_not_double_counted():
    t = "A (2018 - 2020)\nB (2019 - 2020)"
    assert total_experience_years(t, today=date(2024, 1, 1)) == 3.0


def test_stated_years_fallback():
    assert total_experience_years("I have 7+ years of backend experience") == 7.0


def test_resume_fields():
    r = parse_resume(RESUME, today=date(2024, 6, 1))
    assert r.seniority == 3
    assert r.open_to_remote
    assert r.location.startswith("pune")
    assert {"kafka", "python", "docker"} <= r.evidenced
    assert "mysql" in r.skills and "mysql" not in r.evidenced


def test_job_sections():
    jd = """About us
Our stack includes Elixir and Rust.

Requirements
- 4+ years of experience with Python
- PostgreSQL, Redis

Nice to have
- Kubernetes
"""
    j = parse_job("Senior Backend Engineer", jd, "Remote")
    assert j.required == {"python", "postgresql", "redis"}
    assert j.preferred == {"kubernetes"}
    assert j.years_min == 4 and j.remote and j.seniority == 3
    assert "rust" not in j.required   # boilerplate stack line skipped
