"""Cartes de bruit stratégiques des routes non concédées, deux contours de type C."""
from __future__ import annotations

import io
import json
import re
import zipfile

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings
from .archives_littoral import shapefile_2975

BASE = ("https://www.data.gouv.fr/api/1/datasets/cartes-de-bruit-strategiques-des-reseaux-"
        "routiers-et-ferroviaires-non-concedes-directive-europeenne-2002-49-ce/")
SOURCE_NAME = "DEAL — cartes de bruit stratégiques (CBS)"


def _contours(client):
    catalogue = client.get(BASE)
    catalogue.raise_for_status()
    candidates = []
    for resource in catalogue.json()["resources"]:
        found = re.fullmatch(r"CBS\s*(\d{4})\s+Département\s+974\.zip", resource["title"], flags=re.I)
        if found:
            candidates.append((int(found[1]), resource.get("last_modified") or "", resource["url"]))
    if not candidates:
        raise ValueError("Archive CBS du département 974 absente du catalogue Cerema")
    year, _, url = max(candidates)
    response = client.get(url)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        seen = set()
        for indic, code, threshold in (("LD", "lden", "68"), ("LN", "ln", "62")):
            name = f"N_BRUIT_ZBR_INFRA_R_C_{indic}_S_974"
            with shapefile_2975(archive, name) as reader:
                if not len(reader):
                    raise ValueError(f"Couche CBS vide : {name}")
                for rec in reader.iterShapeRecords():
                    attrs = {k.lower(): v for k, v in rec.record.as_dict().items() if v is not None}
                    key = attrs["idzonbruit"]
                    if (key in seen or attrs["annee"] != str(year) or attrs["codedept"] != "974"
                            or attrs["cbstype"] != "C" or attrs["indicetype"] != indic
                            or str(attrs["legende"]) != threshold):
                        raise ValueError(f"Zone CBS incohérente : {key}")
                    seen.add(key)
                    attrs.update(typename=name, indicateur=code,
                                 source=f"Cerema / DEAL Réunion — CBS {year}, routes non concédées")
                    yield (name, "route_" + code, f"CBS routières — dépassement {code} {threshold} dB(A)",
                           attrs, rec.shape.__geo_interface__)


def ingest_bruit_cartes(session: Session, source_id: int | None = None,
                        run_id: int | None = None, log=print,
                        client: httpx.Client | None = None) -> dict:
    own = client is None
    client = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 300),
                                    headers={"User-Agent": constants.USER_AGENT}, follow_redirects=True)
    try:
        records = list(_contours(client))
    finally:
        if own:
            client.close()
    if source_id is None:
        source_id = session.execute(text("SELECT id FROM data_sources WHERE name=:name"),
                                    {"name": SOURCE_NAME}).scalar_one()
    counts = {}
    with session.begin_nested():
        session.execute(text("DELETE FROM spatial_layers WHERE kind='bruit_carte' AND data_source_id=:sid"),
                        {"sid": source_id})
        for layer, sub, name, attrs, geometry in records:
            session.execute(text("""INSERT INTO spatial_layers
                      (kind,subtype,name,geom,attrs,data_source_id,ingestion_run_id)
                    VALUES ('bruit_carte',:sub,:name,ST_Transform(ST_Multi(ST_CollectionExtract(
                      ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g),2975)),3)),4326),
                      CAST(:attrs AS jsonb),:sid,:run)"""),
                            {"sub": sub, "name": name, "g": json.dumps(geometry),
                             "attrs": json.dumps(attrs), "sid": source_id, "run": run_id})
            counts[layer] = counts.get(layer, 0) + 1
        session.flush()
    for layer, count in counts.items():
        log(f"{layer} : {count} zones")
    return counts
