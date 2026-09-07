"""SOURCES-1 lot 3 — cartes de bruit stratégiques (CBS) de la DEAL, WFS Carmen.

Service RÉEL vérifié le 07/09/2026 : `Cartes_bruit_strategiques` (nœud Carmen 29, WFS 1.1.0,
GML EPSG:2975, 15 couches). On ingère les couches **type c** — les ZONES DE DÉPASSEMENT des
valeurs limites (Lden 68 dB(A) / Ln 62 dB(A), routes) pour les trois gestionnaires RN/RD/VC :
6 entités multi-polygones. Les couches type b (« secteurs affectés par le bruit ») ne sont
PAS ingérées : doublon vérifié des bandes du classement sonore déjà servies (kind
`bruit_route`, largeur réglementaire `sect_bruit` du flux Cerema). Les type a (courbes
isophones complètes) sont une cartographie d'exposition, écartées (pas d'effet réglementaire
propre — décision au compte-rendu).

⚠ Les CBS (directive 2002/49/CE, échéance 4, 2022) ne sont PAS le classement sonore
réglementaire (arrêtés préfectoraux des 14-15/12/2023) — le « i » de la couche le dit.
Stockage : spatial_layers kind='bruit_carte', subtype='<rn|rd|vc>_<lden|ln>'.
GML → GeoJSON par ogr2ogr (même mécanique que deal_carmen, lot 2). Purge kind, idempotent.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings
from .layers_ingest import _insert_layer

BASE = "http://ws.carmen.developpement-durable.gouv.fr/WFS/29/Cartes_bruit_strategiques"
SOURCE_NAME = "DEAL — cartes de bruit stratégiques (CBS)"

#: typename → subtype (gestionnaire_indicateur). Type c = dépassements des valeurs limites.
LAYERS: dict[str, str] = {
    "RN_Type_c_LDEN": "rn_lden", "RN_Type_c_LN": "rn_ln",
    "RD_Type_c_LDEN": "rd_lden", "RD_Type_c_LN": "rd_ln",
    "VC_Type_c_LDEN": "vc_lden", "VC_Type_c_LN": "vc_ln",
}

_LIBELLE = {"lden": "dépassement Lden 68 dB(A) — journée entière",
            "ln": "dépassement Ln 62 dB(A) — nuit"}


def _fetch_geojson(typename: str, client: httpx.Client, tmpdir: str) -> list[dict]:
    gml = Path(tmpdir) / f"{typename}.gml"
    gj = Path(tmpdir) / f"{typename}.json"
    with client.stream("GET", BASE, params={
            "SERVICE": "WFS", "VERSION": "1.1.0", "REQUEST": "GetFeature",
            "TYPENAME": typename}) as r:
        r.raise_for_status()
        with open(gml, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    res = subprocess.run(
        ["ogr2ogr", "-f", "GeoJSON", "-t_srs", "EPSG:4326", "-s_srs", "EPSG:2975",
         str(gj), str(gml)],
        capture_output=True, text=True, timeout=600)
    if res.returncode != 0:
        raise RuntimeError(f"ogr2ogr {typename} : {res.stderr[:300]}")
    return json.load(open(gj)).get("features") or []


def ingest_bruit_cartes(session: Session, source_id: int | None = None,
                        run_id: int | None = None, log=print,
                        client: httpx.Client | None = None) -> dict:
    """Ingère les 6 couches type c. Purge kind='bruit_carte' (idempotent). Rend {typename: n}."""
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'bruit_carte'"))
    out: dict[str, int] = {}
    own = client is None
    c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 300.0),
                               headers={"User-Agent": constants.USER_AGENT},
                               follow_redirects=True)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            for typename, sub in LAYERS.items():
                feats = _fetch_geojson(typename, c, tmpdir)
                n = 0
                gest, indic = sub.split("_")
                nom = f"CBS {gest.upper()} — {_LIBELLE[indic]}"
                for f in feats:
                    g = f.get("geometry")
                    if not g:
                        continue
                    _insert_layer(session, "bruit_carte", sub, nom, g, source_id, None,
                                  run_id,
                                  attrs={"typename": typename, "indicateur": indic,
                                         "gestionnaire": gest.upper(),
                                         "source": "DEAL Réunion — CBS échéance 4 (2022), "
                                                   "WFS Carmen"})
                    n += 1
                out[typename] = n
                log(f"  {typename} : {n} entité(s) → bruit_carte/{sub}")
    finally:
        if own:
            c.close()
    session.flush()
    return out
