"""FIX-PRIX-ET-OPPORTUNITES lot 4 — INSTANTANÉ MENSUEL DU SIGNAL SERVI (mesurable forward).

VERITE-TERRAIN-2 volet E a montré que le Signal servi (`score_labuse.signal_p` = P(vente L2-F dans les
12 mois)) **sépare** (lift ×2,29 au décile haut), mais que l'instantané réellement SERVI n'est **pas
jugeable aujourd'hui** : les labels de run (oct. 2026) sont postérieurs à la dernière mutation DVF
(31/12/2025) — la fenêtre de suivi est vide. Le protocole forward (SIGNAL-BACKTEST.md §Protocole) exige
de **figer aujourd'hui** l'instantané daté, puis de le **rejouer** quand DVF aura avancé.

Ce module opère ce protocole, en deux gestes :

  · `figer(session)`   — un job MENSUEL fige dans SA table `signal_instantanes` une copie DATÉE du Signal
                         servi (signal_p, niveau, bande) par parcelle. Idempotent (une clé par date×parcelle).
                         **N'écrit QUE dans `signal_instantanes`. Aucun mail. Aucune autre table touchée.**
  · `rejouer(session, date)` — LECTURE SEULE : pour un instantané figé à T₀, mesure le taux de vente DVF
                         observé APRÈS T₀ par niveau et par bande, avec lift + IC de Wilson (exactement la
                         grille du volet E). N'écrit rien. C'est le juge forward, à lancer quand DVF a avancé.

    PYTHONPATH=src python -m labuse.signal_instantane figer   [--date YYYY-MM-DD] [--run q_vXX]
    PYTHONPATH=src python -m labuse.signal_instantane rejouer  --date YYYY-MM-DD
"""
from __future__ import annotations

import math
import os

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import runs

#: seuils absolus du niveau servi (PALIERS-1, identiques au produit) — rappel, le niveau est figé tel quel.
#: fort ≥0,20 · moyen ≥0,10 · faible <0,10.

DDL = """
CREATE TABLE IF NOT EXISTS signal_instantanes (
  snapshot_le        date NOT NULL,              -- T₀ : date de l'instantané
  run_label          text NOT NULL,              -- run servi figé (traçabilité)
  parcel_id          integer NOT NULL,
  idu                text,
  signal_p           double precision,           -- P(vente 12 mois) servie à T₀
  signal_niveau      text,                        -- fort/moyen/faible servi à T₀
  bande              text,                        -- bande d'opportunité servie à T₀
  score_computed_at  timestamptz,                 -- computed_at de la ligne score_labuse source
  fige_le            timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (snapshot_le, parcel_id)
);
CREATE INDEX IF NOT EXISTS signal_instantanes_date ON signal_instantanes (snapshot_le);
"""


def ensure_schema(session: Session) -> None:
    for stmt in DDL.strip().split(";"):
        if stmt.strip():
            session.execute(text(stmt))


def _run_servi() -> str:
    """Run du Score LABUSE servi (même règle que l'API `_score_labuse_run`) : override admin puis le
    pointeur vivant `config/served_run.txt`. Jamais une constante figée."""
    return os.environ.get("LABUSE_SCORE_RUN") or runs.current()


def _date_reunion():
    """Date du jour à La Réunion (jamais `date.today()` nu : le fuseau compte pour l'horodatage servi)."""
    from .tz import now_reunion
    return now_reunion().date()


# ═══════════════════════════════════════════════════════════════════════════════════════════
#  FIGER — le job mensuel (écrit UNIQUEMENT signal_instantanes)
# ═══════════════════════════════════════════════════════════════════════════════════════════

def figer(session: Session, snapshot_le=None, run_label: str | None = None) -> dict:
    """Fige la prédiction servie datée. Idempotent : ON CONFLICT DO NOTHING sur (snapshot_le, parcel_id)
    → un second passage le même jour ne duplique rien et ne modifie rien. Renvoie les compteurs."""
    ensure_schema(session)
    snap = snapshot_le or _date_reunion()
    run = run_label or _run_servi()
    # garde : la table source doit exister et porter ce run avec un signal.
    if session.execute(text("SELECT to_regclass('score_labuse')")).scalar() is None:
        return {"snapshot_le": str(snap), "run_label": run, "n": 0, "note": "score_labuse absente"}
    res = session.execute(text(
        """
        INSERT INTO signal_instantanes
          (snapshot_le, run_label, parcel_id, idu, signal_p, signal_niveau, bande, score_computed_at)
        SELECT :snap, :run, parcel_id, idu, signal_p, signal_niveau, bande, computed_at
        FROM score_labuse
        WHERE run_label = :run AND signal_p IS NOT NULL
        ON CONFLICT (snapshot_le, parcel_id) DO NOTHING
        """), {"snap": snap, "run": run})
    inseres = res.rowcount if res.rowcount is not None else 0
    total = session.execute(text(
        "SELECT count(*) FROM signal_instantanes WHERE snapshot_le = :snap"), {"snap": snap}).scalar() or 0
    par_niveau = dict(session.execute(text(
        "SELECT signal_niveau, count(*) FROM signal_instantanes WHERE snapshot_le = :snap "
        "GROUP BY signal_niveau"), {"snap": snap}).all())
    session.commit()
    return {"snapshot_le": str(snap), "run_label": run, "inseres": int(inseres),
            "n": int(total), "par_niveau": {k: int(v) for k, v in par_niveau.items()}}


# ═══════════════════════════════════════════════════════════════════════════════════════════
#  REJOUER — le juge forward (LECTURE SEULE, grille du volet E)
# ═══════════════════════════════════════════════════════════════════════════════════════════

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Proportion k/n + bornes de l'IC de Wilson 95 % (même estimateur que le volet E)."""
    if n <= 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    demi = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, centre - demi, centre + demi)


def _taux_par(session, snap, colonne: str, horizon_mois: int | None) -> list[dict]:
    """Taux de vente DVF observé APRÈS T₀, groupé par `colonne` (signal_niveau | bande). Une vente =
    une mutation 'Vente' sur une parcelle de l'instantané, de date STRICTEMENT postérieure à T₀
    (et, si horizon donné, ≤ T₀ + horizon mois). Lecture seule."""
    born_haute = ("AND m.date_mutation <= (:snap::date + (:h || ' months')::interval)"
                  if horizon_mois else "")
    rows = session.execute(text(
        f"""
        WITH vendu AS (
          SELECT DISTINCT s.parcel_id
          FROM signal_instantanes s
          JOIN parcels p ON p.id = s.parcel_id
          JOIN dvf_mutations_parcelle m ON m.id_parcelle = p.idu
          WHERE s.snapshot_le = :snap
            AND m.nature_mutation = 'Vente'
            AND m.date_mutation > :snap::date {born_haute}
        )
        SELECT s.{colonne} AS cle, count(*) AS n,
               count(*) FILTER (WHERE v.parcel_id IS NOT NULL) AS ventes
        FROM signal_instantanes s
        LEFT JOIN vendu v ON v.parcel_id = s.parcel_id
        WHERE s.snapshot_le = :snap
        GROUP BY s.{colonne}
        ORDER BY s.{colonne}
        """), {"snap": snap, "h": horizon_mois}).all()
    return [{"cle": r[0], "n": int(r[1]), "ventes": int(r[2])} for r in rows]


def rejouer(session: Session, snapshot_le, horizon_mois: int | None = None) -> dict:
    """LECTURE SEULE. Mesure le Signal figé à T₀ contre les ventes DVF postérieures. N'écrit rien.
    Renvoie {snapshot_le, n, ventes, base, derniere_dvf, par_niveau, par_bande} avec lift + IC Wilson."""
    snap = snapshot_le
    n_tot = session.execute(text(
        "SELECT count(*) FROM signal_instantanes WHERE snapshot_le = :snap"), {"snap": snap}).scalar() or 0
    if not n_tot:
        return {"snapshot_le": str(snap), "n": 0, "note": "aucun instantané à cette date"}
    derniere = session.execute(text(
        "SELECT max(date_mutation) FROM dvf_mutations_parcelle WHERE nature_mutation = 'Vente'")).scalar()
    born_haute = ("AND m.date_mutation <= (:snap::date + (:h || ' months')::interval)" if horizon_mois else "")
    ventes_tot = session.execute(text(
        f"""SELECT count(DISTINCT s.parcel_id) FROM signal_instantanes s
            JOIN parcels p ON p.id = s.parcel_id
            JOIN dvf_mutations_parcelle m ON m.id_parcelle = p.idu
            WHERE s.snapshot_le = :snap AND m.nature_mutation = 'Vente'
              AND m.date_mutation > :snap::date {born_haute}"""),
        {"snap": snap, "h": horizon_mois}).scalar() or 0
    base = (ventes_tot / n_tot) if n_tot else 0.0

    def _enrichir(groupes):
        out = []
        for g in groupes:
            p, bas, haut = wilson(g["ventes"], g["n"])
            out.append({**g, "taux": p, "ic_bas": bas, "ic_haut": haut,
                        "lift": (p / base) if base else float("nan")})
        return out

    return {
        "snapshot_le": str(snap), "n": int(n_tot), "ventes": int(ventes_tot),
        "base": base, "derniere_dvf": str(derniere) if derniere else None,
        "horizon_mois": horizon_mois,
        "par_niveau": _enrichir(_taux_par(session, snap, "signal_niveau", horizon_mois)),
        "par_bande": _enrichir(_taux_par(session, snap, "bande", horizon_mois)),
    }


# ═══════════════════════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════════════════════

def _imprimer_rejeu(r: dict) -> None:
    print(f"instantané {r['snapshot_le']} · {r.get('n', 0)} parcelles · {r.get('ventes', 0)} ventes "
          f"depuis T₀ · base {r.get('base', 0) * 100:.2f} % · dernière DVF {r.get('derniere_dvf')}")
    if r.get("note"):
        print("  ", r["note"]); return
    for titre, cle in (("Par niveau de Signal", "par_niveau"), ("Par bande", "par_bande")):
        print(f"\n  {titre} :")
        for g in r.get(cle, []):
            lift = "—" if g["lift"] != g["lift"] else f"×{g['lift']:.2f}"
            print(f"    {str(g['cle']):8s} n={g['n']:>7} ventes={g['ventes']:>5} "
                  f"taux={g['taux'] * 100:5.2f}% IC[{g['ic_bas'] * 100:.2f};{g['ic_haut'] * 100:.2f}] lift {lift}")


def main(argv: list[str] | None = None) -> None:
    import argparse

    from .db import session_factory
    pa = argparse.ArgumentParser(prog="labuse.signal_instantane")
    sub = pa.add_subparsers(dest="cmd", required=True)
    pf = sub.add_parser("figer"); pf.add_argument("--date"); pf.add_argument("--run")
    pr = sub.add_parser("rejouer"); pr.add_argument("--date", required=True)
    pr.add_argument("--horizon-mois", type=int, default=None)
    a = pa.parse_args(argv)
    from datetime import date as _date
    s = session_factory()()
    try:
        if a.cmd == "figer":
            d = _date.fromisoformat(a.date) if a.date else None
            print(figer(s, snapshot_le=d, run_label=a.run))
        else:
            _imprimer_rejeu(rejouer(s, _date.fromisoformat(a.date), horizon_mois=a.horizon_mois))
    finally:
        s.close()


if __name__ == "__main__":
    main()
