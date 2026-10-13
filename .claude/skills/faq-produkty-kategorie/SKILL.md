---
name: faq-produkty-kategorie
description: FAQ (najczęstsze pytania) kategorii i produktów w sklepie Florina: jak jest zapisane (wpisy metaobiektu podpięte pod kolekcję), jak dopisać, poprawić albo przypiąć pytania do kategorii, i jak pisać odpowiedzi. Używaj, gdy użytkownik prosi „dodaj pytanie do FAQ”, „FAQ dla kategorii”, „popraw odpowiedź w FAQ”, „FAQ na karcie produktu”, „dlaczego FAQ się nie wyświetla”.
---

# FAQ kategorii i produktów

## Jak to działa w tym motywie (potwierdzone na florina.pl 13.10.2026)

- Kategoria ma listę pytań. Ta sama lista wyświetla się:
  - na stronie kategorii (sekcja `faq_accordion_collection`),
  - na karcie **każdego produktu** tej kategorii (sekcja `faq_accordion_pdp`, nagłówek „FAQ - Najczęściej zadawane pytania”,
    zakładka „Najczęstsze pytania o garnki”).
- Każde pytanie to **osobny wpis metaobiektu** z uchwytem według wzoru `florina-<kategoria>-<numer>-<pytanie>`, np.
  `florina-garnki-01-jakie-garnki-sa-najlepsze` ... `florina-garnki-06-czy-garnki-aluminiowe-sa-zdrowe`.
- Odpowiedzi są pisane w formacie „odpowiedź na początku” (np. „Nienaruszona emalia jest szkliwem obojętnym...”), 50 do 90 słów.

## DO POTWIERDZENIA na sklepie (zrób to raz, na pierwszej sesji z FAQ)

Nie mam jeszcze z Admin API (stan na dzień przygotowania paczki):
1. **typu metaobiektu** FAQ i **nazw jego pól** (np. pytanie / odpowiedź),
2. **metapola kolekcji**, które trzyma listę pytań (typ `list.metaobject_reference`), i ewentualnie tytułu zakładki,
3. czy istnieje **FAQ na poziomie produktu** (osobne metapole produktu) i jak motyw wybiera kategorię dla produktu
   z kilkoma kolekcjami (najpewniej jedna wybrana kolekcja albo metapole produktu wskazujące kolekcję),
4. czy definicja metaobiektu ma **status publikacji** (`publishable`): wtedy nowy wpis musi mieć status ACTIVE, inaczej się nie wyświetli.

Jak to ustalić (tylko odczyt):
- `docs/struktura-sklepu.md`: sekcje „Metaobiekty”, „Próbki metaobiektów” i „Kolekcja wzorcowa garnki” (skrypt `scripts/struktura_sklepu.py`),
- w metapolach kolekcji `garnki` szukaj wartości z listą `gid://shopify/Metaobject/...`; to jest metapole FAQ,
- pobierz wpisy tego typu i sprawdź, że uchwyty zaczynają się od `florina-garnki-`.

Wynik zapisz w `dziennik/lekcje.md` (sekcja „FAQ: struktura”), żeby następnym razem nie sprawdzać od nowa.
Jeśli coś nie pasuje do opisu wyżej (np. FAQ siedzi w blokach motywu, a nie w metaobiektach): **zatrzymaj się i powiedz Igorowi**,
bo wtedy zmiana FAQ to zmiana motywu (zablokowana).

## Dopisanie pytań do kategorii

1. Odczytaj obecne pytania kategorii (lista z metapola + treść wpisów). Pokaż je użytkownikowi.
2. Sprawdź, czy nowe pytanie nie dubluje istniejącego (także w innej kategorii, którą produkt dzieli).
3. Szkic nowych pytań i odpowiedzi w `robocze/faq/<kategoria>.md`. Pokaż, uzyskaj zgodę.
4. Backup: `python scripts/backup_produktu.py --kolekcja <uchwyt>` (zapisze też metapole z listą pytań).
5. **Utwórz wpisy** `metaobjectCreate` z uchwytem według wzoru (kolejny numer, 2 cyfry, uchwyt z pytania bez polskich znaków):
   ```graphql
   mutation Faq($m: MetaobjectCreateInput!) {
     metaobjectCreate(metaobject: $m) {
       metaobject { id handle capabilities { publishable { status } } }
       userErrors { field message code }
     }
   }
   ```
   Zmienne (nazwy pól i typ DO POTWIERDZENIA): `{"m": {"type": "<typ>", "handle": "florina-garnki-07-...", "fields": [{"key": "<pole pytania>", "value": "..."}, {"key": "<pole odpowiedzi>", "value": "..."}], "capabilities": {"publishable": {"status": "ACTIVE"}}}}`
   (fragment `capabilities` tylko, jeśli definicja ma publikację).
   Pole odpowiedzi typu `rich_text_field` przyjmuje JSON Shopify, nie HTML: odczytaj istniejący wpis i zbuduj wartość w tym samym formacie.
6. **Przypnij do kategorii**: `metafieldsSet` na kolekcji z **pełną listą** = obecne id + nowe id, w zamierzonej kolejności.
   Zapis listy **zastępuje** całą listę: jeśli wyślesz tylko nowe, stare pytania znikną ze strony. Lista mieści maks. 128 pozycji.
7. Odczyt: lista w metapolu i treść wpisów. Link: `https://florina.pl/collections/<uchwyt>` i jeden produkt z tej kategorii.

## Poprawa istniejącej odpowiedzi

`metaobjectUpdate(id, metaobject: { fields: [{ key, value }] })`. Backup wpisu: `python scripts/backup_produktu.py --metaobiekt <gid>`.
Pamiętaj: wpis może być podpięty pod **kilka kategorii** (te same pytania). Sprawdź, gdzie jeszcze się wyświetli, i powiedz to użytkownikowi.

## Usuwanie pytania

Usuwanie wpisów jest zablokowane. Pytanie można **odpiąć** od kategorii (zapis listy bez tego id, po zgodzie i backupie).
Sam wpis zostaje w bazie; jego usunięcie robi Igor.

## Jak pisać pytania i odpowiedzi

- **Pytanie** tak, jak zadaje je klient (najlepiej z realnych pytań do obsługi, wyszukiwarki, Google): „Czy garnki aluminiowe są zdrowe?”, „Jaki garnek do rosołu?”.
- **Odpowiedź zaczyna się od odpowiedzi**: „Tak, jeśli...”, „Nie, ...”, „Do rosołu nadaje się wysoki garnek o średnicy od 22 do 28 cm...”. Potem 1 do 3 zdań uzasadnienia z konkretem (temperatura, test magnesem, materiał).
- 50 do 90 słów, bez reklamy, bez „w naszym sklepie znajdziesz najlepsze...”. Można zakończyć wskazaniem rodzaju produktu.
- 4 do 8 pytań na kategorię. Kolejność: od najczęstszych.
- Fakty techniczne zgodne z ofertą (np. czy garnki w tej kategorii faktycznie mają powłokę, czy działają na indukcji): sprawdź metapola produktów kategorii.
- Bez długich myślników, polska typografia jak w `opisy-produktow-i-kategorii/references/styl-i-seo.md`.
