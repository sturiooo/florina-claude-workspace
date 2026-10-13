# Florina: Claude Code workspace

Paczka do pracy w sklepie **florina-pl.myshopify.com** przez Claude Code w VS Code, dla osoby nietechnicznej.
Claude prowadzi ją przez powtarzalne zadania, a zabezpieczenia pilnują, żeby nie dało się zrobić nic poza zakresem.

Instalacja: **[INSTALACJA.md](INSTALACJA.md)** (`install.ps1` robi większość).

## Co osoba obsługująca sklep może zlecić Claude

| Zadanie | Skill |
|---|---|
| Dodawanie produktów do kolekcji, tagowanie | `produkty-kolekcje-tagi` |
| Opisy produktów i kategorii, meta tytuły i opisy | `opisy-produktow-i-kategorii` |
| FAQ kategorii i produktów | `faq-produkty-kategorie` |
| Ocechowanie (metapola, cechy do filtrów), też przez arkusz Excel | `ocechowanie-metapola` |
| Zdjęcia i wideo na karcie produktu, teksty alternatywne | `media-produktu` |
| Rozbieżności BaseLinker i Shopify (stany, ceny, produkty, zamówienia), tylko odczyt | `baselinker-rozbieznosci` |
| Checklista przed zmianą, cofanie zmian | `bezpieczna-praca` |
| Gdzie w sklepie zapisane są dane | `struktura-sklepu` |
| Dziennik zmian i lekcje | `dziennik-zmian` |

Rytm każdej zmiany (wymuszony w `CLAUDE.md` i częściowo technicznie): plan, podgląd „przed / po”, zgoda,
backup do `backup/RRRR-MM-DD/`, próba na 1 obiekcie, partie, weryfikacja odczytem, wpis w dzienniku.

## Zabezpieczenia (cztery warstwy)

1. **Konto pracownika w Shopify z ograniczonymi uprawnieniami** + token CLI z minimalnymi scope'ami (INSTALACJA, kroki 5 i 6). Twarda granica po stronie Shopify.
2. **`.claude/settings.json`** (reguły Claude Code):
   - **blokada**: `rm -rf` i podobne, `del /s`, `rd /s`, `format`, `git push --force`, `git reset --hard`, `git clean`,
     `shopify theme push/publish/delete/rename/share/dev/duplicate`, `shopify app ...`, `shopify auth logout`, odczyt `.env`,
     edycja `.claude/`, `scripts/`, `CLAUDE.md`, `install.ps1` i plików systemowych, konektor Shopify w claude.ai (`mcp__claude_ai_Shopify`),
     tryby bez pytania (`bypassPermissions`, `auto`) wyłączone;
   - **pytanie o zgodę**: każda komenda z `--allow-mutations` (zmiana w sklepie), `shopify store auth`, `shopify theme pull`, `git commit/push/add`, `pip`, `npm`, `winget`, `rm`, `mv`, `Remove-Item`, `Set-Content`, zapis plików poza katalogami roboczymi (także poza projektem);
   - **bez pytania**: odczyty (Read, Grep), skrypty z `scripts/` bez `--allow-mutations`, `shopify store execute` (CLI bez flagi odrzuca mutacje), zapis w `backup/`, `raporty/`, `robocze/`, `dziennik/`.
3. **Hook `.claude/hooks/straznik.py`** (PreToolUse dla Bash i PowerShell, przy awarii blokuje):
   - mutacje GraphQL: **lista dozwolonych** (`productUpdate`, `tagsAdd/Remove`, `collectionAddProducts(V2)/RemoveProducts/ReorderProducts/Update`,
     `metafieldsSet`, `metaobjectCreate/Update`, `stagedUploadsCreate`, `fileCreate/Update`, `productCreateMedia/UpdateMedia/ReorderMedia`,
     `productVariantAppendMedia`, `translationsRegister`) wymaga potwierdzenia z opisem zmiany; **każda inna jest blokowana**
     (w tym `*Delete`, `productCreate/Set/Duplicate`, `productVariant*`, `inventory*`, `priceList*`, `discount*`, `theme*`, `order*`,
     `refund*`, `fulfillment*`, `customer*`, `publishable*`, `bulkOperation*`, `metafieldDefinition*`, `metaobjectDefinition*`, `collectionCreate`, `urlRedirect*`, `menu*`);
   - zakazane pola w dozwolonych mutacjach: `productUpdate` bez `status`, `handle`, `category` (VAT), `templateSuffix`, `variants`;
     `collectionUpdate` bez `handle`, `ruleSet`, `sources`, `templateSuffix`;
   - zmiany tylko na produktach, wariantach, kolekcjach, metaobiektach i mediach (gid zamówień, klientów itd. = blokada);
   - metapola aplikacji (`reviews`, `judgeme`, `mm-google-shopping`, `shopify--discovery`) zablokowane;
   - maks. 60 obiektów w jednej zmianie;
   - zmiany w sklepie tylko przez `scripts/shopify_gql.py`, `scripts/cechy.py`, `scripts/upload_mediow.py` (własne skrypty Claude i bezpośrednie `curl` do Admin API = blokada);
   - BaseLinker: każda metoda zapisująca (`add*`, `set*`, `update*`, `delete*`...) zablokowana.
4. **`scripts/shopify_gql.py`** w chwili wysyłki: ponowna kontrola tej samej polityki, **wymóg dzisiejszego backupu** każdego zmienianego produktu,
   kolekcji i wpisu FAQ, log każdej zmiany w `dziennik/zmiany.log`, wersja API przypięta (2026-07, CLI domyślnie bierze `unstable`).

Test zabezpieczeń: `python .claude/hooks/test_straznik.py` (28 przypadków, uruchamia go też instalator).

Ograniczenia, o których trzeba wiedzieć: reguły Claude Code i hook dopasowują tekst komend, więc to nie jest granica bezpieczeństwa
w sensie informatycznym (zdeterminowany człowiek obejdzie je, pisząc komendę sam). Prawdziwą granicą jest warstwa 1: konto i scope'y.

## Struktura

```
CLAUDE.md                     zasady dla Claude (po polsku, dla początkującego użytkownika)
INSTALACJA.md / install.ps1   instalacja krok po kroku / instalator Windows
.env.example                  szablon (SHOPIFY_STORE, SHOPIFY_API_VERSION, BASELINKER_TOKEN)
.claude/settings.json         uprawnienia + hook
.claude/hooks/                straznik.py, polityka_zmian.py (listy), test_straznik.py
.claude/skills/               9 skilli
scripts/                      shopify_gql.py, backup_produktu.py, struktura_sklepu.py, cechy.py,
                              upload_mediow.py, base_shopify_roznice.py, wspolne.py (tylko biblioteka standardowa Pythona)
backup/ raporty/ robocze/ dziennik/ docs/   dane lokalne (poza repozytorium)
```

Skrypty nie wymagają żadnych bibliotek spoza standardowej biblioteki Pythona 3.10+ (stąd brak `requirements.txt`).

## Dla Igora: zmiany w paczce

- Lista dozwolonych mutacji i zakazanych pól: `.claude/hooks/polityka_zmian.py` (po zmianie: `python .claude/hooks/test_straznik.py`).
- Lekcje zebrane przez Claude u klienta: `dziennik/lekcje.md` na komputerze klienta; stałe przenoś do skilli.
- Punkty **DO POTWIERDZENIA** w skillach (grep po tej frazie) uzupełnij po pierwszej sesji na sklepie.
