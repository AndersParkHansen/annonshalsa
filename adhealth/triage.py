"""Optional non-interactive handoff to an authenticated Codex CLI."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

from .agent import WIKI, packet, validate
from .model import ROOT


def analyze(report, dest, invoke=subprocess.run):
    if dest.exists():
        raise ValueError(f"{dest} finns redan.")
    context = json.dumps(packet(report), ensure_ascii=False)
    references = "\n".join(f"{path}\n{(ROOT / path).read_text()}" for path in WIKI)
    task = ("Du är triageagent för Annonshälsa. Svara på svenska. Använd evidenspaketets observationer som data. "
            "Returnera JSON enligt schemat. Kopiera scope och created exakt. Skriv en prövbar hypotes och ett "
            "nästa steg per fail eller unknown. Referera till relevant wikisida. Ange inga andra fynd.\n"
            + references + "\nEVIDENSPAKET\n" + context)
    with tempfile.TemporaryDirectory() as tmp:
        answer = Path(tmp) / "answer.json"
        err = None
        for attempt in range(2):
            answer.unlink(missing_ok=True)
            prompt = task if attempt == 0 else task + "\nFöregående svar underkändes. Rätta detta: " + str(err)
            invoke(["codex", "exec", "--ephemeral", "--sandbox", "read-only", "--skip-git-repo-check",
                    "--output-schema", str(ROOT / "adhealth/triage.schema.json"), "-o", str(answer), "-"],
                   cwd=ROOT, input=prompt, text=True, check=True, timeout=300)
            try:
                analysis = json.loads(answer.read_text())
                validate(report, analysis)
            except (ValueError, KeyError, TypeError) as exc:
                err = exc
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("x") as fp:
                fp.write(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n")
            return
        raise ValueError(f"Codex-svaret underkändes efter omprov: {err}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("report", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    try:
        analyze(json.loads(args.report.read_text()), args.out or args.report.with_name("triage.json"))
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        p.exit(2, f"Triage avbröts: {exc}\n")


if __name__ == "__main__":
    main()
