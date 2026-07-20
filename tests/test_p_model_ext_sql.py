"""PHASE 0 « Le Juge » — J1.b : label L2-F et flag copro du modèle P (M3.6, `ext_sql.py`).

Fixtures synthétiques MINIMALES sur `labuse_test`, en transaction ROLLBACK (`db_session`) →
aucune pollution. On exécute le FRAGMENT SQL RÉEL `l2f_mutation_flags` (le label servi au modèle)
et les prédicats copro (union RNIC ∪ DVF-appartements) tels qu'ils vivent dans le code.

NB : `build_copro_flags`/`build_ext_dataset` appellent `session.commit()` (créent des tables) →
non appelés ici pour préserver l'isolation ; on caractérise leurs PRÉDICATS (l'union copro).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.scoring.p_model.ext_sql import IMMEUBLE_ENTIER_MIN_APP, l2f_mutation_flags

pytestmark = pytest.mark.db

IDU = "97415000AB0001"


def _mut(session, id_mutation, locals_, idu=IDU, nature="Vente"):
    for tl in locals_:
        session.execute(text(
            "INSERT INTO dvf_mutations_parcelle (id_mutation, id_parcelle, date_mutation, "
            "nature_mutation, type_local, millesime) VALUES (:m, :i, DATE '2022-06-01', :n, :tl, 2022)"),
            {"m": id_mutation, "i": idu, "n": nature, "tl": tl})


def _l2f(session):
    return {r[0]: r[1] for r in session.execute(text(l2f_mutation_flags("dvf_mutations_parcelle"))).all()}


# ───────────────────── Label L2-F : exclusion des ventes de LOT de copro ─────────────────────

def test_l2f_vente_lot_copro_exclue(db_session):
    _mut(db_session, "M_LOT", ["Appartement"])                 # 1 appartement → lot de copro
    assert _l2f(db_session)["M_LOT"] is True


def test_l2f_immeuble_entier_conserve(db_session):
    _mut(db_session, "M_IMM", ["Appartement"] * IMMEUBLE_ENTIER_MIN_APP)   # ≥ 4 apparts → immeuble entier
    assert _l2f(db_session)["M_IMM"] is False                  # conservée dans L2-F (foncier réel)


def test_l2f_frontiere_3_appartements_exclue(db_session):
    # FRONTIÈRE (comportement ACTUEL) : 3 < IMMEUBLE_ENTIER_MIN_APP (4) → exclue.
    _mut(db_session, "M_3", ["Appartement"] * 3)
    assert _l2f(db_session)["M_3"] is True


def test_l2f_terrain_nu_est_l2(db_session):
    # aucun local (type_local NULL) + « Vente terrain à bâtir » → terrain nu = L2 (jamais exclu L2-F).
    _mut(db_session, "M_TER", [None], nature="Vente terrain à bâtir")
    assert _l2f(db_session)["M_TER"] is False


def test_l2f_maison_non_exclue(db_session):
    _mut(db_session, "M_MAI", ["Maison"])                      # pas « exclusivement App/Dép »
    assert _l2f(db_session)["M_MAI"] is False


def test_l2f_appart_plus_dependance_lot_exclue(db_session):
    # tous ∈ {Appartement, Dépendance}, ≥1 App, 1 App < 4 → lot de copro → exclue.
    _mut(db_session, "M_AD", ["Appartement", "Dépendance"])
    assert _l2f(db_session)["M_AD"] is True


# ───────────────────── Flag copro parcelle : union RNIC ∪ DVF-appartements ─────────────────────

def _copro_dvf(session, idu):
    """Prédicat `copro_dvf` d'`ext_sql.build_copro_flags` : mutation L2 « exclusivement App/Dép »
    avec ≥1 Appartement (SANS le seuil < 4 — l'immeuble entier flague AUSSI la parcelle copro)."""
    return session.execute(text(
        "SELECT coalesce(bool_and(type_local IN ('Appartement','Dépendance')) "
        "  FILTER (WHERE type_local IS NOT NULL), false) AND bool_or(type_local = 'Appartement') "
        "FROM dvf_mutations_parcelle WHERE id_parcelle = :i "
        "  AND nature_mutation IN ('Vente','Vente terrain à bâtir')"), {"i": idu}).scalar()


def _copro_rnic(session, idu):
    """Prédicat `copro_rnic` : la parcelle est rattachée à une copro RNIC (idu_codes ∪ parcelle_idu)."""
    return session.execute(text(
        "SELECT EXISTS (SELECT 1 FROM rnic_coproprietes r, "
        "               jsonb_array_elements_text(coalesce(r.idu_codes,'[]')) c(idu) WHERE c.idu = :i) "
        "    OR EXISTS (SELECT 1 FROM rnic_coproprietes r WHERE r.parcelle_idu = :i)"), {"i": idu}).scalar()


def test_copro_rnic_seul_flague(db_session):
    db_session.execute(text(
        "INSERT INTO rnic_coproprietes (numero_immatriculation, idu_codes, parcelle_idu) "
        "VALUES ('RNIC0001', :codes, NULL)"), {"codes": f'["{IDU}"]'})
    assert _copro_rnic(db_session, IDU) is True
    assert _copro_dvf(db_session, IDU) is False        # aucune mutation → pas de flag DVF


def test_copro_dvf_seul_flague(db_session):
    _mut(db_session, "M_APP", ["Appartement", "Appartement"])   # que des apparts → copro DVF
    assert _copro_dvf(db_session, IDU) is True
    assert _copro_rnic(db_session, IDU) is False       # absente du RNIC


def test_copro_ni_rnic_ni_dvf_pas_de_flag(db_session):
    _mut(db_session, "M_MAI2", ["Maison"])             # maison → ni copro DVF ni RNIC
    assert _copro_dvf(db_session, IDU) is False
    assert _copro_rnic(db_session, IDU) is False


def test_copro_dvf_immeuble_entier_flague_la_parcelle(db_session):
    # Distinction FINE : l'immeuble entier (≥4 App) est CONSERVÉ dans le label L2-F (mutation),
    # mais flague QUAND MÊME la PARCELLE comme copro (copro_dvf n'a pas le seuil < 4).
    _mut(db_session, "M_IMM2", ["Appartement"] * IMMEUBLE_ENTIER_MIN_APP)
    assert _copro_dvf(db_session, IDU) is True
    assert _l2f(db_session)["M_IMM2"] is False
