#!/usr/bin/env python3
"""DESTINATIONS-1 — validateur d'une calibration commune (fragments ou YAML final).

Usage : python scripts/audit/destinations/valide_calibration.py <yaml> [pages_max]

Vérifie : YAML parse, statuts dans l'énum, slugs de sous-destinations dans le
référentiel R151-28, page_pdf plausible, silence ∈ {autorise, interdit} + cité,
renvoi vers une zone existante. Sort en erreur (rc 1) au premier lot de problèmes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from labuse.plu.destinations import SOUS_DESTINATIONS  # noqa: E402

STATUTS = {"autorise", "interdit", "sous_condition"}
SEUIL_TYPES = {"surface_vente", "surface_plancher", None}


def valide(path: str, pages_max: int | None = None) -> list[str]:
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    zones = doc.get("zones") or (doc if "meta" not in doc else {})
    errs: list[str] = []
    if not zones:
        return [f"{path}: aucun bloc zones"]
    for zc, zv in zones.items():
        if not isinstance(zv, dict):
            errs.append(f"{zc}: entrée non-dict")
            continue
        if zv.get("renvoi"):
            if zv["renvoi"] not in zones:
                errs.append(f"{zc}: renvoi vers zone inconnue {zv['renvoi']!r}")
            if not zv.get("renvoi_src"):
                errs.append(f"{zc}: renvoi sans renvoi_src (citation obligatoire)")
            continue
        if zv.get("etat") == "non_lu":
            continue
        sil = zv.get("silence")
        if sil not in ("autorise", "interdit"):
            errs.append(f"{zc}: silence manquant ou invalide ({sil!r})")
        elif not zv.get("silence_src"):
            errs.append(f"{zc}: silence sans silence_src (citation obligatoire)")
        for sd, e in (zv.get("sous_destinations") or {}).items():
            if sd not in SOUS_DESTINATIONS:
                errs.append(f"{zc}.{sd}: sous-destination hors référentiel")
                continue
            st = (e or {}).get("statut")
            if st not in STATUTS:
                errs.append(f"{zc}.{sd}: statut invalide {st!r}")
            if not e.get("article"):
                errs.append(f"{zc}.{sd}: article manquant")
            pg = e.get("page_pdf")
            if not isinstance(pg, int) or pg < 1 or (pages_max and pg > pages_max):
                errs.append(f"{zc}.{sd}: page_pdf invalide {pg!r}")
            if st == "sous_condition" and not e.get("condition"):
                errs.append(f"{zc}.{sd}: sous_condition sans condition en clair")
            if e.get("seuil_type") not in SEUIL_TYPES:
                errs.append(f"{zc}.{sd}: seuil_type invalide {e.get('seuil_type')!r}")
            if e.get("seuil_m2") is not None and not isinstance(e["seuil_m2"], (int, float)):
                errs.append(f"{zc}.{sd}: seuil_m2 non numérique {e.get('seuil_m2')!r}")
    return errs


if __name__ == "__main__":
    pages_max = int(sys.argv[2]) if len(sys.argv) > 2 else None
    errs = valide(sys.argv[1], pages_max)
    for e in errs:
        print("ERREUR:", e)
    n = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8")) or {}
    zones = n.get("zones") or (n if "meta" not in n else {})
    nsd = sum(len((z or {}).get("sous_destinations") or {}) for z in zones.values() if isinstance(z, dict))
    print(f"{sys.argv[1]}: {len(zones)} zones, {nsd} entrées explicites, {len(errs)} erreur(s)")
    sys.exit(1 if errs else 0)
