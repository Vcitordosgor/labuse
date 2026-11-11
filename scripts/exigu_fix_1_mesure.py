#!/usr/bin/env python
"""EXIGU-FIX-1 — mesure avant/après + diagnostic du ré-examen terrain_exigu (lecture seule).

Pour chaque parcelle de la population (shardée) :
  · lance le moteur FIX OFF  (LABUSE_EXIGU_FIX=0) → cause/raison d'ORIGINE ;
  · si la cause d'origine est `terrain_exigu`, lance le moteur FIX ON → cause/raison/SDP APRÈS,
    et mesure les métriques géométriques du ré-examen (plus grand morceau net, largeur, etc.).
Écrit une ligne JSONL par parcelle terrain_exigu(OFF) dans reports/data/exigu_mesure_<shard>.jsonl.

Usage : SHARD=0 NSHARD=6 POP=gt1000 python scripts/exigu_fix_1_mesure.py
  POP ∈ {gt1000 (>1000 m² ∩ U/AU), stored (terrain_exigu du run servi), all (U/AU-touchant)}.
Les crons/prod ne lancent jamais ce script : outil de mesure ponctuel.
"""
import json
import os
import sys
import time

from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")

from labuse.db import session_scope                                    # noqa: E402
from labuse.faisabilite.db import (parcel_faisabilite, parcel_context,  # noqa: E402
                                   _reexamen_exigu, _layer_params)
from labuse.faisabilite.zonage import resolve_zone                     # noqa: E402
from labuse.faisabilite.engine import Hypotheses                       # noqa: E402

SHARD = int(os.environ.get("SHARD", "0"))
NSHARD = int(os.environ.get("NSHARD", "1"))
POP = os.environ.get("POP", "gt1000")

POPS = {
    "gt1000": """
        SELECT DISTINCT p.id FROM parcels p
        JOIN spatial_layers z ON z.kind='plu_gpu_zone' AND z.commune=p.commune
          AND labuse_zone_famille(z.subtype)=ANY(ARRAY['U','AU']) AND ST_Intersects(z.geom_2975,p.geom_2975)
        WHERE COALESCE(p.contenance_m2,ST_Area(p.geom_2975))>1000 AND MOD(p.id, :ns) = :sh""",
    "stored": """
        SELECT r.parcel_id AS id FROM parcel_residuel r
        WHERE r.cause='terrain_exigu' AND MOD(r.parcel_id, :ns) = :sh""",
    "lt1000": """
        SELECT p.id FROM parcel_residuel r JOIN parcels p ON p.id=r.parcel_id
        WHERE r.cause='terrain_exigu' AND COALESCE(p.contenance_m2,ST_Area(p.geom_2975))<=1000
          AND MOD(p.id, :ns) = :sh
        ORDER BY md5(p.id::text) LIMIT 700""",
    "all": """
        SELECT DISTINCT p.id FROM parcels p
        JOIN spatial_layers z ON z.kind='plu_gpu_zone' AND z.commune=p.commune
          AND labuse_zone_famille(z.subtype)=ANY(ARRAY['U','AU']) AND ST_Intersects(z.geom_2975,p.geom_2975)
        WHERE MOD(p.id, :ns) = :sh""",
}


def _recul_et_qargs(session, ctx):
    """Reconstruit (recul, qargs) comme parcel_faisabilite, pour mesurer les métriques du ré-examen."""
    rules = resolve_zone(ctx.zone, ctx.commune)
    hyp = Hypotheses.charger(ctx.commune)
    recul = (float(rules.recul_limites_sep_m)
             if rules is not None and isinstance(rules.recul_limites_sep_m, (int, float))
             else hyp.recul_limites_defaut_m)
    zonage = _layer_params("zonage_plu_gpu")
    presc = _layer_params("prescription_plu")
    qargs = {"zkind": zonage.get("spatial_kind", "plu_gpu_zone"),
             "uau_fams": list(zonage.get("positive_prefixes", ["U", "AU"])),
             "pkind": presc.get("spatial_kind", "plu_gpu_prescription"),
             "er_types": [str(t) for t in presc.get("emplacement_reserve_typepsc", ["05"])],
             "ebc_types": [str(t) for t in presc.get("boise_classe_typepsc", ["01"])],
             "peb_ab": [str(z).lower() for z in _layer_params("peb").get("hard_zones", ["a", "b"])],
             "dpf_m": float(_layer_params("dpf").get("marchepied_m", 3.25)),
             "rav_m": float(_layer_params("ravine").get("buffer_m", 10))}
    return recul, qargs


def main():
    outdir = os.path.join(os.path.dirname(__file__), "..", "reports", "data")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, f"exigu_mesure_{POP}_{SHARD}.jsonl")
    with session_scope() as s:
        ids = [r[0] for r in s.execute(text(POPS[POP]), {"ns": NSHARD, "sh": SHARD}).all()]
    t0 = time.time()
    n = kept = 0
    with open(outpath, "w") as fh:
        fixon_only = os.environ.get("FIXON_ONLY") == "1"
        for pid in ids:
            n += 1
            if fixon_only:
                # Census des parcelles DÉJÀ terrain_exigu (POP=stored) : « avant » = terrain_exigu par
                # définition, on ne mesure que l'APRÈS (fix ON) — 1 seul appel moteur (2× plus rapide).
                with session_scope() as s:
                    os.environ["LABUSE_EXIGU_FIX"] = "0"  # (non utilisé ici ; le fix-ON suit)
                    r0 = (None, None)
                kept += 1
                ctx0 = f0 = None
            else:
                os.environ["LABUSE_EXIGU_FIX"] = "0"
                with session_scope() as s:
                    r0 = parcel_faisabilite(s, pid)
                if r0 is None:
                    continue
                ctx0, f0 = r0
                if f0.cause != "terrain_exigu":
                    continue                     # hors périmètre du correctif : le fix ne le touche pas
                kept += 1
            os.environ["LABUSE_EXIGU_FIX"] = "1"
            with session_scope() as s:
                ctx1, f1 = parcel_faisabilite(s, pid)
                # AUTORITAIRE : la trace que le moteur a RÉELLEMENT utilisée (recul exact, sous-zone /
                # exceptions comprises), pas une reconstruction (qui diverge sur les parcelles dont la
                # zone dominante n'est pas constructible mais porte une portion U/AU).
                rex = dict(ctx1.reexamen_exigu or {})
                decision = rex.pop("decision", "non_reexamine")
            cref = ctx0 if ctx0 is not None else ctx1          # fixon_only : repère sur le contexte fix-ON
            fref = f0 if f0 is not None else f1
            rec = {"pid": pid, "idu": cref.idu, "commune": cref.commune,
                   "surf": round(float(cref.surface_m2 or 0)), "zone": fref.zone,
                   "raison_off": (f0.exigu_raison if f0 is not None else None),
                   "cause_on": f1.cause, "raison_on": f1.exigu_raison,
                   "sdp_on": f1.fourchette.get("surface_plancher_m2"),
                   "decision": decision, "net_m2": round(rex.get("net_m2", 0) or 0),
                   "net_larg": round(rex.get("net_larg", 0) or 0, 1),
                   "parc_larg": round(rex.get("parc_larg", 0) or 0, 1),
                   "has_net": rex.get("has_net"), "valide": rex.get("valide")}
            fh.write(json.dumps(rec) + "\n")
            if kept % 200 == 0:
                fh.flush()
                sys.stderr.write(f"[shard {SHARD}] {n}/{len(ids)} vus, {kept} exigu, "
                                 f"{(time.time()-t0)/n*1000:.0f} ms/parc\n")
    sys.stderr.write(f"[shard {SHARD}] FINI {n} vus, {kept} exigu → {outpath} "
                     f"({(time.time()-t0):.0f}s)\n")


if __name__ == "__main__":
    main()
