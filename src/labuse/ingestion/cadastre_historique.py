"""RETOURS-14 S5 — CADASTRE D'ÉPOQUE : retrouver la parcelle D'ORIGINE d'un permis et la
rattacher par la GÉOMÉTRIE aux parcelles actuelles.

Problème (mesuré RETOURS-13/14) : 10 799 permis Sitadel référencent une parcelle qui n'existe
plus au cadastre courant (division/remembrement) → sans géométrie, invisibles ; le repli par
ADRESSE posé en RETOURS-13 plaçait parfois le point SUR UNE AUTRE PARCELLE (constat Vic : le
rond du PC hôtel tombait sur la parcelle boisée au sud du chantier) — un permis au mauvais
endroit est un faux fait servi. La géométrie d'époque, elle, est exacte.

Sources (vérifiées le 05/09/2026) :
· Etalab `cadastre.data.gouv.fr/data/etalab-cadastre/{millésime}/geojson/communes/974/{insee}/
  cadastre-{insee}-parcelles.json.gz` — millésimes trimestriels depuis 2017-07-06 ;
· PCI vecteur DGFiP `…/data/dgfip-pci-vecteur/2017-02-13/edigeo/feuilles/974/{insee}/
  edigeo-{insee}000{feuille}.tar.bz2` — remonte au 13/02/2017 (5 mois plus tôt : c'est là
  qu'a été retrouvée la parcelle BC0328 du PC hôtel de Sainte-Marie, divisée au 31/12/2016).
Une parcelle disparue AVANT 2017-02 reste irrécupérable (aucune archive ouverte plus ancienne)
— l'absence est comptée et dite, jamais contournée.

Rattachement (règle du mandat) : l'ancienne parcelle est intersectée avec les parcelles
actuelles ; si UNE parcelle actuelle couvre > 50 % de l'ancienne → rattachée à celle-ci ;
à cheval → rattachée à toutes (celles qui en couvrent ≥ 10 %), étiquetée « parcelle d'origine
redécoupée ». Le POINT du permis = ST_PointOnSurface de la parcelle d'origine (le vrai lieu).
Table `cadastre_historique` : référence + géométrie SEULEMENT (mandat).
"""
from __future__ import annotations

import gzip
import io
import json
import logging
import subprocess
import tarfile
import tempfile
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("labuse")

BASE_ETALAB = "https://cadastre.data.gouv.fr/data/etalab-cadastre"
BASE_PCI = "https://cadastre.data.gouv.fr/data/dgfip-pci-vecteur"
#: passes Etalab, du plus ANCIEN au plus récent (une parcelle disparue est cherchée dans le
#: millésime le plus proche de sa disparition ; l'ancien d'abord couvre les permis 2013-2017).
MILLESIMES_ETALAB = ["2017-07-06", "2019-07-01", "2021-07-01", "2023-01-01", "2025-09-01"]
MILLESIME_PCI = "2017-02-13"

#: RETOURS-21 B — BD PARCELLAIRE VECTEUR IGN, édition 974 du 27/06/2008 (archive opendatarchives,
#: SHP en RGR92 UTM 40S = EPSG:2975). C'est le SEUL millésime cadastral vecteur ANTÉRIEUR à 2017-02
#: qu'on ait trouvé après avoir regardé (PCI DGFiP ne remonte pas plus tôt ; BD PARCELLAIRE vecteur
#: gelée 2018 est POSTÉRIEURE, sans intérêt ; les couches image 2008-2013/2013-2018 sont raster,
#: sans géométrie exploitable). L'édition 2008 récupère les parcelles disparues entre 2008 et 2017
#: — MESURÉ : 1 041 des 2 391 IDU orphelins y figurent (majorité des permis 2013-2016).
BDPARC_2008_URL = ("https://files.opendatarchives.fr/professionnels.ign.fr/parcellaire-express/"
                   "BDPARCELLAIRE_1-2_VECTEUR/"
                   "BDPARCELLAIRE_1-2_VECTEUR_SHP_RGR92UTM40S_D974_2008-06-27.7z")
MILLESIME_BDPARC = "2008-06-27"

SRC_NAME = "Cadastre d'époque (Etalab / PCI vecteur DGFiP)"


def ensure_table(session: Session) -> None:
    session.execute(text(
        """CREATE TABLE IF NOT EXISTS cadastre_historique (
             idu varchar(14) NOT NULL,
             millesime varchar(10) NOT NULL,
             geom geometry(Geometry, 4326) NOT NULL,
             PRIMARY KEY (idu, millesime))"""))
    session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_cad_histo_geom ON cadastre_historique USING gist (geom)"))


def _idus_cibles(session: Session) -> dict[str, set[str]]:
    """insee → idus d'origine à retrouver (permis sans geom fiable) NON encore en historique."""
    rows = session.execute(text(
        """SELECT DISTINCT t.idu FROM sitadel_permits s,
                  jsonb_array_elements_text(s.idu_codes) AS t(idu)
           WHERE (s.geom IS NULL OR s.raw->>'geoloc' LIKE 'adresse%')
             AND NOT EXISTS (SELECT 1 FROM parcels p WHERE p.idu = t.idu)
             AND NOT EXISTS (SELECT 1 FROM cadastre_historique h WHERE h.idu = t.idu)""")).all()
    out: dict[str, set[str]] = {}
    for (idu,) in rows:
        if idu and len(idu) == 14:
            out.setdefault(idu[:5], set()).add(idu)
    return out


def _pass_etalab(session: Session, millesime: str, cibles: dict[str, set[str]], log_fn=print) -> int:
    n = 0
    with httpx.Client(follow_redirects=True, timeout=300) as c:
        for insee, idus in sorted(cibles.items()):
            if not idus:
                continue
            url = f"{BASE_ETALAB}/{millesime}/geojson/communes/974/{insee}/cadastre-{insee}-parcelles.json.gz"
            try:
                r = c.get(url)
                r.raise_for_status()
                fc = json.load(gzip.open(io.BytesIO(r.content)))
            except Exception as e:  # noqa: BLE001 — une commune qui échoue n'arrête pas le lot
                log_fn(f"  {millesime} {insee} : indisponible ({e})")
                continue
            trouves = 0
            for ft in fc.get("features", []):
                fid = ft.get("id") or ft.get("properties", {}).get("id") or ""
                if fid in idus and ft.get("geometry"):
                    session.execute(text(
                        "INSERT INTO cadastre_historique (idu, millesime, geom) VALUES "
                        "(:i, :m, ST_Force2D(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))) "
                        "ON CONFLICT DO NOTHING"),
                        {"i": fid, "m": millesime, "g": json.dumps(ft["geometry"])})
                    idus.discard(fid)
                    trouves += 1
            n += trouves
            if trouves:
                log_fn(f"  {millesime} {insee} : {trouves} parcelles d'origine retrouvées")
            session.flush()
    return n


def _feuilles_commune(client: httpx.Client, insee: str) -> list[str]:
    r = client.get(f"{BASE_PCI}/{MILLESIME_PCI}/edigeo/feuilles/974/{insee}/")
    if r.status_code != 200:
        return []
    import re
    return sorted(set(re.findall(r"edigeo-([0-9A-Z]+)\.tar\.bz2", r.text)))


def _pass_pci_edigeo(session: Session, cibles: dict[str, set[str]], log_fn=print) -> int:
    """Reliquat pré-2017-07 : feuilles EDIGEO du 13/02/2017 (les SEULES sections utiles)."""
    n = 0
    with httpx.Client(follow_redirects=True, timeout=300) as c:
        for insee, idus in sorted(cibles.items()):
            if not idus:
                continue
            sections = {i[8:10] for i in idus}
            # nom de feuille = {insee}{prefixe}{section}{n° feuille} : '97418000BC01' → section [8:10]
            feuilles = [f for f in _feuilles_commune(c, insee) if len(f) >= 12 and f[8:10] in sections]
            for feuille in feuilles:
                url = f"{BASE_PCI}/{MILLESIME_PCI}/edigeo/feuilles/974/{insee}/edigeo-{feuille}.tar.bz2"
                try:
                    r = c.get(url)
                    r.raise_for_status()
                except Exception:  # noqa: BLE001
                    continue
                with tempfile.TemporaryDirectory() as td:
                    try:
                        with tarfile.open(fileobj=io.BytesIO(r.content), mode="r:bz2") as tf:
                            tf.extractall(td)  # noqa: S202 — archive DGFiP officielle
                        thf = next(Path(td).glob("*.THF"))
                        out = Path(td) / "p.json"
                        # le CRS EDIGEO « IGNF:RGR92UTM » n'est pas résolu par PROJ → on
                        # l'impose : RGR92 / UTM 40 S = EPSG:2975 (la projection du 974).
                        subprocess.run(["ogr2ogr", "-f", "GeoJSON",
                                        "-s_srs", "EPSG:2975", "-t_srs", "EPSG:4326",
                                        str(out), str(thf), "PARCELLE_id"],
                                       check=True, capture_output=True, timeout=120)
                        fc = json.load(open(out))
                    except Exception as e:  # noqa: BLE001
                        log_fn(f"  PCI {insee}/{feuille} : illisible ({e})")
                        continue
                for ft in fc.get("features", []):
                    raw_idu = str(ft.get("properties", {}).get("IDU") or "")
                    fid = ("97" + raw_idu) if len(raw_idu) == 12 else raw_idu
                    if fid in idus and ft.get("geometry"):
                        session.execute(text(
                            "INSERT INTO cadastre_historique (idu, millesime, geom) VALUES "
                            "(:i, :m, ST_Force2D(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))) "
                            "ON CONFLICT DO NOTHING"),
                            {"i": fid, "m": MILLESIME_PCI, "g": json.dumps(ft["geometry"])})
                        idus.discard(fid)
                        n += 1
                session.flush()
            if n:
                log_fn(f"  PCI {insee} : cumul {n}")
    return n


def _pass_bdparcellaire_2008(session: Session, cibles: dict[str, set[str]], log_fn=print) -> int:
    """Reliquat pré-2008 → BD PARCELLAIRE vecteur IGN, édition 974 du 27/06/2008 (EPSG:2975).

    Une seule archive départementale (SHP). L'IDU d'une parcelle se reconstitue depuis les champs
    du fichier PARCELLE : CODE_DEP + CODE_COM + COM_ABS(préfixe) + SECTION(2) + NUMERO(4). On ne
    garde QUE les parcelles dont l'IDU est une cible (permis sans géométrie), reprojetées en 4326
    par ogr2ogr. Échec BRUYANT : si l'archive ou l'outil manque, on le DIT (on ne récupère pas moins
    en silence)."""
    import csv as _csv
    reste = {i for idus in cibles.values() for i in idus}
    if not reste:
        return 0
    n = 0
    with tempfile.TemporaryDirectory() as td:
        arch = Path(td) / "bdparc.7z"
        try:
            with httpx.Client(follow_redirects=True, timeout=600) as c:
                r = c.get(BDPARC_2008_URL)
                r.raise_for_status()
                arch.write_bytes(r.content)
        except Exception as e:  # noqa: BLE001
            log_fn(f"  BD PARCELLAIRE 2008 : archive INDISPONIBLE ({e}) — reliquat non traité, dit.")
            return 0
        try:
            import py7zr
            base = ("BDPARCELLAIRE_1-2_VECTEUR_SHP_RGR92UTM40S_D974_2008-06-27/BDPARCELLAIRE/"
                    "1_DONNEES_LIVRAISON_2020-01-00247/BDPV_1-2_SHP_RGR92UTM40S_D974/")
            with py7zr.SevenZipFile(arch, "r") as z:
                z.extract(path=td, targets=[base + "PARCELLE." + e for e in ("SHP", "SHX", "DBF", "PRJ", "CPG")])
            shp = Path(td) / base / "PARCELLE.SHP"
            gj = Path(td) / "parc.geojson"
            # reprojection 2975 → 4326 par ogr2ogr (le module s'appuie déjà sur ogr2ogr pour l'EDIGEO).
            subprocess.run(["ogr2ogr", "-f", "GeoJSON", "-t_srs", "EPSG:4326", str(gj), str(shp)],
                           check=True, capture_output=True, timeout=600)
            fc = json.load(open(gj))
        except Exception as e:  # noqa: BLE001
            log_fn(f"  BD PARCELLAIRE 2008 : illisible ({type(e).__name__}: {e}) — reliquat non traité, dit.")
            return 0
        for ft in fc.get("features", []):
            p = ft.get("properties") or {}
            insee = f"{p.get('CODE_DEP','')}{p.get('CODE_COM','')}"
            pref = (p.get("COM_ABS") or "000")
            sec = (p.get("SECTION") or "").strip().rjust(2, "0")
            num = (p.get("NUMERO") or "").rjust(4, "0")
            idu = f"{insee}{pref}{sec}{num}"
            if idu in reste and ft.get("geometry"):
                session.execute(text(
                    "INSERT INTO cadastre_historique (idu, millesime, geom) VALUES "
                    "(:i, :m, ST_Force2D(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))) "
                    "ON CONFLICT DO NOTHING"),
                    {"i": idu, "m": MILLESIME_BDPARC, "g": json.dumps(ft["geometry"])})
                reste.discard(idu)
                n += 1
        session.flush()
    log_fn(f"  BD PARCELLAIRE 2008 : {n} parcelles d'origine retrouvées (reliquat pré-2017)")
    return n


def rattacher_par_geometrie(session: Session, log_fn=print) -> dict:
    """Rattache les permis cibles à la géométrie de leur parcelle d'origine.

    geom = ST_PointOnSurface(parcelle d'origine) — le VRAI lieu du permis ; raw.geoloc dit la
    provenance ; raw.parcelles_actuelles = les parcelles actuelles couvertes (> 50 % → une seule ;
    à cheval → toutes ≥ 10 %, étiquetées « parcelle d'origine redécoupée »)."""
    n = session.execute(text("""
        WITH cible AS (
          SELECT s.id, t.idu AS idu_origine, h.geom AS g_old, h.millesime
          FROM sitadel_permits s
          JOIN LATERAL jsonb_array_elements_text(s.idu_codes) AS t(idu) ON true
          JOIN cadastre_historique h ON h.idu = t.idu
          WHERE s.geom IS NULL OR s.raw->>'geoloc' LIKE 'adresse%'),
        une AS (   -- une seule ligne par permis (la 1re parcelle d'origine retrouvée)
          SELECT DISTINCT ON (id) id, idu_origine, g_old, millesime FROM cible ORDER BY id, idu_origine),
        couverture AS (
          SELECT u.id, u.idu_origine, u.g_old, u.millesime, p.idu AS idu_actuel,
                 ST_Area(ST_Intersection(p.geom, u.g_old)) / NULLIF(ST_Area(u.g_old), 0) AS part
          FROM une u
          JOIN parcels p ON ST_Intersects(p.geom, u.g_old)),
        rattache AS (
          SELECT id, idu_origine, g_old, millesime,
                 jsonb_agg(idu_actuel ORDER BY part DESC) FILTER (WHERE part >= 0.10) AS actuelles,
                 max(part) AS part_max
          FROM couverture GROUP BY id, idu_origine, g_old, millesime)
        UPDATE sitadel_permits s
        SET geom = ST_PointOnSurface(r.g_old),
            raw = s.raw || jsonb_build_object(
              'geoloc', 'parcelle d''origine (cadastre ' || r.millesime || ')',
              'parcelle_origine', r.idu_origine,
              'parcelles_actuelles', COALESCE(r.actuelles, '[]'::jsonb),
              'origine_redecoupee',
              (r.part_max IS NULL OR r.part_max < 0.50
               OR jsonb_array_length(COALESCE(r.actuelles, '[]'::jsonb)) > 1))
        FROM rattache r WHERE s.id = r.id""")).rowcount
    session.flush()
    reste = session.execute(text(
        "SELECT count(*) FROM sitadel_permits WHERE geom IS NULL")).scalar()
    log_fn(f"  rattachement géométrique : {n} permis posés sur leur parcelle d'origine · "
           f"{reste} encore sans geom")
    return {"rattaches_geometrie": int(n), "restants_sans_geom": int(reste)}


def demoter_adresses_restantes(session: Session, log_fn=print) -> int:
    """S5.1 — un permis SANS parcelle certaine ne s'affiche JAMAIS comme un point : les replis
    d'adresse restants (non récupérés par la géométrie) quittent `geom` (→ geom_approx, conservé
    pour mémoire) — ils sortent des points de carte, des proximités et de la viabilisation ;
    la liste les montre avec « localisation approximative (adresse) »."""
    session.execute(text(
        "ALTER TABLE sitadel_permits ADD COLUMN IF NOT EXISTS geom_approx geometry(Point, 4326)"))
    n = session.execute(text(
        """UPDATE sitadel_permits
           SET geom_approx = geom, geom = NULL,
               raw = raw || jsonb_build_object('geoloc',
                 'localisation approximative (adresse) — parcelle d''origine irrécupérable, non affichée en point')
           WHERE raw->>'geoloc' LIKE 'adresse%' AND geom IS NOT NULL""")).rowcount
    session.flush()
    log_fn(f"  points d'adresse démis : {n} (jamais un point sur une parcelle incertaine)")
    return int(n)


def marquer_reliquat_sans_localisation(session: Session, log_fn=print) -> int:
    """RETOURS-21 B — le reliquat vraiment non localisable (ni géométrie, ni repli d'adresse) DOIT
    le DIRE dans la liste (mandat S5/étape 4) : jamais un point, mais jamais muet non plus. Les
    permis restés `geom IS NULL` SANS `geoloc` (ceux que ni le cadastre d'époque ni la BD
    PARCELLAIRE 2008 n'ont pu localiser) reçoivent une mention honnête. Idempotent."""
    n = session.execute(text(
        """UPDATE sitadel_permits
           SET raw = raw || jsonb_build_object('geoloc',
                 'sans localisation — parcelle d''origine absente des cadastres disponibles '
                 '(2008 et 2017→2025), non affichée en point')
           WHERE geom IS NULL AND (raw->>'geoloc') IS NULL""")).rowcount
    session.flush()
    log_fn(f"  reliquat sans localisation marqué : {n} permis (mention en liste, jamais un point)")
    return int(n)


def run(log_fn=print) -> dict:
    from ..db import session_scope
    stats: dict = {}
    with session_scope() as s:
        ensure_table(s)
        cibles = _idus_cibles(s)
        total = sum(len(v) for v in cibles.values())
        log_fn(f"S5 — {total} parcelles d'origine à retrouver ({len(cibles)} communes)")
        for m in MILLESIMES_ETALAB:
            stats[f"etalab_{m}"] = _pass_etalab(s, m, cibles, log_fn)
        stats["pci_2017_02"] = _pass_pci_edigeo(s, cibles, log_fn)
        stats["bdparcellaire_2008"] = _pass_bdparcellaire_2008(s, cibles, log_fn)  # RETOURS-21 B
        stats["irrecuperables"] = sum(len(v) for v in cibles.values())
        stats.update(rattacher_par_geometrie(s, log_fn))
        stats["adresses_demises"] = demoter_adresses_restantes(s, log_fn)
        stats["reliquat_marque"] = marquer_reliquat_sans_localisation(s, log_fn)  # RETOURS-21 B
    log_fn(f"✓ S5 : {json.dumps(stats, ensure_ascii=False)}")
    return stats


if __name__ == "__main__":
    run()
