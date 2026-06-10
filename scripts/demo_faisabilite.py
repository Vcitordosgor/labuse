"""Démonstrateur ÉTAPE B : pré-faisabilité tracée sur de vraies parcelles Saint-Paul.
Usage : python scripts/demo_faisabilite.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy import text  # noqa: E402

from labuse.db import session_scope  # noqa: E402
from labuse.faisabilite.db import parcel_faisabilite  # noqa: E402


def render(ctx, f) -> str:
    L = []
    L.append("━" * 78)
    L.append(f"PARCELLE {ctx.idu}  ·  zone PLU {f.zone}  ·  {ctx.surface_m2:,.0f} m²".replace(",", " "))
    pente = f"{ctx.contraintes.pente_pct:.0f}%" if ctx.contraintes.pente_pct is not None else "n/d"
    flags = []
    if ctx.contraintes.bande_littorale:
        flags.append("trait de côte")
    if ctx.contraintes.agricole_sar:
        flags.append("SAFER")
    L.append(f"   contexte : pente {pente}" + (f" · {' · '.join(flags)}" if flags else ""))
    L.append(f"\n▶ VERDICT : {f.verdict}")
    L.append("\n  Calcul (chaque ligne → sa source PLU) :")
    for s in f.steps:
        L.append(f"    • {s.label} : {s.formule} = {s.valeur}")
        L.append(f"        └ source : {s.source}")
    if f.modulation:
        L.append("\n  Modulation réunionnaise :")
        for m in f.modulation:
            L.append(f"    • {m}")
    if f.hypotheses:
        L.append("\n  Hypothèses (signalées) :")
        for h in f.hypotheses:
            L.append(f"    • {h}")
    if f.avertissements:
        L.append("\n  À vérifier (non comblé, jamais deviné) :")
        for a in f.avertissements:
            L.append(f"    • {a}")
    L.append(f"\n  ⚠️  {f.bandeau}")
    return "\n".join(L)


PENTE_SUB = ("(SELECT max((pl.attrs->>'slope_pct')::float) FROM spatial_layers pl "
             "WHERE pl.commune='Saint-Paul' AND pl.kind='pente' "
             "AND ST_Intersects(pl.geom_2975,p.geom_2975))")

PICKS = [
    ("U1c — zone haute (hé 15 m)", "z.name = 'U1c'", "surface"),
    ("U1d — zone basse (hé 6 m)", "z.name = 'U1d'", "surface"),
    ("Parcelle la plus pentue (modulation)", "z.name ~ '^(U|AU)'", "pente"),
    ("U1pru — zone très haute (hé 30 m)", "z.name = 'U1pru'", "surface"),
]


def pick(session, zone_cond, order):
    order_sql = f"{PENTE_SUB} DESC NULLS LAST" if order == "pente" else "ST_Area(p.geom_2975) DESC"
    q = text(f"""
        SELECT p.id
        FROM parcels p
        JOIN spatial_layers z ON z.commune='Saint-Paul' AND z.kind ILIKE '%plu%'
             AND ST_Contains(z.geom,p.centroid)
        WHERE p.commune='Saint-Paul' AND {zone_cond}
          AND ST_Area(p.geom_2975) BETWEEN 400 AND 5000
        ORDER BY {order_sql} LIMIT 1""")
    row = session.execute(q).first()
    return row[0] if row else None


def main():
    with session_scope() as s:
        for label, cond, extra in PICKS:
            pid = pick(s, cond, extra)
            print("\n" + "#" * 78)
            print("#", label)
            if pid is None:
                print("  (aucune parcelle correspondante dans l'échantillon)")
                continue
            res = parcel_faisabilite(s, pid)
            if res is None:
                print("  (zone non résolue)")
                continue
            ctx, f = res
            print(render(ctx, f))


if __name__ == "__main__":
    main()
