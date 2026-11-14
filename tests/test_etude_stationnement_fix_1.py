"""ETUDE-STATIONNEMENT-FIX-1 (LOT 1) — le barème sait porter les vraies règles du PLU.

Tests unitaires du moteur de barème (`BaremeStationnement.exiger`), sans base : formes typées
(par tranche de m², arrondi lu, visiteurs, seuil d'opération, « la plus exigeante de deux
formules », ligne du logement social), conditions non modélisables remontées, destination lue
dans le type de projet. Les chiffres sont calculés à la main depuis le texte (cf. RAPPORT d'audit).
"""
from types import SimpleNamespace

from labuse.implantation.regles import DESTINATION_PAR_PROJET, _bareme


def _prog(spec):
    """spec = [(pieces, surface_m2, n), …] → liste de logements."""
    out = []
    for p, s, n in spec:
        out += [SimpleNamespace(pieces=p, surface_m2=s) for _ in range(n)]
    return out


# Programme « équilibre » du moteur pour 8 logements : T2×4 (2p, 56 m²), T3×3 (3p, 70), T4×1 (4p, 80).
PROG8 = _prog([(2, 56, 4), (3, 70, 3), (4, 80, 1)])


def test_tampon_collectif_retient_la_regle_operation_la_plus_exigeante():
    """Le Tampon Ud12.2 : habitat collectif par pièces (0,5/1/1,5) ET « opération > 5 logements :
    1,5/logt, arrondi inférieur ». Pour 8 logements, la plus exigeante = 12 (vs 10 par typologie)."""
    b = _bareme({"par_typologie": {
        "statut": "valide", "article": "Ud12.2", "page_pdf": 66, "citation": "…", "retenue": "max",
        "detail": [
            {"destination": "collectif", "pieces_max": 1, "places": 0.5, "role": "base", "tranche": "chambre/studio"},
            {"destination": "collectif", "pieces_min": 2, "pieces_max": 2, "places": 1, "role": "base", "tranche": "2 pièces"},
            {"destination": "collectif", "pieces_min": 3, "places": 1.5, "role": "base", "tranche": "3 pièces+"},
            {"destination": "individuel", "places": 1, "role": "base"},
            {"destination": "collectif", "places": 1.5, "arrondi": "inferieur", "logements_min": 6, "role": "operation"},
        ],
        "conditions": ["dont au moins 0,5 place à l'extérieur des espaces privatisés"]}})
    ex = b.exiger(PROG8, destination="collectif")
    assert ex.couvert is True
    assert ex.places == 12                      # 1,5 × 8 (opération > 5), arrondi inférieur
    assert "opération > 5" in ex.formule
    assert any("= 10" in f for f in ex.formules_ecartees)   # lecture par typologie écartée
    assert ex.conditions == ("dont au moins 0,5 place à l'extérieur des espaces privatisés",)


def test_saint_pierre_par_m2_sdp_tranche_complete():
    """Saint-Pierre Ud6 : « 1 place par tranche de 75 m² de SP », tranche complète. HT0538 = 887,5 m²
    → 12 places. La forme par_m2_sdp est désormais SUPPORTÉE (avant : non servie)."""
    b = _bareme({"par_m2_sdp": {"statut": "valide", "article": "Ud6", "page_pdf": 93,
                                "citation": "…", "m2_par_place": 75, "arrondi": "superieur"}})
    ex = b.exiger(_prog([(3, 88.75, 10)]), destination="collectif")   # SDP 887,5
    assert ex.places == 12
    assert "75" in ex.formule


def test_la_plus_exigeante_de_deux_formules():
    """Les Avirons : collectif = « 1,25/logt OU 1 place / 35 m² SDP, la norme produisant le plus de
    places retenue ». Les deux lectures sont calculées, la plus grande retenue."""
    b = _bareme({"par_typologie": {"statut": "valide", "article": "U12.2", "page_pdf": 16, "retenue": "max",
                 "detail": [
                     {"destination": "collectif", "places": 1.25, "role": "alt"},
                     {"destination": "collectif", "par_m2": 35, "role": "alt"}]}})
    ex = b.exiger(PROG8, destination="collectif")
    # SDP = 514 m² → 514/35 = 14,7 → 15 ; 1,25 × 8 = 10 → retient 15
    assert ex.places == 15
    assert any("= 10" in f for f in ex.formules_ecartees)


def test_visiteurs_par_m2_et_par_logements():
    """Le Port : 0,3/logt + 1 visiteur / 100 m² SDP. Saint-Benoît : 1/logt + 1 visiteur / 5 logts."""
    port = _bareme({"par_logement": {"statut": "valide", "article": "Ua12.1", "page_pdf": 30, "places": 0.3,
                                     "visiteurs": {"par_m2_sdp": 100, "places": 1}}})
    ex = port.exiger(PROG8, destination="collectif")
    assert ex.places_residents == 3            # 0,3 × 8 = 2,4 → 3
    assert ex.places_visiteurs == 6            # 514 / 100 = 5,14 → 6
    assert ex.places == 9

    benoit = _bareme({"par_logement": {"statut": "valide", "article": "U12", "page_pdf": 17, "places": 1,
                                       "visiteurs": {"par_logements": 5, "places": 1}}})
    exb = benoit.exiger(PROG8, destination="collectif")
    assert exb.places_residents == 8 and exb.places_visiteurs == 2 and exb.places == 10


def test_arrondi_lu_dans_la_regle_par_logement():
    """Le sens d'arrondi est désormais LU en mode par_logement (avant : toujours supérieur)."""
    inf = _bareme({"par_logement": {"statut": "valide", "article": "x", "page_pdf": 1,
                                    "places": 1.5, "arrondi": "inferieur"}})
    sup = _bareme({"par_logement": {"statut": "valide", "article": "x", "page_pdf": 1,
                                    "places": 1.5, "arrondi": "superieur"}})
    prog5 = _prog([(2, 56, 5)])                 # 1,5 × 5 = 7,5
    assert inf.exiger(prog5, destination="collectif").places == 7     # arrondi inférieur
    assert sup.exiger(prog5, destination="collectif").places == 8     # arrondi supérieur


def test_regle_ne_couvrant_pas_le_programme_reste_non_verifie():
    """Un barème validé dont aucune ligne ne couvre le programme dessiné → couvert=False (le contrôle
    dira « Non vérifié », jamais « Réussi ») — on n'invente rien."""
    b = _bareme({"par_typologie": {"statut": "valide", "article": "x", "page_pdf": 1,
                 "detail": [{"destination": "individuel", "places": 2, "role": "base"}]}})
    ex = b.exiger(PROG8, destination="collectif")   # programme collectif, aucune ligne collectif
    assert ex.couvert is False


def test_destination_suit_le_type_de_projet():
    """La destination lue dans le barème suit le type de projet (plus de « collectif » codé en dur)."""
    assert DESTINATION_PAR_PROJET["collectif"] == "collectif"
    assert DESTINATION_PAR_PROJET["social"] == "social"
    assert DESTINATION_PAR_PROJET["senior"] == "senior"
    assert DESTINATION_PAR_PROJET["etudiante"] == "etudiant"
    b = _bareme({"par_typologie": {"statut": "valide", "article": "x", "page_pdf": 1,
                 "detail": [
                     {"destination": "collectif", "places": 1.5, "role": "base"},
                     {"destination": "social", "places": 1, "role": "base"}]}})
    # mêmes logements, destination « social » → ligne sociale (1/logt) ; « collectif » → 1,5/logt
    prog = _prog([(3, 70, 4)])
    assert b.exiger(prog, destination="social").places == 4
    assert b.exiger(prog, destination="collectif").places == 6
