"""ETUDE-STATIONNEMENT-FIX-2 (LOT 1) — BANC D'EXÉCUTION du stationnement.

La preuve n'est plus « la citation est présente » mais « le nombre de places calculé est JUSTE ». Chaque cas
porte le nombre attendu LU À LA MAIN sur l'image de la page officielle par le relecteur indépendant (contre-
audit en lecture seule), et le compare au calcul du moteur (`BaremeStationnement.exiger`). Détail exigé :
résidents, visiteurs, places publiques à part, arrondi, seuil, plafond.

Programmes types (mandat) : maison T4 120 m² (individuel) ; collectif privé 20 × T3 = 1 400 m² ; le même en
logement aidé ; collectif mixte 10 × 110 m² + 10 × 30 m². Les 15 zones recalculées par le relecteur figurent
ici ; 6 donnaient un nombre faux avant ce lot (Saint-Paul, Saint-Louis, Saint-Leu, Trois-Bassins, Saint-Joseph,
+ la maison seule à Salazie/Sainte-Marie/Sainte-Suzanne).
"""
from types import SimpleNamespace

import pytest

from labuse.implantation import regles as R


def _maison():
    return [SimpleNamespace(pieces=4, surface_m2=120.0)]


def _collectif(n=20, pieces=3, surf=70.0):
    return [SimpleNamespace(pieces=pieces, surface_m2=surf) for _ in range(n)]


# (insee, zone, maison attendue [individuel], collectif privé attendu [20×T3])  — valeurs LUES SUR L'IMAGE.
BANC = [
    ("97415", "U2c", 2, 44),   # Saint-Paul : 40 + 4 visiteurs (1/5) — visiteurs étaient omis
    ("97416", "Ud", 1, 18),    # Saint-Pierre : 1 place / 75 m², tranches complètes
    ("97411", "Uj", 1, 20),    # Saint-Denis
    ("97407", "Uc", 3, 20),    # Le Port
    ("97414", "UA", 2, 40),    # Saint-Louis : 40 privées À DESSINER (+ 10 publiques à part)
    ("97422", "Ud", 1, 30),    # Le Tampon : opération > 5 → 1,5/logt
    ("97410", "Ua", 1, 24),    # Saint-Benoît
    ("97403", "Ua", 3, 44),    # Entre-Deux
    ("97421", "UA", 2, 40),    # Salazie : maison seule = tranche > 50 m² (pas « non vérifié »)
    ("97413", "UD", 2, 30),    # Saint-Leu : collectif par pièces (3-5p = 1,5) — était flat 2
    ("97423", "UC", 1, 40),    # Trois-Bassins : maison = 1,5 arrondi INFÉRIEUR = 1 — était 2
    ("97401", "Ub", 2, 40),    # Les Avirons
    ("97418", "UB", 2, 20),    # Sainte-Marie : maison seule via tranche
    ("97420", "UB", 2, 40),    # Sainte-Suzanne : maison seule via tranche
    ("97412", "U2", 1, 20),    # Saint-Joseph : visiteurs « 1/10 » visent l'HÉBERGEMENT, pas l'ordinaire
]


@pytest.mark.parametrize("insee,zone,maison,collectif", BANC)
def test_banc_maison_et_collectif(insee, zone, maison, collectif):
    b = R.charger(insee, zone).stationnement
    assert b.validee, f"{insee}/{zone} : barème non servi"
    em = b.exiger(_maison(), destination="individuel")
    ec = b.exiger(_collectif(), destination="collectif")
    assert em.places == maison, f"{insee}/{zone} maison : {em.places} ≠ {maison} attendu ({em.formule})"
    assert ec.places == collectif, f"{insee}/{zone} collectif : {ec.places} ≠ {collectif} attendu ({ec.formule})"


def test_saint_louis_places_publiques_a_part():
    """Saint-Louis UA, 20 logements : 40 places PRIVÉES à dessiner + 10 places PUBLIQUES (hors parcelle),
    comptées séparément — elles ne gonflent pas le nombre à dessiner."""
    b = R.charger("97414", "UA").stationnement
    ec = b.exiger(_collectif(20), destination="collectif")
    assert ec.places == 40 and ec.places_publiques == 10


def test_saint_joseph_visiteurs_hebergement_pas_ordinaire():
    """Saint-Joseph : la ligne « 1 place / 10 logements » vise les établissements d'hébergement (CASF), pas
    le logement ordinaire → 20 logements ordinaires = 20 places (était 22)."""
    b = R.charger("97412", "U2").stationnement
    assert b.exiger(_collectif(20), destination="collectif").places == 20


def test_petite_ile_aide_pas_dispense():
    """Petite-Île : la dispense de place est réservée au LLTS, pas à tout l'aidé → 20 logements aidés
    (hors LLTS) = 20 places (était 0)."""
    b = R.charger("97405", "UB").stationnement
    assert b.exiger(_collectif(20), destination="social").places == 20


def test_trois_bassins_maison_arrondi_inferieur():
    """Trois-Bassins : 1,5 place/logt « arrondi à l'entier inférieur » (en-tête) → 1 maison = 1 (était 2)."""
    b = R.charger("97423", "UC").stationnement
    assert b.exiger(_maison(), destination="individuel").places == 1


def test_saint_leu_collectif_par_pieces():
    """Saint-Leu : habitat collectif par pièces (3-5 pièces = 1,5) → 20 T3 = 30 (était 40, barème individuel)."""
    b = R.charger("97413", "UD").stationnement
    assert b.exiger(_collectif(20), destination="collectif").places == 30


def test_plafond_national_ne_fait_que_baisser():
    """LOT 2 — le plafond national L151-35 est un PLAFOND : attaché à un barème local, il borne l'exigence
    (la fait baisser) mais ne la relève JAMAIS, et il s'applique même sur une ligne dédiée."""
    from dataclasses import replace
    b = R.charger("97413", "UD").stationnement  # collectif = 1,5/logt → 20 = 30
    assert b.exiger(_collectif(20), destination="collectif").places == 30
    # plafond 1/logt : borne 30 → 20 (fait baisser)
    b1 = replace(b, plafond_national={"ratio": 1.0, "article": "L151-35"})
    ex1 = b1.exiger(_collectif(20), destination="collectif")
    assert ex1.places == 20 and "barème local = 30" in ex1.formules_ecartees
    # plafond 2/logt : 20×2 = 40 ≥ 30 → NE relève pas, reste 30
    b2 = replace(b, plafond_national={"ratio": 2.0, "article": "L151-35"})
    assert b2.exiger(_collectif(20), destination="collectif").places == 30


def test_plafond_l151_compare_a_l_exigence_applicable():
    """FIX-3 (LOT 3) — le plafond L151-35 se compare à l'exigence RÉELLEMENT applicable au programme (ligne
    aidée comprise), pas au forfait général. Le Port Uc : aidé 0,2/logt + 8/1000 m² = 16 ; plafond 0,5/logt
    le borne à 10 (l'ancien code sautait le plafond car 0,5 ≥ 0,3 forfait général)."""
    from dataclasses import replace
    from types import SimpleNamespace
    b = R.charger("97407", "Uc").stationnement
    mods = [SimpleNamespace(pieces=3, surface_m2=70.0) for _ in range(20)]
    assert b.exiger(mods, destination="social").places == 16
    b05 = replace(b, plafond_national={"ratio": 0.5, "article": "L151-35"})
    assert b05.exiger(mods, destination="social").places == 10


def test_plafond_l151_univ_personnes_agees_0_5_toujours():
    """FIX-3 (LOT 3) — résidences universitaires et établissements personnes âgées : plafond 0,5 place/logt
    QUELLE QUE SOIT la distance (le logement aidé, lui, reste à 1 si > 800 m)."""
    from labuse.implantation import moteur as M
    b = R.charger("97407", "Uc").stationnement
    assert M._plafond_l151(None, ["x"], "senior", b)[0] == 0.5      # distance inconnue → 0,5 quand même
    assert M._plafond_l151(None, ["x"], "etudiante", b)[0] == 0.5
    assert M._plafond_l151(None, ["x"], "social", b)[0] == 1.0      # aidé loin d'un TCSP → 1,0


@pytest.mark.parametrize("insee,zone,fonction_seulement", [
    ("97415", "U1a", False),   # quota de logements locatifs sociaux → vrai programme d'habitation
    ("97414", "UZ", False),    # « maximum 1 logement individuel » dans les espaces d'habitat → vrai habitat
    ("97407", "1AUe", True),   # renvoi vers Ue (logement de fonction) : hérite la restriction
    ("97411", "Uac", True),    # renvoi vers Ua (habitation pour direction/surveillance) : hérite
    ("97407", "Ue", True),
    ("97411", "Ua", True),
    # reliquat #3 — ces deux zones NE sont PAS « habitat interdit / vocation économique » : Le Tampon 2AUa
    # (renvoi Ua, admis sous conditions) et Saint-Paul U1pso (renvoi U1a, habitat ouvert) sont ADMISES par le
    # filtre fonction (False) ; elles ne reçoivent donc jamais le motif « habitat interdit (activités) ».
    ("97422", "2AUa", False),
    ("97415", "U1pso", False),
])
def test_logement_fonction_detection(insee, zone, fonction_seulement):
    """LOT 2 — le filtre « logement de fonction seulement » : ne se déclenche PAS quand la zone ouvre un vrai
    programme d'habitation (social, individuel), et HÉRITE la restriction de la zone parente via renvoi."""
    from labuse.implantation.service import _logement_fonction_seulement
    assert _logement_fonction_seulement(insee, zone) is fonction_seulement


def test_degagement_allee_mesure_localement_pas_boite():
    """LOT 3 (BW2635) — le dégagement devant les places est mesuré LOCALEMENT, pas sur la boîte englobante :
    une allée pincée à 2,25 m devant les places mais dont la boîte fait 5 m est REFUSÉE (avant : validée)."""
    from shapely.geometry import box
    from shapely.ops import unary_union
    from labuse.implantation.controles import _pincement_allee
    # allée pincée à 2,25 m devant 6 places, mais un tronçon large (5 m) ailleurs → boîte 5 m, ancien test « passe ».
    allee = unary_union([box(0, 0, 15, 2.25), box(15, 0, 20, 5.0)])
    places = [box(i * 2.5, -5, i * 2.5 + 2.5, 0) for i in range(6)]
    assert min(allee.bounds[2] - allee.bounds[0], allee.bounds[3] - allee.bounds[1]) >= 5.0  # ancien test aveugle
    assert _pincement_allee([allee], places, 5.0) >= 1.0                                     # nouveau : pincement vu
    # allée large de 5 m partout → acceptée (le liseré d'ouverture reste sous le seuil).
    ok = box(0, 0, 20, 5.0)
    assert _pincement_allee([ok], places, 5.0) < 1.0


def test_bareme_existence_source_unique_par_m2_sdp():
    """LOT 4 (HT0538/Ud) — un barème « par m² de SDP » est VALIDÉ : l'Étude ne doit plus le déclarer « absent »
    d'un côté (garde-fou) et « validé » de l'autre (citation). Source unique = le drapeau `validee`, et la
    règle courte DÉCRIT le barème au m² au lieu de rester vide."""
    from labuse.implantation.service import _regle_stationnement_courte
    from labuse.exports.etude_faisabilite import _bareme_stationnement_absent
    b = R.charger("97416", "Ud").stationnement
    assert b.validee and b.mode == "par_m2_sdp"
    assert _regle_stationnement_courte(b) == "1 place / 75 m² de surface de plancher"
    payload = {"stationnement_regimes": {"general": {"validee": True, "article": "Ud6",
                                                     "regle_courte": _regle_stationnement_courte(b),
                                                     "ratio_par_logement": None}}}
    assert _bareme_stationnement_absent(payload) is False
    # non validé → bien « absent »
    assert _bareme_stationnement_absent({"stationnement_regimes": {"general": {"validee": False}}}) is True


def test_stationnement_cherche_la_cour_reliee():
    """Une barre continue sépare la grande cour du seul accès sur rue."""
    from shapely.geometry import LineString, box
    from shapely.ops import unary_union
    from labuse.implantation.conventions import charger
    from labuse.implantation.geometrie import Frame, Objet, Scene, poser_stationnement

    assiette = unary_union([box(0, 0, 66, 30), box(0, 30, 36, 52)])
    rue = LineString([(36, 33), (36, 52)])
    scene = Scene(Frame(0, 0, 0), assiette, assiette, False, [rue])
    scene.ajouter(Objet("batiment_emprise", box(0, 25, 66, 30)))
    assert poser_stationnement(scene, charger(), cible=12) == 12
    assert all(place.geom_local.bounds[1] >= 30 for place in scene.of("place"))
    assert scene.of("acces")[0].geom_local.distance(rue) < 1e-6



def test_repartition_apres_arrondi_du_type_minoritaire():
    from labuse.implantation.geometrie import _repartir_prorata

    assert _repartir_prorata({"T2": 17, "T3": 22, "T4": 9}, 4) == {"T2": 1, "T3": 2, "T4": 1}
