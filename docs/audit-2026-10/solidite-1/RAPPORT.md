# SOLIDITE-1 — RAPPORT

Branche `fix/solidite-1` (worktree `~/Desktop/labuse-solidite`, ports 8760/5960), **non mergée, non poussée**.
Un commit par lot. Base de test : `postgresql://openclaw@localhost:5432/labuse_test`.
Preuves rejouées contre la base servie locale **q_v18** et le VPS (lecture seule).

Objectif : plus de panne en silence, donnée juste dans le temps, mises à jour répétables.

---

## Lot 1 — plus aucune panne silencieuse  (`dca449ea`)

- **`job_runs`** : chaque passage de job laisse une ligne durable (début/fin/statut/durée/erreur/compteurs),
  en plus de l'état JSON. Logs → `/var/log/labuse/jobs/`, **rotation 12 mois**. `MAILTO=""` (fin du mail
  cron vers le vide).
- **`ops_alertes`** : la porte d'alerte **unique** (mail Brevo à Vic + cloche admin). Un incident = **une**
  alerte, puis **un rappel/jour**, puis un **« résolu »**. Vigies : échec de job, **retard** (1,5× cadence),
  disque > 85 %, **/readyz faux**, sauvegarde absente ou **rétrécie > 30 %**.
- **`recap-matin`** (07:30 Réunion) : un seul mail — vert en une ligne, ou la liste. `healthcheck` (15 min)
  route disque + /readyz par la même porte.
- **Garde externe Mac** (`deploy/mac/readyz_watch.sh` + plist launchd 15 min) : survit à la mort du serveur.
- **Preuve (1.6)** : `labuse ops test-alerte` → **4 `.eml`** (échec, retard, 2 résolus). 9 tests verts.

## Lot 2 — le banc chaque nuit, sur la prod  (`39d74442`)

- **`coherence-banc`** joue désormais, après la cohérence multi-lecteurs, les **25 gardes chasse_donnees**
  EN-PROCESS contre la base servie (TestClient + session pilote, lecture seule). Toute garde ajoutée à
  `GARDES` entre **automatiquement**.
- **`chasse_journal`** (`chasse_runs`) : au premier écart, incident `chasse:<garde>` par la porte unique
  (garde + parcelle témoin + écart) ; retour au vert = résolu. Dashboard `/admin/chasse` + `/admin/coherence`.
- **Preuve (2.4)** : passage réel en-process q_v18 → **21 OK · 0 ECART · 4 SKIP** (SKIP = endpoints à
  service externe injoignable hors-ligne). 4 tests verts.

## Lot 3 — le disque et les sauvegardes  (`36601508`)

- **Inventaire** (`INVENTAIRE-DISQUE.md`) : disque **94 % (6,6 Go libres)**, gisement **~20 Go**, projection
  (le prochain run sature), proposition disque OVH.
- **Copie hors-VPS chiffrée** : `backup_offsite.sh` + job **`backup-offsite`** (hebdo, age/gpg + rclone,
  8 hebdo distantes). Non configuré → **code 3 → incident « rappel »**, jamais d'envoi en clair.
- **restore-test** VPS = contrôle de **lisibilité** (`.dump` + `pg_restore --list`) ; le vrai test =
  `deploy/mac/restore_test.sh` + plist **mensuel** (restaure + compare à la prod + alerte).
- **`menage_disque.sh`** (DRY-RUN par défaut) : runs morts, datasets (jamais `p_model_ext_dataset`),
  schéma reliquat, vieille app.
- **Preuve** : `bash -n` OK, offisite non configuré → exit 3 propre, vigie sauvegarde testée. 6 tests verts.

## Lot 4 — une routine de mise à jour toujours pareille  (`bf4ad28b`)

- **`deploy_donnees.sh`** : porte gardée **unique**, 8 gardes ordonnées (sauvegarde → disque → copie
  `--no-owner` + comptages/checksums → intersections → **bascule en dernier** → manifeste → /readyz → banc),
  arrêt au 1er écart, `--no-bascule`.
- **`deploy_app.sh`** : refuse si le manifeste local sert un run absent des données prod ; contrôle le
  manifeste prod après envoi ; le manifeste servi reste exclu du rsync.
- **`labuse parite [--communes]`** : parité Mac==prod sur les tables de référence.
- **`EXPLOITATION.md §0`** : la routine en une page + 5 leçons q_v18.
- **Preuve** : `labuse parite` → parcels/adresses/intersections/dvf **identiques**, data_sources +1
  (structurel documenté). 5 tests verts.

## Lot 5 — la vérité face aux sources, chaque mois  (`<ce commit>`)

- **`verite_sources`** : échantillon de **20 parcelles au hasard, stratifiées** (bizone, zone rouge,
  nouvelle, contenance ≠ dessin + spread commune), confrontées aux **sources officielles en ligne** (cadastre
  IGN API Carto, Géorisques, DVF, BAN, bâtiments RNB) via l'oracle ORACLE-1 ; fiche servie lue en-process.
  Rapport `verite_sources_runs`, dashboard `/admin/verite-sources`. Écart → incident agrégé (parcelle +
  deux valeurs). Séquentiel/espacé (quotas), **aucune écriture hors rapport**.
- **Job `verite-sources`** (mensuel, le 15). CLI `labuse ops verite-sources`.
- **Preuve (5.1)** : passage réel sur 6 parcelles / 6 communes, 5 familles de sources → **10 vrai · 0 faux ·
  32 non_verifiable** (adresses BAN et bâtiments RNB confirmés ; non-vérifiables = appels sans donnée/réseau
  + aire≠contenance DGFiP assumée). 4 tests verts.

**Total : 51 tests SOLIDITE verts + non-régression registre/crontab/horloges/banc.**

---

## Ce qui attend un geste de Vic

| # | Geste | Pourquoi |
|---|---|---|
| 1 | **Agrandir le disque OVH** (+100 Go Block Storage ≈ 4 €/mois, à confirmer) | 6,6 Go libres : le prochain run sature (Lot 3.1) |
| 2 | **Lancer le ménage** `menage_disque.sh --execute` (après revue) | regagne ~20 Go — *geste VPS, montré avant* |
| 3 | **Compte de stockage objet + clé de chiffrement** (`LABUSE_OFFSITE_*`) | activer la copie hors-VPS (Lot 3.2) |
| 4 | **Clé SMTP Brevo + `LABUSE_ADMIN_EMAIL`** dans `/etc/labuse/labuse.env` | que les alertes PARTENT vraiment (sinon dry-run `.eml`) |
| 5 | **Installer les 2 agents Mac** (`deploy/mac/` : garde `/readyz` 15 min + restore-test mensuel) | survie à la mort du serveur + test de restauration réel |

## Effets au prochain `deploy.sh` (automatiques, via le registre)

- Crontab régénéré : `MAILTO=""`, logs `/var/log/labuse/jobs/`, +3 jobs (`recap-matin`, `backup-offsite`,
  `verite-sources`), `coherence-banc` joue aussi les 25 gardes.
- Tables créées à la première exécution : `job_runs`, `ops_incidents`, `chasse_runs`, `verite_sources_runs`
  (CREATE TABLE IF NOT EXISTS, sans verrou — BOOT-VERROU-1).

## Journal des gestes VPS (montrés avant, vérifiés après)

- **13/10 ~16:45 UTC — ménage disque** (`menage_disque.sh --execute --rm-vieux-app --drop-schema`, approuvé Vic « complet ») :
  TRUNCATE p_model_dataset/_v2/_v2bis (~4,2 Go), rm `/opt/labuse/app-avant-0610` (4,2 Go),
  DROP SCHEMA `sauvegarde_20261006` (21 objets), DELETE 1 726 660 lignes mortes de `parcel_p_score_v2`
  (q_v8_calibre_pre_* + q_v2_demo) + VACUUM FULL. **Résultat vérifié : disque 94 % → 76 % (24 Go libres),
  `/readyz` = 200, `p_model_ext_dataset` intact (4 316 630 lignes).** `score_labuse`/`dryrun_cascade_results`
  déjà au plancher (0 ligne morte). `BREVO_API_KEY` + `LABUSE_ADMIN_EMAIL` (kampusreunion@gmail.com) déjà
  posés ; `LABUSE_SMTP_HOST` vide → alertes routées par l'API Brevo (commit `5490ad9d`).
- **EN ATTENTE — crontab** : `deploy_app.sh` jamais lancé (règle « pas de merge » + risque front
  `VITE_RUN_LABEL`). La pose ciblée est prête (`poser_crontab_solidite.sh`, idempotent, refuse si le code
  n'est pas déployé) : `MAILTO=""` + 3 lignes, gel DVF et 6 jobs commentés préservés. À poser APRÈS un
  déploiement du code, **jamais via deploy.sh**.

## Réserve

- 1 échec de test **PRÉ-EXISTANT** hors périmètre : `test_circuit_p_lot1::…pompe_rapides` attend 9 jobs
  « eau », le registre en a 11 depuis CORRECTIFS-1 (sans lien avec SOLIDITE-1 — nos 3 ajouts sont tous
  `touche="exploitation"`, le compte « eau » est INCHANGÉ). À trancher à part.
