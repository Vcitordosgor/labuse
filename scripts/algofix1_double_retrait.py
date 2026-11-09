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


# Parcelles au chemin de repli (assiette_source) avec leur capacité servie (sdp résiduelle).
_LEGACY = text("""
SELECT p.id, (r.sdp_residuelle_m2 > 0) AS estimee
FROM parcel_residuel r JOIN parcels p ON p.id = r.parcel_id
WHERE r.assiette_source = 'residuel_legacy'
ORDER BY {order} LIMIT :lim
""")

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
        touchees = {"estimee": 0, "zero": 0}
        exposees = {"estimee": 0, "zero": 0}
        aires = []
        for pid, estimee in legacy:
            ov = s.execute(_OVERLAP, {"pid": pid}).scalar() or 0.0
            cle = "estimee" if estimee else "zero"
            if ov > 0:
                exposees[cle] += 1
            if ov > SEUIL_M2:
                touchees[cle] += 1
                aires.append(ov)
        n = len(legacy)
        aires.sort()
        med = aires[len(aires) // 2] if aires else 0.0
        tot_touchees = touchees["estimee"] + touchees["zero"]
        frac = tot_touchees / n if n else 0.0
        estim_touchees_ile = round(frac * total_legacy)

    md = [
        "# ALGO-FIX-1 (P3) — mesure du double retrait des contraintes superposées",
        "",
        f"Chemin de repli `residuel_legacy` : **{total_legacy} parcelles** au run servi q_v20.",
        f"Échantillon mesuré : **{n}** ({'tout le legacy' if args.all else 'tirage md5 reproductible'}).",
        "",
        "« Touchée » = prescription (ER/EBC) ∩ PPR rouge (INTERDICTION) à l'intérieur de la parcelle "
        f"> {SEUIL_M2:.0f} m² (surface doublement soustraite par db.py:629 puis 638).",
        "",
        "| | Estimés (capacité servie > 0) | Zéros (capacité servie = 0) | Total |",
        "|---|---:|---:|---:|",
        f"| Exposées (chevauchement > 0) | {exposees['estimee']} | {exposees['zero']} | "
        f"{exposees['estimee'] + exposees['zero']} |",
        f"| **Touchées (> {SEUIL_M2:.0f} m²)** | {touchees['estimee']} | {touchees['zero']} | "
        f"{tot_touchees} |",
        "",
        f"- Taux de parcelles touchées dans l'échantillon : **{100*frac:.1f} %** "
        f"→ extrapolation île ≈ **{estim_touchees_ile}** parcelles legacy touchées "
        "(estimés ET zéros compris).",
        f"- Surface doublement soustraite (parcelles touchées) : médiane **{med:.0f} m²**, "
        f"max **{aires[-1] if aires else 0:.0f} m²**.",
        f"- **Faux zéros potentiels** : les **{touchees['zero']}** parcelles touchées dont la "
        "capacité servie est nulle — la double soustraction peut avoir vidé une assiette réelle. "
        "À examiner SANS reclassement automatique (avis Astra §2).",
        "",
        "Méthode : chevauchement mesuré entre `plu_gpu_prescription` (ER+EBC) et `ppr/INTERDICTION` "
        "(zone rouge) clippé sur la parcelle. C'est un **majorant** du seul chevauchement EBC∩PPR "
        "(les prescriptions incluent ER). La correction de fond (union globale ou soustractions "
        "successives sur le reliquat) est un geste au niveau du moteur `db.py`, hors de ce mandat "
        "isolé ; la V2 marque entre-temps ces capacités « À vérifier » (P3).",
    ]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"legacy={total_legacy} échantillon={n} touchées={tot_touchees} "
          f"(estimés {touchees['estimee']} / zéros {touchees['zero']}) → écrit {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
