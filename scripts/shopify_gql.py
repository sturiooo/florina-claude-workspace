#!/usr/bin/env python3
"""Jedyna droga do Admin API Shopify w tym projekcie (przez Shopify CLI: `shopify store execute`).

ODCZYT:
  python scripts/shopify_gql.py --query "{ shop { name } }"
  python scripts/shopify_gql.py --query-file robocze/zapytanie.graphql --variables "{\"q\": \"tag:GARNKI\"}"
  python scripts/shopify_gql.py --query-file robocze/produkty.graphql --wszystkie products --out raporty/x.json
    (--wszystkie <sciezka do polaczenia>: pobiera wszystkie strony; zapytanie musi miec $after: String,
     argument after: $after i pageInfo { hasNextPage endCursor })

ZMIANA W SKLEPIE (tylko po zgodzie uzytkownika, po backupie):
  python scripts/shopify_gql.py --query-file robocze/zmiana.graphql --variable-file robocze/zmienne.json --allow-mutations

Skrypt sam pilnuje zasad (.claude/hooks/polityka_zmian.py: motyw i ustawienia zablokowane, reszta za zgoda),
wymaga dzisiejszego backupu kazdego zmienianego obiektu, a przy usuwaniu kazdego obiektu w zmianie (backup/RRRR-MM-DD/)
i zapisuje kazda zmiane w dziennik/zmiany.log.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wspolne import PROJEKT, dzis, sklep, wersja_api_domyslna  # noqa: E402

sys.path.insert(0, os.path.join(PROJEKT, ".claude", "hooks"))
from polityka_zmian import ocen_mutacje  # noqa: E402

# Obiekty, ktore zmiana modyfikuje (klucze typu id / ownerId ...). Przy usuwaniu: kazdy gid w zmianie.
CELE = re.compile(r'\\?"?(?:id|ids|ownerId|productId|collectionId|resourceId|customerId|orderId|inventoryItemId|discountId|fileIds|productIds)\\?"?\s*:\s*\[?\s*\\?"(gid://shopify/[A-Za-z0-9]+/\d+)')
WSZYSTKIE_GID = re.compile(r"gid://shopify/[A-Za-z0-9]+/\d+")
# Typy, ktore sa tylko wskazaniem (nie ma czego cofac w samym obiekcie)
BEZ_BACKUPU = {"Location", "Publication", "Channel", "TaxonomyCategory", "TaxonomyValue", "MetaobjectDefinition"}


class BladShopify(Exception):
    pass


def _cli():
    sciezka = shutil.which("shopify")
    if not sciezka:
        raise BladShopify("Nie znaleziono Shopify CLI (komenda `shopify`). Uruchom ponownie install.ps1.")
    return [sciezka]


def _wymagany_backup(tekst, usuwanie=False):
    """Zwraca liste gid, dla ktorych brakuje dzisiejszego backupu."""
    if usuwanie:
        cele = set(WSZYSTKIE_GID.findall(tekst))
    else:
        cele = set(CELE.findall(tekst))
        for lista in re.findall(r'(?:ids|fileIds|productIds)\\?"?\s*:\s*\[([^\]]*)\]', tekst):
            cele |= set(WSZYSTKIE_GID.findall(lista))
    cele = sorted(g for g in cele if g.split("/")[3] not in BEZ_BACKUPU)
    if not cele:
        return []
    zawartosc = ""
    for plik in glob.glob(os.path.join(PROJEKT, "backup", dzis(), "*.json")):
        try:
            with open(plik, encoding="utf-8") as f:
                zawartosc += f.read()
        except Exception:
            pass
    return [g for g in cele if f'"{g}"' not in zawartosc]


def _loguj_zmiane(nazwy, tekst, wynik, blad=None):
    try:
        os.makedirs(os.path.join(PROJEKT, "dziennik"), exist_ok=True)
        with open(os.path.join(PROJEKT, "dziennik", "zmiany.log"), "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "czas": datetime.now().isoformat(timespec="seconds"),
                "sklep": sklep(),
                "mutacje": nazwy,
                "obiekty": sorted(set(WSZYSTKIE_GID.findall(tekst)))[:300],
                "bledy": blad or _bledy_uzytkownika(wynik),
                "tresc": tekst[:4000],
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _bledy_uzytkownika(wynik):
    bledy = []

    def szukaj(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if (k == "userErrors" or k.endswith("UserErrors")) and v:
                    bledy.extend(v)
                else:
                    szukaj(v)
        elif isinstance(x, list):
            for v in x:
                szukaj(v)
    szukaj(wynik)
    return bledy


def wykonaj(zapytanie, zmienne=None, zmiany=False, wersja_api=None):
    """Wysyla zapytanie i zwraca slownik `data`. Rzuca BladShopify z czytelnym opisem."""
    tekst = zapytanie + "\n" + json.dumps(zmienne or {}, ensure_ascii=False)
    decyzja, powody, nazwy, _ = ocen_mutacje(tekst)
    zmiana = decyzja in ("pytaj", "usun")
    if decyzja == "zakaz":
        raise BladShopify("ZABLOKOWANE: " + " ".join(powody))
    if zmiana and not zmiany:
        raise BladShopify("To zapytanie zmienia sklep. Uruchom je z flaga --allow-mutations dopiero po zgodzie uzytkownika.")
    if zmiana:
        brak = _wymagany_backup(tekst, usuwanie=(decyzja == "usun"))
        if brak:
            raise BladShopify("Brak dzisiejszego backupu dla: " + ", ".join(brak[:20]) + (" ..." if len(brak) > 20 else "") +
                              ". Najpierw: python scripts/backup_produktu.py --obiekt <gid...> (albo --id / --handle / --kolekcja / --metaobiekt).")

    with tempfile.TemporaryDirectory() as tmp:
        pz = os.path.join(tmp, "q.graphql")
        with open(pz, "w", encoding="utf-8") as f:
            f.write(zapytanie)
        cmd = _cli() + ["store", "execute", "-s", sklep(), "--no-input", "-j", "--query-file", pz]
        if zmienne:
            pv = os.path.join(tmp, "v.json")
            with open(pv, "w", encoding="utf-8") as f:
                json.dump(zmienne, f, ensure_ascii=False)
            cmd += ["--variable-file", pv]
        cmd += ["--version", wersja_api or wersja_api_domyslna()]
        if zmiana:
            cmd.append("--allow-mutations")
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "").strip()
    try:
        dane = json.loads(out) if out else {}
    except json.JSONDecodeError:
        dane = None
        for m in re.finditer(r"^\{", out, flags=re.M):
            try:
                dane = json.JSONDecoder().raw_decode(out[m.start():])[0]
                break
            except Exception:
                continue
    if p.returncode != 0 or dane is None or (isinstance(dane, dict) and "error" in dane and len(dane) == 1):
        opis = ""
        if isinstance(dane, dict) and "error" in dane:
            e = dane["error"]
            opis = e.get("message", "")
            szczegoly = (e.get("details") or {}).get("errors")
            if szczegoly:
                opis += " | " + "; ".join(x.get("message", "") for x in szczegoly)
            if e.get("nextSteps"):
                opis += " | Nastepny krok: " + " ".join(e["nextSteps"])
        else:
            opis = (p.stderr or out)[-1500:]
        if zmiana:
            _loguj_zmiane(nazwy, tekst, None, blad=opis)
        if "auth" in opis.lower() or "token" in opis.lower():
            opis += "\nWyglada na brak logowania do sklepu. Uzytkownik musi wpisac w Claude Code: ! shopify store auth ... (patrz INSTALACJA.md, krok 6)."
        raise BladShopify(opis or "Nieznany blad Shopify CLI")
    if zmiana:
        _loguj_zmiane(nazwy, tekst, dane)
    return dane


def _zejdz(d, sciezka):
    for k in sciezka.split("."):
        d = (d or {}).get(k)
    return d


def wszystkie_strony(zapytanie, sciezka, zmienne=None, maks_stron=200):
    """Pobiera wszystkie strony polaczenia (nodes) wskazanego sciezka, np. 'products' albo 'collection.products'."""
    zmienne = dict(zmienne or {})
    wezly = []
    for _ in range(maks_stron):
        dane = wykonaj(zapytanie, zmienne)
        polaczenie = _zejdz(dane, sciezka)
        if polaczenie is None:
            raise BladShopify(f"W odpowiedzi nie ma sciezki '{sciezka}'.")
        wezly.extend(polaczenie.get("nodes") or [e.get("node") for e in polaczenie.get("edges", [])])
        info = polaczenie.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            break
        zmienne["after"] = info.get("endCursor")
    return wezly


def main():
    ap = argparse.ArgumentParser(description="Admin API Shopify przez Shopify CLI, z zasadami bezpieczenstwa.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--query", "-q")
    g.add_argument("--query-file")
    v = ap.add_mutually_exclusive_group()
    v.add_argument("--variables", "-v")
    v.add_argument("--variable-file")
    ap.add_argument("--allow-mutations", action="store_true", help="pozwol na zmiane w sklepie (tylko po zgodzie uzytkownika)")
    ap.add_argument("--wszystkie", metavar="SCIEZKA", help="pobierz wszystkie strony polaczenia, np. products")
    ap.add_argument("--out", help="zapisz wynik do pliku JSON zamiast na ekran")
    ap.add_argument("--wersja-api")
    a = ap.parse_args()

    zapytanie = a.query
    if a.query_file:
        with open(a.query_file, encoding="utf-8") as f:
            zapytanie = f.read()
    zmienne = None
    if a.variables:
        zmienne = json.loads(a.variables)
    elif a.variable_file:
        with open(a.variable_file, encoding="utf-8") as f:
            zmienne = json.load(f)
    try:
        if a.wszystkie:
            wynik = wszystkie_strony(zapytanie, a.wszystkie, zmienne)
        else:
            wynik = wykonaj(zapytanie, zmienne, zmiany=a.allow_mutations, wersja_api=a.wersja_api)
    except BladShopify as e:
        sys.stderr.write(f"BLAD: {e}\n")
        sys.exit(2)
    tekst = json.dumps(wynik, ensure_ascii=False, indent=1)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(tekst)
        print(f"Zapisano: {a.out} ({len(wynik) if isinstance(wynik, list) else 'obiekt'})")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(tekst)
    bledy = _bledy_uzytkownika(wynik)
    if bledy:
        sys.stderr.write("UWAGA: Shopify odrzucil czesc zmiany (userErrors): " + json.dumps(bledy, ensure_ascii=False) + "\n")
        sys.exit(3)


if __name__ == "__main__":
    main()
