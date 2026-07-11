"""Cascade de juges — Étage 2 : juge VLM (API Anthropic, modèle vision économique).

Prompt BINAIRE + confiance sur un crop 400 px où le candidat est entouré d'un cadre
rouge (le juge sait QUOI juger, les abords restent visibles). Batché (concurrence 4),
throttlé, reprise (verdicts persistés dans ortho_detections.juge_vlm).

Coût (Haiku 4.5, 1 $/M in · 5 $/M out ; crop 400² ≈ 213 tok + prompt ≈ 190 tok) :
mesure 300 ≈ 0,16 $ · re-score 19 899 ≈ 10-11 $. Estimé AVANT lancement (règle Vic).

Mesure sur les 300 SANCTUARISÉS uniquement — le prompt n'a jamais vu ces verdicts.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
from typing import Any

import cv2
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ingestion.ortho_tiles import tile_path
from .probe import ml_dir

MODELE = "claude-haiku-4-5-20251001"
CROP_VLM_PX = 400
MARGE_M = 10.0
M_PER_PX = 0.2

PROMPT = (
    "Extrait d'orthophotographie aérienne (20 cm/pixel, île de La Réunion). "
    "L'objet À L'INTÉRIEUR DU CADRE ROUGE est-il une piscine (bassin de baignade, "
    "enterrée ou hors-sol, même petite, eau bleue/turquoise ou verte) ? "
    "Pièges fréquents à ne PAS confondre : bâche ou toile bleue, toit en tôle bleue, "
    "voiture ou camion, trampoline, terrain de sport, conteneur, ombre portée, "
    "citerne. Réponds UNIQUEMENT en JSON strict : "
    '{"piscine": true|false, "confiance": 0.0-1.0}'
)

DDL = "ALTER TABLE ortho_detections ADD COLUMN IF NOT EXISTS juge_vlm jsonb"


def generer_crop_vlm(session: Session, det_id: int) -> bytes | None:
    """Crop 400 px, candidat encadré rouge — JPEG en mémoire (usage unitaire)."""
    r = session.execute(text("""
        SELECT d.tile_id, ST_XMin(d.geom_2975) x0, ST_YMin(d.geom_2975) y0,
               ST_XMax(d.geom_2975) x1, ST_YMax(d.geom_2975) y1
        FROM ortho_detections d WHERE d.id = :i"""), {"i": det_id}).first()
    if r is None:
        return None
    return _crop_depuis_row(r)


def _crop_depuis_row(r) -> bytes | None:
    """Même crop, SANS session (sûr en thread) — r porte tile_id/x0/y0/x1/y1."""
    p = tile_path(r.tile_id)
    img = cv2.imread(str(p)) if p.exists() else None
    if img is None:
        return None
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
    if ax1 - ax0 < 12 or ay1 - ay0 < 12:
        return None
    crop = img[ay0:ay1, ax0:ax1].copy()
    bx0 = int((r.x0 - txmin) / M_PER_PX) - ax0
    bx1 = int((r.x1 - txmin) / M_PER_PX) - ax0
    by0 = int((tymax - r.y1) / M_PER_PX) - ay0
    by1 = int((tymax - r.y0) / M_PER_PX) - ay0
    cv2.rectangle(crop, (bx0, by0), (bx1, by1), (0, 0, 255), 2)
    scale = CROP_VLM_PX / max(crop.shape[:2])
    if scale < 1:
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buf.tobytes() if ok else None


async def _juger_un(client, row) -> dict | None:
    img = await asyncio.to_thread(_crop_depuis_row, row)
    if img is None:
        return None
    b64 = base64.standard_b64encode(img).decode()
    for attempt in range(5):
        try:
            msg = await client.messages.create(
                model=MODELE, max_tokens=64,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64",
                                                 "media_type": "image/jpeg", "data": b64}},
                    {"type": "text", "text": PROMPT},
                ]}])
            raw = msg.content[0].text.strip()
            raw = raw[raw.index("{"):raw.rindex("}") + 1]
            d = json.loads(raw)
            return {"piscine": bool(d["piscine"]),
                    "confiance": float(d.get("confiance", 0.5)),
                    "modele": MODELE}
        except Exception:
            await asyncio.sleep(2 ** attempt)
    return None


def juger(session: Session, ids: list[int], *, concurrence: int = 4,
          log=print) -> dict[str, int]:
    """Juge les détections listées (reprise : celles avec juge_vlm sont sautées)."""
    import anthropic

    session.execute(text(DDL))
    session.commit()
    deja = {i for (i,) in session.execute(text(
        "SELECT id FROM ortho_detections WHERE juge_vlm IS NOT NULL"
        " AND id = ANY(:ids)"), {"ids": ids}).all()}
    a_faire = [i for i in ids if i not in deja]
    # lecture UNIQUE des géométries (aucun accès session depuis les threads/coroutines)
    rows = session.execute(text("""
        SELECT d.id, d.tile_id, ST_XMin(d.geom_2975) x0, ST_YMin(d.geom_2975) y0,
               ST_XMax(d.geom_2975) x1, ST_YMax(d.geom_2975) y1
        FROM ortho_detections d WHERE d.id = ANY(:ids)"""), {"ids": a_faire}).all()
    ok = echec = 0
    resultats: list[tuple[int, str]] = []

    async def main() -> None:
        nonlocal ok, echec
        client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        sem = asyncio.Semaphore(concurrence)

        async def one(row) -> None:
            nonlocal ok, echec
            async with sem:
                res = await _juger_un(client, row)
                if res is None:
                    echec += 1
                    return
                resultats.append((row.id, json.dumps(res)))
                ok += 1
                if ok % 100 == 0:
                    log(f"  VLM {ok}/{len(a_faire)}")

        await asyncio.gather(*(one(r) for r in rows))

    asyncio.run(main())
    for i, j in resultats:
        session.execute(text(
            "UPDATE ortho_detections SET juge_vlm = CAST(:j AS jsonb) WHERE id = :i"),
            {"j": j, "i": i})
    session.commit()
    return {"juges": ok, "echecs": echec, "deja": len(deja)}


def mesurer_sur_sanctuaire(session: Session) -> dict[str, Any]:
    """Précision/rappel du juge VLM sur les 300 sanctuarisés (jamais vus)."""
    rows = session.execute(text("""
        SELECT (validation = 'ok') AS vrai,
               (juge_vlm ->> 'piscine')::bool AS dit_piscine,
               (juge_vlm ->> 'confiance')::float AS conf
        FROM ortho_detections
        WHERE jeu = 'validation' AND juge_vlm IS NOT NULL""")).all()
    n_vrais = sum(1 for r in rows if r.vrai)
    courbe = []
    verdict = None
    for cmin in (0.0, 0.5, 0.6, 0.7, 0.8, 0.9):
        keep = [r for r in rows if r.dit_piscine and r.conf >= cmin]
        if not keep:
            continue
        prec = sum(1 for r in keep if r.vrai) / len(keep)
        rappel = sum(1 for r in keep if r.vrai) / max(1, n_vrais)
        courbe.append({"conf_min": cmin, "gardees": len(keep),
                       "precision": round(prec, 3), "rappel_vrais": round(rappel, 3)})
        if verdict is None and prec >= 0.90 and rappel >= 0.80:
            verdict = courbe[-1]
    out = {"n": len(rows), "courbe": courbe,
           "critere_atteint": verdict is not None, "point": verdict}
    (ml_dir() / "rapport_vlm.json").write_text(json.dumps(out, indent=1))
    return out
