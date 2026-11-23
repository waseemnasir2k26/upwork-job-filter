import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from filter import evaluate, load_jobs, proposals_upper  # noqa: E402
from score import PASS, run, score  # noqa: E402

NOW = datetime(2026, 11, 19, 15, 0, tzinfo=timezone.utc)


def job(**kw):
    base = {"id": "t", "title": "n8n automation", "budget": "1,200.00", "job_type": "fixed",
            "client": {"country": "US", "total_spent": "$9,000.00", "verification_status": "VERIFIED"},
            "published_date": "2026-11-19T10:00:00Z", "proposals_tier": "5 to 10", "skills": ["n8n"]}
    c = dict(base["client"], **kw.pop("client", {}))
    base.update(kw)
    base["client"] = c
    return base


class Rules(unittest.TestCase):
    def kills(self, **kw):
        return evaluate(job(**kw), NOW)["kills"]

    def test_clean_job_survives(self):
        self.assertEqual(evaluate(job(), NOW)["verdict"], "survive")

    def test_country(self):
        self.assertEqual(self.kills(client={"country": "India"}), ["country"])
        for c in ("USA", "GBR", "United Kingdom", "DEU", "SGP", "AUS", "CAN"):
            self.assertEqual(self.kills(client={"country": c}), [], c)

    def test_missing_country_is_review_not_kill(self):
        j = job()
        del j["client"]["country"]
        r = evaluate(j, NOW)
        self.assertEqual((r["kills"], r["verdict"]), ([], "manual_review"))

    def test_payment(self):
        self.assertEqual(self.kills(client={"verification_status": "UNVERIFIED"}), ["payment"])

    def test_hire_rate_only_when_stated(self):
        self.assertEqual(self.kills(client={"hire_rate": 39}), ["hire_rate"])
        self.assertEqual(self.kills(client={"hire_rate": 40}), [])
        self.assertEqual(self.kills(), [])

    def test_spend(self):
        self.assertEqual(self.kills(client={"total_spent": "$499.99"}), ["spend"])
        self.assertEqual(self.kills(client={"total_spent": "$500.00"}), [])

    def test_age(self):
        self.assertEqual(self.kills(published_date="2026-11-15T14:00:00Z"), ["age"])  # 97h
        self.assertEqual(self.kills(published_date="2026-11-15T15:00:00Z"), [])  # 96h

    def test_proposals(self):
        self.assertEqual(proposals_upper({"proposals_tier": "Fewer than 5"}), 4)
        self.assertEqual(proposals_upper({"proposals_tier": "50+"}), 50)
        self.assertEqual(self.kills(proposals_tier="20 to 50"), ["proposals"])
        self.assertEqual(self.kills(proposals_tier="15 to 20"), [])

    def test_budget_floors(self):
        self.assertEqual(self.kills(budget="199.00"), ["budget"])
        self.assertEqual(self.kills(budget="200.00"), [])
        self.assertEqual(self.kills(budget="10.00-24.00/hr", job_type="hourly"), ["budget"])
        self.assertEqual(self.kills(budget="10.00-25.00/hr", job_type="hourly"), [])

    def test_no_budget_not_killed(self):
        j = job()
        del j["budget"]
        self.assertEqual(evaluate(j, NOW)["kills"], [])


class Scoring(unittest.TestCase):
    def test_weights_sum_to_100(self):
        best = job(budget="5,000.00", client={"hire_rate": 90, "total_spent": "$50,000.00"},
                   title="n8n AI chatbot CRM WordPress SEO API", proposals_tier="Fewer than 5",
                   published_date="2026-11-19T14:00:00Z", skills=["python"])
        self.assertEqual(score(best, NOW)["total"], 100)

    def test_killed_job_never_passes(self):
        row = run([job(client={"country": "India"}, budget="5,000.00")], NOW)[0]
        self.assertFalse(row["passed"])

    def test_pass_mark(self):
        self.assertEqual(PASS, 65)

    def test_synthetic_sample(self):
        rows = run(load_jobs(os.path.join(os.path.dirname(__file__), "..", "sample-jobs.json")), NOW)
        by = {r["id"]: r for r in rows}
        self.assertEqual(by["syn-1"]["eval"]["verdict"], "survive")
        self.assertTrue(by["syn-1"]["passed"])
        self.assertEqual(by["syn-2"]["eval"]["kills"], ["proposals"])
        self.assertEqual(by["syn-3"]["eval"]["kills"], ["budget"])
        self.assertEqual(by["syn-4"]["eval"]["kills"], ["country"])
        self.assertEqual(by["syn-5"]["eval"]["verdict"], "manual_review")


if __name__ == "__main__":
    unittest.main()
