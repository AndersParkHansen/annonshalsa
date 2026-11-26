---
title: Mätmetod
type: reference
---
# Mätmetod
En konfigurerad plats är en namngiven CSS-selektor i en JSON-profil. Utan profil letar insamlaren efter vanliga annonsmarkörer i huvudsidans DOM. Noll träffar ger ej bedömbar inventering. En profil gör det möjligt att kontrollera att en specifik plats finns exakt en gång.

Varje körning använder Chromium med ny anonym kontext vid 1440 × 900 och 390 × 844. Mobil använder dessutom touch, mobil viewport och mobil användaragent. Mätningen tar ett första prov efter 600 ms, scrollar upp till 16 steg om 80 procent av vyhöjden, väntar 220 ms per steg och avslutar med 500 ms väntan. Högst 200 platser registreras. Adressen följs som en enda sidvisning per försök. Ett omprov får en ny kontext.

Renderingssignalen kräver att en plats och ett laddat bild- eller videoelement eller en canvas med mätbar yta syns i vyn. Den säger inget om annonsintäkt, viewability enligt branschstandard eller om annonsservern har räknat en impression. En iframe kan ha laddat innehåll som insamlaren inte ser. Textannonser, bakgrundsbilder, skugg-DOM och format inuti ramar kräver andra signaler.

Profilens expectMedia anger att en observerad tom plats ska innehålla synligt media. En okänd plats utan detta kontrakt bedöms försiktigt. En lazy-kontroll förutsätter att platsen började utanför första vyn och att innehåll tillkom när sidan scrollades. Det visar en observerad tidsföljd. För laddningens exakta orsak krävs ytterligare instrumentering.

Standardkörningen tillåter sidans värdnamn. Ange ytterligare resursvärdar vid behov. Blockerade värdar, misslyckade resursanrop och nådd scrollgräns gör negativa slutsatser osäkra. Webbläsaren godkänner inga samtyckesval. Den kan ändå ladda resurser som sidan begär före samtycke. Använd lämpliga testadresser och granska begränsningarna per enhet.
