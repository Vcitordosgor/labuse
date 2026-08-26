# GRAND BALAYAGE — CYCLE 6 · RAPPORT · LES ~1450 (certification finale)

> AUDIT SEUL. Findings GB-041→. Front :5174/socle/, back :8000 (uvicorn SANS dev_mode : rate-limit 60/min, quota fiches 300/j, Copilote 10/j HTTP — cadence imposée aux agents, patron cycle 5). Base labuse, lecture stricte hors [GB-TEST] + labuse_c6_test/:8001 (LOTS AJ/AK, dérogation mandat).
> Barème : 🔴 bloquant / faux chiffre / fuite / régression GB-001→040 · 🟠 dégradé / 500 · 🟡 mineur.
> Budget LLM ≤ 200 appels (AL ≤ 160, AP ≤ 40).

## Seeds (rejouabilité)
| Lot | Seed | Passes visées |
|---|---|---|
| AA vérité des tuiles | 6001 | 150 |
| AB blocs communes | 6002 | 240 |
| AC recherche de masse | 6003 | 200 |
| AD 100 PDF | 6004 | 100 |
| AE fuzzing écritures | 6005 | 100 |
| AF intégrité pleine table | 6006 | 60 |
| AG accessibilité | 6007 | 40 |
| AH deep-links | 6008 | 80 |
| AI déterminisme & redémarrage | 6009 | 40 |
| AJ installation à vide | 6010 | 20 |
| AK backup & restauration | 6011 | 20 |
| AL Copilote grand volume | 6012 | 100 |
| AM budgets de performance | 6013 | 30 |
| AN marches UI longues | 6014 | 100 |
| AO exports restants | 6015 | 70 |
| AP moteur unique de masse | 6016 | 150 |
| AQ flux métier scénarisés | 6017 | 100 |

## Tableau des passes (rempli lot par lot)
| Lot | Passes | OK | KO / note | Annexe |
|---|---|---|---|---|
| AA — vérité des tuiles | 150 | **150** | 0 (obs. O-AA1 sub-pixel, impact nul) | lot-aa.csv |

<!-- SECTIONS PAR LOT APPENDUES CI-DESSOUS -->

## LOT AA — vérité des tuiles (150, seed 6001) — agent
**150/150 OK, 0 fantôme, 0 manquante-serveur, 0 écart de tier.** Échantillonnage : strates commune×zoom (24 communes, z12-16), parcelle aléatoire → centroïde 3857 → z/x/y ; décodage mapbox-vector-tile ; réplique SQL exacte du serveur (`ST_TileEnvelope` + `ST_AsMVTGeom(…,4096,64,true) IS NOT NULL`, `tiles.py:399-408`) ; tier vs `parcel_p_score_v2` run servi `q_v10_m129`. Tuile == SQL **150/150** ; contre-vérification île entière : **0 écart** `mvt_parcels.tier_v2` vs `parcel_p_score_v2` sur 431 663. 24 passes z16 → 204 par design (servi z9-15, sur-zoom client, FIX-CARTE C2) = OK. 0×429.
- **O-AA1 (observation, pas un finding)** — dropout sub-pixel par quantization `ST_AsMVTGeom` : 6 771 occurrences (4 142 idus, méd 6,9 m² à z12), polygone < 1 unité MVT après snap grille → NULL (comportement PostGIS standard, très sous le pixel écran). Toutes rendues à z15 sauf **55 micro-slivers ≤ 3,1 m²** invisibles à tout zoom servi ; **0 chaude/brûlante droppée** (6 755/6 771 = écartée) ; le clic passe par `/parcels/at`, non affecté. Impact client nul → pas de numéro GB (décision orchestrateur, notée).
