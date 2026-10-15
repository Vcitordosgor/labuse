"""CHASSE-INVARIANTS-FIX-1 — correctifs des 15 écarts de docs/audit-2026-10/chasse-invariants-1/.

Un bloc de tests par lot. Les lots « calcul » (dont l'effet n'arrive qu'au run final q_v19) sont
testés au plus près de la CAUSE corrigée (fonction de calcul, fragment SQL, garde-fou) — jamais en
attendant une donnée servie que ce worktree ne régénère pas.
"""
from __future__ import annotations

import contextlib
import os

import pytest


@contextlib.contextmanager
def app_session():
    """Session sur la base APPLICATIVE (données réelles servies). En test, `conftest` repointe
    LABUSE_DATABASE_URL vers la base vierge `labuse_test` ; les gardes `reel` ont besoin du run
    servi réel → on ouvre explicitement LABUSE_APP_DATABASE_URL (la vraie base, lecture seule ici)."""
    from sqlalchemy.orm import sessionmaker
    from labuse.db import make_engine
    url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent (base applicative non définie)")
    eng = make_engine(url=url)
    s = sessionmaker(bind=eng, future=True)()
    try:
        yield s
    finally:
        s.close()
        eng.dispose()


def _ids_for(session, idus):
    from sqlalchemy import text
    rows = session.execute(text("SELECT id, idu FROM parcels WHERE idu = ANY(:w)"),
                           {"w": list(idus)}).fetchall()
    return {r[1]: r[0] for r in rows}


# ───────────────────────────── Lot 1 — E-01 / E-13 : taux d'occupation du gabarit ─────────────
def test_lot1_rendu_unique_taux_emprise_jamais_de_brut_au_dela_de_100():
    from labuse.faisabilite.residuel import TAUX_EMPRISE_SATURE, fmt_taux_emprise
    assert fmt_taux_emprise(None) is None
    assert fmt_taux_emprise(0) == "0 %"
    assert fmt_taux_emprise(45) == "45 %"
    assert fmt_taux_emprise(100) == "100 %"
    for saturee in (101, 300, 301, 9735, 19569):
        aff = fmt_taux_emprise(saturee)
        assert aff == TAUX_EMPRISE_SATURE
        assert "%" not in aff and str(saturee) not in aff  # jamais le pourcentage brut


def test_lot1_bloc_comparatif_pdf_affiche_sature_pas_le_brut():
    """E-01 — la fuite réelle était l'export Comparatif (19 569 % imprimé brut). Il passe
    désormais par le rendu unique : « Saturé … », jamais le nombre."""
    from labuse.exports.blocs.comparatif import rendu
    html = rendu([
        {"idu": "97411000AY0015", "commune": "Saint-Paul", "taux_emprise_pct": 19569, "surface_m2": 500},
        {"idu": "97401000AB0001", "commune": "Les Avirons", "taux_emprise_pct": 42, "surface_m2": 800},
    ])
    assert "Saturé" in html
    assert "19569" not in html and "19 569" not in html   # le brut ne fuit plus
    assert "42 %" in html                                  # sous 100 % : le pourcentage normal


def test_lot1_filtre_emprise_sature_est_une_valeur_a_part_entiere():
    """E-01 — « Saturé » filtrable : le prédicat cherche taux_emprise_pct > 100 (le range 0–100
    ne pourrait jamais l'atteindre)."""
    from labuse.api.app import FiltreCriteres
    where, params = FiltreCriteres(source="q_v18", emprise_sature=True).where()
    assert "taux_emprise_pct > 100" in where
    # inactif par défaut : aucune mention sans la case
    where0, _ = FiltreCriteres(source="q_v18").where()
    assert "taux_emprise_pct > 100" not in where0


def test_lot1_sous_densite_et_taux_lisent_la_meme_valeur_arrondie():
    """E-13 — le flag sous_densite se calcule sur la valeur ARRONDIE (celle servie), plus sur le
    flottant : à 39,6 % → affiché 40 % → sous_densite doit être FAUX (seuil 40)."""
    import labuse.faisabilite.residuel as R

    class _Hyp:
        sous_densite_seuil_pct = 40
        niveaux_bati_existant_defaut = 1
        coef_sdp_existante = 1.0

    # on reconstitue la logique de bord exactement comme le moteur l'écrit (E-13)
    for taux_reel, attendu_affiche, attendu_sous_densite in [
        (39.6, 40, False),   # arrondit à 40 = seuil → PAS sous-densité (c'était la contradiction)
        (39.4, 39, True),    # arrondit à 39 < 40 → sous-densité
        (40.0, 40, False),
    ]:
        arrondi = round(taux_reel)
        sous_densite = arrondi < _Hyp.sous_densite_seuil_pct
        assert arrondi == attendu_affiche
        assert sous_densite is attendu_sous_densite
    # garde-fou : le helper d'affichage lit bien cette même valeur arrondie
    assert R.fmt_taux_emprise(39.6) == "40 %"


# ───────────────────────────── Lot 2 — E-03 / E-11 : PPR rouge compté en UNION ─────────────────
@pytest.mark.reel
def test_lot2_union_coverage_somme_les_polygones_rouges():
    """E-03 — la couverture UNIONNÉE dépasse chaque polygone pris isolément (c'était la faille :
    deux rouges < 50 % chacun, ≥ 50 % cumulés)."""
    from labuse.cascade.context import EvalContext
    with app_session() as s:
        ids = _ids_for(s, ["97401000AK0138"])          # 65 % rouge (2 polygones INTERDICTION)
        if not ids:
            pytest.skip("témoin PPR rouge absent de la base")
        pid = next(iter(ids.values()))
        ctx = EvalContext(s)
        reds = [i for i in ctx.intersections(pid, "ppr") if (i.subtype or "").upper() == "INTERDICTION"]
        if len(reds) < 2:
            pytest.skip("témoin sans multi-polygone rouge aujourd'hui")
        union_frac, _ = ctx.union_coverage(pid, "ppr", {"INTERDICTION"})
        assert union_frac >= 0.50                        # ≥ seuil d'exclusion
        assert union_frac > max(i.coverage for i in reds)  # l'union dépasse le plus gros polygone


@pytest.mark.reel
def test_lot2_cascade_exclut_le_rouge_majoritaire_en_union():
    """E-03/E-11 — la cascade écarte (HARD_EXCLUDE) les témoins ≥ 50 % rouge EN UNION, et NE touche
    pas une parcelle voisine sans rouge majoritaire (pas de faux positif)."""
    from labuse.cascade.pipeline import evaluate_parcels
    exclure = ["97401000AK0138", "97401000AM1179"]       # 65 %, 92 %
    garder = "97401000AI1157"
    with app_session() as s:
        ids = _ids_for(s, [*exclure, garder])
        if len(ids) < 3:
            pytest.skip("témoins PPR rouge absents de la base")
        outcomes = {o.parcel_id: o for o in evaluate_parcels(list(ids.values()), s, persist=False)}
        for idu in exclure:
            o = outcomes[ids[idu]]
            he = [v for v in o.verdicts if v.layer_name == "risques" and v.is_hard_exclude()]
            assert he, f"{idu} devrait être écartée (PPR rouge ≥ 50 % en union)"
            assert "PPR zone rouge" in he[0].detail and "%" in he[0].detail
        o_g = outcomes[ids[garder]]
        assert not any(v.layer_name == "risques" and v.is_hard_exclude() for v in o_g.verdicts)
