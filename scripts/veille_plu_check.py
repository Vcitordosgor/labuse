"""M41 P1.3 — GESTE TRIMESTRIEL de rafraîchissement du radar procédures PLU (outillé, ~2 h).

Ce que le geste de Vic fait tourner :
  1. LINT du registre (config/veille_plu.yaml) — refuse toute entrée incomplète / sans confiance ;
  2. liste ce qui doit être RE-VÉRIFIÉ : date_constat > 90 j (défaut) ou > 30 j (radar actif),
     avec l'URL à visiter par commune ;
  3. après édition du registre, `--diff <ancien.yaml>` montre ce qui a bougé.

Non bloquant, sort 0 (comme les gardes de fraîcheur). Bruyant : les dates parlent.

Usage :
  PYTHONPATH=src python scripts/veille_plu_check.py            # lint + liste à re-vérifier
  PYTHONPATH=src python scripts/veille_plu_check.py --diff config/veille_plu.prev.yaml
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from labuse import veille_plu as V  # noqa: E402


def _diff(old_path: str) -> None:
    import yaml
    with open(old_path, encoding="utf-8") as f:
        old = (yaml.safe_load(f) or {}).get("communes", {}) or {}
    new = V._registre()
    keys = sorted(set(old) | set(new))
    changed = 0
    for k in keys:
        o, n = old.get(k, {}), new.get(k, {})
        diffs = {f: (o.get(f), n.get(f)) for f in set(o) | set(n) if o.get(f) != n.get(f)}
        if diffs:
            changed += 1
            print(f"  {k} {n.get('commune') or o.get('commune')} :")
            for f, (ov, nv) in sorted(diffs.items()):
                print(f"      {f}: {ov!r} → {nv!r}")
    print(f"\n{changed} commune(s) modifiée(s) depuis {old_path}." if changed else "Aucune modification.")


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "--diff":
        _diff(sys.argv[2])
        return
    print("— VEILLE PLU · geste trimestriel —\n")
    errs = V.lint()
    if errs:
        print(f"⛔ LINT : {len(errs)} erreur(s) — corriger avant de servir :")
        for e in errs:
            print(f"   - {e}")
    else:
        print("✓ LINT : registre conforme (schéma strict, confiance présente partout).")
    todo = V.a_reverifier()
    print(f"\nÀ RE-VÉRIFIER : {len(todo)} entrée(s) (seuil 90 j ; 30 j si radar actif).")
    for t in todo:
        print(f"   {t['insee']} {t['commune']:<20} {t['motif']:<28} → {t['source_url']}")
    if not todo:
        print("   (aucune — tout est frais)")
    # non bloquant : exit 0


if __name__ == "__main__":
    main()
