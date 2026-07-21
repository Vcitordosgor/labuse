"""O4 — TRADUCTEUR PLU : application déterministe des règles chiffrées à la parcelle.

Chaque règle sourcée ; emprise/pleine terre converties en m² sur la surface ; A_VERIFIER signalé
(jamais comblé) ; règle absente (None) omise (pas de chiffre inventé). Jamais de conseil juridique.
"""
from __future__ import annotations

from types import SimpleNamespace as NS

from labuse.api import traducteur as t
from labuse.faisabilite.plu_rules import A_VERIFIER


def _zr(**kw):
    base = dict(emprise_sol_pct=None, he_m=None, hf_m=None, recul_voirie_m=None,
               recul_limites_sep_m=None, stat_logement=None, pleine_terre_pct=None,
               hauteur_mode=None, sources={})
    base.update(kw)
    return NS(**base)


def test_emprise_convertie_en_m2_et_sourcee():
    zr = _zr(emprise_sol_pct=40, sources={"emprise": "Art. 9 UA"})
    rows = t._applied(zr, 1000.0)
    r = next(x for x in rows if "Emprise" in x["regle"])
    assert "400 m²" in r["valeur"] and "40 % de 1000" in r["valeur"] and r["source"] == "Art. 9 UA"
    assert "40 % × 1000" in r["calcul"]


def test_pleine_terre_m2():
    rows = t._applied(_zr(pleine_terre_pct=30, sources={"pleine_terre": "Art. 13"}), 1000.0)
    assert any("300 m²" in x["valeur"] for x in rows if "Pleine terre" in x["regle"])


def test_a_verifier_signale_pas_comble():
    rows = t._applied(_zr(recul_voirie_m=A_VERIFIER, sources={"recul_voirie": "Art. 6"}), 500.0)
    r = next(x for x in rows if "voirie" in x["regle"].lower())
    assert r["a_verifier"] is True and "vérifier" in r["valeur"]


def test_regle_absente_omise():
    rows = t._applied(_zr(), 500.0)   # tout None
    assert rows == []                 # aucune règle → aucune ligne inventée


def test_hauteurs_et_reculs_avec_unite():
    zr = _zr(he_m=9, hf_m=12, recul_limites_sep_m=3, sources={"hauteur": "Art. 10", "recul_limites": "Art. 7"})
    rows = t._applied(zr, 800.0)
    vals = {x["regle"]: x["valeur"] for x in rows}
    assert "9 m" in str(vals.get("Hauteur à l'égout / acrotère"))
    assert "3 m" in str(vals.get("Recul sur limites séparatives"))


def test_prospect_note():
    rows = t._applied(_zr(hauteur_mode="prospect", sources={"hauteur": "Art. 10"}), 800.0)
    assert any("prospect" in x["valeur"] for x in rows)


def test_disclaimer_pas_de_conseil_juridique():
    assert "conseil juridique" in t.DISCLAIMER and "opposable" in t.DISCLAIMER
