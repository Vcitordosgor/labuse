"""Outil de validation des détections ortho (mandat wave-ortho, Lot 3 — OBLIGATOIRE).

Page locale minimaliste (aucun build front requis) : vignette ortho aléatoire avec
la détection surlignée + 50 m de contexte, boutons OK / Faux positif (raccourcis
O / F), compteur de progression et précision live. Écrit
`ortho_detections.validation` — ces annotations sont AUSSI le futur dataset
d'entraînement du Lot 8 ML (c'est le plan depuis le début).

Usage Vic : `labuse api` puis http://127.0.0.1:8000/ortho/validation (200 piscines ;
l'outil resservira tel quel pour les 150 PV du Lot 4).
"""
from __future__ import annotations

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import load_yaml_config
from ..ingestion.ortho_tiles import MILLESIME, tile_path

router = APIRouter(prefix="/ortho", tags=["ortho"])

CONTEXTE_M = 50.0
M_PER_PX = 0.2

#: prédicat SQL du profil « strict » retenu sur les 966 verdicts (79,3 % mesuré) —
#: la session de confirmation (quota) ne tire QUE dans ce profil.
SQL_PROFIL_STRICT = (
    " (d.criteres->'hsv_moyen'->>0)::float BETWEEN :ph0 AND :ph1"
    " AND (d.criteres->'hsv_moyen'->>1)::float >= :ps"
    " AND (d.criteres->'hsv_moyen'->>2)::float >= :pv"
    " AND d.surface_m2 BETWEEN :ps0 AND :ps1"
)


def _profil_params() -> dict:
    m = load_yaml_config("detection_ortho")["materialisation"]["piscine_profil_strict"]
    return {"ph0": m["hsv_h"][0], "ph1": m["hsv_h"][1], "ps": m["hsv_s_min"],
            "pv": m["hsv_v_min"], "ps0": m["surface_m2"][0], "ps1": m["surface_m2"][1]}


def get_db():
    from .app import get_db as _g
    yield from _g()


@router.get("/validation/api/suivante")
def suivante(type: str = "piscine", profil: str | None = None,
             db: Session = Depends(get_db)) -> dict:
    """profil=strict : tire UNIQUEMENT au-dessus du seuil retenu (session de
    confirmation) ; l'arrêt au quota est géré par la page (compteur de session)."""
    where, params = "", {"t": type}
    if profil == "strict" and type == "piscine":
        where = " AND " + SQL_PROFIL_STRICT
        params.update(_profil_params())
    row = db.execute(text(f"""
        SELECT d.id, d.surface_m2, d.confiance, d.criteres, p.commune
        FROM ortho_detections d LEFT JOIN parcels p ON p.idu = d.idu
        WHERE d.type = :t AND d.validation IS NULL{where}
        ORDER BY random() LIMIT 1
    """), params).mappings().first()
    stats = _stats(db, type)
    stats["quota_session"] = int(load_yaml_config("detection_ortho")
                                 .get("validation", {}).get("quota_session", 100))
    if row is None:
        return {"fini": True, **stats}
    return {"fini": False, "id": row["id"], "surface_m2": row["surface_m2"],
            "confiance": row["confiance"], "commune": row["commune"],
            "criteres": row["criteres"], **stats}


def _stats(db: Session, type_: str) -> dict:
    ok, fp = db.execute(text(
        "SELECT count(*) FILTER (WHERE validation = 'ok'),"
        " count(*) FILTER (WHERE validation = 'faux_positif')"
        " FROM ortho_detections WHERE type = :t"), {"t": type_}).one()
    total = ok + fp
    return {"valides": total, "ok": ok, "faux_positifs": fp,
            "precision": round(ok / total, 3) if total else None, "objectif": 200}


@router.get("/validation/api/vignette/{det_id}.jpg")
def vignette(det_id: int, db: Session = Depends(get_db)) -> Response:
    row = db.execute(text("""
        SELECT d.tile_id, ST_XMin(d.geom_2975) x0, ST_YMin(d.geom_2975) y0,
               ST_XMax(d.geom_2975) x1, ST_YMax(d.geom_2975) y1,
               ST_AsText(d.geom_2975) wkt
        FROM ortho_detections d WHERE d.id = :i
    """), {"i": det_id}).first()
    if row is None:
        raise HTTPException(404)
    p = tile_path(row.tile_id)
    if not p.exists():
        raise HTTPException(410, "Tuile purgée du cache — relancer labuse ortho-tiles")
    img = cv2.imread(str(p))
    txmin, tymin = (int(v) for v in row.tile_id.split("_"))
    tile_m = img.shape[0] * M_PER_PX
    tymax = tymin + tile_m

    def to_px(x: float, y: float) -> tuple[int, int]:
        return int((x - txmin) / M_PER_PX), int((tymax - y) / M_PER_PX)

    cx0, cy1 = to_px(row.x0 - CONTEXTE_M, row.y0 - CONTEXTE_M)
    cx1, cy0 = to_px(row.x1 + CONTEXTE_M, row.y1 + CONTEXTE_M)
    h, w = img.shape[:2]
    cx0, cy0 = max(0, cx0), max(0, cy0)
    cx1, cy1 = min(w, cx1), min(h, cy1)
    crop = img[cy0:cy1, cx0:cx1].copy()
    # contour de la détection (coordonnées relatives au crop)
    coords = row.wkt[len("POLYGON(("):-2].split(",")
    pts = []
    for c in coords:
        x, y = (float(v) for v in c.strip().split(" ")[:2])
        px, py = to_px(x, y)
        pts.append([px - cx0, py - cy0])
    cv2.polylines(crop, [np.array(pts, np.int32)], True, (0, 0, 255), 2)
    scale = max(1, 480 // max(1, crop.shape[0]))
    if scale > 1:
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return Response(buf.tobytes(), media_type="image/jpeg",
                    headers={"Cache-Control": "no-store"})


@router.get("/equipements/{idu}")
def equipements(idu: str, db: Session = Depends(get_db)) -> dict:
    """Badges fiche parcelle (Lot 6) : piscine, PV, CES, pente — sourcés ortho IGN."""
    row = db.execute(text("""
        SELECT pe.piscine, round(pe.piscine_surface_m2) AS piscine_m2,
               pe.piscine_confiance, pe.pv_detecte, round(pe.pv_surface_m2) AS pv_m2,
               pe.pv_probable_ces,
               t.pente_moy_deg, t.pente_non_batie_deg, t.flag_terrassement_lourd
        FROM parcels p
        LEFT JOIN parcel_equipements pe ON pe.idu = p.idu
        LEFT JOIN parcel_terrain t ON t.idu = p.idu
        WHERE p.idu = :idu
    """), {"idu": idu}).mappings().first()
    if row is None:
        raise HTTPException(404)
    return {**dict(row), "millesime": MILLESIME,
            "source": f"Détection automatique sur orthophotographie IGN {MILLESIME} — "
                      "fiabilité statistique, non contractuelle. © IGN (Licence Ouverte)."}


class VerdictIn(BaseModel):
    verdict: str  # 'ok' | 'faux_positif'


@router.post("/validation/api/{det_id}")
def valider(det_id: int, body: VerdictIn, db: Session = Depends(get_db)) -> dict:
    if body.verdict not in ("ok", "faux_positif"):
        raise HTTPException(422, "verdict : ok | faux_positif")
    n = db.execute(text(
        "UPDATE ortho_detections SET validation = :v WHERE id = :i"),
        {"v": body.verdict, "i": det_id}).rowcount
    if not n:
        raise HTTPException(404)
    db.commit()
    return {"ok": True}


_PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Validation détections — LA BUSE</title>
<style>
 body{background:#0a0f0c;color:#cfe3d6;font:14px system-ui;margin:0;display:flex;
      flex-direction:column;align-items:center;gap:14px;padding:24px}
 img{max-width:min(92vw,760px);border:1px solid #24352b;border-radius:10px;image-rendering:pixelated}
 .meta{color:#7d9488;font-size:12px} b{color:#eaf6ee}
 .btns{display:flex;gap:12px}
 button{font:600 15px system-ui;padding:12px 26px;border-radius:10px;border:0;cursor:pointer}
 .ok{background:#1f8a5b;color:#fff}.fp{background:#a33529;color:#fff}.skip{background:#2a3a31;color:#cfe3d6}
 .bar{height:6px;width:min(92vw,760px);background:#16211b;border-radius:3px;overflow:hidden}
 .bar>div{height:100%;background:#5ce6a1}
 kbd{background:#16211b;border-radius:4px;padding:1px 6px;font-size:11px}
</style></head><body>
<h3 style="margin:0">Validation piscines — ortho IGN __MILLESIME__ <span class="meta">(qualification commerciale)</span></h3>
<div class="bar"><div id="prog" style="width:0%"></div></div>
<div class="meta" id="stats">…</div>
<img id="vig" alt="vignette" src="">
<div class="meta" id="meta"></div>
<div class="btns">
  <button class="ok" onclick="verdict('ok')">✓ Piscine <kbd>O</kbd></button>
  <button class="fp" onclick="verdict('faux_positif')">✗ Faux positif <kbd>F</kbd></button>
  <button class="skip" onclick="suivante()">Passer <kbd>espace</kbd></button>
</div>
<script>
let cur=null, faites=0, quota=null;
const params=new URLSearchParams(location.search);
const profil=params.get('profil')||'';
async function suivante(){
  const d=await (await fetch('/ortho/validation/api/suivante?type=piscine'+(profil?`&profil=${profil}`:''))).json();
  quota = +(params.get('quota')||d.quota_session||100);
  const prec=d.precision==null?'—':(100*d.precision).toFixed(1)+' %';
  document.getElementById('stats').innerHTML=
    `session <b>${faites}</b>/${quota}${profil?` (profil ${profil})`:''} · total ${d.valides} · OK ${d.ok} · FP ${d.faux_positifs} · précision globale <b>${prec}</b>`;
  document.getElementById('prog').style.width=Math.min(100,100*faites/quota)+'%';
  if(faites>=quota){cur=null;document.getElementById('meta').innerHTML='<b>Quota de session atteint — merci !</b> Tu peux fermer.';
    document.getElementById('vig').src='';return}
  if(d.fini){document.getElementById('meta').textContent='Plus rien à valider dans ce profil.';return}
  cur=d.id;
  document.getElementById('vig').src=`/ortho/validation/api/vignette/${d.id}.jpg`;
  document.getElementById('meta').innerHTML=
    `#${d.id} · ${d.commune??'?'} · ~<b>${Math.round(d.surface_m2)} m²</b> · confiance ${d.confiance}`;
}
async function verdict(v){ if(cur==null)return;
  await fetch(`/ortho/validation/api/${cur}`,{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({verdict:v})});
  faites+=1;
  suivante();
}
document.addEventListener('keydown',e=>{
  if(e.key==='o'||e.key==='O')verdict('ok');
  if(e.key==='f'||e.key==='F')verdict('faux_positif');
  if(e.key===' '){e.preventDefault();suivante()}
});
suivante();
</script></body></html>"""


@router.get("/validation", response_class=HTMLResponse)
def page_validation() -> str:
    load_yaml_config("detection_ortho")  # échec franc si la config manque
    return _PAGE.replace("__MILLESIME__", MILLESIME)
