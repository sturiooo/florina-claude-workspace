#!/usr/bin/env python3
"""Polityka zmian w sklepie Florina: JEDNO miejsce, ktore decyduje, jakie mutacje Admin API wolno wykonac.

Uzywaja jej:
  1. hook PreToolUse (.claude/hooks/straznik.py), zanim Claude Code uruchomi komende,
  2. scripts/shopify_gql.py w chwili faktycznego wyslania zapytania do Shopify.

Zasada (decyzja Igora, 14.10.2026): "praktycznie wszystko poza edycja szablonu".
  - ZAKAZ:  motyw / szablon (theme*), ustawienia sklepu, platnosci, operacje finansowe (zwroty, pobrania,
            anulowanie), rynki i dostawy, aplikacje i webhooki, pracownicy, operacje masowe w tle, karty podarunkowe.
            Zmiany motywu robi czlowiek sciezka "!" (skill zmiany-w-szablonie, scripts/szablon_wgraj.py).
  - USUN:   kazde usuwanie (*Delete, *Remove, *Unpublish...) -> pytanie z twardym ostrzezeniem + obowiazkowy backup.
  - PYTAJ:  cala reszta (produkty, warianty, ceny, stany, publikacja, kolekcje i reguly, metapola i definicje,
            metaobiekty i definicje, rabaty, strony, blog, nawigacja, przekierowania, tlumaczenia, pliki, klienci,
            zamowienia: edycja, tagi, notatki).
Zmiany w tym pliku robi tylko Igor (Claude ma zablokowana edycje .claude/).
"""
import re

# Zakazane zawsze (wzorzec nazwy mutacji, powod). Pierwszy pasujacy wygrywa.
ZAKAZANE_WZORCE = [
    (r"^theme|^onlineStoreTheme", "zmiana motywu / szablonu: to robi czlowiek sciezka `!` (skill zmiany-w-szablonie)"),
    (r"^shop[A-Z]|^shopifyPayments", "ustawienia sklepu (dane sklepu, jezyki, polityki, Shopify Payments)"),
    (r"[Pp]ayment", "platnosci"),
    (r"^refund|^returnRefund|^orderCapture|^transaction|^orderCancel|^orderMarkAsPaid|^suggestedRefund",
     "operacje finansowe na zamowieniach (zwroty, pobrania, anulowanie)"),
    (r"^market|^webPresence|^delivery|^location|^carrierService|^fulfillmentService|^backupRegion",
     "ustawienia rynkow, dostaw i lokalizacji"),
    (r"^app[A-Z]|^webhook|^eventBridge|^pubSub|^storefrontAccessToken|^scriptTag|^webPixel|^serverPixel",
     "aplikacje, integracje i skrypty"),
    (r"^staff|^checkoutBranding|^checkoutProfile|^validation|^cartTransform|^consentPolicy",
     "pracownicy i ustawienia kasy"),
    (r"^bulkOperation", "operacje masowe w tle (omijaja limit partii i backup)"),
    (r"^giftCard", "karty podarunkowe (pieniadze)"),
]

# Usuwanie: dozwolone z twardym ostrzezeniem i backupem wszystkiego, czego dotyczy.
USUWANIE = re.compile(r"Delete|Remove|Unpublish|Destroy|Detach")
NIE_USUWANIE = {"tagsRemove"}  # zdjecie tagu: odwracalne, zwykla zmiana

# Ostrzezenia dopisywane do okna zgody, gdy w zmianie sa te pola.
OSTRZEZENIA_POL = {
    "handle": "zmiana uchwytu zmienia adres URL (sprawdz przekierowanie)",
    "status": "zmiana statusu moze ukryc albo pokazac produkt / rabat",
    "category": "kategoria produktu decyduje o stawce VAT",
    "price": "zmiana ceny",
    "compareAtPrice": "zmiana ceny przekreslonej",
    "ruleSet": "zmiana regul kolekcji automatycznej przenosi wiele produktow naraz",
    "quantities": "zmiana stanow magazynowych (BaseLinker moze je nadpisac przy synchronizacji)",
    "templateSuffix": "zmiana szablonu strony (wyglad)",
}

# Typy obiektow, ktorych nie wolno zmieniac nawet "przy okazji".
ZAKAZANE_GID = {"OnlineStoreTheme", "OnlineStoreThemeFile", "Shop", "Location", "Market", "StaffMember", "App", "AppInstallation"}

# Metapola zapisywane przez aplikacje: ostrzegamy.
PRZESTRZENIE_APEK = ["reviews", "judgeme", "mm-google-shopping", "shopify--discovery"]

MAKS_OBIEKTOW = 250

# BaseLinker: wolno tylko czytac (get...).
BL_ZAPIS = re.compile(r"""["'=]\s*((?:add|set|update|delete|create|run|unlink|move|send)[A-Z]\w*)""")


def _pomin_napis(t, i):
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
    """Lista pol najwyzszego poziomu we wszystkich operacjach `mutation` w tekscie (aliasy rozwiniete)."""
    wynik = []
    for m in re.finditer(r"\bmutation\b", tekst):
        j = m.end()
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
                if reszta.startswith(":"):
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


def czy_usuwanie(nazwa):
    return nazwa not in NIE_USUWANIE and bool(USUWANIE.search(nazwa))


def ocen_mutacje(tekst):
    """Zwraca (decyzja, powody, nazwy, ostrzezenia).

    decyzja: "brak" (nie ma mutacji), "pytaj" (zwykla zmiana), "usun" (usuwanie), "zakaz".
    """
    nazwy = nazwy_mutacji(tekst)
    if not nazwy:
        return "brak", [], [], []
    powody, ostrzezenia = [], []
    usuwanie = False
    for n in nazwy:
        if n.startswith("?"):
            powody.append("Nie umiem odczytac tresci mutacji, wiec jej nie przepuszczam. Zapisz ja w pliku .graphql i uzyj scripts/shopify_gql.py.")
            continue
        for wzorzec, opis in ZAKAZANE_WZORCE:
            if re.search(wzorzec, n):
                powody.append(f"`{n}` jest zablokowane: {opis}.")
                break
        else:
            if czy_usuwanie(n):
                usuwanie = True
    typy = set(re.findall(r"gid://shopify/([A-Za-z0-9]+)/", tekst))
    zle = sorted(typy & ZAKAZANE_GID)
    if zle:
        powody.append("Zmiana dotyczy obiektow, ktorych nie wolno zmieniac: " + ", ".join(zle) + ".")
    obiekty = set(re.findall(r"gid://shopify/[A-Za-z0-9]+/\d+", tekst))
    if len(obiekty) > MAKS_OBIEKTOW:
        powody.append(f"Jedna zmiana dotyczy {len(obiekty)} obiektow. Limit to {MAKS_OBIEKTOW}: podziel prace na mniejsze partie.")
    if powody:
        return "zakaz", powody, nazwy, []
    for pole, opis in OSTRZEZENIA_POL.items():
        if re.search(r'(?<![\w$])\\?"?' + re.escape(pole) + r'\\?"?\s*:', tekst):
            ostrzezenia.append(opis)
    for p in PRZESTRZENIE_APEK:
        if re.search(r'namespace\\?"?\s*:\s*\\?"' + re.escape(p), tekst):
            ostrzezenia.append(f"metapola `{p}` zwykle zapisuje aplikacja, reczna zmiana moze zostac nadpisana")
    return ("usun" if usuwanie else "pytaj"), [], nazwy, ostrzezenia


def opis_zmiany(nazwy, tekst, decyzja="pytaj", ostrzezenia=None):
    """Krotki, ludzki opis zmiany do okna potwierdzenia."""
    ile = {}
    for n in nazwy:
        ile[n] = ile.get(n, 0) + 1
    czesci = [f"{n} x{c}" if c > 1 else n for n, c in ile.items()]
    obiekty = set(re.findall(r"gid://shopify/([A-Za-z0-9]+)/(\d+)", tekst))
    typy = {}
    for t, _ in obiekty:
        typy[t] = typy.get(t, 0) + 1
    obj = ", ".join(f"{t}: {c}" for t, c in sorted(typy.items()))
    poczatek = "UWAGA, USUWANIE W SKLEPIE (nie da sie cofnac inaczej niz z backupu): " if decyzja == "usun" else "ZMIANA W SKLEPIE: "
    opis = poczatek + ", ".join(czesci) + (f" (obiekty: {obj})" if obj else "")
    if ostrzezenia:
        opis += ". Uwaga: " + "; ".join(dict.fromkeys(ostrzezenia))
    return opis


def ocen_baselinker(tekst):
    """Lista zakazanych metod BaseLinkera (zapis) znalezionych w tekscie."""
    if not re.search(r"baselinker|connector\.php", tekst, re.I):
        return []
    return sorted(set(BL_ZAPIS.findall(tekst)))
