"""DEPLOY-GROUPE-3 — PREUVE que le recalcul partiel exigu est COMPLET (précisions Vic).

Pourquoi la cible = cause='terrain_exigu' suffit (et couvre « emprise<seuil », précision 2 Vic) :
le ré-examen exigu est strictement condamné à `if emprise < SEUIL_EXIGU_M2` (db.py:902) et, dans le
CODE D'ORIGINE (celui de seq 18, fix inactif), CE SEUL chemin produit cause='terrain_exigu'
(engine.py:557 ; `assiette_a_verifier` exige le fix ACTIF, `redhibitoire` vient d'une branche
NON-emprise). Donc {emprise<SEUIL dans seq 18} ≡ {cause='terrain_exigu'} exactement (cf. EXIGU-FIX-1
§1 et §6). Le set « emprise<seuil mais autre cause » est VIDE. `emprise` n'étant pas une colonne
persistée, on le PROUVE empiriquement : on recalcule HORS cible avec le NOUVEAU code et on montre
l'identité à seq 18, en ciblant surtout les parcelles où une omission POURRAIT se cacher (capacité
constructible quasi nulle). Lecture seule (compare, n'écrit pas).
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
    # (A) hors cible, AU HASARD — prouve que le fix n'a AUCUN effet de bord hors terrain_exigu.
    "hors cible AU HASARD": (
        "r.cause IS DISTINCT FROM 'terrain_exigu'", "ORDER BY md5(p.idu)"),
    # (B) hors cible ET capacité constructible quasi NULLE (sdp_max_m2 < 5) — le proxy FIABLE de
    #     « emprise calculée sous le seuil » (la SDP max est proportionnelle à l'emprise ; contrairement
    #     à taux_emprise_pct qui est l'occupation BÂTIE, sans rapport). C'est la SEULE zone où une
    #     parcelle emprise<seuil pourrait porter une autre cause que terrain_exigu — donc la seule où
    #     une omission de la cible se cacherait (précision 2 de Vic). Attendu : identique à seq 18.
    "hors cible ET capacité quasi nulle": (
        "r.cause IS DISTINCT FROM 'terrain_exigu' AND r.cause IS NOT NULL "
        "AND COALESCE(r.sdp_max_m2, 0) < 5",
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
