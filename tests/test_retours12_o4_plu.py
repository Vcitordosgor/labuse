"""RETOURS-12 O4 — « PLU » : bug IDU « Parcelle inconnue » + compteurs réconciliés.

1. verif_procedure NORMALISE l'IDU (casse, espaces) — un IDU valide en minuscules ou avec un
   espace collé ne doit plus renvoyer « Parcelle inconnue » (bug de Vic : 97413000CJ0096).
2. Le compteur de l'annuaire (procédures en cours) et le registre des procédures lisent la MÊME
   source (veille_plu) : Les Trois-Bassins (révision prescrite le 02/06/2022) est COMPTÉ.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from labuse.api.modules import plu_annuaire_communes, verif_procedure

pytestmark = pytest.mark.db

TB_IDU = "97423000ZZ9001"   # Les Trois-Bassins (INSEE 97423), révision active au registre veille_plu


def _pose_parcelle(db, idu: str) -> None:
    db.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
    db.execute(text(
        "INSERT INTO parcels (idu, commune, geom) VALUES "
        "(:i, 'Les Trois-Bassins', ST_SetSRID(ST_Buffer(ST_MakePoint(55.29, -21.10), 0.0002), 4326))"),
        {"i": idu})


def test_verif_procedure_normalise_casse_et_espaces(db_session):
    _pose_parcelle(db_session, TB_IDU)
    # minuscules + espace en queue = un IDU VALIDE collé/saisi maladroitement → plus de 404
    for saisi in (TB_IDU.lower(), TB_IDU + " ", "  " + TB_IDU + "\n"):
        out = verif_procedure(saisi, db=db_session)
        assert out["idu"] == TB_IDU
        assert out["commune"] == "Les Trois-Bassins"


def test_verif_procedure_idu_vraiment_inconnu_reste_404(db_session):
    db_session.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": TB_IDU})
    with pytest.raises(HTTPException) as ex:
        verif_procedure(TB_IDU, db=db_session)
    assert ex.value.status_code == 404


def test_compteur_procedures_reconcilie_inclut_trois_bassins(db_session):
    d = plu_annuaire_communes(db=db_session)
    # source unique veille_plu : 3 révisions générales actives (dont Les Trois-Bassins)
    assert d["n_procedures"] >= 3
    assert d["procedures_par_etat"].get("révision générale", 0) >= 3
    tb = next(c for c in d["communes"] if c["insee"] == "97423")
    assert tb["procedure_active"] == "révision générale"
    # le compteur « règlement » (statut GPU) reste distinct — jamais confondu avec la procédure
    assert "n_revision" in d and "n_rnu" in d
