"""100-point score: hire rate 25, budget 25, fit 25, competition 15, freshness 10. Pass at 65.

A job passes only if filter.py did not reject it AND it scores >= 65.
Scores are computed for rejected jobs too (for ranking and 'why not'), never used to rescue them.
"""
import json
import re
import sys

from filter import evaluate, load_jobs, parse_budget, parse_now, proposals_upper, age_hours, money

PASS = 65
LANES = {  # 9 points per matched lane, capped at 25
    "automation": ["n8n", "make.com", "zapier", "automation", "workflow", "webhook"],
    "ai": ["ai", "gpt", "openai", "llm", "chatbot", "agent", "claude"],
    "crm": ["crm", "highlevel", "gohighlevel", "hubspot", "pipedrive"],
    "web": ["wordpress", "woocommerce", "shopify", "elementor", "next.js"],
    "marketing": ["seo", "aeo", "whatsapp", "funnel", "lead"],
    "data": ["api", "integration", "postgres", "python", "sheets"],
}


def _has(text, word):
    return re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", text) is not None


def fit_lanes(job):
    text = " ".join([job.get("title", "")] + list(job.get("skills") or [])).lower()
    return [k for k, words in LANES.items() if any(_has(text, w) for w in words)]


def score(job, now):
    c = {}
    why = {}
    client = job.get("client") or {}
    hr = client.get("hire_rate")
    if hr is not None:
        c["hire_rate"] = 25 if hr >= 80 else 20 if hr >= 60 else 12
        why["hire_rate"] = f"stated {hr}%"
    else:  # not in the search payload: proxy from total spend, half credit at most
        sp = money(client.get("total_spent"))
        c["hire_rate"] = 0 if sp is None else 12 if sp >= 10000 else 8 if sp >= 2000 else 5 if sp >= 500 else 0
        why["hire_rate"] = "hire rate not stated; spend proxy (max 12)"
    kind, lo, hi = parse_budget(job)
    if kind == "fixed":
        c["budget"] = 25 if hi >= 2000 else 20 if hi >= 1000 else 15 if hi >= 500 else 9 if hi >= 200 else 0
    elif kind == "hourly":
        c["budget"] = 25 if hi >= 75 else 22 if hi >= 60 else 18 if hi >= 45 else 13 if hi >= 35 else 8 if hi >= 25 else 0
    else:
        c["budget"] = 10
    why["budget"] = "no budget stated, mid score" if kind is None else f"{kind} up to {hi:g}"
    lanes = fit_lanes(job)
    c["fit"] = min(25, 9 * len(lanes))
    why["fit"] = ", ".join(lanes) or "no lane match"
    up = proposals_upper(job)
    c["competition"] = 6 if up is None else 15 if up <= 5 else 11 if up <= 10 else 6 if up <= 20 else 0
    why["competition"] = "proposals unknown" if up is None else f"{up} (upper bound of band)"
    age = age_hours(job, now)
    c["freshness"] = 0 if age is None else 10 if age <= 48 else 5 if age <= 96 else 0
    why["freshness"] = "unknown" if age is None else f"{age:.0f}h old"
    return {"components": c, "total": sum(c.values()), "why": why}


def run(jobs, now):
    rows = []
    for j in jobs:
        ev, sc = evaluate(j, now), score(j, now)
        passed = ev["verdict"] == "survive" and sc["total"] >= PASS
        rows.append({"id": j.get("id"), "title": j.get("title"), "eval": ev, "score": sc, "passed": passed})
    return rows


if __name__ == "__main__":
    a = sys.argv[1:]
    now = parse_now(a[a.index("--now") + 1]) if "--now" in a else parse_now(None)
    json.dump(run(load_jobs(a[0]), now), sys.stdout, indent=2)
