# Florina: Claude Code workspace

Paczka do pracy w sklepie **florina-pl.myshopify.com** przez Claude Code w VS Code, dla osoby nietechnicznej.
Claude prowadzi ją przez zadania w sklepie (plan, podgląd, zgoda, backup, zapis, weryfikacja), a zabezpieczenia pilnują granic.

Instalacja: **[INSTALACJA.md](INSTALACJA.md)** (`install.ps1` robi większość).

## Zakres (decyzja Igora, 14.10.2026): „praktycznie wszystko poza edycją szablonu”

| Obszar | Jak |
|---|---|
| Produkty, warianty, ceny, stany, status, publikacja, kolekcje i reguły, tagi | Claude, za zgodą (skille `produkty-kolekcje-tagi`, `bezpieczna-praca`) |
| Opisy, SEO, FAQ, cechy (metapola i definicje), metaobiekty | Claude, za zgodą (`opisy-produktow-i-kategorii`, `faq-produkty-kategorie`, `ocechowanie-metapola`) |
| Media, rabaty, strony, blog, nawigacja, przekierowania, tłumaczenia, klienci, zamówienia (edycja, tagi, notatki) | Claude, za zgodą |
| Usuwanie czegokolwiek | Claude, za zgodą, z twardym ostrzeżeniem i obowiązkowym backupem |
| **Motyw / szablon** (wygląd, sekcje, kod, edytor motywu) | Claude **przygotowuje**, wgrywa **człowiek** jedną komendą (`zmiany-w-szablonie`) |
| SEO: audyt, frazy, plan, artykuły, GEO | skill `seo` + agent `seo-strateg`, toolkit w `seo/` |
| BaseLinker | tylko odczyt i porównanie (`baselinker-rozbieznosci`) |
| Ustawienia sklepu, płatności, zwroty i anulowanie, rynki, dostawy, aplikacje, pracownicy, karty podarunkowe, operacje masowe w tle | zablokowane |

## Dokumentacja Shopify w projekcie

- **MCP `shopify-dev`** (`.mcp.json`: `cmd /c npx -y @shopify/dev-mcp@latest`), zatwierdzony w `.claude/settings.json` (`enabledMcpjsonServers`),
  narzędzia `mcp__shopify-dev__*` bez pytania (dokumentacja, walidacja GraphQL i Liquid).
- **Wtyczka Shopify AI Toolkit** (`shopify-plugin@shopify-ai-toolkit`), zadeklarowana w `.claude/settings.json` (`extraKnownMarketplaces` z `autoUpdate`,
  `enabledPlugins`), instalowana przez `install.ps1` (`claude plugin install ... --scope local`). Telemetria wyłączona (`OPT_OUT_INSTRUMENTATION`).
- Konektor Shopify z claude.ai (`mcp__claude_ai_Shopify`) jest zablokowany: do sklepu idziemy wyłącznie przez Shopify CLI i nasze skrypty.

## Zabezpieczenia

1. **Konto pracownika w Shopify** (bez płatności, rozliczeń, pracowników) + token CLI z jawną listą scope'ów (INSTALACJA, kroki 6 i 7).
2. **`.claude/settings.json`**:
   - **blokada**: `rm -rf` i podobne, `del /s`, `rd /s`, `format`, `git push --force`, `git reset --hard`, `git clean`,
     `shopify theme push/publish/delete/rename/share/dev/duplicate/console`, `shopify app ...`, `shopify auth logout`, uruchamianie `szablon_wgraj.py`,
     odczyt `.env`, edycja `.claude/`, `scripts/`, `seo/`, `CLAUDE.md`, `.mcp.json`, `install.ps1`, `robocze/motyw/` i plików systemowych,
     konektor `mcp__claude_ai_Shopify`; tryby `bypassPermissions` i `auto` wyłączone;
   - **pytanie o zgodę**: każda komenda z `--allow-mutations`, `shopify store auth`, `shopify theme pull`, `git add/commit/push`, `pip`, `npm`, `winget`,
     `rm`, `mv`, `Remove-Item`, `Set-Content`, zapis plików poza katalogami roboczymi;
   - **bez pytania**: odczyty, `scripts/*` bez `--allow-mutations`, narzędzia SEO (`seo/scripts`, `seo/shopify`), MCP `shopify-dev`,
     skrypty dokumentacji wtyczki, `WebFetch` dla florina.pl i dokumentacji, zapis w `backup/`, `raporty/`, `robocze/`, `dziennik/`.
3. **Hook `.claude/hooks/straznik.py`** (PreToolUse dla Bash i PowerShell; przy awarii blokuje) + **`polityka_zmian.py`**:
   - **zakaz**: `theme*` / `onlineStoreTheme*` (motyw), `shop*` (ustawienia, polityki, języki), płatności, `refund*`, `orderCancel`, `orderCapture`,
     `transaction*`, `market*`, `delivery*`, `location*`, `app*`, `webhook*`, `staff*`, `bulkOperation*`, `giftCard*`; obiekty `OnlineStoreTheme`, `Shop`, `Location`...;
     więcej niż 250 obiektów w jednej zmianie; zmiany poza skryptami `scripts/` (własne skrypty, `curl` do Admin API); zapis do BaseLinkera;
     uruchomienie `scripts/szablon_wgraj.py` przez Claude;
   - **pytanie z twardym ostrzeżeniem** („UWAGA, USUWANIE W SKLEPIE”): każde `*Delete`, `*Remove*` (poza `tagsRemove`), `*Unpublish`;
   - **pytanie** („ZMIANA W SKLEPIE”) dla całej reszty, z dopiskiem ostrzeżeń przy polach `handle`, `status`, `category` (VAT), `price`, `ruleSet`, `quantities`.
4. **`scripts/shopify_gql.py`** w chwili wysyłki: ta sama polityka, **wymóg dzisiejszego backupu** zmienianych obiektów (przy usuwaniu: wszystkich obiektów w zmianie),
   log w `dziennik/zmiany.log`, wersja API przypięta (2026-07).
5. **Ścieżka szablonu**: `scripts/szablon_pobierz.py` (Claude, odczyt) przygotowuje `robocze/szablon/<data>-<nazwa>/`; `scripts/szablon_wgraj.py`
   uruchamia człowiek (terminal VS Code albo `!` w Claude w terminalu): kontrola konfliktu z edytorem, backup plików motywu, zapis, weryfikacja, komenda cofnięcia.
   Komendy wpisane przez człowieka nie są wywołaniem narzędzia przez Claude, więc nie przechodzą przez hook PreToolUse (ten działa tylko na wywołania Claude).

Test: `python .claude/hooks/test_straznik.py` (38 przypadków; uruchamia go też instalator).

Ograniczenie: reguły i hook dopasowują tekst komend, więc nie są granicą bezpieczeństwa w sensie informatycznym. Twardą granicą są uprawnienia konta i scope'y.

## Struktura

```
CLAUDE.md                     zasady dla Claude (po polsku, dla początkującego użytkownika)
INSTALACJA.md / install.ps1   instalacja krok po kroku / instalator Windows
.mcp.json                     serwer dokumentacji Shopify (shopify-dev)
.env.example                  szablon (SHOPIFY_STORE, SHOPIFY_API_VERSION, BASELINKER_TOKEN)
requirements.txt              biblioteki Pythona (narzędzia SEO)
.claude/settings.json         uprawnienia, hook, MCP, wtyczka
.claude/hooks/                straznik.py, polityka_zmian.py, test_straznik.py
.claude/skills/               11 skilli (w tym seo i zmiany-w-szablonie)
.claude/agents/seo-strateg.md agent SEO
scripts/                      shopify_gql.py, backup_produktu.py, struktura_sklepu.py, cechy.py, upload_mediow.py,
                              base_shopify_roznice.py, szablon_pobierz.py, szablon_wgraj.py (tylko człowiek), wspolne.py
seo/                          toolkit SEO: resources/ (skille, agenci, referencje, szablony), scripts/ (ok. 70), shopify/ (metodyka + crawler)
backup/ raporty/ robocze/ dziennik/ docs/   dane lokalne (poza repozytorium)
```

Toolkit SEO pochodzi z paczki SEO Igora (licencja w `seo/LICENSE`). Usunięto z niego pomiar PageSpeed Insights / Lighthouse przez API
(brak klucza; wiedza o CWV została jako referencja), moduły GitHub, przykłady i narzędzia migracji z danymi innych klientów.

## Dla Igora

- Polityka zmian: `.claude/hooks/polityka_zmian.py` (po zmianie: `python .claude/hooks/test_straznik.py`).
- Lekcje zebrane u klienta: `dziennik/lekcje.md` na jego komputerze; stałe przenoś do skilli.
- Punkty **DO POTWIERDZENIA** w skillach (grep po tej frazie) uzupełnij po pierwszej sesji na sklepie.
