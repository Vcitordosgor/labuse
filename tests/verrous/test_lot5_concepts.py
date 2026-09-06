"""CIRCUIT-5 lot 5 — le verrou des concepts et des moteurs. Preuves cassé → vert."""
from __future__ import annotations

import pytest

from labuse import circuit_verrous as CV
from labuse import sonde_circuit
from labuse.registre import donnees as D

pytestmark = pytest.mark.verrous


# ── V5a — un concept = un id ────────────────────────────────────────────────────────────

def test_v5a_prouve_casse_sur_un_doublon_de_libelle(monkeypatch):
    """Deux ids au même libellé normalisé (posés exprès) cassent le verrou — la casse et les
    accents ne suffisent pas à distinguer deux concepts."""
    dbl = dict(D.DONNEES)
    modele = next(iter(D.DONNEES.values()))
    dbl["zz_doublon_a"] = D.Donnee("Prix du marché", "€", "commune", "définition A",
                                   None, "passe_plat", "f:a")
    dbl["zz_doublon_b"] = D.Donnee("PRIX du   marche", "€", "commune", "définition B",
                                   None, "passe_plat", "f:b")
    monkeypatch.setattr(D, "DONNEES", dbl)
    r = CV.verrou_concepts()
    assert r.verdict == "casse"
    assert any("zz_doublon_a" in d and "zz_doublon_b" in d for d in r.details)


def test_v5a_prouve_casse_sur_une_definition_partagee_non_assumee(monkeypatch):
    dbl = dict(D.DONNEES)
    dbl["zz_def_a"] = D.Donnee("Libellé A", "€", "commune", "la même phrase exactement",
                               None, "passe_plat", "f:a")
    dbl["zz_def_b"] = D.Donnee("Libellé B", "€", "commune", "La même  phrase exactement",
                               None, "passe_plat", "f:b")
    monkeypatch.setattr(D, "DONNEES", dbl)
    r = CV.verrou_concepts()
    assert r.verdict == "casse"


def test_v5a_vert_sur_le_registre_reel_et_groupes_assumes():
    """Le registre réel passe : zéro collision hors les DEUX groupes assumés (hypothèses
    saisies, mosaïques ortho par période) — motivés dans le code et CONCEPTS-CANONIQUES.md."""
    r = CV.verrou_concepts()
    assert r.verdict == "ok", r.details
    assert len(D.DEFINITIONS_PARTAGEES_ASSUMEES) == 2


# ── V5b — une donnée = une fonction ─────────────────────────────────────────────────────

def test_v5b_prouve_casse_sur_un_sql_propre(monkeypatch):
    """Un `sql_propre` réintroduit (la régression que CIRCUIT-2 a éteinte) casse le verrou."""
    dbl = dict(D.DONNEES)
    dbl["zz_sauvage"] = D.Donnee("Compteur sauvage", "nombre", "global", "un SELECT dans un coin",
                                 None, "sql_propre", "api/app.py:9999")
    monkeypatch.setattr(D, "DONNEES", dbl)
    r = CV.verrou_une_donnee_une_fonction()
    assert r.verdict == "casse"
    assert any("zz_sauvage" in d and "sql_propre" in d for d in r.details)


def test_v5b_prouve_casse_sans_fonction(monkeypatch):
    dbl = dict(D.DONNEES)
    dbl["zz_sans_fonction"] = D.Donnee("Sans producteur", "nombre", "global", "def",
                                       None, "passe_plat", "  ")
    monkeypatch.setattr(D, "DONNEES", dbl)
    r = CV.verrou_une_donnee_une_fonction()
    assert r.verdict == "casse"


def test_v5b_vert_sur_le_registre_reel():
    r = CV.verrou_une_donnee_une_fonction()
    assert r.verdict == "ok", r.details[:5]
    assert "sql_propre = 0, front = 0" in r.preuve


# ── V5c — zéro couple silencieux ────────────────────────────────────────────────────────

def test_v5c_prouve_casse_sur_un_couple_silencieux(monkeypatch):
    """Un chiffre multi-robinets retiré de NON_SONDES (silence posé exprès) casse le verrou,
    et le détail NOMME le couple — jamais un « non couvert »."""
    ampute = dict(sonde_circuit.NON_SONDES)
    ampute.pop("taux_lls_pct")
    monkeypatch.setattr(sonde_circuit, "NON_SONDES", ampute)
    r = CV.verrou_couples_sondes()
    assert r.verdict == "casse"
    assert any("taux_lls_pct" in d for d in r.details)


def test_v5c_vert_et_ventile_les_238_couples():
    r = CV.verrou_couples_sondes()
    assert r.verdict == "ok", r.details[:5]
    assert "couples sondés" in r.preuve and "mono-robinet" in r.preuve


def test_sonde_couvre_reference_le_registre():
    """SONDE_COUVRE ne peut nommer que des robinets qui SERVENT le chiffre (vérité croisée
    avec le registre — un mapping qui dérive casserait ici)."""
    from labuse.registre import CHIFFRES, ROBINETS
    robs_par_chiffre: dict[str, set] = {}
    for rid, rob in ROBINETS.items():
        for c in rob.chiffres:
            robs_par_chiffre.setdefault(c, set()).add(rid)
    for c, robs in sonde_circuit.SONDE_COUVRE.items():
        assert c in CHIFFRES, c
        for r in robs:
            assert r in ROBINETS, (c, r)
            assert r in robs_par_chiffre.get(c, set()), (c, r)
    for c in sonde_circuit.NON_SONDES:
        assert c in CHIFFRES, c


# ── 5.3 — témoins tournants ─────────────────────────────────────────────────────────────

@pytest.mark.db
def test_temoins_tournants_deterministes_et_bornes(db_session):
    """Le tirage du jour est DÉTERMINISTE (rejouable dans la nuit), borné à n, et tiré des
    parcelles consultées la VEILLE (journal d'usage)."""
    from sqlalchemy import text
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS consultation_log (id bigserial PRIMARY KEY,"
        " ts timestamptz DEFAULT now(), sujet text, chemin text, idu varchar(20))"))
    db_session.execute(text("DELETE FROM consultation_log"))
    for i in range(80):
        db_session.execute(text(
            "INSERT INTO consultation_log (idu, ts, sujet, chemin) "
            "VALUES (:i, now(), 'parcelle', '/parcels')"),
            {"i": f"974150000A{i:04d}"})
    t1 = sonde_circuit.temoins_tournants(db_session, n=50)
    t2 = sonde_circuit.temoins_tournants(db_session, n=50)
    assert t1 == t2                       # même jour → même tirage
    assert len(t1) == 50
    db_session.execute(text(
        "UPDATE consultation_log SET ts = now() - interval '3 days'"))
    assert sonde_circuit.temoins_tournants(db_session, n=50) == []   # rien consulté hier
