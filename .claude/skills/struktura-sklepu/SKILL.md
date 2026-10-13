---
name: struktura-sklepu
description: Gdzie w sklepie Florina zapisane są dane (metapola produktów i kolekcji, wpisy FAQ, opisy, specyfikacja, tagi, kolekcje ręczne i automatyczne) i jak to sprawdzić skryptem scripts/struktura_sklepu.py. Używaj na początku pierwszej sesji, gdy brakuje pliku docs/struktura-sklepu.md, gdy nie wiesz, które metapole odpowiada za daną cechę, i zanim napiszesz jakąkolwiek zmianę metapól, FAQ albo opisu kategorii.
---

# Struktura sklepu Florina

## Zasada

Nie zgaduj nazw pól. Przed pierwszą zmianą danego rodzaju sprawdź `docs/struktura-sklepu.md`.
Jeśli pliku nie ma, uruchom (tylko odczyt, trwa kilka minut):

```
python scripts/struktura_sklepu.py
```

Plik zawiera: definicje metapól produktu, kolekcji i wariantu (typ, liczba wypełnionych, walidacje, lista
dozwolonych wartości), definicje metaobiektów (np. FAQ) z próbkami wpisów, metapola kolekcji wzorcowej
`garnki` i jej przykładowego produktu, listę kolekcji z regułami oraz tagi.

## Co wiemy na pewno (sprawdzone na publicznej stronie florina.pl, 13.10.2026)

- **Opis kolekcji jest w dwóch miejscach na stronie kategorii**:
  krótki wstęp nad listą produktów = pole **opis kolekcji** (`descriptionHtml`, 2 akapity w kolekcji Garnki),
  oraz **dłuższy tekst „Czytaj więcej”** (klasa `collection-info-desc`) z innym, dłuższym tekstem.
  Ten drugi pochodzi najpewniej z metapola kolekcji. **DO POTWIERDZENIA na sklepie**: które metapole (patrz `docs/struktura-sklepu.md`, sekcja „Kolekcja wzorcowa”).
- **FAQ kategorii** wyświetla się na stronie kolekcji (sekcja `faq_accordion_collection`) **i na karcie każdego produktu
  z tej kategorii** (sekcja `faq_accordion_pdp`, nagłówek „FAQ - Najczęściej zadawane pytania”, zakładka
  „Najczęstsze pytania o garnki”). Te same pytania w obu miejscach.
  Pojedyncze pytania mają uchwyty w stylu **`florina-garnki-01-jakie-garnki-sa-najlepsze`**, czyli są to
  **wpisy metaobiektu** (wzór: `florina-<kategoria>-<numer>-<pytanie>`). **DO POTWIERDZENIA na sklepie**: typ metaobiektu,
  nazwy jego pól i metapole, które łączy kolekcję (i ewentualnie produkt) z listą pytań. Szczegóły: skill `faq-produkty-kategorie`.
- **Specyfikacja techniczna na karcie produktu** to tabela etykieta / wartość: Waga, EAN, Materiał, Wysokość, Producent,
  Seria, Pojemność [L], Kolor, Powłoka, Średnica, Indukcja, Zmywarka, Pojemność użytkowa, Pokrywka, Rodzaje kuchenek,
  Kraj produkcji. Wartości pochodzą z metapól produktu. Skill `ocechowanie-metapola`.
- **Tagi** mieszają kategorie i znaczniki: np. `GARNKI`, `GOTOWANIE`, `kat-gotowanie`, `bestseller-top100`,
  `w-przecenie`, `pazdziernik-w-kuchni`. Część kolekcji automatycznych i promocji działa na tagach.
- **Opisy produktów** po migracji z IdoSell miejscami zawierają wklejony kod CSS (np. `.tresc100 { ... }`, `#projector_longdescription`),
  który wycieka jako tekst na kartach w listingu. To jest znany problem do sprzątania (skill `opisy-produktow-i-kategorii`).
- **Kategoria produktu Shopify** (taksonomia) jest ustawiona na 100% produktów i decyduje o stawce VAT: zmieniaj tylko na wyraźną prośbę, z ostrzeżeniem o VAT.

## Co wiemy z audytu Igora (31.08 i 06.10.2026, może być nieaktualne)

- Metapola produktu z polskimi nazwami, które zasilają specyfikację: m.in. `custom.material`, `custom.powloka`,
  `custom.seria`, `custom.producent`, `custom.indukcja`, `custom.zmywarka`, `custom.pojemnosc_l`, `custom.pojemnosc_ml`,
  `custom.kolor`, `custom.ksztalt`, `custom.z_pokrywka`, `custom.mikrofala`, `custom.typ`, `custom.hermetyczny`,
  `custom.ilosc_w_zestawie`, `custom.moc_w`.
- **Są duplikaty o tym samym znaczeniu** (angielskie, prawie puste): `custom.coating` obok `custom.powloka`,
  `custom.brand` obok `custom.producent`, `custom.product_series` obok `custom.seria`, `custom.diameter`, `custom.capacity`.
  **Wypełniaj tylko to pole, które wyświetla się na stronie** (porównaj z tabelą specyfikacji na karcie produktu
  i z liczbą wypełnionych w `docs/struktura-sklepu.md`). Przy wątpliwości: Igor.
- Część etykiet ze specyfikacji (Średnica, Pojemność użytkowa, Pokrywka, Rodzaje kuchenek, Kraj produkcji, Waga)
  nie miała odpowiednika w spisie z 31.08: definicje doszły przy przebudowie sklepu. Sprawdź je w `docs/struktura-sklepu.md`.
- Metapola `shopify.*` (np. `shopify.color-pattern`, `shopify.cookware-bakeware-material`, `shopify.compatible-stove-top-type`)
  to **cechy kategorii Shopify** oparte o słownik (metaobiekty taksonomii). Nie wpisuje się do nich tekstu, tylko
  odwołania do wpisów słownika. Zapis tylko pojedynczo, z gid istniejących wpisów, po zgodzie (skill `ocechowanie-metapola`).
- `reviews.*` (oceny) i `mm-google-shopping.*` zapisują aplikacje: nie ruszamy.

## Jak czytać `docs/struktura-sklepu.md`

- Kolumna **Wypełnione** = ilu produktów dotyczy pole. Pole z 0 wypełnionych to zwykle martwy duplikat.
- Kolumna **Walidacje** z `choices=[...]` = zamknięta lista wartości. Wpisuj dokładnie te wartości (wielkość liter też).
- Kolekcja **automatyczna** (z regułami) nie przyjmuje ręcznego dodawania produktów: produkt trafia do niej przez tag
  albo inną cechę z reguły. Skill `produkty-kolekcje-tagi`.

## Gdy struktura się zmieni

Igor dopisuje lub zmienia metapola w panelu. Po takiej zmianie uruchom skrypt ponownie. Jeśli `docs/struktura-sklepu.md`
przeczy temu skillowi, **wierz plikowi** (jest świeższy) i zanotuj rozbieżność w `dziennik/lekcje.md`.
