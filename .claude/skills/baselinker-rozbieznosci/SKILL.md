---
name: baselinker-rozbieznosci
description: Sprawdzanie rozbieżności między BaseLinkerem (Base.com) a Shopify w sklepie Florina, wyłącznie odczyt: stany magazynowe, ceny, produkty obecne tylko w jednym systemie, SKU i EAN, zamówienia, które nie przeszły. Używaj, gdy użytkownik pyta „czy stany się zgadzają”, „sprawdź Base”, „zamówienie nie spadło do Base”, „różne ceny w Base i w sklepie”, „produkt jest w Base, a nie ma go w sklepie”.
---

# Rozbieżności BaseLinker i Shopify (tylko odczyt)

**W Base niczego nie zmieniamy.** Ani przez API, ani przez przeglądarkę. Skrypt ma listę wyłącznie metod odczytu (`get...`),
a strażnik blokuje każdą metodę zapisującą. Naprawę rozbieżności robi człowiek w panelu Base lub Shopify po decyzji, gdzie leży prawda,
a zmiany cen i stanów w Shopify są możliwe tylko po zgodzie użytkownika i z ostrzeżeniem: jeśli Base synchronizuje stany lub ceny do Shopify, nadpisze ręczną zmianę przy najbliższej synchronizacji. Zanim zaproponujesz poprawkę w Shopify, ustal z użytkownikiem, który system jest źródłem prawdy.

## Klucz API

- Klucz jest w pliku `.env` jako `BASELINKER_TOKEN`. **Nigdy nie proś o wklejenie klucza do czatu i nie wypisuj go.**
- Brak klucza: skrypt powie „Brak BASELINKER_TOKEN”. Wtedy odeślij użytkownika do `INSTALACJA.md`, krok 7.
- Błąd `ERROR_BAD_TOKEN` = zły lub wycofany klucz. Błąd uprawnień = klucz użytkownika bez dostępu do katalogu lub zamówień.

## Polecenia

```
python scripts/base_shopify_roznice.py --lista
```
Najpierw (raz): pokazuje katalogi Base, magazyny (np. `bl_12345`) i grupy cen. Zapisz w `dziennik/lekcje.md`, który magazyn i która grupa cen
odpowiadają sklepowi Shopify (**DO POTWIERDZENIA** z Igorem przy pierwszym uruchomieniu: z którego magazynu Base synchronizuje stany do Shopify).

```
python scripts/base_shopify_roznice.py --produkty [--katalog ID] [--magazyn bl_ID] [--grupa-cen ID]
```
Porównuje produkty po SKU (gdy SKU się nie zgadza, próbuje po EAN). Bez `--magazyn` sumuje stany ze wszystkich magazynów katalogu
(to może dawać fałszywe różnice, jeśli do Shopify idzie tylko jeden magazyn).

```
python scripts/base_shopify_roznice.py --zamowienia --dni 3
```
Zamówienia z ostatnich N dni: czy każde zamówienie Shopify jest w Base, czy kwoty się zgadzają. Zamówienia młodsze niż 30 minut są pomijane
(Base pobiera zamówienia cyklicznie, zwykle co ok. 10 minut).

Wynik: `raporty/RRRR-MM-DD/roznice-*.csv` (Excel) i `.html` (podsumowanie do otwarcia w przeglądarce).

## Jak czytać wyniki (i co powiedzieć użytkownikowi)

| Problem w raporcie | Najczęstsza przyczyna | Co dalej |
|---|---|---|
| Rozny stan | synchronizacja jeszcze nie przeszła, zły magazyn w porównaniu, rezerwacje zamówień w Base | sprawdź ponownie za 15 min; potwierdź magazyn; trwała różnica: zgłoś Igorowi |
| Rozna cena | inna grupa cen w porównaniu, promocja w Shopify (cena przekreślona), ręczna zmiana w jednym systemie | potwierdź grupę cen; lista do decyzji dla osoby od cen |
| Jest w Base, brak w Shopify | produkt nie wystawiony, inne SKU, zestaw (bundle) | sprawdź po nazwie i EAN w Shopify |
| Jest w Shopify (aktywny), brak w Base | produkt dodany ręcznie w Shopify, literówka w SKU | lista dla Igora |
| SKU rozne, ten sam EAN | literówka lub zmiana SKU w jednym systemie | lista do ujednolicenia (decyzja: który SKU jest właściwy) |
| Duplikat SKU | dwa produkty z tym samym SKU: synchronizacja stanów jest wtedy nieprzewidywalna | pilne, zgłoś Igorowi |
| Brak SKU w Shopify | produkt bez SKU nie zsynchronizuje się z Base | lista dla Igora |
| Jest w Shopify, brak w Base (zamówienie) | Base jeszcze nie pobrał, zamówienie testowe, błąd integracji | sprawdź za 15 min; trwały brak: pilne zgłoszenie |
| Rozna kwota (zamówienie) | zwrot lub edycja zamówienia w Shopify, koszt dostawy liczony inaczej | zwykle nie błąd: opisz przypadek |

Zasady interpretacji (z doświadczeń Igora z innych wdrożeń):
- **Zanim nazwiesz coś błędem, policz czas**: cykl pobierania zamówień w Base to kilka minut, synchronizacja stanów też ma opóźnienie.
- **Nie ufaj jednemu przykładowi**: podaj skalę (ile pozycji z ilu) i 3 przykłady.
- Filtry w `getOrders` potrafią być ignorowane przez Base: skrypt filtruje wyniki sam, po swojej stronie.
- Daty z Base są w czasie Unix (UTC); w raporcie są przeliczone na czas lokalny.
- Dopasowanie zamówień idzie po numerze zamówienia Shopify zapisanym w Base (`external_order_id` / `shop_order_id`).
  **DO POTWIERDZENIA** na pierwszym uruchomieniu: jeśli „dopasowane” wyjdzie 0 przy wielu zamówieniach w obu systemach, to Base zapisuje numer inaczej: zgłoś Igorowi.
- Parametr `include_variants` w `getInventoryProductsList` (warianty jako osobne pozycje): **DO POTWIERDZENIA**, czy Base go obsługuje na tym koncie.
  Jeśli warianty nie wracają, raport pokaże je jako „Jest w Shopify, brak w Base”.

## Raport dla użytkownika

Krótko: data i zakres, liczby z podsumowania, 3 najważniejsze problemy z przykładami, co jest pilne, link do pliku HTML.
Bez technicznego żargonu (SKU można zostawić, to termin z panelu).
