"""GARDE-FOU H1 (hygiène déploiement, 28/08/2026) — la version du client Anthropic est FIGÉE.

Post-incident 27/08 : le venv du VPS portait `anthropic==1.1.0`, incompatible (refuse le paramètre
`temperature`), alors que le code exige la lignée 0.116.0. Résultat : le Copilote tombait en mode
DÉGRADÉ SILENCIEUX (« service d'analyse indisponible ») sans erreur visible — une heure de debug.

Ce test rend l'incident IMPOSSIBLE À REPRODUIRE EN SILENCE :
  1. le pin dans pyproject.toml [ai] doit être EXACT (`anthropic==X.Y.Z`, jamais `>=`/plage) — sinon
     `pip install -e .[ai]` peut réinstaller une version au hasard au prochain deploy ;
  2. si anthropic est installé, la version installée doit être EXACTEMENT celle du pin.

Il ne dépend pas de la base ni du réseau (lit le TOML + les métadonnées de paquet installé).
"""
from __future__ import annotations

import pathlib
import re
import tomllib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_PYPROJECT = _ROOT / "pyproject.toml"


def _pin_anthropic() -> str:
    """La spec d'anthropic déclarée dans pyproject.toml [ai] (ex. 'anthropic==0.116.0')."""
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    ai = data["project"]["optional-dependencies"]["ai"]
    specs = [s for s in ai if _norm(s) == "anthropic"]
    assert specs, "anthropic doit être déclaré dans pyproject.toml [project.optional-dependencies].ai"
    return specs[0]


def _norm(spec: str) -> str:
    return re.split(r"[=<>!~ \[]", spec, maxsplit=1)[0].strip().lower()


def test_le_pin_anthropic_est_exact():
    """Le pin doit épingler UNE version exacte — pas de `>=` ni de plage qui rouvre la porte au 1.1.0."""
    spec = _pin_anthropic()
    m = re.fullmatch(r"anthropic==(\d+\.\d+\.\d+)", spec)
    assert m, (
        f"anthropic doit être figé à une version EXACTE dans pyproject.toml [ai], trouvé « {spec} ». "
        "Un `>=` a laissé le VPS installer 1.1.0 (incompatible, Copilote dégradé en silence). "
        "Écris `anthropic==X.Y.Z`."
    )


def test_la_version_installee_correspond_au_pin():
    """La version RÉELLEMENT installée doit être celle du pin — sinon échec BRUYANT (jamais silencieux)."""
    spec = _pin_anthropic()
    attendue = spec.split("==", 1)[1]
    try:
        from importlib.metadata import version
        installee = version("anthropic")
    except Exception:
        pytest.skip("anthropic non installé (extra [ai] absent — provider stub) : rien à comparer")
    assert installee == attendue, (
        f"VERSION ANTHROPIC INATTENDUE : installée={installee}, attendue={attendue} (pin pyproject [ai]). "
        "C'est EXACTEMENT l'incident du 27/08 (venv VPS en 1.1.0 → Copilote dégradé SILENCIEUX). "
        "Réinstalle la bonne version : pip install -e '.[ai]' (ou anthropic==" + attendue + ")."
    )
