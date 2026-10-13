---
name: zmiany-w-szablonie
description: Zmiany w szablonie (motywie) sklepu Florina: wygląd, sekcje, bloki, kod Liquid, CSS, JavaScript, pliki templates/*.json, nagłówek, stopka, strona główna, dane strukturalne w kodzie, „edytuj w edytorze motywu”. Claude NIE wgrywa takich zmian sam: przygotowuje kompletną zmianę z backupem i jedną komendą, którą uruchamia człowiek (prefiks `!` albo terminal VS Code). Używaj zawsze, gdy prośba dotyczy wyglądu lub kodu sklepu albo gdy strażnik zablokował operację na motywie.
---

# Zmiany w szablonie (motywie): ścieżka „człowiek uruchamia”

Motyw to kod, który widzi każdy klient sklepu. Dlatego Claude ma **zablokowane** wszystkie zapisy w motywie
(`shopify theme push/publish/...`, mutacje `theme*`, skrypt `scripts/szablon_wgraj.py`). Claude **przygotowuje** zmianę,
a **wgrywa ją człowiek** jedną komendą. Odczyt motywu jest dozwolony.

Motyw live (stan 06.10.2026): **Purevea 2.1.0, „Florentyna/main”**. Sprawdź aktualny: `python scripts/szablon_pobierz.py --lista`.

## Jak rozpoznać, że to zmiana w szablonie

„zmień wygląd”, „dodaj sekcję / baner / blok”, „przesuń”, „kolor przycisku”, „czcionka”, „na stronie głównej”, „w edytorze motywu”,
„nagłówek / stopka / menu wygląda”, „dodaj kod”, „dane strukturalne w motywie”, „dlaczego na stronie jest X” (gdy X pochodzi z kodu).
Uwaga: **treści** (opis produktu, opis kategorii, FAQ, cechy, menu jako lista linków, strony, blog) to nie szablon: idą zwykłą ścieżką ze zgodą.
Najpierw sprawdź, czy da się to zrobić **bez kodu**: ustawieniem sekcji w edytorze motywu, które użytkownik kliknie sam. Jeśli tak, podaj instrukcję klik po kliku.

## Rytm (zawsze ten sam)

1. **Ustal cel i miejsce.** Który szablon / sekcja (np. `sections/main-collection.liquid`, `templates/collection.json`).
   Znajdź plik: pobierz kandydatów do odczytu i przeszukaj. Nie zgaduj klas i nazw sekcji: czytaj realny kod.
2. **Pobierz aktualny stan** (tylko odczyt):
   ```
   python scripts/szablon_pobierz.py --motyw live --pliki <ścieżka1> <ścieżka2> --zmiana <krótka-nazwa>
   ```
   Powstaje `robocze/szablon/RRRR-MM-DD-<nazwa>/` z `oryginal/`, `pliki/` (do edycji), `_baza.json` (sumy kontrolne), `OPIS.md`.
3. **Wprowadź zmianę tylko w `pliki/`** (nigdy w `oryginal/`). Liquid i JSON sprawdź narzędziem `mcp__shopify-dev__validate`
   (Liquid: `context: theme`, poprawny `fileType`) albo skillem wtyczki Shopify. Szablony `templates/*.json` i `config/settings_data.json`
   zmieniaj minimalnie (tylko potrzebne klucze), bo edytor motywu zapisuje cały plik.
4. **Uzupełnij `OPIS.md`**: co się zmieni (prostymi słowami), dlaczego, jak sprawdzić w sklepie (konkretny adres), jak cofnąć.
5. **Pokaż różnice**: `git diff --no-index robocze/szablon/<katalog>/oryginal robocze/szablon/<katalog>/pliki`
   i wyjaśnij je zdaniem albo dwoma. Zapytaj o zgodę na tę konkretną zmianę.
6. **Przekaż komendy człowiekowi** (gotowe do wklejenia, z pełną ścieżką katalogu):
   - podgląd (nic nie zmienia): `python scripts/szablon_wgraj.py robocze/szablon/<katalog>`
   - wgranie: `python scripts/szablon_wgraj.py robocze/szablon/<katalog> --wgraj`
   Instrukcja dla użytkownika (powiedz ją wprost):
   - „Najpierw zamknij edytor motywu w przeglądarce, u siebie i u innych osób (zapis w edytorze nadpisuje plik).”
   - „Otwórz terminal w VS Code (menu Terminal, Nowy terminal), wklej pierwszą komendę, Enter, przeczytaj podgląd. Potem wklej drugą.”
   - Alternatywa: jeśli pracujecie w Claude Code w trybie terminala (komenda `claude` w terminalu), wklej komendę z prefiksem `!`,
     np. `! python scripts/szablon_wgraj.py robocze/szablon/<katalog> --wgraj`. **W panelu czatu rozszerzenia VS Code prefiks `!` nie działa**
     (dokumentacja Claude Code: „`!` Bash shortcut: CLI tak, rozszerzenie VS Code nie”).
7. Skrypt sam: sprawdza, czy pliki w sklepie nie zmieniły się od przygotowania (jeśli tak, STOP: przygotuj od nowa), robi backup do
   `backup/RRRR-MM-DD/motyw-<id>-<godzina>/`, wgrywa, sprawdza odczytem i wypisuje komendę cofnięcia.
8. **Po wgraniu** (użytkownik napisze „zrobione” albo zobaczysz wynik `!` w rozmowie): sprawdź odczytem
   (`szablon_pobierz.py` do nowego katalogu `...-weryfikacja` i porównanie z `pliki/`), obejrzyj stronę (`curl -sL <adres>?v=<losowa liczba>`,
   pamięć podręczna sklepu potrafi chwilę serwować starą wersję), wpis w dzienniku (skill `dziennik-zmian`).

## Cofnięcie

Komenda z wyniku wgrania, uruchamiana przez człowieka tak samo:
```
python scripts/szablon_wgraj.py --cofnij backup/RRRR-MM-DD/motyw-<id>-<godzina> --wgraj
```
Przywraca pliki z backupu, a pliki dodane zmianą usuwa.

## Zasady bezpieczeństwa przy motywie LIVE

- Zawsze świeże pobranie tego samego dnia, tuż przed zmianą (skrypt i tak blokuje wgranie na zmienionym w międzyczasie pliku).
- Edytor motywu zamknięty u wszystkich osób na czas wgrania; po wgraniu przed ponownym otwarciem edytora odśwież stronę edytora.
- Większe zmiany (nowa sekcja, przebudowa strony): najpierw na **kopii motywu** (użytkownik robi w panelu: Sklep internetowy, Motywy, przy motywie
  live „...”, Duplikuj), wtedy `--motyw <id kopii>`, sprawdzenie w podglądzie, dopiero potem to samo na live.
- Nie zmieniaj publikacji motywu, nie usuwaj motywów (to robi Igor w panelu).
- Gdy zmiana dotyczy wielu plików albo nie jesteś pewien skutków: przygotuj, opisz i zaproponuj, żeby wgrał Igor.

## Dlaczego tak (do wyjaśnienia użytkownikowi, jeśli zapyta)

Komendy wpisane przez człowieka z prefiksem `!` albo w zwykłym terminalu nie są wywołaniem narzędzia przez Claude, więc nie przechodzą
przez blokady Claude (hook PreToolUse działa tylko wtedy, gdy narzędzie wywołuje Claude). Dzięki temu Claude nie może sam zmienić wyglądu sklepu,
a człowiek może, świadomie, jedną komendą, z backupem i podglądem.
