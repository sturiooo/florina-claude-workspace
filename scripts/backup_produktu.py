#!/usr/bin/env python3
"""Backup stanu przed zmiana: produkty, kolekcje, wpisy metaobiektow (FAQ). TYLKO ODCZYT ze sklepu.

Zapis do backup/RRRR-MM-DD/<typ>-<uchwyt>-<godzina>.json. Bez dzisiejszego backupu
scripts/shopify_gql.py nie pozwoli zmienic danego obiektu.

Przyklady:
  python scripts/backup_produktu.py --handle patelnia-x garnek-y --powod "nowe opisy"
  python scripts/backup_produktu.py --id 1234567890 gid://shopify/Product/987
  python scripts/backup_produktu.py --plik robocze/lista-produktow.txt      (uchwyty albo id, jeden w linii)
  python scripts/backup_produktu.py --kolekcja garnki
  python scripts/backup_produktu.py --metaobiekt gid://shopify/Metaobject/123
  python scripts/backup_produktu.py --kolekcja-z-produktami garnki          (kolekcja + wszystkie jej produkty, 1 plik)
  python scripts/backup_produktu.py --obiekt gid://shopify/Customer/123 gid://shopify/DiscountCodeNode/456  (dowolny obiekt)

Jak odtworzyc: plik zawiera pelny stan (opis HTML, tagi, SEO, metapola, media, kolekcje).
Przywracanie robi Claude z tego pliku, ta sama droga co zmiana (productUpdate / metafieldsSet),
po zgodzie uzytkownika. Usunietych mediow z backupu sie nie odtworzy (sa tylko adresy URL).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopify_gql import BladShopify, wszystkie_strony, wykonaj  # noqa: E402
from wspolne import PROJEKT, bezpieczna_nazwa, dzis, gid, godzina, sklep, zapisz_json  # noqa: E402

POLA_PRODUKTU = """
  id legacyResourceId handle title status vendor productType tags templateSuffix
  createdAt updatedAt onlineStoreUrl
  descriptionHtml
  seo { title description }
  category { id fullName }
  collections(first: 100) { nodes { id handle title } }
  metafields(first: 150) { nodes { id namespace key type value } }
  media(first: 100) {
    nodes {
      id alt mediaContentType status
      preview { image { url } }
      ... on Video { sources { url mimeType } }
      ... on ExternalVideo { originUrl }
    }
  }
  variants(first: 100) {
    nodes { id title sku barcode price compareAtPrice inventoryQuantity image { url } inventoryItem { id } }
  }
"""

Q_PRODUKT_ID = "query P($id: ID!) { product(id: $id) { %s } }" % POLA_PRODUKTU
Q_PRODUKT_HANDLE = "query P($h: String!) { productByIdentifier(identifier: { handle: $h }) { %s } }" % POLA_PRODUKTU

POLA_KOLEKCJI = """
  id legacyResourceId handle title updatedAt sortOrder templateSuffix
  descriptionHtml
  seo { title description }
  image { url altText }
  ruleSet { appliedDisjunctively rules { column relation condition } }
  productsCount { count }
  metafields(first: 100) { nodes { id namespace key type value } }
"""
Q_KOLEKCJA_ID = "query K($id: ID!) { collection(id: $id) { %s } }" % POLA_KOLEKCJI
Q_KOLEKCJA_HANDLE = "query K($h: String!) { collectionByIdentifier(identifier: { handle: $h }) { %s } }" % POLA_KOLEKCJI
Q_PRODUKTY_KOLEKCJI = """query PK($id: ID!, $after: String) {
  collection(id: $id) { products(first: 50, after: $after) { pageInfo { hasNextPage endCursor } nodes { %s } } }
}""" % POLA_PRODUKTU.replace("first: 100) { nodes { id handle title }", "first: 30) { nodes { id handle title }")

Q_METAOBIEKT = """query M($id: ID!) { metaobject(id: $id) {
  id handle type displayName updatedAt
  fields { key type value }
} }"""

Q_OBIEKT = """query Obiekt($id: ID!) { node(id: $id) { __typename id
 ... on Customer { email firstName lastName phone tags note state defaultAddress { address1 address2 city zip country company } metafields(first: 50) { nodes { namespace key type value } } }
 ... on Order { name email tags note displayFinancialStatus displayFulfillmentStatus customAttributes { key value } shippingAddress { address1 city zip country } metafields(first: 50) { nodes { namespace key type value } } }
 ... on DiscountCodeNode { codeDiscount { __typename ... on DiscountCodeBasic { title summary status startsAt endsAt codes(first: 20) { nodes { code } } } ... on DiscountCodeFreeShipping { title summary status startsAt endsAt } ... on DiscountCodeBxgy { title summary status startsAt endsAt } } }
 ... on DiscountAutomaticNode { automaticDiscount { __typename ... on DiscountAutomaticBasic { title summary status startsAt endsAt } ... on DiscountAutomaticBxgy { title summary status startsAt endsAt } } }
 ... on Page { title handle body isPublished templateSuffix }
 ... on Article { title handle body summary tags isPublished blog { id handle } }
 ... on Blog { title handle }
 ... on UrlRedirect { path target }
 ... on Menu { title handle items { title url type items { title url } } }
 ... on MetafieldDefinition { namespace key name typDefinicji: type { name } validations { name value } }
 ... on Metafield { namespace key type value }
 ... on ProductVariant { title sku barcode price compareAtPrice inventoryQuantity product { id handle } inventoryItem { id } }
 ... on InventoryItem { sku tracked variant { id product { id handle } } inventoryLevels(first: 20) { nodes { location { id name } quantities(names: ["available", "on_hand"]) { name quantity } } } }
 ... on MediaImage { alt image { url } }
 ... on Video { alt sources { url } }
 ... on GenericFile { alt url }
} }"""


def produkt(ident):
    g = gid("Product", ident)
    if g:
        d = wykonaj(Q_PRODUKT_ID, {"id": g}).get("product")
    else:
        d = wykonaj(Q_PRODUKT_HANDLE, {"h": ident}).get("productByIdentifier")
    if not d:
        raise BladShopify(f"Nie znaleziono produktu: {ident}")
    return d


def kolekcja(ident):
    g = gid("Collection", ident)
    if g:
        d = wykonaj(Q_KOLEKCJA_ID, {"id": g}).get("collection")
    else:
        d = wykonaj(Q_KOLEKCJA_HANDLE, {"h": ident}).get("collectionByIdentifier")
    if not d:
        raise BladShopify(f"Nie znaleziono kolekcji: {ident}")
    return d


def metaobiekt(ident):
    g = gid("Metaobject", ident)
    d = wykonaj(Q_METAOBIEKT, {"id": g or ident}).get("metaobject")
    if not d:
        raise BladShopify(f"Nie znaleziono metaobiektu: {ident}")
    return d


def obiekt(g):
    """Dowolny obiekt po gid (klient, zamowienie, rabat, strona, artykul, przekierowanie, menu, wariant, plik...)."""
    typ = g.split("/")[3] if g.startswith("gid://shopify/") else ""
    if typ == "Product":
        return "produkt", produkt(g)
    if typ == "Collection":
        return "kolekcja", kolekcja(g)
    if typ == "Metaobject":
        return "metaobiekt", metaobiekt(g)
    d = wykonaj(Q_OBIEKT, {"id": g}).get("node")
    if not d:
        raise BladShopify(f"Nie znaleziono obiektu: {g}")
    return f"obiekt-{d['__typename']}", d


def zapisz(typ, nazwa, dane, powod):
    sciezka = os.path.join(PROJEKT, "backup", dzis(), f"{typ}-{bezpieczna_nazwa(nazwa)}-{godzina()}.json")
    zapisz_json(sciezka, {"sklep": sklep(), "typ": typ, "powod": powod, "data": dzis(), "stan": dane})
    return os.path.relpath(sciezka, PROJEKT)


def main():
    ap = argparse.ArgumentParser(description="Backup produktow / kolekcji / metaobiektow przed zmiana (tylko odczyt).")
    ap.add_argument("--handle", nargs="*", default=[])
    ap.add_argument("--id", nargs="*", default=[])
    ap.add_argument("--plik", help="plik z lista uchwytow lub id produktow (jeden w linii)")
    ap.add_argument("--kolekcja", nargs="*", default=[])
    ap.add_argument("--kolekcja-z-produktami", nargs="*", default=[])
    ap.add_argument("--metaobiekt", nargs="*", default=[])
    ap.add_argument("--obiekt", nargs="*", default=[], help="dowolne gid (klient, zamowienie, rabat, strona, plik...)")
    ap.add_argument("--powod", default="")
    a = ap.parse_args()

    produkty = list(a.handle) + list(a.id)
    if a.plik:
        with open(a.plik, encoding="utf-8-sig") as f:
            produkty += [x.strip() for x in f if x.strip() and not x.startswith("#")]
    if not (produkty or a.kolekcja or a.kolekcja_z_produktami or a.metaobiekt or a.obiekt):
        ap.error("podaj co najmniej jeden obiekt (--handle / --id / --plik / --kolekcja / --metaobiekt / --obiekt)")

    zapisane, bledy = [], []
    for p in produkty:
        try:
            d = produkt(p)
            zapisane.append(zapisz("produkt", d["handle"], d, a.powod))
        except BladShopify as e:
            bledy.append(f"{p}: {e}")
    for k in a.kolekcja:
        try:
            d = kolekcja(k)
            zapisane.append(zapisz("kolekcja", d["handle"], d, a.powod))
        except BladShopify as e:
            bledy.append(f"{k}: {e}")
    for k in a.kolekcja_z_produktami:
        try:
            d = kolekcja(k)
            d["produkty"] = wszystkie_strony(Q_PRODUKTY_KOLEKCJI, "collection.products", {"id": d["id"]})
            zapisane.append(zapisz("kolekcja-z-produktami", d["handle"], d, a.powod))
        except BladShopify as e:
            bledy.append(f"{k}: {e}")
    for m in a.metaobiekt:
        try:
            d = metaobiekt(m)
            zapisane.append(zapisz("metaobiekt", f"{d['type']}-{d['handle']}", d, a.powod))
        except BladShopify as e:
            bledy.append(f"{m}: {e}")

    for g in a.obiekt:
        try:
            typ, d = obiekt(g)
            zapisane.append(zapisz(typ, d.get("handle") or d.get("name") or g.split("/")[-1], d, a.powod))
        except BladShopify as e:
            bledy.append(f"{g}: {e}")
    for z in zapisane:
        print("Backup:", z)
    for b in bledy:
        print("BLAD:", b, file=sys.stderr)
    print(f"Zapisano {len(zapisane)} plik(i), bledy: {len(bledy)}.")
    sys.exit(1 if bledy else 0)


if __name__ == "__main__":
    main()
