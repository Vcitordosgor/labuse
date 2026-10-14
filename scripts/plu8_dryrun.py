#!/usr/bin/env python3
"""PLU-CALIBRAGE-8 (oct.) Lot D — dry-run gabarit (LECTURE SEULE, aucune écriture).

Rejoue build_gabarit_input + compute_gabarit sur un échantillon. S'exécute dans les DEUX worktrees
(main = avant, feat/plu-calibrage-8 = après), MÊME base, MÊMES idus → diff avant/après.

  # échantillon des zones calibrées (D1) :
  LABUSE_DATABASE_URL=… DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=<worktree>/src \
      <venv>/python scripts/plu8_dryrun.py calibrees > avant|apres.json
  # témoins hors zones touchées (D2, non-régression) :
  … scripts/plu8_dryrun.py temoins > avant|apres.json   # attendu : 0 diff avant/après
"""
from __future__ import annotations

import json
import sys

from sqlalchemy import text
from labuse.db import session_scope
from labuse.gabarit.builder import build_gabarit_input
from labuse.gabarit.engine import compute_gabarit

# zones CALIBRÉES par ce mandat (insee, zone_lib des parcelles)
CAL = [
    ("97409", z) for z in ("AUb", "AUc", "AUd", "1AUc", "2AUc", "1AUb", "1AUd", "2AUd", "2AUb", "2AUe", "1AUe")
] + [("97411", z) for z in ("AUm", "AUh", "AUj")] \
  + [("97413", z) for z in ("AUA", "AUB", "AUC", "AUD", "AUE")] \
  + [("97414", z) for z in ("1AUb1", "1AUb2", "2AUb1", "2AUb2")] \
  + [("97415", "U1pru"), ("97412", "U5cvd"), ("97416", "Uep")]


def sample_idus(s, mode: str) -> list[str]:
    vals = ", ".join(f"('{i}','{z}')" for i, z in CAL)
    if mode == "calibrees":
        rows = s.execute(text(
            f"WITH cal(insee,zone) AS (VALUES {vals}) "
            "SELECT idu FROM (SELECT z.idu, row_number() OVER (PARTITION BY z.zone_lib "
            "  ORDER BY (sc.sdp_residuelle_m2>0) DESC NULLS LAST, z.idu) rn "
            " FROM parcel_zone_plu z JOIN cal ON cal.insee=substr(z.idu,1,5) AND cal.zone=z.zone_lib "
            " LEFT JOIN score_labuse sc ON sc.idu=z.idu AND sc.run_label='q_v18') q "
            "WHERE rn<=4 ORDER BY idu")).scalars().all()
    else:  # temoins : zones U/AU HORS périmètre calibré, tirage déterministe
        rows = s.execute(text(
            f"WITH cal(insee,zone) AS (VALUES {vals}) "
            "SELECT z.idu FROM parcel_zone_plu z WHERE z.zone_fam IN ('U','AU') "
            "AND NOT EXISTS (SELECT 1 FROM cal WHERE cal.insee=substr(z.idu,1,5) AND cal.zone=z.zone_lib) "
            "ORDER BY md5(z.idu) LIMIT 220")).scalars().all()
    return list(rows)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "calibrees"
    out = {}
    with session_scope() as s:
        idus = sample_idus(s, mode)
        zmap = dict(s.execute(text("SELECT idu, zone_lib FROM parcel_zone_plu WHERE idu = ANY(:ids)"),
                              {"ids": idus}).fetchall())
        for idu in idus:
            rec = {"zone": zmap.get(idu)}
            try:
                br = build_gabarit_input(s, idu)
                if br is None:
                    rec["status"] = "no_input"
                else:
                    res = compute_gabarit(br.input)
                    rec["status"] = res.status
                    rec["blocking"] = br.blocking[:2]
                    if res.status == "ok":
                        rec["implantation_m2"] = res.zoneImplantationM2
                        rec["plafond_m2"] = res.plafondEmpriseM2
                        rec["hauteur_m"] = res.hauteurReglementaireM
                        rec["egout_m"] = res.hauteurEgoutM
            except Exception as e:  # noqa: BLE001
                rec["status"] = "error"
                rec["err"] = str(e)[:120]
            out[idu] = rec
    json.dump(out, sys.stdout, ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main()
