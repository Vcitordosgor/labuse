# AUDIT — Fiche parcelle (le cœur du produit)

**Date** : 2026-08-24 · **Branche** : `audit/fiche-parcelle` · **Type** : audit seul (aucun code modifié ; Postgres lecture ; endpoints fiche sondés en `GET`).
**Périmètre** : la fiche parcelle — tous ses blocs/tiroirs, la chaîne de données, la doctrine de provenance, la cohérence croisée avec les autres surfaces.
**Méthode** : lecture du code (`Fiche.tsx` + sous-composants ; `app.py` `_q_v2_fiche`/`_build_fiche` + engine/résiduel) ; **5 parcelles-témoins** servies en direct (dont **BZ 1065**, le témoin de Vic) et croisées bout en bout avec la base.

**Témoins** (Saint-Denis, un par tier) : `97411000BZ1065` (a_creuser/Neutre, témoin Vic) · `BZ1090` (brûlante) · `HL0011` (chaude) · `AE0747` (déclassée bâti saturé) · `BP0678` (réserve foncière).

> App laissée intacte (uvicorn:8000 + vite) : uniquement des `GET` et des `SELECT`.

---

## 0. Structure & endpoints

La fiche (`Fiche.tsx`) est une **pile de tiroirs en accordéon exclusif** (un seul ouvert), pas des onglets : en-tête sticky (identité + 4 chiffres) → bloc **Analyse LABUSE** (verdict, score v2, pourquoi) → **LE TERRAIN** (Urbanisme · Constructibilité · Risques) → **LE CONTEXTE** (Marché · Réseaux/accès · Propriétaire) → **Données et méthode** → barre d'actions/exports.

Endpoints : `GET /parcels/{idu}?source=q_v*` (**premium** `_q_v2_fiche`, ce que l'UI reçoit — `getFiche` envoie TOUJOURS `source`) ; `/modules/faisabilite/{idu}` (capacité/SHAB, appelé par le tiroir Constructibilité) ; `/parcels/{idu}/mode-b`, `/explain`, `/v2/score`, `/anti-fiche`, `/ortho-equipements`. ⚠ `GET /parcels/{idu}` **sans** `source` → **200** via le builder **legacy** `_build_fiche` (§4.3).

---

## 1. Tableau par bloc

Fraîcheur : « amont » = date de la source (data_sources.source_millesime), « run » = date du run servi (q_v10_m129, dryrun 2026-08-19).

| Bloc / tiroir | Source (table · run) | Fraîcheur exposée | Verdict | Constat |
|---------------|----------------------|-------------------|---------|---------|
| En-tête · identité | `parcels` (idu, surface, coords) + BAN (`parcel_adresse`) | cadastre / BAN | ✓ | Surface Sourcé ; adresse Sourcé BAN (repli honnête si absente). |
| En-tête · 4 chiffres | Zone `reglement_plu` · SDP `potentiel_transformation.sdp_residuelle_m2` · Nu `dvf_parcelle.secteur[terrain]` | GPU / dérivé / DVF 2021-2025 | ✓ | « — » honnête si absent (Nu, SDP≤0, zone non publiée). |
| Analyse · verdict/tier/rang | `parcel_p_score_v2` (v2run) + `dryrun_parcel_evaluations.status` (étage 0) | run (épinglé) | ✓ | Tier == carte pour **5/5 témoins** (§2). verdict_servi = point unique. |
| Analyse · score v2 / fraction | `parcel_p_score_v2` (p_raw, percentile, top5) + `/v2/score` | run | ✓ | « Pourquoi ce score » = top5 contributions. Copro → « hors classement ». |
| Analyse · Pourquoi pas | `/anti-fiche/{idu}` | run | ✓ | Rédhibitoires + vigilances, chacun avec motif + source. |
| Lignes cascade (37) | `dryrun_cascade_results` ⟕ `data_sources` | **amont** (`millesime_amont`) + run (`date`, masqué) | ✓ | Chaque ligne : source (cliquable→drawer) + `source_table#source_id` (audit) + `millesime_amont`. §3. |
| Urbanisme (regles) | `reglement_plu` (GPU) · `plu_fraicheur` (yaml millésimes) · `radar_procedure` · traducteur PLU | GPU / approbation mairie | ✓ | Hauteur/articles Sourcé GPU ; SDP consommée Dérivé ; fraîcheur PLU = horizon mairie (pas ingestion). |
| Urbanisme · APER | `parkings_aper` (M75) | loi 2023-175 | ✓ | Conditionnel (901 parcelles) — null pour les 5 témoins, **pas mort**. |
| Constructibilité (faisa) | `/modules/faisabilite` → `engine.py` (capacité, SHAB) + `parcel_residuel` (résiduel) | run / dérivé | ✓ | SHAB vendable **123** (BZ1065) = MÊME moteur que le module Faisabilité (§2). Étapes tracées + statut Sourcé/Estimé/Dérivé. |
| Constructibilité · Mode B | `/parcels/{idu}/mode-b` (hypothèses saisies) | Estimé (éphémère) | ✓ | `disponible:false` + **motif** honnête si hors population (BZ1065). Jamais Sourcé. |
| Risques | `dryrun_cascade_results` (onglet risques) + `parcel_viabilisation` + `gestionnaires` | amont | ✓ | Lignes sourcées ; viabilisation Dérivé (faisceau) ; ANC point unique. |
| Marché (marche) | `dvf_parcelle` (`v_parcel_dvf_last`, `dvf_secteur_medianes`) + `marche_secteur` (Filosofi/RPLS) + voisinage | DVF 2021-2025 / Filosofi 2021 / RPLS 2025 | ✓ | Nu 369 €/m² == en-tête == ligne DVF (§2). Neuf VEFA = point `marche_service`. |
| Réseaux/accès (viab) | `parcel_viabilisation` · `proximites` (spatial_layers KNN) · `/ortho-equipements` | Sourcé OSM/GTFS/BD TOPO | ✓ | Transport/axes/HT sourcés ; statut dit la source (OSM Sourcé / GTFS Dérivé). |
| Propriétaire (proprio) | `parcelle_personne_morale` + `_pm_etat_societe` (BODACC) + `coproprietes` (RNIC) | DGFiP / BODACC | ✓ | PM Sourcé DGFiP ; PP → « personne physique / non recensé » (honnête). |
| Propriétaire · DPE | `dpe_connu` **(legacy uniquement)** | — | ✗ | **Bloc mort dans l'UI** : le premium ne sert pas `dpe_connu` ; `parcel_dpe` n'existe pas (§4.2). |
| Signaux · entrée-tête / acquérabilité | `parcel_entree_tete` (514) / `parcel_acquerabilite` (1060) via `_m28_badges` | — | ✗ | **Bloc mort dans l'UI** : gaté derrière `LABUSE_M28_BADGES=1` (OFF) → premium renvoie `{}` malgré la donnée prête (§4.1). |
| Données et méthode | `_data_sources_fiche` (`data_sources`) + `qualite_commune` + `icd` | **amont** (millésime + fiabilité) | ✓ | 27 sources : nom · fournisseur · **millésime amont** · fiabilité. Doctrine servie ici (§3). |
| Barre d'actions / ponts | store (setModule, parcelPrefill, openCompare…) | — | ✓ | Ponts contextualisés (§5). Mention légale présente. |

---

## 2. Cohérence croisée — vérifiée bout en bout sur les témoins

| Grandeur | Fiche | Autre surface | Concorde ? |
|----------|-------|---------------|-----------|
| **Tier / rang** | `parcel_p_score_v2` (v2run) | Carte `mvt_parcels` | ✓ **5/5 témoins identiques** (BZ1090 brûlante rang 2090=2090…). |
| **Résiduel** (sdp_residuelle_m2) | `parcel_residuel` (live, 26 m² BZ1065) | Carte `mvt_parcels` | ✓ **0 divergence sur 431 663 parcelles**. Le « périmé » d'AUDIT-CARTE-FOND est un retard de TIMESTAMP (mvt 19/08 < résiduel 23/08) **sans changement de valeur** — fiche et carte s'accordent partout. |
| **SHAB vendable** (~123 m²) | Tiroir Constructibilité → `/modules/faisabilite` (`engine.py:469`) | Module Faisabilité (même endpoint) | ✓ **Même point de calcul** (sol_central × logt_moyen). Non porté par les tuiles → aucune divergence carte. |
| **Prix de zone** (terrain 369 €/m²) | En-tête « Nu » = `dvf_parcelle.secteur[terrain]` | Ligne DVF cascade + tiroir Marché | ✓ **Même `dvf_parcelle.secteur`** (369 = 369 = 369). |
| **Charge foncière** | Calculette → `compute_bilan_servi` (`marche_service.marche_dvf`) | Filtre budget, PDF comparables | ✓ Point d'appel unique DVF (M73-B/F). |
| **Résiduel 26 vs SHAB 123** | Deux grandeurs DISTINCTES (résiduel = reste sous densité ; SHAB = programme complet) | ÉTUDIER réconcilie « 26 < 123 » | ⚠ Concepts différents, tous deux sourcés — l'écart est expliqué (par ÉTUDIER), pas contradictoire (§3). |

**Sous-jacent structurel** : la fiche lit la cascade depuis `Q_A_RUN_LABEL` (dryrun) ET le tier depuis `v2run` (`parcel_p_score_v2`) — deux pointeurs de run, **alignés aujourd'hui** (tous `q_v10_m129`) mais à maintenir en phase.

---

## 3. Doctrine (provenance / fraîcheur) — solide

- **Chaque ligne cascade** porte : `source` (nom, cliquable → drawer), `source_table#source_id` (traçabilité, masquée au client par M70), `date` (= date du RUN, uniforme, **volontairement masquée** via `hideDate` car trompeuse), et **`millesime_amont`** (= `data_sources.source_millesime`, la VRAIE fraîcheur amont, M73 E).
- **Le tiroir « Données et méthode »** liste les 27 sources avec **millésime amont + fiabilité** (suivie/à confirmer). C'est le point où la fraîcheur amont est servie — **jamais la date d'ingestion**.
- **Statuts** Sourcé (open-data direct) / Estimé (calcul, proxy marché, Mode B) / Dérivé (résiduel, SHAB) présents par bloc ; l'absence est dite (« — », « non calculable », « Non publié au GPU », section « Ce que LABUSE ne peut pas savoir »).
- ⚠ **Nuance** : la fraîcheur amont (`millesime_amont`) existe PAR LIGNE dans le payload mais n'est affichée qu'en AGRÉGÉ (tiroir Données) + le drawer de source — pas inline sur chaque ligne (choix M70 : la date inline serait le run uniforme, trompeur). Provenance présente ; fraîcheur par-ligne consultable au drawer.

**Verdict doctrine** : conforme. Aucune valeur affichée sans provenance ; fraîcheur = source amont.

---

## 4. Champs vides / blocs morts

### 4.1 — `entree_tete` + `acquerabilite` : données prêtes, bloc éteint ✗ (moyen)
`_m28_badges` (qui remplit `entree_tete` et `acquerabilite`) est **gaté** : `**(_m28_badges(...) if os.environ.get("LABUSE_M28_BADGES")=="1" else {})` (app.py ~2637). Le flag est **OFF** sur le serveur (confirmé : les 3 témoins n'ont aucun de ces champs). Or les tables sont **peuplées** : `parcel_entree_tete` = **514**, `parcel_acquerabilite` = **1 060**. Le front (Fiche.tsx:1842/1847) rend `if ((f as any).entree_tete…)` → **ne s'affiche jamais** dans l'UI premium. Une donnée calculée (point d'entrée M55-E, signal assemblage) reste dans le noir.

### 4.2 — DPE : bloc mort dans l'UI ✗ (moyen)
Le front (Fiche.tsx:2437) lit `(f as unknown).dpe_connu`. Or `dpe_connu` n'est construit QUE dans le builder **legacy** `_build_fiche` (app.py ~3935), **pas** dans le premium `_q_v2_fiche` → l'UI ne le reçoit jamais → le libellé « DPE connu : … » ne s'affiche jamais. Pire : la table `parcel_dpe` **n'existe pas** en base (le legacy lui-même échouerait). Bloc + libellé promettant une donnée absente.

### 4.3 — Deux builders de fiche, le legacy invisible mais joignable ⚠ (faible-moyen)
`/parcels/{idu}` **sans** `source` renvoie **200** via `_build_fiche` (legacy), qui porte des blocs que le premium N'A PAS (`bati`, `piscine`, `loyers`, `occupation`, `plh`, `market_signal`, `defisc`, `pc_caduc`, `resume`, `dpe`…). L'UI envoie toujours `source` → toujours le premium → ces blocs legacy sont **invisibles à l'UI**. Un appelant API direct (sans source) obtient une structure DIFFÉRENTE. Double maintenance + « richesse » legacy non servie.

### 4.4 — Conditionnels sains (RAS)
`aper` (901), `plu_fraicheur`, `radar_procedure`, `reglement_plu`, `renouvellement`, `rnu`, `mode_b`, `coproprietes`, `marche_secteur`, `icd` : rendus SEULEMENT si présents (absence = aucun rendu, jamais un blanc trompeur). Corrects.

---

## 5. Ponts sortants & cycle de vie (RAS)

Ponts contextualisés, state propre : **Comparer** (`openCompare`+`addToCompare`) · **Remonter le temps/1950** (`setParcelPrefill`+`setFlyTo`+`setModule('temps')`) · **Pièges/risques** (`setModule('risques')`) · **Courrier** (`setModule('courriers')` si PP) · **Scan patrimoine** (`setM02Prefill(siren)` si PM) · **Faisabilité/Calculette/Assemblage** (`setParcelPrefill`+setModule). Fermeture Échap (`select(null)`, sauf drawer source ouvert) ; accordéon exclusif par parcelle (`ficheTiroir[idu]`) ; scroll `scrollIntoView` à l'ouverture d'un tiroir ; calculette réinitialisée au démontage. Aucun résidu détecté.

---

## 6. Classement des problèmes par gravité

| Gravité | # | Problème | Impact |
|---------|---|----------|--------|
| **Moyenne** | F1 | `entree_tete`/`acquerabilite` gatés `LABUSE_M28_BADGES` (OFF) malgré 514/1060 parcelles prêtes (§4.1) | Donnée calculée jamais montrée ; bloc front dark. |
| **Moyenne** | F2 | Bloc DPE mort dans l'UI : `dpe_connu` legacy-only + `parcel_dpe` absente (§4.2) | Libellé promettant une donnée jamais servie. |
| **Faible-moy.** | F3 | Deux builders de fiche ; `_build_fiche` legacy joignable sans `source` (200), structure divergente (§4.3) | Double maintenance ; blocs legacy invisibles à l'UI ; API sans source = shape différente. |
| **Faible** | F4 | `millesime_amont` par ligne non affiché inline (seulement agrégé + drawer) (§3) | Fraîcheur par-ligne moins immédiate (choix M70 défendable). |
| **Faible** | F5 | Deux pointeurs de run (cascade `Q_A_RUN_LABEL` vs `v2run`) à garder en phase (§2) | Alignés aujourd'hui ; risque de décalage en bascule. |

**Le cœur est sain** : verdict/tier, résiduel, SHAB vendable, prix de zone, charge foncière concordent avec les autres surfaces (vérifié sur 5 témoins + à l'échelle de l'île) ; provenance et fraîcheur amont servies par bloc ; aucune valeur affichée sans provenance ; ponts et cycle de vie propres. Les écarts sont des **blocs morts/darks** et une **dette de double-builder**, pas des chiffres faux.

---

## 7. Correctifs candidats à mandater (non faits)

1. **F1** — Trancher `entree_tete`/`acquerabilite` : soit les surfacer (retirer/activer le flag `LABUSE_M28_BADGES` — la donnée est prête, 514/1060), soit retirer les blocs front morts.
2. **F2** — DPE : retirer le bloc front mort (Fiche.tsx:2437) OU servir `dpe_connu` en premium + rétablir la table `parcel_dpe`. Décider si le DPE a sa place dans la fiche.
3. **F3** — Converger les deux builders : faire de `/parcels/{idu}` un endpoint qui EXIGE `source` (404 sans, comme `/parcels` et `/stats`) pour tuer le chemin legacy ; ou rapatrier dans le premium les blocs legacy jugés utiles (loyers, occupation, PLH…) sinon les retirer.
4. **F4** — Envisager d'afficher `millesime_amont` inline par ligne (ou l'assumer dans le tiroir Données).
5. **F5** — Documenter/garantir l'égalité `Q_A_RUN_LABEL` == `v2run` servi (garde de cohérence à la bascule).

---

## 8. Synthèse

La fiche parcelle — le cœur du produit — est **solide et cohérente**. Sur 5 parcelles-témoins (dont BZ 1065) et à l'échelle de l'île : le **verdict/tier** concorde avec la carte (5/5), le **résiduel** est identique fiche↔carte (0 divergence / 431 663), le **SHAB vendable** vient du même moteur que Faisabilité, le **prix de zone** et la **charge foncière** partagent leurs points de calcul uniques. La **doctrine** est respectée : chaque ligne porte sa source (traçable au drawer) et sa fraîcheur AMONT (`millesime_amont`, pas la date d'ingestion), les statuts Sourcé/Estimé/Dérivé sont présents, l'absence est dite honnêtement. **Cinq écarts**, deux de gravité moyenne — des **blocs morts/darks** : `entree_tete`/`acquerabilite` éteints par un flag alors que la donnée est prête, et le **DPE** que l'UI ne reçoit jamais — plus une **dette de double-builder** (le legacy joignable sans `source`). Rien de faux n'est servi ; ce sont des promesses non tenues et de la dette, pas des chiffres erronés.
