"""CIRCUIT-2 lot 1.1 — LE REGISTRE DES DONNÉES (ex-registre des chiffres, CIRCUIT-1 1.1) :
TOUT ce qui s'affiche et vient d'une source est déclaré ICI, une fois — pas seulement les
nombres. Chaque donnée porte son `type` (nombre · classe · texte · liste · geometrie · couche),
les champs de CIRCUIT-1 (définition, moteur ou passe-plat, réservoirs, portée, version), et
selon le type : le DOMAINE d'une classe (valeurs possibles + leur source), la TABLE ou le
TUILAGE d'une couche/géométrie et sa FABRICATION (`build-mvt`, `geom_simple`, vue, requête,
WMTS distant).

Portées : `run` (ne change qu'à la bascule) · `live` (change à l'injection) · `projet`
(saisie client, pas de réservoir, tampon « saisi par le client le … » — 0-bis).
États (règle 4 du mandat) : une donnée non numérique est `servie`, « non déterminée » (la
source ne dit pas) ou « non calculée » (la chaîne a échoué) — l'état voyage dans la Valeur,
jamais un échec déguisé en absence.

`en_attente` : donnée DÉCLARÉE dont le réservoir ou l'affichage arrive par un chantier nommé
(1.8 — maquettes d'exports, réglementaires CIRCUIT-3) ; elle n'est servie par AUCUN robinet
tant que le champ est posé (verrouillé par test), et ce n'est PAS une exception au registre :
rien ne s'affiche hors registre.

Le code est LA vérité ; la base (`registre_*`, cf. sync.py) n'en est que le miroir servi à la
page Circuit et à la sonde. Une donnée absente d'ici n'a pas le droit d'exister à l'écran
(garde de couverture : tests/test_registre.py, tests/test_circuit2_lot1.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

VERSION_DEF = "2026-09-05"      # date de la définition courante (bump à chaque changement de sens)

TYPES = ("nombre", "classe", "texte", "liste", "geometrie", "couche")

#: type dérivé de l'unité quand la déclaration ne le pose pas explicitement (`type="auto"`)
_TYPE_PAR_UNITE = {"classe": "classe", "verdict": "texte", "tranche": "classe", "date": "texte"}


@dataclass(frozen=True)
class Donnee:
    libelle: str
    unite: str          # % · € · €/m² · m² · logements · classe · verdict · tranche · date · nombre · m
    niveau: str         # parcelle · commune · zone · proprietaire · annonce · global
    definition: str     # une phrase, dénominateur et fenêtre compris
    moteur: str | None  # id de moteurs.csv, None si sql_propre/passe_plat/constante/front
    calcul: str         # moteur · sql_propre · passe_plat · constante · front (front → à rapatrier)
    fonction: str       # référence du producteur (fichier:fonction)
    reservoirs: tuple[str, ...] = field(default_factory=tuple)   # ids reservoirs.csv ; vide = interne
    portee: str = "live"        # run | live | projet
    version_def: str = VERSION_DEF
    type: str = "auto"          # ∈ TYPES ; "auto" → dérivé de l'unité (_TYPE_PAR_UNITE)
    domaine: tuple[str, ...] | None = None    # classe : les valeurs possibles
    domaine_source: str | None = None         # classe : la source du domaine (GPU, arrêté, PPR…)
    table: str | None = None    # couche/géométrie/passe-plat : la table (ou le tuilage) lue
    fabrication: str | None = None   # couche : build-mvt · geom_simple · vue · requete · wmts_distant
    en_attente: str | None = None    # déclarée, pas encore servie — le chantier qui l'apporte


#: rétro-compatibilité CIRCUIT-1 (alias conservés — 1.1 : « ne rien casser »)
Chiffre = Donnee
C = Donnee

DONNEES: dict[str, Donnee] = {
 "tier_opportunite": C("Verdict · Classement servi", "classe", "parcelle",
    "tier du run servi (brûlante→froide), reconstruit à la bascule",
    moteur="scoring_p_v2", calcul="moteur", fonction="src/labuse/cli.py (build-mvt) ; parcel_flags",
    reservoirs=("bd_topo", "cosia", "dvf", "filosofi_carreaux", "sitadel",), portee="run",
    domaine=("brulante", "chaude", "a_creuser", "reserve_fonciere", "ecartee"),
    domaine_source="tiers du scoring P v2 (scoring/p_v2/statuts.py)"),
 "zone_plu_famille": C("Zonage PLU (par type)", "classe", "parcelle",
    "famille (U/AU/A/N) de la zone DOMINANTE par surface de la parcelle (drapeau a_cheval, "
    "zone_parts servies) — moteur zone_servie (ZONE-1) ; ≠ zonage_commune (parts d'une commune)",
    moteur="zone_servie", calcul="moteur",
    fonction="src/labuse/faisabilite/zone_servie.py:zone_dominante",
    reservoirs=("gpu_plu_api_carto",), portee="live",
    domaine=("U", "AU", "A", "N"),
    domaine_source="familles de zones du GPU (Géoportail de l'urbanisme)"),
 "tranche_prix_vefa": C("Prix du logement neuf (VEFA)", "tranche", "commune",
    "tranche de prix médian VEFA 36 mois glissants, ≥10 ventes avec prix sinon hachure",
    moteur="marche_service", calcul="moteur", fonction="src/labuse/ingestion/vefa_neuf.py:118",
    reservoirs=("dvf", "sitadel",), portee="live",
    domaine=("moins_4000", "4000_4500", "4500_5000", "5000_5500", "5500_plus", "sous_seuil"),
    domaine_source="tranches TRANCHE_LIBELLE (ingestion/vefa_neuf.py)"),
 "classe_residuel": C("Densifier l'existant", "classe", "parcelle",
    "classe de sous-densité du run résiduel servi, lue SOUS la garde de zone dominante "
    "(bloc au sol du moteur potentiel — EXPORTS-1 lot 3)",
    moteur="potentiel", calcul="moteur",
    fonction="src/labuse/faisabilite/potentiel.py:bloc_potentiel (au_sol, garde zone_servie)",
    reservoirs=("bd_topo", "cadastre_api_carto", "cosia",), portee="run",
    domaine=("sous_densite", "dense"), domaine_source="parcel_residuel.sous_densite (seuil des hypothèses de bilan)"),
 "surface_parcelle_m2": C("Surface", "m²", "parcelle",
    "surface cadastrale parcels.surface_m2",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/scoreur.py:scoreur_adresse",
    reservoirs=("cadastre_api_carto",), portee="live", table="parcels.surface_m2"),
 # GEOPF-3 couche 7 (réconcilié RETOUCHES-1 lot A) — le lieu-dit BD NYME servi sous l'adresse de la
 # fiche (« Secteur : … ») : c'est le chiffre qui rend le réservoir `bd_nyme` non-muet (G6/V1d).
 "secteur_lieu_dit": C("Secteur (lieu-dit)", "texte", "parcelle",
    "toponyme du lieu-dit BD NYME le plus proche du centre de la parcelle (rayon borné 600 m ; None "
    "au-delà) — servi sous l'adresse de la fiche comme « Secteur : … »",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/app.py:_secteur_lieudit",
    reservoirs=("bd_nyme",), portee="live", type="texte",
    table="lieux_dits (toponyme le plus proche par idu)"),
 # GABARIT-1 — outil « Gabarit réglementaire » (moteur pur, sourcé). Servi sur fixtures
 # (démo CDC §9) ; réel per-parcelle dès que la classification des limites arrive (GABARIT-2).
 "gabarit_implantation_m2": C("Zone d'implantation réglementaire", "m²", "parcelle",
    "surface de la zone où une construction peut s'implanter = parcelle − reculs (voie/"
    "séparatives) − exclusions réglementaires (PPR rouge). Calcul géospatial pur, jamais "
    "estimé. Servi per-parcelle (GABARIT-2 : classification des limites voie/séparative par "
    "arête = adjacence cadastre + BD TOPO, mesurée 0 faux/70).",
    moteur="gabarit", calcul="moteur",
    fonction="src/labuse/gabarit/engine.py:compute_gabarit",
    reservoirs=("cadastre_api_carto", "gpu_plu_api_carto",), portee="live"),
 "gabarit_emprise_plafond_m2": C("Plafond d'emprise", "m²", "parcelle",
    "plafond réglementaire d'emprise au sol = surface parcelle × CES / 100. Calculé À PART "
    "de la zone d'implantation (jamais min()).",
    moteur="gabarit", calcul="moteur",
    fonction="src/labuse/gabarit/engine.py:compute_gabarit",
    reservoirs=("cadastre_api_carto", "gpu_plu_api_carto",), portee="live"),
 "gabarit_couverture_verdict": C("Couverture réglementaire", "verdict", "parcelle",
    "nombre de familles réglementaires vérifiées (reculs, hauteur, emprise, risques) — "
    "au plus 4 ; ne compte ni les segments ni les articles PLU.",
    moteur="gabarit", calcul="moteur",
    fonction="src/labuse/gabarit/engine.py:compute_gabarit",
    reservoirs=("gpu_plu_api_carto", "deal_ppr",), portee="live",
    domaine=("0", "1", "2", "3", "4"), domaine_source="4 familles de couverture (CDC §6)"),
 "gabarit_hauteur_m": C("Hauteur réglementaire (gabarit)", "m", "parcelle",
    "hauteur réglementaire servie au gabarit — la valeur PLU vit au §4 Urbanisme, le tiroir la "
    "CITE (jamais redéclarée). « Non chiffrée » quand la règle est en prospect (L ≥ H) : forme "
    "validée mais non numérique (non intégrée), 2D servie, 3D indisponible.",
    moteur="gabarit", calcul="moteur",
    fonction="src/labuse/gabarit/engine.py:compute_gabarit",
    reservoirs=("gpu_plu_api_carto",), portee="live"),
 "gabarit_motif_blocage": C("Gabarit — motif de calcul incomplet", "texte", "parcelle",
    "motif métier quand le gabarit n'est pas calculable (limite non qualifiée, voie privée sans "
    "recul réglé, zone non calibrée, ≥ 2 zones constructibles…). Silence sourcé, jamais estimatif.",
    moteur="gabarit", calcul="moteur",
    fonction="src/labuse/gabarit/builder.py:build_gabarit_input", portee="live", type="texte"),
 "gabarit_plan_2d": C("Gabarit — plan 2D (zone d'implantation)", "texte", "parcelle",
    "figure 2D du gabarit : contour cadastral, zone d'implantation, bandes de retrait et "
    "exclusions (PPR rouge). Schéma des géométries servies (SVG), pas une carte ni un plan de "
    "masse. Déclaré comme figure de la ligne « zone d'implantation ».",
    moteur="gabarit", calcul="moteur",
    fonction="src/labuse/gabarit/plan_svg.py:gabarit_svg",
    reservoirs=("cadastre_api_carto", "gpu_plu_api_carto",), portee="live", type="texte"),
 "capacite_logements": C("Capacité (logements)", "logements", "parcelle",
    "logements estimés du scénario table rase (après plafond de densité et stationnement) — "
    "bloc potentiel (EXPORTS-1 lot 3)",
    moteur="potentiel", calcul="moteur",
    fonction="src/labuse/faisabilite/potentiel.py:bloc_potentiel (table_rase.logements)",
    reservoirs=("bd_topo", "cosia", "gpu_plu_api_carto",), portee="run"),
 "sdp_residuelle_m2": C("SDP résiduelle", "m²", "parcelle",
    "max(0, SDP_max − SDP_existante) du run servi, sous garde de lecture zone dominante "
    "(A/N → 0 avec cause dite — ZONE-1)",
    moteur="potentiel", calcul="moteur",
    fonction="src/labuse/faisabilite/potentiel.py:bloc_potentiel (au_sol.sdp_residuelle_m2)",
    reservoirs=("cosia", "gpu_plu_api_carto",), portee="run"),
 "potentiel_verdict": C("Potentiel (verdict)", "verdict", "parcelle",
    "phrase composée du bloc « au sol / en hauteur / table rase » (moteur potentiel) — "
    "jamais un bloc creux (section omise si rien d'évaluable)",
    moteur="potentiel", calcul="moteur",
    fonction="src/labuse/faisabilite/potentiel.py:bloc_potentiel (verdict)",
    reservoirs=("bd_topo", "cosia", "gpu_plu_api_carto",), portee="run"),
 "charge_fonciere_eur": C("Charge foncière", "€", "parcelle",
    "prix de sortie × SDP − coûts − marge (bilan à rebours)",
    moteur="bilan_promoteur", calcul="moteur", fonction="src/labuse/faisabilite/bilan.py",
    reservoirs=("cadastre_api_carto", "dvf",), portee="live"),
 "taxe_amenagement_eur": C("Taxe d'aménagement", "€", "parcelle",
    "calcul ligne-à-ligne, taux communal SAISI obligatoire, jamais un défaut",
    moteur="taxe_amenagement", calcul="moteur", fonction="src/labuse/taxe_amenagement.py",
    # CIRCUIT-6 lot 0 — l'arête MANQUAIT : les taux communaux/départementaux servis par l'outil
    # viennent de la source « Taxe d'aménagement — taux communaux » (taxe_amenagement_taux) ;
    # reservoirs=() faisait vivre l'outil Taxe hors graphe (SOURCES-AUDIT : SERVIE HORS REGISTRE).
    reservoirs=("taxe_amenagement",), portee="live"),
 # RECETTE-8 W2 — sur la fiche/le Dossier, la taxe d'aménagement ne porte AUCUN montant : elle se
 # paie sur la surface de plancher créée par un PROJET (art. L331 c. urb.), or aucun projet n'est
 # saisi ici. On sert donc UNIQUEMENT le taux communal public (daté) et la phrase disant sur quoi
 # elle se calculera ; le montant en euros n'est chiffré qu'au Financier, sur la SDP du projet.
 "taxe_amenagement_estimee_eur": C("Taxe d'aménagement — taux communal (référence)", "%", "parcelle",
    "référence de taxe d'aménagement servie sur la fiche/le Dossier : le TAUX communal public (daté) "
    "et la part départementale de droit (plafond 2,5 %) — SANS montant en euros, car la taxe porte "
    "sur la surface de plancher CRÉÉE par un projet (art. L331 c. urb.) et aucun projet n'est saisi "
    "à ce stade (RECETTE-8 W1/W2 : avant, elle imprimait « 22 469 € pour 458 m² de table rase », un "
    "scénario que personne n'avait choisi). Le montant chiffré est au Financier, sur la SDP du projet. "
    "Taux communal PUBLIC si connu, sinon « non renseigné » (jamais inventé)",
    moteur="taxe_amenagement", calcul="moteur",
    fonction="src/labuse/api/app.py:_taxe_amenagement_block (taxe_amenagement.calculer, surface=0)",
    # CIRCUIT-6 lot 0 — même arête que taxe_amenagement_eur : le TAUX servi vient de la source
    # « Taxe d'aménagement — taux communaux » (fusion RECETTE-8 W2 × CIRCUIT-6 : la définition
    # de main, l'arête du graphe en plus — reservoirs=() la laissait hors registre).
    reservoirs=("taxe_amenagement",), portee="live"),
 # CIRCUIT-6 lot 0 — le rappel RTAA DOM (exigences de conception, vérifié Légifrance) était servi
 # dans la Faisabilité SANS chiffre au registre : la source rtaa_dom (43) n'alimentait rien.
 "rtaa_exigences": C("Rappel RTAA DOM (exigences de conception)", "liste", "parcelle",
    "exigences réglementaires de conception DOM (aération, protection solaire, eau chaude solaire) "
    "servies en rappel dans la Faisabilité — règles portées par config/rtaa_dom.yaml, vérifiées "
    "sur Légifrance, hors scoring",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/modules.py:faisabilite_sens1 (load_yaml_config rtaa_dom)",
    # TESTS-1 lot 1 — un passe-plat SERVI dit ce qu'il lit : ici pas une table SQL mais le
    # fichier de règles versionné (le réservoir rtaa_dom est « porté par le code », tables.py:149).
    table="config/rtaa_dom.yaml",
    reservoirs=("rtaa_dom",), portee="live", type="liste"),
 # FICHE-1 lot 6 — les annonces Radar rattachées à la parcelle (validées), servies dans « Marché
 # et secteur » : date, prix demandé, statut, lien fiche annonce, écart demandé/acté par annonce.
 "radar_annonces_liste": C("Annonces Radar de la parcelle", "liste", "parcelle",
    "annonces Radar VALIDÉES rattachées à la parcelle (date, prix demandé, statut en cours/"
    "retirée/vendue, lien fiche annonce) ; pour une annonce en cours avec mutation DVF, l'écart "
    "prix demandé vs acté (concept ecart_demande_acte_pct, maille parcelle)",
    moteur="marche_pige", calcul="moteur",
    fonction="src/labuse/api/app.py:_radar_annonces_block (pige_biens ⋈ pige_faits + v_parcel_dvf_last)",
    reservoirs=("radar_pige", "dvf",), portee="live", type="liste"),
 "n_vigilances": C("Vigilances", "nombre", "parcelle",
    "compte des couches cascade en SOFT_FLAG/HARD_EXCLUDE",
    moteur="cascade", calcul="moteur",
    fonction="src/labuse/api/anti_fiche.py (motifs RÉDHIBITOIRE/VIGILANCE de la cascade)",
    # CIRCUIT-SOURCES-1 lot 2 — attribution GRANULAIRE : le compte agrège les vigilances de chaque
    # sous-source Géorisques réellement lue (mvt, ICPE, cavités, sites/sols pollués), plus ABF, PPR,
    # ZNIEFF — au lieu de l'agrégat `georisques_api` (qui masquait quelle source touche la fiche).
    reservoirs=("abf_merimee", "deal_ppr", "georisques_mvt", "georisques_icpe",
                "georisques_cavites", "georisques_ssp", "znieff_inpn",), portee="run"),
 # FICHE-1 lot 3 — le DÉTAIL des aléas (nature/niveau/part/réf. PPR), dérivé des mêmes lignes
 # servies que « Pièges et risques » (cascade arbitrée, point de vérité unique M73).
 # SOURCES-1 lot 4 — la divergence SAR (proxy de vocations) servie dans les vigilances de la
 # fiche (warning PASS de la couche cascade sar, doctrine D2 — jamais un malus).
 "sar_divergence": C("Divergence SAR (indication)", "verdict", "parcelle",
    "warning « zone PLU U/AU ∩ vocation naturelle/agricole du proxy de vocations Région » — "
    "indication non opposable (le SAR officiel n'est pas diffusé en vecteur), jamais un malus",
    moteur="cascade", calcul="moteur",
    fonction="src/labuse/cascade/layers/phase1.py:SarLayer",
    reservoirs=("sar_region",), portee="run", type="texte"),
 "aleas_parcelle_liste": C("Aléas de la parcelle", "liste", "parcelle",
    "liste des aléas touchant la parcelle (nature, niveau, part concernée, référence de l'arrêté "
    "PPR pour un aléa réglementaire) — dérivée de la cascade servie, accord garanti avec Pièges et "
    "risques",
    moteur="cascade", calcul="moteur",
    fonction="src/labuse/api/app.py:_aleas_block (lignes servies layer='risques')",
    # CIRCUIT-SOURCES-1 lot 2 — attribution GRANULAIRE : les aléas lus sont le mouvement de terrain
    # (`georisques_mvt`) et l'inondation AZI/TRI (`georisques_azi_tri`), plus l'arrêté PPR (`deal_ppr`)
    # — au lieu de l'agrégat `georisques_api` (depuis le Circuit, on voit désormais la ligne alimentée).
    reservoirs=("deal_ppr", "georisques_mvt", "georisques_azi_tri",), portee="run", type="liste"),
 "n_extraits_plu": C("extraits (règlement)", "nombre", "commune",
    "extraits de règlement servis par commune (corpus)",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:etat_corpus_plu",
    reservoirs=("gpu_plu_api_carto", "sudocuh",), portee="live"),
 "n_communes_rnu": C("au RNU", "nombre", "global",
    "communes au statut rnu du corpus (registre config/rnu_communes.yaml)",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:etat_corpus_plu (n_rnu)",
    reservoirs=("sudocuh",), portee="live"),
 "simulplu_resultat": C("Simuler un changement (parcelles gagnées)", "nombre", "commune",
    "re-verdict cascade sous zonage hypothétique (dryrun)",
    moteur="cascade", calcul="moteur", fonction="src/labuse/api/moteurs.py:56-124",
    reservoirs=("gpu_plu_api_carto",), portee="run"),
 "comparateur_composite": C("Score composite", "nombre", "commune",
    "moyenne pondérée min-max des 6 axes présents, poids réglables",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:composite_communes",
    reservoirs=("cosia", "dvf", "sitadel",), portee="run"),
 "stock_opportunites": C("Stock d'opportunités (brûlantes + chaudes)", "nombre", "commune",
    "count tiers brûlante+chaude au run servi, par insee",
    moteur="scoring_p_v2", calcul="moteur", fonction="src/labuse/api/comparateur.py:47-50",
    reservoirs=("cosia", "dvf", "sitadel",), portee="run"),
 "velocite_delai_median_mois": C("Vélocité admin (délai médian dépôt→autorisation, mois)", "nombre", "commune",
    "percentile_cont(0.5) sur m10_permit_delais famille logements",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:indicateurs_communes (CTE velo)",
    reservoirs=("sitadel",), portee="live"),
 "permis_5a_n": C("Permis de la commune sur 5 ans (SITADEL)", "nombre", "commune",
    "count sitadel_permits de la commune, fenêtre 5 ans, sans rayon (commune entière)",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:indicateurs_communes (CTE permis)",
    reservoirs=("sitadel",), portee="live"),
 "deficit_sru_pts": C("Déficit SRU (objectif − taux LLS, points)", "nombre", "commune",
    "greatest(objectif_pct − taux_lls, 0) depuis commune_contexte_sru",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/comparateur.py:56",
    reservoirs=("sru_dhup",), portee="live",
    table="commune_contexte_sru (objectif_pct, taux_lls)"),
 "pression_zan_ha": C("Pression ZAN (ENAF consommé 2021-2024, ha)", "nombre", "commune",
    "conso_2021_2024_m2 / 10000",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/comparateur.py:57",
    reservoirs=("enaf_cerema",), portee="live", table="commune_conso_enaf.conso_2021_2024_m2"),
 "prix_neuf_vefa_acte_eur_m2": C("Prix du neuf — VEFA à l'acte (€/m²)", "€/m²", "commune",
    "médiane VEFA déclarée à l'acte (neuf_vefa_commune, live, 36 mois) — USAGE RÉSERVÉ : le "
    "scoring (score_e) lit CET id ; affiché comparateur/communes/fiche commune sous libellé VEFA "
    "(scission 0-bis : ≠ prix_neuf_observe_eur_m2, jamais l'un sous le libellé de l'autre)",
    moteur="marche_service", calcul="moteur",
    fonction="src/labuse/ingestion/dvf_marche.py:neuf_vefa_commune (via marche_service, profil neuf_vefa)",
    reservoirs=("dvf",), portee="live"),
 "prix_neuf_observe_eur_m2": C("Prix du neuf — observé (€/m²)", "€/m²", "commune",
    "neuf observé ≤ 3 ans après achèvement (resolve_prix_neuf_marche : bassin sourcé > secteur > "
    "commune > repli île) — USAGE RÉSERVÉ : bilan et exports (fiche, PDF) lisent CET id "
    "(arbitrage Q3 ; scission 0-bis)",
    moteur="marche_service", calcul="moteur",
    fonction="src/labuse/ingestion/dvf_prix_neuf.py:resolve_prix_neuf_marche "
             "(servi par faisabilite/bilan.py:resolve_prix_sortie_servi)",
    reservoirs=("dvf",), portee="live"),
 "prix_ancien_median_eur_m2": C("€/m² ancien", "€/m²", "commune",
    "médiane DVF ventes strictes, filtre de retenue du baromètre",
    moteur="marche_service", calcul="moteur", fonction="src/labuse/api/moteurs.py:prix_ancien_communes (partagé PDF baromètre)",
    reservoirs=("dvf",), portee="live"),
 "n_parcelles_pm": C("Parcelles détenues", "nombre", "proprietaire",
    "count parcelle_personne_morale par SIREN (millésime 2025)",
    moteur="proprietaire_historique", calcul="moteur",
    fonction="src/labuse/registre/moteurs/proprietaire.py:compte_parcelles_pm "
             "(délégation — le calcul vit dans api/modules.py:patrimoine, une seule vérité)",
    reservoirs=("dgfip_parcelles_pm",), portee="live"),
 "prod_spec_kwh_kwc": C("Productible", "nombre", "parcelle",
    "productible PVGIS SARAH3 gelé au run du builder (parcel_solar)",
    moteur="solaire", calcul="moteur", fonction="src/labuse/api/modules.py:prospection_solaire",
    # CIRCUIT-5b lot 2 — le module solaire lit AUSSI la toiture LiDAR (toiture_lidar,
    # solaire_toiture.py) et l'ombrage végétal (parcel_vegetation, canopée NDVI×MNH,
    # solaire.py) : lidar_hd_mnh et bd_ortho_irc y sont donc rattachés (lecteurs déclarés).
    reservoirs=("bd_topo", "pvgis", "lidar_hd_mnh", "bd_ortho_irc",), portee="run"),
 "azimut_bati_deg": C("Azimut (Estimé)", "nombre", "parcelle",
    "azimut du bâti principal, Estimé",
    moteur="solaire", calcul="moteur", fonction="src/labuse/ingestion/solaire.py (ST_OrientedEnvelope)",
    reservoirs=("bd_topo",), portee="run"),
 "n_piscines": C("Piscines détectées", "nombre", "commune",
    "count parcel_equipements piscine (BD ORTHO 2025, ~90,7 %)",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:compte_piscines",
    reservoirs=("bd_ortho",), portee="live"),
 "mutations_12m_n": C("Mutations 12 mois", "nombre", "commune",
    "count dvf_mutations sur les 12 derniers mois DE DONNÉES (pas calendaire)",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:mutations_12m",
    reservoirs=("dvf",), portee="live"),
 "acquisitions_pm_n": C("Acquisitions récentes (PM)", "nombre", "commune",
    "diff CONSTAT entre millésimes PM, maille commune",
    moteur="proprietaire_historique", calcul="moteur", fonction="src/labuse/api/app.py:commune_acquisitions_pm",
    reservoirs=("dgfip_parcelles_pm",), portee="live"),
 "permis_12m_n": C("Permis de la commune sur 12 mois", "nombre", "commune",
    "count sitadel_permits de la commune, fenêtre 12 mois, sans rayon (commune entière)",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:compte_permis_commune",
    reservoirs=("sitadel",), portee="live"),
 "point_mort_n": C("Permis au point mort", "nombre", "commune",
    "permis autorisés sans DOC/DAACT dans la fenêtre",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:permis_point_mort",
    reservoirs=("sitadel",), portee="live"),
 "n_densifiables": C("Parcelles densifiables", "nombre", "commune",
    "count parcel_renouvellement au run servi",
    moteur="renouvellement", calcul="moteur", fonction="src/labuse/api/app.py:renouvellement_liste",
    reservoirs=(), portee="run"),
 # OUTILS-FIX-5 L6 — les deux outils neufs (Successions M28, Blocs M29) étaient invisibles du Circuit
 # (aucun robinet). On déclare leurs chiffres pour que leurs sources apparaissent dans /sources/rattachements.
 "n_successions_veille": C("Successions à venir", "nombre", "commune",
    "count parcel_veille_succession (signal Score V : dirigeant PM ≥ 70 ans OU SCI dormante) — "
    "île entière ou commune ; snapshot RNE INPI daté, jamais une succession ouverte",
    moteur="v_score", calcul="moteur", fonction="src/labuse/api/modules.py:successions_liste "
             "(lit le snapshot parcel_veille_succession produit par le moteur Score V)",
    reservoirs=("dgfip_parcelles_pm", "inpi_rne",), portee="live"),
 "n_blocs_pm": C("Blocs fonciers", "nombre", "commune",
    "count parcel_blocs (assiettes contiguës d'un même propriétaire PM, ST_DWithin 0,5 m, ≥ 2 "
    "parcelles) — île entière ou commune ; résiduel agrégé lu de la vue servie",
    moteur="blocs_fonciers", calcul="moteur", fonction="src/labuse/api/modules.py:blocs_liste",
    reservoirs=("dgfip_parcelles_pm",), portee="run"),
 "n_parcelles_bloc": C("Parcelles du bloc", "nombre", "parcelle",
    "nombre de parcelles réunies dans un bloc foncier (parcel_bloc_membres)",
    moteur="blocs_fonciers", calcul="moteur", fonction="src/labuse/api/modules.py:blocs_liste",
    reservoirs=("dgfip_parcelles_pm",), portee="run"),
 "population_zone": C("Habitants (zone)", "nombre", "zone",
    "somme carreaux Filosofi 200 m intersectant l'isochrone",
    moteur="zone", calcul="moteur", fonction="src/labuse/zone.py (population_zone — point Filosofi UNIQUE)",
    reservoirs=("filosofi_carreaux",), portee="live"),
 "n_concurrents_zone": C("Concurrents (NAF)", "nombre", "zone",
    "count sirene_etablissements du NAF choisi dans la zone, chacun avec son temps",
    moteur="zone", calcul="moteur", fonction="src/labuse/zone.py (comptages_zone)",
    reservoirs=("sirene_etablissements",), portee="live"),
 "emplois_fourchette": C("Emplois (fourchette)", "tranche", "zone",
    "somme des tranches d'effectifs SIRENE (jamais un point)",
    moteur="zone", calcul="moteur", fonction="src/labuse/zone.py",
    reservoirs=("sirene_etablissements",), portee="live",
    domaine_source="tranches d'effectifs SIRENE (nomenclature INSEE)"),
 "revenu_approche_eur": C("Revenu (valeur approchée)", "€", "zone",
    "niveau de vie approché N/M carreaux couverts (i_est_200)",
    moteur="zone", calcul="moteur", fonction="src/labuse/zone.py",
    reservoirs=("filosofi_carreaux",), portee="live"),
 "trafic_mja": C("Trafic (MJA)", "nombre", "zone",
    "comptage MJA du tronçon RN le plus proche, millésime porté par tronçon",
    moteur=None, calcul="passe_plat", fonction="src/labuse/zone.py",
    reservoirs=("trafic_rn",), portee="live", table="trafic_rn.tmja"),
 "annonces_actives_n": C("Biens en vente", "nombre", "commune",
    "count pige_biens actifs a_qualifier=false ; n<5 → NULL insuffisant",
    moteur="marche_pige", calcul="moteur", fonction="src/labuse/pige/marche.py:71-91",
    reservoirs=("radar_pige",), portee="live"),
 "prix_demande_median_eur_m2": C("Prix demandé (médiane)", "€/m²", "commune",
    "médiane des prix affichés terrain/bâti, n<5 masqué",
    moteur="marche_pige", calcul="moteur", fonction="src/labuse/pige/marche.py:71-91",
    reservoirs=("radar_pige",), portee="live"),
 "delai_vente_median_j": C("Délai médian", "nombre", "commune",
    "médiane 1re vue → retrait/vente",
    moteur="marche_pige", calcul="moteur", fonction="src/labuse/pige/marche.py",
    reservoirs=("radar_pige",), portee="live"),
 "ecart_demande_acte_pct": C("Écart demandé/acté", "%", "commune",
    "médiane demandé vs médiane DVF actée, servi dès SEUIL_N biens",
    moteur="marche_pige", calcul="moteur", fonction="src/labuse/api/fiche_commune.py:16-58 (comparable, partagé)",
    reservoirs=("dvf", "radar_pige",), portee="live"),
 "rang_tier": C("Rang (dans le tier)", "nombre", "parcelle",
    "rang au sein du tier",
    moteur="scoring_p_v2", calcul="moteur", fonction="src/labuse/api/app.py:3283",
    reservoirs=(), portee="run"),
 "prix_terrain_secteur_eur_m2": C("Terrain nu secteur", "€/m²", "parcelle",
    "médiane DVF rayon adaptatif 500→1500 m, trim 5 %, min 8 ventes, indice fiabilité",
    moteur="sector_price", calcul="moteur", fonction="src/labuse/faisabilite/bilan.py (sector_price)",
    reservoirs=("cadastre_api_carto", "dvf",), portee="live"),
 "prix_sortie_bati_eur_m2": C("Prix de sortie — bâti secteur", "€/m²", "parcelle",
    "sector_price PARCELLE (n, rayon effectif, période) servi AU SERVEUR par _q_v2_fiche — "
    "même phrase écran et PDF (EXPORTS-1 1.3, plus de calcul front)",
    moteur="sector_price", calcul="moteur",
    fonction="src/labuse/api/app.py:_q_v2_fiche (sector_price via marche_service, phrase_prix_ancien)",
    reservoirs=("dvf",), portee="live"),
 "ventes_100m_n": C("Ventes à moins de 100 m (36 mois)", "nombre", "parcelle",
    "count mutations DVF à <100 m sur 36 mois (profil voisinage_100m, config/dvf_profils.yaml) + médiane",
    moteur="marche_service", calcul="moteur",
    fonction="src/labuse/api/site_voisinage.py:voisinage_proche (profil voisinage_100m)",
    reservoirs=("dvf",), portee="live"),
 "pente_deg": C("Pente", "nombre", "parcelle",
    "pente moyenne parcelle (RGE ALTI), flag terrassement",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/app.py:3283 (viabilisation)",
    reservoirs=("rge_alti",), portee="live", table="parcel_terrain.pente_moy_deg"),
 "piscine_m2": C("Piscine ~m²", "m²", "parcelle",
    "surface détectée parcel_equipements (BD ORTHO 2025)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/app.py:3283",
    reservoirs=("bd_ortho",), portee="live", table="parcel_equipements.piscine_surface_m2"),
 # FICHE-RANGEMENT-1 Lot 3 — orphelins déclarés (données réelles, affichées, source fiable) :
 "exposition_versant": C("Exposition (versant)", "classe", "parcelle",
    "orientation du versant (octant dominant) et pente moyenne autour de la parcelle, calculées "
    "à la volée sur le MNT RGE ALTI (gdaldem aspect, fenêtre 200 m, pondérée par la pente) ; "
    "terrain quasi plat → « plat », jamais une orientation inventée sur du bruit",
    # FICHE-RANGEMENT-1 Lot 3 — passe-plat SERVI : la valeur n'est pas stockée, elle est produite
    # à la demande par exposition_parcelle (aucun moteur.csv / aucune fiche-règle : donnée
    # informative secondaire, RGE ALTI), servie telle quelle à la tuile. sql_propre interdit (V5b).
    # TESTS-0 : `table=` était omise à l'ajout (FICHE-RANGEMENT-1 Lot 3) — seule passe-plat servie
    # sans table déclarée sur 119 (cf. test_circuit2_lot16). Lecture réelle : parcels (centroïde 2975)
    # puis calcul LIVE sur le MNT RGE ALTI (gdaldem aspect, WMS GetMap) ; aucune valeur stockée.
    moteur=None, calcul="passe_plat",
    table="parcels (centroïde) → MNT RGE ALTI (gdaldem aspect, WMS GetMap) — calcul live, aucune valeur stockée",
    fonction="src/labuse/faisabilite/exposition.py:exposition_parcelle",
    reservoirs=("rge_alti",), portee="live", type="classe",
    domaine=("Nord", "Nord-Est", "Est", "Sud-Est", "Sud", "Sud-Ouest", "Ouest", "Nord-Ouest", "plat"),
    domaine_source="octants du MNT RGE ALTI (faisabilite/exposition.py)"),
 "cosia_detecte_m2": C("Bâti détecté CoSIA (hors BD TOPO)", "m²", "parcelle",
    "surface de bâti détectée par CoSIA au-delà de l'empreinte BD TOPO (parcel_bati_revele), "
    "servie À PART car CoSIA sur-détecte à la maille parcelle ; None tant qu'il n'y a pas de "
    "sur-détection nette (> emprise BD TOPO + 50 m²)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/bati.py:le_bien_block (cosia_detecte_m2)",
    reservoirs=("cosia",), portee="live", type="nombre",
    table="parcel_bati_revele.emprise_cosia_m2"),
 "distance_arret_m": C("Transport public — au plus proche", "m", "parcelle",
    "plus proche arrêt/pôle (distance en m)",
    moteur="parcelle_proximites", calcul="moteur",
    fonction="src/labuse/registre/moteurs/parcelle.py:plus_proche",
    reservoirs=("gtfs_pan", "osm_transport",), portee="live"),
 # FICHE-1 lot 4 — stationnement allégé L151-36 : la parcelle est-elle à moins de 800 m d'une
 # station de transport en site propre (plafond d'une place/logement, 0,5 en social).
 "tcsp_stationnement_allege": C("Stationnement allégé (TCSP, L151-36)", "classe", "parcelle",
    "la parcelle est-elle à MOINS de 800 m (à vol d'oiseau) d'une station de transport en site "
    "propre — plafond d'une aire de stationnement par logement (0,5 pour le logement social), "
    "opposable au PLU (art. L151-34 à 36) ; distance et station nommées",
    moteur="parcelle_proximites", calcul="moteur",
    fonction="src/labuse/api/app.py:_proximites_block (drapeau sous_800m, L151-36 strict)",
    reservoirs=("gtfs_pan", "osm_transport",), portee="live", type="classe",
    domaine=("sous_800m", "au_dela", "aucune_station"),
    domaine_source="art. L151-36 c. urb. (loi n° 2025-1129 du 26/11/2025) — seuil 800 m strict"),
 "n_permis_proximite": C("Permis à 500 m sur 24 mois", "nombre", "parcelle",
    "permis Sitadel dans le rayon 500 m, fenêtre 24 mois — LE profil client (arbitrage Q7), "
    "paramètres TRANSMIS au moteur (EXPORTS-1 4.1, plus jamais les défauts 300 m · 5 ans)",
    moteur="marche_service", calcul="moteur",
    fonction="src/labuse/marche_service.py:permits (profil flash_500m → nearby_permits)",
    reservoirs=("sitadel",), portee="live"),
 "depots_secteur_n": C("Déposés sur le secteur (36 mois)", "nombre", "zone",
    "dépôts Sitadel de la section cadastrale (préfixe IDU 10), fenêtre 36 mois "
    "(DEPOTS_FENETRE_MOIS, profil fiche_36m)",
    moteur="marche_service", calcul="moteur",
    fonction="src/labuse/ingestion/permits.py:depots_recents (via marche_service, profil fiche_36m)",
    reservoirs=("sitadel",), portee="live"),
 "type_proprietaire": C("Propriétaire (type)", "classe", "proprietaire",
    "personne morale (dénomination) / personne physique non recensée — fichier PM "
    "parcelle_personne_morale, millésime 2025 (même assiette que la carte — EXPORTS-1 5.4 : "
    "la ligne « non renseigné » stockée au run est rebranchée sur le fichier PM à la lecture)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/app.py:3586 (proprietaire_moral, parcelle_personne_morale) ; "
             "garde de lecture cascade/context.py (EXPORTS-1 5.4)",
    reservoirs=("dgfip_parcelles_pm",), portee="live",
    table="parcelle_personne_morale.denomination (millésime 2025)",
    domaine=("personne morale", "personne physique non recensée"),
    domaine_source="fichier PM DGFiP (les PP ne sont pas diffusées)"),
 "verdict_icd": C("Confiance données", "verdict", "parcelle",
    "verdict de complétude des couches + liste des manquants",
    moteur="cascade", calcul="moteur", fonction="src/labuse/api/app.py:3283 (bloc icd)",
    reservoirs=(), portee="run"),
 "divisible_classe": C("Division (candidate)", "classe", "parcelle",
    "présence dans division_or_candidates — run figé q_v10, workflow de revue",
    moteur="division_or", calcul="moteur", fonction="src/labuse/api/app.py:2692-2696",
    reservoirs=("cadastre_api_carto", "cosia", "gpu_plu_api_carto",), portee="run",
    domaine=("candidate", "non_candidate", "non_recalculee"),
    domaine_source="présence dans division_or_candidates au run servi (2.3 : run mort jamais servi)"),
 "statut_plu": C("Règles d'urbanisme (statut)", "classe", "commune",
    "RNU (registre) l'emporte ; sinon statut du registre veille_plu",
    moteur="plu_destinations", calcul="moteur", fonction="src/labuse/api/fiche_commune.py:137-144",
    reservoirs=("gpu_plu_api_carto", "sudocuh",), portee="live",
    domaine=("RNU", "à jour", "en révision", "en élaboration", "en modification", "document local"),
    domaine_source="_PLU_STATUT (api/fiche_commune.py) + registre RNU (config/rnu_communes.yaml)"),
 # GEOPF-3 — SCOT couvrant la commune (nom + date d'approbation), par intersection avec kind='scot'.
 # type=texte (nom de SCOT + date = texte libre, pas une classe à domaine fermé).
 "scot_nom_date": C("SCOT (nom + approbation)", "texte", "commune",
    "Schéma de Cohérence Territoriale couvrant la commune (GPU) — nom + date d'approbation",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/fiche_commune.py:scot_commune",
    reservoirs=("scot_gpu",), portee="live",
    type="texte", table="spatial_layers (kind=scot)", fabrication="requete"),
 # COMMUNE-FIX-1 (D12) — la PROCÉDURE PLU EN COURS au dernier relevé Sudocuh (état détaillé + date de
 # prescription + millésime Sudocuh), servie sur la carte Urbanisme. Passe-plat du fichier Sudocuh.
 "plu_procedure_en_cours": C("Procédure PLU en cours (Sudocuh)", "texte", "commune",
    "état détaillé de la procédure d'urbanisme au dernier relevé Sudocuh (révision, modification, "
    "élaboration…), date de prescription et millésime Sudocuh — passe-plat, jamais recalculé",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/fiche_commune.py:plu_statut",
    reservoirs=("sudocuh",), portee="live", type="texte",
    table="sudocuh_procedures (du_en_cours, etat_detaille, prescription_proc)"),
 "zan_reste_ha": C("Enveloppe ZAN (reste)", "nombre", "commune",
    "enveloppe restante estimée depuis conso ENAF",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/api/rarete.py:compute_rarete (reste_zan_ha — producteur nommé, délégation)",
    reservoirs=("enaf_cerema",), portee="live"),
 "taux_lls_pct": C("Taux LLS", "%", "commune",
    "taux LLS de l'inventaire SRU",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/fiche_commune.py (commune_contexte_sru)",
    reservoirs=("sru_dhup",), portee="live", table="commune_contexte_sru.taux_lls"),
 # SOURCES-4 lot 2 — l'EFFECTIF BRUT de LLS de l'inventaire SRU dormait dans detail->nb_lls
 # (seul le taux était servi). Surfacé sur la carte SRU. Le dénominateur (résidences principales)
 # n'est PAS publié dans le CSV DHUP v2 → non ingéré (arbitrage), le taux reste la grandeur servie.
 "lls_inventaire_n": C("Logements sociaux (inventaire SRU)", "logements", "commune",
    "nombre de logements locatifs sociaux de l'inventaire SRU (effectif brut, detail->nb_lls)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/app.py (_rafraichir_partages, commune_contexte_sru)",
    reservoirs=("sru_dhup",), portee="live", table="commune_contexte_sru.detail->>nb_lls"),
 "plh_objectif_logements_an": C("Objectif logements/an", "logements", "commune",
    "objectif PLH, chaque chiffre porte sa référence doc+page",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/fiche_commune.py (plh_epci)",
    reservoirs=("plh_epci",), portee="live", table="plh_epci (objectif logements/an, par EPCI)"),
 # CIRCUIT-5b lot 1 — RPLS (SDES) entre au catalogue : ce passe-plat en est le lecteur déclaré.
 # NB : le taux LLS servi vient, lui, de l'inventaire SRU (sru_dhup → taux_lls_pct), pas du RPLS.
 "parc_social_rpls_logements": C("Parc social (logements RPLS)", "logements", "commune",
    "nombre de logements locatifs sociaux de la commune (RPLS SDES, millésime 01/01/2025) — "
    "contexte marché de la fiche commune, du Flash et du PDF, jamais un signal scoring",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/app.py (marche_secteur — rpls_commune)",
    reservoirs=("rpls_sdes",), portee="live", table="rpls_commune (nb_logements, construct_median)"),
 "prix_terrain_zone_eur_m2": C("Terrain nu (zone U / AU)", "€/m²", "commune",
    "médiane DVF terrain nu par famille de zone, seuil 10 ventes",
    moteur="marche_service", calcul="moteur", fonction="src/labuse/faisabilite/marche_commune.py:ligne2_terrain_zone",
    reservoirs=("dvf", "gpu_plu_api_carto",), portee="live"),
 "loyer_median_eur_m2": C("Loyer médian", "€/m²", "commune",
    "SOURCES-1 lot 5 — bascule CANONIQUE/REPLI : loyer OBSERVÉ de la zone OLL (ADIL 974/"
    "AGORAH) quand la commune tient dans UNE zone (16/24) ; sinon loyer d'ANNONCE DHUP "
    "(carte des loyers, extrait embarqué) avec le motif dit — étiquette de source honnête",
    moteur="loyers", calcul="moteur",
    fonction="src/labuse/faisabilite/marche_commune.py:ligne9_loyer (bascule OLL/DHUP)",
    reservoirs=("loyers_oll", "loyers_dhup",), portee="live"),
 "n_parcelles_commune": C("N parcelles", "nombre", "commune",
    "count parcels par commune",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:compte_parcelles_commune",
    reservoirs=("cadastre_api_carto",), portee="live"),
 "part_zone_U_pct": C("Zonage — U", "%", "commune",
    "surface cadastrée U / surface zonée totale (somme=100 %)",
    moteur="zonage_commune", calcul="moteur",
    fonction="src/labuse/registre/moteurs/zonage.py:parts_zonage_surface",
    reservoirs=("cadastre_api_carto", "gpu_plu_api_carto",), portee="live"),
 "part_zone_AU_pct": C("Zonage — AU", "%", "commune",
    "surface AU / surface zonée",
    moteur="zonage_commune", calcul="moteur",
    fonction="src/labuse/registre/moteurs/zonage.py:parts_zonage_surface",
    reservoirs=("cadastre_api_carto", "gpu_plu_api_carto",), portee="live"),
 "part_zone_A_pct": C("Zonage — A", "%", "commune",
    "surface A / surface zonée (Saint-Paul : 35,8 % — la part en PARCELLES vaut 17,8 %)",
    moteur="zonage_commune", calcul="moteur",
    fonction="src/labuse/registre/moteurs/zonage.py:parts_zonage_surface",
    reservoirs=("cadastre_api_carto", "gpu_plu_api_carto",), portee="live"),
 "part_zone_N_pct": C("Zonage — N", "%", "commune",
    "surface N / surface zonée (Saint-Paul : 47,2 % — la part en PARCELLES vaut 6,8 %)",
    moteur="zonage_commune", calcul="moteur",
    fonction="src/labuse/registre/moteurs/zonage.py:parts_zonage_surface",
    reservoirs=("cadastre_api_carto", "gpu_plu_api_carto",), portee="live"),
 "ppr_pct": C("PPR (part des parcelles)", "%", "commune",
    "part des parcelles de la commune intersectant la couche ppr",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:pct_parcelles_couche",
    reservoirs=("deal_ppr",), portee="live"),
 "catnat_n": C("Arrêtés CatNat", "nombre", "commune",
    "count catnat_arretes",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/fiche_commune.py",
    # CIRCUIT-6 lot 0 — l'arête MANQUAIT : catnat_arretes est le réservoir catnat_gaspar
    # (426 arrêtés servis fiche commune/Pièges sans provenance tracée — SOURCES-AUDIT).
    reservoirs=("catnat_gaspar",), portee="live", table="catnat_arretes (count par insee)"),
 # SOURCES-4 lot 1 — le DÉTAIL des arrêtés (péril, dates début/fin/arrêté, code national + date JO)
 # dormait dans catnat_arretes / raw : seul le COMPTE (catnat_n) était servi. Liste servie sur la
 # fiche commune (12 plus récents), même réservoir, sans nouvelle source.
 "catnat_arretes_liste": C("Arrêtés CatNat (détail)", "liste", "commune",
    "arrêtés CatNat de la commune détaillés : péril, dates de début/fin/arrêté, code national et "
    "date de publication au JO — 12 plus récents (le compte total reste catnat_n)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/fiche_commune.py:risques",
    reservoirs=("catnat_gaspar",), portee="live", type="liste",
    table="catnat_arretes (détail par insee) + raw (code_national_catnat, date_publication_jo)"),
 "habitants_n": C("Habitants", "nombre", "commune",
    "population municipale LÉGALE INSEE (recensement), servie via Sudocuh (pop_mun) — COMMUNE-FIX-1 (A1) : "
    "l'agrégat Filosofi (carreaux fiscaux) sous-estimait la population et n'est plus servi ici (il ne "
    "sert plus que le niveau de vie)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/fiche_commune.py (population)",
    reservoirs=("sudocuh", "insee_rp_logement",), portee="live",
    table="sudocuh_procedures.pop_mun (population municipale légale INSEE)"),
 "vacance_pct": C("Vacance", "%", "commune",
    "100 × vacants / logements (RP)",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:vacance_pct",
    reservoirs=("insee_rp_logement",), portee="live"),
 # DONNEES-1 lot 2.4 — âge du parc (RP2022, table rp_logement_commune jusqu'ici ingérée mais montrée
 # nulle part) : part construit avant 1991 (stock ancien = potentiel rénovation/démolition-recons-
 # truction). Les autres variables logement de rp_logement_commune (type, tenure, vacance, social)
 # sont DÉJÀ servies via commune_insee_logement / IRIS / RPLS — doublon, non rebranchées.
 "parc_ancien_pct": C("Parc construit avant 1991", "%", "commune",
    "part (%) du parc de logements achevé avant 1991 (RP2022, distribution ACHL : A/B = ancien) — "
    "stock ancien, indicatif du potentiel de rénovation ; le reste des variables logement RP2022 "
    "est déjà servi via commune_insee_logement / IRIS / RPLS (doublon)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/fiche_commune.py:_parc_ancien_pct",
    reservoirs=("insee_rp2022_egoul",), portee="live", table="rp_logement_commune"),
 "qpv_n": C("QPV", "nombre", "commune",
    "count QPV intersectant la commune",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:qpv_commune",
    reservoirs=("qpv_2024",), portee="live"),
 "prix_demande_eur": C("Prix demandé", "€", "annonce",
    "fait déclaré de l'annonce (pige_faits), jamais le texte",
    moteur=None, calcul="passe_plat", fonction="src/labuse/pige/client.py",
    reservoirs=("radar_pige",), portee="live", table="pige_faits.prix"),
 "copilote_compte_parcelles": C("Compte de parcelles (réponse)", "nombre", "global",
    "MÊME facette canonique que le filtre écran (égalité verrouillée)",
    moteur="copilote_outils", calcul="moteur",
    fonction="src/labuse/copilote_v2/outils.py:compter_parcelles",
    reservoirs=("cadastre_api_carto",), portee="run"),
 "destination_statut": C("Peut-on ouvrir une activité ? (verdict)", "verdict", "parcelle",
    "MÊME moteur plu.destinations que fiche et étude de zone",
    moteur="plu_destinations", calcul="moteur", fonction="src/labuse/copilote_v2/outils.py:573-599",
    reservoirs=("gpu_plu_api_carto", "sudocuh",), portee="live"),
 "n_veilles": C("Veilles actives", "nombre", "global",
    "count veilles du compte",
    moteur="plateforme_compteurs", calcul="moteur",
    fonction="src/labuse/copilote_v2/veilles.py:lister (producteur nommé, délégation)",
    reservoirs=(), portee="live"),
 "projet_cadrage_n": C("Parcelles (cadrage)", "nombre", "global",
    "count parcelles du projet",
    moteur="plateforme_compteurs", calcul="moteur",
    fonction="src/labuse/api/projets.py:_counts_by_projet (producteur nommé, délégation)",
    reservoirs=(), portee="run"),
 "projet_retenues_n": C("Retenues", "nombre", "global",
    "count retenues",
    moteur="plateforme_compteurs", calcul="moteur",
    fonction="src/labuse/api/projets.py:_counts_by_projet (producteur nommé, délégation)",
    reservoirs=(), portee="run"),
 "crm_cartes_n": C("Cartes par colonne", "nombre", "global",
    "count par colonne",
    moteur="plateforme_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/plateforme.py:cartes_par_colonne",
    reservoirs=(), portee="live"),
 "n_notifications": C("Notifications non lues", "nombre", "global",
    "count event_log non lus du compte",
    moteur="plateforme_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/plateforme.py:notifications_non_lues",
    reservoirs=(), portee="live"),
 "n_bascules_7j": C("Bascules (7 jours)", "nombre", "global",
    "bascules de tier détectées vs run précédent",
    moteur="plateforme_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/plateforme.py:bascules_tiers_hauts",
    reservoirs=(), portee="run"),
 "n_biens_du_jour": C("Biens du jour (digest)", "nombre", "global",
    "biens validés du jour, cartes HTML plafond 10 + « et N autres »",
    moteur="marche_pige", calcul="moteur", fonction="src/labuse/api/events.py:1160-1216",
    reservoirs=("radar_pige",), portee="live"),
 "n_biens_veille": C("NB_BIENS (Brevo 13)", "nombre", "global",
    "len(matches) de LA veille — un mail par veille",
    moteur="marche_pige", calcul="moteur", fonction="src/labuse/pige/digests.py:303-313",
    reservoirs=("radar_pige",), portee="live"),
 "n_parcelles_ile": C("Parcelles (accueil)", "nombre", "global",
    "count parcels mesuré, jamais en dur",
    moteur="plateforme_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/plateforme.py:compte_parcelles_ile",
    reservoirs=("cadastre_api_carto",), portee="live"),
 "n_sources": C("Sources (accueil)", "nombre", "global",
    "count des sources AFFICHÉES (66 au 05/09) — définition canonique WHERE_AFFICHEES "
    "(sources_catalog), servie accueil ET écran Circuit",
    moteur="flux", calcul="moteur",
    fonction="src/labuse/flux.py:construire_flux (producteur nommé, délégation — "
             "l'accueil lit la même définition WHERE_AFFICHEES)",
    reservoirs=(), portee="live"),
 "run_label_servi": C("Run servi (pied)", "classe", "global",
    "label du run servi",
    moteur=None, calcul="constante", fonction="src/labuse/api/accueil.py:57",
    reservoirs=(), portee="run", type="texte"),
 "prix_flash_eur": C("Rapport Flash — 79 €", "€", "global",
    "prix de l'offre Flash, source unique offres.py",
    moteur=None, calcul="constante", fonction="src/labuse/offres.py (source unique des prix)",
    reservoirs=(), portee="live"),
 "n_a_faire": C("À faire (pilotage)", "nombre", "global",
    "gestes attendus : nouvelle_version + a_rafraichir (arbitre unique etats_sources)",
    moteur="plateforme_compteurs", calcul="moteur",
    fonction="src/labuse/etats_sources.py:compteurs (sur lister_etats — arbitre unique, délégation)",
    reservoirs=(), portee="live"),
 "n_sources_surveillees": C("sous veille (écran Circuit)", "nombre", "global",
    "49 = lignes source_veille actives à vraie sonde, compte brut",
    moteur="flux", calcul="moteur",
    fonction="src/labuse/flux.py:construire_flux (comptes.surveillees — producteur nommé, délégation)",
    reservoirs=(), portee="live"),
 "ecart_candidat_pct": C("Écart candidat vs servi", "%", "global",
    "comparaison distribution tiers candidat/servi",
    moteur="golden_ops", calcul="moteur",
    fonction="src/labuse/golden_ops.py:comparer (producteur nommé, délégation)",
    reservoirs=(), portee="run"),
 "ia_cout_eur": C("Conso IA (€)", "€", "global",
    "somme cout par modèle/surface 30 j (ledger ia_log)",
    moteur="plateforme_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/plateforme.py:conso_ia_mois (+ conso_ia_30j)",
    reservoirs=(), portee="live"),
 "n_depots_a_verifier": C("Dépôts à vérifier", "nombre", "global",
    "count pige_faits en attente de validation (file d'extraction Radar)",
    moteur="plateforme_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/plateforme.py:depots_a_verifier",
    reservoirs=("radar_pige",), portee="live"),
 "n_comptes_actifs": C("Comptes actifs", "nombre", "global",
    "count comptes par statut",
    moteur="plateforme_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/plateforme.py:comptes_actifs",
    reservoirs=(), portee="live"), # ── longue traîne (lot 1.3) — robinets à zéro de l'inventaire, chiffres déclarés ici ──
 "n_procedures_plu": C("Procédures d'urbanisme (en cours)", "nombre", "commune",
    "compte des procédures PLU non réconciliées (révision/élaboration) du registre veille_plu",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/veille_plu.py:communes_en_procedure (producteur nommé, délégation)",
    reservoirs=("sudocuh",), portee="live"),
 "assemblage_parcelles_n": C("Parcelles assemblées", "nombre", "parcelle",
    "compte des parcelles retenues dans l'assemblage courant",
    moteur="parcelle_proximites", calcul="moteur",
    fonction="src/labuse/registre/moteurs/parcelle.py:assemblage_assiette "
             "(délégation — le calcul vit dans api/moteurs.py:assemblage, une seule vérité)",
    reservoirs=("cadastre_api_carto",), portee="live"),
 "assemblage_surface_m2": C("Surface assemblée", "m²", "parcelle",
    "somme des surfaces cadastrales des parcelles de l'assemblage",
    moteur="parcelle_proximites", calcul="moteur",
    fonction="src/labuse/registre/moteurs/parcelle.py:assemblage_assiette "
             "(délégation — le calcul vit dans api/moteurs.py:assemblage, une seule vérité)",
    reservoirs=("cadastre_api_carto",), portee="live"),
 "courrier_demandes_n": C("Courriers demandés", "nombre", "global",
    "compte des demandes de courrier propriétaire du compte",
    moteur="plateforme_compteurs", calcul="moteur",
    fonction="src/labuse/courrier.py:demandes_de (producteur nommé, délégation)",
    reservoirs=(), portee="live"),
 "annee_ortho": C("Année de la photographie aérienne", "date", "global",
    "millésime du fond ortho affiché (registre ORTHO_YEARS)",
    moteur=None, calcul="constante", fonction="frontend/src/components/map/basemaps.ts (ORTHO_YEARS)",
    reservoirs=("bd_ortho",), portee="live"),
 "pipeline_entrees_n": C("Entrées du pipeline", "nombre", "global",
    "compte des entrées du pipeline (retour terrain) par statut, périmètre du compte",
    moteur="plateforme_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/plateforme.py:cartes_par_colonne",
    reservoirs=(), portee="live"),
 "couverture_commune_pct": C("Couverture des sources par commune", "%", "commune",
    "part des communes couvertes par chaque source (taux d'ingestion)",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:couverture_sources",
    reservoirs=(), portee="live"),
 "autres_loges_pct": C("logés gratuitement", "%", "commune",
    "100 − locataires_pct − proprietaires_pct (INSEE RP), arrondi 0,1, plancher 0 — calculé au SERVEUR (lot 2.4, avant : ContextePanel.tsx:526)",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:autres_loges_pct",
    reservoirs=("insee_rp_logement",), portee="live"),
 "parcelles_par_zone_n": C("parcelles en zone …", "nombre", "commune",
    "compte de parcelles par famille/zone du filtre (JAMAIS servi comme une part — décision Vic 2.1 : les parts de zonage sont les parts de surface)",
    moteur="zonage_commune", calcul="moteur",
    fonction="src/labuse/registre/moteurs/zonage.py:parcelles_par_zone",
    reservoirs=("gpu_plu_api_carto", "cadastre_api_carto"), portee="live"),
 "usage_outil_n": C("Usage des outils (30 j)", "nombre", "global",
    "compte d'événements d'usage par outil sur la fenêtre choisie (7/30/90 j)",
    moteur="plateforme_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/plateforme.py:usage_par_outil",
    reservoirs=(), portee="live"), # ── 0-bis réconciliation EXPORTS-1/ZONE-1 (05/09) ──
 "mixite_clause": C("Mixité sociale (clause)", "verdict", "parcelle",
    "déclenchement de la clause de mixité Art. 2 : SDP ≥ seuil OU logements ≥ seuil OU terrain "
    "> seuil (seuils des hypothèses de bilan, source déclarée sinon « Estimé ») — bloc unique "
    "servitude + déclenchement (EXPORTS-1 5.1)",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py:_clause_mixite",
    reservoirs=("gpu_plu_api_carto",), portee="live"),
 "cout_construction_saisi_eur_m2": C("Coût de construction (saisi)", "€/m²", "parcelle",
    "hypothèse SAISIE par le client dans la calculette du bilan — jamais un chiffre LABUSE",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/app.py:parcel_export_pdf (calculette — saisie client)",
    reservoirs=(), portee="projet",
    table="(saisie client — corps de requête de la calculette, aucune table)"),
 "marge_frais_saisie_pct": C("Marge et frais (saisis)", "%", "parcelle",
    "hypothèse SAISIE par le client dans la calculette du bilan — jamais un chiffre LABUSE",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/app.py:parcel_export_pdf (calculette — saisie client)",
    reservoirs=(), portee="projet",
    table="(saisie client — corps de requête de la calculette, aucune table)"),
 "prix_demande_saisi_eur": C("Prix demandé (saisi)", "€", "parcelle",
    "prix demandé SAISI par le client (écart au prix demandé calculé dessus) — jamais un "
    "chiffre LABUSE ; ≠ prix_demande_eur (fait déclaré d'une annonce Radar)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/app.py:parcel_export_pdf (calculette — saisie client)",
    reservoirs=(), portee="projet",
    table="(saisie client — corps de requête de la calculette, aucune table)"),
 # RECETTE-8 W13bis — parcours « Revente en l'état » (C3) : achat → frais → travaux → portage →
 # revente ⇒ marge / taux de marge. Saisies client (portée projet), jamais un chiffre LABUSE.
 "prix_achat_revente_saisi_eur": C("Prix d'achat — revente (saisi)", "€", "parcelle",
    "prix d'achat du bien SAISI par le client pour le scénario de revente en l'état — écran Revente",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran Revente)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "travaux_revente_saisi_eur": C("Travaux éventuels — revente (saisi)", "€", "parcelle",
    "montant de travaux éventuels SAISI par le client avant revente (0 si aucun) — écran Revente",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran Revente)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "prix_revente_saisi_eur": C("Prix de revente (saisi)", "€", "parcelle",
    "prix de revente visé SAISI par le client (scénario revente en l'état) — écran Revente",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran Revente)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 # ══ EXPORTS-2 lot 4 — LE QUESTIONNAIRE DU FINANCIER (4 écrans, saisies client portée projet) ══
 # Chaque champ = un id projet, jamais un chiffre LABUSE. Le pré-remplissage sourcé est servi À
 # PART (prefill, avec sa source) ; un champ vidé par le client s'imprime « non chiffré », jamais
 # un défaut silencieux. Servis par l'écran questionnaire (robinet ecran_questionnaire_financier).
 "scenario_saisi": C("Scénario (saisi)", "classe", "parcelle",
    "scénario d'opération choisi par le client (reconstruction après démolition / réhabilitation "
    "du bâti / surélévation) — écran 1",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 1)",
    reservoirs=(), portee="projet", type="classe",
    domaine=("reconstruction", "rehabilitation", "surelevation"),
    domaine_source="scénarios du questionnaire du Financier",
    table="(saisie client — questionnaire du Financier)"),
 "logements_vises_saisi": C("Logements visés (saisi)", "logements", "parcelle",
    "nombre de logements visé par le client — écran 1 (pré-rempli par la fourchette du potentiel)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 1)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "typologie_moyenne_saisi": C("Typologie moyenne (saisi)", "texte", "parcelle",
    "typologie moyenne visée (T2, T3…) — saisie client, écran 1",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 1)",
    reservoirs=(), portee="projet", type="texte",
    table="(saisie client — questionnaire du Financier)"),
 "part_sociale_saisi_pct": C("Part de logement social/intermédiaire (saisi)", "%", "parcelle",
    "part de logement social ou intermédiaire visée — écran 1 (pré-remplie par la mixité de la zone)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 1)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "stationnement_type_saisi": C("Stationnement — type (saisi)", "classe", "parcelle",
    "implantation du stationnement choisie (au sol / sous-sol / silo), écran 1 — modifie le coût "
    "par place",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 1)",
    reservoirs=(), portee="projet", type="classe",
    domaine=("sol", "sous_sol", "silo"),
    domaine_source="implantations du stationnement du questionnaire",
    table="(saisie client — questionnaire du Financier)"),
 "prix_refuse_saisi_eur": C("Prix déjà refusé (saisi)", "€", "parcelle",
    "prix déjà refusé par le vendeur, si le client le connaît — saisie client, écran 2",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 2)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "frais_acquisition_saisi_pct": C("Frais d'acquisition (saisi, %)", "%", "parcelle",
    "pourcentage de frais d'acquisition (notaire, droits) appliqué au prix du terrain — écran 2, "
    "pré-rempli 7 %",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 2)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "commission_apporteur_saisi_eur": C("Commission d'apporteur (saisi)", "€", "parcelle",
    "commission d'apporteur d'affaires, si connue — saisie client, écran 2",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 2)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "honoraires_techniques_saisi_pct": C("Honoraires techniques (saisi, %)", "%", "parcelle",
    "pourcentage d'honoraires techniques (MOE, BET, contrôle) appliqué au coût de construction — écran 3",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 3)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "vrd_saisi_eur_m2": C("VRD et raccordements (saisi)", "€/m²", "parcelle",
    "coût VRD et raccordements au m² de terrain — écran 3, pré-rempli base LABUSE modulée par la "
    "viabilisation",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 3)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "cout_place_stationnement_saisi_eur": C("Coût par place de stationnement (saisi)", "€", "parcelle",
    "coût par place de stationnement — saisie client écran 3 (varie selon sol / sous-sol / silo)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 3)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "aleas_saisi_pct": C("Aléas (saisi, %)", "%", "parcelle",
    "pourcentage de provision pour aléas appliqué au coût de construction — saisie client, écran 3",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 3)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "taxe_amenagement_saisi_eur": C("Taxe d'aménagement (saisi)", "€", "parcelle",
    "taxe d'aménagement retenue — écran 3, pré-remplie par le calcul LABUSE (config datée), modifiable",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 3)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "prix_sortie_saisi_eur_m2": C("Prix de sortie (saisi)", "€/m²", "parcelle",
    "prix de sortie au m² habitable — écran 4, pré-rempli par le neuf observé (l'ancien en repère)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 4)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "prix_vente_bailleur_saisi_eur_m2": C("Prix de vente au bailleur (saisi)", "€/m²", "parcelle",
    "prix de vente au bailleur pour la part sociale — saisie client, écran 4",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 4)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "marge_visee_saisi_pct": C("Marge visée (saisi, %)", "%", "parcelle",
    "marge visée en % du chiffre d'affaires — écran 4, distincte des honoraires et des frais",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 4)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "regime_tva_saisi": C("Régime de TVA (saisi)", "classe", "parcelle",
    "régime de TVA retenu — CHAMP OBLIGATOIRE : il décide si le bilan est HT ou TTC ; renvoi à "
    "l'expert-comptable pour le régime réel — écran 4",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 4)",
    reservoirs=(), portee="projet", type="classe",
    domaine=("assujetti_recuperation", "tva_marge", "autre"),
    domaine_source="régimes de TVA du questionnaire (renvoi expert-comptable)",
    table="(saisie client — questionnaire du Financier)"),
 "duree_portage_saisi_mois": C("Durée de portage (saisi)", "mois", "parcelle",
    "durée de portage en mois — écran 4, pré-remplie par le délai d'instruction médian + 20 mois "
    "de chantier",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 4)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "apport_saisi_eur": C("Apport (saisi)", "€", "parcelle",
    "apport en fonds propres — saisie client facultative (pour la LTV), écran 4",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 4)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 "taux_apport_saisi_pct": C("Taux d'emprunt (saisi, %)", "%", "parcelle",
    "taux d'emprunt — saisie client facultative (pour la LTV), écran 4",
    moteur=None, calcul="passe_plat", fonction="src/labuse/financier_questionnaire.py (écran 4)",
    reservoirs=(), portee="projet", table="(saisie client — questionnaire du Financier)"),
 # ══ CIRCUIT-2 lot 1.2/1.3 — LES COUCHES (type `couche` : table/tuilage + fabrication) ══
 "verdict_couche": C("Verdict · Classement servi (couche)", "couche", "parcelle",
    "aplat des tiers du run servi sur toutes les parcelles (tuiles vectorielles)",
    moteur="flags", calcul="moteur", fonction="src/labuse/api/tiles.py (MVT parcel_flags)",
    reservoirs=("bd_topo", "cosia", "dvf", "filosofi_carreaux", "sitadel",), portee="run",
    type="couche", table="parcel_flags → tuiles MVT (mvt_meta porte le run et la date)",
    fabrication="build-mvt"),
 "zonage_plu_couche": C("Zonage PLU par parcelle (couche)", "couche", "parcelle",
    "chaque parcelle peinte de la famille de sa zone (calée cadastre), code exact au zoom/clic",
    moteur="zone_servie", calcul="moteur", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (plu_gpu_zone)",
    reservoirs=("gpu_plu_api_carto",), portee="live",
    type="couche", table="parcel_zone_plu", fabrication="requete",
    domaine=("U", "AU", "A", "N"), domaine_source="familles de zones du GPU"),
 "gpu_brut_couche": C("Limites officielles PLU — GPU brut (couche)", "couche", "commune",
    "les aplats bruts du document opposable (contours d'origine, hors cadastre)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (plu_gpu)",
    reservoirs=("gpu_plu_api_carto",), portee="live",
    type="couche", table="spatial_layers (kind=zonage_plu_gpu)", fabrication="requete"),
 "cinquante_pas_couche": C("50 pas géométriques (couche)", "couche", "commune",
    "la bande littorale des 50 pas (81,20 m), régime foncier outre-mer",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (cinquante_pas)",
    reservoirs=("cinquante_pas_deal",), portee="live",
    type="couche", table="spatial_layers (kind=cinquante_pas)", fabrication="requete"),
 "znieff_couche": C("ZNIEFF type I & II (couche)", "couche", "commune",
    "inventaire du patrimoine naturel (type I secteur sensible, type II grand ensemble)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (znieff)",
    reservoirs=("znieff_inpn",), portee="live",
    type="couche", table="spatial_layers (kind=znieff, subtype=type I/II)", fabrication="requete",
    domaine=("type I", "type II"), domaine_source="INPN/MNHN (PatriNat)"),
 "mesures_compensatoires_couche": C("Mesures compensatoires ERC (couche)", "couche", "commune",
    "emprises des mesures de compensation écologique (GéoMCE, MTE/OFB) — obligation dormante",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/couches_tuyau.py:couche_tuile (mesures_compensatoires)",
    reservoirs=("geomce",), portee="live",
    type="couche", table="spatial_layers (kind=mesures_compensatoires, subtype=surface/ligne/point)",
    fabrication="requete"),
 "scot_couche": C("SCOT — périmètre (couche)", "couche", "commune",
    "périmètre du Schéma de Cohérence Territoriale (GPU) — planification supra-communale",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (scot)",
    reservoirs=("scot_gpu",), portee="live",
    type="couche", table="spatial_layers (kind=scot)", fabrication="requete"),
 "enr_exclue_hors_toiture_couche": C("EnR interdites hors toiture — APER (couche)", "couche", "commune",
    "zones exclues des aires d'accélération EnR au sol (loi APER, OFB) — toiture possible",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/couches_tuyau.py:couche_tuile (enr_exclue_hors_toiture)",
    reservoirs=("enr_aper_ofb",), portee="live",
    type="couche", table="spatial_layers (kind=enr_exclue_hors_toiture)", fabrication="requete"),
 "bpe_couche": C("Équipements INSEE BPE (couche)", "couche", "commune",
    "équipements géolocalisés BPE (source statistique, distincte d'OSM — jamais fusionnées)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (amenite_bpe)",
    reservoirs=("bpe_insee",), portee="live",
    type="couche", table="spatial_layers (kind=amenite_bpe)", fabrication="requete"),
 "alea_inondation_couche": C("Aléa inondation (couche)", "couche", "commune",
    "secteurs exposés à l'aléa inondation avec leur NIVEAU (cartographie d'aléas DEAL — "
    "l'exposition au phénomène, pas la règle PPR)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/couches_tuyau.py:couche_tuile (georisque_alea, subtype=inondation)",
    reservoirs=("deal_ppr",), portee="live",
    type="couche", table="spatial_layers (kind=georisque_alea)", fabrication="requete",
    domaine=("faible", "moyen", "fort"),
    domaine_source="niveau NORMALISÉ servi (attrs.niveau — layers_ingest._normalise_alea) ; le "
                   "degré DEAL brut (FAIBLE…TRES_ELEVE) voyage dans attrs.degre. RETOURS-13 : "
                   "ELEVE/TRES_ELEVE normalisés en « moyen » = bug — la sonde 4.2 contrôle la "
                   "distribution degre↔niveau"),
 "alea_mvt_couche": C("Aléa mouvement de terrain (couche)", "couche", "commune",
    "secteurs exposés à l'aléa mouvement de terrain avec leur NIVEAU (cartographie DEAL)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/couches_tuyau.py:couche_tuile (georisque_alea, subtype=mouvement_terrain)",
    reservoirs=("deal_ppr",), portee="live",
    type="couche", table="spatial_layers (kind=georisque_alea)", fabrication="requete",
    domaine=("faible", "moyen", "fort"),
    domaine_source="niveau normalisé servi (attrs.niveau) ; degré DEAL brut en attrs.degre — "
                   "distribution contrôlée par la sonde 4.2"),
 "transport_couche": C("Transport public (couche)", "couche", "commune",
    "tracés et arrêts des 7 réseaux GTFS + téléphérique Papang (OSM)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/couches_tuyau.py:couche_tuile (transport_ligne, transport_arret, telepherique)",
    reservoirs=("gtfs_pan", "osm_transport",), portee="live",
    type="couche", table="spatial_layers (kind=transport_ligne/transport_arret/telepherique)",
    fabrication="requete"),
 "axes_couche": C("Axes structurants (couche)", "couche", "commune",
    "axes routiers structurants (BD TOPO importance 1-2) + pôles d'échange",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/couches_tuyau.py:couche_tuile (axe_structurant, pole_echange)",
    reservoirs=("bd_topo", "osm_transport",), portee="live",
    type="couche", table="spatial_layers (kind=axe_structurant/pole_echange)", fabrication="requete"),
 "lignes_ht_couche": C("Lignes haute tension (couche)", "couche", "commune",
    "réseau de transport 63/90 kV (BD TOPO, aérien seul — la HTA n'a pas de source ouverte)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (ligne_ht)",
    reservoirs=("bd_topo",), portee="live",
    type="couche", table="spatial_layers (kind=ligne_ht)", fabrication="requete"),
 "pylone_couche": C("Pylônes électriques (couche)", "couche", "commune",
    "supports du réseau de transport électrique (BD TOPO IGN, points) — servitude de voisinage",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (pylone)",
    reservoirs=("bd_topo",), portee="live",
    type="couche", table="spatial_layers (kind=pylone)", fabrication="requete"),
 "poste_transformation_couche": C("Postes de transformation (couche)", "couche", "commune",
    "postes de transformation électriques (BD TOPO IGN, emprises) — distance au raccordement",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/couches_tuyau.py:couche_tuile (poste_transformation)",
    reservoirs=("bd_topo",), portee="live",
    type="couche", table="spatial_layers (kind=poste_transformation)", fabrication="requete"),
 "tcsp_couche": C("Stationnement allégé — TCSP (couche)", "couche", "commune",
    # COUCHES-REGISTRE-2 lot 1 — l'ancienne déclaration BAOBAB (tcsp_axe, réservoir gtfs_pan) était
    # PÉRIMÉE (couche retirée en RETOURS-13). La couche réelle = voies bus en site propre + stations
    # dérivées + zone 800 m (art. L151-36), servie depuis spatial_layers, source OSM (tcsp_osm).
    "voies bus en site propre (OSM) + stations dérivées + zone de 800 m (art. L151-36)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (tcsp)",
    reservoirs=("tcsp_osm",), portee="live",
    type="couche", table="spatial_layers (kind=tcsp_troncon/tcsp_station/tcsp_zone)",
    fabrication="requete"),
 "dispositifs_couche": C("Dispositifs et périmètres (couche)", "couche", "commune",
    "QPV, NPNRU/ANRU, TVA primo (buffer 500 m DÉRIVÉ des QPV), ZFANG et FRR (maille commune)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/couches_tuyau.py:couche_tuile (qpv, tva_primo, anru, zfang, frr)",
    reservoirs=("qpv_2024", "npnru", "zfang", "frr_ex_zrr",), portee="live",
    type="couche", table="spatial_layers (kinds qpv/anru/zfang/frr ; tva_primo = buffer dérivé)",
    fabrication="requete"),
 "vefa_couche": C("Prix du logement neuf — VEFA (couche)", "couche", "commune",
    "aplat commune de la tranche VEFA (rampe), hachure sous 10 ventes — dérivé DVF live",
    moteur="marche_service", calcul="moteur",
    fonction="src/labuse/api/couches_tuyau.py:couche_tuile (vefa_neuf)",
    reservoirs=("dvf",), portee="live",
    type="couche", table="dvf_mutations_parcelle (agrégat live par commune)", fabrication="vue"),
 "densifier_couche": C("Densifier l'existant (couche)", "couche", "parcelle",
    "parcelles bâties à capacité résiduelle (segment renouvellement du run servi)",
    moteur="renouvellement", calcul="moteur",
    fonction="src/labuse/api/app.py:renouvellement_geojson",
    reservoirs=(), portee="run",
    type="couche", table="parcel_renouvellement (run servi)", fabrication="vue"),
 "ppr_couche": C("PPR multirisque (couche)", "couche", "commune",
    "zonage réglementaire des Plans de Prévention des Risques (la RÈGLE, ≠ l'aléa)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (ppr)",
    reservoirs=("deal_ppr",), portee="live",
    type="couche", table="spatial_layers (kind=ppr)", fabrication="requete"),
 "parc_national_couche": C("Parc national (couche)", "couche", "commune",
    "périmètre du Parc national de La Réunion (urbanisation très restreinte)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (parc_national)",
    reservoirs=("parc_national_inpn",), portee="live",
    type="couche", table="spatial_layers (kind=parc_national)", fabrication="requete"),
 "limites_parcelles_couche": C("Limites parcelles (couche)", "couche", "parcelle",
    "le contour gris de toutes les parcelles cadastrales (sans couleur)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/tiles.py (contours MVT)",
    reservoirs=("cadastre_api_carto",), portee="live",
    type="couche", table="parcels.geom → tuiles", fabrication="build-mvt"),
 "communes_couche": C("Limites communes (couche)", "couche", "global",
    "frontières officielles des 24 communes (référentiel embarqué geo.api.gouv/IGN, seed)",
    # COUCHES-REGISTRE-2 lot 1 — RATTACHÉE au réservoir `communes_ign` (ligne data_sources créée via le
    # seed ; compteur vitrine 91→92). Servie par le tuyau depuis `mvt_communes` (dérivée de `communes`).
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (limites_communes)",
    reservoirs=("communes_ign",), portee="live",
    type="couche", table="communes (contours, seed geo.api.gouv) → mvt_communes", fabrication="requete"),
 "equip_osm_couche": C("Équipements OSM (couche)", "couche", "commune",
    "équipements du quotidien relevés dans OpenStreetMap (couverture partielle DITE — "
    "l'absence n'est pas une preuve)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (amenite)",
    reservoirs=("osm_overpass",), portee="live",
    type="couche", table="spatial_layers (kind=amenite)", fabrication="requete"),
 # ══ lot 1.3 — LES FONDS IGN (service + version de tuiles ; sonde de DISPONIBILITÉ seule) ══
 "tuiles_plan_ign": C("Plan IGN v2 (fond)", "couche", "global",
    "fond de plan vectoriel IGN, interrogé en direct (aucune ingestion)",
    moteur=None, calcul="passe_plat", fonction="frontend/src/components/map/basemaps.ts (WMTS)",
    reservoirs=(), portee="live", type="couche",
    table="WMTS data.geopf.fr — LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2, VERSION=1.0.0, PM",
    fabrication="wmts_distant"),
 "tuiles_ortho_2025": C("Actuelle · Ortho Express 2025 (fond)", "couche", "global",
    "orthophoto 20 cm la plus récente réellement servie île-entière au 974 (vérifiée F4)",
    moteur=None, calcul="passe_plat", fonction="frontend/src/components/map/basemaps.ts (WMTS)",
    reservoirs=(), portee="live", type="couche",
    table="WMTS data.geopf.fr — LAYER=ORTHOIMAGERY.ORTHOPHOTOS.ORTHO-EXPRESS.2025, VERSION=1.0.0, PM",
    fabrication="wmts_distant"),
 "tuiles_ortho_1950_1965": C("Ortho 1950-1965 (fond)", "couche", "global",
    "mosaïque-période IGN (s'arrête ~z15, overzoom au-delà)",
    moteur=None, calcul="passe_plat", fonction="frontend/src/components/map/basemaps.ts (WMTS)",
    reservoirs=(), portee="live", type="couche",
    table="WMTS data.geopf.fr — LAYER=ORTHOIMAGERY.ORTHOPHOTOS.1950-1965, VERSION=1.0.0, PM",
    fabrication="wmts_distant"),
 "tuiles_ortho_2000_2005": C("Ortho 2000-2005 (fond)", "couche", "global",
    "mosaïque-période IGN vérifiée au 974",
    moteur=None, calcul="passe_plat", fonction="frontend/src/components/map/basemaps.ts (WMTS)",
    reservoirs=(), portee="live", type="couche",
    table="WMTS data.geopf.fr — LAYER=ORTHOIMAGERY.ORTHOPHOTOS2000-2005, VERSION=1.0.0, PM",
    fabrication="wmts_distant"),
 "tuiles_ortho_2006_2010": C("Ortho 2006-2010 (fond)", "couche", "global",
    "mosaïque-période IGN vérifiée au 974",
    moteur=None, calcul="passe_plat", fonction="frontend/src/components/map/basemaps.ts (WMTS)",
    reservoirs=(), portee="live", type="couche",
    table="WMTS data.geopf.fr — LAYER=ORTHOIMAGERY.ORTHOPHOTOS2006-2010, VERSION=1.0.0, PM",
    fabrication="wmts_distant"),
 "tuiles_ortho_2011_2015": C("Ortho 2011-2015 (fond)", "couche", "global",
    "mosaïque-période IGN vérifiée au 974",
    moteur=None, calcul="passe_plat", fonction="frontend/src/components/map/basemaps.ts (WMTS)",
    reservoirs=(), portee="live", type="couche",
    table="WMTS data.geopf.fr — LAYER=ORTHOIMAGERY.ORTHOPHOTOS2011-2015, VERSION=1.0.0, PM",
    fabrication="wmts_distant"),
 "tuiles_ortho_2016_2020": C("Ortho 2016-2020 (fond)", "couche", "global",
    "mosaïque-période IGN vérifiée au 974",
    moteur=None, calcul="passe_plat", fonction="frontend/src/components/map/basemaps.ts (WMTS)",
    reservoirs=(), portee="live", type="couche",
    table="WMTS data.geopf.fr — LAYER=ORTHOIMAGERY.ORTHOPHOTOS2016-2020, VERSION=1.0.0, PM",
    fabrication="wmts_distant"),
 "tuiles_ortho_2021_2023": C("Ortho 2021-2023 (fond)", "couche", "global",
    "mosaïque-période IGN vérifiée au 974",
    moteur=None, calcul="passe_plat", fonction="frontend/src/components/map/basemaps.ts (WMTS)",
    reservoirs=(), portee="live", type="couche",
    table="WMTS data.geopf.fr — LAYER=ORTHOIMAGERY.ORTHOPHOTOS2021-2023, VERSION=1.0.0, PM",
    fabrication="wmts_distant"),
 # ══ lot 1.2 — TEXTES d'origine externe (les deux hors_registre restants non-décor) ══
 "mairie_coordonnees": C("Mairie & service urbanisme (coordonnées)", "texte", "commune",
    "adresse, téléphone, courriel et horaires de la mairie — champ manquant = ABSENT, jamais inventé",
    moteur=None, calcul="passe_plat", fonction="src/labuse/ingestion/mairies.py (bloc MAIRIE)",
    reservoirs=("annuaire_service_public",), portee="live",
    type="texte", table="mairies"),
 # FICHE-1 lot 2 — RÉTABLI dans « Le bien » (était en_attente CIRCUIT-5, bloc construit mais
 # plus affiché) : dernier DPE du BÂTIMENT rattaché + nombre. Info fiche SEULE (M71 B1).
 "dpe_connu": C("DPE connu (étiquette, année)", "texte", "parcelle",
    "dernier DPE connu du bâtiment rattaché (étiquette énergie/GES, date, type de bâtiment) + "
    "nombre de DPE — info fiche SEULE, jamais un signal scoring ni un ciblage (M71 B1 : DPE neuf "
    "en DROM) ; DONNEES-1 lot 2 : la ligne ne s'affiche QUE si un DPE existe (non obligatoire en "
    "DROM, ~0,3 % de couverture — aucune ligne « non déterminé »)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/app.py:_dpe_connu_block",
    reservoirs=("dpe_ademe",), portee="live", type="texte", table="dpe_records"),
 "copilote_texte_web": C("Réponse web (Copilote, dernier recours)", "texte", "global",
    "texte libre ≤ 2 phrases MARQUÉ « web » (fait public La Réunion) — jamais un chiffre Sourcé "
    "(garde 2.6), jamais servi sans son marquage",
    moteur=None, calcul="passe_plat", fonction="src/labuse/copilote_v2/outils.py:recherche_web",
    reservoirs=(), portee="live", type="texte", table="(web — aucun réservoir, marquage obligatoire)"),
 # ══ lot 1.5 — les BLOCS de la fiche parcelle jusqu'ici sans id (couverture élargie) ══
 "adresse_ban": C("Adresse", "texte", "parcelle",
    "meilleure adresse BAN rattachée à la parcelle — None si aucune (le front dit « Adresse "
    "non disponible », jamais un champ vide)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/app.py:_ban_adresse",
    reservoirs=("ban",), portee="live", type="texte",
    table="adresses (id_ban) ⋈ adresse_parcelles"),
 "parcelle_geometrie": C("Géométrie de la parcelle", "classe", "parcelle",
    "le polygone cadastral de la parcelle (contour carte, fiche, PDF) — même table cadastre, "
    "même millésime partout (sonde lot 4.5)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/app.py (parcels.geom / geom_2975)",
    reservoirs=("cadastre_api_carto",), portee="live", type="geometrie",
    table="parcels.geom (geom_simple pour les tuiles)"),
 "reglement_plu_bloc": C("Règlement de la zone (extraits)", "liste", "parcelle",
    "zones PLU de la parcelle + extraits de règlement calibrés (corpus) — chaque extrait cite "
    "son document",
    moteur="plu_destinations", calcul="moteur",
    fonction="src/labuse/api/app.py:_reglement_plu_block",
    reservoirs=("gpu_plu_api_carto", "sudocuh",), portee="live", type="liste",
    table="parcel_zone_plu + corpus règlements"),
 "historique_permis_liste": C("Sur cette parcelle (permis)", "liste", "parcelle",
    "permis déposés/autorisés sur la parcelle (Sitadel) + caducité — chaque ligne datée",
    moteur="marche_service", calcul="moteur",
    fonction="src/labuse/api/app.py:_historique_site",
    # CIRCUIT-5b lot 2 — la géométrie des permis orphelins est rattachée via le cadastre
    # d'époque (RETOURS-14, cadastre_historique JOIN → sitadel_permits.geom) : cadastre_epoque
    # est donc un réservoir des permis (lecteur déclaré).
    reservoirs=("sitadel", "cadastre_epoque",), portee="live", type="liste", table="sitadel_permits"),
 "voisinage_100m_liste": C("Autour, à moins de 100 m", "liste", "parcelle",
    "ventes DVF + permis récents (36 mois) dans le buffer 100 m, site exclu (doctrine M38)",
    moteur="marche_service", calcul="moteur",
    fonction="src/labuse/api/site_voisinage.py:voisinage_proche",
    reservoirs=("dvf", "sitadel",), portee="live", type="liste",
    table="dvf_mutations_parcelle + sitadel_permits (buffer 100 m)"),
 "dvf_parcelle_liste": C("Mutations de la parcelle (DVF)", "liste", "parcelle",
    "dernière mutation de la parcelle + médianes du secteur cadastral (indicateur secondaire, "
    "étiqueté — EXPORTS-1 1.3)",
    moteur="marche_service", calcul="moteur", fonction="src/labuse/api/app.py:_q_v2_fiche (dvf_parcelle)",
    reservoirs=("dvf",), portee="live", type="liste",
    table="v_parcel_dvf_last + dvf_secteur_medianes"),
 "coproprietes_liste": C("Copropriétés (RNIC)", "liste", "parcelle",
    "copropriétés immatriculées rattachées à la parcelle (lots, syndic) — RNIC/ANAH",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/app.py:_q_v2_fiche (coproprietes)",
    reservoirs=("rnic_anah",), portee="live", type="liste", table="rnic_coproprietes"),
 "viabilisation_verdict": C("Viabilisation (faisceau)", "verdict", "parcelle",
    "indicateur de viabilisation par faisceau de preuves (accès, réseaux) + gestionnaires — "
    "jamais un booléen inventé",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/app.py:_viabilisation_block",
    # CIRCUIT-5b lot 2 — le bloc viabilisation lit AUSSI parkings_aper (grand parking →
    # note obligation ombrières loi APER, viabilisation_build.py) : parkings_osm_aper rattaché.
    reservoirs=("bd_topo", "rge_alti", "parkings_osm_aper",), portee="live", type="texte",
    table="parcel_viabilisation (faisceau)"),
 "equipements_proximite_liste": C("À proximité (équipements)", "liste", "parcelle",
    "équipements du quotidien nommés + distance (moteur BPE, couverture partielle DITE)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/app.py:_proximites_equipements_block",
    reservoirs=("bpe_insee", "osm_overpass",), portee="live", type="liste",
    table="parcel_amenites + spatial_layers (amenite/amenite_bpe)"),
 "evenements_proprietaire_liste": C("Événements propriétaire (BODACC)", "liste", "proprietaire",
    "événements datés du score V (procédures, radiations) — faits publics, chacun sourcé",
    moteur="v_score", calcul="moteur", fonction="src/labuse/api/app.py:_q_v2_fiche (score_v, evenement)",
    # CIRCUIT-5b lot 2 — le Score V lit le cache d'enrichissement DINUM (owner_enrichment /
    # owner_denom_lookup, score_v.py : état admin, NAF, dirigeants) : recherche_entreprises_dinum
    # y est rattaché (lecteur déclaré).
    reservoirs=("bodacc", "sirene_etablissements", "recherche_entreprises_dinum",), portee="live", type="liste",
    table="parcel_v_score + bodacc_*"),
 # CIRCUIT-5b lot 2 — INPI RNE (dirigeants) entre au registre par son lecteur déclaré : le
 # Scan patrimoine lit pm_dirigeants (société sans dirigeant connu / dirigeant inactif =
 # signal d'approche). Un seul robinet (outil_scan_patrimoine) → mono-robinet (V5c).
 "dirigeant_pm_signal": C("Dirigeant de la société (INPI RNE)", "texte", "proprietaire",
    "présence et activité du dirigeant d'une société propriétaire (INPI RNE) — signal d'approche "
    "factuel (société sans dirigeant connu, ou dirigeant inactif), jamais un export nominatif de masse",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/modules.py (Scan patrimoine — inpi_sans_dirigeant / dirigeant_inactif)",
    reservoirs=("inpi_rne",), portee="live", type="texte", table="pm_dirigeants"),
 # DONNEES-1 lot 2.3 — les dépôts de comptes BODACC (table bodacc_depots, 14 k, jusqu'ici ingérée
 # et surveillée mais montrée nulle part) entrent au registre comme SIGNAL d'approche sur le
 # propriétaire moral : Scan patrimoine + Successions. Factuel, jamais un scoring.
 "dernier_depot_comptes": C("Dépôt de comptes (dernier / silence)", "texte", "proprietaire",
    "année du dernier dépôt de comptes annuels d'une société propriétaire (BODACC) et années "
    "écoulées depuis — un silence prolongé = société en sommeil (signal d'approche foncière), "
    "jamais un scoring ; None si aucun dépôt publié",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/modules.py:_dernier_depot_comptes (Scan patrimoine + Successions)",
    reservoirs=("bodacc",), portee="live", type="texte", table="bodacc_depots"),
 "proprietaire_timeline_liste": C("Historique propriétaire (millésimes PM)", "liste", "proprietaire",
    "timeline unifiée versionné∪servi du fichier PM (2019→2025), diff CONSTAT — servi jamais écrasé",
    moteur="proprietaire_historique", calcul="moteur",
    fonction="src/labuse/proprietaire_historique.py:historique",
    reservoirs=("dgfip_parcelles_pm",), portee="live", type="liste",
    table="pm_proprietaires_millesimes ∪ parcelle_personne_morale"),
 "perimetres_dispositifs_liste": C("Périmètres et dispositifs (parcelle)", "liste", "parcelle",
    "périmètres touchant LA parcelle : QPV, NPNRU/ANRU, bande TVA primo (dérivée), ZFANG/FRR "
    "(commune) — en français, sourcés, jamais un sigle nu",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/app.py:_territoire_fiscal_block",
    reservoirs=("qpv_2024", "npnru", "zfang", "frr_ex_zrr",), portee="live", type="liste",
    table="spatial_layers (qpv/anru/zfang/frr ; tva_primo dérivé)"),
 # ══ lot 1.8 — ids que les maquettes d'exports attendent (réconciliation exports 05/09) ══
 "surface_vendable_m2": C("Surface vendable (Estimé)", "m²", "parcelle",
    "SHAB vendable du scénario table rase (fourchette du moteur commun) — distincte de "
    "capacite_logements",
    moteur="potentiel", calcul="moteur",
    fonction="src/labuse/faisabilite/potentiel.py:bloc_potentiel (table_rase.vendable_m2)",
    reservoirs=("bd_topo", "cosia", "gpu_plu_api_carto",), portee="run"),
 "surface_plancher_m2": C("Surface de plancher créée (table rase)", "m²", "parcelle",
    "surface de plancher CRÉÉE par le scénario table rase (moteur commun, emprise constructible × "
    "occupation × niveaux) — c'est l'ASSIETTE de taxe_amenagement_estimee_eur ; distincte de "
    "capacite_logements ET de sdp_residuelle_m2 (potentiel au sol après bâti existant) : deux "
    "concepts, deux données, jamais deux chiffres pour un même nom (RECETTE-7 lot 0)",
    moteur="potentiel", calcul="moteur",
    fonction="src/labuse/faisabilite/potentiel.py:bloc_potentiel (table_rase.plancher_m2)",
    reservoirs=("bd_topo", "cosia", "gpu_plu_api_carto",), portee="run"),
 "marge_surelevation_m": C("Marge de surélévation (au faîtage)", "m", "parcelle",
    "hauteur restante sous la règle de FAÎTAGE de la zone, comparée au faîtage bâti mesuré (BD "
    "TOPO) — RECETTE-7 E1 : faîtage contre faîtage ; repli égout+toiture type avec incertitude",
    moteur="potentiel", calcul="moteur",
    fonction="src/labuse/faisabilite/potentiel.py:surelevation",
    # CIRCUIT-6 lot 7 (fuite n°2, fusion RECETTE-10 T1) — quand le LiDAR HD a mesuré égout ET
    # faîtage, la marge SERVIE vient de surelevation_mesuree (les DEUX contraintes, la plus
    # serrée mord — batiment_hauteur_lidar) : l'arête lidar_hd_mnh reste posée.
    reservoirs=("lidar_hd_mnh", "bd_topo", "gpu_plu_api_carto",), portee="run"),
 "part_logements_egout_pct": C("Logements raccordés à l'égout", "%", "parcelle",
    "part des logements raccordés au tout-à-l'égout (INSEE RP2022 EGOUL, maille IRIS, repli "
    "commune) — le TAUX, jamais un verdict",
    moteur="anc", calcul="moteur",
    fonction="src/labuse/anc_service.py:statut_anc (producteur nommé, délégation)",
    # SOURCES-3 lot 0.2 — l'Office de l'eau (office_eau_chroniques, communes 100 % ANC servies
    # depuis M95) est RETIRÉ : la branche source_commune a disparu, l'échelle commune est portée
    # par l'INSEE RP2022 EGOUL (anc_maille_taux). Réservoirs restants : le taux INSEE + le zonage
    # SIG d'assainissement (parcel_anc, 4/24 communes GPU).
    reservoirs=("insee_rp2022_egoul", "gpu_zonage_assainissement",),
    portee="live"),
 "ventes_retenues_n": C("Ventes retenues (nuage)", "nombre", "parcelle",
    "ventes DVF retenues par le filtre de comparables (couverture VISIBLE — EXPORTS-1 lot 2)",
    moteur="marche_service", calcul="moteur",
    fonction="src/labuse/marche_service.py:filtre_ventes",
    reservoirs=("dvf",), portee="live"),
 "ventes_ecartees_n": C("Ventes écartées (nuage)", "nombre", "parcelle",
    "ventes DVF écartées par le filtre de comparables, avec motif (couverture visible)",
    moteur="marche_service", calcul="moteur",
    fonction="src/labuse/marche_service.py:filtre_ventes",
    reservoirs=("dvf",), portee="live"),
 "bilan_ca_eur": C("Chiffre d'affaires (bilan)", "€", "parcelle",
    "CA HT total = surface vendable × prix de sortie ÷ (1 + taux de TVA du régime saisi) "
    "(bilan à rebours) — part libre au prix de sortie, part sociale au prix de vente au bailleur ; "
    "décision Vic 07/09 : le bilan travaille HT",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py:compute_bilan (ca)",
    reservoirs=("dvf",), portee="live"),
 "bilan_cout_construction_eur": C("Coût de construction (bilan)", "€", "parcelle",
    "SDP × coût au m² (calibré secteur ou fourchette YAML), majoration pluviale comprise",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py:compute_bilan (cout_construction)",
    reservoirs=(), portee="live"),
 "bilan_vrd_eur": C("VRD (bilan)", "€", "parcelle",
    "VRD base × surface terrain, majorations pente/assainissement (bilan_params par secteur)",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py:compute_bilan (cout_vrd)",
    reservoirs=("rge_alti",), portee="live"),
 "bilan_marge_eur": C("Marge (bilan)", "€", "parcelle",
    "marge cible en % du CA (hypothèse déclarée, jamais cachée)",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py:compute_bilan (marge)",
    reservoirs=(), portee="live"),
 "bilan_frais_eur": C("Honoraires & frais (bilan)", "€", "parcelle",
    "honoraires + frais financiers en % (bilan_params par secteur, hypothèses affichées)",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py:compute_bilan (frais)",
    reservoirs=(), portee="live"),
 "ecart_prix_demande_pct": C("Écart au prix demandé", "%", "parcelle",
    "charge foncière supportable vs prix demandé SAISI (verdict d'achat de la calculette) — "
    "n'existe que si le client a saisi un prix",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py:compute_calculette (verdict d'achat)",
    reservoirs=(), portee="projet"),
 "bilan_demolition_eur": C("Démolition (bilan)", "€", "parcelle",
    "poste démolition du bilan à rebours — saisi par le client (le moteur ne l'estime pas)",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (poste à câbler)",
    reservoirs=(), portee="projet"),
 "sensibilite_cout_construction": C("Sensibilité au coût de construction", "%", "parcelle",
    "variation de la charge foncière pour ±10 % de coût de construction (tableau de sensibilité)",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (dérivable de compute_calculette)",
    reservoirs=(), portee="live"),
 # ═══════════════ EXPORTS-2 lot 0.4 — les chiffres du Financier ═══════════════
 # Créés en_attente : le builder d'exports (lots 1/5) les câble et lève l'attente ; tant
 # qu'aucun robinet ne les sert, verifier() reste vert. Bilan à rebours HT (décision Vic
 # 07/09), bornes de charge foncière, sensibilités, sorties dérivées, fait foncier (D-a).
 "bilan_frais_acquisition_eur": C("Frais d'acquisition (bilan)", "€", "parcelle",
    "frais d'acquisition = pourcentage saisi (7 % proposé) appliqué au prix d'achat retenu "
    "(notaire, mutation) + commission d'apporteur saisie — poste distinct de la charge foncière",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (EXPORTS-2 lot 5 — frais d'acquisition, à câbler)",
    reservoirs=(), portee="projet"),
 "bilan_honoraires_techniques_eur": C("Honoraires techniques (bilan)", "€", "parcelle",
    "honoraires techniques (maîtrise d'œuvre, BET, contrôle technique) = pourcentage saisi "
    "appliqué au coût de construction — distinct de la marge et des frais financiers",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (EXPORTS-2 lot 5 — honoraires techniques, à câbler)",
    reservoirs=(), portee="projet"),
 "bilan_stationnement_eur": C("Stationnement (bilan)", "€", "parcelle",
    "coût du stationnement = nombre de places × coût par place saisi selon le type (sol, "
    "sous-sol ou silo) — le sous-sol et le silo coûtent davantage que le sol",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (EXPORTS-2 lot 5 — stationnement, à câbler)",
    reservoirs=(), portee="projet"),
 "bilan_aleas_eur": C("Aléas (bilan)", "€", "parcelle",
    "provision pour aléas = pourcentage saisi appliqué au coût de construction (imprévus de "
    "chantier) — poste du bilan à rebours",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (EXPORTS-2 lot 5 — aléas, à câbler)",
    reservoirs=(), portee="projet"),
 "bilan_depollution_eur": C("Dépollution et étude de sol (bilan)", "€", "parcelle",
    "poste dépollution et étude de sol — saisi par le client (aucun référentiel public ne le "
    "chiffre) ; laissé vide, il s'imprime « non chiffré », jamais un zéro",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (EXPORTS-2 lot 5 — dépollution, à câbler)",
    reservoirs=(), portee="projet"),
 "bilan_portage_eur": C("Portage financier (bilan)", "€", "parcelle",
    "coût de portage = durée de portage saisie (mois) × taux saisi sur le foncier et les "
    "études, ou forfait si le client n'a pas saisi de taux",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (EXPORTS-2 lot 5 — portage, à câbler)",
    reservoirs=(), portee="projet"),
 "redevance_archeologie_eur": C("Redevance d'archéologie préventive (bilan)", "€", "parcelle",
    "redevance d'archéologie préventive = surface de plancher créée × taux légal (art. L524-7 "
    "du Code du patrimoine), assiette au-delà du seuil d'exonération",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (EXPORTS-2 lot 5 — redevance archéologie, à câbler)",
    reservoirs=(), portee="live"),
 "charge_fonciere_basse_eur": C("Charge foncière — borne basse", "€", "parcelle",
    "borne basse de la charge foncière supportable : coût de construction en haut de fourchette "
    "combiné au prix de sortie en bas — jamais un point seul (lot 5.3)",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (EXPORTS-2 lot 5 — borne basse de charge, à câbler)",
    reservoirs=(), portee="live"),
 "charge_fonciere_haute_eur": C("Charge foncière — borne haute", "€", "parcelle",
    "borne haute de la charge foncière supportable : coût de construction en bas de fourchette "
    "combiné au prix de sortie en haut — jamais un point seul (lot 5.3)",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (EXPORTS-2 lot 5 — borne haute de charge, à câbler)",
    reservoirs=(), portee="live"),
 "sensibilite_prix_sortie": C("Sensibilité au prix de sortie", "%", "parcelle",
    "variation de la charge foncière pour ±5 % de prix de sortie — second axe du tableau de "
    "sensibilité double 3×3 (avec sensibilite_cout_construction), lot 5.3",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (EXPORTS-2 lot 5 — sensibilité prix de sortie, à câbler)",
    reservoirs=(), portee="live"),
 "seuil_rentabilite_eur": C("Seuil de rentabilité (prix d'achat)", "€", "parcelle",
    "prix d'achat du foncier qui atteint exactement la marge visée saisie — le point mort de "
    "l'opération (lot 5.3)",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (EXPORTS-2 lot 5 — seuil de rentabilité, à câbler)",
    reservoirs=(), portee="projet"),
 "prix_revient_eur_m2": C("Prix de revient au m²", "€/m²", "parcelle",
    "prix de revient = (foncier retenu + tous les coûts) ÷ surface vendable, en €/m² habitable "
    "vendable (lot 5.3)",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (EXPORTS-2 lot 5 — prix de revient, à câbler)",
    reservoirs=(), portee="projet"),
 "prix_achat_historique_eur": C("Prix d'achat historique de la parcelle", "€", "parcelle",
    "dernier prix d'acquisition de la parcelle elle-même (mutation DVF sur l'IDU) avec sa date "
    "— fait foncier D-a ; « non disponible » si aucune mutation DVF n'est rattachée à la parcelle",
    moteur="marche_service", calcul="moteur",
    fonction="src/labuse/exports/robinet_fiche.py (EXPORTS-2 lot 2 — D-a, dvf_parcelle.derniere_mutation)",
    reservoirs=("dvf",), portee="live"),
 "mixite_seuil_m2": C("Mixité sociale — seuil de déclenchement", "m²", "parcelle",
    "seuil de surface de plancher au-delà duquel la clause de mixité sociale s'applique (source "
    "règlement de zone si déclarée, sinon Estimé) — distinct du quota et du déclenchement",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (EXPORTS-2 lot 5 — seuil de mixité, à câbler)",
    reservoirs=("gpu_plu_api_carto",), portee="live",
    en_attente="EXPORTS-2 — servi au chantier du Financier (lot 5)"),
 "mixite_quota_pct": C("Mixité sociale — quota de logements aidés", "%", "parcelle",
    "part de logements aidés imposée par la clause de mixité au-delà du seuil (source règlement "
    "de zone si déclarée, sinon Estimé) — distinct du seuil et du déclenchement",
    moteur="bilan_promoteur", calcul="moteur",
    fonction="src/labuse/faisabilite/bilan.py (EXPORTS-2 lot 5 — quota de mixité, à câbler)",
    reservoirs=("gpu_plu_api_carto",), portee="live",
    en_attente="EXPORTS-2 — servi au chantier du Financier (lot 5)"),
 # FICHE-1 lot 1 — tiroir « Le bien » : le bâti EXISTANT servi à la fiche (était en_attente
 # « maquettes d'exports »). Producteur unique bati.le_bien_block (aucun calcul au front).
 "emprise_batie_m2": C("Emprise bâtie", "m²", "parcelle",
    "emprise au sol du bâti — empreinte vecteur BD TOPO (somme des intersections), cohérente avec "
    "le nombre de bâtiments ; CoSIA servi À PART quand il détecte du bâti hors BD TOPO",
    moteur="bati_revele", calcul="moteur",
    fonction="src/labuse/bati.py:le_bien_block (BD TOPO au sol ; CoSIA parcel_bati_revele en note)",
    reservoirs=("bd_topo", "cosia",), portee="live"),
 "hauteur_bati_m": C("Hauteur du bâti", "m", "parcelle",
    "hauteur du bâti principal — max des bâtiments intersectants (BD TOPO) en fiche/potentiel ; "
    "l'extrusion 3D de la carte PRÉFÈRE le faîtage LiDAR HD mesuré (batiment_hauteur_lidar.faitage_m, "
    "flag `lidar` par bâtiment), repli BD TOPO",
    moteur="potentiel", calcul="moteur",
    fonction="src/labuse/faisabilite/potentiel.py:_hauteur_bati_m",
    # SOURCES-3 lot 1 — la hauteur bâtie servie à l'extrusion 3D de la carte (/map/batiments.geojson,
    # robinet couche_batiments_3d) est MESURÉE par le LiDAR HD quand la parcelle est ingérée : lidar_hd_mnh
    # est rattaché (clôture de la fuite « 303k à la carte » — la provenance dit désormais le LiDAR).
    reservoirs=("bd_topo", "lidar_hd_mnh",), portee="live"),
 "part_artificialisee_pct": C("Part artificialisée (OCS GE)", "%", "parcelle",
    "part de la parcelle artificialisée d'après l'OCS GE 2022 (matrice du décret 2023-1096, "
    "étape 1 — avant lissage des seuils réglementaires) — donnée d'îlot, jamais la précision "
    "cadastrale ; n'entre pas dans le score",
    moteur="bati_revele", calcul="moteur",
    fonction="src/labuse/bati.py:le_bien_block (parcel_ocsge — précalcul ingestion/ocsge.py)",
    reservoirs=("ocsge",), portee="live"),
 "usage_sol_dominant": C("Usage du sol dominant (OCS GE)", "classe", "parcelle",
    "code d'usage OCS GE dominant par aire intersectée (millésime 2022) — donnée d'îlot",
    moteur="bati_revele", calcul="moteur",
    fonction="src/labuse/bati.py:le_bien_block (parcel_ocsge — précalcul ingestion/ocsge.py)",
    reservoirs=("ocsge",), portee="live",
    domaine=None, domaine_source="nomenclature OCS GE (IGN)"),
 # DONNEES-2 — CoSIA (IGN, 20 cm) COMPLÈTE OCS GE : la couverture du sol de la PARCELLE elle-même,
 # en 3 parts (Σ surface de classe CoSIA / contenance). Ni doublon ni remplacement d'OCS GE (donnée
 # d'îlot, part ARTIFICIALISÉE) : « imperméabilisé » ≠ « artificialisé », et la maille est la parcelle
 # à 20 cm. Aucune ne recoupe exactement une ligne OCS GE affichée. N'entrent pas dans le score.
 "part_impermeabilisee_cosia_pct": C("Part imperméabilisée (CoSIA)", "%", "parcelle",
    "part de la parcelle scellée (bâti + revêtement imperméable + piscine + serre) mesurée par "
    "CoSIA à 20 cm, Σ surface de ces classes / contenance — complète l'artificialisation OCS GE "
    "d'îlot (≠ imperméabilisé), ne recoupe aucune ligne OCS GE affichée ; hors score",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/bati.py:le_bien_block (_cosia_couverture — part_impermeabilisee_pct)",
    reservoirs=("cosia",), portee="live", table="parcel_cosia_couverture"),
 "part_vegetalisee_cosia_pct": C("Part végétalisée/boisée (CoSIA)", "%", "parcelle",
    "part de la parcelle en végétation vivante (feuillu, conifère, broussaille, pelouse, culture, "
    "vigne) mesurée par CoSIA à 20 cm, Σ surface de ces classes / contenance — donnée de parcelle, "
    "aucune ligne OCS GE affichée ne la donne ; hors score",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/bati.py:le_bien_block (_cosia_couverture — part_vegetalisee_boisee_pct)",
    reservoirs=("cosia",), portee="live", table="parcel_cosia_couverture"),
 "part_sol_nu_cosia_pct": C("Part sol nu (CoSIA)", "%", "parcelle",
    "part de la parcelle en terre nue (sol nu, terre labourée) mesurée par CoSIA à 20 cm, Σ surface "
    "de ces classes / contenance — donnée de parcelle, aucune ligne OCS GE affichée ne la donne ; hors score",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/bati.py:le_bien_block (_cosia_couverture — part_sol_nu_pct)",
    reservoirs=("cosia",), portee="live", table="parcel_cosia_couverture"),
 "zan_evolution_commune": C("Artificialisation 2017→2022 (OCS GE)", "m²", "commune",
    "surface artificialisée entre les millésimes OCS GE 2017 et 2022, par commune — produit "
    "différentiel OFFICIEL IGN (flags artif du portail de l'artificialisation) ; la pression "
    "ZAN a sa source officielle",
    moteur="commune_compteurs", calcul="moteur",
    fonction="src/labuse/registre/moteurs/commune.py:zan_ocsge_commune (ocsge_evolution)",
    reservoirs=("ocsge",), portee="live"),
 "ban_plus_adresses_bati": C("Adresses liées au bâti (BAN PLUS)", "nombre", "parcelle",
    "nombre de liens officiels adresse ↔ bâtiment de la parcelle (BAN PLUS, IGN) — la clé qui "
    "relie l'adresse BAN au bâtiment BD TOPO et, par le RNB local, à l'ID-RNB",
    moteur="bati_revele", calcul="moteur",
    fonction="src/labuse/bati.py:le_bien_block (liens adresse↔bâtiment — ban_plus_liens)",
    reservoirs=("ban_plus",), portee="live"),
 "rnb_batiments_liste": C("Identifiants RNB des bâtiments", "liste", "parcelle",
    "identifiant national (RNB) de chaque bâtiment ACTIF dont l'emprise recoupe la parcelle, "
    "du plus grand recouvrement au plus petit, avec le lien officiel rnb.beta.gouv.fr",
    moteur="bati_revele", calcul="moteur",
    fonction="src/labuse/bati.py:le_bien_block (RNB actifs ∩ parcelle — rnb_batiments)",
    reservoirs=("rnb",), portee="live"),
 "n_batiments": C("Nombre de bâtiments", "nombre", "parcelle",
    "compte des bâtiments de la parcelle (BD TOPO, intersection ≥ 10 m²)",
    moteur="bati_revele", calcul="moteur",
    fonction="src/labuse/bati.py:le_bien_block (bati.fiche_block — BD TOPO)",
    reservoirs=("bd_topo",), portee="live"),
 "surface_libre_sol_m2": C("Surface au sol libre", "m²", "parcelle",
    "surface au sol non bâtie restante (surface parcelle − emprise bâtie), plancher à 0",
    moteur="bati_revele", calcul="moteur",
    fonction="src/labuse/bati.py:le_bien_block (surface parcelle − emprise bâtie)",
    reservoirs=("bd_topo", "cosia", "cadastre_api_carto",), portee="live"),
 "nature_toit": C("Nature du toit", "classe", "parcelle",
    "forme du toit du plus grand bâtiment lue sur le LiDAR HD (MNH), servie ≥ 0,70 de confiance "
    "sinon « non déterminée — pans non nets » (RETOURS-15 U5)",
    moteur="solaire", calcul="moteur",
    fonction="src/labuse/solaire_toiture.py:analyse_toiture (cache toiture_lidar, lecture fiche)",
    reservoirs=("lidar_hd_mnh", "bd_topo",), portee="live", type="classe",
    domaine=("plat", "monopente", "double_pente", "croupe_complexe"),
    domaine_source="classification LiDAR HD (solaire_toiture, seuil 0,70)"),
 "pente_toit_deg": C("Pente du toit", "nombre", "parcelle",
    "pente médiane du toit du plus grand bâtiment (degrés), mesure directe LiDAR HD (MNH) — "
    "servie même sous le seuil de forme",
    moteur="solaire", calcul="moteur",
    fonction="src/labuse/solaire_toiture.py:analyse_toiture (cache toiture_lidar, lecture fiche)",
    reservoirs=("lidar_hd_mnh",), portee="live"),
 # ══ SOURCES-1 lot 1 — les réglementaires du droit des sols SERVIES (en_attente levée) ══
 # Déclarées par FICHE-1 lot 7 (« non calculée — source absente ») ; les réservoirs sont
 # ingérés, les données servies au bloc fiche « Dispositifs et périmètres » (_dispositifs_block).
 "er_emplacement_reserve": C("Emplacement réservé (ER)", "classe", "parcelle",
    "la parcelle est-elle grevée d'un emplacement réservé du PLU (destination, part de la "
    "parcelle) — famille ER = typepsc 05 + rescue/veto libellé (source unique cascade_rules)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/app.py:_dispositifs_block (er)",
    reservoirs=("gpu_prescriptions_er",), portee="live", type="classe",
    table="spatial_layers (kind=plu_gpu_prescription, famille ER)",
    domaine=("grevee", "non_grevee"), domaine_source="prescriptions surfaciques du GPU"),
 "ebc_classe": C("Espace boisé classé (EBC)", "classe", "parcelle",
    "la parcelle intersecte-t-elle un espace boisé classé du PLU (part de la parcelle ; part "
    "soustraite de l'assiette du bloc potentiel — L113-1 CU)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/app.py:_dispositifs_block (ebc)",
    reservoirs=("gpu_prescriptions_ebc",), portee="live", type="classe",
    table="spatial_layers (kind=plu_gpu_prescription, typepsc 01)",
    domaine=("intersecte", "hors"), domaine_source="prescriptions surfaciques du GPU"),
 "dpu_perimetre": C("Droit de préemption urbain (DPU)", "classe", "parcelle",
    "la parcelle est-elle dans un périmètre de préemption publié (DPU simple/renforcé) — les "
    "communes sans DPU publié au GPU sont « non déterminée — non publié par la commune »",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/app.py:_dispositifs_block (dpu)",
    reservoirs=("dpu_perimetres",), portee="live", type="classe",
    table="spatial_layers (kind=dpu)",
    domaine=("simple", "renforce", "hors", "non_publie"),
    domaine_source="informations surfaciques du GPU (typeinf 04)"),
 "peb_zone": C("Plan d'exposition au bruit (PEB)", "classe", "parcelle",
    "zone PEB de l'aérodrome (A/B/C/D) si la parcelle y est — Roland-Garros servi (annexes "
    "GPU) ; Pierrefonds non publié au GPU (couverture partielle dite)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/app.py:_dispositifs_block (peb)",
    reservoirs=("peb_dgac",), portee="live", type="classe",
    table="spatial_layers (kind=peb)",
    domaine=("A", "B", "C", "D", "hors"), domaine_source="zones du PEB (arrêté préfectoral)"),
 "zonage_abc_logement": C("Zonage A/B/C (logement)", "classe", "commune",
    "zone A/B/C du dispositif d'investissement locatif pour la commune (arrêté du 23/06/2026, "
    "en vigueur 26/06/2026 — passe-plat, jamais recalculé)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/ingestion/zonage_abc.py:zonage_commune",
    reservoirs=("zonage_abc_dhup",), portee="live", type="classe",
    table="commune_zonage_abc",
    domaine=("Abis", "A", "B1", "B2", "C"),
    domaine_source="arrêté de zonage A/B/C (D. 304-1 CCH, 23/06/2026)"),
 # ── COMMUNE-RANGEMENT-1 lot 4 — ZFANG / FRR de la commune (carte « ZFANG / FRR » de la fiche commune) :
 #    passe-plats depuis territoire_fiscal_commune, la SOURCE UNIQUE qui peint aussi la carte (dispositifs.py)
 #    et filtre les parcelles. Deux classes, jamais recalculées. ──
 "zfang_regime_commune": C("ZFANG — régime de la commune", "classe", "commune",
    "régime ZFANG de la commune (standard | renforcé) — passe-plat depuis territoire_fiscal_commune, "
    "la même source qui peint la carte des dispositifs et filtre les parcelles ; jamais recalculé",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/territoire_fiscal.py:attributs_commune",
    reservoirs=("zfang",), portee="live", type="classe",
    table="territoire_fiscal_commune.zfang_regime",
    domaine=("standard", "renforce"),
    domaine_source="zonage ZFANG (loi de finances)"),
 "frr_classement_commune": C("FRR — classement de la commune", "classe", "commune",
    "classement France Ruralités Revitalisation de la commune (totalité | partie (les Hauts) | hors) — "
    "passe-plat depuis territoire_fiscal_commune ; jamais recalculé",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/territoire_fiscal.py:attributs_commune",
    reservoirs=("frr_ex_zrr",), portee="live", type="classe",
    table="territoire_fiscal_commune.frr_classement",
    domaine=("totalite", "partie", "hors"),
    domaine_source="arrêté FRR (ex-ZRR)"),
 # ── SOURCES-1 lot 1 — les couches carte du droit des sols ──
 "er_couche": C("Emplacements réservés (couche)", "couche", "commune",
    "emplacements réservés des PLU (prescriptions GPU typepsc 05) — emprise grevée au profit "
    "d'un projet public",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (plu_gpu_prescription/05)",
    reservoirs=("gpu_prescriptions_er",), portee="live",
    type="couche", table="spatial_layers (kind=plu_gpu_prescription, subtype=05)", fabrication="requete"),
 "ebc_couche": C("Espaces boisés classés (couche)", "couche", "commune",
    "espaces boisés classés des PLU (prescriptions GPU typepsc 01) — toute construction "
    "interdite sur l'emprise boisée (L113-1 CU)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (plu_gpu_prescription/01)",
    reservoirs=("gpu_prescriptions_ebc",), portee="live",
    type="couche", table="spatial_layers (kind=plu_gpu_prescription, subtype=01)", fabrication="requete"),
 "dpu_couche": C("Droit de préemption urbain (couche)", "couche", "commune",
    "périmètres de préemption urbaine publiés au GPU (typeinf 04) — communes non publiées "
    "listées à la source",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (dpu)",
    reservoirs=("dpu_perimetres",), portee="live",
    type="couche", table="spatial_layers (kind=dpu)", fabrication="requete"),
 "peb_couche": C("Plan d'exposition au bruit (couche)", "couche", "global",
    "zones A/B/C/D des PEB republiés au GPU (Roland-Garros ; Pierrefonds non publié)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (peb)",
    reservoirs=("peb_dgac",), portee="live",
    type="couche", table="spatial_layers (kind=peb)", fabrication="requete"),
 "sup_couche": C("Servitudes d'utilité publique (couche)", "couche", "commune",
    "assiettes des SUP publiées pour le 974, une sous-couche par catégorie (AC1, AC2, AC3, "
    "AC4, PM1, PM2, PM3, EL10 en base ; T5/PT1/PT2 publiées mais restreintes au "
    "téléchargement ; AS1 et les autres non publiées — inventaire sondé)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (sup)",
    reservoirs=("sup_gpu",), portee="live",
    type="couche", table="spatial_layers (kind=sup, subtype=catégorie)", fabrication="requete"),
 # ── SOURCES-1 lot 2 — la nature et l'eau ──
 "dpf_couche": C("Ravines et reculs — DPF (couche)", "couche", "global",
    "domaine public fluvial DEAL (275 tronçons + 6 plans d'eau, arrêté 06-3077 du 21/08/2006) "
    "— servitude de marchepied 3,25 m rédhibitoire (L2131-2 CGPPP)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (dpf)",
    reservoirs=("deal_dpf_dpe",), portee="live",
    type="couche", table="spatial_layers (kind=dpf)", fabrication="requete"),
 "zone_humide_couche": C("Zones humides (couche)", "couche", "global",
    "inventaires DEAL par secteurs (2003, 2009 + espaces fonctionnels, habitats 2011, basse "
    "altitude 2019) — couverture partielle dite, l'absence n'est pas une preuve",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (zone_humide)",
    reservoirs=("deal_zones_humides",), portee="live",
    type="couche", table="spatial_layers (kind=zone_humide)", fabrication="requete"),
 # TESTS-1 lot 2 — les DEUX robinets couche de SOURCES-2/3 (artificialisation, bâti 3D) pointaient
 # des scalaires sans donnée de type « couche » (le patron du registre : chaque robinet couche sert
 # LA couche elle-même, avec sa table et sa fabrication — test_circuit2_lot1).
 "artificialisation_couche": C("Artificialisation OCS GE (couche)", "couche", "global",
    "polygones artificialisés OCS GE (matrice du décret 2023-1096) peints sous le cadastre — "
    "donnée d'îlot, millésime 2022",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/couches_tuyau.py:couche_tuile (artificialisation)",
    reservoirs=("ocsge",), portee="live",
    type="couche", table="spatial_layers (kind=artificialisation)", fabrication="requete"),
 "batiments_3d_couche": C("Bâti 3D — extrusion (couche)", "couche", "global",
    "empreintes bâties de la BBOX avec hauteur pour l'extrusion 3D (BD TOPO ; faîtage LiDAR HD "
    "mesuré préféré, flag lidar par bâtiment) — sans hauteur, jamais d'extrusion inventée",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/app.py:map_batiments_geojson",
    reservoirs=("bd_topo", "lidar_hd_mnh",), portee="live",
    type="couche", table="spatial_layers (kind=batiment) + batiment_hauteur_lidar", fabrication="requete"),
 "enp_couche": C("Espaces naturels protégés (couche)", "couche", "global",
    "ENP par type (réserves naturelles dont marine, APB, conservatoire du littoral, réserves "
    "biologiques, Ramsar, sites classés/inscrits) — INPN + compléments DEAL Carmen",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (ens)",
    reservoirs=("inpn_espaces_proteges", "enp_complements_deal",), portee="live",
    type="couche", table="spatial_layers (kind=ens, subtype=type)", fabrication="requete"),
 "rpg_couche": C("Cultures déclarées — RPG (couche)", "couche", "commune",
    "déclarations agricoles RPG (38 460, code culture — canne CSA dominante) ; en zone A : "
    "canne ≥ 50 % rédhibitoire, absence de déclaration = friche possible (vigilance)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (safer)",
    reservoirs=("rpg_proxy_ign",), portee="live",
    type="couche", table="spatial_layers (kind=safer)", fabrication="requete"),
 "azi_tri_commune": C("AZI / TRI de la commune", "liste", "commune",
    "atlas des zones inondables et TRI couvrant la commune (GASPAR : libellé, risques, date) "
    "— fait documentaire ; la géométrie d'aléa reste servie par georisque_alea",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/ingestion/azi_tri.py:azi_tri_commune",
    reservoirs=("georisques_azi_tri",), portee="live", type="liste",
    table="azi_communes"),
 "dispositifs_parcelle": C("Dispositifs et périmètres (parcelle)", "liste", "parcelle",
    "liste des dispositifs du droit des sols touchant la parcelle (ER avec part, EBC avec "
    "part, DPU, zone PEB, SUP par catégorie) — intersections live des couches servies, mêmes "
    "seuils que la cascade (source unique cascade_rules.yaml)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/app.py:_dispositifs_block",
    reservoirs=("gpu_prescriptions_er", "gpu_prescriptions_ebc", "dpu_perimetres",
                "peb_dgac", "sup_gpu",), portee="live", type="liste",
    table="spatial_layers (kinds plu_gpu_prescription/dpu/peb/sup)"),
 # ══ SOURCES-1 lot 5 — la valeur ══
 "fibre_parcelle": C("Fibre (raccordable FttH)", "classe", "parcelle",
    "raccordabilité FttH de l'immeuble Arcep le plus proche de la parcelle (≤ 100 m, "
    "DISTANCE DITE — jamais un booléen nu) + opérateurs présents ; « aucun immeuble » est "
    "un état, pas un zéro",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/ingestion/arcep_fibre.py:fibre_parcelle",
    reservoirs=("arcep_fibre",), portee="live", type="classe",
    table="arcep_immeubles",
    domaine=("raccordable", "non_raccordable", "aucun_immeuble"),
    domaine_source="éligibilité FttH Arcep (Ma connexion internet, IPE)"),
 "tfpb_taux_pct": C("Taxe foncière (taux TFPB)", "%", "commune",
    "taux de TFPB appliqué sur la commune (E12 du REI) + part EPCI (E32) + TEOM (F22) — "
    "impositions primitives, passe-plat du fichier DGFiP",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/ingestion/rei.py:rei_commune",
    reservoirs=("dgfip_rei",), portee="live", table="commune_rei"),
 # SOURCES-4 lot 2 — la TFPNB (foncier NON bâti, la plus pertinente pour un terrain) était
 # ingérée mais jamais servie ; désormais au bloc fiscalité. CFE et bases nettes restent en base
 # (commune_rei), disponibles, non affichées (pas de chiffre servi → hors registre servi).
 "tfpnb_taux_pct": C("Taxe foncière non bâti (taux TFPNB)", "%", "commune",
    "taux de TFPNB appliqué sur la commune (B12 du REI) + part EPCI (B32) — impositions "
    "primitives, passe-plat du fichier DGFiP (foncier non bâti = terrain)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/ingestion/rei.py:rei_commune",
    reservoirs=("dgfip_rei",), portee="live", table="commune_rei (tfpnb_commune_pct, tfpnb_epci_pct)"),
 # COMMUNE-FIX-1 (D10) — le TAUX communal de taxe d'aménagement (part communale) servi sur la carte
 # Fiscalité de la fiche commune. MÊME source que l'outil Taxe (taxe_amenagement_taux, DGFiP/DELTA).
 "taxe_amenagement_communale_pct": C("Taxe d'aménagement (part communale)", "%", "commune",
    "taux de la part communale de la taxe d'aménagement (délibération communale), même source "
    "que l'outil Taxe — passe-plat de taxe_amenagement_taux (DGFiP, application DELTA)",
    moteur="taxe_amenagement", calcul="passe_plat",
    fonction="src/labuse/api/fiche_commune.py:taxe_amenagement",
    reservoirs=("taxe_amenagement",), portee="live", table="taxe_amenagement_taux.part_communale_pct"),
 "ort_statut": C("ACV / PVD / ORT", "classe", "commune",
    "statut du dispositif de revitalisation de la commune (table DGALN) + convention ORT "
    "signée (date) + condition communale Denormandie DITE (le périmètre conventionné "
    "n'est pas publié)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/ingestion/ort.py:ort_commune",
    reservoirs=("anct_ort",), portee="live", type="classe", table="commune_ort",
    domaine=("acv", "pvd", "autre", "hors"),
    domaine_source="table DGALN des communes ORT (flags ACV/PVD)"),
 "cout_construction_ref_eur_m2": C("Coût de construction (référence)", "€/m²", "global",
    "fourchette de coût de construction SERVIE au bilan promoteur (ligne labuse_promotion "
    "de cout_construction_ref, 2 300-2 800 €/m² SDP — choix LABUSE sourcé, contexte EPTB "
    "2024 en table) ; lue par Hypotheses.charger, repli constantes",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/faisabilite/engine.py:_couts_construction_reference",
    reservoirs=("cout_construction_sdes",), portee="live", table="cout_construction_ref"),
 # ══ SOURCES-1 lot 3 — les sols et le bruit ══
 "sis_classe": C("Secteur d'information sur les sols (SIS)", "classe", "parcelle",
    "la parcelle est-elle dans un périmètre SIS (étude de sols obligatoire au changement "
    "d'usage L556-2 CE ; information écrite de l'acheteur/locataire obligatoire L125-7 CE)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/app.py:_sols_block (sis)",
    reservoirs=("georisques_sis",), portee="live", type="classe",
    table="spatial_layers (kind=sol_pollue, subtype=sis)",
    domaine=("dans", "hors"), domaine_source="périmètres SIS Géorisques (L125-6 CE)"),
 "casias_statut": C("Ancien site industriel (CASIAS)", "classe", "parcelle",
    "site CASIAS/instruction sur la parcelle ou à moins de 100 m — inventaire historique, "
    "pas une pollution avérée (le libellé le dit)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/app.py:_sols_block (casias)",
    reservoirs=("georisques_casias",), portee="live", type="classe",
    table="spatial_layers (kind=sol_pollue, subtypes casias/instruction)",
    domaine=("sur_place", "proche_100m", "hors"),
    domaine_source="CASIAS/instructions Géorisques (canal SSP)"),
 # FICHE-RANGEMENT-1 Lot 3 — orphelin déclaré : la parcelle est-elle dans une zone protégée
 # derrière un système d'endiguement (cascade risques, FICHE-COUCHES-2). Donnée réelle et servie.
 "endiguement_zone_protegee": C("Système d'endiguement", "classe", "parcelle",
    "la parcelle est-elle dans une ZONE PROTÉGÉE derrière une digue — information : la protection "
    "n'est pas une garantie d'inconstructibilité mais un fait à instruire (aléa résiduel)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/cascade/layers/fiche_couches2.py (endiguement)",
    reservoirs=("endiguement",), portee="live", type="classe",
    table="spatial_layers (kind=endiguement)",
    domaine=("dans", "hors"),
    domaine_source="systèmes d'endiguement DEAL Réunion (Lizmap)"),
 "sis_couche": C("Secteurs d'information sur les sols (couche)", "couche", "commune",
    "périmètres SIS réglementaires (4 au 974 : Le Port, Saint-Benoît, Saint-Louis, "
    "Sainte-Marie)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (sol_pollue/sis)",
    reservoirs=("georisques_sis",), portee="live",
    type="couche", table="spatial_layers (kind=sol_pollue, subtype=sis)", fabrication="requete"),
 "casias_couche": C("Anciens sites industriels (couche)", "couche", "commune",
    "sites CASIAS et instructions en cours (inventaire historique, pas une pollution avérée)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (sol_pollue/casias)",
    reservoirs=("georisques_casias",), portee="live",
    type="couche", table="spatial_layers (kind=sol_pollue, subtypes casias/instruction)",
    fabrication="requete"),
 "bruit_couche": C("Classement sonore (couche)", "couche", "commune",
    "bandes des secteurs affectés par le bruit (largeur réglementaire sect_bruit par axe, "
    "catégories 1-5 — arrêtés préfectoraux des 14-15/12/2023, R571-32 CE)",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (bruit_route)",
    reservoirs=("bruit_itt_cerema",), portee="live",
    type="couche", table="spatial_layers (kind=bruit_route)", fabrication="requete"),
 "bruit_carte_couche": C("Cartes de bruit — dépassements (couche)", "couche", "global",
    "zones de dépassement des valeurs limites Lden 68 / Ln 62 dB(A) des cartes de bruit "
    "stratégiques 2022 (RN/RD/VC) — ≠ classement sonore réglementaire",
    moteur=None, calcul="passe_plat", fonction="src/labuse/api/couches_tuyau.py:couche_tuile (bruit_carte)",
    reservoirs=("deal_bruit_cartes",), portee="live",
    type="couche", table="spatial_layers (kind=bruit_carte)", fabrication="requete"),
 "sols_parcelle": C("Sols (SIS/CASIAS, parcelle)", "liste", "parcelle",
    "l'état des sols de la parcelle : périmètre SIS intersecté, site CASIAS/instruction le "
    "plus proche (≤ 100 m) — intersections live des couches servies, mêmes règles que la "
    "cascade sol_pollue",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/api/app.py:_sols_block",
    reservoirs=("georisques_sis", "georisques_casias",), portee="live", type="liste",
    table="spatial_layers (kind=sol_pollue)"),
 # ══ SOURCES-1 lot 6 — le foncier et les gens ══
 "filiation_parcelle": C("Historique cadastral (filiation DFI)", "liste", "parcelle",
    "la généalogie OFFICIELLE de la parcelle : d'où elle vient (mères), ce qu'elle est "
    "devenue (filles), nature et date de chaque événement (DFI DGFiP) — passe-plat trié ; "
    "absence NORMALE (informatisation 1980-90+, aménagements fonciers exclus) ; contrôle "
    "croisé avec le cadastre d'époque (géométrie), jamais un conflit",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/ingestion/dfi.py:filiation_parcelle",
    reservoirs=("dgfip_dfi",), portee="live", type="liste", table="dfi_filiation"),
 "iris_quartier": C("Quartier INSEE (IRIS)", "liste", "parcelle",
    "le quartier INSEE de la parcelle (IRIS, contours géographie 2024) : logements, vacance, "
    "âge du bâti (part ≤ 1990), taille des ménages (NPER_RP/RP), part 60 ans et +, part "
    "locataires/HLM — RP2022, maille IRIS DITE (affine la commune, ne la remplace pas)",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/ingestion/iris_rp.py:stats_iris (iris_de_parcelle)",
    reservoirs=("insee_rp_iris", "contours_iris",), portee="live", type="liste",
    table="iris_rp"),
 "iris_commune_quartiers": C("Quartiers de la commune (IRIS)", "liste", "commune",
    "l'affinage par quartier de la vérité communale : n IRIS, vacance min/médiane/max par "
    "IRIS (RP2022) — commune_insee_logement reste la vérité communale",
    moteur=None, calcul="passe_plat",
    fonction="src/labuse/ingestion/iris_rp.py:quartiers_commune",
    reservoirs=("insee_rp_iris",), portee="live", type="liste", table="iris_rp"),
}

#: 1.1 — le type des déclarations « auto » est dérivé de l'unité (les entrées historiques de
#: CIRCUIT-1 restent des littéraux inchangés ; les nouvelles déclarations posent `type=`).
DONNEES = {cid: (replace(d, type=_TYPE_PAR_UNITE.get(d.unite, "nombre")) if d.type == "auto" else d)
           for cid, d in DONNEES.items()}

#: rétro-compatibilité CIRCUIT-1 — le registre des chiffres EST le registre des données
CHIFFRES = DONNEES

#: 0-bis (scission du neuf) : l'ancien id `prix_neuf_vefa_eur_m2` recouvrait DEUX définitions
#: (fuite mesurée de CIRCUIT-0, soldée par scission acte/observé). L'alias de transition a vécu
#: UN lot comme prévu puis a été RETIRÉ (lot 6) : plus aucun lecteur de l'ancien id nulle part
#: (vérifié par grep + test) — le dict reste comme mécanisme pour une prochaine scission.
ALIAS_TRANSITION: dict[str, str] = {}


def resoudre(chiffre_id: str) -> str:
    """Résout un id d'alias de transition vers l'id canonique (identité sinon)."""
    return ALIAS_TRANSITION.get(chiffre_id, chiffre_id)


#: CIRCUIT-5 lot 5.1 — les SEULES définitions partagées assumées (deux ids, même phrase de
#: définition) : chaque groupe est motivé ici et dans CONCEPTS-CANONIQUES.md ; toute autre
#: collision de libellé normalisé ou de définition casse le verrou V5a (un concept = un id).
DEFINITIONS_PARTAGEES_ASSUMEES: tuple[frozenset[str], ...] = (
    # deux HYPOTHÈSES saisies par le client dans la calculette : même phrase (« jamais un
    # chiffre LABUSE »), deux grandeurs distinctes (coût €/m² · marge %).
    frozenset({"cout_construction_saisi_eur_m2", "marge_frais_saisie_pct"}),
    # cinq mosaïques ortho IGN d'époques différentes : même définition générique, la PÉRIODE
    # est dans l'id et le libellé.
    frozenset({"tuiles_ortho_2000_2005", "tuiles_ortho_2006_2010", "tuiles_ortho_2011_2015",
               "tuiles_ortho_2016_2020", "tuiles_ortho_2021_2023"}),
)
