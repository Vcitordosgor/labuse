"""Lecteurs des archives territoriales publiées par le Cerema, projetées en RGR92."""
from __future__ import annotations

import io
import re
import zipfile
from urllib.parse import urljoin

import shapefile
from pyproj import CRS


def shapefile_2975(archive, basename):
    """Ouvre les trois composantes en mémoire et valide la projection publiée."""
    paths = {name.rsplit("/", 1)[-1]: name for name in archive.namelist()}
    def read(extension):
        return archive.read(paths[f"{basename}.{extension}"])
    if not CRS.from_wkt(read("prj").decode()).equals(CRS.from_epsg(2975), ignore_axis_order=True):
        raise ValueError(f"Projection inattendue pour {basename}")
    encoding = read("cpg").decode("ascii").strip().lower()
    if encoding == "1252":
        encoding = "cp1252"
    return shapefile.Reader(shp=io.BytesIO(read("shp")), shx=io.BytesIO(read("shx")),
                            dbf=io.BytesIO(read("dbf")), encoding=encoding)


INEC_INDEX = "https://www.geolittoral.developpement-durable.gouv.fr/telechargement-en-ligne-donnees-geolittoral-a802.html"


def profils_inec(client):
    page = client.get(INEC_INDEX)
    page.raise_for_status()
    matches = re.findall(r'href=["\']([^"\']*N_evol-INEC-(\d{4})_8periodes_reunion_espg2975_S\.zip)["\']',
                         page.text, re.IGNORECASE)
    if not matches:
        raise ValueError("Aucune archive INEC réunionnaise à huit périodes sur le site officiel")
    url, annee = max(matches, key=lambda item: int(item[1]))
    response = client.get(urljoin(str(page.url), url))
    response.raise_for_status()
    basename = f"N_evol-INEC-{annee}_P0_reunion_espg2975_S"
    with zipfile.ZipFile(io.BytesIO(response.content)) as outer:
        inner = next(s for s in outer.namelist() if s.rsplit("/", 1)[-1] == basename + ".zip")
        with zipfile.ZipFile(io.BytesIO(outer.read(inner))) as archive:
            with shapefile_2975(archive, basename) as reader:
                seen = set()
                for feature in reader.iterShapeRecords():
                    attrs = feature.record.as_dict()
                    key = attrs["ID_TRACE"]
                    if key in seen or attrs["PERIODE"] != "P0" or not attrs["code_insee"].startswith("974"):
                        raise ValueError(f"Profil INEC incohérent : {key}")
                    seen.add(key)
                    attrs.update(taux=attrs["WLS"], src=f"GéoLittoral/Cerema — INEC {annee}, P0, régression pondérée WLS")
                    yield attrs, feature.shape.__geo_interface__
                if not seen:
                    raise ValueError("Archive INEC vide")
