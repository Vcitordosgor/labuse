"""SOURCES-2 lot 3 — systèmes d'endiguement et zones protégées (DEAL Réunion, Lizmap).

LE risque que la carte des aléas ne dit pas : derrière une digue, l'aléa affiché peut être
faible parce que l'ouvrage protège — mais la protection a un NIVEAU (crue de projet) et une
CLASSE, et au-delà, l'inondation est RÉSIDUELLE. Le projet Lizmap dédié de la DEAL
(`02sprinr/03digues`, vérifié live 13/09/2026) sert en WFS/GeoJSON :

· `digues_zones_protegees` (MultiLineString, 512 m par tronçon ex. « SE Rivière des
  Marsouins ») → subtype='digue' ;
· `Zones_protegee_-_Systeme_d_endiguement` (MultiPolygon) → subtype='zone_protegee', avec
  la classe de l'ouvrage (A/B/C), le niveau de protection (`N protect`, période de retour),
  les niveaux/débits de danger-protection-sûreté (NGR, m³/s), la POPULATION protégée,
  le gestionnaire et la source d'étude (ex. « Hydrétudes-EDD-décembre 2024 »).

kind='endiguement' (spatial_layers), purge par kind, idempotent. Licence Lizmap non écrite —
courrier DEAL au lot 5 (LICENCES-A-CONFIRMER.md).
"""
from __future__ import annotations

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings
from .deal_carmen import _fetch_geojson, _nettoyer_geom
from .layers_ingest import _insert_layer

BASE_DIGUES = ("https://deal974.lizmap.com/cartes/index.php/lizmap/service"
               "?repository=02sprinr&project=03digues")
SOURCE_ENDIGUEMENT = "Systèmes d'endiguement et zones protégées (DEAL Lizmap)"

_LAYERS = (
    ("digues_zones_protegees", "digue", ("layer", "Lineaire")),
    ("Zones_protegee_-_Systeme_d_endiguement", "zone_protegee",
     ("Nom", "nom_zp", "ZP", "Classe", "Commune", "Gestion", "N protect", "Pop tot SE",
      "Pop tot ZP", "Population", "Popul ERP", "NP-H mNGR", "NP-Qm3/s", "ND-H mNGR",
      "ND-Qm3/s", "NS-H mNGR", "NS-Qm3/s", "Surf-ha", "Arrete", "Source", "Observatio")),
)


def ingest_endiguement(session: Session, source_id: int | None = None,
                       run_id: int | None = None, log=print,
                       client: httpx.Client | None = None) -> dict:
    """Ingère digues + zones protégées → kind='endiguement'. Purge par kind, idempotent."""
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'endiguement'"))
    own = client is None
    c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 180.0),
                               headers={"User-Agent": constants.USER_AGENT},
                               follow_redirects=True)
    out: dict[str, int] = {}
    try:
        for typename, subtype, props in _LAYERS:
            feats = _fetch_geojson(BASE_DIGUES, typename, c)
            n = 0
            for f in feats:
                g = _nettoyer_geom(f.get("geometry")) if f.get("geometry") else None
                if not g:
                    continue
                p = f.get("properties") or {}
                nom = (p.get("Nom") or p.get("nom_zp") or p.get("layer") or typename)
                attrs = {k.lower().replace(" ", "_").replace("-", "_"): p.get(k)
                         for k in props if p.get(k) is not None}
                attrs["source"] = "DEAL Réunion — Lizmap (02sprinr/03digues)"
                attrs["typename"] = typename
                if subtype == "zone_protegee":
                    attrs["statut"] = ("zone protégée par un système d'endiguement — "
                                       "inondation RÉSIDUELLE au-delà du niveau de protection")
                _insert_layer(session, "endiguement", subtype, str(nom)[:250], g,
                              source_id, p.get("Commune"), run_id, attrs=attrs)
                n += 1
            out[subtype] = n
            log(f"  {typename} : {n} entité(s) → endiguement/{subtype}")
    finally:
        if own:
            c.close()
    session.flush()
    return out
