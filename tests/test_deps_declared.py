"""GARDE ANTI « DÉPENDANCE IMPLICITE » (post-incident argon2, 23/07/2026).

3 fois une dépendance directement importée par le code n'était PAS déclarée dans
pyproject.toml (anthropic, certifi, argon2-cffi) : le serveur ne « marchait » qu'à la
faveur d'une présence transitive fragile — et le jour où argon2-cffi manquait, la
remédiation de schéma échouait EN SILENCE (comptes/cloison non matérialisés en prod).

Ce test échoue si un import tiers du code (src/labuse + scripts) ne correspond à AUCUNE
distribution déclarée dans pyproject.toml (cœur OU groupe optionnel : ai / ml / dev).
Il ne dépend pas de la base — il lit l'AST et les métadonnées de paquets.
"""
from __future__ import annotations

import ast
import pathlib
import sys
import tomllib
from importlib.metadata import packages_distributions

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_SCANNED = ("src/labuse", "scripts")

# import top-level → distribution (les cas non triviaux ; sinon on tente packages_distributions
# puis l'identité). Normalisés plus bas (minuscule, « _ » → « - »).
_ALIASES = {
    "cv2": "opencv-python-headless",
    "yaml": "PyYAML",
    "dotenv": "python-dotenv",
    "sklearn": "scikit-learn",
    "argon2": "argon2-cffi",
    "shapefile": "pyshp",
    "fpdf": "fpdf2",
    "segmentation_models_pytorch": "segmentation-models-pytorch",
    "PIL": "pillow",
}


def _norm(name: str) -> str:
    return name.lower().replace("_", "-").split("[")[0].strip()


def _declared_dists() -> set[str]:
    pp = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    reqs = list(pp.get("dependencies", []))
    for grp in pp.get("optional-dependencies", {}).values():
        reqs += grp
    out = set()
    for r in reqs:
        # « paquet>=x », « paquet[extra]>=x » → nom du paquet normalisé
        out.add(_norm(r.split(">=")[0].split("==")[0].split("<")[0]))
    return out


def _third_party_imports() -> set[str]:
    stdlib = set(sys.stdlib_module_names)
    found: set[str] = set()
    for rel in _SCANNED:
        for p in (_ROOT / rel).rglob("*.py"):
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    for a in n.names:
                        found.add(a.name.split(".")[0])
                elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                    found.add(n.module.split(".")[0])
    return {m for m in found if m and m not in stdlib and m != "labuse"}


def _dist_for(mod: str) -> str:
    if mod in _ALIASES:
        return _ALIASES[mod]
    dists = packages_distributions().get(mod)
    return dists[0] if dists else mod   # identité en dernier recours


def test_tous_les_imports_du_code_sont_declares():
    declared = _declared_dists()
    undeclared = {}
    for mod in sorted(_third_party_imports()):
        if _norm(_dist_for(mod)) not in declared:
            undeclared[mod] = _dist_for(mod)
    assert not undeclared, (
        "Imports tiers NON déclarés dans pyproject.toml (cœur ou groupe optionnel) :\n"
        + "\n".join(f"  import '{m}'  →  ajouter la distribution '{d}'" for m, d in undeclared.items())
        + "\n→ déclare-les (cœur si le serveur en a besoin, sinon groupe ml/ai) : "
          "une dépendance implicite finit toujours par mordre en prod."
    )
