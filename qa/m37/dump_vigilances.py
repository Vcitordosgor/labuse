"""M37 (addendum) — DUMP EXHAUSTIF des vigilances servies, AVANT/APRÈS extinction.

Les vigilances (signaux non-francs préservés par M34 : accès, pente, surface, bâti partiel,
OSM, + contraintes franches PPR/SAFER/…) sont SERVIES depuis les tables cascade
(`cascade_results` pour le chemin legacy/exports via build_resume ; `dryrun_cascade_results`
pour la fiche web servie via lines/flags), JAMAIS depuis `parcel_evaluations.status` (colonne
= verdict legacy mort depuis M34). Ce dump capture leur SOURCE exacte sur TOUT le parc, pour
PROUVER mécaniquement que l'extinction du rail `status` ne perd/modifie/invente aucune vigilance.

Artefacts (compacts, versionnables) :
  - `<prefixe>_digest.csv` : une ligne (idu, n_vigilances, sha256) par parcelle ayant ≥1
    vigilance — le diff avant/après pointe EXACTEMENT toute parcelle dont l'ensemble de
    vigilances a changé (attendu : aucune).
  - `<prefixe>_global.txt` : SHA256 global du dump ORDONNÉ complet + nb de lignes — preuve
    d'intégrité en une ligne (avant == après ⟺ source de vigilances byte-identique).

Usage : PYTHONPATH=src python qa/m37/dump_vigilances.py <prefixe>   (ex. qa/m37/vigilances_avant)
"""
from __future__ import annotations

import csv
import hashlib
import sys

from sqlalchemy import text

from labuse.db import session_factory

PREFIXE = sys.argv[1] if len(sys.argv) > 1 else "qa/m37/vigilances_avant"

# Lignes cascade qui PEUVENT alimenter une vigilance servie (cf. api/resume._vigilance +
# fiche web lines/flags) : la couche declassement (downgrade_reason) et tout signal
# franc/non-franc HARD_EXCLUDE/SOFT_FLAG, sur les DEUX tables cascade. Ordre déterministe.
_SQL = """
WITH src AS (
  SELECT p.idu, 'cascade_results'::text AS tbl, cr.layer_name, cr.result,
         coalesce(cr.severity, '') AS severity, cr.detail
  FROM cascade_results cr JOIN parcels p ON p.id = cr.parcel_id
  WHERE cr.layer_name = 'declassement' OR cr.result IN ('HARD_EXCLUDE', 'SOFT_FLAG')
  UNION ALL
  SELECT p.idu, 'dryrun_cascade_results', cr.layer_name, cr.result,
         coalesce(cr.severity, ''), cr.detail
  FROM dryrun_cascade_results cr JOIN parcels p ON p.id = cr.parcel_id
  WHERE cr.run_label = :run
    AND (cr.layer_name = 'declassement' OR cr.result IN ('HARD_EXCLUDE', 'SOFT_FLAG'))
)
SELECT idu, tbl, layer_name, result, severity, detail
FROM src
ORDER BY idu, tbl, layer_name, result, severity, detail
"""


def main() -> int:
    db = session_factory()()
    rows = db.execute(text(_SQL), {"run": "q_v8_calibre"}).all()
    db.close()

    glob = hashlib.sha256()
    per_idu: dict[str, list[str]] = {}
    for idu, tbl, layer, result, sev, detail in rows:
        line = f"{idu}\x1f{tbl}\x1f{layer}\x1f{result}\x1f{sev}\x1f{detail}"
        glob.update(line.encode("utf-8"))
        glob.update(b"\n")
        per_idu.setdefault(idu, []).append(line)

    with open(f"{PREFIXE}_digest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["idu", "n_vigilances", "sha256"])
        for idu in sorted(per_idu):
            bloc = "\n".join(per_idu[idu])
            w.writerow([idu, len(per_idu[idu]),
                        hashlib.sha256(bloc.encode("utf-8")).hexdigest()])

    with open(f"{PREFIXE}_global.txt", "w", encoding="utf-8") as f:
        f.write(f"lignes={len(rows)}\nparcelles={len(per_idu)}\nsha256={glob.hexdigest()}\n")

    print(f"{len(rows)} lignes · {len(per_idu)} parcelles → {PREFIXE}_digest.csv + _global.txt")
    print(f"sha256 global : {glob.hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
