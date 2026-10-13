---
name: opisy-produktow-i-kategorii
description: Pisanie i podmiana opisów produktów oraz opisów kategorii (kolekcji) w sklepie Florina, razem z meta tytułem i meta opisem (SEO), w stylu marki i z zasadami SEO. Używaj, gdy użytkownik prosi „napisz opis”, „popraw opis”, „opis kategorii”, „tekst SEO”, „meta title / meta description”, „wyczyść opis z kodu”, oraz przy masowym przeglądzie jakości opisów.
---

# Opisy produktów i kategorii

Zasady stylu i SEO: `references/styl-i-seo.md` (przeczytaj przed pisaniem pierwszego tekstu w sesji).

## Gdzie co jest zapisane

| Treść | Pole | Zmiana przez |
|---|---|---|
| Opis produktu | `descriptionHtml` produktu | `productUpdate(product: { id, descriptionHtml })` |
| Meta tytuł i meta opis produktu | `seo { title description }` | `productUpdate(product: { id, seo: { title, description } })` |
| Krótki opis kategorii (nad listą produktów) | `descriptionHtml` kolekcji | `collectionUpdate(input: { id, descriptionHtml })` |
| Dłuższy tekst kategorii („Czytaj więcej”) | **metapole kolekcji, DO POTWIERDZENIA** w `docs/struktura-sklepu.md` (sekcja „Kolekcja wzorcowa”) | `metafieldsSet` z `ownerId` kolekcji |
| Meta tytuł i opis kategorii | `seo` kolekcji | `collectionUpdate(input: { id, seo: { title, description } })` |

Typ metapola dłuższego tekstu sprawdź przed zapisem: dla `rich_text_field` wartość to JSON Shopify (nie HTML), dla `multi_line_text_field` zwykły tekst, dla `single_line_text_field` jedna linia. Gdy nie masz pewności, który to klucz: zapytaj Igora, nie zgaduj.

## Przebieg pracy

1. **Odczytaj obecny stan**: opis, SEO, tytuł, specyfikację (metapola), kolekcje produktu. Przy kategorii: oba teksty i FAQ (żeby nie powtarzać treści FAQ w opisie).
2. **Fakty tylko ze sklepu**: materiał, powłoka, średnica, pojemność, indukcja, zmywarka bierz z metapól i specyfikacji. **Nie wymyślaj parametrów.** Brakującą informację oznacz w szkicu `[DO UZUPEŁNIENIA: ...]` i zapytaj użytkownika.
3. **Szkic** zapisz w `robocze/opisy/<uchwyt>.html` (oraz `<uchwyt>-seo.txt`). Pokaż użytkownikowi cały tekst, a przy podmianie także stary tekst obok.
4. Poprawki według uwag użytkownika. Zgoda na KONKRETNĄ wersję.
5. Backup (`python scripts/backup_produktu.py --handle <uchwyt>` albo `--kolekcja <uchwyt>`).
6. Zapis. **SEO zawsze w komplecie**: wysyłasz `title` i `description` razem, bo samo `title` kasuje meta opis (pułapka Shopify, `userErrors` jest wtedy puste).
7. Odczyt po zapisie, porównanie z zatwierdzonym szkicem, link do sprawdzenia w sklepie.

Masowo (wiele produktów jednej serii): najpierw 1 produkt do akceptacji stylu, potem partie po 10, każdą z podglądem.

## Sprzątanie opisów po migracji z IdoSell

Część opisów zawiera wklejony kod CSS i resztki starego sklepu (np. `.tresc100 { ... }`, `#projector_longdescription`,
`@media (min-width: 979px)`, znaczniki `<style>`, puste akapity, osadzone `iframe`). Taki kod wycieka jako tekst
na kartach produktów w listingu i psuje opis w danych dla Google.

Jak sprzątać:
1. Policz skalę: wyszukaj produkty i w Pythonie sprawdź `descriptionHtml` pod kątem `<style`, `.tresc`, `projector_`, `{` (zapisz wynik do `raporty/`).
2. Czyszczenie = usunięcie bloków `<style>...</style>` i reguł CSS z tekstu, bez zmiany treści. Pokaż różnicę na 2 produktach.
3. Filmy YouTube z opisu (`iframe`) **nie usuwaj** bez decyzji użytkownika: można je zamiast tego dodać do mediów produktu (skill `media-produktu`).
4. Dalej standardowo: zgoda, backup, partie, odczyt.

## Czego nie robisz

- nie zmieniasz tytułu produktu ani uchwytu (adresu URL) przy okazji opisu; tytuł tylko na wyraźną prośbę; uchwyt wyłącznie na wyraźną prośbę, z przekierowaniem 301 ze starego adresu (`redirectNewHandle: true`) i ostrzeżeniem, że Google musi przeindeksować stronę,
- nie wstawiasz skryptów, stylów, `iframe` ani klas CSS do opisów,
- nie kopiujesz opisów producentów i konkurencji 1:1 (treść zduplikowana),
- nie obiecujesz w opisie rzeczy, których nie potwierdzają dane (gwarancja, certyfikaty, „bez PFOA”), dopóki użytkownik ich nie poda.
