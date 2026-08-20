"""M34 (dette #14) — le verdict de fiche est une TRADUCTION du tier servi.

Verrous :
- servable → statut = tier, label client, jamais un déclassement silencieux ;
- bâtie marginale DIVISIBLE servie (étage 3) → badge « bâtie — emprise marginale » ;
- déclassée bâti saturé → verdict de déclassement + motif du filtre (rien n'est remonté) ;
- exception du registre servi → son motif prime ;
- parcelle hors run → « non évaluée au run servi », JAMAIS un repli legacy muet ;
- sql_exists_servable ne retient que les tiers actifs du run servi.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.scoring.score_v_constants import Q_A_RUN_LABEL
from labuse.verdict_servi import (
    BADGE_DIVISION,
    TIERS_SERVABLES,
    sql_exists_servable,
    verdict_servi,
    verdict_servi_batch,
)

pytestmark = pytest.mark.db

_WKT = ("POLYGON((55.46 -20.90, 55.461 -20.90, 55.461 -20.901, "
        "55.46 -20.901, 55.46 -20.90))")


def _parcel(session, idu: str) -> int:
    return session.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, "
        "                     centroid, bbox) "
        "VALUES (:i, 'Testville', 'VS', '1', ST_GeomFromText(:w, 4326), "
        "        ST_Transform(ST_GeomFromText(:w, 4326), 2975), 800, "
        "        ST_Centroid(ST_GeomFromText(:w, 4326)), ST_Envelope(ST_GeomFromText(:w, 4326))) "
        "RETURNING id"), {"i": idu, "w": _WKT}).scalar()


def _score(session, idu: str, tier: str, rang: int) -> None:
    session.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, rang, "
        "contrib_z, contrib_d, copro, tier, model_version) "
        "VALUES (:r, :i, 0.5, 1.0, 50, :rg, 0, 0, false, :t, 'm34-test')"),
        {"r": Q_A_RUN_LABEL, "i": idu, "rg": rang, "t": tier})


def _ensure_caches(session) -> None:
    """Les deux caches lus par la traduction sont créés par des gestes (builder filtre bâti,
    bascule) — absents de la base de test : on pose le MÊME schéma que la prod."""
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS parcel_filtre_bati (
          parcel_id integer PRIMARY KEY REFERENCES parcels(id),
          idu varchar(14) NOT NULL,
          ratio_pct double precision NOT NULL,
          emprise_max_m2 double precision NOT NULL,
          etage smallint NOT NULL,
          annee_construction int,
          annee_etiquette varchar(8) NOT NULL,
          passoire boolean NOT NULL DEFAULT false,
          divisible boolean,
          decision varchar(12) NOT NULL,
          motif text NOT NULL,
          computed_at timestamptz NOT NULL DEFAULT now())"""))
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS served_run_exceptions (
          run_id varchar(48) NOT NULL,
          idu varchar(20) NOT NULL,
          tier_origine varchar(40),
          tier_servi varchar(40),
          motif text,
          created_at timestamptz DEFAULT now(),
          PRIMARY KEY (run_id, idu))"""))
    session.execute(text(
        "ALTER TABLE served_run_exceptions ADD COLUMN IF NOT EXISTS motif_client text"))


def _seed(session) -> dict[str, int]:
    _ensure_caches(session)
    ids = {}
    cas = [
        ("97499000VS0001", "brulante", 3),            # nue servie
        ("97499000VS0002", "chaude", 120),            # bâtie divisible servie (badge)
        ("97499000VS0003", "declasse_bati_sature", None),
        ("97499000VS0004", "a_creuser", 5000),        # exception registre (piscine)
        ("97499000VS0005", "reserve_fonciere", 2000),
        ("97499000VS0006", "ecartee", None),
    ]
    for idu, tier, rang in cas:
        ids[idu] = _parcel(session, idu)
        _score(session, idu, tier, rang or 400000)
    # filtre bâti : VS0002 divisible (étage 3), VS0003 saturée avec motif
    session.execute(text(
        "INSERT INTO parcel_filtre_bati (parcel_id, idu, ratio_pct, emprise_max_m2, etage, "
        "annee_etiquette, passoire, divisible, decision, motif) VALUES "
        "(:p2, '97499000VS0002', 22.4, 180, 3, 'Absente', false, true, 'divisible', "
        " 'bâtie 15-40 %, divisible (libre 610 m², zone U)'), "
        "(:p3, '97499000VS0003', 55.0, 440, 1, 'Absente', false, false, 'saturee', "
        " 'bâtie saturée — ratio 55 %')"),
        {"p2": ids["97499000VS0002"], "p3": ids["97499000VS0003"]})
    # M35 Lot B : motif INTERNE volontairement « sale » (mandat/dette/prénom/score de modèle)
    # + motif CLIENT propre — le verrou vérifie que seul le client sort.
    session.execute(text(
        "INSERT INTO served_run_exceptions (run_id, idu, tier_origine, tier_servi, motif, motif_client) "
        "VALUES (:r, '97499000VS0004', 'chaude', 'a_creuser', "
        "        'M99 (Vic) : piscine FLAIR 0,9 — dette #13, comme ZZ0000', "
        "        'Piscine détectée sur imagerie aérienne — usage du terrain à vérifier.')"),
        {"r": Q_A_RUN_LABEL})
    # VS0005 : exception SANS motif client → repli neutre attendu, jamais le motif interne.
    session.execute(text(
        "INSERT INTO served_run_exceptions (run_id, idu, tier_origine, tier_servi, motif) "
        "VALUES (:r, '97499000VS0005', 'chaude', 'reserve_fonciere', "
        "        'M98 interne : FLAIR 0,7 — dette #42')"),
        {"r": Q_A_RUN_LABEL})
    session.flush()
    return ids


def test_servable_traduit_le_tier(db_session):
    _seed(db_session)
    v = verdict_servi(db_session, "97499000VS0001")
    assert v["statut"] == "brulante" and v["label"] == "À contacter en priorité"
    assert v["servable"] is True and v["declasse"] is False
    assert v["rang"] == 3 and v["motif"] is None and v["badge_division"] is False


def test_divisible_servie_porte_le_badge_division(db_session):
    _seed(db_session)
    v = verdict_servi(db_session, "97499000VS0002")
    assert v["statut"] == "chaude"                      # le tier N'EST PAS déclassé
    assert v["badge_division"] is True
    assert BADGE_DIVISION in v["badge_division_libelle"]
    assert "22" in v["badge_division_libelle"]          # ratio affiché (source M28)


def test_declassee_reste_declassee_avec_motif(db_session):
    _seed(db_session)
    v = verdict_servi(db_session, "97499000VS0003")
    assert v["statut"] == "declasse_bati_sature"
    assert v["label"] == "Peu de potentiel"
    assert v["servable"] is False and v["declasse"] is True
    assert "saturée" in v["motif"]                      # motif du filtre, jamais remonté


def test_exception_registre_motif_client_seul(db_session):
    # M35 Lot B : le motif servi est le motif CLIENT — la machinerie interne (mandat, dette,
    # prénom, score de modèle, IDU tiers) ne sort JAMAIS.
    _seed(db_session)
    v = verdict_servi(db_session, "97499000VS0004")
    assert v["statut"] == "a_creuser" and v["exception_registre"] is True
    assert v["motif"] == "Piscine détectée sur imagerie aérienne — usage du terrain à vérifier."
    for interdit in ("M99", "Vic", "FLAIR", "dette", "ZZ0000"):
        assert interdit not in v["motif"]


def test_exception_sans_motif_client_repli_neutre(db_session):
    from labuse.verdict_servi import MOTIF_CLIENT_FALLBACK
    _seed(db_session)
    v = verdict_servi(db_session, "97499000VS0005")
    assert v["exception_registre"] is True
    assert v["motif"] == MOTIF_CLIENT_FALLBACK
    for interdit in ("M98", "FLAIR", "dette"):
        assert interdit not in v["motif"]


def test_hors_run_dit_non_evaluee_jamais_legacy(db_session):
    _seed(db_session)
    v = verdict_servi(db_session, "97499000VS9999")
    assert v["statut"] == "non_evaluee"
    assert v["label"] == "Non évaluée au run servi"
    assert v["servable"] is False and v["tier"] is None


def test_batch_rend_toutes_les_cles(db_session):
    _seed(db_session)
    idus = ["97499000VS0001", "97499000VS0006", "97499000VS9999"]
    out = verdict_servi_batch(db_session, idus)
    assert set(out) == set(idus)
    assert out["97499000VS0006"]["statut"] == "ecartee"
    assert out["97499000VS9999"]["statut"] == "non_evaluee"


def test_sql_exists_servable_ne_retient_que_les_tiers_actifs(db_session):
    _seed(db_session)
    rows = db_session.execute(text(
        f"SELECT p.idu FROM parcels p WHERE p.idu LIKE '97499000VS%' "
        f"AND {sql_exists_servable('p')} ORDER BY p.idu"),
        {"vs_run": Q_A_RUN_LABEL}).scalars().all()
    assert rows == ["97499000VS0001", "97499000VS0002", "97499000VS0004", "97499000VS0005"]
    # ni la déclassée (VS0003), ni l'écartée (VS0006)
    assert set(TIERS_SERVABLES) == {"brulante", "chaude", "reserve_fonciere", "a_creuser"}
