"""Cohérence du RUN SERVI (M6 post-merge) — un seul monde, partout.

Trois surfaces doivent raconter le même run et divergent silencieusement sinon
(vécu deux fois : q_v2 codé en dur au M5, tuiles q_v4_m6a vs attente q_v5_m6b au M6) :

1. le backend : ``Q_A_RUN_LABEL`` (source de vérité unique) ;
2. le frontend : ``SOURCE`` (frontend/src/lib/api.ts) + le BUNDLE construit (dist) ;
3. les tuiles : ``mvt_meta.run_label`` écrit par ``labuse build-mvt``.

Ces tests pètent à la MOINDRE divergence — la bascule d'un run servi n'est finie que
quand les trois sont alignés (constante + rebuild front + build-mvt).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from labuse.scoring.score_v_constants import Q_A_RUN_LABEL

ROOT = Path(__file__).resolve().parents[1]


def test_front_source_aligne_sur_le_run_servi():
    """frontend/src/lib/api.ts : SOURCE doit être IDENTIQUE à Q_A_RUN_LABEL."""
    api_ts = (ROOT / "frontend" / "src" / "lib" / "api.ts").read_text(encoding="utf-8")
    m = re.search(r"export const SOURCE = '([^']+)'", api_ts)
    assert m, "constante SOURCE introuvable dans frontend/src/lib/api.ts"
    assert m.group(1) == Q_A_RUN_LABEL, (
        f"front SOURCE={m.group(1)!r} ≠ backend Q_A_RUN_LABEL={Q_A_RUN_LABEL!r} — "
        "bascule de run incomplète (mettre à jour les DEUX constantes + npm run build)")


def test_bundle_front_construit_sur_le_run_servi():
    """Le bundle dist/ doit contenir le label servi (sinon : npm run build oublié)."""
    assets = list((ROOT / "frontend" / "dist" / "assets").glob("*.js"))
    if not assets:
        pytest.skip("frontend/dist absent (front non construit sur cette machine)")
    if not any(Q_A_RUN_LABEL in a.read_text(encoding="utf-8", errors="ignore") for a in assets):
        pytest.fail(
            f"le bundle frontend/dist ne contient pas le run servi {Q_A_RUN_LABEL!r} — "
            "bundle périmé : relancer `npm run build` après la bascule")


def test_tuiles_mvt_materialisees_sur_le_run_servi():
    """mvt_meta.run_label (écrit par build-mvt) doit valoir Q_A_RUN_LABEL.

    ⚠ Le conftest redirige la session vers la base de TEST (labuse_test), qui ne porte
    pas les tuiles : on interroge donc la base APPLICATIVE (celle d'AVANT redirection,
    exposée par conftest._APP_URL, sinon LABUSE_TEST_APP_URL/défaut) — c'est elle qui
    sert les tuiles et doit être cohérente."""
    import os

    from sqlalchemy import create_engine, text

    app_url = (os.environ.get("LABUSE_APP_DATABASE_URL")          # posé par conftest
               or os.environ.get("LABUSE_DATABASE_URL",           # exécution hors pytest
                                 "postgresql+psycopg://labuse:labuse@localhost:5432/labuse"))
    try:
        eng = create_engine(app_url, future=True)
        with eng.connect() as c:
            if not c.execute(text("SELECT to_regclass('mvt_meta')")).scalar():
                pytest.skip("mvt_meta absente (build-mvt jamais lancé sur cette base)")
            mvt_label = c.execute(text(
                "SELECT value FROM mvt_meta WHERE key = 'run_label'")).scalar()
    except Exception as exc:  # noqa: BLE001 - base indisponible = skip, pas un échec
        pytest.skip(f"base applicative indisponible ({type(exc).__name__}) — cohérence mvt non vérifiable ici")
    assert mvt_label == Q_A_RUN_LABEL, (
        f"tuiles mvt_parcels matérialisées sur {mvt_label!r} ≠ run servi {Q_A_RUN_LABEL!r} — "
        "relancer `labuse build-mvt` après la bascule")
