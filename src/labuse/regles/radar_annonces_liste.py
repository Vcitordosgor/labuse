"""Fiche de règle — annonces Radar rattachées à la parcelle. FICHE-1 lot 6 (CIRCUIT-4)."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("radar_annonces_liste",),
    formule_codee=(
        "Biens Radar VALIDÉS (pige_faits.valide_at non nul) rattachés à l'IDU, ordonnés par date "
        "décroissante ; chaque bien = date, prix demandé, type, statut lisible (active/"
        "en_vente_longue → « en cours », retiree → « retirée », vendue → « vendue »). Écart "
        "demandé/acté (concept ecart_demande_acte_pct, maille parcelle) servi UNIQUEMENT pour un "
        "bien EN COURS avec une mutation DVF sur la parcelle : ecart_pct = round(100 × (demandé − "
        "acté) / acté), sur €/m² si disponible des deux côtés (v_parcel_dvf_last.prix_m2_bati), "
        "sinon sur le prix total (valeur). Prix demandés — jamais un prix LABUSE."),
    entrees=("pige_biens ⋈ pige_faits (biens validés)", "pige_annonces (dernier portail/url)",
             "v_parcel_dvf_last (prix acté de référence)"),
    classe="choix_labuse",
    fonction="src/labuse/api/app.py:_radar_annonces_block",
    verdict="choix_assume",
    choix=("Choix LABUSE : servir la LISTE des annonces (tous statuts, lien vers la fiche annonce "
           "interne) et l'écart demandé/acté à la MAILLE PARCELLE (annonce en cours vs dernière "
           "mutation DVF), distinct de l'écart commune-médiane (ecart_demande_acte_pct, marché). "
           "Réutilise le concept d'écart sans dupliquer un id parcelle-grain (V5a préservé)."),
    exemple_temoin="tests/test_fiche1_radar.py::test_ecart_demande_acte_seulement_en_cours_avec_dvf",
    valide_par="cc",
    verifie_le="2026-09-06",
))
