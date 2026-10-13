#!/usr/bin/env python3
"""Testy straznika. Uruchom: python .claude/hooks/test_straznik.py  (wynik: OK albo lista bledow)."""
import json
import os
import subprocess
import sys
import tempfile

TU = os.path.dirname(os.path.abspath(__file__))
STRAZNIK = os.path.join(TU, "straznik.py")
PROJ = os.path.dirname(os.path.dirname(TU))

P = "gid://shopify/Product/111"
WRAPPER = "python scripts/shopify_gql.py --query-file robocze/m.graphql --allow-mutations"
WRAPPER_V = "python scripts/shopify_gql.py --query-file robocze/m.graphql --variable-file robocze/v.json --allow-mutations"
M_SET = "mutation M($m: [MetafieldsSetInput!]!) { metafieldsSet(metafields: $m) { userErrors { message } } }"
M_UPD = "mutation U($p: ProductUpdateInput!) { productUpdate(product: $p) { product { id } userErrors { message } } }"


def g(tresc):
    return {"robocze/m.graphql": tresc}


PRZYPADKI = [
    # (opis, narzedzie, komenda, pliki {nazwa: tresc}, oczekiwana decyzja: deny / ask / None, fragment powodu albo None)
    ("odczyt przez wrapper", "Bash", 'python scripts/shopify_gql.py -q "{ shop { name } }"', {}, None, None),
    ("odczyt w PowerShell", "PowerShell", 'python scripts\\shopify_gql.py -q "{ shop { name } }"', {}, None, None),
    ("zwykla komenda", "Bash", "git status", {}, None, None),
    ("czytanie pliku z nazwami mutacji to nie zmiana", "Bash", "cat .claude/hooks/polityka_zmian.py", {}, None, None),
    ("czytanie skryptu szablonu to nie uruchomienie", "Bash", "cat scripts/szablon_wgraj.py", {}, None, None),

    # motyw / szablon: zablokowane dla Claude
    ("shopify theme push", "Bash", "shopify theme push --theme 123", {}, "deny", "szablon"),
    ("shopify theme publish w PowerShell", "PowerShell", "shopify theme publish --theme 1", {}, "deny", "szablon"),
    ("shopify theme pull nie zmienia sklepu", "Bash", "shopify theme pull --theme 1", {}, None, None),
    ("themeFilesUpsert przez wrapper", "Bash", WRAPPER,
     g('mutation { themeFilesUpsert(themeId: "gid://shopify/OnlineStoreTheme/1", files: []) { userErrors { message } } }'), "deny", "themeFilesUpsert"),
    ("alias nie ukryje mutacji motywu", "Bash", WRAPPER,
     g('mutation { a: tagsAdd(id: "gid://shopify/Product/1", tags: ["x"]) { node { id } } b: themePublish(id: "gid://shopify/OnlineStoreTheme/1") { userErrors { message } } }'),
     "deny", "themePublish"),
    ("skrypt wgrywania szablonu uruchamia tylko czlowiek", "Bash", "python scripts/szablon_wgraj.py robocze/szablon/x --wgraj", {}, "deny", "czlowiek"),
    ("skrypt wgrywania szablonu w PowerShell", "PowerShell", "python .\\scripts\\szablon_wgraj.py robocze\\szablon\\x --wgraj", {}, "deny", "czlowiek"),
    ("pobranie plikow motywu (odczyt)", "Bash", "python scripts/szablon_pobierz.py --motyw live --pliki sections/a.liquid --zmiana x", {}, None, None),
    ("wlasny skrypt z mutacja motywu", "Bash", "python robocze/m.py",
     {"robocze/m.py": 'Q = "mutation { themeFilesUpsert(themeId: \\"gid://shopify/OnlineStoreTheme/1\\", files: []) { userErrors { message } } }"'},
     "deny", "themeFilesUpsert"),

    # zwykle zmiany: pytanie o zgode
    ("opis produktu", "Bash", WRAPPER_V,
     {"robocze/m.graphql": M_UPD, "robocze/v.json": json.dumps({"p": {"id": P, "descriptionHtml": "<p>x</p>"}})}, "ask", "ZMIANA W SKLEPIE"),
    ("zmiana statusu produktu (z ostrzezeniem)", "Bash", WRAPPER_V,
     {"robocze/m.graphql": M_UPD, "robocze/v.json": json.dumps({"p": {"id": P, "status": "ARCHIVED"}})}, "ask", "statusu"),
    ("ceny wariantow (z ostrzezeniem)", "Bash", WRAPPER,
     g('mutation { productVariantsBulkUpdate(productId: "gid://shopify/Product/1", variants: [{id: "gid://shopify/ProductVariant/2", price: "1.00"}]) { userErrors { message } } }'),
     "ask", "ceny"),
    ("rabat", "Bash", WRAPPER,
     g('mutation { discountCodeBasicCreate(basicCodeDiscount: {title: "X"}) { userErrors { message } } }'), "ask", "discountCodeBasicCreate"),
    ("tag na zamowieniu", "Bash", WRAPPER,
     g('mutation { tagsAdd(id: "gid://shopify/Order/9", tags: ["x"]) { userErrors { message } } }'), "ask", "ZMIANA W SKLEPIE"),
    ("nowa kolekcja", "Bash", WRAPPER,
     g('mutation { collectionCreate(input: {title: "Nowa"}) { collection { id } userErrors { message } } }'), "ask", "collectionCreate"),
    ("definicja metapola", "Bash", WRAPPER,
     g('mutation { metafieldDefinitionCreate(definition: {name: "X", namespace: "custom", key: "x", type: "single_line_text_field", ownerType: PRODUCT}) { userErrors { message } } }'),
     "ask", "metafieldDefinitionCreate"),
    ("cecha produktu", "Bash", WRAPPER_V,
     {"robocze/m.graphql": M_SET, "robocze/v.json": json.dumps({"m": [{"ownerId": P, "namespace": "custom", "key": "powloka", "type": "single_line_text_field", "value": "Ceramiczna"}]})},
     "ask", "metafieldsSet"),

    # usuwanie: pytanie z twardym ostrzezeniem
    ("usuniecie produktu", "Bash", WRAPPER,
     g(f'mutation {{ productDelete(input: {{id: "{P}"}}) {{ deletedProductId }} }}'), "ask", "USUWANIE"),
    ("usuniecie pliku", "Bash", WRAPPER,
     g('mutation { fileDelete(fileIds: ["gid://shopify/MediaImage/3"]) { deletedFileIds } }'), "ask", "USUWANIE"),

    # nadal zakazane
    ("zwrot pieniedzy", "Bash", WRAPPER,
     g('mutation { refundCreate(input: {orderId: "gid://shopify/Order/1"}) { userErrors { message } } }'), "deny", "finansowe"),
    ("ustawienia sklepu", "Bash", WRAPPER,
     g('mutation { shopPolicyUpdate(shopPolicy: {type: REFUND_POLICY, body: "x"}) { userErrors { message } } }'), "deny", "ustawienia sklepu"),
    ("operacja masowa w tle", "Bash", WRAPPER,
     g('mutation { bulkOperationRunMutation(mutation: "x", stagedUploadPath: "y") { userErrors { message } } }'), "deny", "masowe"),
    ("zbyt duza partia", "Bash", WRAPPER_V,
     {"robocze/m.graphql": M_SET, "robocze/v.json": json.dumps({"m": [{"ownerId": f"gid://shopify/Product/{i}", "namespace": "custom", "key": "seria",
                                                                       "type": "single_line_text_field", "value": "x"} for i in range(300)]})},
     "deny", "partie"),
    ("bezposrednio CLI z --allow-mutations", "Bash",
     "shopify store execute -s florina-pl.myshopify.com --allow-mutations -q 'mutation { tagsAdd(id: \"gid://shopify/Product/1\", tags: [\"x\"]) { node { id } } }'",
     {}, "deny", "skryptami"),
    ("wlasny skrypt zmieniajacy sklep", "Bash", "python robocze/moj.py",
     {"robocze/moj.py": "import subprocess\nsubprocess.run(['shopify', 'store', 'execute', '--allow-mutations', '-q', 'mutation { tagsAdd(id: \"x\", tags: []) { node { id } } }'])"},
     "deny", None),
    ("curl do Admin API", "Bash", "curl -X POST https://florina-pl.myshopify.com/admin/api/2026-07/graphql.json -d '{}'", {}, "deny", "Admin API"),
    ("zapis do BaseLinkera", "Bash", "curl -X POST https://api.baselinker.com/connector.php -d 'method=setOrderStatus&parameters={}'", {}, "deny", "BaseLinker"),

    # odczyty i skrypty bez zmian
    ("skrypt porownania Base (tylko odczyt)", "Bash", "python scripts/base_shopify_roznice.py --produkty", {}, None, None),
    ("podglad importu cech", "Bash", "python scripts/cechy.py import robocze/cechy.csv", {}, None, None),
    ("zapis cech", "Bash", "python scripts/cechy.py import robocze/cechy.csv --allow-mutations", {}, "ask", "metafieldsSet"),
    ("upload mediow", "Bash", "python scripts/upload_mediow.py --produkt x --pliki a.jpg --alt y --allow-mutations", {}, "ask", "productCreateMedia"),
    ("skrypt SEO (odczyt strony)", "Bash", "python seo/scripts/parse_html.py robocze/strona.html", {}, None, None),
    ("shopify app deploy", "Bash", "shopify app deploy", {}, "deny", None),
]


def uruchom(narzedzie, komenda, cwd):
    wej = json.dumps({"tool_name": narzedzie, "tool_input": {"command": komenda}, "cwd": cwd, "hook_event_name": "PreToolUse"})
    env = dict(os.environ, CLAUDE_PROJECT_DIR=cwd)
    p = subprocess.run([sys.executable, STRAZNIK], input=wej.encode("utf-8"), capture_output=True, env=env)
    out = p.stdout.decode("utf-8", errors="replace").strip()
    if p.returncode == 2:
        return "deny", p.stderr.decode("utf-8", errors="replace")
    if not out:
        return None, ""
    d = json.loads(out)["hookSpecificOutput"]
    return d["permissionDecision"], d["permissionDecisionReason"]


def main():
    bledy = 0
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "scripts"))
        os.makedirs(os.path.join(tmp, "robocze"))
        for s in ("shopify_gql.py", "cechy.py", "upload_mediow.py", "base_shopify_roznice.py", "szablon_pobierz.py"):
            zrodlo = os.path.join(PROJ, "scripts", s)
            if os.path.isfile(zrodlo):
                with open(zrodlo, encoding="utf-8") as f, open(os.path.join(tmp, "scripts", s), "w", encoding="utf-8") as h:
                    h.write(f.read())
        os.makedirs(os.path.join(tmp, ".claude", "hooks"))
        with open(os.path.join(TU, "polityka_zmian.py"), encoding="utf-8") as f, \
                open(os.path.join(tmp, ".claude", "hooks", "polityka_zmian.py"), "w", encoding="utf-8") as h:
            h.write(f.read())
        for opis, narz, kom, pliki, oczek, fragment in PRZYPADKI:
            for nazwa, tresc in pliki.items():
                with open(os.path.join(tmp, nazwa), "w", encoding="utf-8") as f:
                    f.write(tresc)
            dec, powod = uruchom(narz, kom, tmp)
            ok = dec == oczek and (fragment is None or fragment.lower() in powod.lower())
            bledy += 0 if ok else 1
            print(f"{'OK  ' if ok else 'BLAD'} {opis}: {dec} {('| ' + powod[:120]) if powod else ''}")
    print(f"\nWYNIK ({len(PRZYPADKI)} przypadkow):", "wszystkie testy OK" if not bledy else f"{bledy} bledow")
    sys.exit(1 if bledy else 0)


if __name__ == "__main__":
    main()
