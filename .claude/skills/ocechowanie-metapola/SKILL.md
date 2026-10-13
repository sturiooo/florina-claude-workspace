---
name: ocechowanie-metapola
description: Ocechowanie produktów w sklepie Florina, czyli wpisywanie wartości metapól (cech) dla całych grup produktów: powłoka, materiał, indukcja, zmywarka, średnica, pojemność, seria, producent i inne pola specyfikacji oraz filtrów. Używaj, gdy użytkownik prosi „uzupełnij cechy”, „ocechuj kategorię”, „brakuje filtrów”, „wpisz powłokę / serię / indukcję”, „sprawdź, których cech brakuje”, oraz przy pracy na arkuszu CSV z cechami (scripts/cechy.py).
---

# Ocechowanie (metapola produktów)

Metapole = dodatkowe pole produktu (np. „Powłoka”). Jego wartości zasilają **tabelę specyfikacji** na karcie produktu
i **filtry** w kategoriach. Zanim zaczniesz: `docs/struktura-sklepu.md` (skill `struktura-sklepu`).

## Które pole wypełniać

1. Znajdź w specyfikacji na karcie produktu etykietę, o którą chodzi (np. „Powłoka”).
2. W `docs/struktura-sklepu.md` znajdź definicję o tej nazwie w panelu. Gdy są **dwie o tym samym znaczeniu**
   (np. `custom.powloka` i `custom.coating`, `custom.seria` i `custom.product_series`, `custom.producent` i `custom.brand`),
   wybierz tę, która ma dużo wypełnionych wartości i wyświetla się na stronie (z audytu: polskie klucze). Przy wątpliwości: Igor.
3. Sprawdź **typ** i **walidacje**:
   - `single_line_text_field`: tekst; filtr pokazuje każdą wartość osobno, więc pisownia musi być identyczna („Non-stick” to nie „non-stick”),
   - `list.single_line_text_field`: kilka wartości (np. rodzaje kuchenek), w arkuszu rozdzielane `|`,
   - `number_integer` / `number_decimal`: liczba bez jednostki (jednostka jest w nazwie pola, np. „Pojemność [L]”: wpisujesz `3,6`),
   - `boolean`: Tak / Nie,
   - `choices=[...]` w walidacjach: zamknięta lista, wpisujesz tylko te wartości,
   - `metaobject_reference` / `list.metaobject_reference` (np. `shopify.*`, cechy kategorii Shopify): **nie przez arkusz**, to odwołania do słownika. Tylko odczyt, zmiany: Igor.
4. **Słownik wartości**: zanim wpiszesz nową wartość, pobierz wartości już używane w tym polu (eksport całej kategorii)
   i trzymaj się ich pisowni. Nowa wartość (której nikt jeszcze nie użył) wymaga zgody użytkownika, bo tworzy nową pozycję w filtrze.
   Przykład z audytu: w polach Tak/Nie (indukcja, zmywarka, hermetyczny) używa się „Tak” / „Nie”; sprawdź to w eksporcie, zanim założysz.

## Praca na arkuszu (zalecana dla grup produktów)

```
python scripts/cechy.py eksport --kolekcja garnki --pola custom.powloka custom.indukcja custom.zmywarka
```
Powstaje `robocze/cechy-garnki-RRRR-MM-DD.csv` (średnik, otwiera się w Excelu) i podsumowanie: ile produktów ma wypełnione każde pole.

Dwie drogi uzupełniania:
- **użytkownik** uzupełnia arkusz w Excelu i zapisuje (format CSV UTF-8, separator średnik),
- **Ty** uzupełniasz arkusz na podstawie danych ze sklepu (np. seria z tytułu „Garnek ... Florina AmVegan 24 cm”, średnica z tytułu),
  ale **każdą wartość wywiedzioną z tytułu oznacz** i pokaż użytkownikowi listę do akceptacji. Nie zgaduj parametrów, których nie ma w danych.

Potem podgląd (nic nie zapisuje):
```
python scripts/cechy.py import robocze/cechy-garnki-RRRR-MM-DD.csv
```
Pokazuje zmiany „stara wartość -> nowa” i błędy (zły typ, wartość spoza listy). Pusta komórka = bez zmian.
Po zgodzie użytkownika:
```
python scripts/cechy.py import robocze/cechy-garnki-RRRR-MM-DD.csv --allow-mutations
```
Skrypt sam robi backup, zapisuje partiami po 25 metapól, a na koniec **sprawdza odczytem** każdą zmianę i zapisuje raport w `raporty/`.
Limit: 150 produktów na jeden import (większy arkusz podziel). Czyszczenia wartości (zostawienia pustego pola) ten skrypt nie robi.

Kolejność dla nowej kategorii: najpierw 3 do 5 produktów (próba), sprawdzenie karty produktu i filtra w kategorii, potem reszta.

## Pojedyncza zmiana (1 do 5 produktów)

`metafieldsSet` z `ownerId`, `namespace`, `key`, `type`, `value` (typ musi zgadzać się z definicją). Backup produktu przed zapisem.
```graphql
mutation Cechy($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { key namespace value }
    userErrors { field message code elementIndex }
  }
}
```

## Filtry w kategorii

- Filtr pokazuje wartości z produktów w danej kategorii; pojawia się tylko, jeśli ktoś włączył go w aplikacji **Search & Discovery** (to robi Igor).
- Każda różnica w pisowni = osobna pozycja filtra („Tak”, „tak”, „TAK” to trzy pozycje). Dlatego słownik wartości jest ważniejszy niż szybkość.
- Kolekcja z ponad 5 000 produktów nie wyświetla filtrów, a filtr pokazuje maks. 100 wartości (limity Shopify).
- Po zmianie cech filtr odświeża się z opóźnieniem (do kilkunastu minut).

## Raport braków (gdy użytkownik pyta „czego brakuje”)

Eksport kategorii z polami specyfikacji, potem w Pythonie: ile produktów ma każde pole puste, lista produktów bez kluczowych cech.
Zapisz do `raporty/RRRR-MM-DD/braki-cech-<kategoria>.csv` i pokaż podsumowanie (pole: wypełnione X z Y).
