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

---

# Phase B — Migration (exécutée sur go de Vic : VUE, audit→lecture-seule, rétention 4 + is_pinned)

Code : `faisabilite/residuel_runs.py` (schéma, résolution du run servi, migration,
garde-fous, bascule), `faisabilite/residuel.py` (writer ciblé + garde-fou),
`cli.py` (commandes), `audit.py` (compare read-only), `models.py` (ensure view-aware),
`tests/test_residuel_runs.py`. **`compute_residuel()` byte-identique** (l.80-150,
diff prouvé nul — non-négociable #1).

## 1. Schéma + copie run 1 + vue — service byte-identique

`migrate_to_runs()` (une transaction) : crée `parcel_residuel_runs` (clé
`run_seq,parcel_id`) + `residuel_runs` (pointeur), copie l'existant en **run 1
« legacy-mosaïque 29/07·05/08·19/08 » servi**, renomme la table de base en
`parcel_residuel_base_legacy`, crée la **VUE** `parcel_residuel`. Vérifié :
- 431 663 lignes, **digest identique**, `EXCEPT` bidirectionnel base↔vue **0/0** ;
- run 1 servi, `parcel_residuel` = vue (relkind `v`).

## 2. Contrôles Phase B (les deux ajoutés par Vic)

- **Perf vue** : `faisabilite_sens2` île (benchmark M133 = 3 s) → après `ANALYZE`
  (tables neuves = pas de stats) **1,8 → 1,1 → 0,7 s** ; lecture mono-parcelle
  **0,14 ms**. **Pas de dégradation** (meilleur, même). Plan : index PK
  `(run_seq,parcel_id)`, run servi résolu par sous-requête `is_served` — **aucun
  MAX ni tri de chaîne**.
- **7 colonnes** : la vue expose **noms + types + ORDRE à l'identique** (l'ordre
  `computed_at`/`capacite_estimee` corrigé pour matcher la table historique).

## 3. Lecteurs — inchangés (option VUE)

Zéro modification des ~35 lecteurs. La vue leur sert exactement le run servi.

## 4. Écrivain — run désigné à l'appel, garde-fou B.4

`compute_residuel_batch(session, ids, run_seq)` écrit dans `parcel_residuel_runs`.
`assert_writable()` **lève `ServedRunWriteError`** si `run_seq` == run servi
(prouvé). `cli.py` : `compute-residuel --new-run/--into-run` (jamais le servi),
`residuel-migrate`, `residuel-runs`, `residuel-serve` (bascule), `residuel-purge`
(refuse servi/épinglé), `residuel-pin`. **`audit.py`** ne rapièce plus : il
**compare** frais ↔ servi et rapporte l'écart (décision 2a) — la machine à mosaïque
(lot 05/08) est **éteinte à la racine**.

Validé sur **Les Trois-Bassins** (5 314 parcelles, run neuf 2) : écrit en 66 s
(**12,4 ms/parcelle**), **diff run 1 ↔ run 2 = 0**. Bascule testée entièrement :
run 1 → run 3 (copie) → **retour** run 1, service byte-identique à chaque état ;
écriture/purge du run servi refusées, purge d'un run épinglé refusée.

*NB env local : `typer`/`pytest` non installés ici (CLI + tests tournent en
prod/CI) ; le chemin cœur (que le CLI enveloppe) et les garde-fous sont validés
directement en Python contre la base.*

# Phase C — premier run réel (terminé)

Run **île entier dans run 2** (`m135_run_ile.py`) : 431 663 parcelles (253 764
calculées + 177 899 avec cause), **107 min** (12,4 → 15 ms/parcelle), commit
`9cf08f98`, dates 22-23/08 (**fraîches, NON mosaïque**). **Run servi 1 intact tout
du long.**

## C.1 — Diff run 1 ↔ run 2 : PRESQUE nul, une seule colonne, ÉLUCIDÉE

| Colonne | Diff |
|---|---|
| sdp_residuelle_m2 | **0** |
| cause | **0** |
| pct_potentiel | **0** |
| sous_densite | **0** |
| taux_emprise_pct | **0** |
| **capacite_estimee** | **44 824** |
| parcelles manquantes (un run, pas l'autre) | 0 / 0 |

**Les 44 824 sont TOUS `False → True`, TOUS du lot 29/07** (le plus ancien de la
mosaïque), concentrés en communes non/partiellement calibrées (Saint-André 16 712,
Saint-Leu 12 594, Saint-Benoît 11 610, Saint-Denis 3 006…). **Ce n'est pas un bug de
migration** (elle était byte-identique, prouvé) mais **la correction du flag stale**
déjà nommé en M134 A.2 : le lot 29/07 précède M-PLU-REF (14/08, marquage `calibree`) ;
le run 2 frais applique le marquage courant. La SDP, la cause, la sous-densité — tout
ce qui pilote filtres/scoring/vivier — est **identique**. Le flag `capacite_estimee`
est lu par **deux consommateurs d'AFFICHAGE seulement** (`app.py:3161` fiche,
`projets.py:1087` dossier) — l'outil, lui, le résout en direct (M133 B.5). La
correction rend l'affichage **plus juste** ; elle ne régresse rien.

## C.2 — Les 7 ancres : identiques

`EP1044`, `BI1097`, `CW1056`, `BV2471`, `EL0368`, `CN1677`, `BT0960` : SDP + cause
**identiques** run 1 ↔ run 2. Aucune n'est touchée par le diff `capacite_estimee`
(Le Tampon calibrée, ou non-constructible → flag NULL). `sens2` rend le **même**
compte sous run 1 et run 2 (Le Tampon 3 326) — il ne lit que la SDP (identique).

## C.3 — Bascule d'essai run 1 → run 2 → retour : réversible, prouvé

- run 1 (initial) : 1 709 parcelles « estimées » servies.
- **bascule → run 2** : 46 533 (Δ +44 824, les flags corrigés) ; `faisabilite_sens2`
  fonctionne (Le Tampon n=3 326).
- **RETOUR → run 1** : 1 709, **digest byte-identique à l'état initial** (réversibilité
  ✓). Une réversibilité non testée n'existe pas — testée.

Service **remis sur run 1**. Non-régression consommateurs (à travers la vue) :
R+1≠R+7, gel Us/2AUc, PDF projet régénéré conforme M130-12/M131 (faîtage 4 m = 0,
`part X —` = 5, EP1044 sert 6/11 « Us3 §5 p.134 », 2AU par renvoi).

## C.4 — Proposition à Vic (proposer, pas faire)

Le diff n'est pas strictement nul, mais **entièrement élucidé** : une correction
d'affichage (`capacite_estimee`), pas une régression ; tout le reste identique ;
mécanisme et réversibilité prouvés. **Proposition : basculer le service sur le run 2**
(`residuel-serve 2`) — cela (a) sert des valeurs **fraîches et cohérentes** (code
courant uniforme), (b) **corrige** le flag stale des 44 824, (c) **éteint la mosaïque
A.3bis** (run 1 devient un run historique, épinglable puis purgeable). Retour en un
geste (`residuel-serve 1`). **C'est le geste de Vic. CC ne bascule pas.**

CC ne merge jamais, CC ne bascule jamais.
