"""Verrous de la source unique des hypothèses de bilan (MANDAT_HYPOTHESES_BILAN, Vic 28/07/2026).

Même mécanique que les verrous de wording du mandat dette-tests : un écart futur casse la suite
PAR CONSTRUCTION — un changement de doctrine passe par une décision, pas en silence.

1. Le YAML (source unique) porte les valeurs AUDITÉES (audit O2 12/06/2026, `2c25746`) et
   `charger()` coïncide avec les défauts moteur sur les champs de coût.
2. Aucun appel ne construit `Hypotheses()` en direct hors `engine.py` (le `charger()` lui-même)
   et fixtures de test.
3. Aucune constante de coût de construction hors source : un nom contenant « cout » ne reçoit
   jamais de littéral numérique ≥ 100 dans `src/` hors `engine.py` (le 2100 de la calibration
   du 14/06 aurait été attrapé ici).
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "labuse"
ENGINE = SRC / "faisabilite" / "engine.py"

#: seuil STRICT (>) : les coûts de construction sont des centaines d'€/m² — les ratios,
#: pourcentages et divisions « / 100.0 » passent.
SEUIL_LITTERAL_COUT = 100.0
#: bornes de VALIDATION pydantic (ge/le/gt/lt) : des limites de saisie, pas des coûts.
_KWARGS_VALIDATION = {"ge", "le", "gt", "lt", "multiple_of"}


def test_yaml_porte_les_valeurs_auditees():
    """La source unique = fourchette auditée O2 ; charger() ≡ défauts moteur sur les coûts."""
    from labuse.faisabilite.engine import Hypotheses

    h, d = Hypotheses.charger(), Hypotheses()
    assert h.cout_construction_m2_bas == d.cout_construction_m2_bas == 2300.0
    assert h.cout_construction_m2_haut == d.cout_construction_m2_haut == 2800.0
    assert h.coef_plancher_habitable == d.coef_plancher_habitable == 1.15


def test_aucune_instanciation_directe_hypotheses():
    """`Hypotheses()` en direct = retour du double-chemin (fiche 216 k€ / copilote 449 k€)."""
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        if path == ENGINE:
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\bHypotheses\(\)", line):
                offenders.append(f"{path.relative_to(SRC.parent.parent)}:{i}: {line.strip()}")
    assert not offenders, (
        "Appel(s) Hypotheses() direct(s) hors engine.py — utiliser Hypotheses.charger() "
        "(source unique, mandat hypothèses bilan) :\n" + "\n".join(offenders))


def _valeurs_numeriques(node: ast.AST) -> list[float]:
    """Littéraux numériques d'un nœud, bornes de validation exclues (kwargs ge/le/gt/lt)."""
    out: list[float] = []

    def rec(n: ast.AST) -> None:
        if isinstance(n, ast.Constant):
            if isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
                out.append(float(n.value))
            return
        if isinstance(n, ast.Call):
            for a in n.args:
                rec(a)
            for kw in n.keywords:
                if kw.arg not in _KWARGS_VALIDATION:
                    rec(kw.value)
            return
        for child in ast.iter_child_nodes(n):
            rec(child)

    rec(node)
    return out


def _cout_offenders(tree: ast.AST, rel: str) -> list[str]:
    """Affectations / kwargs / clés de dict dont le nom contient « cout » et qui portent un
    littéral ≥ seuil. AST : les commentaires et docstrings ne déclenchent jamais."""
    found: list[str] = []

    def _flag(name: str, value_node: ast.AST, lineno: int) -> None:
        if "cout" not in name.lower():
            return
        gros = [v for v in _valeurs_numeriques(value_node) if v > SEUIL_LITTERAL_COUT]
        if gros:
            found.append(f"{rel}:{lineno}: {name} = {gros}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    _flag(tgt.id, node.value, node.lineno)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value:
            _flag(node.target.id, node.value, node.lineno)
        elif isinstance(node, ast.keyword) and node.arg:
            _flag(node.arg, node.value, getattr(node.value, "lineno", 0))
        elif isinstance(node, ast.Dict):
            for key, val in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    _flag(key.value, val, getattr(val, "lineno", 0))
        elif isinstance(node, ast.Tuple):
            strs = [e.value for e in node.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if any("cout" in s.lower() for s in strs if isinstance(s, str)):
                _flag(next(s for s in strs if "cout" in s.lower()), node,
                      getattr(node, "lineno", 0))
    return found


def test_aucune_constante_de_cout_hors_source():
    """Un littéral de coût de construction hors engine.py/YAML = re-création du bug 2100."""
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        if path == ENGINE:
            continue
        rel = str(path.relative_to(SRC.parent.parent))
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        offenders += _cout_offenders(tree, rel)
    assert not offenders, (
        "Constante(s) de coût hors source unique (fourchette YAML auditée / engine.py) — "
        "un coût dupliqué est la re-création du bug 2100 (mandat hypothèses bilan) :\n"
        + "\n".join(offenders))


def test_defauts_calculette_derives_de_la_source():
    """2500/21 gravés en dur sont morts : les défauts calculette DÉRIVENT de la source unique."""
    from labuse.faisabilite.bilan import (
        CALCULETTE_COUT_DEFAUT_M2,
        CALCULETTE_MARGE_FRAIS_DEFAUT_PCT,
    )
    from labuse.faisabilite.engine import Hypotheses

    h = Hypotheses.charger()
    assert CALCULETTE_COUT_DEFAUT_M2 == round((h.cout_construction_m2_bas
                                               + h.cout_construction_m2_haut) / 2) == 2550.0
    assert CALCULETTE_MARGE_FRAIS_DEFAUT_PCT == round(
        (h.marge_promoteur_pct + h.frais_annexes_pct) * 100) == 21.0


def test_score_e_derive_de_la_source():
    """score_e ne grave plus ses coûts : dérivés de la même source unique (2550/1.15/0.79)."""
    from labuse.ingestion.score_e import COEF_CA, COEF_PLANCHER, COUT_M2

    assert COUT_M2 == 2550.0
    assert COEF_PLANCHER == 1.15
    assert COEF_CA == 0.79
