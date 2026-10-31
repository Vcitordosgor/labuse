"""MARCHE-UNIQUE-1 — RECETTE : une médiane DVF par (commune, type), la MÊME partout.

Le fil rouge de l'audit NU-1 côté marché : chaque surface recalculait sa médiane commune avec son
propre filtre de nature, sa propre fenêtre, son propre dénominateur — d'où, sur le MÊME écran du
Radar, « acté médian maisons » à 4 030 € d'un côté et 3 750 € de l'autre (NU-F-001), le neuf (VEFA)
qui remontait la médiane « ancien » (NU-A-012 / NU-E-030) et un prix d'appartement servi sur une
maison (NU-A-002 / NU-D-010).

Ce test SEMME des ventes connues pour 3 communes × 2 types, puis vérifie que les 3 points de lecture
du produit — le tableau Radar (`_dvf_bati_type`), le bloc commune lu par « Ce bien »/Estimer/les PDF
(`marche_commune_bloc`) et le point de calcul unique (`mediane_commune`) — servent EXACTEMENT la même
médiane, à l'euro près. Il ÉCHOUE au moindre écart. Il vérifie aussi que la VEFA (neuf) et les natures
hors gré à gré (adjudication, échange) ne contaminent JAMAIS la médiane « ancien ».
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

# COHERENCE-HOOK-1 — regroupée sous la suite de cohérence (médiane : une valeur, trois lectures).
pytestmark = pytest.mark.coherence

# 3 communes témoins × 2 types, chacune à un niveau de prix DISTINCT (pour qu'un mélange de
# types ou de communes se verrait). Médiane construite pour être EXACTE (prix tous égaux).
_PLAN = {
    "RECETTEA": {"maison": 3000, "appartement": 2000},
    "RECETTEB": {"maison": 3500, "appartement": 2600},
    "RECETTEC": {"maison": 4200, "appartement": 4800},
}
_N = 12   # ≥ seuil d'effectif (8) pour une médiane servie


def _seed(db, commune: str, type_local: str, prix_m2: int, n: int, *, nature: str = "Vente") -> None:
    surf = 100.0
    for i in range(n):
        db.execute(text(
            "INSERT INTO dvf_mutations (mutation_id, date_mutation, valeur_fonciere, type_local, "
            "  surface_reelle_bati, nature_mutation, commune, geom) "
            "VALUES (:mid, :d, :vf, :tl, :surf, :nat, :c, ST_SetSRID(ST_MakePoint(55.5, -21.0), 4326))"),
            {"mid": f"{commune}-{type_local}-{nature}-{i}", "d": "2025-06-15",
             "vf": prix_m2 * surf, "tl": type_local, "surf": surf, "nat": nature, "c": commune})


@pytest.mark.db
def test_une_mediane_par_commune_et_type_la_meme_partout(db_session):
    db = db_session
    if db.execute(text("SELECT to_regclass('dvf_mutations')")).scalar() is None:
        pytest.skip("base de test sans dvf_mutations")

    from labuse.marche_dvf_commune import mediane_commune
    from labuse.pige.signaux import _dvf_bati_type
    from labuse.faisabilite.marche_commune import marche_commune_bloc

    for commune, par_type in _PLAN.items():
        for tl, prix in par_type.items():
            _seed(db, commune, tl.capitalize(), prix, _N)
        # Contamination à EXCLURE : une VEFA (neuf) très chère + une adjudication très basse, en maison.
        _seed(db, commune, "Maison", 9000, 5, nature="Vente en l'état futur d'achèvement")
        _seed(db, commune, "Maison", 500, 5, nature="Adjudication")
        _seed(db, commune, "Maison", 500, 5, nature="Echange")
    db.flush()

    for commune, par_type in _PLAN.items():
        bloc = marche_commune_bloc(db, commune) or {}
        for tl, attendu in par_type.items():
            canon = mediane_commune(db, commune, tl)
            canonv = round(canon["eur_m2"]) if canon["eur_m2"] is not None else None
            tableau = _dvf_bati_type(db, commune, tl)
            tableauv = round(tableau["eur_m2"]) if tableau.get("eur_m2") is not None else None
            blocv = bloc.get("median_maison_eur_m2" if tl == "maison" else "median_appartement_eur_m2")
            # (1) la médiane servie est bien l'ANCIEN de gré à gré (VEFA 9000 / adjudication 500 exclus)
            assert canonv == attendu, f"{commune}/{tl}: médiane {canonv} ≠ {attendu} (contamination ?)"
            # (2) les 3 surfaces servent la MÊME médiane, à l'euro près — échec au moindre écart
            assert canonv == tableauv == blocv, \
                f"{commune}/{tl}: divergence canon={canonv} tableau={tableauv} bloc={blocv}"


@pytest.mark.db
def test_neuf_vefa_median_jamais_dans_l_ancien(db_session):
    """Le neuf a sa PROPRE médiane (VEFA), jamais mêlée à l'ancien (NU-B-003 / NU-E-030)."""
    db = db_session
    if db.execute(text("SELECT to_regclass('dvf_mutations')")).scalar() is None:
        pytest.skip("base de test sans dvf_mutations")
    from labuse.marche_dvf_commune import mediane_commune, NATURE_ANCIEN_SQL
    # L'ancien exclut strictement la VEFA : le prédicat de nature est 'Vente' seul.
    assert "= 'Vente'" in NATURE_ANCIEN_SQL and "futur" not in NATURE_ANCIEN_SQL
    _seed(db, "RECETTED", "Maison", 3000, _N)
    _seed(db, "RECETTED", "Maison", 9000, _N, nature="Vente en l'état futur d'achèvement")
    db.flush()
    r = mediane_commune(db, "RECETTED", "maison")
    assert round(r["eur_m2"]) == 3000, "la VEFA (9000) ne doit pas remonter la médiane ancien (3000)"
