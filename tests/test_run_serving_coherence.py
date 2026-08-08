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


def test_served_run_fichier_est_la_source_unique():
    """M31 (arbitrage Vic) : config/served_run.txt est le POINT DE VÉRITÉ UNIQUE versionné du run
    servi. Le backend (Q_A_RUN_LABEL) DOIT le lire — pas un littéral codé, pas une var d'env. Ce
    test lie la racine : si le fichier et Q_A_RUN_LABEL divergent, la plomberie est cassée."""
    f = ROOT / "config" / "served_run.txt"
    valeur = next(l.strip() for l in f.read_text(encoding="utf-8").splitlines()
                  if l.strip() and not l.strip().startswith("#"))
    assert valeur == Q_A_RUN_LABEL, (
        f"config/served_run.txt={valeur!r} ≠ Q_A_RUN_LABEL={Q_A_RUN_LABEL!r} — le backend ne lit "
        "pas le point de vérité versionné (ou un override LABUSE_SERVED_RUN traîne dans l'env de test)")


def test_front_source_lit_le_run_injecte_sans_repli_code_en_dur():
    """M-Q P2-70 : frontend/src/lib/api.ts — SOURCE lit VITE_RUN_LABEL (injecté au build depuis
    config/served_run.txt par vite.config.ts) avec un repli VIDE. Plus de run codé en dur : un
    littéral figé servirait SILENCIEUSEMENT l'ancien run après une bascule si l'injection manquait
    (front sur l'ancien, backend sur le nouveau → listes vides, aucun message). La cohérence du run
    RÉEL est vérifiée sur le BUNDLE (test_bundle_front_construit_sur_le_run_servi), et l'absence
    d'injection déclenche une garde VISIBLE au démarrage (main.tsx) — pas un run muet."""
    api_ts = (ROOT / "frontend" / "src" / "lib" / "api.ts").read_text(encoding="utf-8")
    m = re.search(r"export const SOURCE = import\.meta\.env\.VITE_RUN_LABEL \?\? '([^']*)'", api_ts)
    assert m, ("SOURCE doit valoir `import.meta.env.VITE_RUN_LABEL ?? '...'` "
               "dans frontend/src/lib/api.ts")
    assert m.group(1) == "", (
        f"repli SOURCE={m.group(1)!r} — attendu chaîne VIDE (M-Q P2-70). Un run codé en dur en repli "
        "sert l'ancien run après une bascule si VITE_RUN_LABEL n'est pas injecté ; le repli vide + la "
        "garde de démarrage rendent l'erreur franche au lieu de servir un mauvais run.")
    # garde de démarrage : main.tsx refuse de booter sur un run vide (écran « run non configuré »)
    main_tsx = (ROOT / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    assert "SOURCE" in main_tsx and "RunNonConfigure" in main_tsx, (
        "main.tsx doit importer SOURCE et garder le démarrage (RunNonConfigure) si SOURCE est vide — "
        "sinon un build sans injection démarrerait sur un run indéterminé sans le dire.")


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


def test_mvt_run_label_cible_distante():
    """Pré-vol M7 P2 — la MÊME cohérence, vérifiable contre une CIBLE DISTANTE (le geste M7 vs VPS) :
    si LABUSE_QA_TARGET est défini, on interroge /map/tiles/meta de la cible (l'endpoint expose
    mvt_meta.run_label) au lieu de la base locale. Sans l'env : skip — comportement par défaut inchangé."""
    import json
    import os
    import urllib.request

    target = os.environ.get("LABUSE_QA_TARGET")
    if not target:
        pytest.skip("LABUSE_QA_TARGET non défini — vérification distante réservée au geste M7")
    # M7 : cible en LABUSE_ENV=production → login applicatif (cookie) via LABUSE_QA_PASSWORD,
    # et rideau Caddy éventuel via LABUSE_QA_BASIC (même contrat que qa/golden_check.py).
    import base64
    import http.cookiejar
    import ssl
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx),
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    basic = os.environ.get("LABUSE_QA_BASIC")
    if basic:
        opener.addheaders = [("Authorization", "Basic " + base64.b64encode(basic.encode()).decode())]
    pw = os.environ.get("LABUSE_QA_PASSWORD")
    if pw:
        try:
            opener.open(urllib.request.Request(f"{target.rstrip('/')}/login", method="POST",
                        data=json.dumps({"password": pw}).encode(),
                        headers={"Content-Type": "application/json"}), timeout=15)
        except urllib.error.HTTPError:
            pass    # le login répond 303 → urllib suit vers une page protégée ; le cookie est déjà posé
    with opener.open(f"{target.rstrip('/')}/map/tiles/meta", timeout=15) as resp:
        meta = json.loads(resp.read().decode("utf-8"))
    if meta.get("run_label") is None:
        pytest.skip("cible sans tuiles construites (build-mvt jamais lancé)")
    assert meta["run_label"] == Q_A_RUN_LABEL, (
        f"cible distante sur {meta['run_label']!r} ≠ run servi attendu {Q_A_RUN_LABEL!r} — build-mvt à relancer sur la cible")
