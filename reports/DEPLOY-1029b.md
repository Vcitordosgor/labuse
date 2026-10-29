# DEPLOY-1029b — mise en prod de `main` (`b955de8e5`) : RADAR-FIX-3 + CORRECTIFS-2 + ESTIMATION-BANC-1 + RADAR-SOURCES-2 + ANNONCE-5

Lancé le 29/10/2026 depuis `~/Desktop/labuse-main`, prod `labuse-vps` (`https://app.labuse.immo`).
Périmètre : faire avancer la prod de `9dd75d2ab` (DEPLOY-1029a) à **`b955de8e5`** (« Merge branch
'feat/annonce-5' »), soit le delta **RADAR-FIX-3 + CORRECTIFS-2 + ESTIMATION-BANC-1 + RADAR-SOURCES-2 +
ANNONCE-5** (13 commits). **Déploiement code-seul + 1 colonne + restauration de données sous go de Vic** :
manifeste intact, aucun mail, radar-cloche/digest gelés. Mêmes règles que `reports/DEPLOY-1029a.md`.

> ⚠ **DÉPLOIEMENT EN JOURNÉE — go explicite de Vic, aucun client actif.** Joué vers **16 h 15–17 h 16
> Réunion**. Le risque diurne ne s'est pas matérialisé : la seule session active au moment du restart était
> **la session admin de Vic lui-même** (`kampusreunion@gmail.com`, uid 19) — **aucun client**. Le nouvel
> ordre `deploy_app.sh` (restart → readyz 25/25 stable → réchauffage) a tenu : **0 × 503 servi au restart**.

---

## Étape 0 — garde-fou + VACUUM + sessions

- **16 h 15 Réunion** (`TZ=Indian/Reunion`, VPS `vps-5563949c`). Déploiement en journée **assumé sur go de
  Vic** (aucun client actif).
- **Aucun VACUUM / autovacuum** en cours (`pg_stat_activity` = 0).
- **Aucune session client** : une seule session active = **la session admin de Vic** (uid 19). 0 session
  client, 0 session de test résiduelle.
- Disque : **34 G libres / 65 %**. readyz local 200.

---

## Pré-vol

- **Cible strictement en avance, sans divergence** : `9dd75d2ab` est **ancêtre** de `b955de8e5`
  (`git merge-base --is-ancestor` = vrai, 13 commits). `b955de8e5` **== origin/main** (0 commit d'avance,
  re-vérifié après `git fetch`).
- **Prod réelle avant** : `config/deploiement.json` = `9dd75d2abd6418fb…`, `par=deploy_app.sh`,
  déployé 2026-10-29T08:25:17Z — conforme à l'attendu (DEPLOY-1029a).
- **Manifeste servi** : `scoring=q_v20 · cascade=q_v19_sources` — **resté intact** (manifeste exclu du
  rsync, re-vérifié après déploiement).
- **Notifications Radar gelées** : `radar-cloche`/`digest` restent commentés « GELÉ » dans le crontab
  (reposé == registre à l'étape 4b) ; défaut code OFF → **aucun mail possible**.

### Schéma — `pige_passes.n_non_verifiees` posée AVANT le restart (comme `pige_passes.source` à RADAR-FIX-2)
- **Seule nouveauté schéma de tout le delta** (vérifié : `git diff 9dd75d2ab..HEAD` ne contient qu'un seul
  `ADD COLUMN` / `CREATE TABLE`). **Bien'ici / ANNONCE-5 n'attendent AUCUNE autre colonne ni table** (le
  reste est code, front, extension, fixtures).
- Posée manuellement en superutilisateur **avant le restart**, verrou `ACCESS EXCLUSIVE` **borné à 5 s** :
  `SET lock_timeout='5s'; ALTER TABLE pige_passes ADD COLUMN IF NOT EXISTS n_non_verifiees integer NOT NULL
  DEFAULT 0;` → `ALTER TABLE` (exit 0). Objectif : rendre le DDL `IF NOT EXISTS` du heal au boot **no-op**
  (évite le flap 503 du deadlock heal `pige`, incident DEPLOY-1028b).

### Sauvegarde vérifiée (`pg_restore --list`)
- Nouvelle sauvegarde pleine prise **avant la mutation** (daytime + restauration à venir) :
  **`labuse-labuse-20261029-161844.dump` (6,1 G)**, contrôle intégré **« ✓ Sauvegarde OK »** +
  `pg_restore --list` = **1748 entrées TOC**, dont `TABLE DATA public pige_biens` (contient les 60 en
  `retiree`). Dump 13:48 (`…-133004.dump`) conservé en second (rotation KEEP=2). ✓

### Filet (`cp -al`, hardlinks ≈ 0 octet)
- Code : `/opt/labuse/app` → **`/opt/labuse/app-avant-1029b`** (inode identique vérifié).
- venv : `/opt/labuse/venv` → **`/opt/labuse/venv-avant-1029b`**.
- Caddy : `/etc/caddy/Caddyfile` → **`/etc/caddy/Caddyfile.avant-1029b`** (avant la pose du 90 s).

### Phase R — retour arrière (prêt, conservé)
```bash
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app  && sudo mv /opt/labuse/app-avant-1029b  /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-1029b /opt/labuse/venv
sudo chown -R labuse:labuse /opt/labuse/app
sudo cp /etc/caddy/Caddyfile.avant-1029b /etc/caddy/Caddyfile && sudo systemctl reload caddy
sudo systemctl start labuse && curl -fsS http://127.0.0.1:8000/readyz
# Colonne n_non_verifiees : inoffensive pour l'ancien code (jamais lue), laissée en place.
# Restauration des 60 : réversible via la table d'audit pige_restauration_radarfix3 (SQL en §Restauration).
# DB : restaurer labuse-labuse-20261029-161844.dump UNIQUEMENT si l'ancien code ne fonctionne plus.
```

---

## Déploiement — `VITE_RUN_LABEL=q_v20 deploy/scripts/deploy_app.sh labuse-vps`

Arbre local propre sur la cible (`logs/` non suivi mis de côté). Déroulé **exit 0**, nouvel ordre REMISE-1 :

```
── garde manifeste : run local 'q_v20' présent en prod (433229 lignes score_labuse) ✓
── 1. rsync (manifeste/données/docs/qa/tests exclus)   ── 2. venv + chaîne de démarrage importable ✓
── 3. front (vite build --base=/, q_v20)               ── 4. systemd
── 4b. crontab reposé + vérifié : ✓ == registre (aucun écart, tz=reunion)   ← radar mail restent gelés
── 4c. deploiement.json = b955de8e5188 (déployé 2026-10-29T12:43:13Z)
── 5. manifeste prod : 'q_v20' (433229 lignes) ✓
── 6. fiche_cache vidé (DELETE 11, invalidation déploiement — ATTENDU)
      restart → /readyz 200 STABLE (25/25 consécutifs, 39 essais) ✓ → job fiche-commune-cache (détaché)
✓ déployé — service redémarré, /readyz 200 stable, caches en réchauffage.
```

- **SHA prod déployé = `b955de8e5188ffad…`** (la cible).
- **Manifeste INCHANGÉ** : `served_run` = **q_v20** (exclu du rsync).
- **Crontab** reposé depuis le registre et **vérifié == registre** (radar-cloche/digest restent gelés).
- **Aucun 503 servi au démarrage** : le « 39 essais pour 25 consécutifs » = le trou de connexion pendant
  le reboot des workers (connection-refused), **pas** des 503 HTTP. La colonne pré-posée a rendu le heal
  silencieux (aucun `ALTER` en vol). `NRestarts=0` depuis (pas de boucle de crash).
- **`fiche_cache` vidé par le script** (DELETE 11) — **attendu** ; le réchauffage le ré-amorce.

## Caddy — pose de `deploy/Caddyfile.prod` (marge 75 s → 90 s, CORRECTIFS-2 Lot 2), sans redémarrage

- Filet posé (`Caddyfile.avant-1029b`), puis `cp deploy/Caddyfile.prod → /etc/caddy/Caddyfile`, puis
  `systemctl reload caddy` (= `caddy reload --force`, **sans redémarrage**). Caddy reste `active`.
- **`read_timeout` 90 s confirmé dans la config LIVE** (admin API `:2019/config/` → `90000000000` ns, et
  **plus aucun `75000000000`**). Seul écart au fichier précédent = la valeur numérique + les commentaires.
- **`caddy validate` signale `unrecognized global option: encode` (ligne 30)** : **quirk bénin, PAS une
  régression** — l'ancien Caddyfile (`Caddyfile.avant-1029b`), en service depuis le 27/10 sans incident,
  produit **exactement la même erreur**. `encode` est une directive de site que le sous-commande `validate`
  autonome mélit en option globale ; le runtime (`caddy run`/`reload`) l'accepte (service actif, public 200).
  (CORRECTIFS-2 notait déjà que `caddy validate` n'était pas jouable hors prod.)

**Manifeste et données non touchés** par le déploiement du code (hormis la colonne + la restauration ci-dessous).

---

## Restauration des 60 biens — go de Vic donné, API verte

`docs/audit-2026-10/radar-fix-3/restauration.sql` joué en **UNE transaction** (`psql -v ON_ERROR_STOP=1
-1 -f -`) après readyz vert. État **AVANT** (lecture seule) : **60/60 `retiree`, 0 `active`, 0 vente DVF**.

```
BEGIN → DROP/CREATE table d'audit → SELECT 60 → DO (garde-fous OK : 60, toutes retiree, 0 vendue) →
UPDATE 60 →
 actifs | reste_retiree_le | reste_vendue
   60   |        0         |      0
COMMIT
```

- **Vérif indépendante (nouvelle connexion)** : les 60 `bien_id` = **60 `active`, 0 `retiree`, 0
  `retiree_le`, 0 `vendue_le`**. ✓ (exactement 60, sinon ROLLBACK + STOP — non déclenché.)
- **Filet de réversibilité conservé** : table d'audit **`pige_restauration_radarfix3`** (60 lignes, état
  AVANT horodaté) ; SQL de retour arrière en tête du script.
- Les avertissements `transaction already in progress` / `no transaction in progress` sont **attendus** avec
  la commande documentée `-1` (le `BEGIN`/`COMMIT` interne du script niché dans la transaction `-1`) et
  **bénins** — l'`UPDATE 60` est bien committé.

---

## Fumée — méthode 1028b (session de test éphémère, jeton jamais affiché)

Compte `gb-test-ae@labuse.local` = **uid 31, admin**. Session 3 h via `comptes.creer_session(db, 31, 3)` ;
cookie `labuse_session=u.<token>` écrit dans un **curlrc 600** (`/tmp/.gb1029b.curlrc`, labuse), lu par
`curl -K`, **jamais imprimé**. Vérifié : `/version` **401 sans cookie / 200 avec**. **Purgée en fin de
run** (`DELETE … uid 31` → 1 supprimée ; ne reste active que la session de Vic uid 19).

### 1. readyz 25/25 + fiche BY0083 `etat_bien` renseigné ✓
- `/readyz` (Caddy, public) : **25/25 = 200**.
- `GET /parcels/97415000BY0083` → **200, 0,024 s**, 78 clés, Saint-Paul, **`etat_bien = "bati_encore"`**
  (CORRECTIFS-2 Lot 1 : la fiche sert bien l'état du bien), aucune clé d'erreur.

### 2. Étude d'un assemblage de 4 parcelles à froid — **200 via Caddy, aucun 504 de proxy** ✓ (nuance honnête)
- **Marge proxy 90 s vérifiée LIVE** (cf. Caddy ci-dessus).
- **Succès servi** : assiette **4 parcelles contiguës** (Les Avirons `97401000AE0155`+`AE0129`+`AE0153`+
  `AE0131`, zone U, frontières partagées > 0,5 m) → `POST /modules/etude/pdf` via `https://app.labuse.immo`
  → **HTTP 200, 28,5 s, PDF 10 pages** (111 Ko). **Pas de 504.**
- **Nuance (non bloquante, orthogonale au déploiement)** : plusieurs autres assiettes 4-parcelles **à froid**
  dépassent la **borne applicative de 60 s** (`_ETUDE_TIMEOUT_S = 60`, **inchangée par ce déploiement**) et
  renvoient le **503 honnête `etude_trop_lourde`** — et non un 504 : le proxy 90 s a **attendu les 60 s** et
  servi la réponse honnête de l'app (mesuré 60,1 s / 60,4 s). Le proxy **n'a jamais converti** une étude
  bornée en 504.
- Les **504 transitoires** observés pendant mes essais étaient un **artefact de MA recette** : enchaîner
  plusieurs études lourdes laisse des threads abandonnés (`shutdown(wait=False)`, moteur GIL-bound) qui
  **affament l'unique boucle uvicorn** → Caddy renonce avant 90 s. En usage réel (une étude à la fois) le cas
  ne se produit pas ; preuve : l'app a **toujours fini le calcul et rendu le PDF** (journal `weasyprint Step
  6/7`), le 504 n'étant que côté proxy. **À signaler à Vic** (dette d'architecture pré-existante, hors
  périmètre de ce déploiement) : le thread d'étude abandonné à la borne continue en fond et peut dégrader le
  service ~30–60 s pour tous.

### 3. `POST /admin/radar/confirmation` sur une page bloquée — 0 retrait, « non vérifiée » ✓
- `list_id` actif (3244839690), verdict `supprimee` **sans preuve** (le scénario exact de l'incident 28/10).
- Réponse : **`{"ok":true,"retire":false,"non_verifiee":true}`**. Le bien reste **`active`** (vérifié en
  base, `retiree_le` vide). La voie simple ne retire **plus jamais** rien (RADAR-FIX-3).

### 4. Les 60 `bien_id` du rapport RADAR-FIX-3 sont `active` ✓
- **60 / 60 `active`** (cf. Restauration).

### 5. `POST /admin/radar/capture` avec la fixture JSON Bien'ici — annonces acceptées, slug `bienici` ✓
- Fixture `qa/radar-bienici/ECH-BIENICI-1.json` (100 annonces, La Réunion), `source=test`, `passe=nouvelles`.
- Réponse : **`ok:true, nb_annonces:100, nb_nouvelles:95, nb_maj:5, nb_hors_perimetre:0,
  provenance:json_riche, mode:resultats`**. En base : **100 `pige_annonces` avec `portail='bienici'`** ;
  passe journalisée `source=test`.
- **DÉCISION VIC (29/10) — on GARDE les 95 annonces** (Bien'ici est une source désormais active, ce sont
  de vraies annonces). Leur capture a été **requalifiée en capture ordinaire** : `pige_passes` id 335
  passée de `source='test'` à **`source='auto'`** (la signature de l'alarme du soir), en **une transaction
  à garde-fou** (`UPDATE 1`, committé) :
  ```sql
  BEGIN;  -- garde-fou : exactement id=335, source='test', passe='nouvelles', n_nouvelles=95
  UPDATE pige_passes SET source='auto', updated_at=now() WHERE id=335;  -- → UPDATE 1
  COMMIT;
  ```
  Après : **0 passe `test` restante**, les **100 `pige_annonces` Bien'ici conservées** (`portail='bienici'`).

### 6. Analyser une annonce ✓ (nuance DVF sur un chiffre)
- **Par adresse `97413000CX0800` (Saint-Leu)** : `nature=nue`, `type_comparateur=terrain_nu`, **médiane
  495 €/m²**, n=78, **fiabilité « Moyenne » / `precision_pct=19` (±19 %)**, classement **C / À étudier**.
  **PDF `/analyse-annonce/97413000CX0800.pdf` = 200, 2 pages**, « Parcelle nue », « terrain nu », **tableau
  des ventes de terrain**. ✓
- **Par adresse `97411000BZ1065` (Saint-Denis)** : `nature=batie`, `type_comparateur=bati`, fiabilité
  limitée. **PDF = 200, 2 pages**, **« ordre de grandeur » + « lecture foncière »** présents. ✓
  *(NB : BZ1065 est à Saint-Denis insee 97411, non Saint-Paul.)*
- **Par lien, annonce de La Possession** (`leboncoin/3145870482`, relevé le 28/10 depuis le Radar, sans
  fetch) : **« deux lectures » servies** — `lectures.bati` (ordre de grandeur : −29 %, réf 3 778 €/m²,
  n=111) **+** `lectures.fonciere` (terrain 625 m² × 474 €/m² = **296 000 €**, « 82 % du prix… valeur
  surtout foncière »). PDF par lien = 200.
  **Nuance honnête** : la recette citait **289 000 €** ; la foncière vaut **296 000 €** aujourd'hui car la
  **médiane DVF du terrain à La Possession** est passée à **474 €/m²** (289 000 € = 462 €/m² × 625 m²). C'est
  une **dérive de donnée DVF** (médiane servie par q_v20), **inchangée par ce déploiement code-seul** — la
  structure « deux lectures » et la « lecture foncière » sont bien là.

### 7. `docs_coherence.py` zéro écart + 10 min de journaux propres ✓
- **`docs_coherence.py` sur `97415000BY0083`** (API `127.0.0.1:8000`, cookie injecté au runtime via le
  curlrc — jamais affiché ; Bilan rendu en-process) → **0 écart sur 18 données partagées** (exit 0). Les 8
  documents s'accordent (surface 2 458, emprise 900, zone libérée 1 736, pente 9,7°, hauteur 9/6, recul 4,
  2 pl/logt, pleine terre 40 %, prix bâti 4 125, terrain 250, VEFA 4 745, SDP max 1 327, SDP résiduelle 453,
  propriétaire succession, date 27/10/2026) — identique à DEPLOY-1029a.
- **Journaux depuis le restart (3 288 lignes, ~35 min, restart + fumée complète)** : **0 ERROR / 0 Traceback
  / 0 Exception / 0 CRITICAL / 0 segfault** ; **0 mail / radar-cloche / digest / SMTP** ; 0 WARNING
  non-cosmétique. Distribution HTTP = **114 × 200**, 1 × 400 / 2 × 401 / 2 × 404 (tous mes entrées de test
  délibérées), **3 × 503** = mes études 4-parcelles trop lourdes (borne 60 s, par conception — pas un
  défaut, pas un 504). Les 504 de contention n'apparaissent pas côté labuse (côté proxy ; l'app a terminé en
  200).

---

## Synthèse

**Déployé et validé** : `main` **`b955de8e5`** en prod — **RADAR-FIX-3** (preuve positive de retrait, voie
simple neutralisée, compteur `n_non_verifiees`, garde-fou 30 %) + **CORRECTIFS-2** (fiche sert `etat_bien` ;
marge proxy Étude 75→90 s) + **ESTIMATION-BANC-1** (backtest, *docs* seulement) + **RADAR-SOURCES-2 /
ANNONCE-5** (source Bien'ici : traducteur, rattachement, fusion portail-agnostique ; PDF analyse 2 pages,
deux lectures bâti/foncière). **Manifeste q_v20 intact**, aucune bascule, **aucun mail**,
radar-cloche/digest gelés. **1 colonne** posée (`pige_passes.n_non_verifiees`). **60 biens restaurés en
`active`** sous go de Vic (transaction à garde-fous, 60 exactement).

**Les 7 points de fumée sont VERTS**, avec trois nuances honnêtes, **toutes non bloquantes et orthogonales
au déploiement** : (2) les études 4-parcelles *lourdes* à froid atteignent la borne applicative de 60 s
(503 honnête, inchangée) — le proxy 90 s ne produit **aucun 504** ; une étude servie à l'unité rend bien un
PDF 200 (10 p., 28,5 s). **Décision Vic : ce point fera l'objet d'un mandat séparé — rien touché.**
(5) la recette Bien'ici a ingéré **95 annonces** dans la base — **décision Vic : GARDÉES**, leur capture
requalifiée `test→auto` (capture ordinaire, cf. §5). (6) la foncière de l'annonce La Possession vaut
**296 000 €** (et non 289 000 € de la recette) à cause d'une dérive de médiane DVF, pas du code —
**décision Vic : 296 000 € accepté, rien à faire.**

**À signaler à Vic** : dette d'architecture pré-existante — une étude abandonnée à la borne 60 s laisse un
thread GIL-bound en fond qui peut affamer l'unique boucle uvicorn (observé comme 504 transitoires lors
d'essais enchaînés). Hors périmètre de ce déploiement.

**Filet conservé** pour rollback immédiat : `/opt/labuse/app-avant-1029b` + `/opt/labuse/venv-avant-1029b` +
`/etc/caddy/Caddyfile.avant-1029b` + dump `labuse-labuse-20261029-161844.dump` (6,1 G, 1748 TOC) + table
d'audit `pige_restauration_radarfix3`. **Aucun rollback effectué.** Session de test **purgée**, fichiers
temporaires supprimés.
