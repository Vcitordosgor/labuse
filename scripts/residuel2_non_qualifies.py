"""RESIDUEL-2 — répartition par motif des parcelles legacy NON QUALIFIÉES (`residuel_legacy`).

Restreint aux parcelles que le gabarit ne sert pas ET dont le repli n'est PAS qualifiable (motifs
autres que « Limites non qualifiées » seules). Donne, par motif de non-service, l'effectif, un
exemple d'IDU, et ce qui manque pour servir au gabarit / qualifier (texte dans le rapport).

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
from labuse.faisabilite.db import _repli_qualifiable  # noqa: E402
from labuse.gabarit.builder import build_gabarit_input  # noqa: E402
from labuse.gabarit.engine import compute_gabarit  # noqa: E402

N = int(os.environ.get("RESIDUEL2_N", "3500"))


def _bucket(reason: str) -> str:
    r = reason.lower()
    if "voie privée" in r or "façade sur voie" in r:
        return "desserte : voie privée (recul non réglé)"
    if "recul sur voie" in r:
        return "recul sur voie non réglementé"
    if "hors calibrage" in r or "non calibré" in r:
        return "PLU non calibré pour la zone"
    if "non validée (propose)" in r or "règle plu non validée" in r:
        return "règle PLU non validée (propose)"
    if "≥ 2 zones" in r or "multi-zones" in r or "morceau constructible" in r:
        return "multi-zones : morceau non isolable"
    if "sans règles d'implantation" in r:
        return "zone sans règles d'implantation propres"
    if "emprise (ces)" in r:
        return "emprise (CES) non réglementée"
    if "recul sur limite séparative" in r:
        return "recul limite séparative non réglementé"
    if "hauteur" in r:
        return "hauteur réglementaire non validée"
    if "zone non constructible" in r or "entièrement en zone" in r:
        return "A/N dominante (sous-zone non calibrée)"
    if "indéterminée" in r:
        return "zone PLU indéterminée"
    if "introuvable" in r or "indisponible" in r:
        return "géométrie/zone indisponible"
    return "autre : " + reason[:50]


def main() -> None:
    with session_scope() as s:
        rows = s.execute(text(
            "SELECT pr.parcel_id, p.idu FROM parcel_residuel pr JOIN parcels p ON p.id=pr.parcel_id "
            "WHERE pr.assiette_source='residuel_legacy'")).all()
    univ = sorted(((pid, idu) for pid, idu in rows),
                  key=lambda x: hashlib.md5(str(x[0]).encode()).hexdigest())
    sample = univ[:N]
    print(f"legacy total={len(univ)} échantillon={len(sample)}")

    non_qual = Counter()
    examples: dict[str, str] = {}
    n_qual = n_gab = n_nonqual = 0
    with session_scope() as s:
        for pid, idu in sample:
            try:
                build = build_gabarit_input(s, idu)
            except Exception:  # noqa: BLE001
                non_qual["ERREUR build"] += 1
                continue
            if build is None:
                b = "géométrie/zone indisponible"
                non_qual[b] += 1; n_nonqual += 1; examples.setdefault(b, idu); continue
            if build.blocking:
                if _repli_qualifiable(build.blocking):
                    n_qual += 1
                    continue
                # non qualifié : bucket du 1er motif non bénin
                motif = next((b for b in build.blocking
                              if not b.startswith("Limites de la parcelle non qualifiées")),
                             build.blocking[0])
                b = _bucket(motif)
                non_qual[b] += 1; n_nonqual += 1; examples.setdefault(b, idu)
                continue
            # pas de blocking → compute
            try:
                res = compute_gabarit(build.input)
            except Exception:  # noqa: BLE001
                b = "compute_gabarit : exception"
                non_qual[b] += 1; n_nonqual += 1; examples.setdefault(b, idu); continue
            if res.status == "ok":
                n_gab += 1
            else:
                b = f"compute_gabarit : {res.status}"
                non_qual[b] += 1; n_nonqual += 1; examples.setdefault(b, idu)

    # extrapolation sur l'effectif NON QUALIFIÉ réel (part non-qual × total legacy)
    part_nonqual = n_nonqual / len(sample)
    ile_nonqual = round(len(univ) * part_nonqual)
    print(f"\néchantillon : qualifiés={n_qual}  gabarit-servables={n_gab}  NON qualifiés={n_nonqual}")
    print(f"→ NON qualifiés île ≈ {ile_nonqual}\n")
    print("=== RÉPARTITION DES NON QUALIFIÉS PAR MOTIF ===")
    for motif, k in non_qual.most_common():
        pct = 100.0 * k / max(1, n_nonqual)
        ile = round(ile_nonqual * k / max(1, n_nonqual))
        print(f"  {k:5d}  {pct:5.1f}%  ~{ile:6d}  {motif:42}  ex={examples.get(motif,'')}")


if __name__ == "__main__":
    main()
