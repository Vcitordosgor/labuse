"""DONNEES-FIX-1 point 4 — les exceptions PLU `modifie_calcul=true` entrent au moteur.

Garde-fous du système unique `zonage.appliquer_exceptions_calcul` + du calibrage figé
`config/plu_exceptions_effet.json` (les 81 exceptions de PLU-EXCEPTIONS-1/A_CALIBRER.csv) :
  - le calibrage couvre EXACTEMENT les 81, réparties en applique/deja_couvert/hors_sdp/non_modelisee ;
  - une majoration conditionnée à la surface n'entre QUE si la condition est vérifiée, et ne fait
    que RELÂCHER (jamais abaisser) la contrainte de zone ;
  - une exception non modélisable n'est jamais approximée : la parcelle la PORTE (règle + article/page) ;
  - un sous-secteur déjà résolu comme zone calibrée (deja_couvert) ne rejoue rien.
"""
from __future__ import annotations

import json
import os

from labuse.faisabilite.zonage import ZoneRules, appliquer_exceptions_calcul, _exceptions_effet

CALIB = os.path.join(os.path.dirname(__file__), "..", "config", "plu_exceptions_effet.json")


def _calib():
    return json.load(open(CALIB, encoding="utf-8"))["entries"]


def test_calibrage_couvre_les_81_exceptions():
    entries = _calib()
    assert len(entries) == 81, f"{len(entries)} entrées, attendu 81 (A_CALIBRER.csv)"
    from collections import Counter
    dec = Counter(e["decision"] for e in entries.values())
    assert set(dec) <= {"applique", "deja_couvert", "hors_sdp", "non_modelisee"}
    # répartition figée (revue manuelle DONNEES-FIX-1 point 4)
    assert dec["applique"] == 4
    assert dec["hors_sdp"] == 9
    assert dec["deja_couvert"] == 21
    assert dec["non_modelisee"] == 47
    # toute décision `applique` porte un effet exploitable ; toute non_modelisee porte article/page
    for e in entries.values():
        if e["decision"] == "applique":
            assert e["effet"] and e["effet"].get("champ") and e["effet"].get("valeur") is not None
        if e["decision"] == "non_modelisee":
            assert e.get("article") and e.get("page_pdf")
        # PLU-CALIBRAGE-5 — le verbatim est présent partout (affichage fiche des règles portées).
        assert e.get("texte"), f"entrée {e['insee']}/{e['zone']} sans verbatim `texte`"


def test_index_par_zone_charge():
    idx = _exceptions_effet()
    assert ("97402", "Ub") in idx and ("97416", "Uf") in idx


def _rules(**kw):
    base = dict(code="Ub", he_m=8.0, hf_m=11.0, emprise_sol_pct=60.0)
    base.update(kw)
    return ZoneRules(**base)


def test_majoration_surface_appliquee_au_dessus_du_seuil():
    r = _rules()
    r2, nm = appliquer_exceptions_calcul(r, "97402", "Ub", 3000.0)
    assert r2.he_m == 10.0 and r2.hf_m == 13.0, "majoration ≥2000 m² non appliquée"
    # r d'origine JAMAIS mutée (copie via replace)
    assert r.he_m == 8.0 and r.hf_m == 11.0


def test_majoration_surface_pas_sous_le_seuil():
    r2, nm = appliquer_exceptions_calcul(_rules(), "97402", "Ub", 1000.0)
    assert r2.he_m == 8.0 and r2.hf_m == 11.0, "majoration appliquée à tort sous le seuil"


def test_majoration_ne_reduit_jamais():
    # base déjà plus haute que la valeur d'exception → la majoration ne l'abaisse pas
    r2, nm = appliquer_exceptions_calcul(_rules(he_m=12.0, hf_m=15.0), "97402", "Ub", 5000.0)
    assert r2.he_m == 12.0 and r2.hf_m == 15.0


def test_non_modelisee_portee_par_la_parcelle():
    # 97416 Uf : exception bande_limite non modélisable → portée, jamais approximée
    r = ZoneRules(code="Uf", he_m=6.0, hf_m=11.0, emprise_sol_pct=50.0)
    r2, nm = appliquer_exceptions_calcul(r, "97416", "Uf", None)
    assert r2.he_m == 6.0, "valeur de zone altérée par une exception non modélisable"
    assert nm, "règle non modélisée non portée"
    assert all(x.get("article") and x.get("page_pdf") for x in nm)
    assert any(x["porte"] == "bande_limite" for x in nm)


def test_zone_sans_exception_inchangee():
    r = ZoneRules(code="Zzz", he_m=9.0)
    r2, nm = appliquer_exceptions_calcul(r, "97411", "Zzz", 5000.0)
    assert r2 is r and nm == []
