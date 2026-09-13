# REPARATIONS-1 lot 3 — Champs manquants : champ par champ, utile ou inutile (écrit)

10 sources « PARTIELLE — champs manquants ». Les fiches d'audit disaient « champs non pris : non vérifié » : l'instruction a SONDÉ les endpoints producteurs (ODS Région, WFS Géoplateforme, WFS Carmen DEAL) et comparé au schéma en base. Un champ « utile » non ingéré ici garde son rang (REPARATIONS.md §E) — rien n'est sauté, tout est écrit.

## 7 — Parc National de La Réunion (INPN) (`parc_national_inpn`)
- **decret (références des arrêtés délimitant cœur/aire d'adhésion)** — UTILE : Donne la référence réglementaire opposable au « i » de la couche parc_national et au PDF (cœur = inconstructible) · faisabilité : session · geste : Même endpoint ODS data.regionreunion.com/pnrun_2021 (champ `decret` vérifié présent) — l'ajouter aux attrs des 3 objets spatial_layers kind=parc_national
- **surface / surf_ha** — INUTILE (écrit tel quel) : Recalculable par ST_Area sur la géométrie conservée (geom_2975), aucun apport

## 10 — RPG — déclarations agricoles (IGN/ASP) (`rpg_proxy_ign`)
- **année de campagne (RPG.LATEST non pinné)** — UTILE : Le « i » ne peut pas dater la déclaration PAC servie — provenance incomplète relevée par la fiche · faisabilité : session · geste : Basculer du typename RPG.LATEST vers le typename versionné (RPG.<année>:parcelles_graphiques) sur data.geopf.fr/wfs/ows et graver l'année dans attrs.src + millésime
- **id_parcel** — INUTILE (écrit tel quel) : Identifiant technique PAC ; couche repurgée à chaque one-shot, aucun usage client
- **surf_parc (surface déclarée)** — INUTILE (écrit tel quel) : Recalculable via la géométrie conservée ; la surface graphique fait foi pour la carte
- **culture_d1 / culture_d2 (cultures dérobées)** — INUTILE (écrit tel quel) : Quasi vides à La Réunion (canne dominante), aucun impact foncier
- **cat_cult_p (catégorie de culture principale)** — INUTILE (écrit tel quel) : Redondant avec code_group déjà ingéré (attrs) — la légende canne/CSA est déjà servie

## 13 — DEAL Réunion (WMS/WFS) (`deal_wms_wfs`)
- **couche ms:ENS (zonage ENS départemental)** — UTILE : C'est la couche que la fiche 25 croit « introuvable en open data » — droit de préemption ENS départemental sur la fiche parcelle (Dispositifs/Pièges) · faisabilité : session · geste : WFS Carmen DEAL_REUNION_2020 répond (capabilities vérifiées ce jour malgré la sentinelle « injoignable ») : GetFeature typename=ms:ENS → spatial_layers, en remplacement/complément du proxy INPN kind=ens
- **couche ms:L111_ZONE (amendement Dupont L111-6/8)** — UTILE : Inconstructibilité le long des grands axes hors agglomération — manque aux Pièges/Règles de la fiche parcelle · faisabilité : session · geste : GetFeature ms:L111_ZONE sur le même WFS Carmen → spatial_layers + cascade pièges
- **couche ms:BATI_INSAL_RUN (bâti insalubre)** — UTILE : Signal renouvellement urbain/RHI pour Densifier et le Scan — vérifier licence/RGPD avant tout service client · faisabilité : session · geste : GetFeature ms:BATI_INSAL_RUN, usage interne de priorisation d'abord (règle d'archi #2)
- **couche ms:Tache_urbaine_2017** — UTILE : Référence extension/densification du SAR pour l'Étude de zone (zone de demain) · faisabilité : session · geste : GetFeature ms:Tache_urbaine_2017 → spatial_layers
- **couche ms:DIGUES_974 (ouvrages de protection)** — UTILE : Nuance l'aléa inondation servi (parcelle derrière digue) dans la fiche Pièges · faisabilité : session · geste : GetFeature ms:DIGUES_974 → spatial_layers, affichage à côté de georisque_alea
- **couches ALEA_*, ZNIEFF, ZH_*, APB, BASOL_974, UNESCO, Limite_ha_50_pas_geo** — INUTILE (écrit tel quel) : Doublons de couches déjà servies par d'autres sources (georisque_alea, znieff, zone_humide, ens, sol_pollue, cinquante_pas, parc_national)
- **couches CUCS / ZFU / ZRU_ZUS** — INUTILE (écrit tel quel) : Zonages politique de la ville abrogés, remplacés par les QPV génération 2024 déjà servis

## 22 — IGN BD CARTO V5 — occupation du sol (`bd_carto_ocs`)
- **cleabs (identifiant IGN)** — INUTILE (écrit tel quel) : Identifiant technique sans usage ; le producteur ne publie que cleabs+nature (vérifié WFS ce jour) et nature est déjà ingéré
- **couverture/usage OCS GE (codes CS/US millésimés)** — UTILE : Remplacer le proxy grossier (1 643 objets, légende approximative « Sable, gravier » classée artificialisé) par l'OCS GE officielle — artificialisation/ZAN dans l'Étude de zone · faisabilité : mandat · geste : Produit distinct (candidate lot 5 déjà identifiée) : téléchargement OCS GE 974 sur geoservices.ign.fr/ocsge, volumétrie et modèle CS/US à part — pas un complément de champ sur cette couche

## 25 — INPN / patrinat — espaces protégés (`inpn_espaces_proteges`)
- **id_mnhn + url_fiche (fiche INPN du site)** — UTILE : Lien « voir la fiche INPN » dans le « i » de la couche ens et la fiche parcelle — provenance vérifiable en 1 clic · faisabilité : session · geste : Mêmes typenames patrinat_* sur data.geopf.fr/wfs/ows (champs vérifiés présents : id_mnhn, url_fiche) — ajouter aux attrs dans ingest_espaces_proteges (layers_ingest.py:989)
- **date_crea / acte_deb / acte_fin (dates de l'acte de protection)** — UTILE : Date la protection dans le « i » et le PDF — le millésime producteur est aujourd'hui « non vérifié » · faisabilité : session · geste : Mêmes appels WFS, ajouter date_crea aux attrs de chaque objet ens
- **gest_site / operateur (gestionnaire)** — INUTILE (écrit tel quel) : Sans effet sur le droit du sol, aucun écran ne l'attend (souvent NULL en 974)
- **surf_off / area_sig** — INUTILE (écrit tel quel) : Surface recalculable via la géométrie conservée
- **precision / src_geom / src_annee / modif_* (métadonnées de saisie)** — INUTILE (écrit tel quel) : Métadonnées internes patrinat sans usage client

## 31 — INPI RNE (dirigeants) (`inpi_rne`)
- **montant du capital social** — UTILE : Jauge de surface financière des holdings dans Scan patrimoine (prioriser les porteurs solides) · faisabilité : session · geste : Déjà dans le payload /api/companies/{siren} rapatrié à chaque synchro — colonne à poser (table pm_entreprises ou attrs), signal INTERNE (règle d'archi #2)
- **radiation / cessation de l'entreprise** — UTILE : Éviter de prioriser des sociétés radiées dans le Scan (le booléen actif n'existe qu'au niveau dirigeant) · faisabilité : session · geste : Même payload companies (bloc formality/radiation) — flag au niveau entreprise
- **bénéficiaires effectifs** — UTILE : Détention réelle des montages gigognes (au-delà de pm_dirigeant_gigogne) pour Scan patrimoine · faisabilité : producteur · geste : Accès restreint depuis 2023 (art. L. 561-46 CMF) — nécessite une habilitation, pas d'open data
- **comptes annuels (bilans, chiffre d'affaires)** — UTILE : Santé financière d'un porteur/promoteur dans Scan patrimoine · faisabilité : mandat · geste : Autre canal INPI (attachments/FTP comptes annuels), parsing XBRL/PDF, confidentialité des comptes à respecter — chantier à part
- **forme juridique / date d'immatriculation / adresse du siège / activités** — INUTILE (écrit tel quel) : Doublon SIRENE déjà ingéré (158 515 actifs) ; formeJuridique déjà dans raw

## 40 — NPNRU (DEAL Réunion / ANCT) (`npnru`)
- **champs WFS restants** — INUTILE (écrit tel quel) : Le WFS Carmen NPNRU ne publie que Code_qp/Nom_qp/Commune_qp (DescribeFeatureType vérifié ce jour) — tous ingérés dans anru_quartiers + attrs, plus l'intérêt national/régional (liste ANCT)
- **avancement des conventions ANRU (dates de signature, montants, opérations par quartier)** — UTILE : Qualifier le calendrier réel du renouvellement dans la fiche Dispositifs et l'Étude de zone (un périmètre sans les échéances dit peu) · faisabilité : mandat · geste : Non publié par le WFS DEAL ni la liste ANCT — open data ANRU sur data.gouv (conventions/opérations NPNRU), nouvelle table + jointure code_qp_2015 déjà en attrs
- **millésime du jeu WFS** — UTILE : La fiche dit « millésime à re-sonder » — le « i » doit dater la génération servie (QP 2024) · faisabilité : session · geste : Consigner le millésime au seed/registre lors de la prochaine passe one_shot (aucun nouveau champ producteur requis)

## 42 — PLH des 5 EPCI (extraction documentaire) (`plh_epci`)
- **déclinaison communale des objectifs sociaux (CINOR partielle, CIREST absente)** — UTILE : Fiche commune « Programme local » : objectif social par commune, pas seulement par EPCI · faisabilité : producteur · geste : Colonnes vides au CDHH (noté dans plh_epci.detail) — seuls les EPCI/DEAL peuvent fournir la territorialisation
- **volet foncier du PLH (gisements et sites fléchés)** — UTILE : Croiser avec Densifier/potentiel foncier : des parcelles nommément fléchées par un PLH sont un signal fort · faisabilité : mandat · geste : Extraction documentaire des 5 PLH intégraux (dépôt manuel, chaque chiffre référencé doc+page dans plh_epci.refs comme aujourd'hui)
- **typologies fines par année (LLTS/LLS/PLS/accession, calendrier d'actions)** — UTILE : Étude de zone « zone de demain » : qui construit quoi et quand, au-delà de l'objectif logements/an · faisabilité : mandat · geste : Même extraction documentaire — le detail jsonb en porte déjà une partie hétérogène, à normaliser

## 62 — Sudocuh (procédures d'urbanisme) (`sudocuh`)
- **dates intermédiaires de la procédure en cours (débat PADD, arrêt du projet, enquête publique)** — UTILE : Outil Procédure & changement : estimer l'horizon d'approbation d'une révision (aujourd'hui seulement prescription_proc/approbation_opp) · faisabilité : session · geste : Même XLSX data.gouv (r/61541a0f-…) déjà en dépôt manuel — colonnes supplémentaires de la feuille procédures vers sudocuh_procedures (24 lignes)
- **feuille SCOT** — INUTILE (écrit tel quel) : Aucun SCOT à La Réunion — le SAR tient lieu de cadre supra-communal
- **feuilles POS / cartes communales** — INUTILE (écrit tel quel) : 974 = 23 PLU + 1 RNU en base (vérifié) : aucun POS ni carte communale en vigueur
- **population / superficie communales** — INUTILE (écrit tel quel) : Doublon du référentiel INSEE déjà servi
- **autorité compétente (commune/EPCI)** — INUTILE (écrit tel quel) : Déjà portée par etat_detaille (« Compétence commune ») ingéré

## 130 — Loyers DHUP — carte des loyers (annonces) (`loyers_dhup`)
- **typologies fines appartement T1-T2 vs T3+** — UTILE : Fiche commune Loyers + écart demandé/estimé du Radar par typologie (l'extrait embarqué n'a que appartement/maison globaux) · faisabilité : session · geste : Même CSV data.gouv carte des loyers 2025 (4 séries publiées) — régénérer l'extrait 974 data/carte_loyers_reunion_2025.json, loyers.py suit
- **nbobs_mail / maille de repli départementale** — INUTILE (écrit tel quel) : La granularité d'estimation (type_prediction) et nb_obs sont déjà conservées et servies en libellé de fiabilité
- **id_zone / EPCI / DEP / REG** — INUTILE (écrit tel quel) : Jointure géo déjà assurée par le code INSEE conservé

**Total : 21 champs utiles · 19 inutiles (chacun avec sa raison).** Trouvaille transverse : le WFS Carmen DEAL répond (la sentinelle le dit « injoignable ») et porte le zonage ENS départemental que la fiche 25 croyait introuvable en open data.