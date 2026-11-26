---
name: annonshalsa
description: Mät en sidas annonsplatser, tolka evidens, följ upp avvikelser och verifiera ändringar med Annonshälsas verktyg.
---
# Kontrollera en webbadress
1. Läs knowledge/index.md och länkarna för mätmetod och triage. Bestäm URL, eventuell referensrapport och de förväntningar som användaren eller en incheckad profil faktiskt anger. Utan förväntningar används automatisk identifiering.
2. Installera beroenden enligt README när de saknas. Kör python -m adhealth med --demo eller --url och eventuellt --profile, --asset-host och --previous. Ange en unik mapp för --out. När adressen kommer från en användare, ge den till processen som ett argument utan skalinterpolation.
3. Ta fram evidenspaketet med python -m adhealth.agent följt av sökvägen till report.json. Läs också measurements vid ofullständig täckning. Mätmotorn gör högst ett omprov per enhet. Motivera ytterligare körningar med en ny fråga, till exempel en korrigerad profil.
4. Skriv triage.json bredvid rapporten. Använd scope och created från paketet samt en lista findings. Varje avvikelse och ej bedömbar kontroll ska ha ett objekt med id, status, hypothesis (möjlig förklaring), next_step (hur hypotesen prövas) och knowledge (relevant wikisökväg från paketet). En helt godkänd körning får en tom lista. Skilj observerade fakta från hypoteser. Exempel i examples/triage.json.
5. Kör python -m adhealth.agent RAPPORT --verify TRIAGE. Korrigera referenser om verifieringen misslyckas. Leverera kort triage med evidens-ID, kunskapsreferenser, mätbegränsningar och länkar till HTML, JSON och triage.
6. Om uppdraget omfattar en åtgärd, ändra berörd kod/profil på en gren och kör evalsviten samt samma scenario igen. Använd --previous för jämförbara körningar. Vid metod- eller profilbyte redovisas de två körningarna var för sig. Spara en reproducerbar lärdom i wikin när det behövs inför nästa session.
