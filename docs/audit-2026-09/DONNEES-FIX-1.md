# DONNEES-FIX-1 — Le moteur avant le run 11

- **Branche** : `fix/donnees-fix-1` (depuis `origin/main` `cd1fd67e`) · worktree `~/Desktop/labuse-donneesfix` · ports 8675/5875 · non mergée.
- **DB** : `postgresql://openclaw@localhost:5432/labuse` (lecture + un run de test NON servi, run 13). venv `~/Desktop/labuse/.venv`.
- **Date** : 2026-09-29.
- **Aucune bascule, aucun run servi, aucune écriture dans une table servie** (garde `ServedRunWriteError`).

## Résumé

| # | fait / STOP | preuve | commit |
|---|---|---|---|
| 0 | fait | run résiduel servi = **run 10** ; manifeste `residuel_run_seq: 10` (miroir cohérent) | — |
| 1 | **déjà livré + mergé** (revérifié, tient) | run 10→run 11 : AB0012 33366→0, EO0796 179→187, BZ1065 26→36 (`hauteur_source=lidar`) | `a32e1a5c` (base) |
| 2 | **déjà livré + mergé** (revérifié, tient) | badge **53 326 → 189** (58 faîtage aberrant + 132 discord égout) sur 273 552 comparables | `9f637de9` (base) |
| 3 | **déjà livré + mergé** (revérifié, tient) | CD1214/AB0001 faux changements → **0 réel** ; AD0359 vrai changement conservé ; frise = même drapeau | `9cc58260` (base) |
| 4 | **fait** (ce mandat) | 81 exceptions au moteur : 4 appliquées · 21 déjà couvertes · 9 hors-SDP · 47 non modélisées portées | `daf23575` |

> **Constat majeur** : en arrivant sur `origin/main`, les points 1, 2, 3 y étaient **déjà implémentés et mergés** (branche `fix/donnees-fix-1` déjà fusionnée, `bcc32144`), livrables présents dans `donnees-fix-1/`. Je les ai **revérifiés chiffres en main sur la base** (ils tiennent, cf. `ETAT-REVERIFICATION.md`) et n'ai **rien réimplémenté**. Seul le **point 4** restait à faire — c'est l'objet de ce compte rendu.

---

## Étape 0 — garde run servi

- Run résiduel servi = **run 10** (`residuel_runs.is_served=t`, « q_v15 assiette gabarit », code `babcc084`).
- Manifeste `config/served_manifest.json` : `residuel_run_seq: 10` → **miroir cohérent, pas de divergence**.
- Runs 11 (« q_v15 lidar + ER/EBC », île) et 12 sont des runs de test **non servis**.

## Points 1–3 — revérification (rien réimplémenté)

Preuve chiffrée complète dans `donnees-fix-1/ETAT-REVERIFICATION.md`. Synthèse :

- **Point 1** (hauteur LiDAR égout dans le résiduel) : run 10 (NULL partout) vs run 11 (lidar 232 589) — les grosses baisses du rapport livré sont reproduites **à l'octet** (AB0012 33 366→0, DE0210 32 156→0, BN0537 30 741→0). Témoin **EO0796** (bâti 3,3 m) : 179→187 (`lidar`). Témoin **AO1424** (zone A) : 0→0 (terrain_exigu).
- **Point 2** (badge égout↔égout) : ancienne règle |faîtage−BD TOPO|>3 m = **53 326** ; nouvelle |égout−BD TOPO|>15 m ou faîtage aberrant = **189**. BZ1065 dé-badgée, aberrations AZ0128/0417 (faîtage 53 401) toujours captées.
- **Point 3** (pseudo-SIREN) : CD1214/AB0001 → 0 changement réel (2 et 1 « non identifiable ») ; AD0359 vrai changement conservé ; la frise (`moteurs.py:446`) lit le même drapeau `non_identifiable`.

---

## Point 4 — les exceptions PLU `modifie_calcul=true` entrent au moteur

### Le principe (système UNIQUE)

Les 81 exceptions (PLU-EXCEPTIONS-1/`A_CALIBRER.csv`) étaient **affichées** sous le « i » mais **jamais déduites** (`zonage.py` : « n'entre dans aucun calcul »). Elles entrent maintenant par le **même** système que le reste des règles : `faisabilite/zonage.appliquer_exceptions_calcul(rules, commune, zone, surface)`, appelé par `parcel_faisabilite` après `resolve_zone`. `resolve_zone` reste **pur** (l'application est un étage explicite — le garde `test_exception_nentre_dans_aucun_calcul` tient). Calibrage figé, sourcé article/page, dans **`config/plu_exceptions_effet.json`** (clé = ligne de `A_CALIBRER.csv`).

### Ce que l'audit des 81 révèle (nuance de la prémisse)

La prémisse « 81 jamais déduites → résiduel/gabarit trop optimistes » est **en grande partie inexacte** :

| décision | n | ce que c'est |
|---|---:|---|
| **applique** | **4** | 97402 `1AUb`/`Ub` : « terrain d'assiette ≥ 2 000 m² → 10 m égout / 13 m faîtage » (base 8/11). Condition **vérifiable** (surface parcelle) → entre au moteur. |
| **deja_couvert** | **21** | le sous-secteur cité **se résout DÉJÀ comme sa propre zone calibrée** (UBa/UBb/UBc, U5ma/U5ru/U5vi, U6c, Uav, Uaa, UA1, UfCa, UC1…). `resolve_zone` lui sert la bonne valeur ; l'exception sur la zone parente ne concerne pas une parcelle ordinaire → **rien à appliquer, pas de sur-optimisme**. |
| **hors_sdp** | **9** | stationnement (places/logement) — **n'affecte pas l'enveloppe SDP** (résiduel/gabarit). |
| **non_modelisee** | **47** | bandes depuis une limite, voies nommées (RN/RD/rue), destination du projet, sous-secteurs non calibrés, majorations liées à un usage non modélisé. **On ne les approxime PAS** : la règle reste affichée et la parcelle la **PORTE** (`regles_non_modelisees` : regle + porte + article + page). |

Autrement dit : la seule source réelle de sur-optimisme silencieux (restrictions ignorées) est concentrée dans les 47 **non modélisées** — désormais **signalées** (jamais un chiffre faux). Les 21 « déjà couvertes » l'étaient par le calibrage PLU (sous-secteurs = zones à part entière) ; les 9 stationnement ne touchent pas la SDP.

### Où ça entre / ce qui est porté

- **Appliqué** : `he_m`/`hf_m` relevés dans `ZoneRules` (copie `dataclasses.replace`, jamais la règle partagée mutée). Une majoration ne fait que **relâcher** (valeur plus haute) — garde de sens, elle n'abaisse jamais une contrainte.
- **Porté** : colonne `parcel_residuel_runs.regles_non_modelisees` (texte JSON, en fin de vue — run 10 servi reste `NULL`) + champ payload fiche `regles_non_modelisees` (backend ; **aucun changement de front**, l'exception « reste affichée » via le « i » existant).

### Recette — témoins

- **Exception appliquée** — `97402000AI1190` (`Ub`, 32 333 m² ≥ 2 000) : AVANT he 8 → R+2, sdp_max 17 460, **restant 6 941** ; APRÈS he 10 → R+3, sdp_max 26 190, **restant 15 671** (`+8 730`, la majoration légitime des grands terrains). `AI1194` restant 1 958→7 667. La parcelle porte AUSSI une non-modélisée (`voie_specifique`, UB 10.2 p.32).
- **Exception non modélisée** — `97416000CR0151` (`Uf`, Saint-Pierre) : valeur de zone **inchangée**, payload fiche `regles_non_modelisees = [{hauteur.egout, bande_limite, Uf3.5, p.119}]` — la parcelle **porte** la règle, jamais approximée.
- **Déjà couvert** — `97423 Ua` : `appliquer` ne rejoue rien (sous-secteur `Uaa` déjà servi he 12/hf 16 par `resolve_zone`).

### Mesure sur un run de test (run 13, 97402 « Bras-Panon », NON servi)

Run de test **13** « DONNEES-FIX-1 pt4 test 97402 » (6 041 parcelles, commit `daf23575`, NON servi). ⚠ Les diffs **run-à-run** (13 vs 10/11) sont **contaminés** par toutes les fusions intermédiaires (ZONES-FAMILLE-1 a recalculé Bras-Panon 97402, COHERENCE-FIX-1, EXIGU-GRANDES…). Pour **isoler proprement** l'effet, je mesure le point 4 au **même commit, exceptions ON vs OFF**.

| mesure | changent | montent | baissent | net m² | isolation |
|---|---:|---:|---:|---:|---|
| **Point 4 seul** (exceptions ON vs OFF, 97402 Ub/1AUb, 2 261 parcelles) | **58** | **58** | **0** | **+82 428** | propre (même commit) |
| **Point 1 seul** (LiDAR) | île entière, cf. §Point 1 (run 11 vs run 10) : baisses ciblées sur bâti révélé, hausses petites, net quasi neutre | | | | run à run |
| Cumulé pt1+pt4 (97402, run 13 vs run 10) | 1 082 | 988 | 94 | +105 992 | **contaminé** (fusions intermédiaires incluses) — indicatif |

- **Point 4 seul** : **58 parcelles** ≥ 2 000 m² en `Ub`/`1AUb` montent (majoration de hauteur R+2→R+3 légitime des grands terrains), **0 baisse** — la garde « une majoration ne fait que relâcher » tient. Aucune autre zone de 97402 ne bouge (les 47 non-modélisées ne changent aucun chiffre).
- **Drapeaux « règle non modélisée »** : **2 576 / 6 041** parcelles de 97402 portent le drapeau dans le run 13 (exception `voie_specifique` « rue des Limites » sur `Ub`/`1AUb`/`Uba`). Signalement **zone-level** (on ne sait pas quelle parcelle borde la voie nommée) : conservateur et honnête, jamais un chiffre faux.
- **Cumulé** : le run 11 île de Vic portera pt1 **et** pt4. La ligne « cumulé » ci-dessus est **indicative** : le delta 97402 inclut aussi les fusions intermédiaires, donc je ne l'attribue pas au seul mandat.

---

## Vérification (verrous)

- **tsc** (front) : exit 0. **vitest** : 225/225. (Aucun fichier de front modifié pour le point 4.)
- **pytest ciblé** : 26 neufs+voisins verts (`test_donnees_fix1_exceptions_calcul.py` 8, `test_plu_exceptions_1.py`, `test_residuel(_runs).py`, `test_plu_calibrage4_zonage.py`, lots A/B/C). 2 échecs `test_faisabilite.py` (plafond densité / U1pru stationnement) **PRÉ-EXISTANTS** — prouvés identiques sur base (`git stash`).
- **exports mots interdits** : 39/39.
- **banc `--echantillon`** : **sans écart NOUVEAU** (3 660 écarts pré-existants, prouvés identiques sur base — baseline d'environnement, hors mandat).

## Ce que Vic doit lancer ensuite (run 11 île — NON exécuté)

Le point 4 (exceptions) est **cumulable** avec le point 1 (hauteur LiDAR, déjà mergé) : un seul run île les porte tous les deux. Commande (la nuit, seul sur la machine ; sharding conseillé comme run 8) :

```
# depuis le worktree, JAMAIS .venv/bin/labuse :
PYTHONPATH=src .venv/bin/python -c "from labuse.cli import app; app()" \
  compute-residuel --ile --new-run "q_v16 lidar + exceptions PLU" --assiette-clippee
```

Puis (séquence habituelle, hors de ce mandat) : comparer run neuf / run 10 → `residuel-serve <seq>` → séquence scoring. Le run de test **13** (97402) a été **purgé** (non servi, non épinglé) une fois la mesure faite — la colonne `regles_non_modelisees` (nullable, en fin de vue) reste en place pour le run 11 ; le run 10 servi y est `NULL`, inchangé.

## Hors mandat (non fait)

Servir un run · la bascule · merger · modéliser les bandes/voies nommées (géométrie, un mandat à part) · câbler l'aléa PPRI dans le chemin résiduel (rendrait modélisables les 2 exceptions pleine-terre 97415).
