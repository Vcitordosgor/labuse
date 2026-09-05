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

---

## Lot 1 — Le registre (`src/labuse/registre/`)

### Livré

- **1.1 `chiffres.py`** : **96 chiffres déclarés** (les 88 ids de `chiffres.csv` conservés tels quels + 8 de longue traîne) — portée : **76 live / 20 run** ; calcul : moteur 35 · sql_propre 45 · passe_plat 13 · constante 3. `fonction` = référence du producteur (fichier:fonction) ; elle devient un chemin Python importable au fil du lot 2.5 (décision d'autonomie n° 4).
- **1.2 `robinets.py`** : les **122 robinets**, chacun avec la liste des chiffres servis (couples de l'inventaire + rattachements : scan patrimoine → n_parcelles_pm, comparaison communes → les 8 indicateurs, radar client → annonces/prix, solaire toits → prod/azimut…). Graphe dérivé par `registre.aretes()` : 103 arêtes réservoir→chiffre + 169 chiffre→robinet, jamais saisi deux fois.
- **1.3 longue traîne** : les 38 robinets à zéro (recompte, cf. écart d'inventaire) sont soldés — **7 robinets reçoivent 8 chiffres neufs** (procédures PLU, assemblage ×2, courriers, année ortho, pipeline, couverture sources, usage outils), **7 sont rattachés à des chiffres existants**, **24 sont `hors_registre` avec raison déclarée** (fonds = tuiles, couches de présence = géométries, mairie = coordonnées, recherche_web = texte marqué web).
- **1.4 tampon** : `valeur.py` — objet `Valeur{valeur, chiffre_id, version_def, run, reservoirs:{id: millésime}, calcule_le}` ; `tampons_pour(db, ids)` lit les millésimes servis (mapping nom ILIKE stable, jamais un id numérique) + le run courant pour la portée `run`. **`?trace=1` branché sur `/parcels/{idu}` et `/communes/{c}/contexte`** (admin via `exiger_admin`, no-op en local comme le reste de l'auth) → `_trace` = un tampon complet par chiffre déclaré des fiches. Sans `trace=1` : la valeur seule (testé).
- **1.5 miroir** : `labuse registre sync` (sous-commande Typer) → `registre_chiffres`/`registre_robinets`/`registre_aretes` (DDL idempotent, truncate+insert transactionnel). Joué sur la base locale : **96 · 122 · 272**. `registre.verifier()` = 0 problème (mêmes règles que `valide_circuit.py` : ids existants, chaque chiffre servi, robinet vide ⇒ raison).
- **1.6 garde de couverture** : `tests/test_registre.py` (9 verts) — intégrité, énums, arêtes, sync idempotent, tampon complet pour chaque chiffre des fiches parcelle/commune, portée run⇒run servi dans le tampon, `_trace` sur l'endpoint réel. **Exceptions justifiées dans le docstring du test** : robinets hors_registre (24) et endpoints non encore tracés (PDF/mails/Copilote/outils — branchement au lot 7.1).
- **1.7 réservoirs** : `seed_sources.py` reçoit `MODE_ET_CADENCE` (77 sources : mode de remplissage énum CIRCUIT-0 dont `en_direct`, cadence en jours, statut `declaree` (8) / `proposee` (57) / `sans_objet` (12)) + `appliquer_modes_cadences()` (ADD COLUMN IF NOT EXISTS ×3 + UPDATE par nom, idempotent, appelé par `seed()`). Liste livrée : `docs/CIRCUIT/CADENCES-PROPOSEES.md` — Vic corrigera depuis la page.

### Décisions prises en autonomie (suite)

4. **(1.1)** `fonction` reste une référence textuelle (fichier:fonction) tant que les 45 `sql_propre` n'ont pas de fonction extraite — le lot 2.5 les rend appelables. Alternative écartée : exiger un import résolvable dès le lot 1 (aurait forcé 45 extractions avant tout le reste).
5. **(1.4)** `request: Request = None` (défaut) sur les deux endpoints tracés : deux appels INTERNES (`copilote_v2/outils.py:357`, `app.py:4486` fiche export) appellent `commune_contexte()` comme fonction — la signature stricte les cassait (attrapé par `test_m136_exports_ne_crashent_pas`, corrigé, appel interne passé en `db=`).
6. **(1.5)** Le test miroir de `valide_circuit.py` (égalité aux CSV de CIRCUIT-0) est remplacé par `registre.verifier()` (mêmes règles d'intégrité) : les CSV sont l'inventaire FIGÉ du 05/09, le registre est vivant — comparer les tailles au CSV redeviendrait faux au premier chiffre ajouté. L'esprit (aucun id orphelin, chaque chiffre servi) est conservé et testé.

### Compte-rendu du lot (chiffres demandés par le mandat)

- chiffres déclarés : **96** (76 live / 20 run) ; par moteur : scoring_p_v2, marche_communes, marche_pige, zone, residuel, sector_price en tête.
- robinets couverts : **98 avec chiffres + 24 hors_registre = 122/122** (0 orphelin).
- exceptions 1.6 : les 2 familles ci-dessus, listées dans le docstring de `tests/test_registre.py`.

### Attrapé par la suite (et corrigé avant commit)

- Le premier passage complet post-lot 1 a levé 4 rouges NOUVEAUX : les deux tests du cache fiche commune et le flash appellent `commune_contexte()` en POSITIONNEL `(commune, db)` — la signature `?trace=1` a été réordonnée `(commune, db=Depends, request=None, trace=0)` (idem `parcel_fiche`) ; et la garde « module unique plu_destinations » grep tout `src/` — le registre DÉCLARE l'id du moteur sans lire la calibration → filtre `src/labuse/registre/` ajouté à la garde, intention intacte (décision d'autonomie n° 7).

### Suite

- Tests du lot : 9/9 ; voisins (api, api_q_v2, mairies, flux, cache commune, plu_destinations, flash) : 79 verts.
- Suite complète post-lot 1 : **2303 passed · 1 failed (le pré-existant test_r5) · 49 skipped · 1 error instable** (`test_dashboard::test_courrier_transitions_journalisees`, PASSE isolé — ordre de fixtures) — aucun rouge nouveau, +8 verts vs lot 0.
- Au passage : la base `labuse_test` portait des RÉSIDUS de runs interrompus (`p_score_v2_runs` q_v11_m137, annonces pige) qui cassaient 6 tests de façon déterministe — purgés (DELETE/TRUNCATE sur labuse_test, la base bac à sable). Leçon : ne jamais lancer deux pytest en parallèle sur la même base de test.
