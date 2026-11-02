# Overdracht: OWA-website (Omgevingswet Assistent)

## Wat dit is
Eenpagina-website voor OWA, het samenwerkingsverband van Rho Adviseurs, FLO Legal en Witteveen+Bos.
Live te testen op owa-platform.nl (uploaden via FTP). Eén bestand: `owa.html` (alle CSS en JS inline).

## Repo en bestanden
- Repo: `dutchplanet/platform`, branch `claude/determined-gates-PQw82` (pushen werkt nu, laatste commit "favicons gemaakt van het OWA-logo").
- Alles staat in de map `apps/`:

```
apps/
  owa.html            de hele site
  favicon.ico         16/32/48px, komt in de hoofdmap van de server
  img/
    favicon-32.png
    favicon-192.png
    apple-touch-icon.png
```
- Niet in de repo, door de gebruiker zelf in `img/` op de server gezet: `logo-owa.svg`, `logo-white.svg`, `rho-adviseurs.png`, `flo legal.png`, `WB-logo.png`, `hero.png`, `element.svg`, `element-onder.svg`.
- De gebruiker ziet bestanden niet via git maar via de chat (SendUserFile); stuur na elke wijziging `owa.html` opnieuw mee.

## Ontwerp
- Fonts: Nunito Sans 800 (koppen, altijd met roze punt), DM Sans (tekst, 17px basis).
- Kleuren: navy `#272E48`, roze `#F77D8A`, paars `#6548FC`, achtergrond `#F4F4F6`. Geen gradients.
- Iconen: één set inline SVG-lijniconen (`<symbol>` bovenaan de body), in paars vlakje.
- Opbouw in "vlakken" (10px radius, 10px tussenruimte). Alleen de hero loopt over de volle breedte en begint tegen de bovenrand; de zwevende pil-menubalk ligt eroverheen.
- Volgorde: Menu, Hero, Probleemstrook, Intro, Werkwijze, Toolbox, Voor wie, Partners, Contact (roze), Footer (navy).
- Decoratieve parallax-elementen `element.svg` (rechts, hero) en `element-onder.svg` (links, bij "Voor wie"); verborgen onder 900px.
- Alle accenttekens (é, ©, ·) staan als HTML-entities in het bestand, tegen encodingproblemen ("Ã©Ã©n") op de server. Nieuwe tekst met accenten dus ook als entity schrijven of controleren.

## Inhoud (uit het Word-document van de gebruiker)
Verwerkt: naam "Omgevingswet Assistent" overal; hero-tekst (door gebruiker ingekort tot 3 zinnen); introductie "Digitale versnelling, met de professional aan het roer"; label "De toolbox" met nieuwe intro; werkwijze-intro; toollabels bij stap 1 (HarmonisatieTool) en 3, 4, 5 (ODV); partnerkop "Drie partijen, één samenwerking"; slotoproep; nieuwe teksten HarmonisatieTool en ODV; BOPA Viewer verwijderd.
Gebruiker bevestigde: ODV is van FLO Legal, HarmonisatieTool van Witteveen+Bos. Hero-titel: "Werken aan het digitale omgevingsplan."

Door mij ingevuld, niet uit het document (gebruiker mag aanpassen): teksten van de drie probleemblokken, titels/beschrijvingen van de zes stappen, de sectie "Voor wie" (vier doelgroepen), korte partnerbeschrijvingen, knopteksten.

## Contact
`joliene.klooster@witteveenbos.com` (subtiele link in de roze contactsectie, geen knop; footer heeft geen contactkolom meer).

## Favicon
Gemaakt van het OWA-app-logo (paars/roze gradient, wit symbool) dat de gebruiker stuurde. Een SVG-versie bestaat niet; als de gebruiker het logo als SVG levert, kan een scherpere tab-favicon worden toegevoegd.

## Openstaande punten
- Mobiel menu: nu alleen logo + Contact-knop; hamburgermenu aangeboden, nog geen antwoord.
- Gebruiker moet de afbeeldingen/favicons zelf in `img/` en de hoofdmap op de server zetten; Chrome onthoudt favicons lang (Ctrl+F5 of privévenster).
- Eventueel derde tool of andere partnerinhoud: de oorspronkelijke versie van de site was verloren gegaan en is opnieuw opgebouwd; controleer of er tools of teksten ontbreken.

## Werkafspraken
- Nederlands, korte antwoorden, eerst doen dan melden.
- Test met Playwright (Chromium staat op `/opt/pw-browsers/chromium`), gebruik `NODE_PATH=$(npm root -g)`.
- Pushen alleen naar de branch hierboven; geen PR tenzij gevraagd.
