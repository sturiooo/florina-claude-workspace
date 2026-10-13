---
name: produkty-kolekcje-tagi
description: Wyszukiwanie produktów, dodawanie produktów do kolekcji (kategorii) i tagowanie produktów w sklepie Florina. Używaj, gdy użytkownik prosi „dodaj do kolekcji”, „wrzuć do kategorii”, „otaguj”, „dodaj tag”, „usuń tag”, „dlaczego produkt nie jest w kategorii”, „znajdź produkty, które...”, oraz zanim zmienisz jakikolwiek tag (tagi sterują kolekcjami automatycznymi i promocjami).
---

# Produkty, kolekcje i tagi

Zanim zaczniesz: skill `bezpieczna-praca` (checklista) i `docs/struktura-sklepu.md` (lista kolekcji z regułami, tagi).
Gotowe zapytania: `references/zapytania.md`.

## Najpierw ustal: kolekcja ręczna czy automatyczna?

| | Kolekcja ręczna | Kolekcja automatyczna |
|---|---|---|
| Jak produkt do niej trafia | ktoś go dodał | spełnia reguły (np. „tag równa się GARNKI”) |
| Czy można dodać produkt ręcznie | tak (`collectionAddProducts`) | **nie**: Shopify odrzuci; trzeba nadać tag albo cechę z reguły |
| Jak sprawdzić | brak `ruleSet` | `ruleSet` z listą reguł |

Gdy użytkownik prosi „dodaj do kategorii X”, a X jest automatyczna:
1. pokaż mu regułę (np. `TAG EQUALS GARNKI`),
2. zaproponuj nadanie tagu z reguły,
3. sprawdź, **do jakich innych kolekcji ten sam tag wciągnie produkt** (przeszukaj reguły wszystkich kolekcji w `docs/struktura-sklepu.md`). Powiedz to użytkownikowi przed zgodą.

Zmiana reguł kolekcji automatycznej i tworzenie nowej kolekcji są możliwe za zgodą, ale to zmiany struktury: przed zgodą pokaż, ile produktów wejdzie lub wypadnie (policz wyszukiwaniem po nowej regule), czy kolekcja ma trafić do menu i czy nie dubluje istniejącej. Nowa kolekcja startuje nieopublikowana, publikacja to osobny krok.

## Wyszukiwanie produktów (składnia `query`)

- `tag:GARNKI`, `-tag:Wyprzedane` (bez tagu), `tag:GARNKI AND tag:kat-gotowanie`
- `title:*AmVegan*` (fragment nazwy), `vendor:Florina`, `sku:ABC123`, `barcode:5905...`
- `status:active` (tylko aktywne; domyślnie wyszukiwanie zwraca też wersje robocze i archiwum)
- `collection_id:123456` nie istnieje w wyszukiwaniu produktów: produkty kolekcji czytaj przez `collectionByIdentifier { products }`.

Zawsze pokaż użytkownikowi liczbę wyników i kilka przykładów. Gdy wyników jest dużo więcej, niż się spodziewał, zatrzymaj się i dopytaj.

## Dodawanie do kolekcji ręcznej

1. Odczytaj kolekcję (`collectionByIdentifier`): tytuł, liczba produktów, czy ręczna.
2. Znajdź produkty, sprawdź, które **już są** w kolekcji (`inCollection`), i pomiń je.
3. Podgląd: lista produktów do dodania (tytuł, uchwyt, status). Ostrzeż, jeśli są wśród nich wersje robocze lub zarchiwizowane.
4. Zgoda, backup kolekcji (`python scripts/backup_produktu.py --kolekcja <uchwyt>`).
5. `collectionAddProducts` partiami do 20 produktów. Działa tylko dla kolekcji ręcznych.
6. Weryfikacja: `productsCount` przed i po + `inCollection` dla dodanych.

Usunięcie z kolekcji ręcznej (`collectionRemoveProducts`) jest dozwolone tylko do **cofnięcia własnej pomyłki** z tej samej sesji albo na wyraźną prośbę z listą produktów. Mutacja działa w tle (zwraca `job`): sprawdź wynik odczytem po kilku sekundach.

## Tagi

Tagi w sklepie Florina mieszają kilka rzeczy naraz (stan z 10.2026):
- **kategorie wielkimi literami**: `GARNKI`, `PATELNIE`, `GOTOWANIE` (zasilają kolekcje automatyczne),
- **kategorie z prefiksem**: `kat-gotowanie`,
- **promocje i akcje**: np. `w-przecenie`, `pazdziernik-w-kuchni`, `bts-3-1-all`, `sale10`,
- **znaczniki**: `bestseller-top100`, `Wyprzedane`.

Zasady:
- **Tagi są wrażliwe na pisownię.** `Garnki` to nie `GARNKI`. Zanim dodasz tag, sprawdź jego dokładną pisownię na liście tagów (`docs/struktura-sklepu.md` albo zapytanie `productTags`). Nowego tagu, którego nie ma na liście, nie wymyślaj: zapytaj użytkownika, czy na pewno ma powstać nowy.
- **Tagi promocyjne zmieniają ceny w koszyku i udział w akcjach.** Dodanie lub zdjęcie takiego tagu rób tylko na wyraźną prośbę i z ostrzeżeniem.
- `tagsAdd` dopisuje tagi (nie usuwa innych). `tagsRemove` zdejmuje tylko wskazane. Nie używaj `productUpdate` z polem `tags`, bo ono **zastępuje całą listę** tagów.
- Jedno wywołanie = jeden produkt. Kilka produktów: kilka aliasów w jednej mutacji (do 20) albo kolejne wywołania.

## Po zmianie

- Odczytaj produkty ponownie (tagi, `collections`).
- Gdy tag zasila kolekcję automatyczną: sprawdź po minucie, czy produkt w niej jest (Shopify przelicza kolekcje z opóźnieniem).
- Podaj link do sprawdzenia: `https://florina.pl/collections/<uchwyt>`.
- Wpis w dzienniku (skill `dziennik-zmian`).
