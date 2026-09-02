"""RADAR S5 — rattachement à la validation (PROPOSITION, jamais d'idu auto), tolérance ±10 %, file
de re-vérif « à rattacher d'abord ».

Trois vérités gravées :
  (a) `valider()` calcule un rattachement_etat + rattachement_pistes SANS jamais poser d'idu
      (le lien reste un clic humain — doctrine intacte) ;
  (b) la tolérance de surface est ±10 % (une candidate à +8 % passe, alors qu'elle échouait à ±5 %) ;
  (c) la file de re-vérif rend les biens NON RATTACHÉS (idu NULL) en premier.

Base de test vide → on sème des parcelles [RADAR-TEST] + un bien/faits, on gèle, on nettoie.
Aucune requête réseau (le point est déjà porté par le bien, ou l'adresse est absente).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import intake, rattachement_html

pytestmark = pytest.mark.db

COMMUNE = "RadarS5Ville"
INSEE = "97498"
# carré ~ autour d'un point à La Réunion ; PT est à l'intérieur.
WKT = "POLYGON((55.40 -21.10,55.402 -21.10,55.402 -21.102,55.40 -21.102,55.40 -21.10))"
PT = (55.401, -21.101)


def _idu(tag: str) -> str:
    return f"{INSEE}0{tag}0001"[:14].ljust(14, "0")


@pytest.fixture
def seed(engine):
    """Une parcelle de 500 m² AVEC emprise bâtie (100 m²), dans la commune de test, contenant PT.
    Cela permet la convergence surface∩emprise → RATTACHÉE possible dans la cascade (mais jamais
    committée en idu par la validation)."""
    from labuse import communes
    tag = uuid.uuid4().hex[:4].upper()
    idu = _idu(tag)
    # rendre la commune résoluble par l'intake (résolution nom → officiel).
    ajoutee = COMMUNE not in communes._OFFICIAL_BY_NAME
    if ajoutee:
        communes._OFFICIAL_BY_NAME[COMMUNE] = INSEE
        intake._COMMUNE_PAR_NORME[intake._norm(COMMUNE)] = COMMUNE
    with session_scope() as s:
        s.execute(text(
            "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox)"
            " VALUES (:i,:c,'ZZ','1',ST_GeomFromText(:w,4326),ST_Transform(ST_GeomFromText(:w,4326),2975),"
            " 500, ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
            {"i": idu, "c": COMMUNE, "w": WKT})
        s.execute(text("INSERT INTO p_model_bati (idu, emprise_bati_m2) VALUES (:i, 100)"), {"i": idu})
    yield {"idu": idu}
    with session_scope() as s:
        s.execute(text("DELETE FROM p_model_bati WHERE idu = :i"), {"i": idu})
        s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
    if ajoutee:
        communes._OFFICIAL_BY_NAME.pop(COMMUNE, None)
        intake._COMMUNE_PAR_NORME.pop(intake._norm(COMMUNE), None)


def _creer_bien(db, *, lat=None, lng=None, surface_terrain=500.0, surface_hab=80.0,
                type_bien="maison") -> int:
    """Crée un brouillon (valide_at NULL) : bien + faits, comme un dépôt avant validation."""
    bid = db.execute(text(
        "INSERT INTO pige_biens (commune, type_bien, est_copro, statut, lat, lng) "
        "VALUES (:c, :t, false, 'active', :lat, :lng) RETURNING bien_id"),
        {"c": COMMUNE, "t": type_bien, "lat": lat, "lng": lng}).scalar()
    db.execute(text(
        "INSERT INTO pige_faits (bien_id, prix, type_bien, surface_hab, surface_terrain) "
        "VALUES (:b, 250000, :t, :sh, :st)"),
        {"b": bid, "t": type_bien, "sh": surface_hab, "st": surface_terrain})
    return bid


def _purge(db, bid: int) -> None:
    db.execute(text("DELETE FROM pige_prix_historique WHERE bien_id = :b"), {"b": bid})
    db.execute(text("DELETE FROM pige_faits WHERE bien_id = :b"), {"b": bid})
    db.execute(text("DELETE FROM pige_annonces WHERE bien_id = :b"), {"b": bid})
    db.execute(text("DELETE FROM pige_biens WHERE bien_id = :b"), {"b": bid})


# ── (a) validation pose une PROPOSITION, jamais d'idu ──────────────────────────────────────────────

def test_valider_propose_rattachement_sans_poser_idu(seed):
    """Le bien a une géoloc portail dans la parcelle → surface (500=500) ∩ emprise (bâti 100 pour 80 m²
    habitables) convergent → la cascade DIRAIT « rattachee », mais la VALIDATION n'écrit JAMAIS l'idu :
    seulement rattachement_etat + rattachement_pistes. Le lien reste un clic humain."""
    with session_scope() as db:
        bid = _creer_bien(db, lat=PT[1], lng=PT[0])
        db.commit()
    try:
        with session_scope() as db:
            intake.valider(db, bid, {})
        with session_scope() as db:
            row = db.execute(text(
                "SELECT idu, rattachement_etat, rattachement_humain, "
                "jsonb_array_length(rattachement_pistes) AS n_pistes "
                "FROM pige_biens WHERE bien_id = :b"), {"b": bid}).mappings().first()
        # DOCTRINE — jamais d'idu automatique.
        assert row["idu"] is None, "la validation ne doit JAMAIS committer un idu (clic humain requis)"
        assert row["rattachement_humain"] is False
        # une proposition a bien été écrite : la parcelle candidate figure dans les pistes.
        assert row["n_pistes"] >= 1, "la proposition doit lister au moins une piste (candidate)"
        # l'état reflète la cascade (ici la convergence surface∩emprise → rattachee proposée).
        assert row["rattachement_etat"] in ("rattachee", "piste")
        pistes = db_pistes(bid)
        assert any(p.get("idu") == seed["idu"] for p in pistes)
    finally:
        with session_scope() as db:
            _purge(db, bid)
            db.commit()


def test_valider_sans_coordonnee_reste_non_rattachee(seed):
    """Sans géoloc portail NI adresse exploitable, aucune position dérivable → la cascade rend
    honnêtement 'non_rattachee' (commune seule). Toujours pas d'idu."""
    with session_scope() as db:
        bid = _creer_bien(db, lat=None, lng=None)
        db.commit()
    try:
        with session_scope() as db:
            intake.valider(db, bid, {})
        with session_scope() as db:
            row = db.execute(text(
                "SELECT idu, rattachement_etat FROM pige_biens WHERE bien_id = :b"),
                {"b": bid}).mappings().first()
        assert row["idu"] is None
        assert row["rattachement_etat"] == "non_rattachee"
    finally:
        with session_scope() as db:
            _purge(db, bid)
            db.commit()


def test_validation_ne_casse_jamais_meme_si_rattachement_echoue(seed, monkeypatch):
    """Best-effort : un accident dans la proposition (ex. rattacher lève) ne casse pas la validation —
    le bien est promu (valide_at posé) quand même."""
    def _boom(*a, **k):
        raise RuntimeError("simulateur : géocodage/DB en panne")
    monkeypatch.setattr(rattachement_html, "rattacher", _boom)
    with session_scope() as db:
        bid = _creer_bien(db, lat=PT[1], lng=PT[0])
        db.commit()
    try:
        with session_scope() as db:
            out = intake.valider(db, bid, {})
        assert out["valide"] is True
        with session_scope() as db:
            v = db.execute(text("SELECT valide_at, idu FROM pige_faits f JOIN pige_biens b USING(bien_id) "
                                "WHERE b.bien_id = :b"), {"b": bid}).mappings().first()
        assert v["valide_at"] is not None, "la validation doit aboutir même si la proposition échoue"
        assert v["idu"] is None
    finally:
        with session_scope() as db:
            _purge(db, bid)
            db.commit()


def db_pistes(bid: int) -> list[dict]:
    with session_scope() as db:
        raw = db.execute(text("SELECT rattachement_pistes FROM pige_biens WHERE bien_id = :b"),
                         {"b": bid}).scalar()
    import json
    return raw if isinstance(raw, list) else (json.loads(raw) if raw else [])


# ── (b) tolérance ±10 % élargit les candidates vs ±5 % ─────────────────────────────────────────────

def test_tolerance_surface_10pct_elargit_les_candidates(seed):
    """Une surface annoncée à 540 m² est à +8 % de la parcelle (500 m²) : HORS ±5 %, DANS ±10 %.
    Avec TOL_SURFACE=0.10 (S5), la parcelle est candidate ; avec l'ancien 0.05, elle ne l'était pas."""
    assert rattachement_html.TOL_SURFACE == 0.10, "S5 — la tolérance de surface doit être ±10 %"
    rec = {"type": "terrain", "commune": COMMUNE, "lng": PT[0], "lat": PT[1],
           "surface_terrain": 540.0, "surface_hab": None}
    with session_scope() as db:
        # ±10 % (valeur S5) — la candidate à +8 % apparaît.
        hits_10 = rattachement_html._crit_surface(db, PT[0], PT[1], COMMUNE, 540.0)
        assert seed["idu"] in hits_10, "±10 % doit retenir la parcelle à +8 %"
        # ±5 % (ancien) — on rétablit temporairement le seuil pour prouver l'élargissement.
        old = rattachement_html.TOL_SURFACE
        rattachement_html.TOL_SURFACE = 0.05
        try:
            hits_5 = rattachement_html._crit_surface(db, PT[0], PT[1], COMMUNE, 540.0)
        finally:
            rattachement_html.TOL_SURFACE = old
        assert seed["idu"] not in hits_5, "±5 % ratait la parcelle à +8 % (d'où l'élargissement S5)"
    # et la cascade complète voit bien la candidate à ±10 %.
    with session_scope() as db:
        r = rattachement_html.rattacher(db, rec)
    assert any(p.get("idu") == seed["idu"] for p in r.get("pistes", []))


# ── (c) la file de re-vérif rend les NON RATTACHÉES en premier ─────────────────────────────────────

def test_reverif_rend_les_non_rattachees_en_premier(seed):
    """Deux biens VALIDÉS : un rattaché (idu posé à la main), un non rattaché (idu NULL). La file de
    re-vérif place le NON RATTACHÉ en tête (`non_rattachee` = true), le rattaché après."""
    from labuse.pige.api import radar_reverif

    class _FakeAuth:
        pass

    with session_scope() as db:
        b_non = _creer_bien(db)   # idu NULL
        b_ok = _creer_bien(db)
        # les deux validés + un rattaché à la main (idu réel de la commune de test).
        db.execute(text("UPDATE pige_faits SET valide_at = now() WHERE bien_id IN (:a,:c)"),
                   {"a": b_non, "c": b_ok})
        db.execute(text("UPDATE pige_biens SET idu = :i, rattachement_etat = 'rattachee', "
                        "rattachement_humain = true WHERE bien_id = :c"),
                   {"i": seed["idu"], "c": b_ok})
        db.commit()
    try:
        # on appelle la requête telle quelle via un monkeypatch de la garde admin.
        import labuse.api.auth as auth
        rows = _appeler_reverif(auth)
        ids = [r["bien_id"] for r in rows if r["bien_id"] in (b_non, b_ok)]
        assert ids, "les deux biens de test doivent apparaître dans la file"
        # le non rattaché est AVANT le rattaché.
        assert ids.index(b_non) < ids.index(b_ok), "les non rattachées passent en premier"
        # le flag est exposé pour la chip front.
        for r in rows:
            if r["bien_id"] == b_non:
                assert r["non_rattachee"] is True
            if r["bien_id"] == b_ok:
                assert r["non_rattachee"] is False
    finally:
        with session_scope() as db:
            _purge(db, b_non)
            _purge(db, b_ok)
            db.commit()


def test_reverif_expose_le_rattachement_forte_en_un_clic(seed):
    """RETOURS-10 (T1) — l'instruction humaine des candidates est retirée. Sur une annonce NON RATTACHÉE,
    la file de re-vérif expose `rattachable_forte`+`piste_idu` UNIQUEMENT si la confiance stockée est
    forte (≥ 0,85) ET qu'une 1re piste existe → le front propose « Rattacher » en un clic. Une confiance
    faible ne rend AUCUN bouton (l'annonce reste « non rattachée », point)."""
    import json

    with session_scope() as db:
        b_forte = _creer_bien(db)   # idu NULL, confiance forte + piste
        b_faible = _creer_bien(db)  # idu NULL, confiance faible
        db.execute(text("UPDATE pige_faits SET valide_at = now() WHERE bien_id IN (:a,:b)"),
                   {"a": b_forte, "b": b_faible})
        db.execute(text("UPDATE pige_biens SET rattachement_confiance = 0.92, "
                        "rattachement_pistes = CAST(:p AS jsonb) WHERE bien_id = :b"),
                   {"p": json.dumps([{"idu": seed["idu"]}]), "b": b_forte})
        db.execute(text("UPDATE pige_biens SET rattachement_confiance = 0.40, "
                        "rattachement_pistes = CAST(:p AS jsonb) WHERE bien_id = :b"),
                   {"p": json.dumps([{"idu": seed["idu"]}]), "b": b_faible})
        db.commit()
    try:
        import labuse.api.auth as auth
        rows = _appeler_reverif(auth)
        par_id = {r["bien_id"]: r for r in rows}
        assert par_id[b_forte]["rattachable_forte"] is True
        assert par_id[b_forte]["piste_idu"] == seed["idu"]
        # confiance faible → aucune tâche : pas de bouton, pas d'idu de piste servi.
        assert par_id[b_faible]["rattachable_forte"] is False
        assert par_id[b_faible]["piste_idu"] is None
        # les colonnes brutes de confiance/piste ne fuient pas dans la réponse (nettoyées).
        assert "rattachement_confiance" not in par_id[b_forte]
        assert "premiere_piste_idu" not in par_id[b_forte]
    finally:
        with session_scope() as db:
            _purge(db, b_forte)
            _purge(db, b_faible)
            db.commit()


def _appeler_reverif(auth_mod) -> list[dict]:
    """Appelle radar_reverif en neutralisant la garde admin (on teste la REQUÊTE/l'ordre, pas l'auth)."""
    from labuse.pige import api as pige_api
    orig = auth_mod.exiger_admin
    auth_mod.exiger_admin = lambda request: None
    pige_api.__dict__  # noqa: B018 — s'assurer que le module est chargé
    try:
        out = pige_api.radar_reverif(request=None)
    finally:
        auth_mod.exiger_admin = orig
    return out["file"]
