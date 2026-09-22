# GEOM-VERDICT-1 — Que faire de `diag/geom-check-1`

**Nature : audit lecture seule. Aucun merge, aucun cherry-pick, aucune modification de main.**
Worktree `~/Desktop/labuse-geomverdict` sur branche jetable depuis `origin/main`.

## Étape 0 — état
- `pwd` = `/Users/openclaw/Desktop/labuse`, worktree d'audit = `~/Desktop/labuse-geomverdict` @ `f00ad5b5` (== `origin/main`, vérifié).
- Arbre du dépôt principal propre (seul `captures/circuit-sources1/` non suivi, hors sujet).
- `git fetch --all` fait. `main` local == `origin/main` == `f00ad5b5`. `origin/HEAD` → `claude/eager-pascal-cmObd`.
- **Base de diff utilisée : `origin/main` (`f00ad5b5`)**, comme le mandat le prescrit (`git diff origin/main...diag/geom-check-1`). `diag/geom-check-1` = `0960bbf2`.

## La lignée — le fait qui décide tout

```
origin/main (f00ad5b5) ───────────────────────────────────────────────── (safe geom)
        │
        └─ merge-base a7079c5e
                     … 54 commits RACCORDEMENT-1 …
                                   │
                     949e650b (strip 13) ──┬── e2818ae5  feat/raccordement-1  [VIVANTE, worktree labuse-raccordement]
                        (= merge-base)      │                 contient GEOM-FIX-1 (3ea38f8d) → geom SAINE
                                            │
                                            └── 0960bbf2  diag/geom-check-1   [+1 commit : le diagnostic]
                                                                 PAS GEOM-FIX-1 → geom CASSÉE
```

`diag/geom-check-1` **n'est pas une branche de travail** : c'est `feat/raccordement-1` figée au commit `949e650b` (strip 13), **plus un seul commit** : le diagnostic `0960bbf2`.

Conséquences prouvées :
1. **Les 51 fichiers non-diagnostic appartiennent à `feat/raccordement-1`**, branche **vivante** (worktree `labuse-raccordement`, HEAD `e2818ae5`) qui a **dépassé** ce snapshot. `robinets.py` de geom-check est **identique octet pour octet** à celui de racc-1 (`git diff` vide). Rien à « récupérer » ici qui ne soit mieux servi par racc-1.
2. **Ce snapshot précède GEOM-FIX-1** (`3ea38f8d`, le revert de l'optimisation géométrique). `git merge-base --is-ancestor 3ea38f8d diag/geom-check-1` → **NON**. Donc son `app.py` servi contient **encore l'expression bannie** (voir §3 / §Classement C).
3. **Le seul apport exclusif** de la branche = les 11 fichiers du diagnostic (`docs/diag/*`, `scripts/diag/*`).

## 1. Inventaire (62 fichiers, `origin/main...diag/geom-check-1`)

`prov.` = origine réelle : **RACC** = commit de `feat/raccordement-1` (présent dans la branche vivante) · **DIAG** = commit `0960bbf2` exclusif.

| fichier | nature | ± | prov. | rôle en une phrase |
|---|---|---|---|---|
| `src/labuse/api/app.py` | **code servi** | +131 −4 | RACC | endpoint générique `map_couches_info` + kinds virtuels **+ bascule de l'expression géo servie vers `ST_Simplify(:tol)` (bannie)** |
| `src/labuse/registre/robinets.py` | code servi | +50 −6 | RACC | +17 robinets couches sans-toggle, rebranche tcsp/transport, +3 chiffres fiche (voir §3) |
| `src/labuse/registre/resolveurs_fiche.py` | code servi | +643 | RACC | résolveurs déclaration-first de la fiche (nouveau moteur) |
| `src/labuse/registre/declarations.py` | code servi | +262 | RACC | chargeur des YAML de déclaration |
| `src/labuse/registre/assemblage_fiche.py` | code servi | +138 | RACC | assembleur fiche à partir des déclarations |
| `src/labuse/registre/donnees.py` | code servi | +169 −6 | RACC | données ajoutées au registre (couches/fiche) |
| `src/labuse/circuit_verrous.py` | code servi | +48 | RACC | verrou **V6a** garde-fou calibrage PLU (`a_decider`, non bloquant) |
| `src/labuse/cli.py` | code servi | +2 −2 | RACC | libellé compteur « 17 → 18 verrous » |
| `frontend/src/components/map/CouchesGeneriques.tsx` | code servi | +391 | RACC | **rendu générique des couches piloté par déclaration** |
| `frontend/src/components/map/MapView.tsx` | code servi | +9 −207 | RACC | strip du legacy MapView (couches Nature/Risques retirées) |
| `frontend/src/components/map/Legend.tsx` | code servi | +2 −74 | RACC | légende allégée |
| `frontend/src/components/panel/LeftPanel.tsx` | code servi | +2 −17 | RACC | toggles génériques |
| `frontend/src/lib/api.ts` | code servi | +66 −4 | RACC | client `map_couches_info` |
| `frontend/src/store/useApp.ts` | code servi | +1 −15 | RACC | état toggles générique |
| `declarations/FORMAT.md` | déclaration | +125 | RACC | format de déclaration figé |
| `declarations/generiques.yaml` | déclaration | +27 | RACC | styles génériques |
| `declarations/couches/*.yaml` (8) | déclaration | +919 | RACC | 7 familles couches + `couches_sans_toggle.yaml` |
| `declarations/fiche/*.yaml` (7) | déclaration | +548 | RACC | sections fiche déclarées |
| `declarations/_exemples/outils/taxe_amenagement.yaml` | déclaration | +27 | RACC | exemple outil |
| `tests/test_raccordement1_lot0.py` | test | +122 | RACC | test du format de déclaration (lot 0) |
| `docs/audit-2026-09/RACCORDEMENT-1.md` | doc | +1067 | RACC | rapport raccordement-1 |
| `docs/audit-2026-09/RACCORDEMENT-1-*.html/.png` (14) | capture | +213 | RACC | captures fiche/en-tête/couches |
| **`docs/diag/GEOM-CHECK-1.md`** | **doc diag** | +135 | **DIAG** | rapport du diagnostic géométrie |
| **`scripts/diag/geom_check.py`** | **script diag** | +43 | **DIAG** | mesure `ST_IsValid` + parties, branche vs main |
| **`scripts/diag/geom_plot.py`** | **script diag** | +45 | **DIAG** | preuve visuelle SVG des anneaux servis |
| **`docs/diag/geom-*.svg` (4)** | **capture diag** | +2382 | **DIAG** | rendus SVG base/branche/main |
| **`docs/diag/geom-*.png` (4)** | **capture diag** | bin | **DIAG** | mêmes preuves en PNG |

## 2. Classement, avec justification

### A — À RÉCUPÉRER : **AUCUN fichier**
Aucun fichier ne corrige un défaut de main que cette branche seule saurait corriger. Tout le code servi appartient à `feat/raccordement-1`, branche **vivante et en avance** sur ce snapshot ; s'il faut en tirer quelque chose, la source est racc-1, pas cet embranchement gelé. (Observation, pas exception : le rebranchement `couche_tcsp` `tcsp_axe`→`tcsp` corrige bien un robinet mort sur main — `tcsp_axe` = 0 en base — mais ce correctif **existe déjà dans racc-1** et doit passer par ce mandat-là.)

### B — PÉRIMÉ / possédé ailleurs : **51 fichiers** (tout le bloc RACC)
`app.py`(pour sa partie non-géo), `robinets.py`, `resolveurs_fiche.py`, `declarations.py`, `assemblage_fiche.py`, `donnees.py`, `circuit_verrous.py`, `cli.py`, les 6 fichiers front, les 16 `declarations/*`, `test_raccordement1_lot0.py`, `RACCORDEMENT-1.md` + 14 captures.
**Justification :** ce sont les commits de `feat/raccordement-1`, présents **à l'identique ou dépassés** dans la branche vivante `e2818ae5` (vérifié : `robinets.py` diff vide vs racc-1 ; les fichiers-clés `PRESENT in racc-1`). Ce snapshot est un point ancien de racc-1, pas une source indépendante. Reprendre l'un d'eux = le prendre dans racc-1.

### C — DANGEREUX (géométrie / simplification / rendu — décision Vic 16/09) : **`src/labuse/api/app.py`** (+ le pipeline de rendu couches)
**Preuve que le danger est encore dans CE snapshot :** `git show diag/geom-check-1:src/labuse/api/app.py` ligne **5688** sert
`ST_AsGeoJSON(COALESCE(ST_Simplify(COALESCE(sl.geom_simple, sl.geom), :tol), …))`.
C'est exactement l'expression **Douglas-Peucker non topologique** que le propre diagnostic de la branche condamne (éventails de triangles, polygones auto-intersectants) et que **GEOM-FIX-1 a annulée**. Or GEOM-FIX-1 (`3ea38f8d`) **n'est pas** dans la lignée de geom-check (`merge-base --is-ancestor` → NON).
- `origin/main` sert `ST_SimplifyPreserveTopology(…, 0.00002)` — **SAINE**.
- `feat/raccordement-1` (vivante) contient GEOM-FIX-1 — **SAINE**.
- `diag/geom-check-1` — **CASSÉE**.
**Merger/cherry-picker ce snapshot ferait régresser la géométrie de main** — précisément l'optimisation-qui-déforme interdite le 16/09. Le front `CouchesGeneriques.tsx` + strip `MapView.tsx` relèvent du même chantier rendu, mis dessus.

### D — SANS INTÉRÊT (diagnostic ponctuel / travail mort) : **11 fichiers DIAG**
`docs/diag/GEOM-CHECK-1.md`, `scripts/diag/geom_check.py`, `scripts/diag/geom_plot.py`, `docs/diag/geom-{tri_zone,sup,georisque_alea,plu_gpu_zone}.{svg,png}`.
**Justification :** autopsie unique et lecture seule. Elle a **déjà rempli son office** : elle prouvait le bug géométrique de l'optimisation raccordement — bug **déjà corrigé** (GEOM-FIX-1 a rétabli l'expression saine) et **verrouillé** (V6b « géométrie servie ≤ référence »). Les scripts sont des sondes one-shot contre une base live ; les SVG/PNG figent un bug résolu. Aucune valeur d'avenir : la leçon est institutionnalisée ailleurs.

## 3. Le cas `robinets.py` (registre servi)

**Diff vs main** (`+50 −6`), trois natures de changement, tous déclaratifs :
1. **Rebranchements couches transport** : `couche_transport` += `telepherique` ; `couche_tcsp` passe du kind mort `tcsp_axe` (« BAOBAB RETIRÉ, 0 en base ») au kind virtuel `tcsp` ; ajout `couche_ligne_mt` (HTA).
2. **+17 robinets « couches sans toggle »** (endiguement, piscine, icpe, friche, cavite, trait_de_cote, tri_zone, abf, sar, foret_publique, bassin_versant, cimetiere, safer, zone_activite, construction_lineaire, construction_surfacique) — chacun mono-robinet vers `/map/layers.geojson?kind=…`.
3. **+3 chiffres aux robinets fiche** : `exposition_versant` (en-tête), `cosia_detecte_m2` (Le bien), `endiguement_zone_protegee` (Risques) — données SOURCES-2→5 « sans place » résorbées, mono-robinet.

**Pertinence :** ces entrées n'ont de sens **qu'avec** le moteur déclaratif complet (`declarations.py` + `resolveurs_fiche.py` + `CouchesGeneriques.tsx`). Isolées, elles déclarent des couples (donnée, robinet) que le circuit exige de couvrir. Ce sont **des déclarations de refonte, pas des corrections de bug**.

**Possédé par racc-1, pas par geom-check :** le commit `0960bbf2` (diag) **ne touche pas** `robinets.py` ; et `git diff diag/geom-check-1 feat/raccordement-1 -- robinets.py` est **vide** → le fichier est **identique** à la branche vivante. Il n'y a donc rien d'unique à sauver ici.

**Couverture par un test de main :** oui, indirectement — `circuit_verrous.py` de main porte **V5c** (« zéro couple silencieux » : tout couple (donnée, robinet) doit être sondé, mono-robinet, ou raison nommée) et `verifier_robinets`. Ce sont ces verrous qui **exigeraient** que chaque nouveau robinet ci-dessus soit soit sondé soit justifié — mécanisme déjà présent sur main, indépendant de cette branche. Les nouvelles clés (`couche_tri_zone`, `couche_icpe`, `couche_ligne_mt`, `couche_endiguement`) **n'existent pas dans main** (grep = 0).

## 4. Verdict — **(a) supprimer la branche, rien à sauver**

`diag/geom-check-1` = un **snapshot gelé et dangereux** de `feat/raccordement-1` + une **autopsie déjà consommée**.

1. **Le code servi n'est pas à elle.** 51 des 62 fichiers sont des commits de `feat/raccordement-1`, branche **vivante et en avance** (`e2818ae5`, worktree `labuse-raccordement`). `robinets.py` y est identique. Toute reprise passe par racc-1 — jamais par ce point mort.
2. **Ce snapshot ferait régresser main.** Il précède GEOM-FIX-1 : son `app.py:5688` sert encore le `ST_Simplify` Douglas-Peucker que Vic a banni le 16/09 et que son propre diagnostic condamne. C'est du poison, pas un correctif.
3. **Le seul apport exclusif — le diagnostic — a fini son travail.** Il a justifié GEOM-FIX-1 (revert) et V6b (verrou « géométrie servie ≤ référence »), tous deux **déjà en place**. Conserver l'autopsie d'un bug corrigé et verrouillé n'apporte rien.

Il n'y a **ni fichier de catégorie A, ni liste courte à reprendre** (pas de scénario (b)). **Supprimer `diag/geom-check-1`** — local **et** `origin/diag/geom-check-1`. La suppression **ne perd aucun travail de raccordement** (racc-1 le porte, corrigé) et **élimine un risque de régression géométrique** si quelqu'un venait à la merger par erreur.

> Recommandation d'exécution (hors mandat lecture seule, pour Vic) :
> `git push origin --delete diag/geom-check-1 && git branch -D diag/geom-check-1`
> Le chantier couches continue sur `feat/raccordement-1` uniquement.

## 5. Hors mandat (non fait)
Aucun merge, cherry-pick, correctif, réouverture du chantier couches, ni modification d'une autre branche. Rien n'a été écrit hors ce rapport, dans un worktree jetable depuis `origin/main`.
