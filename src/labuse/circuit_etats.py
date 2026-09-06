"""CIRCUIT-P (lot 1.4) — LA FONCTION D'ÉTAT UNIQUE, côté serveur.

Un réservoir et un robinet portent chacun UNE couleur et UN libellé court, calculés ICI et nulle
part ailleurs : le front ne recalcule rien (règle 1.4). C'est la transposition fidèle de
`tankEtat` / `tapEtat` de `docs/CIRCUIT/maquette-circuit-v8.html` (la référence visuelle validée
par Vic le 06/09/2026) sur les VRAIES données de l'endpoint `/admin/circuit`.

Cinq couleurs, une par sens (règle 6) :
  · mint  — ça coule       · ambre — à regarder
  · rouge — bloqué / fuite  · gris — vide / manuel   · mauve — agent / IA

Ce module porte aussi les DEUX regroupements d'affichage : la famille d'affichage d'un réservoir
(la colonne `category` de `data_sources` est fine — 28 valeurs ; la maquette les range en
familles lisibles) et la catégorie d'affichage d'un robinet (le champ `categorie` du registre est
un slug court). L'ORDRE est celui de la maquette.

Divergences avec la maquette, tranchées par l'option la plus sûre et écrites (règle d'autonomie) :
  · la maquette a des états qu'AUCUNE donnée live ne porte encore — `horloge qui ment`,
    `écart à la règle`, `choix LABUSE`, `agent en route`. On les GARDE dans la grammaire (couleur +
    libellé), déclenchés par un champ que le live ne remplit pas encore ; CIRCUIT-4 (règles) et un
    détecteur d'horloge les brancheront (accroche notée au compte-rendu). Live : 0 faux positif.
  · `à vérifier (cadence dépassée)` (le drapeau réel `a_verifier`) n'existe pas dans la maquette :
    on l'ajoute en ambre (« à regarder »), dans la même grammaire.
  · CIRCUIT-P2 (lot 2.1) — « hors moteur » ne désigne QUE `sql_propre` et `front` (un chiffre qui
    court-circuite le moteur : SQL brut servi ou calcul fait au front) ; ceux-là doivent être à 0
    depuis CIRCUIT-2. Un `passe_plat` (une valeur brute d'un réservoir servie telle quelle, déclarée
    au registre) est NEUTRE, pas « hors moteur ». `constante` est délibéré. Seuls `moteur` et
    `passe_plat` alimentent normalement un robinet ; `sql_propre`/`front` sont la régression à voir.
"""
from __future__ import annotations

# ── CIRCUIT-P2 (lot 2.1) — les préfixes de `calcul` qui court-circuitent le moteur (à rebrancher).
#    Un `passe_plat` (valeur brute déclarée) et une `constante` ne comptent PAS : état neutre. ──
HORS_MOTEUR_PREFIXES = ("sql_propre", "front")

def est_hors_moteur(calcul: str | None) -> bool:
    """Un chiffre est-il servi HORS moteur ? (SQL brut ou calcul au front — jamais un passe-plat.)"""
    return (calcul or "").split(":")[0] in HORS_MOTEUR_PREFIXES

# ── familles d'affichage : slug fin (data_sources.category) → famille lisible, DANS L'ORDRE ──
FAMILLES_ORDRE = [
    "Parcelles et propriété",
    "Urbanisme et règles",
    "Risques, nature, patrimoine",
    "Marché, logement, permis",
    "Énergie, réseaux, assainissement",
    "Économie, équipements, accès",
    "Terrain, sol, imagerie",
    "Hubs et catalogues",
    "Voulues, absentes",
    "LABUSE interne",
]
FAMILLE_DE_CATEGORIE = {
    "cadastre": "Parcelles et propriété", "potentiel": "Parcelles et propriété",
    "proprietaire": "Parcelles et propriété", "foncier": "Parcelles et propriété",
    "urbanisme": "Urbanisme et règles", "fiscal": "Urbanisme et règles",
    "reglementaire": "Urbanisme et règles", "reglement": "Urbanisme et règles",
    "risques": "Risques, nature, patrimoine", "environnement": "Risques, nature, patrimoine",
    "agricole": "Risques, nature, patrimoine", "patrimoine": "Risques, nature, patrimoine",
    "signal": "Risques, nature, patrimoine",
    "marche": "Marché, logement, permis", "dynamique": "Marché, logement, permis",
    "logement": "Marché, logement, permis",
    "reseaux": "Énergie, réseaux, assainissement", "energie": "Énergie, réseaux, assainissement",
    "assainissement": "Énergie, réseaux, assainissement",
    "acces": "Économie, équipements, accès", "attractivite": "Économie, équipements, accès",
    "economie": "Économie, équipements, accès",
    "topographie": "Terrain, sol, imagerie", "occupation_sol": "Terrain, sol, imagerie",
    "imagerie": "Terrain, sol, imagerie", "terrain": "Terrain, sol, imagerie",
    "hub": "Hubs et catalogues",
    "aucune": "Voulues, absentes",
    "interne": "LABUSE interne", "labuse": "LABUSE interne",
}

def famille_affichage(categorie: str | None) -> str:
    """La famille lisible d'un réservoir depuis sa `category` fine ; défaut : « Autres »."""
    return FAMILLE_DE_CATEGORIE.get((categorie or "aucune"), "Autres")


# ── catégories d'affichage des robinets : slug registre → libellé lisible, DANS L'ORDRE ──
CATEGORIES_ORDRE = [
    ("fond", "Fonds de carte"), ("couche", "Couches"), ("outil", "Outils"),
    ("fiche", "Fiches"), ("copilote", "Copilote"), ("veille", "Veille"),
    ("projets", "Projets"), ("crm", "CRM"), ("notification", "Notifications"),
    ("pdf", "PDF"), ("page_client", "Pages client"), ("admin", "Admin"),
]
CATEGORIE_LIBELLE = dict(CATEGORIES_ORDRE)

def categorie_affichage(slug: str | None) -> str:
    return CATEGORIE_LIBELLE.get(slug or "", (slug or "?").capitalize())


# ── pont nom → slug de réservoir (reservoirs.csv, inventaire validé) : relie une ligne
#    data_sources (id numérique + nom) au slug du registre, pour allumer réservoir → catégories.
#    Un réservoir absent de ce pont s'allume seul (comportement d'avant CIRCUIT-P), sans erreur. ──
NOM_VERS_SLUG = {
    'Cadastre (API Carto PCI)': 'cadastre_api_carto',
    'Cadastre Etalab (bulk DGFiP/Etalab)': 'cadastre_etalab_bulk',
    'Urbanisme PLU/GPU (API Carto)': 'gpu_plu_api_carto',
    'Géorisques': 'georisques_api',
    'DVF / valeurs foncières': 'dvf',
    'RGE ALTI (altimétrie)': 'rge_alti',
    'Parc National de La Réunion (INPN)': 'parc_national_inpn',
    'Forêts publiques (ONF)': 'forets_onf_bdtopo',
    'Potentiel foncier Région (Région ODS)': 'potentiel_foncier_region',
    'RPG — déclarations agricoles (IGN/ASP)': 'rpg_proxy_ign',
    'Région Réunion Open Data (Opendatasoft)': 'region_ods_hub',
    'PEIGEO (hub régional)': 'peigeo_hub',
    'DEAL Réunion (WMS/WFS)': 'deal_wms_wfs',
    'Géoplateforme IGN': 'geoplateforme_hub',
    'data.regionreunion.com — Potentiel foncier': 'potentiel_foncier_ods',
    "SITADEL (autorisations d'urbanisme)": 'sitadel',
    'BD TOPO IGN': 'bd_topo',
    'Base Adresse Nationale': 'ban',
    'OpenStreetMap / Overpass': 'osm_overpass',
    'BPE INSEE': 'bpe_insee',
    'SIRENE': 'sirene_recherche_entreprises',
    'IGN BD CARTO V5 — occupation du sol': 'bd_carto_ocs',
    'ABF / Monuments historiques': 'abf_merimee',
    'INPN / patrinat — espaces protégés': 'inpn_espaces_proteges',
    'VRD / assainissement (SPANC)': 'spanc_epci',
    'Fichiers fonciers (Cerema)': 'fichiers_fonciers_cerema',
    "Cerema / GéoLittoral — indicateur d'érosion côtière": 'erosion_cotiere_geolittoral',
    'BODACC (procédures collectives)': 'bodacc',
    'DEAL Réunion — PPR / aléas': 'deal_ppr',
    'INPI RNE (dirigeants)': 'inpi_rne',
    'Géorisques — sites et sols pollués': 'georisques_ssp',
    'Géorisques — cavités souterraines': 'georisques_cavites',
    'Géorisques — ICPE': 'georisques_icpe',
    'Cartofriches (Cerema)': 'cartofriches',
    'Géorisques — mouvements de terrain': 'georisques_mvt',
    'DPE ADEME (logements existants)': 'dpe_ademe',
    'QPV 2024 (ANCT)': 'qpv_2024',
    'Inventaire SRU (DHUP)': 'sru_dhup',
    'NPNRU (DEAL Réunion / ANCT)': 'npnru',
    'INSEE RP Logement 2023': 'insee_rp_logement',
    'PLH des 5 EPCI (extraction documentaire)': 'plh_epci',
    'RTAA DOM (textes réglementaires)': 'rtaa_dom',
    'SUP — assiettes GPU (API Carto)': 'sup_gpu',
    "Recherche d'entreprises (DINUM)": 'recherche_entreprises_dinum',
    'Classement sonore ITT (Cerema)': 'bruit_itt_cerema',
    '50 pas géométriques — limite haute (DEAL)': 'cinquante_pas_deal',
    'PVGIS (Commission européenne)': 'pvgis',
    'EDF SEI Réunion — open data': 'edf_sei_opendata',
    'Registre national des installations (ODRÉ)': 'odre_registre_installations',
    'Parkings OSM (loi APER)': 'parkings_osm_aper',
    'Filosofi INSEE (carreaux 200 m)': 'filosofi_carreaux',
    'BD ORTHO 20 cm (IGN)': 'bd_ortho',
    "Sudocuh (procédures d'urbanisme)": 'sudocuh',
    "GPU — zonages d'assainissement": 'gpu_zonage_assainissement',
    'Contours IRIS (IGN/INSEE)': 'contours_iris',
    'RGE ALTI 5 m (IGN)': 'rge_alti_5m',
    'INSEE RP2022 — fichier détail Logements (EGOUL)': 'insee_rp2022_egoul',
    "GPU — zonages d'assainissement (info-surf typeinf 19)": 'gpu_assainissement_infosurf',
    "Office de l'eau Réunion — Chroniques de l'eau": 'office_eau_chroniques',
    'BD ORTHO IRC (IGN)': 'bd_ortho_irc',
    'LiDAR HD — MNH 50 cm (IGN)': 'lidar_hd_mnh',
    'DGFiP — parcelles des personnes morales': 'dgfip_parcelles_pm',
    "ZFANG — zone franche d'activité nouvelle génération (Légifrance)": 'zfang',
    "FRR ex-ZRR — zone spéciale d'action rurale (Légifrance)": 'frr_ex_zrr',
    'Transport public — GTFS (PAN, 7 réseaux)': 'gtfs_pan',
    "OSM — transport (pôles d'échange & téléphérique)": 'osm_transport',
    'ZNIEFF (INPN/MNHN)': 'znieff_inpn',
    'ZNIEFF (INPN / Région)': 'znieff_region_ods',
    'CoSIA (couverture du sol IA, IGN)': 'cosia',
    "Radar (pige d'annonces)": 'radar_pige',
    'SIRENE établissements géolocalisés': 'sirene_etablissements',
    'MOBPRO (mobilités domicile-travail, INSEE)': 'mobpro',
    'Trafic RN (Région Réunion — SIR)': 'trafic_rn',
    'BDNB': 'bdnb',
    'EDF Réunion — lignes moyenne tension HTA (open data)': 'edf_hta',
    'TCSP — voies bus en site propre (OSM)': 'tcsp_osm',
    'Réunion Express — hypothèses de tracé (débat public CNDP)': 'reunion_express_cndp',
    'ECLN (commercialisation des logements neufs, SDES)': 'ecln',
    'LOVAC (logements vacants)': 'lovac',
    # CIRCUIT-5 lot 2 — le pont était incomplet (sources arrivées après CIRCUIT-P) :
    "Cadastre d'époque (Etalab / PCI vecteur DGFiP)": 'cadastre_epoque',
    'CatNat (arrêtés GASPAR / Géorisques)': 'catnat_gaspar',
    "Taxe d'aménagement — taux communaux (délibérations)": 'taxe_amenagement',
    # CIRCUIT-5b lot 1 — les quatre « à rattacher » entrent au catalogue :
    "Annuaire de l'administration (service-public.fr / DILA)": 'annuaire_service_public',
    'RNIC — registre national des copropriétés (Anah)': 'rnic_anah',
    'RPLS — répertoire des logements locatifs sociaux (SDES)': 'rpls_sdes',
    "Consommation d'espaces NAF (Cerema — portail de l'artificialisation)": 'enaf_cerema',
    # SOURCES-1 lot 1 — droit des sols :
    'GPU — emplacements réservés (prescriptions CNIG)': 'gpu_prescriptions_er',
    'GPU — espaces boisés classés (prescriptions CNIG)': 'gpu_prescriptions_ebc',
    'GPU — droit de préemption urbain (info-surf)': 'dpu_perimetres',
    "PEB — plans d'exposition au bruit (DGAC via annexes GPU)": 'peb_dgac',
    'Zonage ABC des communes (DHUP)': 'zonage_abc_dhup',
    'ZPPA — zones de présomption de prescription archéologique (Atlas des patrimoines)': 'zppa_culture',
    # SOURCES-1 lot 2 — nature et eau :
    'Ravines — domaine public fluvial (DEAL Carmen)': 'deal_dpf_dpe',
    'Zones humides — inventaires DEAL (Carmen)': 'deal_zones_humides',
    'Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen)': 'enp_complements_deal',
    'AZI / TRI — inondation (Géorisques GASPAR)': 'georisques_azi_tri',
}

def slug_reservoir(nom: str | None) -> str | None:
    return NOM_VERS_SLUG.get(nom or "")


# ── L'ÉTAT D'UN RÉSERVOIR (couleur, libellé) — ordre de la maquette (tankEtat) ──────────────
def etat_reservoir(r: dict) -> tuple[str, str]:
    filtre = r.get("filtre") or {}
    veille = r.get("veille")
    mode = r.get("mode") or "one_shot"
    if filtre.get("verdict") == "quarantaine":
        return ("rouge", "en quarantaine")
    if r.get("horloge_ment"):                       # détecteur non branché live (accroche)
        return ("rouge", "horloge qui ment")
    if mode == "absente":
        return ("gris", "vide")
    if veille and veille.get("statut") == "nouvelle_version":
        return ("ambre", "nouvelle version à injecter")
    if r.get("agent_en_cours"):                     # transitoire, non exposé live (accroche)
        return ("mauve", "agent en route")
    if filtre.get("verdict") == "avertissements":
        return ("ambre", "filtre avec des KO")
    if not veille:
        return ("ambre", "jamais vérifié")
    if r.get("a_verifier"):                          # divergence assumée : cadence dépassée
        return ("ambre", "à vérifier")
    if veille.get("statut") == "injoignable":
        return ("ambre", "producteur injoignable")
    if mode == "depot_manuel":
        return ("gris", "dépôt manuel")
    return ("mint", "à jour")


# ── L'ÉTAT D'UN ROBINET (couleur, libellé) — ordre de la maquette (tapEtat) ──────────────────
def hors_moteur_de(robinet: dict, chiffres: dict) -> int:
    """Combien de chiffres de ce robinet court-circuitent le moteur (`sql_propre`/`front`).
    CIRCUIT-P2 (lot 2.1) : un `passe_plat` ne compte plus — c'est un état neutre, pas « hors moteur »."""
    n = 0
    for cid in robinet.get("chiffres") or []:
        if est_hors_moteur((chiffres.get(cid) or {}).get("calcul")):
            n += 1
    return n

def etat_robinet(robinet: dict, ctx: dict) -> tuple[str, str]:
    rid = robinet.get("id")
    if rid in ctx.get("fuite_robinets", ()):
        return ("rouge", "fuite mesurée")
    if rid in ctx.get("eau_ancienne_robinets", ()):
        return ("ambre", "eau ancienne")
    if rid in ctx.get("ecart_regle_robinets", ()):   # CIRCUIT-4 (accroche), 0 live
        return ("rouge", "écart à la règle")
    hm = hors_moteur_de(robinet, ctx.get("chiffres", {}))
    if hm:
        return ("ambre", f"{hm} hors moteur")
    if rid in ctx.get("choix_robinets", ()):         # CIRCUIT-4 (accroche), 0 live
        return ("gris", "choix à confirmer")
    if not (robinet.get("chiffres") or []):
        return ("gris", "aucun chiffre")
    return ("mint", "cohérent")


def ko_reservoir(couleur: str, _libelle: str = "") -> bool:
    """« à regarder » : tout sauf mint et gris (comme koTank de la maquette)."""
    return couleur not in ("mint", "gris")

def ko_robinet(couleur: str, libelle: str = "") -> bool:
    """comme koTap : tout sauf mint/gris, PLUS « choix à confirmer » (gris mais à trancher)."""
    return couleur not in ("mint", "gris") or libelle == "choix à confirmer"


# ── CIRCUIT-P2 (lot 2.2) — LES COMPTEURS, calculés UNE seule fois, côté serveur ──────────────
def partition_reservoirs(reservoirs: list[dict]) -> dict:
    """La partition CANONIQUE des réservoirs par état (un réservoir dans une seule case) :
      · à jour et vérifiés (mint)  · à regarder (ambre/rouge/mauve)  · vides ou manuels (gris)
    Invariant garanti et testé : a_jour + a_regarder + vides = réservoirs (règle 2.2).
    « À jour et vérifiés » (règle 2.3) = version producteur == version réservoir, contrôle plus
    récent que la cadence, filtre passé sans bloquant — soit exactement l'état mint d'etat_reservoir
    (un réservoir sous sentinelle mais jamais contrôlé sort ambre « à vérifier », pas mint)."""
    a_jour = a_regarder = vides = 0
    for r in reservoirs:
        couleur = (r.get("etat") or ["", ""])[0]
        if couleur == "mint":
            a_jour += 1
        elif couleur == "gris":
            vides += 1
        else:
            a_regarder += 1
    return {"reservoirs": len(reservoirs), "a_jour": a_jour,
            "a_regarder": a_regarder, "vides": vides}


def robinets_touches(fuites: list[dict], eau_ancienne: list[dict],
                     chiffres_par_robinet: dict) -> tuple[set, set]:
    """CIRCUIT-P3 (lot 2.1) — les ids de robinets REGISTRE touchés par une fuite / une eau ancienne.
    Les colonnes `robinet_a`/`robinet_b` de circuit_ecarts et `robinet` de circuit_eau_ancienne sont
    des LIBELLÉS d'affichage (« attrs.degre (DEAL brut) », « fiche parcelle / filtres »), pas des ids
    de robinet — les compter tels quels donnait au Résumé des robinets que le Circuit ne connaissait
    pas (« 2 fuites, 2 robinets » à gauche, « 0 à regarder » à droite). Le vrai lien passe par le
    `chiffre_id` : un robinet est touché s'il SERT un chiffre qui a une fuite / une eau ouverte.
    `chiffres_par_robinet` = {id_robinet: [chiffres servis]}."""
    fuite_chiffres = {f.get("chiffre_id") for f in fuites if f.get("chiffre_id")}
    eau_chiffres = {e.get("chiffre_id") for e in eau_ancienne
                    if e.get("statut") == "ouvert" and e.get("chiffre_id")}
    fuite_rob, eau_rob = set(), set()
    for rid, chiffres in chiffres_par_robinet.items():
        cs = set(chiffres or [])
        if cs & fuite_chiffres:
            fuite_rob.add(rid)
        if cs & eau_chiffres:
            eau_rob.add(rid)
    return fuite_rob, eau_rob


def compteurs(reservoirs: list[dict], robinets: list[dict]) -> dict:
    """Le SEUL point de vérité des nombres de la page (règle 2.2). Le Résumé, l'en-tête de colonne
    du Circuit, la ligne de fin et l'en-tête « Robinets » lisent CECI, jamais un calcul refait.
    Les clés fuites/eau/chiffres sont ajoutées par l'appelant (données hors état de base)."""
    part = partition_reservoirs(reservoirs)
    rob_ko = sum(1 for rb in robinets if ko_robinet(*(rb.get("etat") or ["mint", ""])))
    return {**part,
            "robinets": len(robinets), "robinets_a_regarder": rob_ko,
            "robinets_coherents": len(robinets) - rob_ko}
