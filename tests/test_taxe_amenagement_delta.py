"""TAXE-AMÉNAGEMENT-1 lot A — ingestion des taux communaux depuis le jeu DGFiP DELTA.

On gèle le COMPORTEMENT du chargeur (sans réseau, via des enregistrements injectés) :
- le taux communal GÉNÉRAL est retenu, l'INSEE est reconstruit (974 + 2 chiffres) ;
- deux délibérations successives → on garde la date d'effet la plus récente ;
- un taux hors bornes [0 ; 20] est écarté et listé (aucun taux aberrant n'entre) ;
- une commune absente de la source est signalée (jamais un taux inventé pour combler) ;
- la part départementale est REMONTÉE (confirmation) sans entrer dans la table communale.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion import taxe_amenagement_delta as ta

pytestmark = pytest.mark.db


def _rec(commune, taux, effet="2022-01-01", dep="974", def_prov="DEFINITIF",
         zone="Communale", libelle="X"):
    return {"departement": dep, "commune": commune, "taux": taux, "date_effet": effet,
            "date_fin": None, "def_prov": def_prov, "zone_application": zone,
            "libelle_commune": libelle}


def test_ingestion_remplit_la_table_par_insee(db_session):
    recs = [_rec("01", 5.0, libelle="LES AVIRONS"),
            _rec("11", 3.0, libelle="SAINT-DENIS"),
            _rec("19", 1.0, libelle="SAINTE-ROSE")]
    res = ta.ingest_taxe_amenagement(
        db_session, records_communaux=recs,
        record_departemental=_rec(None, 2.5, zone="Départementale", libelle=None))
    assert res["n"] == 3
    assert set(res["communes"]) == {"97401", "97411", "97419"}
    assert res["taux_departemental_pct"] == 2.5
    rows = dict(db_session.execute(text(
        "SELECT insee, part_communale_pct FROM taxe_amenagement_taux")).all())
    assert rows == {"97401": 5.0, "97411": 3.0, "97419": 1.0}


def test_garde_la_deliberation_la_plus_recente(db_session):
    recs = [_rec("07", 5.0, effet="2022-01-01"),   # ancienne
            _rec("07", 3.0, effet="2025-01-01")]   # en vigueur
    ta.ingest_taxe_amenagement(db_session, records_communaux=recs)
    row = db_session.execute(text(
        "SELECT part_communale_pct, delib_date FROM taxe_amenagement_taux WHERE insee='97407'"
    )).one()
    assert float(row[0]) == 3.0
    assert row[1].isoformat() == "2025-01-01"


def test_taux_hors_bornes_ecarte_et_liste(db_session):
    recs = [_rec("01", 5.0), _rec("02", 99.0)]     # 99 % = aberrant → écarté
    res = ta.ingest_taxe_amenagement(db_session, records_communaux=recs)
    assert res["n"] == 1
    assert any("97402=99" in h for h in res["hors_bornes"])
    n = db_session.execute(text("SELECT count(*) FROM taxe_amenagement_taux")).scalar()
    assert n == 1


def test_commune_absente_signalee_jamais_inventee(db_session):
    res = ta.ingest_taxe_amenagement(db_session, records_communaux=[_rec("11", 3.0)])
    assert res["n"] == 1
    assert len(res["manquantes"]) == 23     # 24 attendues − 1 présente
    assert "Les Avirons" in res["manquantes"]


def test_source_datee_et_sourcee(db_session):
    ta.ingest_taxe_amenagement(db_session, records_communaux=[_rec("11", 3.0)])
    src = db_session.execute(text(
        "SELECT source FROM taxe_amenagement_taux WHERE insee='97411'")).scalar()
    assert "DELTA" in src and ta.DATASET in src


# ─────────────────────────── Lot C — millésime affiché + fraîcheur ───────────────────────────
from datetime import date  # noqa: E402

from labuse.taxe_amenagement import calculer, config, taux_communal_public  # noqa: E402


def test_millesime_expose_et_frais(db_session):
    ta.ingest_taxe_amenagement(db_session, records_communaux=[_rec("11", 3.0, effet="2022-01-01")])
    pub = taux_communal_public(db_session, "97411")   # relevé aujourd'hui → frais
    # EXPORTS-REBRANCHEMENT-1 lot 0 — la phrase client dit le FAIT (délibération), la source
    # vit dans les champs structurés (source/maj_at) : plus de « DGFiP/DELTA, relevé le … ».
    assert "en vigueur depuis le 01/01/2022" in pub["millesime"]
    assert "DGFiP" not in pub["millesime"] and "relevé le" not in pub["millesime"]
    assert pub["delib_date"] == "2022-01-01"
    assert pub["perime"] is False


def test_alerte_taux_perime_apres_un_an(db_session):
    ta.ingest_taxe_amenagement(db_session, records_communaux=[_rec("11", 3.0)])
    # même relevé, mais on regarde depuis « deux ans plus tard » → périmé.
    pub = taux_communal_public(db_session, "97411", today=date(2028, 9, 8))
    assert pub["perime"] is True


def test_millesime_seulement_pour_le_taux_public():
    # taux SAISI → pas de millésime public exposé (on ne prête pas une date au chiffre du client).
    saisi = calculer(surface_taxable_m2=100, taux_communal_pct=4.0,
                     taux_communal_public_millesime="X", taux_communal_public_perime=True)
    assert saisi["taux_communal_source"] == "saisi"
    assert saisi["taux_communal_millesime"] is None
    assert saisi["taux_communal_perime"] is None
    # taux PUBLIC → millésime + fraîcheur propagés.
    pub = calculer(surface_taxable_m2=100, taux_communal_public_pct=3.0,
                   taux_communal_public_millesime="Taux communal … source DGFiP/DELTA",
                   taux_communal_public_delib_date="2022-01-01", taux_communal_public_perime=False)
    assert pub["taux_communal_source"] == "public"
    assert "DGFiP/DELTA" in pub["taux_communal_millesime"]
    assert pub["taux_communal_perime"] is False


def test_part_departementale_confirmee_par_delta():
    c = config()
    assert c["taux"]["part_departementale_confirmee_974"] is True
    res = calculer(surface_taxable_m2=100, taux_communal_pct=3.0)
    assert res["part_departementale_confirmee"] is True


# ─────────────────── TAXE-FIX-1 point 3 — secteurs à taux majoré (grain parcelle) ───────────────────
def test_idu_from_delta_reconstruit_l_idu():
    """L'IDU cadastral (14 car.) reconstruit d'une ligne DELTA — pur, sans DB ni réseau."""
    from labuse.ingestion.taxe_amenagement_delta import _idu_from_delta
    assert _idu_from_delta({"departement": "974", "commune": "15", "prefixe": "000",
                            "section": "CT", "parcelle": "2268"}) == "97415000CT2268"
    # zéro-complétion défensive (préfixe 3, section 2, parcelle 4)
    assert _idu_from_delta({"departement": "974", "commune": "01", "prefixe": "0",
                            "section": "B", "parcelle": "5"}) == "974010000B0005"
    # incomplet ou hors 974 → None (jamais un IDU partiel)
    assert _idu_from_delta({"departement": "974", "commune": "15", "section": "",
                            "parcelle": "2268"}) is None
    assert _idu_from_delta({"departement": "973", "commune": "15", "section": "CT",
                            "parcelle": "2268"}) is None


def _sec(commune, section, parcelle, taux, prefixe="000", effet="2022-01-01"):
    return {"departement": "974", "commune": commune, "prefixe": prefixe, "section": section,
            "parcelle": parcelle, "taux": taux, "date_effet": effet, "date_fin": None,
            "def_prov": "DEFINITIF", "zone_application": "Communale", "libelle_commune": "SAINT-PAUL"}


def test_secteur_majore_ingere_et_resolu_par_parcelle(db_session):
    from labuse.taxe_amenagement import taux_parcelle, taux_secteur
    res = ta.ingest_taxe_amenagement(
        db_session,
        records_communaux=[_rec("15", 5.0, libelle="SAINT-PAUL")],
        records_secteurs=[_sec("15", "CT", "2268", 10.0), _sec("15", "DK", "1053", 10.0),
                          _sec("15", "ZZ", "9999", 99.0)])   # 99 % = sentinelle → écartée
    assert res["secteurs"] == 2
    assert res["secteurs_communes"] == ["97415"]
    assert any("=99" in h for h in res["secteurs_hors_bornes"])
    # parcelle DANS un secteur → 10 % majoré ; hors secteur → 5 % général (même commune)
    sec = taux_parcelle(db_session, "97415000CT2268")
    assert sec["part_communale_pct"] == 10.0 and sec["secteur_majore"] is True
    assert "Secteur à taux majoré" in sec["millesime"]
    gen = taux_parcelle(db_session, "97415000AB0001")
    assert gen["part_communale_pct"] == 5.0 and gen["secteur_majore"] is False
    assert taux_secteur(db_session, "97415000AB0001") is None


def test_calculer_prend_le_taux_du_secteur(db_session):
    """calculer() reçoit le taux résolu (secteur) via l'endpoint → total au taux majoré."""
    from labuse.taxe_amenagement import calculer as _calc, taux_parcelle
    ta.ingest_taxe_amenagement(db_session, records_communaux=[_rec("15", 5.0, libelle="SAINT-PAUL")],
                               records_secteurs=[_sec("15", "CT", "2268", 10.0)])
    pub = taux_parcelle(db_session, "97415000CT2268")
    out = _calc(surface_taxable_m2=100, taux_departemental_pct=2.5,
                taux_communal_public_pct=pub["part_communale_pct"],
                taux_communal_public_source=pub["source"],
                taux_communal_secteur_majore=pub["secteur_majore"])
    assert out["taux_communal_pct"] == 10.0
    assert out["taux_communal_secteur_majore"] is True
    assert out["part_communale_eur"] == round(100 * 892 * 0.10, 2)


# ─────────── TAXE-INGEST-EXPORT — les secteurs passent par /exports/json (pas /records) ───────────
class _FakeResp:
    def __init__(self, data): self._d = data
    def raise_for_status(self): pass
    def json(self): return self._d


class _FakeClient:
    def __init__(self, data): self._d = data; self.calls = []
    def get(self, url, params=None): self.calls.append((url, params)); return _FakeResp(self._d)


def test_fetch_export_lit_un_tableau_direct_sans_pagination():
    """/exports/json renvoie un TABLEAU JSON direct (pas d'enveloppe {results}), en un seul appel
    (aucun plafond 10 000, contrairement à /records)."""
    from labuse.ingestion.taxe_amenagement_delta import _fetch_export
    cl = _FakeClient([{"departement": "974", "commune": "15", "section": "CT",
                       "parcelle": "2268", "taux": 10.0}])
    out = _fetch_export("where-secteur", client=cl)
    assert len(out) == 1 and out[0]["taux"] == 10.0
    assert len(cl.calls) == 1                                  # UN seul appel, pas de boucle offset
    assert "exports/json" in cl.calls[0][0]
    assert "offset" not in (cl.calls[0][1] or {})
