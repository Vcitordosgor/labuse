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
| ESTIMATED | 151223 | 34.9 % |
| TO_VERIFY | 72314 | 16.7 % |
| DEFERRED | 320 | 0.1 % |
| NO_MARGIN | 64880 | 15.0 % |
| OUTSIDE_OBJECTIVE | 144492 | 33.4 % |

### Statuts V2 — reconstruction
| clé | n | part |
|---|---:|---:|
| ESTIMATED | 2562 | 0.6 % |
| COMPUTE_PENDING | 211759 | 48.9 % |
| TO_VERIFY | 74096 | 17.1 % |
| DEFERRED | 320 | 0.1 % |
| OUTSIDE_OBJECTIVE | 144492 | 33.4 % |

### Bandes V2 — conservation (parcelles « Capacité estimée » seulement)
| clé | n | part |
|---|---:|---:|
| A | 6858 | 4.5 % |
| B | 43122 | 28.5 % |
| C | 52832 | 34.9 % |
| D | 48411 | 32.0 % |

## Matrice complète bande V1 × V2 (conservation)

### bande V1 × STATUT V2
| V1 ↓ / V2 → | ESTIMATED | PRESTUDY | COMPUTE_PENDING | TO_VERIFY | DEFERRED | NO_MARGIN | OUTSIDE_OBJECTIVE | (total) |
|---|---|---|---|---|---|---|---|---|
| A | 3540 | 0 | 0 | 2626 | 0 | 0 | 0 | 6166 |
| B | 25574 | 0 | 0 | 10657 | 23 | 0 | 0 | 36254 |
| C | 39223 | 0 | 0 | 11520 | 170 | 0 | 0 | 50913 |
| D | 82884 | 0 | 0 | 16019 | 104 | 4 | 0 | 99011 |
| 0 | 2 | 0 | 0 | 26476 | 23 | 64876 | 126577 | 217954 |
| NC | 0 | 0 | 0 | 5016 | 0 | 0 | 11256 | 16272 |
| HC | 0 | 0 | 0 | 0 | 0 | 0 | 6659 | 6659 |

### bande V1 × BANDE V2 (y compris les changements entre deux bandes estimées)
| V1 ↓ / V2 → | A | B | C | D | — | (total) |
|---|---|---|---|---|---|---|
| A | 3540 | 0 | 0 | 0 | 2626 | 6166 |
| B | 3318 | 22254 | 2 | 0 | 10680 | 36254 |
| C | 0 | 20868 | 18355 | 0 | 11690 | 50913 |
| D | 0 | 0 | 34475 | 48409 | 16127 | 99011 |
| 0 | 0 | 0 | 0 | 2 | 217952 | 217954 |
| NC | 0 | 0 | 0 | 0 | 16272 | 16272 |
| HC | 0 | 0 | 0 | 0 | 6659 | 6659 |

## Cohortes nommées (où vont les anciennes bandes)

- **Anciennes « A » (6166)** → ESTIMATED/A 3540, TO_VERIFY 2626
- **Anciennes « B » (36254)** → ESTIMATED/B 22254, TO_VERIFY 10657, ESTIMATED/A 3318, DEFERRED 23, ESTIMATED/C 2
- **Anciennes « C » (50913)** → ESTIMATED/B 20868, ESTIMATED/C 18355, TO_VERIFY 11520, DEFERRED 170
- **Anciennes « D » (99011)** → ESTIMATED/D 48409, ESTIMATED/C 34475, TO_VERIFY 16019, DEFERRED 104, NO_MARGIN 4
- **Anciennes « 0 » (217954)** → OUTSIDE_OBJECTIVE 126577, NO_MARGIN 64876, TO_VERIFY 26476, DEFERRED 23, ESTIMATED/D 2
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
