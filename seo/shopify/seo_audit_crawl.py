#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seo_audit_crawl.py  --  szybki crawler SEO do audytu Shopify
============================================================
Pobiera HTML stron i parsuje kluczowe sygnaly SEO. Lepsze niz WebFetch/LLM,
ktory potrafi halucynowac canonical/OG/JSON-LD. Tylko stdlib.

Uzycie:
  python seo_audit_crawl.py https://sklep.pl/ https://sklep.pl/products/xxx
  python seo_audit_crawl.py --file urls.txt
  python seo_audit_crawl.py --file urls.txt --csv wynik.csv

Dla kazdego URL zwraca: status, H1..H6 (liczby), title, meta description,
canonical, liczbe hreflang, og:image (tak/nie), liczbe blokow JSON-LD,
meta robots (jesli noindex/nofollow).

Zakres (~15-25 URL): home + kolekcje z menu + 6-10 produktow (bestseller/
nowosc/OOS) + blog home + 3-5 artykulow + strony statyczne.
"""
import argparse
import csv
import re
import ssl
import sys
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

# Na Windows magazyn CA Pythona bywa nieaktualny -> falszywe "certificate expired".
# --insecure wylacza weryfikacje (uzywaj tylko gdy potwierdzisz cert curl-em).
SSL_CTX = None


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pl,en"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
            return r.getcode(), r.geturl(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except Exception as e:
        return None, url, f"__ERR__ {e}"


def first(pattern, html, flags=re.I | re.S):
    m = re.search(pattern, html, flags)
    return (m.group(1).strip() if m else "")


def analyze(html):
    out = {}
    for t in ("h1", "h2", "h3", "h4", "h5", "h6"):
        out[t] = len(re.findall(rf"<{t}[\s>]", html, re.I))
    title = first(r"<title[^>]*>(.*?)</title>", html)
    out["title"] = re.sub(r"\s+", " ", title)
    out["title_len"] = len(out["title"])
    desc = first(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)', html)
    out["desc_len"] = len(desc)
    out["desc"] = desc[:90]
    out["canonical"] = first(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', html)
    out["hreflang"] = len(re.findall(r'rel=["\']alternate["\'][^>]+hreflang=', html, re.I))
    out["og_image"] = "tak" if re.search(r'property=["\']og:image["\']', html, re.I) else "NIE"
    out["jsonld"] = len(re.findall(r'application/ld\+json', html, re.I))
    robots = first(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']*)', html)
    out["robots"] = robots if re.search(r"noindex|nofollow", robots, re.I) else ""
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--file", help="plik z URL-ami (po jednym w linii; '#' = komentarz)")
    ap.add_argument("--csv", help="zapisz wyniki do CSV")
    ap.add_argument("--insecure", action="store_true", help="pomin weryfikacje SSL (Windows CA workaround)")
    args = ap.parse_args()

    global SSL_CTX
    if args.insecure:
        SSL_CTX = ssl._create_unverified_context()

    urls = list(args.urls)
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            urls += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    if not urls:
        sys.exit("Podaj URL-e albo --file urls.txt")

    rows = []
    for url in urls:
        code, final, html = fetch(url)
        if code is None:
            print(f"[ERR ] {url}  {html}")
            continue
        if html.startswith("__ERR__"):
            print(f"[{code}] {url}  {html}")
            continue
        a = analyze(html)
        red = "" if final.rstrip("/") == url.rstrip("/") else f" -> {final}"
        warn = []
        if a["h1"] != 1:
            warn.append(f"H1={a['h1']}!")
        if not a["canonical"]:
            warn.append("brak canonical")
        if a["title_len"] == 0:
            warn.append("brak title")
        if a["desc_len"] == 0:
            warn.append("brak desc")
        if a["robots"]:
            warn.append(a["robots"])
        flag = ("  <<< " + ", ".join(warn)) if warn else ""
        print(f"[{code}] {url}{red}")
        print(f"      H1-6={a['h1']}/{a['h2']}/{a['h3']}/{a['h4']}/{a['h5']}/{a['h6']}  "
              f"title({a['title_len']})  desc({a['desc_len']})  "
              f"hreflang={a['hreflang']}  og:image={a['og_image']}  JSON-LD={a['jsonld']}{flag}")
        print(f"      title: {a['title']}")
        print(f"      canon: {a['canonical'] or 'BRAK'}")
        rows.append({"url": url, "status": code, **a})

    if args.csv and rows:
        cols = ["url", "status", "h1", "h2", "h3", "h4", "h5", "h6",
                "title_len", "desc_len", "canonical", "hreflang", "og_image",
                "jsonld", "robots", "title", "desc"]
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in cols})
        print(f"\nZapisano CSV: {args.csv} ({len(rows)} URL)")


if __name__ == "__main__":
    main()
