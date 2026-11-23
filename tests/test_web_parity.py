"""The browser engine (web/js/engine.js) must give the same scores as python."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from simran.datasets.synthetic import TODAY, build_benchmark
from simran.model import CoreModel
from simran.parsing import parse_job, parse_resume

ROOT = Path(__file__).resolve().parents[1]
RUNNER = """
const fs=require('fs'),vm=require('vm');
const ctx={console,module:{}};vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1]+'/web/js/model-data.js','utf8')+
  fs.readFileSync(process.argv[1]+'/web/js/engine.js','utf8')+';this.E=SimranEngine;',ctx);
const inp=JSON.parse(fs.readFileSync(0,'utf8'));
const today=new Date(inp.today[0],inp.today[1]-1,inp.today[2]);
console.log(JSON.stringify(inp.cases.map(c=>{const r=ctx.E.parseResume(c.resume,today);
  return c.jobs.map(j=>ctx.E.score(r,ctx.E.parseJob(j.title,j.description,j.location)).score)})));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_matches_python():
    b = build_benchmark(25, 400, seed=31)
    cases = [{"resume": c.text, "jobs": [{"title": b.jobs[i].title, "description": b.jobs[i].text,
                                          "location": b.jobs[i].location} for i in s[:8]]}
             for c, s in zip(b.candidates, b.slates)]
    payload = json.dumps({"today": [TODAY.year, TODAY.month, TODAY.day], "cases": cases})
    out = subprocess.run(["node", "-e", RUNNER, str(ROOT)], input=payload, capture_output=True, text=True, check=True)
    js = json.loads(out.stdout)
    m = CoreModel.load()
    for c, scores in zip(cases, js):
        r = parse_resume(c["resume"], today=TODAY)
        for j, s_js in zip(c["jobs"], scores):
            assert abs(m.score(r, parse_job(j["title"], j["description"], j["location"])) - s_js) < 1e-6
