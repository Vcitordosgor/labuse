# FICHE-FIX-2 — Corriger ce que FICHE-AUDIT-2 a tranché

*Branche `fix/fiche-fix-2` depuis main · worktree `~/Desktop/labuse-fichefix2` · non mergée · un commit par point.*
*Témoin principal : BZ1065 `97411000BZ1065` (Saint-Denis Uh, bâti, zonage ANC). Témoins secondaires cités par point.*

La hauteur d'en-tête était déjà corrigée (GABARIT-6 mergé) et la fiche 500 réparée (`"cause": None`, app.py:5324 présent sur main) — vérifiés à l'Étape 0, hors décompte. Les 6 points ci-dessous sont l'exécution du verdict du §5 de FICHE-AUDIT-2.

| # | Commit | Objet |
|---|---|---|
| P1 | `e4cef9a8` | Réseaux : badge viabilisation eau/élec ≠ assainissement + ensoleillement déplacé |
| P2 | `9833c27e` | Une seule médiane appartement/maison (échantillon bâti unique) |
| P3 | `524fb527` | Faîtage LiDAR douteux : drapeau « Sources discordantes » (seuil 3 m) |
| P4 | `5f90e24d` | Mixité sociale LLS : règle validée branchée + 11e étape capacité |
| P5 | `3571f933` | Parc social : maille commune dite, plus « secteur » |
| P6 | `f38be001` | Écarts restants : une seule pente, étiquette « À suivre », « à vérifier » |

---

## P1 — Le badge Réseaux ne ment plus sur l'assainissement

**Écart (§1.3).** Le badge d'en-tête « Réseaux et desserte · eau · assainissement · élec — confirmée » venait du **score de viabilisation** (`faisabilite/viabilisation.py compute_score/band` : permis < 100 m + façade voie + bâti + zone PLU). Ce score **ne teste jamais l'assainissement**. BZ1065 est en zonage **ANC** → « confirmée » sur l'assainissement était faux.

**Correction (frontend, `reseaux.tsx` + `ViabilisationBlock.tsx`).** Le badge ne couvre plus que ce qu'il teste. Deux faits distincts, source unique `assainissementResume(anc)` partagée en-tête + tiroir :

- **En-tête** (rangée fermée) : badge = **viabilisation eau/élec** (« eau/élec confirmée / probable / à confirmer », rattaché au score) ; sous-titre = **Assainissement : {collectif | non collectif | non renseigné}** (zonage SIG sourcé).
- **Tiroir** : titre « Viabilisation (**eau · élec**) » (plus « assainissement ») ; bloc **Assainissement (zonage)** distinct, verdict explicite en tête (« non collectif — filière autonome à prévoir »), la note de raccordement assainissement rapatriée dedans (un fait, une section) ; l'**Ensoleillement** (PVGIS) + le S3REnR remontent sous leur propre titre « **Électricité — réseau et solaire** », **avant** le bloc Assainissement — la note solaire ne se lit plus comme une suite de l'assainissement (§1.8).

**Preuve payload BZ1065** : `viabilisation.band = confirmee` (→ badge « eau/élec confirmée ») ; `anc.statut = source, anc = True` (→ « non collectif — filière autonome à prévoir »). Deux verdicts, chacun honnête.
**Témoins** : BZ1065 (ANC) ; une parcelle en collectif → sous-titre « Assainissement : collectif », badge vert.

## P2 — Une seule médiane appartement (et maison)

**Écart (§1.4).** Trois filtres DVF pour le même appartement, dans le même module `faisabilite/bilan.py` : `sector_price` (« Prix de sortie », dédup mutation, fenêtre récente) = **2 365** ; `reference_locale` (« Médiane par type », **sans dédup**, 2021-2025) = **2 403** ; `dvf_secteur_medianes` (table précalculée, secteur cadastral) = **2 381**.

**Correction (backend, `bilan.py`).** Comme ETUDIER-BIEN-2 pour le terrain nu : **une fonction, une fenêtre, un dédoublonnage**.

- Extraction de `_ventes_bati_dedup` (requête `dvf_mutations` de la commune + dédoublonnage par `mutation_id`) et `_selection_secteur` (fenêtre récente 5 ans préférée puis élargie, rayon adaptatif 500→1000→1500 m, trim des aberrants [1000;12000] + 5 %) **depuis** `sector_price` — comportement de `sector_price` **inchangé** (helpers extraits, byte-identique).
- `reference_locale` (« médiane par type ») construit désormais son échantillon avec **la même requête + le même dédoublonnage + la même fenêtre + le même trim**. Le seul écart de contrat préservé : pas de repli commune ici (None au bout du rayon → l'appelant pige/Radar replie sur la médiane commune).

**Le choix documenté** : fenêtre = période **récente (5 ans, 2021-2025)** préférée, élargie seulement si l'échantillon récent ne tient pas les 8 ventes ; rayon = **adaptatif 500 → 1000 → 1500 m**, le plus serré qui atteint 8 ventes ; dédoublonnage = **par `mutation_id` géo-DVF** (une mutation = une vente ; ne fusionne pas deux ventes distinctes au même prix, fréquent en VEFA) ; trim = **bornes [1 000 ; 12 000] €/m² puis exclusion des 5 % extrêmes**.

**Preuve BZ1065** : « médiane par type · Appartement » passe de **2 403 (43 ventes)** à **2 365 (34 ventes, rayon 1000 m, période récente)** = « prix de sortie » = bilan. **Une seule valeur appartement partout.** Maison : 3 821 (29 ventes, 500 m). `dvf_secteur_medianes` (2 381) n'est servi côté front QUE pour le **terrain nu** (jamais l'appartement, `marche.tsx` : `find(type_bien==='terrain')`) — indicateur secondaire d'une autre maille, inchangé.

**Grep Comparer / Étude de zone** : `comparateur.py` lit `neuf_vefa_commune`/scoring (prix neuf VEFA-commune, autre métrique) ; `zone.py` (Étude de zone) lit `flash.data._marche` (agrégat DVF à la maille mutation, niveau zone). **Ni l'un ni l'autre ne lit `reference_locale`** → non corrigés (hors fiche, comme demandé). Le consommateur partagé de `reference_locale` est la pige/Radar (`_ref_local`) + `mon-secteur par_type`, qui héritent tous de l'unification.

## P3 — Le faîtage LiDAR douteux est signalé

**Écart (§1.6/§1.7).** BZ1065 : faîtage LiDAR **10,3 m** vs BD TOPO **4,2 m** — écart **6,1 m** déjà calculé en base (`batiment_hauteur_lidar.ecart_faitage_bdtopo_m`) mais jamais montré. La p99 du MNS a vraisemblablement capté végétation / structure voisine dans la dalle.

**Seuil retenu : 3 m.** Justification : 3 m ≈ un niveau bâti entier — en deçà, l'écart LiDAR/BD TOPO relève du bruit de mesure normal (arrondi de la hauteur déclarée BD TOPO, débords de toiture) ; au-delà, il désigne vraisemblablement une captation étrangère (arbre, bâti mitoyen), pas un vrai faîtage. Constante `SEUIL_ECART_FAITAGE_M = 3.0` (`bati.py`).

**Correction.** `bati.le_bien_block` sert `hauteur_bdtopo_m`, `ecart_faitage_bdtopo_m` et un drapeau `hauteur_discordante` (écart > 3 m). En front :
- **§3 Bâti** (`leBien.tsx`) : la ligne Hauteur passe en ambre + badge « **Sources discordantes** » + « LiDAR 10,3 m · BD TOPO 4,2 m — à vérifier sur photo aérienne ».
- **§10 Potentiel** (`app.py` + `constructibilite.tsx`) : la marge en hauteur bornée par le **faîtage** hérite du même drapeau (§1.7). Si la contrainte qui mord est l'égout, pas de drapeau (la marge ne dépend pas du faîtage douteux). **Aucun choix automatique** entre les deux mesures.

**Preuve** : BZ1065 `hauteur_discordante = True` (écart 6,1) ; témoin concordant **97401000AL0223** (écart −0,6) `hauteur_discordante = False`.

## P4 — La mixité sociale LLS est branchée

**Écart (§2).** Le calibrage Saint-Denis Uh porte une clause mixité **validée** (30 logements / 15 %, Art. Uh.2 p.71, `statut: valide`), mais la fiche affichait « non renseigné » et la capacité servait **10 étapes au lieu de 11** (ligne mixité restée bloquée sur `pct_lls=0`).

**Correction.**
- `zonage.ZoneRules` porte désormais `mixite` (seuil_logements, quota_pct, article, page, citation, statut), lu des regles calibrées (`_mixite_leaf`).
- `engine.estimate_capacity` : **11e étape « Logements sociaux imposés (LLS) » toujours présente**, pilotée par `rules.mixite` (plus par l'overlay SMS `extras`). Règle **validée** → seuil, part (%), **nombre de LLS résultant** (quota % du programme retenu), badge **Sourcé** + article cité ; sous le seuil → « 0 imposé au seuil » ; `propose` → non validée ; absente → « **non modélisée pour cette zone** » (jamais « non renseigné », jamais un 0 muet).
- `app._reglement_plu_block` sert `mixite` de la zone dominante (`resolve_zone`).
- `Fiche.tsx` tiroir Urbanisme : le bloc « Mixité sociale (LLS) » lit la règle validée (quota, seuil, article + citation, badge Sourcé) ; `propose`/absente → non modélisée.

**Preuve BZ1065** : `resolve_zone('Uh','Saint-Denis').mixite = {seuil_logements: 30, quota_pct: 15, article: 'Article Uh.2', page_pdf: 71, statut: 'valide'}` ; capacité = **11 étapes**, 11e Sourcée « clause 15 % dès 30 logements — programme ~1-2 logts : seuil non atteint » (honnête : la parcelle est petite, le seuil de 30 logements n'est pas atteint, donc 0 LLS imposé — mais la règle est bien branchée et sourcée).
**Témoins** : BZ1065 (validée) ; N Saint-Denis (`mixite = None`) et U1c Saint-Paul → « non modélisée pour cette zone ».
`test_faisabilite1_capacite` mis à jour (nouveau contrat) + `test_mixite_lls_branchee_regle_validee` ajouté.

## P5 — Le parc social dit sa maille (commune)

**Écart (§1.5).** « Parc social 25 185 logements · RPLS » vivait sous « Contexte socio-économique **(secteur)** » alors que le RPLS est à maille **commune** (`rpls_commune`, `insee = left(idu,5)`) — un chiffre communal lu comme du secteur.

**Vérification base + choix.** Seule `rpls_commune` existe (colonnes insee/commune/millesime/nb_logements/…) ; **pas de table RPLS à l'IRIS ni au carreau**. On ne peut donc pas servir une meilleure maille → on l'**étiquette** (`MarcheSecteurBlock.tsx`) : la ligne devient « **Parc social — commune entière** » (src « RPLS 01/01/2025 · maille commune ») ; la note rappelle que niveau de vie / pauvreté sont au **carreau 200 m** et le parc social à la **commune**. Aucune donnée changée.

## P6 — Les écarts restants de LIGNES.csv

| Écart | Cause | Correction | Témoin |
|---|---|---|---|
| **Pente 13,8° (en-tête/Terrain) vs 17,4° (Exposition)** (§1.2) | Deux périmètres RGE ALTI présentés comme un seul : `pente_moy_deg` sur l'**emprise** (13,8°) vs endpoint `exposition` sur une **fenêtre versant 200 m** (17,4°). | On en **garde un** : la pente de l'emprise (tuile « Pente »). L'Exposition ne montre plus **aucune** pente (tuiles d'en-tête ET Terrain) — seulement l'orientation ; l'azimut du versant reste au tiroir Terrain (l'orientation a besoin du contexte du versant, pas la pente). | BZ1065 |
| **Étiquette « 7 À suivre »** (§1.9) | Le compteur `secteur_opportunites.n` additionne **4 tiers** (brûlante/chaude/priorité/à suivre) mais le libellé n'en nommait qu'un. | Libellé → « N parcelles **Priorité ou À suivre** dans cette section ». Le clic (filtre 4 tiers) était déjà cohérent. | BZ1065 |
| **« À vérifier » — repli « N sans objet »** (LIGNES.csv l.56) | Non vérifiable au moment de l'audit : la fiche renvoyait 500. | La fiche réparée, **vérifié** sur BZ1065 : 15 règles, 11 PASS, **10 affichés** (11 − `bati` exclu ; `dpu`/`peb`/`zonage_plu_gpu` absents des PASS). Compte exact par construction — aucun code à corriger, contrôle levé. | BZ1065 |

Les manques du §3 de l'audit (Cartofriches, OLL, trafic RN, CatNat, acquisitions PM voisines) sont **hors mandat** (FICHE-3 à part).

---

## Captures avant/après (`captures/`)

Captées en réel sur l'app lancée en local — **avant** = point de fork de la branche (`fix/fiche-fix-2~6` = `9b010984`, instance API 8406 / vite 5606) ; **après** = branche `fix/fiche-fix-2` (API 8405 / vite 5605). Playwright chromium 1217, deviceScaleFactor 2, carte masquée pour figer les repaints.

| Point | Avant | Après | Témoin |
|---|---|---|---|
| P1 en-tête + tiroir Réseaux | `P1-reseaux-ferme-avant.png`, `P1-reseaux-ouvert-avant.png` | `P1-reseaux-ferme-apres.png`, `P1-reseaux-ouvert-apres.png` | `P1-temoin-collectif-reseaux-ouvert-apres.png` (97411000EI0155, collectif) |
| P3 Bâti (hauteur) | `P3-bati-hauteur-avant.png` | `P3-bati-hauteur-apres.png` | `P3-temoin-concordant-bati-apres.png` (97401000AL0223, écart −0,6, aucun badge) |
| P3 Potentiel (marge) | `P3-potentiel-marge-avant.png` | `P3-potentiel-marge-apres.png` | — |
| P4 Mixité (tiroir) | `P4-mixite-avant.png` | `P4-mixite-apres.png` | — |
| P4 Capacité (11e étape) | `P4-capacite-11-etapes-avant.png` | `P4-capacite-11-etapes-apres.png` | — |
| P5 Parc social | `P5-parc-social-commune-avant.png` | `P5-parc-social-commune-apres.png` | — |
| P6 Tuiles pente/exposition | `P6-tuiles-pente-exposition-avant.png` | `P6-tuiles-pente-exposition-apres.png` | — |
| P6 « À suivre » | `P6-secteur-opp-avant.png` | `P6-secteur-opp-apres.png` | — |

Points saillants observés : P1 en-tête « eau · assainissement · élec — confirmée » → « eau/élec confirmée » + « Assainissement : non collectif » ; tiroir « Électricité — réseau et solaire » remonté avant l'assainissement. P3 « 10,3 m au faîtage » sans flag → ambre + « Sources discordantes · LiDAR 10,3 m · BD TOPO 4,2 m » (bâti + marge) ; témoin concordant sans flag. P4 « non renseigné » → « 15 % / 30 logements » Sourcé (Art. Uh.2) + 11e étape capacité Sourcée. P5 « Parc social » → « Parc social — commune entière · maille commune ». P6 Exposition « pente 17,4° » → « versant (RGE ALTI) » (pente 13,8° gardée une fois) ; « 7 À suivre » → « 7 Priorité ou À suivre ».

---

## État des tests

- **tsc** (`tsc --noEmit`) : vert. **build** (`npm run build`) : vert.
- **vitest** : **187 passed** (47 fichiers), dont fiche 14/14.
- **pytest** (domaines touchés — bilan, mon-secteur, reference, sector_price, faisabilité, capacité, mixité, bati, hauteur, surélévation, potentiel, zonage, reglement, destinations, viabilisation, anc, pige, radar) : **517 passed**, 14 skips (base de test sans parcelle témoin) et **2 échecs PRÉ-EXISTANTS** confirmés à l'identique sur `main`, sans lien avec ce mandat :
  - `test_plu_destinations::test_module_unique_aucune_autre_lecture` (comptes de la chaîne `plu_destinations` identiques à main ; mes diffs ajoutent 0 occurrence) ;
  - `test_hypotheses_source_unique::test_aucune_instanciation_directe_hypotheses` (offender `prospection.py:72`, hors de mon diff, présent sur main).
- `test_fiche_potentiel_cause` **reste vert** (vérifié isolément).
- **grep de non-régression** : aucune autre fonction ne calcule une médiane appartement pour la fiche — `sector_price` et `reference_locale` partagent `_ventes_bati_dedup` + `_selection_secteur` ; `dvf_secteur_medianes` (terrain nu au front), `neuf_vefa_commune` (Comparer, prix neuf), `flash._marche` (Étude de zone, agrégat zone) répondent à d'autres questions et sont étiquetés comme tels.

### La fonction unique de médiane bâti

`faisabilite/bilan.py` :
- `_ventes_bati_dedup(db, parcel_id) → (ventes, n_doublons)` — requête `dvf_mutations` (appartement/maison, surf ≥ 20 m², valeur > 20 000 €, nature vente, commune de la parcelle) + dédoublonnage par `mutation_id`.
- `_selection_secteur(sales, base_plans, min_n)` — période récente (5 ans) préférée puis élargie ; rayon adaptatif 500/1000/1500 m ; trim [1000;12000] + 5 % ; premier plan qui atteint `min_n = 8`.
- `sector_price` (prix de sortie + bilan) et `reference_locale` (médiane par type) appellent les deux ; convergence prouvée BZ1065 (2 365 = 2 365).

### Note d'environnement

- Base réelle `labuse` (rôle `openclaw`, `LABUSE_DATABASE_URL`), venv `~/Desktop/labuse/.venv`, `PYTHONPATH=src`. Aucun verrou rencontré (base libre pendant l'exécution).
- Un `git stash@{0}` étranger (« WIP on fix/plu-ingest-delete-1 ») préexiste dans le dépôt — **non touché** (jamais de `git stash`).
