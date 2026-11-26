"""Actions adapter. User input travels as arguments without shell evaluation."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

def main():
    url = os.environ.get("TARGET", "").strip()
    profile = os.environ.get("PROFILE", "").strip()
    hosts = sorted(set(h.strip() for h in os.environ.get("HOSTS", "").split(",") if h.strip()))
    if profile and not re.fullmatch(r"[\w-]+\.json", profile):
        sys.exit("Ange ett filnamn under profiles/.")
    if sys.argv[1] == "key":
        key = hashlib.sha256(json.dumps([url, profile, hosts]).encode()).hexdigest()
        with open(os.environ["GITHUB_OUTPUT"], "a") as out:
            print("key=" + key, file=out)
        return
    baseline = Path("out/baseline/report.json")
    args = [sys.executable, "-m", "adhealth", "--out", "out/result"]
    args.extend(["--url", url] if url else ["--demo"])
    if profile:
        args.extend(["--profile", "profiles/" + profile])
    for host in hosts:
        args.extend(["--asset-host", host])
    if baseline.exists():
        args.extend(["--previous", str(baseline)])
    subprocess.run(args, check=True)
    result = Path("out/result/report.json")
    report = json.loads(result.read_text())
    baseline.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(result, baseline)
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as out:
        print("## Annonsrapport\n", file=out)
        for status, label in [("pass","Godkända"), ("fail","Avvikelser"), ("unknown","Ej bedömbara")]:
            print(f"- {label}: {sum(c['status'] == status for c in report['checks'])}", file=out)
        print("\nHämta artefakten och öppna index.html eller ge report.json till Codex.", file=out)

if __name__ == "__main__":
    main()
