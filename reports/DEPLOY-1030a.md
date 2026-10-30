# DEPLOY-1030a — mise en prod de `main` (`153c95032`) : CHASSE-4-FIX + BANC-RAYON-1 + ETUDE-ASYNC-1 + RADAR-COUVERTURE-1 + VEILLE-3 + RECETTE-4

Lancé le 30/10/2026 depuis `~/Desktop/labuse-main`, prod `labuse-vps` (`https://app.labuse.immo`).
Périmètre : faire avancer la prod de `b955de8e5` (DEPLOY-1029b) à **`153c95032`** (« Merge branch
'fix/recette-4' »), soit le delta **CHASSE-4-FIX + RADAR-COUVERTURE-1 + BANC-RAYON-1 + ETUDE-ASYNC-1 +
VEILLE-3 + RECETTE-4** (24 commits). **Déploiement CODE-SEUL** : aucune colonne, aucune table, aucune
donnée, aucune bascule de manifeste, aucun mail, radar-cloche/digest gelés. Mêmes règles que
`reports/DEPLOY-1029b.md`.

> ⚠ **DÉPLOIEMENT HORS FENÊTRE DE NUIT — go explicite de Vic.** Joué **21 h 24 → 21 h 44 Réunion** (soir).
> Le risque ne s'est pas matérialisé : **aucune session client active** au moment du restart (seule session
> ouverte = **la session admin de Vic lui-même**, uid 19). Le nouvel ordre `deploy_app.sh` (restart →
> readyz 25/25 stable → réchauffage) a tenu : **0 × 503 servi au restart**, `NRestarts=0`.

---

## Étape 0 — garde-fou (heure Réunion, VACUUM, sessions)

- **21 h 24 Réunion** (`TZ=Indian/Reunion`, VPS `vps-5563949c`). Déploiement de soirée **assumé sur go de
  Vic** (aucun client actif).
- **Aucun VACUUM / autovacuum** en cours (`pg_stat_activity` : 0 requête `%vacuum%`, 0 `autovacuum worker`).
- **Aucune session client** : une seule session active = **la session admin de Vic** (uid 19,
  `kampusreunion@gmail.com`). 0 session client, 0 session de test résiduelle.
- Disque : **34 G libres / 66 %**. readyz local 200, service `labuse`/`caddy` actifs.

---

## Pré-vol

- **Cible strictement en avance, sans divergence** : `b955de8e5` est **ancêtre** de `153c95032`
  (`git merge-base --is-ancestor` = vrai, **24 commits**). `153c95032` **== origin/main** (ancêtres mutuels).
- **Prod réelle avant** : `/opt/labuse/app/config/deploiement.json` = `b955de8e5188ffad…`, `par=deploy_app.sh`,
  déployé 2026-10-29T12:43:13Z — conforme à l'attendu (DEPLOY-1029b). *(Le `config/deploiement.json` LOCAL
  reste un baseline écrasé par le script ; la vérité est lue sur le VPS.)*
- **Manifeste servi** : `scoring=q_v20` — **resté intact** (manifeste + `served_run.txt` exclus du rsync,
  re-vérifié après déploiement : q_v20, 433 229 lignes `score_labuse`).
- **Notifications Radar gelées** : `radar-cloche`/`digest` restent commentés « GELÉ (LABUSE_RADAR_NOTIFS=off) »
  dans le crontab (reposé == registre à l'étape 4b) ; défaut code OFF → **aucun mail possible**.

### Schéma — AUCUNE colonne ni table nouvelle (déploiement code-seul)
- `git diff b955de8e5..HEAD` ne contient **aucun DDL** (0 `ADD COLUMN` / `CREATE TABLE` / `.sql` ;
  les seules occurrences sont le **texte du rapport DEPLOY-1029b** désormais dans l'arbre).
- Les deux points signalés au mandat sont du **code pur, sur colonnes existantes** :
  - **Veille modifiable** (VEILLE-3) : `veille.modifier` fait un `UPDATE veilles SET criteria, commune …`
    sur des colonnes **déjà servies** par `creer`/`lister` ; `existe_identique(sauf_id=…)` exclut l'alerte
    éditée. Rien de neuf en base.
  - **Référence de courrier** (RECETTE-4 Lot 7) : le format `C-DDMM-XX` est une **chaîne calculée**
    (`courrier.py:_reference`) écrite dans la colonne `courrier_opposition.reference` **préexistante**.
- Conclusion : **rien à poser avant le restart** (contrairement à `pige_passes.n_non_verifiees` de 1029b).

### Sauvegarde vérifiée (`pg_restore --list`)
- **Pas de nouvelle sauvegarde prise** : déploiement **code-seul, sans aucune mutation de données ni
  restauration** — le rollback est un simple échange de répertoires (Phase R). La **dernière sauvegarde
  pleine** (`labuse-labuse-20261029-161844.dump`, 6,1 G, < 24 h) a été **vérifiée restaurable** :
  `pg_restore --list` = **1748 entrées TOC**, dont `TABLE DATA public` pour `score_labuse` (433 229),
  `pige_biens`, `veilles` et `courrier_opposition`. ✓ (conservée telle quelle, c'est « le dernier dump »
  gardé au ménage).

### Filet (`cp -al`, hardlinks ≈ 0 octet)
- Code : `/opt/labuse/app` → **`/opt/labuse/app-avant-1030a`** (inode partagé vérifié : 4525182).
- venv : `/opt/labuse/venv` → **`/opt/labuse/venv-avant-1030a`**.
- Caddy : `/etc/caddy/Caddyfile` → **`/etc/caddy/Caddyfile.avant-1030a`** (snapshot seul — **Caddy non
  touché** ce déploiement, cf. ci-dessous).

### `rsync --delete` — innocuité vérifiée sur les 7 Go de `app/data`
- `/opt/labuse/app/data` pèse désormais **7,0 G** (ingestion `cosia` 3,4 G, `ortho_irc` 1,9 G, etc.,
  peuplée **après** 1029b). Chaque sous-dossier prod de `data/` est soit **dans la liste d'exclusions
  ancrées** de `deploy_app.sh` (`/data/cosia`, `/data/ortho_irc`, `/data/plu_reglements`, …), soit
  **présent dans le dépôt local** (`anc`, `entites`, `fiscal`, `cerfa`, les `.json`). `outputs/` (427 M)
  est exclu. → **aucun sous-dossier de données n'est supprimé** par le `--delete`.
- `logs/` local (non suivi, 2 vieux logs de scoring) **mis de côté** avant le rsync (il n'est **pas** dans
  les exclusions ; la prod n'a pas de `app/logs`), restauré après.

### Caddy — NON touché
- Le delta **ne modifie pas** `deploy/Caddyfile.prod`. La marge `read_timeout 90 s` (CORRECTIFS-2) est déjà
  en prod depuis 1029b. **Config LIVE confirmée** : `read_timeout = 90000000000 ns`. Aucun `reload`.

### Phase R — retour arrière (prêt, conservé)
```bash
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app  && sudo mv /opt/labuse/app-avant-1030a  /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-1030a /opt/labuse/venv
sudo chown -R labuse:labuse /opt/labuse/app
sudo systemctl start labuse && curl -fsS http://127.0.0.1:8000/readyz
# Caddy inchangé ce déploiement (filet Caddyfile.avant-1030a conservé par sécurité).
# DB : aucune mutation → restaurer labuse-labuse-20261029-161844.dump UNIQUEMENT en dernier recours.
```

---

## Déploiement — `VITE_RUN_LABEL=q_v20 deploy/scripts/deploy_app.sh labuse-vps`

Arbre local propre sur la cible (`logs/` mis de côté). Déroulé **exit 0**, ordre REMISE-1 :

```
── garde manifeste : run local 'q_v20' présent en prod (433229 lignes score_labuse) ✓
── 1. rsync (manifeste/données/docs/qa/tests/outputs exclus)   ── 2. venv + chaîne de démarrage importable ✓
── 3. front (vite build --base=/, q_v20)                       ── 4. systemd
── 4b. crontab reposé + vérifié : ✓ == registre (aucun écart, tz=reunion)   ← radar mail restent gelés
── 4c. deploiement.json = 153c95032936 (déployé 2026-10-30T17:29:22Z)
── 5. manifeste prod : 'q_v20' (433229 lignes) ✓
── 6. fiche_cache vidé (DELETE 38, invalidation déploiement — ATTENDU)
      restart → /readyz 200 STABLE (25/25 consécutifs, 37 essais) ✓ → job fiche-commune-cache (détaché)
✓ déployé — service redémarré, /readyz 200 stable, caches en réchauffage.
```

- **SHA prod déployé = `153c95032936d80840…`** (la cible), `deploiement.json` écrit en conséquence.
- **Manifeste INCHANGÉ** : `served_run` = **q_v20** (433 229 lignes, exclu du rsync).
- **Crontab** reposé depuis le registre et **vérifié == registre** (radar-cloche/digest restent gelés).
- **Aucun 503 servi au démarrage** : les « 37 essais pour 25 consécutifs » = le trou de connexion pendant
  le reboot des workers (connection-refused), **pas** des 503 HTTP. `NRestarts=0`.
- **`fiche_cache` vidé** (DELETE 38) — **attendu** ; le réchauffage le ré-amorce.
- **Caddy non redémarré** : public `/readyz` = **200 ×5**, `read_timeout 90 s` toujours en config LIVE.

---

## Fumée — méthode 1028b (session de test éphémère, jeton jamais affiché)

Compte `gb-test-ae@labuse.local` = **uid 31, admin**. Session 3 h via `comptes.creer_session(db, 31, 3)` ;
cookie `labuse_session=u.<token>` écrit **par le script Python lui-même** dans un curlrc 600
(`/tmp/.gb1030a.curlrc`, labuse), lu par `curl -K`, **jamais imprimé**. Vérifié : `/version` **401 sans
cookie / 200 avec**. **Session purgée en fin de run** (`DELETE … uid 31` → 1 supprimée ; ne reste active
que la session de Vic uid 19). **Les 7 points de fumée sont VERTS.**

### 1. readyz 25/25 + fiche BY0083 ✓
- `/readyz` : **25/25 = 200**.
- `GET /parcels/97415000BY0083` → **200, 0,022 s**, 78 clés, Saint-Paul, **`etat_bien = "bati_encore"`**,
  aucune clé d'erreur.

### 2. Étude d'assemblage de 4 parcelles à froid, pendant fiche / carte / Estimer un bien ✓ (ETUDE-ASYNC-1)
- Assiette **4 parcelles contiguës** (Les Avirons `AE0155`+`AE0129`+`AE0153`+`AE0131`) → `POST
  /modules/etude/pdf` **à froid** → **HTTP 200, 32,9 s, PDF 111 Ko** (version 1.7).
- **Pendant** les 32,9 s de calcul, 12 rafales de `fiche` / `carte` (`/map/tuyau/couches`) / `Estimer un
  bien` (`/radar/annonce/estimation/…`) : **toutes 200**, et **rapides** — fiche 12–40 ms, carte 9–940 ms,
  estimation 23–111 ms. **L'API n'est jamais affamée** : le calcul tourne dans le processus enfant « spawn »,
  l'endpoint synchrone attend sur `queue.get` (GIL relâché) et le pool de threads sert les autres requêtes.
- **Le processus enfant disparaît après l'étude** : **6 processus `spawn_main` pendant** (5 workers uvicorn
  persistants `--workers 5` + **1 enfant étude**) → **5 après** (les 5 workers seuls, `ppid` = master
  uvicorn 1940378). *(Nuance méthodo : `pgrep -f spawn_main` lancé en one-liner s'auto-compte — la ligne de
  commande contient « spawn_main » ; le vrai compte au repos est bien 5 workers.)*

### 3. Estimer un bien BZ1065 (`97411000BZ1065`) + copropriété BV2257 ✓
- **BZ1065 (maison)** : `type_bien=maison`, **fiabilité « Limitée » / `precision_pct=28` (±28 %)**
  (BANC-RAYON-1 : `_ECART_SEGMENT{maison:28}`), **`n_aleas=2`** (2 aléas, CHASSE-4-FIX C4-002 : compte
  dédupliqué `_risques_rows`), **valeur indicative 735 000 €** (ordre de grandeur bâti).
  - **Tuile « Dernière vente »** (RECETTE-4 Lot 6, remplace « Classement LABUSE ») : BZ1065 **n'a aucune
    mutation DVF** → la tuile affiche **« aucune depuis 2014 »** (état légitime ; la tuile est bien câblée,
    `AnalyserAnnonce.tsx` lit `dvf_parcelle.derniere_mutation`).
  - **écran = PDF** : `/analyse-annonce/97411000BZ1065.pdf` = **200, 126 Ko** (même point de calcul que
    l'écran, `estimation_annonce` unique).
- **Copropriété BV2257 (`97422000BV2257`)** : `nature=copropriete`, comparateur **appartements**,
  **`valeur_indicative = None` → PAS d'ordre de grandeur** (CHASSE-4-FIX C4-003 : drapeau `score_v2.copro`),
  la **lecture foncière reste** présente. ✓

### 4. En-tête « Fiche commune ▾ », Permis « Tous » à l'arrivée, changer d'outil vide l'état ✓
- **Front déployé neuf** confirmé dans le bundle servi (build `2026-10-30T21:29` Réunion) :
  `« Fiche commune »` (ContextePanel), `« Estimer un bien »` ×4 (**`« Analyser une annonce »` = 0** →
  renommage RECETTE-4 Lot 6 complet), `« aucune depuis 2014 »`, `« Partir d'une sélection »` (ParcoursProjet).
- **Fiche commune ▾** (RECETTE-4 Lot 7) : le sélecteur commune qui gelait l'UI (`setCommune` →
  `getParcelsGeojson`, rechargement carte) est **retiré** au profit d'un **bouton** qui ouvre la fiche
  **sans filtrer ni recharger la carte** (logique front, bundle + vitest).
- **Permis « Tous » à l'arrivée** (RECETTE-4 Lot 2) : `ModulePanel.tsx:521` initialise `seg='tous'` et aligne
  la fenêtre sur 240 mois. Backing vérifié LIVE : `GET /modules/permis?months=240` → **200, total 50 809**.
- **Changer d'outil vide l'état** (RECETTE-4 Lot 1, T1) : `<Body key={def.key} />` force un **remontage neuf**
  à chaque changement d'outil (`ModulePanel.tsx:1950/1973`) — l'état interne (sous-vue, commune) ne survit
  plus (bundle + vitest).

### 5. Veille — page unique, modifier une alerte de test puis la remettre à l'identique ✓ (VEILLE-3)
- Cycle complet sur le compte de test (uid 31), **nettoyé** : `POST /radar/veille` (Saint-Leu/maison) →
  `veille_id=9` ; `PUT /radar/veille/9` (Saint-Paul) → **`{ok:true}`** ; **`PUT` retour à l'identique**
  (Saint-Leu) → **`{ok:true}` (aucun faux 409)** — le `sauf_id` de `existe_identique` exclut bien l'alerte
  éditée (correctif VEILLE-3) ; état relu = `{Saint-Leu, maison}` ; `DELETE` → **`{ok:true}`, absente ensuite**.

### 6. Radar — aucune durée « depuis 1970 » ✓ (RECETTE-4 Lot 5 / RADAR-COUVERTURE-1)
- `GET /radar/biens?taille=300` → 200, **200 biens servis**. **23 biens portent une date de publication
  brute `1970` en base**, mais la règle front `joursDepuis` (plancher 2005, époque/illisible → `null`)
  les **rejette** : max ancienneté calculée = **913 j** (repli sur `date_saisie`), **aucune ~20 756 j**.
  Rendu : `« En vente longue »` quand la durée est nulle (jamais « depuis 1970 »). Garde verrouillée par
  `RadarEcran.joursDepuis.test.ts` et présente dans le bundle (`« longue »`, MapView).

### 7. `docs_coherence.py` zéro écart + ~15 min de journaux propres ✓
- **`docs_coherence.py` sur `97415000BY0083`** (API `127.0.0.1:8000`, cookie injecté au runtime via un
  opener urllib — jamais affiché ; Bilan rendu en-process) → **0 écart sur 18 données partagées** (exit 0) :
  surface 2 458, emprise 900, 11 bâtiments, zone libérée 1 736, pente 9,7°, hauteur 9/6, recul 4, 2 pl/logt,
  pleine terre 40 %, prix bâti 4 125 / terrain 250 / VEFA 4 745, SDP max 1 327 / résiduelle 453, propriétaire
  succession, date 27/10/2026 — **identique à DEPLOY-1029b**.
- **Journaux depuis le restart (2 737 lignes, 21:29:24 → 21:44:21 Réunion, ~15 min)** : **0 ERROR: / 0
  Traceback / 0 Exception / 0 CRITICAL / 0 segfault / 0 HTTP 5xx** ; **0 mail / SMTP / radar-cloche /
  digest**. Distribution HTTP = **119 × 200**, 2 × 401 + 1 × 404 (toutes mes entrées de test délibérées).
  **1 seul WARNING** (21:29:48) : `heal schéma — module « pige » : conflit de verrou (essai 1), nouvelle
  tentative…` → **convergé au 1er réessai** (pas d'essai 2/3, pas de `heal_failed`), readyz resté 200 tout
  du long — c'est exactement le **heal résilient REMISE-1** qui absorbe un verrou transitoire au boot.
  Bénin.

---

## Ménage du VPS (go donné dans le mandat)

Inventaire listé avec tailles avant suppression, puis suppression de **tout ce qui est antérieur au filet de
ce déploiement (`*-1030a`)** ; **conservés : le filet du jour + le dernier dump + le crontab de ce
déploiement**.

**Supprimés (antérieurs) :**
- Code : `app-avant-1029a` (7,7 G), `app-avant-1029b` (235 M), `app-avant-radarfix2` (237 M),
  `app-avant-radarfix2b` (234 M), `app.filet-20261029-000305` (235 M).
- venv : `venv-avant-1029a` (904 M), `venv-avant-1029b`, `venv-avant-etatfix-20261028-0249`,
  `venv-avant-radarfix2`, `venv-avant-radarfix2b` (7,3 M chacun).
- Caddy : `Caddyfile.avant-1027`, `.avant-1029b`, `.avant-zstd`, `.bak-20260722-1852`, `.bak-b11`,
  `.bak.202607231945`, `.rideau-20260827-184956`.
- cron.d : `labuse.bak-deploy-{20261028-172328, -195616, -221823, 20261029-000344, -122515, -164311}`,
  `labuse.bak-dvfdegel-20261020`, `labuse.bak-etatfix-20261028-013357`,
  `labuse.bak-etatfixdeploy-20261028-025128`, `labuse.bak-offsite-20261014-162648`.
- Dump : `labuse-labuse-20261029-133004.dump` (6,1 G) + `labuse-pige-captures-20261029-133004.tar.gz`
  (antérieur au dernier).

**Conservés :** `app-avant-1030a`, `venv-avant-1030a`, `Caddyfile.avant-1030a`,
`/etc/cron.d/labuse.bak-deploy-20261030-212920` (crontab de CE déploiement), dump
`labuse-labuse-20261029-161844.dump` (6,1 G, le dernier) + son tarball captures, et le `Caddyfile` LIVE
intact (service `labuse`/`caddy` actifs, public `/readyz` 200).

**Espace libéré : 7,28 Go** (34 G → **41 G libres**, 66 % → **58 %**) — l'essentiel vient de
`app-avant-1029a` (ancien `data/` non partagé).

---

## Synthèse

**Déployé et validé** : `main` **`153c95032`** en prod — **CHASSE-4-FIX** (fiabilité mot backend, aléas
`_risques_rows`, drapeau copro `score_v2.copro`, comptes terrain par rayon réel) + **RADAR-COUVERTURE-1**
(fenêtre soir heure Réunion, pagination par nouveauté, Bien'ici dans la passe auto) + **BANC-RAYON-1**
(`_ECART_SEGMENT` recalibré {appart 17, maison 28, terrain 19, bâti 26}, rayon de rattachement par source) +
**ETUDE-ASYNC-1** (étude dans un processus séparé tuable — ne bloque plus les autres requêtes) + **VEILLE-3**
(la Veille en une page, modifier une alerte en place) + **RECETTE-4** (18 points, 9 lots : « Estimer un
bien », tuile « Dernière vente », en-tête « Fiche commune », Permis « Tous », date ≠ 1970, …).
**Déploiement CODE-SEUL** : manifeste q_v20 intact, aucune colonne/table, aucune donnée, **aucun mail**,
radar-cloche/digest gelés, **0 × 503**, `NRestarts=0`.

**Les 7 points de fumée sont VERTS**, avec trois nuances honnêtes, **toutes non bloquantes** : (2) le compte
de processus `spawn_main` passe de 6 (pendant) à 5 (après) — les 5 sont les **workers uvicorn persistants**,
l'enfant étude est bien **récupéré** ; (3) la tuile « Dernière vente » de BZ1065 affiche **« aucune depuis
2014 »** car cette parcelle n'a **aucune mutation DVF** (tuile câblée, valeur légitime) ; (6) 23 biens
portent une date brute `1970` en base, **neutralisées** par la garde `joursDepuis` (max 913 j, jamais
20 756) — preuve que le correctif tient sur des données réelles.

**À signaler** : un WARNING unique au boot (heal `pige`, verrou transitoire) **convergé au 1er réessai**
(heal résilient REMISE-1) — comportement attendu, pas un incident.

**Filet conservé** pour rollback immédiat : `/opt/labuse/app-avant-1030a` + `/opt/labuse/venv-avant-1030a` +
`/etc/caddy/Caddyfile.avant-1030a` + dump `labuse-labuse-20261029-161844.dump` (6,1 G, 1748 TOC).
**Aucun rollback effectué.** Session de test **purgée**, fichiers temporaires supprimés.
