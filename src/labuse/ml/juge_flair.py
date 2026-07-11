"""Cascade de juges — Étage 3 : FLAIR-INC (IGN) en INFÉRENCE PURE, local, 0 €.

Modèle IGNF/FLAIR-INC_rgb_15cl_resnet34-unet (licence Etalab 2.0 — usage commercial
OK, attribution IGN), entraîné sur l'ortho aérienne française à 20 cm avec une
classe native « swimming pool » (index 12, nomenclature 15 classes). Nos tuiles
SONT de la BD ORTHO 20 cm : distribution d'entrée idéale, aucun fine-tune requis.

Protocole (discipline sanctuaire inchangée) :
1. crops 256×256 NATIFS (sans cadre rouge, sans resize) centrés sur chaque candidat ;
2. inférence CPU → score = fraction des pixels du bbox du candidat classés piscine ;
3. seuil choisi sur jeu='train' UNIQUEMENT ;
4. UNE mesure sur les 300 sanctuarisés.
"""
from __future__ import annotations

import json
from typing import Any

import cv2
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ingestion.ortho_tiles import tile_path
from .probe import ml_dir

M_PER_PX = 0.2
CROP_PX = 256          # 51 m de contexte natif — divisible par 32 (UNet)
CLASSE_PISCINE = 12    # « swimming pool », nomenclature FLAIR-1 (tête 19 classes), 0-indexé


def _charger_modele():
    import segmentation_models_pytorch as smp
    import torch

    model = smp.Unet("resnet34", classes=19, in_channels=3, encoder_weights=None)
    sd = torch.load(ml_dir() / "flair" / "flair_rgb_15cl.pth",
                    map_location="cpu", weights_only=False)
    if "state_dict" in sd:
        sd = sd["state_dict"]
    sd = {k.removeprefix("model.seg_model."): v for k, v in sd.items()
          if k.startswith("model.seg_model.")}
    model.load_state_dict(sd)
    model.eval()
    return model


def _lots_candidats(session: Session, ids: list[int]) -> list:
    return session.execute(text("""
        SELECT d.id, d.tile_id, ST_XMin(d.geom_2975) x0, ST_YMin(d.geom_2975) y0,
               ST_XMax(d.geom_2975) x1, ST_YMax(d.geom_2975) y1
        FROM ortho_detections d WHERE d.id = ANY(:ids) ORDER BY d.tile_id
    """), {"ids": ids}).all()


def _crop_natif(img, r, txmin: int, tymax: float):
    """(crop 256 natif, bbox pixel du candidat dans le crop) — None si hors tuile."""
    cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
    px = int((cx - txmin) / M_PER_PX) - CROP_PX // 2
    py = int((tymax - cy) / M_PER_PX) - CROP_PX // 2
    h, w = img.shape[:2]
    px, py = max(0, min(w - CROP_PX, px)), max(0, min(h - CROP_PX, py))
    crop = img[py:py + CROP_PX, px:px + CROP_PX]
    if crop.shape[:2] != (CROP_PX, CROP_PX):
        return None
    bx0 = int((r.x0 - txmin) / M_PER_PX) - px
    bx1 = int((r.x1 - txmin) / M_PER_PX) - px
    by0 = int((tymax - r.y1) / M_PER_PX) - py
    by1 = int((tymax - r.y0) / M_PER_PX) - py
    clamp = lambda v: max(0, min(CROP_PX - 1, v))  # noqa: E731
    return crop, (clamp(bx0), clamp(by0), clamp(bx1), clamp(by1))


def scorer(session: Session, ids: list[int], *, batch: int = 8, log=print) -> dict[str, int]:
    """Score FLAIR (fraction de pixels piscine du bbox) → ortho_detections.juge_flair."""
    import torch

    torch.set_num_threads(6)
    session.execute(text(
        "ALTER TABLE ortho_detections ADD COLUMN IF NOT EXISTS juge_flair real"))
    session.commit()
    deja = {i for (i,) in session.execute(text(
        "SELECT id FROM ortho_detections WHERE juge_flair IS NOT NULL AND id = ANY(:ids)"),
        {"ids": ids}).all()}
    rows = [r for r in _lots_candidats(session, [i for i in ids if i not in deja])]
    model = _charger_modele()
    tile_img, tile_id = None, None
    buf, meta = [], []
    done = 0
    import time
    t0 = time.monotonic()

    def flush() -> None:
        nonlocal done
        if not buf:
            return
        x = torch.from_numpy(np.stack(buf)).permute(0, 3, 1, 2).float() / 255.0
        # normalisation ImageNet — VÉRIFIÉE sur piscines connues (frac 0,5-0,8 vs 0,0 en /255)
        mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
        x = (x - mean) / std
        with torch.no_grad():
            pred = model(x).argmax(1).numpy()
        for k, (det_id, bbox) in enumerate(meta):
            bx0, by0, bx1, by1 = bbox
            zone = pred[k, by0:by1 + 1, bx0:bx1 + 1]
            frac = float((zone == CLASSE_PISCINE).mean()) if zone.size else 0.0
            session.execute(text(
                "UPDATE ortho_detections SET juge_flair = :f WHERE id = :i"),
                {"f": round(frac, 4), "i": det_id})
        done += len(buf)
        buf.clear()
        meta.clear()
        if done % 400 < batch:
            session.commit()
            log(f"  FLAIR {done}/{len(rows)} ({done / (time.monotonic() - t0):.1f}/s)")

    for r in rows:
        if r.tile_id != tile_id:
            flush()
            tile_id = r.tile_id
            p = tile_path(tile_id)
            tile_img = cv2.imread(str(p)) if p.exists() else None
        if tile_img is None:
            continue
        txmin, tymin = (int(v) for v in tile_id.split("_"))
        out = _crop_natif(tile_img, r, txmin, tymin + tile_img.shape[0] * M_PER_PX)
        if out is None:
            continue
        crop, bbox = out
        buf.append(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        meta.append((r.id, bbox))
        if len(buf) >= batch:
            flush()
    flush()
    session.commit()
    return {"scores": done, "deja": len(deja)}


def choisir_seuil_sur_train(session: Session) -> dict[str, Any]:
    rows = session.execute(text("""
        SELECT (validation = 'ok') vrai, juge_flair f FROM ortho_detections
        WHERE jeu = 'train' AND juge_flair IS NOT NULL""")).all()
    n_vrais = sum(1 for r in rows if r.vrai)
    meilleurs = []
    for seuil in (0.02, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50):
        keep = [r for r in rows if r.f >= seuil]
        if not keep:
            continue
        meilleurs.append({"seuil": seuil, "n": len(keep),
                          "precision": round(sum(1 for r in keep if r.vrai) / len(keep), 3),
                          "rappel_vrais": round(sum(1 for r in keep if r.vrai) / max(1, n_vrais), 3)})
    return {"train_n": len(rows), "courbe_train": meilleurs}


def mesurer_sur_sanctuaire(session: Session, seuil: float) -> dict[str, Any]:
    rows = session.execute(text("""
        SELECT (validation = 'ok') vrai, juge_flair f FROM ortho_detections
        WHERE jeu = 'validation' AND juge_flair IS NOT NULL""")).all()
    n_vrais = sum(1 for r in rows if r.vrai)
    keep = [r for r in rows if r.f >= seuil]
    prec = sum(1 for r in keep if r.vrai) / max(1, len(keep))
    rappel = sum(1 for r in keep if r.vrai) / max(1, n_vrais)
    out = {"seuil": seuil, "n_sanctuaire": len(rows), "gardees": len(keep),
           "precision": round(prec, 3), "rappel_vrais": round(rappel, 3),
           "critere_atteint": bool(prec >= 0.90 and rappel >= 0.80)}
    (ml_dir() / "rapport_flair.json").write_text(json.dumps(out, indent=1))
    return out
