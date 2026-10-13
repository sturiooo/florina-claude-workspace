"""Wspolne funkcje skryptow (bez zewnetrznych bibliotek)."""
import json
import os
import re
from datetime import datetime

PROJEKT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def wczytaj_env():
    """Czyta plik .env z katalogu projektu (KLUCZ=wartosc). Nie wypisuje wartosci na ekran."""
    wynik = {}
    sciezka = os.path.join(PROJEKT, ".env")
    if os.path.isfile(sciezka):
        with open(sciezka, encoding="utf-8-sig") as f:
            for linia in f:
                linia = linia.strip()
                if not linia or linia.startswith("#") or "=" not in linia:
                    continue
                k, v = linia.split("=", 1)
                wynik[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("SHOPIFY_STORE", "BASELINKER_TOKEN", "SHOPIFY_API_VERSION"):
        if os.environ.get(k):
            wynik[k] = os.environ[k]
    return wynik


def sklep():
    return wczytaj_env().get("SHOPIFY_STORE") or "florina-pl.myshopify.com"


def wersja_api_domyslna():
    """Stabilna wersja Admin API (CLI bez tej flagi uzywa 'unstable')."""
    return wczytaj_env().get("SHOPIFY_API_VERSION") or "2026-07"


def dzis():
    return datetime.now().strftime("%Y-%m-%d")


def godzina():
    return datetime.now().strftime("%H%M%S")


def katalog(*czesci):
    sciezka = os.path.join(PROJEKT, *czesci)
    os.makedirs(sciezka, exist_ok=True)
    return sciezka


def zapisz_json(sciezka, dane):
    os.makedirs(os.path.dirname(sciezka), exist_ok=True)
    with open(sciezka, "w", encoding="utf-8") as f:
        json.dump(dane, f, ensure_ascii=False, indent=2)
    return sciezka


def bezpieczna_nazwa(tekst, dlugosc=60):
    t = re.sub(r"[^A-Za-z0-9_-]+", "-", str(tekst)).strip("-")
    return (t or "obiekt")[:dlugosc]


def gid(typ, wartosc):
    """'123' albo 'gid://shopify/Product/123' -> pelny gid."""
    wartosc = str(wartosc).strip()
    if wartosc.startswith("gid://"):
        return wartosc
    if wartosc.isdigit():
        return f"gid://shopify/{typ}/{wartosc}"
    return None
