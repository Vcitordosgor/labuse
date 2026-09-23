#!/usr/bin/env python3
"""GABARIT-AUDIT-COUVERTURE — couverture du Gabarit sur toute l'île (lecture seule, aucune écriture).

Rejoue `build_gabarit_input` + `compute_gabarit` sur CHAQUE parcelle, en parallèle (multiprocessing,
chaque worker ouvre sa propre session avec `statement_timeout`). N'écrit RIEN en base. Agrège :
servies/bloquées (total + zone U), ventilation des causes, tableau par commune, top causes + exemples.

Usage :
  PYTHONPATH=src DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib <venv>/python scripts/gabcouv_ile.py [N_WORKERS] [SAMPLE]
    N_WORKERS : nb de process (défaut 7)   ·   SAMPLE : n'auditer qu'un échantillon aléatoire (test)
"""
from __future__ import annotations

import os
import sys
import time
from collections import Counter, defaultdict

from sqlalchemy import text

STMT_TIMEOUT = os.environ.get("GABCOUV_STMT_TIMEOUT", "20s")
CHUNK = 1200


def bucket(msg: str) -> str:
    """Regroupe un motif de blocage en cause courte et stable."""
    m = (msg or "").lower()
    if "indéterminée" in m or "hors calibrage" in m or "non calibré" in m:
        return "PLU : zone non calibrée"
    if "propose" in m:
        return "PLU : règle non validée (propose)"
    if "emprise" in m and ("non régle" in m or "non validé" in m):
        return "PLU : CES (emprise) non validée"
    if "hauteur" in m and ("non validé" in m or "non régle" in m):
        return "PLU : hauteur non validée"
    if "sans règles d'implantation" in m:
        return "PLU : zone sans règles d'implantation"
    if "2 zones constructibles" in m or "multi-ces" in m:
        return "multi-zone (≥ 2 zones constructibles)"
    if "non constructible" in m:
        return "zone A/N non constructible"
    if "non qualifiées" in m or "non classable" in m:
        return "limite non qualifiée"
    if "façade" in m:
        return "enclave (sans façade sur voie)"
    if "voie privée" in m:
        return "E2 : voie privée (citation absente)"
    if "recul" in m and ("non régle" in m or "non validé" in m):
        return "recul non validé"
    if "géométrie" in m and "indispon" in m:
        return "géométrie indisponible"
    return "autre : " + (msg or "")[:50]


def process_chunk(idus: list[str]) -> dict:
    """Worker : traite une liste d'IDU, renvoie des agrégats partiels (aucune écriture)."""
    from labuse.db import session_scope
    from labuse.gabarit.builder import build_gabarit_input
    from labuse.gabarit.engine import compute_gabarit

    served = blocked = none_ = err = 0
    fam = defaultdict(lambda: [0, 0])        # famille -> [servie, bloquée]
    commune = defaultdict(lambda: [0, 0])    # commune -> [servie, bloquée]
    causes = Counter()
    causes_u = Counter()
    examples = defaultdict(list)             # cause -> [idu, …] (max 3)

    with session_scope() as s:
        s.execute(text(f"SET statement_timeout='{STMT_TIMEOUT}'"))
        for idu in idus:
            try:
                b = build_gabarit_input(s, idu)
            except Exception:
                err += 1
                s.rollback()
                causes["erreur (timeout / exception)"] += 1
                if len(examples["erreur (timeout / exception)"]) < 3:
                    examples["erreur (timeout / exception)"].append(idu)
                continue
            if b is None:
                none_ += 1
                continue
            racc = b.raccordement or {}
            f = str(((racc.get("zone") or {}).get("famille")) or "?")
            com = str(((racc.get("parcelle") or {}).get("commune")) or "?")
            is_u = (f == "U")
            if b.blocking:
                cause = bucket(b.blocking[0])
                blocked += 1
                fam[f][1] += 1
                commune[com][1] += 1
                causes[cause] += 1
                if is_u:
                    causes_u[cause] += 1
                if len(examples[cause]) < 3:
                    examples[cause].append(idu)
            else:
                try:
                    res = compute_gabarit(b.input)
                except Exception:
                    err += 1
                    s.rollback()
                    continue
                if getattr(res, "status", None) == "ok":
                    served += 1
                    fam[f][0] += 1
                    commune[com][0] += 1
                else:
                    cause = "compute incomplet : " + str(getattr(res, "message", ""))[:40]
                    blocked += 1
                    fam[f][1] += 1
                    commune[com][1] += 1
                    causes[cause] += 1
                    if len(examples[cause]) < 3:
                        examples[cause].append(idu)
    return {"served": served, "blocked": blocked, "none": none_, "err": err,
            "fam": {k: v for k, v in fam.items()}, "commune": {k: v for k, v in commune.items()},
            "causes": dict(causes), "causes_u": dict(causes_u),
            "examples": {k: v for k, v in examples.items()}}


def _merge(dst: dict, part: dict) -> None:
    for k in ("served", "blocked", "none", "err"):
        dst[k] += part[k]
    for scope in ("fam", "commune"):
        for key, (sv, bl) in part[scope].items():
            d = dst[scope].setdefault(key, [0, 0])
            d[0] += sv
            d[1] += bl
    for key, c in part["causes"].items():
        dst["causes"][key] = dst["causes"].get(key, 0) + c
    for key, c in part["causes_u"].items():
        dst["causes_u"][key] = dst["causes_u"].get(key, 0) + c
    for key, lst in part["examples"].items():
        cur = dst["examples"].setdefault(key, [])
        for idu in lst:
            if len(cur) < 3 and idu not in cur:
                cur.append(idu)


def main() -> None:
    import multiprocessing as mp
    from labuse.db import session_scope

    n_workers = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    sample = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    zone_fam = sys.argv[3] if len(sys.argv) > 3 else None   # ex. 'U' → tire dans parcel_zone_plu.zone_fam

    with session_scope() as s:
        if zone_fam:
            # échantillon aléatoire de parcelles dont la zone DOMINANTE (parcel_zone_plu, la même que
            # l'écran) est de cette famille — définition « en zone U » côté client.
            idus = [r[0] for r in s.execute(text(
                "SELECT idu FROM parcel_zone_plu WHERE zone_fam = :f ORDER BY random() LIMIT :n"),
                {"f": zone_fam, "n": sample or 3000}).fetchall()]
        elif sample:
            idus = [r[0] for r in s.execute(text(
                "SELECT idu FROM parcels ORDER BY random() LIMIT :n"), {"n": sample}).fetchall()]
        else:
            idus = [r[0] for r in s.execute(text("SELECT idu FROM parcels ORDER BY id")).fetchall()]
    total = len(idus)
    chunks = [idus[i:i + CHUNK] for i in range(0, total, CHUNK)]
    print(f"parcelles={total}  workers={n_workers}  chunks={len(chunks)}  timeout={STMT_TIMEOUT}", flush=True)

    agg = {"served": 0, "blocked": 0, "none": 0, "err": 0,
           "fam": {}, "commune": {}, "causes": {}, "causes_u": {}, "examples": {}}
    t0 = time.time()
    done = 0
    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=n_workers) as pool:
        for part in pool.imap_unordered(process_chunk, chunks):
            _merge(agg, part)
            done += 1
            if done % 10 == 0 or done == len(chunks):
                seen = agg["served"] + agg["blocked"] + agg["none"] + agg["err"]
                dt = time.time() - t0
                eta = dt / done * (len(chunks) - done)
                print(f"  {done}/{len(chunks)} chunks | vues={seen} servies={agg['served']} "
                      f"bloquées={agg['blocked']} | {dt/60:.1f} min, ETA {eta/60:.1f} min", flush=True)
    agg["elapsed_s"] = time.time() - t0
    agg["total"] = total

    import json
    out = os.path.join(os.path.dirname(__file__), "..", "gabcouv_result.json")
    with open(out, "w") as f:
        json.dump(agg, f, ensure_ascii=False, indent=1)
    print(f"FINI en {agg['elapsed_s']/60:.1f} min → {out}", flush=True)
    print(f"servies={agg['served']} bloquées={agg['blocked']} none={agg['none']} err={agg['err']}", flush=True)


if __name__ == "__main__":
    main()
