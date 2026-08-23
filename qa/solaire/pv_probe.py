#!/usr/bin/env python
"""SOLAIRE M2 Phase 1 — essai empirique de la détection PV (ortho_pv.py, V0 colorimétrique).

Le cache ortho ayant été purgé, on RE-ACQUIERT les tuiles des parcelles échantillon (WMS BD ORTHO
20 cm 2025), on découpe l'emprise de chaque parcelle, et on assemble des PLANCHES à étiqueter
visuellement (vérité terrain = l'œil). On croise l'étiquette avec la détection stockée
(ortho_detections type='pv') → matrice vrais/faux positifs & négatifs.

Échantillon (oversampling car le PV est rare) :
  · GROUPE A « détecté » : parcelles avec une détection PV → mesure la PRÉCISION ;
  · GROUPE B « grands toits » : emprise bâtie ≥ 800 m² (cibles installateur) → mesure le RECALL
    (les PV réels qu'un détecteur DOIT voir) et le contexte de faux positifs.

Étapes : (1) `python qa/solaire/pv_probe.py select` → planches + manifest ; (2) je lis les planches et
remplis les labels ; (3) `python qa/solaire/pv_probe.py score labels.json` → matrice.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

import cv2
import httpx
from sqlalchemy import text

from labuse.db import session_scope
from labuse.ingestion.ortho_tiles import _cfg, _fetch_tile, tile_path, cache_dir

OUT = os.path.dirname(__file__)
CROPS = os.path.join(OUT, "pv_crops")
TILE_M, PX = 512, 2560
MPP = TILE_M / PX
N_A, N_B = 30, 30           # détectés / grands toits
THUMB = 300                 # px par vignette
COLS = 4                    # planche 4 colonnes


def _tile_of(s, idu):
    r = s.execute(text("""
        SELECT t.tile_id FROM ortho_tiles t JOIN parcels p ON p.idu = :i
        WHERE ST_Contains(t.geom, ST_Transform(p.centroid, 2975)) LIMIT 1"""), {"i": idu}).scalar()
    return r


def select_sample():
    cache_dir().mkdir(parents=True, exist_ok=True)
    os.makedirs(CROPS, exist_ok=True)
    with session_scope() as s:
        detected = [dict(r) for r in s.execute(text("""
            SELECT DISTINCT ON (d.idu) d.idu, round(d.confiance::numeric, 2)::float conf,
                   round(d.surface_m2) surf
            FROM ortho_detections d JOIN parcels p ON p.idu = d.idu
            WHERE d.type = 'pv' AND d.idu IS NOT NULL
            ORDER BY d.idu, d.confiance DESC
            LIMIT 400""")).mappings().all()]
        # spread par confiance
        detected.sort(key=lambda x: x["conf"] or 0)
        step = max(1, len(detected) // N_A)
        grp_a = detected[::step][:N_A]
        det_idus = {d["idu"] for d in detected}
        grp_b = [dict(r) for r in s.execute(text("""
            SELECT p.idu, b.emprise_bati_m2 emprise
            FROM p_model_bati b JOIN parcels p ON p.idu = b.idu
            WHERE b.emprise_bati_m2 >= 800
            ORDER BY b.emprise_bati_m2 DESC LIMIT 400""")).mappings().all()]
        # grands toits NON déjà dans A, échantillonnés régulièrement
        grp_b = [g for g in grp_b if g["idu"] not in {d["idu"] for d in grp_a}]
        step_b = max(1, len(grp_b) // N_B)
        grp_b = grp_b[::step_b][:N_B]
        sample = ([{**d, "grp": "A_detecte", "detecte": True} for d in grp_a]
                  + [{**g, "grp": "B_grandtoit", "detecte": g["idu"] in det_idus,
                      "conf": None, "surf": None} for g in grp_b])
        # tuiles + bbox parcelle
        for it in sample:
            it["tile"] = _tile_of(s, it["idu"])
            pb = s.execute(text("SELECT ST_XMin(g) x0,ST_YMin(g) y0,ST_XMax(g) x1,ST_YMax(g) y1 "
                                "FROM (SELECT geom_2975 g FROM parcels WHERE idu=:i) t"),
                           {"i": it["idu"]}).mappings().first()
            it["bbox"] = [pb["x0"], pb["y0"], pb["x1"], pb["y1"]] if pb else None
    sample = [it for it in sample if it["tile"] and it["bbox"]]
    # fetch tuiles manquantes
    tids = sorted({it["tile"] for it in sample if not tile_path(it["tile"]).exists()})
    cfg = _cfg()

    async def fetch():
        async with httpx.AsyncClient(headers={"User-Agent": "labuse/ortho-974"}) as c:
            sem = asyncio.Semaphore(4)
            async def one(t):
                async with sem:
                    return await _fetch_tile(c, cfg, t)
            return await asyncio.gather(*(one(t) for t in tids))
    if tids:
        res = asyncio.run(fetch())
        print(f"tuiles fetchées : {sum(res)}/{len(tids)}")
    # crops + montages
    manifest = []
    imgs_cache: dict = {}
    for i, it in enumerate(sample):
        tp = tile_path(it["tile"])
        if it["tile"] not in imgs_cache:
            imgs_cache[it["tile"]] = cv2.imread(str(tp))
        img = imgs_cache[it["tile"]]
        if img is None:
            continue
        xmin, ymin = (int(v) for v in it["tile"].split("_"))
        x0, y0, x1, y1 = it["bbox"]
        m = 50
        px0 = max(0, int((min(x0, x1) - xmin) / MPP) - m)
        px1 = min(PX, int((max(x0, x1) - xmin) / MPP) + m)
        py0 = max(0, int((ymin + TILE_M - max(y0, y1)) / MPP) - m)
        py1 = min(PX, int((ymin + TILE_M - min(y0, y1)) / MPP) + m)
        crop = img[py0:py1, px0:px1]
        if crop.size == 0:
            continue
        crop = cv2.resize(crop, (THUMB, THUMB), interpolation=cv2.INTER_AREA)
        tag = f"#{i} {'DET' if it['detecte'] else '---'}"
        cv2.rectangle(crop, (0, 0), (THUMB - 1, 16), (0, 0, 0), -1)
        cv2.putText(crop, tag, (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        it["crop_idx"] = i
        it["_crop"] = crop
        manifest.append({k: it[k] for k in ("crop_idx", "idu", "grp", "detecte", "conf", "surf")})
    # planches
    valid = [it for it in sample if "_crop" in it]
    per = COLS * 3
    for pi in range(0, len(valid), per):
        chunk = valid[pi:pi + per]
        rows_img = []
        for r in range(0, len(chunk), COLS):
            line = [c["_crop"] for c in chunk[r:r + COLS]]
            while len(line) < COLS:
                line.append(cv2.copyMakeBorder(line[0] * 0, 0, 0, 0, 0, cv2.BORDER_CONSTANT))
            rows_img.append(cv2.hconcat(line))
        planche = cv2.vconcat(rows_img)
        cv2.imwrite(f"{CROPS}/planche_{pi // per}.png", planche)
        print(f"planche_{pi // per}.png : {len(chunk)} vignettes")
    json.dump(manifest, open(f"{OUT}/pv_manifest.json", "w"), ensure_ascii=False, indent=1)
    print(f"manifest : {len(manifest)} parcelles · détectés {sum(m['detecte'] for m in manifest)}")


def score(labels_path):
    man = {m["crop_idx"]: m for m in json.load(open(f"{OUT}/pv_manifest.json"))}
    labels = json.load(open(labels_path))   # {crop_idx: "pv"|"non"|"?"}
    tp = fp = tn = fn = amb = 0
    for idx, lab in labels.items():
        m = man.get(int(idx))
        if not m:
            continue
        if lab == "?":
            amb += 1
            continue
        truth = lab == "pv"
        det = m["detecte"]
        if det and truth:
            tp += 1
        elif det and not truth:
            fp += 1
        elif not det and truth:
            fn += 1
        else:
            tn += 1
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    print(f"N labellisés={tp+fp+tn+fn} (ambigus écartés={amb})")
    print(f"  TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"  PRÉCISION={'%.0f%%' % (100*prec) if prec is not None else 'n/a'} "
          f"· RECALL={'%.0f%%' % (100*rec) if rec is not None else 'n/a'}")
    seuil = 0.85
    if prec is not None:
        print(("✅ précision ≥ 85 %" if prec >= seuil else "❌ précision < 85 % — STOP (filtre qui ment)"))


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "score":
        score(sys.argv[2])
    else:
        select_sample()
