"""Matrice Q×A (étape 3) — compute_matrice : Q/A séparés, double verrou complétude, override rouge.

Test DB : on injecte des lignes dryrun_cascade_results synthétiques puis on vérifie matrice_statut.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.scoring.dryrun import compute_matrice

LABEL = "t_matrice"


def _parcel(db, idu):
    db.execute(text(
        "INSERT INTO parcels (idu, commune, geom) VALUES (:i,'Saint-Paul', "
        "ST_SetSRID(ST_GeomFromText('POINT(55.27 -21.01)'),4326)) ON CONFLICT (idu) DO NOTHING"), {"i": idu})
    pid = db.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
    db.execute(text("INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score, "
                    "opportunity_score) VALUES (:r,:p,0,0)"), {"r": LABEL, "p": pid})
    return pid


def _line(db, pid, layer, result="POSITIVE", weight=None, evenement=None):
    db.execute(text(
        "INSERT INTO dryrun_cascade_results (run_label, parcel_id, layer_name, result, weight_applied, evenement) "
        "VALUES (:r,:p,:l,:res,:w,:e)"),
        {"r": LABEL, "p": pid, "l": layer, "res": result, "w": weight, "e": evenement})


@pytest.mark.db
def test_matrice_statuts(db_session):
    d = db_session
    # chaude : Q=66 (zonage+surface +16), A=62 (age +12), A-compl 100%
    c = _parcel(d, "97415000MA0001")
    _line(d, c, "zonage_plu_gpu", weight=8)
    _line(d, c, "surface", weight=8)
    _line(d, c, "age_dirigeant", weight=12)
    # à surveiller : Q=66, pas de signal A (A=50<60)
    sv = _parcel(d, "97415000MA0002")
    _line(d, sv, "zonage_plu_gpu", weight=8)
    _line(d, sv, "surface", weight=8)
    # à surveiller (VERROU) : Q=66, A=62 via dvf mais A-compl 33% (<50) → PAS chaude
    gate = _parcel(d, "97415000MA0003")
    _line(d, gate, "zonage_plu_gpu", weight=8)
    _line(d, gate, "surface", weight=8)
    _line(d, gate, "dvf", weight=12)
    _line(d, gate, "age_dirigeant", result="UNKNOWN")
    _line(d, gate, "bodacc", result="UNKNOWN")
    # à creuser : Q=58
    cr = _parcel(d, "97415000MA0004")
    _line(d, cr, "surface", weight=8)
    # écartée : Q=30 (malus)
    ec = _parcel(d, "97415000MA0005")
    _line(d, ec, "risques", result="SOFT_FLAG", weight=-20)
    # exclue étage 0 → écartée
    ex = _parcel(d, "97415000MA0006")
    _line(d, ex, "bati", result="HARD_EXCLUDE")
    # override rouge : Q faible (30) mais BODACC rouge → chaude
    ro = _parcel(d, "97415000MA0007")
    _line(d, ro, "risques", result="SOFT_FLAG", weight=-20)
    _line(d, ro, "bodacc", result="SOFT_FLAG", evenement="rouge")
    d.flush()

    compute_matrice(d, LABEL, "Saint-Paul")

    def statut(idu):
        return d.execute(text("SELECT matrice_statut FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
                              "WHERE d.run_label=:r AND p.idu=:i"), {"r": LABEL, "i": idu}).scalar()

    assert statut("97415000MA0001") == "chaude"
    assert statut("97415000MA0002") == "a_surveiller"
    assert statut("97415000MA0003") == "a_surveiller"      # double verrou : A-compl 33% < 50 → pas chaude
    assert statut("97415000MA0004") == "a_creuser"
    assert statut("97415000MA0005") == "ecartee"
    assert statut("97415000MA0006") == "ecartee"           # exclue étage 0
    assert statut("97415000MA0007") == "chaude"            # override rouge

    # traçabilité Q/A stockés
    row = d.execute(text("SELECT q_score, a_score, a_completude FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
                         "WHERE d.run_label=:r AND p.idu='97415000MA0001'"), {"r": LABEL}).first()
    assert row[0] == 66 and row[1] == 62 and row[2] == 100
