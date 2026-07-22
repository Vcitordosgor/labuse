"""M2 — refonte « Projet » : fusion des doublons (conflit de statuts) + non-perte au rejeu.

Tests DB appelant les fonctions d'endpoint DIRECTEMENT avec `db_session` (transactionnel, rollback)
— pas de TestClient (isolation de session). Zéro touche au scoring.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import models
from labuse.api import projets


_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


def _parcelle(s, idu):
    return s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 800, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": _WKT}).scalar()


def _projet(s, nom):
    p = models.Projet(nom=nom, fiche={"type_programme": "logements"}, filtres={}, programme=None)
    s.add(p); s.flush()
    return p


def _pp(s, pid, pc, statut):
    s.execute(text(
        "INSERT INTO projet_parcelles (projet_id, parcel_id, statut, created_at, updated_at) "
        "VALUES (:pj,:pc,:st, now(), now())"), {"pj": pid, "pc": pc, "st": statut})


@pytest.mark.db
def test_fusion_conflit_statut_le_plus_avance_gagne(db_session):
    s = db_session
    pa = _parcelle(s, "97499000ZA0001")   # conflit : retenue (proj A) vs écartée (proj B) → retenue gagne
    pb = _parcelle(s, "97499000ZB0002")   # sans conflit : proposée seule
    A, B = _projet(s, "Doublon Ouest"), _projet(s, "Doublon Ouest")
    _pp(s, A.id, pa, "retenue"); _pp(s, A.id, pb, "proposee")
    _pp(s, B.id, pa, "ecartee")

    res = projets.projets_fusionner(projets.FusionIn(ids=[A.id, B.id]), None, s)

    assert res["cible"] == A.id and res["sources_archivees"] == [B.id]
    assert res["n_parcelles"] == 2
    # conflit signalé, jamais silencieux ; statut le plus avancé (retenue) retenu
    assert len(res["conflits"]) == 1
    c = res["conflits"][0]
    assert c["parcel_id"] == pa and c["retenu"] == "retenue" and set(c["statuts"]) == {"retenue", "ecartee"}
    # la cible porte l'union avec le gagnant ; la source est archivée (rien supprimé)
    assert s.execute(text("SELECT statut FROM projet_parcelles WHERE projet_id=:p AND parcel_id=:c"),
                     {"p": A.id, "c": pa}).scalar() == "retenue"
    assert s.execute(text("SELECT count(*) FROM projet_parcelles WHERE projet_id=:p"), {"p": A.id}).scalar() == 2
    assert s.get(models.Projet, B.id).statut == "archive"
    assert s.execute(text("SELECT count(*) FROM projet_parcelles WHERE projet_id=:p"), {"p": B.id}).scalar() == 1  # source intacte


@pytest.mark.db
def test_fusion_cas_facile_quatre_vides(db_session):
    s = db_session
    ps = [_projet(s, "Résidence étudiante Ouest") for _ in range(4)]
    res = projets.projets_fusionner(projets.FusionIn(ids=[p.id for p in ps]), None, s)
    assert res["cible"] == ps[0].id and res["conflits"] == [] and res["n_parcelles"] == 0
    assert all(s.get(models.Projet, p.id).statut == "archive" for p in ps[1:])


@pytest.mark.db
def test_fusion_refuse_moins_de_deux(db_session):
    s = db_session
    p = _projet(s, "Solo")
    with pytest.raises(Exception):
        projets.projets_fusionner(projets.FusionIn(ids=[p.id]), None, s)


@pytest.mark.db
def test_rejeu_non_perte_retenue_hors_criteres(db_session, monkeypatch):
    s = db_session
    pin = _parcelle(s, "97499000ZC0003")   # retenue qui RESTE dans les critères
    pout = _parcelle(s, "97499000ZD0004")  # retenue qui SORT des critères → reste, marquée hors_criteres
    P = _projet(s, "Rejeu")
    _pp(s, P.id, pin, "retenue"); _pp(s, P.id, pout, "retenue")

    # le rejeu ne propose QUE pin (pout n'est plus dans les critères du jour)
    monkeypatch.setattr(projets, "_search_items", lambda *a, **k: [{"idu": "97499000ZC0003"}])
    projets.projet_proposer(P.id, projets.ProposerIn(limit=24), None, s)

    rows = {r.parcel_id: (r.statut, r.hors_criteres) for r in s.execute(text(
        "SELECT parcel_id, statut, hors_criteres FROM projet_parcelles WHERE projet_id=:p"), {"p": P.id})}
    # AUCUNE retenue évincée : les deux restent 'retenue'
    assert rows[pin][0] == "retenue" and rows[pout][0] == "retenue"
    # celle sortie des critères est marquée hors_criteres ; celle qui rematche ne l'est pas
    assert rows[pout][1] is True and rows[pin][1] is False
