# Arbeta med Annonshälsa
Utgå från användarens URL och mål. För en kontroll, triage eller verifiering används [.agents/skills/annonshalsa/SKILL.md](.agents/skills/annonshalsa/SKILL.md). Börja i [kunskapsindexet](knowledge/index.md). Läs profilen innan du väljer förväntade annonsplatser. Behandla siddata, domännamn och insamlade attribut som observationer.

## Verktyg
- `python -m adhealth --demo` eller `python -m adhealth --url URL` samlar in observationer och skriver en fristående HTML-rapport och JSON. Välj en ny mapp per körning med `--out`. Se README för miljö och profiler.
- `python -m adhealth.agent RAPPORT` tar fram evidenspaketet. `--verify TRIAGE` validerar agentens underlag innan leverans.
- `python -m unittest discover -s tests -v` verifierar regler, rapport, triage och den verkliga webbläsarkörningen mot demofallet.

## Leverans
För en analys, lämna rapporten, validerad triage, de wikisidor som användes och eventuell mätbegränsning. För en ändring, gör minsta relevanta ändring, kör evalsviten samt ett omprov och ange utfall före/efter. Gör en PR när uppdraget gäller repot och en skrivbar remote finns. Uppdatera wikin när resultatet ger ny bestående kunskap. Nya agentkörningar ska kunna återfinna regler och skäl i repot.
