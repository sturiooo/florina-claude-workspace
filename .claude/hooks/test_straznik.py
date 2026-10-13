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
PRZYPADKI = [
    # (opis, narzedzie, komenda, pliki {nazwa: tresc}, oczekiwana decyzja: deny / ask / None)
    ("odczyt przez wrapper", "Bash", 'python scripts/shopify_gql.py -q "{ shop { name } }"', {}, None),
    ("odczyt w PowerShell", "PowerShell", 'python scripts\\shopify_gql.py -q "{ shop { name } }"', {}, None),
    ("zwykla komenda", "Bash", "git status", {}, None),
    ("czytanie pliku z nazwami mutacji to nie zmiana", "Bash", "cat .claude/hooks/polityka_zmian.py", {}, None),
    ("theme push", "Bash", "shopify theme push --theme 123", {}, "deny"),
    ("theme publish w PowerShell", "PowerShell", "shopify theme publish --theme 1", {}, "deny"),
    ("theme pull jest dozwolony (nie zmienia sklepu)", "Bash", "shopify theme pull --theme 1", {}, None),
    ("productDelete", "Bash", f'python scripts/shopify_gql.py --allow-mutations -q "mutation {{ productDelete(input: {{id: \\"{P}\\"}}) {{ deletedProductId }} }}"', {}, "deny"),
    ("opis produktu wymaga zgody", "Bash", "python scripts/shopify_gql.py --query-file robocze/m.graphql --variable-file robocze/v.json --allow-mutations",
     {"robocze/m.graphql": "mutation U($p: ProductUpdateInput!) { productUpdate(product: $p) { product { id status handle } userErrors { message } } }",
      "robocze/v.json": json.dumps({"p": {"id": P, "descriptionHtml": "<p>x</p>"}})}, "ask"),
    ("zmiana statusu produktu", "Bash", "python scripts/shopify_gql.py --query-file robocze/m.graphql --variable-file robocze/v.json --allow-mutations",
     {"robocze/m.graphql": "mutation U($p: ProductUpdateInput!) { productUpdate(product: $p) { product { id } } }",
      "robocze/v.json": json.dumps({"p": {"id": P, "status": "ARCHIVED"}})}, "deny"),
    ("zmiana uchwytu kolekcji", "Bash", "python scripts/shopify_gql.py --query-file robocze/m.graphql --allow-mutations",
     {"robocze/m.graphql": 'mutation { collectionUpdate(input: {id: "gid://shopify/Collection/5", handle: "nowy"}) { collection { id } } }'}, "deny"),
    ("tag na zamowieniu", "Bash", "python scripts/shopify_gql.py --query-file robocze/m.graphql --allow-mutations",
     {"robocze/m.graphql": 'mutation { tagsAdd(id: "gid://shopify/Order/9", tags: ["x"]) { userErrors { message } } }'}, "deny"),
    ("tag na produkcie", "Bash", "python scripts/shopify_gql.py --query-file robocze/m.graphql --allow-mutations",
     {"robocze/m.graphql": f'mutation {{ tagsAdd(id: "{P}", tags: ["GARNKI"]) {{ userErrors {{ message }} }} }}'}, "ask"),
    ("alias nie ukryje zakazanej mutacji", "Bash", "python scripts/shopify_gql.py --query-file robocze/m.graphql --allow-mutations",
     {"robocze/m.graphql": 'mutation { a: tagsAdd(id: "gid://shopify/Product/1", tags: ["x"]) { node { id } } b: discountCodeBasicCreate(basicCodeDiscount: {}) { userErrors { message } } }'}, "deny"),
    ("ceny wariantow", "Bash", "python scripts/shopify_gql.py --query-file robocze/m.graphql --allow-mutations",
     {"robocze/m.graphql": 'mutation { productVariantsBulkUpdate(productId: "gid://shopify/Product/1", variants: [{id: "gid://shopify/ProductVariant/2", price: "1.00"}]) { userErrors { message } } }'}, "deny"),
    ("nieznana mutacja", "Bash", "python scripts/shopify_gql.py --query-file robocze/m.graphql --allow-mutations",
     {"robocze/m.graphql": "mutation { cosNowego(x: 1) { id } }"}, "deny"),
    ("zbyt duza partia", "Bash", "python scripts/shopify_gql.py --query-file robocze/m.graphql --variable-file robocze/v.json --allow-mutations",
     {"robocze/m.graphql": "mutation M($m: [MetafieldsSetInput!]!) { metafieldsSet(metafields: $m) { userErrors { message } } }",
      "robocze/v.json": json.dumps({"m": [{"ownerId": f"gid://shopify/Product/{i}", "namespace": "custom", "key": "seria", "type": "single_line_text_field", "value": "x"} for i in range(70)]})}, "deny"),
    ("metapole aplikacji opinii", "Bash", "python scripts/shopify_gql.py --query-file robocze/m.graphql --variable-file robocze/v.json --allow-mutations",
     {"robocze/m.graphql": "mutation M($m: [MetafieldsSetInput!]!) { metafieldsSet(metafields: $m) { userErrors { message } } }",
      "robocze/v.json": json.dumps({"m": [{"ownerId": P, "namespace": "reviews", "key": "rating", "type": "rating", "value": "5"}]})}, "deny"),
    ("cecha produktu wymaga zgody", "Bash", "python scripts/shopify_gql.py --query-file robocze/m.graphql --variable-file robocze/v.json --allow-mutations",
     {"robocze/m.graphql": "mutation M($m: [MetafieldsSetInput!]!) { metafieldsSet(metafields: $m) { userErrors { message } } }",
      "robocze/v.json": json.dumps({"m": [{"ownerId": P, "namespace": "custom", "key": "powloka", "type": "single_line_text_field", "value": "Ceramiczna"}]})}, "ask"),
    ("bezposrednio CLI z --allow-mutations", "Bash", "shopify store execute -s florina-pl.myshopify.com --allow-mutations -q 'mutation { tagsAdd(id: \"gid://shopify/Product/1\", tags: [\"x\"]) { node { id } } }'", {}, "deny"),
    ("wlasny skrypt zmieniajacy sklep", "Bash", "python robocze/moj.py",
     {"robocze/moj.py": "import subprocess\nsubprocess.run(['shopify','store','execute','--allow-mutations','-q','mutation { tagsAdd(id: \"gid://shopify/Product/1\", tags: [\"x\"]) { node { id } } }'])"}, "deny"),
    ("curl do Admin API", "Bash", "curl -X POST https://florina-pl.myshopify.com/admin/api/2026-07/graphql.json -d '{}'", {}, "deny"),
    ("zapis do BaseLinkera", "Bash", "curl -X POST https://api.baselinker.com/connector.php -d 'method=setOrderStatus&parameters={}'", {}, "deny"),
    ("skrypt porownania Base (tylko odczyt)", "Bash", "python scripts/base_shopify_roznice.py --produkty", {}, None),
    ("podglad importu cech", "Bash", "python scripts/cechy.py import robocze/cechy.csv", {}, None),
    ("zapis cech wymaga zgody", "Bash", "python scripts/cechy.py import robocze/cechy.csv --allow-mutations", {}, "ask"),
    ("upload mediow wymaga zgody", "Bash", "python scripts/upload_mediow.py --produkt x --pliki a.jpg --alt y --allow-mutations", {}, "ask"),
    ("shopify app deploy", "Bash", "shopify app deploy", {}, "deny"),
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
        for s in ("shopify_gql.py", "cechy.py", "upload_mediow.py", "base_shopify_roznice.py"):
            zrodlo = os.path.join(PROJ, "scripts", s)
            if os.path.isfile(zrodlo):
                with open(zrodlo, encoding="utf-8") as f, open(os.path.join(tmp, "scripts", s), "w", encoding="utf-8") as g:
                    g.write(f.read())
        os.makedirs(os.path.join(tmp, ".claude", "hooks"))
        with open(os.path.join(TU, "polityka_zmian.py"), encoding="utf-8") as f, \
                open(os.path.join(tmp, ".claude", "hooks", "polityka_zmian.py"), "w", encoding="utf-8") as g:
            g.write(f.read())
        for opis, narz, kom, pliki, oczek in PRZYPADKI:
            for nazwa, tresc in pliki.items():
                with open(os.path.join(tmp, nazwa), "w", encoding="utf-8") as f:
                    f.write(tresc)
            dec, powod = uruchom(narz, kom, tmp)
            ok = dec == oczek
            bledy += 0 if ok else 1
            print(f"{'OK  ' if ok else 'BLAD'} {opis}: {dec} {('| ' + powod[:110]) if powod else ''}")
    print("\nWYNIK:", "wszystkie testy OK" if not bledy else f"{bledy} bledow")
    sys.exit(1 if bledy else 0)


if __name__ == "__main__":
    main()
