"""ALGO-FIX-1 — les quatre protections, montrées sur des PARCELLES RÉELLES (run servi q_v20).

Recette du mandat : « plus les quatre protections montrées sur des parcelles réelles : pente
inconnue qui ferait changer la bande → À vérifier ; bâti conservé calculé sans coefficient bâti ;
AU fermée → À différer avant toute bande ; valeur invalide → À vérifier. »

Nécessite la base locale servie (marqueurs `db`, `reel`). Les identifiants ci-dessous ont été
constatés sur q_v20 le 2026-11-09 ; si l'un disparaît d'un run futur, le test SKIP ce cas plutôt
que d'échouer à l'aveugle (il est repéré par sa caractéristique, pas seulement son IDU)."""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as _Session

from labuse.scoring import scenarios_v2 as v2
from labuse.scoring import scenarios_v2_build as build

pytestmark = [pytest.mark.reel]


@pytest.fixture(scope="module")
def db_session():
    """Session LECTURE SEULE sur la base RÉELLE servie (q_v20), indépendante du conftest : elle
    n'applique AUCUN schema-heal (jamais de DDL sur la base de l'app). URL via
    `LABUSE_REEL_DATABASE_URL` (le nightly/poste la pose) ; sinon SKIP — jamais d'échec à l'aveugle.
    Tout est annulé en fin de module (rollback)."""
    url = os.environ.get("LABUSE_REEL_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_REEL_DATABASE_URL non défini (recette réelle q_v20)")
    eng = create_engine(url)
    conn = eng.connect()
    trans = conn.begin()
    sess = _Session(bind=conn)
    try:
        if sess.execute(text("SELECT count(*) FROM score_labuse WHERE run_label='q_v20'")).scalar() == 0:
            pytest.skip("run q_v20 absent de la base réelle")
        yield sess
    finally:
        sess.close()
        trans.rollback()
        conn.close()
        eng.dispose()


def _eval(session, idu, scenario="keep"):
    pid = session.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
    if pid is None:
        pytest.skip(f"parcelle {idu} absente de la base locale")
    recs = build.records_for_parcels(session, [pid], enrich=True)
    if not recs:
        pytest.skip(f"parcelle {idu} non servie en q_v20")
    rec, v1 = recs[0]
    return rec, v1, v2.evaluate(rec, {"mode": "potential", "scenario": scenario})


# ── P1 — pente inconnue qui ferait changer la bande → À vérifier (D4) ────────
def test_pente_inconnue_bascule_bande_a_verifier(db_session):
    rec, v1, r = _eval(db_session, "97422000BI1146")
    assert rec.slope_deg is None                       # pente réellement non mesurée
    assert r.status == "TO_VERIFY"                     # l'inconnue ne fabrique pas une bande
    assert r.cause_codes == ["BANDE_SENSIBLE_INCONNUE"]
    assert r.band is None and r.band_provisional is not None   # bande provisoire conservée au détail
    assert r.quantities["additional"] is not None      # la quantité reste visible


# ── P2 — bâti conservé calculé SANS coefficient bâti (D2) ────────────────────
def test_conservation_sans_coefficient_bati(db_session):
    rec, v1, r = _eval(db_session, "97403000AM0092")   # bâti ~45 % d'emprise, V1 bande D
    assert (rec.built_coverage_pct or 0) >= 30         # parcelle réellement bâtie
    assert r.status == "ESTIMATED"
    # Le coefficient de faisabilité V2 n'inclut AUCUN facteur bâti : son produit = pente×forme×accès.
    d = r.details
    produit = d["f_pente"] * d["f_forme"] * d["f_acces"]
    import math
    assert math.isclose(min(100, round(_points(rec) * max(0.4, produit))), d["score_brut"])
    # La démolition est un point de vigilance, jamais un malus : la bande V2 n'est pas tirée vers le
    # bas par le bâti — ici elle remonte D→C par rapport au score V1 (qui appliquait ×0,8 bâti).
    assert v2._BANDE_RANG[r.band] <= v2._BANDE_RANG.get(v1, 9)


def _points(rec):
    from labuse.scoring import score_labuse as sl
    bareme, _ = sl.charger_bareme()
    pts, _ = sl._bareme_capacite(rec.residual_m2, None, bareme.get("capacite", {}))
    return pts


# ── P3 — AU fermée → À différer, AVANT toute bande (D3) ──────────────────────
def test_au_fermee_differee_avant_bande(db_session):
    rec, v1, r = _eval(db_session, "97410000AB0212")
    assert rec.horizon == "deferred"
    assert r.status == "DEFERRED"
    assert r.band is None                               # aucune bande sur le différé
    assert r.quantities["additional"] is None           # pas de capacité actuelle imputée
    # La capacité conditionnelle est servie à part, sans ×0,5 ni date d'ouverture inventée.
    assert any("conditionnelle" in m for m in r.vigilance)


# ── P4 — valeur incohérente (surface plan ≠ cadastre) → À vérifier (D8) ──────
def test_valeur_incoherente_a_verifier(db_session):
    rec, v1, r = _eval(db_session, "97401000AC0636")   # cause moteur = surface_incertaine
    assert rec.geometry_status == "suspect"
    assert r.status == "TO_VERIFY"
    assert r.band is None                               # jamais un score, jamais une bande (D8)


# ── bonus — reconstruction calculée POUR les parcelles saturées, D_net signé ─
def test_reconstruction_parcelle_saturee_gain_net_negatif(db_session):
    rec, v1, r = _eval(db_session, "97403000AP1634", scenario="rebuild")   # emprise 158 %, V1 « 0 »
    assert v1 == "0"                                    # V1 : « Non retenue », muette
    assert r.status == "ESTIMATED"                      # V2 : un scénario de reconstruction existe
    assert r.quantities["net_signed"] < 0              # gain net SIGNÉ négatif, pas écrasé à 0
    assert r.quantities["project_total"] is not None and r.quantities["existing"] is not None


# ── P4 bis — terrain_exigu de 11 ha hard-exclu : la vraie cause (Parc National), pas « trop étroit » ─
def test_terrain_exigu_grande_parcelle_hard_exclue(db_session):
    # 97403000AL0258 (113 832 m²) est dans le CŒUR DE PARC NATIONAL (UNESCO) + PPR rouge 100 % +
    # forêt domaniale + pente 133 % : « terrain trop étroit » était trompeur ; la vraie cause est
    # une exclusion dure prouvée → Hors de ce projet (avis Astra §4 : géométrie/indices ≠ verdict).
    rec, v1, r = _eval(db_session, "97403000AL0258")
    assert rec.cause_engine == "terrain_exigu"
    assert r.status == "OUTSIDE_OBJECTIVE"
    assert "trop étroit" not in " ".join(r.vigilance)   # le mot faux n'est jamais servi


# ── P4 ter — terrain_exigu SANS exclusion dure : À vérifier, métriques = INDICES (pas « retraits ») ─
def test_terrain_exigu_sans_exclusion_a_verifier(db_session):
    rec, v1, r = _eval(db_session, "97415000AB0732")   # 82 254 m², terrain_exigu, non hard-exclu
    assert rec.cause_engine == "terrain_exigu"
    assert r.status == "TO_VERIFY"
    assert r.cause_codes == ["CALCUL_ASSIETTE_DOUTEUX"]
    joined = " ".join(r.vigilance)
    assert "trop étroit" not in joined                 # jamais déduit d'une taille
    assert "retraits ne sont pas tracés" in joined     # métriques = indices, pas une preuve de retraits


# ── P5 — EH0043 : capacité sur portion AU sans régime établi → À vérifier, provisoire consultable ─
def test_eh0043_au_non_etabli_a_verifier(db_session):
    rec, v1, r = _eval(db_session, "97411000EH0043", scenario="keep")
    assert v1 == "B"                                    # V1 servait « Bonne »
    assert r.status == "TO_VERIFY"
    assert r.cause_codes == ["HORIZON_INCONNU"]         # régime AUm non établi (pas « À différer »)
    assert r.band is None and r.band_provisional is not None   # pas de bande ferme ; provisoire au détail
    assert r.quantities["additional"] is not None       # capacité provisoire CONSULTABLE
    assert r.zone_portion and r.zone_portion["zone"] == "AUm"   # portion productive exposée (D9)
    assert any("régime" in m for m in r.vigilance)
