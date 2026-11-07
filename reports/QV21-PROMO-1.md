# QV21-PROMO-1 — statuts q_v21, écart de paliers canonique, manifeste, E-2 Saint-Denis

Mandat Vic, **2026-11-07** (Réunion +04) depuis `~/Desktop/labuse-main` sur `main`, prod `labuse-vps`.
Go de Vic pour **écrire en prod dans les seules limites de ce mandat**, **jamais 01 h–05 h Réunion**
(travail fait ~21 h–23 h). Opus. `LABUSE_CALCUL_NUIT_PROMEUT=0` **conservé** (vérifié en prod) ;
**q_v20 reste le run servi** (manifeste prod intact). Aucun sous-agent.
Code commité + poussé sur `main` ; appliqué à la prod **par la base** (pas de redéploiement du
service — réservé à Vic). À lire d'abord : `reports/PROD-SUITE-1.md`.

---

## ★ VERDICT — contrôles de promotion de q_v21 rejoués, contrôle par contrôle

Rejoué avec le code corrigé contre la **base de prod** (q_v21 candidat vs q_v20 servi) :

| # | Contrôle | Avant | **Après** | Sens |
|---|---|---|---|---|
| 1 | **manifeste** du candidat | ❌ (toujours « absent ») | ✅ **vert** | q_v21 |
| 2 | **complétude** (score v2 + cascade) | ✅ | ✅ vert | — |
| 3 | **comptes** (candidat = servi) | ❌ 431 663 ≠ 433 229 | ❌ **ROUGE** | **hors mandat** |
| 4 | **copro** en palier actionnable (=0) | ✅ 0 | ✅ vert | — |
| 5 | **zone rouge** en palier actionnable (=0) | ❌ **2** | ✅ **0** | corrigé |
| 6 | **écart de paliers** (< 3 %) | ❌ **35,5 %** | ✅ **0,18 %** | corrigé |
| 7 | **cohérence** (0 écart / 0 erreur, frais) | ⏳ | ⏳ **EN ATTENTE** | banc 03 h 45 |

**Les trois contrôles que le mandat visait sont VERTS** (manifeste, zone rouge, écart de paliers ;
+ copro et complétude déjà verts). **« Tout vert » N'EST PAS atteint** : il reste **deux** points
non verts, **tous deux hors des quatre corrections demandées** —

- **(3) comptes ROUGE** : q_v21 score **431 663** parcelles, q_v20 **433 229** (−1 566). C'est
  l'**oscillation de l'univers de scoring par millésime** (PROD-SUITE-1 §5.3 : q_v21 = q_v16 = q_v11 ;
  q_v20 = q_v18) — **pas un bug localisé**, mais le gate exige l'égalité STRICTE. Le rendre vert
  demanderait de **re-scorer l'île sur l'univers de q_v20**, ce que le mandat **interdit**
  (« sans relancer le calcul de l'île »). **Décision Vic** : accepter l'écart connu, OU assouplir ce
  gate comme on a assoupli celui des paliers (tolérer l'oscillation documentée), OU re-scorer hors mandat.
- **(7) cohérence EN ATTENTE** (pas un échec) : le banc île tourne à **03 h 45** (fenêtre interdite) ;
  son dernier passage **07/11 03 h 58 = 0 écart / 0 erreur** mais a **> 12 h** → non « frais ». Il
  redeviendra frais **au banc de cette nuit** (verdict attendu vert). Je ne peux pas le forcer (01–05 h).

**Je m'arrête donc ici sans promouvoir** (c'était la consigne, et `PROMEUT=0`). La promotion revient à
**Vic, via John**, après : (a) déploiement du code (pour que le gate de prod lise le manifeste et
compare les paliers en canonique), (b) arbitrage du contrôle **comptes**, (c) banc de cohérence frais.

> **⚠ Le service de prod tourne encore l'ANCIEN code** (je n'ai pas redéployé — hors mandat). Les
> corrections de CODE sont sur `main` ; les corrections de DONNÉES (statuts q_v21, manifeste, E-2
> réinjection) sont EN BASE. Le gate NOCTURNE de cette nuit lira l'ancien `jobs_impl` → il reverra
> « manifeste absent » (faux négatif cosmétique) et `comptes` rouge, **ne promeut pas** (`PROMEUT=0`,
> et `_run_complet` → pas de re-score : **mes statuts recomposés survivent**). Tout rentre dans l'ordre
> au déploiement de Vic.

---

## 1. La CAUSE RACINE (différente du diagnostic PROD-SUITE-1)

PROD-SUITE-1 lisait les 35,5 % comme un **ré-étiquetage bénin** « écartée → sans signal ». La vraie
cause est plus simple et plus grave : **q_v21 a été scoré avec `LABUSE_ETAGE0_RUN=q_v20`**, or
**aucune cascade n'existe sous le label `q_v20`** (la cascade de q_v20 vit sous `q_v19_sources` ; q_v21
a la sienne sous `q_v21`). La lecture de l'étage 0 est donc **revenue VIDE** →

- **0 parcelle « Écartée »** dans q_v21 (q_v20 en a 153 283) ;
- les **153 638 exclusions dures** (disparues, foncier public, faux positifs…) sont retombées en
  « Sans signal » → **152 311 « écartée → sans signal »** = l'essentiel des 35,5 % ;
- les **2 zones rouges actionnables** (`97403000AH0307`, `97415000DE0377`) étaient, elles aussi, des
  parcelles **exclues à l'étage 0** qui, faute d'étage 0, ont gardé leur probabilité (0,142 / 0,130)
  et fui en « À suivre ». Les **26 919** parcelles 100 % PPR rouge sont **TOUTES** dans l'étage 0 de
  q_v21 : aucune n'est hors-étage-0 (le « masque zone rouge » ci-dessous n'en rattrape donc aucune de
  plus — mais il ferme la faille par principe).

**« Recalculer les statuts de q_v21 »** = rejouer `assign_paliers` sur **la cascade PROPRE de q_v21**,
sans relancer la cascade ni le scoring (déjà en base).

## 2. Les quatre corrections (code sur `main`, données en prod)

### 2.1 Zone rouge jamais actionnable — `scoring/p_v2/statuts.py` (+ test)
`assign_paliers` masque désormais vers « Sans signal » toute parcelle **entièrement en zone rouge**
(`risque_exclut` = fraction PPR rouge 100 %), **après** l'anti-churn et **avant** l'étage 0 (une rouge
aussi écartée reste « Écartée », motif plus spécifique). p_raw INTACT. Colonne optionnelle
(rétro-compatible, golden intact) ; le pipeline la peuple depuis la cascade `risques` du run (MÊME
source/motif que le gate `rouge_actionnables`). Tests : `tests/test_paliers1.py`
(`test_zone_rouge_totale_jamais_actionnable`, `…_etage0_prime`, `…_colonne_absente_sans_effet`,
`…_n_affecte_pas_une_parcelle_saine`) — reproduisent les 2 fuites (p ≈ 0,14 / 0,13 → Sans signal).

**Recompose des statuts de q_v21** (`labuse recompute-paliers --run q_v21`, cascade résolue = `q_v21`,
rejoue la VRAIE `assign_paliers`, n'écrit que `tier`) :

| tier | q_v21 AVANT | **q_v21 APRÈS** | q_v20 (servi) |
|---|---:|---:|---:|
| sans_signal | 431 229 | 278 565 | 279 144 |
| **ecartee** | **0** | **152 704** | 153 283 |
| a_suivre | 357 | 323 | 659 |
| priorite | 77 | 71 | 143 |

Les **2 zones rouges** `97403000AH0307` et `97415000DE0377` sont désormais **`ecartee`** (p_raw
inchangé 0,141844 / 0,130065). Étage 0 : 153 638 ; zones 100 % rouges : 26 919 (toutes déjà écartées).

### 2.2 Écart de paliers en NOTIONS IDENTIQUES — `tiers_client.canon_sql` + `jobs_impl`
Le gate comparait `a.tier IS DISTINCT FROM b.tier` sur les codes **bruts**. Il projette maintenant
chaque tier (ancien ou nouveau code) sur son **palier canonique** (`code_palier`, source unique) AVANT
de compter — un renommage (`reserve_fonciere`→`sans_signal`, `brulante`/`priorite`→`à suivre`) ne
« change » plus de palier. **Écart réel q_v21 vs q_v20 affiché = 0,18 % (774 / 430 310) < 3 %.**
Détail des 774 vrais mouvements : `à suivre→sans signal` 413, `sans signal→écartée` 353,
`sans signal→à suivre` 7, `à suivre→écartée` 1. Tests : `tests/test_canon_paliers.py`.

### 2.3 Manifeste du candidat écrit — `manifeste.{lire,ecrire,chemin}_candidat` + gate corrigé
Le contrôle `manifeste_present` renvoyait **toujours False** : il lisait `runs._manifeste` (import
**local** dans les fonctions de `runs`, jamais un attribut de module → `AttributeError` avalée). D'où
le « manifeste absent » permanent. Corrigé : il lit le **vrai manifeste candidat**
(`config/candidat_manifest.json`) et exige qu'il concerne CE run. `flux-run` et `recompute-paliers`
l'écrivent. **Écrit pour q_v21** (scoring_run q_v21, cascade q_v21, modèle q_v15
`d8520abaf2e0…`, 431 663, tiers ci-dessus) — **posé en prod** (`/opt/labuse/app/config/`). Traité comme
état runtime (gitignore + exclusion rsync, au même titre que `served_manifest.json`).

### 2.4 E-2 Saint-Denis — « lecture du bon type d'aléa » (`fiche_commune`)
Constat **durci** (live) : le WFS DEAL `ALEA_MOUVEMENT_TERRAIN` ne renvoie **AUCUNE** entité pour 97411,
**ni par `code_insee` ni par emprise (bbox)** — Saint-Denis est la **seule** des 24 communes sans aléa
**études** mvt. La piste « emprise de la requête WFS » du mandat est donc un **cul-de-sac prouvé** (la
bbox ne ramène que des zones de communes voisines). La capacité GetCapabilities ne porte que
`ALEA_MOUVEMENT_TERRAIN` (vide pour SD) et `PPR_APPROUVE` ; l'API Géorisques v1 n'a pas d'aléa mvt zoné.

**Le bon type d'aléa** pour SD = son **PPR « inondation ET mouvement de terrain »** approuvé et zoné
(12 zones `INONDATION_MOUVEMENT_DE_TERRAIN`). La fiche commune lit désormais la couverture mvt depuis
**ce zonage PPR i+mvt** (MÊME source DEAL) **quand la commune n'a aucune zone d'aléa études mvt à elle**
(gate sur la présence des zones propres, pas sur le %, qui comptait des slivers de voisins). Provenance
honnête servie (`mouvement_terrain_repli_ppr=true`, note de source).

**Réinjection par le chemin sûr** : `labuse ingest-georisques --commune 97411 --force` rejoué
(idempotent) — aléas DEAL 12 (inondation 6 + submersion 3+3, **toujours 0 mvt études**), **ppr 12 et
mvt-points 377 intacts** (vérifié avant/après : aucune perte).

**Vérifications :**
- **Fiche commune Saint-Denis** : `mouvement_terrain_pct` **0,1 % → 72,2 %** (PPR i+mvt), `repli_ppr=true` ;
  témoin **Saint-Paul inchangé** (90,2 %, `repli=false` — il a ses propres aléas études). Les 23 autres
  communes sont INCHANGÉES.
- **3 fiches de parcelles SD** (bloc « Pièges & risques », cascade servie) : `97411000HC0201` →
  **« PPR inondation et mouvement de terrain — zone rouge sur 3 %, INCONSTRUCTIBLE »** + aléa inondation
  fort ; `97411000IA0572` et `97411000ES0116` → **« PPR i+mvt — zone bleue 100 %, constructible sous
  prescriptions »**. Le mouvement de terrain est **bien surfacé** au niveau parcelle, via le PPR i+mvt.

> **Réserve E-2 honnête :** pour SD, `mouvement_terrain_pct` = `ppr_pct` = 72,2 % (son PPR est
> **entièrement** i+mvt), et la notion servie devient « zonage réglementaire PPR i+mvt » au lieu de
> « aléa études ». C'est le seul type d'aléa mvt zoné qui existe pour SD ; le drapeau `repli_ppr` et la
> note de source le disent. L'**effet LIVE** (fiche servie) exige le **déploiement du code par Vic** +
> le **rafraîchissement de `commune_contexte_cache`** pour SD (le cache sert l'ancienne valeur).

## 3. Preuves & périmètre

- **Écritures en prod (base uniquement)** : `parcel_p_score_v2.tier` de **q_v21** (152 704 statuts
  recomposés) ; `config/candidat_manifest.json` ; réingestion georisques 97411 (idempotente, sans perte).
  **q_v20 servi, `served_manifest.json`, `PROMEUT=0` : intacts.** Le service n'a **pas** été redéployé
  ni redémarré ; le front n'a **pas** été reconstruit.
- **Rejeu du gate** fait avec le code corrigé contre la base de prod (tunnel SSH, lecture/écriture DB).
- **Tests** : unitaires ciblés verts (paliers, canon, couverture moteurs) ; suite unitaire complète du
  hook de push **2 996 passés** ; secret-scan, front (tsc+vitest) et cohérence (6 témoins, 0 écart)
  verts à l'envoi sur `main`.
- Commits : code `fb2c…`/`f7e706cbb` (push 1) + le présent rapport & derniers correctifs (`%`→bind,
  gate E-2 « zones propres », exclusions manifeste candidat).

## 4. Ce qui reste à Vic (promotion via John)
1. **Déployer le code** (`deploy/scripts/deploy_app.sh` — restart service + build front, hors mandat) :
   le gate de prod lira alors le manifeste candidat et comparera les paliers en canonique ; la fiche SD
   servira 72,2 % mvt (après rafraîchissement du cache contexte de SD).
2. **Arbitrer `comptes`** (−1 566, oscillation d'univers) : l'accepter, assouplir ce gate (comme les
   paliers), ou re-scorer l'île — au choix.
3. **Banc de cohérence** de cette nuit (03 h 45) → frais et vert attendu.
4. Alors **promouvoir q_v21** (bascule). Rien à basculer tant que ces points ne sont pas tranchés.

## 5. Réserves & dette honnêtes
1. **`comptes` −1 566** non résolu (hors mandat — exige un re-score interdit). §VERDICT (3).
2. **Cohérence** en attente du banc nocturne (non forçable, 01–05 h). §VERDICT (7).
3. **E-2** : pas d'aléa **études** mvt pour SD dans AUCUNE source connectée ; servi depuis le PPR i+mvt
   (seul zonage mvt existant), `repli_ppr` signalé. Effet live = déploiement + cache contexte SD.
4. **Service de prod sur l'ancien code** jusqu'au déploiement de Vic (corrections de données déjà en
   base, sans danger ; re-score de nuit neutralisé par `_run_complet`).
5. **`risque_exclut`** ferme la faille par principe mais ne rattrape **aucune** parcelle de plus que
   l'étage 0 restauré (les 26 919 rouges y sont déjà) — défense en profondeur, pas un gain de comptage.
6. Le persistant `etage0_run="q_v20"` dans `p_score_v2_runs.params` de q_v21 est **inoffensif**
   (`resoudre_cascade_run` prend la cascade PROPRE d'abord) mais **trompeur** — à corriger si un run
   réutilise un jour cet enregistrement.
