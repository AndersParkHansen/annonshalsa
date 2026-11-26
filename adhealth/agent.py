"""Prepare an evidence packet and validate a Codex agent's triage before handoff."""
import argparse
import json
from pathlib import Path

from .model import RULES

WIKI = ("knowledge/matmetod.md", "knowledge/triage.md", "knowledge/beslut.md")


def packet(report):
    return {"scope": report["scope"], "created": report["created"], "url": report["url"],
            "profile": report["profile"], "rules": RULES, "checks": report["checks"],
            "comparison": report["comparison"], "knowledge": WIKI}


def validate(report, analysis):
    if not isinstance(analysis, dict) or analysis.get("scope") != report["scope"] or analysis.get("created") != report["created"]:
        raise ValueError("Analysen måste referera till exakt denna körning.")
    findings = analysis.get("findings")
    if not isinstance(findings, list):
        raise ValueError("findings måste vara en lista.")
    checks = {c["id"]: c for c in report["checks"]}
    required = {i for i, c in checks.items() if c["status"] != "pass"}
    cited = set()
    for f in findings:
        if not isinstance(f, dict) or f.get("id") not in required or f["id"] in cited:
            raise ValueError("Okänd, godkänd eller upprepad evidensreferens.")
        cited.add(f["id"])
        if f.get("status") != checks[f["id"]]["status"] or f.get("knowledge") not in WIKI:
            raise ValueError("Bedömningen eller kunskapsreferensen stämmer inte.")
        for field in ("hypothesis", "next_step"):
            if not isinstance(f.get(field), str) or not f[field].strip():
                raise ValueError(f"Fyndet saknar {field}.")
    if cited != required:
        raise ValueError("Alla avvikelser och ej bedömbara kontroller behöver följas upp.")
    return len(cited)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("report", type=Path)
    p.add_argument("--verify", type=Path)
    args = p.parse_args()
    try:
        report = json.loads(args.report.read_text())
        if args.verify:
            n = validate(report, json.loads(args.verify.read_text()))
            print(f"{n} fynd verifierade mot körningens evidens-ID och wiki.")
        else:
            print(json.dumps(packet(report), indent=2, ensure_ascii=False))
    except (ValueError, OSError, TypeError, KeyError) as exc:
        p.exit(2, f"Underlaget kunde inte valideras: {exc}\n")


if __name__ == "__main__":
    main()
