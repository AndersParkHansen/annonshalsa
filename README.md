# Annonshälsa för URL

Ge Codex en webbadress och få en fristående HTML-rapport, mätdata och en triage med spårbara evidens-ID:n. Repot innehåller en helt fiktiv artikelsida, en webbläsarbaserad mätmotor, agentinstruktioner och en versionshanterad kunskapswiki.

**Prova rapporten direkt.** Öppna `docs/index.html` i webbläsaren. Flikarna visar fynd, alla mätningar och förändringar. **Ny URL-kontroll** skapar ett färdigt uppdrag att klistra in i Codex. Rapporten går även att öppna lokalt utan nätverk.

## På personliga GitHub med Codex Cloud

1. Lägg repots innehåll (inklusive `.github/` och `.agents/`) i roten av ditt GitHub-repo på grenen `main`. På GitHub Free kan ett publikt repo använda Pages. För att publicera från ett privat personligt repo behöver du GitHub Pro.
2. Anslut repot till din Codex-molnmiljö. Använd Python 3.12. Kör `python -m pip install -r requirements.txt` och `python -m playwright install --with-deps chromium` vid miljöförberedelsen. Miljön behöver åtkomst till de mål och resursvärdar som ska mätas. Alternativt gör GitHub Actions själva webbmätningen.
3. Slå på Pages via **Settings → Pages → Deploy from a branch → main → /docs → Save**. Det publicerar den incheckade demorapporten. Efter ändringar i rapportmallen eller demot, be Codex köra om demon och ersätta `docs/index.html` i en PR.
4. Ge Codex uppdraget *”Kör demon med repots skill annonshalsa. Visa vilken plats som fortfarande är tom efter omprov på båda enheterna, validera triagen och ange vilka wikisidor du använde.”* För en riktig kontroll byter du ut ”demon” mot en publik HTTPS-URL.
5. Du kan även välja **Actions → URL-kontroll → Run workflow** och ange URL, eventuell profil och extra resursvärdar. Ladda ned artefakten **annonsrapport** från körningen. Öppna `index.html` eller ge `report.json` till Codex för triage. Pages är en statisk rapportläsare. Chromium körs i Actions, Codex-miljön eller på din dator.

Schemat kör den fiktiva sidan varje dag kl. 06.27 UTC när schemalagda Actions är aktiverade på standardgrenen. Manuella mätningar kör den URL du anger. Actions försöker läsa föregående baslinje från GitHubs cache och sparar nya resultat som artefakt i 14 dagar. Om cachen saknas visas ”Första mätningen”. Rollbaserad repoåtkomst gäller även dessa körningar. Lägg bara in adresser som kan visas för repots läsare.

## Direkt körning

```sh
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m adhealth --demo --out out/demo-1
python -m adhealth --demo --previous out/demo-1/report.json --out out/demo-2
python -m adhealth --url https://example.org --out out/url-1
python -m unittest discover -s tests -v
```

Välj en ny körningsmapp för varje mätning. Utan `--out` används en tidsstämplad mapp. En körning som hittar avvikelser skriver fortfarande sin rapport. Felaktiga argument och tekniska startfel ger felkod. På en maskin med systeminstallerad Chromium kan du ange sökvägen med `ADHEALTH_CHROMIUM`.

### Annonser på en riktig sida

Börja utan profil. Motorn läser etablerade DOM-markörer som `data-ad-slot`, `data-ad-unit`, `data-google-query-id`, GPT-id:n och AdSense-element. För att avgöra om en *specifik* plats saknas behöver agenten ett jämförelseunderlag. Lägg profilens namn och lista med förväntade platser i en JSON-fil under `profiles/`. Varje plats har ett unikt namn och en CSS-selektor som matchar exakt ett element. Se [demoprofilen](profiles/demo.json).

- `expectMedia: true` gör en tom, observerad plats till en avvikelse vid full täckning. Utan det kontraktet är utfallet ej bedömbart när renderingen saknar belägg.
- `lazy: true` testar om synligt media tillkommer efter scrollning. En första observation där platsen redan är synlig eller fylld räcker inte för den slutsatsen.
- Välj profilen med `--profile profiles/artikel.json`. Sidans värdnamn är tillåtet som standard. Lägg till varje betrodd resursvärd med `--asset-host cdn.example.org`. Se blockerade värdar i rapportens JSON. Verktyget använder HTTPS, publikt uppslagna värdar, anonyma kontexter och läsande GET/HEAD-anrop. Webbläsaren gör inga klick.
- Mätningen observerar innehåll i huvudsidans DOM. En iframe, ett samtyckeslager eller utebliven resurs kan lämna utfallet ej bedömbart. Se [mätmetoden](knowledge/matmetod.md) för exakta tids- och observationsgränser. Monetär effekt och intäkter kräver andra datakällor.

### Agentens arbetsflöde

[AGENTS.md](AGENTS.md) leder till [Codex-skillen](.agents/skills/annonshalsa/SKILL.md) och [kunskapsindexet](knowledge/index.md). Vid en avvikelse gör mätmotorn ett omprov i en ny kontext. Skillen styr nästa steg från evidens till prövbar hypotes, åtgärd och ommätning. Varje fynd måste referera till rätt körning, kontroll och wikisida.

```sh
python -m adhealth.agent out/demo-1/report.json
python -m adhealth.agent out/demo-1/report.json --verify out/demo-1/triage.json
```

Det andra kommandot förutsätter att agenten har skrivit triagefilen. Ett komplett [exempel](examples/triage.json) hör till den [incheckade mätningen](examples/report.json). I en redan inloggad Codex Cloud-session gör agenten analysen direkt. För en miljö med autentiserad Codex CLI finns även en automatisk agentkörning:

```sh
python -m adhealth.triage out/demo-1/report.json
```

Den skickar evidens och wiki till `codex exec`, kräver ett strukturerat svar och ger agenten ett rättningsförsök vid ogiltiga referenser. Mätningarna och GitHub Actions behöver ingen modellnyckel. CI kör den syntetiska webbläsaren och regel- och agentevals, inklusive ett scenario där sidfoten åtgärdas och jämförs mot före-läget. Läs [projektbesluten](knowledge/beslut.md) för när kunskap ska sparas tillbaka.
