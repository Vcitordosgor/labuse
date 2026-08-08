# M-A — Atomicité & déterminisme du build V — synthèse

Branche `feat/m-a-atomicite` (worktree `~/Desktop/labuse-ma`, base sur `origin/main` 709af2fe).
CC ne merge pas : Vic valide et merge. Méthode : mesurer chaque point avant de corriger.

## 1. P1-2 — DELETE + COPY hors transaction unique — **CORRIGÉ**

**Reproduit.** `compute_all` (score_v.py) faisait `DELETE FROM parcel_v_score` **puis
`session.commit()`** *avant* le COPY. Un COPY qui casse (ou le process qui meurt entre les deux)
laissait la table VIDE.

Fix (modèle `division_or.build_divisions` — « DELETE et INSERT commitent ensemble ») : suppression du
commit intercalaire → DELETE + COPY dans **une seule transaction**, un seul commit final. Toute erreur
pendant le COPY rollback aussi le DELETE (`session_scope`), la table garde son contenu d'avant.

- **Validation #2 (mesurée)** : erreur injectée APRÈS le DELETE, AVANT le COPY → table **431 663
  lignes, checksum identique** (jamais vidée ni partielle). Avant le fix : table vidée.

## 2 & 3. P3-3 `ORDER BY` friches + `_load_owner_links` — **CORRIGÉ**

**Reproduit.** Deux builds identiques divergeaient sur **21 parcelles** : le `ref`/`site_id` de la
friche variait (`AGORAH-97402_36632` vs `_36631`). Cause : une parcelle touche plusieurs friches
(refcad ∪ intersection géométrique) et `_load_friches` retenait une friche ARBITRAIRE (`setdefault` /
`DISTINCT ON` sans tri stable). Le **score n'a jamais changé** (friche = 18 pts quel que soit le site) —
seul le libellé de référence était instable.

Fix : `ORDER BY` déterministe sur les deux requêtes friches (gagnant = plus petit `site_id` à idu
égal) + `ORDER BY idu` sur `_load_owner_links` (stabilise l'ordre de la review queue et du chunking
terrain nu ; le contenu par idu était déjà idempotent).

- **Validation #1 (mesurée)** : deux builds successifs → **diff vide** (0 ligne d'écart hors
  `computed_at`).

**Résultat de contenu à RAPPORTER (périmètre)** : le déterminisme fige, pour ≤21 parcelles
multi-friches, le `site_id` servi sur le plus petit. `v_score`/`v_band` **inchangés** pour toutes ;
seule la référence friche du bloc `signals` passe d'une valeur instable à une valeur stable. Aucun
tier/score servi modifié.

## 4. Garde `check_unicite_pm` — **AJOUTÉE (0 doublon aujourd'hui)**

**Mesuré d'abord** : `parcelle_personne_morale` a une **PK sur `idu`** → **0 doublon**, 0 idu à
plusieurs sirens. L'unicité est structurellement garantie aujourd'hui.

Garde ajoutée quand même (vérification EXPLICITE de l'invariant avant service, défense en profondeur
si la PK sautait / import parallèle / source dégroupée) dans `bascule_gardes.py`, **même régime que
`check_sources_declarees` (M-H) : bruyante, NON bloquante**, `check_unicite_pm(session=None) -> dict`.
Câblée dans la séquence unique de service `tiles.rebuild_mvt_servies` (à côté des autres gardes).

- **Validation #3 (test DB réel)** : `tests/test_unicite_pm.py` retire la PK dans la transaction du
  test, introduit un vrai doublon → la garde renvoie `DOUBLONS` et cite l'idu ; renvoie `OK` sinon ;
  ne lève jamais.

## 5. `date_evenement` à None — **NE SE REPRODUIT PAS (rapporté, non corrigé)**

**Mesuré** : les codes d'événement DATÉS réellement consommés par le pipeline
(`BODACC_LJ/RJ/SAUVEGARDE/CESSION_FONDS`, cf. `EVENT_CODES`) sont **100 % datés — 0 sans date**. Les
signaux à `date_evenement` null sont tous des **non-événements** (FRICHE, DVF_TENURE_OBS5, GEO_*,
NU_PM_HORS_IMMO, RNE_CESSATION anti-signal 0 pt) où null = « pas de date d'événement », jamais une date
fabriquée. Aucune date d'ingestion ni `_today()` n'est injectée comme date amont. Rien à trancher :
la doctrine fraîcheur est déjà respectée. Conformément au mandat, **rapporté, pas corrigé dans le vide**.

## Validation attendue

1. Deux builds → diff vide. ✔ (`reports/m-a-atomicite/verif_build_v.py`)
2. Échec en cours de build → table intacte. ✔ (erreur injectée post-DELETE)
3. `check_unicite_pm` détecte un doublon introduit. ✔ (`tests/test_unicite_pm.py`)
4. Aucun événement ne porte une date fabriquée. ✔ (mesure P5, 0 cas)

## Périmètre

Touché : `scoring/score_v.py` (loaders friches/owner + atomicité), `bascule_gardes.py` (+garde),
`api/tiles.py` (câblage garde), `tests/test_unicite_pm.py`, `reports/m-a-atomicite/`. **Non touché** :
scoring/modèle/calibration, golden, surfaces servies (v_score/v_band inchangés). Tests guards/score_v :
33 passés.
