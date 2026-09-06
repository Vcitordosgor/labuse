"""SOURCES-1 lot 1 — DPU et PEB depuis les « informations » du GPU (API Carto `info-surf`).

Deux sources du mandat SOURCES-1, un seul canal amont (vérifié live 06/09/2026) :

· **DPU** (`dpu_perimetres`) — typeinf CNIG « 04 » = « Droit de préemption urbain » (+ variante
  renforcée). Publié dans les annexes du PLU de CHAQUE commune (partition DU_<insee>) : on filtre
  par partition pour attribuer le périmètre à SA commune — une commune sans typeinf 04 n'a PAS
  publié son DPU au GPU (état « non publié », listé au rapport d'ingestion, jamais un zéro).
  Stockage : spatial_layers kind='dpu', subtype='dpu'|'dpu_renforce'.

· **PEB** (`peb_dgac`) — typeinf CNIG « 27 » = « Plan d'exposition au bruit ». Zones A/B/C/D dans
  `txt`. Le PEB de Roland-Garros est republié par les annexes des PLU des communes concernées ;
  celui de Pierrefonds est ABSENT du GPU au 06/09/2026 (vérifié : 0 typeinf 27 sur la bbox de
  Saint-Pierre) — couverture partielle DITE. Les zones couvrent plusieurs communes → couche
  d'ÎLE (commune = NULL), dédoublonnée par (idurba, zone, empreinte géométrie).
  Stockage : spatial_layers kind='peb', subtype='a'|'b'|'c'|'d' (zone), attrs.zone en clair.

Requête par bbox de commune (même canal que sup_gpu.py), purge par kind avant réinsertion
(idempotent). Plafond API Carto 1000 features/réponse : compté et loggé si atteint.
"""
from __future__ import annotations

import hashlib
import json

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings
from .layers_ingest import _insert_layer
from .run_all import REUNION_COMMUNES

BASE = "https://apicarto.ign.fr/api/gpu"
SOURCE_DPU = "GPU — droit de préemption urbain (info-surf)"
SOURCE_PEB = "PEB — plans d'exposition au bruit (DGAC via annexes GPU)"
TYPEINF_DPU = "04"
TYPEINF_PEB = "27"
CAP_API = 1000

_NOM_PAR_INSEE = dict(REUNION_COMMUNES)


def _bbox_geom(session: Session, commune: str) -> dict | None:
    row = session.execute(text(
        "SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e) FROM "
        "(SELECT ST_Extent(geom) AS e FROM parcels WHERE commune = :c) x"), {"c": commune}).first()
    if not row or row[0] is None:
        return None
    x1, y1, x2, y2 = row
    return {"type": "Polygon",
            "coordinates": [[[x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1]]]}


def _peb_zone(txt: str | None, libelle: str | None) -> str | None:
    """Zone PEB depuis `txt` (« A »…« D » observés). Jamais devinée : None si illisible."""
    z = (txt or "").strip().upper()
    return z.lower() if z in {"A", "B", "C", "D"} else None


def ingest_gpu_infos(session: Session, run_id: int | None = None,
                     source_id_dpu: int | None = None, source_id_peb: int | None = None,
                     log=print, client: httpx.Client | None = None) -> dict:
    """Ingère DPU (par commune, filtré partition) et PEB (île, dédoublonné) via info-surf.

    Rend {"dpu": n, "peb": n, "dpu_non_publie": [noms], "peb_zones": {...},
    "peb_illisibles": n}. Purge kinds 'dpu' et 'peb' avant (idempotent)."""
    session.execute(text("DELETE FROM spatial_layers WHERE kind IN ('dpu', 'peb')"))
    n_dpu = 0
    dpu_communes: set[str] = set()
    peb_vus: set[str] = set()
    peb_zones: dict[str, int] = {}
    n_peb = 0
    peb_illisibles = 0
    own = client is None
    c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 90.0),
                               headers={"User-Agent": constants.USER_AGENT},
                               follow_redirects=True)
    try:
        for insee, nom in REUNION_COMMUNES:
            geom = _bbox_geom(session, nom)
            if geom is None:
                continue
            r = c.get(f"{BASE}/info-surf", params={"geom": json.dumps(geom)})
            if r.status_code >= 500:
                log(f"  ⚠ {nom} info-surf : HTTP {r.status_code}, sauté")
                continue
            r.raise_for_status()
            feats = r.json().get("features") or []
            if len(feats) >= CAP_API:
                log(f"  ⚠ {nom} info-surf : {len(feats)} features = plafond API — possible troncature")
            for f in feats:
                p = f.get("properties") or {}
                g = f.get("geometry")
                if not g:
                    continue
                ti = (p.get("typeinf") or "").strip()
                lib = (p.get("libelle") or "").strip()
                if ti == TYPEINF_DPU:
                    # attribution stricte par partition : le DPU d'une commune vient de SON PLU
                    if (p.get("partition") or "") != f"DU_{insee}":
                        continue
                    sub = "dpu_renforce" if "renforc" in lib.lower() else "dpu"
                    _insert_layer(session, "dpu", sub, lib or "Droit de préemption urbain",
                                  g, source_id_dpu, nom, run_id,
                                  attrs={"libelle": lib, "txt": p.get("txt"),
                                         "idurba": p.get("idurba"),
                                         "partition": p.get("partition"),
                                         "typeinf": ti})
                    n_dpu += 1
                    dpu_communes.add(nom)
                elif ti == TYPEINF_PEB:
                    zone = _peb_zone(p.get("txt"), lib)
                    if zone is None:
                        peb_illisibles += 1
                        log(f"  ⚠ PEB sans zone lisible (txt={p.get('txt')!r}) — écarté, jamais deviné")
                        continue
                    # dédoublonnage île (les bboxes voisines revoient les mêmes zones)
                    empreinte = hashlib.md5(
                        (str(p.get("idurba")) + "|" + zone + "|"
                         + json.dumps(g, sort_keys=True)).encode()).hexdigest()
                    if empreinte in peb_vus:
                        continue
                    peb_vus.add(empreinte)
                    _insert_layer(session, "peb", zone, lib or "Plan d'exposition au bruit",
                                  g, source_id_peb, None, run_id,
                                  attrs={"libelle": lib, "zone": zone.upper(),
                                         "idurba": p.get("idurba"),
                                         "partition": p.get("partition"),
                                         "typeinf": ti})
                    n_peb += 1
                    peb_zones[zone.upper()] = peb_zones.get(zone.upper(), 0) + 1
    finally:
        if own:
            c.close()
    session.flush()
    non_publie = sorted(set(_NOM_PAR_INSEE.values()) - dpu_communes)
    return {"dpu": n_dpu, "peb": n_peb, "dpu_communes": sorted(dpu_communes),
            "dpu_non_publie": non_publie, "peb_zones": peb_zones,
            "peb_illisibles": peb_illisibles}
