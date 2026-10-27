# POSTDEPLOY-1027 — les trois suites du déploiement du 27/10

Branche `fix/postdeploy-1027` (depuis `origin/main`), worktree `~/Desktop/labuse-postdeploy`, ports 8840/6040.
Autonome P1-P3 ; commit + rapport + push par point. P4 n'est joué qu'**après merge dans main par Vic**.

---

## P1 — `doctor` crée les fonctions SQL

### Diagnostic

Les fonctions SQL créées par le code (`CREATE FUNCTION` du dépôt) sont au nombre de **trois** :

| Fonction | Définie dans | Usage |
|---|---|---|
| `labuse_zone_famille(text)` | `models.py` `ZONE_FAMILLE_FN` | famille U/AU/A/N depuis le subtype (faisabilité, implantation, assemblage, app, résiduel) |
| `labuse_hauteur_lidar_m(real)` | `models.py` `HAUTEUR_LIDAR_FN` | borne des hauteurs LiDAR (**Gabarit 3D** `api/gabarit.py`, résiduel, score, filtres hauteur) |
| `labuse_set_geom_2975()` | `models.py` (dans `ensure_geom_2975`) | fonction-trigger reprojection 4326→2975 |

**Racine de l'incident prod** : `ensure_schema` (le chemin pris au **boot** et par `doctor`) appelait
`_ensure_schema_steps`, qui créait bien `labuse_set_geom_2975` (via `ensure_geom_2975`) mais **jamais**
`labuse_zone_famille` ni `labuse_hauteur_lidar_m`. Ces deux-là n'étaient posées que par `create_all`
(`ensure_zone_famille_fn` / `ensure_hauteur_lidar_fn` appelées *après* `_ensure_schema_steps`) — chemin
qui n'est **pas** pris au boot prod. Sur une base où elles manquaient, le Gabarit 3D tombait en **500**
(`SELECT labuse_hauteur_lidar_m(faitage_m) …`) et `doctor` ne regardait aucune fonction → **silencieux**.

### Correctif

- `models.py` : registre **unique** `SQL_FUNCTIONS` (nom → DDL idempotent, `None` pour la fonction-trigger
  posée avec ses triggers) + `REQUIRED_SQL_FUNCTIONS`. Nouvelle `ensure_sql_functions(engine)` appelée
  **dans `_ensure_schema_steps`** → boot / `doctor --fix` / `create_all` **convergent** sur la même liste.
  `create_all` ne porte plus ses deux appels séparés (supprimés : la dérive est éliminée à la source).
- `state.py` `schema_status` : vérifie chaque `REQUIRED_SQL_FUNCTIONS` via `pg_proc` et ajoute
  `fonction <nom>` aux `missing` → une fonction absente rend `ok=False` ⇒ `doctor` sort **✗ Schéma** et
  code de sortie **1** (erreur, pas avertissement).

### Tests (`tests/test_state.py`)

- `test_doctor_signale_fonction_sql_manquante_et_ensure_schema_la_recree` : base sans
  `labuse_hauteur_lidar_m` → `schema_status` KO + nommée ; après `ensure_schema` → présente et vert.
- `test_registre_fonctions_sql_couvre_tout_create_function_du_depot` : garde — scanne le source réel
  (`CREATE FUNCTION …`) et exige que chaque nom soit dans `REQUIRED_SQL_FUNCTIONS` (empêche la récidive :
  une fonction ajoutée au code mais non déclarée serait invisible de `doctor`).

`pytest tests/test_state.py` → **13 passed** (3 ciblés + 10 existants, aucune régression).

### Comparaison avec la prod (lecture seule)

`ssh labuse-vps … psql -d labuse "SELECT proname FROM pg_proc WHERE proname IN (…)"` au 27/10 :
les **trois** fonctions sont présentes (`labuse_hauteur_lidar_m`, `labuse_set_geom_2975`,
`labuse_zone_famille`). `labuse_hauteur_lidar_m` y avait été recréée **à la main** pendant DEPLOY-1027
pour lever le 500 du Gabarit. **Aucune fonction absente en prod aujourd'hui.** Le correctif garantit
qu'au prochain `ensure_schema` prod elles seront (re)créées idempotemment sans geste manuel, et que
`doctor` les surveillerait désormais.

---

## P2 — aucun fichier lu à l'exécution sous un dossier exclu du déploiement

### Diagnostic

`deploy_app.sh` n'envoie PAS `docs/`, `reports/`, `qa/`, `captures/`, `audit_shots/`, `tests/`,
`outputs/`, `exports/` ni certains `data/*`. Un fichier **versionné** sous l'un d'eux et **lu à
l'exécution** est présent en dev mais **absent en prod** → repli silencieux (le bug des pieds
« Sources : » en ids bruts). Revue de `src/labuse` (AST + relecture). **Quatre** lectures runtime de
fichiers versionnés sous dossier exclu :

| Fichier lu | Lecteur runtime | Effet en prod (avant) |
|---|---|---|
| `docs/CIRCUIT/inventaire/reservoirs.csv` | `exports/pieds.py` (pieds de PDF) | pieds « Sources : » en **ids bruts** |
| `docs/CIRCUIT/inventaire/moteurs.csv` | `circuit_dependance.py` (Circuit « À faire ») | ligne « Calculer » **jamais** affichée |
| `docs/audit-2026-09/SOURCES/SCHEMAS.csv` | `circuit_garanties.py` (verrou G2) | verrou G2 **aveugle** aux champs « à voir » |
| `qa/golden_check.py` (parsé pour `GOLDEN_IDUS`) | `sonde_circuit.py` (sonde catégorielle) | témoins golden **tombent au repli** |

### Correctif

- Les trois fichiers de données déplacés (`git mv`) sous **`config/circuit/`** :
  `reservoirs.csv`, `moteurs.csv`, `schemas.csv`. Lecteurs runtime repointés.
  Générateurs/consommateurs dev (`scripts/inventaire/*`) mis à jour pour que le CSV reste
  **régénérable au même endroit** (un `_src()`/`_MOVED` route les 2 fichiers déplacés vers `config/`,
  le reste de l'inventaire reste sous `docs/`).
- `GOLDEN_IDUS` : extraits dans **`config/circuit/golden_idus.json`** (source unique, 32 ids).
  `sonde_circuit.py` lit désormais ce JSON (déployé) au lieu de parser `qa/golden_check.py` ;
  `qa/golden_check.py` charge la même source → plus de double liste.
- `config/` est déployé par `deploy_donnees.sh`/`deploy_app.sh` (seuls `served_manifest.json` et
  `served_run.txt` y sont exclus, car prod-owned) : les quatre lectures aboutissent désormais en prod.

**Non déplacé (classé, non-bug) :** `reports/m6-audit/golden/golden-parcelles.json` lu par
`bascule_gardes.check_golden_regenere` — appelé **uniquement** par les scripts `scripts/bascule_*.py`,
joués depuis le dépôt complet sur le Mac (jamais le runtime prod), et qui **lève bruyamment**
(`GoldenPerimeError`) si le fichier manque — l'inverse du repli silencieux.

### Test (`tests/test_deploy_runtime_reads.py`)

`test_aucune_lecture_runtime_sous_un_dossier_exclu_du_deploiement` : parse les exclusions de
`deploy_app.sh`, reconstruit par AST le chemin de chaque lecture de fichier de `src/labuse`
(`open()` en lecture, `Path.open/.read_text/.read_bytes`, y compris via constante de module), et
échoue si ce chemin est **versionné (git) ET sous un dossier exclu**. C'est ce test qui a fait
remonter la 4ᵉ lecture (`qa/golden_check.py`), que la revue manuelle avait manquée. Les fichiers
seulement écrits (sorties) ou créés au runtime (non versionnés) ne déclenchent pas — seule la
combinaison « livré en dev, absent en prod » est fautive.

`pytest` ciblé (guard + sources1 + sources4 + circuit2 + circuit_p4 + exports/sonde) → **200 passed**
(1 `@pytest.mark.local` `test_g7_vert_apres_sonde` rouge **pré-existant** et sans rapport : il mesure
la fraîcheur de la sonde dans la base locale `labuse`, dernier passage 22/10 > 48 h ; déselectionné
par le hook sans base).

---

## P3 — réingestion des espaces naturels protégés (Réserve Marine)

Détail et preuves : `docs/audit-2026-10/postdeploy-1027/RAPPORT-P3.md` (+ `enp_avant.txt`/`enp_apres.txt`).

### Pourquoi la RNMR était « perdue »

La Réserve Naturelle Marine Régionale **n'a jamais quitté la base** : ses 150 secteurs sont en
`spatial_layers (ens/reserve_naturelle)`. Ce qui s'est perdu au 13/09, c'est son **nom**. La migration
amont **Carmen→Lizmap** (vérifiée 13/09) a cessé de servir la RNMR comme **une** entité « Réserve
Naturelle Marine » et la sert désormais en **150 features par secteur** nommés `Nom_zone` = `COT_*` /
`DAR_*`. L'ingestion prenait `Nom_zone` tel quel → **aucun nom ne contenait « marine »**. Le seul `ens`
« marine » en base est un faux-ami (`conservatoire_du_littoral` « Marine De Vincendo »), que le verrou
écarte car il exige `subtype='reserve_naturelle'`. D'où `d_enp_reserve_marine` → quarantaine → service
sous dérogation. **Ni filtre, ni rejet de géométrie marine : seul le nommage.**

### Correctif (ingestion, pas la donnée à la main)

`deal_carmen.py` : la couche RNMR porte `nom_prefixe = "Réserve Naturelle Marine de La Réunion — "`,
appliqué à l'ingestion (chaque secteur → « Réserve Naturelle Marine de La Réunion — COT_Cap_Champagne »).
Rejouable ; aucune ligne éditée à la main.

### Réingestion Mac + avant/après

`labuse ingest-deal-carmen` (live Lizmap) → RNMR 150, filtre **`enp_complements : ok`**
(`bloquants_ko=0`), **sans dérogation**.

| Mesure | Avant | Après |
|---|---|---|
| Total `ens` | 411 | 411 |
| `reserve_naturelle` (150 RNMR + 2 Étang St-Paul) | 152 | 152 |
| Noms `reserve_naturelle` « marine » | 0 | 150 |
| Verrou `d_enp_reserve_marine` bloque ? | oui | **non** |
| Filtre `enp_complements` | quarantaine (dérogation) | **ok** |
| Parcelles intersectant la RNMR | 209 | 209 |

Entités inchangées (simple renommage des 150 secteurs). Parcelles touchées **stables à 209** et faibles
au regard de l'île — la réserve est **en mer**, seules les parcelles du trait de côte ouest (lagon,
Boucan Canot → L'Étang-Salé) chevauchent sa frange terrestre.

### Test (`tests/test_postdeploy_enp_marine.py`)

WFS simulé (sans réseau) : un secteur `COT_*` entré ressort nommé « …Marine… » en `reserve_naturelle`
et le verrou ne bloque plus ; garde statique que la couche RNMR déclare un `nom_prefixe` « marine ».
→ **14 passed** (avec `test_sources1_lot2`).

---

## P4 — mise en prod (EXÉCUTÉE le 27/10/2026, nuit — après merge `e3a30f601`)

`fix/postdeploy-1027` mergée dans `main` (merge `e3a30f601`, P1-P3 `33d3a0e2c`→`eac8ceba2`). P4 relancée
depuis `~/Desktop/labuse-main`, règles DEPLOY-1027 (jamais `deploy.sh`, env `/etc/labuse/labuse.env`
chargé, manifeste jamais écrasé, crontab non touchée, aucun secret affiché). Prod servait déjà
q_v20 / q_v19_sources / division q_v19 / résiduel 17 (DEPLOY-1027) — P4 ne touche NI le scoring NI la
bascule : **code (P1/P2) + réingestion ENP (P3) seulement**.

### Écart de procédure assumé (et pourquoi)

Le plan disait « `enp_complements` envoyée par `deploy_donnees.sh` ». **`deploy_donnees.sh`/`sync-run.sh`
ne transfèrent QUE les tables de run de scoring** (score_labuse, dryrun_*, résiduel…) — jamais
`spatial_layers`/`enp_complements`. Le correctif P3 vit dans l'**ingestion** (`deal_carmen.py`, déployée
en P4.2) ; le chemin sanctionné, idempotent et rejouable — exactement la preuve P3 du Mac — est
**`labuse ingest-deal-carmen`** (live Lizmap avec le `nom_prefixe`). C'est ce qui a été joué. La commande
rejoue elle-même les filtres (`deal_dpf`, `zones_humides`, `enp_complements`) à la fin.

### P4.1 — filet

- Dump frais **vérifié** : `labuse-labuse-20261027-222603.dump` (6,7 G, `pg_restore --list` OK, rc=0,
  `✓ Sauvegarde OK`). ⚠ Leçon : un backup lancé en `nohup … &` sur ssh paraît « tué » quand on teste
  son pid avec `kill -0` depuis `ubuntu` sur un process `labuse` (EPERM = faux négatif) ; et
  `pg_restore --list` passe sur un dump PARTIEL (le TOC custom-format est écrit tôt). **Le dump de
  référence a été repris EN SYNCHRONE** (ssh tient la session) → taille pleine 6,7 G confirmée.
- `cp -al /opt/labuse/app → app-avant-postdeploy`, idem `venv → venv-avant-postdeploy` (liens durs,
  instantané). Snapshots `/root/{served_manifest.json,served_run.txt,cron.labuse,labuse.service,Caddyfile}.avant-postdeploy`.

### P4.2 — code + schéma

`systemctl stop labuse` → `VITE_RUN_LABEL=q_v20 deploy/scripts/deploy_app.sh labuse-vps` :
garde manifeste (q_v20 présent, 433 229) ✓ · rsync · venv (chaîne de démarrage importable ✓) · front
rebuild (**repli VITE_RUN_LABEL=q_v20** préservé — le défaut `q_v7_defisc` du script AURAIT régressé le
bundle, d'où l'override explicite) · unité systemd · contrôle manifeste prod q_v20 ✓. Puis
`labuse doctor` (service arrêté) → **`✓ Schéma : OK`** (P1 : `ensure_schema` crée/surveille
`labuse_zone_famille`/`labuse_hauteur_lidar_m`/`labuse_set_geom_2975`), Healthcheck 14/14, Données OK.
Le `❌ NON PRÊT` résiduel = fiches de démo pré-chauffées (2/8) — préexistant, hors mandat (DEPLOY-1027).
`systemctl start` → **readyz 200**, boot `env=production · auth=active · schéma=ok`. P2 confirmé :
`config/circuit/{reservoirs,moteurs,schemas}.csv + golden_idus.json` DÉPLOYÉS (le rsync envoie `config/`).

### P4.3 — réingestion ENP + levée de la dérogation

`labuse ingest-deal-carmen` (live Lizmap) → **3 741 entités** (identique preuve P3 Mac), dont RNMR 150
secteurs, **`filtre enp_complements : ok`**. Vérifs base prod :

| Mesure | Avant P4 | Après |
|---|---|---|
| `ens` total | 411 | 411 |
| `reserve_naturelle` | 152 | 152 |
| noms `reserve_naturelle` « marine » | **0** | **150** |
| `d_enp_reserve_marine` | ko (quarantaine) | **ok** |
| dernier verdict `enp_complements` | quarantaine · sqm=true | **ok · bloquants_ko=0 · sqm=false** |
| parcelles ∩ RNMR | 209 | 209 |

**Dérogation DEPLOY-1027 levée et tracée** (une transaction) : `UPDATE filtre_versions SET
servir_quand_meme=false` sur les **15** lignes de la version `…(13/09/2026)` (motif d'audit « LEVÉE
POSTDEPLOY-1027 P4 » conservé dans `servi_motif`) + ligne `circuit_journal` (`filtre`/`enp_complements`/
`ok`, `derogation_levee=true`). **`labuse filtre garde` → « aucune source run en quarantaine »** ;
0 ligne `enp_complements` reste sous `servir_quand_meme`. Le cron `filtres-sources` (07:05) repassera
`ok` de lui-même (donnée réparée). Mac déjà réparé en P3.

### P4.4 — fumée (session loopback temporaire pour le compte test admin uid 31, 1 h, purgée)

Cookie frappé côté serveur (`comptes.creer_session`), jamais affiché, fichier 600, **session purgée en
fin** (`DELETE … WHERE utilisateur_id=31`, 1 ligne), aucun artefact laissé en base (pas de bilan de test).

- **P1 — Gabarit 3D** `GET /outils/gabarit/97415000BY0083` → **200** (0,79 s) — le 500 DEPLOY-1027 est
  structurellement réparé.
- **P2 — pieds « Sources » lisibles** : documents générés en 200 avec des **noms publics, aucun id brut** —
  gabarit (« Cadastre (API Carto PCI) · Urbanisme PLU/GPU (API Carto) · BD TOPO IGN · DEAL Réunion — PPR /
  aléas »), dossier, étude-zone (« INSEE Filosofi 2021 · SIRENE · BPE 2025 · DVF · … »). Documents couverts :
  gabarit/dossier/apporteur/étude-zone/comparatif **200** + pré-dossier.zip **200** (35 s) ; financier **422**
  et bilan **422** (sorties gracieuses — entrées/programme requis, NON fabriqués sur la prod). Le rendu
  `exports/pieds.py` lit bien `config/circuit/reservoirs.csv` DÉPLOYÉ (110 noms chargés).
- **P3 — parcelle côtière ouest avec la Réserve marine** : `GET /servitudes-invisibles/97404000AZ0181`
  (L'Étang-Salé) → **200** : « **Espace naturel protégé — Réserve Naturelle Marine de La Réunion —
  COT_Etang_Sale_Bassin_Pirogues : réglementation spécifique (autorisation requise)** », à côté du PPR
  littoral. (Note : la fiche `/parcels/{idu}` ne nomme pas la réserve — l'ENS nommé vit dans les
  servitudes, lues EN DIRECT de `spatial_layers` par `ST_Intersects`, donc **`build-intersections` inutile**.)
- **readyz 200**, service `active`, **0 ERROR/Traceback/CRITICAL/5xx** sur ~1 863 lignes de journal depuis
  le boot (> 10 min, couvrant déploiement + fumée).

### P4.5 — retour arrière (prêt)

Filet en place ; en cas de besoin, depuis le Mac / en ssh :
```bash
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app  && sudo mv /opt/labuse/app-avant-postdeploy  /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-postdeploy /opt/labuse/venv
sudo chown -R labuse:labuse /opt/labuse/app
sudo systemctl start labuse && curl -fsS http://127.0.0.1:8000/readyz
# Données (seule la réingestion ENP a bougé des spatial_layers) : restaurer
#   /var/backups/labuse/labuse-labuse-20261027-222603.dump  UNIQUEMENT si nécessaire.
```
Le code P1-P3 étant VALIDÉ vert, les copies `app-avant-postdeploy`/`venv-avant-postdeploy` peuvent être
supprimées par Vic quand il le souhaite (récupère un peu d'espace ; disque prod à ~88 % — condition
préexistante signalée par DEPLOY-1027, à traiter par `menage_disque.sh`).

**P4 VERTE — les trois suites (P1 fonctions SQL durables · P2 fichiers lus déployés · P3 Réserve Marine
nommée) sont en production, dérogation levée.**
