"""ETUDE-V6 (Lot E) — document depuis la MÊME étude (study_id stable, PDF = écran prouvé par garde) et
BILAN SURFACIQUE CLOS (aucune double comptabilisation). Rejoué sur Étang-Salé (collectif) et Saint-Leu
AC0264 (lotissement)."""
from __future__ import annotations

import os

import pytest

_ETANG = ["97404000AW0099", "97404000AW0451", "97404000AW0624", "97404000AW0625"]
_AC264 = ["97413000AC0264"]


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
                  {"i": _ETANG + _AC264}).scalar()
    if n != 5:
        s.close()
        pytest.skip("parcelles témoins absentes")
    yield s
    s.close()


def _cfg(idus, typ, lignes):
    return {"idus": idus, "type_projet": typ, "programme": {"mode": "saisi", "lignes": lignes}}


@pytest.mark.reel
def test_study_id_stable_et_deterministe(session_reelle):
    from labuse.implantation.service import etudier_payload
    cfg = _cfg(_ETANG, "collectif", [{"type": "T2", "nombre": 8}, {"type": "T3", "nombre": 4}])
    a = etudier_payload(session_reelle, dict(cfg))
    b = etudier_payload(session_reelle, dict(cfg))
    assert a["study_id"] and a["study_id"].startswith("EF-")
    assert a["study_id"] == b["study_id"]               # même config → même study_id
    autre = etudier_payload(session_reelle, _cfg(_ETANG, "collectif", [{"type": "T2", "nombre": 9}]))
    assert autre["study_id"] != a["study_id"]            # config différente → id différent


@pytest.mark.reel
def test_hypotheses_modifiables_recalcul(session_reelle):
    """Éditer les hypothèses (surfaces T1–T4 + profondeur/coef moteur) recalcule le résultat ET change le
    study_id (donc le PDF suit). Les varangues saisies sont acceptées (le moteur travaille sur la surface)."""
    from labuse.implantation.service import etudier_payload
    base = _cfg(_ETANG, "collectif", [{"type": "T2", "nombre": 8, "surface_m2": 56}, {"type": "T3", "nombre": 4, "surface_m2": 70}])
    edit = {**_cfg(_ETANG, "collectif", [{"type": "T2", "nombre": 8, "surface_m2": 62}, {"type": "T3", "nombre": 4, "surface_m2": 78}]),
            "hypotheses": {"profondeur_m": 12.0, "coef_plancher_habitable": 0.82, "varangues": {"T2": 10}}}
    a = etudier_payload(session_reelle, dict(base))
    b = etudier_payload(session_reelle, dict(edit))
    assert a["study_id"] != b["study_id"]                         # recalcul → nouvel identifiant
    assert b["hypotheses"]["surfaces"]["T2"] == 62.0             # surface éditée servie
    assert b["hypotheses"]["profondeur_m"] == 12.0 and b["hypotheses"]["coef_plancher_habitable"] == 0.82
    # un module plus grand → la variante « votre programme » tient MOINS de logements (sanity)
    assert b["variantes"][0]["resume"]["logements"] <= a["variantes"][0]["resume"]["logements"]


@pytest.mark.reel
def test_pdf_egal_ecran_collectif(session_reelle):
    """Verrou du mandat : tout nombre du PDF est un nombre du payload (donc de l'écran)."""
    from labuse.implantation.service import etudier_payload
    from labuse.exports import etude_faisabilite as ef
    p = etudier_payload(session_reelle, _cfg(_ETANG, "collectif", [{"type": "T2", "nombre": 8}, {"type": "T3", "nombre": 4}]))
    rendu = ef.rendu_etude(p, genere_le="22/10/2026")
    intrus = ef.nombres_hors_payload(p, rendu["html"], genere_le="22/10/2026")
    assert intrus == [], f"nombres du PDF absents du payload (double source) : {intrus[:8]}"


@pytest.mark.reel
def test_bilan_surfacique_collectif_clos(session_reelle):
    from labuse.implantation.service import etudier_payload
    p = etudier_payload(session_reelle, _cfg(_ETANG, "collectif", [{"type": "T2", "nombre": 8}, {"type": "T3", "nombre": 4}]))
    b = p["bilan_surfacique"]
    # contenance = zone constructible + hors-zone, et le plan ne se chevauche pas → clos.
    assert b["decomposition_close"] is True and b["plan_sans_chevauchement"] is True and b["clos"] is True
    assert abs((b["zone_constructible_m2"] + b["hors_zone_m2"]) - b["contenance_m2"]) <= 0.02 * b["contenance_m2"]


@pytest.mark.reel
def test_bilan_surfacique_lotissement_clos_et_pdf(session_reelle):
    from labuse.implantation.service import etudier_payload
    from labuse.exports import etude_faisabilite as ef
    p = etudier_payload(session_reelle, _cfg(_AC264, "lotissement", [{"type": "T3", "nombre": 14}]))
    b = p["lotissement"]["bilan_surfacique"]
    # assiette = lots + voirie + communs + PPR + EBC + hors-zone, à la tolérance près.
    assert b["clos"] is True and abs(b["ecart_m2"]) <= 0.02 * b["assiette_m2"]
    assert b["somme_m2"] == pytest.approx(b["assiette_m2"], abs=0.02 * b["assiette_m2"])
    # le PDF lotissement se rend du MÊME payload (study_id stable) ; ses nombres (tableau des lots,
    # voirie, bilan) sortent tous du payload du lotissement (chiffres de l'écran).
    rendu = ef.rendu_lotissement(p, genere_le="22/10/2026")
    # ETUDE-V6-6 (item 10) — n° de document = EF-<8> dérivé du study_id (identique écran/cartouche).
    assert rendu["html"] and rendu["numero"] == p["study_id"][:11] == ef._numero_document(p)
    assert f"{p['lotissement']['tableau_lots']['nombre']}" in rendu["html"]   # nb de lots repris du payload
