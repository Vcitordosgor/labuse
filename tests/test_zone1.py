"""ZONE-1 — gardes du mandat : UNE résolution de zone PLU + garde de lecture du résiduel.

Les quatre témoins de l'audit EXPORTS (docs/audit-2026-09/EXPORTS/DONNEES-RAPPORT.md,
chapitre A3/transverse) sont REPRODUITS en fixtures : mêmes IDU, mêmes configurations de
zonage (T1 mono-zone U1a Saint-Paul ; T2 Ud3 dominante ~93 % Les Avirons ; T3 à cheval
N 54 %/Ud 46 % Saint-Pierre — dominante N ; T4 à cheval Uh 57 %/N 43 % Saint-Denis —
dominante Uh), géométries synthétiques compactes. Sur la base réelle, T4 est une lanière
(recul 4 m → contour inseté vidé, verdict géométrique légitime) : la fixture compacte
prouve que la capacité se calcule bien sur la portion constructible quand la géométrie
le permet.

Verrouille :
  1. écran (`parcel_zone_plu`) et faisabilité (`parcel_context`) donnent LA MÊME zone —
     plus jamais la zone du centroïde ;
  2. T3 (dominante N) : 0 logement, et la SDP résiduelle stockée (4 188) est servie 0
     PAR RÈGLE avec la cause `zone_non_constructible:N` (garde de lecture, run intact) ;
  3. T4 : drapeau `a_cheval` + parts ~57/43, capacité calculée sur la seule portion
     constructible, et le bilan le dit (libellé dans la modulation).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

T1, T2, T3, T4 = "97415000BO0852", "97401000AD0554", "97416000DY0106", "97411000AV0110"
RUN = "test_zone1"


def _sq(x, y, d):
    return f"POLYGON(({x} {y}, {x + d} {y}, {x + d} {y + d}, {x} {y + d}, {x} {y}))"


def _rect(x0, y0, x1, y1):
    return f"POLYGON(({x0} {y0}, {x1} {y0}, {x1} {y1}, {x0} {y1}, {x0} {y0}))"


def _parcel(db, idu, commune, wkt2975):
    db.execute(text(
        "INSERT INTO parcels (idu, commune, surface_m2, geom) VALUES (:i, :c, "
        " ST_Area(ST_SetSRID(ST_GeomFromText(:w), 2975)),"
        " ST_Transform(ST_SetSRID(ST_GeomFromText(:w), 2975), 4326))"
        " ON CONFLICT (idu) DO NOTHING"), {"i": idu, "c": commune, "w": wkt2975})
    db.execute(text("UPDATE parcels SET centroid = ST_Centroid(geom) WHERE idu = :i"), {"i": idu})


def _zone(db, commune, libelle, subtype, wkt2975):
    db.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, commune, attrs, geom) VALUES "
        "('plu_gpu_zone', :st, :lib, :c, jsonb_build_object('libelle', CAST(:lib2 AS text)), "
        " ST_Transform(ST_SetSRID(ST_GeomFromText(:w), 2975), 4326))"),
        {"st": subtype, "lib": libelle, "lib2": libelle, "c": commune, "w": wkt2975})


@pytest.fixture()
def zone1_env(db_session):
    s = db_session
    s.execute(text(
        "CREATE TABLE IF NOT EXISTS parcel_zone_plu ("
        " idu varchar(14) PRIMARY KEY, zone_lib varchar(40), zone_fam varchar(8),"
        " zone_libelle text, zone_filtre varchar(40))"))
    s.execute(text("DELETE FROM spatial_layers WHERE kind = 'plu_gpu_zone'"))
    s.execute(text("DELETE FROM parcel_zone_plu WHERE idu = ANY(:i)"), {"i": [T1, T2, T3, T4]})

    # T1 — Saint-Paul, mono-zone U1a (26 m → 676 m²)
    _parcel(s, T1, "Saint-Paul", _sq(340000, 7650000, 26))
    _zone(s, "Saint-Paul", "U1a", "U", _sq(339900, 7649900, 300))

    # T2 — Les Avirons, Ud3 dominante ~92.7 % + N 7.3 % (pas à cheval : ≥ 90 %)
    _parcel(s, T2, "Les Avirons", _sq(342000, 7650000, 30))
    _zone(s, "Les Avirons", "Ud3", "U", _rect(341900, 7649900, 342000 + 27.8, 7650200))
    _zone(s, "Les Avirons", "N", "N", _rect(342000 + 27.8, 7649900, 342300, 7650200))

    # T3 — Saint-Pierre, à cheval N 54.4 % (dominante) + Ud 45.6 %
    _parcel(s, T3, "Saint-Pierre", _sq(344000, 7650000, 30))
    _zone(s, "Saint-Pierre", "N", "N", _rect(343900, 7649900, 344000 + 16.32, 7650200))
    _zone(s, "Saint-Pierre", "Ud", "U", _rect(344000 + 16.32, 7649900, 344300, 7650200))

    # T4 — Saint-Denis, à cheval Uh 57.4 % (dominante) + N 42.6 %, COMPACTE (26 m)
    _parcel(s, T4, "Saint-Denis", _sq(346000, 7650000, 26))
    _zone(s, "Saint-Denis", "Uh", "U", _rect(345900, 7649900, 346000 + 14.92, 7650200))
    _zone(s, "Saint-Denis", "N", "N", _rect(346000 + 14.92, 7649900, 346300, 7650200))

    # L'écran : dominantes par surface (ce que build_parcel_zone_plu matérialiserait)
    for idu, lib, fam in ((T1, "U1a", "U"), (T2, "Ud3", "U"), (T3, "N", "N"), (T4, "Uh", "U")):
        s.execute(text(
            "INSERT INTO parcel_zone_plu (idu, zone_lib, zone_fam) VALUES (:i, :l, :f)"),
            {"i": idu, "l": lib, "f": fam})

    # T3 : le run a stocké une SDP résiduelle 4 188 m² (l'anomalie mesurée à l'audit)
    pid3 = s.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": T3}).scalar()
    s.execute(text("DELETE FROM parcel_residuel WHERE parcel_id = :p"), {"p": pid3})
    s.execute(text(
        "INSERT INTO parcel_residuel (parcel_id, sdp_residuelle_m2) VALUES (:p, 4188)"),
        {"p": pid3})
    s.execute(text("DELETE FROM dryrun_cascade_results WHERE run_label = :r"), {"r": RUN})
    s.execute(text(
        "INSERT INTO dryrun_cascade_results (run_label, parcel_id, layer_name, result, "
        " severity, weight_applied, detail) VALUES "
        "(:r, :p, 'residuel_socle', 'POSITIVE', 'INFO', 12, "
        " 'SDP résiduelle 4188 m² — belle opération.')"), {"r": RUN, "p": pid3})
    s.flush()
    return s


def _pid(s, idu):
    return s.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()


@pytest.mark.db
def test_zone_ecran_egale_faisabilite(zone1_env):
    """Point 1 — plus jamais deux vérités : la faisabilité lit LA zone de l'écran."""
    from labuse.faisabilite.db import parcel_context
    s = zone1_env
    for idu, attendu in ((T1, "U1a"), (T2, "Ud3"), (T3, "N"), (T4, "Uh")):
        ecran = s.execute(text(
            "SELECT zone_lib FROM parcel_zone_plu WHERE idu = :i"), {"i": idu}).scalar()
        ctx = parcel_context(s, _pid(s, idu))
        assert ctx is not None
        assert ecran == attendu
        assert ctx.zone == ecran, f"{idu} : faisabilité {ctx.zone!r} ≠ écran {ecran!r}"
    # T1/T2 ne sont PAS à cheval (mono-zone / dominante ≥ 90 %)
    assert parcel_context(s, _pid(s, T1)).a_cheval is False
    assert parcel_context(s, _pid(s, T2)).a_cheval is False


@pytest.mark.db
def test_t3_dominante_n_zero_logement_et_cause(zone1_env):
    """Point 2 — T3 : 0 logement, SDP stockée 4 188 servie 0 PAR RÈGLE, cause affichée,
    run INTACT."""
    from labuse.api.served_cascade import served_cascade_lines
    from labuse.faisabilite.db import parcel_faisabilite
    from labuse.faisabilite.zone_servie import garde_sdp_residuelle
    s = zone1_env
    fz = parcel_faisabilite(s, _pid(s, T3))
    assert fz is None or not fz[1].constructible, "zone dominante N : jamais constructible"
    if fz:
        assert fz[1].fourchette in (None, {}) or \
            (fz[1].fourchette.get("logements_au_sol") or (0, 0))[1] == 0
    # garde pure
    assert garde_sdp_residuelle(4188, "N", "N") == (0.0, "zone_non_constructible:N")
    assert garde_sdp_residuelle(4188, "U", "Ud") == (4188.0, None)
    assert garde_sdp_residuelle(None, "N", "N") == (None, None)
    # garde à la lecture des lignes servies (écran ET exports lisent ce point unique)
    lignes = served_cascade_lines(s, T3, run=RUN)
    socle = [l for l in lignes if l["layer_name"] == "residuel_socle"]
    assert socle, "la ligne residuel_socle doit rester servie (cause affichée, pas masquée)"
    assert "0 m²" in socle[0]["detail"]
    assert "zone_non_constructible:N" in socle[0]["detail"]
    assert socle[0]["result"] == "SOFT_FLAG"
    # le run n'est PAS réécrit
    brut = s.execute(text(
        "SELECT detail FROM dryrun_cascade_results WHERE run_label = :r"), {"r": RUN}).scalar()
    assert "4188" in brut


@pytest.mark.db
def test_t4_a_cheval_capacite_portion_constructible(zone1_env):
    """Point 1 — T4 : dominante Uh, drapeau + parts ~57/43, capacité sur la portion
    constructible, et le bilan le dit."""
    from labuse.faisabilite.db import parcel_faisabilite
    s = zone1_env
    fz = parcel_faisabilite(s, _pid(s, T4))
    assert fz is not None
    ctx, f = fz
    assert ctx.zone == "Uh" and ctx.zone_fam == "U"
    assert ctx.a_cheval is True
    parts = {p["zone"]: p["pct"] for p in ctx.zone_parts}
    assert abs(parts["Uh"] - 57.4) < 2.0 and abs(parts["N"] - 42.6) < 2.0
    # capacité CALCULÉE, sur la seule portion constructible (l'emprise clippée U/AU est
    # STRICTEMENT plus petite que l'inset plein — la portion N ne construit rien)
    assert f.constructible, "dominante Uh compacte : la capacité doit exister"
    assert (f.fourchette or {}).get("shab_vendable_m2", 0) > 0
    # le bilan le dit : libellé à cheval AVec les parts, servi dans la modulation
    a_cheval = [m for m in (list(f.modulation or []) + list(ctx.contraintes.libelles))
                if "à cheval" in m]
    assert a_cheval and "Uh" in a_cheval[0] and "57" in a_cheval[0]
    clip = [m for m in (list(f.modulation or []) + list(ctx.contraintes.libelles))
            if "Zonage mixte" in m]
    assert clip, "l'emprise doit être clippée à la portion U/AU (Décision 1)"
