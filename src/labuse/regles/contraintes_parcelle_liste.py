"""Fiche de règle — la liste des CONTRAINTES relevées de la parcelle (Apporteur). CHIRURGICAL-FIX-1 (LOT H pt2)."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("contraintes_parcelle_liste",),
    formule_codee=(
        "La liste est dérivée des LIGNES DE CASCADE SERVIES de la fiche (`f.lines`, résultat "
        "HARD_EXCLUDE/SOFT_FLAG) — exactement les mêmes alertes que la fiche §Risques-et-environnement "
        "et le Comparatif : aléas (layer='risques'), zone humide, inondation TRI, bruit, SUP… Par "
        "contrainte : libellé arbitré et nature = couche d'origine. EXCLUS (non des alertes qui gênent "
        "le projet) : bassin versant (hydrographie/contexte), marché du neuf (VEFA), et les motifs de "
        "SCORING (déclassement, bâti, SDP résiduelle). Aucune relecture géométrique : la décision "
        "d'alerte vient de la cascade servie, jamais d'un second calcul."),
    entrees=("payload /parcels/{idu} — f.lines (result HARD_EXCLUDE/SOFT_FLAG)",),
    classe="choix_labuse",
    fonction="src/labuse/exports/robinet_fiche.py:_c_contraintes_parcelle",
    verdict="choix_assume",
    choix=("Choix LABUSE : l'Apporteur (pièce qui circule seule) liste TOUTES les alertes servies à la "
           "fiche, pas seulement les aléas (aleas_parcelle_liste, layer='risques') — pour ne masquer "
           "aucune contrainte (zone humide d'AD0887, inondation extrême de BW2635). Même source que la "
           "fiche et le Comparatif, accord garanti."),
    exemple_temoin="tests/test_chirurgical_fix_h.py::test_apporteur_liste_alertes_complete_et_filtree",
    valide_par="cc",
    verifie_le="2026-11-15",
))
