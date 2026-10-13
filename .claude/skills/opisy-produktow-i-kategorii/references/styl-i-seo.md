# Styl i SEO tekstów Floriny

## Głos marki (wzorzec: opis i FAQ kategorii Garnki, 10.2026)

Najlepsze teksty w sklepie są konkretne i rzeczowe, np.:

> Garnki to naczynia do gotowania o wysokich ściankach i płaskim dnie, zwykle z pokrywką. We Florinie znajdziesz
> garnki aluminiowe z powłoką nieprzywierającą, emaliowane i ze stali nierdzewnej (...). Garnek na indukcję poznasz
> po dnie, które przyciąga magnes.

Cechy, które trzymamy:
- **zaczynaj od sedna**: czym jest produkt / kategoria i dla kogo, w pierwszym zdaniu,
- **konkret zamiast przymiotników**: liczby, materiały, zastosowania („średnica 24 cm, pojemność 3,6 l, do indukcji”),
- **praktyczna rada** w jednym zdaniu (jak sprawdzić, jak dobrać, jak dbać),
- forma „Ty” lub bezosobowa, bez wykrzykników, bez CAPS LOCK,
- **zakazane frazy-wypełniacze** (typowe dla starych opisów z IdoSell): „idealna propozycja dla każdego”, „przenieś swoją kuchnię
  na nowy poziom”, „niezbędny element każdej kuchni”, „zachwycający design”, „wyjątkowe doznania kulinarne”,
- nie pisz „najlepszy na rynku”, „nr 1”, „gwarancja jakości” bez podstawy,
- polska typografia: liczby z przecinkiem dziesiętnym (3,6 l), spacja przed jednostką (24 cm), „°C” bez spacji przed C (250 °C),
  nazwy serii wielką literą (AmVegan, Carina Black), marka „Florina”, „Mateusz Gessler” w pełnym brzmieniu.

## Struktura opisu produktu (HTML)

Dozwolone znaczniki: `<p>`, `<h2>`, `<h3>`, `<ul>`, `<li>`, `<strong>`, `<em>`, `<a href="...">` (tylko linki do florina.pl), `<br>`.
Bez `style=`, `class=`, `<style>`, `<script>`, `<iframe>`, `<table>` (specyfikacja wyświetla się sama z metapól).

Wzór:
1. `<p>` 2 do 3 zdań: co to jest, z czego, do czego, dla kogo (z najważniejszą frazą w pierwszym zdaniu).
2. `<h2>` z korzyścią + `<ul>` 3 do 6 punktów: konkretne cechy i ich praktyczny sens („dno ze stalową płytką: działa na indukcji”).
3. `<h2>Jak dbać</h2>` lub `<h2>Na co zwrócić uwagę</h2>` + 2 do 3 zdań (zmywarka, temperatura, przybory).
4. Opcjonalnie `<p>` o serii (link do kolekcji serii, jeśli istnieje).

Długość: 120 do 300 słów. Nagłówków H1 w opisie **nie używamy** (H1 to tytuł produktu na stronie).

## Opis kategorii

- **Krótki wstęp (`descriptionHtml`)**: 2 akapity, łącznie 50 do 90 słów. Czym jest kategoria, jakie rodzaje są w sklepie, jedna rada wyboru.
- **Dłuższy tekst („Czytaj więcej”)**: 250 do 600 słów, śródtytuły H2/H3 pod rodzaje i kryteria wyboru (materiał, rozmiar, płyta, pielęgnacja).
  Nie powtarzaj pytań z FAQ tej kategorii: odpowiedzi szczegółowe zostają w FAQ.
- Linki wewnętrzne: 2 do 5 do podkategorii i serii (`/collections/<uchwyt>`). Sprawdź, czy kolekcja istnieje.

## SEO

- **Meta tytuł**: 50 do 60 znaków, fraza główna na początku, marka na końcu: `Garnek aluminiowy AmVegan 24 cm 3,6 l | Florina`.
- **Meta opis**: 140 do 155 znaków, konkret + zachęta bez krzyku: „Garnek aluminiowy z powłoką nieprzywierającą, do indukcji, 24 cm i 3,6 l. Seria AmVegan by Mateusz Gessler. Sprawdź wymiary i opinie.”
- Fraza główna = to, czego szuka klient (typ produktu + cecha: „patelnia na indukcję 28 cm”, „garnek emaliowany 5 l”).
  Klienci Floriny często szukają **nazwami serii** (Milano, Mokka, Siciliano, Evia): seria w tytule i w pierwszym akapicie.
- Jedna fraza główna na stronę; nie upychaj fraz (bez powtarzania tej samej frazy w każdym zdaniu).
- Nie zmieniaj uchwytu (adresu URL) dla SEO: stare adresy mają przekierowania i historię w Google.
- Odpowiedź na początku akapitu i konkretne liczby pomagają też w cytowaniu przez asystentów AI (ChatGPT już przyprowadza zamówienia).

## Sprawdzenie przed pokazaniem szkicu

- [ ] fakty zgadzają się ze specyfikacją produktu (metapola),
- [ ] brak fraz-wypełniaczy z listy wyżej,
- [ ] długość i struktura według wzoru,
- [ ] meta tytuł 50 do 60 znaków, meta opis 140 do 155 znaków (policz i podaj liczby),
- [ ] tylko dozwolone znaczniki HTML, linki działają (sprawdź `https://florina.pl/collections/<uchwyt>`),
- [ ] brak długich myślników.
