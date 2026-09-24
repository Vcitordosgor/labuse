# FAISABILITE-1 — Livrable

**Date : 24/09/2026 · Branche `feat/faisabilite-1` (base main `f1a55381`) · worktree `~/Desktop/labuse-faisa`.**
**4 commits (un par lot), non mergé.** Voir aussi `A-AUDIT.md` (rapport du lot A) + `verif_temoins.py`/`.out`.

| Lot | Commit | Objet |
|---|---|---|
| A | `55916eda` | Audit des données (lecture seule) — rapport `A-AUDIT.md` |
| B | `52a55a74` | Filtre global « Capacité » (panneau Carte) |
| C | `58ebc28f` | Faisabilité : un seul mode |
| D | `b79cd662` | Hypothèses modifiables + lignes manquantes (bloc partagé fiche + outil) |

---

## 1. Le tableau des 11 étapes (source · badge · où le lot D agit)

Le moteur unique `estimate_capacity` (`faisabilite/engine.py`) émet la liste `steps` ; le même bloc
`FaisabiliteTab` (`fiche/constructibilite.tsx`) la rend **dans la fiche ET dans l'outil M22**
(endpoint sens1 `/modules/faisabilite/{idu}`). Témoin **BZ1065** (Saint-Denis Uh) — badges servis :

| # | Étape | Source | Badge (après lot D) | Éditable (lot D) |
|---|---|---|---|:--:|
| 1 | Emprise au sol — reculs (géométrie réelle) | Art. 7 · PLU calibré | **Sourcé** (Estimé si repli prudent) | — |
| 2 | Emprise au sol — % réglementé | Art. 9 · CES PLU | **Sourcé** (ou « non réglementée ») | — |
| — | **Espaces inconstructibles déduits** *(NOUVEAU, si ER/EBC/greve)* | ER/EBC (L113-1) / PPR-PEB | **Sourcé** | — |
| 3 | Contrainte pleine terre *(si calibrée)* | Art. 13 | **Sourcé** | — |
| 4 | Niveaux constructibles | Art. 10 (R+n lu) | **Sourcé** (Estimé si plage/générique) | — |
| 5 | Emprise bâtie (occupation du gabarit) | `coef_occupation` 0,45 | **Estimé** | ✅ occupation |
| 6 | Surface de plancher brute | occupation × niveaux | **Dérivé** | (suit) |
| 7 | Surface habitable (rendement) | `coef_rendement` 0,80 | **Estimé** | ✅ rendement |
| 8 | Logements — après plafond de densité | `densite` 30/ha/niveau | **Estimé** | ✅ densité |
| 9 | Stationnement — scénario au sol | Art. 12 (+ `place_m2` 25) | **Sourcé** | ✅ m²/place |
| 10 | Stationnement — scénario sous-sol/silo | Art. 12 | **Dérivé** | (suit) |
| 11 | Logements retenus au sol | densité ∩ stationnement ∩ modulation | **Dérivé** | (suit) |
| — | **Mixité sociale (LLS)** *(NOUVEAU, si détectée)* | Art. 2 — part LLS non calibrée | **non modélisée** | — |
| 12 | *(front)* SHAB vendable retenue | logts retenus × logt moyen | **Dérivé** | ✅ surface/logt, hauteur d'étage |

**Correction du lot A (§1.a).** L'audit affirmait « aucune étape ne porte de badge (prov='' → — ) ».
C'est vrai **du moteur brut** et de `fiche_payload`, mais l'endpoint réellement consommé par le bloc
(`sens1`) **dérivait déjà** le badge du libellé de source (`_faisa_step_prov`) : la fiche et l'outil
montraient donc des badges. Le lot D **remplace cette dérivation fragile par un badge DÉCLARÉ au
moteur** (chaque `Step.prov` posé explicitement), `_faisa_step_prov` le respectant désormais en
priorité — plus robuste (fini le pari sur les mots du `source`).

---

## 2. Le moteur — même fonction, tout-ou-rien servi (rappel A-AUDIT)

`parcel_faisabilite` est appelé à l'identique par l'outil (`api/modules.py`) et la fiche
(`app.py`→`fiche_payload`), en **`assiette_clippee=False`** (tout-ou-rien). Le **run résiduel servi**
(base `labuse`, `residuel_runs.is_served` = seq **8** « post-plu8-clip-2shard » au 24/09 — un run de
fond a promu ce run **clippé** pendant la session) a été calculé **avec** l'assiette clippée →
divergence sur les parcelles A/N à cheval (le cache voit une portion U/AU, le moteur live voit 0).
**C'est un écart data profond, laissé à Vic** (choix du run servi ; hors mandat = moteur résiduel).

### Recompte SDP restante = `parcel_residuel` sur les 3 témoins (`verif_temoins.py`)

| Témoin | moteur LIVE (défaut) | vue `parcel_residuel` (servie) | verdict |
|---|---:|---:|---|
| BZ1065 (Saint-Denis, Uh) | **26 m²** | **26 m²** | ✅ identique à l'unité |
| BW0457 (Saint-Paul, U6c, calibré) | **34 m²** | **34 m²** | ✅ identique à l'unité |
| AB1117 (Bras-Panon, N-96 % à cheval) | **0** (« construction neuve non autorisée en zone N ») | **81 m²** (portion U/AU, run clippé) | ✗ **divergence assiette-clippée** |

> Témoin de contrôle BW0457 Saint-Benoît (Ub, non calibré) : live 178 m² vs cache 144 m² — écart de
> **fraîcheur de cache** (le run de fond a recalculé le bâti pendant la session), pas une formule fausse.
> Le chemin par défaut du moteur reste **byte-identique** au servi sur les mono-zone U (golden préservé).

---

## 3. Lot B — filtre global « Capacité » · l'écart de compteur expliqué

Nouveau groupe **« 3 · Capacité »** dans le panneau Filtre (sous Couches) : **SDP restante ≥ X / ≤ Y**,
**Logements possibles ≥ N**, aide-calcul repliable **« Depuis un programme »**, **Destination autorisée**.
SDP/logements lisent `parcel_residuel` du **run servi** (backend `app.py`, `sdp_min`/`capacite_min`
inchangés — la même donnée que la fiche, jamais le gabarit brut). Compteur **SQL exact**, **ET** avec
les autres filtres, entre dans **hash/URL/Mes vues/veille/badge** (`sdp`,`cap`,`dst` ; `destinationAutorisee`
+ SDP/logements classés « faits » → n'allument pas l'analyse LABUSE). Pas d'« Inclure A/N » (Zonage suffit).

**Destination** (`/filtre?destination=<slug>`) : écarte les parcelles dont la zone **interdit** la
sous-destination (`plu_destinations` validées, `_destination_interdit_keys`) ; « calibration en cours »
= non filtrée ; slug inconnu → **400**.

### L'écart « SDP ≥ 960 » vs les 8 949 de l'ancien « Par critères » (recette île, run q_v11_m137)

| Requête | Compte |
|---|---:|
| **Ancien « Par critères » — SDP nécessaire 960 m²** (`POST /modules/programme`) | **8 949** *(reproduit exactement)* |
| **Filtre Capacité — SDP restante ≥ 960** (`/filtre`, île) | **13 789** |
| + zonage U/AU seulement (exclut A/N) | 12 901 |
| + « constructible » (tier vivant) | 11 446 |
| + U/AU **et** constructible | 11 214 |

**Explication.** Le filtre Capacité lit la **SDP restante BRUTE** de `parcel_residuel` sur **toutes**
les parcelles → plus large. « Par critères » retranchait en plus : le **tier scoring** (`s2.tier IN …`,
≈ −2 343), les **A/N** (≈ −888, `masquees` par défaut), et surtout le **plafond au gabarit R+2**
(`sdp_dispo = résiduel × min(N+1,niveaux_max)/niveaux_max`, qui rabote la SDP des zones plus hautes que
R+2) **+ contrôle d'emprise au sol + éligibilité hauteur**. Le reste de l'écart (11 214 → 8 949) est ce
rabotage-gabarit. Le nouveau filtre est **volontairement plus large et composable** (SDP restante ∧, au
choix, Zonage / constructibilité / destination), au lieu d'un unique programme figé à R+N.

---

## 4. Lot C — un seul mode

`M22Programme.tsx` ouvre directement sur la **saisie de parcelle** (sous-titre « Ce que le PLU laisse
construire sur cette parcelle. »). L'onglet « Par critères » et **tout son code propre** sont retirés :
formulaire/pagination/`postProgramme` (front) ; **endpoint `POST /modules/programme` + `ProgrammeIn`**
(backend, aucun autre appelant — grep). Lien discret **« Chercher des parcelles par capacité → »** vers
le groupe Capacité (action store `chercherParCapacite`). **Copilote/projet** : un programme
(`prefill_programme`/`projet.programme`) est **traduit en filtre Capacité** puis la carte s'ouvre sur le
panneau Filtre (plus d'ouverture de M22 en mode critères). **Verrou 17 outils** : `registry.ts` intact.
Deep-links inchangés (fiche/Densifier `setModule('programme')` ouvre M22 en mode parcelle).

---

## 5. Lot D — hypothèses modifiables + lignes manquantes

Bloc **partagé fiche + outil** (une seule implémentation). Lignes **Sourcé verrouillées** (citation
visible) ; lignes **Estimé éditables** (`HypInput`, ambre) → **recalcul immédiat de tout ce qui suit par
le MOTEUR** (`POST /modules/faisabilite/{idu}/recalcul` → `parcel_faisabilite(hyp_overrides=…)`, aucune
reimplémentation → zéro divergence) ; bouton **« Revenir aux hypothèses LABUSE »**. Valeurs **gardées
dans le projet** (`prospection.faisa_overrides` de l'entrée pipeline — JSONB existant, par parcelle,
jamais resservi ailleurs, jamais en base hors projet — doctrine 09/09 ; validées par le clampeur moteur).

**Preuve recalcul (témoin BZ1065)** — occupation 45→60 %, rendement 80→75 %, surface/logt 72,5→50 m² :
SDP brute **219 → 292 m²**, logements retenus **~1-2 → ~3-4**. Overrides hors bornes / clés inconnues
**ignorés** (jamais un calcul détourné).

### Tableau « ce qui manque » — ajouté / laissé à Vic

| Donnée | Statut après FAISABILITE-1 |
|---|---|
| ER / EBC déduits de l'assiette | déjà pris en compte (moteur) — **désormais DIT en étape** (lot D) |
| CES vraie / pleine terre composée | déjà pris en compte (moteur) |
| Stationnement (places exigées, sol/sous-sol) | déjà 2 étapes — `m²/place` **éditable** (lot D) |
| Mixité sociale (LLS) | **ligne « non modélisée »** ajoutée (lot D) — jamais un 0 muet |
| PPR rouge / PEB / DPF / ravine / 50 pas clippés | **laissé à Vic** (dépend du run servi clippé, §2) |
| Résolution sous-zone U/AU (A/N à cheval) | **laissé à Vic** (idem run servi, §2) |
| Hauteur LiDAR du bâti existant | **laissé à Vic** (module `hauteur_lidar` non câblé au résiduel) |
| SUP (servitudes d'utilité publique) | **laissé à Vic** (non déduites au moteur) |

---

## 6. État des tests

| Suite | Résultat |
|---|---|
| `tsc --noEmit` (frontend) | ✅ vert |
| `vite build` | ✅ vert |
| `vitest run` | ✅ **180/180** (nouveaux : mode unique M22, éditeur d'hypothèses) |
| pytest `test_faisabilite1_capacite` (B+C+D) | ✅ 6/6 |
| pytest `test_faisabilite` / `test_scoring6_assiette` / `test_mn_faisabilite` | ✅ 39 (golden inchangé — `extras` informatif, défaut byte-identique) |
| pytest `test_filtres_cumul` / `test_m45_filtres` | ✅ verts |
| pytest `test_prospection` / `test_projet_*` | ✅ 24 (persistance projet, 0 régression) |

**Hors mandat, non touché** : moteur résiduel · calibrage PLU (mixité) · Analyse · autres filtres ·
exports · merge. **Écarts profonds laissés à Vic** : run servi clippé vs non-clippé (§2), LiDAR, SUP,
et `config/served_manifest.json` (indique run 2 alors que la base sert un run clippé — désynchronisé).

## 7. Captures

Vérification conduite **programmatiquement** (TestClient + `verif_temoins.py` + vitest) faute d'avoir
lancé le stack navigateur (run résiduel de fond actif — cf. mandat « ne pas le tuer »). Les preuves
chiffrées (compteurs filtre, recalcul témoin, recompte SDP=résiduel, badges, nouvelles lignes) sont
ci-dessus et rejouables via `docs/audit-2026-09/faisabilite-1/verif_temoins.py`.
