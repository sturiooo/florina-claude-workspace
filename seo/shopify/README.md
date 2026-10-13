# Baza wiedzy - SEO na Shopify (warstwa Shopify toolkitu seo)

Konkretny, rzeczowy przewodnik audytu i wdrażania SEO na sklepie Shopify.
Cel: **rozdzielić co Shopify robi autonomicznie, co musi wyrenderować motyw, a
co jest ręczną pracą w panelu / treściach / narzędziach zewnętrznych** - żeby nie
marnować czasu na rzeczy działające z automatu i skupić się na realnych brakach.

> To **warstwa Shopify** toolkitu SEO w `seo/`. Generyczne narzędzia
> (keyword research, content, schema, linkowanie, ok. 70 skryptów) są w `seo/scripts/`
> i `seo/resources/`. Spina to wszystko subagent **`seo-strateg`**
> (`.claude/agents/seo-strateg.md`), który odpala się automatycznie przy zadaniach SEO.

## Zawartość warstwy `seo/shopify/`

| Element | Rola |
|---|---|
| `README.md` (ten plik) | Pełna metodyka audytu SEO Shopify (19 zagadnień + raport). |
| `seo_audit_crawl.py` | Reużywalny crawler: pobiera URL-e i parsuje H1-H6, title, meta, canonical, hreflang, OG, JSON-LD. |

---

## Co Shopify obsługuje AUTONOMICZNIE

Te funkcje platforma realizuje **bez ingerencji w motyw ani panel**. Nie tracić
na nie czasu - sprawdzić tylko, że nie złamały ich aplikacje / custom code.

| # | Zagadnienie | Co Shopify robi auto | Dokumentacja |
|---|---|---|---|
| 1 | **Struktura URL** | Wymusza prefiksy `/products/`, `/collections/`, `/pages/`, `/blogs/<blog>/<article>` - nie można zmienić. Handle z tytułu. | [URL structure](https://help.shopify.com/en/manual/online-store/themes/managing-themes/url-structure) |
| 2 | **Canonical URL** | `canonical_url` zwraca poprawną wartość: produkt w kolekcji (`/collections/x/products/y`) i `?variant=` → canonical na `/products/y`. | [canonical_url](https://shopify.dev/docs/api/liquid/objects/canonical_url) |
| 3 | **SSL / HTTPS** | Darmowy TLS na każdą domenę, auto-odnawiany. „Force HTTPS" robi 301 z HTTP. | [Secure connections](https://help.shopify.com/en/manual/domains/managing-domains/secure-connections) |
| 4 | **robots.txt** | Auto-generowany. Blokuje `/cart`, `/checkout`, `/account`, `/orders`, `/search`, `?q=`, filtry. Edycja tylko przez `templates/robots.txt.liquid`. | [Editing robots.txt](https://help.shopify.com/en/manual/promoting-marketing/seo/editing-robots-txt) |
| 5 | **sitemap.xml** | `/sitemap.xml`, indeks + sub-mapy products/collections/pages/blogs. Auto-aktualizacja, wyklucza ukryte/draft. Per international domain (Basic+). | [Finding sitemap](https://help.shopify.com/en/manual/promoting-marketing/seo/find-site-map) |
| 6 | **Przekierowania 301** | Przy zmianie handle checkbox „Create a URL redirect…" (domyślnie ON). Manualne: Content → URL redirects. | [URL redirects](https://help.shopify.com/en/manual/online-store/menus-and-links/url-redirect) |
| 7 | **Paginacja** | `canonical_url` jest **self-referential** na `?page=N` (zgodne z Google po deprecation `rel=prev/next`). | [canonical_url](https://shopify.dev/docs/api/liquid/objects/canonical_url) |
| 8 | **Filtry (faceted nav)** | Storefront filters używają `?filter.*`. Domyślny robots.txt blokuje wiele wariantów; motyw zwykle emituje canonical do czystego URL kolekcji. | [Storefront filtering](https://shopify.dev/docs/storefronts/themes/navigation-search/filtering/storefront-filtering/support) |
| 9 | **hreflang** | Przy Markets + opublikowanych alternatywnych językach - adnotacje hreflang wstrzykiwane automatycznie przez `content_for_header`. Sitemap zawiera warianty językowe. | [Markets domains & languages](https://help.shopify.com/en/manual/markets/customizations/domains-and-languages) · [Multi-language](https://shopify.dev/docs/storefronts/themes/markets/multiple-currencies-languages) |
| 10 | **Obrazy (CDN + WebP/AVIF)** | `image_url` / `img_url` serwuje WebP/AVIF do wspieranych przeglądarek, on-the-fly resize do 5760 px. | [image_url filter](https://shopify.dev/docs/api/liquid/filters/image_url) |

### Czego Shopify NIE robi automatycznie (częste pomyłki)

| Zagadnienie | Stan | Dokumentacja |
|---|---|---|
| **JSON-LD Product / Article** | Filtr `structured_data` istnieje, ale emitowany TYLKO jeśli motyw go wywoła (`{{ product \| structured_data }}`). Shopify nie wstrzykuje sam. | [structured_data](https://shopify.dev/docs/api/liquid/filters/structured_data) |
| **BreadcrumbList / Organization / WebSite JSON-LD** | W całości po stronie motywu - brak natywnego filtru. | - |
| **ALT-y obrazów** | Motyw renderuje, ale wartość pochodzi z panelu (`product.featured_image.alt`). Shopify nie generuje. | - |
| **`checkout.liquid` + script tags** | **Sunset 28.08.2025** dla Thank-you / Order status. Tracking → Web Pixels / Checkout Extensibility. | [checkout.liquid](https://shopify.dev/docs/storefronts/themes/architecture/layouts/checkout-liquid) · [Plus upgrade guide](https://help.shopify.com/en/manual/checkout-settings/customize-checkout-configurations/upgrade-thank-you-order-status/plus-upgrade-guide) |
| **GA4 / GTM w `<head>`** | Po sunset `checkout.liquid` tracking przez sandbox Web Pixels (Settings → Customer events) - nie zobaczysz `gtag.js` w źródle. | [Customer events](https://help.shopify.com/en/manual/promoting-marketing/analytics/customer-events) |

---

## Metoda - 3 warstwy weryfikacji

Każde zagadnienie sprawdzamy w trzech miejscach:

| Warstwa | Co weryfikujemy | Narzędzia |
|---|---|---|
| **A. Platforma Shopify** | Czy funkcja dostarczana auto (URL, SSL, robots, sitemap, kanonikalizacja). | dokumentacja Shopify Help / shopify.dev |
| **B. Motyw (kod)** | Czy szablon poprawnie renderuje dane z platformy (title, meta, canonical, OG, JSON-LD, H1, alt). | `layout/theme.liquid`, `snippets/meta-tags.liquid`, `snippets/*-ld-json.liquid`, snippety nagłówków/banerów |
| **C. Panel + treści (klient)** | Czy pola wypełnione, redirecty utworzone, GSC zgłoszony, GA4/GTM podpięty. | Shopify Admin, GSC (raport Podstawowe wskaźniki internetowe), Rich Results Test |

---

## Lista zagadnień do sprawdzenia (19 pozycji)

Dla każdej pozycji odnotuj: **kto obsługuje** + **status** (✅ OK / ⚠️ do poprawy /
🔎 do sprawdzenia w panelu / ➖ N/D).

### 1. Struktura URL
- Shopify wymusza prefiksy `/products/`, `/collections/`, `/pages/`, `/blogs/` - poprawne, nie ruszać.
- Handle generowane z tytułu (małe litery, myślniki, diakrytyki usuwane).
- Produkt w wielu kolekcjach → **jeden kanoniczny URL** (`/products/handle`).
- Warianty `?variant=` nie powinny być indeksowane osobno (kanonikalizowane).
- **Sprawdź**: czy aplikacje nie generują własnych URL-i (`/a/...`, `/apps/...`).

### 2. SSL / HTTPS
- Shopify AUTO: certyfikat, „Force HTTPS", 301 z HTTP.
- **Sprawdź**: mixed content - brak `http://` w aplikacjach, custom liquid, snippetach analityki.

### 3. Meta title
- **Render w motywie**: `snippets/meta-tags.liquid` lub `layout/theme.liquid` → `<title>{{ page_title }} ...</title>`.
- **Treść w panelu**: „Search engine listing" pod produktem/kolekcją/stroną/artykułem.
- **Wytyczne treści**: unikalny per podstrona, ~55-65 znaków, marka na końcu, bez keyword stuffingu.
- **Sprawdź**: czy `shop.name` nie jest doklejany podwójnie (`unless page_title contains shop.name`).

### 4. Meta description
- Render: `<meta name="description" content="{{ page_description | escape }}">`.
- Treść w panelu - j.w.
- **Wytyczne treści**: unikalne, zachęcające do kliknięcia, USP/cena/dostawa/zwroty, ~120-160 zn. (Google może nadpisać).
- **Sprawdź**: blog homepage (częsty brak), kolekcje tagowe.

### 5. Linki kanoniczne
- Render: `<link rel="canonical" href="{{ canonical_url }}">` w `layout/theme.liquid`.
- Shopify liczy poprawnie: produkt w wielu kolekcjach → `/products/handle`, paginacja → self-canonical, filtry → canonical bez parametrów.
- **Sprawdź**: aplikacje nie nadpisują canonicala; canonical to **self** (ta sama domena/locale).

### 6. Dyrektywy robots / noindex
- Render w `snippets/meta-tags.liquid`: warunki na template (search, account, cart).
- **Wytyczne**: `noindex,follow` na: wyszukiwarka wewnętrzna (`/search`), koszyk/konto/zamówienia, strony techniczne, opcjonalnie głęboka paginacja.
- **Nie stosować** `nofollow` globalnie.

### 7. robots.txt
- Shopify AUTO - blokuje `/cart`, `/checkout(s)`, `/account`, `/orders`, `/admin`, `/search`, `/policies/`, filtry (`*sort_by*`, `*+*`, `*filter*&*filter*`).
- Zawiera `Sitemap: domena/sitemap.xml`.
- **Sprawdź**: czy nie ma własnego `templates/robots.txt.liquid` (zwykle nie potrzeba).

### 8. sitemap.xml
- Shopify AUTO pod `/sitemap.xml` - indeks + products/collections/pages/blogs + warianty językowe (`/en/`).
- Wyklucza ukryte (metafield `seo.hidden`), wersje robocze, strony techniczne.
- **Ręcznie**: zgłosić w Google Search Console po starcie.

### 9. Przekierowania 301
- Shopify AUTO przy zmianie handle (checkbox „Create URL redirect" - domyślnie ON).
- Panel: **Content → URL Redirects**, import CSV (`Redirect from,Redirect to`).
- **Sprawdź**: brak łańcuchów 301→301→200, brak redirect → 404, czyszczenie po migracji.
- **Przekierowania po migracji**: sprawdzaj `redirect_checker.py` (łańcuchy, pętle, 404). Masowy import przekierowań robi Igor.

### 10. Paginacja
- Shopify: self-canonical na `?page=N` (`rel=next/prev` wycofane).
- **Sprawdź**: opis kategorii tylko na stronie 1 (`unless paginate.current_page > 1`).

### 11. Filtrowanie / faceted navigation
- Natywne filtry (Search & Discovery) → `?filter.*`; Shopify kanonikalizuje do czystego URL i nie dodaje do sitemap.
- **Sprawdź**: czy aplikacje filtrów nie generują indeksowalnych URL-i.
- Opcjonalnie: `templates/robots.txt.liquid` z `Disallow: *?filter.*` (tylko bardzo duży katalog).

### 12. Dane strukturalne (JSON-LD)
**Shopify NIE dodaje sam - w całości w motywie.**

| Schema | Plik / lokalizacja |
|---|---|
| Organization + WebSite (+ SearchAction) | `snippets/header-ld-json.liquid` lub `theme.liquid` |
| Product (+ Offer + Brand + AggregateRating) | `snippets/main-product-ld-json.liquid` → `{{ product \| structured_data }}` |
| Article | `snippets/main-article-ld-json.liquid` → `{{ article \| structured_data }}` |
| BreadcrumbList | własna impl. w `snippets/breadcrumb.liquid` (Home → kolekcja → produkt) |
| FAQPage | tylko jeśli FAQ realnie występuje (inaczej ostrzeżenia w GSC) |

**Weryfikacja**: Google Rich Results Test dla home / produktu / artykułu.

### 13. hreflang
- Shopify AUTO przy Markets / wielu opublikowanych językach, wstrzyk przez `{{ content_for_header }}`.
- **Sprawdź**: HTML zawiera `<link rel="alternate" hreflang="...">` dla każdej wersji + `x-default`.

### 14. Mobile / Core Web Vitals
- Infra Shopify auto (CDN, HTTP/2); wynik = motyw + aplikacje + waga grafik.
- **Cele (mobile)**: LCP < 2,5 s · INP < 200 ms · CLS < 0,1.
- **Sprawdź**: raport Podstawowe wskaźniki internetowe w GSC (dane terenowe) + ryzyka z kodu (`lcp_subparts.py`, `image_weight_audit.py`, `third_party_script_audit.py`). Pomiar przez PageSpeed Insights API jest w tym projekcie wyłączony (brak klucza).

### 15. Optymalizacja grafik
- CDN/WebP/AVIF - auto.
- **Motyw** (`snippets/image.liquid` lub równoważne):
  - `width`/`height` z `image.width/height` → CLS,
  - `loading="lazy"` domyślnie + `eager` + `fetchpriority="high"` dla pierwszej sekcji (LCP),
  - `alt: alt | default: image.alt`.
- **Panel/klient**: wypełnić ALT-y w Admin (motyw je pobiera, Shopify nie generuje).
- **Sprawdź**: pokrycie ALT produktów (Admin API: `products(first:250){ media{ ... alt } }`).

### 16. Wersje językowe
- Shopify Markets + **Translate & Adapt**.
- Każda wersja: unikalny URL (`/en/...`), hreflang auto.

### 17. Struktura bloga
- Motyw renderuje H1 = `article.title`.
- **Klient**: autor (E-E-A-T), data publikacji + aktualizacji, multimedia, spis treści, linkowanie do produktów.
- **Sprawdź**: brak podwójnego H1 (drugi H1 = często pierwszy nagłówek wstępu → zamień na H2 w edytorze HTML).

### 18. Narzędzia analityczne
- **GA4**: kanał Google & YouTube (oficjalny).
- **GTM**: Custom Pixel w **Settings → Customer events** (po sunset `checkout.liquid` 28.08.2025 - tracking przez Web Pixels / Checkout Extensibility).
- **Sprawdź**: HTML NIE zawiera `gtag.js` - Shopify ładuje przez sandbox Web Pixels.
- Dodatkowo: mapy ciepła / nagrania sesji (Hotjar, Clarity).

### 19. Aplikacje Shopify
- Audyt zainstalowanych aplikacji - każda obciąża CWV.
- Usunąć nieużywane (Settings → Apps and sales channels).

---

## Weryfikacja H1 i spójności logicznej szablonu

Najczęstsze błędy struktury (sprawdzać dla każdego typu szablonu):

| Problem | Gdzie szukać |
|---|---|
| Wiele H1 na home (banery jako `<h1>`) | `snippets/img-banner-*.liquid`, `sections/hero-*.liquid` - sparametryzować `heading_tag` (domyślnie h2) |
| Wiele H1 na produkcie (tytuł sekcji „Opisy" jako H1) | `sections/main-product.liquid`, sekcje rekomendacji |
| Wiele H1 na artykule (pierwszy nagłówek wstępu w body) | edytor HTML artykułu w Admin |
| H1 = 0 na kolekcji | `sections/main-collection.liquid` / `collection-intro.liquid` - tytuł tylko gdy ustawiony |
| Podwójne „Kolekcja: Kolekcja…" | admin title kolekcji zawiera „Kolekcja" + prefix z motywu |
| H6 w nav, H5 w footerze, H5 na kartach produktów | `snippets/header-*`, `snippets/footer-*`, `snippets/product-card-*` - zamienić na `<span>`/`<p>`/`<h3>` |
| H1 ukryty wizualnie na search | OK, ale musi istnieć w DOM |

**Narzędzie**: rozszerzenie „Detailed SEO" lub `document.querySelectorAll('h1').length` w konsoli.

---

## Jak crawlować

WebFetch / LLM bywa zawodny (halucynuje canonical/OG/JSON-LD). Preferowane:
**pobranie HTML + parsing**. W tym folderze jest gotowy skrypt:

```bash
python seo_audit_crawl.py https://domena.com/ https://domena.com/products/xxx ...
# albo lista URL-i z pliku:
python seo_audit_crawl.py --file urls.txt
```

Zwraca per URL: status, liczbę H1-H6, title, meta description, canonical, liczbę
hreflang, obecność `og:image`, liczbę bloków JSON-LD. Bez zależności (stdlib).

Ręczny odpowiednik (PowerShell + curl), gdyby trzeba ad-hoc:
```powershell
curl.exe -sL -A "Mozilla/5.0" "https://domena.com/products/xxx" -o "$env:TEMP\page.html"
python seo_audit_crawl.py --file - < nul   # lub przekaż URL bezpośrednio
```

**Zakres crawla (~15-25 URL-i)**: home + wszystkie kolekcje z menu + 6-10
produktów (bestseller / nowość / OOS) + blog homepage + 3-5 artykułów + strony
statyczne (kontakt, o-nas, regulamin, polityka).

---

## Format raportu finalnego

1. **Kontekst** - co audytujemy, jakie wytyczne, jaki sklep/motyw, źródła weryfikacji.
2. **Tabela zbiorcza 19 zagadnień** - kolumny: `#`, `Zagadnienie`, `Kto obsługuje`, `Status`.
3. **Co Shopify robi autonomicznie** - sekcja „nie ruszamy".
4. **Zweryfikowane w kodzie motywu - ✅ działa** - z odnośnikami do plików i linii (`layout/theme.liquid:25`).
5. **Wykryte problemy w motywie - zadania kodowe** - z priorytetem (wysoki/średni/niski), opisem, sugestią naprawy.
6. **Zadania po stronie klienta - ręczne** - checklist (meta, ALT-y, redirecty, GSC, GA4/GTM, mixed content, aplikacje).
7. **Weryfikacja na żywej witrynie** - jak potwierdzić każdy punkt (źródło strony, Rich Results Test, DevTools).
8. **Wyniki weryfikacji na produkcji** - co znaleziono + Admin API (pokrycie ALT, pola SEO, redirecty, hreflang).
9. **Podsumowanie** - ile z N zagadnień: autonomicznie / w motywie OK / do poprawy / ręcznie.

**Legenda statusów**: ✅ OK · ⚠️ DO POPRAWY · 🔎 DO SPRAWDZENIA · ➖ N/D · ✅ WDROŻONE (po naprawie: data + commit).

---

## Re-crawl po naprawach

24-48 h po deploy / edycjach w Admin. Porównaj z poprzednim raportem w sekcji
„v1 → v2": ✅ naprawione · ❌ utrzymane · ⬆ poprawa · ⚠ nowy problem.
