"""M137-U — INGESTION ZNIEFF (INPN/MNHN via Géoplateforme WFS) → spatial_layers kind='znieff'.

Zones Naturelles d'Intérêt Écologique, Faunistique et Floristique. C'est une CONTRAINTE (pas un
dispositif d'avantage) : un inventaire du patrimoine naturel qui pèse en instruction (études
d'impact renforcées, risque de recours), sans interdire de construire → HORS CASCADE.

  subtype = 'type I'  (secteur à fort intérêt biologique, plus sensible)
  subtype = 'type II' (grand ensemble naturel)

CONTINENTAL SEUL (portée validée) : les ZNIEFF marines sont en mer, sans intersection avec des
parcelles constructibles → EXCLUES (couches `*_mer` non lues, raison notée au catalogue).

100 % LECTURE — WFS ouvert (Licence Ouverte INPN/PatriNat). Île entière, commune=NULL (une ZNIEFF
couvre plusieurs communes, comme le Parc national). Idempotent : purge kind='znieff' puis réinsère.
Le jeu Région Réunion ODS (28 zones = type II seul, amputé) est ÉCARTÉ au profit de ce WFS complet.
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.wfs import WfsConnector

# bbox île (lon, lat, lon, lat) — la Géoplateforme en EPSG:4326 forme courte attend cet ordre.
ILE_BBOX = (55.20, -21.42, 55.90, -20.85)
# (typename WFS continental, subtype servi). Les typenames marines (*_mer) sont volontairement absents.
_LAYERS = [("patrinat_znieff1:znieff1", "type I"), ("patrinat_znieff2:znieff2", "type II")]
SOURCE_NAME = "ZNIEFF (INPN/MNHN)"


def build_znieff(session: Session, log=lambda *_: None) -> dict:
    """Ingère les ZNIEFF continentales type I + II de La Réunion. Renvoie {subtype: n}."""
    wfs = WfsConnector("geoplateforme_wfs")
    sid = session.execute(text("SELECT id FROM data_sources WHERE name = :n"),
                          {"n": SOURCE_NAME}).scalar()
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'znieff'"))
    counts: dict[str, int] = {}
    for typename, subtype in _LAYERS:
        fc = wfs.fetch_layer("geoplateforme_wfs", typename, bbox=ILE_BBOX, max_features=2000)
        n = 0
        for f in fc.get("features", []) or []:
            if not f.get("geometry"):
                continue
            p = f.get("properties") or {}
            if str(p.get("marin", "")).strip().upper() == "T":
                continue                                             # garde-fou : jamais du marin
            if str(p.get("territoire", "REU")).strip().upper() not in ("REU", ""):
                continue                                             # garde-fou : Réunion seule
            nom = (p.get("nom_site") or p.get("nom") or "ZNIEFF")[:255]
            session.execute(text(
                """INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, commune)
                   VALUES ('znieff', :s, :n,
                           ST_Force2D(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))),
                           CAST(:a AS jsonb), :sid, NULL)"""),
                {"s": subtype, "n": nom, "g": json.dumps(f["geometry"]),
                 "a": json.dumps({"id_mnhn": p.get("id_mnhn"), "url_fiche": p.get("url_fiche"),
                                  "precision": p.get("precision"), "gestionnaire": p.get("gest_site"),
                                  "type": subtype}),
                 "sid": sid})
            n += 1
        counts[subtype] = n
        log(f"  znieff {subtype}: {n}")
    session.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"), {"n": SOURCE_NAME})
    session.flush()
    return counts
