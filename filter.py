"""Kill rules for Upwork jobs. Pure functions, no network, no scraping.

Input: JSON saved from the official Upwork connector's job search (a list of jobs,
a list of searches each with a "jobs" list, or {"jobs": {id: job}}).
A rule only fires on a STATED value. Missing data is reported, never guessed.
"""
import json
import re
import sys
from datetime import datetime, timezone

ELIGIBLE = {"US", "CA", "AU", "GB", "DE", "SG"}
_COUNTRY = {
    "US": "US", "USA": "US", "UNITED STATES": "US", "UNITED STATES OF AMERICA": "US",
    "CA": "CA", "CAN": "CA", "CANADA": "CA",
    "AU": "AU", "AUS": "AU", "AUSTRALIA": "AU",
    "UK": "GB", "GB": "GB", "GBR": "GB", "UNITED KINGDOM": "GB", "GREAT BRITAIN": "GB",
    "DE": "DE", "DEU": "DE", "GERMANY": "DE",
    "SG": "SG", "SGP": "SG", "SINGAPORE": "SG",
}
MIN_HIRE_RATE, MIN_SPEND, MAX_AGE_H, MAX_PROPOSALS = 40, 500, 96, 20
MIN_FIXED, MIN_HOURLY_MAX = 200, 25


def money(v):
    """'$1,219.65' -> 1219.65 ; None/unparseable -> None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"\d[\d,]*\.?\d*", str(v))
    return float(m.group(0).replace(",", "")) if m else None


def parse_budget(job):
    """-> (kind, low, high) with kind in fixed/hourly/None. Only stated budgets count."""
    b = job.get("budget")
    if not b:
        return None, None, None
    nums = [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.?\d*", str(b))]
    if not nums:
        return None, None, None
    hourly = job.get("job_type") == "hourly" or "/hr" in str(b)
    return ("hourly" if hourly else "fixed"), min(nums), max(nums)


def proposals_upper(job):
    """Upper bound of the proposals count or tier ('Fewer than 5','5 to 10','50+'). None if absent."""
    if isinstance(job.get("proposals"), (int, float)):
        return int(job["proposals"])
    t = job.get("proposals_tier")
    if not t:
        return None
    t = str(t).strip()
    m = re.match(r"(?i)(?:fewer|less) than (\d+)$", t)
    if m:
        return int(m.group(1)) - 1
    m = re.match(r"(\d+)\s*(?:to|-)\s*(\d+)$", t)
    if m:
        return int(m.group(2))
    m = re.match(r"(\d+)\s*\+?$", t)
    return int(m.group(1)) if m else None


def age_hours(job, now):
    ts = job.get("published_date") or job.get("created_date")
    if not ts:
        return None
    d = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return (now - d).total_seconds() / 3600


def country_iso(job):
    c = (job.get("client") or {}).get("country")
    if not c:
        return None, False  # (iso, stated)
    return _COUNTRY.get(str(c).strip().upper()), True


def evaluate(job, now):
    """Return {'kills': [rule ids], 'reasons': [...], 'missing': [...], 'verdict': ...}."""
    client = job.get("client") or {}
    kills, reasons, missing = [], [], []

    iso, stated = country_iso(job)
    if not stated:
        missing.append("country")
    elif iso not in ELIGIBLE:
        kills.append("country")
        reasons.append("client country outside US/CA/AU/UK/DE/SG")

    if client.get("verification_status") != "VERIFIED":
        kills.append("payment")
        reasons.append("payment not verified")

    hr = client.get("hire_rate")
    if hr is not None and float(hr) < MIN_HIRE_RATE:
        kills.append("hire_rate")
        reasons.append("hire rate under 40%")

    spend = money(client.get("total_spent"))
    if spend is not None and spend < MIN_SPEND:
        kills.append("spend")
        reasons.append("total spend under $500")

    age = age_hours(job, now)
    if age is None:
        missing.append("posted_date")
    elif age > MAX_AGE_H:
        kills.append("age")
        reasons.append("posted more than 96h ago")

    up = proposals_upper(job)
    if up is None:
        missing.append("proposals")
    elif up > MAX_PROPOSALS:
        kills.append("proposals")
        reasons.append("more than 20 proposals")

    kind, lo, hi = parse_budget(job)
    if kind == "fixed" and hi < MIN_FIXED:
        kills.append("budget")
        reasons.append("fixed budget under $200")
    elif kind == "hourly" and hi < MIN_HOURLY_MAX:
        kills.append("budget")
        reasons.append("hourly ceiling under $25")
    # no budget stated -> not killed

    verdict = "reject" if kills else ("manual_review" if missing else "survive")
    return {"kills": kills, "reasons": reasons, "missing": missing, "verdict": verdict}


def load_jobs(path):
    """Accept list of jobs, list of searches, or {'jobs': {id: job}}; dedupe on id."""
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("jobs"), dict):
        return [dict(v, id=k) for k, v in data["jobs"].items()]
    if isinstance(data, dict) and "jobs" in data and isinstance(data["jobs"], list):
        data = [data]
    jobs, seen = [], set()
    for item in data:
        for j in (item.get("jobs") if isinstance(item, dict) and "jobs" in item else [item]):
            key = j.get("id") or json.dumps(j, sort_keys=True)
            if key not in seen:
                seen.add(key)
                jobs.append(j)
    return jobs


def parse_now(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else datetime.now(timezone.utc)


if __name__ == "__main__":
    args = sys.argv[1:]
    now = parse_now(args[args.index("--now") + 1]) if "--now" in args else parse_now(None)
    out = [dict(id=j.get("id"), **evaluate(j, now)) for j in load_jobs(args[0])]
    json.dump(out, sys.stdout, indent=2)
