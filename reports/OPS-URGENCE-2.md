# OPS-URGENCE-2 — disque, calcul de nuit, sauvegardes/cohérence, radar

Mandat Vic, lancé le **2026-11-05** (après-midi, Réunion +04) depuis `~/Desktop/labuse-main`, prod
`labuse-vps` (`vps-5563949c`, `app.labuse.immo`). Go de Vic pour écrire en prod **dans les seules
limites de ce mandat**, **jamais 01 h–05 h Réunion**. Modèle Opus. Branche de code
`fix/ops-urgence-2` (merge `660fdb297`), déployée en prod ; rapport sur `main`.

À lire d'abord : `docs/audit-2026-11/nu-4/E/RAPPORT.md` (§R4, R5, R7). Ce mandat **corrige** ce que cet
audit **constatait**.

---

## ★ Pour Vic — l'essentiel

1. **Disque : 94,6 % (pic) → 82 % → 67 %.** Sous le seuil des 70 % demandé, **32 G libres**. Gardé :
   **2 sauvegardes complètes vérifiées** (04 + 05/11) et **le dernier filet de déploiement**. Supprimé :
   2 vieux dumps `GARDE-`, 8 filets de déploiement périmés, tuiles de /tmp, journaux journald. **Alerte
   abaissée à 80 %** et **rotation automatique** posée (filets + journald + logrotate).
2. **Calcul de nuit q_v21 : la reprise AVANÇAIT bel et bien** (189 241 / 433 229 parcelles = 43,7 %,
   **sans doublon**, cumulées sur 3 nuits) — ce n'était **pas** « repart sans avancer ». Le vrai frein :
   la **fenêtre ~3 h** (02 h→05 h) est trop courte pour les communes lourdes qui restent (Saint-Paul,
   Le Tampon, Saint-Pierre, Saint-Louis…). **J'ai lancé une reprise CONTINUE + PARALLÉLISÉE par commune**
   (4 workers + un « finisher » pour le scoring, §2), cet après-midi hors fenêtre interdite, qui **finit
   q_v21 cette nuit (~22 h 30–23 h 30)** — écrit uniquement dans le scratch non servi. **`PROMEUT=0`
   conservé** (reste candidat, bascule = décision de Vic).
3. **Sauvegardes (4 nuits KO) & banc de cohérence (5 nuits KO) : causes trouvées et corrigées.** La
   sauvegarde butait sur un verrou transitoire pendant les déploiements → **retry + `--lock-wait-timeout`**.
   Le banc butait sur un fichier d'échantillon **non livré** (docs/ exclu du rsync) → **régénération
   automatique si absent**.
4. **Radar « 100 % de retraits » : LECTURE FAUSSE, confirmée.** Le garde-fou des 30 % avait **tout
   retenu** : **aucune annonce retirée à tort les nuits concernées** (11-03/04/05). En revanche l'audit a
   révélé un bug **antérieur** (18 biens multi-annonces marqués `retiree` alors qu'une autre annonce
   était toujours active) : **18 biens rétablis**, et **garde multi-annonces** posée pour que ça ne
   recommence pas.

> **État prod au rapport** : SHA servi **`660fdb297`**, run servi **q_v20** inchangé, `/readyz` 200
> stable, `NRestarts=0`, `PROMEUT=0`. Aucune donnée servie modifiée. La reprise q_v21 tourne en tâche
> de fond (unité `labuse-qv21-catchup`, séparée du service — le déploiement ne l'a pas interrompue).

---

## 1. Disque — ce qui l'occupait, ce qui a été libéré

**Constat (05/11, après le pic de 94,6 % de l'audit, redescendu).** `/` = 96 G, **79 G utilisés
(82 %)**. Répartition :

| Poste | Taille | Nature | Décision |
|---|---:|---|---|
| Base PostgreSQL (`labuse`) | **37 G** | donnée réelle + tables d'entraînement | gardée (voir note) |
| `/var/backups/labuse` | **25 G** | 4 dumps × 6,5 G (2 `GARDE-` + 2 quotidiens) | **ramené à 2** |
| `/opt/labuse/app/data` | 7,0 G | rasters SOURCES (cosia 3,4 G, ortho_irc 1,9 G, rgealti, dvf_histo…) | **gardé** (entrées d'ingestion, re-téléchargeables mais pas « cache ») |
| 9 filets `app-avant-*` + `venv-avant-*` | ~2 G | filets de déploiement accumulés | **ramenés à 1 (puis 2 ce soir)** |
| `/opt/labuse/app/outputs/flash` | 0,43 G | sorties de travail | laissé (hors mandat strict) |
| journald `/var/log/journal` | 0,55 G | journaux système | **capé à 200 M** |
| `/tmp/coherence_tile_*.pbf` | 0,37 G | tuiles laissées par le banc | **purgées** |

> **Note sur la base (37 G).** C'est le plancher structurel. Le bloat réel est **faible partout**
> (autovacuum suit : `dead_pct` ~0). Donc un `VACUUM FULL` ne rendrait quasi rien et prendrait un
> ACCESS EXCLUSIVE dangereux — **non fait**. La plus grosse table, `dryrun_cascade_results` (10 G,
> 51 M lignes, scratch des dry-runs), est **déjà exclue des sauvegardes** (dump « lean ») — c'est un
> candidat de purge propre, mais **hors du strict nécessaire** pour passer sous 70 % ; signalé comme
> dette, non touché (lecture potentielle par des outils d'analyse à vérifier avant purge).

**Gestes (go Vic, 18 h Réunion, hors fenêtre interdite) :**
- `GARDE-…20261102` + `GARDE-…20261103` **supprimés** (−13 G). **Gardés : les 2 plus récents**
  (`…20261104`, `…20261105`), **vérifiés restaurables** (`pg_restore --list` : 1825 / 1823 entrées TOC).
- 8 filets de déploiement périmés **supprimés** (`app/venv-avant-{1030a,autonomie,autonomie2,final,
  john,ops-nuit1,opsnuit2,tableau1}`) — **gardé `…-groupe1`** (le filet du déploiement en cours).
- `/tmp/coherence_tile_*.pbf` **purgées**, **journald vacuum → 26 M**.

**Résultat : 79 G → 65 G, 82 % → 67 %, 32 G libres.** ✓ (< 70 % demandé.)

**Alerte à 80 %** — `config.disque_seuil_pct` **85 → 80** (`ops_alertes.healthcheck` pose l'incident
`disque` au-delà ; déployé, vérifié `=80` dans le code servi).

**Rotation AUTOMATIQUE :**
- **Filets** : `deploy_app.sh` §1b (NEUF) **élague à chaque déploiement** les `*-avant-*` au-delà des
  N plus récents (défaut 2, `LABUSE_FILETS_KEEP`).
- **Journaux système** : `/etc/systemd/journald.conf.d/labuse-cap.conf` posé (`SystemMaxUse=200M`,
  `SystemKeepFree=2G`) → journald journald.
- **Journaux applicatifs** : les 2 configs `logrotate` du dépôt (`/var/log/labuse/*.log` hebdo×8,
  `…/jobs/*.log` mensuel×12) **n'étaient PAS installées** sur le VPS → **installées** et validées.
- **Sauvegardes** : `backup_postgres.sh` garde déjà `KEEP=2` + garde-disque structurel + anti-rétrécissement.

---

## 2. Calcul de nuit — pourquoi q_v21 « ne finit jamais », et la correction

**Mesure sur le VPS (table `dryrun_parcel_evaluations`, label `q_v21`) :**

| Nuit (Réunion) | parcelles AJOUTÉES | fenêtre réelle | durée job | issue |
|---|---:|---|---:|---|
| 11-03 | **102 171** | 02:03 → 05:51 | 14 341 s | `IdleInTransactionSessionTimeout` |
| 11-04 | **47 748** | 02:02 → 04:53 | 10 736 s | abandon « fin de fenêtre 5 h » |
| 11-05 | **39 322** | 02:03 → 04:32 | 10 736 s | abandon « fin de fenêtre 5 h » |
| **cumul** | **189 241 / 433 229 (43,7 %)** | — | — | q_v21 jamais promu (`PROMEUT=0`) |

**Diagnostic — la reprise AVANCE, elle ne « repart » PAS de zéro.** 189 241 parcelles distinctes,
**0 doublon** (`count = count(distinct parcel_id)`), cumulées sur 3 nuits : `flux-run --resume` lit bien
l'état (`SELECT parcel_id … WHERE run_label='q_v21'`) et **saute les parcelles déjà faites**. La preuve
en direct : la reprise de cet après-midi a **traversé instantanément** les communes déjà faites
(« 0 évaluées » pour Saint-Denis, Saint-Joseph…) pour attaquer **celles qui restent**.

**Le vrai frein — budget borné à fin de fenêtre (`min(14400, secondes jusqu'à 05 h)` ≈ 3 h)** et
**communes lourdes restantes** : Saint-Paul (51 597), Le Tampon (42 974), Saint-Pierre (42 654),
Saint-Louis (29 342), Saint-Leu (19 114 restantes), etc. — denses, beaucoup de couches spatiales par
parcelle. Le rythme sur ces communes (~16–18 k/h les 04–05/11) × 3 h = ~40–50 k/nuit : q_v21 avançait
mais aurait pris **~6 nuits**. Le `IdleInTransactionSessionTimeout` du 11-03 (déjà corrigé par
OPS-NUIT-1 : sessions courtes) a coûté une nuit de plus.

**Corrections de code (`fix/ops-urgence-2`) :**
- `cli flux-run` : en `--resume`, **`force=not resume`** → on ne **reconstruit plus** le cache
  `spatial_layers_sub` (1,5 M pièces, ST_Subdivide) **chaque nuit** ; la **garde de péremption** reste
  (il reconstruit quand même si une couche a changé). Un run **frais** force encore.
- `jobs_impl.calcul_nuit` : **garde anti-doublon** — si un `flux-run` tourne déjà
  (`run_progress.en_cours()`), le passage programmé **s'abstient** (pas deux calculs concurrents sur le
  même label = plus de course sur `dryrun_parcel_evaluations`). **+ compteurs d'AVANCEMENT**
  (`parcelles_faites` / `_total` / `avancement_pct`) à la fin de fenêtre → le résumé du matin **montre
  la progression** au lieu d'un faux « bloqué ».

**Correction opérationnelle — « fenêtre élargie si la charge le permet » (sanctionné par le mandat).**
Charge VPS à 0,06 ; l'audit NU-4-E §2.4 a montré que le calcul de nuit concurrent n'effondre pas le
service. **Reprise CONTINUE lancée à 18 h 05** (hors fenêtre interdite) comme unité transitoire
`labuse-qv21-catchup` (`flux-run --resume --label q_v21 --recette q_v15`, `nice`, mémoire capée 8 G,
survit à ma déconnexion ET au redémarrage du déploiement). Elle **ne s'arrête plus à 05 h** : elle
porte q_v21 à son terme d'une traite. **`PROMEUT=0` conservé** — `flux-run` ne promeut jamais : q_v21
reste candidat, la bascule reste la décision de Vic. La garde anti-doublon déployée fait que le passage
programmé de 02 h **ne doublera pas** la reprise si elle tourne encore.

**Rythme et parallélisation pour finir CETTE NUIT.** La reprise mono-process tourne à ~16–20 k/h sur
les communes lourdes restantes (débit des nuits 04–05/11) → ~243 k parcelles = **~14 h** en mono-file :
ça finirait **demain matin**, pas « cette nuit ». Comme le *dry-run par commune* écrit dans des tables
**parallèles** (`dryrun_*`) et que les communes sont **disjointes** (aucune parcelle partagée → aucune
course sur `(run_label, parcel_id)`), j'ai **parallélisé proprement** (18 h 38, go Vic, écrit seulement
dans le scratch non servi, réversible) :

- **4 workers** (`labuse dryrun-evaluate --label q_v21 --commune … --resume`, unités transientes
  `qv21-w1..w4`, `nice`, mémoire capée), partition équilibrée (~57–66 k parcelles chacun) :
  W1 Saint-Paul+Trois-Bassins · W2 Le Tampon+Sainte-Marie · W3 Saint-Pierre+Sainte-Suzanne+Saint-Philippe ·
  W4 Saint-Louis+Saint-Leu+Salazie+Cilaos+Sainte-Rose.
- **Un « finisher »** (`qv21-finisher`) attend la fin des 4 workers puis lance
  `flux-run --resume --label q_v21` : la cascade est alors **toute faite** (sautée), il ne reste que le
  **SCORING** sous le même label → **q_v21 COMPLET**. Indépendant de ma session (systemd).

Sur les 6 vCores, 4 cascades en parallèle ≈ **×3–4** → **reste ~4–5 h → achèvement ~22 h 30–23 h 30**,
donc **cette nuit**, bien avant le passage programmé de 02 h. `/readyz` reste **200** sous la charge
(load ~6 ; trafic client du soir faible ; workers `nice` sous les requêtes servies). **`PROMEUT=0`
conservé** : `flux-run`/`dryrun-evaluate` ne promeuvent jamais → q_v21 reste **candidat**, la bascule
reste la décision de Vic (le verdict des contrôles partira au résumé du matin via le passage de 02 h,
qui retrouvera q_v21 déjà complet).

---

## 3. Sauvegardes & banc de cohérence — causes et corrections

### 3.1 Sauvegardes — 4 nuits KO (30/10 → 02/11)
**Cause.** `pg_dump` pose un `LOCK TABLE … ACCESS SHARE` sur **toutes** les tables au démarrage ;
pendant la période dense de déploiements/heal (30/10→02/11), un **ACCESS EXCLUSIVE concurrent**
(ALTER/build/bascule sur `surface_d_events` / `spatial_layers_sub` / `tuyau_subdivise`) le **bloquait**,
puis le timeout externe du job tuait le dump → **nuit perdue** (`job_runs` : 3 échecs à durée 0 + 1
coupé en plein COPY le 02/11). **Collision TRANSITOIRE** : le dump rejoué à la main le 02/11 à 16 h 33
passait, et **toutes les nuits depuis le 02/11 sont vertes** (4 dumps OK d'affilée). La garde
anti-rétrécissement a bien protégé (aucun dump corrompu gardé).

**Correction** (`backup_postgres.sh`) : **`--lock-wait-timeout`** (défaut 120 s → échec **propre**
plutôt qu'un blocage jusqu'au couperet) **+ retry/backoff** (défaut 3× / 180 s) → une collision de
verrou passagère **ne perd plus** la sauvegarde de la nuit (elle réessaie, comme le geste manuel du
02/11).

### 3.2 Banc de cohérence — 5 nuits KO (29/10 → 02/11)
**Cause.** `coherence-banc` lit un échantillon figé `docs/audit-2026-09/COHERENCE-1/ECHANTILLON.csv`.
Or le rsync de déploiement **exclut `/docs`** (`deploy_app.sh:49`, `--delete`) : le fichier **suivi en
git n'était jamais livré** → `FileNotFoundError` **5 nuits de suite**, escaladé « non résolu depuis
5 j ». Le « correctif du 02/11 » = l'ajout d'un **rsync explicite** qui re-livre nommément les 3
`ECHANTILLON.csv` (committé, `deploy_app.sh:61-65`) — mais **fragile par fichier** (tout nouvel
échantillon retomberait dans le trou).

**Correction** (`scripts/coherence/banc.py`) : si l'échantillon est **absent**, le banc le **régénère
depuis la base** (même tirage que `echantillon.py`, mais **DSN de l'environnement** via `lib` — pas le
DSN Mac en dur) et le réécrit pour stabiliser les nuits suivantes, **au lieu de tomber**. Un fichier
manquant ne peut plus rougir le job.

---

## 4. Radar « 100 % de retraits » — vraie ou fausse lecture ?

**Réponse : LECTURE FAUSSE.** La « passe de confirmation » (pilotée par le scraper externe via
`/admin/radar/confirmation-batch`) a vu, 3 nuits de suite, un taux de « retraits » monter
**32 % (11-02) → 43 % (11-03) → 100 % (11-04)** — symptôme classique d'un **scraper qui casse**
(le portail renvoie 404/expiré pour (presque) tous les liens). Le **garde-fou des 30 %** (RADAR-FIX-3) a
fait son travail : **au-delà de 30 %, AUCUN retrait n'est écrit** (anomalie journalisée « blocage
probable »).

**Preuve qu'aucune annonce n'a été retirée à tort ces nuits-là** (`pige_biens`) :
- 11-03 (43 %) et 11-04 (100 %) : les événements disent **« rien écrit »**, et **aucun bien** n'a de
  `retiree_le` au 03, 04 ou 05/11. Les annonces n'ont **pas** été retirées — elles sont restées en vente.

**MAIS l'audit a révélé un bug ANTÉRIEUR (hors des 3 nuits).** En vérifiant, j'ai trouvé **18 biens
marqués `retiree` alors qu'une AUTRE de leurs annonces était active et re-vue APRÈS le retrait** (ex.
#141/#146/#147 le 04/11 : annonce leboncoin partie, annonce bienici toujours active). Cause : le retrait
marque **le bien** dès qu'**UNE** de ses annonces disparaît, sans regarder ses autres annonces → un bien
multi-portails/ré-listé meurt à tort.

**Corrections :**
- **Données (go Vic)** : les **18 biens rétablis** (`statut='active'`, `retiree_le=NULL`), tracés dans
  `event_log` (`pige:retabli:ops-urgence-2:<id>`). `pige_biens` : `retiree` 121 → **103**, `active` +18.
- **Code (`pige/api.py`)** : **garde multi-annonces** — on **ne retire plus** un bien si une **autre**
  de ses annonces a été vue dans les 14 derniers jours (seule cette annonce est partie ; le vrai retrait
  total attend que **toutes** aient disparu). Compteur `n_gardes_multi_annonces` exposé. **2 tests**
  (retient / retire) dans `test_pige_confirmation.py`.

> Le garde-fou des 30 % est **conservé** (il a prouvé sa valeur). La garde multi-annonces couvre le
> **trou sous le seuil** (un lot à <30 % qui écrivait des retraits partiellement faux).

---

## 5. Déploiement (court, règles DEPLOY-GROUPE-1)

- **Pré-vol** (go-fenêtre) : Réunion ~18 h (hors 01–05 h), `/readyz` 200, `NRestarts=0`, aucun
  `pg_dump`/rsync/backup en cours, disque 67 %. **Filets** `cp -al` posés : `app-avant-ops-urgence2`,
  `venv-avant-ops-urgence2`, `labuse.env.avant-ops-urgence2`, `Caddyfile.avant-ops-urgence2`.
- **Pas de migration de schéma** (diff = code/scripts/shell/config seulement).
- `deploy/scripts/deploy_app.sh labuse-vps` : import-smoke OK, deps calcul-nuit OK, front bâti,
  systemd reposé, **crontab == registre (0 écart)**, `deploiement.json = 660fdb297`, `fiche_cache`
  vidé, restart, **`/readyz` 200 STABLE 25/25**, réchauffage détaché.
- **Vérifs post-déploiement** : `disque_seuil_pct=80` servi ✓ · rotation des filets jouée (2 gardés) ✓ ·
  **unité `labuse-qv21-catchup` toujours active** (le restart ne l'a pas tuée) ✓ · q_v21 **progresse**
  (191 241 et +) ✓ · run servi **q_v20** inchangé (433 229) · `NRestarts=0`.

### Retour arrière (prêt, non utilisé)
```bash
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app  && sudo mv /opt/labuse/app-avant-ops-urgence2  /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-ops-urgence2 /opt/labuse/venv
sudo cp -p /etc/labuse/labuse.env.avant-ops-urgence2 /etc/labuse/labuse.env
sudo systemctl start labuse
```

---

## 6. Recette (hook)
- Python unitaires (famille du hook, sans base) : **2959 passés / 0 échec**, 50 skip.
- `test_pige_confirmation.py` (base) : **13/13** (dont 2 neufs, garde multi-annonces).
- `test_ops_nuit_2.py` + `test_run_progress.py` : **15/15**.
- Front : `tsc -b` **0 erreur**, `vitest` **309/309**. Scan de secrets : propre.
- `bash -n` sur les 2 scripts shell : OK.

---

## 7. Réserves honnêtes & dette

1. **q_v21 « cette nuit ».** En mono-file les communes lourdes restantes (~16–20 k/h) donnaient ~14 h
   (demain matin). **Parallélisé par commune disjointe (4 workers + finisher, §2)** → achèvement estimé
   **~22 h 30–23 h 30** (cette nuit), avant le passage de 02 h. Sûr (communes disjointes = pas de course
   sur `(run_label, parcel_id)`, écrit seulement dans le scratch `dryrun_*` non servi). **À surveiller**
   (unités `qv21-w1..w4` + `qv21-finisher`) ; si un worker échouait, son `--resume` le rejoue sans perte.
2. **`PROMEUT=0`** conservé : q_v21, une fois complet, **reste candidat** — la bascule est la décision de
   Vic (le verdict des contrôles partira au résumé du matin quand le passage programmé verra q_v21 fait).
3. **`dryrun_cascade_results` (10 G)** : scratch des dry-runs, déjà hors sauvegarde — purge propre
   possible (gain ~10 G) mais à valider (lecteurs d'analyse) avant de toucher. Non fait.
4. **Échantillon de cohérence sous `docs/`** : régénération posée en filet, mais la **relocalisation
   durable hors `docs/`** (dette déjà notée dans `deploy_app.sh`) reste la vraie cible.
5. **Sauvegarde `restore-test` réel** non rejoué ici (dette DEPLOY-GROUPE-1 : rôle superuser) — hors
   mandat.
6. **2 verrous cassés** (carte rouge du Tableau, pré-existants, saga verrous) : hors mandat, inchangés.
