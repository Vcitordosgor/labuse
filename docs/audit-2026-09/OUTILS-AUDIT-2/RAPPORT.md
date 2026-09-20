# RAPPORT OUTILS-AUDIT-2 — Les 17 outils après les chantiers

**Exécuté par :** CC (Fable), 20/09/2026 — lecture seule.
**Branche :** `feat/outils-audit-2` depuis `main` **`85ac26a5`** (étape 0, worktree propre au départ).
**Run servi :** `q_v11_m137` (`config/served_manifest.json`, fait foi ; `served_run.txt` = vue dérivée BASCULE-1).
**Environnement de mesure :** API dédiée `:8065` (uvicorn local, base `labuse` 431 663 parcelles), Vite `:5265`, `LABUSE_API_DEV` pointé dessus. `labuse circuit verrous` **jamais lancé**. Parcelle témoin : **97410000AN0347** (Saint-Benoît, 4 501 m², zone N/Nerl, propriétaire COMMUNE DE SAINT BENOIT — PM publique, tier `ecartee`).
**Preuves :** `captures/outils-audit2/` (20 PNG : 17 outils + fiche ×2 + Scan ×2) · `tsc -b` **vert** (exit 0).
**Référence :** `docs/audit-2026-09/OUTILS-AUDIT/RAPPORT.md` (audit du 06/09, 15 outils). Depuis, mergés dans main : OUTILS-FIX-1→4, OUTILS-MUSCLER-1/1B/2/3 (+2 outils : Successions M28, Blocs fonciers M29), FICHE-1, SOURCES-1→5 (92 sources), COMPTE-2, COUCHES-1/2 + couches-tuyau, PALIERS-1, EXPORTS-2, TAXE-AMENAGEMENT-1, RECETTE-1→4/12, CIRCUIT-4/5/6, PLU-CALIBRAGE-1→5, REPARATIONS-1.

## LES TROIS CHIFFRES

| | |
|---|---|
| **Outils entièrement à jour** | **10 / 17** — assemblage, blocs-fonciers, successions, permis, plu, courriers, renouvellement, prospection-solaire, etude-zone, temps |
| **Outils qui lisent un vestige (actif, sur le chemin servi)** | **6** — scoreur-adresse (`score_e`), programme (`ta_note` fausse), taxe-amenagement (écran pré-TA-1), comparer (`contrainte_majeure` perdue), patrimoine (`f.owner_siren` inexistant), risques (append ZNIEFF périmé → doublon) |
| **Chiffres divergents outil/fiche** | **5** — taux TA (fiche 5 % / outil « à saisir ») · étiquette zone (fiche « Nerl » / outil « N ») · propriétaire (fiche « COMMUNE DE SAINT BENOIT » / Scan « pas de PM ») · neuf VEFA Évolution (1 304 €/m² n=6 / « — » partout ailleurs) · « dormants » commune (103 vs 565 sous le même mot) |

`communes` n'est ni « entièrement à jour » ni « lit un vestige » : ses deux accrocs sont des divergences de seuil/définition, pas des vestiges.

**Écart mandat vs réel — « les 51 couches »** : sur main, le tuyau couches sert **56 couches** (`/map/tuyau/couches`, `api/couches_tuyau.py:504`) dont **38 déclarées** dans `declarations/couches/famille_*.yaml` ; le chiffre 51/52 vient de `feat/raccordement-1` (**non mergée** — `CouchesGeneriques` absent d'ici). Les contrôles « couches » ci-dessous sont donc faits contre le tuyau réel de main.

---

## RÉCAPITULATIF DES CONSTATS NEUFS (inconnus au 06/09)

### 🔴 Fonction cassée / faux servi
1. **Scan patrimoine — l'entrée par IDU et le repli adresse sont cassés pour TOUTES les parcelles** : `ownerDeIdu` lit `f.owner_siren` à la racine du payload fiche (`ScanPatrimoine.tsx:68-73`) alors que ce champ n'existe que sous `score_v.owner_siren` (`app.py:3775-3790` — il n'a jamais été à la racine, vérifié `git log -S`). Mesuré à l'écran : IDU 97410000AN0347 → « Cette parcelle n'a pas de propriétaire personne morale connu » pendant que la fiche affiche COMMUNE DE SAINT BENOIT (capture `08-scan-patrimoine-idu-casse.png`). L'entrée SIREN/nom fonctionne (capture `08b`).
2. **Faisabilité — `fiscal.ta_note` sert un mensonge** : « Taxe d'aménagement : taux communal non ingéré — à confirmer en mairie » (`modules.py:1757-1760`), FAUX depuis TAXE-AMENAGEMENT-1 (table 24/24). Rendu fiche §7 à trois lignes du bloc taxe qui affiche le taux public 5 % + millésime DELTA — contradiction dans un même écran.
3. **Taxe d'aménagement — le front n'a jamais branché la table des taux** : le paramètre `insee` de l'endpoint calcul (`app.py:2641`) n'est envoyé nulle part (`api.ts:504-526`, `TaxeAmenagement.tsx` : 0 occurrence, `git log -S insee` : rien). L'outil exige la saisie manuelle du taux que LABUSE connaît (mesuré : sans insee → `total_eur:null` ; avec `insee=97410` → 5 % public, millésime, total 6 690 € pour 100 m²). Le code millésime de l'outil (`TaxeAmenagement.tsx:282-291`) est mort — inatteignable.
4. **Comparer — ligne « Contrainte majeure » dégradée en permanence** : `majeure` calculée (`app.py:6398-6399`) mais la clé `contrainte_majeure` a disparu du payload au commit `e6b7b5bb` (22/08) ; le front la lit toujours (`api.ts:1048`) → repli « N signalée(s) » pour toujours. Antérieur au 06/09, jamais repéré.

### 🟠 Divergences chiffrées
5. **Fiche parcelle — étiquette de zone fausse par agrégation** : `_reglement_plu_block` GROUP BY `sl.subtype` + `max(attrs->>'libelle')` (`app.py:4969-4978`) → sur AN0347 le confetti **Nerl de 7 m²** (0,15 %) donne son libellé à 99,96 % de part agrégée ; la fiche cite le règlement Nerl (espaces remarquables du littoral) quand l'outil Faisabilité dit N ordinaire. Bug côté fiche, visible en cohérence outil/fiche.
6. **Communes/Évolution — seuil VEFA non appliqué** : `_barometre_data` sert `neuf_reference` sans le seuil `marche_service.neuf_vefa_seuil()` = 8 (`moteurs.py:766-770`) ; mesuré Saint-Benoît : Évolution affiche **1 304 €/m² sur 6 ventes** quand le comparateur (`comparateur.py:64`) et la fiche commune disent « — ».
7. **Deux « dormants » sous le même mot** : fiche commune = `pc_caducs` (103 à Saint-Benoît, `fiche_commune.py:202-204`) vs outil Permis = `permis_point_mort` run-scopé 36 mois (565). Deux définitions, zéro distinction à l'écran.
8. **Risques — ZNIEFF ×2 au crible** : le run q_v11_m137 contient désormais une couche cascade `znieff` ET l'append géométrique « hors cascade » de M137-U reste (`modules.py:1541-1543`, commentaire périmé) ; la dédup (clé layer+detail) ne replie pas `znieff`/`ZNIEFF`. Mesuré sur AN0347 : 2 lignes pour 1 fait.

### 🟡 Notables
- **Scan patrimoine — encart INPI trompeur sur PM publique** : « Aucun dirigeant au registre INPI — succession ou société en sommeil probable » affiché pour une **commune** (les personnes publiques ne sont pas à l'INPI ; la garde FIX-3 B3 ne teste que rows+nom). Blocs fonciers sait écarter les publics (`is_public`), le Scan non.
- **Courrier — le plafond du jour compte la mauvaise table** : `envois_du_jour` lit `courrier_envois` (chemin d'envoi direct DORMANT) ; le flux servi écrit `courrier_demandes` → « reste 100/100 » ne bougera jamais (28 demandes en base, `envoyes_jour: 0`).
- **PLU — les règles calibrées se perdent au bloc fiche pour les zones U sans hauteur exploitable** : `resolve_reglement` conditionne `regles_valeurs` à `rules.calibree` or `_zone_generique` rend `calibree=False` même quand l'overlay applique des feuilles validées (`zonage.py:190-192`, `plu_reglement.py:109-126`). Prouvé sur 97410000AB0003 (Ub) : `regles_valeurs:[]` alors que `resolve_zone` porte emprise 80 % « Art. U 5 · p.10 (calibrage validé) ». Les citations calibrées sortent par les steps Faisabilité, pas par le bloc « règlement PLU ».
- **Risques — couches cascade nouvelles limitées à ~53 parcelles du run** (tri_zone 53, endiguement 53, znieff 53, dpu 53, peb 56…) : le backfill île entière = rejeu de run (geste Vic, déjà identifié RECETTE-4). O5 compense en live `spatial_layers` pour ses 13 kinds mais **pas** tri_zone/endiguement.
- **Perf simulateur AU→U** : `/moteurs/simulplu?zone=AUc&commune=Saint-Benoît` mesuré **32-35 s** (×2 tirs) contre 0,39 s au 06/09 (percentile + ILIKE sur 15,9 M lignes).
- **Blocs fonciers — fraîcheur** : un seul build (07/09) épinglé sur le run résiduel 2 (calculé 22-23/08, AVANT PLU-CALIBRAGE) — cohérent avec la vue servie, mais divergera de la SDP live recalibrée tant que ni run résiduel ni `blocs-build` ne sont rejoués (geste Vic).
- **Successions — donnée figée au 09/08** (`score-v-compute` jamais rejoué, décision Vic actée) — l'écran date honnêtement (bandeau + RNE 06/07).

### Corrigés depuis le 06/09 (vérifiés au code ET mesurés)
Les 3 🟠 d'alors sont soldés : pied Solaire lit `source_millesime` en base (FIX-1 A1) ; CSV solaire branché PUIS retiré sur décision Vic tracée (FIX-3 E) ; colonne Surélévation retirée des deux côtés (FIX-1 C1, 100 % NULL en base). Également soldés : pont Scan→Courrier (FIX-2/3), pont permis→Scan, ponts Étudier→Faisabilité/Assemblage, saisie clavier Assemblage + voisines proposées (MUSCLER-1), badges Sourcé/Estimé + fourchette logements + saisie IDU de Comparer (FIX-2 D), millésime MAJIC affiché (FIX-4 A1), tiroir seuils risques lu de `cascade_rules.yaml` (FIX-4 C1), CATNAT au crible (C2), dédup aléas (C3 — mesuré 1 seule ligne mvt sur AC0024), plafond courrier à l'ouverture (D), code mort MOBPRO supprimé (CIRCUIT-6), PDF baromètre et export.pdf étude de zone supprimés (EXPORTS-2), `plu_rules` mort (0 référence, PLU-CALIBRAGE-4), doute « deux chemins revenu » tranché (source unique, mesuré identique).

---

# LES 17 TABLEAUX

> Format : les 5 contrôles du mandat. « Registre » = `src/labuse/registre` (robinets/donnees/lectures) + `/sources/rattachements` (`app.py:5547`). Mesures live sur `:8065`, parcelle témoin 97410000AN0347 sauf mention.

## 1. Étudier un bien (`scoreur-adresse` O2 · alias M23/S1)

| Contrôle | Constat |
|---|---|
| **Affiche** | Prix secteur bâti/type/terrain nu + annonces (`mon_secteur.py` → `sector_price`/`marche_service.filtre_ventes`), constat parcelle (`scoreur.py:209-226`), dernières ventes parcelle (`dvf_mutations_parcelle`, LIMIT 6), charge calibrée (`compute_bilan_servi`). **En dur** : « ventes actées 2021-2025 » (`EtudierBien.tsx:192` — millésime qui pourrira), badges Sourcé/Estimé par champ (constantes front), SEUIL_N=5, bornes terrain nu 20-3000 (`mon_secteur.py:37`) |
| **Lit** | `parcels`, `parcel_p_score_v2` (runs.current()), **`score_e` legacy**, DVF, pige. Robinet `outil_etudier_bien` déclare **`/modules/scoreur-adresse` — route réelle `/scoreur-adresse`** (`robinets.py:162-163`) ; lecture `score_e` absente de `lectures.py` |
| **Bougé** | Prix via marche_service ✓ (sauf `_terrain_local` SQL direct documenté) ; run servi ✓ ; adresse mon-secteur résolue (donnée, pas code). **Vestige : `score_e` toujours lu** (`scoreur.py:129-138`) — et sa valeur n'est même plus servie (front envoie `prix=null` toujours) : lecture morte à chaque requête. Docstring :10 cite encore `served_run.txt` |
| **N'affiche pas** | `parcel_terrain.pente_max/flag_terrassement` (dans getFiche, non affichés), `dpe_records` (1 123 désormais), `catnat_arretes`, `taxe_amenagement_taux` |
| **Cohérence fiche** | **OK mesuré** : bâti secteur **1 360 €/m²** (appartement, n=30, 500 m) = fiche `prix_ancien.median` 1 360 ; tier/rang/percentile/surface identiques ; refus propre en zone N des deux côtés. Capture `01` |

**Verdict : lit un vestige** (`score_e`) — le reste à jour.

## 2. Faisabilité (`programme` M22)

| Contrôle | Constat |
|---|---|
| **Affiche** | Capacité + steps sourcés (`engine.estimate_capacity`), charge (`bilan`), liste critères paginée. **En dur (invisibles en mode critères)** : coef occupation 0,45 · rendement 0,80 · densité 30 lgt/ha/niveau · reculs 5/3 m · étage 3,0 m (`engine.py:63-71`, surchargeables YAML) ; coûts 2300/2800 désormais SOURCÉS (`cout_construction_ref`) |
| **Lit** | Zone via `zone_servie.zone_dominante` (plus jamais le centroïde), règles via **`faisabilite/zonage.py`** + calibrages `plu.destinations` (feuilles `valide` seulement), `spatial_layers` (pente/ER/EBC/QPV…), `marche_service.marche_dvf`. Robinet `outil_faisabilite` ✓ ; **`/modules/programme` sans robinet** |
| **Bougé** | `plu_rules` mort ✓ ; run servi ✓ (`runs.cascade()` + `_v2run`) ; payload critères 959 Ko → **340 Ko mesuré**. **Vestige servi FAUX : `fiscal.ta_note` « taux communal non ingéré »** (`modules.py:1757-1760`), contredit par le bloc taxe du même écran |
| **N'affiche pas** | `taux_emprise_pct`/`sous_densite` en mode critères (inchangé 06/09), `parcel_terrain.pente_max`, `taxe_amenagement_taux` (au bloc fiscal) |
| **Cohérence fiche** | Valeurs **OK** (zone N, SDP 0, refus `capacite_non_resolue` des deux côtés — capture `02`) ; **étiquette KO** : fiche « Nerl 99,96 % » (bug GROUP BY `app.py:4969-4978`) vs outil « N » |

**Verdict : lit un vestige** (`ta_note`) + 1 divergence d'étiquette (bug fiche).

## 3. Taxe d'aménagement (`taxe-amenagement` K3)

| Contrôle | Constat |
|---|---|
| **Affiche** | Barème 100 % piloté back (`config/taxe_amenagement.yaml` millésime 2026, source citée) ; détail ligne à ligne ; total NULL sans taux ✓. Rien de chiffré en dur au front |
| **Lit** | YAML + prefill `parcels`/`parcel_zone_plu`/`parcel_residuel` (`taux_emprise_pct` désormais lu). **`taxe_amenagement_taux` (24/24, vérifiée psql) : lue par la FICHE et les EXPORTS, PAS par l'outil.** Robinet déclare `/modules/taxe-amenagement` ≠ route réelle `/outils/taxe-amenagement` (`robinets.py:167-168`) |
| **Bougé** | **KO principal : le front n'envoie jamais `insee`** (`api.ts:504-526`) → saisie manuelle obligatoire d'un taux que la base connaît ; code millésime de l'outil mort (`:282-291`) ; hint « à confirmer auprès du département » (`:220`) contredit `part_departementale_confirmee_974: true` |
| **N'affiche pas** | `taxe_amenagement_taux` (le cœur du sujet), `parcel_residuel.cause` |
| **Cohérence fiche** | **KO mesuré** : fiche = taux communal **5 % public + millésime DELTA + 2,5 % confirmé** ; outil = champ vide obligatoire, total null. Avec `insee=97410` le back rend 6 690 €/100 m² — le dernier mètre front manque. Captures `03` / `00` |

**Verdict : PAS à jour** (écran pré-TA-1) — back prêt, front pas câblé.

## 4. Pièges et risques (`risques` M10 + O5)

| Contrôle | Constat |
|---|---|
| **Affiche** | Crible lot (`/modules/duediligence` → cascade `runs.cascade()` + CATNAT + ZNIEFF + PM) ; servitudes parcelle (`/servitudes-invisibles`, 13 kinds datés/sourcés) ; **tiroir seuils branché** (lit `cascade_rules.yaml` : PPR 2/50/10 %, cavité 50 m, ICPE 50/150/300). **En dur servis** : barème 70/50/30/10 + 100 + bonus 10 (`modules.py:1481-1485`), bandes libellé front ≥60/≥30, checklist cap 5 |
| **Lit** | `dryrun_cascade_results` (run servi), `spatial_layers`, `catnat_arretes` (426 — FIX-4 C2 ✓), `parcelle_personne_morale`. Nouvelles sources : submersion servie via aléas ✓ ; TRI/endiguement en couche carte mais **pas dans O5** (`_KINDS`) et seulement ~53 parcelles au run ; SUP acte/générateur en popup carte, pas dans O5 |
| **Bougé** | Doublon aléa AC0024 **corrigé** (C3, mesuré 1 ligne) ; **vestige : commentaire M137-U « ZNIEFF hors cascade » périmé → ZNIEFF ×2 au crible** (couche cascade + append géométrique, dédup inopérante) ; crible non arbitré (multi-niveaux par aléa) vs fiche arbitrée (max) — présentation |
| **N'affiche pas** | tri_zone/endiguement dans O5 ; SUP acte/générateur dans O5 ; `mvt_overlays`, `bodacc_sondages` |
| **Cohérence fiche** | **OK mesuré** : risque 100/100, 3 HARD (zone N 100 %, PPR rouge 100 %/54 %), CATNAT 17 arrêtés (dernier 20/03/2025), tier `ecartee` = fiche ; O5 : 5 servitudes datées. Capture `04` |

**Verdict : lit un vestige** (append ZNIEFF périmé) — le reste à jour.

## 5. PLU (`plu` O13 + M15)

| Contrôle | Constat |
|---|---|
| **Affiche** | Annuaire 24 communes (23 PLU/1 RNU, 2 « texte en mairie » dits), recherche verbatim (`plu_reglement_extrait`, 3 258 — inchangé), pack GPU, vérif procédure (confiance SOURCE/DEDUIT), simulateur AU→U (ratio servi back) |
| **Lit** | Corpus extraits + GPU + `veille_plu.yaml` + **calibrage PLU-CALIBRAGE : 23/23 communes « calibree / à jour » (`/sources/calibrages`), 1 832 règles `valide` / 150 `propose`** — consommé par le moteur faisabilité/fiche, **pas par l'annuaire** (deux corpus parallèles non fusionnés) |
| **Bougé** | `plu_rules` supprimé proprement (`7fd90541`, −405 l., 0 réf.) ✓ ; run servi ✓. Vestige : docstring `plu_reglement.py:4` cite `config/plu_<commune>.yaml` disparus. 🟡 perf simulplu 32-35 s (vs 0,39 s au 06/09) |
| **N'affiche pas** | `regles_valeurs` calibrées perdues au bloc fiche pour zones U sans hauteur (`calibree=False` malgré overlay — prouvé 97410000AB0003) ; citations calibrées absentes de l'annuaire ; `parcel_au_statut`/`parcel_pau`/`sudocuh` brut (inchangé, assumé) |
| **Cohérence fiche** | **OK mesuré** : zone N/Nerl (⊂ N), tier `ecartee` partout, procédure « aucune, confiance SOURCE, constat 06/08 » ; PLU Saint-Benoît 06/02/2020 servi annuaire ET fiche. Capture `05` |

**Verdict : à jour** (réserves = trous de service, pas vestiges).

## 6. Comparer des parcelles (`comparer` A8)

| Contrôle | Constat |
|---|---|
| **Affiche** | 17 lignes ROWS aux mêmes moteurs que la fiche (`_compare_row` → `fiche_payload`/`_q_v2_fiche`/`build_marche_commune`). Badges Sourcé/Estimé ✓ (FIX-2 D2) mais classification EN DUR front ; fourchette logements lo–hi ✓ (D3) ; saisie IDU ✓ (D1) |
| **Lit** | Tout via moteurs fiche (run servi partout). **Robinet registre pointe `/comparateur-communes` avec des chiffres COMMUNE** (`robinets.py:177-178`) — le vrai `/compare` n'a aucun robinet |
| **Bougé** | Les 4 manques 06/09 corrigés (badges, fourchette, saisie, export retiré sur décision). **Régression : `contrainte_majeure` calculée jamais servie** (payload perdu à `e6b7b5bb` ; front `api.ts:1048` → repli compteur permanent) |
| **N'affiche pas** | `parcel_terrain.pente`, `parcel_solar`, `taxe_amenagement_taux` (comparable de coût candidat), `dpe_records`, `catnat_arretes` |
| **Cohérence fiche** | **OK mesuré** : tier/rang/surface identiques ; zone « N » vs « Nerl » = granularité famille (même bug de libellé fiche qu'en 2) ; prix 1 445 = fiche `dvf_parcelle.secteur` maison (conforme à son libellé). Capture `06` |

**Verdict : lit un vestige** (clé payload disparue) — le reste à jour.

## 7. Assemblage (`assemblage` M16)

| Contrôle | Constat |
|---|---|
| **Affiche** | Voisines proposées (ST_DWithin 0,5 m, « même propriétaire » trié serveur), analyse d'assiette via **`fiche_payload`** par parcelle (plus jamais la somme des résiduels), gain calculé back, PM nommées/particuliers comptés. Cap 30 = config (`config/moteurs.yaml:10`) |
| **Lit** | `parcels`, `parcel_p_score_v2` + `dryrun_parcel_evaluations` (run servi/`runs.cascade()`), `parcelle_personne_morale`, `p_model_ext_dataset` (SDP voisines). Robinet `outil_assemblage` ✓ |
| **Bougé** | Voisines MUSCLER-1 **branchées** ✓, saisie clavier **ajoutée** ✓ (les 2 manques 06/09 soldés). Vestiges dormants : `GET /assemblages` (`app.py:5688`), `GET /assemblage/study` (`:5700`), `voisinage.assemblage_unlock` (`:6116`) — 0 lecteur front |
| **N'affiche pas** | `dvf_mutations`/`sitadel_permits` des voisines, `pc_caducs`, `score_assemblage` (dormant assumé). ⚠ 3 expressions de SDP « Estimé » (voisines=feature store, analyse=fiche live, blocs=parcel_residuel) peuvent différer sur une même parcelle |
| **Cohérence fiche** | **OK mesuré** : AN0347+AN0346 → contigu, 7 906 m², SDP 0, tier `ecartee` ×2, PM COMMUNE DE SAINT BENOIT = fiche. 6 voisines dont 5 même propriétaire à l'écran. Capture `07` |

**Verdict : à jour.**

## 8. Scan patrimoine (`patrimoine` M02 + S3)

| Contrôle | Constat |
|---|---|
| **Affiche** | Bandeau « DGFiP · situation 2025 » **lu en base** (FIX-4 A1 ✓), 4 KPI (dont valorisation Estimé en synthèse, A2 ✓), signaux BODACC/INPI, liste 200 paginée, pont Courrier ✓ (cases + « ✉ Préparer les courriers (n) », FIX-2/3), frise promoteur (filiales par `pm_dirigeants.gerant_siren`) |
| **Lit** | `parcelle_personne_morale` (+`millesime` désormais lu ✓), run servi partout (tier épinglé + `runs.cascade()`), `v_foncier_sous_pression`, `sitadel_permits`. Valorisation via `ligne2_terrain_nu_zone` = le référentiel unique terrain nu (pas un moteur parallèle) |
| **Bougé** | Tous les 🟡 06/09 soldés SAUF : **🔴 entrée IDU/adresse cassée** (`f.owner_siren` lu à la racine, n'existe que sous `score_v` — cf. récap 1) ; **encart INPI trompeur sur PM publique** (une commune n'est pas à l'INPI) ; CSV : bouton retiré sur décision, endpoint + helper orphelins assumés |
| **N'affiche pas** | **`bodacc_depots` (14 078, NOUVEAU SOURCES-5) : 0 lecteur API**, `bodacc_sondages`, `pm_dirigeants` noms/dates, `rnic` (fiche seule), historique millésimes à la parcelle (fiche seule), croisement SIREN×succession |
| **Cohérence fiche** | **KO sur l'entrée IDU** (fiche : COMMUNE DE SAINT BENOIT ; outil : « pas de propriétaire PM » — captures `08`/`08b`) ; par SIREN : OK (990 parcelles, 316 actionnables, SDP 623 607 m², 333,9 M€ Estimé, millésime 2025 ; item AN0347 tier `ecartee` = fiche) |

**Verdict : lit un vestige** (champ payload inexistant) → entrée annoncée cassée.

## 9. Courrier propriétaire (`courriers` M09)

| Contrôle | Constat |
|---|---|
| **Affiche** | 3 étapes ; état + plafond à l'ouverture (FIX-4 D ✓, carte affichée que si disponible) ; 4 gabarits EN DUR front (contact victor@labuse.immo, RECETTE-5) ; adresse propriétaire jamais servie (design) ; tarif jamais affiché client |
| **Lit** | `parcels` seul côté client. Pas de scoring → run sans objet. Mail admin via `mail.send_email_async` (SMTP direct), **PAS la file `mail_queue` COMPTE-2** (réservée cycle de vie client) |
| **Bougé** | Statuts unifiés (source unique `courrier.py:92-103`) ✓. **Vestiges : `POST /modules/courriers` mort** (`modules.py:1456-1472` + gabarits doublons `_COURRIER`) **et le robinet registre `outil_courrier` déclare cette route morte** (`robinets.py:188`). 🟡 plafond compté sur `courrier_envois` jamais alimenté par le flux demandes |
| **N'affiche pas** | Type de propriétaire au ciblage (PM publique/privée/particulier — il accepterait d'écrire « À l'occupant » d'une parcelle communale en zone N), `parcel_veille_succession` au choix du gabarit |
| **Cohérence fiche** | **OK** : statut stub `{disponible:false, tarif 4,04 €, plafond 100/100}` ; destinataire = mêmes `parcels` que la fiche. Capture `09` |

**Verdict : à jour** (vestiges dormants au back/registre, hors chemin servi).

## 10. Densifier l'existant (`renouvellement` MR1)

| Contrôle | Constat |
|---|---|
| **Affiche** | Barre « ma parcelle », top 5 + note datée, tableau (SDP nette + puce −N %), couche geojson (troncature dite 1 500/total). Pondérations 47/29/24 et facteurs 0,5/0,85/0,90 = **config** (`renouvellement.yaml`) ; **en dur** : max recopiés `app.py:4722` (doublon config), défauts de repli `renouvellement.py:84-87`, facteurs toujours pas dits à l'écran |
| **Lit** | `parcel_renouvellement` (67 260, **100 % run q_v11_m137**, rebuild 14/09), cascade du run, feature store. Couche = geojson ad hoc hors tuyau (assumé « overlay dérivé d'outil ») |
| **Bougé** | **Colonne Surélévation soldée des deux côtés** (FIX-1 C1 ; 100 % NULL mesuré) ; pont Faisabilité ✓ (FIX-2 A2) + Comparer ; vocabulaire PALIERS-1 résolu front. Vestiges dormants : colonnes `surelevation_*` au DDL (« à supprimer au prochain rebuild »), robinet `outil_densifier` → **URL `/modules/renouvellement` inexistante** (`robinets.py:210`) |
| **N'affiche pas** | `dpe_records` (17 → **1 123** : pertinence montée), `parcel_vegetation` (431 663 — regroupement 10 du 06/09 toujours pas fait), BDNB/vacance absents de la base |
| **Cohérence fiche** | **OK mesuré** : hors segment des deux côtés (zone N prouvée psql ; bloc fiche `renouvellement:null` = même source). Liste : total 67 260, maj 14/09, run q_v11_m137 servi. Capture `10` |

**Verdict : à jour.**

## 11. Permis (`permis` M03 + M04)

| Contrôle | Constat |
|---|---|
| **Affiche** | Partition Tous/Récent/Dormant/Achevé/Autres **exacte** (mesuré île : 50 544 = 5 580+15 549+20 534+8 881), source unique états/couleurs (`permisEtats.ts`), moteurs registre (`compte_permis_commune`, `permis_point_mort`), drawer complet. En dur : 24/36 mois (dits à l'écran), rayons 100/200 m, LIMIT 60 000 carte |
| **Lit** | `sitadel_permits` (dmax 31/07/2026 servi), `m10_permit_delais`, `via_permits_geo`, cascade au run servi. `cadastre_historique` consommé à l'ingestion (rattachement d'époque) |
| **Bougé** | Pont → Scan du porteur ✓ (FIX-2 A4) ; dormants paginés (56 Ko mesuré). Vestiges dormants : `tier_v2/rang_v2` servis par `/promesses` non affichés ; M05 dormant lit `rang_delai` plus servi (`ModulePanel.tsx:929-931`) ; `p_model_permits` (59 568) toujours orpheline de l'outil |
| **N'affiche pas** | Croisement dormants × millésimes PM/DVF (« changé de mains ? » — regroupement 3 du 06/09 toujours pas fait), `bodacc_depots` du porteur |
| **Cohérence fiche** | **OK par construction** : outil et bloc Autour de la fiche appellent le MÊME `/modules/parcelle-permis` (mesuré c100=1, c200=8 sur AN0347). Capture `11` |

**Verdict : à jour.**

## 12. Communes (`communes` O6 + M18)

| Contrôle | Constat |
|---|---|
| **Affiche** | 4 portes (Comparaison / Évolution / **Radar marché (nouvelle)** / Acquisitions). Comparaison = moteurs registre, une source par indicateur. En dur : bornes 100-12 000, terrain 5-5 000, min 100 ventes, 5 ans permis, 8 trimestres, budget ZAN −50 % ; seuil VEFA en config |
| **Lit** | `parcel_p_score_v2` (run servi), `m10_permit_delais`, `sitadel_permits`, SRU, `commune_conso_enaf`, DVF, `pm_proprietaires_millesimes`. Maille commune HORS `marche_service` — doctrine documentée (`app.py:1946-1948`), seuil VEFA partagé via `neuf_vefa_seuil()` |
| **Bougé** | Double vocabulaire paliers tenu ; « Priorité » masquée (REPARATIONS-1). **🟠 seuil VEFA non appliqué dans l'Évolution** (`moteurs.py:766-770` : neuf 1 304 €/m² sur 6 ventes servi quand tableau et fiche disent « — ») ; **🟠 deux « dormants »** (fiche commune `pc_caducs` 103 vs outil run-scopé 565). Vestiges dormants : libellé « brûlantes ou chaudes » sans consommateur (`app.py:2198`), O7Carnet dormant, fiche de règle `prix_ancien_median_eur_m2.py:11` citant `marche_service` au lieu de `moteurs.py` |
| **N'affiche pas** | **`rp_logement_commune` (24, NOUVEAU SOURCES-5) : 0 lecteur API** ; `annuaire_services` (ops seul) ; `bodacc_depots` ; `taxe_amenagement_taux` hors comparateur ; OCS GE ZAN hors comparateur ; filosofi/rpls/insee_logement = fiche commune seule (inchangé) |
| **Cohérence fiche** | Outil ↔ fiche commune : **identité mesurée** (1 838 €/m²/n=634, terrain 237, vélocité 8,0, permis 907 — mêmes fonctions) ; fiche parcelle 1 360 = métrique locale documentée. **KO** : neuf Évolution (cf. Bougé). Capture `12` |

**Verdict : pas entièrement à jour** (2 divergences de seuil/définition) — pas de vestige actif.

## 13. Prospection solaire (`prospection-solaire` M26)

| Contrôle | Constat |
|---|---|
| **Affiche** | Fiche soleil 8 KPI ; **kWc/production calculés AU BACK** (FIX-1 A6, hypothèse 0,2 kWc/m² lue de `config/prospection_solaire.yaml` et DITE à l'écran) ; **millésime lu en base** (`max(source_millesime)` → « relevé 2026-08-23 ») ; piscines comptées SQL ; limites avouées (maille 400 m, ombrage, « panneaux existants non détectés ») |
| **Lit** | `parcel_solar` (431 663), `parcel_equipements` (8 299 piscines), `toiture_lidar` (27 — à la demande), `parcel_terrain`, run servi pour le classement |
| **Bougé** | Les 2 🟠 du 06/09 **soldés** ; pv_* abandonnés (précision 0 %, décision Vic, avoué à l'écran) ; pont Courrier ajouté PUIS retiré (RECETTE-1 R23, tracé). Vestiges DOC : commentaires « gelées 11/07 » démentis par la base (`ProspectionSolaire.tsx:2-3`, `modules.py:708/758`, `registry.ts:116`) ; helper CSV orphelin (`api.ts:858`) |
| **N'affiche pas** | `ghi_kwh_m2_an`/`score_solaire` (jamais servis), `dpe_records` (1 123 — cibles passoires pertinentes), `pente_max` (fiche seule) |
| **Cohérence fiche** | **OK mesuré : 1 540 kWh/kWc = 1 540** (fiche `viabilisation.solaire.prod_kwh_kwc`). Écran : 69,8 kWc, 107 492 kWh/an, relevé 23/08. Capture `13` |

**Verdict : à jour.**

## 14. Étude de zone (`etude-zone` M27)

| Contrôle | Constat |
|---|---|
| **Affiche** | Habitants/ménages/revenu badgé (Filosofi carreaux), **emplois en fourchette** (tranches SIRENE, non-renseignés dits), concurrents datés, marché 12/36 mois, trafic RN par axe daté, zones PLU en parts, zone de demain (Sitadel+AU), verdict sous-destination (calibrage PLU) |
| **Lit** | `filosofi_carreaux_200m`, `sirene_etablissements`, DVF, pige, `sitadel_permits`, `spatial_layers` (BPE/PLU/transport), `trafic_rn`, `arcep_immeubles`, isochrones IGN (échec → « indisponible », jamais un cercle) |
| **Bougé** | Code mort MOBPRO **supprimé** (CIRCUIT-6, verrou G6) ; export PDF **supprimé** (EXPORTS-2 — mais `api.ts:378 etudeZonePdfUrl` orphelin reste) ; doute « deux chemins revenu » **tranché et mesuré** (même requête carreau-centroïde, `app.py:5237-5244`). En dur : millésimes littéraux (« Filosofi 2021 », « BPE 2025 », « Arcep 2026_T1 ») non lus de `data_sources` |
| **N'affiche pas** | **`res.fibre` servi-muet** (1 161 immeubles, 99,4 % FttH servis, cité dans la note, aucun bloc écran) ; **`population.iris`** (vacance, bâti <1990) servi non rendu — 2 candidats à brancher ou cesser de servir |
| **Cohérence fiche** | **OK mesuré** : habitants 3 228 == 3 228 (Autour) ; revenu fiche/Autour = même carreau (None/None sur AN0347) ; l'outil affiche 15 453 € = revenu de la ZONE (18 carreaux), objet distinct étiqueté. Capture `14` |

**Verdict : à jour.**

## 15. Remonter le temps (`temps` M08)

| Contrôle | Constat |
|---|---|
| **Affiche** | Comparateur swipe 7 couches ortho — **libellés = couches IGN exactes, vérifiés couche par couche** (tuiles proxy vivantes 200) ; zones noires légendées ; **frise des faits (MUSCLER-2)** : ventes (`dvf_mutations_parcelle` + **`dvf_mutations_histo`**), permis (3 événements), propriétaire (changements `pm_proprietaires_millesimes`), découpes (`dfi_filiation` 409 623) — millésimes des 4 sources affichés |
| **Lit** | Orthos via proxy backend uniquement ; corpus cadastre 35 millésimes (SOURCES-5) exploité à l'ingestion (rattachement permis), pas par l'outil |
| **Bougé** | Le manque 06/09 (« ne renvoie vers rien ») **comblé** : 3 ponts (Permis, fiche-ventes, Scan). `basemaps.ts:24` : vestige **non reproduit — clos**. Restes : `flux.py:72` déclare `temps` sans moteur alors qu'il consomme `/moteurs/histoire` ; lectures DVF de l'histoire absentes du registre (`dvf_mutations_histo` jamais déclarée dans `lectures.py`) |
| **N'affiche pas** | Géométrie `cadastre_historique` (contours d'époque sur l'ortho ancienne — seule vraie marge restante) ; propriétaire stable = 0 fait (by design, la fiche montre l'historique complet) |
| **Cohérence fiche** | **OK mesuré** : AN0347 frise n=0 = fiche (0 vente/0 permis/0 DFI — état vide honnête à l'écran) ; contrôle positif 97421000AL0499 : fait-à-fait identique (vente 07/01/2021, découpe 16/11/2015). Capture `15` |

**Verdict : à jour** — 2 ⚠ « non servies » du 06/09 (dvf_histo, millésimes PM parcelle) levées par cet outil.

## 16. Blocs fonciers (`blocs-fonciers` M29 — NOUVEAU)

| Contrôle | Constat |
|---|---|
| **Affiche** | Liste des blocs (SDP « Estimé », parcelles, surface, zonages, SIREN), bandeau millésime PM + build lus en base, publics écartés par défaut (dit + case), détail membres, ponts Assembler/Scan/Courrier. En dur : MIN_PARCELLES=2 (`blocs.py:32`), paliers filtres front ; 0,5 m = constante partagée assemblage, dite à l'écran |
| **Lit** | `parcel_blocs`/`parcel_bloc_membres` (build : PM même SIREN, union-find), résiduel = vue SERVIE (`residuel_run_seq=2` épinglé sur 11 225 blocs = manifeste). **Aucun robinet registre → M29 invisible de `/sources/rattachements`** (tables déclarées, lectures déclarées, robinet absent) |
| **Bougé** | Outil créé 07/09 ; publics écartés (6 361 privés / 4 864 publics mesurés). ⚠ fraîcheur : un seul build (07/09) sur résiduels calculés 22-23/08 — AVANT PLU-CALIBRAGE : cohérent avec la vue servie, divergera de la SDP live recalibrée tant que rien n'est rejoué (geste Vic) |
| **N'affiche pas** | Le regroupement 7 du 06/09 (« clusters fonciers PM ») est **désormais SERVI — acté** (11 225 blocs, 59 835 membres). Restent : croisement bloc × BODACC/succession, historique millésimes, DVF du bloc |
| **Cohérence fiche** | **OK mesuré** : AN0347 ∈ bloc 28762 (COMMUNE DE SAINT BENOIT, 7 parcelles, 16 806 m², SDP 0, is_public → écarté par défaut) ; SDP 0 = résiduel 0 = assemblage 0 = fiche `ecartee`. Capture `16` |

**Verdict : à jour** (trou registre à combler).

## 17. Successions à venir (`successions` M28 — NOUVEAU)

| Contrôle | Constat |
|---|---|
| **Affiche** | Cartes (SDP « Estimé », zone, PM+SIREN, motif dirigeant ≥70 ans / SCI dormante), bandeau « signal RNE INPI au 09/08/2026 » lu en base, seuils dits à l'écran, « jamais “en succession” » respecté (wording + avertissement serveur), pont Courrier |
| **Lit** | `parcel_veille_succession` (7 129) + jointures parcels/zone/PM. Seuils = constantes code (`score_v_constants.py:171-172,192-193` — 70 ans, SCI 20/5 ans, « 3-7 ans »), pas config. **Aucun robinet registre → M28 invisible de `/sources/rattachements`** (comme M29) |
| **Bougé** | Créé MUSCLER-1/1B ; depuis : RECETTE-1 mineur. **Donnée figée au 09/08** (`score-v-compute` jamais rejoué — décision Vic actée ; daté honnêtement à l'écran, 42 j au 20/09). Table snapshot mono-run (pas de run_label — assumé, SDP même grandeur que la fiche) |
| **N'affiche pas** | La ⚠ 06/09 `parcel_veille_succession` « jamais exploitée » est **levée — acté**. Reste : `pm_proprietaires_millesimes` (ancienneté de détention), date « depuis » (impossible amont RNE, documenté) |
| **Cohérence fiche** | **OK mesuré** : AN0347 hors veille (0 ligne psql ; commune 398 parcelles en veille — c'est la parcelle, pas un trou) = fiche sans badge. Écran : 7 129, top Saint-Leu 57 018 m²/89 ans. Capture `17` |

**Verdict : à jour côté code/écran** (donnée = geste Vic, daté).

---

# LISTE 1 — VESTIGES

## Actifs (sur le chemin servi — les 6 outils comptés)
1. **`score_e`** encore lu par `scoreur.py:129-138` à chaque requête — et sa valeur n'est plus jamais servie (front envoie `prix=null`) : lecture morte. Autres lecteurs restants : `app.py:1482` (filtre marge), `app.py:1676-1687` (presets charge), `tiles.py:276`, `bascule_gardes.py:770`, `sonde_circuit.py:357`.
2. **`fiscal.ta_note` « taux communal non ingéré »** (`modules.py:1757-1760`) — faux depuis TA-1, servi et rendu fiche §7.
3. **Taxe : écran pré-TA-1** — `insee` jamais envoyé (`api.ts:504-526`), hint « à confirmer » (`TaxeAmenagement.tsx:220`), commentaire périmé (`:96`), code millésime mort (`:282-291`).
4. **Comparer : `contrainte_majeure`** calculée (`app.py:6398-6399`) jamais mise au payload depuis `e6b7b5bb` ; front la lit (`api.ts:1048`).
5. **Scan : `f.owner_siren`** lu à la racine (`ScanPatrimoine.tsx:68-73`) — n'existe que sous `score_v` → entrée IDU/adresse cassée.
6. **Risques : append ZNIEFF « hors cascade »** (`modules.py:1541-1543`, commentaire M137-U périmé) → ZNIEFF ×2 au crible.

## Dormants (servis/présents, zéro lecteur)
- `POST /modules/courriers` (`modules.py:1456-1472`) + gabarits `_COURRIER` (`:1432-1453`) ; **le robinet `outil_courrier` déclare cette route morte** (`robinets.py:188`).
- Assemblage : `GET /assemblages` (`app.py:5688`), `GET /assemblage/study` (`:5700`, cap 8 en dur), `voisinage.assemblage_unlock` (`:6116`), `_params()` PLACEHOLDER (`assemblage.py:21-27`).
- Helpers front orphelins : `etudeZonePdfUrl` (`api.ts:378` — route supprimée), `pdfUrl` (`:993`), `prospectionSolaireCsvUrl` (`:858`), `modPatrimoineCsvUrl` (`:1162`).
- Densifier : colonnes `surelevation_possible`/`niveaux_surelevation` au DDL, 100 % NULL (retrait au prochain rebuild, assumé) ; M05 dormant lit `rang_delai` plus servi (`ModulePanel.tsx:929-931`).
- Communes : libellé serveur « N parcelles brûlantes ou chaudes » (`app.py:2198`) sans consommateur ; `O7Carnet`/`O10` dormants ancien vocabulaire.
- Division : `/modules/division*` dormant ACTÉ (décision Vic 19/08, `api.ts:1155`) — pas une découverte.

## Registre menteur / troué (le circuit `/sources/rattachements` ne voit pas juste)
- Routes de robinets fausses : `outil_etudier_bien` → `/modules/scoreur-adresse` (réel `/scoreur-adresse`) ; `outil_taxe_amenagement` → `/modules/taxe-amenagement` (réel `/outils/…`) ; `outil_densifier` → `/modules/renouvellement` (inexistant) ; `outil_courrier` → `/modules/courriers` (mort) ; `outil_comparer_parcelles` → `/comparateur-communes` avec chiffres COMMUNE (le `/compare` parcelles n'a aucun robinet).
- **M28 Successions et M29 Blocs : AUCUN robinet** → invisibles des rattachements (le front les connaît, le registre back non).
- `regles/prix_ancien_median_eur_m2.py:11` cite `marche_service.py` — la fonction vit à `api/moteurs.py:648`.
- Lectures non déclarées : DVF de `/moteurs/histoire` (`dvf_mutations_histo` absente de `lectures.py`), `score_e` du scoreur ; `flux.py:72` déclare `temps` sans moteur.

## Docs/commentaires périmés (rien à l'écran)
`scoreur.py:10` (served_run.txt), `plu_reglement.py:4` (plu_<commune>.yaml), `servitudes.py:9/29` (PEB), commentaires « gelées 11/07/2026 » (solaire ×4), `ScoringV2.tsx:7` (q_v10_m129), `TaxeAmenagement.tsx:96`.

## Clos depuis le 06/09 (vérifié)
`plu_rules` (0 référence, module supprimé), code mort MOBPRO (supprimé, verrou G6), PDF baromètre (supprimé en entier), `/outils/etude-zone/export.pdf` (route supprimée), `basemaps.ts:24` (non reproduit).

# LISTE 2 — DIVERGENCES OUTIL/FICHE (les 5 chiffres)

| # | Chiffre | Fiche | Outil | Cause |
|---|---|---|---|---|
| 1 | Taux TA communal (AN0347) | **5 % public + millésime DELTA + 2,5 % confirmé** | champ vide obligatoire, total null | front n'envoie pas `insee` (jamais câblé) |
| 2 | Étiquette zone (AN0347) | **« Nerl » part 99,96 %** | Faisabilité/Comparer : **« N »** | fiche : GROUP BY subtype + max(libelle) élit le confetti 7 m² (`app.py:4969-4978`) |
| 3 | Propriétaire (AN0347, entrée IDU) | **COMMUNE DE SAINT BENOIT / 219740107** | Scan : « pas de propriétaire PM connu » | `f.owner_siren` inexistant à la racine |
| 4 | Prix neuf Saint-Benoît | fiche commune + comparateur : **« — » (n=6 < 8)** | Évolution : **1 304 €/m² (6 ventes)** | seuil `neuf_vefa_seuil()` non appliqué (`moteurs.py:766-770`) |
| 5 | « Dormants » Saint-Benoît | fiche commune : **103** (`pc_caducs`) | outil Permis : **565** (run-scopé 36 m) | deux définitions sous le même mot |

Écarts NON comptés (moteurs distincts, étiquetés, documentés) : 1 360 €/m² (sector_price local) vs 1 445 (dvf_parcelle secteur maison) vs 1 838 (agrégat commune) — chacun porte son n/rayon/millésime ; revenu carreau (fiche) vs revenu de zone (outil) ; servitudes O5 (5) vs vigilances cascade (12) — périmètres différents nommés. Présentation : crible M10 non arbitré (multi-niveaux par aléa) vs fiche arbitrée au max — le score n'est pas gonflé.

# LISTE 3 — DONNÉES EN BASE NON SERVIES

## Levées depuis le 06/09 (sur les ~16 d'alors)
`dvf_mutations_histo` (110 k → frise M08) · `pm_proprietaires_millesimes` à la parcelle (→ frise, changements) · `parcel_veille_succession` (→ M28) · clusters PM (→ M29 `parcel_blocs`, 11 225) · `catnat_arretes` (→ crible Risques) · `rnic_coproprietes` (→ fiche) · `dvf_mutations_parcelle` dernières ventes (→ Étudier un bien) · `parcelle_personne_morale.millesime` (→ bandeau Scan) · `taxe_amenagement_taux` (0 → 24/24, → fiche + exports — **PAS l'outil Taxe**, cf. divergence 1).

## Restent non servies (aucun outil)
- **`bodacc_depots` (14 078, NOUVEAU SOURCES-5) : 0 lecteur API** — signal dépôt de comptes/cessation, naturel au Scan et aux dormants Permis.
- **`rp_logement_commune` (24, NOUVEAU SOURCES-5) : 0 lecteur API** — 24 variables logement, naturelles au comparateur Communes.
- `annuaire_services` (436) : lu par `api/ops.py` (admin) seulement.
- `bodacc_sondages` (12 605), `pm_dirigeants` détail (noms/dates — EXISTS + gérance seuls), `parcel_amenites` (431 k), `parcel_vegetation` (431 k — regroupement 10 « canopée sur résiduel » toujours pas fait), `parcel_au_statut` (10 537), `parcel_pau` (2 656), `mvt_overlays` (6 009), `score_snapshot_parcelles` (3,45 M, archives), `_lota_grave_parcels` (73 k), `cadastre_historique` au-delà du rattachement permis (contours d'époque), `mobpro_commune` (0, conservée documentée).
- Champs morts : `parcel_solar.ghi_kwh_m2_an`/`score_solaire` ; `parcel_equipements.pv_*` (0 partout — abandon ACTÉ, avoué à l'écran) ; `parcel_terrain.pente_max_deg`/`flag_terrassement_lourd` (fiche seule, pas les outils).
- `dpe_records` : **17 → 1 123 lignes** — lu par la fiche (FICHE-1), toujours ni Densifier ni Solaire (cibles passoires).

## Servis par l'API mais muets à l'écran
Étude de zone : `res.fibre` (Arcep, cité dans la note de sources !) et `population.iris` (vacance, bâti <1990). Permis : `tier_v2/rang_v2/statut` des dormants ; `raw.surf_hab` en liste. Assemblage : `score_assemblage` (doctrine faits-pas-notes, assumé). PLU : `veille_plu.raisonnement` (choix retenu) ; **`regles_valeurs` calibrées perdues au bloc fiche** pour les zones U sans hauteur (`calibree=False` malgré overlay — cas 97410000AB0003).

## Couches cascade en attente de run
tri_zone/endiguement/znieff/dpu/peb/bassin_versant/bruit_carte… présentes dans q_v11_m137 pour **~53 parcelles seulement** (backfill FICHE-COUCHES-2 partiel) — le rejeu île entière est le geste « run » déjà identifié (RECETTE-4) ; O5 compense en live pour ses 13 kinds, pas pour tri_zone/endiguement.

---

# COMPTE-RENDU (15 lignes)

1. **10/17 outils entièrement à jour · 6 lisent un vestige actif · 5 chiffres divergents outil/fiche.** Le run servi q_v11_m137 est épinglé partout où il doit l'être (17/17 vérifiés, `runs.current()`/`runs.cascade()`/`_v2run`) ; `plu_rules` est mort sans reste ; les prix passent par `marche_service` ou par LE moteur nommé de leur maille (doctrine commune documentée) — aucun moteur prix parallèle ressuscité.
2. Les trois constats les plus lourds sont NEUFS (aucun n'était au rapport du 06/09) :
3. — **Le Scan patrimoine a son entrée IDU/adresse cassée pour toutes les parcelles** (`f.owner_siren` lu à un endroit du payload où il n'a jamais existé) — l'outil dit « pas de propriétaire » quand la fiche l'affiche.
4. — **L'outil Taxe d'aménagement n'a jamais branché la table des 24 taux qu'il a lui-même motivée** (TA-1 mergée : fiche et exports servis, l'outil exige encore la saisie manuelle) — et la Faisabilité sert en plus une note « taux non ingéré » désormais fausse.
5. — **La fiche étiquette la zone au libellé d'un confetti** (GROUP BY subtype : « Nerl » 7 m² baptise 99,96 % de N) — visible dès qu'on croise outil et fiche.
6. Les 3 🟠 du 06/09 sont soldés et mesurés (pied solaire, CSV décidé-retiré, surélévation) ; les ponts manquants (Scan→Courrier, →Faisabilité, →Assemblage, permis→Scan) sont tous en place.
7. Les 2 outils nés depuis (Successions, Blocs) sont propres, run-scopés/épinglés et honnêtes à l'écran — mais **invisibles du registre back** (aucun robinet → absents de `/sources/rattachements`), et leurs données ont un « dernier geste » qui date (score-v 09/08 ; blocs-build 07/09 sur résiduels pré-calibrage).
8. Le registre ment par endroits : 5 routes de robinets fausses ou mortes, 1 fiche de règle citant le mauvais fichier, des lectures non déclarées — le Circuit croit des chemins qui n'existent plus.
9. Divergences de seuil à la maille commune : le neuf VEFA de l'Évolution ignore le seuil n≥8 que tout le reste applique ; « dormants » recouvre deux définitions (103 vs 565).
10. Réserve de puissance : les 2 nouvelles tables SOURCES-5 (`bodacc_depots` 14 k, `rp_logement_commune` 24) n'ont AUCUN lecteur API ; `parcel_vegetation` (431 k) et le croisement dormants×mutations restent les regroupements non faits les plus denses ; `dpe_records` est passé de 17 à 1 123 lignes et attend Densifier/Solaire.
11. Cohérence outil/fiche sur la parcelle témoin : 14/17 outils strictement cohérents (mêmes moteurs ou même endpoint) ; les 3 KO sont les n° 1-3 de la liste 2.
12. Limites : mesures locales (pas la prod) ; parcelle témoin en zone N chez un propriétaire public — elle exerce bien les refus propres et la privacy, moins les chemins « capacité/bilan » (couverts par les mesures API des agents sur d'autres parcelles) ; perf simulplu 32 s à confirmer hors contention machine.
13. Aucune modification de code ni écriture en base ; le serveur local a exécuté son auto-réparation de schéma standard (idempotente).
14. Livrables : ce rapport + 20 captures `captures/outils-audit2/` ; `tsc -b` vert ; un commit, branche poussée.
15. Gestes suggérés (Vic tranche) : réparer les 4 fils courts (owner_siren, insee Taxe, ta_note, contrainte_majeure), appliquer le seuil VEFA à l'Évolution, combler les robinets M28/M29 et corriger les 5 routes menteuses du registre.
