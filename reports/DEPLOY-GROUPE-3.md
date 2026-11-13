# DEPLOY-GROUPE-3 — tout le code en prod, puis le run candidat q_v23

Mandat Vic, **2026-11-10** (Réunion +04), worktree `~/Desktop/labuse-deploy3`, branche
`ops/deploy-groupe-3`, Opus. Prod via `ssh labuse-vps`. **Aucune écriture prod 01 h–05 h** (Réunion) ;
run servi **q_v20** jamais touché ; **`PROMEUT=0`** (promotion = John, sur ordre de Vic). À lire
d'abord : `reports/DEPLOY-GROUPE-2.md`, `RESIDUEL-1.md`, `RESIDUEL-2.md`,
`docs/audit-2026-11/algo-fix-1/COMPTE-RENDU.md`.

---

## ★ VERDICT — en tête

| Étape | Résultat |
|---|---|
| **0. Pré-requis** | ✅ origin/main `7d4f9f0ec` contient les 11 merges ; branche deploy FF à origin/main |
| **Décision Score↔résiduel** | ✅ code : la vue `parcel_residuel` lit un run CANDIDAT par numéro, sans servir (commit `d214556f7`) — identité sur run servi prouvée, suite 3203 verte |
| **A. Déploiement** | ✅ `9fd5de9867e1` déployé · `/readyz` 200 stable 25/25 · 37 jobs selftest · crontab==registre · migrations additives (C/E/D_net + vue GUC) · **verite-permanente 6 vert / 0 rouge / 0 sauté (F VERT)** · served q_v20 intact |
| **B. Calcul q_v23** | ✅ _chaîne de nuit faite_ : résiduel seq 18 (R+C/E/D_net) · cascade q_v23 (21,09 M) · build_all (frame 433 229) · flux-run Signal (p_score_v2 433 229) · Score LABUSE (seq 18). **Scénarios V2 = demain** (après merge origin/main + foncier-public-1). |
| **C. Contrôles** | ✅ _7 contrôles VERTS_ (`ok=True`) · témoins fiche↔run 6/6 · comptes 433 229 · banc cohérence achevé 0/0. **Répartition statuts/bandes V2 = demain** (avec les scénarios V2). |

**Phrase pour John (promotion)** : _à finaliser demain après les scénarios V2._ **Reco actuelle : NE PAS
promouvoir q_v23 en l'état** (cf. §D) : le run est juste (7 contrôles verts, comptes 433 229, batch≡fiche)
et corrige de vraies erreurs, mais il porte dans le classement le faux positif `terrain_exigu` sur ~122
grandes parcelles (≥ 48 Excellentes/Bonnes). Corriger `terrain_exigu` (ALGO-LECTURE-1) puis recompute,
PUIS promouvoir. `PROMEUT=0`, la promotion reste un geste de John sur ordre de Vic.

### Incidents prod trouvés & corrigés pendant A (hors périmètre nominal)

1. **`jobs selftest` cassé** (régression merge OPS-3) : `h["cmd"]` sur un harnais sauté/rouge →
   `KeyError('cmd')` → **deploy_app.sh refusait le déploiement**. Fix `h.get("cmd", [])` (commit
   `9fd5de986`, test de non-régression). **C'est ce qui a bloqué le 1ᵉʳ essai de déploiement.**
2. **`/etc/labuse/labuse.env` passé en `0600` root-only le 09/11 02:01** (tous les backups historiques
   sont `0640 root:labuse`) → le compte `labuse` ne pouvait plus **sourcer** l'env → **tous les crons
   échouaient** (cause de la **sauvegarde du 09/11 manquante** ; probable origine : écriture env de
   l'OPS-3 `ops3_creer_recette`). **Restauré à `0640 root:labuse`** ; `labuse` source de nouveau,
   `PROMEUT=0` confirmé. **À surveiller : d'autres jobs de nuit 09/10–10/11 ont pu échouer.**
3. **verite-permanente 6/6** : libs Chromium (`install-deps`) ; lot **F** CSP-bypass (audit seul) +
   cible = front Caddy `https://app.labuse.immo/socle/` (le backend :8000 ne sert pas `/assets/*`) ;
   lot **A** fixture `preuves/choix.json` livrée ; `LABUSE_HARNAIS_BASE` ajouté à l'env (le cron de
   nuit joue désormais A/B/F). Correctifs durables : commit `984de417e` (deploy_app.sh + F harness).
4. **Banc de cohérence F3 cassé par le déploiement de DOCS-1** (commit `34b43f18e`) : déployer les 11
   merges inclut `fix/docs-1`, qui a **supprimé** `labuse.exports.financier_bilan` (document « Financier »,
   commit `e441d473c`). La famille métamorphique **F3** l'importait encore → `ImportError` → banc2 la
   classe « indisponible » → `coherence-banc` **non achevé** (`acheve=false`, « invariants indisponibles :
   F3 ») → gate 7 rouge (OPS-3), ALORS QUE la cohérence réelle était saine (`faux_client=0`,
   `erreurs_lecteur=0`, 1 écart tolérable). **Régression INTRODUITE par ce déploiement** (le nightly
   coherence-banc aurait échoué chaque nuit). Fix : import `FBILAN` gracieux + les sous-familles
   F3.revente/F3.bilan (seules à dépendre du moteur financier retiré) ne se registrent que si le moteur
   existe → F3 reste importable + joue ses autres invariants → banc achevé. (DOCS-1 aurait dû retirer ces
   invariants.) Banc relancé — résultat en §C.

---

## Étape 0 — pré-requis (✅)

origin/main (fetch) = **`7d4f9f0ec` (Merge branch 'fix/residuel-2')**. Les **11** merges demandés sont
présents dans l'historique d'origin/main (vérifiés un par un) : `fix/saint-leu-1`, `fix/docs-1`,
`fix/ops-3`, `fix/residuel-1`, `feat/docs-da-1`, `fix/retours-17`, `fix/commune-fix-2`,
`fix/verif-fix-1`, `feat/ecrans-nov-1`, `fix/algo-fix-1`, `fix/residuel-2`. La branche
`ops/deploy-groupe-3` a été **fast-forward** à origin/main (elle était à `54878db3b`, soit origin/main
moins les 3 commits RESIDUEL-2). **État prod de départ** : served **q_v20** (433 229), `/readyz`+
`/healthz` 200, disque **17 G libres (83 %)**, swap **4 Go** (DEPLOY-GROUPE-2) intact, NRestarts=0.

---

## Décision — le Score lit le résiduel d'un run CANDIDAT par numéro (sans le servir)

**Constat (bloquant, découvert avant exécution).** Le Score LABUSE (`score_labuse.py:328`), les
features du Signal (`p_model/sql.py`, `p_v2/potentiel.py`…), le repli des scénarios V2 **et de nombreux
chemins CLIENT en direct** (tuiles carte `api/tiles.py`, filtres de recherche `api/app.py`, blocs de
fiche `verdict_servi.py`/`blocs.py`, projets, partenaires) lisent le résiduel par la **VUE**
`parcel_residuel`, **câblée en dur** sur `WHERE run_seq = (run SERVI)` (`residuel_runs.py:141`). Donc un
Score candidat calculé « normalement » lirait l'**ancien** résiduel q_v20 ; pour qu'il reflète le
**nouveau** résiduel (RESIDUEL-1/2), il faudrait **servir** le résiduel candidat — ce qui est **visible
client** (la vue bascule pour tout le monde) et réintroduit l'incohérence fiche↔classement. Le mandat
interdit de toucher le run servi.

**Décision de Vic** : faire lire au Score **et** aux features du Signal le résiduel candidat **par son
numéro de run**, en paramètre, au lieu de la vue liée au servi — petit changement de code, testé
(Score sur le run servi par ce chemin = Score actuel), commité, déployé avec le reste. Si > 1 h de
travail : s'arrêter et prendre l'option « différer le Score à la promotion ».

**Fait (≪ 1 h, commit `d214556f7`)** :
- **`residuel_runs.py` `_view_sql`** — la vue lit `WHERE run_seq = COALESCE(NULLIF(current_setting(
  'labuse.residuel_run_seq', true),'')::int, (run servi))`. Une session qui **ne pose pas** le réglage
  (tous les clients, le service) lit le **run servi** — comportement **strictement inchangé**.
- **`residuel_runs.apply_residuel_run_seq(conn, run_seq)`** — pose le réglage de session (lecture
  seule ; ne touche ni `is_served` ni aucune donnée).
- **`db.make_engine`** — `-c labuse.residuel_run_seq=<int>` dans les options de connexion quand
  l'env **`LABUSE_RESIDUEL_RUN_SEQ`** est posé (`int()` valide → pas d'injection) : **tout process de
  calcul** lancé avec cet env fait lire le run candidat à TOUTES ses connexions (Score **et** Signal).
- **`ensure_runs_schema`** — refait la vue (idempotent) si sa définition ne contient pas encore le
  marqueur `residuel_run_seq`, en plus de l'ajout des colonnes C/E/D_net de RESIDUEL-2. S'applique au
  boot du déploiement (ACCESS EXCLUSIVE bref, une seule fois, derrière la stabilisation `/readyz`).
- **`cli score-labuse`** — option `--residuel-run-seq` (applique le réglage par session).

**Preuves (base locale réelle)** : vue par défaut = run servi (seq 17) ; `GUC=1/15/16` → la vue lit
**exactement** ces runs (comptes + Σ SDP = lecture directe de `parcel_residuel_runs`), `is_served`
**intact** ; **identité** : `score_batch` en visant le run servi == vue par défaut (test
`test_score_sur_run_servi_identique`). Env au connect : `LABUSE_RESIDUEL_RUN_SEQ=18` → `current_setting`
= 18. **Suite unitaire 3203 passed, 0 échec** ; `tests/test_residuel_run_seq_param.py` (3 verts + 1
`reel` skip faute de run candidat dans la base de test, prouvé hors pytest).

---

## A. Déploiement du code en prod — PLAN _(après 05:00)_

1. **Pré-vol** : aucun job concurrent ; sauvegarde < 24 h présente ; `/readyz`+`/healthz` 200 ;
   NRestarts=0 ; disque mesuré. Filets `cp -al` (`app-avant-groupe3`, `venv-avant-groupe3`,
   `labuse.env.avant-groupe3`).
2. **`deploy/scripts/deploy_app.sh`** depuis le worktree (= `ops/deploy-groupe-3`, HEAD `d214556f7`) :
   garde manifeste (q_v20 présent) ✓ · artefacts de modèle + harnais NU-5 livrés · **migrations
   ADDITIVES** appliquées au boot via `ensure_runs_schema` (colonnes `sdp_max_m2/sdp_existante_m2/
   d_net_m2` de RESIDUEL-2 + vue `parcel_residuel` au marqueur `residuel_run_seq`) et `ensure_table`
   de `parcel_scenario_v2_runs` (ALGO-FIX-1) — **tables/colonnes NEUVES seulement** · **jobs
   selftest** à blanc · **crontab == registre** · `/readyz` 200 STABLE 25/25 · `fiche_cache` vidé.
3. **Bibliothèques système de Chromium** pour le lot F de verite-permanente : `playwright
   install-deps chromium` (ou paquets apt, dont `libatk-1.0.so.0` absent au groupe 2/ops-3) +
   `npx playwright install chromium` si besoin ; **`LABUSE_CHROMIUM`** posé. **Espace disque mesuré
   avant/après.**
4. **Vérité permanente** : `labuse jobs run verite-permanente` → **verdict des 6 lots** (A B C D E F) ;
   **F doit passer vert** (libs Chromium posées ; C vert attendu car MAILS-1/OPS-3 déployés).

## B. Calcul du run candidat q_v23 — PLAN _(hors 01–05, RAM/disque/swap surveillés)_

Ordre **séquentiel** (jamais résiduel-shards ET cascade-workers en même temps — OOM au groupe q_v22) ;
chaque étape **chronométrée** ET **disque mesuré (`df -h`) après chaque grosse étape** (consigne Vic).
Le run servi q_v20 n'est jamais écrit (`assert_writable` sur le résiduel, `is_served` intact, `PROMEUT=0`).

0. **Disque** : mesurer. Purge **seulement si la place manque**, et **seulement** q_v21 et q_v22
   (jamais promus) — leurs lignes `p_score_v2` + cascade (consigne Vic). **GARDER TOUJOURS** : q_v20
   (servi), **q_v19_sources** (cascade servie), et **q_v18** (dernier run servi avant q_v20 = retour
   arrière) + ses composantes. Jamais q_v16/q_v18/q_v19/q_v20.
1. **Résiduel île (seq NEUF) — ✅ `run_seq=18`** (`residuel-runs`, non servi, servi reste seq 17).
   Seed commune 97417 (157 s) + **4 shards équilibrés par comptage** (INSEE, `--into-run 18`) →
   **433 229 parcelles, 24 communes, 0 erreur**, C/E/D_net persistés (258 210 constructibles).
   **Durée wall-clock ~6 h 24** (shards : s1 5 h 19 · s2 **6 h 24** · s3 5 h 51 · s4 5 h 22 — plus
   long que l'estimé 3,6 h : trafic prod de jour + communes de cirque contrainte-lourdes). Disque
   après : **17 G libres**. Served seq 17 intact (`assert_writable`).
2. **`labuse rebuild`** (spatial_layers_sub) si l'injection de nuit a bougé les couches (comme q_v22).
3. **Cascade fraîche q_v23** (étage 0) — ✅ 24 communes disjointes, 4 workers (`dryrun-evaluate --label
   q_v23 --resume`). **21 094 673 lignes** (identique q_v21/q_v22 — même univers/couches), **433 229
   parcelles couvertes** (eval), 24 communes. **Durée ~2 h 54** (4 workers, ~26 parc/s agrégé ; Saint-Leu
   **~11/s**, le fix `saint-leu-1` tient — plus le 1,3/s de q_v22). Disque après : 12 G. Les 1 353
   « sans étage0 » = parcelles hors univers servi (434 582 cadastrales − 433 229 servies). **INCIDENT
   corrigé en cours** : les séquences d'id `dryrun_parcel_evaluations_id_seq` (7,87 M < max 9,18 M) et
   `dryrun_cascade_results_id_seq` (237 M < max 287 M) étaient **en retard sur leur max** (séquelle de la
   copie manuelle Saint-Leu de QV22 §A.2bis : ids explicites sans `setval`) → 1ᵉʳ essai : `UniqueViolation`
   sur les 4 workers → `setval(max)` des deux séquences + purge du partiel q_v23 + relance propre.
4. **`build_all`** (`scripts/m3-p-model/build_dataset.py`, `LABUSE_RESIDUEL_RUN_SEQ=18`) — ✅
   **`p_model_frame = p_model_static = 433 229`** (= univers vivant ; le correctif comptes de q_v22 tient,
   plus le 431 663 périmé). **Durée ~13 min** (bati = l'étape longue ~12 min ; frame/mutations/permits/
   static/dataset < 1 min chacun). Disque 12 G.
5. **Scoring Signal** — ✅ `LABUSE_ETAGE0_RUN=q_v23 LABUSE_RESIDUEL_RUN_SEQ=18 flux-run --label q_v23
   --resume --recette q_v15` (cascade sautée via `--resume`, scoring seul). **433 229 parcelles scorées**
   (= comptes cible), tiers **a_suivre 337 · priorité 72 · écartée 153 638 · sans_signal 279 182**
   (≈ q_v22 335/73/153 638/279 183 → Signal intact). **Durée ~17 min** (1013 s). Manifeste candidat écrit
   (`scoring_run=q_v23, cascade_run=q_v23`). Disque 11 G. NON servi.
6. **Score LABUSE** — ✅ `LABUSE_RESIDUEL_RUN_SEQ=18 score-labuse --run q_v23 --cascade-label q_v23
   --signal-run q_v23 --residuel-run-seq 18`. **433 229 scorées · ~22 min** (1303 s). **Bandes q_v23 vs
   q_v20 (servi)** : 0 **229 868** (q_v20 217 954, **+11 914**) · A 6 009 (6 166) · B 34 271 (36 254) ·
   C 47 222 (50 913) · D 93 236 (99 011) · HC 6 351 (6 659) · NC 16 272 (=). **Écart EXPLIQUÉ** : q_v20
   lit le résiduel du **run-of-night NON clippé** (seq 17, trop généreux sur les parcelles multi-zones /
   marginales) ; q_v23 lit le **chemin unique clippé** (seq 18 ≡ **fiche**, invariant batch≡fiche RESIDUEL-1).
   214 parcelles **0→constructible** (correctif PPR partiel, dont DH0076) ; **11 819** marginales
   **A–D→0** (SDP q_v20 moy **131 m²** → 0 : saturées après clip U/AU + reculs gabarit, cause NULL). Le
   classement rejoint enfin la fiche (toujours clippée côté client). **Shift matériel ~12 k parcelles —
   à valider par Vic/John avant promotion** (correct par construction, mais ampleur > simulations ciblées
   RESIDUEL-1/2). Disque 9 G.
7. **Paliers** — les tiers du Signal sont déjà calculés par `flux-run` (a_suivre 337/priorité 72) ;
   `recompute-paliers` non requis (run frais). Écart de paliers mesuré **0,17 %** (755/433 229, gate < 3 %).
8. **Scénarios V2** — **AVANT de lancer (consigne Vic 10/11)** : déployer `origin/main` (code seul,
   procédure A, hors 01h–05h) puis lancer les scénarios. **NB** : on ne déploie PAS `origin/main` nu —
   il manque les 3 commits de ce mandat (GUC résiduel `d214556f7` requis pour que les scénarios lisent
   seq 18 ; selftest `9fd5de986` sinon deploy refusé ; F/A `984de417e`) → on **merge `origin/main` dans
   `ops/deploy-groupe-3`** (apporte le nouveau code en gardant les fixes) puis deploy. **État 10/11 ~19h :
   origin/main `ddaeaf315` a `feat/ecrans-nov-2` mais PAS `fix/foncier-public-1`** (vérifié ×2, pas même
   une branche remote). À re-vérifier demain avant l'étape ; résultat noté ici. Puis
   `LABUSE_RESIDUEL_RUN_SEQ=<seq18>
   compute_scenarios_v2_batch(run_label=q_v23)` : conservation exacte (île) + reconstruction **enrich**
   (C/E/D_net via `compute_residuel` LIVE = nouveau code). Table `parcel_scenario_v2_runs`. Durée : _…_

## C. Contrôles de promotion sur q_v23

**7 contrôles** (`autonomie.controler_run` sur q_v23, précédent = servi q_v20) :

| # | Contrôle | Résultat q_v23 |
|---|---|---|
| 1 | manifeste candidat | ✅ présent (`scoring_run=q_v23, cascade_run=q_v23`) |
| 2 | complétude (score v2 + cascade) | ✅ « run complet (score v2 + cascade propre au run) » |
| 3 | copro en palier actionnable = 0 | ✅ 0 |
| 4 | zone rouge en palier actionnable = 0 | ✅ 0 |
| 5 | écart de paliers < 3 % | ✅ **0,17 %** (755/433 229) |
| 6 | **comptes = 433 229** | ✅ **433 229 = 433 229** (résiduel seq 18, cascade, p_score_v2, score_labuse : tous 433 229) |
| 7 | cohérence 0/0 FRAÎCHE + achevée | ✅ banc id=28 (10/11 23:04) **achevé**, **faux_client 0 / erreurs_lecteur 0** (1 écart `incoherent` tolérable connu — pas un gate) — après le fix F3 (§incident 4) |

➜ **VERDICT `controler_run` : `ok=True`, `echecs=[]`, `en_attente=[]` — les 7 contrôles sont VERTS.**

- **Cohérence fiche ↔ run — ✅ sur les 6 témoins** : `score_labuse` q_v23 `sdp_residuelle` = résiduel
  seq 18 à l'identique — AK0804 34 223 (A) · BZ1065 35 (D) · EH0043 44 117 (B) · EI0085 11 368 (B) ·
  **DH0076 26 258 (A — flip RESIDUEL-1 0→constructible confirmé)** · AL0258 0 (terrain_exigu). **Prouve
  que le Score lit bien le résiduel candidat seq 18 (mécanisme GUC) et que batch≡fiche tient.**
- **Comptes** : univers servi **433 229** partout (0 trou/doublon).
- **Banc de cohérence** (`coherence-banc`, relancé le 10/11 au soir) : _résultat à compléter_ (gate 7).
- **Répartition des bandes Score** : cf. §B.6 (écart +11 914 bande 0 expliqué). **Répartition statuts/
  bandes V2** : **demain**, après le calcul des scénarios V2 (comparaison ALGO-FIX-1 §5).

## D. Les ~11 819 bascules A–D → bande 0 (analyse demandée par Vic avant promotion)

**Cohorte** : parcelles constructibles en q_v20 (bande A/B/C/D) qui tombent en **bande 0** dans q_v23 =
**11 819** (214 font l'inverse, 0→constructible). Toutes **lecture seule**, **batch ≡ fiche vérifié**.

**Par cause** (proximale ; le clip du chemin unique combine reculs + emprise/CES + découpe PPR rouge +
portion U/AU — non séparables sans instrumenter le moteur, limite honnête) :

| Famille | n | Nature | Jugement |
|---|---:|---|---|
| **Saturées par le clip** (gabarit, `C ≤ E`, cause nulle) | **8 136** | capacité clippée ≤ existant → reconstruction nulle (déjà bâti au max) ; aire médiane **467 m²** | **CORRECT** (thèse RESIDUEL-1 : q_v20 lisait un C non clippé trop généreux ; q_v23 = la fiche) |
| **`terrain_exigu`** (fragment jugé trop étroit) | **3 683** | < 300 m² : **plausible** (735) ; 200–1000 m² (2 826) ; **> 1000 m² : 122**, dont **48 bande A/B**, jusqu'à **5 791 m²** | **DISCUTABLE** — heuristique fautive ALGO-LECTURE-1 |

**Par bande d'origine (q_v20)** : A (Excellente) **11** · B (Bonne) **307** · C **1 977** · D (Faible)
**9 524** (80,6 %). **Par commune** (tête) : La Possession 3 194 · Saint-Denis 3 002 · Saint-Joseph
2 736 · Sainte-Marie 1 039 · Bras-Panon 967 · Saint-Paul 168.

**20 parcelles au hasard, capacité avant/après + raison, vérifiées contre la fiche** (`compute_residuel`
live) : **batch == fiche 20/20**. Exemples : `97408000AP1022` (La Possession, C) R 370 → C 159 ≤ E 297
(saturée) ; `97412000BX0131` (Saint-Joseph, D) R 134 → C 142 ≤ E 181 ; `97418000AT0525` (Sainte-Marie, D,
260 m²) → `terrain_exigu`. Les saturées montrent toutes `C_clippé ≤ E` conforme à la fiche.

**Famille DISCUTABLE — `terrain_exigu` sur grandes parcelles (vérifiée 8/8 batch == fiche)** :
`97418000AY0416` Sainte-Marie **2 017 m², q_v20 bande A (Excellente), R 1 828** → `terrain_exigu`, R 0 ;
`97411000DK0447` Saint-Denis 2 256 m², B, R 1 324 → 0 ; `97415000CW0252` Saint-Paul 2 143 m², B, R 1 270
→ 0 ; `97419000AN0398` Sainte-Rose **5 791 m²** → 0. **Une parcelle de 2 017 m² « Excellente » (1 828 m²
résiduels) ne peut pas être « terrain trop exigu ».** C'est le défaut documenté par ALGO-LECTURE-1
(`terrain_exigu` teste l'étroitesse du CONTOUR après reculs, pas la SURFACE → faux positifs sur grandes
parcelles), **amplifié** par le clip RESIDUEL-1 (le fragment clippé a un contour plus étroit). `batch ≡
fiche` tient (la fiche est tout aussi fausse) → ce n'est **pas** une régression de q_v23, mais q_v23
porte ce faux positif dans le **classement** (≥ **48** parcelles A/B > 1000 m², ~**122** > 1000 m² au
total). La famille saturée compte aussi 170 A/B / 285 à R20 ≥ 500 — plus gros écarts, mais conformes à la
fiche et au clip (échantillon saturé vérifié OK).

### Recommandation : **NE PAS promouvoir q_v23 en l'état.**

q_v23 est **juste par construction** (batch ≡ fiche, 7 contrôles verts, comptes 433 229) et corrige deux
vraies erreurs de q_v20 (214 parcelles rouvertes dont DH0076 ; 8 136 saturées enfin alignées sur la
fiche). **MAIS** il propage dans le classement le faux positif **`terrain_exigu`** sur ~122 grandes
parcelles (≥ 48 Excellentes/Bonnes, jusqu'à 5 791 m²), qui disparaîtraient à tort des classements.
Comme `batch ≡ fiche`, le défaut est **dans l'heuristique `terrain_exigu` elle-même** (donc déjà faux
côté fiche/client). **Reco** : (1) corriger `terrain_exigu` (tester la SURFACE nette, pas seulement le
contour post-reculs — ALGO-LECTURE-1) ; (2) recompute q_v23 ; (3) alors promouvoir — les corrections
saturées + flips PPR restent valides. Si Vic veut promouvoir malgré tout (le run EST cohérent avec la
fiche actuelle), le faire en connaissance des ~122 faux « terrain exigu » à corriger ensuite.

## E. Recalcul PARTIEL de q_v23 après `fix/exigu-fix-1` (préparé, à lancer au merge)

Décision Vic : ne pas promouvoir q_v23 ; un correctif `terrain_exigu` arrive. On recalcule **seulement
les parcelles `cause='terrain_exigu'`** (résiduel → Score → scénarios V2), **sans refaire l'île** — car
`exigu-fix` ne *relâche* que la règle `terrain_exigu` (aucune parcelle hors de cet ensemble ne peut
*devenir* terrain_exigu ; la cascade, le socle et le Signal ne changent pas).

**Cible** : `terrain_exigu` dans le run candidat (seq 18) = **72 083 parcelles** (23 communes ; tête :
Saint-Denis 11 909 · Saint-Paul 7 981 · Saint-Pierre 6 045 · Le Tampon 5 271 · Saint-Joseph 4 782…).

**Procédure** (`scripts/q23_exigu_delta.sh`, lancée en `labuse` sur le VPS APRÈS déploiement d'origin/main
exigu-fix compris ; hors 01 h–05 h) :
1. **Pré-vérif** : diff de `exigu-fix` limité à la règle `terrain_exigu` — sinon le delta est invalide
   (faire un recompute complet). git merge origin/main dans la branche (garder les fixes) + `deploy_app.sh`.
2. **Résiduel delta** : `compute-residuel --into-run 18 --parcelles-fichier <72 083>` en **4 shards**
   (écrase les lignes terrain_exigu de seq 18 par les valeurs corrigées — upsert `(run_seq, parcel_id)`,
   run servi seq 17 intact).
3. **Sous-ensemble corrigé** : parcelles dont la cause n'est plus `terrain_exigu`.
4. **Score LABUSE delta** : `score-labuse --run q_v23 --parcelles-fichier <cible> --cascade-label q_v23
   --signal-run q_v23 --residuel-run-seq 18` (nouveau `--parcelles-fichier`, commit `0e96618a3`).
5. **Scénarios V2 delta** : `compute_scenarios_v2_batch(run_label='q_v23', enrich=True)` sur les corrigées.
6. **Rejouer les 7 contrôles** (`scripts/q23_gate.py`) + re-vérifier §D (les grandes parcelles A/B
   `terrain_exigu` doivent retrouver une bande constructible).

**Durée estimée ~2–3 h** : résiduel delta sur 72 083 (4 shards) **~1,5–2 h** (poste dominant) · Score delta
**~1 min** · scénarios V2 enrich (sous-ensemble corrigé) **~10–40 min** · contrôles + banc **~20 min**.
**Skippé** (donc économisé) : cascade (~3 h) + build_all + flux-run Signal (inchangés). Vs recompute
complet ~15 h.

## F. Second déploiement — FRAICHEUR-FIX-1 + ESTIMER-2 (évaluation demandée par Vic)

**Décision Vic (11/11)** : déploiement 1 = **seulement jusqu'à `585d3dd8e`** (ECRANS-NOV-2 +
FONCIER-PUBLIC-1) puis scénarios V2 ; FRAICHEUR-FIX-1 + ESTIMER-2 (mergés depuis, pointe `a8d578655`)
partent dans un **2ᵉ déploiement avec le correctif exigu**, avant le recalcul partiel.

**Touchent-ils résiduel / cascade / Signal / Score ? — NON (vérifié).** Diff `585d3dd8e..a8d578655` sur
`src/` : **0 fichier sensible** (ni `faisabilite/residuel*` / `residuel_runs` / `faisabilite/db.py`, ni
`cascade/`, ni `scoring/p_v2` / `p_model` / `signal` / `score_labuse` / `scenarios_v2`). `faisabilite/
bilan.py` touché = **prix** (`_mediane_ponderee`), pas le résiduel. → **orthogonaux à q_v23**.

**Ce que ça change en prod :**
- **Au déploiement du code (immédiat, sans ingestion)** : (a) **prix de secteur = médiane PONDÉRÉE**
  (ESTIMER-2) calculée sur le DVF DÉJÀ ingéré (31/12/2025) → €/m² servis changent (fiche/Dossier/bilan/
  Estimer/Radar) ; « dernière vente » lue sur tout l'historique (37 488 parcelles corrigées) ; prix
  terrain (rayon adaptatif, plus de vide) ; surface maison (niveaux LiDAR). **Client-visible, indépendant
  de q_v23.** (b) La page Données passe **5 sources « en retard »** (DVF, SITADEL, RP, INPI, OSM) tant
  qu'elles ne sont pas rechargées (surveillance honnête). (c) **3 nouveaux jobs de nuit** installés au
  crontab : `fraicheur-nuit` 07:50, `estimer-banc-precision` 04:30 (calibration prix, pas une ingestion),
  **`ingest-inpi-rne` mensuel (≈ 1 h 45, INGESTION)**.
- **`jobs rattraper`** (FRAICHEUR-FIX-1 ajoute cet appel dans `deploy.sh`) : relance les crons du JOUR
  dont le créneau est passé → **peut déclencher des INGESTIONS** (`ingest-dvf`, `ingest-sitadel`,
  `injection-nuit`…). ⚠ **À NEUTRALISER au 2ᵉ déploiement** (consigne « aucune ingestion sans accord ») :
  lister ce qu'il relancerait, OK de Vic, sinon déploiement avec rattraper désactivé.
- **Ingestions explicites (SEULEMENT sur accord Vic, hors 01–05)** : `refresh-dvf` (+1 606 ventes 2026-S1,
  ~3–6 min), `ingest-permits --refresh` (SITADEL), `ingest-inpi-rne` (~1 h 45), `ingest-iris-rp` (RP2023
  si publié). **ESTIMER-2 ne requiert AUCUNE ingestion** (recalcule sur le DVF existant + histo + LiDAR).
- **Signal** : **code non touché**. Mais un **rechargement DVF** (ingestion FRAICHEUR-FIX-1) change les
  **intrants** du Signal et des prix → après `calcul-nuit` (rebuild `dvf_mutations_parcelle`), **prix
  médianes recalés (+6 mois) + Signal re-scoré** sur mutations plus fraîches. Tant que les dérivés ne sont
  pas reconstruits, prix DVF et Signal ne bougent pas.

**Ordre recommandé vs promotion de q_v23** (les deux chantiers sont orthogonaux) :
1. **Demain** — déploiement 1 (≤ `585d3dd8e`) + scénarios V2 q_v23 (aucun changement prix/Signal).
2. **Au merge d'exigu-fix** — déploiement 2 (exigu-fix + FRAICHEUR-FIX-1 + ESTIMER-2), **`jobs rattraper`
   neutralisé** → changement immédiat du **prix servi** (médiane pondérée, à annoncer) + 5 sources « en
   retard » + 3 jobs ; puis **recalcul partiel exigu** (§E) → rejeu des 7 contrôles.
3. **Promouvoir q_v23** (John, sur ordre Vic) — run capacité/Score/scénarios, sur DVF courant.
4. **Puis, opération SÉPARÉE sur accord Vic** — ingestions DVF/SITADEL/RP/INPI → `calcul-nuit` → prix +
   Signal rafraîchis. Découplé de q_v23 (surfaces servies différentes).

Je recommande cet ordre (promouvoir q_v23 d'abord, rafraîchir les données ensuite) : q_v23 reste sur un
DVF stable, et le rafraîchissement DVF/Signal est une opération de fraîcheur distincte, approuvée à part.
*Variante si tu veux q_v23 servi sur le DVF le plus frais : recharger DVF d'abord, re-scorer le Signal de
q_v23 (flux-run ~17 min), puis promouvoir — plus couplé.*

## G. Déploiement 1 (≤ `585d3dd8e`) + scénarios V2 — 11/11

**Déploiement 1 — ✅ `a8cc09dee383`** (merge `585d3dd8e` = ECRANS-NOV-2 + FONCIER-PUBLIC-1 + audit
fraicheur-1, dans ma branche, mes 5 fixes gardés ; PAS la pointe) : filets `*-avant-groupe3b`, **37 jobs
selftest**, **crontab == registre** (aucun job FRAICHEUR, **pas de `jobs rattraper`** — c'est le 2ᵉ
déploiement), front reconstruit, `/readyz` 200 stable 25/25, manifeste q_v20 (433 229) intact. Le banc
`coherence-banc` de **03:45 a tourné ACHEVÉ** (id=29, faux_client 0) → le fix F3 tient en nocturne.

**Écran scénario — « Analyse en cours de mise à jour » VÉRIFIÉ LIVE** : avant le calcul des scénarios
q_v20, l'endpoint rend `run_calcule=false`, `n_selection=0`, **pas de 500** → l'écran affiche le message
(jamais erreur ni vide). Après le calcul q_v20 : `run_calcule=true`, `n_selection>0` → l'écran sert
l'analyse. Garantie Vic tenue.

**Scénarios V2 q_v20 (mode rapide) — ✅** : 433 229 parcelles, **1 631 s (~27 min)**, table 866 458 lignes
(keep + rebuild). **Mesure du mode rapide : ~27 min < 30 min** (sous le seuil ; pas de report du front —
et la fenêtre « vide » était de toute façon couverte par le message). foncier-public-1 appliqué nativement.

**Scénarios V2 q_v23 (mode rapide) — ✅** : 433 229 parcelles, **1 622 s (~27 min)**, 866 458 lignes.
foncier-public-1 natif. _Reconstruction enrich île différée_ : recalcule `compute_residuel` LIVE (~3 h/4
shards) alors que C/E/D_net sont DÉJÀ dans seq 18 (redondant) → à faire à la finalisation (après exigu-fix)
ou via un lecteur des colonnes persistées.

**Répartition statuts V2 q_v23 vs ALGO-FIX-1 §5 (q_v20) — écarts expliqués** :

| Conservation (keep) | q_v20 §5 | q_v23 | Δ |
|---|---:|---:|---:|
| Capacité estimée | 151 223 | 150 605 | −618 |
| **Hors de ce projet** | 144 492 | **146 194** | **+1 702** — équipements publics (FONCIER-PUBLIC-1) |
| À vérifier | 72 314 | 71 476 | −838 |
| Aucun ajout | 64 880 | 64 636 | −244 |
| À différer | 320 | 318 | −2 |

Reconstruction (rebuild) : **COMPUTE_PENDING « Calcul à compléter » 215 241** · OUTSIDE 146 194 · TO_VERIFY
71 476 · DEFERRED 318. L'absence de « Capacité estimée » (q_v20 §5 en avait 2 562, enrich Entre-Deux +
Saint-Denis) **vient du mode rapide** (0 enrich) — ce sera comblé par l'enrich (différé). Bandes V2 keep :
A 6 511 · B 42 954 · C 52 766 · D 48 374 · (0/∅) 282 624. **Foncier public** : 2 198 équipements → « Hors de
ce projet », 36 151 parcelles de terrain public drapeautées. Totaux 433 229 (keep & rebuild) ✓.

**Lecture** : la V2 q_v23 est cohérente avec ALGO-FIX-1 §5 ; seuls écarts = (1) +1 702 « Hors de ce
projet » (foncier-public-1, attendu), (2) reconstruction entièrement « Calcul à compléter » (mode rapide,
enrich différé), (3) micro-décalages du résiduel clippé. **Le faux positif `terrain_exigu` (§D) reste à
corriger (exigu-fix, §E) avant promotion.**

---

_Exécuté : A (déploiement + 4 incidents) ✅ · B (chaîne de nuit q_v23) ✅ · C (7 contrôles) ✅ + analyse §D
+ §E/§F préparées + §G déploiement 1 & scénarios V2.
Reste : scénarios V2 (demain, après merge origin/main + foncier-public-1) + finalisation. Commit, pas de merge._

---

## §H — Journal disque (12/11, consignes Vic)

Reprise 05:07 Réunion (hors fenêtre 01–05), déploiement 2 déjà live (`205d8ddf8`), servi seq 17 intact.

| Étape | Disque libre | Note |
|---|--:|---|
| Avant déploiement 2 (12/11 00:13) | 9,1 Go | après purge Nov 10 (superseded, Nov 11 vérifiée, 2 nets) |
| Après déploiement 2 (00:14) | 8,9 Go | code seul, readyz 25/25 |
| **Après delta exigu (≈09h)** | **7,9 Go** | −1 Go (résiduel seq 18 réécrit + Score + constructibilité des 72 083) |
| Garde sauvegarde 12:57 — avant | 7,9 Go | enrich NON lancé (décision A/B/C en attente Vic) ; hebdo Nov 8 vérifié lisible |
| Garde sauvegarde 12:57 — après suppr. daily Nov 11 | **15 Go** | +6,3 Go ; reste hebdo Nov 8 (1 net) → +Nov 12 à 13:30 = 2 nets, pas de saturation |

Plancher 3 Go respecté en continu. La daily Nov 11 était superseded par la Nov 12 imminente (Option C validée par Vic) ; hebdo Nov 8 `pg_restore -l` lisible avant suppression. Vérif Nov 12 programmée 14:05.

**Gros objets (pour l'agrandissement disque)** : `dryrun_cascade_results` 21 Go (q_v18_s/q_v19_s/q_v21/q_v22/q_v23 ~3 Go ch.), `score_labuse` 7,2 Go, `parcel_p_score_v2` 5,3 Go, `spatial_layers` 3,3 Go, sauvegardes 6,2–6,3 Go/pièce. Purge q_v21/q_v22 (~8–10 Go) exige un VACUUM FULL (temp ≈ 21 Go) → à faire après agrandissement.

**Garde 14:05 — vérif sauvegarde Nov 12** : écrite (6,76 Go) et `pg_restore -l` **LISIBLE** ✓. 2 nets sains (hebdo Nov 8 + daily Nov 12). Disque après écriture **8,0 Go** (pas de saturation, plancher 3 Go respecté). Option C réussie de bout en bout.

---

## §I — 12/11 : recalcul partiel exigu + enrich scénarios V2 + contrôles

Reprise 05:07 Réunion (hors fenêtre 01–05). Déploiement 2 live (`205d8ddf8`), servi seq 17 (q_v20) jamais touché, PROMEUT=0.

### §I.1 — Delta exigu (cible `terrain_exigu`, prouvée COMPLÈTE)
Code déployé vérifié actif (`exigu_fix_actif=True`) : témoins basculent comme attendu (AY0416 → 1 831 m² régain, DK0447 → 1 077 régain, AL0258 → `assiette_a_verifier`). **Cible = 72 083 parcelles `cause='terrain_exigu'` de seq 18** (= le set `emprise<SEUIL`, EXIGU-FIX-1 §1/§6). Recalcul : résiduel `--into-run 18` (4 shards) + cache `parcel_constructibilite` + Score q_v23.

**Preuve de complétude (2 cohortes × 500, condition Vic)** : 500 hors-cible au hasard + 500 hors-cible à capacité quasi nulle (`sdp_max<5`) → **1 000 / 1 000 IDENTIQUES à seq 18** (`q23_exigu_proof.py`). Le fix ne change AUCUNE parcelle hors cible → recalcul partiel valide.

**Résultat** — les 72 083 deviennent : **49 249 restent exigu (68 %, avec preuve géométrique)** · **14 215 régain capacité (20 %)** · **8 455 `assiette_a_verifier` (12 %, « à vérifier »)** · 146 `capacite_nulle` · 18 `redhibitoire`. seq 18 : total 433 229, `terrain_exigu` 72 083→49 249, `assiette_a_verifier` 0→8 455.

### §I.2 — Enrich scénarios V2 : option A tentée, NON retenue → B (ta condition 3)
Mesure : l'enrich live (`enrich=True`, `compute_residuel` 210 ms/parc) = **~28 h** sur l'île. Comme seq 18 persiste déjà la reconstruction (C=`sdp_max_m2`, E=`sdp_existante_m2`, D_net=`d_net_m2` ; 272 425 parcelles), j'ai écrit **option A** (`scripts/q23_scenarios_enrich_seq18.py`, commité) : substituer la sortie de `compute_residuel` par les colonnes de seq 18 (logique scénario inchangée, `zone_dominante` reste live 13 ms → île ~1,5 h).

**Preuve d'équivalence (condition 3) : 1 écart sur 508 parcelles** → arrêt, passage en B. Parcelle `97412000BW2165` : R persisté arrondi **80 → bande C** ; R live précis **79,55 → bande D**. Le barème de bande utilise la **précision complète** (`_precis`), que seq 18 ne persiste pas (colonnes `integer` ; condition 5 — champ absent, non inventé). Pour toute parcelle dont R est au bord d'un seuil de bande, arrondi ≠ précis. **A ne peut pas être identique à l'unité → B**, comme tu l'avais tranché (« au moindre écart, B pas C »). Script + preuve restent commités (condition 1).

**B appliqué** : batch scénarios V2 q_v23 rafraîchi en **mode rapide** (`enrich=False`), 433 229 parcelles, 866 458 lignes, ~28 min — reflète le delta (le batch de nuit était périmé pour les 72 083). La **fiche par parcelle enrichit déjà en live** côté client (reconstruction exacte à la demande) ; la « Reconstruction » reste « Calcul à compléter » dans la LISTE/effectifs (déférée). Le §D ci-dessous est calculé depuis les données autoritaires post-delta (`score_labuse` + reconstruction persistée seq 18).

### §I.3 — 7 contrôles (`q23_gate.py`)
| Contrôle | Résultat |
|---|---|
| Comptes parcelles | **433 229 = 433 229** (précédent) ✓ |
| Copropriétés actionnables | **0** ✓ |
| Rouge actionnables | **0** ✓ |
| Paliers changés | 755 / 433 229 (**0,17 %**) ✓ |
| Cohérence | 0 faux-client, achevée (voir §I.6) |
| Manifeste candidat | présent ✓ |
| Run complet (Score V2 + cascade) | ✓ |

**Verdict `ok=False`** — échecs=[] ; le seul point rouge est la **FRAÎCHEUR du banc de cohérence** (voir §I.6).

### §I.4 — §D : ce que q_v23 change (vs q_v20 servi)
**Analyse V2 des 72 083** (scénario keep) : **39 078 « Hors de ce projet »** (exclusion dure de cascade — PAS « trop étroit ») · **29 879 « À vérifier »** · 3 107 « Aucun ajout » · 19 « À différer ». Cohérent avec EXIGU-FIX-1 P1 (la cascade pré-empte les grandes parcelles en zone dure).

**Transition de bande q_v20 → q_v23 : 30 647 parcelles changent** de bande. Principales :
| q_v20 → q_v23 | n | lecture |
|---|--:|---|
| 0 → NC | 8 448 | ex-`terrain_exigu` → « À vérifier » (fin du faux « trop étroit ») — **honnête** |
| D → 0 | 7 302 | résiduel CLIPPÉ (q_v20 lisait non-clippé) — correction ALGO-FIX-1/RESIDUEL |
| 0 → HC | 6 292 | hors champ |
| C → D | 3 132 | descente d'une bande (clip) |
| 0 → A/B/C/D | 1 608 | **régain de capacité via exigu** (0/NC/HC → A-D) |
| C → 0 | 1 353 | clip |

bande 0 q_v23 = 210 641 au total. Parcelles qui passent À bande 0 (hors exigu) concentrées : La Possession 2 514, Saint-Joseph 2 417, Saint-Denis 2 324, Bras-Panon 901.

Grandes parcelles (> 1 000 m²) : la répartition autoritaire est celle d'EXIGU-FIX-1 §4.1 (9 933 → 59 % régain / 11 % exigu-preuve / 30 % à vérifier) ; côté seq 18 la surface n'est persistée que pour les constructibles, donc §D.4 local sous-compte (limite notée, pas un chiffre inventé).

### §I.5 — Recommandation
Le **blocage de Vic (faux positif `terrain_exigu`) est LEVÉ et prouvé** : la correction ne touche que la cible, les 1 000 témoins hors-cible sont identiques, les 5 témoins basculent correctement. Les changements de bande q_v23↔q_v20 sont (a) des **corrections honnêtes** (0→NC « à vérifier », 1 608 régains) et (b) les **corrections de clip résiduel déjà décidées** (ALGO-FIX-1 : q_v20 lisait un résiduel non clippé ; q_v23 = clippé, aligné sur la fiche). Ce ne sont pas des régressions.

→ **q_v23 est recommandé à la promotion** du point de vue du moteur et des contrôles substantiels — **MAIS la promotion est BLOQUÉE tant que le contrôle de cohérence n'est pas au VERT** (§I.6). Promotion = John sur ton ordre ; je ne promeus pas.

### §I.6 — Contrôle rouge (fraîcheur cohérence) : comment revenir au vert — PROMOTION BLOQUÉE JUSQU'AU VERT
Le banc `coherence-banc` (île, ~15 min, vérifie le run SERVI q_v20) a tourné cette nuit (03:45–04:00, `job_runs` 12565 : **achevé, faux_client=0**, 849 règles banc2, 20/25 gardes chasse). Le gate le compte **`coherence_frais=false`** car l'horodatage (04:00) est périmé pour le cycle courant → `ok=False`. q_v20 n'a PAS été modifié par cette opération (delta + batch = candidat q_v23 seulement) ; le verdict de fond est donc inchangé (0 faux-client), seul l'horodatage manque.

**Pour repasser au VERT, deux voies :** (1) **relancer le banc** `coherence-banc` **en tant qu'utilisateur `labuse`** (chemin exact du cron — flock OK) ; c'est fait à 16h (en cours), il produit un passage frais → gate vert ; (2) sinon, **attendre le passage de nuit** (cron 03:45 Réunion), qui le rafraîchit automatiquement. **PROMOTION BLOQUÉE JUSQU'AU VERT** : je ne propose pas de promouvoir sur un contrôle rouge, même expliqué.

### §I.7 — Défaut OUVERT : le wrapper de job sort en SILENCE sous root
**Observé** : `labuse jobs run coherence-banc` lancé **en root (`sudo bash`)** sort en **moins de 30 s sans rien faire** — aucun `job_runs`, aucun `coherence_runs`, stdout vide, process disparu. `sudo flock -n /var/lock/labuse-job-coherence-banc.lock echo` renvoie **« cannot open lock file: Permission denied »** (anormal pour root). En **utilisateur `labuse`** (propriétaire du verrou `labuse:labuse 0664`, chemin du cron), le même job **tourne normalement** (`jobs run` → `jobs exec`).
**Ce que ça empêche** : relancer hors-cycle un job sous flock (`coherence-banc`, `coherence-robinets`, `backup-postgres`…) depuis un shell root ; le wrapper échoue **silencieusement** (ni erreur ni code non-nul remonté à l'opérateur) au lieu d'échouer bruyamment. Un opérateur en sudo croit avoir relancé le banc alors que rien n'a tourné.
**Pas de contournement appliqué.** Correctif à faire (hors de cette opération) : le wrapper doit (a) détecter l'échec d'ouverture/acquisition du verrou et **sortir en erreur bruyante** (code ≠ 0 + message), (b) documenter que la relance manuelle se fait en `labuse`, pas en root.

---

## §J — Incident : cache SERVI modifié par le delta (12–13/11) + correction

**L'incident, tel quel.** L'étape 3 du delta exigu (`compute-constructibilite`, suivant EXIGU-FIX-1 §P3) a recalculé le cache **`parcel_constructibilite`** — qui est **servi** (lu par la fiche), **global et indépendant du run** — avec le code exigu-fixé, **à 05:00 le 12/11, alors que q_v20 est le run servi**. **54 094 lignes modifiées** (53 956 ajoutées + 138 bascules de cause), toutes `computed_at > 05:00`. Conséquence : des parcelles que q_v20 classe constructibles apparaissaient « non constructibles » sur la fiche → **faux-client** détecté par le banc (EZ0299). **Aggravé par deux erreurs de ma part :** (1) la sauvegarde propre immédiatement antérieure (**Nov 11 13:30**) avait été **supprimée à 12:57** lors de la garde disque, retirant la seule référence exacte pré-delta ; (2) **premier diagnostic faux** (« 2 143 lignes » — en réalité 54 094).

**Cause de fond (confirmée par Vic).** Le **code du déploiement 2 (exigu-fix) et le run servi q_v20 ne classent pas les mêmes parcelles** : le moteur déployé reclasse en `terrain_exigu`/`assiette_a_verifier` des parcelles que q_v20 tient pour constructibles. Tant que le cache est recalculé par ce moteur et que q_v20 reste servi, des contradictions apparaissent. La **résolution permanente est la promotion** (aligner moteur et run servi).

**Correction (a), validée par Vic — faite.** Filet `parcel_constructibilite_sauv_20261112` (copie datée, 65 360 lignes / 10 MB, **gardée pour la promotion**). Transaction atomique : **suppression des 53 956 ajoutées**, **138 remises à leur valeur du 10/11**, **378 disparues NON remises**. Contrôles avant COMMIT (sinon ROLLBACK), tous verts : **11 404 lignes** · écart vs dump 10/11 = **exactement les 378 disparues, rien d'autre** · **3 890 contradictions avec q_v20, pas une de plus**. Puis `fiche_cache` vidé des rendus > 05:00 ; EZ0299 + DM0322 vérifiées (cache absent, q_v20 constructible, cohérent).

**Analyse des 3 890 contradictions pré-delta (celles qui restent, PAS de moi).** Cause au cache : redhibitoire 1 414 · zone_transition 1 353 · terrain_exigu 919 · (vide) 124 · habitat_interdit 80. Bande q_v20 : **3 555 sont constructibles (A–D)**. **Date d'entrée au cache : 3 636 au 2026-07-29**, 254 au 12/11. Seules **259 / 3 890** sont dans les 72 083 exigu. Ce que q_v23 en dit : **3 631 constructibles**. Verdict du **moteur LIVE** sur 5 exemples : **tous constructibles**. → **Lequel a raison : le classement.** Pour 3 631/3 890, **q_v20, q_v23 ET le moteur live disent « constructible » — seul le cache dit « non »**, avec des lignes **figées au 29/07 jamais rafraîchies**. C'est un **défaut PRÉ-EXISTANT : cache `parcel_constructibilite` périmé**, la fiche contredit le classement depuis **>3 mois**, et **c'est la fiche qui a tort**. À traiter (invalidation/rafraîchissement du cache).

**Défaut du banc de cohérence (à traiter).** Le banc `coherence-banc` ne teste qu'un **échantillon** de l'île : `faux_client = 0` **ne prouve pas** l'absence de contradiction sur toute l'île (3 890 contradictions coexistaient avec `faux_client = 0` à 03:58). Le « vert » du banc est nécessaire mais non suffisant.

**Gel du calcul de nuit (13/11).** `calcul-nuit` (02:00, `flux-run` + contrôles + **promotion**) tournait encore (q_v24, incomplet ~18 %) et **faisait abstenir le banc** (anti-OOM). Ligne commentée dans `/etc/cron.d/labuse` (« gelé le 13/11 sur ordre de Vic »), calcul en cours **arrêté** (SIGTERM), `LABUSE_CALCUL_NUIT_PROMEUT=0` (auto-promotion désactivée → q_v24 n'aurait pas promu), lignes partielles q_v24 laissées (à purger au ménage). **Ce gel doit être reporté dans le registre sur `main`**, sinon le prochain déploiement réactivera calcul-nuit.

**Promotion : toujours BLOQUÉE jusqu'au vert de TOUS les contrôles.** Rien promu (résiduel servi seq 17, PROMEUT=0).
