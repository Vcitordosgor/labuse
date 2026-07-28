"""Phase 4 PLU — mesures groupées (LECTURE SEULE, aucun re-run de scoring).

Méthodologie identique à qa/plu_saint_pierre_validation_b.py (campagne -33 % SP/StP/StD) :
  - pool servi = parcel_p_score_v2 run q_v7_defisc, tier <> 'ecartee', par commune ;
  - random.seed(42), échantillon 400 (distribution) + 10 parcelles étalées par zones (échantillon manuel) ;
  - passe AVANT = repli générique (resolve_zone patché -> _zone_generique, équivalent
    « commune sans YAML », plu_rules.py:178) ; passe APRÈS = moteur calibré normal ;
  - moteur complet parcel_faisabilite (géométrie réelle, clip U/AU, ER, prospect).
Différence assumée vs le script SP : le repli est forcé EN MÉMOIRE (pas de déplacement du
YAML sur disque — l'API tourne, et Saint-Paul est aussi le porteur des Hypotheses).
Sorties : un JSON par commune dans /tmp/phase4/out/.
"""
import json, os, random, statistics, sys, time

from sqlalchemy import text
from sqlalchemy.orm import Session

from labuse.db import make_engine
import labuse.faisabilite.plu_rules as pr
import labuse.faisabilite.db as fdb

OUT = "/tmp/phase4/out"
os.makedirs(OUT, exist_ok=True)

COMMUNES = [
    "Saint-Paul", "Saint-Joseph", "Saint-Louis", "Saint-Benoît", "La Possession",
    "Sainte-Marie", "L'Étang-Salé", "Petite-Île", "Le Port", "Sainte-Suzanne",
    "Sainte-Rose", "Entre-Deux", "Les Avirons", "Cilaos",
    "La Plaine-des-Palmistes", "Les Trois-Bassins", "Bras-Panon", "Salazie",
]

eng = make_engine(os.environ.get("LABUSE_DATABASE_URL",
                                 "postgresql://openclaw@localhost:5432/labuse"))

POOL_SQL = text("""
    SELECT p.id, p.idu, ST_Area(p.geom_2975) AS surf
    FROM parcel_p_score_v2 s JOIN parcels p ON p.idu = s.parcelle_id
    WHERE s.run_id = 'q_v7_defisc' AND s.tier <> 'ecartee' AND p.commune = :c
    ORDER BY p.idu""")

ZONE_SQL = text("""
    SELECT COALESCE(z.attrs->>'libelle', z.subtype, z.name) AS lib, p.id, p.idu
    FROM parcel_p_score_v2 s
    JOIN parcels p ON p.idu = s.parcelle_id
    JOIN spatial_layers z ON z.kind = 'plu_gpu_zone' AND z.commune = p.commune
         AND ST_Intersects(z.geom_2975, ST_PointOnSurface(p.geom_2975))
    WHERE s.run_id = 'q_v7_defisc' AND s.tier <> 'ecartee' AND p.commune = :c
    ORDER BY p.idu""")


def collect(session, pid):
    try:
        r = fdb.parcel_faisabilite(session, pid)
    except Exception as e:  # noqa: BLE001 — consigné, jamais masqué
        return {"err": str(e)[:120]}
    if r is None:
        return None
    ctx, f = r
    src_h = next((st.source for st in f.steps if "iveaux" in st.label), "")
    return {"zone": f.zone, "calibree": f.calibree, "constructible": f.constructible,
            "verdict": f.verdict[:110],
            "sdp": f.fourchette.get("surface_plancher_m2"),
            "hauteur_m": f.fourchette.get("hauteur_m"),
            "niveaux": f.fourchette.get("niveaux"),
            "emprise": f.fourchette.get("emprise_constructible_m2"),
            "emprise_batie": f.fourchette.get("emprise_batie_max_m2"),
            "logts": f.fourchette.get("logements_sous_sol"),
            "src_hauteur": src_h}


def run_pass(ids, repli):
    orig = fdb.resolve_zone
    if repli:
        fdb.resolve_zone = lambda code, commune=None: pr._zone_generique(code)
    out = {}
    try:
        with Session(eng) as s:
            for pid in ids:
                out[pid] = collect(s, pid)
    finally:
        fdb.resolve_zone = orig
    return out


def q(vals, p):
    vals = sorted(vals)
    if not vals:
        return None
    k = (len(vals) - 1) * p
    f, c = int(k), min(int(k) + 1, len(vals) - 1)
    return vals[f] + (vals[c] - vals[f]) * (k - f)


for commune in COMMUNES:
    slug = pr._commune_slug(commune)
    dest = f"{OUT}/{slug}.json"
    if os.path.exists(dest):
        print(f"[skip] {commune} (déjà mesurée)", flush=True)
        continue
    t0 = time.time()
    with Session(eng) as s:
        pool = s.execute(POOL_SQL, {"c": commune}).all()
        zrows = s.execute(ZONE_SQL, {"c": commune}).all()
    pool_ids = [r.id for r in pool]
    surf = {r.id: float(r.surf) for r in pool}
    idus = {r.id: r.idu for r in pool}

    # Échantillon 10 : zones triées par pool décroissant, 1 parcelle (idu min) par zone
    # en round-robin jusqu'à 10 — déterministe, vérifiable à la main.
    byz = {}
    for lib, pid, idu in zrows:
        byz.setdefault(lib, []).append(pid)
    zones_sorted = sorted(byz, key=lambda z: (-len(byz[z]), z))
    picked, rank = [], 0
    while len(picked) < min(10, len(pool_ids)) and rank < 40:
        for zlib in zones_sorted[:10]:
            plist = sorted(byz[zlib], key=lambda pid: idus.get(pid, ""))
            if rank < len(plist) and len(picked) < 10:
                if plist[rank] not in [p for _, p in picked]:
                    picked.append((zlib, plist[rank]))
        rank += 1

    random.seed(42)
    dist_ids = random.sample(pool_ids, min(400, len(pool_ids)))
    all_ids = list(dict.fromkeys([p for _, p in picked] + dist_ids))

    print(f"[{commune}] pool={len(pool_ids)} sample10={len(picked)} dist={len(dist_ids)}",
          flush=True)
    avant = run_pass(all_ids, repli=True)
    apres = run_pass(all_ids, repli=False)

    # Stats distribution (mêmes définitions que la campagne SP)
    deltas_rel, deltas_abs, sdp_av, sdp_ap = [], [], [], []
    perdants, gagnants, err = [], [], 0
    for pid in dist_ids:
        a, b = avant.get(pid), apres.get(pid)
        if not a or not b or "err" in (a or {}) or "err" in (b or {}):
            err += 1
            continue
        ca = a["constructible"] and (a["sdp"] or 0) > 0
        cb = b["constructible"] and (b["sdp"] or 0) > 0
        if ca:
            sdp_av.append(a["sdp"])
        if cb:
            sdp_ap.append(b["sdp"])
        if ca and not cb:
            perdants.append(idus[pid])
        if cb and not ca:
            gagnants.append(idus[pid])
        if ca and cb:
            deltas_abs.append(b["sdp"] - a["sdp"])
            deltas_rel.append(100.0 * (b["sdp"] - a["sdp"]) / a["sdp"])

    res = {
        "commune": commune, "pool_servi": len(pool_ids),
        "n_dist": len(dist_ids), "n_err": err,
        "echantillon10": [
            {"zone_couche": zlib, "idu": idus[pid], "surface_m2": round(surf[pid]),
             "avant": avant.get(pid), "apres": apres.get(pid)}
            for zlib, pid in picked],
        "stats": {
            "n_constructibles_avant": len(sdp_av),
            "n_constructibles_apres": len(sdp_ap),
            "sdp_mediane_avant": statistics.median(sdp_av) if sdp_av else None,
            "sdp_mediane_apres": statistics.median(sdp_ap) if sdp_ap else None,
            "n_deux_passes": len(deltas_rel),
            "delta_sdp_mediane_m2": statistics.median(deltas_abs) if deltas_abs else None,
            "delta_rel_q25_pct": q(deltas_rel, 0.25),
            "delta_rel_mediane_pct": q(deltas_rel, 0.50),
            "delta_rel_q75_pct": q(deltas_rel, 0.75),
            "delta_rel_min_pct": min(deltas_rel) if deltas_rel else None,
            "delta_rel_max_pct": max(deltas_rel) if deltas_rel else None,
            "n_perdant_constructibilite": len(perdants),
            "n_gagnant_constructibilite": len(gagnants),
            "perdants_idu": perdants[:30],
            "gagnants_idu": gagnants[:30],
        },
    }
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    st = res["stats"]
    print(f"    -> méd. rel {st['delta_rel_mediane_pct'] and round(st['delta_rel_mediane_pct'],1)} % | "
          f"perdants {st['n_perdant_constructibilite']} | gagnants {st['n_gagnant_constructibilite']} | "
          f"{time.time()-t0:.0f}s", flush=True)

print("FIN CAMPAGNE ÉCART", flush=True)
