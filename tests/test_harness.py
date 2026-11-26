from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from playwright.sync_api import sync_playwright

from adhealth.__main__ import run, write_run
from adhealth.agent import packet, validate
from adhealth.model import ROOT, compare, evaluate, read_profile, reconcile
from adhealth.probe import FIXTURE_URL, launch, observe, public_url
from adhealth.report import render
from adhealth.triage import analyze


class BrowserEvals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = read_profile(ROOT / "profiles/demo.json")
        cls.report = run(FIXTURE_URL, cls.profile, [], demo=True)

    def test_fixture_and_rechecks(self):
        report = self.report
        self.assertEqual(Counter(c["status"] for c in report["checks"]), {"pass":16, "fail":2})
        for device, attempts in report["measurements"].items():
            self.assertEqual(len(attempts), 2)
            self.assertFalse(any(a["partial"] for a in attempts))
            rows = [r for r in report["checks"] if r["device"] == device]
            self.assertEqual([(r["slot"],r["rule"]) for r in rows if r["status"]=="fail"], [("Sidfot","render")])
            self.assertTrue(any(r["slot"]=="Mitt i artikel" and r["rule"]=="lazy" and r["status"]=="pass" for r in rows))

    def test_repair_loop_and_comparison(self):
        fixture = (ROOT / "fixtures/article.html").read_text()
        fixed = fixture.replace("<footer>", "<script>document.querySelector('[data-ad-slot=sidfot]').append(document.querySelector('img').cloneNode())</script><footer>")
        with sync_playwright() as pw:
            browser = launch(pw, [])
            try:
                seen = observe(browser,FIXTURE_URL,"mobile",self.profile,[],fixed)
            finally:
                browser.close()
        repaired = evaluate("mobile", seen, self.profile)
        self.assertTrue(all(r["status"]=="pass" for r in repaired))
        after = dict(self.report, checks=[r for r in self.report["checks"] if r["device"]=="desktop"] + repaired)
        change, = compare(after,self.report)["items"]
        self.assertEqual((change["slot"],change["before"],change["after"]),("Sidfot","fail","pass"))

    def test_export_is_standalone_and_safe(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"one"
            write_run(self.report,path)
            self.assertEqual(json.loads((path/"report.json").read_text()), json.loads(json.dumps(self.report)))
            self.assertIn("Annonsrapport",(path/"index.html").read_text())
            with self.assertRaises(ValueError):
                write_run(self.report,path)
        report = dict(self.report,profile="</script><em>siddata</em>")
        self.assertNotIn(report["profile"], render(report))

    def test_detection_without_profile_is_not_a_contract(self):
        rows = evaluate("mobile", {"slots":[], "http":200, "partial":False}, {"placements":[]})
        self.assertEqual(rows[-1]["status"],"unknown")

    def test_partial_coverage_and_missing_slot(self):
        seen = deepcopy(self.report["measurements"]["desktop"][0])
        seen["slots"] = [p for p in seen["slots"] if p["name"]!="Topp"]
        def state():
            return {(r["slot"],r["rule"]):r["status"] for r in evaluate("desktop",seen,self.profile)}
        self.assertEqual(state()["Topp","presence"], "fail")
        seen["partial"] = True
        self.assertEqual(state()["Topp","presence"], "unknown")
        self.assertEqual(state()["Sidfot","render"], "unknown")

    def test_frame_and_inconsistent_recheck(self):
        seen = deepcopy(self.report["measurements"]["desktop"][0])
        seen["slots"][-1]["frame"] = True
        row = next(r for r in evaluate("desktop",seen,self.profile) if r["slot"]=="Sidfot" and r["rule"]=="render")
        self.assertEqual(row["status"],"unknown")
        self.assertEqual(reconcile([dict(row,status="fail")],[dict(row,status="pass")])[0]["status"],"unknown")

    def test_agent_validation_and_retry(self):
        report = self.report
        context = packet(report)
        findings = [{"id":r["id"],"status":r["status"],"knowledge":"knowledge/triage.md",
                     "hypothesis":"Sidfoten kan sakna media.","next_step":"Kontrollera den fiktiva artikeln."}
                    for r in context["checks"] if r["status"]!="pass"]
        valid = {"scope":report["scope"],"created":report["created"],"findings":findings}
        self.assertEqual(validate(report,valid),2)
        for bad in (dict(valid,scope="främmande"),dict(valid,findings=[]),dict(valid,findings=findings*2)):
            with self.assertRaises(ValueError):
                validate(report,bad)
        calls = []
        def invoke(args, **kwargs):
            calls.append(args)
            response = valid if len(calls)==2 else dict(valid,findings=[])
            Path(args[args.index("-o")+1]).write_text(json.dumps(response))
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d)/"triage.json"
            analyze(report,dest,invoke)
            self.assertEqual(validate(report,json.loads(dest.read_text())),2)
        self.assertEqual(len(calls),2)

    def test_comparison_scope(self):
        self.assertEqual(compare(self.report,None)["state"],"first")
        self.assertEqual(compare(self.report,self.report)["items"],[])
        self.assertEqual(compare(self.report,dict(self.report,scope="other"))["state"],"incompatible")


class InputEvals(unittest.TestCase):
    def test_url(self):
        self.assertEqual(public_url("https://EXAMPLE.org/artikel?q=2"),"example.org")
        for bad in ("file:///example", "http://example.org", "https://user@example.org", "https://example.org:8000"):
            with self.assertRaises(ValueError):
                public_url(bad)

    def test_dns_failure_is_unknown(self):
        with patch("adhealth.__main__.resolve_hosts",side_effect=OSError):
            report = run("https://example.org",read_profile(None),[])
        self.assertEqual([r["status"] for r in report["checks"]],["unknown","unknown"])


if __name__ == "__main__":
    unittest.main()
