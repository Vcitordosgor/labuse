"""CIRCUIT-2 lot 1.5 — LA COUVERTURE ÉLARGIE de la fiche parcelle : chaque clé de premier
niveau du payload `/parcels/{idu}` est rattachée à une ou plusieurs DONNÉES du registre, ou
classée `interne` (dérivation/méta LABUSE sans source externe propre — la raison est dite).

La règle (mandat 1.5) : tout champ NON NUMÉRIQUE d'ORIGINE EXTERNE servi par un endpoint de
robinets.py sans id échoue le test — et la liste d'exceptions est VIDE. Une clé absente d'ici
fait échouer `tests/test_circuit2_lot1.py` : déclarer la donnée (donnees.py) puis la rattacher
ici, jamais l'inverse.
"""
from __future__ import annotations

#: clé du payload fiche parcelle → ids de données du registre, OU ("interne", raison).
FICHE_PARCELLE_CLES: dict[str, tuple[str, ...] | tuple[str, str]] = {
    "idu": ("interne", "identifiant de la parcelle (clé, pas une donnée affichée)"),
    "commune": ("interne", "nom de commune (référentiel géographique, clé de navigation)"),
    "adresse": ("adresse_ban",),
    "coords": ("parcelle_geometrie",),
    "surface_m2": ("surface_parcelle_m2",),
    "prix_ancien": ("prix_terrain_secteur_eur_m2", "prix_sortie_bati_eur_m2",
                    "ventes_retenues_n", "ventes_ecartees_n"),
    "marche_synthese": ("prix_sortie_bati_eur_m2",),
    "marche_secteur": ("prix_terrain_secteur_eur_m2", "prix_sortie_bati_eur_m2"),
    "dvf_parcelle": ("dvf_parcelle_liste",),
    "score_v2": ("tier_opportunite", "rang_tier"),
    "score_v": ("evenements_proprietaire_liste",),
    "evenement": ("evenements_proprietaire_liste",),
    "evenement_detail": ("evenements_proprietaire_liste",),
    "proprietaire_moral": ("type_proprietaire",),
    "proprietaire_historique": ("proprietaire_timeline_liste", "acquisitions_pm_n"),
    "reglement_plu": ("reglement_plu_bloc", "zone_plu_famille"),
    "rnu": ("statut_plu",),
    "plu_fraicheur": ("interne", "méta-fraîcheur GPU vs mairie (dates de sources, pas une donnée)"),
    "radar_procedure": ("n_procedures_plu",),
    "prescriptions_verifiables": ("interne", "drapeau dérivé de zone_servie (Q12) — pas une source"),
    "prescriptions_non_verifiables_motif": ("interne", "motif du drapeau ci-dessus"),
    "historique_site": ("historique_permis_liste",),
    "voisinage_proche": ("voisinage_100m_liste", "ventes_100m_n"),
    "depots": ("depots_secteur_n",),
    "potentiel_transformation": ("potentiel_verdict", "sdp_residuelle_m2", "surface_vendable_m2",
                                 "surface_plancher_m2", "marge_surelevation_m", "capacite_logements"),
    "renouvellement": ("classe_residuel",),
    "coproprietes": ("coproprietes_liste",),
    "terrain": ("pente_deg",),
    "viabilisation": ("viabilisation_verdict",),
    "anc": ("part_logements_egout_pct",),
    "gestionnaires": ("interne", "annuaire de gestionnaires (config LABUSE, pas une source de donnée)"),
    "aper": ("interne", "obligation APER dérivée du bâti/parking (information réglementaire calculée)"),
    "proximites": ("distance_arret_m",),
    "proximites_equipements": ("equipements_proximite_liste",),
    "territoire_fiscal": ("perimetres_dispositifs_liste",),
    "anru": ("perimetres_dispositifs_liste",),
    "radar_bien": ("prix_demande_eur",),
    "secteur_opportunites": ("stock_opportunites",),
    "icd": ("verdict_icd",),
    "completeness_score": ("verdict_icd",),
    "lines": ("n_vigilances",),
    "flags": ("interne", "drapeaux d'affichage dérivés du run (build-mvt), servis par tier_opportunite"),
    "etage0": ("interne", "drapeau interne du scoring (étage 0), jamais affiché tel quel"),
    "mode_b": ("interne", "lecture dérivée (réhabilitation) — rien de persisté, toujours Estimé"),
    "parc_analysees": ("interne", "théâtre « N parcelles analysées » (compte gelé du run — méta)"),
    "data_sources": ("interne", "bloc « Les données » : liste des sources utilisées (méta-registre)"),
    "qualite_commune": ("couverture_commune_pct",),
    "calculette": ("cout_construction_saisi_eur_m2", "marge_frais_saisie_pct",
                   "prix_demande_saisi_eur", "ecart_prix_demande_pct"),
    "_trace": ("interne", "le tampon lui-même (?trace=1, admin)"),
    # SOURCES-1 lot 1 — bloc « Dispositifs et périmètres » (ER, EBC, DPU, PEB, SUP)
    "dispositifs": ("dispositifs_parcelle", "er_emplacement_reserve", "ebc_classe",
                    "dpu_perimetre", "peb_zone"),
    # SOURCES-1 lot 3 — bloc « Sols » (SIS, CASIAS)
    "sols": ("sols_parcelle", "sis_classe", "casias_statut"),
}


#: lot 5.2 — clé de couche du FRONT (LayerToggles / LAYER_INFO) → donnée `couche` du registre.
#: Sert le « i » des couches (source, millésime, fabrication — traçage côté client, sobre).
COUCHE_PAR_CLE_FRONT: dict[str, str] = {
    "zonage": "gpu_brut_couche", "zonage_parcelle": "zonage_plu_couche",
    "parcelles": "verdict_couche", "couleurs_verdict": "verdict_couche",
    "limites": "limites_parcelles_couche", "communes": "communes_couche",
    "ppr": "ppr_couche", "alea_inondation": "alea_inondation_couche",
    "alea_mvt": "alea_mvt_couche", "parc": "parc_national_couche",
    "znieff": "znieff_couche", "cinquante_pas": "cinquante_pas_couche",
    "equipements": "equip_osm_couche", "equipements_bpe": "bpe_couche",
    "transport": "transport_couche", "tcsp": "tcsp_couche", "axes": "axes_couche",
    "lignes_ht": "lignes_ht_couche", "qpv": "dispositifs_couche",
    "tva_primo": "dispositifs_couche", "anru": "dispositifs_couche",
    "zfang": "dispositifs_couche", "frr": "dispositifs_couche",
    "vefa_neuf": "vefa_couche", "renouv": "densifier_couche",
    # SOURCES-1 lot 1 — droit des sols (groupe « Contraintes »)
    "er": "er_couche", "ebc": "ebc_couche", "dpu": "dpu_couche",
    "peb": "peb_couche", "sup": "sup_couche",
    # SOURCES-1 lot 3 — sols et bruit
    "sis": "sis_couche", "casias": "casias_couche",
    "bruit_route": "bruit_couche", "bruit_carte": "bruit_carte_couche",
    # SOURCES-1 lot 2 — nature et eau (groupes « Contraintes » / « Nature »)
    "dpf": "dpf_couche", "zone_humide": "zone_humide_couche",
    "enp": "enp_couche", "rpg": "rpg_couche",
}


def probleme_cles(cles_servies: set[str]) -> list[str]:
    """Confronte les clés réellement servies par l'endpoint à la carte ci-dessus.
    Rend les problèmes : clé servie non rattachée, id rattaché inconnu du registre."""
    from .donnees import DONNEES
    pb: list[str] = []
    for cle in sorted(cles_servies):
        if cle not in FICHE_PARCELLE_CLES:
            pb.append(f"clé servie sans rattachement au registre : {cle}")
    for cle, ids in FICHE_PARCELLE_CLES.items():
        if ids and ids[0] == "interne":
            continue
        for cid in ids:
            if cid not in DONNEES:
                pb.append(f"clé {cle} : id inconnu du registre {cid}")
    return pb
