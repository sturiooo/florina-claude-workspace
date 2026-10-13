---
name: dziennik-zmian
description: Prowadzenie dziennika zmian w sklepie Florina i zapisywanie lekcji (co zaskoczyło, co się nie udało, jak naprawdę działa dane pole). Używaj po każdej zakończonej zmianie w sklepie, na koniec sesji, gdy użytkownik pyta „co dziś zmieniliśmy / kiedy zmieniliśmy X”, gdy diagnoza okazała się błędna albo gdy odkryjesz coś o strukturze sklepu, czego nie ma w skillach.
---

# Dziennik zmian i lekcje

Dziennik jest dla użytkownika i dla Igora: ma pozwolić w 2 minuty odpowiedzieć „co, kiedy, dlaczego i jak to cofnąć”.
Klient bywa, że po dwóch tygodniach prosi o odwrotność tego, o co prosił: wtedy dziennik jest dowodem i instrukcją cofnięcia.

## Dziennik zmian: `dziennik/RRRR-MM.md`

Po każdej zakończonej zmianie dopisz na końcu pliku (utwórz plik, jeśli go nie ma):

```markdown
## 2026-10-14 10:35: opisy serii AmVegan (6 produktów)
- Prośba: „nowe opisy dla patelni AmVegan, krótsze, bez lania wody” (użytkownik, 14.10)
- Co zmienione: descriptionHtml + seo (title, description) dla 6 produktów: amvegan-20, amvegan-24, ...
- Backup: backup/2026-10-14/produkt-amvegan-20-103012.json (i 5 kolejnych)
- Weryfikacja: odczyt po zapisie zgodny 6/6; sprawdzone na florina.pl/products/amvegan-24
- Jak cofnąć: przywrócić descriptionHtml i seo z backupu (skill bezpieczna-praca, „Cofanie zmiany”)
- Otwarte sprawy: amvegan-32 bez średnicy w metapolach, do uzupełnienia
```

Zasady:
- zawsze data i godzina, cytat prośby (dosłownie, krótko), liczba obiektów, ścieżka backupu, wynik weryfikacji,
- operacje tylko odczytu (raporty, rozbieżności Base) zapisuj jednym wierszem z ścieżką raportu,
- techniczny log każdej mutacji prowadzi sam skrypt w `dziennik/zmiany.log`, a decyzje strażnika w `dziennik/straznik.log`.
  Dziennik `.md` to wersja dla ludzi, nie kopia logów.

## Lekcje: `dziennik/lekcje.md`

Dopisz lekcję, gdy:
- potwierdziłeś coś, co w skillu było oznaczone **DO POTWIERDZENIA** (np. typ metaobiektu FAQ, magazyn Base),
- Shopify zachował się inaczej, niż zakładał skill (komunikat błędu, opóźnienie, pole, które nadpisuje inne),
- Twoja pierwsza diagnoza okazała się błędna: zapisz, z czego wynikał błąd (np. „patrzyłem na kolekcję automatyczną, a myślałem, że ręczna”),
- użytkownik ustalił regułę stylu lub danych („w polu Powłoka piszemy Non-stick, nie Nieprzywierająca”).

Format:
```markdown
## 2026-10-14: FAQ, struktura
- Fakt: typ metaobiektu FAQ to `...`, pola `...`, lista pytań kolekcji w metapolu `custom....`
- Skąd wiem: odczyt definicji + kolekcja garnki (zapytanie w robocze/faq-struktura.graphql)
- Skutek dla pracy: przy dopisywaniu pytań ...
```

Na początku każdej sesji, w której zmieniasz dane danego rodzaju, przejrzyj `dziennik/lekcje.md` (szukaj po temacie).
Lekcje, które powinny trafić do skilli na stałe, zbiera Igor przy przeglądzie (Claude nie edytuje skilli ani CLAUDE.md).

## Na koniec sesji

Krótkie podsumowanie dla użytkownika: co zrobione, co otwarte, co sprawdzić w sklepie. Te same punkty dopisz w dzienniku.
