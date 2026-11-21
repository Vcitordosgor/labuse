"""CHIRURGICAL-FIX-1 (LOT A) — le VERDICT de non-constructibilité est le MÊME partout.

Une parcelle en zone urbaine mais non constructible pour une AUTRE raison — habitat interdit en zone
UE (97404000AM0838) ou commune au RNU sans potentiel résiduel (97417000AO0050) — doit porter le même
verdict, lu au point unique `potentiel_batir`, sur TOUTES les surfaces :
  · fiche      — analyse_labuse.cause_libelle (nommé, pas la contribution « aucune SDP ») ;
  · Bilan      — modèle `sources_parcelle` (non_constructible_pct = 100, motif nommé — E104) ;
  · Estimer    — `estimer3.rapport3` (jamais « (Pas) » sur une commune RNU — E105) ;
  · Comparatif — cause EN CLAIR, jamais le code brut « habitat interdit:UE » (E112a).

Le test ÉCHOUE si une surface dit autre chose que la fiche (« constructible », « 100 % constructible »,
« (Pas) », cause brute). Base APPLICATIVE réelle requise (marqueur `reel`) ; joué au push par le hook.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.coherence, pytest.mark.reel]

# AM0838 : zone UE (famille U) mais habitat interdit. AO0050 : commune au RNU, sans potentiel résiduel.
NON_CONSTRUCTIBLES = ["97404000AM0838", "97417000AO0050"]


def _present(app_session, idu: str) -> bool:
    return app_session.execute(text("SELECT 1 FROM parcels WHERE idu=:i"), {"i": idu}).scalar() is not None


@pytest.mark.parametrize("idu", NON_CONSTRUCTIBLES)
def test_verdict_non_constructible_identique_partout(app_session, idu):
    if not _present(app_session, idu):
        pytest.skip(f"{idu} absente de la base réelle")
    from labuse.bilan.reperes import sources_parcelle
    from labuse.exports.blocs.comparatif import _cause_court
    from labuse.faisabilite.potentiel_batir import potentiel_batir

    # 1) POINT UNIQUE — le verdict que lit la fiche : non constructible + un motif nommé.
    pb = potentiel_batir(app_session, idu)
    assert pb and (not pb.get("constructible") or pb.get("rien_a_batir")), \
        f"{idu} : potentiel_batir la dit constructible — le verdict de référence ne ferme pas la parcelle"
    assert pb.get("motif"), f"{idu} : verdict sans motif"

    # 2) BILAN (modèle) — ne présente PLUS la parcelle 100 % constructible (E104).
    src = sources_parcelle(app_session, idu)
    assert src["non_constructible_pct"] == 100.0, \
        f"{idu} : Bilan modèle non_constructible_pct={src['non_constructible_pct']} (≠ 100 → présentée constructible)"
    assert src.get("non_constructible_motif"), f"{idu} : Bilan modèle ferme la parcelle sans nommer le motif"

    # 3) COMPARATIF — la cause est écrite EN CLAIR, jamais le code brut « habitat interdit:UE » (E112a).
    cause = app_session.execute(text(
        "SELECT r.cause FROM parcel_residuel r JOIN parcels p ON p.id = r.parcel_id "
        "WHERE p.idu = :i AND r.cause IS NOT NULL"), {"i": idu}).scalar()
    if cause:
        court = _cause_court(cause)
        assert court and ":" not in court, f"{idu} : Comparatif rend la cause brute « {court} » (deux-points + code)"


def test_estimer_commune_rnu_sans_code_pas(app_session):
    """E105 — Estimer sur une commune au RNU n'écrit JAMAIS « (Pas) » (le libellé « Pas de PLU local »
    pris pour un code de zone). La raison reste dite, en clair."""
    idu = "97417000AO0050"
    if not _present(app_session, idu):
        pytest.skip(f"{idu} absente de la base réelle")
    from labuse.api.app import _q_v2_fiche
    from labuse.pige import estimer3

    fiche = _q_v2_fiche(app_session, idu)
    r3 = estimer3.rapport3(app_session, idu, fiche)
    est = r3.get("estimation") or {}
    raison = est.get("terrain_sans_total_raison") or ""
    assert "(Pas)" not in raison, f"Estimer RNU écrit encore « (Pas) » : {raison!r}"
    assert est.get("terrain_non_constructible") is True, "Estimer n'affiche pas la non-constructibilité"
