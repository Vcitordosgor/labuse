# COMPTE-RENDU CIRCUIT-1 — tenu au fil des lots

Branche `feat/circuit-1` depuis main `aafdccbe` (qui inclut le merge de CIRCUIT-0). Worktree `~/Desktop/labuse-audit`, base locale `labuse`.

## Étape 0 (05/09/2026)

- pwd/arbre propre : OK. `git fetch` + `main` à jour + branche créée.
- Maquette : `~/Downloads/maquette-circuit-v5.html` trouvée, copiée dans `docs/CIRCUIT/` (509 lignes), commitée avec le mandat (`74e57173`).
- **`fix/retours-12` : le tronc RETOURS-12 est mergé (`4c25588f`), mais le commit RETOURS-13 Lot 1 `44443736` (seed des sources 93 EDF HTA · 94 TCSP · 95 Réunion Express) vit encore sur la branche seule.** Conformément à l'étape 0.3 : ces sources sont lues telles qu'en base locale et déclarées au registre à partir de là ; le merge de `fix/retours-12` alignera le seed.
- **Suite backend (main + .env local copié du worktree principal, `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` pour WeasyPrint)** : le premier passage (2277/4+10 err.) était POLLUÉ par des tests lancés en parallèle (contention DB) ; le passage propre donne **2295 passed, 1 failed, 49 skipped** — l'unique rouge `test_front_reliquats.py::test_r5_etudier_deux_marges_chacune_dit_son_referentiel` est PRÉ-EXISTANT sur main (prouvé par `git stash` : échoue aussi sans les changements du lot 0). Référence de non-régression : **≥ 2295 verts, seul ce rouge admis**.

## Décisions prises en autonomie

1. **(Étape 0)** La suite n'est pas verte au départ (4 failed + 10 errors pré-existants sur main). Option la plus sûre : ne PAS tenter de réparer main dans ce mandat (hors périmètre, risque de conflit avec les correctifs en cours côté RETOURS-13) ; la référence devient « aucun rouge nouveau, ≥ 2277 verts ». Alternative écartée : réparer d'abord main (retarderait le mandat, doublonnerait un travail probablement en cours ailleurs).
2. **(0.2)** `comptes.total` de l'écran Circuit = `len(sources)` déjà filtrées `WHERE_AFFICHEES` (une seule requête, impossible à désynchroniser), plutôt qu'un second `count(*)` filtré. `surveillees` = vraies sondes actives PARMI ces lignes. Alternative écartée : refaire deux requêtes SQL filtrées (2e chemin qui peut diverger).
3. **(0.3)** Le mensonge du tampon DPE vit à DEUX niveaux : `dpe.py:243` (par commune — véridique quand la commune est réellement interrogée, conservé tel quel) et surtout `fraicheur.trace_ingestion` (CLI) qui posait `last_sync_at` même quand TOUTES les communes étaient sautées. Correctif au niveau du contexte de trace (`handle["tampon"]`), défaut True pour ne rien changer à bodacc/géorisques. La passe « orphelins » compte comme traitement réel (elle interroge l'ADEME et upserte). Alternative écartée : guarder `_touch_source` sur `n>0` dans `ingest_commune` (aurait rendu muette une commune légitimement vide, sans corriger le vrai mensonge du passage à vide).

## Non fait (avec raison)

- (rempli au fil des lots)

---

## Lot 0 — Lever ce qui bloque

### 0.1 — Les crons du VPS : LUS (le DOUTE n° 1 de CIRCUIT-0 est levé)

Sortie brute : `docs/CIRCUIT/VPS-CRONS-05-09.txt` (172 lignes, ssh lecture seule, commandes autorisées uniquement).

**Vérité constatée : le VPS ne fait tourner QUE les crons legacy.** `/etc/cron.d/` contient 11 fichiers `labuse-*` (posés 27/08 18:34, horaires en heure RÉUNION — le VPS est passé en fuseau Indian/Reunion, commentaire en tête de chaque fichier) : abuse, backup(+maintenance), ban, bodacc, dpe, dvf, fraicheur, notifications, radar, sessions, sitadel(+hebdo). **Le crontab wrapper (`deploy/cron.d-labuse`, 16 jobs) n'est PAS posé** ; `crontab -l` (ubuntu) est vide ; **`/opt/labuse/state/jobs/` n'existe pas** — le wrapper n'a jamais tourné là-bas. Conséquences : sentinelle-sources, radar-cycle/digests/releves, coherence-run, fiche-commune-cache, sources-fraicheur, ingest-sirene/sitadel(mensuel)/dpe(mensuel)/sync-gpu du wrapper **ne tournent pas en production**. Le lot 8 par-tira de cette vérité (et non de l'hypothèse).

### 0.2 — Compteur de sources unique

- `src/labuse/flux.py` : `comptes.total` = lignes affichées (WHERE_AFFICHEES, la même requête que la liste servie) ; `comptes.surveillees` = vraies sondes actives parmi elles. Avant : 77/49 bruts ; après : 66/41 sur la base locale du 05/09 — les trois écrans (page Sources client `app.py:919`, Catalogue admin `dashboard.py:893`, Circuit) disent le même nombre par construction.
- `src/labuse/api/dashboard.py:893` : `est_affichee(...)` reçoit désormais `affichage_desactive`.
- Tests : `tests/test_circuit1_lot0.py` (5) — égalité Circuit == arbitre `lister_etats`, DOUBLON/désactivée exclus, sonde d'un DOUBLON et rappel manuel exclus des « surveillées », prédicat avec flag.

### 0.3 — Le tampon DPE ne ment plus

- `fraicheur.trace_ingestion` yield un handle `{"id", "tampon"}` ; `last_sync_at` n'est posé que si `tampon` (défaut True — bodacc/géorisques inchangés).
- `cli.py::ingest_dpe_cmd` : compte les communes réellement interrogées ; tout sauté → `tampon=False`, message explicite « last_sync_at INCHANGÉ » ; le saut affiche « (ré-ingérer : --force) ».
- Tests : passage à vide → `last_sync_at` NULL et trace `ingestion_runs='ok'` ; passage réel → posé.

### Suite

- Tests du lot : 5/5 verts. Suite complète post-lot 0 : **2295 passed, 1 failed (pré-existant stash-prouvé), 49 skipped** — aucun rouge nouveau, +18 verts vs le passage pollué.

### Écart d'inventaire relevé (le code gagne)

- Le rapport CIRCUIT-0 (lot 5) disait « 139 couples couvrant 55 robinets ; 67 robinets à 0 » : le recompte sur `chiffres.csv` donne **84 robinets couverts / 38 à 0**. La longue traîne du lot 1.3 porte donc sur 38 robinets, pas 67.
