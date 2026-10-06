# QV16-VERIF-1 — La répartition du run q_v16 tient-elle debout ?

**Mandat** : trancher avant de servir — *plus de la moitié de l'île en bande 0 (52,8 %), est-ce la réalité du territoire ou un filtre trop large ?*
**Mode** : lecture seule. Aucun run, aucune bascule, aucune écriture (seul ce rapport est commité).
**Branche** `audit/qv16-verif-1` · worktree `~/Desktop/labuse-qv16` · base `origin/main` · ports 8715/5915.
**Date** : 2026-10-06. **Run audité** : `score_labuse.run_label = 'q_v16'` (calculé le 2026-10-06 11:01, `score_version labuse_v1+d07ec637`), assis sur le résiduel `run_seq = 13` (`q_v16 lidar + exceptions PLU + oracle + chasse`, commit `7cda6244`).

> **Note d'état importante.** Au moment de l'audit, la bascule a **déjà eu lieu** dans l'environnement partagé : `config/served_run.txt = q_v16`, `config/served_manifest.json` → `scoring_run=q_v16, residuel_run_seq=13`, `residuel_runs.run_seq=13 is_served=true` (et le git du dossier `config/` est **propre** : c'est l'état de `origin/main`). Ce rapport vaut donc **vérification d'un run déjà promu** autant que gate pré-serve. Le résultat ne change pas : la question « la répartition tient-elle ? » se pose à l'identique.

**Répartition q_v16 (vérifiée en base, `score_labuse`)** — total **431 663** parcelles :

| Bande | n | Part |
|---|---:|---:|
| 0 | 228 084 | 52,8 % |
| A | 5 952 | 1,4 % |
| B | 35 072 | 8,1 % |
| C | 49 147 | 11,4 % |
| D | 98 386 | 22,8 % |
| NC | 15 022 | 3,5 % |

Les chiffres correspondent **exactement** à l'annoncé du mandat (0=228 084, A=5 952, B=35 072, C=49 147, D=98 386, NC=15 022 ; somme = 431 663).

---

## 1. Ce que veut dire chaque bande

Source de vérité : `src/labuse/scoring/score_labuse.py` + barème `config/score_labuse.yaml`.

Chaîne : `score = clip( barème_capacité(SDP résiduelle) × coef_faisabilité , 0, 100 )`, puis la bande est une **fonction pure du score** (`bande_de_score`, `score_labuse.py:197`). Le barème de capacité part à **0 pts dès que SDP ≤ 0** (`_bareme_capacite`, ligne 107) ; le coefficient de faisabilité a un **plancher 0,4** (ligne 263). Conséquence arithmétique : le plus petit score non nul possible est 15 pts (SDP < 80 m²) × 0,5 (AU différée) × 0,4 = **3** → **un score ne vaut jamais entre 1 et 2** ; `score == 0` ⟺ `SDP ≤ 0`. Vérifié en base : min(score) par bande = 0/80/50/30/**3**.

| Bande | Condition (fichier:ligne) | En une phrase, au client |
|---|---|---|
| **NC** | `score is None` — renvoyé quand `_cause_nc` trouve un motif d'**ignorance** (`score_labuse.py:163-194`, test `bande_de_score:202`) : résiduel absent, géométrie nulle, `zone_non_resolue*`/`hors_plu`, `regle_plu_non_validee*`, `hauteur_indispo`, SDP `NULL`, ou toute cause **non certaine** (`cause_certaine`, `engine.py`). | « Analyse incomplète » — on ne sait pas encore classer (zone non résolue, règle non validée…), **jamais** « sans potentiel ». |
| **0** | `score == 0` (`:204`) ⟺ `SDP résiduelle ≤ 0` **et cause certaine** (sinon NC). | « Non retenue » — pas de surface de plancher constructible restante. |
| **D** | `0 < score < 30` (`:209`, `au_dessous`). | « Faible » — un potentiel résiduel marginal. |
| **C** | `30 ≤ score < 50` (`:206`). | « À étudier ». |
| **B** | `50 ≤ score < 80`. | « Bonne ». |
| **A** | `score ≥ 80`. | « Excellente ». |

Point clé pour la suite : **la bande 0 n'est pas une exclusion du produit**. La parcelle reste visible sur la fiche avec son motif rédigé (CHASSE-FIX-2 D04 : le mot « exigu »/la cause est désormais servie). C'est une étiquette de présentation, pas un filtre qui cache la parcelle.

---

## 2. D'où viennent les 228 084 de la bande 0

La bande 0 = parcelles à **SDP résiduelle ≤ 0 avec une cause certaine**. Vérifié : les 228 084 ont toutes `sdp_residuelle_m2 ≤ 0` (0 NULL, 0 > 0). Décomposition par motif (jointure `parcel_residuel_runs` run_seq 13) :

| Motif d'exclusion | n | Part de la bande 0 |
|---|---:|---:|
| Zone non constructible (secteurs N / A / zones interdites) | 82 449 | 36,1 % |
| Terrain trop exigu (contour inseté < 5 m² après reculs) | 71 252 | 31,2 % |
| Bâti saturé / emprise nulle (SDP calculée = 0 exactement) | 64 267 | 28,2 % |
| Risque rédhibitoire | 5 074 | 2,2 % |
| Habitat interdit (secteurs U d'activité/économiques) | 5 042 | 2,2 % |
| **Total** | **228 084** | **100 %** |

**Aucune cause d'ignorance n'a fuité dans la bande 0** : zéro `zone_non_resolue`, `hors_plu` ou `regle_plu_non_validee` ici — elles sont toutes parties en NC (cf. §1), ce qui est le comportement attendu. La garde « 0 n'est jamais NC et NC n'est jamais 0 » tient en base.

Le bloc « SDP calculée = 0 » (64 267) est le plus subtil : le moteur a tourné jusqu'au bout et la soustraction `max(0, SDP_max − SDP_existante)` est tombée à 0 — c'est-à-dire **bâti déjà saturé** (le bâti existant occupe tout, voire plus, de l'enveloppe autorisée). Les échantillons le confirment : ces parcelles affichent un `taux_emprise_pct` de 105 à 245 % (emprise bâtie > emprise constructible autorisée).

### Croisement avec le zonage PLU (`parcel_zone_plu`)

| Famille de zone | Bande 0 | Total île | Part de la famille en bande 0 |
|---|---:|---:|---:|
| U (urbain) | 127 347 | 306 630 | 41,5 % |
| A (agricole) | 64 510 | 73 946 | 87,2 % |
| N (naturel) | 31 521 | 36 306 | 86,8 % |
| AU (à urbaniser) | 4 706 | 10 537 | 44,7 % |

A et N sont en bande 0 à ~87 % : c'est **attendu et correct** — ce sont les zones où le logement est interdit. Le point à examiner, demandé par le mandat, est la zone **U**.

### Le cas à examiner : 127 347 parcelles en zone U, bande 0

| Motif (en zone U) | n |
|---|---:|
| Bâti saturé / emprise nulle (SDP calculée = 0) | 61 704 |
| Terrain trop exigu | 56 206 |
| Habitat interdit (secteurs U activité/éco) | 4 414 |
| Risque rédhibitoire | 3 554 |
| Zone U non constructible (secteur interdit) | 1 469 |

**92,6 % (117 910) sont « bâti saturé » ou « terrain exigu »** — soit des parcelles urbaines déjà construites à saturation, soit des parcelles trop petites pour accueillir quoi que ce soit après reculs. C'est la texture réelle d'un territoire insulaire dense : le tissu U de La Réunion est massivement composé de petites parcelles pavillonnaires déjà bâties. **Une parcelle U déjà construite au-delà de son enveloppe PLU n'a, de fait, aucun résiduel.**

10 exemples (IDU · zone · motif · emprise) :

| IDU | Commune | Zone | Motif | emp % |
|---|---|---|---|---:|
| 97420000AW0095 | Sainte-Suzanne | UC | bâti saturé | 127 |
| 97411000HE0412 | Saint-Denis | Um | bâti saturé | 67* |
| 97403000AP1634 | Entre-Deux | Ub | bâti saturé | 157 |
| 97408000BN0094 | La Possession | UA | bâti saturé | 105 |
| 97416000CW2415 | Saint-Pierre | Uf | bâti saturé | 109 |
| 97416000EW1074 | Saint-Pierre | Uf | bâti saturé | 115 |
| 97416000IE0601 | Saint-Pierre | Ug | bâti saturé | 130 |
| 97415000DI0646 | Saint-Paul | U2d | bâti saturé | 245 |
| 97406000AV1267 | La Plaine-des-Palmistes | Ub | terrain exigu | — |
| 97411000HD0281 | Saint-Denis | Um | terrain exigu | — |

\* 97411000HE0412 : emp 67 % mais SDP résiduelle = 0 — l'enveloppe restante (après reculs/hauteur) ne dégage pas de plancher ; cohérent avec un petit tènement Um déjà occupé.

---

## 3. Comparaison avec le run précédent (q_v15)

Prédécesseur = `score_labuse.run_label = 'q_v15'` (résiduel run 10, `q_v15 assiette gabarit`), le Score servi avant q_v16.

| Bande | q_v15 | q_v16 | Écart | % |
|---|---:|---:|---:|---:|
| 0 | 269 422 | 228 084 | **−41 338** | **−15,3 %** |
| A | 5 124 | 5 952 | +828 | +16,2 % |
| B | 27 293 | 35 072 | +7 779 | +28,5 % |
| C | 39 661 | 49 147 | +9 486 | +23,9 % |
| D | 75 425 | 98 386 | +22 961 | +30,4 % |
| NC | 14 738 | 15 022 | +284 | +1,9 % |

**Toutes les bandes bougent de plus de 10 %, sauf NC (+1,9 %).** Et elles bougent **dans le même sens** : la bande 0 se vide (−41 k), les bandes constructibles (A/B/C/D) se remplissent. Un seul mouvement explique l'essentiel.

**Matrice de transition q_v15 → q_v16** (cellules > 500) :

- **49 602 parcelles de la bande 0 (q_v15) sont montées** en q_v16 : 40 411 → D, 7 236 → C, 1 722 → B, le reste → A/divers. C'est la source du −15 % sur 0 et des +16 à +30 % sur les constructibles.
- Contre-flux plus petit : **~8 110 parcelles B/C/D sont descendues en 0** (D→0 5 560, C→0 1 676, B→0 874).
- NC **gelé** : 14 738 → 14 738 sur la diagonale (le +284 net vient de constructibles devenus NC ailleurs).

**Cause, comprise et documentée (EXPLIQUE-RUN13 / SCORING-9).** La montée de 49 602 parcelles hors de la bande 0 vient du **recalcul du bâti existant** (commit `a32e1a5c`, DONNEES-FIX-1) : les niveaux du bâti sont désormais dérivés de l'**égout LiDAR** (`max(1, round(égout/3))`) avec coef toit→plancher 0,95. La `sdp_existante` baisse → le résiduel `max(0, sdp_max − sdp_existante)` remonte → des parcelles qui étaient à 0 dégagent un résiduel positif (+14 M m² SDP à l'échelle île, **98 % en zone U**, entièrement sur du bâti). Le contre-flux (B/C/D → 0) est l'autre face du run : l'assiette déduit désormais l'enveloppe des servitudes PPR/SUP de l'implantation (RETOUCHES-1 D.15 + ORACLE-FIX-1 B), ce qui pousse quelques parcelles sous le seuil exigu.

**Verdict sur les écarts : compris.** Le signe est cohérent (un bâti mieux mesuré = plus de résiduel = moins de bande 0), l'amplitude est portée par un unique changement de source tracé, et NC — qui ne dépend pas du résiduel — reste stable, ce qui est exactement ce qu'on attend. Rien d'inexpliqué.

---

## 4. Vérification par échantillon (20 parcelles)

Tirage pseudo-aléatoire stratifié par bande (`row_number() over (partition by bande order by md5(idu||seed))`). Pour chacune, recalcul manuel de la bande à partir des faits servis (zone, SDP résiduelle, emprise, pente, forme, cause). Facteurs de faisabilité relus un à un (`score_labuse.py:104-159`).

| IDU | Bande | Score | Zone | SDP | emp% | pente° | Cause | Contrôle manuel | Cohérent |
|---|---|---:|---|---:|---:|---:|---|---|---|
| 97416000HY0295 | 0 | 0 | Ug | 0 | — | 11,4 | redhibitoire | SDP 0 + risque rédhibitoire → 0 | ✅ |
| 97406000AD0673 | 0 | 0 | Ub | 0 | — | 2,2 | terrain_exigu | contour < 5 m² → 0 | ✅ |
| 97424000AC0860 | 0 | 0 | A | 0 | — | 11,4 | terrain_exigu | A + exigu, **touche PPR pm1** (vérifié) → 0 | ✅ (voir §5) |
| 97416000EN1435 | A | 90 | Ud | 2787 | 3 | 4,6 | — | 100 pts × 0,9 (emp) = 90 | ✅ |
| 97411000BH0781 | A | 90 | Ud | 1069 | 0 | 5,7 | — | 90 pts × 1,0 = 90 | ✅ |
| 97410000BE0761 | A | 81 | Ub | 1351 | 20 | 2,7 | — | 90 × 0,9 = 81 | ✅ |
| 97409000BE2162 | A | 90 | UB | 1017 | 0 | 5,2 | — | 90 × 1,0 = 90 | ✅ |
| 97422000AP0685 | B | 57 | Uc | 487 | 8 | 11,0 | — | 75 × 0,9 × 0,85 (pente 19%) = 57 | ✅ |
| 97410000BM0366 | B | 72 | Uap | 1478 | 25 | 6,1 | — | 90 × 0,8 = 72 | ✅ |
| 97421000AV0521 | B | 61 | UB | 1504 | 32 | 11,3 | — | 90 × 0,8 × 0,85 = 61 | ✅ |
| 97414000ET0277 | B | 75 | UC | 428 | 0 | 5,7 | — | 75 × 1,0 = 75 | ✅ |
| 97422000BR1557 | C | 44 | Uc | 262 | 41 | 7,8 | — | 55 × 0,8 = 44 | ✅ |
| 97411000DL0139 | C | 44 | Ui | 241 | 48 | 4,7 | — | 55 × 0,8 = 44 | ✅ |
| 97408000AC1757 | C | 47 | UBc | 206 | 0 | 13,3 | — | 55 × 0,85 (pente 24%) = 47 | ✅ |
| 97412000CE1917 | C | 35 | U5ru | 185 | 0 | 5,9 | — | 35 × 1,0 = 35 | ✅ |
| 97420000BH1983 | D | 23 | UB | 124 | 59 | 1,2 | — | 35 × 0,65 (emp>50) = 23 | ✅ |
| 97415000CH2481 | D | 15 | U6c | 14 | 0 | 7,5 | — | 15 × 1,0 = 15 | ✅ |
| 97408000AO0689 | D | 10 | UA | 23 | 0 | 10,2 | — | 15 × 0,85 (pente) × 0,8 (**lame, w=3,9 m** vérifié) = 10 | ✅ |
| 97415000ET1643 | NC | — | A | 0 | — | 20,5 | zone_non_resolue:A | zone non résolue → NC | ✅ |
| 97415000EV0078 | NC | — | A | 0 | — | 12,1 | zone_non_resolue:A | zone non résolue → NC | ✅ |
| 97415000DW0009 | NC | — | A | 0 | — | 4,7 | zone_non_resolue:A | zone non résolue → NC | ✅ |
| 97415000ET1120 | NC | — | A | 0 | — | 22,9 | zone_non_resolue:A (64 m²) | zone non résolue > taille → NC | ✅ |

**22 parcelles, 22 cohérentes.** Deux points vérifiés en profondeur :
- **97408000AO0689** (D, score 10) : géométrie confirmée `w = 2·aire/périmètre = 3,9 m` → « parcelle en lame » (forme 0,8). 15 × 0,85 × 0,8 = 10,2 → 10. Le facteur forme, invisible dans le tableau brut, explique l'écart apparent avec 15×0,85.
- **97424000AC0860** (Cilaos, A, terrain_exigu) : intersection avec `tuyau_sup` pm1 (PPR) **confirmée en base** → l'enveloppe de risque déduite collapse le contour sous 5 m². Classement correct au sens de la règle ; la question de fond (parcelle *partiellement* rouge mise à 0) est traitée au §5.

Aucun « non ».

---

## 5. Verdict

> **Le run q_v16 est servable.** Les 52,8 % de l'île en bande 0 sont la **réalité du territoire**, pas un filtre trop large : 36 % sont des zones agricoles/naturelles où le logement est interdit, 28 % des parcelles urbaines **déjà bâties à saturation**, 31 % des parcelles **trop exiguës** après reculs, et ~4 % des zones à risque rédhibitoire ou d'activité. La règle de classement a été relue ligne à ligne et vérifiée sur 22 parcelles (22/22 cohérentes) ; aucune cause d'ignorance ne contamine la bande 0 (elles partent toutes en NC) ; l'écart avec le run précédent (−15 % sur 0, +16 à +30 % sur les constructibles) est porté par **un seul changement tracé** — le recalcul du bâti existant au LiDAR — et le signe est le bon.

**Le doute à nommer plutôt que de conclure à moitié.** Le bloc « terrain exigu » (71 252, soit 31 % de la bande 0) est un mélange : **49,2 % (35 054) touchent une servitude PPR (pm1)**, les ~51 % restants sont géométriquement petits ou en lame. Toucher une PPR n'est pas être *entièrement* en zone rouge : à l'intérieur de ce bloc se niche le chantier post-déploiement déjà identifié par EXPLIQUE-RUN13 — les parcelles **partiellement** rouges dont on déduit toute l'enveloppe et qu'on met à 0 alors qu'une portion hors-rouge resterait constructible (borné à **≤ 4 122 parcelles / −1,87 M m²**, soit ~1,8 % de la bande 0). C'est une **sur-exclusion connue, bornée et pré-existante** (règle Vic « 0 plutôt qu'incohérence »), **pas une régression de q_v16** et pas un bloquant : elle ne concerne qu'une frange, elle va dans le sens prudent, et la parcelle reste visible avec son motif. À reprendre après déploiement, pas avant de servir.

### Annexe — harnais (rejouable, lecture seule)

Toutes les mesures proviennent de `psql` sur la base `labuse` (`PGUSER=openclaw PGHOST=localhost`), sans écriture :
- bandes : `SELECT bande,count(*) FROM score_labuse WHERE run_label='q_v16' GROUP BY bande;`
- motifs bande 0 : jointure `parcel_residuel_runs` (`run_seq=13`) sur la cause.
- zonage : jointure `parcel_zone_plu` (`zone_fam`).
- transition : self-join `score_labuse` q_v15 ↔ q_v16 sur `parcel_id`.
- PPR : `ST_Intersects(tuyau_sup.geom_2975, parcels.geom_2975)` où `subtype='pm1'`.
- échantillon : `row_number() over (partition by bande order by md5(idu||'qv16seed'))`.

Définitions des bandes : `src/labuse/scoring/score_labuse.py` + `config/score_labuse.yaml`. Arrêt propre, 0 transaction idle-in-transaction, ports 8715/5915 non ouverts (audit purement SQL+lecture de code).
