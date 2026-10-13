#!/usr/bin/env python3
"""Rozbieznosci BaseLinker <> Shopify. TYLKO ODCZYT w obu systemach.

Klucz BaseLinkera: BASELINKER_TOKEN w pliku .env (nigdy w komendzie, nigdy w czacie).
Wynik: raporty/RRRR-MM-DD/roznice-<tryb>-<godzina>.csv (otwiera sie w Excelu) + .html (podsumowanie).

  python scripts/base_shopify_roznice.py --lista                       katalogi, magazyny i grupy cen w Base
  python scripts/base_shopify_roznice.py --produkty                    SKU, stany, ceny (domyslny katalog Base)
  python scripts/base_shopify_roznice.py --produkty --katalog 123 --magazyn bl_456 --grupa-cen 789
  python scripts/base_shopify_roznice.py --zamowienia --dni 3          zamowienia z ostatnich 3 dni
"""
import argparse
import csv
import html
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopify_gql import BladShopify, wszystkie_strony  # noqa: E402
from wspolne import PROJEKT, dzis, godzina, wczytaj_env  # noqa: E402

BL_URL = "https://api.baselinker.com/connector.php"
# Wylacznie metody odczytu. Skrypt odmawia wywolania czegokolwiek spoza tej listy.
BL_ODCZYT = {
    "getInventories", "getInventoryWarehouses", "getInventoryPriceGroups", "getInventoryProductsList",
    "getInventoryProductsData", "getInventoryProductsStock", "getInventoryProductsPrices",
    "getOrders", "getOrderSources", "getOrderStatusList", "getExternalStoragesList",
}
TOLERANCJA_CENY = 0.01
TOLERANCJA_KWOTY_ZAMOWIENIA = 0.05


class BladBase(Exception):
    pass


def bl(metoda, parametry=None):
    if metoda not in BL_ODCZYT or not metoda.startswith("get"):
        raise BladBase(f"Metoda {metoda} nie jest na liscie odczytu. Ten skrypt niczego w Base nie zmienia.")
    token = wczytaj_env().get("BASELINKER_TOKEN")
    if not token:
        raise BladBase("Brak BASELINKER_TOKEN w pliku .env (patrz INSTALACJA.md, krok 7).")
    dane = urllib.parse.urlencode({"method": metoda, "parameters": json.dumps(parametry or {})}).encode()
    req = urllib.request.Request(BL_URL, data=dane, headers={"X-BLToken": token})
    for proba in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                odp = json.loads(r.read().decode("utf-8"))
            break
        except Exception as e:
            if proba == 2:
                raise BladBase(f"Polaczenie z Base: {e}")
            time.sleep(3)
    time.sleep(0.7)  # limit Base: 100 zapytan na minute
    if odp.get("status") != "SUCCESS":
        raise BladBase(f"{metoda}: {odp.get('error_code')} {odp.get('error_message')}")
    return odp


def norm(sku):
    return (sku or "").strip().upper()


def zapisz_raport(tryb, wiersze, kolumny, podsumowanie):
    katalog = os.path.join(PROJEKT, "raporty", dzis())
    os.makedirs(katalog, exist_ok=True)
    baza = os.path.join(katalog, f"roznice-{tryb}-{godzina()}")
    with open(baza + ".csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=kolumny, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(wiersze)
    grupy = {}
    for r in wiersze:
        grupy.setdefault(r["problem"], []).append(r)
    czesci = [f"<h1>Rozbieznosci Base i Shopify: {tryb}</h1><p>{html.escape(datetime.now().strftime('%Y-%m-%d %H:%M'))}</p><ul>"]
    for k, v in podsumowanie.items():
        czesci.append(f"<li>{html.escape(str(k))}: <b>{html.escape(str(v))}</b></li>")
    czesci.append("</ul>")
    for problem, lista in grupy.items():
        czesci.append(f"<h2>{html.escape(problem)} ({len(lista)})</h2><table><tr>" +
                      "".join(f"<th>{html.escape(c)}</th>" for c in kolumny) + "</tr>")
        for r in lista[:300]:
            czesci.append("<tr>" + "".join(f"<td>{html.escape(str(r.get(c, '')))}</td>" for c in kolumny) + "</tr>")
        czesci.append("</table>" + (f"<p>... i {len(lista) - 300} kolejnych (pelna lista w CSV)</p>" if len(lista) > 300 else ""))
    styl = ("<style>body{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#222}table{border-collapse:collapse;font-size:13px}"
            "td,th{border:1px solid #ccc;padding:4px 8px;text-align:left}th{background:#f2f2f2}h2{margin-top:32px}</style>")
    with open(baza + ".html", "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><html lang='pl'><meta charset='utf-8'><title>Rozbieznosci {tryb}</title>{styl}" + "".join(czesci) + "</html>")
    return os.path.relpath(baza + ".csv", PROJEKT), os.path.relpath(baza + ".html", PROJEKT)


def lista():
    odp = bl("getInventories")
    for inv in odp.get("inventories", []):
        print(f"Katalog {inv.get('inventory_id')}: {inv.get('name')}  (domyslny: {inv.get('is_default')})")
        print(f"  magazyny: {inv.get('warehouses')}  domyslny: {inv.get('default_warehouse')}")
        print(f"  grupy cen: {inv.get('price_groups')}  domyslna: {inv.get('default_price_group')}")
    try:
        mag = bl("getInventoryWarehouses").get("warehouses", [])
        print("Magazyny:", [(m.get("warehouse_type", "") + "_" + str(m.get("warehouse_id")), m.get("name")) for m in mag])
        gr = bl("getInventoryPriceGroups").get("price_groups", [])
        print("Grupy cen:", [(g.get("price_group_id"), g.get("name"), g.get("currency")) for g in gr])
    except BladBase as e:
        print("(nie udalo sie pobrac magazynow / grup cen:", e, ")")


def produkty(a):
    invs = bl("getInventories").get("inventories", [])
    if not invs:
        raise BladBase("Brak katalogow w Base (getInventories). Moze Base korzysta z magazynu sklepu, zapytaj Igora.")
    inv = next((i for i in invs if str(i.get("inventory_id")) == str(a.katalog)), None) if a.katalog else \
        next((i for i in invs if i.get("is_default")), invs[0])
    if not inv:
        raise BladBase(f"Nie ma katalogu {a.katalog}. Uruchom --lista.")
    magazyn = a.magazyn or inv.get("default_warehouse")
    grupa = str(a.grupa_cen or inv.get("default_price_group") or "")
    print(f"Base: katalog {inv['inventory_id']} ({inv.get('name')}), magazyn {magazyn or 'suma wszystkich'}, grupa cen {grupa or 'pierwsza'}")

    base = []
    strona = 1
    while True:
        odp = bl("getInventoryProductsList", {"inventory_id": inv["inventory_id"], "page": strona, "include_variants": True})
        prod = odp.get("products") or {}
        if not prod:
            break
        base.extend(prod.values())
        print(f"  Base: strona {strona}, razem {len(base)}")
        if len(prod) < 1000:
            break
        strona += 1

    print("Shopify: warianty ...")
    q = """query V($after: String) { productVariants(first: 250, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes { id sku barcode price inventoryQuantity product { handle title status } } } }"""
    shop = wszystkie_strony(q, "productVariants")
    print(f"  Shopify: {len(shop)} wariantow")

    def stan_base(p):
        st = p.get("stock") or {}
        if magazyn:
            return st.get(magazyn)
        return sum(v for v in st.values() if isinstance(v, (int, float))) if st else None

    def cena_base(p):
        ce = p.get("prices") or {}
        if grupa and grupa in ce:
            return ce[grupa]
        return next(iter(ce.values()), None) if ce else None

    idx_b, dup_b = {}, set()
    for p in base:
        k = norm(p.get("sku")) or ("EAN:" + p["ean"] if p.get("ean") else "")
        if not k:
            continue
        if k in idx_b:
            dup_b.add(k)
        idx_b[k] = p
    idx_s, dup_s = {}, set()
    for v in shop:
        k = norm(v.get("sku"))
        if not k:
            continue
        if k in idx_s:
            dup_s.add(k)
        idx_s[k] = v
    ean_s = {(v.get("barcode") or "").strip(): v for v in shop if (v.get("barcode") or "").strip()}

    wiersze = []

    def wiersz(problem, sku, b=None, s=None, uwagi=""):
        wiersze.append({
            "problem": problem, "sku": sku,
            "nazwa_base": (b or {}).get("name", ""), "nazwa_shopify": ((s or {}).get("product") or {}).get("title", ""),
            "uchwyt_shopify": ((s or {}).get("product") or {}).get("handle", ""),
            "status_shopify": ((s or {}).get("product") or {}).get("status", ""),
            "stan_base": stan_base(b) if b else "", "stan_shopify": (s or {}).get("inventoryQuantity", ""),
            "cena_base": cena_base(b) if b else "", "cena_shopify": (s or {}).get("price", ""),
            "ean_base": (b or {}).get("ean", ""), "ean_shopify": (s or {}).get("barcode", ""), "uwagi": uwagi})

    for k in sorted(dup_b):
        wiersz("Duplikat SKU w Base", k, b=idx_b[k])
    for k in sorted(dup_s):
        wiersz("Duplikat SKU w Shopify", k, s=idx_s[k])
    for v in shop:
        if not norm(v.get("sku")) and (v.get("product") or {}).get("status") == "ACTIVE":
            wiersz("Brak SKU w Shopify (aktywny produkt)", "", s=v)
    for k, b in idx_b.items():
        s = idx_s.get(k)
        if not s and b.get("ean"):
            s = ean_s.get(str(b["ean"]).strip())
            if s:
                wiersz("SKU rozne, ten sam EAN", k, b=b, s=s, uwagi=f"SKU w Shopify: {s.get('sku')}")
                continue
        if not s:
            wiersz("Jest w Base, brak w Shopify", k, b=b)
            continue
        sb, ss = stan_base(b), s.get("inventoryQuantity")
        if sb is not None and ss is not None and int(sb) != int(ss):
            wiersz("Rozny stan", k, b=b, s=s, uwagi=f"roznica {int(ss) - int(sb):+d} (Shopify minus Base)")
        cb, cs = cena_base(b), s.get("price")
        if cb not in (None, "") and cs not in (None, "") and abs(float(cb) - float(cs)) > TOLERANCJA_CENY:
            wiersz("Rozna cena", k, b=b, s=s, uwagi=f"roznica {float(cs) - float(cb):+.2f} zl")
    ean_b = {str(b.get("ean") or "").strip() for b in base if b.get("ean")}
    for k, s in idx_s.items():
        if k in idx_b or (s.get("barcode") or "").strip() in ean_b:
            continue
        if (s.get("product") or {}).get("status") == "ACTIVE":
            wiersz("Jest w Shopify (aktywny), brak w Base", k, s=s)

    podsum = {"produkty w Base": len(base), "warianty w Shopify": len(shop)}
    for r in wiersze:
        podsum[r["problem"]] = podsum.get(r["problem"], 0) + 1
    kol = ["problem", "sku", "nazwa_base", "nazwa_shopify", "uchwyt_shopify", "status_shopify", "stan_base", "stan_shopify",
           "cena_base", "cena_shopify", "ean_base", "ean_shopify", "uwagi"]
    return zapisz_raport("produkty", wiersze, kol, podsum), podsum


def zamowienia(a):
    teraz = datetime.now(timezone.utc)
    od = teraz - timedelta(days=a.dni)
    print(f"Shopify: zamowienia od {od.astimezone().strftime('%Y-%m-%d %H:%M')} ...")
    q = """query O($after: String, $q: String) { orders(first: 100, after: $after, query: $q, sortKey: CREATED_AT) {
      pageInfo { hasNextPage endCursor }
      nodes { id legacyResourceId name createdAt cancelledAt test displayFinancialStatus
              currentTotalPriceSet { shopMoney { amount } } } } }"""
    shop = wszystkie_strony(q, "orders", {"q": f"created_at:>='{od.strftime('%Y-%m-%dT%H:%M:%SZ')}'"})
    print(f"  Shopify: {len(shop)}")

    base = []
    param = {"date_from": int(od.timestamp()), "get_unconfirmed_orders": True}
    while True:
        lista_b = bl("getOrders", param).get("orders") or []
        base.extend(o for o in lista_b if int(o.get("date_add") or 0) >= int(od.timestamp()))
        print(f"  Base: razem {len(base)}")
        if len(lista_b) < 100:
            break
        param = {"date_from": int(od.timestamp()), "get_unconfirmed_orders": True,
                 "id_from": max(int(o["order_id"]) for o in lista_b) + 1}

    idx = {}
    for o in shop:
        for k in (str(o["legacyResourceId"]), o["name"], o["name"].lstrip("#")):
            idx[k] = o
    dopasowane = set()
    wiersze = []

    def suma_base(o):
        return sum(float(p.get("price_brutto") or 0) * float(p.get("quantity") or 0) for p in o.get("products") or []) + float(o.get("delivery_price") or 0)

    for o in base:
        klucze = [str(o.get("external_order_id") or ""), str(o.get("shop_order_id") or "")]
        s = next((idx[k] for k in klucze if k and k in idx), None)
        wiersz = {"problem": "", "zamowienie_shopify": s["name"] if s else "", "id_base": o.get("order_id"),
                  "zrodlo_base": f"{o.get('order_source')} {o.get('order_source_id')}",
                  "data_base": datetime.fromtimestamp(int(o.get("date_add") or 0)).strftime("%Y-%m-%d %H:%M"),
                  "kwota_base": round(suma_base(o), 2), "kwota_shopify": "", "status_platnosci_shopify": "", "uwagi": ""}
        if not s:
            if str(o.get("order_source")) in ("shop", "shopify", ""):
                wiersz["problem"] = "Jest w Base (ze sklepu), brak w Shopify"
                wiersze.append(wiersz)
            continue
        dopasowane.add(s["id"])
        ks = float(s["currentTotalPriceSet"]["shopMoney"]["amount"])
        wiersz["kwota_shopify"] = ks
        wiersz["status_platnosci_shopify"] = s["displayFinancialStatus"]
        if abs(ks - suma_base(o)) > TOLERANCJA_KWOTY_ZAMOWIENIA:
            wiersz["problem"] = "Rozna kwota"
            wiersz["uwagi"] = f"roznica {ks - suma_base(o):+.2f} zl (Shopify minus Base; zwroty i rabaty tez to zmieniaja)"
            wiersze.append(wiersz)
    granica = teraz - timedelta(minutes=30)
    for s in shop:
        if s["id"] in dopasowane or s["cancelledAt"] or s["test"]:
            continue
        utw = datetime.fromisoformat(s["createdAt"].replace("Z", "+00:00"))
        if utw > granica:
            continue  # Base pobiera zamowienia co kilka minut, swiezych nie liczymy
        wiersze.append({"problem": "Jest w Shopify, brak w Base", "zamowienie_shopify": s["name"],
                        "data_base": "", "kwota_shopify": s["currentTotalPriceSet"]["shopMoney"]["amount"],
                        "status_platnosci_shopify": s["displayFinancialStatus"],
                        "uwagi": "utworzone " + utw.astimezone().strftime("%Y-%m-%d %H:%M")})
    podsum = {"zamowienia w Shopify": len(shop), "zamowienia w Base": len(base), "dopasowane": len(dopasowane)}
    for r in wiersze:
        podsum[r["problem"]] = podsum.get(r["problem"], 0) + 1
    kol = ["problem", "zamowienie_shopify", "id_base", "zrodlo_base", "data_base", "kwota_base", "kwota_shopify",
           "status_platnosci_shopify", "uwagi"]
    return zapisz_raport("zamowienia", wiersze, kol, podsum), podsum


def main():
    ap = argparse.ArgumentParser(description="Rozbieznosci BaseLinker <> Shopify (tylko odczyt).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--lista", action="store_true")
    g.add_argument("--produkty", action="store_true")
    g.add_argument("--zamowienia", action="store_true")
    ap.add_argument("--katalog")
    ap.add_argument("--magazyn", help="np. bl_12345; bez tego: suma wszystkich magazynow katalogu")
    ap.add_argument("--grupa-cen")
    ap.add_argument("--dni", type=int, default=3)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        if a.lista:
            lista()
            return
        (csv_p, html_p), podsum = produkty(a) if a.produkty else zamowienia(a)
    except (BladBase, BladShopify) as e:
        print("BLAD:", e, file=sys.stderr)
        sys.exit(2)
    print("\nPodsumowanie:")
    for k, v in podsum.items():
        print(f"  {k}: {v}")
    print(f"\nRaport: {csv_p}\n        {html_p}")


if __name__ == "__main__":
    main()
