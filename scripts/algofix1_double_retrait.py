"""ALGO-FIX-1 (3ᵉ passe / P3) — MESURE du double retrait des contraintes superposées.

Le chemin de repli `residuel_legacy` soustrait SÉPARÉMENT (db.py:629 puis 638) l'union(ER, EBC)
puis l'union(PPR rouge, PEB, DPF, ravine, 50 pas). Là où ces deux ensembles se CHEVAUCHENT, leur
intersection est soustraite DEUX FOIS → l'emprise est SOUS-estimée (faux zéros possibles, avis
Astra §2). Ce script mesure, sur les parcelles au chemin de repli :

  1. l'EXPOSITION : parcelles qui intersectent À LA FOIS une prescription (ER/EBC) et un PPR rouge ;
  2. les PARCELLES TOUCHÉES : chevauchement géométrique réel (prescription ∩ PPR rouge dans la
     parcelle) > seuil, avec la surface doublement soustraite ;
  3. la répartition estimés (capacité servie > 0) / zéros (capacité servie = 0, faux zéros potentiels).

Lecture seule, aucune écriture. Échantillon par défaut (coût SIG) ; `--all` pour tout le legacy.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import create_engine, text          # noqa: E402
from sqlalchemy.orm import Session                   # noqa: E402

RUN = "q_v20"
SEUIL_M2 = 5.0


def _session() -> Session:
    url = (os.environ.get("LABUSE_REEL_DATABASE_URL")
           or "postgresql+psycopg://openclaw@localhost:5432/labuse")
    return Session(bind=create_engine(url))


# Parcelles au chemin de repli, AVEC leur R servi (séparer R>0 / R=0 / R absent — avis Astra §4).
_LEGACY = text("""
SELECT p.id, r.sdp_residuelle_m2 AS r
FROM parcel_residuel r JOIN parcels p ON p.id = r.parcel_id
WHERE r.assiette_source = 'residuel_legacy'
ORDER BY {order} LIMIT :lim
""")


def _categorie_r(r):
    if r is None:
        return "r_absent"
    return "r_positif" if r > 0 else "r_nul"

# Chevauchement prescription (ER/EBC) ∩ PPR rouge (INTERDICTION) À L'INTÉRIEUR de la parcelle.
_OVERLAP = text("""
WITH g AS (SELECT geom_2975 AS geom, commune FROM parcels WHERE id = :pid),
pres AS (SELECT ST_Union(ST_MakeValid(s.geom_2975)) u FROM spatial_layers s, g
         WHERE s.kind = 'plu_gpu_prescription' AND s.commune = g.commune
           AND ST_Intersects(s.geom_2975, g.geom)),
rouge AS (SELECT ST_Union(ST_MakeValid(s.geom_2975)) u FROM spatial_layers s, g
          WHERE s.kind = 'ppr' AND s.subtype = 'INTERDICTION' AND s.commune = g.commune
            AND ST_Intersects(s.geom_2975, g.geom))
SELECT COALESCE(ST_Area(ST_Intersection(ST_Intersection(pres.u, rouge.u), g.geom)), 0.0) AS overlap_m2
FROM g LEFT JOIN pres ON TRUE LEFT JOIN rouge ON TRUE
""")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=1500)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", default="docs/audit-2026-11/algo-fix-1/DOUBLE-RETRAIT.md")
    args = ap.parse_args()
    lim = 10_000_000 if args.all else args.sample

    with _session() as s:
        total_legacy = s.execute(text(
            "SELECT count(*) FROM parcel_residuel WHERE assiette_source='residuel_legacy'")).scalar()
        legacy = s.execute(text(str(_LEGACY).replace("{order}",
                           "p.id" if args.all else "md5(p.idu::text)")), {"lim": lim}).fetchall()
        CATS = ("r_positif", "r_nul", "r_absent")
        exposees = {c: 0 for c in CATS}       # chevauchement brut > 0
        touchees = {c: 0 for c in CATS}       # chevauchement brut > seuil
        total = {c: 0 for c in CATS}
        aires = []
        for pid, r in legacy:
            cat = _categorie_r(r)
            total[cat] += 1
            ov = s.execute(_OVERLAP, {"pid": pid}).scalar() or 0.0
            if ov > 0:
                exposees[cat] += 1
            if ov > SEUIL_M2:
                touchees[cat] += 1
                aires.append(ov)
        n = len(legacy)
        aires.sort()
        med = aires[len(aires) // 2] if aires else 0.0
        tot_touchees = sum(touchees.values())
        frac = tot_touchees / n if n else 0.0
        estim_expo_ile = round(frac * total_legacy)

    md = [
        "# ALGO-FIX-1 — double retrait : EXPOSITION BRUTE À EXAMINER (pas une mesure d'impact)",
        "",
        f"Chemin de repli `residuel_legacy` : **{total_legacy} parcelles** au run servi q_v20.",
        f"Échantillon mesuré : **{n}** ({'tout le legacy' if args.all else 'tirage md5 reproductible'}).",
        "",
        "**Ce que ce fichier mesure (et ne mesure PAS).** On mesure un **chevauchement brut** : "
        f"`plu_gpu_prescription` ∩ `ppr/INTERDICTION` à l'intérieur de la parcelle > {SEUIL_M2:.0f} m². "
        "Ce n'est PAS la population effectivement affectée par le défaut (avis Astra passe-3 §4) : "
        "(1) il prend TOUTES les prescriptions, sans filtre des sous-types ER/EBC que le moteur "
        "applique ; (2) il mesure sur la parcelle entière, sans reculs ni restriction à l'assiette "
        "U/AU du repli ; (3) il ne compare pas l'emprise de l'ancien calcul à celle d'une union "
        "correcte, et ne propage rien jusqu'à C et R. C'est donc une **exposition à examiner**, "
        "un majorant — pas « parcelles touchées » ni « faux zéros imputables ».",
        "",
        "| Catégorie de R | Effectif échantillon | Exposées (> 0) | Chevauchement > "
        f"{SEUIL_M2:.0f} m² |",
        "|---|---:|---:|---:|",
    ]
    for c, lib in (("r_positif", "R > 0 (capacité servie positive)"),
                   ("r_nul", "R = 0"), ("r_absent", "R absent (NULL)")):
        md.append(f"| {lib} | {total[c]} | {exposees[c]} | {touchees[c]} |")
    md += [
        f"| **Total** | {n} | {sum(exposees.values())} | {tot_touchees} |",
        "",
        f"- Chevauchement brut dans l'échantillon : **{100*frac:.1f} %** → extrapolation île ≈ "
        f"**{estim_expo_ile}** parcelles legacy exposées (à examiner, pas « touchées »).",
        f"- Surface de chevauchement brut (cas > seuil) : médiane **{med:.0f} m²**, "
        f"max **{aires[-1] if aires else 0:.0f} m²**.",
        f"- Les **{touchees['r_nul']} cas R = 0** exposés sont des **candidats à examiner** (le double "
        "retrait a pu vider une assiette réelle), SANS reclassement automatique. Les cas **R absent "
        "(NULL)** sont comptés à part — ce ne sont pas des zéros.",
        "",
        "## Mesure d'impact réelle → RESIDUEL-2",
        "",
        "La mesure d'impact (emprise selon l'ancien calcul vs emprise avec union globale des "
        "contraintes ; C avant/après ; E inchangé ; R avant/après ; en séparant augmentation "
        "géométrique, capacité inchangée après plafonds, et résiduel redevenu positif ; contraintes "
        "hors PPR incluses) exige de rejouer le moteur de faisabilité sur l'assiette exacte avec ses "
        "filtres/unités/sources. Elle est **renvoyée à RESIDUEL-2** (correctif amont au niveau du "
        "moteur). En attendant, la V2 **isole** ces capacités non qualifiées en « À vérifier » (P1a), "
        "par scénario (R en conservation, C en reconstruction).",
    ]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"legacy={total_legacy} échantillon={n} chevauchement>{SEUIL_M2:.0f}m²={tot_touchees} "
          f"(R>0 {touchees['r_positif']} / R=0 {touchees['r_nul']} / R absent {touchees['r_absent']}) "
          f"→ écrit {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
