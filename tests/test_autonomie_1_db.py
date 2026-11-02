"""DEPLOY-AUTONOMIE — recette DB du calcul de nuit (marquée `reel` : exige la base SERVIE réelle).

La couche DB d'AUTONOMIE-1 (`jobs_impl._mesures_run`, les contrôles AVANT promotion) n'avait JAMAIS
tourné contre le schéma servi : elle visait des colonnes inexistantes en prod (code_palier, parcel_id,
parcel_flags.run_id/entierement_rouge, coherence_runs.ecarts/cree_at). Chaque mesure retombait alors à
None (caught) → controler_run REFUSAIT toujours (fail-closed, mais le calcul de nuit ne pouvait JAMAIS
promouvoir). Ce test est le GARDE-FOU qui manquait : il exécute les mesures contre la vraie base et
exige que chacune CONCLUE (int, pas None) — une régression de nom de colonne le rend rouge.

JAMAIS en CI (base vide) : rejoué au banc de nuit en prod (marqueur `reel`)."""
from __future__ import annotations

import contextlib
import os

import pytest

pytestmark = pytest.mark.reel


@contextlib.contextmanager
def app_session():
    """Session sur la base APPLICATIVE (données réelles servies, lecture seule). cf. test_chasse_*."""
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


def _deux_runs(session):
    """Le run servi + un run précédent DISTINCT (pour le self-join des paliers)."""
    from sqlalchemy import text

    from labuse import runs
    servi = runs.current()
    autre = session.execute(text(
        "SELECT run_id FROM p_score_v2_runs WHERE run_id <> :s ORDER BY computed_at DESC LIMIT 1"),
        {"s": servi}).scalar()
    if not autre:
        pytest.skip("un seul run en base — pas de précédent pour comparer")
    return servi, autre


def test_mesures_run_concluent_toutes_contre_le_schema_reel():
    """GARDE-FOU DEPLOY-AUTONOMIE — chaque mesure de controler_run doit CONCLURE contre la vraie base.
    Rouge sur l'ancien code (colonnes inexistantes → None). Le candidat sert ici de stand-in : on
    valide la RÉSOLUTION de schéma, pas une valeur métier (le candidat réel n'existe qu'au run de nuit)."""
    from labuse import jobs_impl
    with app_session() as s:
        candidat, precedent = _deux_runs(s)
        m = jobs_impl._mesures_run(s, candidat, precedent)
    # les 6 mesures chiffrées DOIVENT être des entiers (une seule à None = un contrôle qui ne conclut pas)
    for cle in ("comptes_parcelles", "comptes_precedent", "copro_actionnables",
                "rouge_actionnables", "paliers_total", "paliers_change"):
        assert isinstance(m.get(cle), int), f"{cle} = {m.get(cle)!r} (devrait être un int ; régression schéma ?)"
    assert m["paliers_total"] > 0, "aucune parcelle commune — self-join cassé"
    assert m["run_complet"] is True, f"complétude du run servi KO : {m.get('run_complet_motif')}"
    # cohérence : lue du banc (faux_client + erreurs_lecteur) — int si un passage existe
    assert m["coherence_ecarts"] is None or isinstance(m["coherence_ecarts"], int)
    assert m["coherence_erreurs"] is None or isinstance(m["coherence_erreurs"], int)


def test_controler_run_cable_les_mesures_reelles():
    """Les mesures réelles alimentent bien le verdict : un run propre (copro/rouge = 0) passe ; le même
    avec une copropriété en palier actionnable (doctrine E-010) est REFUSÉ. Prouve le câblage mesure→verdict."""
    from labuse import autonomie, jobs_impl
    with app_session() as s:
        candidat, precedent = _deux_runs(s)
        m = jobs_impl._mesures_run(s, candidat, precedent)
    base = dict(m, manifeste_present=True, coherence_ecarts=0, coherence_erreurs=0,
                comptes_precedent=m["comptes_parcelles"], copro_actionnables=0, rouge_actionnables=0,
                paliers_change=0)
    assert autonomie.controler_run(base, palier_delta_max_pct=3.0).ok is True
    casse = dict(base, copro_actionnables=393)
    assert autonomie.controler_run(casse, palier_delta_max_pct=3.0).ok is False
