# DEPLOY-1029a — mise en prod de `main` (`9dd75d2ab`) : ANNONCE-2 + ANNONCE-3

Lancé le 29/10/2026 depuis `~/Desktop/labuse-main`, prod `labuse-vps` (`https://app.labuse.immo`).
Périmètre : faire avancer la prod de `4c38f525c` (DEPLOY-1028d) à **`9dd75d2ab`** (« Merge branch
'feat/annonce-3' »), soit le delta **ANNONCE-2 + ANNONCE-3** (+ 2 rapports d'audit *docs* et le rapport
1028d). **Déploiement code-seul** : manifeste et données non touchés, aucun mail, aucune bascule.
Mêmes règles que `reports/DEPLOY-1028d.md` / `1028b.md`.

> ⚠ **DÉCALAGE HORAIRE — go explicite de Vic.** Les étapes 0 + pré-vol ont été jouées vers **03 h 01–
> 03 h 22 Réunion** (tout vert). La session est ensuite restée en veille plusieurs heures ; au moment de
> reprendre il était **12 h 08 Réunion**, **bien au-delà** du garde-fou (déploiement à terminer avant
> 05 h 30 / 06 h 03). **Arrêt automatique** conformément à la runbook, puis **go explicite de Vic** pour
> déployer en pleine journée en assumant le risque diurne (utilisateurs actifs possibles, 503 transitoire
> au restart). Le nouvel ordre `deploy_app.sh` (restart → readyz 25/25 stable → réchauffage) est
> précisément conçu pour éviter le 503 ; le résultat l'a confirmé (0 × 503 servi, cf. Déploiement).

---

## Étape 0 — garde-fou horaire + VACUUM

- **03 h 01 Réunion** (`TZ=Indian/Reunion`, UTC 23:01) au premier relevé : **< 05 h 30 → feu vert à ce
  moment**. (Un `date` de login affichait une TZ trompeuse ; l'heure autoritative `TZ=Indian/Reunion` et
  le mtime des dumps concordent.)
- **Aucun VACUUM** en cours (`pg_stat_activity` : 0 autovacuum worker, 0 `VACUUM` manuel hors requête
  auto-référente ; le VACUUM FULL nocturne de MENAGE-1 était déjà terminé).
- **Reprise à 12 h 08 Réunion** → garde-fou franchi → STOP automatique → **go explicite de Vic** (cf.
  encadré). Au moment du déploiement effectif : **12 h 24**, **aucun VACUUM**, readyz 200.

---

## Pré-vol

- **Cible strictement en avance, sans divergence** : `4c38f525c` est un **ancêtre** de `9dd75d2ab`
  (14 commits d'écart, `git merge-base --is-ancestor` = vrai). `9dd75d2ab` **== origin/main** (0 commit
  d'avance de main sur la cible, re-vérifié après `git fetch` à la reprise).
- **Prod réelle avant** : `config/deploiement.json` = `4c38f525cd18386b…`, `par=deploy_app.sh`,
  déployé 2026-10-28T20:03:46Z — conforme à l'attendu.
- **Aucune session concurrente** : `sessions_auth` actives = **0** (0 utilisateur), 0 requête
  applicative en vol — re-vérifié à la reprise (jour).
- **Manifeste servi** : `scoring=q_v20 · cascade=q_v19_sources · mvt=q_v20 · division=q_v19 ·
  residuel_seq=17` — **doit rester intact** (aucune bascule).
- **Notifications Radar gelées** : `radar-cloche` (07:05) et `digest` (07:15) **commentés « GELÉ
  (notifications OFF, LABUSE_RADAR_NOTIFS=off) »** dans `/etc/cron.d/labuse` ; défaut code = OFF
  (`jobs._gel_notifs` : actif seulement si `radar_notifs=="on"`, non positionné en prod). → **aucun mail
  possible au restart**. (Les crons `radar-cycle`/`-dvf` actifs sont du cycle de vie de données, sans
  mail.)
- **Disque** : 34 G libres / 66 %.

### Sauvegarde vérifiée (`pg_restore --list`)
- `deploy/scripts/backup_postgres.sh` → **`labuse-labuse-20261029-030308.dump` (6,1 G)**, contrôle
  intégré **« ✓ Sauvegarde OK (6.1G) »** + contrôle **explicite** `pg_restore --list` = **1748 entrées
  TOC**. Captures Radar archivées (1,4 M). ✓

### Filet (`cp -al`, hardlinks ≈ 0 octet)
- Code : `/opt/labuse/app` → **`/opt/labuse/app-avant-1029a`** (même inode vérifié).
- venv : `/opt/labuse/venv` → **`/opt/labuse/venv-avant-1029a`**.

### Phase R — retour arrière (prêt, conservé)
```bash
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app  && sudo mv /opt/labuse/app-avant-1029a  /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-1029a /opt/labuse/venv
sudo chown -R labuse:labuse /opt/labuse/app
sudo systemctl start labuse && curl -fsS http://127.0.0.1:8000/readyz
# Manifeste/config/crontab NON touchés → rien à restaurer côté config.
# DB : restaurer labuse-labuse-20261029-030308.dump UNIQUEMENT si l'ancien code ne fonctionne plus.
```

---

## Déploiement — `VITE_RUN_LABEL=q_v20 deploy/scripts/deploy_app.sh labuse-vps`

Arbre local propre sur la cible (`logs/` non suivi mis de côté pour ne pas l'expédier). Déroulé **exit 0**,
dans le nouvel ordre REMISE-1 Lot A :

```
── garde manifeste : run local 'q_v20' présent en prod (433229 lignes score_labuse) ✓
── 1. rsync (manifeste/données/docs exclus)   ── 2. venv + chaîne de démarrage importable ✓
── 3. front (vite build --base=/, q_v20)      ── 4. systemd
── 4b. crontab reposé + vérifié : ✓ == registre (aucun écart, tz=reunion)   ← radar mail restent gelés
── 4c. deploiement.json = 9dd75d2abd64 (déployé 2026-10-29T08:25:17Z)
── 5. manifeste prod : 'q_v20' (433229 lignes) ✓
── 6. restart → /readyz 200 STABLE (25/25 consécutifs, 37 essais) ✓ → job fiche-commune-cache (détaché)
✓ déployé — service redémarré, /readyz 200 stable, caches en réchauffage.
```

- **SHA prod déployé = `9dd75d2abd6418fb…`** (la cible). Code = 16 fichiers hors docs (+1257/−75).
- **Manifeste INCHANGÉ** : `served_run` = **q_v20** (manifeste exclu du rsync).
- **Crontab** reposé depuis le registre et **vérifié == registre** (radar-cloche/digest restent gelés).
- **Aucun 503 servi au démarrage.** Le « 37 essais pour 25 consécutifs » = le **trou de connexion**
  pendant le reboot des workers (connection-refused tant que le service n'écoute pas), **pas** des 503
  HTTP : le journal depuis le restart compte **0 × 503**. Le gate a attendu la convergence du heal
  (résilient `lock_timeout` + réessais) avant de lancer le réchauffage → pas de contention, pas de flap.
- **Réchauffage** (REMISE-1) : job `fiche-commune-cache` relancé **après** readyz stable → **statut `ok`,
  769,2 s**, 0 erreur. Caches **frais** : `comparateur_raw_cache` 5 (empreinte, doctor « VITESSE-2 :
  frais »), `commune_contexte_cache` 24 communes, `fiche_cache` ré-amorcé.
- readyz **local 200 + Caddy 200**.

---

## Fumée — méthode 1028b (session de test éphémère, jeton jamais affiché)

Compte `gb-test-ae@labuse.local` = **utilisateur id 31, admin**. Session serveur **3 h** via
`comptes.creer_session(db, 31, 3)` ; jeton écrit dans un **curlrc `600`** (`/tmp/.gb1029a.curlrc`, labuse)
lu par `curl -K`, **jamais imprimé**. Vérifié : `/version` **401 sans cookie / 200 avec**, `/moi` **200**,
**1 seule** session active uid 31. **Purgée en fin de run** (`DELETE … utilisateur_id=31` → 1 supprimée,
**0 active restante**).

### 1. readyz 25/25 + fiche BY0083 ✓
- `/readyz` (Caddy) : **25/25 = 200**.
- `GET /parcels/97415000BY0083` → **200, 0,12 s**, payload **77 clés**, commune Saint-Paul, **aucune**
  clé erreur.

### 2. Analyser une annonce **par adresse** — nue puis bâtie ✓
- **CX0800 = `97413000CX0800` (Saint-Leu)** — `GET /radar/annonce/estimation/97413000CX0800` :
  `nature="nue"`, `type_comparateur="terrain_nu"`, **médiane 495 €/m²**, **n = 78** (ventes de terrain),
  période 2021–2025, périmètre secteur, fiabilité fiable. **Exactement l'attendu : « Parcelle nue »,
  ≈ 495 €/m², 78 ventes de terrain.** Rapport parcelle `GET /parcels/97413000CX0800` **200** ;
  classement `GET /radar/annonce/classement/97413000CX0800` → **« C · À étudier »**.
- **Parcelle bâtie `97416000CX0800` (Saint-Pierre)** — estimation : `nature="batie"`,
  **`type_comparateur="bati"`**, médiane 3 108 €/m² (q1 2 636 / q3 3 487), n = 41, type « appartement »,
  rayon 500 m, période 2022–2025. → **comparateur bâti** bien servi.

### 3. Analyser une annonce **par lien** présent au Radar — « relevée le » = date de capture ✓
- `POST /radar/annonce/analyser` sur
  `https://www.leboncoin.fr/ad/ventes_immobilieres/3145870482` (list_id présent au Radar) →
  **`ok=true`**, commune **La Possession**, **`releve_le = "2026-10-28"`**.
- Capture correspondante en base : `pige_annonces.date_saisie` = **2026-10-28 23:03 (Réunion)** →
  **date 2026-10-28**. **La date « relevée le » == la date de capture** (lecture **Radar d'abord**, sans
  fetch, conforme ANNONCE-2).

### 4. Export PDF — outil == Docs, 1 page, parcelle entière ✓
Le code confirme que l'**outil** (`AnalyserAnnonce.tsx`) et **Docs** (`DocumentsView.tsx`) appellent les
**mêmes routes** (`/analyse-annonce/{idu}.pdf` par adresse, `/analyse-annonce.pdf?url=…` par lien).
Empiriquement, sur `https://app.labuse.immo` :

| PDF | HTTP | Pages | outil vs Docs (pdftotext) |
|---|---|---|---|
| `/analyse-annonce/97413000CX0800.pdf` (adresse) | 200 | **1** | **texte IDENTIQUE** |
| `/analyse-annonce.pdf?url=…3145870482` (lien/annonce) | 200 | **1** | **texte IDENTIQUE** |

- Le seul écart outil/Docs est l'horodatage interne WeasyPrint (quelques octets) ; **le texte est
  identique**.
- **PDF == écran, chiffre pour chiffre** : le PDF CX0800 porte « Saint-Leu · 97413000CX0800 ·
  29/10/2026 », **495 €/m²**, **Ventes de terrain 78**, « Parcelle nue — comparée aux ventes de terrain
  nu », badge **C · À étudier** — mêmes valeurs que l'estimation servie.
- **Parcelle entière sur le plan** : rendu PNG du PDF inspecté → le plan aérien montre la parcelle
  **entièrement cadrée avec marge** (conforme ANNONCE-3-FIX-3).

### 5. `docs_coherence.py` — zéro écart ✓
Exécuté **en prod** contre `127.0.0.1:8000` (cookie de la session **injecté au runtime via le curlrc,
jamais affiché** ; Bilan rendu en-process) sur `97415000BY0083` → **0 écart sur 18 données partagées**
(exit 0). Les 8 documents s'accordent (surface 2 458, emprise 900, zone libérée 1 736, pente 9,7°,
hauteur 9/6, recul 4, 2 pl/logt, pleine terre 40 %, prix bâti 4 125, terrain 250, VEFA 4 745, SDP max
1 327, SDP résiduelle 453, propriétaire succession, date 27/10/2026) — identique à DEPLOY-1028d.

### 6. 10 minutes de journaux propres ✓
Fenêtre `journalctl -u labuse` **12:25:18 → 12:39:44 Réunion** (**14 min 26 s**, 2 853 lignes, couvrant
tout le restart + la fumée + 9 sondes réparties) :
- **0 ERROR / 0 Traceback / 0 Exception / 0 CRITICAL**.
- **0 code 5xx** ; readyz **0 × 503**. Distribution HTTP = **120 × 200 + 1 × 401** (le 401 = mon test
  « sans cookie » délibéré).
- **0** mail / radar-cloche / digest / SMTP dans la fenêtre (notifications restent coupées).
- WARNINGs présents mais **tous cosmétiques de génération PDF** : weasyprint (fontTools/HarfBuzz,
  sélecteurs `::note-*`, « anchor defined twice ») + **1** `pypdf._writer — No fields to update on this
  page` — bénins, pré-existants.

---

## Synthèse

**Déployé et validé** : `main` **`9dd75d2ab`** en prod — **ANNONCE-2** (l'entrée LIEN lit le Radar
d'abord, fetch en repli ; garde légal §2 par exceptions ligne-par-ligne) + **ANNONCE-3** (export PDF de
l'outil « Analyser une annonce » + 9ᵉ document Docs « Analyse d'annonce », + FIX 1-3 : plan 1 page
centré, estimation selon la nature, parcelle entière). **Code-seul** : manifeste **q_v20** intact, aucune
bascule, aucune migration, **aucun mail**, radar-cloche/digest gelés. **Les 6 points de fumée sont
VERTS.**

**Nuance honnête, non bloquante :** le déploiement a eu lieu **en pleine journée (12 h 24 Réunion)**,
**hors de la fenêtre nocturne** du garde-fou, sur **go explicite de Vic** (la session était restée en
veille au-delà de 05 h 30). Le risque diurne ne s'est **pas matérialisé** : 0 session concurrente au
moment du restart, **0 × 503 servi**, 0 erreur, réchauffage `ok`.

**Filet conservé** pour rollback immédiat : `/opt/labuse/app-avant-1029a` + `/opt/labuse/venv-avant-1029a`
+ dump `labuse-labuse-20261029-030308.dump` (6,1 G, `pg_restore --list` 1748 TOC). **Aucun rollback
effectué.** Session de test **purgée**, fichiers temporaires supprimés.
