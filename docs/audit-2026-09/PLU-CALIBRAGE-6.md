# PLU-CALIBRAGE-6 — les 95 `propose` numériques qui nourrissent la SDP

**Date : 21/09/2026 · Branche : `feat/plu-calibrage-6` (base main `8564b1e7`) · worktree `~/Desktop/labuse-plu6`.**
**Rien de mergé, aucun `residuel-serve`, rien de servi ne change.** `q_v11_m137` reste servi.

Décision Vic (SCORING-5) : on **valide** plutôt que couper — un résiduel calculé sur du non-validé
casse la règle « chaque chiffre est sourcé ». Ce mandat source (article + page + citation) les
feuilles `propose` numériques que la BASE du calcul de SDP lisait, pose le garde-fou validées-only,
et mesure l'impact avant `residuel-serve`.

**Décision de périmètre (Vic, en cours de mandat)** : le §2 valide **les 95 `propose` numériques
complètes** — le §6 « hors mandat » exclut les **55 non-numériques** (feuilles `absent`/`plage`/sans
valeur, qui ne branchent déjà pas), **pas** les 31 pleine-terre/stationnement numériques. Réconcilié
au chiffre : `150 propose = 95 numériques (branchent la SDP) + 55 non-numériques`.

Livrables : ce rapport · `config/plu_destinations/*.yaml` (72 feuilles passées `valide`) ·
`src/labuse/faisabilite/{zonage,engine,residuel}.py` (garde) · `tests/test_plu_calibrage6_garde.py` ·
scripts et données de mesure sous `captures/plu-calibrage6/` (jetables : `TABLE-95.csv/json`,
`SONDAGE-10.md`, `RELECTURE.json`, `applied_log.json`, `impact.py`, `impact_resultat.json`).

---

## 1. Inventaire des 95 feuilles `propose` numériques (constat SCORING-5-RETOUR §2)

La base du calcul de SDP lit `zonage._val` (`_zone_rules_from_regles`) : **avant ce mandat, `_val`
renvoyait la valeur numérique de TOUTE feuille, quel que soit son statut** — donc 95 feuilles
`propose` numériques branchaient la SDP (l'overlay `_calibrage_overlay`, lui, était déjà
validées-only). Réconciliation exacte du décompte (`config/plu_destinations/974*.yaml`) :

| champ | propose numériques (branchent) |
|---|---|
| hauteur.faitage | 10 |
| hauteur.egout | 9 |
| emprise_sol.ces | 11 |
| retraits.voie | 21 |
| retraits.limites_separatives | 13 |
| pleine_terre.pct | 18 |
| stationnement.par_logement | 13 |
| **TOTAL** | **95** |

Les 95 se répartissent sur **9 communes**, **19 592** parcelles dominantes concernées (une feuille
= une (commune, zone, champ) ; plusieurs feuilles peuvent porter la même zone). Comptage parcelles =
zone dominante par surface (`parcel_zone_plu`, la même que l'écran). Table complète (commune · zone ·
champ · valeur gravée · provenance · nb parcelles) : **`captures/plu-calibrage6/TABLE-95.csv`**.

Par commune : Saint-Joseph 48 · Sainte-Marie 18 · Le Port 10 · Sainte-Rose 6 · Saint-Pierre 5 ·
Saint-Paul 4 · Petite-Île 2 · Bras-Panon 1 · La Possession 1.

**Provenance** (pourquoi restées `propose` après PLU-CALIBRAGE-5) : 81 « valeur X absente de la
citation (harmonisation ≠ texte) » — la valeur venait de l'ancien système, jamais littéralement
retrouvée ; 14 « attribution douteuse (citation sous secteur None) ». Beaucoup sont des renvois
`1AU<n><indice> → U<n><indice>` (la règle vit dans l'article de la zone U).

---

## 2. Validation une par une (même méthode que PLU-CALIBRAGE-5)

Un agent interne par commune a relu chaque feuille contre le **règlement PDF authentique**
(`data/plu_reglements/974xx_*.pdf`), suivi les renvois `1AU→U`, rattaché la valeur au bon secteur,
et retenu la **sous-chaîne littérale** portant le nombre. **Garde anti-invention** (vérifiée
mécaniquement, 0 échec sur les 71 validée/corrigée) : le nombre retenu doit apparaître
LITTÉRALEMENT dans la citation ; sinon la feuille RESTE `propose`, sans valeur inventée.

**Relecture indépendante** (`captures/plu-calibrage6/RELECTURE.json`) : 38 décisions re-contrôlées
au PDF (les 13 corriger + l'absent + 12 validee échantillonnées + les 23 propose pour faux
négatifs) → **38 accords, 0 désaccord, 0 faux négatif**.

### Résultat : 58 validée · 13 corrigée · 1 absente · 23 restées propose

| champ | validée | corrigée | absente | propose |
|---|---:|---:|---:|---:|
| emprise_sol.ces | 10 | 0 | 0 | 1 |
| hauteur.egout | 9 | 0 | 0 | 0 |
| hauteur.faitage | 10 | 0 | 0 | 0 |
| pleine_terre.pct | 9 | 0 | 1 | 8 |
| retraits.limites_separatives | 4 | 7 | 0 | 2 |
| retraits.voie | 9 | 0 | 0 | 12 |
| stationnement.par_logement | 7 | 6 | 0 | 0 |
| **TOTAL** | **58** | **13** | **1** | **23** |

Par commune : Saint-Joseph 42v/5c · Sainte-Marie 16v/1c · Sainte-Rose 6c · Bras-Panon 1c ·
Le Port 1 absente/9 propose · Saint-Paul 4 propose · Saint-Pierre 5 propose · Petite-Île 2 propose ·
La Possession 1 propose.

**Bilan `propose` : 150 → 78** (95 numériques : 72 résolues, 23 restées ; les 55 non-numériques,
hors mandat §6, sont intactes). `valide` : 1825 → 1897.

### Les 13 corrigées (valeur harmonisée FAUSSE → valeur réelle du texte) — à signaler à Vic

Toutes confirmées par la relecture au PDF. **Ce sont des valeurs servies qui changent** (mais impact
SDP nul dans l'échantillon, cf. §4 — ces zones sont majoritairement déjà non calculables) :

- `retraits.limites_separatives` — 7 corrections vers le vrai plancher : Bras-Panon Uba 4→**3** ·
  Saint-Joseph 1AU3 5,5→**3**, 1AU3a 4→**3**, 1AU5 3,5→**3**, 1AU6 6→**3**, 1AU6c 7,5→**3** (art. U 7.2
  « H/2, minimum 3 mètres ») · Sainte-Marie 1AUep 8→**4** (zone activités, « inférieure à 4 mètres »).
- `stationnement.par_logement` — 6 corrections 2→**1,5** (Sainte-Rose Ua/Ub/Uc/Ud, 1AUa/1AUc) : le
  barème résidentiel est ventilé (1 place <50 m² / **1,5 place ≥50 m²**) ; le « 2 » gravé n'existe
  nulle part dans le règlement. Distinct de Saint-Joseph, dont le barème est **plat** (« 2 places
  minimum par logement », validé à 2). Le stationnement ne détermine pas la SDP.

### Les 23 restées `propose` (0 faux négatif — impossibles à valider sans inventer)

| cause | feuilles | parcelles dominantes |
|---|---:|---:|
| recul « à l'alignement »/en limite (=0 non littéral ; ou plancher en annexe/RN) | 14 | 5 089 |
| pleine-terre **composée** (« X % éco-aménageable **dont 50 % de pleine terre** » → produit 15/10 % jamais littéral) | 8 | 7 726 |
| CES exprimé en **m²/ha** (densité surfacique, pas un % — Saint-Pierre Uep) | 1 | 12 |

**1 absente** : Le Port 1AUem (→ Ue 11.1) régit 20 % éco-aménageable **sans** clause de pleine terre
(les autres zones l'ont) → silence prouvé sur la pleine terre ; la valeur gravée 20 recopiait à tort
le % éco-aménageable.

### Sondage de 10 pour Vic

`captures/plu-calibrage6/SONDAGE-10.md` (tirage `random.seed(6)` sur les 71 validée/corrigée) :
chaque règle avec valeur retenue + article/page + **citation verbatim** vérifiée. Extrait :

1. Saint-Joseph 1AU3a hauteur.faitage = **9** (renvoi 1AU3a→U3a) · Art. U3 10.2
2. Sainte-Marie 1AUep hauteur.faitage = **16** (activités) · 3. Saint-Joseph 1AU5vi limites = **3**
4. Saint-Joseph 1AU3 pleine_terre = **15 %** (règlement direct, ≠ Le Port composé)
5. Bras-Panon Uba limites **corrigée 4→3** · 6. Saint-Joseph 1AU5 pleine_terre = **35 %**
7. Sainte-Marie 1AUc stationnement = **1,5** · 8-9. Saint-Joseph 1AU6c/1AU5 voie = **4**
10. Sainte-Marie 1AUb hauteur.egout = **12**

---

## 3. Garde-fou : la base du calcul de SDP devient validées-only (code, sur la branche)

`src/labuse/faisabilite/` :

- **`zonage._val`** : validées-only. Une feuille `propose` renvoie `a_verifier` (non numérique →
  n'entre PAS dans la SDP), comme `_calibrage_overlay`. C'est le trou de SCORING-5-RETOUR §2 fermé.
  Idem `_stat_from_regles` (la valeur numérique ne branche que si `valide` ; l'exemption, non
  numérique, reste reconnue).
- **`zonage._regles_sdp_non_validees` + `_zone_regle_non_validee`** : si une zone calibrée garde une
  feuille SDP-**déterminante** `propose` avec une valeur (hauteur, emprise CES, reculs, pleine terre),
  `resolve_zone` porte `regle_non_validee` et **ne retombe PAS sur l'estimation générique** (ce serait
  une valeur par défaut). Le stationnement est **exclu** du déclencheur : il ne détermine pas
  `surface_plancher_m2` (il borne le scénario « logements au sol »).
- **`engine.estimate_capacity`** : sort AVANT tout calcul → `constructible=False`, cause
  **`regle_plu_non_validee`** ; aucun recul « hypothèse prudente », aucune hauteur générique, aucun
  chiffre non sourcé n'entre dans la SDP.
- **`residuel._cause_indisponible`** : mappe `regle_plu_non_validee:<zone>`, SDP écrite = 0 (« le
  moteur ne sait pas », pas un droit).

**Test** `tests/test_plu_calibrage6_garde.py` (9 cas, verts) — casse si la base relit une règle non
validée : `_val` propose→`a_verifier` ; détection des feuilles déclencheuses (stationnement exclu) ;
`resolve_zone` d'une zone à hauteur `propose` → `regle_non_validee` + moteur non calculable **sans
repli générique** ; contrôle positif (mêmes feuilles `valide` → la zone se calcule).

Suite de non-régression (sans DB) : `test_faisabilite`, `test_plu_calibrage2_branchement`,
`test_mn_faisabilite`, `test_prospect`, `test_plu_calibrage_lot2`, `test_plu_calibrage4_zonage`,
`test_plu_calibrage6_garde` = **71 verts**. Deux cas de `test_faisabilite` repointés (U3a/U6a,
désormais non calculables car leur recul de voie reste `propose`) vers U1c (calculable) — l'intention
du test (contrainte pleine terre / modulation de pente) est préservée. Aucune régression de code
(les échecs restants du sweep sont tous « role labuse » de la base de test absente + `test_retours11f4`
pré-existant).

---

## 4. Mesure d'impact (lecture seule, `captures/plu-calibrage6/impact.py`)

Comparaison parcelle par parcelle, dans le MÊME process, état **A** (avant : `_val` lit les propose,
pas de garde) vs état **C** (après : garde + 72 validations appliquées), sur un échantillon
**reproductible** (id-ordonné, ≤40/zone) des 29 zones affectées.

**Échantillon = 923 parcelles** :

| transition | n | part |
|---|---:|---:|
| calculable **→ non calculable** (règle PLU non validée) | 464 | 50 % |
| déjà non calculable (autre cause : terrain exigu, zone A/N dominante…) — **pas un changement net** | 389 | 42 % |
| inchangée (calculée) | 70 | 8 % |
| capacité **changée de valeur** (corrections) | **0** | 0 % |

Les corrections `limites_separatives`/`stationnement` ne changent **aucune** SDP résiduelle servie
dans l'échantillon (ces zones — 1AU de Saint-Joseph surtout — sont majoritairement déjà non
calculables, et le stationnement ne pilote pas la SDP).

**Extrapolation** (taux d'échantillon par zone × taille réelle des 22 zones NC) : **~8 471 parcelles
passent nouvellement « non calculable — règle PLU non validée »** (sur 12 696 parcelles dominantes de
ces zones ; le reste était déjà non calculable) :

| commune | ~parcelles nouvellement NC | / parcelles des zones NC |
|---|---:|---:|
| Le Port | ~4 950 | 8 112 |
| Saint-Pierre | ~2 043 | 2 758 |
| Saint-Paul | ~1 090 | 1 356 |
| La Possession | ~172 | 215 |
| Petite-Île | ~118 | 131 |
| Saint-Joseph | ~83 | 98 |
| Sainte-Marie | ~14 | 26 |
| **TOTAL** | **~8 471** | **12 696** |

**Comparaison aux 16 963 NC « zone PLU non résolue » connues** : +~8 471 ≈ **+50 %** de non
calculables. **Mais la quasi-totalité relève de deux limites de SCHÉMA, pas de règles réellement
non sourcées** (cf. §5) : Le Port ~4 950 = pleine-terre **composée** ; Saint-Pierre/Saint-Paul/La
Possession/Petite-Île/Saint-Joseph/Sainte-Marie ~3 520 = recul **« à l'alignement »** (=0).

---

## 5. Ce qui reste bloquant avant `residuel-serve`

1. **Process frais obligatoire (lru_cache)** — `_calibrage_overlay` et `_zonage_doc` sont en
   `lru_cache` à vie du process (`zonage.py`) ; toute édition YAML avant un run impose un
   **redémarrage** (sinon l'ancien calibrage est servi). L'édition YAML de ce mandat est déjà faite ;
   le prochain `compute-residuel --ile --new-run` doit tourner en **process neuf**.

2. **Les deux limites de schéma qui génèrent ~8 471 NC — décision Vic** (les valider réduirait
   fortement la NC ; sinon acter la NC honnête) :
   - **Recul « à l'alignement » (=0)** — 14 feuilles, ~3 520 parcelles (centres urbains :
     Saint-Pierre Up/Ucv/Uazp, Saint-Paul U3a/U4a/U5a/U6a…). La règle EST au texte
     (« implantées à l'alignement »), mais « 0 » n'est pas une sous-chaîne → la garde anti-invention
     la laisse `propose` → zone non calculable. **Piste** : autoriser une forme validée
     `retraits.voie: {alignement: true, min_m: 0}` sourcée par la phrase d'alignement (0 assumé,
     pas inventé).
   - **Pleine-terre composée** — 8 feuilles, ~4 950 parcelles (Le Port surtout : « X % éco-aménageable
     **dont au moins 50 % de pleine terre** »). Le produit (15/10 %) n'est jamais littéral. **Piste** :
     schéma `pleine_terre: {eco_pct: 30, dont_pleine_terre_pct: 50}` (deux nombres littéraux) au lieu
     d'un `pct` dérivé.
   - Cas résiduel : Saint-Pierre Uep, CES exprimé en **m²/ha** (12 parcelles) — hors modèle CES-%.

3. **Ces 8 471 NC sont un plancher pédagogique** : elles remplacent une SDP qui, aujourd'hui,
   utilisait soit un défaut (recul/hauteur prudente), soit un produit non sourcé (pleine terre) — donc
   « non calculable, motif porté » est plus juste que le chiffre actuel. À trancher **avant** de figer
   les bandes de score (SCORING-5 §3 : les bandes sont à re-caler post-calibrage).

4. **Rappel chaîne (SCORING-5-RETOUR §2, inchangé)** : `compute-residuel --ile --new-run "<label>"`
   (process frais) → comparer au run 2 → `residuel-serve <seq>` (geste Vic séparé, atomique). Aucun
   de ces gestes n'est fait ici.

## 6. Hors mandat (respecté)

Les **55 `propose` non-numériques** (feuilles `absent`/`plage`/sans valeur — majoritairement
stationnement et pleine-terre) : intactes, elles ne branchent déjà pas. `residuel-serve`, scoring,
tout merge, toute bascule : non touchés.
