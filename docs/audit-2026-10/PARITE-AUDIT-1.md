# PARITE-AUDIT-1 — parité VPS prod ↔ local / origin/main

**Date** : 2026-10-07 · **Mode** : lecture seule (aucune correction appliquée, aucune branche, aucun commit).
**Référence code** : `origin/main` = `143a5739` (`docs(recette-prod-1): MAJ rapport…`).
**Hôte prod** : `labuse-vps` (`vps-5563949c`, Ubuntu 24.04, disque 76/96 Go = 79 %).

**Conventions** : base **locale** = référence pour les **données de référence** ; **prod** fait foi pour les
**données clients** et les **tables alimentées par ses crons** (adresses, Sitadel, BODACC…).
🟢 identique · 🟡 prod plus récente / écart normal · 🔴 prod en retard (à corriger).

---

## Verdict d'ensemble

| Section | Verdict | En un mot |
|---|---|---|
| 1. Branches non mergées | ℹ️ info | 6 branches WIP non livrées (worktrees), hors prod — attendu |
| 2. Code applicatif | 🟢 | `/opt/labuse/app` = `origin/main`, au fichier près (hors artefact auto-généré) |
| 2b. Front servi (dist) | 🟢 | reconstruit depuis la source synchronisée (même commit) |
| 3. Dépendances Python + binaires | 🟢 | 77/77 paquets du verrou présents, versions exactes ; binaires présents |
| 4. Fichiers de données exclus du rsync | 🟢 | tout ce que le runtime lit est présent en prod |
| 5. Base — structure | 🟡 | `public` identique (265 tables) ; 34 tables mortes encore en prod + 1 vue inerte absente |
| 5b. Base — données référence / crons | 🟡 | référence identique ; crons prod **plus récents** (normal) |
| 6. Exploitation — **cron** | 🔴 | **crontab du registre (25 jobs) NON déployé ; 11 crons legacy couvrent un sous-ensemble** |
| 6b. systemd / env / pointeurs run | 🟢 | unit identique+actif, vars requises présentes, run servi identique |

**Un seul 🔴 : l'ordonnancement.** Le code, le front, les dépendances, les données et les pointeurs de run
sont en parité (ou prod plus fraîche). La prod tourne encore sur les **anciens fichiers cron par source**
au lieu du crontab unifié généré depuis le registre — elle exécute ~11 tâches sur les 25 déclarées.

---

## 1. Branches non mergées (`git branch -a --no-merged origin/main`)

Informationnel — ces branches sont des chantiers (worktrees) non livrés ; **aucune n'est en prod**
(prod = `origin/main`). Rien à « rattraper » côté VPS.

| Branche | Dernier commit | Objet |
|---|---|---|
| `audit/docs-audit-1` | `4aff717f` | audit lecture seule de la page « Docs » |
| `audit/g1-mesure` | `c7d27080` | ouverture carte : doublon limites_parcelles = 81 % du poids |
| `fix/g1` | `a3482087` | contour île servi par parcels-ile (overlay supprimé) + brotli |
| `fix/g1-lot3` | `612ecae3` | correctif zones noires (extent 4096 dès z9) + captures |
| `fix/maplibre-1` | `e924e81a` | montée maplibre-gl 4.7.1→6.4.1 (perf GPU réel) |
| `fix/ppr-partiel-a` | `bddb0cbc` | badge PPR partiel (lots 1-2 livrés, lot 3 arrêté) |
| `merge/maplibre-1` | `d3a914d5` | merge de `fix/maplibre-1` |

*(les mêmes existent sur `origin/*` — poussées, pas mergées).*

---

## 2. Code applicatif — `rsync -n --checksum` (mêmes exclusions que `deploy_app.sh`)

Le VPS n'a pas de `.git` (rsync strip) ; la parité est mesurée par `rsync -n -i --checksum`
(owner/group/perms neutralisés, bruit du `-a` inter-UID).

| Constat | Verdict |
|---|---|
| **Aucun** fichier de code/donnée présent localement n'est manquant ou différent sur le VPS | 🟢 |
| Seul écart de contenu : `src/labuse.egg-info/SOURCES.txt` (régénéré par `pip install -e`) | 🟢 ignorable |
| 109 tuiles `.local/ortho-proxy-cache/express/*` présentes en prod, absentes en local (cache runtime) | 🟢 prod en a plus |

> ⚠️ remarque hors parité : `.local/` **n'est pas exclu** par `deploy_app.sh` → un futur
> `deploy_app.sh` supprimerait ce cache ortho du VPS (`--delete`). Non bloquant (le cache se
> reconstruit), mais à ajouter aux exclusions si on veut l'épargner. *(Observation, pas une correction.)*

### 2b. Front servi (`frontend/dist` du VPS)

`dist` se construit **sur le VPS** (ne se copie pas). Pas de hash de commit embarqué, donc parité
établie par la chronologie : source `frontend/src` synchronisée à **03:23:31** (identique à `origin/main`
au checksum), `dist/index.html` + assets bâtis à **03:23:56** le 2026-10-07 — soit **25 s après**, depuis
la source courante. → **dist = même commit** `143a5739`. 🟢

---

## 3. Dépendances

### Python — venv `/opt/labuse/venv` (Python **3.12.3**) vs `requirements.lock` (77 paquets)

| Constat | Verdict |
|---|---|
| **77/77** paquets du verrou présents en prod, **versions exactes** (0 manquant, 0 divergent) | 🟢 |
| 12 paquets en plus côté prod (fermeture transitive d'`anthropic`/`pandas` : `distro`, `httpx`, `jiter`, `greenlet`, `six`, `sniffio`, `truststore`…) | 🟢 normal |

### Binaires système appelés par le code

| Binaire | Prod | Note |
|---|---|---|
| `gdaldem`, `gdalinfo`, `ogr2ogr`, `gdal_translate` | 🟢 présents | GDAL **3.13.2** (⚠ contredit la note mémoire « gdaldem absent » : présent aujourd'hui → relief OK) |
| `git`, `curl`, `pg_dump`, `pg_restore`, `psql` | 🟢 présents | psql 18.4 |
| `node` / `npm` / `npx` | 🟢 présents | node v22.23.1 |
| `weasyprint` (CLI) | absent → **sans objet** | utilisé comme **module Python** (`import weasyprint` ✓, 27 réfs code `WeasyPrint`) |
| `brotli` (CLI) | absent → **sans objet** | utilisé comme **module Python** (`import brotli` ✓) |

Bindings `osgeo/gdal` Python non installés — **normal**, le code appelle GDAL en CLI, pas en module. 🟢

---

## 4. Fichiers de données exclus du rsync que le code lit

Tous les répertoires `data/*` exclus du transfert (ingérés une fois, protégés du `--delete`) sont
**présents** en prod, y compris ceux lus au runtime :

| Chemin lu au runtime | Prod | Chemin lu au runtime | Prod |
|---|---|---|---|
| `data/plu_reglements/` (197 Mo) | 🟢 | `data/cerfa/` (3 Mo) | 🟢 |
| `data/ban/adresses/…` (74 Mo, régén. cron) | 🟢 | `data/fiscal/territoire_fiscal.csv` | 🟢 |
| `data/carte_loyers_reunion_2025.json` | 🟢 | `data/entites/acronymes_moraux.csv` | 🟢 |
| `data/obsimmo_vente_reunion.json` | 🟢 | `data/anc/…` | 🟢 |
| `data/ortho_tiles` · `ortho_irc` · `cosia` · `ml` · `rgealti` · `dvf*` · `insee_rp` · `edf_hta` · `tcsp` | 🟢 | | |

`data/etalab-cadastre` et `data/dgfip-pci-vecteur` **absents** en prod → **sans impact** : leurs
références dans `radar.py`/`connectors` sont des **URL distantes** (`cadastre.data.gouv.fr`), pas des
lectures locales ; seuls les modules `ingestion/*` (one-shot) écrivent sous ces chemins. 🟢

---

## 5. Base de données (`labuse`, local `openclaw@localhost` vs VPS `postgres`)

### 5a. Structure (schéma `public`)

| Objet | Local | VPS | Verdict |
|---|---|---|---|
| **Tables** `public` | 265 | 265 communes (+34) | 🟢 noyau · 🟡 extras |
| Tables présentes **local, absentes VPS** | — | **0** | 🟢 rien ne manque en prod |
| Vues | 11 | 10 (+2 `pg_stat_statements`) | 🟡 1 vue inerte absente (ci-dessous) |
| Vues matérialisées | 1 | 2 (`mv_toitures_tertiaires` en plus) | 🟢 prod en a plus |
| Fonctions | 6 | 6 | 🟢 identiques |
| Triggers | 3 | 4 (`agent_events` en plus) | 🟢 prod en a plus |
| Extensions | 6 | 7 (`pg_stat_statements` en plus) | 🟢 prod en a plus |
| Index | 526 | 528 | 🟢 **0 index manquant en prod** |

**🟡 34 tables mortes encore dans `public` sur le VPS.** Localement, elles ont été déplacées dans un
schéma `poubelle` (nettoyage DISQUE-VPS-1 non encore appliqué à la prod) : `agent_events`, `agent_runs`,
`backup_*`, `*_pre_v8`, `*_prebascule`, `m6_snapshot_*`, `cascade_ext_avant`, `p_model_scores_2026`,
`pv_registry`, `segment_presets*`, `solar_api_cache`, `parcel_adjacence`, `qa_cadastre_bati`, `tdl_faisa`,
`zone_cat_p`, `m50_marker`, `ortho_verdicts_quarantaine`, `conso_baseline_commune`, `algo2_prop_features`,
`p_model_bati_features`, `mvt_overlays`… → **prod a plus**, pas de manque ; seulement du disque à récupérer
(cf. DISQUE-VPS-1, suppression prévue ~20/10). *Non bloquant.*

**🟡 Vue `v_parcelle_contact_compte` absente en prod.** Créée par `CREATE OR REPLACE VIEW`
(`scoring/p_v2/potentiel.py:ensure_vue_contact`) **pendant un backfill potentiel**, pas au boot.
**Aucun lecteur runtime** (0 `FROM`/`JOIN` dans le code) → inerte ; se recrée au prochain backfill p_v2.
Risque faible. Pour la poser dès maintenant (lecture seule côté métier) :
```bash
ssh labuse-vps 'cd /opt/labuse/app && sudo -u labuse /opt/labuse/venv/bin/python -c "
from labuse.db import get_session
from labuse.scoring.p_v2.potentiel import ensure_vue_contact
with get_session() as s: ensure_vue_contact(s); s.commit()"'
```

### 5b. Données — comptages `count(*)` et fraîcheur

**Tables de référence** (local fait foi) — **identiques**, ou prod légèrement devant (cron d'ingestion) :

| Table | Local | VPS | | Table | Local | VPS |
|---|---|---|---|---|---|---|
| `communes_referentiel` | 24 | 24 🟢 | | `rpls_commune` | 24 | 24 🟢 |
| `sudocuh_procedures` | 24 | 24 🟢 | | `taxe_amenagement_taux` | 24 | 24 🟢 |
| `taxe_amenagement_secteur` | 10465 | 10465 🟢 | | `territoire_fiscal_commune` | 24 | 24 🟢 |
| `cout_construction_ref` | 3 | 3 🟢 | | `oll_loyers` / `oll_zonage` | 133/193 | 133/193 🟢 |
| `anc_maille_taux` | 350 | 350 🟢 | | `population_legale` | 24 | 24 🟢 |
| `defisc_fenetres` | 1166 | 1166 🟢 | | `commune_zonage_abc` | 24 | 24 🟢 |
| `lettre_zonage_refs` | 19 | 19 🟢 | | `mairies`/`annuaire_services` | 24/436 | 24/436 🟢 |
| `data_sources` | 129 | **130** 🟡 | | | | |

**Socle cadastre (doit être identique)** — 🟢 : `parcels` 431663=431663 · `parcel_zone_plu` 427419=427419 ·
`p_model_static` 431663=431663 · `parcel_residuel` 431663=431663 · `rnb_batiments` 414081=414081 ·
`dvf_mutations` 29566=29566 · `dvf_mutations_histo` 110477=110477 · `bodacc_depots` 14078=14078 ·
`dpe_records` 1123=1123.

**Tables alimentées par les crons prod** — 🟡 **prod plus récente** (preuve que les crons tournent) :

| Table | Local | VPS | Date la + récente (local → VPS) |
|---|---|---|---|
| `adresses` | 339915 | **340494** | `refreshed_at` 2026-08-19 → **2026-09-05** |
| `sitadel_permits` | 50545 | **50805** | `date_depot` 2026-07-31 → **2026-08-31** |
| `bodacc_procedures` | 674 | **677** | — |
| `data_sources` | — | — | `last_sync_at` 2026-10-06 01:37 → **2026-10-06 09:20** |
| `ingestion_runs` | — | — | `finished_at` 2026-09-19 → **2026-10-06 09:20** |

**Tables clients (prod fait foi)** — local porte du bruit de dev, **prod = vérité, aucun manque réel** :
`comptes` 40/**24**, `utilisateurs` 22/**20**, `pipeline_entries` 227/**82**, `usage_events` 14883/**435**,
`courrier_demandes` 32/**27**, `ia_log` 5988/**5720**, `watched_parcels` 14/**12**, `mail_queue` 5/**4**,
`projets` 9/**68** (prod devant). `score_labuse` local 1 022 997 = plusieurs runs d'historique vs prod
431663 = **le seul run servi** (q_v16) → attendu. → 🟢 (pas de retard prod).

---

## 6. Exploitation

### 6a. 🔴 CRON — crontab du registre NON déployé

- **Attendu** : `deploy.sh` génère `/etc/cron.d/labuse` depuis le registre (`labuse jobs crontab`) =
  **25 jobs** (`labuse jobs run <id>`), puis retire les `/etc/cron.d/labuse-*` legacy.
- **Constaté sur le VPS** :
  - `/etc/cron.d/labuse` **n'existe pas** ;
  - le vérificateur du registre répond **« ✗ ÉCART : /etc/cron.d/labuse ne correspond pas au registre »** ;
  - **11 fichiers legacy** `/etc/cron.d/labuse-*` toujours en place et actifs (ban, bodacc, dpe, dvf,
    sitadel, radar, notifications, sessions, abuse, fraicheur, backup) — avec les **anciens noms de
    commande** (`labuse ingest-ban`, `refresh-dvf`, `radar-sources`, `purge-sessions`, `abuse-scan`…).

**Conséquence** : la prod exécute ~11 tâches ; **~14 jobs du registre ne sont jamais ordonnancés**, dont :
`healthcheck`, `sante-endpoints`, `pg-maintenance`, `restore-test`, `mail-queue-consommer`,
`ingest-sirene`, `detect-events`, `digest`, `radar-cloche`, `radar-cycle-mensuel`, `agents-sources`,
`coherence-banc`, `coherence-robinets`, `copilote-purge`, `fiche-commune-cache`, `filtres-sources`,
`sonde-sources`, `sync-gpu`. *(Les données restent fraîches car les crons legacy couvrent l'ingestion ;
mais la supervision, la purge, la maintenance PG et la consommation de file mail ne tournent pas.)*

**Correctif exact** (à lancer **sur le VPS en root** ; pose le crontab du registre PUIS retire le legacy
sans trou — idempotent) :
```bash
ssh labuse-vps
sudo bash /opt/labuse/app/deploy.sh          # génère /etc/cron.d/labuse (tz=reunion) + retire les legacy
# vérif :
sudo -u labuse /opt/labuse/venv/bin/labuse jobs crontab --tz reunion --verifier /etc/cron.d/labuse && echo OK
ls /etc/cron.d/labuse-*    # doit renvoyer « aucun » (sauvegardés sous /root/crons-legacy-<date>/)
```

### 6b. systemd / env / pointeurs run

| Point | Constat | Verdict |
|---|---|---|
| Unit `labuse.service` | `/etc/systemd/system/labuse.service` **identique** au dépôt ; service **active + enabled** | 🟢 |
| Vars d'env **requises** | toutes présentes dans `/etc/labuse/labuse.env` (DB, SECRET_KEY, AUTH, SMTP×4, BREVO + 8 templates, STRIPE×5, ANTHROPIC, ADMIN_EMAIL, MAIL_*, PUBLIC_URL…) | 🟢 |
| Vars **optionnelles** absentes | `GOOGLE_MAPS_EMBED_KEY` (panorama street-view), `INPI_API_USERNAME`/`INPI_API_PASSWORD` (enrichissement dirigeants), `LABUSE_AGENT_PLAFOND_EUR` (défaut 0) — toutes `os.environ.get` à **dégradation gracieuse** | 🟡 à confirmer |
| Flags/overrides absents | `LABUSE_DISABLE_*`, `LABUSE_QUOTA_*`, `LABUSE_SERVED_RUN` (**volontairement retiré** — `served_run.txt` gouverne), `PYTHONPATH`/`PYTEST_*`, dirs → **défauts code**, absence normale | 🟢 |
| `config/served_run.txt` | **q_v16** = **q_v16** | 🟢 identique |
| `config/run_precedent.txt` | **q_v11_m137** = **q_v11_m137** | 🟢 identique |
| Résiduel servi (`residuel_runs.is_served`) | `run_seq=13` des deux côtés | 🟢 identique |

> 🟡 `GOOGLE_MAPS_EMBED_KEY` + `INPI_API_*` : non bloquants (fonctionnalités désactivées si absentes).
> À renseigner dans `/etc/labuse/labuse.env` **seulement si** le panorama Google et l'enrichissement INPI
> sont voulus en prod, puis `sudo systemctl restart labuse`. *(Décision Vic — non appliqué.)*

---

## Ce qu'il reste à faire pour « prod = ou mieux » (par priorité)

1. **🔴 Déployer le crontab du registre** → `sudo bash /opt/labuse/app/deploy.sh` sur le VPS (§6a).
   Seul vrai retard de la prod. Rétablit supervision, maintenance PG, purge, file mail.
2. 🟡 (optionnel) Renseigner `GOOGLE_MAPS_EMBED_KEY` / `INPI_API_*` si ces intégrations sont voulues (§6b).
3. 🟡 (hygiène, non urgent) Appliquer le nettoyage DISQUE-VPS-1 : déplacer/supprimer les 34 tables mortes
   de `public` sur le VPS (prévu ~20/10) ; poser la vue inerte `v_parcelle_contact_compte` si souhaité (§5a).
4. ℹ️ (confort) Ajouter `.local` aux exclusions de `deploy_app.sh` pour épargner le cache ortho (§2).

Aucune autre divergence : code, front, dépendances, binaires, données de référence, socle cadastre et
pointeurs de run sont en parité ; les données de crons/clients sont **plus fraîches en prod**, comme attendu.

---

# Annexe A — les 25 jobs du registre (`src/labuse/jobs.py`)

Heures en **fuseau Réunion** (ce que génère `labuse jobs crontab --tz reunion`).
📧 = envoie un mail **client** · 🛎️ = alerte **admin** (cloche) · 👤 = touche des **données client** sans mail · — = infra/sources.

### Groupe « l'eau » (sources amont) — `touche=eau`

| # | Job | Ce qu'il fait | Mail/clients | Fréquence |
|---|---|---|---|---|
| 1 | `sonde-sources` | Requête HTTP sur chaque source interrogeable : détecte une version amont plus récente, **n'ingère pas** | 🛎️ cloche si neuf | quotidien 07:00 |
| 2 | `agents-sources` | Agent IA lit les pages amont sans API lisible, sous plafond de dépense | 🛎️ cloche | **dim. 1 sem/2** 23:00 |
| 3 | `filtres-sources` | Rejoue les contrôles qualité sur les versions réellement servies | — | quotidien 07:05 |
| 4 | `coherence-robinets` | Sonde « tout coule » : 2 chemins d'un même chiffre doivent concorder + eau ancienne | 🛎️ ligne rouge | quotidien 07:25 |
| 5 | `ingest-bodacc` | Ingère BODACC (procédures collectives) → nourrit Radar/score ; **replie `fraicheur-derives`** | — | quotidien 06:40 |
| 6 | `ingest-sitadel` | Permis SITADEL (`ingest-permits`) → veille foncière + golden candidat | 👤 veille client | **mensuel le 10** 04:30 |
| 7 | `ingest-dpe` | DPE ADEME | — | **mensuel le 12** 04:00 |
| 8 | `ingest-sirene` | SIRENE (concurrents géolocalisés) + rattachement établissement→parcelle | — | **mensuel le 7** 04:00 |
| 9 | `sync-gpu` | Diff PLU des 24 communes → veille foncière + bandeau PLU | 👤 veille client | **mensuel le 15** 04:00 |

### Groupe « exploitation »

| # | Job | Ce qu'il fait | Mail/clients | Fréquence |
|---|---|---|---|---|
| 10 | `backup-postgres` | Dump PostgreSQL (pg_dump inline) + rotation | — | quotidien 13:30 |
| 11 | `pg-maintenance` | `VACUUM ANALYZE` des 6 tables chaudes | — | **hebdo dim.** 04:00 |
| 12 | `healthcheck` | Sonde `/health` + disque, 2 échecs → alerte | 🛎️ admin | **toutes les 15 min** |
| 13 | `sante-endpoints` | Sonde endpoints métier avec DB (accueil/sources/fiche/radar/projets/ask) | 🛎️ admin | **toutes les 30 min** |
| 14 | `copilote-purge` | Purge les conversations Copilote au-delà de la rétention (7 j) | 👤 **supprime données client** | quotidien 03:30 |
| 15 | `radar-cloche` | Annonces du jour qui matchent une veille client → pose à sa cloche | 👤 client (le digest e-maile) | quotidien 07:05 |
| 16 | `radar-cycle` | Cycle de vie des annonces (expirées / en-vente-longue / à-revérifier) | — | quotidien 04:00 |
| 17 | `radar-cycle-dvf` | Rapprochement DVF : bien rattaché + vente → `vendue` (**ne ré-ingère pas DVF**) | — | quotidien 04:30 |
| 18 | `radar-cycle-mensuel` | Qualifie `retiree_sans_vente` (cible Courrier) | — (interne) | **mensuel le 1er** 05:30 |
| 19 | `evaluer-suivis` | Veille des parcelles **suivies par un client** (mutation/permis/BODACC/zonage) → cloche | 👤 client → digest | quotidien 07:02 |
| 20 | `detect-events` | Bascules du marché (diff run servi/précédent) + parcelle suivie qui bascule | 👤 client → digest | quotidien 07:04 |
| 21 | `digest` | **UN mail par compte** : parcelles suivies + Radar + nouveautés | 📧 **client** (via mail_queue, différé) | quotidien 07:15 |
| 22 | `mail-queue-consommer` | Fait partir les mails dûs (digest différé, programmés J+3/J+10) + rejoue les échecs transitoires | 📧 **client** (l'expéditeur de la file) | **toutes les 5 min** |
| 23 | `fiche-commune-cache` | Précalcule le contexte des 24 communes (ouverture fiche < 500 ms) | — | quotidien 03:00 |
| 24 | `coherence-banc` | Banc de cohérence nocturne : chaque notion, tous ses lecteurs (île) | 🛎️ cloche si écart | quotidien 03:45 |
| 25 | `restore-test` | Restaure le dernier dump dans une base jetable, vérifie, DROP | 🛎️ admin si échec | **mensuel le 1er** 05:00 |

Un seul job envoie des mails clients de masse (`digest`) ; un seul les fait réellement partir de la file
(`mail-queue-consommer`). Les deux sont actuellement **non planifiés** en prod (cf. §6a).

---

# Annexe B — mécanique des mails (invitation / reset / digest)

La façade unique `mail.envoyer_mail` (`src/labuse/mailfile.py:231-252`) **enfile** la ligne dans `mail_queue`
PUIS, **si l'envoi est immédiat** (`prevu_at` absent), **déclenche le départ tout de suite**
(`_tenter_depart` → appel Brevo → état `recu`). États : `en_attente` (en file) → `recu` (« Reçu par Brevo »
= **parti**) ; `a_rejouer` (échec transitoire, backoff 5 min/1 h/24 h) ; `echec` ; `annule`.

**→ L'invitation d'essai et le reset de mot de passe partent DIRECTEMENT** (envoi synchrone à la requête),
**sans** `mail-queue-consommer`. Le worker ne sert qu'aux mails **différés** (digest via `differe=True`,
programmés J+3/J+10) et aux **rejeux** (`a_rejouer`).

**Preuve en prod (2026-10-07)** — `mail_queue` : **4 lignes, toutes `recu`** (parties, `parti_at` +
`message_id` renseignés), **0 en attente**, alors que le worker n'est pas planifié :

| Template | État | Parti le |
|---|---|---|
| `LABUSE-D-MDP-OUBLIE` (reset mot de passe) | `recu` ✅ | 02:29 |
| `LABUSE-D-MDP-MODIFIE` (mdp modifié) | `recu` ✅ | 02:30 |
| `LABUSE-E-ESSAI-48H` (essai 48 h) | `recu` ✅ | 01:30 |
| `LABUSE-0-SOUSCRIPTION` (lien souscription) | `recu` ✅ | 01:30 |

**Perte réelle sans le worker** : rien n'attend aujourd'hui, mais sans `mail-queue-consommer` (a) un envoi
transactionnel qui échoue transitoirement (`a_rejouer`) n'est jamais rejoué, et (b) le **digest** et les
**relances d'onboarding J+3/J+10** ne partent jamais. Chemin nominal transactionnel : OK sans le cron.

---

# Annexe C — correspondance des 11 fichiers legacy → les 25 jobs du registre

18 commandes distinctes (certains fichiers en enchaînent plusieurs par `&&`). Horaires legacy tels que posés.

| Fichier legacy | Commande legacy | Horaire | Remplacé par (registre) | Verdict |
|---|---|---|---|---|
| `labuse-bodacc` | `ingest-bodacc` | quotidien 06:30 | **`ingest-bodacc`** | ✅ remplacé |
| `labuse-bodacc` | `fraicheur-derives` | chaîné | **`ingest-bodacc`** (replie `fraicheur-derives`, `jobs_impl.py:787`) | ✅ remplacé |
| `labuse-dpe` | `ingest-dpe` | mar 09:20 | **`ingest-dpe`** (mensuel le 12) | ✅ remplacé |
| `labuse-dpe` | `fraicheur-derives` | chaîné | **`ingest-bodacc`** (quotidien) | ✅ remplacé |
| `labuse-sitadel` | `permits_sdes --refresh` | quotidien 06:15 | **`ingest-sitadel`** (→ `ingest-permits`, mensuel le 10) | ✅ remplacé |
| `labuse-sitadel` | `fraicheur-derives --hebdo` | lun 07:45 | `ingest-bodacc` (quotidien) couvre le cœur ; variante `--hebdo` non reprise | ⚠️ partiel (mineur) |
| `labuse-notifications` | `evaluer-suivis` | quotidien 07:00 | **`evaluer-suivis`** | ✅ remplacé |
| `labuse-notifications` | `evaluer-veilles` | chaîné | **aucun** — retiré VEILLE-2 (secteurs/recherches sauvegardées archivés) | ⛔ retiré **volontaire** |
| `labuse-notifications` | `notifier-fraicheur` | chaîné | **aucun** — fraîcheur affichée à la lecture (`check-fraicheur` live) + cloche `sonde-sources` | ⛔ retiré **volontaire** |
| `labuse-notifications` | `purge-notifications` | chaîné | **aucun** — rétention des notifications non reprise | 🟡 non couvert (mineur) |
| `labuse-notifications` | `digest --freq quotidien` | chaîné | **`digest`** (+ `mail-queue-consommer` pour l'envoi) | ✅ remplacé |
| `labuse-radar` | `radar-sources` | lun 06:00 | **`sonde-sources`** (+ `agents-sources`) — même fonction « sonde amont, signale » | ✅ remplacé |
| `labuse-fraicheur` | `check-fraicheur` | quotidien 10:30 | **aucun** — sentinelle calculée **à la lecture** (verdict live), cron redondant | ⛔ retiré **volontaire** |
| `labuse-backup` | `backup_postgres.sh` | quotidien 09:30 | **`backup-postgres`** (réimpl. Python) | ⚠️ remplacé, **policy ≠** |
| `labuse-backup` | `db_maintenance.sh` | dim 08:00 | **`pg-maintenance`** (VACUUM ANALYZE 6 tables chaudes) | ⚠️ remplacé, **plus étroit** |
| `labuse-ban` | `ingest-ban --download` | le 5 à 07:30 | **aucun** | 🔴 **NON COUVERT — à garder** |
| `labuse-dvf` | `refresh-dvf` | mer 09:00 | **aucun** (`radar-cycle-dvf` rapproche, **n'ingère pas**) | 🔴 **NON COUVERT — à garder** |
| `labuse-abuse` | `abuse-scan` | quotidien 10:00 | **aucun** | 🔴 **NON COUVERT — à garder** |
| `labuse-sessions` | `purge-sessions` | quotidien 08:00 | **aucun** (aucune purge au runtime) | 🔴 **NON COUVERT — à garder** |

### Les 4 commandes genuinement non couvertes (à ne PAS laisser disparaître)

| Commande | Rôle | Alimente | Conséquence si supprimée |
|---|---|---|---|
| `ingest-ban --download` | BAN 974 → table `adresses` | **tout le géocodage** du produit | les adresses figent (dernier refresh prod 05/09) |
| `refresh-dvf` | DVF : recharge les millésimes Etalab modifiés | `dvf_mutations`, prix, `radar-cycle-dvf` | plus aucune nouvelle vente DVF |
| `abuse-scan` | Score quotidien des patterns de scraping → `abuse_scores` | alerte admin (anti-scraping) | plus de détection d'abus |
| `purge-sessions` | Supprime les `sessions_auth` expirées | hygiène (dette AC-011) | accumulation de lignes mortes |

⚠️ Écarts de comportement à connaître sur les 2 « remplacés mais différents » :
- **backup** : le job Python fait rotation **14 dumps** et **n'a PAS le garde-disque** `df` de
  `backup_postgres.sh` (qui gardait `LABUSE_BACKUP_KEEP=4` + suppression des plus anciens si disque serré,
  DISQUE-VPS-1). **Sur un disque à 79 %, 14 dumps quotidiens peuvent remplir le disque.** À vérifier/aligner
  (`BACKUP_ROTATION_N` du job vs KEEP=4) avant de retirer `labuse-backup`.
- **pg-maintenance** : VACUUM ANALYZE sur **6 tables** (`parcels, event_log, pige_biens, pige_faits, veilles,
  dvf_mutations`) au lieu de la **base entière** (`db_maintenance.sh`). Le reste repose sur l'autovacuum.

### Comment garder les 4 non couvertes — deux voies

**Voie A (immédiate, zéro code) — conserver seulement leurs fichiers legacy.** Lors du retrait legacy
(Annexe D), **ne pas supprimer** `labuse-ban`, `labuse-dvf`, `labuse-abuse`, `labuse-sessions` ; retirer
uniquement les 7 remplacés. Les 4 gardés sont autonomes (sourcent l'env, `flock`, loggent) et continuent
de tourner. Aucun double (aucun n'a d'équivalent registre ; `labuse-dvf` rejoue `fraicheur-derives`, qui
est idempotent). **Limite** : un futur `deploy.sh` complet les supprimerait → voie B pour durer.

**Voie B (propre, un commit) — les ajouter au registre.** Les 4 commandes CLI existent déjà ; l'ajout est
mécanique, calqué sur `ingest-dpe` (qui ne fait qu'appeler `_ingest_via_cli`). Dans `src/labuse/jobs.py`,
4 entrées `_j(...)` ; dans `src/labuse/jobs_impl.py`, 4 fonctions `_ingest_via_cli(ctx, "<commande>")`
(ex. `ingest-ban` → `_ingest_via_cli(ctx, "ingest-ban", "--download")`). Le crontab généré les porterait
alors, et `deploy.sh` cesserait de diverger. **Recommandation : A tout de suite, B ensuite.**

> `purge-notifications` (mineur) : retirer `labuse-notifications` l'arrête aussi. Rétention des
> notifications à 90 j — sans impact fonctionnel immédiat ; à ajouter au registre (voie B) si la table enfle.

---

# Annexe D — poser UNIQUEMENT le crontab du registre + retirer le legacy (adapté : garde les 4)

Aucune autre étape de `deploy.sh`. **Rien n'est appliqué — à lancer sur le VPS.**

```bash
ssh labuse-vps

# 1) Générer le crontab depuis le registre dans un fichier d'attente ÉDITABLE.
#    Le suffixe ".nouveau" contient un point → cron IGNORE ce fichier tant qu'il est là
#    (les fichiers de /etc/cron.d avec un point ne sont jamais exécutés) : édition sans risque.
sudo -u labuse /opt/labuse/venv/bin/labuse jobs crontab --tz reunion \
  | sudo tee /etc/cron.d/labuse.nouveau >/dev/null

# 2) (optionnel) COMMENTER les jobs non voulus : préfixer leur ligne d'un '#'
#    (ex. "... exec labuse jobs run restore-test"). NE PAS lancer --verifier après (il exige
#    l'égalité stricte au registre et refuserait le commentage).
sudo nano /etc/cron.d/labuse.nouveau

# 3) Poser le crontab actif (racine, 644 — obligatoire pour /etc/cron.d, sinon ignoré).
sudo install -o root -g root -m 644 /etc/cron.d/labuse.nouveau /etc/cron.d/labuse
sudo rm -f /etc/cron.d/labuse.nouveau

# 4) Retirer SEULEMENT les 7 fichiers legacy REMPLACÉS (sauvegardés d'abord).
#    On GARDE labuse-ban, labuse-dvf, labuse-abuse, labuse-sessions (non couverts — cf. Annexe C).
sudo mkdir -p /root/crons-legacy-manuel-$(date +%Y%m%d)
for f in bodacc dpe sitadel notifications radar fraicheur backup; do
  sudo cp "/etc/cron.d/labuse-$f" "/root/crons-legacy-manuel-$(date +%Y%m%d)/" 2>/dev/null
  sudo rm -f "/etc/cron.d/labuse-$f"
done

# 5) Recharger cron.
sudo systemctl restart cron

# Contrôle (lecture seule) :
ls -l /etc/cron.d/labuse*   # attendu : labuse + labuse-ban + labuse-dvf + labuse-abuse + labuse-sessions
grep -c '^[0-9*]' /etc/cron.d/labuse   # nb de jobs actifs du registre
```

⚠️ Avant de retirer `labuse-backup` (étape 4) : aligner la rotation du job `backup-postgres` (voir Annexe C),
sinon 14 dumps quotidiens sur un disque à 79 %. Les jobs commentés / fichiers gardés seront **écrasés par un
futur `deploy.sh`** (qui régénère depuis le registre) — porter les désactivations/ajouts dans le code (voie B).
