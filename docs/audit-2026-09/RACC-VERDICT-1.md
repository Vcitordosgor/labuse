# RACC-VERDICT-1 — Que faire de `feat/raccordement-1`

**Nature : audit lecture seule. Aucun merge, aucun cherry-pick, aucune modification de main.**
Worktree `~/Desktop/labuse-raccverdict` sur branche jetable `diag/racc-verdict` depuis `origin/main`.

## Étape 0 — état

- `pwd` du dépôt principal = `/Users/openclaw/Desktop/labuse`. Arbre **propre** (`git status --porcelain` vide).
- `git fetch --all --prune` fait. `main` local == `origin/main` == `a272d4a5` (ahead/behind = `0 / 0`).
- Cible d'audit : `feat/raccordement-1` == `origin/feat/raccordement-1` == **`e2818ae5`** (conforme au mandat).
- Base de diff : **`origin/main` (`a272d4a5`)**, `git diff origin/main...feat/raccordement-1`.
- Merge-base = `a7079c5e` (65 commits d'écart). Le rapport est écrit dans ce worktree, commité sur `diag/racc-verdict`.

## La lignée — le fait qui décide tout

```
origin/main (a272d4a5) ─── couches-tuyau MERGÉ (403526eb) + COUCHES-RECETTE + COUCHES-REGISTRE
   │                       + EXPORTS-REBRANCHEMENT-1 + DONNEES-1 + COMMUNE-RANGEMENT-2
   │                       → moteur déclaratif + tuiles MVT, ÉVOLUÉ
   │
   └─ merge-base a7079c5e ── 65 commits RACCORDEMENT-1 (lot 0→3, strip 1→13,
                             GEOM-FIX-1, COUCHES-52, GEOM-FINAL-1, COUCHES-AFFICHAGE-1)
                                          │
                                          └── e2818ae5  feat/raccordement-1  [tip, geom SAINE]
```

**Le fait central, prouvé plus bas :** `feat/raccordement-1` a inventé un moteur déclaratif de couches
(YAML `declarations/`, endpoint générique, rendu `CouchesGeneriques.tsx`). Pendant que la branche
dormait, **la même idée a été reconçue et mergée dans main par une lignée plus propre et plus avancée**
(`feat/couches-tuyau` → tuiles MVT + COUCHES-RECETTE + EXPORTS-REBRANCHEMENT-1 + DONNEES-1 +
COMMUNE-RANGEMENT-2). **Main est en avance sur la branche**, pas l'inverse. La branche est un ancêtre
périmé de code déjà servi.

## 1. Inventaire (178 fichiers, dont 139 docs/captures)

### Code servi (15 fichiers)

| fichier | ± | rôle en une phrase |
|---|---|---|
| `src/labuse/registre/resolveurs_fiche.py` | +643 | **NOUVEAU** moteur de résolution déclaration-first de la fiche parcelle |
| `frontend/src/components/map/CouchesGeneriques.tsx` | +491 | **NOUVEAU** rendu générique des couches piloté par déclaration |
| `src/labuse/registre/declarations.py` | +262 | chargeur des YAML de déclaration (**version ancienne — voir §3**) |
| `src/labuse/api/app.py` | +251 −38 | endpoint générique `map_couches_info` + kinds virtuels + assemblage fiche |
| `src/labuse/circuit_verrous.py` | +199 | verrou **V6a** (garde-fou calibrage PLU, `a_decider`, non bloquant) |
| `src/labuse/registre/donnees.py` | +169 −6 | données couches/fiche ajoutées au registre |
| `src/labuse/registre/assemblage_fiche.py` | +138 | **NOUVEAU** assembleur fiche depuis les déclarations |
| `frontend/src/lib/api.ts` | +70 −4 | client `map_couches_info` |
| `src/labuse/registre/robinets.py` | +50 −6 | +17 robinets couches, rebranche tcsp/transport, +3 chiffres fiche (**§3**) |
| `src/labuse/models.py` | +16 −1 | modèle(s) de support |
| `frontend/src/components/map/MapView.tsx` | +9 −207 | **strip** du legacy MapView (familles Nature/Risques retirées) |
| `frontend/src/components/map/Legend.tsx` | +2 −74 | légende allégée |
| `frontend/src/components/panel/LeftPanel.tsx` | +2 −17 | toggles génériques |
| `src/labuse/store/useApp.ts` | +1 −15 | état toggles générique |
| `src/labuse/cli.py` | +2 −2 | libellé compteur de verrous |

### Déclarations (18 YAML/MD), scripts (4), test (1), qa (1)

- `declarations/FORMAT.md` (+125), `generiques.yaml` (+27), `_exemples/outils/taxe_amenagement.yaml` (+27).
- `declarations/couches/*.yaml` (8 : `couches_sans_toggle` +272, `famille_risques` +166, `famille_transport` +130, `famille_urbanisme` +116, `famille_dispositifs` +89, `famille_nature` +72, `famille_equipements` +57, `famille_marche` +22).
- `declarations/fiche/*.yaml` (7 : `sections_restantes` +174, `le_bien` +99, `entete_tuiles` +79, `marche` +63, `risques` +53, `petites_sections` +51, `reseaux` +29).
- `scripts/recette_delta_e.py` (+117 — outil ΔE de teintes), `scripts/diag/geom_after.py` (+94), `geom_plot.py` (+45), `geom_check.py` (+43).
- `tests/test_raccordement1_lot0.py` (+122 — test du format de déclaration), `qa/couches_52.mjs` (+267 — harnais navigateur 52 couches).

### Commits (65, du plus récent au plus ancien — extrait)

`e2818ae5` COUCHES-AFFICHAGE-1 lot 2 (tuiles vectorielles) · `28bb458f` GEOM-FINAL-1 lot 1 (géométrie BRUTE, zéro optim) · `cca1f045`→`82e6b3ae` COUCHES-52 (5 causes) · **`3ea38f8d` GEOM-FIX-1** (revert ST_Simplify → PreserveTopology) · `949e650b`→`c50ca5ab` RACCORDEMENT-1 strip 1→13 (retrait legacy MapView) · `71f29410`→`e8a28a5d` lot 3 familles (Risques/Nature/Transport/Urbanisme/Dispositifs/Équipements) · `9837dec0` Transport complet (ligne_mt + TCSP rebranchés) · `51260184`→`31635581` lot 0-1 (coupe fiche, format de déclaration figé).

## 2. Classement, avec justification par fichier

### A — À RÉCUPÉRER : **AUCUN fichier.**

Aucun fichier ne corrige un défaut **encore présent sur main aujourd'hui**. Chaque candidat a été testé
contre `origin/main` et trouvé **déjà résolu** :

- **Les 3 chiffres fiche** (`exposition_versant`, `cosia_detecte_m2`, `endiguement_zone_protegee`) que
  `robinets.py` ajoute : **déjà sur main**, présents dans `declarations/fiche/*.yaml`, `registre/donnees.py`
  ET `registre/robinets.py` (`git grep` = présent dans les trois sur `origin/main`).
- **Les 17 couches « sans toggle »** : **déjà déclarées et servies sur main** (voir §3.3), pas via
  `robinets.py` mais via `declarations/couches/couches_sans_toggle.yaml` (`surface: couche_icpe`, …) et
  les tuiles MVT — l'architecture couches-tuyau a déplacé la déclaration du robinet vers le YAML.
- **Le rebranchement transport/TCSP/ligne_mt** : **déjà fait sur main** dans `famille_transport.yaml`
  (routes `/map/tiles/{tcsp,ligne_mt}/…pbf`, kinds servis dans `app.py`).
- **GEOM-FIX-1** : main n'a **jamais** porté la régression (voir §3.1) — rien à récupérer.

> Faux ami écarté : `couche_piscine` (robinet + kind) est le **seul** robinet de la branche vraiment
> absent de main — mais il l'est **volontairement** : DONNEES-1 lot 2.1 a **sorti la piscine du tuyau**
> (elle vit désormais dans le mode Piscines de Prospection solaire, compteur 56→55, robinet retiré).
> Le réintroduire **recréerait un défaut corrigé** : c'est du poison, pas un fichier de catégorie A.

### B — PÉRIMÉ / possédé ailleurs : **la quasi-totalité du code + déclarations + front.**

Justifié fichier par fichier par le fait que **main a absorbé la même idée, en plus avancé** :

- `declarations/couches/*.yaml`, `declarations/fiche/*.yaml`, `FORMAT.md`, `generiques.yaml`,
  `taxe_amenagement.yaml` — **main possède les mêmes fichiers, évolués** : `couches_sans_toggle.yaml`
  diverge de **104 lignes**, `famille_risques` de 49, `famille_transport` de 48, `le_bien` de 37.
  `FORMAT.md` et `generiques.yaml` sont **identiques** (0 ligne). Main a en plus des fichiers que la
  branche n'a pas : `couches/tuyau_hors_registre.yaml`, `fiche/sections.yaml`, `fiche/reste_a_declarer.yaml`,
  et tout `declarations/commune/` (5 fichiers, COMMUNE-RANGEMENT-2). La branche est un **sous-ensemble périmé**.
- `src/labuse/registre/declarations.py` — **main est strictement plus riche.** `git diff origin/main…branche`
  ne montre que des **suppressions** de fonctionnalités présentes sur main : catégorie `fiche_commune`,
  familles `reperes`/`equipements`, champ `masquer_si_absent` (DONNEES-1), `fiche_section` +
  `sections_fiche()` (EXPORTS-REBRANCHEMENT-1), champs carte `groupe`/`etiquette`/`icones`/`detail_kind`/
  `popup_detail`/`note` (COUCHES-RECETTE-1/2). La branche est l'**ancêtre** de la version servie.
- `src/labuse/registre/robinets.py` — voir §3 : les 3 natures de changement sont **toutes déjà sur main**
  (déclaration YAML + MVT + les 3 chiffres). Reprendre = régresser vers la voie GeoJSON abandonnée.
- `frontend/CouchesGeneriques.tsx`, `MapView.tsx` (strip), `Legend.tsx`, `LeftPanel.tsx`, `lib/api.ts`,
  `store/useApp.ts` — **rendu de couches par l'endpoint GeoJSON générique**, remplacé sur main par le
  **rendu par tuiles MVT** (`app.include_router(_couches_tuyau_router)` — chemin `/map/tiles/{kind}/…`).
  Deux implémentations concurrentes du même besoin ; main a tranché pour l'autre. Les reprendre
  entrerait en collision frontale avec le tuyau servi.
- `qa/couches_52.mjs`, `tests/test_raccordement1_lot0.py` — harnais/test du format de déclaration de la
  branche ; le format servi est celui de main (verrous V5c/V5d/V5e déjà en place).
- Les 139 docs/captures RACCORDEMENT-1 — rapports d'un chantier dont le résultat vit ailleurs.

### C — DANGEREUX (géométrie / simplification / rendu — décision Vic 16/09).

- **Le tip `e2818ae5` est géométriquement SAIN** (vérifié) : aucun `ST_Simplify(:tol)` Douglas-Peucker sur
  le chemin des couches ; il sert `COALESCE(sl.geom_simple, sl.geom)` puis, après GEOM-FINAL-1/
  COUCHES-AFFICHAGE-1, la **quantification MVT native** (pas d'optimisation qui déforme). Le seul
  `ST_Simplify*` restant est `ST_SimplifyPreserveTopology(…, 0.00002)` sur les **parcelles**, identique
  à main. **Le tip ne porte donc pas le poison** — c'est son histoire intermédiaire qui l'a porté (voir §3.1).
- **Le vrai danger est le chantier RENDU lui-même.** `CouchesGeneriques.tsx` + strip `MapView.tsx` +
  endpoint GeoJSON générique appartiennent à une **ligne de rendu que main a résolue autrement** (tuiles
  MVT). Merger/cherry-picker ce front **réintroduirait un rendu concurrent** et rouvrirait exactement le
  chantier couches que Vic a stabilisé ailleurs. À traiter comme dangereux **par collision architecturale**,
  même si la géométrie du tip est propre.

### D — SANS INTÉRÊT (travail mort / ponctuel).

- `scripts/diag/geom_check.py`, `geom_plot.py`, `geom_after.py` — sondes one-shot contre base live ; leur
  leçon (le bug ST_Simplify) est **institutionnalisée** sur main par le verrou géométrie servie.
- `scripts/recette_delta_e.py`, `qa/couches_52.mjs` — outils de recette du chantier couches abandonné.
- `src/labuse/registre/resolveurs_fiche.py` (+643) + `assemblage_fiche.py` (+138) — **moteur fiche
  déclaration-first parallèle**, câblé dans `app.py:5094` (`from ..registre.assemblage_fiche import
  assembler_fiche`). **Main ne l'a pas adopté** : la fiche reste servie par `app.py /parcels/{idu}`, et
  seule la **projection Dossier** lit les déclarations (`exports/robinet_fiche.py`, EXPORTS-REBRANCHEMENT-1).
  C'est un demi-moteur jamais retenu — travail mort.
- `circuit_verrous.py` V6a (+199) — garde-fou calibrage PLU `a_decider`, non bloquant, lié au chantier
  couches ; main a sa propre batterie de verrous (V5c/V5d/V5e/V5f/V6b/V6c).
- Les 139 docs/captures.

## 3. Points précis à vérifier

### 3.1 — GEOM-FIX-1 est-il dans la branche, et main porte-t-il l'équivalent ?

- **Dans la branche : OUI** — commit `3ea38f8d` (`merge-base --is-ancestor 3ea38f8d feat/raccordement-1`
  = vrai). Il **annule une régression que la branche s'était infligée** (le lot 3 avait remplacé
  l'expression servie par un `ST_Simplify` Douglas-Peucker non topologique → éventails de triangles) et
  rétablit `COALESCE(geom_simple, ST_SimplifyPreserveTopology(geom, 0.0002))` + pose le verrou V6b.
- **Main porte l'équivalent : SANS OBJET.** Main n'a **jamais** eu la régression. `origin/main` sert
  `ST_SimplifyPreserveTopology(…, 0.00002)` sur les parcelles et les **tuiles MVT** sur les couches — les
  deux topologiquement sûrs. GEOM-FIX-1 est un **auto-correctif interne à la branche** ; main n'a rien à
  recevoir. (Note : le snapshot `diag/geom-check-1`, tranché par GEOM-VERDICT-1, était figé **avant**
  GEOM-FIX-1 et servait donc encore le poison — ce n'est **pas** le cas du tip `e2818ae5`.)

### 3.2 — `robinets.py` : diff vs main, changements, pertinence, couverture par un test de main

- **Diff `+50 −6`, trois natures** (toutes déclaratives, aucune correction de bug) :
  1. **Transport** — `couche_transport` += `telepherique` ; `couche_tcsp` passe du kind mort `tcsp_axe`
     (« BAOBAB retiré, 0 en base ») au kind virtuel `tcsp` ; ajout `couche_ligne_mt` (HTA).
  2. **+17 robinets couches sans toggle** (endiguement, piscine, icpe, friche, cavite, trait_de_cote,
     tri_zone, abf, sar, foret_publique, bassin_versant, cimetiere, safer, zone_activite,
     construction_lineaire, construction_surfacique), chacun mono-robinet vers `/map/layers.geojson?kind=…`.
  3. **+3 chiffres fiche** : `exposition_versant`, `cosia_detecte_m2`, `endiguement_zone_protegee`.
- **Pertinence aujourd'hui : NULLE.** Les trois natures sont **déjà sur main**, faites autrement :
  transport/tcsp/ligne_mt via `famille_transport.yaml` + tuiles MVT ; les couches via
  `couches_sans_toggle.yaml` + MVT ; les 3 chiffres dans `donnees.py`+`robinets.py`+déclarations. De plus
  les routes de la branche (`/map/layers.geojson?kind=…`) sont l'**ancienne voie GeoJSON**, remplacée par
  `/map/tiles/{kind}/…pbf`. Et `couche_piscine` **contredit** DONNEES-1 (piscine sortie du tuyau).
- **Couverture par un test de main : OUI, indirecte.** `circuit_verrous.py` de main porte **V5c**
  (« zéro couple silencieux » : tout couple (donnée, robinet) doit être sondé, mono-robinet, ou porter sa
  raison) via `verifier_robinets`. Ce mécanisme, **déjà sur main et indépendant de la branche**, est ce qui
  a exigé — puis obtenu — que chaque couche/chiffre soit déclaré. Il n'a pas besoin des entrées de la branche.

### 3.3 — Les 17 robinets sans toggle + rebranchements transport/TCSP : encore manquants sur main ?

**NON — plus manquants.** La question date de GEOM-VERDICT-1, qui avait constaté leur absence des **clés
`robinets.py`** de main et **différé la décision à ce mandat**. Vérification faite contre `origin/main`
(`a272d4a5`) :

- **Les 17 couches sont servies** : `declarations/couches/couches_sans_toggle.yaml` de main les déclare
  toutes (`surface: couche_icpe`, `surface: couche_friche`, …) avec `route: /map/tiles/{kind}/…pbf`.
  L'architecture couches-tuyau **déclare le robinet dans le YAML**, plus dans `robinets.py` — d'où le
  `git grep` vide en clés `robinets.py`, qui **n'est pas** une absence réelle.
- **Transport/TCSP/ligne_mt sont rebranchés** : `couche_tcsp` de main pointe `/map/tiles/tcsp/…pbf` (kind
  virtuel `tcsp`), `couche_ligne_mt` existe (`famille_transport.yaml` + `app.py:4618/4721`), `telepherique`
  est géré (`app.py:4614/4633/4673`). La note `famille_transport.yaml:5-6` (« rebranchés au prochain pas »)
  a bien été suivie d'effet.
- **Piscine : retirée exprès** (DONNEES-1), donc son absence est une décision, pas un manque.

## 4. Verdict — **(a) supprimer la branche, rien à sauver.**

`feat/raccordement-1` est un **ancêtre périmé** d'un chantier que main a repris, dépassé et servi par une
lignée plus propre (couches-tuyau + tuiles MVT + COUCHES-RECETTE + EXPORTS-REBRANCHEMENT-1 + DONNEES-1 +
COMMUNE-RANGEMENT-2).

1. **Aucun fichier de catégorie A.** Chaque défaut que la branche corrigeait est **déjà corrigé sur main** :
   17 couches déclarées+servies, transport/tcsp/ligne_mt rebranchés, 3 chiffres fiche présents, géométrie
   saine. Le seul robinet vraiment absent de main (`couche_piscine`) est absent **par décision** — le
   reprendre régresserait.
2. **Le code servi n'apporte que du périmé ou du concurrent.** Le moteur déclaratif de la branche est une
   version antérieure de celui de main (`declarations.py` : la branche ne fait que **retirer** des
   fonctionnalités que main a) ; le front (`CouchesGeneriques`/strip `MapView`) est un rendu GeoJSON
   concurrent du tuyau MVT servi — le reprendre rouvrirait le chantier couches que Vic a clos ailleurs.
3. **Le moteur fiche déclaration-first** (`resolveurs_fiche` + `assemblage_fiche`) **n'a jamais été
   adopté** : main sert la fiche par `app.py` et ne miroite que le Dossier. Demi-moteur mort.
4. **Le diagnostic géométrique a fini son office** : GEOM-FIX-1 (revert) et le verrou géométrie servie
   sont **institutionnalisés** ; les sondes `scripts/diag/*` figent un bug résolu.

Il n'y a **ni fichier de catégorie A, ni liste courte à reprendre** (pas de scénario (b)), et **surtout
pas** de reprise de la branche telle quelle (pas de scénario (c) — elle régresserait le rendu). **Supprimer
`feat/raccordement-1`**, local **et** `origin/feat/raccordement-1`. La suppression **ne perd aucun travail
de raccordement** (main le porte, en mieux) et **retire un risque** de réintroduction d'un rendu concurrent
ou du robinet piscine banni.

> Recommandation d'exécution (hors mandat lecture seule, pour Vic) :
> `git push origin --delete feat/raccordement-1 && git branch -D feat/raccordement-1` puis retirer le
> worktree `~/Desktop/labuse-raccordement` (`git worktree remove`). Le besoin « couches au registre » est
> déjà satisfait sur main par le tuyau ; les vrais restes (calibrage PLU) sont des mandats séparés.

## 5. Hors mandat (non fait)

Aucun merge, cherry-pick, correctif, réouverture du chantier couches, ni modification de main, d'une autre
branche ou de Gabarit. Rien écrit hors ce rapport, dans un worktree jetable depuis `origin/main`.
