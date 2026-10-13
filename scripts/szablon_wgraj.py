#!/usr/bin/env python3
"""WGRANIE ZMIANY W SZABLONIE (MOTYWIE). URUCHAMIA WYLACZNIE CZLOWIEK.

Claude ma ten skrypt zablokowany (hook + reguly uprawnien). Uzytkownik uruchamia go sam:
  - w terminalu VS Code (Terminal > Nowy terminal), albo
  - w Claude Code w trybie terminala, wklejajac komende z prefiksem `!`.

  python scripts/szablon_wgraj.py robocze/szablon/2026-10-14-baner-garnki            podglad (nic nie zmienia)
  python scripts/szablon_wgraj.py robocze/szablon/2026-10-14-baner-garnki --wgraj    wgranie (backup + zapis + sprawdzenie)
  python scripts/szablon_wgraj.py --cofnij backup/2026-10-14/motyw-123-101500 --wgraj cofniecie do stanu z backupu

Przed wgraniem: edytor motywu zamkniety u WSZYSTKICH osob (zapis w edytorze nadpisuje cale pliki szablonow).
"""
import argparse
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopify_gql import BladShopify, wykonaj  # noqa: E402
from szablon_pobierz import pobierz_pliki  # noqa: E402
from wspolne import PROJEKT, dzis, godzina, sklep, wersja_api_domyslna, zapisz_json  # noqa: E402

M_ZAPIS = """mutation W($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $themeId, files: $files) {
    upsertedThemeFiles { filename }
    job { id done }
    userErrors { field message code filename }
  }
}"""
M_USUN = """mutation D($themeId: ID!, $files: [String!]!) {
  themeFilesDelete(themeId: $themeId, files: $files) {
    deletedThemeFiles { filename }
    userErrors { field message code filename }
  }
}"""


def md5(t):
    return hashlib.md5(t.encode("utf-8")).hexdigest()


def mutacja_motywu(zapytanie, zmienne):
    """Mutacja motywu wprost przez Shopify CLI (shopify_gql.py celowo jej nie przepuszcza)."""
    cli = shutil.which("shopify")
    if not cli:
        raise BladShopify("Brak Shopify CLI.")
    with tempfile.TemporaryDirectory() as tmp:
        pq, pv = os.path.join(tmp, "q.graphql"), os.path.join(tmp, "v.json")
        with open(pq, "w", encoding="utf-8") as f:
            f.write(zapytanie)
        with open(pv, "w", encoding="utf-8") as f:
            json.dump(zmienne, f, ensure_ascii=False)
        p = subprocess.run([cli, "store", "execute", "-s", sklep(), "--no-input", "-j", "--query-file", pq,
                            "--variable-file", pv, "--version", wersja_api_domyslna(), "--allow-mutations"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        dane = json.loads(p.stdout)
    except Exception:
        raise BladShopify((p.stderr or p.stdout)[-1500:])
    if p.returncode != 0 or "error" in dane:
        raise BladShopify(json.dumps(dane.get("error", dane), ensure_ascii=False)[:1500])
    try:
        with open(os.path.join(PROJEKT, "dziennik", "zmiany.log"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"czas": datetime.now().isoformat(timespec="seconds"), "sklep": sklep(),
                                "mutacje": ["szablon (czlowiek)"], "pliki": [x.get("filename", x) if isinstance(x, dict) else x
                                                                            for x in zmienne.get("files", [])]},
                               ensure_ascii=False) + "\n")
    except Exception:
        pass
    return dane


def potwierdz(tekst):
    if not sys.stdin or not sys.stdin.isatty():
        return True  # komenda wklejona recznie przez czlowieka (np. `!`): samo uruchomienie z --wgraj jest zgoda
    return input(f"{tekst} Wpisz TAK, aby kontynuowac: ").strip().upper() == "TAK"


def czytaj(sciezka):
    with open(sciezka, encoding="utf-8", newline="") as f:
        return f.read()


def plan_zmiany(katalog):
    baza = json.load(open(os.path.join(katalog, "_baza.json"), encoding="utf-8"))
    pliki_dir = os.path.join(katalog, "pliki")
    nowe = {}
    for root, _, files in os.walk(pliki_dir):
        for fn in files:
            pelna = os.path.join(root, fn)
            nazwa = os.path.relpath(pelna, pliki_dir).replace("\\", "/")
            nowe[nazwa] = czytaj(pelna)
    oryg_dir = os.path.join(katalog, "oryginal")
    zmienione = {}
    for nazwa, tresc in nowe.items():
        o = os.path.join(oryg_dir, *nazwa.split("/"))
        if os.path.exists(o) and czytaj(o) == tresc:
            continue
        zmienione[nazwa] = tresc
    return baza, zmienione


def pokaz_roznice(nazwa, stara, nowa):
    diff = list(difflib.unified_diff((stara or "").splitlines(), nowa.splitlines(), lineterm="", n=1))
    dodane = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
    usuniete = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
    print(f"\n=== {nazwa}: +{dodane} / -{usuniete} linii")
    for d in diff[:40]:
        print("   " + d[:160])
    if len(diff) > 40:
        print(f"   ... ({len(diff) - 40} kolejnych linii roznic)")


def wgraj(theme, pliki_do_zapisu, do_usuniecia, opis):
    print("\nBackup obecnego stanu ...")
    nazwy = list(pliki_do_zapisu) + list(do_usuniecia)
    obecne = pobierz_pliki(theme["id"], nazwy)
    kat = os.path.join(PROJEKT, "backup", dzis(), f"motyw-{theme['id'].split('/')[-1]}-{godzina()}")
    manifest = {"motyw": theme, "opis": opis, "pliki": {}}
    for n in nazwy:
        p = obecne.get(n)
        if p and "content" in (p.get("body") or {}):
            sc = os.path.join(kat, "pliki", *n.split("/"))
            os.makedirs(os.path.dirname(sc), exist_ok=True)
            with open(sc, "w", encoding="utf-8", newline="") as f:
                f.write(p["body"]["content"])
            manifest["pliki"][n] = {"istnial": True}
        else:
            manifest["pliki"][n] = {"istnial": False}
    zapisz_json(os.path.join(kat, "manifest.json"), manifest)
    print("Backup:", os.path.relpath(kat, PROJEKT))

    if pliki_do_zapisu:
        wej = [{"filename": n, "body": {"type": "TEXT", "value": t}} for n, t in pliki_do_zapisu.items()]
        w = mutacja_motywu(M_ZAPIS, {"themeId": theme["id"], "files": wej})["themeFilesUpsert"]
        if w["userErrors"]:
            print("BLEDY Shopify:", json.dumps(w["userErrors"], ensure_ascii=False))
            print(f"Nic nie zostalo czesciowo cofniete. Backup jest w {os.path.relpath(kat, PROJEKT)}.")
            sys.exit(3)
    if do_usuniecia:
        w = mutacja_motywu(M_USUN, {"themeId": theme["id"], "files": list(do_usuniecia)})["themeFilesDelete"]
        if w["userErrors"]:
            print("BLEDY przy usuwaniu nowych plikow:", json.dumps(w["userErrors"], ensure_ascii=False))

    print("Sprawdzam odczytem ...")
    zgodne = {}
    for _ in range(10):
        po = pobierz_pliki(theme["id"], list(pliki_do_zapisu))
        zgodne = {n: md5((po.get(n, {}).get("body") or {}).get("content", "")) == md5(t) for n, t in pliki_do_zapisu.items()}
        if all(zgodne.values()):
            break
        time.sleep(3)
    for n, ok in zgodne.items():
        uw = "" if ok else ("  (Shopify mogl przeformatowac plik JSON, sprawdz w podgladzie)" if n.endswith(".json") else "  NIEZGODNE")
        print(f"  {n}: {'OK' if ok else 'rozni sie'}{uw}")
    print(f"\nCofniecie: python scripts/szablon_wgraj.py --cofnij {os.path.relpath(kat, PROJEKT)} --wgraj")


def main():
    ap = argparse.ArgumentParser(description="Wgranie zmiany w szablonie. Uruchamia tylko czlowiek.")
    ap.add_argument("katalog", nargs="?", help="robocze/szablon/<data>-<nazwa>")
    ap.add_argument("--cofnij", help="katalog backupu motywu (backup/<data>/motyw-<id>-<godzina>)")
    ap.add_argument("--wgraj", action="store_true", help="naprawde zapisz (bez tego tylko podglad)")
    ap.add_argument("--ignoruj-zmiany", action="store_true", help="wgraj mimo ze plik w sklepie zmienil sie od przygotowania")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        if a.cofnij:
            man = json.load(open(os.path.join(a.cofnij, "manifest.json"), encoding="utf-8"))
            theme = man["motyw"]
            zapis = {n: czytaj(os.path.join(a.cofnij, "pliki", *n.split("/"))) for n, i in man["pliki"].items() if i["istnial"]}
            usun = [n for n, i in man["pliki"].items() if not i["istnial"]]
            print(f"COFNIECIE w motywie {theme['name']} ({theme['role']}): przywrocenie {len(zapis)} plikow, usuniecie {len(usun)} nowych.")
            for n in usun:
                print(f"  usuniety zostanie plik dodany zmiana: {n}")
            if not a.wgraj:
                print("\nPODGLAD. Aby cofnac, dodaj --wgraj.")
                return
            if not potwierdz("Cofam zmiane w motywie."):
                sys.exit("Przerwano.")
            wgraj(theme, zapis, usun, f"cofniecie {a.cofnij}")
            return

        if not a.katalog:
            ap.error("podaj katalog zmiany albo --cofnij")
        baza, zmienione = plan_zmiany(a.katalog)
        theme = baza["motyw"]
        if not zmienione:
            sys.exit("Brak roznic miedzy pliki/ a oryginal/. Nic do wgrania.")
        obecne = pobierz_pliki(theme["id"], list(zmienione))
        konflikty = []
        for n in zmienione:
            b = baza["pliki"].get(n, {})
            teraz = (obecne.get(n, {}).get("body") or {}).get("content")
            if b.get("istnial") and teraz is not None and md5(teraz) != b.get("md5"):
                konflikty.append(n)
        print(f"Motyw: {theme['name']}  rola: {theme['role']}" + ("   <<< TO JEST MOTYW LIVE, KLIENCI WIDZA ZMIANE OD RAZU" if theme["role"] == "MAIN" else ""))
        for n, t in zmienione.items():
            pokaz_roznice(n, (obecne.get(n, {}).get("body") or {}).get("content"), t)
        if konflikty and not a.ignoruj_zmiany:
            print("\nSTOP: te pliki zmienily sie w sklepie od chwili przygotowania zmiany (edytor motywu albo ktos inny):")
            for n in konflikty:
                print("  ", n)
            sys.exit("Popros Claude o przygotowanie zmiany od nowa (szablon_pobierz.py), zeby nie skasowac cudzych zmian.")
        print("\nPRZED WGRANIEM: zamknij edytor motywu u wszystkich osob (zapis w edytorze nadpisze ten plik).")
        if not a.wgraj:
            print("PODGLAD: nic nie zostalo zmienione. Aby wgrac, uruchom to samo z --wgraj.")
            return
        if not potwierdz("Wgrywam zmiane do motywu."):
            sys.exit("Przerwano.")
        wgraj(theme, zmienione, [], f"zmiana {a.katalog}")
    except BladShopify as e:
        sys.exit(f"BLAD: {e}")


if __name__ == "__main__":
    main()
