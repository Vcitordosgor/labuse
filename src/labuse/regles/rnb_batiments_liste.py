"""Fiche de règle — identifiants RNB des bâtiments de la parcelle.
TESTS-1 lot 1 (dette SOURCES-2 lot 3 / REPARATIONS-1 lot 4 : donnée servie sans fiche)."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("rnb_batiments_liste",),
    formule_codee=(
        "rnb_batiments ACTIFS (is_active) dont l'emprise recoupe la parcelle "
        "(&& puis ST_Intersects sur shape_2975 × geom_2975), triés du plus grand recouvrement "
        "au plus petit (ST_Area(ST_Intersection) DESC), LIMIT 12 ; chaque ligne porte rnb_id, "
        "statut et le lien officiel https://rnb.beta.gouv.fr/batiments/<rnb_id>. Table absente "
        "ou erreur → liste vide, jamais un tiroir cassé (bati.py:le_bien_block)."),
    entrees=("rnb_batiments (RNB — rnb_id, statut, is_active, shape_2975)",
             "parcels (geom_2975)"),
    classe="methode_standard",
    fonction="src/labuse/bati.py:le_bien_block (rnb)",
    verdict="choix_assume",
    choix=(
        "Rattachement GÉOMÉTRIQUE (intersection d'emprises), pas le lien officiel bâtiment↔parcelle "
        "du RNB : un bâtiment à cheval apparaît sur chaque parcelle recoupée — c'est voulu "
        "(l'identité du bâtiment se lit depuis chaque parcelle concernée). Plafond 12 ids "
        "(lisibilité fiche) ; seuls les ACTIFS sortent, les démolis/annulés jamais."),
    exemple_temoin=None,
    verifie_le="2026-09-14",
))
