"""VITESSE-PROD-1 — preuve d'égalité d'`aleas_parcelle` : spatial_layers (AVANT) vs tuyau_subdivise
(APRÈS). Échantillon : parcelles touchant un PPR ou un aléa (les seules où les requêtes renvoient
quelque chose), tirées déterministiquement (ORDER BY idu, 1 sur N). Pour chaque parcelle, la liste
COMPLÈTE (nature, niveau, part_pct, libelle, redhibitoire, source, millesime) doit être IDENTIQUE.

Sortie : « N parcelles · égales N · différentes M » + détail des différences. Temps AVANT/APRÈS.
Usage : PYTHONPATH=src python docs/audit-2026-10/VITESSE-PROD-1/harnais/aleas_egalite.py [n]
"""
from __future__ import annotations

import sys
import time

from sqlalchemy import text

from labuse.api import servitudes
from labuse.db import session_scope

N = int(sys.argv[1]) if len(sys.argv) > 1 else 120


def main() -> None:
    with session_scope() as db:
        # parcelles touchant ppr/georisque_alea par bbox (cheap) — échantillon déterministe réparti
        idus = [r[0] for r in db.execute(text("""
            WITH cand AS (
                SELECT DISTINCT p.idu FROM parcels p
                WHERE EXISTS (SELECT 1 FROM tuyau_subdivise s
                              WHERE s.kind IN ('ppr', 'georisque_alea')
                                AND s.geom_2975 && p.geom_2975)
            )
            SELECT idu FROM (SELECT idu, row_number() OVER (ORDER BY idu) rn,
                                    count(*) OVER () tot FROM cand) t
            WHERE rn % GREATEST(tot / :n, 1) = 0 LIMIT :n"""), {"n": N}).all()]
        print(f"échantillon : {len(idus)} parcelles touchant PPR/aléa (bbox)")
        diff = 0
        t_av = t_ap = 0.0
        for idu in idus:
            # AVANT : force spatial_layers (patch temporaire de la sonde de table)
            orig = servitudes._table_aleas
            servitudes._table_aleas = lambda _db: "spatial_layers"
            db.info.pop("_aleas_parcelle_memo", None)
            t0 = time.perf_counter()
            avant = servitudes.aleas_parcelle(db, idu)
            t_av += time.perf_counter() - t0
            servitudes._table_aleas = orig
            db.info.pop("_aleas_parcelle_memo", None)
            t0 = time.perf_counter()
            apres = servitudes.aleas_parcelle(db, idu)
            t_ap += time.perf_counter() - t0
            db.info.pop("_aleas_parcelle_memo", None)
            ka = sorted((d["nature"], d["niveau"] or "", d["part_pct"], d["libelle"],
                         d["redhibitoire"], d["source"], d["millesime"] or "") for d in avant)
            kb = sorted((d["nature"], d["niveau"] or "", d["part_pct"], d["libelle"],
                         d["redhibitoire"], d["source"], d["millesime"] or "") for d in apres)
            if ka != kb:
                diff += 1
                print(f"≠ {idu}")
                for x in ka:
                    if x not in kb:
                        print(f"   AVANT seul : {x}")
                for x in kb:
                    if x not in ka:
                        print(f"   APRÈS seul : {x}")
        print(f"{len(idus)} parcelles · égales {len(idus) - diff} · différentes {diff}")
        print(f"temps cumulés : AVANT {t_av:.1f}s · APRÈS {t_ap:.1f}s "
              f"(x{t_av / t_ap:.0f} plus rapide)" if t_ap else "")
        if diff:
            sys.exit(1)


if __name__ == "__main__":
    main()
