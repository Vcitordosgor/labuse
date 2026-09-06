"""OUTILS-MUSCLER-1 — gardes des deux nouveaux endpoints.

Lot A : /modules/successions (tag radar patrimonial parcel_veille_succession servi en outil —
succession PROBABLE, jamais « en succession », aucun tier/score servi).
Lot B : /moteurs/assemblage/voisines (1ᵉʳ anneau contigu proposé ; « même propriétaire » =
égalité de SIREN, jamais un match par nom ; départ particulier → indécidable, dit).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db


def _p(db, idu, wkt, surf, commune="Succville"):
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox, geom_2975) VALUES "
        "(:i,:c,'S','1', ST_GeomFromText(:w,4326), :s, ST_Centroid(ST_GeomFromText(:w,4326)), "
        " ST_Envelope(ST_GeomFromText(:w,4326)), ST_Transform(ST_GeomFromText(:w,4326),2975)) RETURNING id"),
        {"i": idu, "c": commune, "w": wkt, "s": surf}).scalar()


def _pm(db, idu, denomination, siren):
    db.execute(text("INSERT INTO parcelle_personne_morale (idu, denomination, siren) "
                    "VALUES (:i, :d, :s) ON CONFLICT (idu) DO UPDATE SET denomination = :d, siren = :s"),
                {"i": idu, "d": denomination, "s": siren})


def _veille(db, idu, siren, age=None, sci=False):
    db.execute(text("INSERT INTO parcel_veille_succession (parcelle_id, siren, dirigeant_age, sci_dormante) "
                    "VALUES (:i, :s, :a, :sci) ON CONFLICT (parcelle_id) DO NOTHING"),
                {"i": idu, "s": siren, "a": age, "sci": sci})


_SQ = "POLYGON((55.80 -21.40,55.8003 -21.40,55.8003 -21.3997,55.80 -21.3997,55.80 -21.40))"


def test_successions_liste(db_session):
    """La liste sert le signal avec propriétaire PM NOMMÉ, motif réel (âge / SCI dormante),
    millésime du calcul — et JAMAIS un tier/score (l'analyse n'a pas été demandée)."""
    from labuse.api.modules import successions_liste
    _p(db_session, "SUCC0001", _SQ, 600)
    _p(db_session, "SUCC0002",
       "POLYGON((55.81 -21.41,55.8103 -21.41,55.8103 -21.4097,55.81 -21.4097,55.81 -21.41))", 900)
    _pm(db_session, "SUCC0001", "SCI DU TEST", "111222333")
    _pm(db_session, "SUCC0002", "FONCIERE TEST", "444555666")
    _veille(db_session, "SUCC0001", "111222333", sci=True)
    _veille(db_session, "SUCC0002", "444555666", age=82)
    out = successions_liste(commune="Succville", sdp_min=0, limit=200, offset=0, db=db_session)
    assert out["total"] == 2 and out["n"] == 2
    assert out["maj"] is not None                     # millésime du signal — toujours servi
    par_idu = {i["idu"]: i for i in out["items"]}
    assert par_idu["SUCC0001"]["sci_dormante"] is True
    assert par_idu["SUCC0002"]["dirigeant_age"] == 82
    for it in out["items"]:
        assert it["proprio"]["type"] == "personne_morale" and it["proprio"]["denomination"]
        assert "tier_v2" not in it and "etage0" not in it   # aucun badge de score sur cet écran
        assert "sdp_residuelle_m2" in it                    # Estimé — peut être None (hors PLU / store absent)
    # doctrine A0 : l'avertissement dit « probable », jamais une succession ouverte.
    assert "probable" in out["avertissement"].lower()


def test_successions_commune_vide_honnete(db_session):
    """Commune sans signal : 0 ligne MAIS le millésime voyage (l'état vide honnête le cite)."""
    from labuse.api.modules import successions_liste
    _p(db_session, "SUCC0010", _SQ.replace("55.80", "55.82").replace("55.8003", "55.8203"), 500)
    _veille(db_session, "SUCC0010", "777888999", age=75)
    out = successions_liste(commune="Nulleville", sdp_min=0, limit=200, offset=0, db=db_session)
    assert out["total"] == 0 and out["items"] == []
    assert out["maj"] is not None


def test_successions_sdp_min_exclut_les_inconnues(db_session):
    """Un seuil de résiduel demandé : une SDP inconnue ne peut pas le prouver → exclue (0 fabriqué
    nulle part). Sur une base sans feature store, le seuil ne rend RIEN plutôt qu'un mensonge."""
    from labuse.api.modules import successions_liste
    _p(db_session, "SUCC0020",
       "POLYGON((55.83 -21.43,55.8303 -21.43,55.8303 -21.4297,55.83 -21.4297,55.83 -21.43))", 700)
    _veille(db_session, "SUCC0020", "121212121", age=71)
    has_ext = bool(db_session.execute(text(
        "SELECT to_regclass('p_model_ext_dataset') IS NOT NULL")).scalar())
    out = successions_liste(commune="Succville", sdp_min=100000, limit=200, offset=0, db=db_session)
    if not has_ext:
        assert out["total"] == 0     # pas de store → aucune SDP prouvable au seuil
    else:
        assert all((i["sdp_residuelle_m2"] or 0) >= 100000 for i in out["items"])
