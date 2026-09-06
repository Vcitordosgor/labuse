"""Fiche de règle — comparables DVF : filtre de retenue + profils. CIRCUIT-4."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("ventes_retenues_n", "ventes_ecartees_n", "dvf_parcelle_liste", "voisinage_100m_liste",
             "ventes_100m_n"),
    formule_codee=(
        "filtre_ventes (marche_service) : chaque vente DVF est RETENUE ou ÉCARTÉE AVEC MOTIF "
        "(nature de mutation hors vente, prix nul, surface nulle, hors bornes de bon sens, doublon "
        "multi-parcelles) — la couverture est VISIBLE (n retenues + n écartées + motifs, EXPORTS-1 "
        "lot 2). Profils déclarés (config/dvf_profils.yaml) : voisinage_100m = ventes + permis 36 "
        "mois dans un buffer de 100 m, site exclu (doctrine M38) ; dvf_parcelle_liste = dernière "
        "mutation de la parcelle + médianes du secteur cadastral (indicateur secondaire étiqueté)."),
    entrees=("dvf_mutations_parcelle (nature, prix, surfaces, geom)", "config/dvf_profils.yaml"),
    classe="regle_externe",
    fonction="src/labuse/marche_service.py:filtre_ventes (+ profils)",
    verdict="reference_introuvable",
    choix=("Bornes de bon sens et rayons de profils = conventions LABUSE déclarées (YAML) ; les "
           "DÉFINITIONS des champs lus (mutation, disposition, nature, valeur foncière) sont "
           "celles de DGFiP (lot 2)."),
    exemple_temoin="tests/regles/test_medianes_dvf.py::test_filtre_motifs_visibles",
    verifie_le="2026-09-06",
))
