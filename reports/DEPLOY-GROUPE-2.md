# DEPLOY-GROUPE-2 — déploiement des 4 chantiers du week-end + dette ops

Mandat Vic, **2026-11-08** (Réunion +04), worktree `~/Desktop/labuse-deploy2`, branche `fix/saint-leu-1`
(partie C seulement), Opus. Prod via `ssh labuse-vps`. Aucune écriture prod 01 h–05 h (tout fait avant
minuit). À lire d'abord : `reports/QV22-1.md`, `reports/DEPLOY-QV21.md`.

---

## ★ VERDICT — en tête

| Étape | Résultat |
|---|---|
| **0. Pré-requis** | ✅ origin/main `55958d79f` contient les 4 merges (mails-1, john-cout-1, mails-exploit-1, qv22). Condition « q_v22 servi » **retirée** (décision Vic : promotion séparée). |
| **A1. Déploiement** | ✅ `55958d79f` déployé · `/readyz` 200 stable 25/25 · 37 jobs selftest à blanc · crontab == registre · **q_v20 servi intact** · NRestarts=0 |
| **A2. Swap** | ✅ 4 Go permanents (`/swapfile` + `/etc/fstab`) · `vm.swappiness=10` (persistant) · `free -m` : Swap 4095 Mo |
| **A3. Mails recette** | ✅ 2 mails RÉELS envoyés par la prod (Brevo) à `victorlaganepro+recette@gmail.com` · **15 modèles Brevo à supprimer** (liste §A3) |
| **A4. Vérité permanente** | ⚠️ **2 vert (D,E) · 1 rouge (C) · 3 sautés (A,B,F)**. node/chromium posés pour F (+701 Mo). A/B/F exigent un **instance app sans auth** (pas qu'un env) — §A4. Lot C rouge = **harnais périmé** (pas Brevo) — §A4. |
| **B. Coût John** | ⚠️ 2/3 sous 10 c€ (jobs 1,3 c€ · sauvegarde 1,9 c€) ; **« Tout est à jour ? » 9,7–10,1 c€** (question la plus large) — §B |
| **C. Saint-Leu** | ✅ cause corrigée (branche, sans déploiement) · cascade Saint-Leu COMPLÈTE **finit en 14 min 38 s** (avant : bloquée) · 0 écart de verdict · hook vert · commité `14fe0cbed`, **non mergé** |

**Promotion q_v22** : séparée du code (décision Vic). À faire ensuite par toi via John (nouveau garde-fou).
S'il refuse encore, je promeus q_v22 sur ton ordre (mêmes contrôles rejoués + filet de retour). **Non fait
dans ce mandat.** `PROMEUT=0` conservé, q_v20 servi.

---

## Étape 0 — pré-requis (après merge qv22)

origin/main (fetch) = **`55958d79f` (Merge branch 'fix/qv22')**. Les 4 branches sont ancêtres :
`feat/mails-1` `2e060650c` · `fix/john-cout-1` `c36295825` · `fix/mails-exploit-1` `9c39613f3` ·
`fix/qv22` `6169c886d` (merge `55958d79f`). Condition « q_v22 servi » **retirée** à ta demande.

## A1 — Déploiement de `main` en prod

- **Pré-vol** (23 h 28 Réunion) : aucun job concurrent (pg_dump/rsync/flux-run/calcul-nuit/injection/
  build-mvt/dryrun) ; sauvegarde du jour `labuse-labuse-20261108-133003.dump` (6,56 Go, 13 h 48, < 24 h) ;
  `/readyz`+`/healthz` 200 ; NRestarts=0 ; 22 G libres ; prod sur `13748ffed` (ancêtre strict → avance).
- **Filets** (hardlinks `cp -al`, ~0 octet) : `app-avant-groupe2`, `venv-avant-groupe2`,
  `labuse.env.avant-groupe2`, `Caddyfile.avant-groupe2` (inode partagé vérifié).
- **`deploy_app.sh` depuis `~/Desktop/labuse-main` (= origin/main)** exit 0 : garde manifeste (q_v20,
  433 229 l.) ✓ · 0 DDL/migration (diff `13748ffed..55958d79f`) · **37 jobs selftest à blanc** ✓ · front
  bâti sur le VPS · **crontab reposé == registre** (tz reunion, 0 écart) · `deploiement.json=55958d79fe2e`
  · manifeste prod **q_v20** intact · `fiche_cache` vidé · **`/readyz` 200 STABLE 25/25 (34 essais)** ·
  réchauffage détaché.
- **Post** : NRestarts=0, `/readyz`+`/healthz` 200, `LABUSE_CALCUL_NUIT_PROMEUT=0` + `LABUSE_JOHN_PLAFOND_EUR=50`
  + `LABUSE_CALCUL_NUIT_LABEL=q_v22` présents, served run **q_v20** (433 229). 0 incident introduit.

## A2 — Swap 4 Go permanent

`/swapfile` 4 Go (`fallocate`+`mkswap`+`swapon`), ligne `/swapfile none swap sw 0 0` dans `/etc/fstab`
(survit au reboot), `vm.swappiness=10` dans `/etc/sysctl.d/99-labuse-swappiness.conf` (+ appliqué à chaud).
`free -m` : **Swap total 4095, used 0**. C'est le « filet dur » réclamé par QV22-1 §C.2 (0 swap = tout pic
transitoire = OOM-kill sec, qui avait tué le banc de cohérence). Disque après : 18 G libres (83 %).

## A3 — Mails recette + modèles Brevo inutiles

**Deux mails RÉELS envoyés par la PROD** (code MAILS-1 déployé, transport Brevo `envoyer_html`) à
`victorlaganepro+recette@gmail.com`, `sent=True detail=ok` :
1. **Client — réinitialisation de mot de passe** (`mdp_oublie`), sujet « Réinitialisation de votre mot de
   passe LABUSE » (gabarit perso-signé).
2. **Résumé d'exploitation** (`mails_exploit`, faits réels prod), sujet « LABUSE — 5 choses à faire
   (08/11/2026) », 5 points.

**Modèles Brevo DEVENUS INUTILES** (rendus par l'app désormais ; Brevo = simple transport). Les 15 présents
chez Brevo sont tous à supprimer (12 `radar_digest` et 20 `essai_fin_proche` sont **déjà absents** — rien à
faire). À supprimer toi-même :

| id | nom Brevo | clé |
|---:|---|---|
| 4 | LABUSE-E-ESSAI-48H | essai |
| 5 | LABUSE-0-SOUSCRIPTION | souscription |
| 6 | LABUSE-1-BIENVENUE | onboarding1 |
| 7 | LABUSE-2-METHODE | onboarding2 |
| 8 | LABUSE-3-POINT-ETAPE | onboarding3 |
| 9 | LABUSE-A-CARTE-REFUSEE | relance_carte |
| 10 | LABUSE-B-SUSPENSION | suspension |
| 11 | LABUSE-C-RETABLI | retablissement |
| 13 | LABUSE-13-RADAR-ALERTE | radar_alerte |
| 14 | 14 · LABUSE-D-MDP-OUBLIE | mdp_oublie |
| 15 | 15 · LABUSE-D-MDP-MODIFIE | mdp_modifie |
| 16 | 16 · LABUSE-F-RESILIATION | resiliation |
| 17 | 17 · LABUSE-G-FLASH-PRET | flash_pret |
| 18 | 18 · LABUSE-H-EMAIL-CHANGE | email_change |
| 19 | 19 · LABUSE-I-RETOUR-TRAITE | retour_traite |

(Vérifié par GET read-only `/v3/smtp/templates` : 0 orphelin, 0 encore routé vers un template Brevo — toutes
les clés sont `mails_contenu.gere()`.)

## A4 — Vérité permanente (6 lots)

Rejeu `scripts/verite_permanente.py` en prod : **D VERT · E VERT · C ROUGE · A/B/F SAUTÉS** (2 v · 1 r · 3 s).

### node / chromium pour F — fait, place prise
`node` v22.23.1 déjà présent (build front). **Playwright chromium installé** (`npx playwright install
chromium`) → binaire `~labuse/.cache/ms-playwright/chromium-1254/.../chrome`, `LABUSE_CHROMIUM` posé dans
l'env. **Place prise : ~701 Mo** (chromium + headless-shell + ffmpeg). Disque : 17 G libres (83 %).

### A/B/F — « ce qui manque » n'est PAS qu'un env var (constat honnête)
`LABUSE_HARNAIS_BASE` **n'a pas été posé** : seul, il ferait passer A/B de « sauté » à **rouge** (connexion
refusée), car il n'existe aucune instance derrière. Le vrai blocage est structurel :
- **A & B** tapent une API **sans auth** (`env=local`) et lisent des fixtures (`preuves/choix.json` pour A).
  Or la prod renvoie **401** sur `/parcels/{idu}`, `/dossier/*.pdf`, `/communes` ; et le déploiement
  n'expédie que le dossier `harnais/` (pas `preuves/`). Les pointer sur l'API prod échouerait.
- **F** exige en plus `npm install` dans le dossier du harnais (package.json non déployé → playwright/axe-core
  absents) **et** un front servi **sans auth** (le backend renvoie 302→login sur `/socle/`).

→ Faire « tourner » A/B/F exige une **instance applicative dédiée `env=local` (auth désactivée), bornée à
127.0.0.1**, + le dépôt des fixtures (A/B) + `npm install`/front (F). C'est un **service auth-off permanent
sur la prod** : décision de sécurité qui te revient — je ne l'ai pas érigé unilatéralement. Reco : un
`labuse-harnais.service` systemd bindé `127.0.0.1:9790`, `LABUSE_ENV=local`, lancé juste avant
`verite-permanente` (ou transitoire dans le job). **Levier déjà en place : node + chromium + `LABUSE_CHROMIUM`.**

### Lot C — ROUGE, mais **pas** à cause de Brevo
Contrairement à l'hypothèse « vert après suppression Brevo » : **non**. Le harnais `C/harnais_mails.py`
**plante** sur `AttributeError: module 'labuse.emails' has no attribute 'reset_password'` — il appelle
`emails.reset_password` (+ `digest_notifications`, `annonce_email`, `maintenance_email`, `mise_en_vente_email`)
**supprimés/renommés par la refonte MAILS-1** (`emails.py` −266 lignes). Son autre moitié (`rendre_brevo()`)
fait un GET des templates Brevo qui **404era** justement après ta suppression. **Ce qu'il faut : réécrire le
harnais C au modèle MAILS-1** (rendu par `mails_contenu.rendre` pour les 20 clés, Brevo = transport ;
contrôles expéditeur unique / liens https / désinscription / params non substitués). La suppression Brevo
seule ne le verdira pas (elle aggraverait même son chemin `rendre_brevo`). **Diagnostic seul — non corrigé**
(hors périmètre « config » du mandat ; chantier contenu, je peux le prendre si tu veux).

### D, E — VERT (inchangés, base prod).

## B — 3 questions à John, coût lu au ledger `ia_log`

Toutes routées au modèle le moins cher (`john-lecture` / Sonnet 5.5), 2 appels/tour :

| Question | Coût | Objectif < 10 c€ |
|---|---:|:-:|
| « Tout est à jour ? » | **10,14 c€** (chaud 9,66 c€) | ❌ au plafond |
| « Jobs de la nuit dernière » | **1,32 c€** | ✅ |
| « État de la sauvegarde » | **1,94 c€** | ✅ |

« Tout est à jour ? » est la seule au-dessus — et **ce n'est pas un effet de cache froid** (re-posée cache
chaud : 9,66 c€). C'est la question **la plus large** : John marshale l'état de tous les sous-systèmes et
rend une réponse longue (2 546 car. ; cohérence en échec, calcul, Radar, verrous…). Les deux autres sont
étroites (liste de jobs, sauvegarde) → ~1–2 c€. Réponses de John exactes et sourcées (banc cohérence en
échec `IdleInTransactionSessionTimeout`, sauvegarde ok 6 560 Mo, etc.).

## C — Saint-Leu : cause du blocage corrigée (branche `fix/saint-leu-1`, commit `14fe0cbed`, non mergé)

**Cause** (profilée, 100 parcelles Saint-Leu) : **96,4 s / 97,5 s** = `ST_Area(ST_Union(ST_Intersection(
sl.geom_2975, p.geom_2975)))` **par parcelle** (couverture PPR rouge unionnée, `union_coverage_interdit`),
sur la **géométrie BRUTE** (polygones PPR/aléa DEAL jusqu'à ~221 906 sommets), appelé pour **~87 %** des
parcelles (multi-rouges, la norme à Saint-Leu) à ~1,1 s/appel. (La diagnose QV22-1 §A.2bis(c) — « coût
spatial agrégé par parcelle » — pointait bien là, pas le prime() batch.)

**Correctifs (résultat identique)** :
1. `union_coverage` / `union_coverage_interdit` lisent le cache **subdivisé** `spatial_layers_sub` (pièces
   ≤256 sommets + GiST) au lieu de la géométrie entière → **1082 ms → 6 ms** (×180), même aire (écart
   1,5·10⁻⁵ m² sur 165 514 m²). Repli sur `spatial_layers` si cache absent.
2. `prime()` ne calcule l'intersection batch **que des kinds réellement lus** (`cascade_intersection_kinds`
   = YAML ∪ littéraux code, dont « pente ») → exclut batiment_cosia (~37 k pièces/Saint-Leu), piscine_cosia,
   transport_*… (jamais lus).

**Preuves (local, q_v20)** :
- **correctness** : 500 parcelles Saint-Leu, ANCIEN vs NOUVEAU → **0 écart de score/statut, 23 549 verdicts
  de cascade identiques** (0 en plus/en moins), PPR rouge 0 écart ;
- **la cascade Saint-Leu COMPLÈTE (23 046 parcelles) FINIT en 14 min 38 s** (~26 parc/s) — avant, à
  ~1,3 parc/s, elle n'aurait pas fini avant la fenêtre (le blocage du mandat QV22-1) ;
- `run_cascade` : 227,6 s → 4,4 s sur 500 parcelles (×52).
- **Tests** : `tests/test_saint_leu_cascade.py` (6, verts). **Hook `test-unit` : 3225 passed, 0 échec.**

**Non mergé, non déployé** (consigne). La branche part de `55958d79f` (main à jour, qv22 compris).

## Périmètre & preuves

- **Écritures prod (dans le mandat)** : déploiement `55958d79f` (restart + front) ; swap 4 Go + swappiness ;
  `LABUSE_CHROMIUM` dans l'env ; 2 mails recette (Brevo) ; 3+1 questions John (appels IA réels, ledger) ;
  install chromium (venv/cache labuse). **Served run q_v20 intact, `PROMEUT=0`, rien 01 h–05 h.**
- **Lectures seules** : état prod, Brevo GET templates, verite-permanente, profilage Saint-Leu (base LOCALE).
- **Local (base q_v20)** : fix Saint-Leu + recette (scratch `dryrun_*` nettoyé).
- **Filets prod conservés** : `app-avant-groupe2`, `venv-avant-groupe2`, `labuse.env.avant-groupe2` + dump du jour.

## Réserves honnêtes & dette

1. **Promotion q_v22 non faite** (séparée, décision Vic → John ; fallback moi sur ordre, hors ce mandat).
2. **A/B/F de verite-permanente** restent sautés : il manque une **instance app auth-off bornée localhost**
   + fixtures (A/B) + npm/front (F) — décision de sécurité (service auth-off permanent) à trancher. node +
   chromium + `LABUSE_CHROMIUM` posés.
3. **Lot C rouge = harnais périmé** (références `emails.*` supprimées par MAILS-1), **pas** Brevo. Réécriture
   au modèle MAILS-1 à faire (je peux la prendre).
4. **« Tout est à jour ? » à ~10 c€** (question la plus large) — légèrement au plafond, pas un effet de cache.
5. Le fix Saint-Leu **n'est pas déployé** : la prochaine cascade de nuit en prod ne profitera du gain
   qu'après merge + déploiement (à ta main).
