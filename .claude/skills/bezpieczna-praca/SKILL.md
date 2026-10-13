---
name: bezpieczna-praca
description: Checklista przed każdą zmianą w sklepie Florina (opis, tag, kolekcja, cecha, FAQ, zdjęcie) i postępowanie, gdy coś zablokuje strażnik albo zmiana pójdzie źle. Używaj ZAWSZE przed pierwszą zmianą w sesji, przy każdej prośbie typu „zmień / dodaj / uzupełnij / popraw” w sklepie, gdy pojawi się okno potwierdzenia zmiany, gdy komenda zostanie zablokowana i gdy trzeba cofnąć zmianę.
---

# Bezpieczna praca na żywym sklepie

Sklep Floriny jest **żywy**: klienci kupują w nim w tej chwili. Każda zmiana jest od razu widoczna.
Użytkownik jest początkujący, więc to Ty pilnujesz procesu, a nie on.

## Checklista przed każdą zmianą (przejdź całą, w tej kolejności)

1. **Czy to jest w zakresie?** (CLAUDE.md, tabela „Zakres pracy”). Nie: powiedz, że to zadanie dla Igora.
2. **Czy wiem, gdzie to jest zapisane?** Sprawdź `docs/struktura-sklepu.md` (skill `struktura-sklepu`). Nie zgaduj nazw metapól.
3. **Policz skalę na danych**, nie na jednym przykładzie: ile produktów / kolekcji to dotyczy. Podaj liczbę użytkownikowi.
4. **Podgląd „przed / po”** w tabeli. Treści pokaż w całości. Przy zmianach tagów lub kolekcji automatycznych powiedz, co jeszcze się zmieni (np. produkt wypadnie z promocji).
5. **Wyraźna zgoda** użytkownika na TEN konkretny podgląd. „Rób” do innego zakresu to nie zgoda.
6. **Backup**: `python scripts/backup_produktu.py --id ... --powod "..."` (albo `--handle`, `--plik`, `--kolekcja`, `--metaobiekt`). Skrypty `cechy.py` i `upload_mediow.py` robią backup same.
7. **Próba na 1 obiekcie**, odczyt, pokazanie efektu, dopiero potem reszta partiami (do 20).
8. **Weryfikacja odczytem** po każdej partii (pobierz jeszcze raz, porównaj z planem).
9. **Dziennik**: wpis w `dziennik/RRRR-MM.md` (skill `dziennik-zmian`).
10. **Co sprawdzić w sklepie**: podaj użytkownikowi link `https://florina.pl/products/<uchwyt>` albo `https://florina.pl/collections/<uchwyt>`.

## Okno potwierdzenia zmiany

Przy każdej zmianie Claude Code pokaże okno z tekstem „ZMIANA W SKLEPIE: ...”. Zanim użytkownik kliknie:
- powiedz mu jednym zdaniem, co dokładnie się zmieni i na ilu obiektach,
- przypomnij: „Zatwierdź tylko, jeśli to zgadza się z podglądem, który widziałeś”.

Nigdy nie sugeruj opcji „zezwalaj zawsze” dla zmian w sklepie.

## Jak technicznie robić zmianę

- Zapytanie GraphQL zapisz w `robocze/<nazwa>.graphql`, zmienne w `robocze/<nazwa>.json`.
- Wykonaj: `python scripts/shopify_gql.py --query-file robocze/x.graphql --variable-file robocze/x.json --allow-mutations`.
- **Jeden rodzaj zmiany na wywołanie** (np. same `tagsAdd`), wtedy komunikaty są czytelne.
- Kod wyjścia 3 = Shopify odrzucił część zmiany (`userErrors`): przeczytaj błąd, powiedz użytkownikowi, nie ponawiaj w ciemno.

## Gdy strażnik coś zablokuje

Komunikat zaczyna się od powodu (np. „`productDelete` jest zablokowane”). Wtedy:
1. Nie obchodź blokady (inna komenda, własny skrypt, rozbicie na części, inny program). To jest twarda zasada.
2. Wyjaśnij użytkownikowi prostym językiem, co i dlaczego zostało zablokowane.
3. Zaproponuj notatkę dla Igora: co trzeba zrobić, na jakich produktach, dlaczego.

## Pułapki Shopify, które psują dane po cichu

- **`seo` nadpisuje cały obiekt**: wysłanie samego `seo: { title }` kasuje meta opis. Zawsze wysyłaj `title` i `description` razem (wartości z backupu, jeśli jednej nie zmieniasz).
- **`metafieldsSet` jest atomowy**: jeden zły element odrzuca całą partię, a `elementIndex` w błędzie potrafi wskazać zły element. Przy błędzie zmniejsz partię i znajdź winowajcę.
- **Pole listy (`list.*`) mieści maks. 128 elementów**, a zapis listy ZASTĘPUJE całą listę. Zawsze odczytaj obecną listę i dopisz do niej.
- **`collection.products` zwraca też produkty zarchiwizowane i wersje robocze**: licząc, filtruj po `status`.
- **Tagi sterują kolekcjami automatycznymi i promocjami**: dodanie lub usunięcie tagu może przenieść produkt do innej kategorii albo wyrzucić go z akcji (np. „3+1”). Zanim zmienisz tag, sprawdź w `docs/struktura-sklepu.md`, w których regułach kolekcji występuje.
- **Komunikat „sukces” to nie dowód.** Zawsze odczyt po zapisie.

## Cofanie zmiany

1. Znajdź backup: `backup/RRRR-MM-DD/<typ>-<uchwyt>-<godzina>.json` (pole `stan`).
2. Pokaż użytkownikowi, do jakiego stanu wracamy (przed / po).
3. Po zgodzie: nowy backup obecnego stanu, potem zapis wartości z pliku tą samą drogą co zmiana.
4. Czego NIE cofniesz sam: usuniętych mediów, zmian w motywie, zmian w Base. Wtedy: Igor.

## Sygnały, że trzeba przerwać i zawołać Igora

- liczba obiektów wyszła dużo większa, niż zakładał użytkownik,
- odczyt po zapisie nie zgadza się z planem,
- dane wyglądają na niespójne (np. dwa metapola o tym samym znaczeniu, oba wypełnione inaczej),
- prośba wymaga zmiany struktury (nowe metapole, nowa kolekcja, nowa sekcja w motywie).
