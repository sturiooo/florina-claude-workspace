#!/usr/bin/env python3
"""Polityka zmian w sklepie Florina: JEDNO miejsce, ktore decyduje, jakie mutacje Admin API sa dozwolone.

Uzywaja jej dwa mechanizmy:
  1. hook PreToolUse (.claude/hooks/straznik.py) zanim Claude Code uruchomi komende,
  2. scripts/shopify_gql.py w chwili faktycznego wyslania zapytania do Shopify.

Zasada: LISTA DOZWOLONYCH. Mutacja spoza listy jest blokowana, nawet jesli nikt jej tu nie przewidzial.
Zmiany w tym pliku robi tylko Igor (Claude ma zablokowana edycje katalogu .claude/hooks).
"""
import re

# Mutacje, ktore osoba obslugujaca sklep moze wykonac (zawsze PO potwierdzeniu w oknie Claude Code).
DOZWOLONE_MUTACJE = {
    # opisy, tagi, SEO produktu (bez statusu, uchwytu, kategorii: patrz ZAKAZANE_POLA)
    "productUpdate",
    "tagsAdd",
    "tagsRemove",
    # kolekcje: tylko przypisanie produktow i opis
    "collectionAddProducts",
    "collectionAddProductsV2",
    "collectionRemoveProducts",
    "collectionReorderProducts",
    "collectionUpdate",
    # ocechowanie i FAQ
    "metafieldsSet",
    "metaobjectCreate",
    "metaobjectUpdate",
    # media
    "stagedUploadsCreate",
    "fileCreate",
    "fileUpdate",
    "productCreateMedia",
    "productUpdateMedia",
    "productReorderMedia",
    "productVariantAppendMedia",
    # tlumaczenia (opcjonalnie, wymaga scope write_translations)
    "translationsRegister",
}

# Czytelne powody dla najczestszych zakazanych operacji (reszta dostaje komunikat ogolny).
ZAKAZANE_WZORCE = [
    (r"Delete", "usuwanie danych"),
    (r"(?<!collection)Remove(?!Products)", "usuwanie danych"),
    (r"^(productCreate|productDuplicate|productSet|productChangeStatus)$", "tworzenie lub nadpisywanie calych produktow"),
    (r"^productVariant", "warianty, ceny i stany magazynowe"),
    (r"^inventory", "stany magazynowe"),
    (r"^priceList|^quantityPricing|^quantityRules", "cenniki"),
    (r"^discount|^giftCard", "rabaty i karty podarunkowe"),
    (r"^theme|^onlineStoreTheme", "motyw i kod sklepu"),
    (r"^order|^draftOrder|^refund|^return|^fulfillment|^reverse", "zamowienia, zwroty i wysylki"),
    (r"^customer|^company", "klienci i firmy B2B"),
    (r"^payment|^shopPolicy|^shopLocale|^market|^delivery|^location|^webPresence", "ustawienia sklepu"),
    (r"^publishable|^publication", "widocznosc w kanalach sprzedazy"),
    (r"^bulkOperation", "operacje masowe w tle"),
    (r"^metafieldDefinition|^metaobjectDefinition|^standardMetafield|^standardMetaobject", "struktura metapol i metaobiektow"),
    (r"^collectionCreate|^collectionDuplicate", "tworzenie kolekcji (decyzja Igora)"),
    (r"^urlRedirect|^menu", "przekierowania i nawigacja"),
    (r"^webhook|^app|^eventBridge|^pubSub", "integracje i aplikacje"),
    (r"^sellingPlan|^subscription", "subskrypcje"),
    (r"^translationsRemove", "usuwanie tlumaczen"),
]

# Pola, ktorych NIE wolno ustawiac nawet w dozwolonej mutacji.
ZAKAZANE_POLA = {
    "productUpdate": {
        "status": "zmiana statusu (aktywny / wersja robocza / zarchiwizowany) ukrywa produkt",
        "handle": "zmiana uchwytu psuje adres URL i pozycje w Google",
        "redirectNewHandle": "zmiana uchwytu psuje adres URL",
        "category": "kategoria produktu decyduje o stawce VAT",
        "templateSuffix": "zmiana szablonu to zmiana wygladu (motyw)",
        "giftCard": "karta podarunkowa",
        "requiresSellingPlan": "subskrypcje",
        "variants": "warianty i ceny",
        "collectionsToLeave": "wypisywanie z kolekcji rob przez collectionRemoveProducts, po jednej kolekcji",
    },
    "collectionUpdate": {
        "handle": "zmiana uchwytu psuje adres URL kolekcji",
        "redirectNewHandle": "zmiana uchwytu psuje adres URL kolekcji",
        "ruleSet": "zmiana regul kolekcji automatycznej przenosi setki produktow naraz",
        "sources": "zmiana regul kolekcji automatycznej przenosi setki produktow naraz",
        "templateSuffix": "zmiana szablonu to zmiana wygladu (motyw)",
        "products": "przypisania produktow rob przez collectionAddProducts",
    },
}

# Typy obiektow, ktorych identyfikatory (gid) moga sie pojawic w zmianie.
DOZWOLONE_GID = {
    "Product", "ProductVariant", "Collection", "Metaobject",
    "MediaImage", "Video", "ExternalVideo", "GenericFile", "Model3d", "ProductImage",
    "Metafield",  # tylko jako cel tlumaczenia (translationsRegister); usuwanie metapol blokuje lista nazw
}

# Przestrzenie metapol zarezerwowane dla aplikacji (opinie, feed Google): nie zapisujemy recznie.
ZAKAZANE_PRZESTRZENIE = ["reviews", "judgeme", "mm-google-shopping", "shopify--discovery"]

# Maksymalna liczba roznych obiektow w jednej zmianie (male partie).
MAKS_OBIEKTOW = 60

# Metody BaseLinkera: wolno tylko czytac (get...).
BL_ZAPIS = re.compile(r"""["'=]\s*((?:add|set|update|delete|create|run|unlink|move|send)[A-Z]\w*)""")


def _pomin_napis(t, i):
    """t[i] == '"'. Zwraca indeks za koncem napisu GraphQL (zwyklego albo blokowego)."""
    if t.startswith('"""', i):
        j = t.find('"""', i + 3)
        return len(t) if j < 0 else j + 3
    j = i + 1
    while j < len(t):
        if t[j] == "\\":
            j += 2
            continue
        if t[j] == '"':
            return j + 1
        j += 1
    return len(t)


def _pomin_nawiasy(t, i):
    """t[i] == '('. Zwraca indeks za domknieciem nawiasu (z pominieciem napisow)."""
    glebokosc = 0
    j = i
    while j < len(t):
        c = t[j]
        if c == '"':
            j = _pomin_napis(t, j)
            continue
        if c == "(":
            glebokosc += 1
        elif c == ")":
            glebokosc -= 1
            if glebokosc == 0:
                return j + 1
        j += 1
    return len(t)


def nazwy_mutacji(tekst):
    """Zwraca liste pol najwyzszego poziomu we wszystkich operacjach `mutation` w tekscie."""
    wynik = []
    for m in re.finditer(r"\bmutation\b", tekst):
        j = m.end()
        # pomin nazwe operacji i definicje zmiennych az do pierwszego '{'
        while j < len(tekst) and tekst[j] != "{":
            if tekst[j] == "(":
                j = _pomin_nawiasy(tekst, j)
                continue
            if tekst[j] in "};":
                break
            j += 1
        if j >= len(tekst) or tekst[j] != "{":
            wynik.append("?nieczytelna-mutacja")
            continue
        glebokosc = 0
        k = j
        while k < len(tekst):
            c = tekst[k]
            if c == '"':
                k = _pomin_napis(tekst, k)
                continue
            if c == "{":
                glebokosc += 1
                k += 1
                continue
            if c == "}":
                glebokosc -= 1
                k += 1
                if glebokosc == 0:
                    break
                continue
            if c == "(":
                k = _pomin_nawiasy(tekst, k)
                continue
            if glebokosc == 1 and (c.isalpha() or c == "_"):
                n = re.match(r"[A-Za-z_]\w*", tekst[k:]).group(0)
                k += len(n)
                reszta = tekst[k:].lstrip()
                if reszta.startswith(":"):  # alias: pole
                    k = len(tekst) - len(reszta) + 1
                    m2 = re.match(r"\s*([A-Za-z_]\w*)", tekst[k:])
                    if m2:
                        n = m2.group(1)
                        k += m2.end()
                if n not in ("on", "fragment"):
                    wynik.append(n)
                continue
            k += 1
    return wynik


def ocen_mutacje(tekst):
    """Ocena tekstu zawierajacego GraphQL (i ewentualnie zmienne JSON).

    Zwraca (decyzja, powody, nazwy):
      decyzja = "brak"   -> tekst nie zawiera mutacji,
                "pytaj"  -> mutacja dozwolona, wymaga potwierdzenia czlowieka,
                "zakaz"  -> mutacja zablokowana.
    """
    nazwy = nazwy_mutacji(tekst)
    if not nazwy:
        return "brak", [], []
    powody = []
    for n in nazwy:
        if n in DOZWOLONE_MUTACJE:
            continue
        opis = None
        for wzorzec, o in ZAKAZANE_WZORCE:
            if re.search(wzorzec, n):
                opis = o
                break
        if n.startswith("?"):
            powody.append("Nie umiem odczytac tresci mutacji, wiec jej nie przepuszczam. Zapisz ja w pliku .graphql i uzyj scripts/shopify_gql.py.")
        elif opis:
            powody.append(f"`{n}` jest zablokowane ({opis}). Taka zmiane robi Igor.")
        else:
            powody.append(f"`{n}` nie jest na liscie dozwolonych zmian. Jesli jest potrzebna, zapytaj Igora.")
    for n in set(nazwy):
        for pole, dlaczego in ZAKAZANE_POLA.get(n, {}).items():
            if re.search(r'(?<![\w$])"?' + re.escape(pole) + r'"?\s*:', tekst):
                powody.append(f"`{n}` z polem `{pole}` jest zablokowane: {dlaczego}.")
    typy = set(re.findall(r"gid://shopify/([A-Za-z0-9]+)/", tekst))
    zle = sorted(t for t in typy if t not in DOZWOLONE_GID)
    if zle:
        powody.append("Zmiana dotyczy obiektow, ktorych nie wolno zmieniac: " + ", ".join(zle) + " (np. zamowienia, klienci, ustawienia).")
    for p in ZAKAZANE_PRZESTRZENIE:
        if re.search(r'namespace"?\s*:\s*\\?"' + re.escape(p), tekst):
            powody.append(f"Metapola z przestrzeni `{p}` zapisuje aplikacja, nie czlowiek.")
    obiekty = set(re.findall(r"gid://shopify/(?:Product|Collection|Metaobject|ProductVariant)/\d+", tekst))
    if len(obiekty) > MAKS_OBIEKTOW:
        powody.append(f"Jedna zmiana dotyczy {len(obiekty)} obiektow. Limit to {MAKS_OBIEKTOW}: podziel prace na mniejsze partie.")
    if powody:
        return "zakaz", powody, nazwy
    return "pytaj", [], nazwy


def opis_zmiany(nazwy, tekst):
    """Krotki, ludzki opis zmiany do okna potwierdzenia."""
    ile = {}
    for n in nazwy:
        ile[n] = ile.get(n, 0) + 1
    czesci = [f"{n} x{c}" if c > 1 else n for n, c in ile.items()]
    obiekty = set(re.findall(r"gid://shopify/(Product|Collection|Metaobject|ProductVariant)/(\d+)", tekst))
    typy = {}
    for t, _ in obiekty:
        typy[t] = typy.get(t, 0) + 1
    slownik = {"Product": "produkty", "Collection": "kolekcje", "Metaobject": "wpisy FAQ / metaobiekty", "ProductVariant": "warianty"}
    obj = ", ".join(f"{slownik.get(t, t)}: {c}" for t, c in typy.items())
    return "ZMIANA W SKLEPIE: " + ", ".join(czesci) + (f" ({obj})" if obj else "")


def ocen_baselinker(tekst):
    """Zwraca liste zakazanych metod BaseLinkera (zapis) znalezionych w tekscie."""
    if not re.search(r"baselinker|connector\.php", tekst, re.I):
        return []
    return sorted(set(BL_ZAPIS.findall(tekst)))
