### 1. Bandes × ventes (cohorte backtest, V@T−12 mois)
N cohorte = 103 840 · taux de base cohorte = 20.00% (échantillon ENRICHI 1 vendue : 4 non-vendues — lift relatif valide  taux absolus non)
| bande | n | ventes | taux | lift vs base cohorte |
|---|---|---|---|---|
| Brûlantes (chaude ∧ V≥50) | 0 | 0 | 0.00% | — |
| chaudes (V<50) | 272 | 141 | 51.84% | 2.59× |
| V 25-49 | 104 | 40 | 38.46% | 1.92× |
| V 8-24 | 249 | 148 | 59.44% | 2.97× |
| V 1-7 | 11 | 5 | 45.45% | 2.27× |
| V 0 | 4861 | 1147 | 23.60% | 1.18× |
| V n/a (public·bailleur) | 316 | 106 | 33.54% | 1.68× |
| écartées | 98027 | 19181 | 19.57% | 0.98× |

### 2b. DVF — mutations par an en base (dvf_mutations_parcelle, 431 663 parcelles)
| année | mutations (lignes parcelle) | parcelles distinctes |
|---|---|---|
| 2021 | 24 198 | 9 784 |
| 2022 | 23 580 | 9 763 |
| 2023 | 20 999 | 8 681 |
| 2024 | 19 251 | 7 596 |
| 2025 | 14 523 | 7 657 |

BODACC cache : 1418 annonces · 569 SIREN · 2008-02-03 → 2026-07-09

DPE : 914 enregistrements, 914 datés (2021-07-06 → 2026-07-03)

### 3a. Déciles (run q_v3_datagap)
| score | n | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 |
|---|---|---|---|---|---|---|---|---|---|---|
| Q | 431663 | 41.0 | 50.0 | 50.0 | 50.0 | 50.0 | 50.0 | 50.0 | 50.0 | 50.0 |
| A | 431663 | 50.0 | 50.0 | 50.0 | 50.0 | 50.0 | 50.0 | 50.0 | 50.0 | 61.0 |
| V (non-NULL) | 383721 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

### 3b. Corrélations (n triplets complets = 383 721)
| paire | Pearson | Spearman |
|---|---|---|
| Q/A | -0.397 | -0.440 |
| Q/V | 0.003 | 0.003 |
| A/V | 0.084 | 0.040 |

### 3c. owner_type (parcel_v_score  n = 431 663)
| owner_type | n | % |
|---|---|---|
| pp | 349 597 | 81.0% |
| public | 36 463 | 8.4% |
| pm | 33 713 | 7.8% |
| bailleur | 11 479 | 2.7% |
| copro | 411 | 0.1% |

### 3d. Couverture par famille (≥1 signal ; base = 431 663 parcelles scorées)
| famille | parcelles | % |
|---|---|---|
| A | 2 335 | 0.5% |
| B | 10 559 | 2.4% |
| C | 9 856 | 2.3% |
| D | 16 895 | 3.9% |
| E | 27 | 0.0% |

SIREN PM distincts : 12605 · matchés BODACC : 564 (4.5%) · fiche RNE/recherche-entreprises : 9582 (76.0%)

### 4a. Taux de base annuel (parcelles mutées / 431 663)
| année | parcelles mutées (toutes natures) | taux | dont Vente | taux Vente |
|---|---|---|---|---|
| 2021 | 9784 | 2.27% | 9290 | 2.15% |
| 2022 | 9763 | 2.26% | 9218 | 2.14% |
| 2023 | 8681 | 2.01% | 8138 | 1.89% |
| 2024 | 7596 | 1.76% | 7205 | 1.67% |
| 2025 | 7657 | 1.77% | 7403 | 1.71% |

### 4b. Fenêtre 2023-2025 par statut matrice (taux 3 ans ; annualisé = /3)
| statut | n | mutées (toutes) | taux 3 ans | vendues (Vente) | taux Vente 3 ans | Vente annualisé |
|---|---|---|---|---|---|---|
| ecartee | 409 036 | 20039 | 4.90% | 19181 | 4.69% | 1.56% |
| a_creuser | 15 580 | 1116 | 7.16% | 1010 | 6.48% | 2.16% |
| a_surveiller | 5 889 | 224 | 3.80% | 211 | 3.58% | 1.19% |
| chaude | 1 158 | 178 | 15.37% | 164 | 14.16% | 4.72% |

### 5. Transition q_v2 → q_v3_datagap (lignes = avant, colonnes = après)
| avant \ après | chaude | a_surveiller | a_creuser | ecartee | total avant |
|---|---|---|---|---|---|
| chaude | 654 | 202 | 221 | 6 | 1 083 |
| a_surveiller | 381 | 4 959 | 1 225 | 5 | 6 570 |
| a_creuser | 110 | 642 | 12 522 | 2 729 | 16 003 |
| ecartee | 13 | 86 | 1 612 | 406 296 | 408 007 |

### 6. Sonde ecartee : 4248 parcelles (4445 rattachements permis autorisés < 24 mois)
| idu | commune | motif d'écartement | date permis | type |
|---|---|---|---|---|
| 97412000CY0369 | Saint-Joseph | Zone A PLU — inconstructible (recouvrement 100 %). | 2026-08-17 | DP |
| 97412000BL1049 | Saint-Joseph | Exclue : PPR zone rouge (inconstructible). | 2026-05-30 | DP |
| 97417000AX0318 | Saint-Philippe | Exclue : forêt domaniale (domaine public — terrain inacquérable). | 2026-05-29 | PC |
| 97414000DE0293 | Saint-Louis | ensemble bâti : 4 bâtiments couvrant 23 % de la parcelle (BD TOPO) | 2026-05-29 | PC |
| 97414000CT1471 | Saint-Louis | ensemble bâti : 4 bâtiments couvrant 18 % de la parcelle (BD TOPO) | 2026-05-29 | PC |
| 97414000HA0485 | Saint-Louis | déjà bâtie : 2 bâtiment(s) couvrant 61 % de la parcelle (BD TOPO) | 2026-05-29 | PC |
| 97422000AR0282 | Le Tampon | aucune exclusion dure — qualité insuffisante (Q 38) | 2026-05-29 | PC |
| 97414000CO1128 | Saint-Louis | Exclue : PPR zone rouge (inconstructible). | 2026-05-29 | PC |
| 97414000ES1030 | Saint-Louis | aucune exclusion dure — qualité insuffisante (Q 31) | 2026-05-29 | PC |
| 97414000DE1193 | Saint-Louis | déjà bâtie probable : 39 % de la surface intersecte 2 bâtiment(s) (BD  | 2026-05-29 | PD |
| 97414000DE1194 | Saint-Louis | déjà bâtie probable : 39 % de la surface intersecte 11 bâtiment(s) (BD | 2026-05-29 | PD |
| 97414000ES0005 | Saint-Louis | déjà bâtie probable : 35 % de la surface intersecte 2 bâtiment(s) (BD  | 2026-05-29 | DP |
| 97402000AB0090 | Bras-Panon | Exclue : PPR zone rouge (inconstructible). | 2026-05-29 | DP |
| 97414000EN3337 | Saint-Louis | aucune exclusion dure — qualité insuffisante (Q 44) | 2026-05-28 | PC |
| 97407000AS0998 | Le Port | Emplacement réservé 26 : Projet de transport en commun en site propre  | 2026-05-28 | PC |
| 97407000BC0491 | Le Port | Emplacement réservé 26 : Projet de transport en commun en site propre  | 2026-05-28 | PC |
| 97407000AS1243 | Le Port | Emplacement réservé 26 : Projet de transport en commun en site propre  | 2026-05-28 | PC |
| 97414000CW0609 | Saint-Louis | aucune exclusion dure — qualité insuffisante (Q 40) | 2026-05-28 | PC |
| 97407000AH0932 | Le Port | déjà bâtie : 3 bâtiment(s) couvrant 69 % de la parcelle (BD TOPO) | 2026-05-28 | PC |
| 97422000BM0340 | Le Tampon | aucune exclusion dure — qualité insuffisante (Q 40) | 2026-05-28 | PC |

### 6. Sonde a_creuser : 529 parcelles (555 rattachements permis autorisés < 24 mois)
### 7. Traces d'usage en base
consultation_log : 608 lignes · 2026-07-11 → 2026-07-12 · 1 sujets distincts · top : [('ip:12ca17b49af2289436f3', 608)]
pipeline_entries (CRM) : [(4,)]
projets : [(6,)]
usage_compteurs (par kind) : [('fiche', 301), ('export', 29), ('nl', 11), ('dossier', 6)]
ia_log (stub vs réel) : [(False, 763), (True, 154)]
nl_query_log : [('traduit', 8), ('out_of_scope', 3)]

CSV → reports/extraction-ml

## Précisions (probes complémentaires)
- V non-NULL : 363 710 à ZÉRO (94,8 %), 20 011 > 0 · P95 = 4 · P99 = 30 · max = 81.
- Q : 354 360 exactement à 50 (82,1 %) · 20 863 > 50 · 56 440 < 50.
- Sonde écartées par état permis : 3 002 « autorisé » · 90 « commencé » · 1 237 « terminé » (les annulés — état 6, 335 parcelles — sont EXCLUS de la sonde).
- Usage : consultation_log = 608 lignes / 1 SEUL sujet (hash IP local) / 11-12 juillet = trafic d'audit-QA ; aucun usage tiers tracé.
