import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import sync_playwright

from .model import DEVICES, ROOT, compare, evaluate, read_profile, reconcile
from .probe import FIXTURE_URL, hostname, launch, observe, public_url, resolve_hosts
from .report import render


def run(url, profile, extra_hosts, demo=False, previous=None):
    hosts = sorted({public_url(url), *(hostname(h) for h in extra_hosts)})
    scope = json.dumps([url, hosts, profile, demo, "observation-v1"], sort_keys=True)
    u = urlsplit(url)
    result = {
        "schema": 1, "scope": hashlib.sha256(scope.encode()).hexdigest(),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "url": urlunsplit((u.scheme, u.netloc, u.path, "", "")), "demo": demo, "profile": profile["name"],
        "checks": [], "measurements": {}, "viewports": DEVICES
    }
    fixture = (ROOT / "fixtures/article.html").read_text() if demo else None
    try:
        mappings = [] if demo else resolve_hosts(hosts)
    except OSError:
        for device in DEVICES:
            error = {"problem": "DNS-uppslagningen misslyckades."}
            result["measurements"][device] = [error]
            result["checks"].extend(evaluate(device, error, profile))
    else:
        with sync_playwright() as pw:
            browser = launch(pw, mappings, None if demo else public_url(url))
            try:
                for device in DEVICES:
                    attempts = []
                    rows = []
                    for _ in range(2):
                        m = observe(browser, url, device, profile, hosts, fixture)
                        attempts.append(m)
                        rows.append(evaluate(device, m, profile))
                        if not m.get("problem") and not any(c["status"] == "fail" for c in rows[-1]):
                            break
                    result["checks"].extend(reconcile(rows[0], rows[1] if len(rows) == 2 else None))
                    result["measurements"][device] = attempts
            finally:
                browser.close()
    result["comparison"] = compare(result, previous)
    return result


def write_run(result, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise ValueError(f"{out} finns redan. Välj en ny körningsmapp.")
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        stage = Path(tmp) / "result"
        stage.mkdir()
        (stage / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        (stage / "index.html").write_text(render(result))
        stage.rename(out)


def main():
    parser = argparse.ArgumentParser(description="Undersök annonsplatser på en URL med Chromium.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--demo", action="store_true")
    target.add_argument("--url")
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--asset-host", action="append", default=[], help="Extra publikt värdnamn för sidresurser.")
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        profile = read_profile(args.profile or (ROOT / "profiles/demo.json" if args.demo else None))
        previous = json.loads(args.previous.read_text()) if args.previous else None
        result = run(args.url or FIXTURE_URL, profile, args.asset_host, args.demo, previous)
        dest = args.out or Path("out") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        write_run(result, dest)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"Körningen avbröts: {exc}\n")
    counts = {v: sum(c["status"] == v for c in result["checks"]) for v in ("pass", "fail", "unknown")}
    print(f"{dest}/index.html | {counts['pass']} godkända, {counts['fail']} avvikelser, {counts['unknown']} ej bedömbara")


if __name__ == "__main__":
    main()
