# OPS-URGENCE-3 — q_v21, artefacts q_v15 livrés, calcul-nuit, verrous V1c/V6b, résumé de John

Mandat Vic, lancé le **2026-11-06** (après-midi, Réunion +04) depuis `~/Desktop/labuse-main` sur `main`,
prod `labuse-vps` (`vps-5563949c`, `app.labuse.immo`). Go de Vic pour écrire en prod **dans les seules
limites de ce mandat**, **jamais 01 h–05 h Réunion**. `LABUSE_CALCUL_NUIT_PROMEUT=0` conservé. Modèle
Opus. Branche de code `fix/ops-urgence-3` (`c76fd3136`), déployée en prod ; rapport sur `main`.

À lire d'abord : `reports/OPS-URGENCE-2.md` (ce mandat prolonge le q_v21 lancé là-bas).

---

## ★ Pour Vic — le verdict des contrôles de promotion de q_v21, contrôle par contrôle

> **q_v21 est COMPLET (cascade + scoring faits, 0 erreur) mais les contrôles de promotion le REFUSENT :
> ne pas le promouvoir en l'état.** Il reste **candidat, non promu** ; le run servi est toujours
> **q_v20** ; `PROMEUT=0` conservé — rien n'a basculé, la bascule reste ta décision. Voici les
> **contrôles de promotion**, joués maintenant à la main (lecture seule), **sans promouvoir** :

| # | Contrôle | Résultat | Mesure |
|---|---|---|---|
| 1 | **Manifeste** du candidat | ❌ ÉCHEC | manifeste candidat absent/illisible (lecture best-effort — le signal le plus faible) |
| 2 | **Complétude** (score v2 + cascade) | ✅ OK | cascade propre + score v2 présents (`_run_complet` = vrai) |
| 3 | **Comptes** de parcelles | ❌ ÉCHEC | candidat **431 663** ≠ servi **433 229** (**−1 566**) |
| 4 | **Cohérence** | ⏳ EN ATTENTE (vert mais pas frais) | banc du **06/11 03:58 = 0 écart, 0 erreur** de lecteur ; > 12 h → règle de fraîcheur |
| 5 | Aucune **copropriété** actionnable | ✅ OK | **0** |
| 6 | Aucune **zone rouge** actionnable | ❌ ÉCHEC | **2** parcelles entièrement en PPR rouge, palier actionnable (doctrine E-010 : doit être 0) |
| 7 | **Écart de paliers** | ❌ ÉCHEC | **35,5 %** (152 772 / 430 310) ≫ seuil **3 %** — dérive anormale |

> **Décision : REFUS — NE PAS PROMOUVOIR q_v21 en l'état.** Les contrôles font leur travail : q_v21 est
> **complet** (il a scoré tout son univers, 0 erreur) mais **4 contrôles sur 7 refusent** la promotion —
> surtout l'**écart de paliers de 35,5 %** (un run qui reclasse plus d'un tiers des parcelles n'est pas
> promouvable sans comprendre pourquoi) et la **divergence de comptes** (−1 566 vs le servi). q_v21 reste
> **candidat, non servi** ; le servi reste **q_v20**. `PROMEUT=0` conservé — rien n'a basculé.
> Comprendre la cause de ces dérives (données/univers/modèle q_v15) avant toute bascule = ta décision.
>
> Deux cartes rouges de sécurité **corrigées** par ce mandat : **V1c** (tables orphelines) et **V6b**
> (banc de cohérence). Il reste **V3b** (une « eau ancienne » DPE) — **hors de ce mandat**, c'est un
> geste de ré-ingestion DPE (détail §5).

---

## 1. État de q_v21 — complet, sans doublon, sans trou

### 1.1 Les unités parallèles ont-elles fini ?
**Oui.** Les unités transitoires `qv21-w1..w4` + `qv21-finisher` d'OPS-URGENCE-2 **ont toutes terminé**
(aucune n'existe plus ; `systemctl list-units qv21*` vide, aucun `flux-run`/`dryrun-evaluate` en vol).
La **cascade** de q_v21 est **complète**.

### 1.2 Parcelles calculées contre 433 229 — doublons, trous
| Mesure | Valeur |
|---|---:|
| `dryrun_parcel_evaluations` (cascade q_v21) — total | **433 229** |
| — distinctes (`count(distinct parcel_id)`) | **433 229** |
| **Doublons** (total − distinct) | **0** |
| Univers servi (score_labuse q_v20) | 433 229 |
| **Trous** (manquantes vs univers servi) | **0** |

La cascade q_v21 couvre **exactement** l'univers servi (433 229), **0 doublon**, **0 trou**. (La table
`parcels` compte 434 582 lignes : l'écart de 1 353 = les parcelles hors scoring — slivers, mêmes
exclusions que q_v20 ; **non** un trou de q_v21.)

### 1.3 Le passage de calcul-nuit de 02 h a-t-il touché ce run ?
**Oui — et c'est là qu'il a planté.** La passe programmée du **06/11 02:00** a tourné, relancé
`flux-run q_v21`, trouvé la **cascade déjà faite** (sautée) puis attaqué le **SCORING** — qui a
**échoué en 38 s** (`code 1`) sur l'absence des artefacts q_v15 (§2). C'est pour cela que, à mon
arrivée, q_v21 avait sa **cascade à 100 %** mais **aucun scoring** (`score_labuse`/`parcel_p_score_v2`/
`p_score_v2_runs` vides pour q_v21). Les nuits précédentes (03→05/11) avançaient la cascade ; le 06/11
l'a trouvée finie et est tombé au scoring.

### 1.4 Achèvement du scoring (geste de ce mandat)
Le scoring manquait **uniquement** à cause des artefacts absents (§2). Une fois ceux-ci livrés par le
déploiement, j'ai **terminé q_v21** : `flux-run --resume --label q_v21 --recette q_v15` (unité
`qv21-score`, `nice`/`ionice idle`, mémoire capée 8 G, hors fenêtre interdite). **Scoring terminé en
~15 min (`Result=success`, exit 0)** : **`parcel_p_score_v2`(q_v21) = 431 663**, `p_score_v2_runs` = 1.
Les unités temporaires sont **retirées** (`qv21-score` auto-collectée ; `qv21-w*`/`finisher`
d'OPS-URGENCE-2 déjà parties).
**`PROMEUT=0` conservé** : `flux-run` ne promeut jamais — q_v21 reste candidat.
`score_labuse` pour q_v21 reste à **0**, et c'est **normal** : il se construit **À LA BASCULE**, pas par
`flux-run` (« NON servi — bascule manuelle »). Les contrôles de promotion lisent `parcel_p_score_v2`
(score v2), pas `score_labuse`.

---

## 2. Pourquoi calcul-nuit a planté — « Artefacts q_v15 absents (reports/q-v15/) »

### 2.1 La cause
Le SCORING d'un run (le cœur du calcul de nuit, `flux-run --recette q_v15`) **LIT des artefacts de
modèle GELÉS** : le modèle du Signal `reports/q-v15/{FREEZE-q_v15.json, artifacts-q_v15-12m.joblib,
-24m.joblib}` (`scoring/p_v2/qv15.py:verify_artifacts`). **Absents → `RuntimeError: Artefacts q_v15
absents (reports/q-v15/)`** (exactement l'erreur du 06/11 02:00).

**Pourquoi absents du VPS ?** Le rsync de déploiement **EXCLUT `/reports`** (`deploy_app.sh`, ligne
`--exclude /reports`) — `reports/` est traité comme un dossier d'audit/dev. Or les **modèles gelés y
vivent** (committés en git, mais jamais expédiés). **Exactement la même classe de bug** que l'ÉCHANTILLON
de cohérence sous `/docs` (OPS-URGENCE-2 §3.2) : un fichier *suivi en git* mais *jamais livré*. Le VPS
n'avait sous `reports/` que `m36-foncier/FREEZE-scoring2026.json` (reliquat d'une vieille copie), même
pas le `.joblib` — donc **aucun** scoring de run frais n'était possible en prod.

### 2.2 La correction — les fichiers dont le calcul a besoin sont livrés avec le code
`deploy_app.sh` (OPS-URGENCE-3) :
- **REDÉPOSE explicitement** les **12 artefacts** de modèle que le calcul lit, par le même mécanisme que
  l'ÉCHANTILLON (`rsync -R`, chemins relatifs recréés) : `reports/q-v15/` (Signal), `reports/m36-foncier/`
  (modèle de base + `fold2025`), `reports/q-v12/` et `reports/q-v14/` (recettes candidates). Sans lever
  l'exclusion générale de `/reports`.
- **GARDE FAIL-LOUD** : avant l'envoi, refus si un artefact manque **en local** ; après l'envoi, refus si
  un artefact manque **en prod**. **Plus jamais un artefact dont le calcul dépend ne part en silence.**
  (Déploiement vérifié : `artefacts de modèle (12) livrés et présents en prod ✓`.)

> *Relocalisation durable hors `reports/` (dans l'arbre toujours livré)* = la vraie cible long terme,
> notée en dette (comme pour l'ÉCHANTILLON) ; la garde fail-loud ferme le risque entre-temps.

### 2.3 calcul-nuit ne relance plus un run déjà complet
`jobs_impl.calcul_nuit` (OPS-URGENCE-3) : **avant** de lancer `flux-run`, il demande à la garde canonique
de bascule `bascule_flux._run_complet` (score v2 **ET** cascade présents) si le run est **déjà complet**.
Si oui, il **ne relance rien** et **passe DROIT aux contrôles + verdict**. Un run fini n'est donc plus
re-scoré pour rien — et, surtout, ne retombe plus en « calcul-nuit en échec » sur un scoring qui
re-tourne (c'est ce qui a transformé un run fini en incident le 06/11). Couvert par un test unitaire
(`test_ops_urgence_3.py` : flux-run **interdit** quand `_run_complet` dit oui).

---

## 3. Contrôles de promotion de q_v21 — joués, SANS promouvoir

Joués en lecture seule (`autonomie.controler_run` sur les mesures réelles `_mesures_run`, candidat q_v21
vs précédent servi q_v20), **aucune promotion**. Verdict détaillé :

1. **Manifeste du candidat — ❌ ÉCHEC.** `_manifeste_candidat_present(q_v21)` = faux. C'est une lecture
   *best-effort* (le signal le plus faible des sept) ; `flux-run` n'écrit pas de manifeste candidat
   relu par ce contrôle. À noter comme tel, pas un drame en soi — mais c'est un refus formel.
2. **Complétude — ✅ OK.** `_run_complet(q_v21)` = vrai (« run complet (score v2 + cascade — cascade
   propre au run) »).
3. **Comptes de parcelles — ❌ ÉCHEC.** candidat **431 663** (distinct 431 663) ≠ servi q_v20 **433 229**
   (distinct 433 229) → **−1 566**. La **cascade** q_v21 couvre bien 433 229 ; c'est le **score v2**
   (univers `p_model_ext_dataset`) qui vaut 431 663 aujourd'hui alors que q_v20 en portait 433 229 — un
   rétrécissement de l'univers de scoring entre le 21/10 (q_v20) et maintenant. Le contrôle le refuse.
4. **Cohérence — ⏳ EN ATTENTE (mais verte).** dernier banc île = **06/11 03:58**, `faux_client=0`,
   `erreurs_lecteur=0` (aucun client ne lit une valeur fausse) → **cohérence verte**. Mais à 18 h il a
   > 12 h → `coherence_frais=False` → le contrôle la classe « en attente » (3ᵉ état OPS-NUIT-2, **pas**
   un échec). Le banc de 03h45 la rafraîchira ; je n'ai PAS relancé un banc de 15 min puisque le verdict
   global est déjà REFUS sur d'autres contrôles.
5. **Aucune copropriété actionnable — ✅ OK.** `copro_actionnables = 0`.
6. **Aucune zone rouge actionnable — ❌ ÉCHEC.** `rouge_actionnables = 2` : 2 parcelles **entièrement**
   en PPR zone rouge (fraction ≥ 100 %) classées dans un palier actionnable (doctrine E-010 : doit être
   0). À instruire avant toute bascule.
7. **Écart de paliers — ❌ ÉCHEC.** **35,5 %** des parcelles communes changent de palier vs q_v20
   (**152 772 / 430 310**) ≫ seuil **3 %**. C'est le refus le plus fort : un run qui reclasse **plus
   d'un tiers** du territoire est, par construction du garde-fou, une **dérive anormale** à comprendre
   (univers/données/recette) avant de servir quoi que ce soit.

**Verdict global : REFUS (`controler_run.ok = False`).** q_v21 reste candidat, non servi. C'est
exactement le rôle de ces contrôles : **empêcher une promotion silencieuse d'un run qui a beaucoup
bougé**. Rien n'a basculé (`PROMEUT=0`). La suite — comprendre la dérive (−1 566 comptes, 35,5 % de
paliers, 2 rouge) — est une décision/instruction pour Vic, **hors** du périmètre de ce mandat
(qui était : *terminer* q_v21 et *jouer* les contrôles sans promouvoir).

---

## 4. Verrous V1c et V6b — la cause de chacun, corrigée

### 4.1 V1c — `verrou_tables_orphelines` : **casse → a_decider** (corrigé)
**Cause.** Le verrou calcule les tables **orphelines** (schéma moins la carte du registre) et CASSE si
l'une n'a **aucune action proposée**. Au 06/11 il listait **8 orphelines sans action** : les **7 tables
de John** (`john_carnet`, `john_conversations`, `john_ecarts_acceptes`, `john_journal`, `john_messages`,
`john_resume`, `john_veille` — mémoire du second de bord, posées par `feat/john-taylor-2`) **+**
`job_premiere_vue` (l'ancre de la vigie « jamais réussi » d'OPS-NUIT-2). **Elles existaient en base mais
n'avaient jamais été déclarées à la carte** — le trou classique « on ajoute la table, on oublie le
registre ».

**Correction** (`registre/tables.py`, `TABLES_EXPLOITATION`) : les **8 tables déclarées** (ce sont des
tables d'exploitation : la machine elle-même). Elles **appartiennent désormais à la carte** → **ne sont
plus des orphelines**. Vérifié en prod après déploiement : **V1c n'est plus `casse`** (verdict
`a_decider` : 27 orphelines **toutes avec action proposée** — ce sont de vieilles tables de travail
`agent_*`, `_cad_sm1_*`, `m50_marker`… en attente de **ta** purge, lot 1.4 « à décider », **pas** un
échec de sécurité).

### 4.2 V6b — `verrou_coherence_banc` : **casse → ok** (corrigé)
**Cause.** La 4ᵉ mâchoire rejoue le **golden des 7 témoins** (valeurs servies figées) et CASSE sur toute
dérive non acceptée. Au 06/11 : **8 dérives**, toutes « **notion disparue** » sur `surface_parcelle_m2`
(7 témoins) + un `hauteur_faitage_m`. Ce n'est **pas** une perte de donnée : **ECARTS-ZERO-1** (déployé
par DEPLOY-GROUPE-1) a **scindé** la surface en **deux faits distincts** — `surface_terrain_m2(contenance
servie)` et `surface_dessin_m2` (`checks_parcelle.py`) — et rendu la hauteur de faîtage **conditionnelle**.
Le **golden** pointait encore l'**ancienne** notion `surface_parcelle_m2` : obsolète. Les valeurs servies
sont justes (banc 0 écart) ; seule la référence gelée était périmée.

**Correction** : **régénération du golden** (`labuse coherence --accepter`, le geste sanctionné),
**joué en prod** (en-process, mêmes lecteurs que le banc → capture la vraie réalité servie, y compris la
taxe que seul le serveur sert) → **7 témoins réécrits** (17–19 notions chacun). Vérifié en prod :
**V6b = `ok`** (« golden 7 témoins rejoués · 0 dérive »). Le golden régénéré est **rapporté dans le dépôt**
(`tests/golden/coherence/*.json`, le motif au commit).

### 4.3 V3b (hors mandat, signalé honnêtement)
**Un troisième verrou est `casse`** : **V3b** `verrou_eau_ancienne` — *« 1 eau ancienne ouverte :
`dpe_connu` → payload fiche (bloc non affiché) »*. C'est une **version de source DPE non encore bue**
(geste : `cron DPE : ré-ingérer --force`). **Hors du mandat** (V1c/V6b) et **pré-existant** à ce
déploiement ; **non touché**. Signalé pour que la carte rouge du Tableau soit lue juste : après ce mandat
elle ne porte plus que **V3b** (DPE, geste de données).

### 4.4 Passage de contrôle rejoué en prod (met à jour le Tableau / le résumé de John)
`labuse circuit verrous -w G8` rejoué en prod après les correctifs → journal `circuit_journal` à jour :
**32 joués ; V1c = « à décider » (plus cassé), V6b = OK, seul V3b reste cassé**. **G8** (une *garantie*,
pas un verrou : « 7 sources vitrine sans sonde, agent à 0 € ») reste un **avertissement NON bloquant**
(`-w G8`, convention du déploiement/cron — `VERROUS_AVERTISSEMENT={"G8"}`), pré-existant. Avant ce
mandat le journal listait **V1c + V3b + V6b** ; après, **V3b seul** (verrou réel) + G8 (avertissement).
Le résumé de John nommera désormais le bon état au prochain passage.

---

## 5. Le résumé du matin de John — complet, propre, avec secours

**Les deux défauts.** (a) Le mail était **tronqué** (« Radar du 05/ », coupé en pleine phrase) ; (b) il
**montrait ses astérisques** (`**…**`) au lieu d'un texte mis en forme.

**Causes.**
- **Troncature** : l'appel modèle de John était plafonné à `max_tokens=700` (`john/resume.py`) ; au-delà,
  la sortie est **coupée** (`stop_reason=max_tokens`) — une phrase en l'air — et partait telle quelle.
- **Astérisques** : le mail d'exploitation part en **TEXTE SIMPLE** (Brevo `textContent`) ; or John
  écrivait du **Markdown** (`**gras**`) → les balises s'affichaient littéralement. Aucune conversion, et
  **aucun repli** prévu pour une sortie coupée (seuls pause/erreur/vide/anti-invention retombaient sur le
  résumé factuel).

**Corrections** (`john/resume.py` + `ai/core.py`) :
1. **Complet** : plafond `700 → 1200` jetons ; et surtout une sortie **coupée est détectée**
   (`IAResult.stop_reason`/`.tronque`, neufs dans `ai.core`) → elle **retombe sur le résumé de secours
   factuel** (complet par construction, jamais tronqué). **Plus jamais un « Radar du 05/ ».**
2. **Propre** : la consigne de John impose désormais le **TEXTE BRUT** (pas d'astérisques/dièses/backticks,
   puces en « • », « termine tes phrases ») **et** un nettoyeur (`_texte_propre`) **retire toute balise
   Markdown** du texte envoyé — John **comme** le secours.
3. **Secours** : si la sortie est vide **ou coupée**, le **résumé factuel** part (texte propre, complet).

Tests unitaires (`test_ops_urgence_3.py`) : `_texte_propre` retire le Markdown ; `IAResult.tronque` ;
`_generer_defaut` rend « » (→ secours) si dégradé **ou** coupé ; sinon le texte complet.

---

## 6. Déploiement (court, règles DEPLOY-GROUPE-1)

- **Pré-vol** (go-fenêtre) : Réunion **~18 h 00** (hors 01–05 h), `/readyz` 200, `NRestarts=0`, aucun
  `pg_dump`/rsync/backup/`flux-run`/Radar en cours, disque **69 %** (30 G libres), dump < 24 h présent
  (`…20261106-133004.dump`, 6,5 Go). **Filets** `cp -al` posés : `app-avant-ops-urgence3`,
  `venv-avant-ops-urgence3`, `labuse.env.avant-ops-urgence3`, `Caddyfile.avant-ops-urgence3`.
- **Pas de migration de schéma** (diff = code/registre/shell ; aucun DDL ; `registre/tables.py` n'est
  qu'un dictionnaire).
- `deploy/scripts/deploy_app.sh labuse-vps` (exit 0) : garde manifeste (q_v20 présent, 433 229 l.) ✓ →
  rsync → **artefacts de modèle (12) livrés et présents en prod ✓** (garde fail-loud) → venv +
  import-smoke ✓ → deps calcul-nuit ✓ → front bâti → systemd → **crontab == registre (0 écart)** →
  `deploiement.json = c76fd3136` → manifeste prod **q_v20** intact → `fiche_cache` vidé → restart →
  **`/readyz` 200 STABLE 25/25 (33 essais)** → réchauffage détaché.
- **Post-déploiement** : NRestarts=0, `/readyz` 200, run servi **q_v20** (433 229) inchangé, artefacts
  q_v15 + m36 présents, **V1c** plus `casse`, **V6b** `ok`.

### Retour arrière (prêt, non utilisé)
> Note : la **rotation des filets** (OPS-URGENCE-2 §1b, mtime) a élagué le filet `*-ops-urgence3` fraîchement
> posé (quirk `cp -a` qui préserve le mtime → tri mtime trompé) et gardé `*-groupe1` + `*-ops-urgence2`.
> Le retour arrière reste **sûr** : l'état d'avant ce déploiement est le code **OPS-URGENCE-2 `660fdb297`**,
> **présent en git** (re-déployable), et le filet `app-avant-ops-urgence2` existe toujours.
```bash
# Option A (git) — revenir au code d'avant ce déploiement :
cd ~/Desktop/labuse-main && git checkout 660fdb297 && deploy/scripts/deploy_app.sh labuse-vps
# Option B (filet) :
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app  && sudo mv /opt/labuse/app-avant-ops-urgence2  /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-ops-urgence2 /opt/labuse/venv
sudo systemctl start labuse && curl -fsS http://127.0.0.1:8000/readyz
# Schéma inchangé (aucune migration) → rien à défaire.
```

---

## 7. Recette (hook vert)
- Python unitaires (famille du hook, sans base) : **2988 passés / 0 échec**, 50 skip (dont
  `test_ops_urgence_3` **4/4**). *(1 relance : abort natif sklearn macOS — OpenMP — contourné par
  `KMP_DUPLICATE_LIB_OK`, pas une régression.)*
- Front : `tsc -b` **0 erreur**, `vitest` **309/309**. Scan de secrets : propre.
- Cohérence (12 témoins, base locale) : **0 écart**. Verrous hermétiques : **86/0**.
- `bash -n deploy_app.sh` : OK. **« ✓ Vérifications OK — envoi autorisé. »**

---

## 8. Réserves honnêtes & dette
1. **`PROMEUT=0` conservé** : q_v21 complet **reste candidat** — la bascule est ta décision (contrôles §3).
2. **V3b (DPE `dpe_connu`)** : eau ancienne non bue — geste de ré-ingestion DPE, **hors mandat**, non touché.
3. **27 orphelines `a_decider`** (V1c) : vieilles tables de travail avec action proposée — purge =
   ton geste (`labuse tables purger --apply`), **pas** un échec.
4. **Relocalisation des artefacts de modèle hors `reports/`** : la garde fail-loud ferme le risque ; la
   cible durable reste de les ranger dans l'arbre toujours livré (même dette que l'ÉCHANTILLON de cohérence).
5. **Rotation des filets vs `cp -a`** : le filet `*-ops-urgence3` a été élagué (mtime hérité) ; retour
   arrière sûr par git/filet ops-urgence2 (§6). Dette fine : poser les filets avec un mtime frais, ou
   trier la rotation autrement.
6. **Golden régénéré en prod** : le dépôt porte la version prod (taxe incluse) ; une base locale sans la
   donnée taxe montrera une dérive locale sur cette notion (gap de données local, pas une régression).
