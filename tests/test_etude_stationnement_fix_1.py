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


def test_saint_pierre_par_m2_sdp_tranche_complete_arrondi_inferieur():
    """Saint-Pierre Ud6 : « 1 place par tranche de 75 m² de SP » + « la place est comptabilisée par tranche
    complète » → seules les tranches ENTIÈRES comptent → arrondi INFÉRIEUR. 887,5 m² → 11 places (pas 12)."""
    b = _bareme({"par_m2_sdp": {"statut": "valide", "article": "Ud6", "page_pdf": 93,
                                "citation": "…", "m2_par_place": 75, "arrondi": "inferieur"}})
    ex = b.exiger(_prog([(3, 88.75, 10)]), destination="collectif")   # SDP 887,5
    assert ex.places == 11
    assert "inférieur" in ex.formule
    # 450 m² = 6 tranches entières exactes → 6 quel que soit l'arrondi
    assert b.exiger(_prog([(3, 90, 5)]), destination="collectif").places == 6


def test_tranche_muette_prend_le_plus_exigeant_superieur():
    """Formule « 1 place / 35 m² » sans mention d'arrondi (Les Avirons, ligne alternative) → plus exigeant
    = arrondi SUPÉRIEUR."""
    b = _bareme({"par_typologie": {"statut": "valide", "article": "x", "page_pdf": 1, "retenue": "max",
                 "detail": [{"destination": "collectif", "par_m2": 35, "role": "alt"}]}})
    ex = b.exiger(_prog([(2, 56, 4), (3, 70, 3), (4, 80, 1)]), destination="collectif")   # SDP 514
    assert ex.places == 15          # 514 / 35 = 14,7 → 15 (supérieur)
    assert "supérieur" in ex.formule


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


def test_destination_dediee_senior_etudiant_gouverne():
    """Règle permanente #4 — un projet senior/étudiant lit SA ligne (0,3 ou 0,2 / hébergement), pas la
    règle collective générale ; sans ligne dédiée la destination reste « Non vérifié » (via le moteur)."""
    b = _bareme({"par_logement": {"statut": "valide", "article": "x", "page_pdf": 1, "places": 1.5,
                                  "senior": {"places": 0.3}, "etudiant": {"places": 0.2}}})
    prog = _prog([(3, 70, 9)])
    assert b.exiger(prog, destination="collectif").places == 14   # 9 × 1,5 = 13,5 → 14
    assert b.exiger(prog, destination="senior").places == 3       # 9 × 0,3 = 2,7 → 3
    assert b.exiger(prog, destination="etudiant").places == 2     # 9 × 0,2 = 1,8 → 2
    assert b.has_destination("senior") and not b.has_destination("social")


def test_colonne_places_integrees_condition_bloquante_au_seuil():
    """Règle permanente #2 — la colonne « places intégrées » : au-delà du seuil de SDP, une part des places
    doit être bâtie → condition bloquante à vérifier (plein air exclu). En dessous : rien."""
    b = _bareme({"par_logement": {"statut": "valide", "article": "x", "page_pdf": 1, "places": 1.0,
                                  "places_integrees": {"pct": 100, "seuil_m2": 1000}}})
    assert b.exiger(_prog([(3, 70, 20)]), destination="collectif").conditions   # 1400 m² > 1000 → condition
    assert not b.exiger(_prog([(3, 70, 5)]), destination="collectif").conditions  # 350 m² < 1000 → aucune


def _signature(b):
    """Signature de la RÈGLE appliquée (valeurs, pas le texte) — pour comparer deux zones."""
    lignes = tuple(sorted(
        f"{l.destination}|{l.role}|{l.places}|{l.par_m2}|{l.pieces_min}|{l.pieces_max}|"
        f"{l.sdp_min}|{l.sdp_max}|{l.logements_min}|{l.arrondi}" for l in b.lignes))
    vis = None if b.visiteurs is None else (b.visiteurs.places, b.visiteurs.par_logements,
                                            b.visiteurs.par_m2_sdp, b.visiteurs.logements_min, b.visiteurs.arrondi)
    return (b.mode, b.flat_places, b.m2_par_place, b.arrondi, b.retenue, lignes, vis, tuple(b.conditions))


def test_controle_citation_identique_implique_regle_identique():
    """CONTRÔLE (correctif #3) — aucune citation IDENTIQUE entre deux zones sans que la RÈGLE appliquée soit
    identique. C'est exactement ce qui aurait attrapé le bug « Ucv recopie la citation de Ud » (même phrase,
    mais Ucv applique 0,85 et Ud applique 1 — signatures ≠). Sur les cinq communes pilotes."""
    from labuse.plu import destinations as D
    from labuse.implantation import regles as R
    import re
    PILOTES = {"97401": "les_avirons", "97407": "le_port", "97410": "saint_benoit",
               "97416": "saint_pierre", "97422": "le_tampon"}
    for insee, slug in PILOTES.items():
        par_citation = {}
        for r in D.regles_commune(insee):
            z = r["zone"]
            if not re.match(r'^\d*(U|AU)', z, re.I):
                continue
            b = R.charger(insee, z).stationnement
            if not b.validee or not b.citation:
                continue
            par_citation.setdefault(b.citation, []).append((z, _signature(b)))
        for cit, items in par_citation.items():
            sigs = {sig for _z, sig in items}
            zones = [z for z, _s in items]
            assert len(sigs) == 1, (
                f"{insee} : la même citation est servie à des zones de règle DIFFÉRENTE {zones} "
                f"(citation « {cit[:60]}… ») — recopie probable, chaque zone doit citer son propre texte.")


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
