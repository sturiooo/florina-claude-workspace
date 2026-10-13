#!/usr/bin/env python3
"""Rozpoznanie struktury sklepu (TYLKO ODCZYT). Uruchom na pierwszej sesji i zawsze, gdy Igor zmieni metapola.

Zapisuje:
  docs/struktura-sklepu.md   opis dla czlowieka i dla Claude (definicje metapol, metaobiekty, FAQ, kolekcje, tagi)
  docs/struktura-sklepu.json pelne dane

  python scripts/struktura_sklepu.py
  python scripts/struktura_sklepu.py --kolekcja-wzorcowa garnki
"""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopify_gql import BladShopify, wszystkie_strony, wykonaj  # noqa: E402
from wspolne import PROJEKT, dzis, sklep, zapisz_json  # noqa: E402

Q_DEF = """query D($owner: MetafieldOwnerType!, $after: String) {
  metafieldDefinitions(ownerType: $owner, first: 100, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes {
      namespace key name description
      type { name }
      validations { name value }
      metafieldsCount
      capabilities { adminFilterable { enabled } smartCollectionCondition { enabled } }
    }
  }
}"""

Q_MO_DEF = """query MD($after: String) {
  metaobjectDefinitions(first: 50, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id type name metaobjectsCount
      capabilities { translatable { enabled } publishable { enabled } }
      fieldDefinitions { key name required type { name } validations { name value } }
    }
  }
}"""

Q_MO_PROBKA = """query MP($t: String!) {
  metaobjects(type: $t, first: 5) { nodes { id handle displayName fields { key type value } } }
}"""

Q_KOLEKCJE = """query K($after: String) {
  collections(first: 100, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes { id handle title productsCount { count } ruleSet { appliedDisjunctively rules { column relation condition } } }
  }
}"""

Q_KOLEKCJA_WZOR = """query KW($h: String!) {
  collectionByIdentifier(identifier: { handle: $h }) {
    id handle title
    descriptionHtml
    metafields(first: 50) { nodes { namespace key type value } }
    products(first: 1) { nodes { id handle title tags metafields(first: 80) { nodes { namespace key type value } } } }
  }
}"""

Q_TAGI = "{ productTags(first: 250) { nodes } }"


def main():
    ap = argparse.ArgumentParser(description="Rozpoznanie struktury sklepu (tylko odczyt).")
    ap.add_argument("--kolekcja-wzorcowa", default="garnki", help="kolekcja do podgladu metapol (domyslnie garnki)")
    a = ap.parse_args()

    dane = {"sklep": sklep(), "data": dzis(), "metapola": {}, "metaobiekty": [], "probki_metaobiektow": {}}
    for owner in ("PRODUCT", "COLLECTION", "PRODUCTVARIANT"):
        print(f"Definicje metapol: {owner} ...")
        dane["metapola"][owner] = wszystkie_strony(Q_DEF, "metafieldDefinitions", {"owner": owner})
    print("Definicje metaobiektow ...")
    dane["metaobiekty"] = wszystkie_strony(Q_MO_DEF, "metaobjectDefinitions")
    for d in dane["metaobiekty"]:
        t = d["type"]
        if any(s in (t + " " + d["name"]).lower() for s in ("faq", "pyt", "question", "accordion", "collapsible", "spec")):
            try:
                dane["probki_metaobiektow"][t] = wykonaj(Q_MO_PROBKA, {"t": t})["metaobjects"]["nodes"]
            except BladShopify as e:
                dane["probki_metaobiektow"][t] = [{"blad": str(e)}]
    print("Kolekcje ...")
    dane["kolekcje"] = wszystkie_strony(Q_KOLEKCJE, "collections")
    print(f"Kolekcja wzorcowa: {a.kolekcja_wzorcowa} ...")
    try:
        dane["kolekcja_wzorcowa"] = wykonaj(Q_KOLEKCJA_WZOR, {"h": a.kolekcja_wzorcowa}).get("collectionByIdentifier")
    except BladShopify as e:
        dane["kolekcja_wzorcowa"] = {"blad": str(e)}
    try:
        dane["tagi"] = wykonaj(Q_TAGI)["productTags"]["nodes"]
    except BladShopify as e:
        dane["tagi"] = [f"(nie udalo sie pobrac: {e})"]

    zapisz_json(os.path.join(PROJEKT, "docs", "struktura-sklepu.json"), dane)
    md = opis_md(dane)
    with open(os.path.join(PROJEKT, "docs", "struktura-sklepu.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print("Zapisano docs/struktura-sklepu.md i docs/struktura-sklepu.json")


def _walidacje(v):
    out = []
    for x in v or []:
        val = x["value"]
        if len(val) > 120:
            val = val[:117] + "..."
        out.append(f"{x['name']}={val}")
    return "; ".join(out)


def opis_md(d):
    L = [f"# Struktura sklepu {d['sklep']} (odczyt {d['data']})", "",
         "Wygenerowane przez `scripts/struktura_sklepu.py`. Nie edytuj recznie, uruchom skrypt ponownie.", ""]
    nazwy = {"PRODUCT": "produktu", "COLLECTION": "kolekcji", "PRODUCTVARIANT": "wariantu"}
    for owner, lista in d["metapola"].items():
        L += [f"## Metapola {nazwy[owner]} ({len(lista)})", "",
              "| Klucz | Nazwa w panelu | Typ | Wypelnione | Filtr w panelu | Walidacje |", "|---|---|---|---|---|---|"]
        for m in sorted(lista, key=lambda x: -(x.get("metafieldsCount") or 0)):
            filtr = "tak" if ((m.get("capabilities") or {}).get("adminFilterable") or {}).get("enabled") else ""
            L.append(f"| `{m['namespace']}.{m['key']}` | {m['name']} | {m['type']['name']} | {m.get('metafieldsCount', '')} | {filtr} | {_walidacje(m.get('validations'))} |")
        L.append("")
    L += [f"## Metaobiekty ({len(d['metaobiekty'])})", ""]
    for mo in d["metaobiekty"]:
        L.append(f"### `{mo['type']}`: {mo['name']} ({mo.get('metaobjectsCount', '?')} wpisow)")
        for f in mo["fieldDefinitions"]:
            L.append(f"- `{f['key']}` ({f['type']['name']}){' wymagane' if f.get('required') else ''}: {f['name']}")
        L.append("")
    if d["probki_metaobiektow"]:
        L += ["## Probki metaobiektow (FAQ, specyfikacje, zakladki)", ""]
        for t, wpisy in d["probki_metaobiektow"].items():
            L.append(f"### `{t}`")
            for w in wpisy[:3]:
                if "blad" in w:
                    L.append(f"- blad: {w['blad']}")
                    continue
                pola = ", ".join(f"{p['key']}={str(p['value'])[:60]!r}" for p in w["fields"])
                L.append(f"- `{w['handle']}`: {pola}")
            L.append("")
    kw = d.get("kolekcja_wzorcowa") or {}
    if kw and "blad" not in kw:
        L += [f"## Kolekcja wzorcowa `{kw['handle']}`", "", "Metapola kolekcji:"]
        for m in kw["metafields"]["nodes"]:
            L.append(f"- `{m['namespace']}.{m['key']}` ({m['type']}): {str(m['value'])[:100]}")
        prod = (kw.get("products") or {}).get("nodes") or []
        if prod:
            p = prod[0]
            L += ["", f"Przykladowy produkt `{p['handle']}`, tagi: {', '.join(p['tags'])}", "", "Metapola produktu:"]
            for m in p["metafields"]["nodes"]:
                L.append(f"- `{m['namespace']}.{m['key']}` ({m['type']}): {str(m['value'])[:100]}")
        L.append("")
    kol = d.get("kolekcje") or []
    auto = [k for k in kol if k.get("ruleSet")]
    L += [f"## Kolekcje ({len(kol)}: automatyczne {len(auto)}, reczne {len(kol) - len(auto)})", "",
          "| Uchwyt | Tytul | Produkty | Rodzaj | Reguly |", "|---|---|---|---|---|"]
    for k in sorted(kol, key=lambda x: -((x.get("productsCount") or {}).get("count") or 0)):
        rs = k.get("ruleSet")
        reg = ""
        if rs:
            reg = (" LUB " if rs["appliedDisjunctively"] else " I ").join(f"{r['column']} {r['relation']} {r['condition']}" for r in rs["rules"])
        L.append(f"| `{k['handle']}` | {k['title']} | {(k.get('productsCount') or {}).get('count', '')} | {'automatyczna' if rs else 'reczna'} | {reg[:140]} |")
    L.append("")
    tagi = d.get("tagi") or []
    L += [f"## Tagi produktow (pierwsze {len(tagi)})", "", ", ".join(f"`{t}`" for t in tagi), ""]
    return "\n".join(L)


if __name__ == "__main__":
    try:
        main()
    except BladShopify as e:
        print("BLAD:", e, file=sys.stderr)
        sys.exit(2)
