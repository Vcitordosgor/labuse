# ALGO-FIX-1 — BILAN avant/après, un seul instantané (run servi q_v20)

Statuts/bandes V2 lus de la table de run `parcel_scenario_v2_runs` ; décomposition lue
des caches de Score. Conservation = analogue direct de la note V1. Reconstruction : les
capacités non chiffrées sont « Calcul à compléter » (jamais « Capacité estimée » déduite).

## Île entière — 433229 parcelles

### Bandes V1 (servies)
| clé | n | part |
|---|---:|---:|
| A | 6166 | 1.4 % |
| B | 36254 | 8.4 % |
| C | 50913 | 11.8 % |
| D | 99011 | 22.9 % |
| 0 | 217954 | 50.3 % |
| NC | 16272 | 3.8 % |
| HC | 6659 | 1.5 % |

### Statuts V2 — conservation
| clé | n | part |
|---|---:|---:|
| ESTIMATED | 151451 | 35.0 % |
| TO_VERIFY | 72046 | 16.6 % |
| DEFERRED | 320 | 0.1 % |
| NO_MARGIN | 64920 | 15.0 % |
| OUTSIDE_OBJECTIVE | 144492 | 33.4 % |

### Statuts V2 — reconstruction
| clé | n | part |
|---|---:|---:|
| ESTIMATED | 4342 | 1.0 % |
| COMPUTE_PENDING | 212024 | 48.9 % |
| TO_VERIFY | 72051 | 16.6 % |
| DEFERRED | 320 | 0.1 % |
| OUTSIDE_OBJECTIVE | 144492 | 33.4 % |

### Bandes V2 — conservation (parcelles « Capacité estimée » seulement)
| clé | n | part |
|---|---:|---:|
| A | 6905 | 4.6 % |
| B | 43204 | 28.5 % |
| C | 52898 | 34.9 % |
| D | 48444 | 32.0 % |

## Matrice complète bande V1 × V2 (conservation)

### bande V1 × STATUT V2
| V1 ↓ / V2 → | ESTIMATED | PRESTUDY | COMPUTE_PENDING | TO_VERIFY | DEFERRED | NO_MARGIN | OUTSIDE_OBJECTIVE | (total) |
|---|---|---|---|---|---|---|---|---|
| A | 3579 | 0 | 0 | 2587 | 0 | 0 | 0 | 6166 |
| B | 25649 | 0 | 0 | 10582 | 23 | 0 | 0 | 36254 |
| C | 39289 | 0 | 0 | 11454 | 170 | 0 | 0 | 50913 |
| D | 82934 | 0 | 0 | 15969 | 104 | 4 | 0 | 99011 |
| 0 | 0 | 0 | 0 | 26438 | 23 | 64916 | 126577 | 217954 |
| NC | 0 | 0 | 0 | 5016 | 0 | 0 | 11256 | 16272 |
| HC | 0 | 0 | 0 | 0 | 0 | 0 | 6659 | 6659 |

### bande V1 × BANDE V2 (y compris les changements entre deux bandes estimées)
| V1 ↓ / V2 → | A | B | C | D | — | (total) |
|---|---|---|---|---|---|---|
| A | 3579 | 0 | 0 | 0 | 2587 | 6166 |
| B | 3326 | 22321 | 2 | 0 | 10605 | 36254 |
| C | 0 | 20883 | 18406 | 0 | 11624 | 50913 |
| D | 0 | 0 | 34490 | 48444 | 16077 | 99011 |
| 0 | 0 | 0 | 0 | 0 | 217954 | 217954 |
| NC | 0 | 0 | 0 | 0 | 16272 | 16272 |
| HC | 0 | 0 | 0 | 0 | 6659 | 6659 |

## Cohortes nommées (où vont les anciennes bandes)

- **Anciennes « A » (6166)** → ESTIMATED/A 3579, TO_VERIFY 2587
- **Anciennes « B » (36254)** → ESTIMATED/B 22321, TO_VERIFY 10582, ESTIMATED/A 3326, DEFERRED 23, ESTIMATED/C 2
- **Anciennes « C » (50913)** → ESTIMATED/B 20883, ESTIMATED/C 18406, TO_VERIFY 11454, DEFERRED 170
- **Anciennes « D » (99011)** → ESTIMATED/D 48444, ESTIMATED/C 34490, TO_VERIFY 15969, DEFERRED 104, NO_MARGIN 4
- **Anciennes « 0 » (217954)** → OUTSIDE_OBJECTIVE 126577, NO_MARGIN 64916, TO_VERIFY 26438, DEFERRED 23
- **Anciennes « NC » (16272)** → OUTSIDE_OBJECTIVE 11256, TO_VERIFY 5016
- **Anciennes « HC » (6659)** → OUTSIDE_OBJECTIVE 6659

## Décomposition à ENTRÉES CONSTANTES (même R, pente, forme, accès)

Sur **416957** parcelles calculables. Isole les coefficients du recalcul de capacité (ici R est tenu CONSTANT = R servi).

**Invariant retrait bâti** : parcelles dont le score BAISSE en retirant le seul coefficient bâti = **0** (doit être 0 ; f_bâti ≤ 1).

### Changements de bande dus au SEUL retrait du coefficient bâti
| clé | n | part |
|---|---:|---:|
| B→A | 5529 | 7.3 % |
| C→B | 27828 | 36.8 % |
| D→C | 42166 | 55.8 % |

### Changements de bande dus au SEUL retrait du ×0,5 AU (après bâti)
| clé | n | part |
|---|---:|---:|
| B→A | 108 | 16.4 % |
| C→A | 125 | 18.9 % |
| C→B | 226 | 34.2 % |
| D→B | 86 | 13.0 % |
| D→C | 115 | 17.4 % |

> Le reste des mouvements de bande V1→V2 (hors ces deux colonnes) vient du RECALCUL des capacités (R servi vs R recalculé) et des changements de statut — distincts de l'effet des coefficients.
