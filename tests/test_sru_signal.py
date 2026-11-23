"""OUTIL-COMMUNES-FIX-1 bloquant 2 — le signal SRU de la fiche commune suit le STATUT officiel.

Le défaut (relecteur) : Cilaos (2,94 / 25) et Saint-Philippe (9,57 / 20), EXEMPTÉES pour la période,
portaient un signal rouge « SRU déficitaire » parce que le signal se calculait sur la seule soustraction
objectif − taux. Une commune exemptée (ou conforme) ne doit JAMAIS porter « déficitaire ». Taux, objectif,
statut et année sont affichés séparément ; le signal est daté.

Test PUR (sans base) sur `_sru_signal`.
"""
from __future__ import annotations

from labuse.api.app import _sru_signal

_MILL = "inventaire LLS 01/01/2024 · périmètre 01/01/2025 · prélèvement 2025"


def _sru(statut, taux, obj, millesime=_MILL):
    return {"statut": statut, "taux_lls": taux, "objectif_pct": obj, "millesime": millesime}


def test_exemptee_ne_porte_jamais_deficitaire():
    # Cilaos et Saint-Philippe : exemptées, taux < objectif — AUCUN signal d'alerte.
    assert _sru_signal(_sru("exemptee", 2.94, 25)) is None
    assert _sru_signal(_sru("exemptee", 9.57, 20)) is None


def test_conforme_sans_signal():
    assert _sru_signal(_sru("conforme", 38.62, 20)) is None


def test_deficitaire_signal_date():
    s = _sru_signal(_sru("deficitaire", 18.33, 25))
    assert s and s["code"] == "sru" and s["ton"] == "rouge"
    assert "déficitaire" in s["libelle"]
    assert "2025" in s["libelle"]          # statut DATÉ
    assert "18,3" in s["libelle"] and "25" in s["libelle"]   # taux / objectif affichés


def test_carencee_distincte_de_deficitaire():
    s = _sru_signal(_sru("carencee", 10.29, 25))
    assert s and "carencée" in s["libelle"] and "2025" in s["libelle"]


def test_donnee_absente_sans_signal():
    assert _sru_signal(None) is None
    assert _sru_signal({"statut": "deficitaire", "taux_lls": None, "objectif_pct": 25}) is None
    assert _sru_signal({"statut": "deficitaire", "taux_lls": 10, "objectif_pct": None}) is None
