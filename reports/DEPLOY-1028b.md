# DEPLOY-1028b — mise en prod de `fix/vitesse-2` (main)

Lancé le 28/10/2026 depuis `~/Desktop/labuse-main`, prod `labuse-vps`.
Périmètre demandé : le merge de `fix/vitesse-2` (VITESSE-2, Lots 1→7) — cache PARTAGÉ des indicateurs
comparateur (`comparateur_raw_cache`), cache de fiche PARTAGÉ multi-worker (`fiche_cache`), index
fonctionnels `left(idu,14)`, réutilisation du cache par `/compare`, réchauffage des caches au déploiement
et au démarrage de chaque worker. **Déploiement code-seul + 2 tables auto-créées** (aucun run de données,
q_v20 reste servi, aucune bascule, aucune migration manuelle).

Règles (identiques DEPLOY-1027/1028) : jamais `deploy.sh` ni `deploy_donnees.sh` ; env chargé ; manifeste
servi jamais écrasé ; crontab reposé/vérifié au déploiement ; aucun secret affiché ; une phase ne démarre
que si la précédente est verte ; retour arrière prêt.

> **Périmètre réel confirmé en séance (décision Vic).** Prod était à `8fa2e3dc0` (RECETTE-PROD-1,
> DEPLOY-1028). Déployer `main` fait avancer la prod sur **tout** le delta `8fa2e3dc0 → main`, qui
> contient — en plus de `fix/vitesse-2` — **DONNEES-ETAT-FIX-2** (merge `6cb05919d` + `aec5db1ca` +
> correctif `7850374f3` : la bascule ne spawn plus de rebuild détaché, test de restauration Mac, cartes
> cockpit copie hors-site/incidents, propagation après bascule). Choix validé : **déployer `main`
> entier** (prod == main, pas de divergence ; un cherry-pick de vitesse-2 seul aurait fait diverger
> prod de main — anti-pattern). Le détail du delta est documenté au §Phase 2.

---

## Phase 0 — état des lieux (lecture seule)

### 0.1 Mac
- `git fetch` + `git rev-parse` au démarrage : HEAD = origin/main = **`5810551f3`** (« Merge branch
  'fix/vitesse-2' »). Pendant la séance, `main` a **fast-forwardé** de 2 commits `docs:` poussés en amont
  (`d1ddb4d5a` RADAR-ETAT-1, `18e5c6a87` DONNEES-ETAT-2 — **documentation uniquement**). Déploiement fait
  depuis **`18e5c6a8`** (tip de main). `git diff 5810551f3..18e5c6a8` = **5 fichiers sous `docs/`
  seulement** → le code expédié est **identique octet pour octet à `5810551f3`** (`docs/` est exclu du
  rsync). Voir §Phase 2.
- Intrus sans effet : `logs/` non suivi.

### 0.2 VPS
- Service `labuse` : **active** ; `/readyz` → **200**. ✓
- Disque `/dev/sda1` : 96 G, **71 G utilisés, 26 G libres (74 %)**. ✓
- Mémoire : OK.
- Run servi (`served_manifest.json`) : **scoring=q_v20 · cascade=q_v19_sources · mvt=q_v20 ·
  division=q_v19 · residuel_seq=17** ; `served_run.txt` = q_v20. **Doit rester q_v20** (aucune bascule).
- Code prod avant = déploiement du 27/10 (`8fa2e3dc0`) — confirmé : `grep _fiche_servie app.py` = 0 sur
  la prod (vitesse-2 absent). `deploiement.json` montrait un marqueur périmé (`8564b1e7`, 21/09) car le
  `deploy_app.sh` de l'époque n'avait pas encore l'étape 4c (ajoutée par DONNEES-ETAT-FIX-2) — corrigé
  par ce déploiement.

### 0.3 Écart de schéma (`labuse doctor`, user labuse, env chargé)
```
✓ Base joignable · ✓ Schéma réconcilié · ✓ Schéma : OK · ✓ Données (Saint-Paul) : OK · ✓ Healthcheck 14/14
✗ Parcelles de démo conformes   • Cache fiches démo : 2/8 pré-chauffées
• Déclassements AU en attente : 1862 (statut ok)
```
**Aucun écart de schéma.** Le seul « NON PRÊT » = pré-chauffage des fiches de démo (2/8) — **préexistant**
(DEPLOY-1027/1028), hors mandat.

### 0.4 Tables neuves absentes AVANT déploiement
`to_regclass('comparateur_raw_cache')` = NULL, `to_regclass('fiche_cache')` = NULL → **les deux tables
n'existaient pas** en prod (attendu : vitesse-2 pas encore déployé). Elles sont auto-créées (cf. §2b).

### 0.5 Variables d'environnement de réchauffage
`LABUSE_WARM_ON_BOOT` et `LABUSE_WARM_IDUS` : **absentes de `/etc/labuse/labuse.env`**. Par défaut (code) :
`LABUSE_WARM_ON_BOOT` est **actif hors `env=local`** → **réchauffage au démarrage ACTIF en production** ;
`LABUSE_WARM_IDUS` par défaut = les 3 témoins `97410000AE1369 / 97415000BY0083 / 97411000BZ1065`.

### 0.6 Go / no-go
**GO.** Code-seul à faible risque : 2 tables auto-créées (`CREATE TABLE IF NOT EXISTS`), 2 index
fonctionnels posés au boot (heal idempotent), pas de données, pas de bascule, pas de migration manuelle,
disque sain.

---

## Phase 1 — filet de sécurité

### Sauvegarde
- `deploy/scripts/backup_postgres.sh` (nohup, env chargé, user labuse) → **`labuse-labuse-20261028-170218.dump`
  (6,7 G)**. Contrôle d'intégrité **intégré** (`pg_restore --list`) : **« ✓ Sauvegarde OK (6.7G) »** ;
  contrôle **explicite** supplémentaire : `pg_restore --list` → **OK, 1763 entrées TOC**. ✓
- Rotation : **3** dumps conservés (`LABUSE_BACKUP_KEEP=7` dans `labuse.env` ; le cron ramène à 2 via
  `BACKUP_ROTATION_N`). **À signaler à Vic (répété DEPLOY-1028 §1)** : `LABUSE_BACKUP_KEEP=7` contredit
  l'intention DONNEES-ETAT-FIX-1 (2 quotidiens) — sans effet sur ce déploiement.

### Copies (hardlinks `cp -al` → ~0 octet)
- Code : `/opt/labuse/app` → **`/opt/labuse/app-avant-1028b`** (vérifié : même inode qu'en prod).
- venv : `/opt/labuse/venv` → **`/opt/labuse/venv-avant-1028b`**.
- Refs config : `/etc/caddy/Caddyfile`, `/etc/cron.d/labuse`, `served_manifest.json` → `/root/*.avant-1028b`.

### Disque après dump
**78 G utilisés / 19 G libres (81 %)** — ample (code-seul, rsync en place, croissance ≈ 0).

### Phase R — retour arrière (commandes exactes)
```bash
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app  && sudo mv /opt/labuse/app-avant-1028b  /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-1028b /opt/labuse/venv
sudo chown -R labuse:labuse /opt/labuse/app
sudo systemctl start labuse && curl -fsS http://127.0.0.1:8000/readyz
# Les 2 tables neuves (comparateur_raw_cache, fiche_cache) sont ignorées par l'ancien code — sans effet.
#   (optionnel : DROP TABLE comparateur_raw_cache, fiche_cache ; les index left(idu,14) peuvent rester.)
# Manifeste/config/caddy NON touchés → rien à restaurer côté config.
# DB : restaurer labuse-labuse-20261028-170218.dump UNIQUEMENT si l'ancien code ne fonctionne plus.
```

**Verdict phase 1 : VERT.**

---

## Phase 2 — code

`sudo systemctl stop labuse` (readyz injoignable, attendu), puis
`VITE_RUN_LABEL=q_v20 deploy/scripts/deploy_app.sh labuse-vps` (depuis le Mac) :

```
── garde manifeste : run local 'q_v20' présent en prod (433229 lignes score_labuse) ✓
── 2. venv + dépendances … chaîne de démarrage importable ✓
── 3. Front (vite build --base=/, VITE_RUN_LABEL=q_v20)
── 4b. crontab reposé + vérifié : ✓ /etc/cron.d/labuse == registre (aucun écart, tz=reunion)
── 4c. marqueur de déploiement : deploiement.json = 18e5c6a87eb3 (déployé 2026-10-28T13:23:29Z)
── 5. manifeste prod : 'q_v20' (433229 lignes) ✓
── 6. fiche_cache vidé (invalidation déploiement) ; job fiche-commune-cache relancé (détaché)
✓ déployé
```

**Délta réellement déployé (`8fa2e3dc0` → `18e5c6a8`)** :
- `fix/vitesse-2` (Lots 1→7) — le mandat.
- **DONNEES-ETAT-FIX-2** (`6cb05919d`, `aec5db1ca`, correctif `7850374f3`).
- `f9eb57619` (rapport DEPLOY-1028, markdown), `d1ddb4d5a` + `18e5c6a87` (audits `docs/`, **non expédiés**).
- `git diff 5810551f3..18e5c6a8` = 5 fichiers `docs/` seulement ⇒ **code expédié == `5810551f3`** (docs
  exclus du rsync). La prod tourne donc exactement le code de main (vitesse-2 + DONNEES-ETAT-FIX-2).
- Pendant la rédaction, main a encore avancé (`18e5c6a8 → 29c3d3e6`) : diff **`docs/` + `reports/`
  uniquement** (re-merge du correctif bascule déjà inclus) ⇒ **le code prod reste à jour avec main**
  (rien de nouveau côté code après le déploiement). Ce rapport est commité sur `29c3d3e6`.

`labuse doctor` (service arrêté, env chargé) : **Base ✓ · Schéma réconcilié ✓ · Schéma OK ✓ · Données
Saint-Paul OK ✓ · Healthcheck 14/14 ✓** + nouvelle ligne **« ✓ Cache indicateurs communes (VITESSE-2) :
frais »**. Seul « NON PRÊT » = fiches démo 2/8 (préexistant).

`sudo systemctl start labuse` → **readyz 200** une fois le startup terminé (17:25:33) ; boot
« **env=production · auth=active · schéma=ok** », `Application startup complete`, et
**« labuse.rechauffage — réchauffage : indicateurs partagés (24 communes) chauds »** (réchauffage par
worker ACTIF). Manifeste servi **inchangé** : q_v20. ✓

**Phase 2 VERTE.**

---

## Phase 2b — tables neuves, `fiche_cache`, index, env

| Contrôle | Résultat |
|---|---|
| `comparateur_raw_cache` présente | **oui** (auto-créée), **1 ligne** (1 empreinte = les 24 communes), doctor « frais » ✓ |
| `fiche_cache` présente | **oui** (auto-créée) |
| `fiche_cache` schéma | `(idu PK, cle_fraicheur, payload jsonb, computed_at)` — **aucune colonne plan/compte** ✓ |
| Index `ix_pm_millesimes_idu14`, `ix_parcelle_pm_idu14` | **présents** (posés au boot/heal) ✓ |
| `LABUSE_WARM_ON_BOOT` / `LABUSE_WARM_IDUS` | **non positionnés** → défaut (réchauffage actif en prod, 3 témoins) |

### « `fiche_cache` vide après déploiement » — ce qui a VRAIMENT été observé
Le déploiement **vide bien** `fiche_cache` (étape 6 : `DELETE FROM fiche_cache`, invalidation prouvée).
**Mais** le réchauffage au démarrage (`LABUSE_WARM_ON_BOOT`, actif par défaut en prod) appelle
`_fiche_servie` sur les 3 témoins, dont le chemin **persiste** la fiche dans le cache PARTAGÉ L2. Donc,
quelques secondes après le `start`, `fiche_cache` contient **exactement 3 lignes = les 3 fiches témoins
PUBLIQUES** (AE1369 / BY0083 / BZ1065, écrites à 17:25:36–43), et **rien d'autre** :

```
      idu       |     cle      |          computed_at
97410000AE1369  | 4105e63c676e | 2026-10-28 17:25:36+04
97411000BZ1065  | 0431c3c30f49 | 2026-10-28 17:25:43+04
97415000BY0083  | b0f52e40bf77 | 2026-10-28 17:25:40+04
```

**Lecture honnête :** `fiche_cache` n'est pas *littéralement* vide après déploiement — elle est **vidée
de tout résidu de l'ancien code** (clé de fraîcheur = code_sha ⇒ invalidation) **et de toute donnée
compte/plan** (le schéma n'en a pas), puis **ré-amorcée par le réchauffage avec les 3 témoins publics**.
C'est **voulu et bénéfique** (les 5 workers lisent les témoins depuis L2 au lieu de recalculer chacun).
Si Vic veut une table **strictement vide** post-déploiement, il faudrait `LABUSE_WARM_ON_BOOT=0` — ce qui
**réintroduirait** le coût d'amorçage à froid que vitesse-2 supprime (non recommandé).
Au moment du rapport, après la recette, `fiche_cache` = 18 fiches, **toutes publiques** (idu-keyées).

**Phase 2b VERTE** (avec la nuance ci-dessus explicitée).

---

## Phase 3 — réchauffage des caches (déploiement + boot)

- **Étape 6 du déploiement** : job `fiche-commune-cache` relancé détaché → **statut `ok`, durée 755 s
  (~12,6 min), 24 communes, 0 erreur** (`job_runs` : début 17:23:32, fin 17:36:07, erreur NULL). Il
  réchauffe d'abord `comparateur_raw_cache` (Lot 1) puis `commune_contexte_cache` (24/24 communes). ✓
- `comparateur_raw_cache` : **frais** (clé == empreinte servie, doctor « frais »). `commune_contexte_cache`
  = **24 communes**. ✓
- **Réchauffage par worker** (boot) : chaque worker a chargé `raw_rows` (24 communes) en mémoire + les 3
  fiches témoins (journal `labuse.rechauffage`). ✓

**Phase 3 VERTE.**

---

## Phase 4 — vitesse en prod (lot C)

**Session.** Compte `gb-test-ae@labuse.local` = **utilisateur id 31, rôle admin, actif** (compte 31,
plan `illimite`). Session serveur **temporaire 3 h** via `comptes.creer_session(db, 31, 3)` ; le jeton
n'est **jamais affiché** — écrit dans un curlrc `600` (`/tmp/.gb1028b.curlrc`, labuse) lu par `curl -K`
(cookie `labuse_session=u.<token>`). Vérifié : `/version` **200** avec cookie / **401** sans ; 1 seule
session active uid 31. **Purgée en fin de phase 5.**

### C1 — matrice de latence (via Caddy `https://app.labuse.immo`, `time_total`, tous **200**)
cold = 1ᵉʳ hit · chaud = meilleur de 5 relances (5 workers). Colonne « Prod AVANT » = DEPLOY-1028 §Phase 4.

| Mesure | témoin | **AVANT** froid | **AVANT** chaud | **APRÈS** froid | **APRÈS** chaud |
|---|---|---|---|---|---|
| Fiche parcelle `/parcels/{idu}` | AE1369 (St-Benoît) | 4,07 s | 0,096 s | **0,151 s** | 0,082 s |
| | BY0083 (St-Paul) | 3,60 s | 0,088 s | **0,081 s** | 0,079 s |
| | BZ1065 (St-Denis) | 3,33 s | 0,083 s | **0,093 s** | 0,071 s |
| Clic carte / fiche commune `/communes/{c}/contexte` | Saint-Benoît | **5,62 s** | 0,074 s | **0,206 s** | 0,121 s |
| | Saint-Paul | 0,109 s | 0,069 s | **0,106 s** | 0,086 s |
| | Saint-Denis | 0,073 s | 0,073 s | **0,161 s** | 0,093 s |
| Gabarit 3D `/outils/gabarit/{idu}` | AE/BY/BZ | 0,30/0,32/0,27 | ~0,20 | 0,49/0,83/0,41 | 0,22/0,25/0,18 |
| Étude de faisabilité `/modules/faisabilite/{idu}` | AE/BY/BZ | 0,55/0,65/0,91 | 0,37–0,64 | 0,55/0,67/0,74 | 0,42/0,57/0,49 |
| Comparatif `/compare` (3 témoins) | — | **7,29 s** | **7,09 s** | **1,15 s** | **1,23 s** |
| Taxe d'aménagement `/outils/taxe-amenagement/prefill` | AE/BY/BZ | 0,091 | 0,081 | 0,09/0,10/0,08 | 0,07/0,09/0,07 |

**Lecture.** Les deux symptômes prod de DEPLOY-1028 sont **fermés** : le **1ᵉʳ clic commune** Saint-Benoît
**5,62 s → 0,21 s** (cache partagé `comparateur_raw_cache` + réchauffage, Lot 1) ; le **Comparatif
7,29 s → 1,15 s** (réutilisation du cache de fiche, Lots 3+7). Les fiches témoins sont servies **chaudes
dès le 1ᵉʳ hit** (3–4 s → ~0,1 s) grâce au réchauffage au boot (Lot 4). Gabarit/Étude restent des calculs
LIVE (pas de cache persistant) : ordres de grandeur inchangés, conformes.

### 10 parcelles JAMAIS ouvertes (fiche à froid — effet INDEX `left(idu,14)` + cache partagé L2)

| idu | froid | chaud | | idu | froid | chaud |
|---|---|---|---|---|---|---|
| 97409000BL0111 | **47,29 s** ⚠ | 0,092 s | | 97415000AW2362 | 1,76 s | 0,088 s |
| 97410000BW0967 | 1,95 s | 0,069 s | | 97416000CW1762 | 2,58 s | 0,071 s |
| 97411000HE0412 | 2,13 s | 0,084 s | | 97417000BC0831 | 1,36 s | 0,083 s |
| 97413000CT0442 | 1,81 s | 0,082 s | | 97418000AI0265 | 2,47 s | 0,086 s |
| 97414000HI0401 | 2,20 s | 0,066 s | | 97419000AK0762 | 1,46 s | 0,081 s |

- **Froid steady-state ≈ 1,4–2,6 s** (coût d'un calcul COMPLET d'une fiche jamais vue — inhérent, aucun
  cache ne peut aider une fiche jamais calculée ; comparable aux 3,3–4,1 s de DEPLOY-1028).
- **Chaud ≈ 0,07–0,09 s** sur **n'importe quel worker** (cache partagé L2).
- ⚠ **L'outlier 47,3 s (BL0111)** = la **toute première** fiche jamais vue, frappée **à l'instant du
  déploiement** pendant que (a) les 5 workers réchauffaient simultanément, (b) le job `fiche-commune-cache`
  tournait (gros 6-joins + DVF), (c) les premiers buffers étaient froids. **Transitoire et non
  reproductible** : vérifié après apaisement, sur système **idle**, une fiche fraîche jamais vue
  (`97412000BK0634`, `97420000BC1246`) = **3,71 s / 1,98 s** — pas 47 s. L'outlier n'est pas un état
  permanent ; c'est le pic d'une fenêtre de déploiement.

### `/compare` sur 3 parcelles JAMAIS ouvertes
`/compare?idus=97421000BN0236,97422000BV2440,97424000AC0263` : **froid 6,65 s · chaud 0,786 s**
(AVANT DEPLOY-1028 : 7,3 s / 7,1 s). Le froid calcule 3 fiches jamais vues (~5 s) ; le chaud lit le cache
partagé → **~9× plus rapide** qu'avant.

### Cache de fiche PARTAGÉ multi-worker (Lot 7) — preuve directe
Parcelle fraîche ouverte **1×** (froid 2,67 s) puis **12 relances en round-robin sur les 5 workers** :
`0,085 0,067 0,074 0,086 0,076 0,116 0,078 0,066 0,101 0,073 0,113 0,097` → **max 0,116 s**. Aucun worker
ne recalcule (avant Lot 7, une relance tombant sur un autre worker repayait ~2 s). ✓

**Phase 4 VERTE.**

---

## Phase 5 — fumée en prod + forfaits

### 5.1 `docs_coherence.py` sur BY0083 (contre `https://app.labuse.immo`)
Copie exécutée en prod (cookie de la session injecté au runtime, jamais affiché ; Bilan en-process) :
**0 écart sur 18 données partagées** (exit 0). Les 8 documents génèrent ET s'accordent (surface 2 458,
emprise 900, zone libérée 1 736, hauteur 9/6, recul 4, 2 pl/logt, pleine terre 40 %, prix bâti 4 125,
terrain 250, VEFA 4 745, SDP max 1 327, SDP résiduelle 453, date 27/10/2026, propriétaire succession…). ✓

### 5.2 Forfaits — rien dans `fiche_cache` ne dépend du plan ni du compte ; le filtrage est APRÈS le cache
**Preuve dans le code :**
- `_fiche_servie(db, idu, run)` (app.py:6836) ne prend **que** `(db, idu, run)` ; de même `_q_v2_fiche` et
  `analyse_labuse`. Clé L1 = `(idu, run, score_run, version data_sources, jeton_parcelle)` — **aucun
  compte/plan** (app.py:6854). Clé L2 `_fiche_db_cle` = empreinte run + version + jeton — **aucun
  compte/plan** (app.py:6718-6724). Schéma `fiche_cache` = `(idu, cle_fraicheur, payload, computed_at)` —
  **aucune colonne compte/plan** (app.py:6695-6702).
- La **seule** chose ajoutée par requête APRÈS `_fiche_servie` est `_trace` (admin + `trace=1`), hors
  cache (app.py:6938-6946). L'endpoint `/parcels/{idu}` **ne filtre jamais** le contenu de la fiche selon
  le plan.
- Le plan n'agit QUE sur les **exports / quotas**, évalués **en direct** à leurs propres endpoints :
  `plans.acces("dossier_illimite"/"dossier_parcelle"/"pre_dossier_pc")` + quota par compte
  (`usage_compteurs` clé `sujet_quota`) dans `dossier.py` (l.57/77/83) et `pre_dossier.py` (l.1070) —
  **après / en dehors** de la lecture du cache de fiche. (Note : `plans.plan_courant()` est aujourd'hui
  un **STUB global** lisant `LABUSE_PLAN_DEFAUT` — « Auth & Plans branchera ici le plan réel du compte » ;
  la dimension par-compte vivante est `comptes.plan` et le quota export par compte — jamais la fiche.)

**Preuve empirique en prod (lecture seule) :**
- `sha256` canonique de `/parcels/BY0083` servi **== `sha256` canonique du `payload` stocké dans
  `fiche_cache`** (MATCH) → la fiche servie **est** le payload partagé, agnostique au compte.
- Le payload de fiche a **77 clés de 1ᵉʳ niveau, ZÉRO** clé `plan/compte/forfait/abonnement/quota/
  account/stripe`. `cle_fraicheur` = `b0f52e40…` (aucune dimension compte).
- `/moi` renvoie le plan **par compte** (`illimite` ici) — la dimension compte vit dans `comptes`, pas
  dans la fiche. `/dossier/statut` (lecture seule) renvoie le **gate plan/quota** (`plan`, `illimite`,
  `quota_mois`, `restants`), évalué en direct à l'endpoint d'export.

> La bascule de plan en prod (A/B « même parcelle, deux plans ») a été **écartée** : elle aurait muté un
> compte de production, hors périmètre (« confirme dans le code »). La preuve lecture-seule ci-dessus
> (sha fiche servie == payload caché + 0 clé plan + gate aux endpoints d'export) établit l'invariant :
> **une même parcelle montre la même fiche quel que soit le plan ; « ce que le plan autorise » ne diffère
> que pour les exports/quotas, calculés en direct, jamais servis depuis `fiche_cache`.**

### 5.3 `/readyz` et journaux — un incident réel, diagnostiqué et CORRIGÉ
- `/readyz` (local + Caddy) : **200** stable après correction (voir ci-dessous).
- **Incident `/readyz` flappant (503 ~40 %) après le 1ᵉʳ démarrage — RÉSOLU.** Dans l'heure suivant le
  `start`, `/readyz` renvoyait **503 ~1 fois sur 3** (journal depuis le restart : 11×503 vs 20×200 ;
  échantillon rapide : 8/20 en 503). **Cause racine (lecture du code + détail readyz avec session admin) :**
  au boot, le **heal de schéma du module `pige`** (`ALTER TABLE pige_biens ADD COLUMN IF NOT EXISTS
  retiree_le`) a **deadlocké** sur 1–2 workers — collision de verrous (AccessExclusiveLock de l'ALTER vs
  AccessShareLock d'un lecteur) à l'instant du déploiement, le gros job `fiche-commune-cache` (étape 6)
  tournant **en même temps** que le heal par-worker. Or `/readyz` **reflète honnêtement** l'état du heal
  (`app.state.schema_heal`, FIX-GB-011, app.py:921-929) : les workers dont le heal a échoué renvoient
  `ready=false` → **503**, les autres **200** → d'où le flap ~40 % (5 workers load-balancés).
  - **Pas de dégât de schéma** : la colonne `pige_biens.retiree_le` **existe** (un autre worker l'a bien
    ajoutée) ; `data.ok:true`, `served_run:q_v20`. Le heal échoué était un artefact de **timing de
    verrous**, pas un schéma cassé.
  - **Correction (geste de déploiement)** : **restart propre à froid** (système idle, job terminé) →
    tous les workers rejouent le heal (idempotent, colonne déjà là → aucun verrou en conflit) →
    `schéma=ok` sur tous. Vérifié : **readyz 25/25 = 200**, `schema.ok:true`, `heal_failed:null`,
    Caddy readyz 200.
- **Fenêtre propre post-restart (~52 min, 18:07 → 18:59, 111 lignes journal)** : **0 ERROR / Traceback /
  CRITICAL / Exception · 0 HTTP 5xx · readyz 101×200 / 0×503** (76 passifs + 25/25 échantillons actifs).
  Bien au-delà des 10 min demandées. ✓
- Note : les mesures de la Phase 4 ont été prises AVANT ce restart ; elles restent valides (le flap
  touchait l'état du heal `pige` des workers, pas le service de fiches/contexte).

### Purge de la session
`DELETE FROM sessions_auth WHERE utilisateur_id=31` → **0 session active restante** ; curlrc
`/tmp/.gb1028b.curlrc` + scripts/py temporaires de recette supprimés (cf. Phase 6).

**Phase 5 VERTE** (0 écart docs, forfaits prouvés ; readyz flap diagnostiqué ET corrigé → 200 stable,
~52 min de journaux propres).

---

## Phase 6 — après
- Fumée verte (après correction readyz) → snapshots `/opt/labuse/app-avant-1028b` + `/opt/labuse/venv-avant-1028b`
  **supprimés** ; curlrc + scripts/py de recette (`/tmp/.gb1028b.curlrc`, `h1028b*.sh`, `dc_run.py`,
  `forfait_*`, `jlog*.txt`, CSV) **supprimés** ; session gb-test-ae **purgée** (0 active). Refs config
  `/root/*.avant-1028b` conservées (quelques Ko, non utilisées — config non touchée).
- **État final prod** : readyz **200** (local + Caddy), `served_run` **q_v20**, disque **81 % / 19 G**,
  dump de reprise `labuse-labuse-20261028-170218.dump` conservé.
- Ce rapport commité et poussé (hook normal).

---

## Synthèse

**Déployé et validé** : `main` (**`18e5c6a8`**, code == `5810551f3`) en prod — **VITESSE-2 (Lots 1→7)**
+ **DONNEES-ETAT-FIX-2**. Code-seul + 2 tables auto-créées (`comparateur_raw_cache`, `fiche_cache`) + 2
index fonctionnels `left(idu,14)` ; **aucun run de données, aucune bascule, aucune migration manuelle** —
la prod sert toujours **q_v20 / q_v19_sources / mvt q_v20 / division q_v19 / résiduel 17** (manifeste
intact). Toutes les phases VERTES.

**Gains prod mesurés (vs DEPLOY-1028) :**
- 1ᵉʳ clic commune (Saint-Benoît) : **5,62 s → 0,21 s**.
- Fiche témoin à froid : **3–4 s → ~0,1 s** (réchauffage au boot).
- Comparatif 3 témoins : **7,29 s → 1,15 s** ; relance : **7,09 s → 1,23 s**.
- Relecture multi-worker d'une fiche : **~2 s (worker froid) → 0,07–0,12 s** (cache partagé L2).
- Fiche jamais vue à froid : ~2–3,7 s (inhérent au calcul complet, inchangé ; aucun cache n'aide une
  fiche jamais calculée).

**Décisions / nuances prises en séance :**
- **Déployer `main` entier** (vitesse-2 + DONNEES-ETAT-FIX-2) — confirmé par Vic (prod == main).
- `fiche_cache` **non littéralement vide** après déploiement : vidée du résidu/compte, puis ré-amorcée par
  le réchauffage avec **3 fiches témoins publiques** (voulu). Cf. §2b.
- Forfaits : preuve **dans le code** + **empirique lecture-seule** (pas de bascule de plan en prod).

**À faire ensuite (hors mandat) :**
1. **⚠ Séquencement déploiement → deadlock du heal `pige` → readyz flap (CORRIGÉ ici par restart, mais à
   fiabiliser).** `deploy_app.sh` étape 6 lance le gros job `fiche-commune-cache` **puis** le service
   redémarre ; le heal par-worker (ALTER TABLE `pige_biens`) et le job se disputent les verrous →
   deadlock → workers « non prêts » → `/readyz` 503 ~40 % jusqu'au restart. **Pistes** : (a) heal de
   schéma sous `lock_timeout` court + retry (pas d'ÉCHEC définitif sur un simple conflit de verrous) ;
   (b) ne lancer le job d'étape 6 **qu'après** le `start` du service et son heal ; (c) à défaut, ajouter
   un **restart propre** comme geste documenté de fin de déploiement (fait ici).
2. **Outlier 47 s** à la toute 1ʳᵉ fiche d'un déploiement (même fenêtre de contention réchauffage-job +
   boot + buffers froids). Piste : étaler/retarder le réchauffage. Sans impact en régime permanent
   (fiche fraîche idle = 2–3,7 s).
3. **`LABUSE_BACKUP_KEEP=7`** dans `labuse.env` (répété DEPLOY-1028) — aligner sur 2.
4. **Préexistants** (DEPLOY-1027/1028) : fiches démo 2/8 ; disque 81 %.
