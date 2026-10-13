# Instalacja: Claude Code dla sklepu Florina (Windows)

Czas: ok. 30 do 45 minut. Potrzebne: komputer z Windows 10/11, konto Claude (Pro, Max albo Team),
konto pracownika w Shopify Floriny, dostęp do panelu BaseLinkera (do wygenerowania klucza).

## 0. Przed wizytą (Igor)

- [ ] Konto pracownika w Shopify dla nowej osoby, z **ograniczonymi uprawnieniami** (krok 5). To najważniejsze zabezpieczenie: nawet gdyby wszystko inne zawiodło, Shopify nie pozwoli zrobić więcej, niż pozwala konto.
- [ ] Osobny użytkownik w BaseLinkerze z uprawnieniami tylko do podglądu (krok 7).
- [ ] Konto Claude dla tej osoby (Pro lub w zespole Team).

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

Bez GitHuba: Igor pobiera ZIP na swoim komputerze (`gh repo archive` nie istnieje, użyj
`gh api repos/sturiooo/florina-claude-workspace/zipball > florina-claude.zip`), przenosi pendrivem i rozpakowuje do `Dokumenty\florina-claude`.

## 3. Instalator

W folderze projektu otwórz PowerShell (w Eksploratorze: pasek adresu, wpisz `powershell`, Enter) i uruchom:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Skrypt instaluje brakujące: Git, Node.js LTS, Python 3.12, GitHub CLI (pomiń: `-BezGitHubCli`), Shopify CLI (npm),
Claude Code (oficjalny instalator Anthropic: `irm https://claude.ai/install.ps1 | iex`, zapasowo winget),
rozszerzenie Claude Code w VS Code, tworzy `.env` i katalogi robocze, uruchamia test zabezpieczeń i wypisuje wersje.
Można go uruchamiać wiele razy. Jeśli coś się nie zainstaluje: zamknij okno, otwórz nowe i uruchom ponownie (Windows odświeża PATH dopiero w nowym oknie).

Na końcu musi być: `[OK] Straznik dziala poprawnie`. Jeśli nie: **nie używaj projektu**, najpierw napraw Pythona (patrz „Problemy”).

## 4. Logowanie do Claude

1. VS Code: Plik, Otwórz folder, wskaż `florina-claude`.
2. Kliknij ikonę Claude na pasku bocznym (albo Ctrl+Esc). Zaloguj się kontem Claude w przeglądarce.
3. Przy pierwszym otwarciu folderu VS Code / Claude zapyta, czy ufasz temu folderowi: **tak** (inaczej nie wczytają się zabezpieczenia i skille).
4. Napisz w okienku Claude: „Jakie masz zasady pracy w tym sklepie?”. Odpowiedź powinna streszczać `CLAUDE.md` (plan, podgląd, zgoda, backup...).

## 5. Konto pracownika w Shopify (ograniczone uprawnienia)

Panel Shopify Floriny: Ustawienia, Użytkownicy, Dodaj pracownika. Zaznacz tylko (dokładne nazwy uprawnień **do potwierdzenia w panelu**, Shopify je zmienia):
- Produkty: wyświetlanie i edycja produktów, **bez** usuwania, **bez** edycji cen i kosztów, **bez** zarządzania stanami,
- Kolekcje (w ramach produktów): edycja,
- Pliki: wgrywanie,
- Sklep internetowy: **bez** motywów (bez edycji kodu i publikacji),
- Zamówienia, Klienci, Rabaty, Ustawienia, Płatności, Aplikacje: **brak**.

Logowanie Shopify CLI tworzy token w imieniu zalogowanej osoby, więc ten token ma najwyżej uprawnienia tego konta.
**Do potwierdzenia jutro:** czy konto pracownika bez uprawnień do aplikacji może zatwierdzić logowanie CLI. Jeśli nie, jedna z dwóch opcji:
(a) nadaj na chwilę uprawnienie do aplikacji, zaloguj, odbierz; (b) zaloguj Igora, ale wtedy token ma uprawnienia Igora i hamulcem zostaje tylko strażnik w projekcie.

## 6. Logowanie do sklepu (Shopify CLI)

W terminalu VS Code (Terminal, Nowy terminal) wklej w całości:

```powershell
shopify store auth --store florina-pl.myshopify.com --scopes read_products,write_products,read_files,write_files,read_metaobjects,write_metaobjects,read_metaobject_definitions,read_inventory,read_orders,read_translations,write_translations,read_locales
```

Otworzy się przeglądarka: zaloguj się **kontem pracownika z kroku 5** i zatwierdź. Sprawdzenie:

```powershell
python scripts\shopify_gql.py -q "{ shop { name } }"
```

Zakres uprawnień tokenu (minimalny dla tego projektu):

| Scope | Po co |
|---|---|
| `read_products`, `write_products` | produkty, kolekcje, tagi, opisy, metapola produktów i kolekcji, media produktu |
| `read_files`, `write_files` | wgrywanie zdjęć i wideo |
| `read_metaobjects`, `write_metaobjects` | wpisy FAQ |
| `read_metaobject_definitions` | odczyt struktury FAQ (bez zmiany struktury) |
| `read_inventory` | stany do porównania z BaseLinkerem |
| `read_orders` | zamówienia do porównania z BaseLinkerem (tylko odczyt, ostatnie 60 dni) |
| `read_translations`, `write_translations`, `read_locales` | opcjonalnie: tłumaczenia opisów, jeśli sklep ma drugi język. Bez tłumaczeń usuń te trzy |

Celowo **nie ma**: `write_orders`, `write_customers`, `write_discounts`, `write_themes`, `write_inventory`, `write_publications`,
`write_metaobject_definitions`, `write_online_store_navigation`, `read_customers`.

W Claude Code to samo logowanie można zrobić bez terminala, wpisując w okienku Claude wiadomość zaczynającą się od `!` (np. `! shopify store auth ...`).
Gdy po kilku dniach pojawi się błąd logowania („Token refresh failed”, „No stored app authentication”), powtórz ten krok.

## 7. Klucz BaseLinkera (tylko odczyt)

1. W BaseLinkerze utwórz osobnego użytkownika (pracownika) z uprawnieniami **tylko do podglądu** produktów (katalog) i zamówień, bez edycji
   (Ustawienia konta, Pracownicy / Uprawnienia: dokładna ścieżka **do potwierdzenia w panelu Base**).
2. Zaloguj się jako ten użytkownik i wygeneruj token API (Moje konto, API). Token API w Base działa z uprawnieniami użytkownika, który go wygenerował.
3. W VS Code otwórz plik `.env` (lewy panel), wklej token po `BASELINKER_TOKEN=` i zapisz (Ctrl+S).
   **Nie wklejaj tokenu do czatu z Claude.** Claude nie ma dostępu do odczytu `.env` (blokada), skrypty czytają go same.
4. Sprawdzenie: w okienku Claude napisz „Pokaż katalogi i magazyny w Base” (uruchomi `python scripts/base_shopify_roznice.py --lista`).

## 8. Pierwsza sesja (razem z Igorem)

1. „Uruchom rozpoznanie struktury sklepu”: powstanie `docs/struktura-sklepu.md`.
2. Potwierdźcie razem punkty oznaczone w skillach jako **DO POTWIERDZENIA** (FAQ: typ metaobiektu i metapole kolekcji; dłuższy opis kategorii; magazyn i grupa cen w Base) i zapiszcie wyniki w `dziennik/lekcje.md`.
3. Ćwiczenie na jednym produkcie: zmiana tagu albo jednej cechy, z pełnym rytmem (plan, podgląd, zgoda, backup, zapis, weryfikacja, dziennik). Pokaż okno potwierdzenia i co znaczy „ZMIANA W SKLEPIE”.
4. Pokaż blokadę w akcji: poproś Claude „usuń ten produkt”. Ma odmówić, a strażnik zablokować.

## Problemy

| Objaw | Co zrobić |
|---|---|
| `python` otwiera Microsoft Store albo „nie rozpoznano” | Ustawienia, Aplikacje, Zaawansowane ustawienia aplikacji, Aliasy wykonywania aplikacji: wyłącz `python.exe` i `python3.exe`; nowe okno; `install.ps1` ponownie |
| `claude` / `shopify` „nie rozpoznano” | zamknij wszystkie okna PowerShell i VS Code, otwórz ponownie (PATH) |
| Każda komenda w Claude jest blokowana z komunikatem o hooku | strażnik nie może się uruchomić (zwykle Python). `python .claude\hooks\test_straznik.py` w terminalu powie, co jest nie tak |
| „Brak dzisiejszego backupu dla: ...” | tak ma być: najpierw backup (`python scripts/backup_produktu.py ...`), Claude zrobi to sam |
| „No stored app authentication” / „Token refresh failed” | krok 6 jeszcze raz |
| `ERROR_BAD_TOKEN` z BaseLinkera | zły token w `.env` (spacje, cudzysłowy, stary token) |
| Zmiana w sklepie nie widać od razu | podgląd sklepu bywa z pamięci podręcznej: odśwież po minucie, dodaj `?v=1` do adresu |

## Co jest zablokowane i dlaczego

Opis zabezpieczeń: `README.md`, sekcja „Zabezpieczenia”. Listy dozwolonych i zakazanych zmian: `.claude/hooks/polityka_zmian.py`
(zmienia tylko Igor).
