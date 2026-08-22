# M135 — Phase A : inventaire + conception (lecture seule, aucune écriture)

Branche `feat/m135-residuel-runs` @ `4967c736`. **Aucune écriture, aucun code
touché.** Garde-fou : `origin/main` a avancé `dfa402d3 → 4967c736` (merge M134,
docs-only — écart hors périmètre M135, vérifié) → branché sur le HEAD courant, signalé.

## A.1 — Les lecteurs, exhaustifs (~35 sites, tous en SQL inline, aucun helper)

Chaque site lit `parcel_residuel` en jointure/EXISTS sur `parcel_id`. **Aucun ne
passe par un helper commun** : SQL inline partout.

| Famille | fichier:ligne | Forme |
|---|---|---|
| **Faisabilité outil** | `api/modules.py:1172` | `JOIN … sdp_residuelle_m2 >= :sdp` (sens2) |
| Modules (listes) | `api/modules.py:226, 637` | `LEFT JOIN` |
| **FiltreCriteres (facettes)** | `api/app.py:924, 982, 1017, 1052, 1055, 1062, 1083, 1086, 1092, 1181, 1190` | `EXISTS(SELECT 1 FROM parcel_residuel …)` — ~11 facettes |
| Listes/exports q_v2 | `api/app.py:2026, 2268, 3134, 3470` | `LEFT JOIN … cause IS NULL` |
| **Dossiers projet** | `api/projets.py:841, 1091` | `LEFT JOIN` |
| Partners / apporteur | `api/partners.py:106, 133, 500` | `LEFT JOIN` |
| Tuiles carte | `api/tiles.py:168` | `LEFT JOIN` |
| Moteurs (outils) | `api/moteurs.py:66, 154` | `JOIN sdp>0` / `LEFT JOIN` |
| Événements | `api/events.py:527, 968` | `LEFT JOIN` |
| **Verdict servi** | `verdict_servi.py:113` | `LEFT JOIN … cause IS NULL` |
| **Cascade** | `cascade/context.py:603` (→ `etage0_ext.py:172` via `ctx.residuel_sdp`) | `SELECT sdp_residuelle_m2 WHERE parcel_id` |
| **Scoring P (features)** | `scoring/p_model/sql.py:289-291` (+ registre `features.py:110-117`) | `LEFT JOIN` |
| **Scoring v2** | `scoring/p_v2/pipeline.py:398` | `EXISTS(SELECT 1 … JOIN parcel_residuel)` |
| Score E | `ingestion/score_e.py:98` | `LEFT JOIN … cause IS NULL` |
| Flash / rapport | `flash/data.py:227` | `FROM parcel_residuel JOIN parcels` |
| Marché commune | `faisabilite/marche_commune.py:241` | `FROM parcel_residuel` |
| Filtre bâti | `faisabilite/filtre_bati.py:108` | `LEFT JOIN` |
| Fraîcheur (garde) | `bascule_gardes.py:495` | `SELECT max(computed_at)` — hygiène, pas une donnée servie |

**~35 requêtes, 14 fichiers, 0 helper.** Colonnes lues : `sdp_residuelle_m2` (27×),
`cause` (7×), `sous_densite` (5×), `pct_potentiel` (3×), `computed_at` (3×),
`capacite_estimee` (2×), `taux_emprise_pct` (1×) — **les 7**. Aucun `SELECT *`.

## A.2 — Les écrivains (deux chemins, dont un incrémental problématique)

Le **seul** UPSERT vers `parcel_residuel` est `residuel.py:152/188/198`
(`compute_residuel_batch`). Deux appelants :
1. **`cli.py:1261`** (`compute-residuel`, avec `--commune`/`--chunk`) — le run global.
2. **`audit.py:65`** — `compute_residuel_batch(session, ids)` pour les parcelles
   **auditées** (« caché aussi pour la parcelle auditée → visible au filtre »). C'est
   un **recalcul incrémental, en place**, déclenché à chaque audit. **C'est l'origine
   du lot 05/08** (8 032 parcelles auditées entre les runs → toutes « disponible »).

`compute_residuel()` (fonction pure, `residuel.py:80`) reste **byte-identique** : ce
mandat ne la touche pas.

**Point dur** : le chemin `audit.py` écrit **en place dans la table servie**. Sous
versionnement à run servi immuable, cette écriture heurte le garde-fou B.4
(« écrire dans le run servi est une erreur »). À trancher (§A.3, décision Vic).

## A.3 — Conception proposée

### Recommandation : OPTION VUE (lecteurs inchangés)

Avec **~35 lecteurs hétérogènes en SQL inline et zéro helper**, l'option colonne
(amender chaque lecteur pour filtrer `run_seq`) est **risquée à proportion exacte du
nombre** : un lecteur oublié lit le mauvais run **en silence** (l'avertissement même
du mandat). L'option vue les garde **tous byte-identiques**. **C'est décisif ici.**

**Schéma cible :**

```
-- données, versionnées
parcel_residuel_runs(
  run_seq int, parcel_id int,
  taux_emprise_pct int, pct_potentiel int, sous_densite bool,
  sdp_residuelle_m2 int, capacite_estimee bool, cause text, computed_at timestamptz,
  PRIMARY KEY (run_seq, parcel_id))
CREATE INDEX ON parcel_residuel_runs (parcel_id, run_seq);   -- lecteurs par parcel_id

-- métadonnées + pointeur de service
residuel_runs(
  run_seq int PRIMARY KEY,          -- entier MONOTONE (séquence), JAMAIS trié en chaîne
  label text, is_served bool DEFAULT false,
  code_commit text, communes text,  -- NULL = île entière ; sinon partiel
  computed_at_min timestamptz, computed_at_max timestamptz, duree_s int, note text)
CREATE UNIQUE INDEX ON residuel_runs (is_served) WHERE is_served;  -- au plus UN servi

-- la table historique devient une VUE (mêmes 7 colonnes, même forme) :
CREATE VIEW parcel_residuel AS
  SELECT parcel_id, taux_emprise_pct, pct_potentiel, sous_densite,
         sdp_residuelle_m2, capacite_estimee, cause, computed_at
  FROM parcel_residuel_runs
  WHERE run_seq = (SELECT run_seq FROM residuel_runs WHERE is_served);
```

Les 35 lecteurs ne changent pas d'une ligne (la vue expose exactement les colonnes
d'aujourd'hui, sans `run_seq`).

### Pointeur de service : flag `is_served` en base (PAS un fichier)

Une VUE doit filtrer sur le pointeur **au moment de la requête** → il doit être
**résident en base** (un `served_run.txt` obligerait la vue à appeler une fonction
lisant un fichier — fragile). Donc `residuel_runs.is_served`.

- **Bascule** : `UPDATE residuel_runs SET is_served = (run_seq = :cible);` — une seule
  transaction, atomique, met exactement un run à `true` (garanti par l'index partiel).
- **Retour** : le geste symétrique, `:cible = run_precedent`. Réversible en un UPDATE.
- **Aucun `MAX`, aucun tri de chaîne** : la désignation est le flag booléen + l'entier
  `run_seq` (dette §8 M133 respectée).

### Devenir de l'existant

Le cache actuel (41 MB, mosaïque) → copié en **run 1**, `residuel_runs` :
`label='legacy-mosaïque 29/07·05/08·19/08'`, `is_served=true`,
`computed_at_min=2026-07-29`, `computed_at_max=2026-08-19`,
`note='mosaïque 3 états de code, cf. M134 A.3bis'`. **Servi tel quel** — son identité
de mosaïque conservée dans les métadonnées, pas effacée.

### Écrivain

`compute_residuel_batch(session, ids, run_seq=…)` écrit dans
`parcel_residuel_runs` au `run_seq` **passé à l'appel**. **Garde-fou B.4** : si
`run_seq` == le run servi → **exception** (pas un warning), avec test. `cli.py`
crée/désigne un run cible ; **jamais** le servi.

**Décision requise — le chemin `audit.py`** (écriture incrémentale in-place) :
- **(a) audit en lecture seule** : l'audit affiche le résiduel recalculé (via
  `compute_residuel()` pur) sans le cacher — la valeur servie reste celle du run
  jusqu'au prochain run complet. Petit changement de comportement, respecte
  l'immuabilité. **Recommandé.**
- (b) exception au garde-fou pour l'audit (patch mono-parcelle du run servi) — brise
  l'immuabilité/reproductibilité du run.
- (c) run servi « mutable » — incompatible avec la reproductibilité.

### Métadonnées par run

Dans `residuel_runs` : `label`, `code_commit` (SHA au calcul), `communes` (NULL=île,
sinon la liste — pour un run partiel), `computed_at_min/max`, `duree_s`, `note`.

### Rétention (41 MB/run)

Proposer : garder **le servi + le précédent + les runs explicitement épinglés**
(ex. un run ayant servi à un entraînement scoring). Une commande
`residuel-runs --purge <seq>` qui **refuse** de purger `is_served` ou un run épinglé.
Défaut ≈ 3-4 runs (≈ 120-160 MB). **Purge = geste de Vic**, jamais automatique.

### Articulation avec le scoring

Les features (`p_model`, `p_v2`) lisent la **vue = run servi** — inchangé. Pour la
**reproductibilité d'un entraînement**, le snapshot d'entraînement doit **enregistrer
le `run_seq` servi** au moment du calcul (métadonnée `residuel_runs`), et la rétention
**ne doit pas purger** un run dont dépend un entraînement vivant. Un ciblage
`run_seq` explicite par les features serait un **changement scoring — hors périmètre
M135** ; signalé.

### Option colonne (pour mémoire, NON recommandée)

`run_seq` ajouté à la PK, **chaque** lecteur amendé pour filtrer le run servi.
Honnête mais : 35 sites hétérogènes à modifier, un oubli = mauvais run silencieux.
Le jeu n'en vaut pas la chandelle vu le nombre trouvé en A.1.

---

## STOP — Vic arbitre la conception avant toute écriture

À trancher : (1) **option vue** (recommandée) vs colonne ; (2) le sort du chemin
**`audit.py`** (a/b/c ci-dessus, (a) recommandé) ; (3) la **rétention** (nb de runs,
qui épingle). Sur ton go, Phase B (migration ordonnée, service inchangé) puis Phase C
(premier run réel île, diff run 1 ↔ run 2, essai de bascule + retour).

**Aucune écriture, aucun code touché, service intact.** CC ne merge jamais, CC ne
bascule jamais.
