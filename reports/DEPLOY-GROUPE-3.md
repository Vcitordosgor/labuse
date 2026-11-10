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

---

_Exécuté : A (déploiement + 4 incidents) ✅ · B (chaîne de nuit q_v23) ✅ · C (7 contrôles) ✅ + analyse §D.
Reste : scénarios V2 (demain, après merge origin/main + foncier-public-1) + finalisation. Commit, pas de merge._
