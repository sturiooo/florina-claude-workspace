---
name: media-produktu
description: Dodawanie zdjęć i wideo do karty produktu w sklepie Florina (pliki z komputera, zdjęcia z adresu URL, filmy YouTube), teksty alternatywne (alt), kolejność galerii i zdjęcie główne. Używaj, gdy użytkownik prosi „wgraj zdjęcia”, „dodaj film do produktu”, „zmień zdjęcie główne”, „popraw alty”, „zdjęcie się nie wyświetla”.
---

# Zdjęcia i wideo produktu

Narzędzie: `scripts/upload_mediow.py` (domyślnie tylko podgląd; zapis z `--allow-mutations` po zgodzie, sam robi backup produktu).

## Przygotowanie plików

- Użytkownik wkłada pliki do `robocze/media/<uchwyt-produktu>/` (jeden katalog na produkt).
- Zdjęcia: JPG, PNG albo WEBP, najlepiej kwadrat lub ten sam format co reszta galerii, min. 1200 px na krótszym boku, maks. 20 MB.
  Nazwa pliku opisowa, bez polskich znaków i spacji: `patelnia-amvegan-28-cm-z-gory.jpg` (nazwa pliku też trafia do Google).
- Wideo: MP4 albo MOV (Shopify przyjmuje też inne, ale te są pewne), maks. ok. 1 GB i kilka minut (**DO POTWIERDZENIA** aktualny limit długości w panelu).
- YouTube / Vimeo: sam link, film nie jest kopiowany do Shopify.

Przed wgraniem obejrzyj listę plików i porównaj z prośbą (czy to na pewno ten produkt, ten kolor, ten rozmiar).
Zdjęcie innego wariantu na karcie produktu to częsty błąd, a usunięcie pliku jest nieodwracalne (zostaje tylko adres w backupie).

## Teksty alternatywne (alt)

Alt opisuje, co widać na zdjęciu (dla osób niewidomych i dla Google). Wymagany dla każdego pliku.
- Wzór: `<typ produktu> <marka> <seria> <rozmiar>, <co widać>`: „Patelnia Florina AmVegan 28 cm, widok z góry na powłokę”.
- 5 do 15 słów, bez „zdjęcie”, „obrazek”, bez upychania fraz, bez powtarzania identycznego altu na każdym zdjęciu.
- Wideo: alt opisuje treść filmu („Patelnia AmVegan w użyciu, smażenie jajek bez tłuszczu”).

## Przebieg

1. Odczytaj produkt: obecne media (ile, jaka kolejność, alty).
2. Podgląd:
   ```
   python scripts/upload_mediow.py --produkt <uchwyt> --pliki robocze/media/<uchwyt>/a.jpg robocze/media/<uchwyt>/b.jpg --alty "alt 1" "alt 2"
   ```
   Opcje: `--url <adres>` (zdjęcie z internetu), `--youtube <link>`, `--na-poczatek` (nowe media na początek galerii, pierwsze = zdjęcie główne).
3. Pokaż użytkownikowi plan (pliki, alty, pozycja), uzyskaj zgodę.
4. To samo polecenie z `--allow-mutations`. Skrypt: backup, wysłanie plików, dodanie do produktu, czekanie na przetworzenie (status READY).
5. Status FAILED = plik uszkodzony lub zły format: powiedz użytkownikowi, nie ponawiaj w kółko.
6. Link do sprawdzenia: `https://florina.pl/products/<uchwyt>` (galeria, kolejność, zdjęcie główne na liście w kategorii).

## Zmiana altu albo kolejności istniejących mediów

- Alt: `productUpdateMedia(productId, media: [{ id, alt }])` (backup produktu przed zmianą).
- Kolejność: `productReorderMedia(id, moves: [{ id, newPosition: "0" }])`; działa w tle, sprawdź odczytem po chwili.

## Zdjęcia wariantów

Natywnie wariant ma jedno zdjęcie (`productVariantAppendMedia`). Plik musi najpierw być w mediach produktu.
Galeria per wariant (wiele zdjęć na kolor) zależy od motywu: **DO POTWIERDZENIA** z Igorem, zanim obiecasz to użytkownikowi.

## Czego nie robisz

- nie usuwasz mediów bez wyraźnej prośby; usunięcie (`productDeleteMedia` albo `fileDelete`) tylko z listą do akceptacji, backupem produktu (`--handle`) i ostrzeżeniem, że to nieodwracalne,
- nie wgrywasz zdjęć, do których marka nie ma praw (zdjęcia konkurencji, z Google Grafika),
- nie wgrywasz wideo do biblioteki plików „na zapas”: zawsze do konkretnego produktu.
