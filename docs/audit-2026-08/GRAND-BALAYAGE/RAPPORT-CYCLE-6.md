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
| AB — blocs communes | 240 | **240** | 0 faux chiffre (🟠 GB-041 data-gap DPE) | lot-ab.csv |
| AC — recherche de masse | 200 | **196** | 4 (🟡 GB-042 jokers LIKE ; 🟡 GB-043 suffixe IDU) | lot-ac.csv |
| AF — intégrité pleine table | 62 | **59** | 3 (🟡 GB-044/045/046) · G2 ✅ G3 ✅ | lot-af.csv |

<!-- SECTIONS PAR LOT APPENDUES CI-DESSOUS -->

## LOT AA — vérité des tuiles (150, seed 6001) — agent
**150/150 OK, 0 fantôme, 0 manquante-serveur, 0 écart de tier.** Échantillonnage : strates commune×zoom (24 communes, z12-16), parcelle aléatoire → centroïde 3857 → z/x/y ; décodage mapbox-vector-tile ; réplique SQL exacte du serveur (`ST_TileEnvelope` + `ST_AsMVTGeom(…,4096,64,true) IS NOT NULL`, `tiles.py:399-408`) ; tier vs `parcel_p_score_v2` run servi `q_v10_m129`. Tuile == SQL **150/150** ; contre-vérification île entière : **0 écart** `mvt_parcels.tier_v2` vs `parcel_p_score_v2` sur 431 663. 24 passes z16 → 204 par design (servi z9-15, sur-zoom client, FIX-CARTE C2) = OK. 0×429.
- **O-AA1 (observation, pas un finding)** — dropout sub-pixel par quantization `ST_AsMVTGeom` : 6 771 occurrences (4 142 idus, méd 6,9 m² à z12), polygone < 1 unité MVT après snap grille → NULL (comportement PostGIS standard, très sous le pixel écran). Toutes rendues à z15 sauf **55 micro-slivers ≤ 3,1 m²** invisibles à tout zoom servi ; **0 chaude/brûlante droppée** (6 755/6 771 = écartée) ; le clic passe par `/parcels/at`, non affecté. Impact client nul → pas de numéro GB (décision orchestrateur, notée).

## LOT AB — les 240 blocs communes (240, seed 6002) — agent
**240/240 exacts vs recalcul SQL indépendant — 0 faux chiffre sur l'outil vitrine.** Les 10 blocs = 9 lignes de `GET /moteurs/marche/{commune}` (`build_marche_commune`, point de calcul unique) + `pression_zan` du `/comparateur-communes`. Recalculs ré-implémentés (sector_price refait en Python : dédup mutation_id, rayons 500/1000/1500, Tukey [1000;12000], min_n 8 ; terrain U/AU dédupé ; tendance 24 mois ; liquidité trimestrielle ; Sitadel 12 mois ; gisement run q_v10_m129 ; DPE ; ENAF/10000 ; loyer fichier versionné ; neuf snapshot `dvf_prix_sortie_neuf` préséance secteur>commune>île). Vérifs annexes vertes : colonne `prix_ancien` du tableau (source unique `prix_ancien_communes`) 24/24 exacte et DISTINCTE par conception du `prix_ancien_median` fiche (documenté `moteurs.py:396-402`) ; tous les « non calculable » justifiés par les comptes réels (n<30 tendance, n<10 terrain AU, social-dominant). 0×429 (cadence 1/2,2 s).
- **GB-041 · 🟠 · Bloc DPE servi sur une table-échantillon de 17 lignes, sans seuil d'honnêteté** — `dpe_records` ne contient que **17 lignes pour toute l'île** (échantillon d'ingestion, pas la base ADEME) ; le bloc « pression DPE » sert « 0,0 % sur 1 DPE » (La Possession), « 50,0 % sur 2 » (Saint-André) avec fiabilité « **moyenne** » dès connus>0 (`marche_commune.py:283-306`), là où tendance exige n≥30 et terrain n≥10. Chiffre exact vs sa table (pas un faux chiffre) mais promesse vitrine non tenue : le bloc devrait dire « non calculable / données non chargées ». Repro : `GET /moteurs/marche/La Possession`.
- **O-AB2 (observation)** — 2 fragilités théoriques vérifiées INERTES sur les données actuelles (liquidité sans dédup mutation : 0 trimestre divergent ; tendance `DISTINCT ON` sans tri secondaire : 0 mutation ambiguë).

## LOT AC — recherche de masse (200, seed 6003) — agent
**196/200 OK.** Adresses 80/80 (rappel 100 % sur BAN locale 339 915 lignes, tirage md5 seedé) ; géométrie **20/20** (point BAN ⊂ parcelle servie ou ≤30 m — aucune « mauvaise parcelle avec assurance ») ; IDU 60/60 (minuscules/espaces/section+numéro servis ; tronqués/faux → 0 résultat honnête ou 404 propre) ; lieux-dits 30/30 (table `adresses` = housenumbers only, retombées honnêtes) ; hostiles 26/30 (zéro 500 ; vide/null-byte → 422 ; 10k car./RTL/HTML → 0 résultat).
- **GB-042 · 🟡 · Jokers LIKE non échappés → résultats sûrs-d'eux pour requêtes absurdes** — `/adresses/autocomplete?q=%%%` → 12 suggestions confiantes ; `/parcels/search?q=974%` matche les 431 663 IDU. Cause : `app.py:1770` (`LIKE '%'||:q||'%'` sans échappement `%`/`_`) et `app.py:1827`. Paramétré (0 injection), mais réponse absurde assumée + vecteur LIKE-scan.
- **GB-043 · 🟡 · `/parcels/search` ne matche que la FIN d'IDU** — un début d'IDU collé (« 97421000AV », forme naturelle insee+section) → 0 résultat (`app.py:1827`). Honnête mais rappel nul sur un geste courant.
- **O-AC3/O-AC4 (observations)** — 21/339 915 adresses BAN sans idu exclues par design (0,006 %) ; coller le label complet servi (« 10 Rue de Paris, Saint-Denis (97400) ») → 0 résultat (l'app ne ré-avale pas son propre format d'affichage).

## LOT AF — intégrité pleine table (62, dont gardées) — agent
**59/62 OK. G2 ✅ (`/readyz` ready+schema.ok+data.ok, run servi q_v10_m129) · G3 ✅ (SHLMR 2618, SAFER 844, SEDRE 1847 — identiques cycle 5 au chiffre près).** Couverture : géométries 12/12 (431 663 parcelles **0 invalide** geom+geom_2975, SRID homogènes, ortho_tiles 2975, spatial_layers 1,84 M propres, bbox Réunion) · unicité 10/10 (idu partout, p_score_v2 3,03 M, adjacence 1,13 M sans doublon/boucle) · FK 15 passes (63 FKs déclarées + anti-joins réels : **0 orphelin** ; implicites 3 M/4,3 M/1,13 M : 0) · NULLs 8/8 — **M125 conforme au chiffre exact** (cause NULL = 253 764 calculées, sdp NULL = 4 397 hors_plu seuls, total 431 663 = 100 %) · bornes 10/10 · compteurs 5/7. OK-avec-note (design documenté) : 635 IDU MAJIC orphelins (GB-007 connu), 1 154 dvf_mutations_parcelle historiques (mono-millésime M126), taux>100 cap volontaire `residuel.py:123-124`, 7 parcelles >10 km² réelles. pg_stat périmé détecté → tous les verdicts sur COUNT exacts.
- **GB-044 · 🟡 · Run fantôme `q_v2_demo` dans `parcel_p_score_v2`** — 8 lignes d'un run absent de `p_score_v2_runs` (8 run_id distincts vs 7 enregistrés). Vestige démo, run servi sain. Purge cosmétique proposée.
- **GB-045 · 🟡 · `ortho_tiles.nb_detections` périmé sur 3 122/5 041 tuiles** — la purge PV `20eb5bd8` (DELETE 23 529 détections) n'a jamais décrémenté le compteur. Interne, aucune surface servie identifiée. Recalcul ou note schéma.
- **GB-046 · 🟡 · `ingestion_runs.parcels_count` ≠ parcelles rattachées** — sémantique de journal (nb à l'époque) + upserts qui ré-attribuent `ingestion_run_id` ; non documenté, aucun consommateur cassé. À documenter ou renommer.
