#!/usr/bin/env python3
"""Przygotowanie zmiany w szablonie (motywie): pobranie aktualnych plikow motywu. TYLKO ODCZYT.

Claude moze uruchamiac ten skrypt sam. Samo wgranie zmiany robi czlowiek (scripts/szablon_wgraj.py przez `!`).

  python scripts/szablon_pobierz.py --motyw live --pliki sections/main-collection.liquid templates/collection.json --zmiana baner-garnki
  python scripts/szablon_pobierz.py --lista                      (motywy w sklepie: id, nazwa, rola)

Tworzy katalog robocze/szablon/RRRR-MM-DD-<zmiana>/:
  oryginal/<sciezka>   stan pliku w chwili pobrania (nie edytowac)
  pliki/<sciezka>      kopia do edycji: TU Claude wprowadza zmiane
  _baza.json           motyw, sumy kontrolne plikow (szablon_wgraj.py sprawdzi, czy nikt ich w miedzyczasie nie zmienil)
  OPIS.md              Claude opisuje: co zmienia, dlaczego, jak sprawdzic, jak cofnac
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopify_gql import BladShopify, wykonaj  # noqa: E402
from wspolne import PROJEKT, bezpieczna_nazwa, dzis, zapisz_json  # noqa: E402

Q_MOTYWY = "{ themes(first: 30) { nodes { id name role updatedAt } } }"
Q_PLIKI = """query T($id: ID!, $names: [String!]) { theme(id: $id) { id name role
  files(filenames: $names, first: 50) { nodes { filename checksumMd5 size updatedAt
    body { ... on OnlineStoreThemeFileBodyText { content } ... on OnlineStoreThemeFileBodyBase64 { contentBase64 } } } } } }"""


def znajdz_motyw(motyw):
    motywy = wykonaj(Q_MOTYWY)["themes"]["nodes"]
    if motyw in ("live", "main"):
        m = next((t for t in motywy if t["role"] == "MAIN"), None)
    else:
        g = motyw if motyw.startswith("gid://") else f"gid://shopify/OnlineStoreTheme/{motyw}"
        m = next((t for t in motywy if t["id"] == g), None)
    if not m:
        raise BladShopify(f"Nie znaleziono motywu {motyw}. Uruchom --lista.")
    return m


def pobierz_pliki(theme_id, nazwy):
    d = wykonaj(Q_PLIKI, {"id": theme_id, "names": nazwy})["theme"]
    return {n["filename"]: n for n in d["files"]["nodes"]}


def md5(tekst):
    return hashlib.md5(tekst.encode("utf-8")).hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Pobranie plikow motywu do przygotowania zmiany (tylko odczyt).")
    ap.add_argument("--lista", action="store_true")
    ap.add_argument("--motyw", default="live", help="live albo id motywu")
    ap.add_argument("--pliki", nargs="*", default=[], help="sciezki w motywie, np. sections/header.liquid")
    ap.add_argument("--zmiana", help="krotka nazwa zmiany, np. baner-garnki")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        if a.lista:
            for t in wykonaj(Q_MOTYWY)["themes"]["nodes"]:
                print(f"{t['id'].split('/')[-1]:>14}  {t['role']:<12} {t['name']}  (zmieniony {t['updatedAt']})")
            return
        if not a.pliki or not a.zmiana:
            ap.error("podaj --pliki i --zmiana")
        m = znajdz_motyw(a.motyw)
        pliki = pobierz_pliki(m["id"], a.pliki)
    except BladShopify as e:
        sys.exit(f"BLAD: {e}")

    katalog = os.path.join(PROJEKT, "robocze", "szablon", f"{dzis()}-{bezpieczna_nazwa(a.zmiana)}")
    baza = {"motyw": m, "pobrano": dzis(), "pliki": {}}
    for nazwa in a.pliki:
        p = pliki.get(nazwa)
        if p is None:
            baza["pliki"][nazwa] = {"istnial": False}
            print(f"  {nazwa}: nie istnieje w motywie (zmiana go utworzy)")
            continue
        body = p.get("body") or {}
        if "content" not in body:
            sys.exit(f"BLAD: {nazwa} jest plikiem binarnym. Tym narzedziem zmieniamy tylko pliki tekstowe.")
        for pod in ("oryginal", "pliki"):
            sciezka = os.path.join(katalog, pod, *nazwa.split("/"))
            os.makedirs(os.path.dirname(sciezka), exist_ok=True)
            with open(sciezka, "w", encoding="utf-8", newline="") as f:
                f.write(body["content"])
        baza["pliki"][nazwa] = {"istnial": True, "md5": md5(body["content"]), "checksumMd5": p.get("checksumMd5"), "updatedAt": p.get("updatedAt")}
        print(f"  {nazwa}: pobrano ({p.get('size')} B, zmieniony {p.get('updatedAt')})")
    zapisz_json(os.path.join(katalog, "_baza.json"), baza)
    opis = os.path.join(katalog, "OPIS.md")
    if not os.path.exists(opis):
        with open(opis, "w", encoding="utf-8") as f:
            f.write(f"# Zmiana w szablonie: {a.zmiana}\n\nMotyw: {m['name']} ({m['role']}, {m['id']})\n\n"
                    "## Co zmienia\n\n## Dlaczego\n\n## Jak sprawdzic po wgraniu\n\n## Jak cofnac\n")
    print(f"\nMotyw: {m['name']} ({m['role']})\nKatalog zmiany: {os.path.relpath(katalog, PROJEKT)}")
    print("Edytuj pliki w podkatalogu pliki/. Wgranie robi czlowiek: scripts/szablon_wgraj.py (skill zmiany-w-szablonie).")


if __name__ == "__main__":
    main()
