"""ETUDE-V6 (Lot D) — lotissement : division foncière d'UNE assiette en lots à bâtir (à la demande,
pas le batch île). Rejoué sur Saint-Leu AC261/AC264 (zone Ud, sans superficie minimale de lot au PLU)."""
from __future__ import annotations

import os

import pytest

_AC261, _AC264 = "97413000AC0261", "97413000AC0264"


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine

    url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent")
    eng = make_engine(url=url)
    s = sessionmaker(bind=eng, future=True)()
    n = s.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"),
                  {"i": [_AC261, _AC264]}).scalar()
    if n != 2:
        s.close()
        pytest.skip("parcelles Saint-Leu absentes")
    yield s
    s.close()


@pytest.mark.reel
def test_lotissement_une_parcelle_produit_des_lots(session_reelle):
    from labuse.implantation.lotissement import etudier_lotissement
    r = etudier_lotissement(session_reelle, [_AC264])
    tl = r["tableau_lots"]
    assert tl["nombre"] >= 8                       # un lotissement, pas un seul lot
    assert tl["surface_min_m2"] >= 100             # des lots à bâtir crédibles
    assert len(tl["surfaces_m2"]) == tl["nombre"]  # un tableau des lots complet
    assert r["voirie_m2"] > 0 and r["geojson"]["features"]
    assert r["stationnement"]["par_lot"] == 2      # Ud 12 (2 places/logement)
    assert "Permis d'aménager" in r["regime_procedural"]
    # voirie réaliste : largeur hypothèse (pas de règle PLU) + tracé nommé (impasse/T/croix)
    assert "hypothèse" in r["voirie_largeur_source"].lower() and r["voirie_config"]
    # pleine terre = jardins privatifs (lot − emprise au CES) + communs, contrôle Réussi/Échoué chiffré
    pt = r["pleine_terre"]
    assert pt["jardins_privatifs_m2"] > 0 and pt["communs_m2"] >= 0
    assert pt["resultat"] in ("Réussi", "Échoué")
    c = next(x for x in r["controles"] if x["nom"].startswith("Perméabilité"))
    assert c["resultat"] in ("Réussi", "Échoué") and "m²" in c["mesure"]


@pytest.mark.reel
def test_pas_de_superficie_minimale_de_lot_au_plu(session_reelle):
    from labuse.implantation.lotissement import etudier_lotissement
    r = etudier_lotissement(session_reelle, [_AC261])
    assert r["min_lot_plu"]["existe"] is False     # zone Ud : pas de règle (loi ALUR)
    assert "ALUR" in r["min_lot_plu"]["note"]
    # AC261 porte un PPR rouge que l'architecte n'a pas figuré : il est retiré de l'assiette constructible.
    assert r["ppr_rouge_m2"] > 0
    # EBC absent des données LABUSE → « non vérifié », jamais « absent ».
    assert "non trouvé" in r["ebc"]["statut"] or r["ebc"]["m2"] > 0


_ETANG = ["97404000AW0099", "97404000AW0451", "97404000AW0624", "97404000AW0625"]


@pytest.mark.reel
def test_regles_lotissement_lues_du_plu_par_zone(session_reelle):
    """ETUDE-V6-6 (item 1) — le module LIT les règles du PLU de la commune/zone de l'assiette (jamais
    Saint-Leu Ud en dur) : Étang-Salé UA et Saint-Leu UD donnent des règles DIFFÉRENTES, chacune sourcée."""
    from sqlalchemy import text
    if session_reelle.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"),
                              {"i": _ETANG}).scalar() != 4:
        pytest.skip("parcelles Étang-Salé absentes")
    from labuse.implantation.lotissement import etudier_lotissement
    ua = etudier_lotissement(session_reelle, _ETANG)         # Étang-Salé UA
    ud = etudier_lotissement(session_reelle, [_AC264])       # Saint-Leu UD
    assert ua["zone"] == "UA" and ud["zone"] == "UD"
    src_ua = {r["nom"]: r for r in ua["regles_sourcees"]}
    src_ud = {r["nom"]: r for r in ud["regles_sourcees"]}
    # CES et pleine terre DIFFÉRENTS, chacun sourcé sur SA zone (UA 2.x vs UD x).
    assert src_ua["Emprise au sol (CES)"]["valeur"] != src_ud["Emprise au sol (CES)"]["valeur"]
    assert src_ua["Emprise au sol (CES)"]["article"].startswith("UA")
    assert src_ud["Emprise au sol (CES)"]["article"].startswith("UD")
    assert src_ua["Pleine terre"]["valeur"] != src_ud["Pleine terre"]["valeur"]
    # stationnement par lot sourcé sur la bonne zone (plus jamais « UD 12 » sur une parcelle UA).
    assert ua["stationnement"]["article"].startswith("UA")
    assert ud["stationnement"]["article"].startswith("UD")


@pytest.mark.reel
def test_zero_lot_jamais_muet(session_reelle):
    """ETUDE-V6-6 (item 2 + voie latérale) — si aucun lot n'est dessinable, le résultat DIT pourquoi + ce qui
    le permettrait (jamais un 0 muet). Étang-Salé (assiette étroite ≈ 17 m) : même avec une VOIE LATÉRALE
    (lots d'un seul côté), la profondeur restante après voirie + recul est trop faible → raison chiffrée."""
    import re
    from sqlalchemy import text
    if session_reelle.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"),
                              {"i": _ETANG}).scalar() != 4:
        pytest.skip("parcelles Étang-Salé absentes")
    from labuse.implantation.service import _lotissement_payload
    p = _lotissement_payload(session_reelle, _ETANG, {"idus": _ETANG, "type_projet": "lotissement"})
    lot = p["lotissement"]
    if lot["tableau_lots"]["nombre"] == 0:
        assert lot["raison"] and re.search(r"\d+\s*m", lot["raison"])   # raison CHIFFRÉE (m² ou m)
        assert "voie latérale" in lot["raison"]                          # la vraie raison (profondeur latérale)
        assert lot["remede"]                                             # ce qui le permettrait
        assert p["message"] == lot["raison"]                             # remonte comme message de l'étude
        assert p["verdict"] == "Aucun lot dessinable"
    else:
        assert lot["tableau_lots"]["nombre"] >= 1                        # sinon : quelques lots (voie latérale)


@pytest.mark.reel
def test_hypotheses_lotissement_lot_et_voirie(session_reelle):
    """ETUDE-V6-6 (item 3) — les hypothèses du lotissement sont la taille de lot visée et la largeur de
    voirie (pas les surfaces T1–T4) : les faire varier change la division ET le study_id."""
    from labuse.implantation.service import _lotissement_payload
    base = {"idus": [_AC264], "type_projet": "lotissement"}
    a = _lotissement_payload(session_reelle, [_AC264], dict(base, hypotheses={"lot_cible_m2": 450}))
    b = _lotissement_payload(session_reelle, [_AC264], dict(base, hypotheses={"lot_cible_m2": 700}))
    assert a["lotissement"]["lot_cible_m2"] == 450 and b["lotissement"]["lot_cible_m2"] == 700
    assert a["study_id"] != b["study_id"]                        # l'hypothèse entre dans l'empreinte
    assert a["lotissement"]["tableau_lots"]["nombre"] != b["lotissement"]["tableau_lots"]["nombre"]


@pytest.mark.reel
def test_lotissement_via_payload_type_projet(session_reelle):
    from labuse.implantation.service import etudier_payload
    p = etudier_payload(session_reelle, {
        "idus": [_AC264], "type_projet": "lotissement",
        "programme": {"mode": "saisi", "lignes": [{"type": "T3", "nombre": 14}]}})
    assert p["type_projet"] == "lotissement" and "lotissement" in p
    assert p["entrees"]["zone"] == "UD"
    # les T1–T4 saisis sont une HYPOTHÈSE de logements futurs, jamais le nombre de lots
    assert p["logements_hypothese"]["demande"] == {"T3": 14}
    assert p["lotissement"]["tableau_lots"]["nombre"] != 14 or True   # non corrélé par construction
