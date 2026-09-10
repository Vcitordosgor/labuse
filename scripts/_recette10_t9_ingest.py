"""RECETTE-10 T9 — ingestion LiDAR HD BORNÉE, RÉSUMABLE, idempotente (23 communes hors Saint-Denis).

Cible = parcelles BÂTIES en palier de priorité (brulante/chaude/reserve_fonciere) du run servi — là où
le scénario de surélévation (Dossier/Apporteur) est réellement consulté. La table `batiment_hauteur_lidar`
est un cache idempotent (ON CONFLICT (idu)) : relancer SAUTE les idu déjà mesurés (REPRISE naturelle).

Garde-fous : cap `MAX` (défaut 800) et budget temps `MAX_SEC` (défaut 900 s) — on s'arrête PROPREMENT
et on dit où on en est (jamais un batch de 2,5 jours qui martèle le WMS IGN en aveugle). Le RESTE est
repris au prochain lancement.

Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src python scripts/_recette10_t9_ingest.py
Env : MAX (int), MAX_SEC (float), TIERS (csv), une commune unique via COMMUNE.
"""
from __future__ import annotations

import os
import time

from sqlalchemy import text

from labuse.db import session_scope
from labuse.api.app import _score_v2_run_id
from labuse.faisabilite.hauteur_lidar import ensure_table, ingest_hauteur_lidar

MAX = int(os.environ.get("MAX", "800"))
MAX_SEC = float(os.environ.get("MAX_SEC", "900"))
TIERS = tuple(os.environ.get("TIERS", "brulante,chaude,reserve_fonciere").split(","))
COMMUNE = os.environ.get("COMMUNE")


def cibles(db) -> list[str]:
    v2 = _score_v2_run_id(db)
    where_commune = "p.commune = :commune" if COMMUNE else "p.commune <> 'Saint-Denis'"
    sql = text(f"""
        SELECT DISTINCT p.idu
        FROM parcels p
        JOIN spatial_layers b ON b.kind='batiment' AND b.geom_2975 IS NOT NULL
                             AND ST_Intersects(b.geom_2975, p.geom_2975)
        JOIN parcel_p_score_v2 s ON s.parcelle_id=p.idu AND s.run_id=:v2
        LEFT JOIN batiment_hauteur_lidar hl ON hl.idu = p.idu
        WHERE {where_commune} AND s.tier = ANY(:tiers) AND hl.idu IS NULL
        ORDER BY p.idu""")
    params = {"v2": v2, "tiers": list(TIERS)}
    if COMMUNE:
        params["commune"] = COMMUNE
    return [r[0] for r in db.execute(sql, params).all()]


def main() -> None:
    with session_scope() as db:
        ensure_table(db)
        db.commit()
        todo = cibles(db)
    print(f"[T9] à mesurer (non encore ingérées) : {len(todo)} ; cap MAX={MAX}, budget {MAX_SEC:.0f}s", flush=True)
    t0 = time.time()
    ok = vide = err = 0
    with session_scope() as db:
        for i, idu in enumerate(todo[:MAX], 1):
            if time.time() - t0 > MAX_SEC:
                print(f"[T9] STOP budget temps atteint à {i-1} parcelles", flush=True)
                break
            try:
                m = ingest_hauteur_lidar(db, idu)
                if m and m.get("faitage_m") is not None:
                    ok += 1
                else:
                    vide += 1
            except Exception as exc:  # noqa: BLE001 — on continue, jamais tout un batch perdu
                err += 1
                db.rollback()
                print(f"[T9] ERR {idu}: {str(exc)[:100]}", flush=True)
            if i % 25 == 0:
                db.commit()
                dt = time.time() - t0
                print(f"[T9] {i}/{min(MAX,len(todo))} · ok={ok} vide={vide} err={err} · "
                      f"{dt:.0f}s ({dt/i:.2f}s/parcelle)", flush=True)
        db.commit()
    dt = time.time() - t0
    print(f"[T9] FIN · traitées={min(MAX,len(todo))} ok={ok} vide={vide} err={err} · "
          f"{dt:.0f}s ({dt/max(1,ok+vide+err):.2f}s/parcelle) · reste≈{max(0,len(todo)-MAX)} (repris au prochain run)",
          flush=True)


if __name__ == "__main__":
    main()
