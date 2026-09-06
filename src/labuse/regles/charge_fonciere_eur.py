"""Fiche de règle — bilan promoteur à rebours (charge foncière). CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("charge_fonciere_eur", "bilan_ca_eur", "bilan_cout_construction_eur", "bilan_frais_eur",
             "bilan_marge_eur", "bilan_vrd_eur", "bilan_demolition_eur", "ecart_prix_demande_pct",
             "sensibilite_cout_construction"),
    formule_codee=(
        "Bilan à rebours classique : CA = SHAB vendable × prix de sortie observé (fiche "
        "prix_sortie_bati_eur_m2) ; coût construction = SDP × coût/m² (SDP ≈ SHAB × 1,15 — "
        "circulations/gaines/murs), fourchette calibrée secteur ou YAML 2 300-2 800 €/m² (prudent "
        "Réunion : para-cyclonique, matériaux importés) ; VRD = base €/m² terrain × surface, "
        "majorations pente/assainissement ; frais annexes = 12 % du CA ; marge = 9 % du CA ; "
        "démolition = SAISIE client (jamais estimée). Charge foncière = CA − construction − VRD − "
        "frais − marge − démolition. ecart_prix_demande = 100 × (charge foncière − prix demandé "
        "saisi) ÷ prix demandé. Sensibilité = variation de la charge pour ±10 % de coût. Prix "
        "« insuffisant » → PAS de bilan chiffré (on n'invente pas de prix)."),
    entrees=("sector_price (prix de sortie)", "faisabilité (SHAB/SDP)",
             "Hypotheses/bilan_params (coûts, marge 9 %, frais 12 %, plancher×1,15, VRD)",
             "saisies client (démolition, prix demandé)"),
    classe="methode_standard",
    fonction="src/labuse/faisabilite/bilan.py:compute",
    verdict="reference_introuvable",
    choix=("Tous les pourcentages (marge 9 %, frais 12 %, coefficient plancher 1,15, coûts 2 300-"
           "2 800 €/m²) sont des HYPOTHÈSES LABUSE affichées avec le bilan et réglables (YAML) — "
           "l'estimation est bandée « indicative, ne remplace pas un bilan professionnel »."),
    exemple_temoin=None,
    verifie_le="2026-09-06",
))
