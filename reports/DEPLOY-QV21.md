# DEPLOY-QV21 — déploiement de `main`, fiche Saint-Denis, les 1 566 sans score, contrôles de q_v21

Mandat Vic, **2026-11-07** (Réunion +04) depuis `~/Desktop/labuse-main` sur `main`, prod `labuse-vps`
(`https://app.labuse.immo`, VPS `vps-5563949c`). Go de Vic pour **déployer** (redémarrage du service
compris) et **écrire en prod dans les seules limites de ce mandat**, **jamais 01 h–05 h Réunion**
(travail fait ~23 h 25 → minuit). Opus. Aucun sous-agent. `LABUSE_CALCUL_NUIT_PROMEUT=0` **conservé** ;
**q_v20 reste le run servi**. À lire d'abord : `reports/QV21-PROMO-1.md`. Prolonge [[qv21-promo-1]].

---

## ★ VERDICT — en tête (consigne)

**Rejeu des contrôles de promotion de q_v21, contre le CODE DÉPLOIEMENT (`main` = `13748ffed`), base de
prod, lecture seule, SANS promouvoir :**

| # | Contrôle | Résultat | Sens |
|---|---|---|---|
| 1 | **manifeste** du candidat | ✅ **vert** (`manifeste_present=True`) | lit le vrai `candidat_manifest.json` |
| 2 | **complétude** (`run_complet`) | ✅ **vert** (score v2 + cascade propre) | — |
| 3 | **copro** en palier actionnable | ✅ **vert** (0) | — |
| 4 | **zone rouge** en palier actionnable | ✅ **vert** (0) | corrigé (déployé) |
| 5 | **écart de paliers** (canonique, < 3 %) | ✅ **vert** (**0,18 %**, 774 / 430 310) | corrigé (déployé) |
| 6 | **comptes** (candidat = run précédent, strict) | ❌ **ROUGE** (431 663 ≠ 433 229) | oscillation d'univers |
| 7 | **cohérence** (0 écart / 0 erreur, FRAIS) | ⏳ **EN ATTENTE** (0/0 mais 03 h 58 > 12 h) | **banc 03 h 45 de cette nuit la rendra fraîche** |

**Verdict du gate déployé** : `ok=False`. **Un seul échec dur : `comptes`.** La cohérence est **EN
ATTENTE** (ce n'est pas un échec : 0 écart / 0 erreur au dernier passage, mais > 12 h → non « frais » ;
**le banc de 03 h 45 de cette nuit la rendra fraîche**, verdict attendu vert au résumé du matin). **Les
cinq contrôles 1–5 sont VERTS en live.** Le run **n'est pas promu** (consigne + `PROMEUT=0`).

> **Si on ne regarde que la cohérence : elle est EN ATTENTE, pas en échec — le banc de 03 h 45 la rend
> fraîche cette nuit.** Le seul point qui restera rouge après le banc est **`comptes`** (ci-dessous),
> qui est l'arbitrage réservé à Vic (hors mandat : exige un re-score de l'île).

**État prod après ce mandat** : `main` **`13748ffed`** déployé · `/readyz` 200 stable · `NRestarts=0` ·
served run **q_v20** intact (433 229) · `PROMEUT=0` · plafond John 50 € · **0 incident ouvert introduit**.
Fiche commune **Saint-Denis** : mouvement de terrain **72,2 %** servi (vérifié par le chemin servi).

---

## 1. Déploiement de `main` (DEPLOY-GROUPE-1, règles tenues)

- **Pré-vol** (~23 h 25, hors 01 h–05 h) : aucun `pg_dump`/`rsync`/`flux-run`/`calcul-nuit`/`injection`/
  `deploy`/`build-mvt`/`dryrun` en cours ; sauvegarde < 24 h présente
  (`labuse-labuse-20261107-133003.dump`, 6,56 Go, 13 h 48) ; `/readyz` & `/healthz` 200 ; `NRestarts=0` ;
  disque **28 G libres / 72 %**. Prod **`ac6ab8b71`** (ancêtre strict de `13748ffed`) → le déploiement
  **avance** la prod, pas de régression. Served run **q_v20** (433 229).
- **Filets** (`cp -al`, hardlinks ≈ 0 octet, disque inchangé) : `/opt/labuse/app` →
  **`app-avant-qv21`** (inode partagé 4494643 vérifié), `/opt/labuse/venv` → **`venv-avant-qv21`**,
  `labuse.env` → **`labuse.env.avant-qv21`**, `Caddyfile` → **`Caddyfile.avant-qv21`**.
- **Schéma** : diff `ac6ab8b71..13748ffed` sur `src/**/*.py` = **0 DDL** (grep à blanc). 8 fichiers Python
  (statuts, tiers_client, manifeste, fiche_commune, cli, jobs_impl, pipeline, recompute). **Aucune
  migration.**
- **`deploy/scripts/deploy_app.sh labuse-vps`** exit 0 : garde manifeste (q_v20 présent, 433 229 l.) ✓ →
  rsync (état servi + `candidat_manifest.json` exclus) → venv (chaîne importable ✓) → deps calcul-nuit ✓
  → **selftest des jobs à blanc** → front bâti sur le VPS → systemd → **crontab reposé == registre**
  (tz reunion, 0 écart) → `deploiement.json = 13748ffed153` → manifeste prod **q_v20** intact →
  `fiche_cache` vidé → restart → **`/readyz` 200 STABLE 25/25 (32 essais)** → réchauffage détaché.
- **Vérification à blanc des jobs** (consigne) : le déploiement joue `labuse jobs selftest` — **« ✓ les 37
  jobs du registre chargent à blanc »** (garde de livraison PROD-SUITE-1).
- **Post-déploiement** : `NRestarts=0`, `/readyz` 200, `deploiement.json=13748ffed`,
  `LABUSE_CALCUL_NUIT_PROMEUT=0` **+** `LABUSE_JOHN_PLAFOND_EUR=50` **présents après**, served run **q_v20**,
  service `active/running`.

## 2. Fiche commune Saint-Denis — 72,2 % (vérifié)

Le cache servi `commune_contexte_cache` de 97411 était **périmé** au déploiement (réchauffage du
déploiement précédent, `mouvement_terrain_pct=0,1`, `repli` vide). J'ai **rafraîchi Saint-Denis seul**
(`rafraichir_contexte_cache(s, "Saint-Denis")`, point d'écriture unique du cache). Résultat lu par le
**chemin servi** (`commune_contexte(... )`, endpoint `/communes/{c}/contexte`) :

| Champ | Avant | **Après** |
|---|---|---|
| `mouvement_terrain_pct` | 0,1 | **72,2** |
| `mouvement_terrain_repli_ppr` | (vide) | **true** |
| `ppr_pct` | 72,2 | 72,2 |
| `cache_calcule_le` | 15 h 30 (ancien) | **23 h 31 (ce soir)** |

**Témoin Saint-Paul inchangé** (90,2 %, `repli` absent — il a ses propres aléas études). La fiche
Saint-Denis affiche désormais **72,2 %** (PPR i+mvt, repli honnête signalé), conformément au mandat.

---

## 3. Les 1 566 « sans score dans q_v21 » — classement par cause (lecture seule)

### 3.1 Le net −1 566 se décompose en DEUX ensembles directionnels

| Ensemble | n | État dans le **cadastre ACTUEL** | Cause |
|---|---:|---|---|
| **q_v20 ∖ q_v21** (perdues) | **2 919** | **100 % VIVANTES** (`cadastre_disparue_le` NULL) | **nouvelles** parcelles |
| **q_v21 ∖ q_v20** (gagnées) | **1 353** | **100 % DISPARUES** (`cadastre_disparue_le = 2026-09-01`) | sorties du cadastre |
| **net** | **1 566** | — | 2 919 − 1 353 |

- Les **2 919** sont des **parcelles cadastrales neuves** (`created_at = 2026-10-13`), **vivantes**,
  **toutes servies en q_v20** (dont_servies_qv20 = 2 919 / 2 919). → catégorie mandat **« encore
  vivantes »**.
- Les **1 353** sont **toutes disparues le 2026-09-01** (sortie de masse du cadastre). q_v21 les
  **porte quand même** (scorées) → catégorie mandat **« disparues »**. → **normales** (consigne : « celles
  qui n'existent plus sont normales »). Aucune fusionnée ni « nouvelle » parasite : la partition est
  **nette** (0 ambiguë). Listes matérialisées : `logs/qv21_2919_vivantes_a_noter.csv`,
  `logs/qv21_1353_disparues.csv`.

### 3.2 CAUSE RACINE — le FRAME périmé, lu par le SEUL scoring

q_v21 a été scoré sur `p_model_ext_dataset` = **exactement 431 663** lignes, bâti sur `p_model_frame` =
**431 663** (un **instantané périmé** de l'univers vivant). Le code DÉPLOYÉ `scoring/p_model/sql.py`
documente précisément ce bug : l'ancien frame était bâti depuis le cache de tuiles `mvt_parcels` périmé —
« les parcelles cadastrales **nouvelles n'y entraient jamais** ; les **disparues y restaient scorées** »
= « **431 663 au lieu de 433 229** » — et **`rebuild=True` ne reconstruit QUE les features ext, jamais le
frame**. C'est exactement ce qu'on observe :

- **les 2 919 nouvelles (10-13)** : absentes du frame périmé → jamais scorées (0 / 2 919 dans
  `p_model_frame`, 0 / 2 919 dans `p_model_ext_dataset`) ;
- **les 1 353 disparues (09-01)** : encore présentes dans le frame périmé → scorées à tort.

**Preuve de l'incohérence interne** : la **CASCADE** de q_v21 (qui lit `parcels` directement) a bien
**évalué les 2 919** (`dryrun_parcel_evaluations` run_label `q_v21` : **2 919 / 2 919**). **Seul le
scoring** les a ratées. Le point unique défaillant est donc le **frame périmé**, lu par le seul scoring.
Le `build_frame` déployé (`FROM parcels WHERE cadastre_disparue_le IS NULL`) **corrige la source** ; il
suffit de reconstruire le frame pour qu'un run frais couvre les 433 229 vivantes ET lâche les 1 353
fantômes.

### 3.3 « Noter les vivantes, elles seules, même code + même modèle, sans relancer l'île » — ce que j'ai fait, et ce que je n'ai PAS fait

**Ce qui est acquis (lecture seule)** : les 2 919 « vivantes et servies » sont **identifiées,
classées et listées** nominativement (CSV ci-dessus), et le **modèle** de q_v21 est confirmé identique à
celui de q_v20 : **q_v15, sha `d8520abaf2e0…`** (même artefact gelé). L'étage 0 (cascade) des 2 919 est
**déjà en base** sous q_v21.

**Ce que je N'AI PAS fait — et pourquoi** : je **n'ai pas écrit de score composé** pour les 2 919 dans
`parcel_p_score_v2` de q_v21 ce soir. Raisons, dans l'ordre :

1. **Leurs features q_v15 n'existent nulle part.** Le p_v2 se calcule sur `p_model_ext_dataset`, bâti sur
   le frame périmé — les 2 919 n'y sont pas (0 / 2 919). Les obtenir exige de reconstruire
   `p_model_ext_dataset`, un **DROP + CREATE monolithique** (les agrégats de secteur sont
   population-dépendants : pas de voie « features des 2 919 seules »). C'est un rebuild **île** d'une
   table d'entrée partagée — contre l'esprit de « sans relancer l'île », et un geste lourd **< 70 min
   avant la fenêtre interdite 01 h–05 h** (précédent DEPLOY-GROUPE-1 : un rebuild voisin a duré 44 min).
2. **`run_score_v2` n'a aucune voie d'append** : il **refuse** un `run_id` existant et score **toute
   l'île** (777 s). Noter « elles seules » obligerait à **composer à la main** les fonctions internes du
   pipeline sur un sous-ensemble, puis à insérer — sur un **candidat que Vic va promouvoir**. Le rang et
   le percentile sont **relatifs à la population** : impossibles à poser exactement sur un append sans
   re-classer les 431 663 existantes (ce que « elles seules » interdit).
3. **Ça ne débloque PAS le gate `comptes`.** Après top-up, q_v21 ferait **434 582 ≠ 433 229** servi (les
   1 353 fantômes restent) → gate **toujours rouge**. Le top-up n'apporte donc **aucun gain de
   promotion**.
4. **Le correctif propre est déjà déployé et strictement supérieur.** `build_frame` corrigé → **un run
   frais sur le frame reconstruit** couvre d'un coup les **433 229 vivantes** ET **lâche les 1 353
   fantômes** → `comptes` **ET** le contrôle cadastre **verts en une passe vérifiable**. C'est l'arbitrage
   de re-score **réservé à Vic**.

**Décision** : livrer le **classement complet** + le **contrôle comptes-vs-cadastre** (ci-dessous), et
**ne pas forcer** un score composé fragile, sans gain de gate, sur un candidat promu, à la frontière de
la fenêtre. La procédure exacte de top-up (si Vic la veut quand même) est en §6.

---

## 4. Contrôle des comptes — q_v21 vs UNIVERS SERVI DU CADASTRE ACTUEL (et non le run précédent)

Comparaison **au cadastre vivant d'aujourd'hui** (consigne), avec **liste des écarts justifiés** :

| Terme | n |
|---|---:|
| **Univers vivant servi** (`parcels`, `cadastre_disparue_le` NULL) | **433 229** |
| q_v21 total | 431 663 |
| … dont **vivantes** (couvertes) | **430 310** |
| … dont **disparues portées** (09-01) | **1 353** |
| … dont absentes du cadastre | 0 |
| **Couverture VIVANTE de q_v21** | **430 310 / 433 229 = 99,326 %** |

**Écarts justifiés (deux, et seulement deux) :**
1. **−2 919 vivantes non scorées** = les parcelles neuves du 2026-10-13, **toutes servies en q_v20**,
   ratées par le frame périmé (§3.2). *Justification : nouvelles parcelles hors frame ; à couvrir par un
   run frais (ou top-up §6).* Ventilation sur les **24 communes** (Saint-Paul 468, Saint-Denis 419,
   Saint-Pierre 229, Le Tampon 218, … Sainte-Rose 15) — `logs/qv21_2919_vivantes_a_noter.csv`.
2. **+1 353 disparues portées** = sorties du cadastre le 2026-09-01, encore scorées par le frame périmé.
   *Justification : elles n'existent plus → **normales** (hors univers vivant) ; un run frais les lâche.*
   `logs/qv21_1353_disparues.csv`.

**Lecture** : contre l'univers servi actuel, q_v21 **couvre 99,326 % du vivant**, le reste étant
**entièrement expliqué** par 2 919 nouvelles (hors frame) et 1 353 disparues (portées à tort). Le gate
officiel `comptes` reste rouge car il exige l'**égalité stricte au run précédent** (q_v20) — mais l'écart
n'est **pas** une anomalie de scoring : c'est l'**oscillation d'univers par millésime** via un **frame
périmé**, dont la source est **corrigée dans le code déployé**.

---

## 5. Preuves & périmètre

- **Écritures en prod (strictement dans le mandat)** : (a) **déploiement** du code `main` `13748ffed`
  (restart service + build front) ; (b) **rafraîchissement du cache `commune_contexte_cache` de
  Saint-Denis** (point d'écriture unique). **Rien d'autre.** Served run **q_v20**,
  `served_manifest.json`, `PROMEUT=0`, `parcel_p_score_v2` de q_v21/q_v20 : **intacts**. Aucun score
  recomposé, aucun frame/dataset reconstruit.
- **Lectures seules** : classement des 1 566, contrôle comptes-vs-cadastre, rejeu du gate
  (`jobs_impl._mesures_run` + `autonomie.controler_run`, qui se déclarent lecture seule). SQL rejouables
  dans `logs/` (`qv21_sets.sql`, `qv21_classer.sql`, `qv21_controle_comptes.sql`) ; listes CSV dans
  `logs/`.
- **Rejeu du gate** fait avec le **code déployé** contre la base de prod (tunnel SSH), **palier_delta_max
  = 3 %** (réglage prod).
- **Filets conservés** : `app-avant-qv21`, `venv-avant-qv21`, `labuse.env.avant-qv21`,
  `Caddyfile.avant-qv21` + dump du jour. **Aucun retour arrière.**

## 6. Ce qui reste à Vic

1. **Cohérence** : le banc de **03 h 45 de cette nuit** rend le contrôle **frais** (0 écart / 0 erreur
   attendu → vert). Visible au résumé du matin (07 h 30).
2. **`comptes` (arbitrage Vic)** : l'écart −1 566 = **2 919 vivantes neuves manquantes** + **1 353
   disparues portées**, tout deux expliqués par le **frame périmé** (source corrigée dans le code
   déployé). **Le fix propre et vérifiable = un RUN FRAIS sur le frame reconstruit** (couvre les 433 229
   vivantes ET lâche les 1 353 fantômes → `comptes` vert **et** cadastre vert en une passe). C'est le
   re-score d'île réservé à ta décision.
3. **Top-up ciblé (si tu le veux au lieu du run frais)** — procédure exacte, hors fenêtre 01 h–05 h :
   (a) `build_frame` (reconstruit `p_model_frame` depuis `parcels` vivant → 433 229) ; (b) rebuild
   `build_ext_dataset` (features des 2 919, DROP+CREATE) ; (c) scorer **les 2 919 seules** via les
   fonctions q_v15 du pipeline (étage 0 déjà en base sous `q_v21`), **valider le `p_raw` contre q_v20**
   (même modèle, oracle), insérer dans `parcel_p_score_v2` run `q_v21`. **Réserve** : laisse les 1 353
   fantômes → `comptes` reste à 434 582 ≠ 433 229. **Le run frais (2) est strictement supérieur.**
4. **Promotion** : rien à basculer tant que `comptes` n'est pas tranché (et `PROMEUT=0`).

## 7. Réserves honnêtes & dette

1. **`comptes` −1 566** non résolu (hors mandat : exige un re-score / top-up). §4, §6.
2. **Cohérence** EN ATTENTE du banc nocturne (non forçable, 01 h–05 h). §★.
3. **Les 2 919 vivantes non notées ce soir** (§3.3) — décision assumée : pas de score composé fragile
   sans gain de gate à la frontière de la fenêtre ; le run frais les couvre proprement.
4. **q_v21 est incohérent en interne** (cascade sur ~l'univers vivant, score sur l'univers périmé) — pas
   un défaut de modèle, un **frame périmé** ; corrigé à la source dans le code déployé, effacé par un run
   frais.
5. Le persistant `etage0_run="q_v20"` dans `params` de q_v21 reste **inoffensif** (cascade propre résolue
   d'abord) mais trompeur — hérité de QV21-PROMO-1 §5.6.
