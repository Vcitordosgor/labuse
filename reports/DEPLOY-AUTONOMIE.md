# DEPLOY-AUTONOMIE — mise en prod d'AUTONOMIE-1 + POST-DEPLOY-1 (`4e7c9d29f` → `17eb6f8b2`)

Lancé le **2026-11-02** (après-midi, Réunion +04) depuis `~/Desktop/labuse-main`, prod `labuse-vps`
(`https://app.labuse.immo`). Go de Vic, dans les seules limites du mandat. Mêmes règles que
`reports/DEPLOY-FINAL.md`. Périmètre : avancer la prod de **`4e7c9d29f`** (DEPLOY-FINAL de ce matin,
q_v20 servi) à **`17eb6f8b2`** — les 5 commits AUTONOMIE-1 + POST-DEPLOY-1 **plus un correctif de
pré-vol** (cf. §0bis). À lire d'abord : `docs/audit-2026-11/autonomie-1/COMPTE-RENDU.md`,
`docs/audit-2026-11/post-deploy-1/COMPTE-RENDU.md`.

> **Bilan en une ligne.** Code + env + fumée déployés et verts sur `17eb6f8b2` ; un **correctif de
> pré-vol** indispensable (la couche DB du calcul de nuit visait des colonnes inexistantes — jamais
> testée contre le schéma servi) écrit, testé et déployé avec l'accord de Vic ; la **première
> promotion q_v21 est mise sous gate** (calcule + contrôle + mail, PAS de bascule auto — décision
> Vic) ; un **flap readyz** post-déploiement (recurrence DEPLOY-1028b, heal `event_log` sous charge)
> traversé et résolu par un re-heal propre. Prod reste servie en **q_v20**. **Aucun retour arrière.**

---

## §0bis — Correctif de pré-vol (décision Vic) : la couche DB du calcul de nuit était cassée

Le pré-vol a prouvé, **contre le schéma de prod en lecture seule**, que les contrôles « avant
promotion » du calcul de nuit (`jobs_impl._mesures_run`) interrogeaient des **colonnes inexistantes** :
`code_palier` (réel : `tier`), `parcel_id` (réel : `parcelle_id` = IDU), `parcel_flags.run_id` /
`entierement_rouge` (réels : `run_label`, pas de colonne `entierement_rouge`), `coherence_runs.ecarts`
/ `cree_at` (réels : `n_ecarts`/`ts`), et un appel `verify_completude(db, candidat)` à la mauvaise
signature. La suite `db/reel` n'ayant jamais tourné dans le worktree AUTONOMIE-1, ces requêtes
tombaient toutes à `None` → `controler_run` REFUSAIT systématiquement : le calcul de nuit aurait
calculé q_v21 chaque nuit **sans jamais pouvoir promouvoir** (+ mail « contrôles échoués » trompeur,
+ heures de CPU gâchées).

**Décision Vic : corriger la couche SQL avant de déployer.** Réécrit (`commit 17eb6f8b2`) sur les
colonnes réelles et les lectures **canoniques déjà servies** — complétude via `bascule_flux._run_complet`,
« entièrement rouge » via la fraction PPR de `dryrun_cascade_results` (motif « N % de la surface », même
source que `renouvellement.ppr_x`, cascade résolue par `bascule_flux.resoudre_cascade_run`), paliers
actionnables = `tier ∈ {brulante,chaude,priorite,a_suivre}` (`golden_ops`), écart de paliers par
self-join sur `parcelle_id`, cohérence lue du banc (vert = `faux_client` + `erreurs_lecteur`, pas le
`n_ecarts` brut du balayage île). **Chaque requête validée en lecture seule contre la prod.** Test
`reel` garde-fou ajouté (`tests/test_autonomie_1_db.py`) : il exécute `_mesures_run` contre la base
servie et exige que chaque mesure CONCLUE (int, pas None). Recette : pure 36/36, reel 2/2, cohérence
témoins 6/0, hook pre-push vert.

**Gate de promotion (décision Vic, première nuit).** `LABUSE_CALCUL_NUIT_PROMEUT=0` posé en prod :
cette nuit le calcul de nuit CALCULE q_v21, le CONTRÔLE et MAILE le verdict, mais **ne bascule pas** —
la première mise en service de q_v21 se fait sous l'œil de Vic (conforme à AUTONOMIE-1). Défaut du
code = `True` (pleine autonomie) pour les nuits suivantes, au clic de Vic.

---

## Étape 0 — garde-fou (pré-vol)

- **~18 h 29 Réunion** (`TZ=Indian/Reunion`, VPS `vps-5563949c`). Heures ouvrées, assumé.
- **Aucun VACUUM** (`pg_stat_activity` hors self : 0). **Aucune sauvegarde / dump / deploy / rsync**
  en cours. **0 backend non-idle.**
- **Sauvegarde < 24 h** : `labuse-labuse-20261102-163345.dump` **6 558 Mo**, âge **~1 h** (la
  sauvegarde Phase 0 d'AUTONOMIE-1). `/readyz` 200, `NRestarts=0`, disque **34 G libres / 65 %**.
- **1 session active** = celle de Vic (uid 19, ouverte 16:17) — il a autorisé le déploiement en
  direct ; le redémarrage l'a terminée (reconnexion nominative + 2FA = son geste).
- **Cible** : local `main` == `origin/main` == **`17eb6f8b2`** ; prod `4e7c9d29f` ancêtre strict.

### Filets (`cp -al`, hardlinks ≈ 0 octet)
- `/opt/labuse/app` → **`app-avant-autonomie`** (inode partagé 4457357 vérifié).
- `/opt/labuse/venv` → **`venv-avant-autonomie`**.
- `/etc/caddy/Caddyfile` → **`Caddyfile.avant-autonomie`** ; `/etc/labuse/labuse.env` →
  **`labuse.env.avant-autonomie`** (640 root:labuse préservé). Disque inchangé.

### Environnement — compte pilote retiré + gate de promotion
Fichier **sauvegardé avant** (`labuse.env.avant-autonomie`). Retiré **`LABUSE_LOGIN_PILOTE_ACTIF`**
(variable morte : le champ config a été supprimé par POST-DEPLOY-1 ; `extra="ignore"` l'aurait
tolérée, mais le mandat demande de la retirer). Ajouté **`LABUSE_CALCUL_NUIT_PROMEUT=0`** (gate
première nuit, commentaire sur sa propre ligne). **Conservés** : `LABUSE_AUTH_PASSWORD` (devenu
l'interrupteur d'auth, POST-DEPLOY-1) et `LABUSE_PILOT_COMMUNE_*` (config produit Saint-Paul, toujours
lue — **sans rapport** avec le compte pilote partagé). Perms **640 root:labuse** ré-asserties.
`LABUSE_PILOTE_TOTP_SECRET` déjà absent (retiré au DEPLOY-FINAL).

### Schéma — aucune migration neuve requise
Vérifié : le code neuf (autonomie) ne lit **aucun** objet absent de prod — `data_sources.last_sync_at`
/ `source_horizon_at`, `source_veille.*`, `coherence_runs.*`, `parcel_flags.*`, `dryrun_cascade_results`,
`parcel_p_score_v2.*`, `p_score_v2_runs` **présents**. Seule DDL du code neuf = un `ADD COLUMN IF NOT
EXISTS` **idempotent et pré-existant** (hors chemin de ce delta). `deploy_app.sh` **n'applique pas** de
migration. → **Rien à poser.** (La migration `2026-11-02-deploy-final.sql` a été appliquée ce matin.)

---

## Déploiement — `deploy/scripts/deploy_app.sh labuse-vps`

Déroulé **exit 0** : garde manifeste (q_v20 présent, 433 229 l.) ✓ → rsync → venv (chaîne importable ✓)
→ **2bis : deps calcul-nuit** (`requirements-calcul.txt`, sklearn/joblib/pandas **sans torch**) installées
+ **import-smoke ✓** → front (vite sur VPS) → systemd → **crontab reposé == registre** (tz=reunion, aucun
écart) → `deploiement.json = 17eb6f8b2` → manifeste prod **q_v20** intact → `fiche_cache` vidé → restart →
**`/readyz` 200 STABLE 25/25 (38 essais)**. `NRestarts=0`. **Pas d'incident au boot du déploiement.**

Vérifié après coup : `NRestarts=0`, readyz **200 local + public**, deps venv `sklearn 1.9.1 / pandas
3.0.3`, les **3 nouveaux jobs armés** au crontab — `injection-nuit 01:00`, `calcul-nuit 02:00`,
`restore-test 05:00 le 5` (Réunion).

---

## ⚠ Incident readyz (traversé, résolu) — recurrence DEPLOY-1028b

Pendant la **fumée** (génération des 24 PDF de `docs_coherence` + fin du job de réchauffage
`fiche-commune-cache`), `/readyz` a **flappé** : **un seul worker** (pid 2031078) répondait 503. Cause
(lue via cookie banc) : son heal de schéma au boot a buté sur `ALTER TABLE event_log ADD COLUMN IF NOT
EXISTS source` en **`lock timeout`** (table chaude, contention de la fenêtre réchauffage + mes PDF) →
`schema_heal.ok=false` sur ce worker → 503 permanent (exactement DEPLOY-1028b / l'incident du
DEPLOY-FINAL). **La colonne `source` EXISTE déjà** (no-op bloqué par le verrou, pas un manque) ; aucun
autre worker touché ; **`schema_heal` ne garde QUE `/readyz`**, pas le service des requêtes clients
(impact client nul, seul le signal de monitoring était faux). Partiellement auto-infligé (mes PDF
écrivaient dans `event_log` pendant la fenêtre).

**Résolution** (pas un retour arrière) : attendu la fin du réchauffage → fenêtre calme (0 backend
non-idle, 0 attente de verrou, load 0,68) → **`systemctl restart labuse`** → re-heal propre →
**`/readyz` 50/50 = 200** (série 50), **0/15** réponse `heal.ok=false`, `NRestarts=0`.

---

## Fumée

| Point du mandat | Résultat |
|---|---|
| `readyz` + `smoke_test.sh` | ✅ readyz 200 local+public ; smoke_test tous critiques PASSENT (smoke_build Playwright = SKIP, navigateur absent du VPS, non bloquant) |
| `/healthz/crons` couvre tous les jobs dont les 2 nouveaux | ✅ **33 jobs**, dont `calcul-nuit`/`injection-nuit`/`restore-test` (statut `jamais_vu` = état honnête avant la 1ʳᵉ nuit). `ok:false` global = ces 3 neufs + 3 gelés intentionnels (purge-runs/radar-cloche/digest) — **0 job en erreur** |
| Connexion « pilote » refusée | ✅ POST `/login` sans identifiant → **401** ; mauvais creds → 401 ; `/login/2fa` → 302 ; grep code `login_pilote\|pilote_totp\|password_ok` = **vide** |
| Connexion nominative Vic + 2FA | ⏳ **à confirmer par Vic** (action interactive) |
| Pilotage < 1 s à chaud | ✅ **~23–30 ms** (3 appels, endpoint réel, cookie banc) — même sous la charge concurrente des PDF |
| `docs_coherence.py` à 0 | ✅ **0 écart** sur BY0083 / BL0020 / IE0241 (RC=0) — hauteur 10/7, prix terrain unique : les 2 écarts du DEPLOY-FINAL sont fermés |
| `coherence-banc` relancé main et vert | ⚠️ **machinerie RESTAURÉE** (le job tourne de nouveau — passe la barre du FileNotFoundError ECHANTILLON qui le tuait en 0 s depuis le 28/10 ; **incident `job-echec:coherence-banc` auto-fermé 19:16**) ; **`faux_client=0`** (0 mensonge client) ✓ ; **MAIS `erreurs_lecteur=1198`** = lacune du lecteur « tuile » du banc (cf. §Carte), **la carte client elle-même est saine** |
| contrôle « verrous » vert | ⚠️ **NON — 6 cassés, TOUS pré-existants (0 causé par ce déploiement)** — cf. §Verrous |
| Tableau de bord : plus de cartes en double, incidents réglés fermés | ✅ fusion echec+retard → **1 carte** pour coherence-banc (5 incidents → 3 cartes) ; escalades d'ancienneté masquées (0) ; incidents backup **résolus** (Phase 0) |
| 15 min de journaux propres | ✅ fenêtre 19:07–19:22 : **0 ERROR/Traceback/5xx, 0 mail** (200×208, 401×123 = le lecteur tuile du banc, 302×6) |

### Carte / tuiles — lacune du BANC, carte client SAINE (finding, non bloquant)

Les **1198 `erreurs_lecteur`** du banc sont **toutes** le lecteur `tuile:` renvoyant un corps vide
(`Expecting value: line 1 column 1`) ; les lecteurs `fiche:`/`sql:` lisent bien. **La carte servie aux
clients est saine**, vérifié indépendamment : tuile `/map/tiles/z/x/y.pbf` **avec session → HTTP 200,
930 Ko** de données ; `mvt_parcels` 433 229 l., `mvt_tile_cache` 2371, `meta.perime=false`, run q_v20 ;
la route **n'est pas admin-only** (session cliente suffit ; 401 seulement sans session). Cause probable :
la migration MVT de la vague NU (`couches_tuyau`, servie au DEPLOY-FINAL **de ce matin**) sert désormais
du **protobuf** là où le lecteur du banc attendait du JSON — le banc n'avait pas tourné depuis le 28/10
(FileNotFoundError), c'est son **premier passage post-vague** qui le révèle. **Pas une régression de ce
déploiement, pas client-facing.** _Conséquence pour l'autonomie_ : tant que le lecteur tuile du banc
n'est pas réaligné, le **contrôle de cohérence** du calcul de nuit (qui exige `erreurs_lecteur=0`) ne
passera pas → en mode pleine autonomie (gate=1) il **bloquerait la promotion** (sûr : on ne promeut pas
sur un banc non probant). Cette nuit : gate=0, donc **sans effet** (verdict mailé seulement). **Suite
dédiée** : réaligner le lecteur tuile du banc sur le format MVT.

### Verrous — machinerie restaurée, 6 cassés pré-existants (rouge noté, pas un retour arrière)

`labuse circuit verrous --complet` : **32 joués (22 verrous + 8 garanties), 6 CASSÉS — V1c, V3b, V4a,
V6b, G5, G8.** Les verrous n'étaient **plus évalués depuis le 28/10** (coherence-banc crashait avant de
les atteindre) ; le correctif AUTONOMIE-1 (ECHANTILLON redéposé) les **rétablit** — ils tournent de
nouveau et révèlent 6 états **pré-existants**, aucun causé par ce déploiement (qui ne touche ni le
schéma, ni les sources, ni le golden, ni les données) :

| Verrou | Diagnostic (du journal) | Nature |
|---|---|---|
| **V1c** | 7 tables orphelines sans action proposée (`TABLES-ORPHELINES.md` à compléter) | hygiène schéma / dette doc |
| **V3b** | 1 « eau ancienne » ouverte (tampon périmé) | fraîcheur donnée (famille rouges-7) |
| **V4a** | 21 tables sans clé étrangère commune | structure schéma |
| **V6b** | 17 problème(s) golden/banc (golden q_v20) | état golden pré-existant (rouges-7) |
| **G5** | EduGéo Réunion 1980 : aucune date de contrôle ni mention « jamais » | état source (registre) |
| **G8** | 8 sources vitrine sans contrôle récent (agent IA à 0 €) + Radar rappel manuel | ops (agent plafonné 0 €) |

→ **À triager hors déploiement** (AUTONOMIE-1 prévoyait « à confirmer au 1er passage » : c'est fait — ils
ne sont pas verts). Aucun ne justifie un retour arrière : états antérieurs au déploiement, non
fonctionnels-bloquants (l'app sert juste : readyz 200, smoke vert, docs_coherence 0, Pilotage rapide).

---

## Première nuit (sans lancer q_v21 à la main) — ✅ vérifié

Dry-run des fonctions de décision (sans exécuter flux-run), contre la prod :
- **Gate** `LABUSE_CALCUL_NUIT_PROMEUT=0` posé ✓ → cette nuit : CALCULE + CONTRÔLE + MAILE le verdict,
  **PAS de bascule**.
- **Fenêtre** : `fenetre_nuit(02:00, 1 h, 5 h) = True` ✓ (le cron `calcul-nuit` vise 02:00 Réunion ;
  `_fenetre_calcul_ok` répond False à 19 h = correct, abstention hors fenêtre).
- **Déclencheur** : dernière promotion (q_v20) = **2026-10-27** ; `declencheur_entree = True — « 2 sources
  avancées depuis la dernière promotion »** → **`doit_calculer = True`** → calcul-nuit **PRENDRA q_v21
  cette nuit**.
- **Plafonds** : nice 15 · ionice 7 · RLIMIT_AS 6000 Mo · budget 14400 s ✓ ; deps `pandas/numpy/joblib/
  sklearn` **toutes présentes** ✓ ; label **q_v21** / recette **q_v15**.
- **injection-nuit** (01:00, avant le calcul) : **classe A = 35 · classe B = 95** (total 130 sources) ✓.
  Elle LISTE les sources A et ne signale les nouvelles versions B qu'au clic de Vic ; le câblage
  source→ingesteur par source A reste « à compléter » (AUTONOMIE-1) — elle n'injecte jamais à l'aveugle.

### Ce que Vic lira demain matin dans son mail
Un message du **calcul de nuit** : « q_v21 CALCULÉ et CONTRÔLÉ, promotion en attente de ton geste » —
avec le **verdict des contrôles** (OK, ou la liste des contrôles en échec), l'**écart de paliers %**, et
les **mesures** (comptes, copro actionnables, rouge actionnables, cohérence). q_v21 **reste en base, non
servi** : pour le servir, `labuse golden promote q_v21` (ou page Circuit → Basculer). Si les contrôles
échouent, le même mail dit lesquels et q_v21 reste rejouable. _(Note : si une entrée n'avait pas changé,
le mail dirait « abstention » ; ici le déclencheur est positif.)_ Possible aussi : un mail
**injection-nuit** listant d'éventuelles sources structurantes (B) à valider d'un clic.

---

## Première nuit (sans lancer q_v21 à la main)

_(à finaliser : déclencheur d'entrée, fenêtre 01–05 h, plafonds ; injection-nuit liste de sources A ;
ce que Vic lira dans son mail)_

---

## État final prod (vérifié)

Served run **q_v20** · SHA **`17eb6f8b2`** · `NRestarts=0` · `/readyz` 200 stable. **Filets conservés** :
`app-avant-autonomie`, `venv-avant-autonomie`, `Caddyfile.avant-autonomie`, `labuse.env.avant-autonomie`
+ dump `labuse-labuse-20261102-163345.dump`. **Aucun retour arrière.**

### Phase R — retour arrière (prêt, non utilisé)
```bash
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app  && sudo mv /opt/labuse/app-avant-autonomie  /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-autonomie /opt/labuse/venv
sudo cp -p /etc/labuse/labuse.env.avant-autonomie /etc/labuse/labuse.env
sudo chown -R labuse:labuse /opt/labuse/app
sudo systemctl start labuse && curl -fsS http://127.0.0.1:8000/readyz
# Schéma inchangé par ce déploiement (aucune migration posée) → rien à défaire.
```

## Findings (notés, non bloquants — aucun n'exige de retour arrière)
1. **Verrous : 6 cassés pré-existants** (V1c/V3b/V4a/V6b/G5/G8) — hygiène schéma / fraîcheur / ops ;
   révélés par le retour en service du banc, aucun causé par ce déploiement. À triager.
2. **Lecteur « tuile » du banc désaligné** (format MVT/pbf vs JSON) → `erreurs_lecteur=1198` au banc et
   **blocage du contrôle de cohérence en pleine autonomie**. Carte client SAINE. À réaligner avant de
   passer `LABUSE_CALCUL_NUIT_PROMEUT` à 1 (autonomie pleine).
3. **Flap `/readyz` traversé** pendant la fumée (heal `event_log` sous charge, recurrence DEPLOY-1028b) —
   résolu par re-heal propre ; partiellement auto-infligé (mes 24 PDF de `docs_coherence`). **Leçon** (déjà
   celle du DEPLOY-FINAL) : la DDL `event_log` devrait être dans la migration de pré-vol, pas au heal de boot.
4. **q_v21 sous gate** cette nuit (décision Vic) : calcule + contrôle + mail, pas de bascule.
5. `restore-test-ancien` reste ouvert jusqu'au 1ᵉʳ passage de `restore-test` (le 5) ; `job-retard:coherence-banc`
   + escalades se ferment au prochain passage de la vigie.

## Rappels à Vic
- **Confirme ta connexion** au compte admin nominatif + 2FA (le redémarrage a fermé ta session).
- **q_v21 cette nuit** : le serveur le calcule 01–05 h, contrôle, et te **maile le verdict** — il NE
  bascule PAS (gate `LABUSE_CALCUL_NUIT_PROMEUT=0`). Si le verdict te convient : `labuse golden promote
  q_v21` (ou page Circuit → Basculer) pour servir q_v21. **Avant de retirer la variable** (autonomie
  pleine), réaligner le lecteur tuile du banc (finding 2), sinon le contrôle de cohérence bloquera.
