#!/usr/bin/env python3
"""Dodawanie zdjec i wideo do karty produktu.

Domyslnie TRYB PODGLADU: nic nie wysyla, tylko pokazuje plan. Zmiana dopiero z --allow-mutations
(po zgodzie uzytkownika). Przed zmiana skrypt sam robi backup produktu do backup/RRRR-MM-DD/.

  python scripts/upload_mediow.py --produkt patelnia-x --pliki robocze/media/a.jpg robocze/media/b.jpg --alty "Patelnia X 24 cm z gory" "Patelnia X 24 cm, powloka"
  python scripts/upload_mediow.py --produkt patelnia-x --pliki robocze/media/film.mp4 --alt "Patelnia X w uzyciu" --allow-mutations
  python scripts/upload_mediow.py --produkt patelnia-x --url https://.../zdjecie.jpg --alt "..."      (zdjecie z publicznego adresu)
  python scripts/upload_mediow.py --produkt patelnia-x --youtube https://www.youtube.com/watch?v=XXXX --alt "..."
  --na-poczatek   nowe media trafiaja na poczatek galerii (pierwsze = zdjecie glowne)

Droga techniczna: stagedUploadsCreate -> wyslanie pliku (POST multipart) -> productCreateMedia -> czekanie na status READY.
"""
import argparse
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backup_produktu import produkt as pobierz_produkt, zapisz as zapisz_backup  # noqa: E402
from shopify_gql import BladShopify, wykonaj  # noqa: E402

TYPY = {
    ".jpg": ("IMAGE", "image/jpeg"), ".jpeg": ("IMAGE", "image/jpeg"), ".png": ("IMAGE", "image/png"),
    ".webp": ("IMAGE", "image/webp"), ".gif": ("IMAGE", "image/gif"),
    ".mp4": ("VIDEO", "video/mp4"), ".mov": ("VIDEO", "video/quicktime"),
}
MAKS_MB = {"IMAGE": 20, "VIDEO": 1024}

M_STAGED = """mutation S($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets { url resourceUrl parameters { name value } }
    userErrors { field message }
  }
}"""

M_MEDIA = """mutation C($productId: ID!, $media: [CreateMediaInput!]!) {
  productCreateMedia(productId: $productId, media: $media) {
    media { id alt mediaContentType status }
    mediaUserErrors { field message }
  }
}"""

M_KOLEJNOSC = """mutation R($id: ID!, $moves: [MoveInput!]!) {
  productReorderMedia(id: $id, moves: $moves) {
    job { id }
    mediaUserErrors { field message }
  }
}"""

Q_STATUS = """query St($id: ID!) { product(id: $id) { media(first: 100) { nodes { id status alt mediaContentType
  mediaErrors { code details message } } } } }"""


def wyslij_plik(cel, sciezka, mime):
    granica = uuid.uuid4().hex
    czesci = []
    for p in cel["parameters"]:
        czesci.append(f'--{granica}\r\nContent-Disposition: form-data; name="{p["name"]}"\r\n\r\n{p["value"]}\r\n'.encode())
    with open(sciezka, "rb") as f:
        zawartosc = f.read()
    nazwa = os.path.basename(sciezka)
    czesci.append(f'--{granica}\r\nContent-Disposition: form-data; name="file"; filename="{nazwa}"\r\nContent-Type: {mime}\r\n\r\n'.encode())
    czesci.append(zawartosc)
    czesci.append(f"\r\n--{granica}--\r\n".encode())
    cialo = b"".join(czesci)
    req = urllib.request.Request(cel["url"], data=cialo, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={granica}"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            if r.status not in (200, 201, 204):
                raise BladShopify(f"Wysylanie pliku {nazwa}: HTTP {r.status}")
    except urllib.error.HTTPError as e:
        raise BladShopify(f"Wysylanie pliku {nazwa}: HTTP {e.code} {e.read()[:300]!r}")


def main():
    ap = argparse.ArgumentParser(description="Zdjecia i wideo do produktu (domyslnie tylko podglad).")
    ap.add_argument("--produkt", required=True, help="uchwyt albo id produktu")
    ap.add_argument("--pliki", nargs="*", default=[])
    ap.add_argument("--url", nargs="*", default=[], help="publiczne adresy zdjec")
    ap.add_argument("--youtube", nargs="*", default=[], help="linki YouTube / Vimeo")
    ap.add_argument("--alt", default="", help="jeden tekst alternatywny dla wszystkich")
    ap.add_argument("--alty", nargs="*", default=[], help="teksty alternatywne po kolei dla kazdego elementu")
    ap.add_argument("--na-poczatek", action="store_true")
    ap.add_argument("--allow-mutations", action="store_true", help="wykonaj naprawde (po zgodzie uzytkownika)")
    a = ap.parse_args()

    elementy = []
    for p in a.pliki:
        ext = os.path.splitext(p)[1].lower()
        if ext not in TYPY:
            sys.exit(f"BLAD: nieobslugiwany typ pliku {p}. Dozwolone: {', '.join(TYPY)}")
        if not os.path.isfile(p):
            sys.exit(f"BLAD: nie ma pliku {p}")
        typ, mime = TYPY[ext]
        mb = os.path.getsize(p) / 1024 / 1024
        if mb > MAKS_MB[typ]:
            sys.exit(f"BLAD: {p} ma {mb:.1f} MB, limit dla {typ} to {MAKS_MB[typ]} MB.")
        elementy.append({"rodzaj": "plik", "sciezka": p, "typ": typ, "mime": mime, "mb": mb})
    for u in a.url:
        elementy.append({"rodzaj": "url", "sciezka": u, "typ": "IMAGE", "mime": mimetypes.guess_type(u)[0] or "", "mb": 0})
    for u in a.youtube:
        elementy.append({"rodzaj": "youtube", "sciezka": u, "typ": "EXTERNAL_VIDEO", "mime": "", "mb": 0})
    if not elementy:
        ap.error("podaj --pliki, --url albo --youtube")
    for i, e in enumerate(elementy):
        e["alt"] = a.alty[i] if i < len(a.alty) else a.alt
        if not e["alt"].strip():
            sys.exit(f"BLAD: brak tekstu alternatywnego dla {e['sciezka']}. Kazde zdjecie i wideo musi miec alt (--alt albo --alty).")
        if len(e["alt"]) > 512:
            sys.exit(f"BLAD: alt dla {e['sciezka']} jest dluzszy niz 512 znakow.")

    sys.stdout.reconfigure(encoding="utf-8")
    prod = pobierz_produkt(a.produkt)
    print(f"Produkt: {prod['title']} ({prod['handle']}), obecnie mediow: {len(prod['media']['nodes'])}")
    for e in elementy:
        print(f"  + {e['typ']:<14} {e['sciezka']}  ({e['mb']:.1f} MB)  alt: {e['alt']}")
    print(f"  Pozycja: {'na poczatku galerii' if a.na_poczatek else 'na koncu galerii'}")
    if not a.allow_mutations:
        print("\nTRYB PODGLADU: nic nie zostalo wyslane. Po zgodzie uzytkownika uruchom to samo z --allow-mutations.")
        return

    print("Backup:", zapisz_backup("produkt", prod["handle"], prod, "przed dodaniem mediow"))
    pliki = [e for e in elementy if e["rodzaj"] == "plik"]
    if pliki:
        wej = [{"resource": e["typ"], "filename": os.path.basename(e["sciezka"]), "mimeType": e["mime"],
                "fileSize": str(os.path.getsize(e["sciezka"])), "httpMethod": "POST"} for e in pliki]
        wynik = wykonaj(M_STAGED, {"input": wej}, zmiany=True)["stagedUploadsCreate"]
        if wynik["userErrors"]:
            sys.exit(f"BLAD stagedUploadsCreate: {wynik['userErrors']}")
        for e, cel in zip(pliki, wynik["stagedTargets"]):
            print("Wysylam", e["sciezka"], "...")
            wyslij_plik(cel, e["sciezka"], e["mime"])
            e["zrodlo"] = cel["resourceUrl"]
    media = []
    for e in elementy:
        zrodlo = e.get("zrodlo") or e["sciezka"]
        media.append({"originalSource": zrodlo, "alt": e["alt"], "mediaContentType": e["typ"]})
    wynik = wykonaj(M_MEDIA, {"productId": prod["id"], "media": media}, zmiany=True)["productCreateMedia"]
    if wynik["mediaUserErrors"]:
        sys.exit(f"BLAD productCreateMedia: {wynik['mediaUserErrors']}")
    nowe = [m["id"] for m in wynik["media"]]
    print("Dodane media:", ", ".join(nowe))

    for _ in range(40):  # do ok. 3 minut
        stan = {m["id"]: m for m in wykonaj(Q_STATUS, {"id": prod["id"]})["product"]["media"]["nodes"]}
        statusy = [stan.get(i, {}).get("status") for i in nowe]
        if all(s in ("READY", "FAILED") for s in statusy):
            break
        time.sleep(5)
    for i in nowe:
        m = stan.get(i, {})
        print(f"  {i}: {m.get('status')} {m.get('mediaErrors') or ''}")
    if a.na_poczatek:
        ruchy = [{"id": i, "newPosition": str(n)} for n, i in enumerate(nowe)]
        r = wykonaj(M_KOLEJNOSC, {"id": prod["id"], "moves": ruchy}, zmiany=True)["productReorderMedia"]
        print("Kolejnosc:", "zmieniona" if not r["mediaUserErrors"] else r["mediaUserErrors"])
    if any(stan.get(i, {}).get("status") == "FAILED" for i in nowe):
        sys.exit("UWAGA: czesc mediow ma status FAILED (zly plik albo format). Sprawdz w panelu i powiedz Igorowi.")
    print("Gotowe. Sprawdz karte produktu w sklepie (podglad) i porownaj z oczekiwaniem.")


if __name__ == "__main__":
    try:
        main()
    except BladShopify as e:
        print("BLAD:", e, file=sys.stderr)
        sys.exit(2)
