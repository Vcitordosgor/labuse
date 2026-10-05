# CHASSE-FIX-2 — corriger ce que CHASSE-2 a trouvé

Branche `fix/chasse-2` (base `origin/main` `56cc27ea`, audit/chasse-2 + fix/dashboard-1 mergés) ·
worktree `~/Desktop/labuse-chassefix2` · 2026-10-05. Règle du mandat : chaque écart corrigé =
sa commande de reproduction rejouée → 0, plus un verrou qui le tient. **Aucun run, aucune bascule,
aucun merge.** La colonne « touche le run » est dans `CHANGEMENTS.csv`.

## Verdict en une ligne

Les **2 bloquants fermés** (D05 carte = compteur ; D04 terrain exigu nommé partout), **tout le reste
d'ECARTS.csv corrigé ou classé-avec-preuve**, le **verrou rouge du dashboard (V1c) remis au vert** sans
rien désactiver, le **badge « Propriétaire public » (C35)** posé avec une règle unique. 8 verrous neufs
(`tests/test_chasse_fix2.py`), le test BPE préexistant corrigé. **0 écart touche le run.**

## Étape 0 — le verrou rouge nommé et corrigé

`labuse.cli circuit verrous` : parmi les **24 verrous V**, un seul cassait → **V1c** (d'où le « 23/24 »
du dashboard). Les 8 garanties G1–G8 ne comptent pas dans les 24 ; G5/G8 restent l'état connu
« agent sonde à 0 € » (documenté VERROUS-FIX-1, non rejouable ici).

- **Verrou** : V1c — « Toute table du schéma appartient à la carte, ou est une orpheline listée qui
  attend le geste de Vic ».
- **Cause** : la table `coherence_runs` (journal des passages du banc de cohérence, COHERENCE-FIX-1 —
  écrite par `coherence_journal.py`/`jobs.py`, lue par l'onglet « Cohérence » de la page Données)
  était ORPHELINE sans action proposée. Ce n'est pas une table à purger : c'est une table
  d'EXPLOITATION active (un journal, comme `circuit_journal`).
- **Correction (jamais désactivée)** : déclarée dans `TABLES_EXPLOITATION`
  (`src/labuse/registre/tables.py`). Preuve : V1c repasse « ok » → **24/24 verrous**.

## Lot 1 — les 2 bloquants

### D05 (+ D06) — /filtre?idus=1 et Densifier résolvent la cascade

Une seule mécanique : les lecteurs qui joignent `dryrun_parcel_evaluations` doivent résoudre
`_cascade_run` (q_v16 → étage 0 réutilisé q_v13_sources1) comme le font déjà compteur/liste/stats.
Le bloc `idus` de `/filtre` (app.py) et la jointure étage 0 de `/renouvellement/liste` lisaient le
run SERVI BRUT, absent de `dryrun_parcel_evaluations` depuis la bascule q_v15→q_v16.

- `idus` : `run_idus = _cascade_run(db, c.source)`.
- Densifier : la jointure dryrun passe sur `:drun = _cascade_run(db, runs.current())` (le score v2 et
  `parcel_renouvellement` restent sur le run servi, c'est correct).
- **Preuve** : `make -C scripts/chasse filtres` → **33 tests · 0 écart** (était 28 écarts compte≠liste) ;
  `/renouvellement/liste` → `etage0` allumé (5 sur l'échantillon, était 0).
- **Verrou** : `test_d05_filtre_idus_resout_la_cascade` / `test_d06_densifier_etage0_resout_la_cascade`
  — un run EMPRUNTEUR (cascade dans un autre run) ; un lecteur qui lit le run brut rend 0, le test casse.

### D04 (+ D03) — terrain exigu : la vraie raison nommée partout

`cause_libelle(cause, exigu_raison)` (`faisabilite/engine.py`) traduit CHAQUE cause structurée
(`terrain_exigu`, `redhibitoire`, `zone_non_constructible:X`, …) en libellé client « Non retenue — … ».
La raison fine du terrain exigu (RECETTE-1 A1 : ppr_rouge / emplacement_reserve / ebc / contraintes /
portion_reduite / reculs) n'est pas écrite au run → elle est recalculée **LIVE sur la fiche** (une seule
parcelle) : « servir la raison déjà calculée » sans toucher au run.

- **D03** : le bloc Potentiel lit désormais la cause (jointure `AND r.cause IS NULL` retirée) et sert
  `sdp_residuelle_m2 = 0` + le libellé qui nomme la raison — fin de la contradiction « Marge SDP non
  calculée » (sdp ∅) vs Analyse LABUSE sdp 0.
- Servie et affichée : **fiche** (bloc Potentiel, badge « Non retenue »), **liste** (`cause_libelle`
  sur la ligne), **Dossier PDF** (`verdicts.verdict_potentiel` nomme la raison au lieu de « nul par la
  règle de zonage » — faux pour un terrain_exigu géométrique), **Copilote** (`potentiel_non_retenue`).
- **Deux familles de cause (arbitrage Vic 2026-10-05)** :
  - **CERTAINE** (zone_non_constructible, terrain_exigu, habitat_interdit, redhibitoire, capacite_nulle)
    → verdict ferme « Non retenue — <raison> », **SDP 0 nommée** (le 0 est écrit par le run, jamais forcé) ;
  - **IGNORANCE** (zone_non_resolue, hors_plu, regle_plu_non_validee, hauteur_indispo, indetermine)
    → « **Analyse incomplète** — <raison> », **SDP ∅** (on écarte le 0 du dataset), cohérent avec C26
    (NULL ≠ 0) et la bande NC.
  Partition unique `faisabilite.engine.cause_certaine` ; le lecteur SQL du banc applique le MÊME
  prédicat (raw sdp si cause NULL ou certaine, ∅ sinon). Vérifié sur **2 témoins × 8 familles**
  (fiche = banc, 0 divergence).
- **Preuve** : `make -C scripts/chasse libelles2` → **exigu 70 nommé / 0 muet** (était 0/70),
  **discordance intra-fiche 0** (était 43/70), différé 40/40 conservé. Témoin 97409000AK0804 nommé.
- **Verrou** : `test_d04_cause_libelle_nomme_la_raison`.

**Conséquence assumée (supersession d'une décision COHERENCE-FIX-1).** COHERENCE-FIX-1 avait choisi
que les lecteurs vivants rendent ∅ pour une ligne à cause (« le 0 est un artefact de dataset »). D03
la révise explicitement : le bloc Potentiel LIT la ligne à cause et sert sa SDP (0 nommé). C'est
honnête MAINTENANT parce que le 0 n'est plus nu — il porte sa cause (« 0 m² — Non retenue : zone A
inconstructible »). Deux suites nécessaires, faites proprement :
- le **lecteur SQL du banc de cohérence** (`scripts/coherence/checks_parcelle.py`) lisait
  `CASE WHEN cause IS NULL THEN sdp END` (il modélisait l'ANCIEN comportement ∅) → aligné sur la
  valeur servie (sinon la sonde nocturne G7 aurait crié 376 faux écarts fiche↔sql à perpétuité) ;
- le **golden des 7 témoins** (`tests/golden/coherence/`) régénéré via l'app EN-PROCESS : seuls les
  2 témoins à cause (97408000AO1424, 97418000AC0198) bougent, sdp ∅→0 — **dérive ACCEPTÉE** au sens
  de V6b (motif au commit). Les 5 autres témoins inchangés ; les tuiles ne divergent pas (aucun
  couple fiche↔tuile dans les écarts) → aucun rebuild de run requis.

## Lot 2 — le reste d'ECARTS.csv

- **D07** — « retirées (30 j) » : le compteur 4-chiffres (`_AGG`, pige/marche.py) partage EXACTEMENT la
  définition RADAR-FIX-3 du tableau (retraits confirmés par l'ouverture du lien, import initial en bloc
  exclu). Île : **1 = 1** (était 101 vs 1 sur le même écran). Verrou `test_d07`.
- **D01 / D11** — plan de situation : `_fetch_tile` (flash/carte.py) **réessaie avec backoff exponentiel**
  un 400/5xx IGN transitoire avant d'abandonner ; un 404 (tuile hors couverture) ne se réessaie pas. Un
  rendu incomplet n'est jamais servi comme définitif si une relance peut réussir. Verrous
  `test_d01_*` (2×400 → OK ; 404 → pas de retry).
- **D02** — le libellé d'écart de la recette exports (`scripts/recette_exports1.py`) nomme la (les)
  ligne(s) qui divergent réellement (diff pdftotext), plus le « nom commercial » par défaut.
- **D09** — cibles invraisemblables (poste électrique, château d'eau, cité récente) : **classé limite
  produit**. Les calculs suivent les règles (0 FAUX numérique) ; aucune donnée d'usage n'entre au
  scoring. Disqualifier par l'usage **toucherait le run** → non fait (noté « touche le run = oui » dans
  CHANGEMENTS.csv). Le badge C35 surface le sous-ensemble à propriétaire public (poste EDF, château
  d'eau, parc public = 2 des 3 témoins).
- **D10** — « étages plafonnés à 3 » : **classé faux positif de harnais**. `parcel_filtre_bati.etage`
  est un ÉTAGE DE FILTRE (1 marginal / 2 intermédiaire / 3 saturé), **jamais servi au client comme un
  nombre d'étages** (le badge `filtre_bati` ne lit que ratio/décision/motif/année). Les vrais niveaux du
  bâti viennent du LiDAR (`niveaux_reels`/`niveaux_existants`, run 13). Aucun lecteur client ne ment ;
  pas de défaut, pas de run touché. Même famille que D08 (harnais mal libellé).
- **D08** — déjà un constat de harnais (node_modules + vocabulaire tiers) : node_modules symlinké pour
  le rejeu ; hors périmètre app.
- **Base de test (leçon D05)** : le banc de bascule (`scripts/chasse/bascule.py`) lit désormais AUSSI
  le chemin `idus=1` (c'est lui que la bascule a cassé sans que le banc ne le voie). Le semis
  borrowed-cascade **archivé et rejouable** avec `idus=1` est `test_chasse_fix2.py` (base `labuse_tf1`).

## Lot 3 — badge « Propriétaire public » (C35, décision Vic)

Les parcelles d'un propriétaire public (État, région, département, commune, EPCI, établissement public)
**restent au classement**, avec un badge « Propriétaire public » sur la ligne de liste ET la fiche ; le
filtre existant (`proprietaire_type=public`) permet de les écarter. **Même règle de détection partout** :
une seule constante `PUBLIC_DGFIP_GROUPES = (1,2,3,4,9)` (`proprietaire_type.py`) alimente le filtre, la
colonne de liste (`proprietaire_public`, lue EN DIRECT — jamais le `owner_type` matérialisé qui peut
dater d'un ancien run) et le badge de fiche. Verrous `test_c35_*` (liste = fiche = filtre) ; vérifié sur
une parcelle réelle (97411000DE0285 = public).

## Clôture

- `make -C scripts/chasse chasse` rejoué : filtres **33/0**, libelles2 exigu **70/0 muet** + discordance
  **0**, invariants2 **7/7 à 0**. Le face-à-face des lecteurs revient à sa baseline documentée —
  **CHASSE-1 231 écarts (0 FAUX-CLIENT ; 155 INCOHERENT + 76 TOLERABLE)**, **CHASSE-2 169 (0 FAUX-CLIENT ;
  114 + 55)** : les 376/410 écarts `sdp_residuelle_m2` apparus (puis **résorbés** par l'alignement du
  lecteur de banc, D03) ont disparu ; le reste = familles déjà classées (C44 slivers
  `surface_parcelle_m2`, C34 `cinquante_pas`, D08b `tiers_hauts_n` vocab q_v11, `filiation_mere` artefact).
- `labuse circuit verrous` = **24/24 verrous** (V1c réparé, V6b vert après acceptation golden) ; seuls
  G5/G8 restent (garanties « agent sonde à 0 € », hors des 24, documenté VERROUS-FIX-1), G7 0 fuite.
- `tests/test_chasse_fix2.py` : **8 verrous neufs verts** ; chasse_fix1 **7/7** ; vitest **235/235**
  (BPE `layersCoquilles` corrigé) ; tsc 0.
- `CHANGEMENTS.csv` : 0 écart touche le run (D09 noté « oui » car la seule correction possible — par
  l'usage — toucherait le run et n'a pas été faite).
