"""RESIDUEL-2 — pourquoi le gabarit ne sert pas les 53 923 parcelles `residuel_legacy`.

Rejoue `build_gabarit_input` + `compute_gabarit` (la MÊME porte que `_assiette_gabarit`)
sur un échantillon reproductible des parcelles de repli et classe le motif de blocage.
Objectif : la carte des causes qui décide, par cause, « gabarit capable » vs « repli qualifié ».

Lecture seule. Base réelle via LABUSE_DATABASE_URL.
"""
from __future__ import annotations

import hashlib
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import text  # noqa: E402

from labuse.db import session_scope  # noqa: E402
from labuse.gabarit.builder import build_gabarit_input  # noqa: E402
from labuse.gabarit.engine import compute_gabarit  # noqa: E402

N = int(os.environ.get("RESIDUEL2_N", "2500"))


def _bucket(reason: str) -> str:
    r = reason.lower()
    if "zone non constructible" in r or "entièrement en zone" in r:
        return "A/N : zone non constructible (dominante)"
    if "≥ 2 zones" in r or "multi-zones" in r or "morceau constructible" in r:
        return "multi-zones : morceau constructible non isolable"
    if "indéterminée" in r:
        return "zone PLU indéterminée"
    if "hors calibrage" in r or "non calibré" in r:
        return "PLU non calibré pour la zone"
    if "non validée (propose)" in r or "règle plu non validée" in r:
        return "règle PLU non validée (propose)"
    if "sans règles d'implantation" in r:
        return "zone sans règles d'implantation propres"
    if "emprise (ces)" in r:
        return "emprise (CES) non réglementée / non validée"
    if "hauteur" in r:
        return "hauteur réglementaire non validée"
    if "façade sur voie" in r or "voie privée" in r:
        return "desserte : pas de façade sur voie"
    if "limites de la parcelle non qualifiées" in r:
        return "limites non qualifiées (voie/limite séparative)"
    if "recul" in r and "séparative" in r:
        return "recul limite séparative non réglementé"
    if "recul" in r and "voie" in r:
        return "recul sur voie non réglementé"
    if "géométrie de parcelle indisponible" in r:
        return "géométrie de parcelle indisponible"
    return "autre : " + reason[:60]


def main() -> None:
    with session_scope() as s:
        rows = s.execute(text(
            "SELECT pr.parcel_id, p.idu FROM parcel_residuel pr "
            "JOIN parcels p ON p.id = pr.parcel_id "
            "WHERE pr.assiette_source = 'residuel_legacy'"
        )).all()
    universe = [(pid, idu) for pid, idu in rows]
    total = len(universe)
    # tirage md5 reproductible
    universe.sort(key=lambda x: hashlib.md5(str(x[0]).encode()).hexdigest())
    sample = universe[:N]
    print(f"legacy total={total}  échantillon={len(sample)}")

    buckets: Counter[str] = Counter()
    first_block: Counter[str] = Counter()
    compute_fail = 0
    no_block_but_fail = 0
    served_ok = 0  # gabarit sert en fait (ne devrait pas arriver si run cohérent)
    errors = 0
    examples: dict[str, str] = {}

    with session_scope() as s:
        for pid, idu in sample:
            try:
                build = build_gabarit_input(s, idu)
            except Exception as e:  # noqa: BLE001
                errors += 1
                buckets["ERREUR build: " + type(e).__name__] += 1
                continue
            if build is None:
                buckets["build=None (parcelle/zone introuvable)"] += 1
                examples.setdefault("build=None (parcelle/zone introuvable)", idu)
                continue
            if build.blocking:
                b = _bucket(build.blocking[0])
                buckets[b] += 1
                first_block[build.blocking[0]] += 1
                examples.setdefault(b, idu)
                continue
            # pas de blocking → compute_gabarit a dû échouer (sinon gabarit servirait)
            try:
                res = compute_gabarit(build.input)
            except Exception as e:  # noqa: BLE001
                errors += 1
                buckets["ERREUR compute: " + type(e).__name__] += 1
                continue
            if res.status != "ok":
                b = f"compute_gabarit status={res.status}"
                buckets[b] += 1
                no_block_but_fail += 1
                examples.setdefault(b, idu)
            else:
                served_ok += 1
                buckets["gabarit OK (incohérence run)"] += 1
                examples.setdefault("gabarit OK (incohérence run)", idu)

    print(f"\ncompute_fail={compute_fail} no_block_but_fail={no_block_but_fail} "
          f"served_ok={served_ok} errors={errors}\n")
    print("=== CAUSES (échantillon) ===")
    for cause, n in buckets.most_common():
        pct = 100.0 * n / len(sample)
        extrap = round(total * n / len(sample))
        ex = examples.get(cause, "")
        print(f"{n:5d}  {pct:5.1f}%  ~{extrap:6d}  {cause}   ex={ex}")

    print("\n=== top motifs bruts (blocking[0]) ===")
    for reason, n in first_block.most_common(25):
        print(f"{n:5d}  {reason}")


if __name__ == "__main__":
    main()
