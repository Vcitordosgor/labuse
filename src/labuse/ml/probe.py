"""Cascade de juges (Lot 8 révisé, GO Vic 11/07) — Étage 1 : probe linéaire.

Backbone vision GELÉ (DINOv2 ViT-S/14, torch.hub, CPU — MPS indisponible sur
macOS 13.0) → embeddings des crops des candidats piscine → régression logistique
entraînée sur les verdicts jeu='train' (1 093), MESURÉE sur le jeu SANCTUARISÉ
jeu='validation' (300, intouchable — jamais vu par l'entraînement ni la calibration).

Critère d'arrêt de Vic : précision ≥ 90 % en conservant ≥ 80 % des vrais sur les
300. Atteint → c'est notre juge, STOP cascade. Sinon → Étage 2 (juge VLM).

Artefacts : data/ml/{crops/, embeddings.npy, ids.npy, probe_logreg.joblib,
rapport_probe.json} — les crops servent aussi aux étages suivants.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import _repo_root
from ..ingestion.ortho_tiles import tile_path

M_PER_PX = 0.2
MARGE_M = 6.0     # contexte autour du bbox de détection (le juge voit les abords)
CROP_PX = 224


def ml_dir() -> Path:
    p = _repo_root() / "data" / "ml"
    (p / "crops").mkdir(parents=True, exist_ok=True)
    return p


def extraire_crops(session: Session, *, type_: str = "piscine", log=print) -> dict[str, int]:
    """Crop 224×224 centré sur chaque détection (bbox + 6 m), depuis le cache tuiles."""
    rows = session.execute(text("""
        SELECT d.id, d.tile_id, ST_XMin(d.geom_2975) x0, ST_YMin(d.geom_2975) y0,
               ST_XMax(d.geom_2975) x1, ST_YMax(d.geom_2975) y1
        FROM ortho_detections d WHERE d.type = :t ORDER BY d.tile_id
    """), {"t": type_}).all()
    done = skip = 0
    cache: dict[str, np.ndarray | None] = {}
    for r in rows:
        out = ml_dir() / "crops" / f"{r.id}.jpg"
        if out.exists():
            done += 1
            continue
        if r.tile_id not in cache:
            cache.clear()  # une tuile à la fois (RAM 8 Go) — rows triées par tuile
            p = tile_path(r.tile_id)
            cache[r.tile_id] = cv2.imread(str(p)) if p.exists() else None
        img = cache[r.tile_id]
        if img is None:
            skip += 1
            continue
        txmin, tymin = (int(v) for v in r.tile_id.split("_"))
        tymax = tymin + img.shape[0] * M_PER_PX
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        half = max(r.x1 - r.x0, r.y1 - r.y0) / 2 + MARGE_M
        ax0 = int((cx - half - txmin) / M_PER_PX)
        ax1 = int((cx + half - txmin) / M_PER_PX)
        ay0 = int((tymax - cy - half) / M_PER_PX)
        ay1 = int((tymax - cy + half) / M_PER_PX)
        h, w = img.shape[:2]
        ax0, ay0, ax1, ay1 = max(0, ax0), max(0, ay0), min(w, ax1), min(h, ay1)
        if ax1 - ax0 < 10 or ay1 - ay0 < 10:
            skip += 1
            continue
        crop = cv2.resize(img[ay0:ay1, ax0:ax1], (CROP_PX, CROP_PX),
                          interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(out), crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
        done += 1
        if done % 2000 == 0:
            log(f"  crops {done}/{len(rows)}")
    return {"crops": done, "sans_image": skip}


def calculer_embeddings(*, batch: int = 32, log=print) -> dict[str, Any]:
    """DINOv2 ViT-S/14 gelé, CPU — embeddings 384-d de tous les crops."""
    import torch

    torch.set_num_threads(6)
    # cache hub peuplé manuellement (le check réseau de torch.hub échoue derrière
    # ce réseau alors que GitHub répond) — chargement LOCAL
    hub_dir = Path.home() / ".cache/torch/hub/facebookresearch_dinov2_main"
    model = torch.hub.load(str(hub_dir), "dinov2_vits14", source="local")
    model.eval()
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    files = sorted((ml_dir() / "crops").glob("*.jpg"), key=lambda p: int(p.stem))
    ids, embs = [], []
    buf, buf_ids = [], []

    def flush() -> None:
        if not buf:
            return
        x = torch.stack(buf)
        with torch.no_grad():
            e = model(x)
        embs.append(e.numpy())
        ids.extend(buf_ids)
        buf.clear()
        buf_ids.clear()

    import time
    t0 = time.monotonic()
    for i, f in enumerate(files):
        img = cv2.imread(str(f))
        if img is None:
            continue
        t = torch.from_numpy(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).permute(2, 0, 1).float() / 255
        buf.append((t - mean) / std)
        buf_ids.append(int(f.stem))
        if len(buf) >= batch:
            flush()
            if (i + 1) % 1600 < batch:
                log(f"  embeddings {i + 1}/{len(files)}"
                    f" ({(i + 1) / (time.monotonic() - t0):.1f}/s)")
    flush()
    E = np.concatenate(embs) if embs else np.zeros((0, 384), np.float32)
    np.save(ml_dir() / "embeddings.npy", E)
    np.save(ml_dir() / "ids.npy", np.array(ids))
    return {"n": len(ids), "dim": int(E.shape[1]) if len(ids) else 0}


def entrainer_et_mesurer(session: Session, log=print) -> dict[str, Any]:
    """Logreg sur jeu='train', mesure sur jeu='validation' (sanctuarisé).

    Sortie : la courbe précision/rappel-des-vrais sur les 300 + le verdict du
    critère Vic (précision ≥ 0,90 en gardant ≥ 0,80 des vrais).
    """
    import joblib
    from sklearn.linear_model import LogisticRegression

    E = np.load(ml_dir() / "embeddings.npy")
    ids = np.load(ml_dir() / "ids.npy")
    pos = {i: k for k, i in enumerate(ids)}
    rows = session.execute(text(
        "SELECT id, jeu, validation FROM ortho_detections"
        " WHERE type = 'piscine' AND jeu IS NOT NULL")).all()
    Xtr, ytr, Xva, yva = [], [], [], []
    for r in rows:
        k = pos.get(r.id)
        if k is None:
            continue
        (Xtr if r.jeu == "train" else Xva).append(E[k])
        (ytr if r.jeu == "train" else yva).append(1 if r.validation == "ok" else 0)
    Xtr, ytr, Xva, yva = map(np.array, (Xtr, ytr, Xva, yva))
    log(f"  train {len(ytr)} (ok {ytr.sum()}) · validation {len(yva)} (ok {yva.sum()})")
    clf = LogisticRegression(max_iter=3000, C=1.0, class_weight="balanced")
    clf.fit(Xtr, ytr)
    joblib.dump(clf, ml_dir() / "probe_logreg.joblib")
    proba = clf.predict_proba(Xva)[:, 1]
    courbe = []
    verdict = None
    for seuil in np.arange(0.30, 0.96, 0.05):
        keep = proba >= seuil
        if keep.sum() == 0:
            continue
        prec = float(yva[keep].mean())
        rappel_vrais = float(yva[keep].sum() / max(1, yva.sum()))
        courbe.append({"seuil": round(float(seuil), 2), "gardees": int(keep.sum()),
                       "precision": round(prec, 3), "rappel_vrais": round(rappel_vrais, 3)})
        if verdict is None and prec >= 0.90 and rappel_vrais >= 0.80:
            verdict = courbe[-1]
    out = {"courbe": courbe, "critere_atteint": verdict is not None, "point": verdict}
    (ml_dir() / "rapport_probe.json").write_text(json.dumps(out, indent=1))
    return out
