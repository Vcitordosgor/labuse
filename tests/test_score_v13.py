"""Score V v1.3 « correction des signes » (mandat M1, 12/07/2026) — moteur pur, sans DB.

Contrats : cessation/radiation → 0 pt (tracés) · famille B hors de V · cession de fonds
inchangée vs v1.2 · SCI dormante → 0 pt dans V + tag veille_succession · PP jamais taggés ·
match par dénomination jamais taggé.
"""
from __future__ import annotations

from datetime import date

from labuse.scoring import score_v_constants as C
from labuse.scoring.score_v import _retain, _signal, famille_b, veille_succession_eligible

TODAY = date(2026, 7, 12)
MATCH = {"type": "siren", "valeur": "123456789", "confiance": 1.0}


def _fiche(**kw):
    base = {"etat_administratif": "A", "nature_juridique": "5499", "activite_principale": "68.20B",
            "date_creation": "1990-01-01", "date_fermeture": None, "date_mise_a_jour_rne": None,
            "siege": {"departement": "974", "commune_insee": "97415", "adresse": "St-Paul",
                      "code_pays_etranger": None, "libelle_commune": "SAINT-PAUL"},
            "dirigeants": [], "denomination": "TEST"}
    base.update(kw)
    return base


def test_cessation_vaut_zero_point():
    sigs = famille_b("123456789", _fiche(etat_administratif="C"), None, "", MATCH, TODAY)
    cess = [s for s in sigs if s["code"] == "RNE_CESSATION"]
    assert cess and cess[0]["points"] == 0


def test_famille_b_est_sortie_de_v():
    """Tout le barème B vaut 0 : quel que soit le stack B, la contribution à V est nulle."""
    assert all(pts == 0 for fam, pts, _ in C.SIGNALS.values() if fam == "B")
    cands = [_signal("RNE_DIRIGEANT_75", source="x", match=MATCH),
             _signal("RNE_SCI_DORMANTE", source="x", match=MATCH)]
    _, total = _retain(cands, None)
    assert total == 0


def test_cession_de_fonds_identique_v12():
    assert C.SIGNALS["BODACC_CESSION_FONDS"] == ("A", 10, "Cession de fonds de commerce < 12 mois")
    retained, total = _retain([_signal("BODACC_CESSION_FONDS", source="x", match=MATCH)], None)
    assert total == 10 and retained[0]["points"] == 10


def test_radiation_ne_deplace_plus_la_cession():
    """v1.3 : dans la famille A, le MAX retient la cession (10) face à la radiation (0)."""
    retained, total = _retain([_signal("BODACC_RADIATION", source="x", match=MATCH),
                               _signal("BODACC_CESSION_FONDS", source="x", match=MATCH)], None)
    assert [s["code"] for s in retained] == ["BODACC_CESSION_FONDS"] and total == 10


def test_sci_dormante_zero_dans_v_et_taggee():
    sigs = famille_b("1", _fiche(date_creation="2001-05-01"), None, "SCI", MATCH, TODAY)
    assert [s["code"] for s in sigs] == ["RNE_SCI_DORMANTE"] and sigs[0]["points"] == 0
    assert veille_succession_eligible("pm", C.CONF_SIREN_DIRECT, None, True)


def test_veille_succession_dirigeant_70():
    assert veille_succession_eligible("pm", C.CONF_SIREN_DIRECT, 70, False)
    assert not veille_succession_eligible("pm", C.CONF_SIREN_DIRECT, 69, False)


def test_pp_jamais_taggees():
    assert not veille_succession_eligible("pp", C.CONF_SIREN_DIRECT, 90, True)
    assert not veille_succession_eligible("public", C.CONF_SIREN_DIRECT, 90, True)
    assert not veille_succession_eligible("bailleur", C.CONF_SIREN_DIRECT, 90, True)


def test_match_nom_jamais_tagge():
    """Identité par dénomination (0.8) = jamais de tag — le radar exige le SIREN confirmé."""
    assert not veille_succession_eligible("pm", C.CONF_DENOMINATION, 80, True)
    assert not veille_succession_eligible("pm", None, 80, True)
