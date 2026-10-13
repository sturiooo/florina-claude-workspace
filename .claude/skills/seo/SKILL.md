---
name: seo
description: SEO sklepu Florina (florina.pl): audyt strony, kategorii albo produktu, research fraz kluczowych, plan treści i klastry tematyczne, artykuły na bloga z linkowaniem wewnętrznym, dane strukturalne, widoczność w asystentach AI (GEO, AEO, llms.txt), przekierowania i indeksacja. Używaj, gdy użytkownik pisze o SEO, Google, pozycjach, frazach, słowach kluczowych, meta title, blogu, artykule, ruchu z wyszukiwarki, ChatGPT / AI. Pełny zestaw narzędzi jest w katalogu seo/, a cięższe zadania przekaż agentowi seo-strateg.
---

# SEO dla Floriny

Toolkit: `seo/` (skille szczegółowe w `seo/resources/skills/`, referencje, szablony, ok. 70 skryptów w `seo/scripts/`,
warstwa Shopify w `seo/shopify/README.md`). Pochodzi z paczki SEO Igora (licencja w `seo/LICENSE`).

## Kiedy co

| Prośba | Co robisz |
|---|---|
| „Sprawdź SEO tej strony / kategorii / produktu” | sam: `python seo/scripts/fetch_page.py <url>` + `python seo/scripts/parse_html.py <plik> --json`, według `seo/resources/skills/seo-page.md`; przy kilku adresach agent `seo-strateg` |
| „Pełny audyt sklepu”, „plan SEO”, „klastry”, „research fraz” | agent **`seo-strateg`** (Agent tool, `subagent_type: seo-strateg`) |
| „Napisz artykuł na bloga” | agent `seo-strateg` (szkic do `robocze/blog/`), potem publikację robisz Ty po zgodzie (strony i blog to zwykłe zmiany w sklepie, skill `bezpieczna-praca`) |
| „Popraw meta title / opis kategorii pod SEO” | skill `opisy-produktow-i-kategorii` (styl i limity znaków) |
| „Dodaj dane strukturalne / zmień nagłówki w szablonie” | rekomendacja od `seo-strateg`, wdrożenie skillem `zmiany-w-szablonie` (człowiek przez `!`) |
| „Czy ChatGPT nas poleca / llms.txt / GEO” | `seo/resources/skills/seo-geo.md`, `seo-aeo.md`, `python seo/scripts/llms_txt_checker.py https://florina.pl` |
| „Czy przekierowania działają” | `python seo/scripts/redirect_checker.py <url>`; lista przekierowań z panelu przez `scripts/shopify_gql.py` (`urlRedirects`) |

## Zasady

- Skrypty SEO tylko **czytają** strony (pobierają publiczny HTML). Uruchamiasz je bez pytania. Zmiany w sklepie dalej idą przez skrypty z `scripts/`.
- **Nie mierzymy PageSpeed Insights / Lighthouse przez API** (brak klucza). Core Web Vitals: ryzyka z kodu i HTML
  (`lcp_subparts.py`, `image_weight_audit.py`, `third_party_script_audit.py`) jako hipotezy; dane terenowe tylko z Google Search Console od użytkownika.
- Fakty z realnego HTML, nie z pamięci. Każde znalezisko: dowód, waga, rekomendacja przed / po.
- Wyniki: `raporty/seo/RRRR-MM-DD-<temat>.md`. Szkice treści: `robocze/`.
- Styl treści Floriny: `.claude/skills/opisy-produktow-i-kategorii/references/styl-i-seo.md`.
- Gdy skrypt potrzebuje biblioteki, której brak (`requests`, `beautifulsoup4`, `lxml`): poproś o `pip install -r seo/requirements.txt` (wymaga zgody).
