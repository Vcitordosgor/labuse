# VERITE-TERRAIN-2 — volet D : la capacité LABUSE face aux vrais permis Sit@del (post-PLU)

Les volets A/B/C ont vérifié ce que LABUSE **sert** (règles PLU, trajets, DPE/permis/risques) contre les sources. Le volet D pose l'autre question : **ce que LABUSE dit constructible tient-il face à ce qui a été réellement autorisé ?** Pour chaque parcelle ayant obtenu un permis logements (Sit@del/SDES) **depuis l'entrée en vigueur du PLU en cours de sa commune**, on compare l'**autorisé** (surface habitable créée, logements créés) à la **capacité LABUSE** servie en q_v19 (SDP max du moteur de faisabilité, logements estimés).

Lecture seule stricte (DB `read_only=True`, aucun écrit, aucune modif de code existant). Le moteur de faisabilité est appelé **en lecture** sur l'état servi q_v19. Un seul module neuf : `src/labuse/verite_terrain_capacite.py`. Cache disque par parcelle (`cache/capacite/`, non commité) + journal append-only resumable (`_capacite_partiel.csv`, non commité). Livrable : `PERMIS-VS-CAPACITE.csv` (6569 lignes = 1 par permis) + ce NOTES.

---

## 0. Verdict d'ensemble

- **6569 permis** post-PLU retenus sur **23 communes**.
- **Filtre** : PC/DP, famille « logements », **non annulés** (ETAT_DAU ≠ 4), créant une surface habitable OU des logements (`surf_hab_creee` > 0 ou `nb_lgt_tot_crees` > 0), portant au moins un IDU, **date d'autorisation postérieure au millésime du PLU** de la commune.
- **4203 permis (64.0 %) ≤ capacité LABUSE** (LABUSE couvre l'autorisé) · **2366 (36.0 %) au-dessus** (LABUSE sous-estime ou ne sert pas).

### Écart médian & dispersion (ratio autorisé / LABUSE)

| grandeur | n mesurable | médiane | Q1 | Q3 | IQR | min | max | ratios « inf » (LABUSE=0) |
|---|---|---|---|---|---|---|---|---|
| **SDP** (plancher) | 4732 | 0.46 | 0.23 | 0.89 | 0.66 | 0.00 | 26.91 | 1441 |
| **logements** | 4732 | 0.40 | 0.25 | 0.75 | 0.50 | 0.00 | 23.00 | 1450 |

Ratio = autorisé / capacité LABUSE. **< 1 = LABUSE couvre** (capacité ≥ autorisé) ; **> 1 = LABUSE sous-estime** (autorisé plus grand). « inf » = capacité LABUSE nulle alors que le permis a créé quelque chose (classé en cause ci-dessous). La médiane est donnée **telle quelle**, sans retrait d'aberrants.

### Cause dominante des permis au-dessus

| cause | permis |
|---|---|
| parcelle non servie | 1293 |
| densité réelle > calibrage LABUSE | 889 |
| non constructible LABUSE | 158 |
| réunion de parcelles incomplète | 25 |
| surface Sit@del aberrante | 1 |

---

## 1. Méthode

### 1.1 Autorisé = Sit@del/SDES (`sitadel_permits`)

- **Source** : table `sitadel_permits` (permis ingérés de Sit@del3/SDES). Famille « logements », type PC ou DP. **Annulés exclus** (`raw->>'etat' = '4'` = ETAT_DAU annulé, cf. `ingestion/permits.ETAT_LABELS`) — on garde autorisés / travaux commencés / achevés.
- **Surface créée** : `raw->>'surf_hab'` = `surf_hab_creee` = **surface HABITABLE** créée (libellé source « m² hab. », `ingestion/permits._nature`). Ce n'est **pas** une surface de plancher. On la convertit en plancher (**× 1,15**, coef `score_e.COEF_PLANCHER`) avant de la comparer à la SDP brute LABUSE, sinon le ratio sous-estime mécaniquement.
- **Logements créés** : `raw->>'nb_lgt'` = `nb_lgt_tot_crees`. Comparaison directe.
- **Date** : colonne `date` = `date_reelle_autorisation` (date réelle d'autorisation, `ingestion/permits.ingest_permits`) ; repli `date_depot` si `date` nulle. **C'est la date d'autorisation** qui borne « post-PLU ».
- **Réunion foncière** : `idu_codes` (jsonb) = liste des parcelles du permis ; les projets multi-parcelles (579 permis ici) sont comparés à la **somme** des capacités LABUSE de leurs parcelles servies.

### 1.2 Entrée en vigueur du PLU

`config/plu_destinations/<insee>_*.yaml`, champ `meta.millesime` = **date du règlement en vigueur** (relu au PDF/GPU dans les volets A et CALIBRAGE). Seuls les permis **postérieurs** à cette date sont retenus : avant, les règles que LABUSE modélise ne s'appliquaient pas. Les millésimes vont de 2007 (Saint-Leu, le plus ancien → quasi tous ses permis sont « post-PLU ») à 2026 (Saint-Denis, Bras-Panon → très peu de permis postérieurs).

### 1.3 Capacité LABUSE servie (q_v19)

Run servi confirmé par `config/served_manifest.json` : `scoring_run = q_v19`, `residuel_run_seq = 16`, `residuel_runs` ligne `run_seq 16` / label `q_v19` / `is_served = t`. La capacité est lue par le **moteur de faisabilité** (`faisabilite.db.parcel_faisabilite`) **en lecture** sur l'état servi (zones `parcel_zone_plu`, PLU calibré, bâti BD TOPO/CoSIA, hauteur LiDAR) — exactement ce qui alimente la fiche servie q_v19. On en tire, par parcelle :

- **SDP max** = `fourchette['surface_plancher_m2']` (surface de plancher max, grandeur brute).
- **logements estimés** = `max(logements_au_sol[1], logements_sous_sol[1])` — **exactement la formule servie** (`faisabilite/bilan.py:404-405`), le haut de fourchette (la capacité).
- parcelle non servie / non constructible → SDP max 0, logements 0, avec la cause servie (`parcel_residuel_runs.cause`, run 16).

**Grain** : la comparaison est au grain **permis** (projet), pas parcelle isolée — l'autorisé d'un projet est confronté à la **somme** des capacités LABUSE des parcelles du permis.

---

## 2. Écart médian & dispersion par commune

| commune | permis | ≤ capacité | au-dessus | méd. ratio SDP | IQR SDP | méd. ratio logts | IQR logts |
|---|---|---|---|---|---|---|---|
| Saint-Leu | 2036 | 1089 | 947 | 0.68 | 0.87 | 0.50 | 0.50 |
| Saint-André | 1012 | 716 | 296 | 0.41 | 0.45 | 0.25 | 0.33 |
| Saint-Benoît | 830 | 511 | 319 | 0.24 | 0.23 | 0.25 | 0.17 |
| Le Tampon | 534 | 436 | 98 | 0.27 | 0.30 | 0.25 | 0.19 |
| Saint-Pierre | 508 | 353 | 155 | 0.60 | 0.69 | 0.50 | 0.46 |
| Sainte-Rose | 197 | 100 | 97 | 0.52 | 0.97 | 0.50 | 0.75 |
| Petite-Île | 194 | 120 | 74 | 0.61 | 0.79 | 0.50 | 0.67 |
| Saint-Paul | 169 | 122 | 47 | 0.54 | 0.70 | 0.50 | 0.36 |
| Les Trois-Bassins | 160 | 86 | 74 | 0.70 | 0.88 | 0.50 | 0.67 |
| La Plaine-des-Palmistes | 142 | 100 | 42 | 0.49 | 0.61 | 0.37 | 0.25 |
| Salazie | 119 | 103 | 16 | 0.16 | 0.23 | 0.25 | 0.21 |
| Saint-Louis | 117 | 81 | 36 | 0.36 | 0.61 | 0.33 | 0.30 |
| Saint-Joseph | 91 | 64 | 27 | 0.55 | 0.77 | 0.50 | 0.75 |
| Entre-Deux | 83 | 59 | 24 | 0.26 | 0.65 | 0.33 | 0.83 |
| L'Étang-Salé | 72 | 54 | 18 | 0.54 | 0.66 | 0.40 | 0.42 |
| Les Avirons | 70 | 57 | 13 | 0.52 | 0.67 | 0.50 | 0.75 |
| Sainte-Marie | 67 | 35 | 32 | 1.01 | 1.73 | 0.50 | 0.67 |
| Cilaos | 53 | 38 | 15 | 0.39 | 0.59 | 0.50 | 0.46 |
| Sainte-Suzanne | 49 | 32 | 17 | 0.45 | 0.45 | 0.33 | 0.47 |
| Le Port | 36 | 27 | 9 | 0.61 | 0.90 | 0.33 | 0.25 |
| Bras-Panon | 12 | 6 | 6 | 0.77 | 1.24 | 0.60 | 0.67 |
| La Possession | 10 | 9 | 1 | 0.66 | 0.84 | 0.50 | 0.25 |
| Saint-Denis | 8 | 5 | 3 | 1.05 | 1.60 | 1.00 | 1.02 |

## 3. Écart médian & dispersion par famille de zone PLU

Famille = `parcel_zone_plu.zone_fam` servie, repli sur la zone normalisée (préfixe de phase AU retiré : 1AUc→AU) : U (urbain), AU (à urbaniser), A (agricole), N (naturel). `?` = permis dont aucune parcelle n'est servie (foncier redécoupé) → sans zone ni ratio mesurable.

| zone | permis | ≤ capacité | au-dessus | méd. ratio SDP | IQR SDP | méd. ratio logts | IQR logts |
|---|---|---|---|---|---|---|---|
| U | 4199 | 3300 | 899 | 0.45 | 0.68 | 0.40 | 0.75 |
| ? | 1623 | 386 | 1237 | — | — | — | — |
| AU | 443 | 369 | 74 | 0.52 | 0.41 | 0.33 | 0.25 |
| N | 159 | 69 | 90 | 0.62 | 0.88 | 0.50 | 0.76 |
| A | 145 | 79 | 66 | 0.39 | 0.74 | 0.50 | 0.55 |

---

## 4. Les permis au-dessus de la capacité LABUSE, un par un

**2366 permis** dépassent la capacité LABUSE (ratio SDP ou logements > 1.10). Classés par cause, du plus structurel au plus métier.

### parcelle non servie — 1293 permis

| permit_id | commune | zone(s) | date | n parc. (servies) | SDP aut. (planch.) m² | logts aut. | SDP max LABUSE m² | logts LABUSE | ratio SDP | ratio logts | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 97440226A0015 | Bras-Panon | Uba (U) | 2026-05-20 | 1 (0) | 139 | 1 | 0 | 0 | inf | inf | aucune parcelle du permis n'est servie par LABUSE (foncier redécoupé après le permis) |
| 97440226A0022 | Bras-Panon | ? | 2026-07-08 | 1 (0) | 251 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440226A0039 | Bras-Panon | ? | 2026-08-26 | 1 (0) | 0 | 1 | 0 | 0 |  | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440324A0039 | Entre-Deux | ? | 2024-10-21 | 1 (0) | 97 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440324A0043 | Entre-Deux | ? | 2024-12-04 | 1 (0) | 141 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440324A0049 | Entre-Deux | ? | 2024-12-10 | 1 (0) | 100 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440324A0057 | Entre-Deux | ? | 2024-12-18 | 1 (0) | 147 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 9744032500037 | Entre-Deux | ? | 2025-10-14 | 1 (0) | 101 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 9744032500126 | Entre-Deux | ? | 2025-12-11 | 1 (0) | 45 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440325A0007 | Entre-Deux | Ub (U) | 2025-04-23 | 1 (0) | 60 | 1 | 0 | 0 | inf | inf | aucune parcelle du permis n'est servie par LABUSE (foncier redécoupé après le permis) |
| 97440325A0029 | Entre-Deux | ? | 2025-09-04 | 1 (0) | 68 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440325A0038 | Entre-Deux | ? | 2025-11-28 | 1 (0) | 118 | 2 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440325A0045 | Entre-Deux | AUb (AU) | 2025-11-18 | 1 (0) | 132 | 1 | 0 | 0 | inf | inf | aucune parcelle du permis n'est servie par LABUSE (foncier redécoupé après le permis) |
| 97440325A0055 | Entre-Deux | ? | 2026-02-17 | 1 (0) | 164 | 2 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440326A0007 | Entre-Deux | ? | 2026-05-04 | 1 (0) | 467 | 2 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440326A0026 | Entre-Deux | ? | 2026-07-21 | 1 (0) | 38 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440326A0029 | Entre-Deux | ? | 2026-07-21 | 1 (0) | 198 | 2 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440425A0043 | L'Étang-Salé | ? | 2025-11-20 | 1 (0) | 80 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440425A0045 | L'Étang-Salé | ? | 2025-11-05 | 1 (0) | 100 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440425A0086 | L'Étang-Salé | ? | 2025-11-05 | 1 (0) | 79 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440425A0089 | L'Étang-Salé | UC (U) | 2025-11-10 | 1 (0) | 91 | 1 | 0 | 0 | inf | inf | aucune parcelle du permis n'est servie par LABUSE (foncier redécoupé après le permis) |
| 97440425A0099 | L'Étang-Salé | ? | 2025-11-21 | 1 (0) | 207 | 2 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440425A0100 | L'Étang-Salé | ? | 2025-10-14 | 1 (0) | 116 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440425A0107 | L'Étang-Salé | ? | 2026-01-23 | 1 (0) | 167 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440425A0116 | L'Étang-Salé | ? | 2026-04-15 | 1 (0) | 167 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440425A0119 | L'Étang-Salé | UC (U) | 2026-01-22 | 1 (0) | 31 | 1 | 0 | 0 | inf | inf | aucune parcelle du permis n'est servie par LABUSE (foncier redécoupé après le permis) |
| 97440426A0027 | L'Étang-Salé | ? | 2026-07-15 | 1 (0) | 184 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440124A0055 | Les Avirons | ? | 2025-02-25 | 1 (0) | 330 | 3 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 9744012520012 | Les Avirons | ? | 2025-06-19 | 1 (0) | 78 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 9744012520052 | Les Avirons | Ud3 (U) | 2025-12-17 | 1 (0) | 23 | 1 | 0 | 0 | inf | inf | aucune parcelle du permis n'est servie par LABUSE (foncier redécoupé après le permis) |
| 97440523A0026 | Petite-Île | UZ (U) | 2023-06-22 | 2 (0) | 105 | 1 | 0 | 0 | inf | inf | réunion de 2 parcelle(s) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécoupé après le permis) |
| 97440523A0027 | Petite-Île | ? | 2023-09-11 | 1 (0) | 116 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440523A0028 | Petite-Île | ? | 2023-07-18 | 1 (0) | 166 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440523A0034 | Petite-Île | ? | 2023-06-22 | 1 (0) | 208 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440523A0036 | Petite-Île | ? | 2023-07-27 | 1 (0) | 110 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440523A0041 | Petite-Île | ? | 2023-08-07 | 2 (0) | 106 | 1 | 0 | 0 | inf | inf | réunion de 2 parcelle(s) ; 2/2 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie  |
| 97440523A0042 | Petite-Île | ? | 2023-07-26 | 1 (0) | 107 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440523A0045 | Petite-Île | ? | 2023-09-25 | 1 (0) | 109 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440523A0051 | Petite-Île | ? | 2023-08-29 | 1 (0) | 151 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440523A0060 | Petite-Île | ? | 2023-08-29 | 1 (0) | 284 | 2 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440523A0061 | Petite-Île | ? | 2023-08-18 | 1 (0) | 121 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440523A0071 | Petite-Île | ? | 2023-09-11 | 1 (0) | 76 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440523A0081 | Petite-Île | ? | 2023-10-02 | 1 (0) | 90 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440523A0089 | Petite-Île | ? | 2023-12-18 | 1 (0) | 135 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440523A0096 | Petite-Île | ? | 2023-12-28 | 1 (0) | 166 | 2 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440523A0108 | Petite-Île | ? | 2024-01-29 | 1 (0) | 105 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440523A0119 | Petite-Île | UC (U) | 2024-02-12 | 1 (0) | 101 | 1 | 0 | 0 | inf | inf | aucune parcelle du permis n'est servie par LABUSE (foncier redécoupé après le permis) |
| 97440524A0019 | Petite-Île | ? | 2024-07-01 | 2 (0) | 176 | 2 | 0 | 0 | inf | inf | réunion de 2 parcelle(s) ; 2/2 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie  |
| 97440524A0020 | Petite-Île | ? | 2024-05-17 | 1 (0) | 48 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440524A0037 | Petite-Île | ? | 2024-08-12 | 1 (0) | 75 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440524A0056 | Petite-Île | ? | 2024-11-04 | 1 (0) | 151 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440524A0062 | Petite-Île | ? | 2024-09-09 | 1 (0) | 282 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440524A0073 | Petite-Île | ? | 2025-01-09 | 1 (0) | 145 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440524A0093 | Petite-Île | ? | 2025-01-27 | 1 (0) | 90 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440524A0096 | Petite-Île | ? | 2025-01-27 | 1 (0) | 101 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440524A0099 | Petite-Île | ? | 2025-02-05 | 1 (0) | 101 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440525A0018 | Petite-Île | ? | 2025-05-12 | 1 (0) | 170 | 2 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440525A0032 | Petite-Île | ? | 2025-11-10 | 1 (0) | 77 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440525A0047 | Petite-Île | ? | 2025-08-13 | 1 (0) | 86 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| 97440525A0049 | Petite-Île | ? | 2025-09-02 | 1 (0) | 95 | 1 | 0 | 0 | inf | inf | 1/1 parcelle(s) non servie(s) (disparue/redécoupée) ; aucune parcelle du permis n'est servie par LABUSE (foncier redécou |
| … | … | … | … | … | … | … | … | … | … | … | (+1233 autres de même cause, voir CSV) |

### densité réelle > calibrage LABUSE — 889 permis

| permit_id | commune | zone(s) | date | n parc. (servies) | SDP aut. (planch.) m² | logts aut. | SDP max LABUSE m² | logts LABUSE | ratio SDP | ratio logts | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 97440226A0025 | Bras-Panon | 1AUc (AU) | 2026-06-24 | 1 (1) | 253 | 2 | 124 | 2 | 2.04 | 1.0 | SDP autorisée 253 m² (plancher, = 220 m² hab.×1.15) > SDP max LABUSE 124 m² |
| 97440226A0026 | Bras-Panon | Uc (U) | 2026-08-26 | 1 (1) | 113 | 1 | 80 | 1 | 1.409 | 1.0 | SDP autorisée 113 m² (plancher, = 98 m² hab.×1.15) > SDP max LABUSE 80 m² |
| 97440226A0029 | Bras-Panon | Ub (U) | 2026-08-05 | 1 (1) | 167 | 1 | 100 | 2 | 1.667 | 0.5 | SDP autorisée 167 m² (plancher, = 145 m² hab.×1.15) > SDP max LABUSE 100 m² |
| 97440324A0046 | Entre-Deux | Ub (U) | 2025-02-26 | 1 (1) | 57 | 1 | 16 | 1 | 3.594 | 1.0 | SDP autorisée 57 m² (plancher, = 50 m² hab.×1.15) > SDP max LABUSE 16 m² |
| 9744032500002 | Entre-Deux | AUb (AU) | 2025-04-02 | 1 (1) | 118 | 1 | 80 | 1 | 1.481 | 1.0 | SDP autorisée 118 m² (plancher, = 103 m² hab.×1.15) > SDP max LABUSE 80 m² |
| 97440325A0003 | Entre-Deux | N (N) | 2025-03-31 | 1 (1) | 168 | 1 | 106 | 1 | 1.584 | 1.0 | SDP autorisée 168 m² (plancher, = 146 m² hab.×1.15) > SDP max LABUSE 106 m² |
| 97440325A0025 | Entre-Deux | AUb (AU) | 2025-09-29 | 3 (3) | 2474 | 36 | 214 | 3 | 11.559 | 12.0 | réunion de 3 parcelle(s) ; 1 parcelle(s) non constructible(s) chez LABUSE (terrain_exigu) ; SDP autorisée 2474 m² (planc |
| 97440325A0046 | Entre-Deux | Ua (U) | 2025-12-02 | 1 (1) | 296 | 3 | 204 | 2 | 1.449 | 1.5 | SDP autorisée 296 m² (plancher, = 257 m² hab.×1.15) > SDP max LABUSE 204 m² ; 3 logements autorisés > 2 estimés LABUSE |
| 97440326A0004 | Entre-Deux | Ua (U) | 2026-04-10 | 1 (1) | 164 | 2 | 109 | 1 | 1.509 | 2.0 | SDP autorisée 164 m² (plancher, = 143 m² hab.×1.15) > SDP max LABUSE 109 m² ; 2 logements autorisés > 1 estimés LABUSE |
| 97440326A0005 | Entre-Deux | Ua (U) | 2026-04-10 | 1 (1) | 170 | 2 | 109 | 1 | 1.561 | 2.0 | SDP autorisée 170 m² (plancher, = 148 m² hab.×1.15) > SDP max LABUSE 109 m² ; 2 logements autorisés > 1 estimés LABUSE |
| 97440326A0019 | Entre-Deux | N (N) | 2026-04-10 | 1 (1) | 153 | 1 | 111 | 1 | 1.378 | 1.0 | SDP autorisée 153 m² (plancher, = 133 m² hab.×1.15) > SDP max LABUSE 111 m² |
| 97440425A0079 | L'Étang-Salé | UC (U) | 2025-09-18 | 2 (2) | 145 | 1 | 65 | 1 | 2.229 | 1.0 | réunion de 2 parcelle(s) ; 1 parcelle(s) non constructible(s) chez LABUSE (terrain_exigu) ; SDP autorisée 145 m² (planch |
| 97440425A0104 | L'Étang-Salé | UA (U) | 2026-01-22 | 1 (1) | 2528 | 34 | 1749 | 19 | 1.445 | 1.789 | SDP autorisée 2528 m² (plancher, = 2198 m² hab.×1.15) > SDP max LABUSE 1749 m² ; 34 logements autorisés > 19 estimés LAB |
| 97440425A0110 | L'Étang-Salé | AUc (AU) | 2025-12-31 | 1 (1) | 158 | 1 | 126 | 2 | 1.25 | 0.5 | SDP autorisée 158 m² (plancher, = 137 m² hab.×1.15) > SDP max LABUSE 126 m² |
| 97440425A0135 | L'Étang-Salé | UA (U) | 2026-06-24 | 1 (1) | 1214 | 17 | 1334 | 14 | 0.91 | 1.214 | 17 logements autorisés > 14 estimés LABUSE |
| 97440426A0009 | L'Étang-Salé | UD (U) | 2026-02-13 | 1 (1) | 174 | 1 | 150 | 1 | 1.158 | 1.0 | SDP autorisée 174 m² (plancher, = 151 m² hab.×1.15) > SDP max LABUSE 150 m² |
| 97440426A0014 | L'Étang-Salé | UBv (U) | 2026-04-14 | 1 (1) | 169 | 1 | 130 | 2 | 1.3 | 0.5 | SDP autorisée 169 m² (plancher, = 147 m² hab.×1.15) > SDP max LABUSE 130 m² |
| 97440426A0026 | L'Étang-Salé | UC (U) | 2026-06-24 | 1 (1) | 179 | 2 | 123 | 2 | 1.459 | 1.0 | SDP autorisée 179 m² (plancher, = 156 m² hab.×1.15) > SDP max LABUSE 123 m² |
| 97440426A0055 | L'Étang-Salé | UA (U) | 2026-08-25 | 1 (1) | 57 | 1 | 18 | 1 | 3.194 | 1.0 | SDP autorisée 57 m² (plancher, = 50 m² hab.×1.15) > SDP max LABUSE 18 m² |
| 97440124A0042 | Les Avirons | Uc (U) | 2025-01-28 | 1 (1) | 222 | 2 | 101 | 1 | 2.198 | 2.0 | SDP autorisée 222 m² (plancher, = 193 m² hab.×1.15) > SDP max LABUSE 101 m² ; 2 logements autorisés > 1 estimés LABUSE |
| 9744012520018 | Les Avirons | Ud (U) | 2025-07-31 | 1 (1) | 126 | 1 | 106 | 1 | 1.193 | 1.0 | SDP autorisée 126 m² (plancher, = 110 m² hab.×1.15) > SDP max LABUSE 106 m² |
| 9744012520029 | Les Avirons | Uc (U) | 2025-11-06 | 2 (2) | 171 | 4 | 279 | 3 | 0.614 | 1.333 | réunion de 2 parcelle(s) ; 4 logements autorisés > 3 estimés LABUSE |
| 9744012520046 | Les Avirons | Ud1 (U) | 2026-02-09 | 1 (1) | 150 | 0 | 117 | 2 | 1.278 | 0.0 | SDP autorisée 150 m² (plancher, = 130 m² hab.×1.15) > SDP max LABUSE 117 m² |
| 9744012620006 | Les Avirons | Ud (U) | 2026-05-22 | 1 (1) | 101 | 1 | 78 | 1 | 1.297 | 1.0 | SDP autorisée 101 m² (plancher, = 88 m² hab.×1.15) > SDP max LABUSE 78 m² |
| 9744012620012 | Les Avirons | Ud (U) | 2026-07-28 | 1 (1) | 108 | 1 | 90 | 1 | 1.201 | 1.0 | SDP autorisée 108 m² (plancher, = 94 m² hab.×1.15) > SDP max LABUSE 90 m² |
| 9744012620013 | Les Avirons | Ud (U) | 2026-07-28 | 1 (1) | 210 | 2 | 165 | 2 | 1.275 | 1.0 | SDP autorisée 210 m² (plancher, = 183 m² hab.×1.15) > SDP max LABUSE 165 m² |
| 9744012620034 | Les Avirons | Ud3 (U) | 2026-08-12 | 1 (1) | 125 | 1 | 92 | 1 | 1.363 | 1.0 | SDP autorisée 125 m² (plancher, = 109 m² hab.×1.15) > SDP max LABUSE 92 m² |
| 97440523A0037 | Petite-Île | UC (U) | 2023-06-15 | 1 (1) | 105 | 1 | 89 | 1 | 1.176 | 1.0 | SDP autorisée 105 m² (plancher, = 91 m² hab.×1.15) > SDP max LABUSE 89 m² |
| 97440523A0046 | Petite-Île | UC (U) | 2023-09-11 | 1 (1) | 241 | 2 | 212 | 2 | 1.139 | 1.0 | SDP autorisée 241 m² (plancher, = 210 m² hab.×1.15) > SDP max LABUSE 212 m² |
| 97440523A0063 | Petite-Île | UD (U) | 2023-08-18 | 2 (2) | 171 | 1 | 42 | 2 | 4.08 | 0.5 | réunion de 2 parcelle(s) ; SDP autorisée 171 m² (plancher, = 149 m² hab.×1.15) > SDP max LABUSE 42 m² |
| 97440523A0076 | Petite-Île | UC (U) | 2023-09-18 | 1 (1) | 116 | 1 | 83 | 1 | 1.399 | 1.0 | SDP autorisée 116 m² (plancher, = 101 m² hab.×1.15) > SDP max LABUSE 83 m² |
| 97440523A0079 | Petite-Île | N (N) | 2023-11-13 | 1 (1) | 151 | 2 | 65 | 1 | 2.318 | 2.0 | SDP autorisée 151 m² (plancher, = 131 m² hab.×1.15) > SDP max LABUSE 65 m² ; 2 logements autorisés > 1 estimés LABUSE |
| 97440523A0086 | Petite-Île | UD (U) | 2023-10-16 | 1 (1) | 170 | 1 | 94 | 1 | 1.811 | 1.0 | SDP autorisée 170 m² (plancher, = 148 m² hab.×1.15) > SDP max LABUSE 94 m² |
| 97440523A0097 | Petite-Île | A|UC (A|U) | 2024-03-18 | 2 (2) | 460 | 8 | 420 | 6 | 1.095 | 1.333 | réunion de 2 parcelle(s) ; 1 parcelle(s) non constructible(s) chez LABUSE (terrain_exigu) ; 8 logements autorisés > 6 es |
| 97440523A0100 | Petite-Île | N (N) | 2024-01-29 | 1 (1) | 159 | 1 | 72 | 1 | 2.204 | 1.0 | SDP autorisée 159 m² (plancher, = 138 m² hab.×1.15) > SDP max LABUSE 72 m² |
| 97440523A0115 | Petite-Île | UC (U) | 2024-02-20 | 3 (3) | 539 | 5 | 447 | 5 | 1.207 | 1.0 | réunion de 3 parcelle(s) ; SDP autorisée 539 m² (plancher, = 469 m² hab.×1.15) > SDP max LABUSE 447 m² |
| 97440523A0121 | Petite-Île | UD (U) | 2024-01-08 | 1 (1) | 82 | 1 | 68 | 1 | 1.201 | 1.0 | SDP autorisée 82 m² (plancher, = 71 m² hab.×1.15) > SDP max LABUSE 68 m² |
| 97440523A0122 | Petite-Île | UC (U) | 2024-03-29 | 1 (1) | 169 | 2 | 75 | 1 | 2.254 | 2.0 | SDP autorisée 169 m² (plancher, = 147 m² hab.×1.15) > SDP max LABUSE 75 m² ; 2 logements autorisés > 1 estimés LABUSE |
| 97440523A0124 | Petite-Île | A (A) | 2024-03-25 | 1 (1) | 110 | 2 | 43 | 1 | 2.567 | 2.0 | SDP autorisée 110 m² (plancher, = 96 m² hab.×1.15) > SDP max LABUSE 43 m² ; 2 logements autorisés > 1 estimés LABUSE |
| 97440523A0126 | Petite-Île | A|UC (A|U) | 2024-02-19 | 2 (2) | 155 | 1 | 30 | 1 | 5.175 | 1.0 | réunion de 2 parcelle(s) ; 1 parcelle(s) non constructible(s) chez LABUSE (terrain_exigu) ; SDP autorisée 155 m² (planch |
| 97440523E0102 | Petite-Île | UD (U) | 2023-07-26 | 1 (1) | 0 | 2 | 76 | 1 | 0.0 | 2.0 | 2 logements autorisés > 1 estimés LABUSE |
| 97440524A0010 | Petite-Île | UB (U) | 2024-06-24 | 1 (1) | 89 | 1 | 72 | 1 | 1.23 | 1.0 | SDP autorisée 89 m² (plancher, = 77 m² hab.×1.15) > SDP max LABUSE 72 m² |
| 97440524A0021 | Petite-Île | UC (U) | 2024-06-24 | 1 (1) | 60 | 1 | 41 | 1 | 1.459 | 1.0 | SDP autorisée 60 m² (plancher, = 52 m² hab.×1.15) > SDP max LABUSE 41 m² |
| 97440524A0031 | Petite-Île | N (N) | 2024-11-04 | 1 (1) | 86 | 1 | 38 | 1 | 2.27 | 1.0 | SDP autorisée 86 m² (plancher, = 75 m² hab.×1.15) > SDP max LABUSE 38 m² |
| 97440524A0033 | Petite-Île | N (N) | 2024-08-12 | 1 (1) | 93 | 1 | 6 | 1 | 15.525 | 1.0 | SDP autorisée 93 m² (plancher, = 81 m² hab.×1.15) > SDP max LABUSE 6 m² |
| 97440524A0046 | Petite-Île | N (N) | 2024-09-26 | 1 (1) | 90 | 1 | 42 | 1 | 2.136 | 1.0 | SDP autorisée 90 m² (plancher, = 78 m² hab.×1.15) > SDP max LABUSE 42 m² |
| 97440524A0066 | Petite-Île | UD (U) | 2024-11-04 | 1 (1) | 94 | 1 | 32 | 1 | 2.947 | 1.0 | SDP autorisée 94 m² (plancher, = 82 m² hab.×1.15) > SDP max LABUSE 32 m² |
| 97440524A0075 | Petite-Île | UC (U) | 2025-02-18 | 2 (2) | 1745 | 24 | 1647 | 15 | 1.059 | 1.6 | réunion de 2 parcelle(s) ; 24 logements autorisés > 15 estimés LABUSE |
| 97440524A0086 | Petite-Île | UD (U) | 2025-01-24 | 1 (1) | 121 | 1 | 62 | 1 | 1.948 | 1.0 | SDP autorisée 121 m² (plancher, = 105 m² hab.×1.15) > SDP max LABUSE 62 m² |
| 97440524A0088 | Petite-Île | N (N) | 2024-12-30 | 1 (1) | 114 | 1 | 65 | 1 | 1.752 | 1.0 | SDP autorisée 114 m² (plancher, = 99 m² hab.×1.15) > SDP max LABUSE 65 m² |
| 97440524A0095 | Petite-Île | UD (U) | 2025-01-27 | 1 (1) | 146 | 1 | 84 | 1 | 1.739 | 1.0 | SDP autorisée 146 m² (plancher, = 127 m² hab.×1.15) > SDP max LABUSE 84 m² |
| 97440525A0006 | Petite-Île | UD (U) | 2025-03-31 | 1 (1) | 159 | 1 | 88 | 1 | 1.803 | 1.0 | SDP autorisée 159 m² (plancher, = 138 m² hab.×1.15) > SDP max LABUSE 88 m² |
| 97440525A0007 | Petite-Île | UC (U) | 2025-03-31 | 2 (2) | 246 | 3 | 172 | 2 | 1.431 | 1.5 | réunion de 2 parcelle(s) ; SDP autorisée 246 m² (plancher, = 214 m² hab.×1.15) > SDP max LABUSE 172 m² ; 3 logements aut |
| 97440525A0010 | Petite-Île | UB (U) | 2025-04-11 | 1 (1) | 112 | 1 | 100 | 1 | 1.115 | 1.0 | SDP autorisée 112 m² (plancher, = 97 m² hab.×1.15) > SDP max LABUSE 100 m² |
| 97440525A0014 | Petite-Île | UC (U) | 2025-07-16 | 1 (1) | 108 | 1 | 83 | 1 | 1.302 | 1.0 | SDP autorisée 108 m² (plancher, = 94 m² hab.×1.15) > SDP max LABUSE 83 m² |
| 97440525A0021 | Petite-Île | UD (U) | 2025-06-06 | 1 (1) | 120 | 1 | 37 | 1 | 3.232 | 1.0 | SDP autorisée 120 m² (plancher, = 104 m² hab.×1.15) > SDP max LABUSE 37 m² |
| 97440525A0026 | Petite-Île | Nce (N) | 2025-08-13 | 1 (1) | 139 | 2 | 34 | 1 | 4.093 | 2.0 | SDP autorisée 139 m² (plancher, = 121 m² hab.×1.15) > SDP max LABUSE 34 m² ; 2 logements autorisés > 1 estimés LABUSE |
| 97440525A0033 | Petite-Île | N (N) | 2025-08-13 | 1 (1) | 140 | 3 | 144 | 1 | 0.974 | 3.0 | 3 logements autorisés > 1 estimés LABUSE |
| 97440525A0041 | Petite-Île | UD (U) | 2025-07-16 | 1 (1) | 150 | 1 | 44 | 1 | 3.398 | 1.0 | SDP autorisée 150 m² (plancher, = 130 m² hab.×1.15) > SDP max LABUSE 44 m² |
| 97440525A0045 | Petite-Île | UD (U) | 2025-07-16 | 1 (1) | 89 | 1 | 63 | 1 | 1.406 | 1.0 | SDP autorisée 89 m² (plancher, = 77 m² hab.×1.15) > SDP max LABUSE 63 m² |
| … | … | … | … | … | … | … | … | … | … | … | (+829 autres de même cause, voir CSV) |

### non constructible LABUSE — 158 permis

| permit_id | commune | zone(s) | date | n parc. (servies) | SDP aut. (planch.) m² | logts aut. | SDP max LABUSE m² | logts LABUSE | ratio SDP | ratio logts | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 97440324A0047 | Entre-Deux | N (N) | 2025-03-31 | 1 (1) | 148 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:N) ; LABUSE classe la (les) parcelle(s) non const |
| 97440324A0052 | Entre-Deux | Aba (A) | 2025-03-31 | 1 (1) | 90 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Aba) ; LABUSE classe la (les) parcelle(s) non con |
| 97440623A0013 | La Plaine-des-Palmistes | A (A) | 2023-06-22 | 1 (1) | 153 | 3 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:A) ; LABUSE classe la (les) parcelle(s) non const |
| 97440623A0040 | La Plaine-des-Palmistes | Uc (U) | 2023-06-05 | 1 (1) | 87 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (terrain_exigu) ; LABUSE classe la (les) parcelle(s) non constructible(s) |
| 97440624A0002 | La Plaine-des-Palmistes | Uc (U) | 2024-02-27 | 1 (1) | 100 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (terrain_exigu) ; LABUSE classe la (les) parcelle(s) non constructible(s) |
| 97440624A0064 | La Plaine-des-Palmistes | Nto (N) | 2024-12-04 | 1 (1) | 161 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Nto) ; LABUSE classe la (les) parcelle(s) non con |
| 97440624A0087 | La Plaine-des-Palmistes | Ur (U) | 2025-01-16 | 1 (1) | 61 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (terrain_exigu) ; LABUSE classe la (les) parcelle(s) non constructible(s) |
| 9744062510040 | La Plaine-des-Palmistes | Nto (N) | 2025-08-06 | 1 (1) | 285 | 3 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Nto) ; LABUSE classe la (les) parcelle(s) non con |
| 9744062510099 | La Plaine-des-Palmistes | Nto (N) | 2026-04-14 | 1 (1) | 80 | 2 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Nto) ; LABUSE classe la (les) parcelle(s) non con |
| 97440124A0059 | Les Avirons | A (A) | 2025-03-25 | 2 (2) | 163 | 1 | 0 | 0 | inf | inf | réunion de 2 parcelle(s) ; 2 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:A) ; LABUSE classe la  |
| 9744012520037 | Les Avirons | A (A) | 2025-10-06 | 3 (3) | 53 | 1 | 0 | 0 | inf | inf | réunion de 3 parcelle(s) ; 3 parcelle(s) non constructible(s) chez LABUSE (terrain_exigu, zone_non_constructible:A) ; LA |
| 97440919A0265 | Saint-André | A (A) | 2020-05-18 | 1 (1) | 0 | 1 | 0 | 0 |  | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:A) ; LABUSE classe la (les) parcelle(s) non const |
| 97440921A0058 | Saint-André | A (A) | 2021-05-10 | 1 (1) | 156 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:A) ; LABUSE classe la (les) parcelle(s) non const |
| 97440922A0072 | Saint-André | UD (U) | 2022-07-22 | 1 (1) | 205 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (terrain_exigu) ; LABUSE classe la (les) parcelle(s) non constructible(s) |
| 97440925A0134 | Saint-André | A (A) | 2025-12-12 | 1 (1) | 103 | 3 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:A) ; LABUSE classe la (les) parcelle(s) non const |
| 97440925A0226 | Saint-André | A (A) | 2026-04-30 | 1 (1) | 103 | 3 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:A) ; LABUSE classe la (les) parcelle(s) non const |
| 97441020A0089 | Saint-Benoît | A (A) | 2020-10-08 | 1 (1) | 98 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:A) ; LABUSE classe la (les) parcelle(s) non const |
| 97441020A0096 | Saint-Benoît | Ns46 (N) | 2021-05-11 | 1 (1) | 93 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns46) ; LABUSE classe la (les) parcelle(s) non co |
| 97441020A0111 | Saint-Benoît | Ns32 (N) | 2021-02-23 | 1 (1) | 115 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns32) ; LABUSE classe la (les) parcelle(s) non co |
| 97441020A0190 | Saint-Benoît | Ns45 (N) | 2021-03-08 | 1 (1) | 76 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns45) ; LABUSE classe la (les) parcelle(s) non co |
| 97441020A0200 | Saint-Benoît | A (A) | 2021-03-09 | 1 (1) | 528 | 3 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:A) ; LABUSE classe la (les) parcelle(s) non const |
| 9744102100325 | Saint-Benoît | Ns36 (N) | 2022-04-22 | 1 (1) | 106 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns36) ; LABUSE classe la (les) parcelle(s) non co |
| 9744102100326 | Saint-Benoît | Ns41 (N) | 2022-07-07 | 1 (1) | 168 | 2 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns41) ; LABUSE classe la (les) parcelle(s) non co |
| 9744102100350 | Saint-Benoît | A|Ns33 (A|N) | 2022-05-23 | 2 (2) | 61 | 1 | 0 | 0 | inf | inf | réunion de 2 parcelle(s) ; 2 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:A, zone_non_constructi |
| 97441021A0072 | Saint-Benoît | ?|Ub (U) | 2021-06-25 | 2 (1) | 118 | 1 | 0 | 0 | inf | inf | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; 1 parcelle(s) non constructible(s) chez |
| 97441021A0082 | Saint-Benoît | Ns28 (N) | 2021-08-10 | 1 (1) | 91 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns28) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0112 | Saint-Benoît | A (A) | 2021-07-20 | 1 (1) | 93 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:A) ; LABUSE classe la (les) parcelle(s) non const |
| 97441021A0116 | Saint-Benoît | Ns38 (N) | 2021-12-16 | 1 (1) | 114 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns38) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0183 | Saint-Benoît | Ns21 (N) | 2021-10-25 | 1 (1) | 216 | 3 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns21) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0214 | Saint-Benoît | Ns21 (N) | 2021-12-15 | 1 (1) | 114 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns21) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0217 | Saint-Benoît | Ns32 (N) | 2022-03-24 | 2 (2) | 138 | 4 | 0 | 0 | inf | inf | réunion de 2 parcelle(s) ; 2 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns32) ; LABUSE classe  |
| 97441021A0220 | Saint-Benoît | Ns41 (N) | 2021-11-26 | 1 (1) | 124 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns41) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0221 | Saint-Benoît | Ns26 (N) | 2022-04-07 | 1 (1) | 60 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns26) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0230 | Saint-Benoît | Ns22 (N) | 2022-01-19 | 1 (1) | 109 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns22) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0236 | Saint-Benoît | Ns34 (N) | 2022-03-21 | 1 (1) | 89 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns34) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0237 | Saint-Benoît | Ns41 (N) | 2022-04-08 | 1 (1) | 120 | 2 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns41) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0241 | Saint-Benoît | N (N) | 2022-03-24 | 1 (1) | 143 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:N) ; LABUSE classe la (les) parcelle(s) non const |
| 97441021A0254 | Saint-Benoît | Ns34 (N) | 2022-06-01 | 1 (1) | 89 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns34) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0259 | Saint-Benoît | Ns40 (N) | 2023-04-03 | 1 (1) | 92 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns40) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0261 | Saint-Benoît | Ns21 (N) | 2022-03-10 | 1 (1) | 82 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns21) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0262 | Saint-Benoît | Ns21 (N) | 2021-12-16 | 1 (1) | 82 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns21) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0263 | Saint-Benoît | A (A) | 2022-03-14 | 1 (1) | 117 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:A) ; LABUSE classe la (les) parcelle(s) non const |
| 97441021A0265 | Saint-Benoît | Ns41 (N) | 2022-01-18 | 1 (1) | 114 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns41) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0271 | Saint-Benoît | Ns40 (N) | 2022-04-07 | 1 (1) | 94 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns40) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0275 | Saint-Benoît | Ns28 (N) | 2022-01-24 | 1 (1) | 139 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns28) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0277 | Saint-Benoît | Ns28 (N) | 2022-07-08 | 1 (1) | 131 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns28) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0279 | Saint-Benoît | A (A) | 2022-04-08 | 1 (1) | 170 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:A) ; LABUSE classe la (les) parcelle(s) non const |
| 97441021A0281 | Saint-Benoît | Ns34 (N) | 2022-05-23 | 1 (1) | 138 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns34) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0282 | Saint-Benoît | Ns21 (N) | 2022-01-27 | 1 (1) | 171 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns21) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0288 | Saint-Benoît | Ns21 (N) | 2022-01-27 | 1 (1) | 159 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns21) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0296 | Saint-Benoît | Ns34 (N) | 2022-05-03 | 1 (1) | 138 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns34) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0304 | Saint-Benoît | Ns21 (N) | 2022-07-04 | 1 (1) | 37 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns21) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0308 | Saint-Benoît | Ns40 (N) | 2022-07-28 | 1 (1) | 75 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns40) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0312 | Saint-Benoît | Ns46 (N) | 2022-05-05 | 1 (1) | 87 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns46) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0320 | Saint-Benoît | Ns41 (N) | 2022-03-10 | 1 (1) | 77 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns41) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0323 | Saint-Benoît | Ns41 (N) | 2022-03-10 | 1 (1) | 118 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns41) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0329 | Saint-Benoît | A (A) | 2023-07-10 | 1 (1) | 113 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:A) ; LABUSE classe la (les) parcelle(s) non const |
| 97441021A0334 | Saint-Benoît | Ns21 (N) | 2022-11-14 | 1 (1) | 92 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns21) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0336 | Saint-Benoît | Ns21 (N) | 2022-07-07 | 1 (1) | 103 | 1 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Ns21) ; LABUSE classe la (les) parcelle(s) non co |
| 97441021A0339 | Saint-Benoît | Acor (A) | 2022-05-03 | 1 (1) | 171 | 3 | 0 | 0 | inf | inf | 1 parcelle(s) non constructible(s) chez LABUSE (zone_non_constructible:Acor) ; LABUSE classe la (les) parcelle(s) non co |
| … | … | … | … | … | … | … | … | … | … | … | (+98 autres de même cause, voir CSV) |

### réunion de parcelles incomplète — 25 permis

| permit_id | commune | zone(s) | date | n parc. (servies) | SDP aut. (planch.) m² | logts aut. | SDP max LABUSE m² | logts LABUSE | ratio SDP | ratio logts | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 9744072600031 | Le Port | ?|Ub (U) | 2026-06-17 | 3 (2) | 171 | 1 | 132 | 2 | 1.298 | 0.5 | réunion de 3 parcelle(s) ; 1/3 parcelle(s) non servie(s) (disparue/redécoupée) ; 1 parcelle(s) non constructible(s) chez |
| 97442223A0365 | Le Tampon | Uc (U) | 2023-12-06 | 2 (1) | 164 | 2 | 132 | 2 | 1.246 | 1.0 | réunion de 2 parcelle(s) ; projet sur plusieurs parcelles dont certaines ne sont pas servies → somme des capacités LABUS |
| 97442223A0572 | Le Tampon | ?|Nco|Uc (N|U) | 2024-07-11 | 3 (2) | 160 | 1 | 121 | 3 | 1.321 | 0.333 | réunion de 3 parcelle(s) ; 1/3 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 9744222500200 | Le Tampon | ?|Ud (U) | 2025-09-12 | 2 (1) | 197 | 1 | 153 | 2 | 1.285 | 0.5 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 9744232600024 | Les Trois-Bassins | 1AUb|? (AU) | 2026-06-24 | 2 (1) | 124 | 1 | 78 | 1 | 1.592 | 1.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97440523A0047 | Petite-Île | ?|A (A) | 2023-08-18 | 2 (1) | 171 | 1 | 80 | 1 | 2.142 | 1.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97440524A0082 | Petite-Île | ?|UB (U) | 2025-01-24 | 2 (1) | 103 | 1 | 16 | 1 | 6.469 | 1.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97440922A0129 | Saint-André | ?|UB (U) | 2022-09-13 | 2 (1) | 82 | 1 | 35 | 1 | 2.333 | 1.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97440923A0100 | Saint-André | 1AUd|? (AU) | 2023-11-06 | 2 (1) | 292 | 3 | 42 | 1 | 6.955 | 3.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97440924A0209 | Saint-André | ?|UC (U) | 2025-06-11 | 3 (1) | 4206 | 62 | 2184 | 25 | 1.926 | 2.48 | réunion de 3 parcelle(s) ; 2/3 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97441313A0103 | Saint-Leu | ?|UC (U) | 2013-09-10 | 2 (1) | 603 | 5 | 83 | 1 | 7.26 | 5.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97441314A0192 | Saint-Leu | ?|UD (U) | 2014-12-30 | 2 (1) | 155 | 1 | 37 | 1 | 4.196 | 1.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97441315A0205 | Saint-Leu | ?|UD (U) | 2016-04-27 | 2 (1) | 166 | 2 | 21 | 1 | 7.886 | 2.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97441317A0013 | Saint-Leu | ?|UD (U) | 2017-06-08 | 2 (1) | 152 | 2 | 116 | 1 | 1.309 | 2.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97441317A0243 | Saint-Leu | ?|UA (U) | 2018-01-03 | 3 (2) | 152 | 1 | 106 | 2 | 1.432 | 0.5 | réunion de 3 parcelle(s) ; 1/3 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97441317A0255 | Saint-Leu | ?|UB (U) | 2018-04-10 | 2 (1) | 164 | 1 | 101 | 1 | 1.628 | 1.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97441318A0019 | Saint-Leu | ?|UC (U) | 2018-09-27 | 2 (1) | 3542 | 43 | 263 | 2 | 13.468 | 21.5 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97441318A0231 | Saint-Leu | ?|N (N) | 2019-01-14 | 3 (1) | 121 | 1 | 96 | 1 | 1.258 | 1.0 | réunion de 3 parcelle(s) ; 2/3 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97441319A0166 | Saint-Leu | ?|UD (U) | 2019-09-23 | 2 (1) | 171 | 2 | 18 | 1 | 9.519 | 2.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97441320A0025 | Saint-Leu | ?|UC (U) | 2020-07-29 | 2 (1) | 106 | 1 | 44 | 1 | 2.405 | 1.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97441321A0032 | Saint-Leu | ?|UC (U) | 2022-04-19 | 3 (1) | 1078 | 12 | 681 | 6 | 1.582 | 2.0 | réunion de 3 parcelle(s) ; 2/3 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97441321A0143 | Saint-Leu | ?|UD (U) | 2021-12-17 | 2 (1) | 223 | 3 | 26 | 1 | 8.581 | 3.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97441322A0149 | Saint-Leu | ?|UC (U) | 2022-12-06 | 2 (1) | 288 | 2 | 129 | 1 | 2.229 | 2.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 97441323A0002 | Saint-Leu | ?|UD (U) | 2023-04-17 | 2 (1) | 153 | 1 | 101 | 1 | 1.514 | 1.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |
| 9744152500486 | Saint-Paul | ?|U5b (U) | 2026-03-11 | 2 (1) | 1336 | 18 | 76 | 1 | 17.583 | 18.0 | réunion de 2 parcelle(s) ; 1/2 parcelle(s) non servie(s) (disparue/redécoupée) ; projet sur plusieurs parcelles dont cer |

### surface Sit@del aberrante — 1 permis

| permit_id | commune | zone(s) | date | n parc. (servies) | SDP aut. (planch.) m² | logts aut. | SDP max LABUSE m² | logts LABUSE | ratio SDP | ratio logts | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 9744182500191 | Sainte-Marie | UD (U) | 2026-01-13 | 1 (1) | 493 | 1 | 136 | 1 | 3.628 | 1.0 | surf_hab 429 m² / 1 logt = 429 m²/logt (invraisemblable, erreur de la source Sit@del) |

---

## 5. Limites honnêtes

1. **Grain SDP ≠ grain permis.** Sit@del publie une surface **habitable** (`surf_hab_creee`), LABUSE une **surface de plancher** (brute). On convertit habitable → plancher (× 1,15) mais le coef est une moyenne : un projet avec beaucoup de circulations/parkings aura un vrai coef supérieur, donc le ratio SDP est **légèrement conservateur** (tend à sous-dire les dépassements).
2. **Réunion de parcelles redécoupée.** Quand un permis a été autorisé puis le foncier redécoupé, `idu_codes` peut pointer des parcelles **disparues** : la somme des capacités LABUSE est alors incomplète et le ratio gonfle artificiellement. Ces cas sont **marqués** (`n_parcelles_servies < n_parcelles`) et classés « réunion de parcelles incomplète » ou « parcelle non servie », jamais comptés comme une erreur de calibrage.
3. **Surfaces non-logement / mixtes.** Un PC « logements » peut inclure du commerce/tertiaire au RDC : `surf_hab_creee` ne compte que l'habitable, mais `nb_lgt` reste le nombre de logements — la comparaison logements est la plus fiable pour ces projets.
4. **Surfaces source aberrantes.** Quelques permis Sit@del portent une `surf_hab` invraisemblable (> 400 m² habitables / logement) : erreur de saisie de la source, **isolée** en cause « surface Sit@del aberrante » et non imputée à LABUSE.
5. **Permis pré-PLU résiduels.** On borne par la **date réelle d'autorisation** ; si cette date est nulle on retombe sur `date_depot`. Un permis déposé juste après le PLU mais instruit sous l'ancien règlement peut subsister — effet de bord assumé, minoritaire.
6. **N réel.** Saint-Leu (PLU 2007), Saint-André (2019) et Saint-Benoît (2020) pèsent la majorité des permis (millésimes anciens → longue fenêtre) ; les communes à PLU 2025-2026 n'ont que quelques permis postérieurs. Les médianes par commune de ces dernières reposent sur de petits effectifs (lire la colonne « permis »).
7. **Capacité = SDP MAX, pas résiduelle.** On compare l'autorisé à la SDP **max** du gabarit (ce que la parcelle peut porter au total), pas à la SDP **résiduelle** (max − existant). Un permis sur terrain déjà partiellement bâti peut donc être « couvert » par la SDP max sans que le résiduel servi (plus petit) ne l'eût prédit — choix assumé : on teste le **gabarit**, pas le reste à bâtir.

