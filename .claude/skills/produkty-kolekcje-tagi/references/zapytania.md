# Zapytania: produkty, kolekcje, tagi

Zwalidowane względem schematu Admin API 2026-07. Zapisuj je do `robocze/*.graphql`, zmienne do `robocze/*.json`
i uruchamiaj przez `python scripts/shopify_gql.py --query-file ... --variable-file ...`
(dla zmian dodatkowo `--allow-mutations`, po zgodzie i backupie).

## Wyszukiwanie produktów (wszystkie strony)

```graphql
query Szukaj($q: String, $after: String) {
  products(first: 100, after: $after, query: $q) {
    pageInfo { hasNextPage endCursor }
    nodes { id handle title status tags }
  }
}
```
Zmienne: `{"q": "tag:GARNKI status:active"}`. Uruchom z `--wszystkie products --out robocze/wyniki.json`.

## Kolekcja: rodzaj i liczba produktów

```graphql
query Kolekcja($h: String!) {
  collectionByIdentifier(identifier: { handle: $h }) {
    id title handle
    productsCount { count }
    ruleSet { appliedDisjunctively rules { column relation condition } }
  }
}
```
`ruleSet: null` = kolekcja ręczna. (Pole `ruleSet` jest oznaczone jako przestarzałe, ale działa.)

## Czy produkt jest w kolekcji

```graphql
query CzyWKolekcji($p: ID!, $c: ID!) { product(id: $p) { handle inCollection(id: $c) } }
```

## Dodanie produktów do kolekcji ręcznej (zmiana)

```graphql
mutation Dodaj($id: ID!, $productIds: [ID!]!) {
  collectionAddProducts(id: $id, productIds: $productIds) {
    collection { id productsCount { count } }
    userErrors { field message }
  }
}
```
Zmienne: `{"id": "gid://shopify/Collection/...", "productIds": ["gid://shopify/Product/...", "..."]}` (do 20 na raz).

## Usunięcie z kolekcji ręcznej (tylko cofnięcie pomyłki)

```graphql
mutation Usun($id: ID!, $productIds: [ID!]!) {
  collectionRemoveProducts(id: $id, productIds: $productIds) {
    job { id done }
    userErrors { field message }
  }
}
```

## Tagi (zmiana)

```graphql
mutation Tag($id: ID!, $tags: [String!]!) {
  tagsAdd(id: $id, tags: $tags) { node { id } userErrors { field message } }
}
```
```graphql
mutation Untag($id: ID!, $tags: [String!]!) {
  tagsRemove(id: $id, tags: $tags) { node { id } userErrors { field message } }
}
```
Kilka produktów w jednej mutacji (aliasy):
```graphql
mutation {
  p1: tagsAdd(id: "gid://shopify/Product/1", tags: ["GARNKI"]) { userErrors { message } }
  p2: tagsAdd(id: "gid://shopify/Product/2", tags: ["GARNKI"]) { userErrors { message } }
}
```

## Lista tagów w sklepie

```graphql
{ productTags(first: 250) { nodes } }
```
