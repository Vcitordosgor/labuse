# SCORING-DONNÉES-1 — ce que la base contient déjà pour nourrir le score, mesuré au banc K0

**Audit + mesure, lecture seule.** Branche `audit/scoring-donnees-1`. Aucun code servi modifié,
aucune table servie écrite, aucun run lancé, aucune ingestion, aucun promote — `q_v11_m137`
reste le run servi. Scripts : `scripts/audit/scoring/donnees1_*.py` (extension du harnais
SCORING-1/2, banc K0). CSV : `reports/score-v2-arene/donnees1/`.

**Protocole** (règles du mandat, appliquées à l'identique sur tous les lots) : banc K0
(`protocole.py`) — entraîner ≤ 2023 · calibrer 2024 · tester 2025. Point de départ = la recette
**q_v12** (`labuse/scoring/p_v2/qv12.py` : K1c censoring + K2 mortes retirées + K3 résiduel
100 % + K4 bis voisinage global + **isotonique par segment** 2024). Chaque variable est mesurée
**seule, ajoutée à ce candidat**, construite **as-of** (état au 01/01 de l'année de la ligne) —
sinon documentée, pas mesurée. Couverture < 5 % → notée, pas candidate.

**Reproduction contrôlée** : la colonne de base `q_v12_base` refaite par le harnais coïncide avec
la ligne `q_v12` de SCORING-3 à 10⁻⁶ près (AUC 0,620090, lift 2,270690 — `k0_donnees1.csv` vs
`k0_table.csv`). Test de fuite K4 bis rejoué : aucune fuite (`reports/q-v12/q_v12_test_fuite.csv`).
Les variables candidates sont toutes construites sur des prédicats « événement daté < asof »
(permis, mutations, annonces, millésimes) — l'as-of y est structurel.

---

## Lot A — le faux passé (priorité 1)

### A1. Le biais, mesuré

Sur les **58 810 lignes d'apprentissage labellisées 1** (ventes L2-F 2017-2024, la vente qui
fabrique le label étant lue avec son drapeau `bati` — `p_model_ext_mut_l2.bati` ×
`p_model_static.emprise_bati_m2`) :

| variable statique (état 2026) | contradiction mesurée | chiffre |
|---|---|---|
| bâti / nu (emprise BD TOPO) | parcelle **bâtie en 2026** mais **vendue nue** | **14 637 / 43 985 = 33,3 %** des « bâties » labellisées 1 (`a1_biais_bati_nu.csv`) |
| — sens inverse | parcelle nue en 2026 mais vendue bâtie | 5 940 / 14 825 = 40,1 % — en large part des mutations multi-parcelles (le drapeau `bati` porte sur la mutation entière), à lire comme une borne haute |
| dates Sitadel | achèvement ou 1ʳᵉ autorisation **postérieurs à la vente** parmi les 14 637 | 4 344 achèvements + 1 530 autorisations = **35,2 % confirmés par Sitadel seul** (`a1_biais_sitadel_posterieur.csv`) |
| résiduel M125 (`sdp_residuelle_m2`, `sous_densite`) | les 14 637 vendues nues puis bâties ont appris un résiduel **post-construction** | **8 866 ont appris « SDP = 0 »** et 5 664 une SDP amputée — le modèle apprend « peu de droits restants » sur des parcelles qui étaient nues et pleines de droits à la vente (`a1_biais_residuel.csv`) |
| zone PLU (GPU = dernier approuvé) | vente **antérieure à l'approbation du PLU servi** (borne haute : le flip parcelle par parcelle est immesurable) | **13 475 / 58 810 = 22,9 %** ; par année : 51,3 % en 2017, 48,1 % en 2018, 25,0 % en 2019, → 7,4 % en 2024 (`a1_biais_zone_plu*.csv`, `sudocuh_procedures.approbation_opp`) |

Le mécanisme redouté par le mandat est donc réel et massif : une parcelle nue vendue en 2018 puis
bâtie apprend au modèle « le bâti se vend » — un tiers des exemples positifs « bâtis » sont dans
ce cas, et les années anciennes (2017-2018) sont apprises pour moitié sous un zonage qui
n'existait pas encore.

### A2. Ce qui permet (ou pas) de reconstruire l'as-of (`a2_inventaire_asof.csv`)

| source | verdict as-of |
|---|---|
| `cadastre_historique` (7 millésimes 2008-2025) | **inutilisable** : 6 495 géométries en tout sur 431 663 parcelles, pas d'emprise bâtie |
| année de construction MAJIC (`parcel_filtre_bati.annee_construction`) | **inutilisable** : 184 renseignées sur 294 865 (0,06 %) |
| BD TOPO / CoSIA (emprise bâtie) | **impossible seul** : édition unique (2026 ; CoSIA 2025) |
| GPU / zonage (`parcel_zone_plu`) | **impossible par parcelle** : aucune archive géométrique ; `plu_reglement_extrait` = 20 millésimes de *textes* ; seule borne : `sudocuh_procedures.approbation_opp` |
| **Sitadel** (`p_model_permits` × `m10_permit_delais`) | **utilisable** : 59 264 permis 2013-2026, autorisation 100 % datée, achèvement 41 % (20 785/50 290) |
| **DVF** (`p_model_ext_mut_l2.bati`, 2014-2025) | **utilisable** : une mutation bâtie prouve le bâti à sa date, une mutation nue prouve le nu |
| `pm_proprietaires_millesimes` (2019-2024) | utilisable (Lot D) : état propriétaire PM au 01/01 de chaque année |

### A3. Bâti/nu rejoué as-of, mesuré au K0 — la mesure la plus importante du mandat

Reconstruction de l'état physique au 01/01/Y (`donnees1_a.py::_nu_asof_grille`, règles
conservatrices) : parcelle bâtie 2026 réputée **nue au 01/01/Y** si son premier PC est autorisé à
partir de Y et qu'aucune mutation bâtie n'est antérieure ; parcelle nue 2026 réputée bâtie si une
mutation bâtie est postérieure (démolition). Rappel de la reconstruction sur le biais A1 :
**4 831 / 14 637 flips corrigés (33,0 %)** — le solde est constructions sans PC en base
(`a3_rappel_reconstruction.csv`). La **zone as-of est impossible** (A2) : le rejeu ne porte que
le bâti/nu ; le zonage reste le servi, dit et assumé.

Deux variables rejouées (remplacement dans la recette, tout le reste constant) :

| candidat K0 (test 2025) | préc@100 méd. | lift décile | AUC | ECE | verdict |
|---|---|---|---|---|---|
| `q_v12_base` | 0,080 | 2,271 | 0,6201 | 0,0021 | — |
| `A_nu_asof` (remplace `nu_constructible_v3`) | 0,080 | 2,271 | **0,6232** | 0,0021 | **gain** (ΔAUC +0,0031 ; AUC terrain nu 0,6542 → 0,6614) |
| `A_pct_bati_secteur_asof` (remplace `pct_bati_secteur`) | 0,080 | **2,297** | 0,6195 | 0,0021 | **gain** (Δlift +0,026) |
| `A_asof_combine` (les deux) | 0,080 | 2,285 | 0,6226 | 0,0022 | cohérent (informatif — la recette finale les prend séparément) |

## Lot B — profondeur DVF : il n'y a rien à aller chercher

`dvf_mutations_histo` : 110 477 mutations 2014-2020, 45 089 parcelles, toutes natures (Vente,
VEFA, terrain à bâtir, échange, adjudication, expropriation). `dvf_mutations_parcelle` : 102 551
lignes 2021-2025. **Preuve d'absorption** (`b2_tenure_profondeur.csv`) : l'union brute des deux
tables et `p_model_ext_mut_all` (la source de la tenure censurée K1c de q_v12) contiennent
**exactement les mêmes 76 371 parcelles (0 écart dans les deux sens)**, et chaque nature de
l'histo est reprise ligne à ligne (`b3_natures_histo.csv`). Le « % informatif » de la tenure
profonde **est** donc le chiffre actuel : 73 907/431 663 = **17,1 %** — la profondeur 2014
est déjà entièrement consommée, et il n'existe aucune table DVF antérieure à 2014 en base.
**Aucune variable nouvelle possible → pas de mesure K0** (c'est la réponse du lot, prouvée).

## Lot C — gestes précurseurs (`c1_inventaire_gestes.csv`)

| geste | état | as-of | K0 |
|---|---|---|---|
| division cadastrale | traces indirectes seulement (8 912 permis `origine_redecoupee`, 33 `division_or_candidates`) ; **aucune date de création de parcelle en base** | **non** | documenté, pas mesuré |
| DP sur la parcelle | 2 722 DP, 2 492 parcelles, 2013-2026, 100 % datées (natures non distinguées — les DP de division ne sont pas isolables) | oui | `C_dp_parcelle_36m` : préc@100 **0,075** (dégrade) → **écartée** |
| PA (lotissement) | 1 273 PA — le voisin 400 m est **déjà dans la recette** (`operations_pa_400m_24m`) | oui | couvert |
| permis refusés | **absents** : Sitadel open data ne publie que les autorisés | — | documenté |
| PC caduc jamais commencé | `pc_caducs` : 2 161 parcelles, PC 2013-2022, caducité estimée 2016-2025 (« jamais commencé » constaté en 2026 vaut a fortiori pour tout Y antérieur) | oui | `C_pc_caduc_asof` : neutre (AUC −0,0005, lift +0,005) |
| **PC d'une personne morale sur parcelle d'un particulier** | 7 257/46 157 PC portent un SIREN demandeur (les particuliers sont anonymisés) | oui (demandeur) × statique (propriétaire) | `C_pc_pm_sur_parcelle_pp_36m` : **précision Priorité 7,4 % → 30,1 %** (25/83 vendues dans l'année, p≈10⁻⁸ ≫ bruit ±8 pts) ; préc@100/lift/AUC stables, ECE tenu → **gain (tête)** |
| DPE frais (ADEME) | **17 DPE en base** (14 parcelles) — la source est « connectée » mais quasi vide | oui en théorie | couverture ≈ 0,004 % ≪ 5 % → **notée, pas candidate** ; l'ingestion ADEME réelle est le préalable |

Réserve documentée sur `pc_pm_sur_parcelle_pp_36m` : le côté « détenue par un particulier » lit
`owner_type` (statique 2026) — les parcelles achetées par la PM entre-temps en sortent. Le signal
mesuré est donc plutôt une **sous-estimation** du geste (les cas « promoteur a fini par acheter »
sont exclus du positif), mais la version servie devra lire le propriétaire aux millésimes
(2019-2024) — écrit pour la recette q_v13.

## Lot D — bloc propriétaire personne morale (segment PM)

Inventaire (`d1_inventaire_pm.csv`) : `pm_proprietaires_millesimes` 461 570 liens (millésimes
2019-2024, situation au 01/01 — as-of propre) ; `pm_dirigeants` 27 146 dirigeants RNE dont
19 852 avec date de naissance (âge recalculable à toute date) ; `bodacc_annonces_owner` 1 418
annonces datées 2008-2026 (pcl / radiation / vente_cession) ; `owner_enrichment` 9 730 SIREN dont
9 700 avec date de création (la « dormance RNE » `date_mise_a_jour_rne` est un état 2026 : PAS
as-of) ; `parcel_veille_succession` 7 129 lignes `computed_at` 2026 → **documentée, pas mesurée
telle quelle** — son contenu (âge du dirigeant, SCI dormante) est **recalculé as-of** ici.

Cinq variables construites as-of, verdict lu sur le segment PM (`d2_couverture_pm_par_annee.csv`) :

| candidat K0 | préc@100 | lift | AUC PM | ECE PM | verdict |
|---|---|---|---|---|---|
| `q_v12_base` | 0,080 | 2,271 | 0,6725 | 0,0048 | — |
| `D_dirigeant_age_max_asof` | 0,075 | 2,262 | 0,6664 | 0,0049 | **écartée** : couverture 4,9 % du dataset (≈ un quart du segment PM a un dirigeant daté) ET dégrade l'AUC PM (−0,006) |
| `D_sci_agee_asof` | 0,080 | 2,275 | 0,6742 | 0,0049 | neutre (+0,0017 d'AUC PM, sous le seuil +0,002) |
| `D_bodacc_36m` | 0,080 | 2,270 | 0,6725 | 0,0048 | neutre (1 418 annonces sur toute l'île : trop rare pour peser) |
| `D_pm_entree_recente` | 0,080 | 2,272 | 0,6677 | 0,0063 | **écartée** : inservable au scoring 2026 (le millésime PM de l'année n'existe pas → couverture 0 as-of service) et ECE PM dégradé |
| `D_ventes_pm_secteur_36m` | 0,080 | **2,321** | 0,6732 | 0,0054 | **neutre (ECE PM dégradé +7·10⁻⁴)** — c'est pourtant le meilleur lift global du mandat (+0,050) : à remesurer dès qu'un millésime PM courant raccourcira le décalage acquéreur |

La limite structurelle du bloc D est la **fraîcheur** : le dernier millésime propriétaire est
2024 — toute variable propriétaire est périmée de deux ans au scoring 2026, et la détection
« acquéreur PM » s'arrête aux ventes 2023. Le signal existe (lift), la donnée est en retard.

## Lot E — ce que le PLU annonce (`e1_inventaire_plu.csv`)

| objet | état |
|---|---|
| emplacements réservés | **présents** : 741 polygones GPU (`spatial_layers` kind=`plu_gpu_prescription`) — **statiques** (un seul millésime) → documentés, pas mesurés |
| OAP | **absentes** des couches en base |
| ZAC | **absentes** (le SAR et le potentiel foncier existent, pas les périmètres ZAC) |
| changement de zonage entre millésimes GPU | **impossible** : aucune archive géométrique |
| commune en procédure | `sudocuh_procedures` : 11/24 communes en procédure (prescription datée) — mais les procédures **closes** n'ont pas d'historique → « en procédure au 01/01/Y » irreconstructible ; + registre humain `config/veille_plu.yaml` |
| **ancienneté du PLU** (la seule variable proprement as-of) | `E_anciennete_plu_annees` : lift **2,271 → 2,297**, ECE 0,0020 (meilleur que base), AUC PM 0,676 → **gain** (couverture 99 % en 2026, manquant explicite avant l'approbation) |

## Lot F — sources non ingérées : fiches (`f1_fiches_sources.csv`), rien d'ingéré

Faits vérifiés le 06/09/2026 — URLs testées, fichiers réellement téléchargés et comptés.

**INSEE RP 2022 à l'IRIS** (parution 16/10/2025 ; RP 2023 = communal seulement). 974 couvert :
**344 lignes IRIS** (343 IRIS + La Plaine-des-Palmistes en bloc). Mais sur les 4 indicateurs du
mandat, **2 n'existent pas à l'IRIS** : l'ancienneté d'emménagement s'arrête à « 10 ans ou plus »
(`P22_MEN_ANEM10P`) et « personne de référence 75 ans+ » n'est pas ventilé (proxys :
`P22_POPMEN80P`, `P22_POP75P`) ; vacance (`P22_LOGVAC`) et résidences secondaires (`P22_RSECOCC`)
sont là. Jointure : code IRIS → parcelle par la couche `iris_insee` **déjà en base**. Licence
ouverte 2.0. Coût : **faible, ~1 jour**.

**RPG 2024** (éd. 3.0, GPKG R04 testé, 47 Mo) : **22 722 parcelles déclarées, 35 730 ha, dont
canne (CSA) 7 505 parcelles / 18 539 ha**. Aucun identifiant cadastral → intersection géométrique
(EPSG:2975 commun). Licence ouverte. Coût : **faible-moyen, 1-2 jours** ; éditions annuelles
depuis 2015 re-téléchargeables → un as-of partiel est même possible.

**BDNB 2026-02.a** : **La Réunion toujours absente** — métadonnée `country-subset:fr:metro`,
départements 01-95+2A/2B, sonde S3 `dep95`→200 / `dep974`→403, aucune extension DROM au
changelog. Confirme SCORING-3 L3 ; la veille L3 détectera un éventuel ajout. Clé prête le jour
venu : `rel_batiment_groupe_parcelle` (IDU cadastral).

**Radar agrégé commune × type** (`f4_radar_etat_serie.csv`) : **infaisable** — `radar_releves`
(la série) est vide, 108 annonces sur **2 jours** (29-30/08/2026), 62 % à Saint-Denis, collecte
manuelle. À réévaluer avec des mois de profondeur.

---

## Lot G — le tableau unique, les verdicts, la recette

### Le tableau unique (format SCORING-2 — `k0_donnees1.csv`, base en première colonne)

Chaque ligne = le candidat q_v12 + UNE variable (test 2025, hors copro pour les métriques de
rang ; Priorité donnée avec son bruit ±8 pts, jamais seule).

| candidat | préc@100 méd. | Priorité (n) | lift décile | AUC | AUC PM | ECE | churn vs servi |
|---|---|---|---|---|---|---|---|
| **q_v12_base** | 0,080 | 7,4 % (81) | 2,271 | 0,6201 | 0,6725 | 0,0021 | 48,4 % |
| A_nu_asof | 0,080 | 7,4 % (95) | 2,271 | **0,6232** | 0,6675 | 0,0021 | 47,6 % |
| A_pct_bati_secteur_asof | 0,080 | 7,2 % (83) | **2,297** | 0,6195 | 0,6737 | 0,0021 | 48,9 % |
| A_asof_combine | 0,080 | 6,6 % (91) | 2,285 | 0,6226 | 0,6646 | 0,0022 | 47,8 % |
| C_dp_parcelle_36m | 0,075 | 7,3 % (82) | 2,275 | 0,6201 | 0,6726 | 0,0021 | 48,5 % |
| C_pc_caduc_asof | 0,080 | 7,4 % (81) | 2,275 | 0,6195 | 0,6725 | 0,0022 | 48,4 % |
| C_pc_pm_sur_parcelle_pp_36m | 0,080 | **30,1 % (83)** | 2,268 | 0,6209 | 0,6736 | 0,0022 | 50,8 % |
| E_anciennete_plu_annees | 0,080 | 7,2 % (83) | **2,297** | 0,6199 | 0,6761 | 0,0020 | 49,4 % |
| D_dirigeant_age_max_asof | 0,075 | 9,5 % (84) | 2,262 | 0,6201 | 0,6663 | 0,0022 | 53,5 % |
| D_sci_agee_asof | 0,080 | 7,4 % (81) | 2,275 | 0,6199 | 0,6742 | 0,0021 | 48,4 % |
| D_bodacc_36m | 0,080 | 7,4 % (81) | 2,270 | 0,6200 | 0,6725 | 0,0021 | 48,4 % |
| D_pm_entree_recente | 0,080 | 7,6 % (92) | 2,272 | 0,6181 | 0,6677 | 0,0027 | 48,4 % |
| D_ventes_pm_secteur_36m | 0,080 | 5,9 % (85) | **2,321** | 0,6202 | 0,6732 | 0,0020 | 49,0 % |
| **q_v13_candidat** | 0,080 | **30,9 % (81)** | 2,266 | **0,6242** | 0,6660 | 0,0023 | 51,4 % |

### Verdict par famille (`g1_verdicts.csv`)

Règle pré-enregistrée (`donnees1_g.py`, la même pour tous) : **gain** si Δpréc@100 > 0 OU
Δlift ≥ +0,02 OU ΔAUC ≥ +0,002 OU ΔPriorité ≥ +16 pts (2× le bruit ±8 du mandat), avec
Δpréc@100 ≥ 0 et ECE ≤ base + 5·10⁻⁴ ; Lot D lu sur le segment PM ; couverture < 5 % → écartée.

| famille | verdict | le chiffre qui le justifie |
|---|---|---|
| **A — bâti/nu as-of** (`A_nu_asof`) | **gain** | AUC 0,6201 → 0,6232 (+0,0031) |
| **A — % bâti secteur as-of** | **gain** | lift 2,271 → 2,297 (+0,026) |
| A — zone as-of | **impossible as-of** | aucune archive GPU par parcelle (borne : 22,9 % des labels 1 appris sous un PLU postérieur) |
| B — profondeur DVF | **rien à gagner** | union brute = source servie, 0 parcelle d'écart ; 17,1 % = déjà le chiffre profond |
| C — DP sur parcelle | neutre | préc@100 0,080 → 0,075 (dégrade) |
| C — PC caduc | neutre | AUC −0,0005, lift +0,005 |
| **C — PC de PM sur parcelle de particulier** | **gain (tête)** | précision Priorité 7,4 % → 30,1 % (25/83, ≈ 4× ; p ≈ 10⁻⁸ ≫ 2× bruit) |
| C — division cadastrale | **impossible as-of** | aucune date de création de parcelle en base |
| C — DPE frais | **à ingérer** | 17 lignes en base (couverture ≈ 0,004 % ≪ 5 %) |
| D — âge dirigeant | écartée | couverture 4,9 % ET AUC PM −0,006 |
| D — SCI âgée / BODACC | neutres | AUC PM +0,0017 / +0,0000 |
| D — entrée récente en PM | écartée | inservable en 2026 (millésime absent), ECE +6·10⁻⁴ |
| D — ventes vers PM (secteur) | neutre (ECE PM) | lift 2,321 (le meilleur du mandat) mais ECE PM 0,0048 → 0,0054 ; à remesurer avec un millésime PM frais |
| **E — ancienneté du PLU** | **gain** | lift 2,271 → 2,297, ECE 0,0020 (meilleur que base) |
| E — ER / OAP / ZAC / zonage entre millésimes | **impossible as-of** (ER statiques ; OAP/ZAC absents) | `e1_inventaire_plu.csv` |
| F — RP IRIS, RPG | **à ingérer** | fiches vérifiées, coût ~1-2 jours chacune (2 des 4 indicateurs RP absents à l'IRIS) |
| F — BDNB | **à ingérer… quand la source couvrira le 974** | sonde S3 : dep974 → 403 |
| F — Radar agrégé | infaisable | série de 2 jours (108 annonces) |

### Recette q_v13 recommandée

**q_v13 = q_v12 + les quatre gains prouvés, et rien d'autre** :

1. `nu_constructible_asof` (REMPLACE `nu_constructible_v3`) — bâti/nu reconstruit à la date ;
2. `pct_bati_secteur_asof` (REMPLACE `pct_bati_secteur`) — part bâtie du secteur à la date ;
3. `pc_pm_sur_parcelle_pp_36m` (AJOUT) — le promoteur sous compromis ; **en service, lire le
   propriétaire aux millésimes PM** (l'arène a mesuré avec `owner_type` statique, qui
   sous-estime le geste) ;
4. `anciennete_plu_annees` (AJOUT) — ancienneté du PLU de la commune.

Mesuré ensemble au K0 (ligne `q_v13_candidat`) : **AUC 0,6201 → 0,6242**, **précision Priorité
7,4 % → 30,9 % à effectif constant (81)**, préc@100 stable 0,080, lift 2,27 stable, ECE 0,0023
(tenu), churn top-1158 vs servi 51,4 % — les gains s'additionnent sans se neutraliser, et la
tête de liste change de nature : une Priorité sur trois se vend dans l'année, contre une sur
treize aujourd'hui. Les deux variables A corrigent en outre le faux passé À LA SOURCE (le modèle
n'apprend plus « le bâti se vend » sur des ventes de terrains).

Ce qui n'entre PAS et pourquoi : `dp_parcelle_36m` (dégrade préc@100), `pc_caduc_asof` (neutre),
tout le bloc D (couverture, fraîcheur des millésimes, ECE), `ventes_pm_secteur_36m` (meilleur
lift du mandat mais ECE PM dégradé — premier candidat à remesurer quand le millésime PM courant
sera ingéré).

### Les 50 premières du candidat recommandé face au servi (`g2_top50.csv`)

Les 50 premières du classement 2026 du candidat (hors copro), chacune avec ses trois
contributions principales en français — extrait :

| rang | idu | rang servi | tier servi | contributions principales |
|---|---|---|---|---|
| 1 | 97416000ET2242 | 39 | brûlante | ancienneté du dernier permis (+1,17) · permis déposé par un professionnel (SIREN) sur une parcelle détenue par un particulier (+0,88) · permis à moins de 100 m (+0,26) |
| 2 | 97416000ET2243 | 26 | brûlante | idem (parcelle jumelle) |
| 3 | 97416000CS0269 | 193 | déclassée bâti saturé | ancienneté du dernier permis (+1,17) · permis d'un professionnel sur parcelle de particulier (+0,88) · piscine détectée (+0,37) |
| 4 | 97411000AL0497 | 313 | chaude | permis d'un professionnel (+0,88) · ventes à moins de 150 m (+0,25) |
| 5 | 97422000AX1477 | 105 | chaude | croisement ancienneté de détention × surface (+1,85) · ancienneté de détention (+0,84) · zone du PLU (+0,41) |

Lecture d'ensemble des 50 : **33 sont déjà chaude ou brûlante** au run servi (dont 11 dans son
top-50) — la tête n'est pas renversée, elle est **resserrée** sur les parcelles à geste de
promoteur ; 12 sont aujourd'hui déclassées ou écartées (bâti saturé, zone, AU) et remontent par
le signal permis — à instruire au cas par cas, les gates du pipeline restant souverains.

Manifeste : `reports/score-v2-arene/donnees1/g3_manifeste.json` (protocole, couvertures,
variantes, verdicts, hygiène de la cible, test de fuite).

Rien n'est promu, rien n'est servi : **`q_v11_m137` reste le run servi.**
