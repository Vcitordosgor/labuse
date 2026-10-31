"""COHERENCE-HOOK-1 — socle de la suite de cohérence (tests/coherence/).

La suite interroge la base APPLICATIVE réelle (le run SERVI, le scoring, DVF, PLU…), pas la base de
test vierge. On lit donc `LABUSE_APP_DATABASE_URL` (posée par le conftest racine = la base d'origine),
en LECTURE SEULE, et on rebranche l'engine GLOBAL de l'app dessus le temps de chaque test — car
certains points de service (ex. l'endpoint d'estimation `radar_annonce_estimation`) ouvrent LEUR
PROPRE `session_scope()` (engine global), que le conftest racine pointe sinon sur `labuse_test`.

Base injoignable :
  • par défaut (dev, CI) → SKIP (on ne peut pas vérifier la cohérence sans la base réelle) ;
  • si `LABUSE_COHERENCE_REQUIRE_DB` est posé (le HOOK et le banc de nuit le posent) → ÉCHEC ROUGE,
    JAMAIS un skip silencieux : la dérive doit être impossible à ignorer.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

# Les 12 témoins du lot A (docs/audit-2026-11/nu-1/A) — mêmes IDU que test_sdp_unique_coherence.
# DR0042 est « disparue » (fiche de courtoisie, 404 sur l'analyse) : la plupart des faits ne s'y
# appliquent pas ; les tests l'ignorent proprement quand la fiche n'existe pas.
TEMOINS = [
    "97411000IN0347", "97411000IE0241", "97411000HC0139", "97424000AE0050",
    "97424000AM0893", "97421000AB0133", "97411000AO0753", "97411000EY0173",
    "97417000BI0076", "97411000AB0785", "97411000HN0074", "97411000DR0042",
]

_REQUIRE = bool(os.environ.get("LABUSE_COHERENCE_REQUIRE_DB"))


def _app_url() -> str:
    return (os.environ.get("LABUSE_APP_DATABASE_URL")
            or os.environ.get("LABUSE_DATABASE_URL",
                              "postgresql+psycopg://labuse:labuse@localhost:5432/labuse"))


def _absente(message: str):
    """Base réelle injoignable : ÉCHEC si le hook l'exige, sinon SKIP (jamais en silence côté hook)."""
    if _REQUIRE:
        pytest.fail("COHÉRENCE NON VÉRIFIÉE — base locale injoignable alors que "
                    "LABUSE_COHERENCE_REQUIRE_DB est posé : " + message)
    pytest.skip("base applicative réelle injoignable — cohérence non vérifiable ici : " + message)


@pytest.fixture(scope="session")
def app_engine():
    """Engine sur la base APPLICATIVE réelle (run servi). Connexion éprouvée une fois."""
    from labuse.db import make_engine
    url = _app_url()
    try:
        eng = make_engine(url=url)
        with eng.connect() as c:
            # Garde : la base doit porter le run RÉSIDUEL servi (sinon ce n'est pas la base attendue).
            seq = c.execute(text("SELECT run_seq FROM residuel_runs WHERE is_served")).scalar()
            if not seq:
                _absente("aucun run résiduel servi (residuel_runs.is_served vide)")
    except pytest.skip.Exception:
        raise
    except pytest.fail.Exception:
        raise
    except Exception as exc:  # noqa: BLE001
        _absente(f"{type(exc).__name__}: {exc}")
    return eng


@pytest.fixture(autouse=True)
def _bind_app_db(app_engine):
    """Rebranche l'engine GLOBAL de l'app sur la base réelle le temps du test (points de service qui
    ouvrent leur propre session_scope), et pointe aussi l'ENV (hérité par un éventuel sous-processus
    « spawn »). Restauré ensuite — les autres familles de tests retrouvent `labuse_test`."""
    from labuse import db as db_mod
    anc_eng, anc_sess = db_mod._engine, db_mod._Session
    anc_url = os.environ.get("LABUSE_DATABASE_URL")
    db_mod._engine, db_mod._Session = app_engine, None
    os.environ["LABUSE_DATABASE_URL"] = str(app_engine.url)
    try:
        yield
    finally:
        db_mod._engine, db_mod._Session = anc_eng, anc_sess
        if anc_url is None:
            os.environ.pop("LABUSE_DATABASE_URL", None)
        else:
            os.environ["LABUSE_DATABASE_URL"] = anc_url


@pytest.fixture
def app_session(app_engine):
    """Session LECTURE SEULE sur la base réelle (aucune écriture possible)."""
    s = sessionmaker(bind=app_engine, future=True)()
    s.execute(text("SET default_transaction_read_only = on"))
    try:
        yield s
    finally:
        s.rollback()
        s.close()


@pytest.fixture(scope="session")
def fiches(app_engine):
    """{idu: fiche} calculée UNE fois pour tous les tests (le point d'entrée de la FICHE,
    `_q_v2_fiche`, est coûteux). Une parcelle disparue (404) est absente du dict."""
    from labuse.api.app import _q_v2_fiche
    s = sessionmaker(bind=app_engine, future=True)()
    s.execute(text("SET default_transaction_read_only = on"))
    out: dict[str, dict] = {}
    try:
        for idu in TEMOINS:
            try:
                out[idu] = _q_v2_fiche(s, idu)
            except Exception:  # noqa: BLE001 — parcelle disparue / hors périmètre : non servie
                continue
    finally:
        s.rollback()
        s.close()
    if not out:
        _absente("aucune fiche témoin servie (base réelle sans les parcelles du lot A ?)")
    return out
