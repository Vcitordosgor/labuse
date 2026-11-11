"""DEPLOY-GROUPE-3 — PREUVE que le recalcul partiel exigu est complet (précision 4 de Vic).

Tire 500 parcelles AU HASARD HORS de la cible (cause != 'terrain_exigu' dans seq 18), recalcule le
résiduel avec le NOUVEAU code (exigu-fix), et montre que le résultat est IDENTIQUE à seq 18 — donc
le fix ne change RIEN hors de la cible, et recalculer la cible suffit. Lecture seule (compare, n'écrit pas).
Usage : python scripts/q23_exigu_proof.py [N=500]
"""
from __future__ import annotations
import sys
from labuse.db import session_scope
from sqlalchemy import text
from labuse.faisabilite.residuel import compute_residuel


def _g(d, *ks):
    for k in ks:
        if isinstance(d, dict) and k in d and d[k] is not None:
            return d[k]
    return None


_SEL = {
    # (A) hors cible, AU HASARD
    "hors cible AU HASARD": (
        "r.cause IS DISTINCT FROM 'terrain_exigu'", "ORDER BY md5(p.idu)"),
    # (B) hors cible ET emprise calculée < seuil d'exiguïté (≈5 m²) — les seules où une omission
    #     pourrait se cacher (précision 4 de Vic). emprise ≈ taux_emprise_pct/100 × surface.
    "hors cible ET emprise<seuil": (
        "r.cause IS DISTINCT FROM 'terrain_exigu' AND "
        "COALESCE(r.taux_emprise_pct,0)/100.0 * COALESCE(r.surface_terrain_m2,0) < 5",
        "ORDER BY md5(p.idu)"),
}


def _cohorte(s, nom, where, order, n):
    rows = list(s.execute(text(
        f"SELECT r.parcel_id, p.idu, r.sdp_residuelle_m2, r.sdp_max_m2, r.cause "
        f"FROM parcel_residuel_runs r JOIN parcels p ON p.id=r.parcel_id "
        f"WHERE r.run_seq=18 AND {where} {order} LIMIT :n"), {"n": n}))
    diffs = []
    for pid, idu, r18, c18, cause18 in rows:
        live = compute_residuel(s, pid) or {}
        lr = _g(live, "sdp_residuelle_m2"); lc = _g(live, "sdp_max_m2"); lcause = _g(live, "cause")
        if (round(lr or 0) != round(r18 or 0) or round(lc or 0) != round(c18 or 0)
                or (lcause or None) != (cause18 or None)):
            diffs.append((idu, (round(r18 or 0), round(c18 or 0), cause18),
                          (round(lr or 0), round(lc or 0), lcause)))
    print(f"[{nom}] IDENTIQUES {len(rows)-len(diffs)}/{len(rows)} · DIFFÉRENTES {len(diffs)}")
    for idu, a, b in diffs[:10]:
        print(f"    ✗ {idu} seq18={a} live={b}")
    return len(diffs)


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    tot = 0
    with session_scope() as s:
        for nom, (where, order) in _SEL.items():
            tot += _cohorte(s, nom, where, order, n)
    print("✓ PREUVE OK : le fix ne change AUCUNE parcelle hors cible (2 cohortes) → recalcul partiel complet."
          if tot == 0 else
          "✗ des parcelles HORS cible changent → la cible est INCOMPLÈTE (élargir le recalcul).")
    return 0 if tot == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
