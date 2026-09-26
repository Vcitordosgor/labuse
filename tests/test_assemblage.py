"""Assemblage foncier v1 (Lot C5) — paires contiguës franchissant le seuil, sur PostGIS réel."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import assemblage

pytestmark = pytest.mark.db


def _p(db, idu, wkt, surf):
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox, geom_2975) VALUES "
        "(:i,'Asmville','S','1', ST_GeomFromText(:w,4326), :s, ST_Centroid(ST_GeomFromText(:w,4326)), "
        " ST_Envelope(ST_GeomFromText(:w,4326)), ST_Transform(ST_GeomFromText(:w,4326),2975)) RETURNING id"),
        {"i": idu, "w": wkt, "s": surf}).scalar()


def test_paire_contigue_franchit_le_seuil(db_session, monkeypatch):
    monkeypatch.setattr(assemblage, "_params", lambda: {"min_surface_m2": 1000.0, "individuel_max_m2": 1000.0})
    # deux carrés ADJACENTS de ~600 m² chacun (côte à côte) → cumul ~1200 ≥ 1000, chacun < 1000
    a = _p(db_session, "ASM00001", "POLYGON((55.40 -21.00,55.4003 -21.00,55.4003 -20.9997,55.40 -20.9997,55.40 -21.00))", 600)
    _p(db_session, "ASM00002", "POLYGON((55.4003 -21.00,55.4006 -21.00,55.4006 -20.9997,55.4003 -20.9997,55.4003 -21.00))", 600)
    groups = assemblage.find_assemblages(db_session, "Asmville")
    assert any(set(g["parcelles"]) == {"ASM00001", "ASM00002"} and g["surface_cumulee_m2"] >= 1000
               for g in groups)
    u = assemblage.parcel_assemblage(db_session, a)
    assert u["possible"] and u["meilleur_cumul_m2"] >= 1000


def test_parcelle_seule_au_dessus_du_seuil_pas_d_assemblage(db_session, monkeypatch):
    monkeypatch.setattr(assemblage, "_params", lambda: {"min_surface_m2": 1000.0, "individuel_max_m2": 1000.0})
    big = _p(db_session, "ASM00010", "POLYGON((55.50 -21.10,55.5005 -21.10,55.5005 -21.0995,55.50 -21.0995,55.50 -21.10))", 1500)
    u = assemblage.parcel_assemblage(db_session, big)
    assert u["possible"] is False   # déjà au-dessus du seuil seule → pas besoin d'assemblage


def test_parcelles_non_contigues_pas_de_paire(db_session, monkeypatch):
    monkeypatch.setattr(assemblage, "_params", lambda: {"min_surface_m2": 1000.0, "individuel_max_m2": 1000.0})
    _p(db_session, "ASM00020", "POLYGON((55.60 -21.20,55.6003 -21.20,55.6003 -21.1997,55.60 -21.1997,55.60 -21.20))", 600)
    _p(db_session, "ASM00021", "POLYGON((55.70 -21.30,55.7003 -21.30,55.7003 -21.2997,55.70 -21.2997,55.70 -21.30))", 600)
    groups = assemblage.find_assemblages(db_session, "Asmville")
    assert not any(set(g["parcelles"]) == {"ASM00020", "ASM00021"} for g in groups)


def test_endpoint_moteurs_assemblage_ne_leve_pas(db_session):
    """L'ENDPOINT scoré (/moteurs/assemblage) n'était couvert par AUCUN test. Il ne doit pas lever :
    422 si < 2 demandées, 404 si < 2 trouvées, et sur 2 parcelles contiguës il rend la structure —
    base de test SANS faisabilité servie → sans_potentiel, JAMAIS une exception. Les vestiges de
    matrice (opportunity_score / sdp_cumulee_m2 / statut / m2_par_logement) ont disparu du payload."""
    from fastapi import HTTPException

    from labuse.api.moteurs import AssemblageIn
    from labuse.api.moteurs import assemblage as endpoint
    with pytest.raises(HTTPException) as e1:
        endpoint(AssemblageIn(idus=["ASM00099"]), db=db_session)
    assert e1.value.status_code == 422
    with pytest.raises(HTTPException) as e2:
        endpoint(AssemblageIn(idus=["97499000ZZ9998", "97499000ZZ9999"]), db=db_session)
    assert e2.value.status_code == 404
    _p(db_session, "ASM00050", "POLYGON((55.40 -21.00,55.4003 -21.00,55.4003 -20.9997,55.40 -20.9997,55.40 -21.00))", 600)
    _p(db_session, "ASM00051", "POLYGON((55.4003 -21.00,55.4006 -21.00,55.4006 -20.9997,55.4003 -20.9997,55.4003 -21.00))", 600)
    out = endpoint(AssemblageIn(idus=["ASM00050", "ASM00051"]), db=db_session)   # ne lève pas
    assert out["n"] == 2 and out["contigu"] is True
    assert out["sans_potentiel"] is True and out["score_assemblage"] == 0   # aucune faisabilité servie
    # ASSEMBLAGE-2 (RETOUCHES-1 lot B.4) — la note dit désormais que le calcul est sur l'UNION
    # (une assiette, une VRD) ; sans zonage en base de test, la capacité d'union est « aucune ».
    assert "UNION" in out["note_sdp"] and out["ca"] is None and out["charge_fonciere"] is None
    # vestiges retirés (payload + items)
    for k in ("opportunity_score", "sdp_cumulee_m2", "m2_par_logement"):
        assert k not in out
    for it in out["items"]:
        assert "sdp_m2" in it and "tier_v2" in it
        assert "opportunity_score" not in it and "statut" not in it and "sdp_residuelle_m2" not in it


# ── ASSEMBLAGE-2 (RETOUCHES-1 lot B.4) — l'assiette est l'UNION des géométries, pas la somme ──

def test_aggregate_assiette_calcule_sur_l_union(db_session):
    """Sur un trio de parcelles CONTIGUËS CONSTRUCTIBLES (données réelles), la capacité de
    l'assemblage est calculée sur l'UNION (une assiette, une VRD), pas par somme des résiduels :
    les reculs internes disparaissent → la SDP de l'union est SUPÉRIEURE à la somme par parcelle,
    et la charge foncière est UNE seule (dict unique par_m2_terrain), jamais N VRD additionnées."""
    from types import SimpleNamespace

    # trio mutuellement contigu parmi les parcelles à capacité résiduelle > 0 (contour cadastral).
    cand = db_session.execute(text(
        "SELECT p.id, p.surface_m2, p.idu, p.commune FROM parcels p "
        "JOIN parcel_residuel r ON r.parcel_id = p.id "
        "WHERE r.sdp_residuelle_m2 > 50 AND p.surface_m2 BETWEEN 200 AND 1200 LIMIT 5000")).mappings().all()
    if len(cand) < 3:
        pytest.skip("pas de parcelles à capacité résiduelle en base (run résiduel absent)")
    byid = {c["id"]: c for c in cand}
    ids = list(byid)
    adj: dict[int, set[int]] = {i: set() for i in ids}
    for a, b in db_session.execute(text(
            "SELECT a.id a, b.id b FROM parcels a JOIN parcels b "
            "ON a.id < b.id AND ST_DWithin(a.geom_2975, b.geom_2975, 0.5) "
            "WHERE a.id = ANY(:i) AND b.id = ANY(:i)"), {"i": ids}).all():
        adj[a].add(b)
        adj[b].add(a)
    trio = next(([a, b, next(iter(adj[a] & adj[b]))] for a in ids for b in adj[a] if adj[a] & adj[b]), None)
    if trio is None:
        pytest.skip("aucun trio contigu constructible en base")
    ps = [SimpleNamespace(id=byid[i]["id"], surface_m2=byid[i]["surface_m2"],
                          idu=byid[i]["idu"], commune=byid[i]["commune"]) for i in trio]
    agg = assemblage.aggregate_assiette(db_session, ps)
    assert agg["assiette"] == "union"
    assert agg["emprise_union_m2"] and agg["emprise_union_m2"] > 0
    # SDP de l'union ≥ somme des résiduels par parcelle (reculs internes supprimés à la fusion).
    somme = sum(agg["sdp_par_parcelle"].values())
    assert agg["sdp_m2"] >= somme, (agg["sdp_m2"], somme)
    # charge foncière = UN dict (par_m2_terrain), jamais une somme de N bilans.
    cf = agg["charge_fonciere"]
    assert cf is None or ("par_m2_terrain" in cf and set(cf) >= {"bas", "central", "haut"})
