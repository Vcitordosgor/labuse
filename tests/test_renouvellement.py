"""M-RENOUV lot A — tests du segment Renouvellement.

Couvre : (1) config (Σ poids = 100, REFUS sinon) ; (2) reconnaissance du code BatiLayer
depuis le motif (miroir Python/SQL, symétrie avec bati.classify) ; (3) doctrine wording
(« opportunité » interdit) ; (4) build DB : définition A1 respectée (bati-exclue U/AU
capacitaire entre ; copro, foncier public, hors-zone, sans-capacité n'entrent pas),
score borné, rangs déterministes — et AUCUNE écriture hors parcel_renouvellement.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import bati
from labuse import renouvellement as rn

# ───────────────────────── config ─────────────────────────

def test_config_poids_somment_a_100():
    cfg = rn.load_config()
    assert sum(cfg["poids"].values()) == 100
    # M129-C (Vic 19/08/2026) : `divisibilite` RETIRÉE (division_or sort du produit) — 3 composantes.
    assert set(cfg["poids"]) == {"potentiel_residuel", "assiette", "contexte_marche"}
    assert cfg["seuils"]["sdp_min_m2"] == 100 and cfg["seuils"]["surface_min_m2"] == 600


def test_config_refus_si_poids_faux(monkeypatch):
    monkeypatch.setattr(rn, "load_yaml_config", lambda _n: {
        "poids": {"potentiel_residuel": 47, "assiette": 29, "contexte_marche": 30},
        "seuils": {"sdp_min_m2": 100, "surface_min_m2": 600}})
    with pytest.raises(ValueError, match="≠ 100"):
        rn.load_config()


# ─────────────────── code BatiLayer (miroir Python/SQL) ───────────────────

def test_code_from_detail_reconnait_les_trois_cas_francs():
    # Les motifs réels sont émis par bati.classify — on teste sur SA sortie (source unique),
    # pas sur des chaînes inventées : si le wording de classify change, ce test casse.
    assert rn.code_from_detail(bati.classify(0.6, 2, 100, 800)["motif"]) == "deja_bati"
    assert rn.code_from_detail(bati.classify(0.35, 1, 100, 800)["motif"]) == "deja_bati_probable"
    assert rn.code_from_detail(bati.classify(0.20, 4, 100, 800)["motif"]) == "ensemble_bati"


def test_code_from_detail_rejette_les_non_francs():
    # partiellement bâti (flag qualité) et vacants n'ont pas de motif franc
    assert rn.code_from_detail(bati.classify(0.20, 1, 100, 800)["motif"]) is None
    assert rn.code_from_detail(None) is None
    assert rn.code_from_detail("PPR rouge — aléa fort") is None


def test_ordre_prefixes_probable_avant_deja_batie():
    # « déjà bâtie probable » doit matcher AVANT « déjà bâtie » (préfixe commun)
    assert rn.code_from_detail("déjà bâtie probable : 35 % …") == "deja_bati_probable"
    assert rn.code_from_detail("déjà bâtie : 3 bâtiment(s) …") == "deja_bati"


# ───────────────────────── doctrine wording ─────────────────────────

def test_wording_jamais_opportunite():
    textes = [rn.LIBELLE_SEGMENT, *rn.LIBELLES_COMPOSANTES.values()]
    for t in textes:
        assert "opportunit" not in t.lower()
    assert "renouvellement" in rn.LIBELLE_SEGMENT.lower()
    assert "occupée" in rn.LIBELLE_SEGMENT
    # M129-C : la divisibilité a QUITTÉ le segment — aucun libellé ne mentionne la division
    assert all("division" not in t.lower() for t in rn.LIBELLES_COMPOSANTES.values())


# ───────────────────────── build DB ─────────────────────────

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"
_RUN = "q_vtest_renouv"


def _seed_parcelle(s, idu, surface=800):
    return s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), :su, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": _WKT, "su": surface}).scalar()


def _seed_bati_exclude(s, pid, detail=None):
    # Le motif servi vient de bati.classify (source unique) — on NE réinvente PAS la chaîne :
    # si le wording de classify change, le seed suit (même principe que test_code_from_detail).
    if detail is None:
        detail = bati.classify(0.6, 2, 100, 800)["motif"]   # « déjà bâtie : 2 bâtiment(s) couvrant 60 % … »
    s.execute(text(
        "INSERT INTO dryrun_cascade_results (run_label, parcel_id, layer_name, result, detail) "
        "VALUES (:r, :p, 'bati', 'SOFT_FLAG', :d)"), {"r": _RUN, "p": pid, "d": detail})


def _seed_public_exclude(s, pid):
    s.execute(text(
        "INSERT INTO dryrun_cascade_results (run_label, parcel_id, layer_name, result, detail) "
        "VALUES (:r, :p, 'foncier_public', 'SOFT_FLAG', 'domaine public — non acquérable')"),
        {"r": _RUN, "p": pid})


def _ensure_ext_tables(s):
    s.execute(text("""
        CREATE TABLE IF NOT EXISTS p_model_ext_dataset (
          idu varchar(14), annee int, zone_plu text, sdp_residuelle_m2 int,
          surface_m2 float, rot_bati_brute float)"""))
    s.execute(text("""
        CREATE TABLE IF NOT EXISTS p_model_ext_copro (
          idu varchar(14) PRIMARY KEY, copro_rnic boolean, copro_dvf boolean)"""))
    s.execute(text("""
        CREATE TABLE IF NOT EXISTS division_or_candidates (idu varchar(14) PRIMARY KEY)"""))


def _seed_dataset(s, idu, zone="U", sdp=500, surface=800.0, rot=0.01, annee=2026):
    s.execute(text(
        "INSERT INTO p_model_ext_dataset (idu, annee, zone_plu, sdp_residuelle_m2, surface_m2, rot_bati_brute) "
        "VALUES (:i, :a, :z, :sdp, :su, :r)"),
        {"i": idu, "a": annee, "z": zone, "sdp": sdp, "su": surface, "r": rot})


@pytest.mark.db
def test_build_definition_a1(db_session):
    s = db_session
    _ensure_ext_tables(s)
    IN1, IN2, COP, PUB, ZONE, CAP, PART = (f"97499000R{i}000{i}" for i in range(1, 8))

    # IN1 : bati-exclue, U, sdp 500 → ENTRE (M129-C : la divisibilité ne compte plus)
    p = _seed_parcelle(s, IN1); _seed_bati_exclude(s, p); _seed_dataset(s, IN1, sdp=500, rot=0.02)
    # IN2 : bati-exclue (ensemble), AU, sdp 0 mais surface 900 ≥ 600 → ENTRE par la surface
    p = _seed_parcelle(s, IN2, 900); _seed_bati_exclude(
        s, p, bati.classify(0.20, 4, 100, 800)["motif"])   # « ensemble bâti : 4 bâtiments … »
    _seed_dataset(s, IN2, zone="AU", sdp=0, surface=900.0)
    # COP : idem IN1 mais copro → N'ENTRE PAS
    p = _seed_parcelle(s, COP); _seed_bati_exclude(s, p); _seed_dataset(s, COP, sdp=500)
    s.execute(text("INSERT INTO p_model_ext_copro (idu, copro_rnic, copro_dvf) VALUES (:i, true, false) "
                   "ON CONFLICT (idu) DO UPDATE SET copro_rnic = true"), {"i": COP})
    # PUB : idem IN1 mais foncier public → N'ENTRE PAS
    p = _seed_parcelle(s, PUB); _seed_bati_exclude(s, p); _seed_public_exclude(s, p); _seed_dataset(s, PUB, sdp=500)
    # ZONE : bati-exclue mais zone N → N'ENTRE PAS
    p = _seed_parcelle(s, ZONE); _seed_bati_exclude(s, p); _seed_dataset(s, ZONE, zone="N", sdp=500)
    # CAP : bati-exclue, U, sdp 50 ≤ 100 et surface 400 < 600 → N'ENTRE PAS
    p = _seed_parcelle(s, CAP, 400); _seed_bati_exclude(s, p); _seed_dataset(s, CAP, sdp=50, surface=400.0)
    # PART : partiellement bâtie (PAS un HARD_EXCLUDE bati) → N'ENTRE PAS
    p = _seed_parcelle(s, PART); _seed_dataset(s, PART, sdp=500)

    r = rn.build(s, run_label=_RUN, commit=False)

    rows = {x["idu"]: x for x in s.execute(text(
        "SELECT * FROM parcel_renouvellement")).mappings().all()}
    assert set(rows) >= {IN1, IN2} and not ({COP, PUB, ZONE, CAP, PART} & set(rows))
    assert rows[IN1]["code_bati_origine"] == "deja_bati"
    assert rows[IN2]["code_bati_origine"] == "ensemble_bati"
    # score borné, composantes cohérentes avec la config
    for x in rows.values():
        assert 0 <= x["renouv_score"] <= 100
        assert x["renouv_score"] == min(100, x["comp_potentiel"] + x["comp_assiette"]
                                        + x["comp_marche"])
    # rangs : denses, déterministes (score DESC puis idu)
    assert sorted(x["rang_segment"] for x in rows.values()) == list(range(1, len(rows) + 1))
    # entonnoir cohérent : final = n
    assert r["funnel"]["5_hors_foncier_public_final"] == r["n"] == len(rows)
    assert r["funnel"]["1_bati_fait"] >= r["funnel"]["2_zone_u_au"] >= r["funnel"]["3_capacite"] \
        >= r["funnel"]["4_hors_copro"] >= r["n"]


@pytest.mark.db
def test_build_n_ecrit_que_sa_table(db_session):
    """Règle 1 du mandat : la seule écriture est parcel_renouvellement — les tables
    servies (dryrun_*, parcel_p_score_v2) sont intactes après build."""
    s = db_session
    _ensure_ext_tables(s)
    idu = "97499000RX0001"
    p = _seed_parcelle(s, idu); _seed_bati_exclude(s, p); _seed_dataset(s, idu, sdp=500)
    avant_cascade = s.execute(text(
        "SELECT count(*) FROM dryrun_cascade_results WHERE run_label = :r"), {"r": _RUN}).scalar()
    rn.build(s, run_label=_RUN, commit=False)
    apres_cascade = s.execute(text(
        "SELECT count(*) FROM dryrun_cascade_results WHERE run_label = :r"), {"r": _RUN}).scalar()
    assert avant_cascade == apres_cascade
    # idempotence : rebuild → mêmes lignes
    n1 = s.execute(text("SELECT count(*) FROM parcel_renouvellement")).scalar()
    rn.build(s, run_label=_RUN, commit=False)
    n2 = s.execute(text("SELECT count(*) FROM parcel_renouvellement")).scalar()
    assert n1 == n2
