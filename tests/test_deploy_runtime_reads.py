"""POSTDEPLOY-1027 (P2) — GARDE : aucun fichier VERSIONNÉ sous un dossier exclu du déploiement
(`deploy/scripts/deploy_app.sh`) n'est lu à l'exécution par `src/labuse`.

Incident : `reservoirs.csv` vivait sous `docs/` (exclu du rsync) mais était lu au moment de générer
les PDF → en prod le fichier était absent, les pieds « Sources : » sortaient en ids bruts. Le code
ne tombait pas en erreur (repli silencieux), donc rien ne le signalait. Même piège pour `moteurs.csv`
(Circuit « À faire ») et `SCHEMAS.csv` (verrou G2). Tous trois déplacés sous `config/` (déployé).

Ce test reconstruit, par analyse AST, le chemin de chaque lecture de fichier de `src/labuse`
(`open(...)` en lecture, `Path(...).open()/.read_text()/.read_bytes()`, y compris via une constante
de module), le résout en chemin dépôt, et échoue si ce chemin est À LA FOIS versionné (git) ET sous
un dossier exclu — c'est exactement la combinaison « présent en dev, absent en prod ». Les fichiers
seulement ÉCRITS (sorties sous `outputs/`, `reports/`…) et ceux créés au runtime (non versionnés) ne
sont pas concernés : seule une lecture d'un fichier livré-en-dev-mais-pas-en-prod est un bug.
"""
from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src" / "labuse"
_DEPLOY = _REPO / "deploy" / "scripts" / "deploy_app.sh"


def _dossiers_exclus() -> list[str]:
    """Les chemins `--exclude /xxx` de deploy_app.sh (relatifs à la racine), hors fichiers .env."""
    txt = _DEPLOY.read_text(encoding="utf-8")
    exclus = re.findall(r"--exclude\s+/([A-Za-z0-9_./]+)", txt)
    # on ne garde que les RÉPERTOIRES (les deux served_*.* sont des fichiers prod-owned, non versionnés)
    return [e for e in exclus if not e.endswith(".json") and not e.endswith(".txt")]


def _tracked() -> set[str]:
    out = subprocess.run(["git", "-C", str(_REPO), "ls-files"],
                         capture_output=True, text=True, check=True).stdout
    return set(out.splitlines())


def _sous_dossier_exclu(relpath: str, exclus: list[str]) -> str | None:
    for ex in exclus:
        if relpath == ex or relpath.startswith(ex + "/"):
            return ex
    return None


def _resoudre(expr: ast.AST, pyfile: Path) -> str | None:
    """Reconstruit un chemin dépôt-relatif depuis une expression AST, ou None si non statique.
    Formes gérées : `Path(__file__)....parents[N] / "a" / "b"` et chaîne littérale relative "a/b"."""
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        s = expr.value
        return s if not s.startswith("/") else None            # littéral relatif seulement
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Div):
        gauche = _resoudre(expr.left, pyfile)
        if gauche is None or not isinstance(expr.right, ast.Constant):
            return None
        return f"{gauche}/{expr.right.value}"
    # `...parents[N]` → N niveaux au-dessus du PARENT du fichier, relatif à la racine du dépôt
    if isinstance(expr, ast.Subscript):
        val = expr.value
        if (isinstance(val, ast.Attribute) and val.attr == "parents"
                and isinstance(expr.slice, ast.Constant) and isinstance(expr.slice.value, int)):
            rel = pyfile.relative_to(_REPO).parts           # ex. ('src','labuse','exports','pieds.py')
            coupe = expr.slice.value + 1                      # parents[0] = dossier parent immédiat
            base = rel[:-coupe] if coupe <= len(rel) else ()
            return "/".join(base)                             # '' = racine du dépôt
    return None


def _chemins_lus(pyfile: Path) -> list[tuple[int, str]]:
    """Chemins dépôt-relatifs effectivement OUVERTS EN LECTURE dans le fichier (ligne, chemin)."""
    tree = ast.parse(pyfile.read_text(encoding="utf-8"))
    # 1er passage : nom de variable → chemin reconstruit (constantes de module/fonction)
    noms: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            chemin = _resoudre(node.value, pyfile)
            if chemin is not None:
                noms[node.targets[0].id] = chemin

    def _cible(arg: ast.AST) -> str | None:
        if isinstance(arg, ast.Name) and arg.id in noms:
            return noms[arg.id]
        return _resoudre(arg, pyfile)

    lus: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        # open(path[, mode]) — lecture si le mode ne contient pas w/a/x/+
        if isinstance(f, ast.Name) and f.id == "open" and node.args:
            mode = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else "r"
            if not any(c in str(mode) for c in "wax+"):
                c = _cible(node.args[0])
                if c:
                    lus.append((node.lineno, c))
        # path.open(...) / path.read_text() / path.read_bytes()
        elif isinstance(f, ast.Attribute) and f.attr in ("read_text", "read_bytes", "open"):
            if f.attr == "open":
                mode = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else "r"
                if any(c in str(mode) for c in "wax+"):
                    continue
            c = _cible(f.value)
            if c:
                lus.append((node.lineno, c))
    return lus


def test_aucune_lecture_runtime_sous_un_dossier_exclu_du_deploiement():
    exclus = _dossiers_exclus()
    assert "docs" in exclus and "reports" in exclus, "deploy_app.sh : liste d'exclusions non reconnue"
    tracked = _tracked()
    coupables: list[str] = []
    for py in _SRC.rglob("*.py"):
        for ligne, chemin in _chemins_lus(py):
            chemin = chemin.lstrip("/")
            ex = _sous_dossier_exclu(chemin, exclus)
            if ex and chemin in tracked:
                rel = py.relative_to(_REPO)
                coupables.append(f"{rel}:{ligne} lit « {chemin} » (versionné, sous « {ex}/ » exclu du déploiement)")
    assert not coupables, (
        "Des fichiers versionnés sous un dossier exclu de deploy_app.sh sont lus à l'exécution — "
        "ils seront ABSENTS en prod. Déplace-les sous config/ :\n  " + "\n  ".join(coupables))
