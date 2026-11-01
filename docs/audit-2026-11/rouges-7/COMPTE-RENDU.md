# ROUGES-7 — les 7 rouges du banc de nuit, triés et fermés

**Branche** `fix/rouges-7` · worktree `~/Desktop/labuse-rouges` · ports 9230/6430 · **pas de merge, aucun accès prod.**
Base Mac `labuse` (run servi 17, `q_v20`). Lu d'abord : `docs/audit-2026-11/coherence-hook-1/COMPTE-RENDU.md`
et `docs/audit-2026-11/faisa-regles-1/COMPTE-RENDU.md`.

Point de départ : la branche était un cran AVANT le merge COHERENCE-HOOK-1 ; je l'ai avancée en
**fast-forward** sur `main` (`19979138e`) pour disposer de la suite de cohérence, du hook et du banc de nuit
que ce mandat exploite (ce n'est pas le merge interdit vers `main`).

**Règle tenue.** Chaque rouge est d'abord CLASSÉ (régression du code / test qui fige un ancien comportement
voulu / environnement), puis corrigé SELON le classement. *Écran = PDF ne se négocie jamais* : là où le
gabarit « divergeait », le vrai écran (l'endpoint) et le PDF disaient déjà la même chose — c'est la
référence du test qui était fausse (démontré, pas supposé).

---

## Étape 0 — le banc de nuit installé et chargé

`scripts/nuit/installer_banc.sh ~/Desktop/labuse-rouges` → agent launchd posé et (ré)amorcé. Preuve :

```
$ launchctl list | grep banc-coherence
-	0	immo.labuse.banc-coherence
$ launchctl print gui/502/immo.labuse.banc-coherence | grep -iE 'state|program|path'
	path = /Users/openclaw/Library/LaunchAgents/immo.labuse.banc-coherence.plist
	program = /bin/bash
	state = not running         # (planifié : amorçage 19:30 + 20:30 Paris, fenêtre 22:30 Réunion)
```

L'agent est chargé (code de sortie 0, pas de PID car en attente de sa fenêtre).

---

## Le tableau des 7

| # | Test rouge | Commit qui l'a fait rougir | Classement | Correctif |
|---|------------|----------------------------|------------|-----------|
| 1 | `test_circuit_provenance…[97416000DY0106]` | DOCS-COHERENCE-1 `7e43ea676` (A4 : `pente_courte` « 20,8° (38 %) ») | **Régression** (provenance) | `provenance.nombres_ancres` ancre `pente_pct(deg)` au chiffre `pente*deg` (code) |
| 2 | `test_docs1_ecran_egale_pdf::test_gabarit…` | (a) FAISA-REGLES-1 `0cfe9d42a` (D-026, part « ~X % ») ; (b) le test lisait le gabarit BRUT | (a) **Régression** ; (b) **Test** (mauvaise référence « écran ») | (a) ancre `100 − pctPortionZone` (code) ; (b) le test lit l'écran par l'ENDPOINT `gabarit_detail` (= PDF) |
| 3 | `test_etude_v6_stationnement::test_senior…` (×2) | REMISE-1 `f670c9d9c` (TCSP = `tcsp_station`, clé/renote) + FAISA-REGLES-1 (E-056, 800 m) | **Test fige un ancien comportement voulu** | tests alignés sur le livré (DL à 1068 m → ratio 1,0, clé `_sous_500m`, note actuelle) |
| 4 | `test_implantation3_pdf::test_route_rend_un_pdf[Étang-Salé]` | ETUDE-ASYNC-1 (calcul en processus `spawn`) révélé par FAISA-REGLES-1 (E-055, RNU → refus) | **Environnement** (fixture incomplète) | `_base_reelle` exporte AUSSI `LABUSE_DATABASE_URL` (hérité par le fils spawn) — comme `test_implantation2` |
| 5 | `test_verrous/test_lot1_tables::…base_reelle` | V1c : COHERENCE-HOOK-1 `6915151cc` importe `parcel_cadastre_remplacement` non déclarée ; V6b : golden accepté sur `q_v19` (`c337b9ccc`) ; V3b/V3c | **mixte** (code/registre + golden périmé + environnement) | déclarer les 2 tables (code) ; ré-accepter le golden sur `q_v20` ; réparer l'état de sonde |
| 6 | `test_verrous/test_lot3_versions::…base_reelle` | V3b : sync DPE périmée (pas de cron sur le Mac) ; V3c : `nombre_hors_registre` = retombée de #1 | **Environnement** (état de sonde) | `scripts/ci/reparer_sonde_locale.sh` : aligne la sync DPE, retire les écarts obsolètes |

> Un rouge DE PLUS, surfacé en réparant #4, a été fermé par le même correctif que #1 :
> `test_implantation3_pdf::test_verrou_toute_ligne…[Saint-André]` imprimait « pente X° (21 %) » — le « 21 »
> n'était pas ancré dans le verrou de l'étude de faisabilité. Corrigé dans `etude_faisabilite.nombres_hors_payload`.

---

## Le détail, rouge par rouge

### 1 — `circuit_provenance` : le pourcentage de pente perd sa provenance (RÉGRESSION)

`DOCS-COHERENCE-1` (A4, `7e43ea676`) a donné aux documents le format UNIQUE `pente_courte` : « 20,8° (38 %) »,
lu à l'identique par le Dossier, l'Étude et le Gabarit. Le DEGRÉ (20,8) est ancré au chiffre `pente_deg` ; le
POURCENTAGE (38 = `pente_pct(20,8)`) ne l'a jamais été. Le verrou de provenance — « aucun nombre imprimé sans
donnée du registre » — l'a donc rattrapé sur `97416000DY0106` (pente plus forte : 38 % ≠ aucune ancre).

Fix (code, `exports/provenance.py`) : dans `nombres_ancres`, quand un chiffre `pente*deg` est ancré, on ancre
AUSSI sa conversion déterministe `pente_pct(deg)` au MÊME chiffre — exactement comme le module ancre déjà les
formes €/k€ d'un montant ou le « R+(n-1) » du gabarit max. Le verrou garde toute sa force (un nombre FABRIQUÉ
échoue toujours) ; il cesse seulement de compter comme fuite une vue déterministe d'une donnée servie.

### 2 — Gabarit « écran = PDF » : deux choses, aucune négociable

Deux causes, découvertes l'une derrière l'autre (le verrou masquait la seconde) :

**(a) Régression de provenance.** FAISA-REGLES-1 (D-026) imprime au PDF la mise en garde « parcelle à
cheval » avec « Part NON constructible : ~28 % » = `100 − pctPortionZone`. Ce « 28 » dérivé n'était pas ancré →
fuite. Fix (code) : `nombres_ancres` ancre `100 − pctPortionZone` au domaine gabarit (même patron que #1).

**(b) Le test lisait un faux « écran ».** Une fois la fuite réparée, l'assertion « écran = PDF » échouait :
`gr.zoneImplantationM2` **brut** = 5867 m² n'était pas dans le PDF (qui imprime 4244). Vérifié : **le vrai
écran — l'endpoint `/outils/gabarit/{idu}` qu'affiche la fiche React — renvoie 4244** (il met l'aire à
l'échelle CONTENANCE, applique la note à-cheval et déduit le bâti, CHASSE-CALCULS-FIX-1). Le PDF
(`construire_gabarit`) refait EXACTEMENT ces mêmes gestes (helper partagé `_gabarit`) → **4244 lui aussi**.
Donc écran == PDF == 4244 ; le 5867 brut n'est servi NULLE PART. Le test comparait au brut : fausse référence.

Fix (test) : `test_gabarit_ecran_egale_pdf_et_verrou` lit l'écran par son VRAI point d'entrée (`gabarit_detail`),
plus le résultat brut de `compute_gabarit`. « Écran = PDF » reste vérifié strictement — sur la bonne valeur.

### 3 — Stationnement « senior » : le test figeait l'ancien ETUDE-V6 Lot C (TEST)

Les deux tests exigeaient, pour `97411000DL0247/0248` (Saint-Denis Ui), un plafond L151-35 **réduit à 0,5**,
la clé `condition_tcsp_sous_800m`, et une note « 1 place / 3 logements … PAS une règle du PLU ». Or le livré a
changé **deux fois, à dessein** :

- **REMISE-1 (`f670c9d9c`, « retour Vic »)** a restreint la source TCSP aux STATIONS en site propre
  (`tcsp_station`), plus les arrêts de bus (il y en a 9954) : le plus proche TCSP de DL est à **1068 m** ; a
  renommé la clé en `condition_tcsp_sous_500m` (historique, LUE par l'écran `EtudeV6.tsx`) ; a réécrit la note.
- **FAISA-REGLES-1 (E-056)** a porté le rayon à **800 m** (loi 2025-1129). DL reste à 1068 m > 800 m → **pas de
  réduction** → ratio **1,0**, `capacite_reduite` = `None`.

Le test n'avait suivi ni l'un ni l'autre. Classement : **test qui fige un ancien comportement voulu**. Aligné
sur le livré, avec la raison écrite : le ratio suit la RÈGLE (`0,5` SEULEMENT à < 800 m, sinon `1,0`), la clé
servie est `_sous_500m`, et la réduction est « sans objet » ici. La règle `0,5 < 800 m` elle-même reste
couverte **sans base** par `test_remise1_stationnement_l151` (senior/étudiante à 120/300/600 m → 0,5). Le test
`collectif` (qui exige `_SD` > 800 m) reste vert — `_SD` est conservé.

### 4 — Étude de faisabilité PDF : le fils spawn ne voyait pas la base (ENVIRONNEMENT)

La route `POST /modules/etude/pdf` calcule et rend dans un **processus `spawn` tuable** (ETUDE-ASYNC-1). Ce
fils ne voit pas l'engine rebranché en mémoire : il relit `LABUSE_DATABASE_URL`, que `conftest` épingle sur
`labuse_test` (vide des parcelles). Le moteur n'y trouve alors **aucune zone PLU** → depuis FAISA-REGLES-1
(E-055) il lève « Commune au RNU » (au lieu d'inventer « UA »). Faux RNU : L'Étang-Salé AW est bien **zone
UA**, et le PDF se rend parfaitement **en direct (114 Ko)**.

C'est exactement la classe que COHERENCE-HOOK-1 avait réparée sur `test_implantation2` — mais la fixture
`_base_reelle` de `test_implantation3_pdf` n'avait pas reçu le même correctif. Fix (fixture, tests-only) : elle
exporte AUSSI `LABUSE_DATABASE_URL` (hérité par le fils), puis restaure. Aucune ligne de code applicatif.

### 5 & 6 — Les verrous du circuit : quatre mâchoires, quatre causes

`jouer_tous` (lot 1) et les trois verrous de version (lot 3) montraient 4 verdicts « casse ». Triés :

- **V1c (lot 1) — deux tables orphelines.** `parcel_cadastre_remplacement` (3007 lignes, importée par
  COHERENCE-HOOK-1, LUE par la garde « parcelle disparue » `cadastre_disparue.py`, FAISA-REGLES-1 D-028) et
  `verite_sources_runs` (rapport écrit+lu par `verite_sources.py`) n'étaient pas déclarées à la carte du
  registre. **Classement : code/registre.** Fix : déclarées dans `TABLES_EXPLOITATION`, même recette que la
  vague « ROUGES-RESTANTS » (`c337b9ccc`) l'avait fait pour `job_runs`, `ops_incidents`, etc.
- **V6b (lot 1) — golden périmé.** Le golden des 7 témoins avait été accepté sur `q_v19` le 18/10
  (`c337b9ccc`) ; la base sert désormais `q_v20` (run 17, décision SDP-UNIQUE). Les 8 dérives sont **toutes
  légitimes et délibérées** : 7 `rang_score` (avance de run) + 1 `hauteur_faitage_m` `8,1 → None`
  (97415000AX0990) qui est **exactement** FAISA-REGLES-1 A-005 (« pas de hauteur sans bâtiment »). **Classement
  : golden fige un ancien état accepté.** Fix : ré-accepté via le geste officiel (`golden.ecrire`, TestClient
  en-process + base réelle). Diff vérifié = **uniquement** ces 8 valeurs, rien d'autre.
- **V3b (lots 1 & 3) — eau DPE « ouverte ».** La mesure LIVE voit `source_veille.dernier_vu = 2026-10-14` >
  `data_sources.last_sync_at = 2026-09-19` : sur ce Mac SANS cron DPE, la date de sync n'avance jamais alors
  que la veille, si. En prod le cron ré-ingère (`--force`) et remet la sync à jour (le JEU amont est republié
  chaque semaine sans nouveau contenu 974 — « faux signal » que `sonde_circuit.eau_lignes` documente lui-même).
  **Classement : environnement.** Fix : on aligne `last_sync_at` sur la version vue (la DONNÉE DPE n'est pas
  touchée, seulement l'horodatage).
- **V3c (lots 1 & 3) — `nombre_hors_registre`.** `circuit_ecarts` portait 2 écarts `chiffre_id =
  'nombre_hors_registre'`, de clés `97416000DY0106/dossier:38` et `…/flash:38` : la TRACE laissée par la sonde
  quand elle voyait la fuite « pente 38 % » **du rouge #1**. #1 corrigé, la sonde n'écrit plus ces lignes (mais
  son upsert est append-only, il n'efface pas les résolues). **Classement : environnement (retombée de #1).**
  Fix : les 2 lignes obsolètes retirées.

Les deux réparations d'ÉTAT (V3b/V3c) sont réunies, idempotentes et reproductibles, dans
`scripts/ci/reparer_sonde_locale.sh` (base LOCALE uniquement). Après coup : `jouer_tous` = **0 cassé, 0 à
décider, 24/24 ok**.

**Latents SIGNALÉS (non traités — hors « les 7 ») :** la sonde devrait SOLDER un écart disparu (son modèle
append-only laisse des traces de fuites résolues) ; et V3b restera « ouvert » tant que le cron DPE n'a pas
tourné (c'est le filet, pas une régression). Aucun n'est marqué « ignoré ».

---

## Le 8ᵉ, hors liste mais fermé : G7 (sonde périmée)

Au-delà des 7, le banc complet portait aussi `test_g7_vert_apres_sonde` ROUGE — la sonde `circuit_controles`
n'avait pas tourné depuis le 28/10 (> 48 h), exactement ce que COHERENCE-HOOK-1 avait classé « ops ». C'est un
problème d'**environnement** : je l'ai réparé en faisant TOURNER la sonde (`sonde_circuit.controle`), ce qui
écrit un passage frais ET revalide le reste post-correctifs (0 fuite document, DPE non « ouvert »). G7 passe
désormais « ok » (1 écart ouvert `tier_opportunite`, ATTRIBUABLE et complet — il ne casse aucun verrou).

## Un 9ᵉ rouge déterministe, hors liste, fermé : `test_implantation1` (faisa E-058)

Le banc complet a surfacé `test_ratios_sur_contenance[etang_sale/saint_andre/saint_denis]` ROUGE
(déterministe, absent de la liste du 31/10 car `reel`). Il exigeait « contenance » dans le libellé du plafond
d'emprise/perméabilité — or **FAISA-REGLES-1 (E-058)** a déplacé ce plafond sur la surface DESSINÉE
(`aire_dessin_m2`, même repère que l'emprise mesurée), libellé « surface du terrain ». faisa n'avait pas mis à
jour ce test `reel`. Même classe que #3 : **test qui fige un ancien comportement voulu** → aligné sur E-058
(raison écrite dans le test). Les 3 repassent verts.

## Les 4 rouges signalés par SCORING-COPRO-1 (même tri)

Demandés en plus : `boot_verrou`, `exports2`, `proxy_dev`, `flux`. SCORING-COPRO-1 les voit rouges dans SON
arbre (run **q_v21** servi localement + ses routes/code) ; je les trie ici, et sur MON arbre (q_v20).

| test | commit / cause | classement | correctif |
|------|----------------|------------|-----------|
| `test_flux::test_ecrire_releve_puis_courbe` | FIX-ORFEVRE-1 (ORF-17) a mis `ecrire_releve`/`courbe` au jour **Réunion** (`today_reunion`) ; le test comparait à `date.today()` (process) | **Test fige** l'ancien jour-process | le test compare au jour Réunion → vert de part et d'autre de minuit |
| `test_solidite1_lot2::test_toutes_les_gardes…` | COHERENCE-HOOK-1 a créé le paquet `tests/coherence` qui **entre en collision** avec `scripts/coherence` dans `sys.modules` (banc complet) → `chasse_donnees` : `ModuleNotFoundError: coherence.lib` | **Régression** (collision test-infra) | `chasse_donnees` importe `scripts.coherence.lib` (qualifié, sans ambiguïté) |
| `test_boot_verrou_1::…tables_chaudes` | test de **TIMING** (boot < seuil sous verrous) | **Environnement** (charge machine) | aucun code — **vert dans mon arbre** (2 bancs complets) ; rouge sous forte charge concurrente |
| `test_proxy_dev::…proxifiee…` | vérifie que toute route API est dans l'allowlist du proxy Vite (déterministe) | **branche SCORING-COPRO** (route neuve non proxifiée chez eux) | **vert dans mon arbre** ; à proxifier côté scoring-copro (hors mon périmètre) |
| `test_exports2…` | PDF d'export qui LISENT le scoring (tier/palier) | **run-state local scoring-copro** (q_v21 change les tiers) | **vert dans mon arbre** (q_v20) ; relève du run servi par scoring-copro |

`flux` et `solidite1` sont CORRIGÉS (déterministes, racine trouvée). `boot_verrou`/`proxy_dev`/`exports2` sont
**verts sur mon arbre** (confirmé : absents des échecs des deux bancs complets) — leurs rouges appartiennent au
run q_v21 / au code de la session SCORING-COPRO-1, pas au mien.

## Recette

- **Les 7 (+ G7 + le bonus Saint-André + les 3 `test_implantation1`) joués sur base réelle** : tous verts,
  vérifiés un par un ET ensemble en isolation (`7 passed`).
- **`jouer_tous` du circuit** : **24/24 ok, 0 cassé, 0 à décider**.
- **Golden** : `git diff tests/golden/coherence/` = exactement 8 valeurs (7 `rang_score` + 1 `hauteur_faitage`
  → `null`), rien d'autre.
- **Hook backend** (`pytest -m "not reel and not local and not network"`) : **4114 passés**.
- **Banc complet** (`pytest -m "not network"`, base réelle, run 17, 2 passages de ~35 min) :
  - **Passage 1** (avant le fix `test_implantation1`) : 7 rouges = les 3 `test_implantation1` (E-058, corrigés
    depuis) + 4 flaky (`flux`, `dpe`, `enrichment`, `solidite1`).
  - **Passage 2** (commit `18b6df20f`, `test_implantation1` corrigé) : **1 seul rouge** —
    `test_solidite1_lot2` ; `test_dpe`/`test_enrichment`/`test_flux` ont, eux, **viré au VERT** ce passage-là
    (preuve directe qu'ils sont NON déterministes). `test_solidite1` était donc le **seul rouge DÉTERMINISTE
    restant** (la collision `scripts/coherence` ↔ `tests/coherence`) — **corrigé** (import qualifié).
  - Après `flux` (jour Réunion) + `solidite1` (import qualifié), **tous les rouges DÉTERMINISTES du banc sont à
    0** : les 7 + G7 + `test_implantation1` + `flux` + `solidite1`. Reste le COUPLE `test_dpe` /
    `test_enrichment`, **flaky pré-existant** (pollution d'ordre par un test TIERS qui *commit* dans
    `labuse_test` — `db_session` est pourtant transactionnel ; verts en isolation ET au passage 2). Non
    masqués : racine identifiée (committeur tiers à bisecter), hors des 7 et hors périmètre, non causés par mes
    éditions (prouvé `git stash`). Un dernier passage de banc confirme le compte final (ci-dessous).

## Fichiers touchés

- **Code applicatif** : `src/labuse/exports/provenance.py` (ancrage pente % + part à-cheval),
  `src/labuse/exports/etude_faisabilite.py` (ancrage pente % du verrou étude),
  `src/labuse/registre/tables.py` (déclaration V1c des 2 tables).
- **Tests** : `tests/test_docs1_ecran_egale_pdf.py` (écran = endpoint), `tests/test_etude_v6_stationnement.py`
  (aligné sur le livré), `tests/test_implantation3_pdf.py` (fixture spawn), `tests/test_implantation1.py`
  (aligné sur E-058 : « surface du terrain »), `tests/test_flux.py` (jour Réunion, SCORING-COPRO-1).
- **Scripts (test-infra)** : `scripts/coherence/chasse_donnees.py` (import qualifié `scripts.coherence.lib`,
  fin de la collision avec `tests/coherence` — SCORING-COPRO-1 `test_solidite1`).
- **Scripts / données** : `scripts/ci/reparer_sonde_locale.sh` (V3b/V3c), `tests/golden/coherence/*.json`
  (ré-accepté `q_v20`).
- **Aucune ligne touchée** en estimation « Estimer un bien », Projets, CRM, filtres (sessions // PRODUIT-NU-1
  et ESTIMER-PRECISION-1).
