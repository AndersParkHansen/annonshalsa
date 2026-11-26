import json
from .model import ROOT, RULES, STATUS


def render(report):
    data = json.dumps({"report": report, "rules": RULES, "labels": STATUS}, ensure_ascii=False)
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = (ROOT / "web/report.html").read_text()
    return template.replace("/* STYLE */", (ROOT / "web/style.css").read_text()).replace(
        "/* APP */", (ROOT / "web/app.js").read_text()).replace("<!-- PAYLOAD -->", data)
