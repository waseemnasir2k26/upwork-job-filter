"""Make a MASKED table for screen recordings: no client names, no titles, no URLs, no ids.

Keeps lane (generic), type, country, proposals band, budget, spend, age, score, verdict, kill reasons.
Usage: python mask.py jobs.json --now 2026-11-19T15:33:00Z --out OUTDIR
Writes OUTDIR/masked-table.md and OUTDIR/masked-jobs.json.
"""
import json
import os
import sys

from filter import load_jobs, parse_now, age_hours
from score import run

LANES = [
    ("CRM automation (GoHighLevel)", ["gohighlevel", "highlevel", "ghl"]),
    ("Shopify", ["shopify"]),
    ("WordPress", ["wordpress", "woocommerce", "elementor"]),
    ("n8n / workflow automation", ["n8n", "automation", "workflow", "zapier"]),
    ("AI agent / chatbot", ["chatbot", "agent", " ai ", "voice"]),
    ("SEO / content", ["seo", "content"]),
]


def lane(job):
    text = " " + (job.get("title", "") + " " + " ".join(job.get("skills") or [])).lower() + " "
    for name, words in LANES:
        if any(w in text for w in words):
            return name
    return "Other"


def mask(jobs, now):
    rows = run(jobs, now)
    out = []
    for n, (j, r) in enumerate(zip(jobs, rows), 1):
        c = j.get("client") or {}
        out.append({
            "ref": f"#{n:02d}",
            "lane": lane(j),
            "type": j.get("job_type"),
            "country": c.get("country") or "not stated",
            "payment": "verified" if c.get("verification_status") == "VERIFIED" else "not verified",
            "client_total_spent": c.get("total_spent") or "not stated",
            "client_hire_rate": "not provided" if c.get("hire_rate") is None else c["hire_rate"],
            "posted_hours_ago": round(age_hours(j, now)),
            "proposals": j.get("proposals_tier") or "not stated",
            "budget": j.get("budget") or "not stated",
            "score": r["score"]["total"],
            "verdict": "pass" if r["passed"] else r["eval"]["verdict"],
            "kill_reasons": r["eval"]["reasons"],
            "missing_fields": r["eval"]["missing"],
        })
    return out


def table(masked):
    h = "| # | Lane | Type | Country | Proposals | Budget | Score | Verdict | Why rejected |\n|---|---|---|---|---|---|---|---|---|\n"
    return h + "\n".join(
        f"| {m['ref']} | {m['lane']} | {m['type']} | {m['country']} | {m['proposals']} | "
        f"{m['budget']} | {m['score']} | {m['verdict']} | {'; '.join(m['kill_reasons']) or '-'} |"
        for m in masked) + "\n"


if __name__ == "__main__":
    a = sys.argv[1:]
    now = parse_now(a[a.index("--now") + 1]) if "--now" in a else parse_now(None)
    out = a[a.index("--out") + 1] if "--out" in a else "."
    os.makedirs(out, exist_ok=True)
    m = mask(load_jobs(a[0]), now)
    json.dump(m, open(os.path.join(out, "masked-jobs.json"), "w", encoding="utf-8"), indent=1)
    open(os.path.join(out, "masked-table.md"), "w", encoding="utf-8").write(table(m))
    print(table(m))
