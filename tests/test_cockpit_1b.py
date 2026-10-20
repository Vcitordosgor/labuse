"""COCKPIT-1b — retours de recette : vitrine comptée UNE fois (point 6) + Journal « Échecs seulement »
(point 2). Les points front (onglet Usine, phrase Circuit, rail, cartes de cache) sont couverts par
tsc/vitest + les tests unitaires de cockpit_resume (test_cockpit_lot_a).

Pattern db : TestClient + session_scope (jamais la fixture db_session, dont la transaction ouverte
bloquerait le DDL idempotent de l'app — deadlock)."""
from __future__ import annotations

import pytest
from sqlalchemy import text


# ─────────────── point 6 — une seule fonction de comptage vitrine (99) ───────────────

@pytest.mark.db
def test_compter_vitrine_exclut_le_referentiel_interne():
    """`sources_catalog.compter_vitrine` = le compteur CANONIQUE. Il n'inclut JAMAIS une source de
    statut `interne` (référentiel) : vitrine ∪ interne = la liste des réservoirs admin, qui comptait
    à tort une source de plus (100 vs 99)."""
    from labuse import sources_catalog as sc
    from labuse.db import session_scope
    with session_scope() as s:
        vitrine = sc.compter_vitrine(s)
        internes_en_vitrine = int(s.execute(text(
            f"SELECT count(*) FROM data_sources WHERE lower(status)='interne' AND ({sc.WHERE_AFFICHEES})"),
            {"masquees": sc.masquees_param()}).scalar() or 0)
        avec_interne = int(s.execute(text(
            f"SELECT count(*) FROM data_sources d WHERE (({sc.WHERE_AFFICHEES}) OR lower(status)='interne')"),
            {"masquees": sc.masquees_param()}).scalar() or 0)
    assert internes_en_vitrine == 0                       # un interne n'est jamais « en vitrine »
    assert avec_interne >= vitrine                        # la liste admin ⊇ la vitrine


@pytest.mark.db
def test_dashboard_badge_sources_accueil_concordent():
    """Les TROIS surfaces donnent le MÊME chiffre (= compter_vitrine) : badge dashboard
    (etats_sources.vitrine), liste /sources (app cliente), compteur d'accueil (site public).
    Plus de « 100 d'un côté, 99 de l'autre »."""
    from fastapi.testclient import TestClient

    from labuse import sources_catalog as sc
    from labuse.api.app import app
    from labuse.db import session_scope
    with session_scope() as s:
        attendu = sc.compter_vitrine(s)
    with TestClient(app) as c:
        circuit = c.get("/admin/circuit").json()
        srcs = c.get("/sources").json()
        accueil = c.get("/accueil/chiffres").json()
    assert circuit["etats_sources"]["vitrine"] == attendu          # badge dashboard
    liste = srcs if isinstance(srcs, list) else (srcs.get("sources") or srcs.get("served") or [])
    assert len(liste) == attendu                                   # liste /sources (app)
    assert accueil.get("sources") == attendu                       # compteur d'accueil (site public)
    # et le badge n'est PLUS la liste des réservoirs admin (vitrine ∪ interne).
    assert circuit["etats_sources"]["vitrine"] <= len(circuit["reservoirs"])


# ─────────────── point 2 — Journal « Échecs seulement » ───────────────

@pytest.mark.db
def test_journal_echecs_seulement():
    from fastapi.testclient import TestClient

    from labuse import circuit_journal as cj
    from labuse.api.app import app
    from labuse.db import session_scope
    lot = cj.nouveau_lot()
    with session_scope() as s:
        cj.ensure(s)
        cj.journaliser(s, "cockpit:lancer-job", "zz-ok-1b", "admin", "ok", lot=lot)
        cj.journaliser(s, "cockpit:lancer-job", "zz-ko-1b", "admin", "echec", lot=lot)
        s.commit()
    with TestClient(app) as c:
        tous = c.get("/admin/circuit/journal?taille=200").json()
        echecs = c.get("/admin/circuit/journal?echecs=1&taille=200").json()

    def _resultats(d):
        out = []
        for e in d["entrees"]:
            out += [m["resultat"] for m in e.get("membres", [])] or [e["resultat"]]
        return out
    assert set(_resultats(echecs)) <= {"echec", "refuse", "timeout"}    # ne garde QUE les échecs
    assert "echec" in _resultats(echecs) and "ok" not in _resultats(echecs)
    assert "ok" in _resultats(tous)                                    # garde-fou : pas un faux vide
