#!/usr/bin/env python3
"""Ocechowanie produktow (metapola) przez arkusz CSV, ktory mozna otworzyc w Excelu.

1) EKSPORT (tylko odczyt): produkty z kolekcji / z tagiem + wybrane metapola -> CSV (srednik, UTF-8)
   python scripts/cechy.py eksport --kolekcja garnki --pola custom.powloka custom.indukcja custom.zmywarka
   python scripts/cechy.py eksport --szukaj "tag:PATELNIE status:active" --pola custom.powloka --out robocze/cechy-patelnie.csv

2) IMPORT: porownanie arkusza ze sklepem i podglad roznic (nic nie zmienia)
   python scripts/cechy.py import robocze/cechy-garnki.csv
   ...a po zgodzie uzytkownika zapis (sam robi backup):
   python scripts/cechy.py import robocze/cechy-garnki.csv --allow-mutations

Zasady arkusza:
  - kolumny id, handle, title, status zostaw bez zmian; zmieniasz tylko kolumny metapol,
  - PUSTA komorka = bez zmian (czyszczenia wartosci nie robimy tym skryptem, to robi Igor),
  - listy wartosci rozdzielaj znakiem |  (np. "Gazowa | Indukcja | Elektryczna"),
  - tak/nie dla pol typu boolean: Tak / Nie,
  - liczby z przecinkiem albo kropka (3,6 albo 3.6).
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backup_produktu import zapisz as zapisz_backup  # noqa: E402
from shopify_gql import BladShopify, wszystkie_strony, wykonaj  # noqa: E402
from wspolne import PROJEKT, bezpieczna_nazwa, dzis, godzina  # noqa: E402

MAKS_PRODUKTOW_NA_IMPORT = 150
PARTIA = 25  # metafieldsSet przyjmuje maks. 25 metapol w jednym wywolaniu

M_SET = """mutation MS($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { key namespace value ownerType }
    userErrors { field message code elementIndex }
  }
}"""

Q_DEF = """query DF($owner: MetafieldOwnerType!) {
  metafieldDefinitions(ownerType: $owner, first: 250) {
    nodes { namespace key name type { name } validations { name value } }
  }
}"""


def definicje():
    d = wykonaj(Q_DEF, {"owner": "PRODUCT"})["metafieldDefinitions"]["nodes"]
    return {f"{x['namespace']}.{x['key']}": x for x in d}


def pola_zapytania(pola):
    czesci = []
    for i, p in enumerate(pola):
        ns, key = p.split(".", 1)
        czesci.append(f'f{i}: metafield(namespace: "{ns}", key: "{key}") {{ value type }}')
    return "\n".join(czesci)


def produkty(kolekcja, szukaj, pola):
    pz = pola_zapytania(pola)
    if kolekcja:
        q = """query P($h: String!, $after: String) { collectionByIdentifier(identifier: { handle: $h }) {
          products(first: 100, after: $after) { pageInfo { hasNextPage endCursor }
            nodes { id handle title status %s } } } }""" % pz
        return wszystkie_strony(q, "collectionByIdentifier.products", {"h": kolekcja})
    q = """query P($q: String, $after: String) { products(first: 100, after: $after, query: $q) {
      pageInfo { hasNextPage endCursor } nodes { id handle title status %s } } }""" % pz
    return wszystkie_strony(q, "products", {"q": szukaj})


def produkty_po_id(ids, pola):
    pz = pola_zapytania(pola)
    q = "query N($ids: [ID!]!) { nodes(ids: $ids) { ... on Product { id handle title status %s } } }" % pz
    wynik = []
    for i in range(0, len(ids), 50):
        wynik += [n for n in wykonaj(q, {"ids": ids[i:i + 50]})["nodes"] if n]
    return wynik


def na_arkusz(wartosc, typ):
    if wartosc is None:
        return ""
    if typ and typ.startswith("list."):
        try:
            return " | ".join(str(x) for x in json.loads(wartosc))
        except Exception:
            return wartosc
    if typ == "boolean":
        return "Tak" if wartosc == "true" else "Nie"
    return wartosc


def z_arkusza(tekst, definicja):
    """Zamienia komorke arkusza na wartosc metapola. Rzuca ValueError z opisem po polsku."""
    typ = definicja["type"]["name"]
    t = tekst.strip()
    if typ in ("single_line_text_field", "multi_line_text_field"):
        wynik = t
    elif typ == "number_integer":
        wynik = str(int(t.replace(" ", "")))
    elif typ == "number_decimal":
        wynik = str(float(t.replace(" ", "").replace(",", ".")))
    elif typ == "boolean":
        m = {"tak": "true", "nie": "false", "true": "true", "false": "false"}
        if t.lower() not in m:
            raise ValueError("wpisz Tak albo Nie")
        wynik = m[t.lower()]
    elif typ == "list.single_line_text_field":
        wynik = json.dumps([x.strip() for x in t.split("|") if x.strip()], ensure_ascii=False)
    else:
        raise ValueError(f"typ {typ} nie jest obslugiwany przez arkusz (np. odwolania do metaobiektow). Zapytaj Igora.")
    for v in definicja.get("validations") or []:
        if v["name"] == "choices":
            dozwolone = json.loads(v["value"])
            kandydaci = json.loads(wynik) if typ.startswith("list.") else [wynik]
            zle = [k for k in kandydaci if k not in dozwolone]
            if zle:
                raise ValueError(f"wartosci {zle} spoza listy dozwolonych: {dozwolone}")
    return wynik


def eksport(a):
    defs = definicje()
    brak = [p for p in a.pola if p not in defs]
    if brak:
        sys.exit(f"BLAD: nie ma definicji metapol: {brak}. Sprawdz docs/struktura-sklepu.md.")
    lista = produkty(a.kolekcja, a.szukaj, a.pola)
    nazwa = a.out or os.path.join("robocze", f"cechy-{bezpieczna_nazwa(a.kolekcja or a.szukaj)}-{dzis()}.csv")
    os.makedirs(os.path.dirname(os.path.abspath(nazwa)), exist_ok=True)
    with open(nazwa, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["id", "handle", "title", "status"] + a.pola)
        for p in lista:
            w.writerow([p["id"], p["handle"], p["title"], p["status"]] +
                       [na_arkusz((p.get(f"f{i}") or {}).get("value"), defs[pole]["type"]["name"]) for i, pole in enumerate(a.pola)])
    print(f"Zapisano {nazwa}: {len(lista)} produktow, pola: {', '.join(a.pola)}")
    for pole in a.pola:
        i = a.pola.index(pole)
        pelne = sum(1 for p in lista if (p.get(f"f{i}") or {}).get("value"))
        print(f"  {pole} ({defs[pole]['name']}, {defs[pole]['type']['name']}): wypelnione {pelne}/{len(lista)}")


def import_(a):
    with open(a.plik, encoding="utf-8-sig", newline="") as f:
        probka = f.read(4096)
        f.seek(0)
        sep = ";" if probka.count(";") >= probka.count(",") else ","
        wiersze = list(csv.DictReader(f, delimiter=sep))
    if not wiersze:
        sys.exit("BLAD: arkusz jest pusty.")
    pola = [k for k in wiersze[0].keys() if k and "." in k]
    defs = definicje()
    brak = [p for p in pola if p not in defs]
    if brak:
        sys.exit(f"BLAD: nie ma definicji metapol: {brak}")
    ids = [w["id"].strip() for w in wiersze if w.get("id", "").strip().startswith("gid://shopify/Product/")]
    obecne = {p["id"]: p for p in produkty_po_id(ids, pola)}

    zmiany, bledy, przed = [], [], {}
    for nr, w in enumerate(wiersze, start=2):
        pid = (w.get("id") or "").strip()
        if pid not in obecne:
            bledy.append(f"wiersz {nr}: nie znaleziono produktu {pid or '(brak id)'}")
            continue
        for i, pole in enumerate(pola):
            komorka = (w.get(pole) or "").strip()
            if not komorka:
                continue
            try:
                nowa = z_arkusza(komorka, defs[pole])
            except ValueError as e:
                bledy.append(f"wiersz {nr} ({w.get('handle')}), {pole}: {e}")
                continue
            stara = (obecne[pid].get(f"f{i}") or {}).get("value")
            if stara == nowa:
                continue
            ns, key = pole.split(".", 1)
            zmiany.append({"ownerId": pid, "namespace": ns, "key": key, "type": defs[pole]["type"]["name"], "value": nowa,
                           "_handle": obecne[pid]["handle"], "_stara": stara})
            przed.setdefault(pid, {"id": pid, "handle": obecne[pid]["handle"], "przed": {}})["przed"][pole] = stara

    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Arkusz: {len(wiersze)} wierszy, pola: {', '.join(pola)}")
    print(f"Zmian do zapisania: {len(zmiany)} (produktow: {len(przed)}), bledow w arkuszu: {len(bledy)}")
    for b in bledy[:40]:
        print("  BLAD", b)
    for z in zmiany[:60]:
        print(f"  {z['_handle']}: {z['namespace']}.{z['key']}: {z['_stara']!r} -> {z['value']!r}")
    if len(zmiany) > 60:
        print(f"  ... i {len(zmiany) - 60} kolejnych")
    if len(przed) > MAKS_PRODUKTOW_NA_IMPORT:
        sys.exit(f"STOP: {len(przed)} produktow w jednym imporcie. Limit to {MAKS_PRODUKTOW_NA_IMPORT}, podziel arkusz.")
    if bledy and a.allow_mutations:
        sys.exit("STOP: popraw bledy w arkuszu, zanim cokolwiek zapiszemy.")
    if not zmiany:
        print("Nic do zmiany.")
        return
    if not a.allow_mutations:
        print("\nTRYB PODGLADU: nic nie zostalo zapisane. Po zgodzie uzytkownika uruchom to samo z --allow-mutations.")
        return

    print("Backup:", zapisz_backup("cechy", os.path.splitext(os.path.basename(a.plik))[0], list(przed.values()), f"przed importem {a.plik}"))
    zapisane = 0
    for i in range(0, len(zmiany), PARTIA):
        partia = [{k: v for k, v in z.items() if not k.startswith("_")} for z in zmiany[i:i + PARTIA]]
        wynik = wykonaj(M_SET, {"metafields": partia}, zmiany=True)["metafieldsSet"]
        if wynik["userErrors"]:
            print("BLAD w partii (cala partia odrzucona, Shopify zapisuje partie atomowo):", wynik["userErrors"])
            print(f"Zapisano wczesniej: {zapisane}. Zatrzymuje sie.")
            sys.exit(3)
        zapisane += len(partia)
        print(f"  zapisano {zapisane}/{len(zmiany)}")

    po = {p["id"]: p for p in produkty_po_id(list(przed.keys()), pola)}
    niezgodne = []
    for z in zmiany:
        i = pola.index(f"{z['namespace']}.{z['key']}")
        if (po.get(z["ownerId"], {}).get(f"f{i}") or {}).get("value") != z["value"]:
            niezgodne.append(z["_handle"])
    raport = os.path.join(PROJEKT, "raporty", dzis(), f"import-cech-{godzina()}.json")
    os.makedirs(os.path.dirname(raport), exist_ok=True)
    with open(raport, "w", encoding="utf-8") as f:
        json.dump({"plik": a.plik, "zapisane": zapisane, "niezgodne_po_odczycie": niezgodne,
                   "zmiany": [{k: v for k, v in z.items()} for z in zmiany]}, f, ensure_ascii=False, indent=1)
    print(f"Weryfikacja odczytem: zgodne {len(zmiany) - len(niezgodne)}/{len(zmiany)}. Raport: {os.path.relpath(raport, PROJEKT)}")
    if niezgodne:
        sys.exit(f"UWAGA: niezgodne po zapisie: {sorted(set(niezgodne))[:20]}")


def main():
    ap = argparse.ArgumentParser(description="Ocechowanie przez arkusz CSV.")
    sub = ap.add_subparsers(dest="tryb", required=True)
    e = sub.add_parser("eksport")
    g = e.add_mutually_exclusive_group(required=True)
    g.add_argument("--kolekcja")
    g.add_argument("--szukaj", help='zapytanie wyszukiwania produktow, np. "tag:GARNKI status:active"')
    e.add_argument("--pola", nargs="+", required=True, help="np. custom.powloka custom.indukcja")
    e.add_argument("--out")
    i = sub.add_parser("import")
    i.add_argument("plik")
    i.add_argument("--allow-mutations", action="store_true")
    a = ap.parse_args()
    try:
        eksport(a) if a.tryb == "eksport" else import_(a)
    except BladShopify as ex:
        print("BLAD:", ex, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
