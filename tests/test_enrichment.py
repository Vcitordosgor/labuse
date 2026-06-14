"""Tests de l'enrichissement « fiche promoteur » (TEMPS 1).

On verrouille la partie SUBTILE : la dégradation façade/profondeur (terrain régulier
→ profondeur ; forme irrégulière → non significative) et le mode hors-ligne
(aucun appel externe, dégradation propre). Géométries posées en EPSG:2975 (mètres)
puis reprojetées en 4326 pour le stockage → mesures exactes et déterministes.
"""
from __future__ import annotations

from sqlalchemy import text

from labuse.api import enrichment as E

# Parcelle de test ancrée dans la zone valide RGR92 UTM 40S (La Réunion).
X0, Y0 = 340000.0, 7660000.0


def _insert_parcel_2975(db, idu: str, wkt_2975: str) -> int:
    """Insère une parcelle définie en mètres (2975) → geom stocké en 4326, trigger → geom_2975."""
    pid = db.execute(
        text(
            "INSERT INTO parcels (idu, commune, geom, surface_m2, centroid) VALUES ("
            "  :idu, 'Test',"
            "  ST_Transform(ST_SetSRID(ST_GeomFromText(:w), 2975), 4326),"
            "  ST_Area(ST_SetSRID(ST_GeomFromText(:w), 2975)),"
            "  ST_Transform(ST_Centroid(ST_SetSRID(ST_GeomFromText(:w), 2975)), 4326)"
            ") RETURNING id"
        ), {"idu": idu, "w": wkt_2975},
    ).scalar()
    return int(pid)


def _insert_voirie_2975(db, wkt_2975: str) -> None:
    db.execute(
        text(
            "INSERT INTO spatial_layers (kind, geom) VALUES "
            "('voirie', ST_Transform(ST_SetSRID(ST_GeomFromText(:w), 2975), 4326))"
        ), {"w": wkt_2975},
    )


def test_facade_et_profondeur_terrain_regulier(db_session):
    """Lot rectangulaire 25 m (rue) × 20 m → façade ≈ 25 m, profondeur ≈ 20 m."""
    x, y = X0, Y0
    rect = (f"POLYGON(({x} {y},{x+25} {y},{x+25} {y+20},{x} {y+20},{x} {y}))")
    pid = _insert_parcel_2975(db_session, "TEST00000000R1", rect)
    # voie parallèle à la façade basse, 3 m en dessous (dans la tolérance de 6 m)
    _insert_voirie_2975(db_session, f"LINESTRING({x-5} {y-3},{x+30} {y-3})")

    f = E.facade_depth(db_session, pid)
    assert f["sur_rue"] is True
    assert 23.0 <= f["facade_principale_m"] <= 27.0          # ≈ 25 m
    assert f["profondeur_m"] is not None
    assert 18.0 <= f["profondeur_m"] <= 22.0                 # ≈ 20 m
    assert "régulier" in f["profondeur_note"]
    assert f["forme"]["rectangularite"] >= E.RECT_MIN


def test_profondeur_degradee_forme_irreguliere(db_session):
    """Parcelle en croix (non rectangulaire, non convexe) → profondeur non significative."""
    x, y = X0, Y0
    cross = (
        f"POLYGON(({x+10} {y},{x+20} {y},{x+20} {y+10},{x+30} {y+10},{x+30} {y+20},"
        f"{x+20} {y+20},{x+20} {y+30},{x+10} {y+30},{x+10} {y+20},{x} {y+20},"
        f"{x} {y+10},{x+10} {y+10},{x+10} {y}))"
    )
    pid = _insert_parcel_2975(db_session, "TEST00000000R2", cross)
    _insert_voirie_2975(db_session, f"LINESTRING({x+5} {y-3},{x+25} {y-3})")

    f = E.facade_depth(db_session, pid)
    assert f["profondeur_m"] is None
    assert "irrégulière" in f["profondeur_note"]


def test_facade_absente_coeur_dilot(db_session):
    """Parcelle sans voie à proximité → pas de façade, profondeur non calculée."""
    x, y = X0 + 5000, Y0 + 5000   # loin de toute voirie
    rect = f"POLYGON(({x} {y},{x+25} {y},{x+25} {y+20},{x} {y+20},{x} {y}))"
    pid = _insert_parcel_2975(db_session, "TEST00000000R3", rect)

    f = E.facade_depth(db_session, pid)
    assert f["sur_rue"] is False
    assert f["profondeur_m"] is None
    assert "Aucune façade" in f["profondeur_note"]


def test_altimetrie_hors_ligne_degrade_proprement(db_session, monkeypatch):
    """Mode hors-ligne : aucun appel réseau, dégradation explicite (jamais d'exception)."""
    monkeypatch.setenv("LABUSE_ENRICH_LIVE", "0")
    x, y = X0, Y0
    rect = f"POLYGON(({x} {y},{x+25} {y},{x+25} {y+20},{x} {y+20},{x} {y}))"
    pid = _insert_parcel_2975(db_session, "TEST00000000R4", rect)

    a = E.altimetry(db_session, pid)
    assert a["available"] is False
    assert "RGE ALTI" in a["source"]


def test_reseaux_et_proprietaire_honnetes(db_session):
    """Aucune valeur fabriquée : réseaux → DT-DICT, propriétaire → non vérifié."""
    net = E.networks(db_session, 1)
    assert net["eau_potable"]["disponible_open_data"] is False
    assert "DT-DICT" in net["eau_potable"]["note"]
    own = E.owner(db_session, 1)
    assert own["categorie"] is None
    # 1.A : absente du fichier DGFiP des personnes morales → particulier → voie SPF, jamais de nom.
    assert "aucune donnée nominative" in own["note"].lower() and own["needs_spf"] is True


def test_proprietaire_categorie_affichee_si_disponible(db_session):
    """Si les Fichiers fonciers sont ingérés, on AFFICHE la catégorie (brief §5)."""
    import json
    x, y = X0, Y0
    pid = _insert_parcel_2975(db_session, "TEST00000000O1",
                              f"POLYGON(({x} {y},{x+20} {y},{x+20} {y+20},{x} {y+20},{x} {y}))")
    ff = "Fichiers fonciers (Cerema)"
    sid = db_session.execute(text("SELECT id FROM data_sources WHERE name=:n"), {"n": ff}).scalar()
    if not sid:
        sid = db_session.execute(
            text("INSERT INTO data_sources (name, status) VALUES (:n, 'a_faire') RETURNING id"), {"n": ff}
        ).scalar()
    db_session.execute(
        text("INSERT INTO parcel_source_results (parcel_id, data_source_id, status, raw_payload) "
             "VALUES (:p, :s, 'repondu', CAST(:raw AS jsonb))"),
        {"p": pid, "s": sid, "raw": json.dumps(
            {"personne_morale": True, "categorie": "Commune", "indivision": False})},
    )
    own = E.owner(db_session, pid)
    assert own["categorie"] == "publique" and own["personne_morale"] is True
    assert "publique" in own["note"].lower()
