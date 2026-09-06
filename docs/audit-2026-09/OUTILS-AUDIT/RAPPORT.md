# RAPPORT OUTILS-AUDIT-1 — Audit des 15 outils en lecture seule

**Exécuté par :** CC (Fable), 06/09/2026 — mandat `docs/audit-2026-09/OUTILS-AUDIT/MANDAT.md`.
**Branche :** `audit/outils-1` (depuis `fix/retours-12`, contient RETOURS-13/14/15 — vérifié étape 0).
**Run servi :** `q_v11_m137` (`config/served_run.txt` + `config/served_manifest.json`, relu vivant par `src/labuse/runs.py:49`).
**Environnement de mesure :** base Postgres locale (431 663 parcelles), serveur `uvicorn labuse.api.app:app` local, auth désactivée. Les temps A8 sont des temps locaux (machine de dev), pas des temps prod.

## Écart menu réel vs liste du mandat

Le menu réel (registry.ts, entrées non `hidden`) compte bien 15 outils mais diffère de la liste du mandat sur deux points :

- **« Mon secteur » n'est plus au menu** : clé `mon-secteur` passée `hidden`, fusionnée dans « Étudier un bien » (`frontend/src/components/outils/registry.ts:115`, RETOURS-3 R5). Son contenu est audité dans la fiche 1.
- **« Remonter le temps » est au menu** (`registry.ts:148`) et absent de la liste du mandat. Il est audité en fiche 15.

L'ordre audité est l'ordre réel du menu. Clés aliasées résolvantes sans carte : `calculette-fonciere`→1, `mon-secteur`→1, `veille-promoteurs`→8, `barometre`→12, `promesses`→11.

## Les 3 parcelles fixes de l'audit

| Parcelle | Commune | Zone | Surface |
|---|---|---|---|
| `97411000AB0009` | Saint-Denis | Uavap (U dense) | 449 m² |
| `97415000AC0024` | Saint-Paul | Acu | 2 551 m² |
| `97417000AE0003` | Saint-Philippe | RNU (aucune ligne `parcel_zone_plu`) | 1 906 m² |

---

## RÉCAPITULATIF DES KO

### 🔴 Faux chiffre servi ou donnée périmée
Aucun constaté sur les 75 appels mesurés et les 15 chaînes table→moteur→écran suivies. Les trois candidats historiques (aplat zonage, aléas ELEVE/TRES_ELEVE servis « moyen », libellés d'année ortho) sont corrigés sur cette branche (CIRCUIT-2 lot 4 ; libellés temps = couches IGN exactes, `frontend/src/components/map/basemaps.ts:53-79`).

### 🟠 Fonction annoncée absente ou cassée
1. **Solaire — pied de page de fraîcheur faux** : l'écran affiche « données gelées 11/07/2026 » (`ProspectionSolaire.tsx:28`, constante `SOURCES_PIED`) alors que la base sert `parcel_solar.source_millesime = « PVGIS v5_3 · SARAH3 · relevé 2026-08-23 »` (SQL : `select max(updated_at)::date, max(source_millesime) from parcel_solar`). La donnée servie est plus fraîche que l'étiquette — l'étiquette ment.
2. **Solaire — export CSV de démarchage jamais branché à l'écran** : l'endpoint existe (`src/labuse/api/modules.py:803-830`, `fmt=csv` avec mentions Sourcé/Estimé) et le helper front aussi (`frontend/src/lib/api.ts:802-803` `prospectionSolaireCsvUrl`), mais **aucun composant ne le consomme** (grep : 0 usage hors api.ts). Le registre promet « export CSV de démarchage » (`registry.ts:99-102`).
3. **Densifier — colonne Surélévation morte** : le batch sert `false AS surelevable, NULL::int AS niveaux_sur` en dur (`src/labuse/renouvellement.py:219-220`) pour les 67 260 parcelles du segment ; le tableau affiche la colonne (`Renouvellement.tsx:253-255`) qui ne dira jamais rien. Dette EXPORTS-1 assumée en commentaire (« pas de signal plutôt qu'un signal faux ») — le signal vivant (`faisabilite/potentiel.surelevation`) n'est pas rebranché.

### 🟡 Dettes, vestiges, perf
- **Payloads lourds mesurés** : `POST /modules/programme` = 959 Ko pour une commune (0,81 s local) ; `GET /modules/promesses` = 283 Ko (Saint-Denis) ; fiche parcelle 66–84 Ko.
- **Appels froids lents** : fiche soleil 4,2 s à froid (analyse LiDAR à la demande, cache `toiture_lidar` = 24 lignes seulement) ; scoreur 2,8 s au 1er appel ; patrimoine grosse PM (4 183 parcelles) 3,6 s / 101 Ko.
- **Endpoints/code morts** : `/modules/courriers` legacy non appelé par M09 (`modules.py:1241-1282`) ; `/outils/etude-zone/export.pdf` sans bouton (`app.py:4503`, retrait RECETTE-2 C1) ; PDF baromètre retiré (`moteurs.py:588-591`) ; emplois MOBPRO abandonné, code conservé (`zone.py:200-219`, table `mobpro_commune` = 0 ligne) ; table `taxe_amenagement_taux` définie, 0 ligne, jamais lue.
- **Héritage** : `score_e` (285 781 lignes, moteur prix legacy) encore lu par le scoreur (`scoreur.py:131-136`, try/except muet).
- **Hypothèses invisibles à l'écran** (valeurs en dur, utilisateur ne les voit pas) : seuils PPR 2 %/50 % et recouvrement 10 % (`config/cascade_rules.yaml:147-154`) ; barème sévérité→score risque 70/50/30 + bonus +10 particulier (`modules.py:1290,1323-1325`) ; facteurs densifier 0,5 pente / 0,85 ravine / 0,90 mvt (`config/renouvellement.yaml:63-66`) ; coef occupation 0,45, rendement 0,80, densité 30 lgt/ha/niveau (`faisabilite/engine.py:32-37`) ; fenêtre 5 ans secteur (`bilan.py:109`) ; maturité cohorte vélocité 12 mois (`modules.py:1040`).
- **Statut Sourcé/Estimé non affiché** dans Comparer (aucun badge sur les ~20 lignes, `ComparePanel.tsx`) et dans Étudier un bien (implicite hors bloc secteur) ; la fourchette logements de Comparer n'affiche que la borne haute (`app.py:5501-5503`).
- **Renvois attendus absents** : Scan patrimoine → Courrier (aucun `setModule('courriers')` dans `ScanPatrimoine.tsx` — le flux « sourcer puis approcher » s'interrompt) ; Solaire → Courrier ; Densifier → Faisabilité ; Étudier un bien → Faisabilité/Assemblage ; Comparer et Remonter le temps sans pré-remplissage depuis les autres outils.
- **Fraîcheur non dite** : `parcelle_personne_morale.millesime` existe et n'est jamais lu ni affiché par Scan patrimoine ; le nom du run servi n'est affiché nulle part (libellé « Analyse LABUSE » seul).
- **DPE quasi vide en base** : `dpe_records` = 17 lignes (source non ingérée) — toute lecture DPE serait du vide.
- `basemaps.ts:24` commentaire obsolète (« mosaïque = 2022 » pour une couche jamais servie).
- **mon-secteur** : `adresse: null` sur les 3 parcelles testées (`parcel_adresse` couvre 257 340/431 663 parcelles).

### DOUTE (non tranchables en local)
- **Courrier — envoi réel** : `courrier_provider = "stub"` en local (`GET /courrier/statut` → `disponible: false`) ; le bouton « Demander l'envoi » est masqué en stub. L'état prod n'est pas vérifiable d'ici.
- **Risques — doublon d'aléa** : sur `97415000AC0024`, « mouvement_terrain moyen » apparaît 2 fois dans la cascade ; l'arbitrage (`risques_arbitrage.py:94`) garde un niveau max par type — à confirmer sur écran réel.
- **Étude de zone — deux chemins « revenu »** : fiche (strate secteur) vs tiroir Autour (`population_zone()` centroïde) peuvent diverger sur un carreau frontière (`app.py:4340-4341` promet une source unique, l'implémentation en garde deux).
- **Scoreur — flag `with_constat`** non documenté dans le schéma d'API (`scoreur.py:162-166`).

---

# PARTIE A — LES 15 FICHES

> Chaque fiche condense A1→A11. A8 = temps serveur locaux mesurés le 06/09 (3 parcelles fixes, table complète en annexe). A9 = `usage_events` 30 j **sur la base locale** (usage Vic, pas la prod). Les fiches détaillées longues (agents d'audit) restent la preuve de travail ; tout constat cité ici porte son `fichier:ligne`.

## 1. Étudier un bien (`scoreur-adresse` O2 · alias `calculette-fonciere` M23, `mon-secteur` S1)

**A1.** Front `EtudierBien.tsx:25-264` + `MonSecteur.tsx:44-120` (bloc secteur embarqué). Back : `POST /scoreur-adresse` (`api/scoreur.py:96-167`), `GET /outils/mon-secteur` (`api/mon_secteur.py:61-150`). Moteurs : `faisabilite/bilan.py` (`compute_bilan_servi`, `sector_price`, `resolve_prix_sortie_servi`), `marche_commune.prix_terrain_nu_zone`, `geocode.geocode_ban`.
**A2.** IDU ✓ (`scoreur.py:106-109`), adresse BAN ✓ (`scoreur.py:111-115`), clic carte ✓ (`EtudierBien.tsx:46`). Réf courte / SIREN / nom / dessin : ABSENT. Pré-remplissage fiche parcelle ✓ (`calcPrefill`, `EtudierBien.tsx:26-54`). État vide : formulaire neutre sans autofocus.
**A3.** `parcels`, `parcel_p_score_v2` (run servi), `score_e` (legacy), DVF via `sector_price` (rayon 500→1500 m, n≥8, 5 ans), `pige_biens/faits` (annonces), `parcel_adresse`. Statuts : n ventes/rayon/« extrêmes exclus » affichés au bloc secteur ; pas de badge Sourcé/Estimé par champ ailleurs.
**A4.** Aucun calcul métier au front (max(0,·) et écart = présentation, `EtudierBien.tsx:79-80`). Hypothèses : rayons/n min/trim affichés ; fenêtre 5 ans (`bilan.py:109`), bornes 1 000–12 000 €/m² (`bilan.py:138-148`), coef rendement — invisibles.
**A5.** Secteur (prix, annonces), en-tête (tier, surface), « ce que porte la parcelle » (SHAB, terrain, alerte cohérence résiduel), repères marché, analyse d'opération (charge calibrée / vos hypothèses), porte « fiche complète ». Jamais rendus : `mult_base`, `contrib_z/d`, `bilan.steps` et `bilan.hypotheses` (réservés PDF), `type_prix` secteur.
**A6.** Non lus et pertinents : `parcel_terrain.pente_moy_deg`/`flag_terrassement_lourd` (contrainte coût), `parcel_au_statut` (motif AU), `dvf_mutations_parcelle` (historique ventes de LA parcelle — seules les médianes sont servies), `parcel_flags`.
**A7.** Sort vers fiche complète et vers Risques (si alerte, `EtudierBien.tsx:152-153`) ; reçoit fiche/Copilote. Absents : renvoi Faisabilité, Assemblage. Fusion sans doublon (3 clés → 1 composant).
**A8.** scoreur : 2,83 s (froid) / 0,14 / 0,05 s — 200 rendu ×3. mon-secteur : 0,73 / 0,45 / 0,16 s — rendu ×3 (mais `adresse:null` ×3).
**A9.** 28 (scoreur-adresse) + 11 (mon-secteur) ouvertures/30 j (base locale).
**A10.** `score_e` legacy try/except muet (`scoreur.py:131-136`) 🟡 ; `with_constat` non documenté DOUTE ; le reste OK (choix design tracés).
**A11.** Fait bien : chaîne complète run-scopée, secteur honnête sous seuil (n<5). Ne fait pas : badge Sourcé/Estimé systématique, renvois vers Faisabilité/Assemblage. Cassé : rien.

## 2. Faisabilité (`programme` M22)

**A1.** Front `M22Programme.tsx` (2 modes : par critères / par parcelle) + `fiche/constructibilite.tsx:321-446` (`FaisabiliteTab` PARTAGÉ avec la fiche — même composant, zéro doublon de calcul). Back : `POST /modules/programme` (`modules.py:1720`), `GET /modules/faisabilite/{idu}` (`modules.py:1431`), `POST /modules/faisabilite/{idu}/charge` (`modules.py:1527`), `GET …/explain` (`modules.py:1657`). Moteurs : `faisabilite/engine.py` (`estimate_capacity`), `db.py` (`parcel_faisabilite`), `plu_rules.resolve_zone`, `bilan.py`, `residuel.py`.
**A2.** IDU/adresse/réf courte/clic carte ✓ (omnibox `ParcelInput.tsx:79-103`). Mode critères : formulaire (bâtiments, R+N, unités, m²/unité, circulations %, destination R151-28, commune). Pré-remplissage : Copilote (`m22Prefill`) ✓, fiche (`parcelPrefill`) ✓ ; Radar ABSENT.
**A3.** `parcels`, `parcel_residuel` (SDP), `parcel_zone_plu`, `parcel_p_score_v2` + `dryrun_parcel_evaluations` (run `runs.current()`, `modules.py:1753`), `spatial_layers` (contraintes), DVF via `marche_dvf`, QPV, `config/rtaa_dom.yaml`. Statuts affichés : steps tracés avec `prov` sourcée/estimée/dérivée (badge `StepProv`), capacité badgée « estimée » si zone non calibrée.
**A4.** Aucun calcul métier au front (tri de présentation seul). Hypothèses : circulations % éditable ✓ ; étage 3,0 m visible dans steps ; coef occupation 0,45, rendement 0,80, densité 30 lgt/ha/niveau, recul défaut 3 m (`engine.py:31-39`) — invisibles ; seuils mixité 1500 m²/20 lgt/6000 m² tracés au bilan.
**A5.** Liste paginée 200 (mode critères) + récap épinglé ; capacité + 11 steps + calculette charge/prix max (hypothèses SAISIES, jamais estimées) ; portes Calculette/Assemblage. Jamais rendus en mode critères : `taux_emprise_pct`, `sous_densite`, `pct_potentiel` (en base `parcel_residuel`).
**A6.** `parcel_residuel.taux_emprise_pct`, `.sous_densite` — densité réelle du candidat — Sourcé ; `parcel_terrain.pente/flag_terrassement` — coût — Sourcé ; `parcel_viabilisation` détaillée (l'écran n'a que le verdict).
**A7.** Reçoit fiche + Copilote ; sort vers Calculette et Assemblage (`constructibilite.tsx:718-723`). Absent : Radar→M22. Zone à cheval servie avec parts (ZONE-1) ; conflit centroïde/dominante → SDP non servie (prudent, `db.py:1806-1814`).
**A8.** sens1 : 0,20 / 0,08 / 0,02 s. charge : 0,18 s (calculable Saint-Denis) / « capacite_non_resolue » ×2 (Acu, RNU — refus propre, pas un faux chiffre). programme Saint-Denis : 0,81 s **mais 959 Ko** 🟡.
**A9.** 12 ouvertures/30 j.
**A10.** Payload programme 959 Ko 🟡 ; hypothèses implicites listées ci-dessus 🟡 ; délaissé <50 m² protégé OK ; le reste OK.
**A11.** Fait bien : chaîne tracée step par step, run-scopé, hypothèses économiques jamais inventées. Ne fait pas : surfacer emprise/sous-densité en mode critères. Cassé : rien (payload à surveiller).

## 3. Taxe d'aménagement (`taxe-amenagement` K3)

**A1.** Front `TaxeAmenagement.tsx:59-317`. Back : `GET /outils/taxe-amenagement/config` (`app.py:2539`), `/prefill` (`app.py:2549`), `/outils/taxe-amenagement` calcul (`app.py:2578`). Moteur `src/labuse/taxe_amenagement.py:29-123`, barème `config/taxe_amenagement.yaml` (millésime 2026, relevé 28/08/2026, source service-public A15416 citée à l'écran).
**A2.** IDU/adresse/réf courte/clic carte ✓ (omnibox). Prefill : surface terrain, SDP gabarit (`parcel_residuel.sdp_residuelle_m2`, éditable), zone PLU, flag bâti (`app.py:2550-2575`). État vide : consigne explicite.
**A3.** `parcels`, `parcel_zone_plu`, `parcel_residuel` + YAML. **Taux communal : AUCUNE source — saisie obligatoire, jamais de défaut** (`yaml:51`, message écran). Taux départemental : plafond légal 2,5 % pré-rempli étiqueté « à confirmer » (`part_departementale_confirmee_974: false`).
**A4.** 100 % backend (formule CGI 1635 quater : 892 €/m² hors IdF, abattement 50 %/100 m², exo <5 m², forfaits piscine 251 €/m², parking 2 928 €/pl — chaque ligne du détail affiche son calcul). Si taux communal absent → total NULL, jamais inventé (`taxe_amenagement.py:100-103`).
**A5.** Détail ligne à ligne + assiette + parts + total. Pas d'export ni de sauvegarde. Rien de calculé non rendu.
**A6.** `taxe_amenagement_taux` (table des taux par commune) : **définie, 0 ligne, jamais lue** — un jour peuplée elle éviterait la saisie ; `parcel_residuel.cause` (motif SDP non calculable) non affiché.
**A7.** Entrées : menu, Radar, bloc Marché de la fiche (`fiche/marche.tsx:91-93`). **Aucun renvoi sortant** (ni PLU, ni Faisabilité) — outil isolé ; la taxe n'apparaît nulle part ailleurs (un fait, une section ✓).
**A8.** prefill : 0,03 / 0,02 / 0,01 s. config : 0,01 s. calcul : 0,01 s. Rendu ×3 (SDP 38 / 0 / NULL gérés proprement).
**A9.** 26 ouvertures/30 j.
**A10.** Tout OK par design (aucun taux inventé — vérifié). Millésime à basculer chaque 01/01 🟡 (procédure non automatisée).
**A11.** Fait bien : formule publique traçable, refus de calculer sans taux. Ne fait pas : servir les taux communaux (table prête, vide). Cassé : rien.

## 4. Pièges et risques (`risques` M10 + O5)

**A1.** Front `ModulePanel.tsx:1331-1507` (M10 lot + hub) + `blocB.tsx:34-100` (O5 parcelle) + `fiche/risques.tsx`. Back : `POST /modules/duediligence` (`modules.py:1329-1363`), `GET /servitudes-invisibles/{idu}` (`servitudes.py:109-150`). Moteurs : cascade `cascade/layers/etage1.py`, arbitrage `api/risques_arbitrage.py:71-109`, mapping onglets `served_cascade.py:155`.
**A2.** Les DEUX entrées annoncées existent (une parcelle / un lot au crible, `ModulePanel.tsx:1504`). IDU 14 + section-numéro (`AB 9`) ✓, clic carte ✓ (O5). Porte depuis l'onglet Risques de la fiche ✓. État vide : consignes.
**A3.** `dryrun_cascade_results` (run_label = q_v11_m137) + `spatial_layers` (50 kinds : ppr, georisque_alea, sol_pollue, cavite, icpe, mvt, trait_de_cote, anc, znieff, sup…) + `parcelle_personne_morale` + `parcel_p_score_v2`. Le « non couvert » est affiché (PEB, SUP hors GPU, canalisations — `servitudes.py:74-80`, `ModulePanel.tsx:1408-1416`) : la promesse du registre (pas d'exhaustivité) est tenue.
**A4.** Score risque 0-100 calculé back (`modules.py:1293-1326` : HARD_EXCLUDE→100, sinon max sévérité 70/50/30, +10 particulier plafonné). **Seuils invisibles** : PPR rouge 2 %/50 %, recouvrement 10 % (`cascade_rules.yaml:147-154`), distances 50 m cavité/icpe/mvt (`yaml:335,350`) 🟡. Aucun calcul front.
**A5.** Lot : compteur, non-couvert, chips (tier, score, propriétaire, checklist ≤5) + **pont Courrier** (`ModulePanel.tsx:1468-1471`). Parcelle : servitudes datées + méthode/limites. PDF retiré (choix). Poids internes non montrés.
**A6.** `catnat_arretes` (426 arrêtés) — lus par la fiche, PAS par cet outil ; `bodacc_procedures` (674) — signal faiblesse propriétaire non exploité ici ; `parcel_terrain.pente_max_deg`.
**A7.** Fiche→outil ✓ (porte), outil→Courrier ✓. Un fait une section ✓ (cascade lue une fois, arbitrée).
**A8.** duediligence : 1,00 / 0,10 / 0,23 s. servitudes : 0,07 / 0,13 / 0,08 s. Rendu ×3 (5 / 1 / 1 servitudes — ZNIEFF seul à St-Philippe).
**A9.** 7 ouvertures/30 j.
**A10.** Seuils PPR non exposés 🟡 ; doublon aléa « mouvement_terrain moyen ×2 » constaté sur AC0024 DOUTE (arbitrage censé dédupliquer) ; masquage âge dirigeant sur particulier corrigé OK.
**A11.** Fait bien : deux entrées réelles, non-couvert avoué, run épinglé. Ne fait pas : montrer ses seuils. Cassé : rien de confirmé (un doublon d'aléa à vérifier à l'écran).

## 5. PLU (`plu` O13 + O11 + M15)

**A1.** Hub `Plu.tsx:1-58` → `PluAnnuaire.tsx` (annuaire/recherche/pack GPU), `ProcedureChangement.tsx` + `VerifProcedure.tsx` (procédures), `moteurs.tsx:30-123` (simulateur AU→U M15). Back : `/modules/plu-annuaire/communes` (`app.py:1972`), `/search` (`app.py:2037`), `/pack/{insee}` (`app.py:1991`), `/modules/verif-procedure/{idu}` (`app.py:1895`), `/moteurs/simulplu*` (`moteurs.py:46-127`). Moteurs : `plu_reglement.py` (`resolve_reglement`, `regles_valeurs`), `plu/destinations.py` (23 sous-destinations R151-28, seuil CDAC 1 000 m² cité), `veille_plu.py` (radar procédures, point unique).
**A2.** IDU/adresse/réf courte ✓ (omnibox) ; commune (CommuneScope) et zone ✓ ; prefill fiche→annuaire (`setPluPrefill`, `Fiche.tsx:561`) et fiche→vérif procédure ✓. État vide honnête (RNU/non ingérée dits).
**A3.** `plu_reglement_extrait` (3 258 extraits, 21/24 communes servies), `spatial_layers` plu_gpu_zone (5 845 zones, 23/24), `parcel_zone_plu` (427 419), `veille_plu.yaml`/`plu_millesimes.yaml` (24), cascade zonage au run. Millésime du PLU (date mairie) affiché ; confiance SOURCE/DEDUIT/ABSENT affichée sur les procédures.
**A4.** `resolve_reglement` : YAML calibré → article+page+URL GPU profonde ; sinon repli générique EXPLICITE (jamais inventé). Simulateur AU→U : ratio = médiane SDP/surface des parcelles U sourcées, totaux stables hors pagination (`moteurs.py:76-105`), ratio servi par le back (plus de re-division front). Aucun calcul front.
**A5.** Annuaire (24 communes, badges), recherche verbatim (article + PDF cliquable + mention « verbatim opposable, non conseil juridique »), radar procédures, simulation paginée. Valeurs de règles avec état `chiffre|texte|absent|a_verifier`. `veille_plu.raisonnement` (DEDUIT) lu back, non affiché — seul champ retenu.
**A6.** Zones A/N non indexées article par article (repli documenté `plu_reglement.py:145-147`) ; `sudocuh_procedures` (24) réconciliées via YAML curé, la table brute n'est plus le point de vérité.
**A7.** Fiche↔annuaire↔procédures↔simulation tous câblés (4 ponts vérifiés). Un fait une section ✓ (règles = résolution unique ; procédures = radar unique).
**A8.** verif-procedure : 0,28 / 0,07 / 0,04 s. annuaire communes : 0,18 s (24 communes, 21 servables). search « hauteur » 97411 : rendu. simulplu/zones : 0,39 s. Rendu ×3 — St-Philippe : « RNU, élaboration prescrite 2002, dormante » (dit, daté).
**A9.** 33 ouvertures/30 j.
**A10.** Couverture réelle mesurée : corpus 21/24, GPU 23/24, cascade 24/24 ; 2 communes (St-Leu, St-André) servies par correction mairie — affiché. Saint-Philippe RNU 24 ans nommé. RETOURS-15 U8 (PLU en vigueur pendant révision) en place. RAS.
**A11.** Fait bien : verbatim sourcé, procédures avec confiance explicite, couverture avouée. Ne fait pas : zones A/N article par article. Cassé : rien.

## 6. Comparer des parcelles (`comparer` A8)

**A1.** Front `compare/ComparePanel.tsx` (module :67-142, overlay :145-244). Back : `GET /compare?idus=` (`app.py:5711-5747`), `_compare_row` (`app.py:5472-5540`) qui appelle `fiche_payload()` + `_q_v2_fiche()` + `build_marche_commune()` — les MÊMES moteurs que la fiche (cohérence par construction, gardée par `test_compare_row_source_servie`).
**A2.** Ajout par clic carte (mode picking, `MapView.tsx:1320-1324`), depuis la fiche (porte « Comparer », `fiche/marche.tsx:112-114`), bouton « + parcelle courante ». Max 3. **Aucune saisie IDU/adresse directe, aucun pré-remplissage depuis un autre outil.** État vide : consigne.
**A3.** ~20 lignes servies (surface, zone, constructible, SDP max/résiduelle, emprise, charge foncière, terrain nu zone, prix bâti secteur, bâti %, gabarit, logements, accès/réseaux, ANC, propriétaire, contraintes, verdict/fraction/raison) — run servi partout. **Aucun badge Sourcé/Estimé** (libellés contextuels seuls) 🟡.
**A4.** Front : `bestIdx()` (surlignage du meilleur) et rien d'autre. Logements = borne HAUTE seule (`app.py:5501-5503`) — la fourchette est perdue 🟡.
**A5.** Tableau plein écran, clic IDU→fiche, ✕ retrait, TTL sélection 15 min documenté. **Aucun export, aucune synthèse agrégée.**
**A6.** Comparables utiles non lus : `parcel_terrain.pente`, `parcel_solar` (exposition), `parcel_equipements`, détail viabilisation (verdict unique servi).
**A7.** Sort vers fiche (clic IDU) ; reçoit fiche. Ni deep-link ni Copilote. Un fait une section ✓ (mêmes moteurs que la fiche, pas de recalcul).
**A8.** compare 3 IDU : 1,93 s — rendu (3 parcelles).
**A9.** **3 ouvertures/30 j** — l'outil le moins utilisé.
**A10.** Statut fiabilité invisible DOUTE ; export ABSENT ; pré-remplissage inter-outils ABSENT ; borne basse logements ABSENTE — causes factuelles plausibles du non-usage.
**A11.** Fait bien : cohérence fiche/comparateur par moteurs partagés. Ne fait pas : export, fourchettes, badges de fiabilité. Cassé : rien.

## 7. Assemblage (`assemblage` M16)

**A1.** Front `outils/moteurs.tsx:127-325` (M16). Back : `POST /moteurs/assemblage` (`moteurs.py:154-262`). Moteur `src/labuse/assemblage.py` (`aggregate_assiette:119`, contiguïté ST_DWithin 0,5 m `:18`, DFS composantes).
**A2.** **Clic carte uniquement** (`MapView.tsx:1318-1320`, toggle sélection, cap 30 configurable) + porte fiche (`parcelPrefill`, `moteurs.tsx:132-135`). Ni saisie IDU, ni adresse, ni dessin. État vide : « aucune parcelle sélectionnée ».
**A3.** `parcels`, `dryrun_parcel_evaluations` + `parcel_p_score_v2` (run servi, `moteurs.py:177`), `parcelle_personne_morale`, agrégats via `fiche_payload()`. SDP affichée « ESTIMÉE par analogie DVF » (titre explicite `moteurs.tsx:237-240`).
**A4.** Ratio gain calculé back (KO-15 soldé : le front ne re-divise plus, `moteurs.tsx:148-152`). Contiguïté 0,5 m ; « score assemblage » calculé et **jamais affiché** (doctrine faits-pas-notes, `moteurs.py:231-235`). Charge négative → « résultat d'un scénario », bloc rouge.
**A5.** Faits (contiguïté, propriétaires PM nommés / particuliers comptés jamais nommés), KPI assiette, détail par parcelle, **pont Courrier** (`moteurs.tsx:313-317`), note indivision honnête. Pas d'export ni de lien Projets.
**A6.** `dvf_mutations` des voisines (dynamique du voisinage), `sitadel_permits` voisins, `pc_caducs` — rien de tout cela n'est lu.
**A7.** Reçoit fiche ; sort vers Courrier. Absents : Projets, Scan patrimoine (propriétaire d'une voisine).
**A8.** 2 parcelles : 0,25 s — rendu (contigu:false correct : AB0009 et AB0011 ne se touchent pas).
**A9.** **5 ouvertures/30 j.**
**A10.** Tout tracé OK ; la cause plausible du faible usage est factuelle : sélection au clic uniquement (pas de saisie), donc geste coûteux 🟡.
**A11.** Fait bien : agrégation par le moteur de la fiche, privacy correcte, pont Courrier. Ne fait pas : entrée clavier, suggestion de voisines. Cassé : rien.

## 8. Scan patrimoine (`patrimoine` M02 + `veille-promoteurs` S3)

**A1.** Front `ScanPatrimoine.tsx` (2 temps : recherche → encart + 2 onglets) + `VeillePromoteurs.tsx` (construit) + M02 `ModulePanel.tsx:160`. Back : `/modules/patrimoine/search` (`modules.py:197-226`), `/modules/patrimoine` (`modules.py:232-394`, + `fmt=csv` :351), `/outils/veille-promoteurs*` (`veille_promoteurs.py:160-275`).
**A2.** Nom d'entreprise ✓, SIREN/SIRET ✓, IDU ✓ (via propriétaire de la fiche), **repli adresse BAN** ✓, clic carte (pin propriétaire) ✓ — 4 exemples cliquables à l'état vide. Prefill : fiche (bloc PM, `Fiche.tsx:1508`), Communes (acquéreur), Radar.
**A3.** `parcelle_personne_morale` (82 701 liens), `parcels`, `parcel_p_score_v2`+`dryrun_parcel_evaluations` (run servi), `parcel_residuel`, `v_foncier_sous_pression` (BODACC), `pm_dirigeants` (27 146 — lu en simple EXISTS), `sitadel_permits` (millésime affiché), `programmes`. **`parcelle_personne_morale.millesime` jamais lu — la fraîcheur MAJIC n'est pas dite** 🟡.
**A4.** Comptes SQL purs ; valorisation indicative = surface × prix zone (étiquetée, silencieuse si pas de marché) ; assiette contiguë union-find ≤250 m ; regroupement opérations SIREN+contiguë+24 mois (constantes `veille_promoteurs.py:34-35`, dites à l'écran).
**A5.** Encart (nom, SIREN cliquable Pappers), 3 chiffres (parcelles/actionnables/SDP), signaux BODACC+INPI, liste paginée 200 avec tiers, **export CSV** (`modPatrimoineCsvUrl`, servi ET branché — contrairement au solaire), frise opérations. `valorisation_nu_eur` retournée jamais affichée.
**A6.** BODACC complet (12 605 sondages — seule la vue filtrée est lue), dirigeants INPI (noms/dates jamais servis), DVF des acquisitions du même SIREN, `rnic_coproprotes` (2 220), groupes MAJIC (autres SIREN du même groupe non liés).
**A7.** Fiche↔Scan bidirectionnel ✓ ; Communes→Scan ✓ ; Veille↔Scan ✓. **Scan → Courrier ABSENT** (`ScanPatrimoine.tsx` : aucun setModule('courriers')) — rupture du flux « sourcer → approcher » 🟡.
**A8.** search : 0,16 s. patrimoine SIREN 310863592 (4 183 parcelles) : 3,64 s / 101 Ko 🟡. veille-promoteurs : 0,15 s (83 opérations).
**A9.** 19 (+10 veille-promoteurs) ouvertures/30 j.
**A10.** Millésime MAJIC absent 🟡 ; pont Courrier absent 🟡 ; run jamais nommé à l'écran 🟡 ; « N actionnables » dépend des écartées du compte (cloisonnement voulu) OK.
**A11.** Fait bien : résolution multi-entrées robuste, signaux BODACC/INPI, CSV réel. Ne fait pas : dire la fraîcheur MAJIC, enchaîner vers Courrier. Cassé : rien.

## 9. Courrier propriétaire (`courriers` M09)

**A1.** Front `ModulePanel.tsx:1131-1326` (3 étapes). Back `api/courrier.py` : `POST /courrier/demande` (:105), `GET /courrier/demandes` (:156), `POST /courrier/pdf` (:248), `GET /courrier/statut` (:39) + admin. Moteur `src/labuse/courrier.py` (idempotence GB-013 : advisory lock + md5 + fenêtre 120 s, `courrier.py:176-198`).
**A2.** IDU/adresse via ParcelInput ✓ ; prefills : fiche (mono), Assemblage + Risques (`courrierPrefillIdus`), CRM piste (`courrierPrefillPiste`). État vide : 0 destinataire, bouton désactivé.
**A3.** `parcels` (commune, surface) seul. **L'adresse du propriétaire n'est JAMAIS servie au client** (design : adressage générique « À l'occupant », `courrier.py:335`) — l'adresse réelle est l'affaire de l'admin au dépôt.
**A4.** 4 gabarits front + substitution `{parcelle}/{commune}/{surface}` — pas d'IA, pas de calcul métier. Tarif (2,69 € × 1,5) jamais affiché client (gardé au /statut).
**A5.** Récap, PDF de relecture (fpdf), demande enregistrée + suivi statuts (demande→déposé→envoyé→répondu), mail admin, cloche. Le client ne voit PAS « imprimé/posté » (choix Vic documenté).
**A6.** `parcel_adresse.ban_voie` (257 340) — utilisée au dépôt, pas dans l'outil ; `parcelle_personne_morale` (PM vs PP au ciblage) ; `parcel_veille_succession` (7 129 — signal d'opportunité jamais exploité ici) ; BODACC.
**A7.** Reçoit Scan patrimoine (— en fait NON : le pont annoncé n'existe que depuis Risques, Assemblage, fiche, CRM ; voir fiche 8), ne renvoie nulle part (fin de chaîne).
**A8.** statut : 0,01 s (`disponible:false, provider:stub`). demandes : 0,01 s (43+ demandes en base locale). Aucun POST d'écriture appelé.
**A9.** 12 ouvertures/30 j.
**A10.** Provider stub → envoi réel non vérifiable d'ici DOUTE ; plafond/jour découvert seulement à l'erreur 422 🟡 ; endpoint legacy `/modules/courriers` mort (`modules.py:1241-1282`) 🟡 ; idempotence concurrente OK (vérifiée GB-013).
**A11.** Fait bien : demande robuste, privacy stricte, suivi statuts. Ne fait pas : dire si le service est actif avant le geste, être alimenté par Scan patrimoine. Cassé : rien (stub = état local).

## 10. Densifier l'existant (`renouvellement` MR1)

**A1.** Front `Renouvellement.tsx:43-286` (panneau + overlay tableau). Back : `GET /renouvellement/liste` (`app.py:4968-5015`), `GET /map/renouvellement.geojson` (`app.py:4928`), bloc fiche `_renouvellement_block` (`app.py:3924-3969`). Moteur `src/labuse/renouvellement.py` (build :276-335, config `config/renouvellement.yaml` : pondérations 47/29/24).
**A2.** Omnibox complète (adresse/IDU/réf courte/carte) pour « ma parcelle densifie-t-elle ? » ; liste triable (score/sdp/surface/rang), filtre commune. Pas de pré-remplissage contexte. État vide : top 5 + note datée (jamais blanc).
**A3.** `parcel_renouvellement` (67 260, **run_label = q_v11_m137 filtré partout** — vérifié), `parcels`, `parcel_p_score_v2`, `dryrun_parcel_evaluations`. Tier v2 servi 67 260/67 260 (zéro repli historique — vérifié SQL).
**A4.** Capacité NETTE : SDP × (1−PPR%) × 0,5 si pente>30 % × 0,85 ravine × 0,90 mvt (`renouvellement.py:233-238`) ; score = percent_rank 47/29/24, continu (top à 99,8, pas de plateau). Seuils 100 m² SDP / 600 m² surface / pente 30 % dits à l'écran ; **facteurs 0,5/0,85/0,90 invisibles** 🟡. Aucun calcul front.
**A5.** Tableau 9 colonnes paginé 200 (cap 400 affiché), infobulle « SDP brute — N % déduits », pas d'export (OUTILS-1 B7, testé). **🟠 colonne Surélévation morte** : `false AS surelevable, NULL::int` en dur (`renouvellement.py:219-220`) — cf. récap KO.
**A6.** `dpe_records` (17 lignes — vide de fait), année de construction (BDNB pas encore au 974), `parcel_vegetation` (431 663 — jamais lu), vacance.
**A7.** Sort vers fiche (clic ligne) ; **aucun pont vers Faisabilité** (une densifiable n'ouvre pas le calcul détaillé) 🟡. Bloc fiche = même source (pas de doublon).
**A8.** liste : 0,12 s Saint-Denis (7 242 total) / 0,15 s Saint-Paul (8 075) / 0,04 s **Saint-Philippe : 0** (RNU — segment U/AU vide par construction, l'écran affiche liste vide).
**A9.** 7 ouvertures/30 j.
**A10.** Surélévation 🟠 (récap) ; facteurs invisibles 🟡 ; DPE inutilisable 🟡 ; run-scoping exemplaire OK.
**A11.** Fait bien : capacité nette déduite et affichée, score déscaturé, run épinglé partout. Ne fait pas : surélévation (colonne morte), lien Faisabilité. Cassé : la surélévation, en connaissance de cause.

## 11. Permis (`permis` M03 + `promesses` M04)

**A1.** Front `ModulePanel.tsx:438-841` + `lib/permisEtats.ts` (source unique états/couleurs). Back : `GET /modules/permis` (`modules.py:428-532`), `/modules/permis/{id}` (:548), `/modules/parcelle-permis` (:593), `/modules/promesses` (:634). Moteurs registre `compte_permis_commune`/`permis_point_mort` (`registre/moteurs/commune.py:261-286`).
**A2.** Adresse/rue ✓, clic carte ✓, commune ✓, nature PC/DP/PA/PD ✓, fenêtres 12-240 mois ✓, IDU→permis rattachés ✓, n° Sitadel ✓, filtre dormants (clé `promesses` pré-active, 36 mois = caducité PC). État vide : message.
**A3.** `sitadel_permits` (60 696, **93,1 % géolocalisés**, profondeur 2013→31/07/2026 affichée), `m10_permit_delais`, `via_permits_geo` (signal viabilisation fiche), cascade run-scopée pour l'exclusion bâti des dormants. **Rattachement par géométrie d'époque** : `cadastre_historique` (6 495 ; 7 325 orphelins posés en geom_approx badgés « approx. (adresse) » — RETOURS-14).
**A4.** Partition récent/dormant/achevé/autre EXACTE (somme = total, testée `test_retours17_permis.py:57-68`). Définitions affichées (24 mois récent, 36 dormant). Front : seul le badge « N ans » des dormants est calculé en JS (année civile — dérive d'un jour au 31/12, négligeable) DOUTE mineur.
**A5.** Liste paginée 200 + compteur vrai, carte points cliquables, fiche permis complète (porteur+SIREN, destination, délais, source), recherche par parcelle (rayons 100/200 m).
**A6.** `raw.surf_hab` en liste radar (servi au point mort seul) ; lieudit ; famille. `p_model_permits` (59 264) : enrichissement jamais lu par l'outil.
**A7.** Fiche (bloc Autour) → drawer permis ✓ ; fiche commune → permis ✓. Permis → Scan patrimoine : indirect seulement (pas de bouton « voir ce SIREN »).
**A8.** permis : 0,04 s / 128 Ko (Saint-Denis 24 m). dormants : 0,12 s / **283 Ko** 🟡 / 0,09 / 0,01 s. parcelle-permis AB0009 : 0,02 s (c200=9). Rendu ×3 communes.
**A9.** 72 ouvertures/30 j — 2e outil le plus utilisé.
**A10.** Payloads dormants 🟡 ; états centralisés OK ; millésime servi en direct OK ; état « Autorisé » masqué en liste (constant au 974) OK documenté.
**A11.** Fait bien : partition exacte, rattachement d'époque, définitions affichées. Ne fait pas : pont direct vers le porteur (Scan). Cassé : rien.

## 12. Communes (`communes` O6 + M05 + O9 + MU1 + `barometre` M18)

**A1.** Front `Communes.tsx` (3 portes : Comparaison / Évolution / Acquisitions), `blocB.tsx` (O6Comparateur), `moteurs.tsx:518+` (M18). Back : `/communes` (`app.py:1869`), `/communes/{c}/contexte` (:1983), `/communes/{c}/acquisitions-pm` (:2197), `/comparateur-communes` (`comparateur.py:112`), `/moteurs/barometre[?insee=]` (`moteurs.py:573`), `/moteurs/marche/{c}` (:580), `/modules/velocite` (`modules.py:1035`), `/pipeline-rarete` (`rarete.py:98`).
**A2.** Sélection par tableau (Comparaison), sélecteur (Acquisitions), île entière ou commune (Évolution). Aucune entrée parcelle — normal. Pas de prefill.
**A3.** Comparaison : `parcel_p_score_v2` (stock, run servi), `m10_permit_delais` (vélocité p50), `sitadel_permits` (5 ans), SRU (DHUP), ZAN (`commune_conso_enaf`, 24 lignes), DVF (ancien n≥100 / neuf VEFA / terrain nu 23/24 communes — St-Philippe sans terrain nu, affiché « — »). Évolution : 8 trimestres révolus, nature='Vente' stricte, bornes 100-12 000 €/m². Acquisitions : `pm_proprietaires_millesimes` (461 570) — changements de SIREN depuis 2022, honnêteté « constat DGFiP, pas une vente » documentée.
**A4.** Tous calculs back via moteurs registre nommés (un fait = une requête, vérifié : fiche commune et outil lisent les MÊMES fonctions — `comparateur.raw_rows` en direct des deux côtés, RETOURS-12 O8). Fenêtre vélocité (recul 12 mois maturité) invisible 🟡.
**A5.** Tableau 24 communes triable + légende, série 8 trimestres (« — » jamais 0), acquisitions groupées par acquéreur avec **pont Scan patrimoine** ✓ et clic IDU→fiche ✓. **PDF baromètre retiré** (`moteurs.py:588-591`) — la donnée d'Évolution n'a plus d'export 🟡.
**A6.** `filosofi_carreaux_200m`, `commune_insee_logement` (24), `rpls_commune` (24) : lus par la FICHE commune, pas par les 3 portes de l'outil.
**A7.** Sort : fiche commune, fiche parcelle, Scan, Permis, Radar, Densifier. Duplication maîtrisée (source unique par indicateur).
**A8.** communes : 0,005 s. comparateur : 0,007 s. barometre : 0,17 (île) / 0,08 s (97411). acquisitions : 2,10 (froid St-Denis) / 0,38 / 0,10 s. contexte : 2,44 (froid) / 0,01 / 0,01 s (cache). Rendu ×3.
**A9.** 74 ouvertures/30 j — outil le plus utilisé.
**A10.** Terrain nu 23/24 (affiché « — ») OK ; ZAN étiqueté estimation OK ; PDF retiré 🟡 ; fenêtre vélocité invisible 🟡.
**A11.** Fait bien : source unique par indicateur, fenêtres nommées, jamais de zéro muet. Ne fait pas : export de l'Évolution. Cassé : rien.

## 13. Prospection solaire (`prospection-solaire` M26)

**A1.** Front `ProspectionSolaire.tsx` (2 modes : Piscines / Ensoleillement). Back : `/modules/prospection-solaire` (`modules.py:715-834`, `fmt=csv` :803), `/parcelle/{idu}` (:837), `/modules/prospection-piscines` (:909) + `/points` (:953) + `POST /pas-une-piscine` (:999). Moteurs : `ingestion/solaire.py` (PVGIS v5.3 SARAH3), `solaire_toiture.py` (LiDAR HD à la demande, seuil 0,70), `ingestion/ortho_equipements.py` (détection FLAIR).
**A2.** Ensoleillement : omnibox parcelle + prefill tuile Solaire de la fiche (`RadarView.tsx:173`) ✓. Piscines : drill communes + carte. Filtres réels (potentiel min, proba occupant, incertaines, tri).
**A3.** `parcel_solar` (431 663), `parcel_equipements` (piscines : 7 821 haute confiance ≥0,80 / 8 299 total — comptés en SQL), `piscine_corrections` (0), `p_model_bati` (emprise toit), `parcel_terrain` (pente RGE ALTI), run servi pour tier/étage0. **🟠 pied « données gelées 11/07/2026 » faux** (base : relevé 23/08) — cf. récap.
**A4.** Productible PVGIS (plein nord, 65°, maille ~400 m — dits à l'écran) ; kWc = toit × 0,2 et prod = kWc × productible **calculés au front** (`ProspectionSolaire.tsx:325-326`) — présentation d'une règle métier simple, hypothèse 0,2 kWc/m² non écrite à l'écran 🟡 ; toiture LiDAR : verdict sous seuil → « non déterminée » (honnête).
**A5.** Fiche soleil (8 KPI + profil 12 mois + rosace + photo), compteurs piscines honnêtes (« N affichées · P listées sur T détectées »), geste « pas une piscine » (retire partout), carte points. **🟠 export CSV jamais branché à l'écran** — cf. récap. Jamais rendus : `ghi_kwh_m2_an`, `score_solaire`, `pv_detecte/pv_surface` (PV existants détectés, en base, jamais servis).
**A6.** `parcel_equipements.pv_detecte/pv_surface_m2/pv_confiance` (déjà équipés = à exclure du démarchage) ; `dpe_records` (17 — vide) ; `toiture_lidar` (24 calculées seulement) ; raccordement (hors base).
**A7.** Fiche→Solaire ✓ (tuile), Communes→Solaire ✓. **Solaire→Courrier ABSENT** 🟡 (8 299 piscines détectées, aucun flux d'approche).
**A8.** fiche-soleil : 4,17 s (froid, LiDAR) / 1,34 / 0,76 s. piscines : 0,06 / 0,04 / 0,04 s (1 226 / 1 545 / 29). Rendu ×3.
**A9.** 22 ouvertures/30 j.
**A10.** Deux 🟠 (récap) ; calcul kWc au front 🟡 ; cache LiDAR quasi vide 🟡 ; jamais de faux « zéro piscine » OK.
**A11.** Fait bien : détection honnête (confiance, corrections), fiche soleil sourcée. Ne fait pas : exporter (bouton absent), dire le vrai millésime. Cassé : l'étiquette de gel et le CSV côté écran.

## 14. Étude de zone (`etude-zone` M27)

**A1.** Front `EtudeZone.tsx:42-399` + tiroir fiche `AutourZoneBlock.tsx:34-128` (MÊME moteur). Back : `POST /outils/etude-zone` (`app.py:4415-4472`), `GET /parcels/{idu}/zone` (:4333), `POST /outils/etude-zone/entreprises` (:4475), `GET /outils/etude-zone/naf*` (:4388-4400), export PDF mort (:4503). Moteur `src/labuse/zone.py` (`etude_de_zone:542-612`).
**A2.** Point (parcelle omnibox OU adresse) + temps 5/10/15 + voiture/à-pied ✓ ; **polygone dessiné** ✓ (seul outil avec dessin) ; NAF (recherche + familles) ; sous-destination R151-28 (porte chalandise) ; prefill Copilote ✓.
**A3.** `filosofi_carreaux_200m` (14 773 — revenus badgés sourcé/approché selon imputation), `sirene_etablissements` (158 515 — emplois en FOURCHETTE de tranches, jamais un point ; fraîcheur >24 mois alertée), DVF 12/36 mois, `pige_biens` (réserve « collecte partielle » affichée), `sitadel_permits`, `spatial_layers` (BPE 5 domaines, transport, PLU), `trafic_rn` (692), isochrone IGN + cache `zone_isochrone_cache` (TTL 30 j ; API KO → « indisponible », jamais un cercle inventé, `zone.py:103`).
**A4.** Tout back ; habitants/concurrent calculé back (`app.py:4464`). 3 états partout (servie / non couverte / erreur). Ventilation population au centroïde de carreau (technique, invisible — acceptable).
**A5.** 3 étapes, cartes (isochrone + bandes), stats, concurrents cliquables→fiche, toutes-entreprises plafonnées avec note. Export PDF : endpoint vivant, bouton retiré 🟡.
**A6.** `mobpro_commune` (0 — abandonné, code mort `zone.py:200-219`) ; BPE hors 5 domaines (volontaire) ; arrêts sans énumération de lignes.
**A7.** Tiroir fiche = même moteur ✓ (aucune duplication) ; deux chemins « revenu » fiche vs Autour DOUTE (récap).
**A8.** parcel-zone : 1,89 / 1,58 / 1,52 s (isochrone). etude-zone AB0009 : 1,04 s (cache), 24 Ko. Rendu ×3.
**A9.** 33 ouvertures/30 j.
**A10.** Code mort MOBPRO 🟡 ; PDF mort 🟡 ; badge imputation dépendant d'une colonne optionnelle DOUTE ; le reste exemplaire (3 états, fourchettes, réserves).
**A11.** Fait bien : la donnée dit son état (servie/non couverte/erreur), fourchettes plutôt que points. Ne fait pas : PDF, transports détaillés. Cassé : rien.

## 15. Remonter le temps (`temps` M08)

**A1.** Front `TimeMachine.tsx:49+` (comparateur SWIPE 2 cartes) + bandeau `ModulePanel.tsx:1001-1091` + `map/basemaps.ts` (frise). Back : `GET /parcels/{idu}/geojson` (`app.py:2232`), proxy tuiles `GET /map/tiles/ortho/{couche}/{z}/{x}/{y}` (`ortho_proxy.py:221-255`) → WMTS IGN Géoplateforme.
**A2.** IDU/adresse/clic carte ✓ + prefill fiche (bouton « 1950 ») ✓. État vide : « la parcelle d'abord ».
**A3.** 7 couches : 1950-1965, 2000-2005, 2006-2010, 2011-2015, 2016-2020, 2021-2023, « Actuelle · Ortho Express 2025 » — **chaque libellé = la couche IGN exacte** (`ortho_proxy.py:45-54` vs `basemaps.ts:60-79`) ; 1965-80/1980-95 exclues car métropole seule (vérifié GetTile, commentaire `basemaps.ts:54`), zones noires légendées. Conformité RETOURS-11F C6 maintenue : **aucun libellé d'année ne ment**.
**A4-A5.** Aucun calcul (outil purement visuel) ; « après » verrouillé sur aujourd'hui (testé `TempsMillesimes.test.tsx:47-61`). Pas d'export. Non rendus : dates exactes de prise de vue (plages seulement).
**A6.** L'« histoire de la parcelle » se limite à l'ortho : `dvf_mutations_parcelle` (ventes datées), `via_permits_geo`/`sitadel_permits` (permis datés), `cadastre_historique` (découpes) — rien de vectoriel n'accompagne la frise.
**A7.** Reçoit fiche/Copilote ; **ne renvoie vers rien** (ni Permis de la période, ni DVF de la période) 🟡.
**A8.** geojson : 0,008 / 0,006 / 0,010 s. Tuile 1950 z15 : 0,32 s (72 Ko). Tuile Express z19 : 0,13 s. Rendu.
**A9.** 8 ouvertures/30 j.
**A10.** `basemaps.ts:24` commentaire obsolète 🟡 ; aucun libellé mensonger (vérifié couche par couche) OK.
**A11.** Fait bien : libellés exacts, limites IGN avouées. Ne fait pas : croiser la frise avec permis/ventes datés. Cassé : rien.

---

# PARTIE B — MATRICE DONNÉES × OUTILS

> Volumes = `SELECT count(*)` réels du 06/09 (les `n_live_tup` de `pg_stat_user_tables` sont périmés sur ~15 tables — plusieurs « 0 » affichés sont en réalité peuplés ; toutes les tables marquées ici ont été recomptées). Lecteurs = parmi les 15 outils seulement ; « fiche » = lue par la fiche parcelle/commune mais par AUCUN des 15. ⚠ = donnée métier peuplée servie par aucun outil (réserve de puissance).

## Cadastre & parcellaire
| Table | Volume | Lecteurs |
|---|---|---|
| `parcels` | 431 663 | tous (15/15) |
| `parcel_adresse` | 257 340 | 1, 2, 6 (via fiche_payload) — utilisée au dépôt Courrier |
| `cadastre_historique` | 6 495 | 11 (rattachement d'époque) |
| `parcel_flags` | 2 208 373 | 2 (moteur) |
| ⚠ `mvt_overlays` | 6 009 | aucun (couche mouvement servie carte, pas outil) |
| ⚠ `_lota_grave_parcels` | 73 179 | aucun |
| ⚠ `parcel_pau` | 2 656 | aucun — fiche |
| ⚠ `parcel_veille_succession` | 7 129 | aucun (signal succession jamais exploité) |

## PLU & destinations
| Table | Volume | Lecteurs |
|---|---|---|
| `parcel_zone_plu` | 427 419 | 2, 3, 5, 6, 10 |
| `spatial_layers` kind=plu_gpu_zone | 5 845 zones | 2, 4, 5, 14 |
| `plu_reglement_extrait` | 3 258 | 5 |
| `parcel_residuel` | 431 663 | 1, 2, 3, 6, 8, 10 |
| `sudocuh_procedures` | 24 | 5 (via YAML curé) |
| ⚠ `parcel_au_statut` | 10 537 | aucun — le moteur faisabilité lit le motif AU ailleurs ; la table dédiée n'est servie par aucun outil |
| ⚠ `parcel_residuel_bati` | 0 (orpheline) | aucune — morte (dette EXPORTS-1, cf. fiche 10) |

## DVF & marché
| Table | Volume | Lecteurs |
|---|---|---|
| `dvf_mutations` | 29 566 | 1, 2, 12, 14 (médianes) |
| `dvf_mutations_parcelle` | 102 551 | 6, 12, 14 (+fiche) |
| `score_e` | 285 781 | 1 (legacy 🟡) |
| ⚠ `dvf_mutations_histo` | 110 477 | aucun (archives) |
| ⚠ `p_model_ext_dvf` | 213 028 | aucun des 15 (feature store scoring) |
| ⚠ `p_model_ext_mut_all` / `_mut_l2` | 119 114 / 113 641 | aucun des 15 (feature store) |

## Sitadel & permis
| Table | Volume | Lecteurs |
|---|---|---|
| `sitadel_permits` | 60 696 | 8, 11, 12, 14 |
| `m10_permit_delais` | peuplée | 11, 12 |
| `via_permits_geo` | 47 070 | 11 (+signal viabilisation fiche) |
| ⚠ `p_model_permits` | 59 264 | aucun des 15 (feature store) |

## Propriétaires PM / MAJIC
| Table | Volume | Lecteurs |
|---|---|---|
| `parcelle_personne_morale` | 82 701 | 4, 7, 8, 11 (fiche aussi) — champ `millesime` jamais lu 🟡 |
| `pm_proprietaires_millesimes` | 461 570 | 12 (acquisitions) — historique par PARCELLE jamais servi |
| `pm_dirigeants` | 27 146 | 8 (EXISTS seul — noms/dates jamais servis) |
| `bodacc_procedures` | 674 | 8 (via vue filtrée) |
| ⚠ `bodacc_sondages` | 12 605 | aucun |

## Risques, servitudes, cascade
| Table | Volume | Lecteurs |
|---|---|---|
| `dryrun_cascade_results` | 63,0 M | 4 + tous via tier/étage0 |
| `dryrun_parcel_evaluations` | 1,75 M | tous (étage 0) |
| `parcel_p_score_v2` | 3,46 M | tous (tier v2, run servi) |
| `spatial_layers` (50 kinds, hors PLU/BPE) | 1,85 M total | 4, 14 (+cascade) |
| `catnat_arretes` | 426 | fiche seule — aucun outil |
| ⚠ `score_snapshot_parcelles` | 3,45 M | aucun (archives de scores) |

## Réseaux & viabilisation
| Table | Volume | Lecteurs |
|---|---|---|
| `parcel_viabilisation` | 431 663 | 2, 6 (verdict) |
| `trafic_rn` | 692 | 14 (12 n'en fait rien) |
| ⚠ `anc_maille_taux` | 350 | aucun (l'ANC servie vient de spatial_layers) |

## Équipements, SIRENE, socio-éco
| Table | Volume | Lecteurs |
|---|---|---|
| `sirene_etablissements` | 158 515 | 14 (8 pour l'identité via _pm_identite fiche) |
| `spatial_layers` kind=amenite_bpe | 35 546 | 14 (+fiche « À proximité ») |
| `filosofi_carreaux_200m` | 14 773 | 14 (+fiche) |
| `commune_insee_logement` | 24 | fiche commune seule |
| `rpls_commune` | 24 | fiche commune seule |
| `commune_conso_enaf` | 24 | 12 (ZAN) |
| `mairies` / `commune_contacts` | 24 / 0 | fiche commune (contacts) |
| ⚠ `rnic_coproprietes` | 2 220 | aucun — le flag copro servi vient de `p_model_ext_copro` |
| ⚠ `parcel_amenites` | 431 663 | aucun des 15 (le « À proximité » de la fiche passe par BPE spatial_layers) |
| ⚠ `parcel_vegetation` | 431 663 | aucun des 15 |
| ⚠ `mobpro_commune` | 0 | abandonné (code mort zone.py) |

## Solaire / LiDAR / détection
| Table | Volume | Lecteurs |
|---|---|---|
| `parcel_solar` | 431 663 | 13 |
| `parcel_equipements` | 11 558 lignes utiles | 13 — champs `pv_*` (PV existants) jamais servis 🟡 |
| `piscine_corrections` | 0 | 13 (écriture par geste humain) |
| `toiture_lidar` | 24 | 13 (cache à la demande) |
| `rgealti_pente_5m` | 2 793 | via `parcel_terrain` |
| `parcel_terrain` | 431 663 | 10, 13 (2 via moteur) — `pente_max`, `flag_terrassement` jamais servis |

## Densification & scoring produit
| Table | Volume | Lecteurs |
|---|---|---|
| `parcel_renouvellement` | 67 260 | 10 |
| `p_model_ext_copro` | 431 663 | 10 (flag copro) |
| `p_model_ext_dataset` | 4,3 M | moteurs (feature store) |
| `p_model_static` | 431 663 | moteurs |

## Radar / pige / programmes
| Table | Volume | Lecteurs |
|---|---|---|
| `pige_biens` / `pige_faits` | 109 / 109 | 1 (annonces secteur), 12, 14 (comptes) |
| `programmes` | 9 | 8 |
| `projets` / `projet_parcelles` | 9 / 1 004 | produit (Projets), hors périmètre des 15 |

**Techniques/produit (hors matrice)** : sessions_auth, api_keys, totp_*, stripe_events, usage_*, ia_*, copilote_*, event_log/event_seen, consultation_log, signalements, alertes, retours, circuit_*, registre_*, filtre_*, saved_*, watch_*, source_veille/checks, run_bascule_journal, backups (m6_*, repli_*, backup_*), crm_columns, pipeline_entries, comptes, utilisateurs, mvt_parcels/mvt_meta (tuiles), lettre_zonage_refs, data_sources (métadonnées lues partout).

**Synthèse ⚠ (réserve de puissance)** : `dvf_mutations_histo` (110 k), `pm_proprietaires_millesimes` à la parcelle (461 k, seul l'agrégat commune est servi), `bodacc_sondages` (12,6 k), `pm_dirigeants` en détail (27 k), `rnic_coproprietes` (2,2 k), `parcel_amenites` (431 k), `parcel_vegetation` (431 k), `parcel_veille_succession` (7,1 k), `parcel_au_statut` (10,5 k), `parcel_pau` (2,7 k), `catnat_arretes` (426, fiche seule), `mvt_overlays` (6 k), `score_snapshot_parcelles` (3,45 M, archives), `cadastre_historique` au-delà du rattachement permis (5-6 k), `_lota_grave_parcels` (73 k), champs morts : `parcelle_personne_morale.millesime`, `parcel_equipements.pv_*`, `parcel_terrain.pente_max_deg/flag_terrassement_lourd`, `parcel_solar.ghi_kwh_m2_an`.

---

# PARTIE C — REGROUPEMENTS NON SERVIS

Faits et faisabilité seulement ; volumes = comptes réels.

1. **Histoire d'une parcelle** : `dvf_mutations_parcelle` (102 551) + `pm_proprietaires_millesimes` (461 570) + `cadastre_historique` (6 495) permettent de répondre à « qui a possédé/acheté cette parcelle, quand, à quel prix, et comment a-t-elle été découpée ? ». Faisabilité : jointures par IDU existantes (le moteur acquisitions de Communes fait déjà la détection de changement de SIREN par millésime) ; à écrire : la vue par parcelle. Volume : ~570 k lignes sources.
2. **PV existants + solaire** : `parcel_equipements.pv_detecte/pv_surface_m2/pv_confiance` (peuplés, jamais servis) + `parcel_solar` permettent de répondre à « quels toits bien exposés ne sont PAS encore équipés ? » (exclusion des équipés du démarchage). Faisabilité : moteur solaire existant, filtre SQL à ajouter. Volume : 431 663 lignes.
3. **Permis dormants — pourquoi** : `sitadel_permits` (PC>36 m sans DAACT) + `pm_proprietaires_millesimes` (changement de propriétaire depuis le dépôt) + `dvf_mutations_parcelle` (revente) + cascade (obstacle) permettent de répondre à « ce PC dormant a-t-il changé de mains ou rencontré un obstacle ? ». Faisabilité : moteur dormants existant (`modules.py:634`), croisements à écrire. Volume : ~4 700 dormants (1 484+3 053+124 sur les 3 communes mesurées, extrapolable).
4. **Succession + patrimoine** : `parcel_veille_succession` (7 129) + `parcelle_personne_morale`/MAJIC + `parcel_residuel` permettent de répondre à « quelles parcelles à potentiel sont en situation de succession ? ». Faisabilité : signal déjà stocké, aucun moteur ne le lit ; croisement simple. Volume : 7 129.
5. **Copropriétés** : `rnic_coproprietes` (2 220) + `p_model_ext_copro` (flag) + `parcel_residuel` permettent de répondre à « quelles copropriétés identifiées portent un résiduel constructible ? ». Faisabilité : RNIC en base mais non rattachée aux parcelles — rattachement à écrire (adresse/parcelle). Volume : 2 220 copros.
6. **Procédures BODACC en masse** : `bodacc_sondages` (12 605) + `bodacc_procedures` (674) + `parcelle_personne_morale` permettent de répondre à « quels propriétaires fonciers du 974 entrent en difficulté ? » au-delà de la vue filtrée servie à Scan patrimoine. Faisabilité : vue `v_foncier_sous_pression` existante à élargir. Volume : ~13 k annonces.
7. **Clusters fonciers PM** : `parcelle_personne_morale` (82 701) + contiguïté (moteur assemblage, union-find existant `assemblage.py:88-165`) + `parcel_residuel` permettent de répondre à « quels blocs contigus un même propriétaire détient-il, avec quel potentiel groupé ? ». Le Scan calcule déjà la plus grande assiette d'UN SIREN ; la matrice complète n'existe pas. Volume : ~12 k clusters estimés.
8. **AU futures + chronologie** : `spatial_layers` AU (744 îlots AUc+AUs) + `veille_plu` (procédures) + `sitadel_permits` 36 m permettent de répondre à « où et quand du foncier va s'ouvrir, avec quel flux de permis autour ? ». Faisabilité : `zone_demain()` (`zone.py:511-539`) et le simulateur M15 existent ; le tableau chronologique commune×AU manque. Volume : ~240 lignes.
9. **Maille humaine fine** : `filosofi_carreaux_200m` (14 773) + `sirene_etablissements` + BPE permettent une lecture carreau par carreau (habitants+emplois+équipements) aujourd'hui calculée à la volée par zone ; matérialisée, elle servirait tri et carte. Faisabilité : moteur `zone.py` existant, matérialisation à écrire. Volume : ~15 k carreaux.
10. **Végétation × densification** : `parcel_vegetation` (431 663, jamais lue par un outil) + `parcel_renouvellement` permettent de répondre à « le résiduel de cette parcelle occupée est-il sous canopée ? » (coût d'abattage, contrainte paysagère). Faisabilité : jointure simple. Volume : 431 663.

---

# ANNEXE — MESURES A8 COMPLÈTES (serveur local, 06/09/2026)

75 appels, **75 × HTTP 200, 0 erreur, 0 timeout**. Sélection complète (tool · appel · code · temps · taille) :

```
etudier      scoreur AB0009/AC0024/AE0003        200  2.83 / 0.14 / 0.05 s   0,6 Ko
etudier      mon-secteur ×3                      200  0.73 / 0.45 / 0.16 s   1-2 Ko (adresse:null ×3)
faisabilite  sens1 ×3                            200  0.20 / 0.08 / 0.02 s   13 / 5,7 / 5,7 Ko
faisabilite  charge ×3                           200  0.18 / 0.04 / 0.02 s   (calculable / non_resolue ×2)
faisabilite  programme Saint-Denis               200  0.81 s                 959 Ko ⚠
taxe         prefill ×3 · config · calcul        200  0.03-0.01 s            <1 Ko
risques      duediligence ×3                     200  1.00 / 0.10 / 0.23 s   2-3 Ko
risques      servitudes ×3                       200  0.07 / 0.13 / 0.08 s   1-2 Ko (5/1/1 servitudes)
plu          verif-procedure ×3                  200  0.28 / 0.07 / 0.04 s   0,3 Ko
plu          annuaire · search · simulplu/zones  200  0.18 / — / 0.39 s      9 Ko / — / 86 o
comparer     compare 3 idus                      200  1.93 s                 3,1 Ko
assemblage   2 parcelles                         200  0.25 s                 1,4 Ko (contigu:false)
patrimoine   search · SIREN 310863592 · veille   200  0.16 / 3.64 / 0.15 s   55 o / 101 Ko / 35 Ko
courrier     statut · demandes                   200  0.01 / 0.01 s          (stub)
densifier    liste StD/StP/StPh                  200  0.12 / 0.15 / 0.04 s   84 / 85 / 0,5 Ko (7242/8075/0)
permis       permis ×3 · dormants ×3             200  0.04-0.02 / 0.12-0.01  128-23 Ko / 283-30 Ko ⚠
permis       parcelle-permis AB0009              200  0.02 s                 (c200=9)
communes     communes · comparateur              200  0.005 / 0.007 s        5 / 12 Ko
communes     barometre île · 97411               200  0.17 / 0.08 s          3 Ko
communes     acquisitions ×3 · contexte ×3       200  2.10-0.10 / 2.44-0.01  43-4 Ko / 8-10 Ko (froid/cache)
solaire      fiche-soleil ×3                     200  4.17 / 1.34 / 0.76 s   ~1 Ko (LiDAR à la demande)
solaire      piscines ×3                         200  0.06-0.04 s            (1226 / 1545 / 29)
zone         parcel-zone ×3                      200  1.89 / 1.58 / 1.52 s   7 / 2,5 / 6 Ko (isochrone)
zone         etude-zone AB0009                   200  1.04 s                 24 Ko (cache isochrone)
temps        geojson ×3 · 2 tuiles proxy         200  0.01 / 0.32 / 0.13 s   72 / 12 Ko
```

Détail brut : `/tmp/outils-audit/mesures.tsv` (non versionné — hors livrable). Script rejouable : boucle curl sur les URLs listées dans chaque fiche.

**Usage A9 (usage_events, 30 j, base locale)** : communes 74 · permis 72 · plu 33 · etude-zone 33 · scoreur-adresse 28 · taxe 26 · prospection-solaire 22 · patrimoine 19 · courriers 12 · programme 12 · mon-secteur 11 · veille-promoteurs 10 · temps 8 · risques 7 · renouvellement 7 · assemblage 5 · comparer 3. Capteur : `usage_par_outil` (`registre/moteurs/plateforme.py:78-84`), servi par `GET /admin/produit` (`dashboard.py:1451`). Présent pour les 15 ; valeurs locales ≠ prod.

---

# COMPTE-RENDU (20 lignes)

1. Décompte : **0 🔴 · 3 🟠 · ~18 🟡 · 4 DOUTE** ; ABSENT structurants : export Comparer, saisie clavier Assemblage, ponts Scan/Solaire→Courrier.
2. Les trois constats les plus lourds :
3. — **Prospection solaire ment sur sa fraîcheur** (« gelées 11/07 » vs relevé 23/08 en base) et son export CSV promis n'a pas de bouton : l'outil de démarchage ne démarche pas.
4. — **Densifier sert une colonne Surélévation morte** (`false/NULL` en dur pour 67 260 parcelles) — dette EXPORTS-1 assumée mais visible à l'écran.
5. — **La chaîne « sourcer → approcher » est coupée** : ni Scan patrimoine ni Solaire ne renvoient vers Courrier, alors que Risques et Assemblage le font.
6. Le socle est sain : les 75 appels mesurés rendent tous 200, le run q_v11_m137 est épinglé partout où il doit l'être (aucune lecture LIVE servie trouvée),
7. aucun faux chiffre servi n'a été constaté, et les cas limites (RNU, SDP=0, zone sans marché) refusent proprement au lieu d'inventer.
8. Les outils les plus utilisés (Communes 74, Permis 72) sont aussi les plus propres ; les moins utilisés (Comparer 3, Assemblage 5) ont des causes d'entrée factuelles (pas de saisie, pas d'export, pas de pré-remplissage).
9. Réserve de puissance (Partie B) : ~16 tables métier peuplées qu'aucun outil ne lit — les plus denses : pm_proprietaires_millesimes à la parcelle (461 k), dvf_mutations_histo (110 k), parcel_vegetation et parcel_amenites (431 k chacune), pv_detecte (équipés PV jamais exclus du démarchage).
10. Limites de l'audit : temps mesurés en local (pas la prod) ; usage A9 = base locale (l'usage réel client n'est pas observable d'ici) ;
11. l'envoi Courrier réel (provider stub en local) et le rendu écran exact (captures) n'ont pas pu être vérifiés — c'est l'objet du croisement avec les captures de Vic ;
12. le doublon d'aléa (Risques, AC0024) et la divergence potentielle des deux chemins « revenu » (Étude de zone) sont notés DOUTE, à trancher sur écran ;
13. les fiches détaillées des 15 agents d'audit (preuves longues) ont servi de matière et leurs constats cités ici ont été contre-vérifiés dans le code pour tous les KO.
14. Aucune modification de code ni écriture en base n'a été faite ; seul ce rapport est produit. Le lancement local du serveur a exécuté son auto-réparation de schéma standard (idempotente, aucune donnée modifiée).
