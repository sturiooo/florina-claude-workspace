# Instalacja: Claude Code dla sklepu Florina (Windows)

Czas: ok. 45 minut. Potrzebne: komputer z Windows 10/11, konto Claude (Pro, Max albo Team),
konto pracownika w Shopify Floriny, dostęp do panelu BaseLinkera (do wygenerowania klucza).

## 0. Przed wizytą (Igor)

- [ ] Konto pracownika w Shopify dla nowej osoby z uprawnieniami z kroku 6 (szerokie, ale bez płatności, rozliczeń i zarządzania pracownikami).
- [ ] Osobny użytkownik w BaseLinkerze z uprawnieniami tylko do podglądu (krok 8).
- [ ] Konto Claude dla tej osoby (Pro albo w zespole Team).

## 1. VS Code

Zainstaluj Visual Studio Code ze strony code.visualstudio.com (albo `winget install Microsoft.VisualStudioCode`).
Przy instalacji zaznacz „Dodaj do PATH” i „Otwórz za pomocą Code”.

## 2. Folder projektu (pobranie paczki)

Repozytorium jest prywatne. Na komputerze klienta najprościej:

```powershell
cd $env:USERPROFILE\Documents
winget install GitHub.cli -e
gh auth login            # zaloguj się kontem Igora (tylko na chwilę)
gh repo clone sturiooo/florina-claude-workspace florina-claude
gh auth logout           # wyloguj Igora z tego komputera
cd florina-claude
git remote remove origin # klient nie wysyła nic do repozytorium Igora
```

Bez logowania na GitHub u klienta: Igor pobiera ZIP na swoim komputerze
(`gh api repos/sturiooo/florina-claude-workspace/zipball > florina-claude.zip`), przenosi pendrivem i rozpakowuje do `Dokumenty\florina-claude`.

## 3. Instalator

W folderze projektu otwórz PowerShell (w Eksploratorze: pasek adresu, wpisz `powershell`, Enter) i uruchom:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Skrypt (można go uruchamiać wiele razy):
1. sprawdza `winget`,
2. instaluje brakujące: Git, Node.js LTS, Python 3.12, GitHub CLI (pomiń: `-BezGitHubCli`),
3. Shopify CLI (`npm install -g @shopify/cli`),
4. Claude Code (oficjalny instalator: `irm https://claude.ai/install.ps1 | iex`, zapasowo `winget install Anthropic.ClaudeCode`),
5. rozszerzenie Claude Code w VS Code (`anthropic.claude-code`),
6. wtyczkę **Shopify AI Toolkit**: `claude plugin marketplace add Shopify/shopify-ai-toolkit` i `claude plugin install shopify-plugin@shopify-ai-toolkit --scope local`,
7. biblioteki Pythona dla narzędzi SEO (`seo/requirements.txt`: requests, beautifulsoup4, lxml),
8. `.env` z `.env.example` i katalogi robocze,
9. test zabezpieczeń (`python .claude\hooks\test_straznik.py`),
10. wypisuje wersje.

Na końcu musi być `[OK] Straznik dziala poprawnie`. Jeśli nie: **nie używaj projektu**, najpierw napraw Pythona (patrz „Problemy”).
Jeśli coś się nie zainstaluje: zamknij okno, otwórz nowe i uruchom ponownie (Windows odświeża PATH dopiero w nowym oknie).

## 4. Pierwsze otwarcie w VS Code: logowanie, zaufanie, MCP, wtyczka

1. VS Code: Plik, Otwórz folder, wskaż `florina-claude`. Kliknij ikonę Claude na pasku bocznym (albo Ctrl+Esc) i zaloguj się kontem Claude.
2. **„Czy ufasz temu folderowi?”: Tak.** Bez tego Claude Code nie wczyta reguł, hooka, skilli, wtyczki ani serwera MCP z projektu.
3. **Serwer dokumentacji Shopify (`.mcp.json`, serwer `shopify-dev`)**: plik w projekcie uruchamia `cmd /c npx -y @shopify/dev-mcp@latest`
   (`cmd /c` to zalecany sposób uruchamiania `npx` na Windows). Ustawienie `enabledMcpjsonServers: ["shopify-dev"]` w `.claude/settings.json`
   zatwierdza ten serwer **dopiero w zaufanym folderze** (w niezaufanym serwer czeka jako „Pending approval”). Jeśli mimo to pojawi się
   pytanie o serwer `shopify-dev`, zatwierdź. Sprawdzenie: wpisz w czacie `/mcp`, serwer `shopify-dev` ma status „connected”
   (pierwsze uruchomienie pobiera pakiet przez `npx`, może potrwać do minuty). Narzędzia `mcp__shopify-dev__*` działają bez pytania.
4. **Wtyczka Shopify AI Toolkit** (`shopify-plugin@shopify-ai-toolkit`): w `.claude/settings.json` są `extraKnownMarketplaces` (z `autoUpdate: true`)
   i `enabledPlugins`. Według dokumentacji Claude Code:
   - po zaufaniu folderowi Claude Code sam pobiera w tle katalog wtyczek zadeklarowany w projekcie (może pokazać „Plugins changed. Run /reload-plugins”),
   - samo `enabledPlugins` w pliku projektu **nie instaluje** wtyczki na nowym komputerze („enabled in project settings but isn't installed here”),
     dlatego instalator robi to komendą `claude plugin install ... --scope local` (wpis w `.claude/settings.local.json`, poza repozytorium),
   - ta wtyczka ma źródło wewnątrz katalogu (`"source": "./"`), więc gdy katalog jest już pobrany, ładuje się bez osobnej kopii.
   Sprawdzenie: wpisz w czacie `/plugins` (lista „Manage plugins”: `shopify-plugin` zainstalowany i włączony). Jeśli go nie ma: na zakładce
   Plugins wyszukaj `shopify-plugin` i kliknij Install (zakres „Install locally”), albo w terminalu:
   `claude plugin install shopify-plugin@shopify-ai-toolkit --scope local`, potem w czacie `/reload-plugins`.
   Telemetria wtyczki i serwera MCP jest wyłączona (`OPT_OUT_INSTRUMENTATION=true` w ustawieniach projektu i `.mcp.json`).
5. Napisz w czacie: „Jakie masz zasady pracy w tym sklepie?”. Odpowiedź powinna streszczać `CLAUDE.md` (plan, podgląd, zgoda, backup, szablon przez człowieka).

## 5. Ważne: panel czatu w VS Code a komendy z `!`

W panelu czatu rozszerzenia VS Code **prefiks `!` nie działa** (dokumentacja Claude Code, tabela „VS Code extension vs. CLI”: „`!` Bash shortcut: CLI tak, rozszerzenie nie”).
Zmiany w szablonie (motywie), które Claude przygotuje, wgrywasz więc jedną komendą **w terminalu VS Code** (menu Terminal, Nowy terminal, wklej, Enter).
Kto woli pracować w Claude w terminalu (komenda `claude` w terminalu VS Code), może wkleić tę samą komendę z prefiksem `!`.

## 6. Konto pracownika w Shopify

Panel Shopify Floriny: Ustawienia, Użytkownicy, Dodaj pracownika (dokładne nazwy uprawnień **do potwierdzenia w panelu**, Shopify je zmienia).

**Zaznacz:**
- Strona główna, Produkty (wszystkie, w tym ceny, koszty, stany, import i eksport), Kolekcje, Zapasy,
- Zamówienia (wyświetlanie i edycja, tagi, notatki), Wersje robocze zamówień,
- Klienci (wyświetlanie i edycja),
- Rabaty, Marketing (jeśli potrzebne),
- Treści: Strony, Blog, Pliki, Metaobiekty (wpisy i definicje), Nawigacja (menu i przekierowania),
- Sklep internetowy z **Motywami** (potrzebne do ścieżki `!` dla szablonu, wgrywa człowiek), Tłumaczenia,
- Analityka i raporty.

**Nie zaznaczaj:**
- Ustawienia sklepu: płatności, rozliczenia (billing), plan, dane sklepu,
- zarządzanie pracownikami i uprawnieniami,
- przeniesienie własności i zamknięcie sklepu,
- zarządzanie aplikacjami (chyba że krok 7 tego wymaga, patrz niżej),
- zwroty pieniędzy i anulowanie zamówień (jeśli panel pozwala to odznaczyć osobno).

Logowanie Shopify CLI tworzy token w imieniu zalogowanej osoby, więc ten token ma najwyżej uprawnienia tego konta.
**Do potwierdzenia na miejscu:** czy konto pracownika bez uprawnień do aplikacji może zatwierdzić logowanie CLI. Jeśli nie:
(a) nadaj na chwilę uprawnienie do aplikacji, zaloguj, odbierz; (b) zaloguj Igora, ale wtedy token ma uprawnienia Igora i hamulcem zostaje tylko strażnik w projekcie.

## 7. Logowanie do sklepu (Shopify CLI)

W terminalu VS Code wklej w całości:

```powershell
shopify store auth --store florina-pl.myshopify.com --scopes read_products,write_products,read_inventory,write_inventory,read_locations,read_orders,write_orders,read_order_edits,write_order_edits,read_draft_orders,write_draft_orders,read_customers,write_customers,read_discounts,write_discounts,read_content,write_content,read_online_store_pages,write_online_store_pages,read_online_store_navigation,write_online_store_navigation,read_publications,write_publications,read_files,write_files,read_metaobjects,write_metaobjects,read_metaobject_definitions,write_metaobject_definitions,read_translations,write_translations,read_locales,read_themes,write_themes,read_reports
```

Otworzy się przeglądarka: zaloguj się **kontem pracownika z kroku 6** i zatwierdź. Sprawdzenie: `python scripts\shopify_gql.py -q "{ shop { name } }"`.

| Scope | Po co |
|---|---|
| `read_products`, `write_products` | produkty, warianty, ceny, kolekcje, tagi, opisy, metapola produktów i kolekcji, media produktu |
| `read_inventory`, `write_inventory`, `read_locations` | stany magazynowe (zmiana i porównanie z Base) |
| `read_orders`, `write_orders` | zamówienia z ostatnich 60 dni: edycja danych, tagi, notatki (zwroty i anulowanie blokuje strażnik) |
| `read_order_edits`, `write_order_edits` | edycja pozycji zamówienia |
| `read_draft_orders`, `write_draft_orders` | wersje robocze zamówień |
| `read_customers`, `write_customers` | klienci (dane, tagi, notatki) |
| `read_discounts`, `write_discounts` | rabaty |
| `read_content`, `write_content`, `read_online_store_pages`, `write_online_store_pages` | strony, blog, artykuły (`write_online_store_pages` to nowsza alternatywa dla `write_content`) |
| `read_online_store_navigation`, `write_online_store_navigation` | menu i przekierowania 301 |
| `read_publications`, `write_publications` | publikacja produktów i kolekcji w kanałach sprzedaży |
| `read_files`, `write_files` | zdjęcia, wideo, pliki |
| `read_metaobjects`, `write_metaobjects`, `read_metaobject_definitions`, `write_metaobject_definitions` | FAQ i inne metaobiekty, także ich struktura |
| `read_translations`, `write_translations`, `read_locales` | tłumaczenia (jeśli sklep ma drugi język) |
| `read_themes`, `write_themes` | odczyt motywu przez Claude; zapis tylko ścieżką `!` / terminal (Claude ma zapis zablokowany) |
| `read_reports` | raporty ShopifyQL (analityka) |

Osobnego scope'u na metapola nie ma (`write_metafields` nie istnieje): metapola zapisuje się w ramach scope'u właściciela (produkty, klienci, zamówienia...).
Definicje metapól produktów i kolekcji wymagają `write_products`. Celowo **nie ma**: płatności, Shopify Payments, rynków, dostaw, lokalizacji (zapis),
aplikacji, pracowników, kart podarunkowych.

Gdy po kilku dniach pojawi się błąd logowania („Token refresh failed”, „No stored app authentication”), powtórz ten krok.

## 8. Klucz BaseLinkera (tylko odczyt)

1. W BaseLinkerze utwórz osobnego użytkownika (pracownika) z uprawnieniami **tylko do podglądu** produktów (katalog) i zamówień
   (ścieżka w panelu Base **do potwierdzenia**).
2. Zaloguj się jako ten użytkownik i wygeneruj token API (Moje konto, API). Token działa z uprawnieniami użytkownika, który go wygenerował.
3. W VS Code otwórz `.env`, wklej token po `BASELINKER_TOKEN=` i zapisz (Ctrl+S). **Nie wklejaj tokenu do czatu.**
4. Sprawdzenie w czacie: „Pokaż katalogi i magazyny w Base”.

## 9. Pierwsza sesja (razem z Igorem)

1. „Uruchom rozpoznanie struktury sklepu” → `docs/struktura-sklepu.md`.
2. Potwierdźcie punkty **DO POTWIERDZENIA** ze skilli (FAQ, dłuższy opis kategorii, magazyn i grupa cen w Base) → `dziennik/lekcje.md`.
3. Ćwiczenie na jednym produkcie (tag albo cecha) z pełnym rytmem: plan, podgląd, zgoda, backup, zapis, weryfikacja, dziennik.
4. Ćwiczenie ze szablonem: poproś o drobną zmianę wyglądu na **kopii motywu**; Claude przygotuje komendę, użytkownik wklei ją w terminalu.
5. Pokaz blokad: „opublikuj motyw” albo „zrób zwrot dla zamówienia” (Claude odmawia, strażnik blokuje) oraz „usuń ten produkt”
   (Claude proponuje archiwum, a przy usunięciu okno „UWAGA, USUWANIE”).
6. Pokaz SEO: „Zrób audyt SEO kategorii Garnki” (agent `seo-strateg`, raport w `raporty/seo/`).

## Problemy

| Objaw | Co zrobić |
|---|---|
| `python` otwiera Microsoft Store albo „nie rozpoznano” | Ustawienia, Aplikacje, Zaawansowane ustawienia aplikacji, Aliasy wykonywania aplikacji: wyłącz `python.exe` i `python3.exe`; nowe okno; `install.ps1` ponownie |
| `claude` / `shopify` „nie rozpoznano” | zamknij wszystkie okna PowerShell i VS Code, otwórz ponownie (PATH) |
| Każda komenda w Claude jest blokowana komunikatem o hooku | strażnik nie może się uruchomić (zwykle Python). `python .claude\hooks\test_straznik.py` w terminalu powie, co jest nie tak |
| `/mcp`: `shopify-dev` „failed” albo „pending” | folder niezaufany (zaufaj i uruchom ponownie) albo brak Node.js (`node --version`) |
| `/plugins`: brak `shopify-plugin` | `claude plugin install shopify-plugin@shopify-ai-toolkit --scope local` w terminalu, potem `/reload-plugins` |
| „Brak dzisiejszego backupu dla: ...” | tak ma być: najpierw backup (`python scripts/backup_produktu.py ...`), Claude zrobi to sam |
| „No stored app authentication” / „Token refresh failed” | krok 7 jeszcze raz |
| `ERROR_BAD_TOKEN` z BaseLinkera | zły token w `.env` (spacje, cudzysłowy, stary token) |
| `szablon_wgraj.py`: „STOP: te pliki zmieniły się w sklepie” | ktoś zapisał motyw w edytorze w międzyczasie: poproś Claude o przygotowanie zmiany od nowa |
| Błąd certyfikatu w narzędziach SEO | dodaj `--insecure` do `seo/shopify/seo_audit_crawl.py` (stary magazyn certyfikatów Pythona na Windows) |
| Zmiany nie widać od razu | podgląd sklepu bywa z pamięci podręcznej: odśwież po minucie, dodaj `?v=1` do adresu |
