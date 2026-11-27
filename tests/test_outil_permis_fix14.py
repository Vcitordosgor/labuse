"""OUTIL-PERMIS-FIX-14 — LOT 0 : le FILET, écrit AVANT le correctif (il doit échouer maintenant).

Relecture-permis-7, point 3 : la table dérivée `p_model_permits` est PÉRIMÉE — `date_autorisation`
porte parfois la date de DÉPÔT brute (ex. 97415000DP0016 : 28/08/2023 au lieu du 26/02/2020 réel) et
il lui manque des couples. La rubrique « Bâti » de la fiche lit cette table pour l'avertissement
« un permis autorisé après le survol LiDAR a pu changer le bâti » → elle annonce « permis du
28/08/2023 postérieur au survol » alors que le permis réel (sitadel_permits) est du 26/02/2020,
ANTÉRIEUR au survol : avertissement FAUX.

Le correctif (LOT 1) fait lire la SOURCE `sitadel_permits.date` par une FONCTION UNIQUE
`permis_classe.permis_autorise_apres`. Ce filet verrouille son contrat : la date STALE de
`p_model_permits` ne doit JAMAIS ressortir ; seule la date d'autorisation source compte.
"""
from __future__ import annotations

import ast as _ast
import datetime as dt
import io as _io
import re as _re
import tokenize as _tokenize
from pathlib import Path

import pytest
from sqlalchemy import text

_SRC = Path(__file__).resolve().parents[1] / "src" / "labuse"


# ───────────────────────────── test structurel (non-db, dans le hook) ─────────────────────────────
# OUTIL-PERMIS-FIX-14 — relecture-permis-7 (point 3) : `p_model_permits` est PÉRIMÉE. AUCUN lecteur
# ne doit en tirer une date ou un état de permis pour l'AFFICHER à l'utilisateur ; les seuls usages
# légitimes qui restent sont internes (features du modèle P, garde de fraîcheur, rattachement/flag
# non daté, construction de la table, registre). Chaque usage vise une FONCTION autorisée NOMMÉMENT
# avec sa raison. Un usage hors liste (nouveau lecteur, ou le caveat §Bâti qui y reviendrait) échoue ;
# une exception périmée (sans usage réel) échoue aussi. Même mécanique AST+tokenize que FIX-10/12.
#: USAGES de `p_model_permits` : (chemin relatif à src/labuse, FONCTION) → RAISON. `<module>` = niveau module.
LECTEURS_P_MODEL_PERMITS: dict[tuple[str, str], str] = {
    # ── INTERNE scoring (modèle P / q_v2) — features, JAMAIS une date affichée (LOT 2, à reconstruire avant q_v25) ──
    ("scoring/p_model/sql.py", "build_permits"): "scoring — CONSTRUIT la table (date_autorisation = sitadel.date::date).",
    ("scoring/p_model/sql.py", "build_dataset"): "scoring — features du modèle P (comptes/récence de permis as-of).",
    ("scoring/p_model/ext_sql.py", "build_ext_dataset"): "scoring — features étendues du modèle P.",
    ("scoring/p_v2/qv12.py", "charger_censoring"): "scoring q_v2 — censure as-of (feature).",
    ("scoring/p_v2/qv12.py", "_permis_annee"): "scoring q_v2 — année de permis (feature).",
    ("scoring/p_v2/qv14.py", "<module>"): "scoring q_v2 — gabarit SQL de features permis.",
    ("scoring/p_v2/qv14.py", "_colonnes_pc_pm"): "scoring q_v2 — colonnes PC/PM (features).",
    ("scoring/p_v2/monitoring.py", "run_monitor"): "scoring q_v2 — monitoring (non servi au client).",
    ("scoring/p_v2/pipeline.py", "check_permits_fraicheur"): "scoring q_v2 — GARDE de fraîcheur p_model_permits vs Sitadel.",
    ("scoring/backtest.py", "mutation_lift"): "scoring — backtest offline (prédicat d'existence PC).",
    # ── RATTACHEMENT non daté (LOT 2 — pas une date affichée ; sensible au linkage, pas à la date périmée) ──
    ("ingestion/defisc_fenetres.py", "<module>"): "defisc — rattachement (idu, permit_id, type=PC) puis JOIN Sitadel pour le DAACT.",
    ("ingestion/dvf_prix_neuf.py", "<module>"): "prix neuf — rattachement PC puis JOIN Sitadel pour le DAACT.",
    # OUTIL-PERMIS-FIX-16 (LOT 6) — api/app.py ne lit PLUS p_model_permits : le drapeau permis_pro (pro_pc
    # CTE) et sa garde _permits_ready lisent la SOURCE sitadel_permits. Les deux entrées app.py sont retirées.
    # ── REGISTRE — libellé de table ──
    ("registre/tables.py", "<module>"): "registre — libellé descriptif de la table (documentation).",
}
_PMP = _re.compile(r"\bp_model_permits\b")


def _lignes_a_ignorer(txt: str, tree: _ast.Module) -> set[int]:
    """Lignes de COMMENTAIRE et de DOCSTRING — pas un usage de la table."""
    ignore: set[int] = set()
    try:
        for tok in _tokenize.generate_tokens(_io.StringIO(txt).readline):
            if tok.type == _tokenize.COMMENT:
                ignore.add(tok.start[0])
    except _tokenize.TokenError:
        pass
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.Module, _ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
            if node.body and isinstance(node.body[0], _ast.Expr) and \
                    isinstance(getattr(node.body[0], "value", None), _ast.Constant) and \
                    _ast.get_docstring(node, clean=False) is not None:
                v = node.body[0].value
                for ln in range(v.lineno, (v.end_lineno or v.lineno) + 1):
                    ignore.add(ln)
    return ignore


def _fonction_englobante(tree: _ast.Module, lineno: int) -> str:
    best = None
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and \
                node.lineno <= lineno <= (node.end_lineno or node.lineno):
            if best is None or node.lineno > best.lineno:
                best = node
    return best.name if best else "<module>"


def _usages_p_model_permits() -> set[tuple[str, str]]:
    trouves: set[tuple[str, str]] = set()
    for f in sorted(_SRC.rglob("*.py")):
        txt = f.read_text(encoding="utf-8")
        if not _PMP.search(txt):
            continue
        tree = _ast.parse(txt)
        ignore = _lignes_a_ignorer(txt, tree)
        rel = f.relative_to(_SRC).as_posix()
        for i, line in enumerate(txt.splitlines(), 1):
            if i not in ignore and _PMP.search(line):
                trouves.add((rel, _fonction_englobante(tree, i)))
    return trouves


def test_lot1_structurel_lecteurs_p_model_permits():
    """Aucun lecteur de `p_model_permits` hors `LECTEURS_P_MODEL_PERMITS` (intrus = nouveau lecteur,
    ou le caveat §Bâti qui y reviendrait) ; aucune exception périmée. Le caveat de la fiche §Bâti
    (`api/app.py::_potentiel_transformation_block`) ne doit PLUS y figurer — il lit Sitadel (FIX-14)."""
    usages = _usages_p_model_permits()
    intrus = sorted(u for u in usages if u not in LECTEURS_P_MODEL_PERMITS)
    perimes = sorted(u for u in LECTEURS_P_MODEL_PERMITS if u not in usages)
    assert not intrus, (
        "Lecteur de p_model_permits hors LECTEURS_P_MODEL_PERMITS : "
        + "; ".join(f"{r}::{fn}" for r, fn in intrus)
        + " — lire la date d'autorisation à la SOURCE via permis_classe.permis_autorise_apres / "
        "date_autorisation_sql (sitadel_permits), ou inscrire l'usage NOMMÉMENT avec sa raison.")
    assert not perimes, (
        "Exception(s) PÉRIMÉE(s) dans LECTEURS_P_MODEL_PERMITS : "
        + "; ".join(f"{r}::{fn}" for r, fn in perimes) + " — retirer l'entrée.")

    # garde-fou explicite : le caveat §Bâti n'est plus un lecteur de la table périmée.
    assert ("api/app.py", "_potentiel_transformation_block") not in usages


def _seed_parcelle(db, idu):
    wkt = "POLYGON((55.30 -21.0,55.301 -21.0,55.301 -21.001,55.30 -21.001,55.30 -21.0))"
    db.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) "
        "VALUES (:i,'Survolville','DP','0016', ST_GeomFromText(:w,4326), "
        " ST_Transform(ST_GeomFromText(:w,4326),2975), 500, ST_Centroid(ST_GeomFromText(:w,4326)), "
        " ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"), {"i": idu, "w": wkt}).scalar()


@pytest.mark.db
def test_lot0_caveat_survol_lit_sitadel_pas_la_table_perimee(db_session):
    """Témoin DP0016 — permis réel autorisé 26/02/2020 (ANTÉRIEUR au survol 18/08/2023), mais la table
    périmée `p_model_permits` porte 28/08/2023 (postérieur). L'avertissement « permis postérieur au
    survol » doit valoir None (le permis est antérieur). ÉCHOUE avant LOT 1 (la fonction unique
    `permis_classe.permis_autorise_apres` n'existe pas encore ; l'ancien code lisait 28/08/2023)."""
    from labuse import permis_classe
    s = db_session
    idu = "97415000DP0016"
    _seed_parcelle(s, idu)
    # permis RÉEL (source Sitadel) : autorisé 26/02/2020, rattaché à la parcelle via idu_codes
    s.execute(text("DELETE FROM sitadel_permits WHERE permit_id = '97441520A0030'"))
    s.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, idu_codes, commune, raw) "
        "VALUES ('97441520A0030','PC','2020-02-26', CAST(:i AS jsonb),'Survolville','{}'::jsonb)"),
        {"i": '["%s"]' % idu})
    # table PÉRIMÉE : une date d'autorisation FAUSSE (28/08/2023) — ne doit JAMAIS ressortir
    s.execute(text("CREATE TABLE IF NOT EXISTS p_model_permits "
                   "(permit_id varchar(64), idu text, type varchar(8), date_autorisation date)"))
    s.execute(text("DELETE FROM p_model_permits WHERE idu = :i"), {"i": idu})
    s.execute(text("INSERT INTO p_model_permits (permit_id, idu, type, date_autorisation) "
                   "VALUES ('97441520A0030', :i, 'PC', '2023-08-28')"), {"i": idu})

    survol = dt.date(2023, 8, 18)
    # la fonction unique lit la SOURCE : le seul permis (26/02/2020) est antérieur au survol → None
    assert permis_classe.permis_autorise_apres(s, idu, survol) is None

    # contrôle positif : un VRAI permis postérieur au survol (10/01/2024) ressort bien
    s.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, idu_codes, commune, raw) "
        "VALUES ('97441520A9999','PC','2024-01-10', CAST(:i AS jsonb),'Survolville','{}'::jsonb)"),
        {"i": '["%s"]' % idu})
    assert permis_classe.permis_autorise_apres(s, idu, survol) == dt.date(2024, 1, 10)
