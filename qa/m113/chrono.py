"""M113 · Phase 0 — chronométrage de la latence du Copilote, par ÉTAGE.

Enveloppe core.complete pour mesurer le temps mur + le modèle de chaque appel (kind : copilote-route
/ copilote-select / copilote-web / copilote-formule), sur 3 cas : le maire (QUESTION→web), un
comptage facette, une clarification. Le « réseau/reste » = total answer() − somme des appels modèle.

Usage : .venv/bin/python qa/m113/chrono.py   (nécessite ANTHROPIC_API_KEY + base réelle)
"""
from __future__ import annotations

import time

from labuse.ai import core
from labuse.copilote_v2 import answering
from labuse.db import session_scope

CAS = [
    ("maire (QUESTION→web)", "Qui est le maire de La Possession ?", None, None),
    ("comptage facette", "Combien de parcelles à Saint-Paul ?", None, None),
    ("clarification", "Je veux investir.", None, None),
]

_events: list[dict] = []
_orig = core.complete


def _wrapped(*a, **kw):
    kind = kw.get("kind", "?")
    model = kw.get("model", core.MODEL_FACTUAL)
    t0 = time.perf_counter()
    r = _orig(*a, **kw)
    _events.append({"kind": kind, "model": model, "ms": round((time.perf_counter() - t0) * 1000),
                    "tin": getattr(r, "tokens_in", 0), "tout": getattr(r, "tokens_out", 0)})
    return r


def main() -> int:
    core.complete = _wrapped
    answering.core.complete = _wrapped   # l'alias importé dans le module
    short = {"claude-haiku-4-5-20251001": "haiku", "claude-sonnet-4-6": "sonnet"}
    with session_scope() as db:
        for label, msg, hist, prior in CAS:
            print(f"\n═══ {label} : « {msg} » ═══")
            for run in (1, 2):                       # 2 passes (la 1re paie le chauffage réseau)
                _events.clear()
                t0 = time.perf_counter()
                rep = answering.answer(db, msg, history=hist, prior_params=prior)
                total = round((time.perf_counter() - t0) * 1000)
                somme_llm = sum(e["ms"] for e in _events)
                etages = " + ".join(f"{e['kind'].replace('copilote-','')}({short.get(e['model'],e['model'])}"
                                    f",{e['ms']}ms)" for e in _events)
                reste = total - somme_llm
                intent = (rep.get("_route") or {}).get("intent")
                print(f"  run{run}: TOTAL {total} ms  [{intent}]  = {etages} + réseau/reste({reste}ms)")
    core.complete = _orig
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
