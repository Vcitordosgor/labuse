#!/usr/bin/env python3
"""DESTINATIONS-1 — assemble les fragments YAML d'une commune en calibration finale.

Usage : assemble_commune.py <insee> <slug> <fragments_dir> <meta.yaml> <out.yaml>

Fusionne les blocs `zones:` des fragments (ordre alphabétique de fichier), refuse
les doublons de zone divergents, préfixe le bloc meta fourni, valide le tout.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from valide_calibration import valide  # noqa: E402


def main() -> int:
    insee, slug, frag_dir, meta_path, out_path = sys.argv[1:6]
    meta = yaml.safe_load(Path(meta_path).read_text(encoding="utf-8"))
    zones: dict = {}
    for f in sorted(Path(frag_dir).glob("*.yaml")):
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        zs = doc.get("zones") or doc
        for code, v in zs.items():
            if code in zones and zones[code] != v:
                print(f"CONFLIT zone {code}: {f.name} diverge d'un fragment précédent")
                return 1
            zones[code] = v
    final = {"meta": meta["meta"] if "meta" in meta else meta, "zones": zones}
    out = Path(out_path)
    out.write_text(yaml.dump(final, allow_unicode=True, sort_keys=False, width=110),
                   encoding="utf-8")
    errs = valide(str(out), int(final["meta"].get("pages_total") or 0) or None)
    for e in errs:
        print("ERREUR:", e)
    nsd = sum(len((z or {}).get("sous_destinations") or {})
              for z in zones.values() if isinstance(z, dict))
    print(f"{out}: {len(zones)} zones, {nsd} entrées explicites, {len(errs)} erreur(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
