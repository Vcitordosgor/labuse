"""FICHE-1 lot 3 — les aléas en détail sur la fiche.

CONTRÔLE D'ACCORD (mandat) : la liste d'aléas de la fiche (`_aleas_block`) est dérivée des MÊMES
lignes de cascade servies que « Pièges et risques » (anti_fiche) — les deux écrans ne peuvent pas
se contredire. Vérifié sur la base réelle (le run servi doit contenir au moins une parcelle à aléa).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.registre import ROBINETS
from labuse.registre.donnees import DONNEES


def test_registre_aleas_declare():
    assert "aleas_parcelle_liste" in DONNEES
    d = DONNEES["aleas_parcelle_liste"]
    assert d.moteur == "cascade" and d.en_attente is None
    assert "aleas_parcelle_liste" in ROBINETS["fiche_parcelle_risques"].chiffres
    # n_vigilances reste servi au-dessus de la liste
    assert "n_vigilances" in ROBINETS["fiche_parcelle_risques"].chiffres


def test_alea_nature_lue_sur_le_libelle():
    from labuse.api.app import _alea_nature
    assert _alea_nature("PPR zone rouge sur 7 % de la surface") == "PPR — zonage réglementaire"
    assert _alea_nature("Aléa inondation — niveau fort.") == "Inondation"
    assert _alea_nature("Aléa mouvement de terrain — niveau moyen.") == "Mouvement de terrain"


@pytest.mark.db
def test_fiche_et_pieges_daccord_sur_les_aleas(db_session):
    """Le nombre d'aléas de la fiche = le nombre de lignes 'risques' servies à Pièges et risques,
    pour toute parcelle du run servi : même moteur, aucune contradiction possible."""
    from labuse import runs
    from labuse.api.app import _aleas_block, _q_v2_fiche
    from labuse.api.served_cascade import served_cascade_lines
    run = runs.current()
    idu = db_session.execute(text(
        "SELECT p.idu FROM dryrun_cascade_results cr JOIN parcels p ON p.id = cr.parcel_id "
        "WHERE cr.run_label = :r AND cr.layer_name = 'risques' "
        "AND cr.result IN ('HARD_EXCLUDE','SOFT_FLAG') LIMIT 1"), {"r": run}).scalar()
    if not idu:
        pytest.skip("base de test sans parcelle à aléa dans le run servi")
    f = _q_v2_fiche(db_session, idu, run)
    fiche_n = (f.get("aleas") or {}).get("n", 0)
    pieges = [l for l in served_cascade_lines(db_session, idu, run)
              if l["layer_name"] == "risques" and l["result"] in ("HARD_EXCLUDE", "SOFT_FLAG")]
    assert fiche_n == len(pieges), (fiche_n, len(pieges))
    assert fiche_n > 0
