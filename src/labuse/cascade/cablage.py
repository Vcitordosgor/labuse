"""M-B — garde de CÂBLAGE du scoring (bloquante).

Contrairement aux gardes de bascule (bruyantes, NON bloquantes : une source en retard peut être
servie avec sa mention), un câblage incohérent ne doit PAS servir du tout — il traduit une erreur
de programmation, jamais un état de donnée légitime. Cette garde REFUSE le démarrage / le run et
NOMME précisément la couche, la sévérité, la clé ou le kind fautif.

Quatre invariants (mesurés cohérents au 09/08/2026 — la garde verrouille, elle ne corrige pas) :

  1. YAML ↔ registry (P2-18) : toute couche de `cascade_rules.yaml` a son implémentation dans
     `REGISTRY`, et RÉCIPROQUEMENT. Une couche déclarée non implémentée = signal silencieusement
     absent (engine.py la SAUTE sans bruit) ; implémentée non déclarée = code jamais exécuté.
  2. Sévérités (P1-3/P2-19) : toute sévérité de l'enum a un multiplicateur en config — `info`
     INCLUS et == 0 (une sévérité ABSENTE de la config vaudrait ×1 par défaut, cf. opportunity.py
     `mult.get(sev, 1)` : ignorer ≠ mettre à zéro) ; toute sévérité citée au YAML est connue.
  3. bonus_keys (P1-3) : toute clé de bonus utilisée (params YAML + littéraux `bonus_key=`) existe
     en config (sinon `bonuses.get(key, 0)` la met silencieusement à 0).
  4. spatial_kinds (P2-30) : tout kind référencé au YAML existe réellement en base — vérifié
     UNIQUEMENT si une session est fournie (le `SELECT DISTINCT kind` coûte ~1,2 s : trop cher au
     boot de l'API à chaque worker, négligeable au lancement d'un run qui paie déjà la base).

Branchement (tranché sur mesure) : statique (1-3, ~0 ms, sans base) au BOOT de l'app ET au RUN ;
DB (4) au RUN seulement.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..config import cascade_rules, opportunity_weights
from ..enums import Severity
from .base import REGISTRY


class CablageError(RuntimeError):
    """Câblage scoring incohérent — refus de démarrer/scorer. Le message nomme le·s fautif·s."""


def _collect_yaml_values(node, key_substr: str) -> set[str]:
    """Valeurs (str, ou éléments str de listes) portées par une clé dont le NOM contient
    `key_substr`, en profondeur. Robuste aux clés non-str (maps à clés entières)."""
    out: set[str] = set()

    def walk(n):
        if isinstance(n, dict):
            for k, v in n.items():
                if isinstance(k, str) and key_substr in k:
                    if isinstance(v, str):
                        out.add(v)
                    elif isinstance(v, list):
                        out.update(x for x in v if isinstance(x, str))
                walk(v)
        elif isinstance(n, list):
            for x in n:
                walk(x)

    walk(node)
    return out


def _emitted_bonus_key_literals() -> set[str]:
    """Clés de bonus écrites en littéral `bonus_key="..."` dans le code des couches (best-effort,
    littéraux uniquement — les clés dynamiques `params["bonus_key"]` sont couvertes par le YAML)."""
    out: set[str] = set()
    layers_dir = Path(__file__).parent / "layers"
    for f in layers_dir.glob("*.py"):
        out.update(re.findall(r"""bonus_key\s*=\s*["'](\w+)["']""", f.read_text(encoding="utf-8")))
    return out


def check_cablage_scoring(session=None) -> dict:
    """Vérifie le câblage du scoring. LÈVE `CablageError` (message itemisé) au moindre écart.
    Renvoie un résumé `{...: "OK"}` quand tout passe. `session` fourni → vérifie aussi les kinds
    spatiaux en base (P2-30)."""
    problems: list[str] = []
    rules = cascade_rules()
    weights = opportunity_weights()

    # ── 1. YAML ↔ registry (les deux sens) ──────────────────────────────────────────────
    yaml_layers = {l["name"] for l in rules.get("layers", []) if isinstance(l, dict) and l.get("name")}
    reg = set(REGISTRY)
    for name in sorted(yaml_layers - reg):
        problems.append(f"[YAML↔registry] couche « {name} » déclarée dans cascade_rules.yaml mais "
                        f"ABSENTE du registry (non implémentée → engine la saute en silence).")
    for name in sorted(reg - yaml_layers):
        problems.append(f"[YAML↔registry] couche « {name} » implémentée (registry) mais NON déclarée "
                        f"dans cascade_rules.yaml (code jamais exécuté).")

    # ── 2. Sévérités (enum ↔ multiplicateurs, info==0, YAML ⊆ enum) ──────────────────────
    enum_sev = {s.value for s in Severity}
    mult = weights.get("severity_multipliers", {}) or {}
    for sev in sorted(enum_sev - set(mult)):
        problems.append(f"[sévérité] « {sev} » (enum Severity) SANS multiplicateur dans "
                        f"opportunity_weights.severity_multipliers → vaudrait ×1 par défaut "
                        f"(opportunity.py mult.get(sev,1)) au lieu d'être explicite.")
    if "info" in mult and mult["info"] != 0:
        problems.append(f"[sévérité] info doit valoir 0 (flag affiché, 0 point) — trouvé "
                        f"{mult['info']!r}. Une sévérité à zéro ≠ ignorée.")
    for sev in sorted(_collect_yaml_values(rules, "severity") - enum_sev):
        problems.append(f"[sévérité] « {sev} » citée dans cascade_rules.yaml mais INCONNUE de "
                        f"l'enum Severity {sorted(enum_sev)}.")

    # ── 3. bonus_keys utilisées ⊆ config ────────────────────────────────────────────────
    cfg_bonus = set(weights.get("bonuses", {}) or {})
    used_bonus = _collect_yaml_values(rules, "bonus_key") | _emitted_bonus_key_literals()
    for key in sorted(used_bonus - cfg_bonus):
        problems.append(f"[bonus_key] « {key} » utilisée (YAML/couche) mais ABSENTE de "
                        f"opportunity_weights.bonuses → bonus silencieusement à 0 "
                        f"(opportunity.py bonuses.get(key,0)).")

    # ── 4. spatial_kinds référencés existent en base (si session) ────────────────────────
    if session is not None:
        from sqlalchemy import text
        kinds = _collect_yaml_values(rules, "kind")
        present = {r[0] for r in session.execute(text("SELECT DISTINCT kind FROM spatial_layers"))}
        # Tolérance base non ingérée : si AUCUN kind de la cascade n'est présent, la base n'est pas
        # (encore) alimentée pour la cascade — ce n'est pas un défaut de CÂBLAGE (fresh/test DB). On
        # ne flague un kind que si la base EST peuplée mais que ce kind précis manque (vrai trou).
        if present & kinds:
            for kind in sorted(kinds - present):
                problems.append(f"[spatial_kind] « {kind} » référencé dans cascade_rules.yaml mais AUCUNE "
                                f"couche spatial_layers de ce kind en base (signal mort → UNKNOWN partout).")

    if problems:
        raise CablageError("Câblage scoring incohérent — refus de servir :\n  - "
                           + "\n  - ".join(problems))
    return {"layers": "OK", "severites": "OK", "bonus_keys": "OK",
            "spatial_kinds": "OK" if session is not None else "NON VÉRIFIÉ (pas de session)"}


_STATIC_OK = False


def ensure_cablage_static() -> None:
    """Garde de câblage STATIQUE (invariants 1-3, sans base), mémoïsée une fois par processus —
    à appeler au lancement de tout calcul de cascade (le câblage ne change pas en cours de run).
    Bloquante : lève `CablageError` si incohérent."""
    global _STATIC_OK
    if _STATIC_OK:
        return
    check_cablage_scoring(session=None)
    _STATIC_OK = True
