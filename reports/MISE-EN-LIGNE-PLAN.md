# MISE-EN-LIGNE-PLAN — préparer la mise en ligne (un déploiement, un classement)

**Mandat** MISE-EN-LIGNE-1, 21/11/2026. Préparation seule — **rien de ce plan n'a été exécuté**.
Aucune écriture serveur pendant ce mandat (prod lue en ssh, `statement_timeout`, hors fenêtres).
Worktree `~/Desktop/labuse-deploy3`, branche `ops/deploy-groupe-3` **fusionnée avec main**
(étape 0 vérifiée : `origin/main` contient `d25b7f91f` fix/etude-stationnement-1 et `165505ce3`
fix/moteur-verite-1 ; tête main `23a7551ba` du 21/11).

---

## Page 1 — l'ordre des étapes, en français simple

| # | Étape | Durée | Coupure du site | « C'est bon » quand… | Retour arrière |
|---|---|---|---|---|---|
| 0 | **Vic fusionne la branche dans main** (main redevient la seule vérité) | 10 min | aucune | `git log` : main contient la branche ; CI verte | `git revert -m` du merge |
| 1 | **Purge des runs morts** (liste figée MENAGE-PROD-1, ~14,7 Go — le disque est à 81 %, la chaîne en consommera ~8) | ~1 h (VACUUM compris) | aucune (hors 13 h 30–14 h) | comptes q_v20/q_v19_sources/q_v18 inchangés (433 229 / ~21 M) ; `readyz` 200 | sauvegarde du jour (relue, 6,2 Go) |
| 2 | **Déploiement** (rsync → venv → selftest jobs → build front → crontab → restart) | ~10 min dont **coupure 1–2 min** (restart → readyz stable) | **1–2 min** | `/readyz` 200 stable ; selftest jobs vert ; crontab vérifié ; tampon PDF = sha du déploiement | filets `app-avant-*`/`venv-avant-*` (cp -al) + redeploy de l'ancien commit |
| 2b | *(si Vic dit oui)* **Mot de passe base changé** pendant la coupure | +5 min dans la coupure | inclus | l'app redémarre et `readyz` 200 avec le nouveau mot de passe | remettre l'ancien hash (gardé le temps du geste) |
| 3 | **Données : PLU** — réingérer sur le Mac le zonage GPU de Saint-Denis (PLU du 05/08/2026) et La Possession (25/06/2026), puis pousser le fond Mac→prod (`deploy_donnees.sh`, qui corrige aussi spatial_layers ±1) | ~1–2 h (ingestion + push + contrôles comptages) | aucune | `parite` : FOND tout « = » ; une fiche Saint-Denis affiche le zonage du PLU 20260805 | re-pousser le fond précédent (dump avant push, prévu par sync-run) |
| 4 | **Données : ventes** — `labuse jobs run ingest-dvf` (= refresh-dvf + dvf-marche, désormais enchaînés) | ~5–10 min | aucune | `donnees_jusqu_au = 30/06/2026` partout ; l'incident `fraicheur-retard:DVF` se referme à 07 h 50 | sans objet (idempotent) |
| 5 | **Nouveau classement q_v25** — chaîne complète sur le serveur, de jour, sous surveillance : résiduel île (4 shards, ~23 h cumulées → 2 jours à 2 shards) → cascade (~3 h) → score (22 min) → scénarios (27 min) | **~2 jours** étalés | aucune (le site sert q_v20 pendant tout le calcul) | chaque étape : comptes 433 229 + disque ≥ 3 Go | arrêter la chaîne ; q_v20 n'est jamais touché |
| 6 | **Modèle de probabilité** — dataset reconstruit sans doublon (déjà corrigé dans le code), ré-entraînement recette q_v15, banc K0 | ~1 h (parallèle à l'étape 5) | aucune | K0 (test 2025) ≥ artefact actuel → on prend ; sinon **on garde l'actuel et on le dit** | garder l'artefact gelé actuel |
| 7 | **Contrôles avant bascule** — les 7 de `controler_run`, la garde des rubans, bandes ancien/nouveau avec les 50 plus fortes montées/descentes relues, témoins fiche/classement, rejeu vérité-terrain-3 (permis) | ~2–3 h (dont relecture humaine) | aucune | tout vert, relecture des 50 sans anomalie | ne pas basculer |
| 8 | **Bascule** — `golden-promote q_v25` + `residuel-serve <seq25>` (manifeste + rebuild caches détaché) | < 5 min | aucune (hot-swap) | témoins fiche = classement ; `readyz` 200 ; banc cohérence vert le lendemain | `golden-promote q_v20` + `residuel-serve 17` (< 1 min, q_v20 intact) |
| 9 | **Après** — dégel de calcul-nuit (motif retiré du registre), `LABUSE_CALCUL_NUIT_PROMEUT=0` quelques nuits puis `=1` ; ménage filets + `.bak` cron | 15 min | aucune | 3 nuits calmes de calcul-nuit sans promotion, puis une promotion propre | re-geler au registre |

**Les décisions que Vic doit prendre (questions fermées)** :
1. **Fusionner `ops/deploy-groupe-3` dans main avant le déploiement ?** (recommandé : oui — la
   branche ne porte que des rapports, l'outillage q23, et 4 correctifs nés en prod, tous
   compatibles ; détail LOT 1.)
2. **Purger les runs morts avant la chaîne ?** (recommandé : oui — 19 Go libres seulement,
   incident disque ouvert depuis le 17/11 ; la liste MENAGE-PROD-1 est figée et épargne q_v20,
   q_v19_sources, q_v18 et le futur q_v25.)
3. **Changer le mot de passe de la base pendant la coupure du déploiement ?** (oui/non — geste
   § LOT 5.3, 5 minutes de plus dans la coupure déjà payée.)
4. **q_v25 calculé sur le serveur** (recommandé — les flux quotidiens DVF/SITADEL y font foi),
   en journée surveillée, résiduel en 2 shards parallèles max (mémoire 11 Gi, swap déjà entamé) ?
   Ou sur le Mac avec envoi `deploy_donnees.sh` ?
5. **Modèle p : on ne remplace l'artefact que si le banc K0 est au moins aussi bon** — d'accord
   avec ce critère (sinon on garde q_v15 et le rapport le dit) ?
6. **Dégel de calcul-nuit : après 3 nuits calmes post-bascule, `PROMEUT=0` d'abord, `=1` après
   une semaine** — d'accord ?
7. **Ménage après succès** (filets `app-avant-groupe3c` + `venv-avant-groupe3c` ≈ 5,9 Go, et les
   20 `.bak-deploy-*` de `/etc/cron.d`) — oui/non ?

---

## LOT 1 — une seule branche à déployer

**Fait dans ce mandat** : `git merge origin/main` dans `ops/deploy-groupe-3` → merge `502ff7c03`.
**Un seul conflit**, documentaire (`docs/audit-2026-11/outils-fiches-1/analyser-annonce.md`) :
résolu en gardant le bloc « Comment ça marche » + capture apportés par main **et** la ligne
d'endpoints corrigée par la branche (ESTIMER-3, point unique `estimation3`) — rien défait.
Hook vert sans `--no-verify`, poussé (après `npm ci` : le merge apporte `three` pour la vue 3D
du Gabarit, absent du node_modules du worktree — environnement, pas code).

**Ce que la branche porte en plus de main** (`git diff origin/main..`) :
- **6 rapports** d'exploitation (`DEPLOY-GROUPE-3`, `MENAGE-PROD-1`, `REPRISE-1`,
  `FRAICHEUR-PROD-2` (.md + .csv), `FRAICHEUR-PROD-3`) — traçabilité, zéro risque.
- **6 scripts** `scripts/q23_*` (outillage né du run q_v23 : échantillon, delta exigu, gate,
  scénarios rapides/enrich) — réutilisés au LOT 4.
- **Correctifs nés en prod** : message « Analyse en cours de mise à jour » (AnalyseScenario,
  `scenarios_v2_persist`), `--parcelles-fichier` (cli), lecture du résiduel d'un run candidat par
  numéro (db.py + residuel_runs.py, GUC `labuse.residuel_run_seq`), tolérance selftest/banc
  (jobs.py, f3_metamorphique), CSP bypass du harnais a11y, +3 lignes deploy_app.sh ; 2 tests.
- **Ajouts de ce mandat (LOT 5)** : relecture roulante INPI + retrait des partis (+ tests),
  gel de `calcul-nuit` déclaré au registre (+ tests ajustés), repli du tampon de version
  (`build_rev.py` + tests).

**Verdict : tout peut entrer dans main tel quel.** Aucun des diffs ne contredit main (vérifié
fichier par fichier) ; les correctifs sont des compléments, pas des forks. Vic peut fusionner la
branche dans main avant le déploiement — main redevient la seule vérité.

---

## LOT 2 — l'écart entre la prod et main (lecture seule)

**Le commit servi en prod** : identifié par empreintes de fichiers — l'arbre déployé =
**`2a6dc958b` (merge du 11/11, 10 h 36)**, plus `cli.py` hot-patché au niveau `cc79f59fd`
(outillage delta exigu posé le 12/11). Crontab régénéré le 13/11 04 h 03. Écart vers la branche
fusionnée : **365 commits** (dont 340 de main). Chantiers concernés : documents (DOCS/EXPORTS),
moteur de constructibilité (MOTEUR-VERITE-FIX-1→8), Étude de faisabilité (stationnement,
plafond, capacité), OUTILS-P0/P1, GABARIT-3D, ESTIMER-3/écran, CHIRURGICAL-FIX (A→R),
CAPACITE-1, MINI-CORRECTIONS-1, RETOURS-26→29, PLU-VEILLE-FIX-1.

**Ce que le déploiement déclenche** :
- **Migrations de schéma : aucune nouvelle** depuis l'arbre déployé (les deux SQL du dossier —
  2026-11-02 et 2026-11-04 — sont déjà appliquées : colonnes et tables John présentes en prod).
  Le **heal pré-service** (ExecStartPre, avant l'ouverture du port) est idempotent (~5-10 s) ;
  il créera la table **`etude_revisions`** (chantier Étude — absente en prod, vue au `parite`)
  et les index manquants. Aucun verrou long attendu.
- **`ix_sitadel_permits_date` : existe déjà en prod** (vérifié dans `pg_indexes`) — le heal
  passera en no-op dessus.
- **Dépendances : rien de nouveau** en prod (CairoSVG est dev-only ; requirements-calcul
  inchangés). Front : `npm ci` au build (le lock apporte `three`).
- **Variables d'environnement : aucune nouvelle.** En prod : `LABUSE_CALCUL_NUIT_PROMEUT=0`
  (vérifié — la promotion automatique est déjà coupée), `LABUSE_RADAR_NOTIFS=off`.
- **Jobs du registre** : **+1** `plu-veille-nuit` (quotidien 08 h 10 — compare l'idurba GPU au
  servi par couche : **c'est le correctif de l'angle mort PLU** trouvé par FRAICHEUR-PROD-2) ;
  `ingest-dvf` **enchaîne désormais `dvf-marche`** (le prix de secteur suit la recharge dans la
  même tâche) ; `sonde-sources`/`fraicheur-nuit` inchangés. **Gel au registre (CRON-PROD-1)** :
  le crontab est régénéré depuis le registre — un gel posé à la main serait perdu, c'est
  pourquoi le gel de `calcul-nuit` est maintenant **déclaré au registre** (LOT 5.4, fait sur la
  branche) : purge-runs, radar-cloche, digest **et calcul-nuit** sortiront commentés.
- **Fichiers runtime hors code** : config PLU des 24 communes (`config/plu_destinations/*`),
  `cascade_rules.yaml`, `plu_millesimes.yaml`, `plu_exceptions_effet.json` — livrés par le
  rsync ; artefacts de modèle (`reports/*/FREEZE-*.joblib`) redéposés explicitement ;
  `config/served_manifest.json`/`served_run.txt` **jamais envoyés** (le manifeste prod fait foi).
- **Tampon de version des PDF** : `_commit_build` lisait env → git → rien ; `_FICHE_CODE_REV`
  lisait git → constante datée. En prod (rsync **sans** `.git`, env non posée) : PDF **sans
  version** et fiches sur une constante fausse. **Corrigé sur la branche** : repli sur
  `config/deploiement.json` — le marqueur `{sha, deploye_le, par}` que `deploy_app.sh` écrit
  déjà à chaque déploiement (`src/labuse/build_rev.py`, testé). Après déploiement, chaque PDF
  portera le sha réellement servi.
- **Déroulé/coupure** : garde manifeste → rotation filets (2 gardés) → rsync → deps calcul →
  **selftest des jobs (refus si un job ne charge pas)** → build front → systemd → crontab
  régénéré + vérifié (refus si écart) → marqueur déploiement → restart → readyz **stable** →
  réchauffage fiche-commune détaché. **Coupure = restart → readyz : 1–2 min.**

**État du serveur (21/11, 16 h-17 h Réunion)** : disque **19 Go libres (81 % — incident ouvert
depuis le 17/11, escaladé)** ; mémoire 11 Gi (5,7 utilisés) + **swap déjà entamé (1,4/4 Gi)** —
l'arrière-plan du risque OOM du calcul ; sauvegarde du jour **21/11 13 h 30, 6,2 Go, relue**
(`pg_restore --list` OK) + hebdo du 15/11 + copie externe (13/11, disque TOSHIBA) ; run servi
**q_v20** (manifeste du 27/10) ; crons gelés : purge-runs, radar-cloche, digest, calcul-nuit
(commentaire manuel du 13/11) ; incidents ouverts : disque 80 %+, `verite-permanente` en échec
depuis le 16/11 (harnais — à requalifier après déploiement), `injection-b-en-attente` (1 source
structurante attend le clic), **`fraicheur-retard:DVF` toujours ouvert** — attendu : le contrôle
lit l'horizon sur la table parcelle, que seul `dvf-marche` (étape 4) remettra d'équerre.

---

## LOT 3 — les données à mettre à niveau (Mac ⟷ prod, lecture seule)

### PLU des 24 communes

| Qui | Version servie | Constat |
|---|---|---|
| **Prod** | 21 communes = GPU ; **Saint-Denis `20260423`** et **La Possession `20251217`** = versions **archivées** au GPU ; zonage bâti le 13/10 (sig `5841/2170600/2348269218`) | en retard sur 2 communes (FRAICHEUR-PROD-2 § A.2) |
| **Mac** | règlements **extraits** des bonnes versions : Saint-Denis `97411_PLU_20260805` (23/09), La Possession `97408_PLU_20260625` (15/11) — mais **zonage identique à la prod** (même signature, bâti 15/10) | le texte est prêt, le zonage ne l'est pas |
| **GPU (15/11)** | Saint-Denis 20260805 (publié 24/08), La Possession 20260625 (publié 29/10), Le Port 20241209 republié « partiellement annulé » (18/11/2025 — extraits prod postérieurs, a priori conformes) | la cible |

**Ce qui doit partir du Mac, et comment** : (1) sur le Mac, réingérer le zonage GPU des deux
communes (pipeline GPU existant — celui qui a bâti `parcel_zone_plu` ; `sync-gpu`/ingestion
zones par commune), ce qui met à jour `spatial_layers` + `parcel_zone_plu` + les intersections ;
les prescriptions/SUP suivent le même canal ; les règles calibrées, le stationnement et
l'implantation sont **dans le code** (`config/plu_destinations/*.yaml`, règles du moteur) — ils
partent avec le déploiement, pas avec les données. (2) Pousser le **fond** Mac→prod par le geste
officiel **`deploy/scripts/deploy_donnees.sh`** (délègue à `sync-run.sh` : dump ciblé, restore
`--no-owner`, comptages Mac==prod obligatoires). Tables de fond concernées (`flux_sens.py`) :
`parcels`, `parcel_cadastre_remplacement`, `adresses`, `adresse_parcelles`, `parcel_zone_plu`,
`spatial_layers`, `parcel_couche_intersection`. Ce push **corrige au passage le seul écart de
fond** vu par `labuse parite` : `spatial_layers` 1 931 178 (Mac) vs 1 931 177 (prod).
Vérification : `labuse parite` tout « = » ; une fiche dionysienne sert le zonage 20260805.
**Après la bascule des données PLU, le nouveau job `plu-veille-nuit` surveille l'idurba chaque
nuit — l'angle mort est refermé.**

### Ventes

`labuse jobs run ingest-dvf` = `refresh-dvf` (**186 s** mesurés le 15/11, delta par période)
**puis** `dvf-marche` (recalcul idempotent TRUNCATE+INSERT des médianes de secteur, **dédup du
couple (id_mutation, id_parcelle) par CTE DISTINCT** — le correctif chirurgical-fix-j ; quelques
minutes, ~2 400 lignes). Place disque : négligeable. Effet : l'horizon « ventes jusqu'au … »
passe au 30/06/2026 partout, le prix terrain suit, l'incident `fraicheur-retard:DVF` se referme.
Nota : le Mac porte 31 171 mutations vs 31 079 en prod (le Mac a rattrapé une republication
Etalab plus récente) — flux **quotidien**, la prod fait foi et rattrapera au premier
`ingest-dvf` post-déploiement (le cron du 17/11 était bien no-op, vérifié).

### Autres tables (`labuse parite`, lancé ce jour)

FOND : tout « = » sauf `spatial_layers` ±1 (corrigé par le push PLU). QUOTIDIEN : prod ≥ Mac
partout (normal). CLIENT : prod fait foi, jamais poussé — RAS ; `etude_revisions` absente en
prod (créée par le heal au déploiement, vide au départ : les études en prod se réviseront à la
première ouverture).

---

## LOT 4 — le plan du nouveau classement (q_v25)

**Pourquoi tout rejouer** : le moteur de constructibilité corrigé (MOTEUR-VERITE-FIX-1→8)
change le résiduel, donc la cascade, donc le score — et q_v20 (servi, calculé le 21/10) porte le
défaut connu « 257 éclats/rubans U/AU » (§K quater).

**Pourquoi q_v23 et q_v24 n'ont pas abouti proprement** :
- **q_v23** (calculé 10/11) : complet en apparence mais **276 478 rangs sur 433 229 (64 %)** et
  surtout le faux « terrain exigu » (de grandes parcelles classées bande 0 parce que l'heuristique
  testait l'étroitesse du contour après reculs, pas une absence mesurée) + 4 487 parcelles A/N à
  capacité fantôme (sous-zone U/AU erronée). Vic a refusé la promotion (§D).
- **q_v24** (13/11) : **tué (code -15)** après ~2 h — communes à 1 000-1 600 s chacune, mémoire
  sous pression (11 Gi, swap), pendant que le site servait ; `calcul-nuit` gelé dans la foulée.
- **Ce qui garantit que cela ne se reproduit pas** : (1) les causes algorithmiques sont
  corrigées **dans main** — « trop exigu veut dire que rien ne tient » (FIX-6 LOT 6), « un refus
  se fonde sur une assiette réellement testée » (FIX-7), « un refus exige une absence mesurée »
  (FIX-8), sous-zone par classe réelle (§K bis/ter, érosion 3 m + garde des rubans EXPORTS-FIX-3) ;
  (2) l'exécution change : **de jour, sous surveillance, séquencée** (2 shards résiduel max,
  cascade commune par commune), jamais en concurrence avec la sauvegarde, disque purgé d'abord,
  et le run **n'est pas promu par un automate** (`LABUSE_CALCUL_NUIT_PROMEUT=0`, calcul-nuit
  gelé au registre) — la promotion est un geste humain après les contrôles.

**Purger avant** (décision Q2) : liste figée MENAGE-PROD-1 §A (runs morts q_v11_m137, q_v16,
q_v21, q_v22, q_v24 partiel + seqs 1/2/13 + tables p_model mortes) ≈ **14,7 Go**. On GARDE :
q_v20 + q_v19_sources + q_v19 + seq 17 (**le retour arrière**), q_v18 + seq 15 (le précédent),
les snapshots de calibrage. Transaction unique + VACUUM, comptes q_v20 revérifiés après.

**La chaîne (commandes vérifiées dans la CLI)** — ordre obligatoire, chronométré, disque mesuré
après chaque étape (plancher 3 Go) :

1. **Résiduel île** — `labuse compute-residuel` par shards (runner `scripts/residuel_shard.sh`),
   nouveau `run_seq` (≈ 25). Mesuré q_v23 : 4 shards de 5 h 19 à 6 h 24 (**~23 h cumulées**) →
   à 2 shards parallèles ≈ **2 jours de jour** ; disque ≈ −2 Go.
2. **Cascade + Signal** — `LABUSE_RESIDUEL_RUN_SEQ=<seq> labuse flux-run --label q_v25` (recette
   Signal q_v15 gelée). Mesuré : cascade **~2 h 54** (24 communes), features ~13 min, Signal
   **~17 min** ; ~21 M lignes, disque ≈ −5 Go.
3. **Score LABUSE** — `labuse score-labuse --run q_v25 --cascade-label q_v25 --residuel-run-seq
   <seq>` : **~22 min**.
4. **Scénarios V2** — mode rapide (`scenarios_v2_persist`, outillage `scripts/q23_scenarios_fast.py`) :
   **~27 min** (le mode enrich ~28 h est exclu).
5. **Contrôles** (ci-dessous) puis **bascule**.

**Modèle de probabilité de vente** (chirurgical-fix-j : deux variables gonflées par les doublons
de ventes — la surface de terrain du bilan (jusqu'à ×209) et la feature de prix `s_bati` du
p-model (×57, 934 couples)) : les requêtes sont **déjà corrigées dans main** (CTE DISTINCT).
Plan : reconstruire le dataset (features ext re-matérialisées par `score-v2 --rebuild`, qui lit
désormais les ventes dédupliquées), ré-entraîner **à recette constante q_v15** (protocole K0
gravé : train ≤ 2023, calibration isotonique 2024, **test 2025**), comparer les métriques K0 au
gel actuel (`FREEZE-q_v15.json`). **On ne remplace l'artefact que s'il fait au moins aussi
bien ; sinon on garde l'actuel et le rapport le dit** (décision Q5). Signal mesuré stable aux
corrections (q_v23 : tiers inchangés vs q_v22) — on ne s'attend pas à un bouleversement.

**Contrôles avant bascule** (tous exigés verts) :
1. Les **sept contrôles de `controler_run`** (`autonomie.py:177`) : manifeste candidat présent ·
   run complet (toutes tables à 433 229) · 0 copropriété en palier actionnable · 0 parcelle
   entièrement rouge en actionnable · écart de paliers sous seuil (3 %) · comptes = 433 229 =
   précédent · banc de cohérence frais, achevé, 0 écart.
2. **Garde des rubans** `bascule_gardes.check_uau_erode_ruban` (née de §K quater) : plus
   d'éclats/rubans U-AU érodés servis en capacité.
3. **Comparaison des bandes q_v20 → q_v25** (outillage `scripts/q23_gate.py` relabellisé) :
   répartition par bande, et **les 50 plus fortes montées et les 50 plus fortes descentes
   relues une à une** (fiche ouverte, motif compris) avant d'aller plus loin.
4. **Témoins fiche/classement** : `labuse coherence` (banc : chaque notion, tous ses lecteurs)
   + les témoins du hook (12).
5. **Rejeu de la confrontation aux permis** — scripts de `docs/audit-2026-11/verite-terrain-3/`
   pointés sur q_v25 : la part des permis réellement accordés que le classement dit
   constructibles ne doit pas reculer (réf. 96,3 % sur le servi).

**La bascule** : `labuse golden-promote q_v25` (écrit le **manifeste** via
`bascule_flux.basculer` — le même chemin que le bouton admin, avec ses gardes de fraîcheur)
puis `labuse residuel-serve <seq25>` (bascule atomique du résiduel + rebuild des caches
détaché). **Retour arrière** : `labuse golden-promote q_v20` + `labuse residuel-serve 17` —
< 1 min, q_v20 et toutes ses composantes sont conservées intactes (jamais purgées).

---

## LOT 5 — les restes à embarquer

| Reste | État | Geste |
|---|---|---|
| **Dirigeants — relecture roulante + retrait des partis** | **FAIT sur la branche (ce mandat)** : `sirens_a_relire()` (jamais lus d'abord, puis > 90 j du plus ancien au plus récent — le quota quotidien sert toujours les plus périmés, arrêt quota résumable), option `--fraicheur-jours` (défaut 90), et `_desactiver_partis()` (actif=false pour tout dirigeant que le RNE ne renvoie plus — **jamais sur une réponse vide**, règle « ne pas remplacer du réel par du vide » ; résorbe les 268 orphelins de FRAICHEUR-PROD-3 §7 au fil des relectures). Tests : `tests/test_inpi_relecture_roulante.py` (4, verts). | Part avec le déploiement ; la tâche mensuelle du 6 décembre tournera en roulant. |
| **Dégel du calcul de nuit** | `LABUSE_CALCUL_NUIT_PROMEUT=0` **déjà posé en prod** (vérifié). Gel du 13/11 : était un commentaire manuel du crontab (perdu à la régénération). | **FAIT sur la branche** : gel déclaré au registre (survit au déploiement). Dégel = retirer le motif de `jobs.py` + redéployer le crontab, **après** la bascule q_v25 et 3 nuits calmes ; `PROMEUT=1` une semaine plus tard (décision Q6). |
| **Mot de passe de la base** (exposé lors d'un ancien déploiement) | à faire | Pendant la coupure du déploiement (décision Q3) : `ALTER ROLE labuse WITH PASSWORD '<nouveau>'` (généré, jamais écrit dans un fichier suivi), mise à jour de `/etc/labuse/labuse.env` (droits 640 root:labuse, vérifiés) + restart. L'ancien hash gardé le temps du geste pour pouvoir revenir. |
| **Registre à jour dans main (gel calcul-nuit)** | **FAIT sur la branche** (+ tests `test_autonomie_registre`/`test_cockpit_lot_b` ajustés) — entre dans main à la fusion (Q1). | — |
| **Ménage après succès** | à faire **après** un déploiement réussi + 48 h calmes (décision Q7) | `rm -rf /opt/labuse/app-avant-groupe3c /opt/labuse/venv-avant-groupe3c` (~5,9 Go — le nouveau déploiement aura créé ses propres filets, rotation à 2) ; purge des 20 `/etc/cron.d/labuse.bak-deploy-*` (garder les 2 derniers). |

---

## Méthode

Prod lue en ssh (`sudo -u postgres psql`, `statement_timeout` 20-120 s), 16 h-18 h Réunion —
hors 13 h 30-14 h et 1 h-5 h, rien de lourd. Le commit prod est identifié par empreintes md5 de
fichiers contre l'historique git (pas de `.git` en prod). `labuse parite` exécuté depuis le Mac
(lecture seule par conception). Les durées de la chaîne viennent des mesures réelles de q_v23
(reports/DEPLOY-GROUPE-3.md) ; celles du déploiement, du script `deploy_app.sh` lui-même. Les
commandes du LOT 4 sont vérifiées une à une dans la CLI de la branche (pas de commande déduite).
Code ajouté dans ce mandat : INPI roulant + partis, gel registre, `build_rev` — testés
(`pytest` ciblé vert) ; la suite complète est rejouée par le hook au push.
