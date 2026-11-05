"""SOURCES-2 lot 3 — BAN PLUS : le lien adresse ↔ bâtiment ↔ parcelle (IGN, Géoplateforme).

Le jeu `BAN PLUS` (data.gouv.fr/datasets/ban-plus, IGN) sert en WFS Géoplateforme la couche
`BAN-PLUS:lien_adresse_bati` : id adresse BAN ↔ id bâtiment BD TOPO (`cleabs`) ↔ IDU de
parcelle, avec le type de lien (GEO…) et les cardinalités (nb_adr, nb_bat). Mesuré live
13/09/2026 : **745 874 liens** sur l'emprise Réunion.

Ce que ça débloque : l'adresse d'un logement mène à SON bâtiment — et par
`rnb_batiments.ext_bdtopo` (le RNB rattache déjà chaque bâtiment BD TOPO à son ID-RNB), le
lien remonte à l'**ID-RNB, clé de jointure DPE ↔ RPLS ↔ BAN** demandée par le mandat. La
colonne `rnb_id` est résolue à l'ingestion (jointure locale, aucun appel réseau de plus).

Table `ban_plus_liens` (réservoir déclaré au registre). Filtrage 974 AU PLUS TÔT : la moisson
WFS est bornée à la bbox de l'île ET filtrée sur idu 974xx. Idempotent (troncature + réinsert).
"""
from __future__ import annotations

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings

SOURCE_BAN_PLUS = "BAN PLUS — lien adresse ↔ bâtiment (IGN)"
WFS = "https://data.geopf.fr/wfs/ows"
TYPENAME = "BAN-PLUS:lien_adresse_bati"
BBOX_974 = "-21.45,55.15,-20.8,55.9,urn:ogc:def:crs:EPSG::4326"
PAGE = 5000

DDL = """
CREATE TABLE IF NOT EXISTS ban_plus_liens (
  id_adr varchar(40) NOT NULL,
  id_bat varchar(40) NOT NULL,
  idu varchar(20),
  type_lien varchar(24),
  nb_adr integer,
  nb_bat integer,
  rnb_id varchar(16),
  ingere_le timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (id_adr, id_bat)
);
CREATE INDEX IF NOT EXISTS ix_ban_plus_idu ON ban_plus_liens (idu);
CREATE INDEX IF NOT EXISTS ix_ban_plus_rnb ON ban_plus_liens (rnb_id)
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        for stmt in DDL.split(";"):
            if stmt.strip():
                c.execute(text(stmt))


def ingest_ban_plus(session: Session, log=print, client: httpx.Client | None = None) -> dict:
    """Moisson WFS paginée (count/startIndex) → ban_plus_liens, puis résolution rnb_id par
    `rnb_batiments.ext_bdtopo`. ⚠ ÉCRIT + RÉSEAU (Géoplateforme seule).

    INJECTION-SOLIDE-2 — passe par `remplacer_servie` : la moisson WFS remplit une STAGING puis swap
    ATOMIQUE (plus de `TRUNCATE ban_plus_liens` à vif). Une moisson vide / interrompue (réseau) est
    REFUSÉE → la version servie est conservée. Unicité (id_adr, id_bat)."""
    from . import injection_sure
    own = client is None
    c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 300.0),
                               headers={"User-Agent": constants.USER_AGENT},
                               follow_redirects=True)
    stats = {"n": 0, "hors_974": 0}

    def charger(conn, staging):
        start = 0
        try:
            while True:
                r = c.get(WFS, params={
                    "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
                    "TYPENAMES": TYPENAME, "COUNT": PAGE, "STARTINDEX": start,
                    "OUTPUTFORMAT": "application/json", "BBOX": BBOX_974})
                r.raise_for_status()
                feats = r.json().get("features") or []
                if not feats:
                    break
                rows = []
                for f in feats:
                    p = f.get("properties") or {}
                    idu = p.get("idu")
                    if idu and not idu.startswith("974"):
                        stats["hors_974"] += 1    # bbox déborde l'île ? jamais servi — filtre au plus tôt
                        continue
                    rows.append({"a": p.get("id_adr"), "b": p.get("id_bat"), "i": idu,
                                 "t": p.get("type_lien"), "na": p.get("nb_adr"),
                                 "nb": p.get("nb_bat")})
                if rows:
                    conn.execute(text(
                        f'INSERT INTO "{staging}" (id_adr, id_bat, idu, type_lien, nb_adr, nb_bat) '
                        "VALUES (:a, :b, :i, :t, :na, :nb) ON CONFLICT (id_adr, id_bat) DO NOTHING"),
                        rows)
                    stats["n"] += len(rows)
                log(f"  page {start}-{start + len(feats)} : {len(rows)} lien(s)")
                if len(feats) < PAGE:
                    break
                start += PAGE
        finally:
            if own:
                c.close()

    injection_sure.remplacer_servie(
        session, table="ban_plus_liens", charger_staging=charger, a_geometrie=False,
        couverture_974_min=0, delta_max_pct=50.0, like_including="ALL",
        alerter=injection_sure.alerte_injection("ban_plus_liens", SOURCE_BAN_PLUS))
    n, hors_974 = stats["n"], stats["hors_974"]
    # rnb_id : le bâtiment BD TOPO du lien est rattaché à son ID-RNB par le réservoir RNB local.
    n_rnb = 0
    if session.execute(text("SELECT to_regclass('rnb_batiments')")).scalar() is not None:
        # jointure par unnest (hash join) — le `= ANY(ext_bdtopo)` naïf est un produit croisé
        # 746 k × 414 k qui ne finit pas (mesuré 13/09/2026, annulé après 28 min).
        n_rnb = session.execute(text(
            "UPDATE ban_plus_liens bl SET rnb_id = m.rnb_id FROM ("
            "  SELECT rnb_id, unnest(ext_bdtopo) AS id_bat FROM rnb_batiments"
            ") m WHERE bl.id_bat = m.id_bat")).rowcount
    session.execute(text(
        "UPDATE data_sources SET last_sync_at = now() WHERE name = :n"), {"n": SOURCE_BAN_PLUS})
    session.flush()
    return {"liens": n, "hors_974": hors_974, "avec_rnb": n_rnb}
