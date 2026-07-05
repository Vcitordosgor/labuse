"""Ingestion ABF / Monuments Historiques (clôture Vague B) → spatial_layers kind='abf'  [data pure].

Source Mérimée (data.culture.gouv.fr) : 204 MH pour le 974. Pour chaque MH on génère les abords
par un TAMPON ~500 m (en 2975, métrique) → polygone → intersection parcelles.

⚠ FLAG QUALITÉ (# TODO étage 1), PAS une exclusion étage 0. Le tampon 500 m SUR-COUVRE vs le
régime réel (périmètre délimité PDA, ou 500 m AVEC covisibilité) → attr `flag` explicite
« abords ~500 m (tampon), covisibilité à instruire » (amendement Vic).

Rattachement parcelle par INTERSECTION SPATIALE du buffer UNIQUEMENT — jamais via
`cog_insee_lors_de_la_protection` (code d'époque). La géométrie fait foi (amendement Vic).
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.merimee import MerimeeConnector

SOURCE_NAME = "ABF / Monuments historiques"
BUFFER_M = 500
FLAG = "abords ~500 m (tampon), covisibilité à instruire"

# Insert : géométrie = tampon 500 m (calculé en 2975 puis reprojeté 4326) ; commune = commune de la
# parcelle CONTENANT le MH (lookup géométrique, pas cog_insee) ; le trigger remplit geom_2975.
_INSERT = text(
    "INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, commune) "
    "SELECT 'abf', :subtype, :name, "
    "  ST_Transform(ST_Buffer(ST_Transform(ST_SetSRID(ST_Point(:lon,:lat),4326),2975), :buf), 4326), "
    "  CAST(:attrs AS jsonb), :sid, "
    "  (SELECT commune FROM parcels WHERE ST_Contains(geom, ST_SetSRID(ST_Point(:lon,:lat),4326)) LIMIT 1)")


def ingest(session: Session, connector: MerimeeConnector | None = None) -> dict:
    """Ingère tous les MH du 974 en abords ABF (tampon 500 m). Idempotent (purge kind='abf' d'abord).
    Retourne des compteurs. ⚠ ÉCRIT + APPELS RÉSEAU. Ne touche PAS au score (# TODO étage 1)."""
    connector = connector or MerimeeConnector()
    sid = session.execute(text("SELECT id FROM data_sources WHERE name=:n"), {"n": SOURCE_NAME}).scalar()
    session.execute(text("DELETE FROM spatial_layers WHERE kind='abf'"))
    n = n_geo = 0
    for rec in connector.fetch_reunion():
        n += 1
        c = connector.coords(rec)
        if c is None:
            continue
        lon, lat = c
        nom = (rec.get("denomination_de_l_edifice") or rec.get("titre_editorial_de_la_notice")
               or "Monument historique")
        attrs = {
            "reference": rec.get("reference"),
            "denomination": rec.get("denomination_de_l_edifice"),
            "nature_protection": rec.get("nature_de_la_protection"),
            "commune_source": rec.get("commune_forme_editoriale"),
            "flag": FLAG,
            "buffer_m": BUFFER_M,
        }
        session.execute(_INSERT, {
            "subtype": (rec.get("nature_de_la_protection") or None), "name": str(nom)[:255],
            "lon": lon, "lat": lat, "buf": BUFFER_M, "attrs": json.dumps(attrs, ensure_ascii=False),
            "sid": sid})
        n_geo += 1
    session.execute(text("UPDATE data_sources SET last_sync_at=now() WHERE name=:n"), {"n": SOURCE_NAME})
    session.flush()
    return {"mh_total": n, "mh_geolocalises": n_geo}


def parcelles_intersectees(session: Session) -> int:
    """Nombre de parcelles intersectant AU MOINS un abord ABF (intersection géométrique du buffer)."""
    return int(session.execute(text(
        "SELECT count(DISTINCT p.id) FROM parcels p "
        "WHERE EXISTS (SELECT 1 FROM spatial_layers l WHERE l.kind='abf' "
        "  AND ST_Intersects(p.geom_2975, l.geom_2975))")).scalar() or 0)


def bilan(session: Session) -> dict:
    """Bilan ABF : total abords, parcelles intersectées, top communes."""
    total = int(session.execute(text("SELECT count(*) FROM spatial_layers WHERE kind='abf'")).scalar() or 0)
    par_commune = {r[0]: r[1] for r in session.execute(text(
        "SELECT commune, count(*) FROM spatial_layers WHERE kind='abf' GROUP BY commune "
        "ORDER BY 2 DESC NULLS LAST LIMIT 6")).all()}
    return {"abords": total, "parcelles_intersectees": parcelles_intersectees(session),
            "top_communes": par_commune}
