# DEPLOY-1028 — mise en prod de RECETTE-PROD-1 (main 8fa2e3dc0)

Lancé le 28/10/2026 depuis `~/Desktop/labuse-main`, prod `labuse-vps`.
Périmètre : le merge de `fix/recette-prod-1` — Lot A (fiche parcelle, A1 ×6 + A7 gabarit « Estimé »), Lot B (documents), Lot D (accueil/carte/Sources/Projets/Copilote), Lot F (fiche commune Saint-Paul, seuil 5 + date Radar). **Déploiement code-seul** (aucun run de données, q_v20 reste servi).

Règles (identiques DEPLOY-1027) : jamais `deploy.sh` ni `deploy_donnees.sh` ; env chargé ; manifeste servi jamais écrasé ; crontab en ciblé ; aucun secret affiché ; une phase ne démarre que si la précédente est verte ; retour arrière prêt.

---

## Phase 0 — état des lieux (lecture seule)

### 0.1 Mac
- `git fetch` + `git rev-parse` : HEAD = origin/main = **`8fa2e3dc0`** (« Merge branch 'fix/recette-prod-1' »), 0 ahead / 0 behind. ✓
- Intrus sans effet : `logs/` + `reports/DEPLOY-1027.md` non suivis (le second est le rapport précédent, laissé tel quel).

### 0.2 VPS
- Service `labuse` : **active** (redémarré 28/10 02:50, 5 workers, `--timeout-keep-alive 75`) ; `/readyz` → **200**. ✓
- Disque `/dev/sda1` : 96 G, **78 G utilisés, 19 G libres (81 %)**. ✓ (sain — déploiement code-seul, pas de dump de données, croissance quasi nulle)
- Mémoire : OK.
- Run servi (`/opt/labuse/app/config/served_manifest.json`) : **scoring=q_v20 · cascade=q_v19_sources · mvt=q_v20 · division=q_v19 · residuel_seq=17**, promu le 27/10 (DEPLOY-1027). `served_run.txt` = q_v20. **Doit rester q_v20** — ce déploiement n'y touche pas (aucune bascule).
- Commit du code prod : inconnu (le rsync n'expédie pas `.git`) ; état = déploiement du 27/10 (`f28550160`). Après phase 2 ce sera `8fa2e3dc0`.

### 0.3 Écart de schéma (`labuse doctor` en prod, user labuse, env chargé)
```
✓ Base joignable
✓ Schéma réconcilié (léger)
✓ Schéma : OK
✓ Données (Saint-Paul) : OK
✓ Healthcheck : 14/14
✗ Parcelles de démo conformes   • Cache fiches démo : 2/8 pré-chauffées
• Déclassements AU en attente : 1862 (plus ancienne 89 j, statut ok)
```
**Aucun écart de schéma.** Le seul « NON PRÊT » = pré-chauffage des fiches de démo (2/8) — **préexistant** (déjà signalé DEPLOY-1027 §Phase 7-5), hors mandat. Le merge RECETTE-PROD-1 **n'ajoute ni table ni colonne** : diff = frontend + `api/app.py`, `api/fiche_commune.py`, `exports/robinet_fiche.py`, `faisabilite/zonage.py`, `gabarit/{builder,contract,engine}.py`, `config/veille_plu.yaml`, `.gitignore`. Pas de migration en phase 2.

### 0.4 Dépendances runtime vérifiées présentes (survivent au rsync)
- `deploy_app.sh` exclut `/docs` du rsync **et** `--delete` ne touche pas les chemins exclus → les CSV lus au runtime reposés en DEPLOY-1027 **persistent** : `docs/CIRCUIT/inventaire/*.csv` (9 fichiers, pieds PDF) + `docs/audit-2026-09/SOURCES/SCHEMAS.csv` (160 K, `circuit_garanties`) — **présents** ✓.
- Fonctions SQL `labuse_hauteur_lidar_m` + `labuse_zone_famille` (gabarit A7 / résiduel) — **présentes** ✓ (créées manuellement DEPLOY-1027, non droppées).

### 0.5 Go / no-go
**GO.** Déploiement code-seul à faible risque : pas de schéma, pas de données, pas de bascule, disque sain. Phases qui touchent la prod :
- Phase 1 : dump filet + `cp -al` app → `app-avant-1028`.
- Phase 2 : rsync `/opt/labuse/app` + venv + front + unité systemd + `doctor`. Aucun DROP, manifeste exclu.
- Phase 3 : recompute `commune_contexte_cache` (24 communes) + réchauffe gabarit A7. Caches uniquement.
- Phase 4 : session temporaire gb-test-ae (serveur), mesures lecture seule, purge.
- Phase 5 : fumée lecture seule.

### 0.6 ⚠ Incident secret (consigné)
Un contrôle psql de la phase 0 a — par erreur — passé `$LABUSE_DATABASE_URL` (URL SQLAlchemy avec mot de passe) à `psql`, qui l'a réaffiché dans son message d'erreur. **Le mot de passe du rôle `labuse` a été exposé dans le journal de session.** Correctif immédiat : tous les contrôles SQL suivants passent par `sudo -u postgres psql -d labuse` (auth peer, zéro mot de passe en ligne de commande). **Recommandation à Vic : faire tourner (rotate) le mot de passe DB `labuse`** (`/etc/labuse/labuse.env` + `ALTER ROLE labuse PASSWORD …` + restart) à la première occasion.

### 0.7 Observation — un déploiement DONNEES-ETAT-FIX-1 a eu lieu cette nuit
Snapshot prod `app-avant-etatfix-20261028-0249` + restart service 02:50 + dump 02:48 = une intervention nocturne a posé **DONNEES-ETAT-FIX-1**, qui **est déjà dans main `8fa2e3dc0`** (merge `b10ed1281`). Aucune divergence : `deploy_app.sh` amène la prod déterministe à `8fa2e3dc0` (superset). Pas de risque de régression.

---

## Phase 1 — filet de sécurité

### Sauvegarde
- `deploy/scripts/backup_postgres.sh` (nohup, env `/etc/labuse/labuse.env` chargé, user labuse, journal `/tmp/backup_phase1_1028.log`) → **`labuse-labuse-20261028-031157.dump` (6,7 G)**.
- **Contrôle d'intégrité intégré** (script l.81 : `pg_restore --list` — échec ⇒ dump supprimé + sortie bruyante) : **passé** (« ✓ Sauvegarde OK (6.7G) », dump conservé). ✓
- Rotation : le script a gardé **4** dumps (pas 2) car `labuse.env` pose `LABUSE_BACKUP_KEEP=7` (lancé à la main, le script lit cet env ; le cron `backup-postgres` ramène à 2 via `BACKUP_ROTATION_N`). **À signaler à Vic** : `LABUSE_BACKUP_KEEP=7` dans `labuse.env` contredit l'intention DONNEES-ETAT-FIX-1 (2 quotidiens) — sans effet sur ce déploiement.

### Copies (instantanées, hardlinks `cp -al` → ~0 octet)
- Code : `/opt/labuse/app` → **`/opt/labuse/app-avant-1028`**.
- venv : `/opt/labuse/venv` → **`/opt/labuse/venv-avant-1028`** (insurance ; code-seul ⇒ venv quasi inchangé).
- Config (référence) : `/etc/caddy/Caddyfile` → `/root/Caddyfile.avant-1028` ; `/etc/cron.d/labuse` → `/root/cron.labuse.avant-1028` ; `served_manifest.json` → `/root/served_manifest.json.avant-1028`.

### Disque
Après dump : **84 G utilisés / 12 G libres (88 %)** — ample pour un déploiement code-seul (rsync direct en place, pas de transit /tmp de données, croissance nette ≈ 0).

### Phase R — commandes exactes de retour arrière
```bash
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app && sudo mv /opt/labuse/app-avant-1028 /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-1028 /opt/labuse/venv
sudo chown -R labuse:labuse /opt/labuse/app
sudo systemctl start labuse && curl -fsS http://127.0.0.1:8000/readyz
# Code-seul : manifeste/config/caddy NON touchés par ce déploiement → rien à restaurer côté config.
# DB : restaurer labuse-labuse-20261028-031157.dump UNIQUEMENT si l'ancien code ne fonctionne plus.
```

**Verdict phase 1 : VERT.**

---

## Phase 2 — code

1. `sudo systemctl stop labuse` → inactive, readyz injoignable (attendu).
2. `deploy/scripts/deploy_app.sh labuse-vps` (depuis le Mac) :
   - **garde manifeste** : run local `q_v20` présent en prod (433 229 lignes score_labuse) ✓ ;
   - rsync direct `/opt/labuse/app` (exclusions d'usage : `.git`, `docs/`, manifeste/served_run, sources d'ingestion — donc les CSV runtime de `docs/` **survivent**) ;
   - venv = `requirements.lock` + `-e . --no-deps`, **chaîne de démarrage importable ✓** ;
   - front construit sur le VPS ;
   - unité systemd installée (`deploy/systemd/labuse.service`) + `daemon-reload` ;
   - contrôle manifeste prod après envoi : `q_v20` (433 229 lignes) ✓.
3. **Front reconstruit avec le bon repli `VITE_RUN_LABEL=q_v20`** (lu de `served_run.txt` ; le script défaut à `q_v7_defisc`, comme en DEPLOY-1027). dist fraîche (03:35), label baké = **q_v20** (grep du bundle : une seule occurrence, q_v20).
4. `labuse doctor` (service arrêté, env chargé) : **Base joignable ✓ · Schéma réconcilié ✓ · Schéma OK ✓ · Données Saint-Paul OK ✓ · Healthcheck 14/14 ✓**. Schéma identique avant/après = confirme le déploiement code-seul (aucune migration). Seul « NON PRÊT » = pré-chauffage fiches de démo 2/8 (préexistant, hors mandat).
5. `sudo systemctl start labuse` → **readyz 200** (après ~4 s), boot « **env=production · auth=active · schéma=ok** », `Application startup complete`.
6. Manifeste servi **inchangé** (exclu du rsync) : toujours q_v20. ✓

**Phase 2 VERTE.**

---

## Phase 3 — caches

### 3.1 Recalcul du cache des fiches communes
- Job `fiche-commune-cache` (`labuse jobs run`, verrou+journal, détaché nohup/setsid, user labuse, env chargé) : **24/24 communes OK, 0 échec**, durée **785 s** (~13 min), statut `ok`, journal `/var/log/labuse/jobs/fiche-commune-cache.log` → « fin (code 0) ». (Le job lit DISTINCT commune de `parcels` = 24 communes, écrit `commune_contexte_cache`.)
- **Vérif Saint-Paul (97415)** — payload recalculé (computed_at 28/10 03:47) :

| Clé servie | Valeur |
|---|---|
| `seuil_n` / `demande_seuil_n` | **5** (seuil unique, plus de 5/30) ✓ |
| `prix_demande_median_eur_m2` | **4 784 €/m²** (médiane du demandé) ✓ |
| `prix_demande_n` | 24 (≥ 5) ; `demande_sous_seuil` = false → médiane **servie** ✓ |
| `ecart_demande_acte_pct` | 12,1 % ; `prix_acte_eur_m2` 4 267 |
| `derniere_collecte` | **2026-10-06** → « Radar — dernier relevé le 06/10/2026 » ✓ (pige en pause depuis ~06/10) |

(La valeur locale RECETTE-PROD-1 était 4 657 €/m², n=42 : la prod sert **ses propres** annonces Radar — n=24 — ce qui est attendu, la prod fait foi sur sa pige.)

### 3.2 Caches du gabarit A7
Le gabarit est **servi en direct** (`/outils/gabarit/{idu}`) — **aucun cache persistant** (ni table, ni `commune_contexte_cache` pour le gabarit). Le seul cache concerné est le `_FICHE_CACHE` **en mémoire du worker** (OrderedDict, max 128, VITESSE-PROD-1), **vidé par le restart de la phase 2** → froid, recalculé avec le nouveau code. Donc « purge » sans objet ; « réchauffage » = premiers hits sur Saint-Benoît / La Possession / Saint-Denis, effectués en phase 4 (avec session) pour obtenir les mesures froid→chaud.

**Phase 3 VERTE.**

---

## Phase 4 — vitesse en prod (lot C)

**Session.** Compte `gb-test-ae@labuse.local` = **id 31, role admin, actif** (quota-exempt). Session serveur **temporaire 3 h** frappée via `comptes.creer_session(db, 31, 3)` ; le jeton n'est **jamais affiché** — écrit dans un curlrc `600` (`/tmp/.gb1028.curlrc`, labuse) lu par `curl -K`. Vérifié : `/version` **200** avec cookie / **401** sans (1 seule session active uid 31 → purge propre). ⚠ **Interprétation du périmètre** : la phase 5 (fumée) exige aussi l'auth ; comme en DEPLOY-1027 (session unique pour toute la fumée), **cette session couvre les phases 4 ET 5** et est **purgée en fin de phase 5** (confirmée au §Phase 5). Je le signale explicitement puisque le mandat dit « purgée en fin de phase » pour la phase 4.

### C1 — matrice de latence (via Caddy `https://app.labuse.immo`, `time_total`)
cold = 1ᵉʳ hit · chaud = meilleur de 5 relances (5 workers uvicorn, `_FICHE_CACHE` par worker). **Tous 200.**

| Mesure | témoin | froid | chaud |
|---|---|---|---|
| Fiche parcelle `/parcels/{idu}` | AE1369 (St-Benoît) | 4,07 s | **0,096 s** |
| | BY0083 (St-Paul) | 3,60 s | **0,088 s** |
| | BZ1065 (St-Denis) | 3,33 s | **0,083 s** |
| Fiche commune / clic carte `/communes/{c}/contexte` | Saint-Benoît | **5,62 s** | 0,074 s |
| | Saint-Paul | 0,109 s | 0,069 s |
| | Saint-Denis | 0,073 s | 0,073 s |
| Gabarit 3D `/outils/gabarit/{idu}` | AE1369 / BY0083 / BZ1065 | 0,30 / 0,32 / 0,27 s | ~0,20 s |
| Étude de faisabilité `/modules/faisabilite/{idu}` | AE1369 / BY0083 / BZ1065 | 0,55 / 0,65 / 0,91 s | 0,37–0,64 s |
| Comparatif `/compare` (3 témoins) | — | 7,29 s | 7,09 s |
| Taxe d'aménagement `/outils/taxe-amenagement/prefill` | AE1369 | 0,091 s | 0,081 s |

(Réchauffage gabarit A7 des 3 communes effectué par ces hits — phase 3.2.)

### C2 / C3 — le clic commune / la fiche commune répondent-ils vite ? **OUI**, avec un bémol diagnostiqué
- **Oui** : cache recalculé, la fiche commune / le clic répondent en **0,07–0,11 s** une fois les workers chauds (Saint-Paul et Saint-Denis même à froid < 0,11 s).
- **Bémol (cause trouvée, lecture seule)** : le **tout premier** appel contexte a payé **5,62 s**. Cause racine : `GET /communes/{c}/contexte` **ne se contente pas de lire le cache DB** — à chaque appel, `_rafraichir_partages` recalcule **en direct** les indicateurs partagés avec le comparateur (`fiche_commune.comparable` → `comparateur.raw_rows`, les 24 communes : ancien/neuf/permis/vélocité/stock/terrain-nu). `raw_rows` est **mémoïsé par worker, TTL 1 h** (`_mem_cached(("o6-raw",), 3600)` ; `_MEM_CACHE` = global de module = **par process**). Donc le 1ᵉʳ appel d'un worker froid (ou après expiration du TTL 1 h) reconstruit tout (~5 s) ; les suivants sur ce worker = 0,07 s.
- **Conséquence** : avec 5 workers × TTL 1 h, un clic commune peut tomber sur un worker froid et payer ~5 s **plusieurs fois par jour** (chaque worker se réchauffe indépendamment toutes les heures). Le job nocturne `fiche-commune-cache` réchauffe le **cache DB** `commune_contexte_cache`, **pas** ce mémo in-process → d'où le résiduel « lent / ne fait rien » au premier clic. **C'est exactement le symptôme C2.** (Le job de phase 3 restait nécessaire : sans lui, `cle_fraicheur` ne matcherait pas et le contexte se recalculerait ~20 s en direct à chaque première lecture — maintenant évité ; ne reste que les ~5 s de `raw_rows`.)
- **Correctif (mandat suivant, PAS ici)** : réchauffer `raw_rows` au démarrage de chaque worker (événement startup FastAPI) et/ou après déploiement (hit `/communes/.../contexte` ≥ nb workers), et/ou partager/allonger le mémo, et/ou sortir le comparateur live du chemin chaud du contexte. Fiche parcelle à froid 3–4 s = coût normal de calcul complet (pas de cache persistant ; `_FICHE_CACHE` en mémoire vidé au restart) → chaud < 0,1 s, conforme à DEPLOY-1027 (6,3 s pendant les rebuilds à l'époque).

### C3 bis — le job de recalcul tourne-t-il après déploiement et chaque nuit ?
- **Chaque nuit : OUI** — crontab prod `0 3 * * *` (Réunion) `labuse jobs run fiche-commune-cache` ; au registre (`jobs list`), dernier run `ok` 28/10 03:50.
- **Après déploiement : NON automatisé** — `deploy_app.sh` ne lance pas le job (grep 0). C'est un **geste de déploiement manuel** (fait en phase 3 ici). **À signaler à Vic** : soit câbler un hook post-déploiement, soit garder l'étape documentée dans le mandat DEPLOY. (Et noter que, même recalculé, le mémo `raw_rows` par-worker reste à réchauffer — cf. C2.)

**Phase 4 VERTE** (session maintenue pour la phase 5).

---

## Phase 5 — test de fumée en prod (https://app.labuse.immo)

Même session gb-test-ae que la phase 4 (voir §Phase 4). **Purge confirmée en fin de phase ci-dessous.**

### 5.1 AE1369 (Saint-Benoît Ub) — gabarit « Estimé », aucune des 6 contradictions A1
- **Gabarit `/outils/gabarit/97410000AE1369` (JSON écran)** : `status=ok`, `plafondEmpriseM2=763,2` (status `integrated`, CES 80 %), `hauteurReglementaireM=9,0` à l'égout (`integrated`), **`hauteurEstimee=true`** (`raccordement.hauteur_egout.estimee=true`). Plus aucun « PLU non calibré / Calcul incomplet ». ✓
- **Gabarit PDF** (200) : « Plafond d'emprise **763 m²** sourcé », « Hauteur réglementaire **9 m à l'égout · Estimé (table graphique par secteur)** sourcé » — étiquette « Estimé » à l'écran ET au PDF. ✓
- **6 contradictions A1** : ce sont des correctifs de **rendu front** (Fiche.tsx…), désormais **déployés** (dist construit de main `8fa2e3dc0`), nourris par la **donnée backend correcte** servie pour AE1369 : `reglement_plu.zone_famille=U` (⇒ pas de note zones A/N — A1 #3), `le_bien.nb_batiments=0` + `emprise_batie_m2=0` (⇒ lecture unique « terrain nu » partout — A1 #1/#2, pas de « bâti conservé » / « SDP consommée »). La fiche parcelle n'étant pas un PDF, la vérification est faite au niveau de la donnée servie + du bundle déployé (pas de capture SPA — voir note 5.4).

### 5.2 BY0083 (Saint-Paul) — documents & cohérence
- **`docs_coherence.py` contre `https://app.labuse.immo`** (copie patchée : en-tête Cookie de la session lu du curlrc **au runtime**, jamais embarqué ni affiché ; Bilan en-process) : **0 écart sur 18 données partagées** ✓ — les 8 documents génèrent ET s'accordent (surface 2 458, emprise bâtie 900, zone libérée 1 736, hauteur 9/6, recul 4, stationnement 2 pl/logt, pleine terre 40 %, prix bâti 4 125, prix terrain 250, VEFA 4 745, SDP max 1 327, date 27/10/2026…).
- **Les 8 documents en 200** (temps via Caddy) : Dossier 8,2 s · Apporteur 2,0 s · Étude de zone 14,9 s · Gabarit 2,1 s · Comparatif 9,4 s · Pré-dossier PC (zip) 33,7 s · Bilan (doc_id 6) 2,0 s · **Étude de faisabilité (POST `/modules/etude/pdf`, 24 T1 aérien) 200 en 29,6 s — < 75 s ✓**.
- **Bilan 422 à vide** : export du Bilan sans chiffre d'affaires (doc_id 5, `produits: []`) → **422** « Export indisponible : aucun chiffre d'affaires. » ✓ (garde serveur `_refuser_si_ca_nul`).

### 5.3 Fiche commune Saint-Paul — menu « Toute l'île » ET carte
Les deux entrées UI (menu `Header` « Toute l'île » et clic commune sur la carte) posent `contexteCommune` → **le même** `GET /communes/Saint-Paul/contexte` — vérifié **200**, payload complet (Lot F : `seuil_n=5`, médiane demandé 4 784 €/m², `derniere_collecte=2026-10-06`). ✓

### 5.4 Copilote / Sources / Projets / panneau Cartes (Lot D)
Correctifs **front** (code-seul) ; vérifiés dans le **bundle déployé** (`dist` construit de main `8fa2e3dc0`), sans capture SPA (l'auth prod aurait exigé d'injecter le jeton côté navigateur — écarté par prudence, comme DEPLOY-1027 qui validait par endpoints/PDF) :
- **D7 Copilote** : 10ᵉ exemple « …taxe d'aménagement de 97415000BY0083 » **présent** dans le bundle ✓.
- **D6 Projets** : phrase « Chaque projet garde votre cadrage… » **absente** ✓.
- **D5 Sources** : phrase « sentinelle » / « La plupart de nos sources… » **absente** ✓.
- **D4 menu communes** : `communePastille` présent (Avirons/Étang-Salé sans article) ✓.

### 5.5 Journaux
Service `labuse` depuis le restart phase 2 (03:36) → **0 ERROR / Traceback / CRITICAL / Exception, 0 HTTP 5xx** sur ~34 min (fumée complète ; journalisation active = 4 559 lignes depuis 04:00, lignes d'accès présentes). readyz 200. Bien au-delà des 10 min demandées. ✓

### Purge de la session (confirmée)
`DELETE FROM sessions_auth WHERE utilisateur_id=31` → **DELETE 1**, **0 session active restante** pour uid 31 ; curlrc `/tmp/.gb1028.curlrc` + `/tmp/dc_patched.py` **supprimés** (ls → No such file). Aucun artefact client créé par ce mandat : doc_id 5/6 réutilisés = **restes DEPLOY-1027** (à purger avec les autres `[GB-TEST]`, inchangés).

**Phase 5 VERTE — déploiement validé.**

---

## Phase 6 — après
- Fumée verte → `/opt/labuse/app-avant-1028` et `/opt/labuse/venv-avant-1028` **supprimés** ; temp VPS (`/tmp/fcc_1028.out`) supprimé. Refs config `/root/*.avant-1028` conservées (quelques Ko, référence — non utilisées car config non touchée).
- Scripts temp locaux (`reports/.deploy1028-*`) supprimés. readyz **200**, disque 88 % / 12 G.
- Ce rapport commité et poussé.
- **Hook pre-push** : 2 669 passed, **2 failed** (`test_geom_2975::test_cascade_lit_ppr_assiette_flag_prudent`, `test_sar::test_cascade_sar_proxy_informatif…`). **Prouvés PRÉ-EXISTANTS et SANS RAPPORT** : (a) ce commit ne touche QU'`reports/DEPLOY-1028.md` (1 fichier, markdown — ne peut pas faire échouer un test Python) ; (b) les deux fichiers de test sont INCHANGÉS sur le parent `8fa2e3dc0` (déjà sur origin/main, déjà passé la CI au merge) ; (c) cause = **données absentes de la base Mac locale** (PPR/aléas → « Aléas non couverts par la source », SAR → « hors îlot cartographié »), même symptôme que les tests Saint-Paul `SKIPPED` « base applicative indisponible ». Aucun rapport avec le code déployé (RECETTE-PROD-1 ne touche ni cascade ni SAR) ; la fumée prod est à 0 erreur. Push fait avec `--no-verify` (cas explicitement prévu par le hook : « rouge connu/sans rapport, la CI GitHub re-vérifie »). **À signaler à Vic** : banc local Mac à re-semer (PPR/SAR) pour que ces 2 gardes passent localement.

---

## Synthèse

**Déployé et validé** : main **`8fa2e3dc0`** en prod — RECETTE-PROD-1 (Lot A fiche parcelle + **A7 gabarit « Estimé »**, Lot B documents, Lot D accueil/carte/Sources/Projets/Copilote, Lot F fiche commune seuil 5 + date Radar). **Déploiement code-seul** : aucun run de données, aucune bascule, aucune migration de schéma — la prod sert toujours **q_v20 / q_v19_sources / mvt q_v20 / division q_v19 / résiduel 17** (manifeste intact). Cache des 24 fiches communes recalculé (24/24 ok). Toutes les phases VERTES.

**Décisions prises en séance (dans le périmètre du mandat)** :
- Session unique gb-test-ae pour les phases 4 **et** 5 (la fumée exige l'auth), purgée en fin de phase 5 — comme DEPLOY-1027 ; signalé au §Phase 4.
- Bilan « 422 à vide » testé en **réutilisant** le doc_id 5 existant (reste DEPLOY-1027, `produits: []`) → aucun nouvel artefact client créé.

**À faire ensuite (hors mandat, par priorité)** :
1. **Secret DB à faire tourner** : le mot de passe du rôle `labuse` a été exposé dans un message d'erreur psql en phase 0 (URL SQLAlchemy passée à `psql`). Rotation recommandée (`labuse.env` + `ALTER ROLE labuse PASSWORD …` + restart). Cf. §0.6.
2. **Correctif C2 (clic commune « lent » résiduel)** : `/communes/{c}/contexte` recalcule le comparateur `raw_rows` **en direct**, mémoïsé **par worker, TTL 1 h** — non réchauffé par le job nocturne. 1ᵉʳ clic d'un worker froid ≈ 5 s, plusieurs fois/jour (5 workers). Réchauffer `raw_rows` au démarrage worker (startup FastAPI) et/ou après déploiement, et/ou partager/allonger le mémo. Cf. §Phase 4 C2.
3. **Job cache post-déploiement non automatisé** : `fiche-commune-cache` tourne chaque nuit (crontab 03:00) mais `deploy_app.sh` ne le relance pas après un déploiement → geste manuel (fait ici en phase 3). Câbler un hook post-déploiement **ou** garder l'étape documentée au mandat DEPLOY.
4. **`LABUSE_BACKUP_KEEP=7`** dans `labuse.env` contredit l'intention DONNEES-ETAT-FIX-1 (2 quotidiens) — le cron ramène à 2 via `BACKUP_ROTATION_N`, mais un lancement manuel garde 7 (disque). À aligner.
5. **Préexistants** (déjà DEPLOY-1027) : fiches de démo 2/8 pré-chauffées (`labuse rebuild-demo --commune 97415` + `labuse warm-demo`) ; purge des `[GB-TEST]` dont **doc_id 5 et 6** ; disque VPS 88 % (runs morts en base, `menage_disque.sh` en heure creuse). `docs/CIRCUIT/inventaire/*.csv` + `SCHEMAS.csv` lus au runtime mais hors rsync (POSTDEPLOY-1027 les sort de `docs/` — non mergé).

