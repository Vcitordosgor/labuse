# TAXE-INGEST-EXPORT — ingestion réelle des secteurs à taux majoré

**Bug corrigé** : `ingest-taxe-amenagement` plantait en **HTTP 400 à offset=10 000** — l'API Opendatasoft v2.1 `/records` plafonne la pagination à 10 000 lignes, or les secteurs 974 au grain parcelle font ~11 636 lignes. **Fix** : les secteurs passent désormais par **`/exports/json`** (même `where`), qui renvoie tout le jeu filtré en un seul tableau JSON, sans pagination (`_fetch_export`). Le communal (24) et le départemental (1) restent sur `/records` (jeux courts).

## Ingestion réelle (local, dev DB, DELTA live — 24/09/2026)

```
taux communaux généraux : 24  (0 commune manquante)
secteurs (parcelles)    : 10 465  en vigueur, dédupliqués, taux ∈ [0;20]
sentinelles 99 % écartées : 1 171          (10 465 + 1 171 = 11 636 lignes brutes ✓)
```

### Nombre de parcelles par commune (secteurs à taux majoré)

| INSEE | Commune | Parcelles | Taux |
|---|---|---|---|
| 97401 | Les Avirons | 183 | 10 % |
| 97403 | Entre-Deux | 108 | 8,5 % |
| 97407 | Le Port | 914 | 5 – 20 % |
| 97413 | Saint-Leu | 8 343 | 14 % |
| 97415 | Saint-Paul | 649 | 10 % |
| 97423 | Les Trois-Bassins | 268 | 20 % |
| **Total** | **6 communes** | **10 465** | |

## Vérifications demandées

```
97415000CT2268 : 10,0 %  secteur_majore=True     ✓ (secteur à taux majoré Saint-Paul)
97415000CO0322 :  5,0 %  secteur_majore=False    ✓ (hors secteur → taux général Saint-Paul 5 %)
Saint-Paul (97415) taux général : 5,0 %
```

CT2268 prend bien le taux du secteur (10 %) ; CO0322 (la parcelle témoin de l'audit) n'est dans aucun secteur et garde le taux communal général (5 %) — le total 23 415 € de TAXE-AUDIT-1 reste juste.

Test neuf : `test_fetch_export_lit_un_tableau_direct_sans_pagination` (un seul appel, endpoint `exports/json`, pas d'offset).
