# SOURCES-AUDIT-3 — chaque consommateur, sa source

**Branche** `audit/sources-3` · worktree `/Users/openclaw/Desktop/labuse-sources3` · ports 8595/5795 · **lecture seule** (aucune écriture `src/`, aucune écriture base, aucun run) · 2026-09-28.
**Base** `postgresql://openclaw@localhost:5432/labuse` (dev, même schéma que `main`). API + front lancés une fois pour la vérification écran (Lot C).

**Différence avec SOURCES-AUDIT-2** : AUDIT-2 partait de la liste des sources et cherchait où chacune s'affiche (source→écran). **Ici on part de chaque consommateur** (outil, section de fiche, couche, export, job) et on remonte chaque donnée lue jusqu'à sa ligne `data_sources` (consommateur→donnée→table/API→source). But : zéro donnée servie hors de la liste, zéro outil sur la mauvaise source.

**Méthode.** La chaîne de branchement : `registre/donnees.DONNEES[slug]` (registre servi : libellé, `fonction`=producteur, `reservoirs`) → `registre/tables.RESERVOIR_TABLES[slug]` (tables/vues SQL + `kind` de `spatial_layers` + millésime) → `circuit_etats.NOM_VERS_SLUG` (pont nom↔slug) → `data_sources` (la liste : id, statut, millésime). Un **squelette machine** (`scripts/_sources3_backbone.py`, 286 données résolues) a servi de socle ; 11 traçages de consommateur ont ensuite suivi le code réel (grep/read `fichier:ligne`), croisé les comptes exacts en base (`count(*)`, jamais l'estimateur), et interrogé l'API live. Toute affirmation de blocage-grade a été **revérifiée à la main** (voir « corrections » plus bas).

---

## Les chiffres

| Chiffre | Valeur |
|---|---:|
| **Consommateurs tracés** (périmètres) | **11** — fiche parcelle (12 sections + bandeau), fiche commune (10 cartes), 16 outils du menu, panneau Filtre (52 filtres), couches de la carte (48 vecteur + fonds/rasters), 4 PDF + Flash, Copilote (3 chemins + AskBar), Radar, Veille/digest, Étude de zone, dashboard admin (Sources + Circuit) |
| **Étiquettes de consommateur distinctes** | **236** |
| **Données affichées tracées** (`BRANCHEMENT.csv`) | **617** |
| **Branchements OK** (remontent à une ligne `data_sources`) | **529 (86 %)** |
| **Lignes `HORS-LISTE`** (sans origine `data_sources`) | **57** — dont ~35 légitimes (transport d'envoi, fond WMTS, saisie porteur, constante juridique en config, méta interne) et 22 signalées cat.1 |
| **Sources `data_sources` distinctes réellement lues** | **100** (sur 123 actives) |
| **Anomalies** (`ANOMALIES.csv`) | **100** |
| dont **bloquant déploiement** | **0** |
| dont **à corriger** | **34** |
| dont **cosmétique** | **66** |

**Anomalies par catégorie** : 1 (hors liste) **22** · 2 (source retirée/morte lue) **3** · 3 (mauvais branchement) **10** · 4 (mauvaise étiquette) **24** · 5 (couverture) **14** · 6 (appel externe à l'exécution) **27**.

Livrables : **`BRANCHEMENT.csv`** (617 lignes : consommateur · donnée · table/API · fichier:ligne · source(s) · statut · millésime), **`ANOMALIES.csv`** (99 lignes catégorisées), **`captures/`** (Lot C), ce rapport, `scripts/_sources3_backbone.py`.

---

## Verdict : aucun bloquant déploiement

**Aucune donnée fausse n'est servie depuis l'extérieur de la liste.** Les 22 `HORS-LISTE` cat.1 sont soit des **paramètres/constantes légitimes** (hypothèses de faisabilité saisies par le porteur, valeur forfaitaire CGI 892 €/m² 2026 en config datée/sourcée, annuaires mairies/EPCI/gestionnaires, calibrages LABUSE), soit des **méta internes** (qualité commune, run analysé), jamais une donnée territoriale inventée. Les appels externes à l'exécution (27, cat.6) ont **tous un repli propre et nommé** (jamais un faux « — » présenté comme une mesure). Les 5 sources `retiree` (49 EDF SEI, 50 ODRÉ, 68 Office de l'eau, 87 MOBPRO, 89 BDNB) ne sont **lues par aucun consommateur vivant** ; les 3 cat.2 sont des **références mortes sans effet** (voir plus bas).

Les 34 « à corriger » sont réels mais aucun ne sert un chiffre faux à l'acheteur : ce sont des **doublons de calcul**, des **étiquettes de source figées** décorrélées du catalogue, et des **couches sur une source non canonique**. Les plus proches d'un blocage sont listés ci-dessous.

### Les « à corriger » les plus visibles produit (candidats prioritaires)

1. **Mouvement de terrain servi depuis deux sources concurrentes** (cat.3/4/5 — rows fiche_commune §Risques, couche_carte:alea_mvt). La fiche commune lit `spatial_layers kind='mvt'` (**3 085** lignes, source **36 Géorisques — mouvements de terrain**, datée 2026-09-14). La carte lit `kind='georisque_alea' subtype='mouvement_terrain'` (issu de **4 Géorisques**, une ligne catch-all **sans millésime ni last_sync**). Deux jeux de données distincts (3 085 vs sous-ensemble de 1 093) pour la même notion ; le `kind='mvt'`/source 36 n'est dessiné par **aucune** couche. Un utilisateur peut voir un % en fiche et une emprise en carte qui ne coïncident pas. *(à corriger)*

2. **Deux « Classement LABUSE » de deux runs coexistent** (cat.4 — outil Comparer, carte Analyse). Comparer et la carte Analyse servent le classement depuis `score_labuse` au run **candidat q_v15** (`SCORE_LABUSE_RUN`, 431 663 lignes, seul run non-dry-run en base), tandis que le verdict/tier de la carte et de la fiche vient du run **servi q_v11_m137**. Deux vintages du « LABUSE » dans le même produit — cohérent Comparer↔Analyse, incohérent vs carte/fiche. *(à corriger)*

3. **La couche « SAR » est un proxy non diffusé** (cat.1 — couche_carte:sar). `spatial_layers kind='sar'` (**2 453** polygones) est affiché comme SAR alors que la source officielle **118 (partenariat_requis, « couche SIG NON diffusée »)** n'existe pas ; ce sont en réalité les îlots de **potentiel foncier Région (source 9, alias)** — vérifié : les 2 453 géométries `kind='sar'` sont **identiques** (`ST_Equals`) aux 2 453 `kind='potentiel_foncier'`. Le caveat « PROXY » existe sur le chiffre `sar_divergence` mais **pas sur la couche carte**. *(à corriger)*

4. **Deux magasins de millésime à l'admin** (cat.4 — dashboard:page_circuit). Le millésime « servi » affiché dépend de l'écran admin ouvert : page Circuit lit `data_sources.source_millesime`, page compteur lit `RESERVOIR_TABLES[slug].millesime`. **66/129 sources mappées divergent**, 39 avec les deux textes renseignés et différents. Pas de vérité unique. *(à corriger)*

5. **`/sources` client sert le millésime BRUT (sans `composer`)** et **22 sources affichées ont `source_millesime` NULL** (cat.4 — dashboard:page_sources). Contrairement à la fiche, l'endpoint client n'applique pas `millesime_source.composer` : les notes internes (« édition non enregistrée », « latest ingérée », « proxy ») ne seraient pas nettoyées. Impact atténué car `SourcesPage.tsx` a retiré l'affichage du millésime ; mais 17 des 22 sources vides possèdent un millésime dans `RESERVOIR_TABLES` non recopié dans le magasin client. *(à corriger)*

6. **Le pré-dossier ZIP double le chemin de collecte de la fiche** (cat.3 — export:pre-dossier vs dossier). Le Dossier PDF passe par le robinet unique (`robinet_fiche.py`, payload `/parcels`) ; le pré-dossier ZIP requête la base **en direct** (`flash/data.py collect_report_data`, `spatial_layers`/`dvf_secteur_medianes`/`resolve_zone`), avec sa propre table de sources semi-statique (`_SECTION_SOURCES`, millésimes figés). Risque de divergence Dossier↔Pré-dossier pour la même parcelle. *(à corriger)*

---

## Ce qui est SAIN (levée de doutes du mandat)

- **Faisabilité (M22) ne calcule rien en front** : `FaisabiliteTab`→`POST /modules/faisabilite/{idu}/scenario`→`faisabilite_scenario` (moteur unique). **Gabarit (M24)** lit la même zone d'implantation (`resolve_zone` + reculs). *(vérifié)*
- **Le point historique « médiane DVF recalculée avec bornes maison » d'AUDIT-2 (E1) est corrigé** : `zone.py` délègue désormais à `dvf_mediane.mediane_bati` (mêmes bornes [1000;12000]/36 mois que la fiche). Il reste une divergence **assumée et documentée** avec le baromètre commune (bornes [100;12000], tout l'historique, min 100 ventes — `moteurs.py:714`) : voulue, pas à aligner (cosmétique).
- **Le filtrage `subtype` est forcé** partout où un `kind` porte plusieurs sources : `sol_pollue` (SIS 115 vs CASIAS 116), `georisque_alea` (inondation vs mouvement), `enp`→`ens`, prescriptions PLU 05/01 — aucun mélange de sources sous un même toggle. *(vérifié — le point de vigilance du mandat est levé pour les couches)*
- **Le Dossier et le Flash sont des miroirs de la fiche** (`builder.py:443`, `robinet_fiche.py`) : mêmes sources que l'écran ; le « Banquier » n'existe plus (redirige vers `/financier`). Les pieds « Sources » sont dérivés des réservoirs réellement lus (sauf exceptions cat.4 ci-dessous).
- **Radar/Veille/Digest** : Radar = `radar_pige` (id 84) ± `dvf` (id 5), les deux en base ; Veille = 4 flux réels (Mutation/Permis/BODACC/Propriétaire-PM) ; Digest = Brevo/SMTP en repli dry-run. Les 3 trous de VEILLE-AUDIT-2 (dépôt du soir, `digest_freq`, worker mail) sont **fermés**.
- **Taxe d'aménagement** : moteur unique `calculer()`, taux communal (`taxe_amenagement_taux`, 24) + secteur (`taxe_amenagement_secteur`, 10 465), tous 98:taxe_amenagement (DELTA, connecte).

---

## Corrections apportées aux traçages bruts (fiabilité)

Les agents de traçage sont fiables sur le chemin de code mais se sont trompés 3 fois sur des comptes/attributions — **revérifié à la main et corrigé dans `ANOMALIES.csv`** :

- **`mesures_compensatoires` (GéoMCE 150)** : un traçage l'a dite « 0 ligne, couche vide ». **FAUX** — `spatial_layers kind='mesures_compensatoires'` compte **24 lignes** et la fiche parcelle la lit bien (`app.py:4279`→`fiche_blocs3.mesures_compensatoires`). Le manque signalé par AUDIT-2 (« devrait » en fiche parcelle) est désormais **comblé** (SOURCES-FIX-1). Anomalie retirée.
- **`grid_capacity`/S3REnR** : signalé « donnée servie sans source ». En réalité c'est un **STUB** (24 postes, `capa_dispo_mw=0` fabriqué, geom NULL) qui **s'auto-supprime** (`return None` si aucune capacité positive ni géométrie) → **rien n'est servi aujourd'hui**. Reclassé cosmétique (fuite latente si un jour capa>0 sans source).
- **filtre EDF cat.2** : signalé « lit la source retirée 49 ». En réalité les lignes HTA/HTB viennent de la source connectée **93 / BD TOPO** ; le `source_motif='EDF%'` matche par nom l'id 49 **qui n'a aucune ligne** → attribution morte, impact nul. Reclassé cosmétique.

---

## Détail par catégorie (voir `ANOMALIES.csv` pour les 99 lignes)

- **cat.1 — hors liste (22)** : appels externes/constantes légitimes (hypothèses faisabilité, 892 €/m² CGI, annuaires mairies/EPCI/gestionnaires, défisc/acronymes en config) ; méta interne (qualité commune) ; fonds ortho historiques 1950→2023 sans ligne dédiée (couverts par le seul hub 14) ; couche SAR = proxy potentiel foncier ; filtre `flair` (aucune ligne « FLAIR » — la donnée est BD ORTHO 61).
- **cat.2 — source retirée lue (3)** : toutes **inertes** — mention « EDF SEI » dans un bloc export mort (`reseaux.py`, non rendu), filtre EDF (motif matchant l'id 49 vide), filtre `potentiel_foncier_region` appuyé sur une source `alias` (9) plutôt que connectée. Aucune donnée retirée réellement affichée.
- **cat.3 — mauvais branchement (10)** : MVT (36 vs 4), piscine liste (`parcel_equipements` 8 299 FLAIR seul) vs fiche/agg (`piscines` 12 576 FLAIR∪CoSIA), « ce qui bloque » (Comparer `contrainte_majeure` vs Risques `contraintes_parcelle`), délai d'instruction (deux points de lecture Sitadel), DVF baromètre vs médiane (documenté), pré-dossier vs dossier.
- **cat.4 — mauvaise étiquette (23)** : le gros du lot — dates d'ingestion affichées comme millésime (Risques « 50 pas · 2026-09-13 » alors que cadastre 1877/2012), millésimes/noms de source **codés en dur au front** (`ProprietaireHistorique.tsx` « 2019–2025 » alors que base 2019→2024 ; `leBien.tsx` « BD TOPO » ; CADASTRE_MILLESIME « Etalab 2026-06 » du Copilote), deux magasins de millésime admin, `/sources` sans `composer`, pieds export figés (financier, RNB/BAN PLUS, taxe).
- **cat.5 — couverture (14)** : `kind='mvt'`/`ocs_ge`/`potentiel_foncier` en base non dessinés par une couche ; blocs export morts (7 sections + pipeline `flash/`) ; endpoints servis non rendus (`prix_ancien`, `marche_synthese`, `radar_bien`, `/modules/prospection-solaire`). **Nuance importante** : les « 11 sources affichées non lues » du dashboard sont un artefact du squelette (limité au registre `DONNEES`) — la plupart (Forêts ONF, érosion, Cartofriches, BD CARTO, EDF HTA, SCAN50/EduGéo) sont bien servies **en couche carte ou via la cascade runtime**, hors du registre `DONNEES` (recoupé AUDIT-2). Aucune source affichée n'est confirmée morte de fait.
- **cat.6 — appel externe à l'exécution (27)** : WMS/WMTS IGN Géoplateforme (exposition 60 s, hauteur-LiDAR 90 s, profil alti 20 s, ortho/courbes/EnR 15 s, isochrone 30 s, nature-toiture 60 s), Street View Google (iframe, gaté sur clé), Copilote `web_search` Anthropic (45 s, contenu marqué « web », hors data_sources), routage/formulation haiku (25 s, ne servent aucune donnée), Brevo/SMTP (15 s, dry-run), Merci Facteur (envoi courrier), contrôle CERFA service-public (6 s). **Tous** ont un repli nommé ; le seul contenu servi hors liste est la réponse `web_search` du Copilote (honnêtement étiquetée, refus si 0 citation).

---

## Lot C — vérification à l'écran (3 témoins)

Témoins : `97411000EM0174` (Saint-Denis), `97415000AB0134` (Saint-Paul), `97411000BZ1065` (Saint-Denis).
⚠ **Coquille du mandat** : le 3ᵉ IDU annoncé `97410000BZ1065` n'existe pas en base (commune 97410 = Saint-Benoît) ; la parcelle réelle des audits précédents est `97411000BZ1065` (Saint-Denis), utilisée ici.

**40 captures PNG** dans `captures/` : T1 EM0174 (12 sections de fiche + commune + **les 16 outils**), T2 AB0134 (5 fiche + commune), T3 BZ1065 (5 fiche + commune). 31 consommateurs distincts recoupés (10 sections fiche + 16 outils + 5 cartes commune) face à `BRANCHEMENT.csv`.

**Résultat : concordance quasi totale.** Toutes les sources affichées à l'écran (BD TOPO/LiDAR/CoSIA, RGE ALTI, GPU/PLU API Carto, DEAL PPR, DVF Etalab, Arcep, PVGIS SARAH3, DGFiP PM/DFI/SIRENE/BODACC, Filosofi/RPLS/RP IRIS, DELTA taxe + 892 €/m² CGI, SITADEL, INPI RNE) correspondent aux `source_ids` de `BRANCHEMENT.csv`.

**1 seul écart écran↔BRANCHEMENT** : fiche §Risques (T1 EM0174 **et** T2 AB0134), la « friche recensée » est sourcée à l'écran **« Cartofriches (AGORAH 2025) »**, or le catalogue id 35 = **« Cartofriches (Cerema) »**, provider Cerema/DGALN, `source_millesime` **VIDE**. Le millésime « AGORAH 2025 » est un littéral (`fiche_blocs3.py:32`) et l'opérateur (AGORAH) est cité au lieu du producteur (Cerema). → ajouté en cat.4 cosmétique (ANOMALIES.csv).

**Points de forme conformes** : le badge commune « Habitants » affiche « INSEE » abrégé (le pied §Population précise bien « pop. légale INSEE · 31/12/2024 · via Sudocuh » = 62:sudocuh) ; 6 outils sont des écrans « landing » (Scan patrimoine, Assemblage, Étude de zone, Remonter le temps, Blocs fonciers, Faisabilité) dont la mention de source n'apparaît qu'après saisie — marqués `na`. Détail : `captures/lotc_verif.tsv`.

---

## Annexe — reproductibilité

- Squelette : `scripts/_sources3_backbone.py` → `/tmp/backbone.tsv` (286 données résolues aux sources).
- Statuts catalogue : `SELECT status,count(*) FROM data_sources GROUP BY status;` (128 = 96 connecte + 14 partenariat_requis + 6 alias + 5 retiree + 4 hub + 2 manuel + 1 interne ; 123 actives).
- Comptes exacts : `count(*)` par table de `RESERVOIR_TABLES` ; `SELECT kind,count(*) FROM spatial_layers GROUP BY kind;`
- Preuves de divergence : `ST_Equals` SAR↔potentiel_foncier (2 453/2 453) ; `score_labuse` run_labels (seul q_v15 non-dry-run) ; `mvt` 3 085 vs `georisque_alea` 1 093 ; deux magasins millésime (`/tmp/dashboard_divergences_cat4.txt`, 66/129).
