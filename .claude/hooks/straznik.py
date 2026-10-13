#!/usr/bin/env python3
"""Hook PreToolUse (Bash i PowerShell): straznik zmian w sklepie Florina.

Co robi przed kazda komenda, ktora Claude chce uruchomic:
  - BLOKUJE: motyw / szablon (shopify theme push/publish/..., mutacje theme*, skrypt szablon_wgraj.py, ktory
    uruchamia tylko czlowiek przez `!`), ustawienia sklepu, platnosci i inne pozycje z polityka_zmian.py,
    bezposrednie wywolania Admin API z pominieciem skryptow, zapis do BaseLinkera,
    zmiany w sklepie robione wlasnym, doraznym skryptem zamiast skryptow z katalogu scripts/.
  - PYTA (okno potwierdzenia): o kazda inna zmiane w sklepie, z opisem; przy usuwaniu z twardym ostrzezeniem.
  - Milczy przy zwyklych odczytach (wtedy decyduja reguly z .claude/settings.json).

Polityka (listy) jest w polityka_zmian.py. Dziennik decyzji: dziennik/straznik.log.
Wejscie: JSON na stdin (tool_name, tool_input.command, cwd). Wyjscie: JSON hookSpecificOutput albo nic.
"""
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polityka_zmian import nazwy_mutacji, ocen_baselinker, ocen_mutacje, opis_zmiany  # noqa: E402

TYLKO_CZLOWIEK = ("szablon_wgraj.py",)

ZNANE_SKRYPTY_ZMIAN = ("scripts/shopify_gql.py", "scripts/upload_mediow.py", "scripts/cechy.py")
ROZSZERZENIA = (".graphql", ".gql", ".json", ".py", ".txt", ".js", ".ps1", ".sh")
URUCHAMIA = re.compile(r"(?i)(^|[\s;&|(])(shopify|python3?|py|node|curl|wget|invoke-restmethod|invoke-webrequest|irm|iwr|pwsh|powershell)(\.exe|\.cmd)?\b")
MOTYW = re.compile(r"(?i)\bshopify(\.cmd)?\s+theme\s+(push|publish|delete|rename|share|dev|duplicate|console|init|package|metafields|profile)\b")
APKA = re.compile(r"(?i)\bshopify(\.cmd)?\s+app\b")
ADMIN_API = re.compile(r"(?i)myshopify\.com/admin|/admin/api/\d")


def projekt():
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def loguj(decyzja, komenda, szczegoly):
    try:
        katalog = os.path.join(projekt(), "dziennik")
        os.makedirs(katalog, exist_ok=True)
        with open(os.path.join(katalog, "straznik.log"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"czas": datetime.now().isoformat(timespec="seconds"), "decyzja": decyzja,
                                "komenda": komenda[:600], "szczegoly": szczegoly}, ensure_ascii=False) + "\n")
    except Exception:
        pass


def odpowiedz(decyzja, powod, komenda):
    loguj(decyzja, komenda, powod)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": decyzja,
                                             "permissionDecisionReason": powod}}))
    sys.exit(0)


def pliki_z_komendy(komenda, cwd):
    """Czyta pliki wskazane w komendzie (zapytania .graphql, zmienne .json, skrypty .py)."""
    tresci = {}
    tokeny = re.findall(r'"([^"]+)"|\'([^\']+)\'|(\S+)', komenda)
    for grupa in tokeny:
        t = next((g for g in grupa if g), "")
        if "=" in t and t.startswith("--"):
            t = t.split("=", 1)[1]
        t = t.strip().strip(",;")
        if not t.lower().endswith(ROZSZERZENIA):
            continue
        sciezka = t if os.path.isabs(t) else os.path.join(cwd, t)
        try:
            if os.path.isfile(sciezka) and os.path.getsize(sciezka) < 3_000_000:
                with open(sciezka, encoding="utf-8", errors="replace") as f:
                    tresci[t.replace("\\", "/")] = f.read()
        except Exception:
            pass
    return tresci


def ocen(komenda, cwd):
    norm = komenda.replace("\\", "/")
    if MOTYW.search(komenda):
        return "deny", ("Claude nie zmienia motywu (kod, publikacja, usuwanie). Zmiane w szablonie przygotuj jako komende dla czlowieka (skill zmiany-w-szablonie): uzytkownik uruchamia ja sam przez `!` albo w terminalu VS Code.")
    if APKA.search(komenda):
        return "deny", "Komendy `shopify app` sa zablokowane w tym projekcie."
    if not URUCHAMIA.search(komenda):
        return None, ""
    if any(s in norm.lower() for s in TYLKO_CZLOWIEK):
        return "deny", ("Ten skrypt zmienia motyw sklepu i uruchamia go wylacznie czlowiek: wklejajac komende z prefiksem `!` "
                        "albo w terminalu VS Code (skill zmiany-w-szablonie). Przygotuj komende i popros uzytkownika.")
    pliki = pliki_z_komendy(komenda, cwd)
    tekst = komenda + "\n" + "\n".join(pliki.values())

    if ADMIN_API.search(komenda):
        return "deny", "Bezposrednie wywolania Admin API sa zablokowane. Uzyj scripts/shopify_gql.py (pilnuje zasad i robi dziennik)."

    bl = ocen_baselinker(tekst)
    if bl:
        return "deny", "BaseLinker jest tylko do odczytu. Zablokowane metody: " + ", ".join(bl) + "."

    flaga = "allow-mutations" in komenda
    znany = any(s in norm.lower() for s in ZNANE_SKRYPTY_ZMIAN)
    if flaga and not znany:
        return "deny", ("Zmiany w sklepie wolno robic tylko skryptami scripts/shopify_gql.py, scripts/upload_mediow.py "
                        "i scripts/cechy.py (sprawdzaja zasady, wymagaja backupu i zapisuja dziennik).")
    for nazwa, tresc in pliki.items():
        if nazwa.endswith(".py") and "allow-mutations" in tresc and not any(nazwa.lower().endswith(s) for s in ZNANE_SKRYPTY_ZMIAN):
            return "deny", f"Skrypt {nazwa} probuje zmieniac sklep z pominieciem skryptow z katalogu scripts/. To jest zablokowane."

    decyzja, powody, nazwy, ostrzezenia = ocen_mutacje(tekst)
    if any(n.endswith(".py") for n in pliki):
        # ostrzezenia o polach licz tylko z tresci zapytan i zmiennych, nie z kodu skryptow
        tekst_danych = komenda + "\n" + "\n".join(t for n, t in pliki.items() if not n.endswith(".py"))
        ostrzezenia = ocen_mutacje(tekst_danych)[3] if nazwy_mutacji(tekst_danych) else []
    if decyzja == "zakaz":
        return "deny", " ".join(powody)
    if flaga:
        if decyzja in ("pytaj", "usun"):
            opis = opis_zmiany(nazwy, tekst, decyzja, ostrzezenia)
        else:
            skrypt = next((s for s in ZNANE_SKRYPTY_ZMIAN if s in norm.lower()), "skrypt")
            opis = f"ZMIANA W SKLEPIE przez {skrypt}"
        return "ask", (opis + ". Zatwierdz tylko, jesli Claude pokazal Ci podglad zmian, zrobil backup "
                       "i to jest dokladnie to, o co prosiles.")
    return None, ""


def main():
    surowe = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    dane = json.loads(surowe or "{}")
    wejscie = dane.get("tool_input") or {}
    komenda = wejscie.get("command") or ""
    if not komenda:
        sys.exit(0)
    cwd = dane.get("cwd") or projekt()
    try:
        decyzja, powod = ocen(komenda, cwd)
    except Exception as e:  # awaria straznika: przy komendach dotyczacych sklepu blokujemy
        if re.search(r"(?i)shopify|baselinker|allow-mutations", komenda):
            sys.stderr.write(f"Straznik nie mogl ocenic komendy ({e}). Dla bezpieczenstwa blokuje.\n")
            loguj("deny-blad", komenda, str(e))
            sys.exit(2)
        sys.exit(0)
    if decyzja:
        odpowiedz(decyzja, powod, komenda)
    sys.exit(0)


if __name__ == "__main__":
    main()
