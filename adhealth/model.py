"""Evidence-based checks shared by the command, report and agent."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEVICES = {"desktop": (1440, 900), "mobile": (390, 844)}
STATUS = {"pass": "Godkänd", "fail": "Avvikelse", "unknown": "Ej bedömbar"}
RULES = {
    "page": "Sidan gick att läsa",
    "inventory": "Annonsplatser hittades",
    "presence": "Förväntad plats finns",
    "render": "Synligt innehåll i platsen",
    "lazy": "Innehåll tillkom efter scrollning",
}


def read_profile(path):
    if path is None:
        return {"name": "Automatisk identifiering", "placements": []}
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict) or not isinstance(data.get("name"), str) or not isinstance(data.get("placements"), list):
        raise ValueError("Profilen behöver name och placements.")
    seen = set()
    for slot in data["placements"]:
        if not isinstance(slot, dict) or not all(isinstance(slot.get(k), str) and slot[k].strip() for k in ("name", "selector")):
            raise ValueError("Varje plats behöver name och selector.")
        if slot["name"] in seen or not all(isinstance(slot.get(k, False), bool) for k in ("lazy", "expectMedia")):
            raise ValueError("Platsnamn måste vara unika och lazy/expectMedia ska vara true eller false.")
        seen.add(slot["name"])
    return data


def check(device, rule, slot, state, evidence, identity=None):
    key = json.dumps([device, rule, identity or slot], ensure_ascii=False)
    return {"id": hashlib.sha256(key.encode()).hexdigest()[:16], "device": device, "rule": rule,
            "slot": slot, "status": state, "evidence": evidence}


def evaluate(device, run, profile):
    def row(rule, slot, status, evidence, identity=None):
        return check(device, rule, slot, status, evidence, identity)
    if run.get("problem"):
        return [row("page", "Hela sidan", "unknown", run["problem"])]
    rows = [row("page", "Hela sidan", "pass", f"HTML lästes med HTTP {run['http']}.")]
    places = run["slots"]
    rows.append(row("inventory", "Hela sidan", "pass" if places else "unknown",
                    f"{len(places)} unika platser observerades med profilens selektorer eller generella annonsmarkörer."))
    for target in profile["placements"]:
        name = target["name"]
        hits = [p for p in places if p["expected"] == name]
        if len(hits) == 1:
            state = "pass"
        elif run["partial"] and not hits:
            state = "unknown"
        else:
            state = "fail"
        rows.append(row("presence", name, state, f"{len(hits)} träffar för {target['selector']}."))
    contracts = {t["name"]: t for t in profile["placements"]}
    for p in places:
        name = p["name"]
        key = p["key"]
        contract = contracts.get(p["expected"], {})
        if p["visibleMedia"]:
            state, reason = "pass", "En bild, video eller canvas med synlig yta observerades i vyn."
        elif not p["seen"] or run["partial"] or p["frame"] or not contract.get("expectMedia"):
            state, reason = "unknown", "Synligt annonsinnehåll kunde inte beläggas i denna mätning."
        else:
            state, reason = "fail", "Platsen kom in i vyn men saknade synligt media under mätfönstret."
        rows.append(row("render", name, state, reason, key))
        if contract.get("lazy"):
            if p["initialMedia"] or p["initialInView"] or run["partial"] or not p["seen"]:
                state, reason = "unknown", "Ingen isolerbar övergång från tom plats till innehåll efter scrollning."
            elif p["visibleMedia"]:
                state, reason = "pass", "Tom före scrollning, synligt media när platsen nåddes."
            elif p["frame"]:
                state, reason = "unknown", "En ram observerades. Innehållet kunde inte verifieras."
            else:
                state, reason = "fail", "Platsen nåddes vid scrollning men fick inget synligt media."
            rows.append(row("lazy", name, state, reason, key))
    return rows


def reconcile(first, second):
    """A discrepancy must reproduce in a fresh context to be reported as a failure."""
    if second is None:
        return first
    original = {r["id"]: r for r in first}
    retry = {r["id"]: r for r in second}
    output = []
    for key in dict.fromkeys([*original, *retry]):
        a, b = original.get(key), retry.get(key)
        row = dict(a or b)
        if a and b and a["status"] == b["status"]:
            row["evidence"] += " Samma utfall vid omprov."
        else:
            row.update(status="unknown", evidence="Omprovet gav olika observationer. " +
                       " / ".join(x["evidence"] if x else "Ingen observation." for x in (a, b)))
        output.append(row)
    return output


def compare(report, previous):
    if previous is None:
        return {"state": "first", "items": []}
    if any(previous.get(k) != report[k] for k in ("schema", "scope")):
        return {"state": "incompatible", "items": []}
    old = {r["id"]: r for r in previous["checks"]}
    new = {r["id"]: r for r in report["checks"]}
    items = []
    for key in sorted(old.keys() | new.keys()):
        before = old[key]["status"] if key in old else None
        after = new[key]["status"] if key in new else None
        if before != after:
            row = new.get(key) or old[key]
            items.append({**{k: row[k] for k in ("id", "device", "slot", "rule")}, "before": before, "after": after})
    return {"state": "compared", "items": items}
