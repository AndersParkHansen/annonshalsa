"""Exercise the hosted form in Chromium with isolated GitHub responses."""
import json
import unittest

from playwright.sync_api import expect, sync_playwright

from adhealth.model import ROOT
from adhealth.probe import launch

SITE = "https://exempelkonto.github.io/annonshalsa/"
API = "https://api.github.com/repos/exempelkonto/annonshalsa"
ARTIFACT_URL = "https://github.com/exempelkonto/annonshalsa/actions/runs/123/artifacts/345"


class PagesForm(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = launch(cls.playwright, [])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.ctx = self.browser.new_context(viewport={"width":390,"height":844})
        self.addCleanup(self.ctx.close)
        self.dispatches = []
        self.result = 200
        self.conclusion = "success"
        self.ctx.route("**/*", self.respond)
        self.page = self.ctx.new_page()
        self.page.goto(SITE)
        expect(self.page.locator("#launch")).to_be_visible()

    def respond(self, route):
        url = route.request.url
        if url == SITE or url == SITE + "launch.js":
            file = "index.html" if url == SITE else "launch.js"
            route.fulfill(body=(ROOT / "docs" / file).read_text(),
                          content_type="text/html" if url == SITE else "text/javascript")
            return
        if not url.startswith(API + "/actions/"):
            route.abort()
            return
        headers = {"Access-Control-Allow-Origin":"*", "Access-Control-Allow-Headers":"*",
                   "Access-Control-Allow-Methods":"GET, POST, OPTIONS"}
        if route.request.method == "OPTIONS":
            route.fulfill(status=204, headers=headers)
            return
        status = 200
        if url == API + "/actions/workflows/audit.yml/dispatches":
            self.dispatches.append((route.request.post_data_json,route.request.headers.get("authorization")))
            status = self.result
            data = {"workflow_run_id":123}
        elif url == API + "/actions/runs/123":
            data = {"status":"completed","conclusion":self.conclusion}
        elif url == API + "/actions/runs/123/artifacts":
            data = {"artifacts":[{"id":345,"name":"annonsrapport-123","expired":False}]}
        else:
            status, data = 404, {}
        route.fulfill(status=status, headers=headers, content_type="application/json",body=json.dumps(data))

    def authorize(self):
        self.page.locator("#github-credential").fill("demo-test")
        self.page.get_by_role("button",name="Anslut och starta").click()

    def test_dispatch_and_resume_report(self):
        self.page.locator("#launch-url").fill("example.org/artikel?q=7")
        self.page.locator("#launch-submit").click()
        self.authorize()
        link = self.page.get_by_role("link",name="Hämta rapport (ZIP)")
        expect(link).to_have_attribute("href", ARTIFACT_URL)
        self.assertEqual(self.dispatches,[({"ref":"main","inputs":{"url":"https://example.org/artikel?q=7"}},"Bearer demo-test")])
        self.assertTrue(self.page.url.endswith("#korning=123"))
        self.assertEqual(self.page.locator("#github-credential").input_value(),"")
        self.assertEqual(self.page.evaluate("() => localStorage.length + sessionStorage.length"),0)
        self.page.reload()
        expect(link).to_have_attribute("href", ARTIFACT_URL)
        expect(self.page.locator("#forget-token")).to_be_hidden()
        self.assertEqual(len(self.dispatches),1)

    def test_invalid_input_and_forbidden_dispatch(self):
        self.page.locator("#launch-url").fill("http://example.org")
        self.page.locator("#launch-submit").click()
        expect(self.page.locator("#auth-dialog")).to_be_hidden()
        self.assertFalse(self.page.locator("#launch-url").evaluate("el => el.validity.valid"))
        self.result = 403
        self.page.locator("#launch-url").fill("https://example.org")
        self.page.locator("#launch-submit").click()
        self.authorize()
        expect(self.page.locator("#launch-feedback")).to_contain_text("GitHub nekade")
        expect(self.page.locator("#forget-token")).to_be_hidden()
        self.page.locator("#launch-submit").click()
        expect(self.page.locator("#auth-dialog")).to_be_visible()
        self.assertEqual(len(self.dispatches),1)

    def test_failed_job_remains_accessible(self):
        self.conclusion = "failure"
        self.page.locator("#launch-url").fill("example.org")
        self.page.locator("#launch-submit").click()
        self.authorize()
        expect(self.page.locator("#launch-feedback")).to_contain_text("misslyckades")
        expect(self.page.get_by_role("link",name="Öppna körningen på GitHub")).to_be_visible()
        expect(self.page.get_by_role("link",name="Hämta rapport (ZIP)")).to_have_count(0)
