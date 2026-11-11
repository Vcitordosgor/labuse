#!/usr/bin/env python
"""EXIGU-FIX-1 — répartition V2 (statut × bande) des terrain_exigu > 1000 m² APRÈS correction.

Lit les pids du census gt1000, lance l'Analyse V2 LIVE (enrich=compute_residuel fix ON) et tallie
statut + bande (ferme sinon provisoire). Shardé. Lecture seule.
Usage : SHARD=0 NSHARD=3 python scripts/exigu_fix_1_v2.py
"""
import glob
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
os.environ["LABUSE_EXIGU_FIX"] = "1"

from sqlalchemy.orm import sessionmaker                                   # noqa: E402
from labuse.db import make_engine                                        # noqa: E402
from labuse.scoring.scenarios_v2_build import analyse_scenarios_payload  # noqa: E402

SHARD = int(os.environ.get("SHARD", "0"))
NSHARD = int(os.environ.get("NSHARD", "1"))

pids = []
for fp in glob.glob(os.path.join(os.path.dirname(__file__), "..", "reports", "data",
                                 "exigu_mesure_gt1000_*.jsonl")):
    for line in open(fp):
        if line.strip():
            pids.append(json.loads(line)["pid"])
pids = [p for i, p in enumerate(sorted(set(pids))) if i % NSHARD == SHARD]

s = sessionmaker(bind=make_engine(url=os.environ["LABUSE_DATABASE_URL"]), future=True)()
statut = defaultdict(int)
bande = defaultdict(int)          # ferme si présente, sinon provisoire (TO_VERIFY) — « — » si aucune
CH = 300
for i in range(0, len(pids), CH):
    chunk = pids[i:i + CH]
    pl = analyse_scenarios_payload(s, chunk, enrich=True, limit=len(chunk))
    for d in pl["parcelles"]:
        statut[d["statut"]] += 1
        b = d["bande"] or d["bande_provisoire"] or "—"
        bande[b] += 1
    sys.stderr.write(f"[v2 shard {SHARD}] {min(i+CH,len(pids))}/{len(pids)}\n")
s.close()
out = {"shard": SHARD, "n": len(pids), "par_statut": dict(statut), "par_bande": dict(bande)}
outpath = os.path.join(os.path.dirname(__file__), "..", "reports", "data", f"exigu_v2_{SHARD}.json")
json.dump(out, open(outpath, "w"), ensure_ascii=False, indent=0)
sys.stderr.write(f"[v2 shard {SHARD}] FINI {json.dumps(out, ensure_ascii=False)}\n")
