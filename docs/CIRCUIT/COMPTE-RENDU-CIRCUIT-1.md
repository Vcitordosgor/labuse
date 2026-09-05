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

---

## Lot 2 — Les rebranchements

### Tableau des rebranchements livrés (chacun avec son test)

| # | rebranchement | avant → après | test |
|---|---|---|---|
| 2.1 | **Zonage = surface partout, moteur unique** `registre/moteurs/zonage.py` : `parts_zonage_surface` (LA part, ids `part_zone_*_pct`) + `parcelles_par_zone` (le COMPTE des filtres, id `parcelles_par_zone_n`, « jamais une part »). `_foncier_commune` (app.py) et `/zonage/zones` ne calculent plus : ils demandent. | Saint-Paul servi INCHANGÉ (A 35,8 % / N 47,2 % — le chemin surface était déjà celui de la fiche) ; le chemin « comptes » ne peut plus être servi comme part, par construction | `test_21_*` (3) — dont LE test qui aurait attrapé la fuite : 3 petites U vs 1 grande N → la part servie est la surface |
| 2.2 | **score_e → neuf LIVE** : `_SELECT_RAW` reçoit `:neuf_live` (JSONB {insee: €/m²} depuis `neuf_vefa_commune`, seuil source unique `neuf_vefa_seuil()`=8) + repli île = médiane des médianes live (même règle social-dominantes). Le grain « secteur » disparaît (il n'existait que dans le précalcul divergent). | Saint-Paul : le neuf de score_e devient 5 003 €/m² (celui du comparateur) au PROCHAIN run candidat (portée run) — avant : 4 730 (précalc) | `test_22_score_e_ne_lit_plus_le_precalcul` + `test_score_e` (6, seed VEFA live) |
| 2.3 | **Division d'or run-scopée** : `_division_fiche` (app.py:2692), filtre `division_or` (app.py:1573), découpe `division_review.py:38` — run servi SEUL ; candidat d'un autre run → « divisibilité non recalculée pour ce run ». (`verdict_servi.py:40` était un commentaire, pas un lecteur.) | q_v10_m129 (33 lignes) N'EST PLUS SERVI nulle part ; la fiche le dit honnêtement en attendant le recalcul (geste Calculer, lot 3) | `test_23_*` (2) : run mort jamais servi · run courant servi normalement |
| 2.4a | **« logés gratuitement » calculé au serveur** (`autres_loges_pct`, registre + `_compute_commune_contexte`) ; le front lit le serveur avec repli identique le temps des vieux caches. tsc OK. | même valeur (même arithmétique), mais elle EXISTE désormais côté serveur et porte un id | (couvert par la déclaration registre + tsc) |
| 2.6 | **Garde formelle Copilote voie B** : `garde_generale_sans_chiffre` (answering.py) — un nombre PRÉCIS à unité de donnée (€, €/m², m², parcelles, logements, %) hors fourchette est retiré, phrase remplacée par le renvoi aux outils ; les fourchettes 4bis survivent. Déterministe, appliquée à toute réponse `copilote-general`. | — | `test_26_garde_generale_10_pieges_0_chiffre_invente` (10 pièges, 0 survivant ; 2 fourchettes conservées) |
| 2.7 | **Caches** : `zone_isochrone_cache` TTL 30 j (lecture) + PURGE à la bascule (`bascule_flux.basculer`, jamais bloquant) ; le tampon fiche commune est celui du registre depuis 1.4. | l'eau ancienne « isochrone illimitée » de CIRCUIT-0 est soldée | (TTL lu dans zone.py ; purge listée dans caches_purges du journal de bascule) |

### Décisions prises en autonomie (suite)

8. **(2.2)** Le niveau « secteur » du prix neuf disparaît de score_e : il n'existait QUE dans le précalcul divergent ; le moteur live est communal (VEFA n'atteint le seuil que dans ~11/24 communes). `niveau_label("secteur")` reste pour les lignes historiques. Alternative écartée : reconstruire un neuf sectoriel live (nouvelle définition non mandatée, données insuffisantes — 32 % des VEFA seulement portent une surface).
9. **(2.6)** La garde est DÉTERMINISTE (regex phrases), pas un 2e appel LLM : testable hors ligne, coût nul, zéro latence ajoutée ; la règle 4bis (fourchettes de prestations) survit par construction. Alternative écartée : juge LLM (coût/latence par réponse, non testable en CI).
10. **(2.3)** Le message « non recalculée pour ce run » est servi dans le champ `ligne` existant (le front l'affiche tel quel, aucun changement front requis).

### Non fait (avec raison) — lot 2

- **2.4 (8 des 9 sites front)** : seul « autres logés » est rapatrié. Restants — charge foncière bornée (`constructibilite.tsx:137` : calculette interactive à curseurs, la valeur par défaut serveur existe déjà), kWc/MWh (`ProspectionSolaire.tsx:325-326`), % propriétaires (`MarcheSecteurBlock.tsx:16`), % ZAN (`blocB.tsx:358`), % décidées (`ProjetsPanel.tsx:53`), heures restantes (`Licences.tsx:26` — durée d'affichage, reclassable dérivation légère), n_vigilances (`risques.tsx:16-30`), + le 9e (ResultsSection compteurs max(0,…)). Raison : chaque site exige un aller-retour endpoint+composant spécifique ; l'inventaire précis avec fichier:ligne est posé, le registre les porte déjà (`calcul=front` → à rapatrier), reste ~2-4 h de travail mécanique. Ce qu'il faudrait : un mini-lot « front-serveur » dédié.
- **2.5 (les 45 `sql_propre`)** : l'exemplaire est fait (zonage → `registre/moteurs/zonage.py`, LE cas à fuite mesurée) ; les 44 restantes sont chacune UN SEUL point de calcul aujourd'hui (vérifié au lot 1 : aucun chiffre `sql_propre` n'a deux chemins). Les déplacer toutes = pur déménagement à risque de régression sans gain de cohérence immédiat. Raison du report : le bénéfice vient avec la sonde (lot 4) qui comparera par les ENDPOINTS ; l'extraction mécanique peut suivre chiffre par chiffre. Ce qu'il faudrait : traiter chaque extraction au moment où sa fonction devient `fonction` appelable du registre.
- **Lecteurs restants du précalcul neuf** (hors mandat 2.2 qui visait score_e) : `moteurs.py:526` (référence île du baromètre) et `app.py:1687` (filtre EXISTS) lisent encore `dvf_prix_sortie_neuf` — listés pour un correctif ultérieur ; le précalcul est marqué obsolète dans le docstring de score_e et du CLI.

### Suite

- Tests du lot : 16 verts (7 lot 2 + 6 score_e + 9 registre inchangés) ; tsc front OK.
- Suite complète post-lot 2 : **2311 passed · 1 failed (le pré-existant test_r5) · 49 skipped** — aucun rouge nouveau, +8 verts vs lot 1.

---

## Lot 3 — La pompe unifiée

### Livré

- **3.1 Le manifeste** : `src/labuse/manifeste.py` — `config/served_manifest.json` `{scoring_run, residuel_run_seq, mvt_run, division_run, promoted_at, par, precedent}`, écrit ATOMIQUEMENT (tmp + `os.replace`), manifeste incomplet REFUSÉ (jamais un pointeur partiel). `runs.current()`/`precedent()` lisent le manifeste d'abord, repli sur `served_run.txt`/`run_precedent.txt` tant qu'il n'est pas posé — **aucun comportement ne change avant la première bascule** (migration douce). Bootstrap : `construire_depuis_pointeurs(db)`.
- **3.2 Le résiduel dans le manifeste** : `basculer()` écrit LE manifeste (scoring+résiduel+mvt+division en un seul écrit) ; `residuel_runs.is_served` devient une VUE DÉRIVÉE (mise à jour par la bascule seule) ; **Revenir restaure le manifeste précédent ENTIER**. `residuel_entrees_changees(db)` compare les tampons (PLU/GPU, cadastre, CoSIA — `last_sync_at`) à `computed_at_max` du run résiduel servi : entrées inchangées → le candidat REPORTE le servi.
- **3.3 Calculer** : `labuse pompe calculer --label L --recette R --par X` — chaîne flux-run (cascade+scoring, brique existante), score É pour L (neuf live), division d'or POUR L (env `LABUSE_SERVED_RUN=L` sur le builder — jamais le servi tamponné), garde résiduel, **note de version** puis `rapport_candidat`. La **note de version vient du registre** (`bascule_flux.note_version`) : réservoirs+millésimes (photo F2.2 du run si posée, sinon état courant), chiffres recalculés = portée `run` du registre, écart de classement (`golden_ops.comparer` — honnête sur un candidat inconnu : motif, jamais un écart inventé).
- **3.6 `circuit_journal`** : table `(ts, geste, cible, par, resultat, details)` + `journaliser()` jamais bloquant. Branché : **Injecter** (dashboard, avec le « qui » = compte_email — comblé), **Calculer** (endpoint run/lancer avec « qui », + CLI pompe), **Basculer/Revenir** (`basculer()`, en plus de `run_bascule_journal`), **purge** (CLI). Agents : au lot 6.
- **2.3→3.1** : `_division_fiche` lit désormais `manifeste.division_run()` (repli scoring courant).

### Décisions prises en autonomie (suite)

11. **(3.3)** division d'or « pour le label » : le builder tamponne `runs.current()` — plutôt que d'ajouter un paramètre de run à travers toute la chaîne, le CLI pompe le lance en sous-process avec `LABUSE_SERVED_RUN=L` (l'override d'env EXISTANT, prioritaire par construction). Alternative écartée : refactor du builder (plus propre mais plus risqué ; à faire quand la chaîne division passera au registre).
12. **(3.4)** « tables préparées AVANT la bascule → garde 6/6 instantanée » : **non fait** — `build-mvt` fait un DROP à verrou exclusif (deadlock CONSTATÉ avec les lectures de la garde, commentaire dashboard.py:1428-1432) ; préparer sous le label candidat exigerait un build shadow+swap façon `_rebuild.py`. La bascule reste : pointeur instantané + reconstruction détachée (5/6 assumé pendant la reconstruction, comme avant). Ce qu'il faudrait : porter `build-mvt` sur `rebuild_swap` (chantier dédié).
13. **(3.1)** Les vues dérivées (`served_run.txt` etc.) restent ÉCRITES à chaque bascule (pas encore retirées) : tout code non migré continue de lire juste. Leur retrait = après le lot 5 (page) et une bascule de recette réussie.

### Non fait (avec raison) — lot 3

- 3.4 partiel (ci-dessus, décision 12) ; le « contrôle après bascule » automatique arrive avec la sonde (lot 4.1, déclenchée par la bascule).
- 3.5 (bouton Purger sur la page) : la page est le lot 5 ; le CLI journalisé est prêt.

### Suite

- Tests du lot : `tests/test_circuit1_lot3.py` (8) — manifeste atomique/incomplet refusé/lu par runs, division_run repli, bootstrap, journal (qui/quand/quoi), note de version honnête, garde résiduel honnête.
- Suite complète post-lot 3 : **2319 passed · 1 failed (le pré-existant test_r5) · 49 skipped** — aucun rouge nouveau, +8 verts vs lot 2.

---

## Lot 4 — La sonde de cohérence « Vérifier que tout coule »

### Livré

- **`src/labuse/sonde_circuit.py`** : tables `circuit_ecarts` (dédup UNIQUE (chiffre, clé, robinet_a, robinet_b) ; réouverture si l'écart revient), `circuit_eau_ancienne` (statuts ouvert/etiquete/solde), `circuit_controles` (verdict par passage, lu par la page).
- **4.1 `verifier_robinets`** : témoins v1 = parts de zonage ×24 communes (moteur vs chemin fiche — LA fuite de CIRCUIT-0, méthode de `mesure_fuites.py`) + compte de sources (Circuit vs arbitre). **4.4** : un écart re-mesuré sans divergence passe `solde` en GARDANT sa ligne (`solde_le`).
- **4.2 `verifier_eau_ancienne`** : par tampon — division hors manifeste (etiquete : plus servie depuis 2.3, purge au geste), DPE (amont sonde vs max en base : OUVERT si retard), isochrones > TTL (etiquete : ignorées à la lecture), solaire gelé (etiquete, jamais ouvert — la seule admise par le mandat).
- **4.3** : `controle()` écrit le verdict ; **job wrapper `coherence-robinets`** (quotidien 07:25, notification admin dédupliquée si fuite/eau ouverte — `jobs.py` passe à 20 jobs) ; **déclenché automatiquement après chaque bascule** (`bascule_flux.basculer`, best-effort — une sonde qui échoue n'annule jamais une bascule).

### Décisions prises en autonomie (suite)

14. **(4.1)** V1 : chemins comparés = FONCTIONS des robinets (les mêmes points d'entrée que les endpoints), pas encore l'appel HTTP `?trace=1`/builders PDF/outils Copilote — la générisation vient avec le lot 7.1 (tampon partout). Les chiffres multi-robinets NON couverts sont comptés et affichés dans le verdict (`non_couverts`) : la sonde dit elle-même ce qu'elle ne voit pas (règle no-silent-caps).
15. **(4.3)** Horaire 07:25 (mandat : 07:15) — coherence-run (surfaces/run) tourne déjà à 07:15 ; même famille de contrôles, jamais en même temps sur les mêmes tables.

### Suite

- Tests du lot : `tests/test_circuit1_lot4.py` (5) — dédup+réouverture, solde qui garde la ligne, solaire etiquete jamais ouvert, verdict écrit, job au registre.
- Suite complète post-lot 4 : **2324 passed · 1 failed (le pré-existant test_r5) · 49 skipped** — aucun rouge nouveau, +5 verts vs lot 3.

---

## Lot 5 — La page Circuit : NON CLOS — point de reprise (session suivante : « continue CIRCUIT-1 »)

État : lots 0-4 CLOS et poussés (`b5ab1502` → `c565e2a7`), arbre propre, suite 2324 verts / 1 rouge pré-existant. La session s'arrête au point de coupure naturel « après le 4 » (mandat, Ordre des lots).

### Ce que la session suivante doit faire, dans l'ordre

1. **5.1 `GET /admin/circuit`** (dashboard.py) — assembler EN UN APPEL : réservoirs (`data_sources`+`source_veille`+`mode_remplissage`/`cadence_attendue_jours`/`cadence_statut` posés au lot 1.7 + horloges = jobs de `jobs.py` par source + dernier rapport d'agent — table au lot 6), pompe (manifeste `manifeste.lire()` ou bootstrap, candidat = `bascule_flux.runs_termines`, `residuel_entrees_changees`), robinets/chiffres = miroir `registre_*` (relancer `labuse registre sync` avant), arêtes = `registre.aretes()`, fuites = `circuit_ecarts` statut ouvert, eau ancienne = `circuit_eau_ancienne` dernier passage, dernier contrôle = `circuit_controles` dernière ligne, compteurs du bandeau. Test de perf < 1 s (les briques sont déjà mémoïsées ; attention à `runs_termines` limit_ecart).
2. **5.3 la vanne étendue** — `config/sources_ingestion.yaml` : ajouter toute source `mode_remplissage ∈ {job_sur_clic, cron_mensuel, one_shot}` à job identifiable. La correspondance source→CLI est DÉJÀ inventoriée : `docs/CIRCUIT/inventaire/reservoirs.csv` colonne `job_ingestion` (~40 commandes `labuse ingest-*`/`*-build`). `depot_manuel` (5) : vanne « déposer un fichier » ; `en_direct` (4) : mention sans vanne ; celles sans script → listées au compte-rendu.
3. **5.2 `Circuit.tsx`** — la maquette `docs/CIRCUIT/maquette-circuit-v5.html` est AUTONOME : structure DATA lisible en tête de script (familles/tanks, categories/taps, rc/cr, fuites, compteurs), styles CSS complets (lignes 8-140), rendu (tankRow/tapRow/chk/clock, pipes SVG `#base/#plink/#lit`, sheet 3 colonnes, recherche `#q`, groupes repliables, pompe sticky `#pump`). Transposer en React dans `frontend/src/components/admin/Circuit.tsx`, données = `GET /admin/circuit`. Remplacer les onglets Flux + MiseAJour dans `AdminView.tsx` (MiseAJour.tsx disparaît, ses 3 endpoints réutilisés : injecter → 5.3, run/lancer → Faire tourner, bascule → Basculer avec note de version `bascule_flux.note_version` OUVERTE avant activation du bouton). DA : survol vert opaque inversé (`.cl:hover`), mauve = agents seulement, « Fiche → » jaune.
4. **5.4/5.5** — boutons pompe (Faire tourner = `POST /admin/flux/run/lancer` existant ; Basculer = `POST /admin/flux/bascule` existant + note de version pré-affichée ; Revenir ; Purger = nouvel endpoint fin appelant `purge-runs-morts --apply` avec confirmation) ; « Vérifier que tout coule » = endpoint fin sur `sonde_circuit.controle(db, declencheur="bouton")` ; « Envoyer les agents » = lot 6.
5. **5.6** — page Sources client : inchangée (déjà les mêmes objets depuis lot 0.2).
6. **5.7 recette navigateur base LOCALE** — uvicorn :8000 (tuer l'ancien : `lsof -ti tcp:8000|xargs kill`) + vite (base /socle/, :5175) ; chromium local `chromium_headless_shell-1217` (chemin executablePath — cf. mémoire RECETTE-2/zone-recette) ; scénario : injecter BODACC → calculer (label court) → basculer → vérifier → REVENIR (base remise en état) ; captures avant/après dans `docs/CIRCUIT/RECETTE-CIRCUIT-1/`.
7. Clore le lot : compte-rendu, suite complète (référence : ≥ 2324 verts, seul `test_r5` admis), commit « CIRCUIT-1 lot 5 — … », push. Puis lots 6 (agents — `SURFACES` d'ai_models.py à étendre avec `agent_source`, sortie JSON strict, table `source_agent_rapports`), 7 (traçage front `format.ts`), 8 (horloges : la VÉRITÉ VPS est dans `docs/CIRCUIT/VPS-CRONS-05-09.txt` — SEUL le legacy est posé ; 8.1 retire le legacy du deploy, pose le wrapper, BODACC quotidien au wrapper, bdnb retiré (974 absent), copilote-purge + sante-endpoints posés ; 8.2 healthz lit `jobs.py` ; 8.4 « à vérifier » sur cadence_attendue).

### Rappels d'environnement (gagnés cette session)

- `.env` local copié de `~/Desktop/labuse/.env` (LABUSE_DATABASE_URL=openclaw@localhost/labuse) ; suite : `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib pytest -q` (~3 min) ; JAMAIS deux pytest en parallèle (pollution labuse_test — déjà purgée une fois : p_score_v2_runs/pige_*).
- `python -m labuse.cli` résout le worktree PRINCIPAL (install éditable) — utiliser `PYTHONPATH=$PWD/src python3 -c "...app()"` ou les tests.
- Front : `cd frontend && npm install && ./node_modules/.bin/tsc -b` (OK cette session).
