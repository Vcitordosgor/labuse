"""SOURCES-1 lot 5 — observatoire local des loyers (ADIL 974 / AGORAH, réseau OLL).

Source vérifiée live 07/09/2026 : le jeu data.gouv « Résultats des observatoires locaux des
loyers par agglomération » (Anil/réseau OLL) diffuse « Niveau des loyers en 2024 pour l'Île
de La Réunion » (`Base_OP_2024_L9740.zip`) — l'OBSERVATOIRE DÉPARTEMENTAL (agrément
28/08/2024), résultats agrégés OUVERTS : loyer €/m² (médiane, quartiles, déciles) par ZONE
(6 zones de calcul couvrant l'île) × type d'habitat × nombre de pièces, + zonage IRIS→zone
(`L9740Zonage2024.csv`). Micro-données restreintes (fiche 15) — non demandées ici.

Maille DITE : la zone OLL (secteur), PAS la commune. 16 communes tiennent dans UNE zone ;
8 en chevauchent plusieurs (Saint-Denis 6, Saint-Pierre/Sainte-Marie 5, La Possession/
Saint-Leu/Saint-Paul/Le Tampon 4, Sainte-Suzanne 3 — mesuré au zonage). Contrôle plaquette :
médiane agglomération 10,9 €/m² (fiche 15 : 10,90) — vérifié à l'ingestion.

Tables : `oll_zonage` (insee, iris, zone) et `oll_loyers` (zone 0 = agglomération entière).
"""
from __future__ import annotations

import csv
import io
import zipfile


def _texte(zf: "zipfile.ZipFile", nom: str) -> io.StringIO:
    """Les CSV du réseau OLL mélangent les encodages (Base_OP en latin-1, zonage en UTF-8 BOM
    — mesuré) : essai utf-8-sig, repli latin-1. Jamais de caractère perdu en silence."""
    brut = zf.read(nom)
    try:
        return io.StringIO(brut.decode("utf-8-sig"))
    except UnicodeDecodeError:
        return io.StringIO(brut.decode("latin-1"))

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings

SOURCE_NAME = "Loyers OLL — ADIL Réunion / AGORAH (réseau des observatoires)"
URL_ZIP = "https://www.observatoires-des-loyers.org/datagouv/2024/Base_OP_2024_L9740.zip"
ANNEE = 2024
MILLESIME = "OLL 2024 — Île de La Réunion (L9740, agrément 28/08/2024)"

DDL = """
CREATE TABLE IF NOT EXISTS oll_zonage (
    insee  varchar(5) NOT NULL,
    iris   varchar(6) NOT NULL,
    zone   integer    NOT NULL,
    epci   varchar(16),
    annee  integer    NOT NULL,
    PRIMARY KEY (insee, iris, annee)
);
CREATE TABLE IF NOT EXISTS oll_loyers (
    annee            integer     NOT NULL,
    zone             integer     NOT NULL,          -- 0 = agglomération entière
    type_habitat     varchar(16) NOT NULL,          -- tous | Appartement | Maison
    pieces           varchar(16) NOT NULL,          -- tous | 1P | 2P | ...
    loyer_median     numeric(6,2),
    loyer_q1         numeric(6,2),
    loyer_q3         numeric(6,2),
    surface_moyenne  numeric(7,1),
    n_obs            integer,
    methode          varchar(48),
    PRIMARY KEY (annee, zone, type_habitat, pieces)
)
"""


def ensure_tables(engine) -> None:
    with engine.begin() as cx:
        for stmt in DDL.strip().split(";\n"):
            if stmt.strip():
                cx.execute(text(stmt))


def _fr(v: str | None) -> float | None:
    v = (v or "").strip().replace(",", ".")
    try:
        return float(v) if v else None
    except ValueError:
        return None


def _zone_of(code: str) -> int | None:
    """`Zone_calcul` = L9740.1.NN → zone NN ; vide = agglomération (0)."""
    code = (code or "").strip()
    if not code:
        return 0
    parts = code.split(".")
    return int(parts[-1]) if parts[-1].isdigit() else None


def ingest_oll(session: Session, *, url: str = URL_ZIP, zip_bytes: bytes | None = None,
               client: httpx.Client | None = None, log=print) -> dict:
    """Télécharge le ZIP OLL 2024, charge zonage + loyers agrégés. Rend
    {"zones", "lignes", "mediane_agglo", "communes_mono_zone"}."""
    if zip_bytes is None:
        own = client is None
        c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 120.0),
                                   headers={"User-Agent": constants.USER_AGENT},
                                   follow_redirects=True)
        try:
            r = c.get(url)
            r.raise_for_status()
            zip_bytes = r.content
        finally:
            if own:
                c.close()
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    nom_base = next(n for n in zf.namelist() if n.startswith("Base_OP") and n.endswith(".csv"))
    nom_zonage = next(n for n in zf.namelist() if "Zonage" in n and n.endswith(".csv"))
    session.execute(text("DELETE FROM oll_loyers WHERE annee = :a"), {"a": ANNEE})
    session.execute(text("DELETE FROM oll_zonage WHERE annee = :a"), {"a": ANNEE})
    # zonage IRIS → zone
    nz = 0
    for row in csv.DictReader(_texte(zf, nom_zonage), delimiter=";"):
        if not (row.get("Insee") or "").startswith("974"):
            continue
        session.execute(text(
            "INSERT INTO oll_zonage (insee, iris, zone, epci, annee) "
            "VALUES (:i, :ir, :z, :e, :a) ON CONFLICT DO NOTHING"),
            {"i": row["Insee"], "ir": (row.get("Iris") or "").zfill(4)[-4:],
             "z": int(row["Zone"]), "e": row.get("EPCI"), "a": ANNEE})
        nz += 1
    # loyers agrégés : par zone (et agglo), type × pièces « homogènes » vides = toutes catégories
    nl = 0
    mediane_agglo = None
    for row in csv.DictReader(_texte(zf, nom_base), delimiter=";"):
        zone = _zone_of(row.get("Zone_calcul"))
        if zone is None or (row.get("Zone_complementaire") or "").strip():
            continue
        # on ne garde que les lignes SANS ventilation époque/ancienneté (agrégats purs)
        if (row.get("epoque_construction_local") or row.get("epoque_construction_homogene")
                or row.get("anciennete_locataire_local") or row.get("anciennete_locataire_homogene")):
            continue
        th = (row.get("Type_habitat") or "").strip() or "tous"
        pieces = (row.get("nombre_pieces_local") or row.get("nombre_pieces_homogene") or "").strip() or "tous"
        med = _fr(row.get("loyer_median"))
        session.execute(text(
            "INSERT INTO oll_loyers (annee, zone, type_habitat, pieces, loyer_median, loyer_q1, "
            " loyer_q3, surface_moyenne, n_obs, methode) "
            "VALUES (:a, :z, :t, :p, :med, :q1, :q3, :s, :n, :meth) "
            "ON CONFLICT (annee, zone, type_habitat, pieces) DO UPDATE SET "
            " loyer_median = :med, loyer_q1 = :q1, loyer_q3 = :q3, surface_moyenne = :s, "
            " n_obs = :n, methode = :meth"),
            {"a": ANNEE, "z": zone, "t": th, "p": pieces, "med": med,
             "q1": _fr(row.get("loyer_1_quartile")), "q3": _fr(row.get("loyer_3_quartile")),
             "s": _fr(row.get("surface_moyenne")),
             "n": int(row["nombre_observations"]) if (row.get("nombre_observations") or "").isdigit() else None,
             "meth": (row.get(list(row.keys())[-1]) or "").strip() or None})
        nl += 1
        if zone == 0 and th == "tous" and pieces == "tous" and med is not None:
            mediane_agglo = med
    session.flush()
    mono = session.execute(text(
        "SELECT count(*) FROM (SELECT insee FROM oll_zonage WHERE annee = :a "
        "GROUP BY insee HAVING count(DISTINCT zone) = 1) x"), {"a": ANNEE}).scalar()
    log(f"  OLL : {nz} lignes de zonage, {nl} agrégats, médiane agglo {mediane_agglo} €/m², "
        f"{mono} communes mono-zone")
    return {"zonage": nz, "lignes": nl, "mediane_agglo": mediane_agglo,
            "communes_mono_zone": int(mono or 0)}


def oll_commune(session: Session, insee: str) -> dict | None:
    """Le loyer OLL d'une commune : la valeur de SA zone si la commune tient dans UNE zone
    OLL ('toutes catégories') ; None sinon (multi-zones — le repli DHUP est servi, le détail
    par zone reste disponible à la parcelle). Maille DITE."""
    zones = [z for (z,) in session.execute(text(
        "SELECT DISTINCT zone FROM oll_zonage WHERE insee = :i AND annee = :a"),
        {"i": insee, "a": ANNEE}).all()]
    if len(zones) != 1:
        return None
    row = session.execute(text(
        "SELECT loyer_median, loyer_q1, loyer_q3, n_obs FROM oll_loyers "
        "WHERE annee = :a AND zone = :z AND type_habitat = 'tous' AND pieces = 'tous'"),
        {"a": ANNEE, "z": zones[0]}).mappings().first()
    if row is None or row["loyer_median"] is None:
        return None
    return {"zone": zones[0], "loyer_median_eur_m2": float(row["loyer_median"]),
            "q1": float(row["loyer_q1"]) if row["loyer_q1"] is not None else None,
            "q3": float(row["loyer_q3"]) if row["loyer_q3"] is not None else None,
            "n_obs": row["n_obs"], "annee": ANNEE, "millesime": MILLESIME}


def oll_parcelle(session: Session, idu: str) -> dict | None:
    """Le loyer OLL de la ZONE de la parcelle (via l'IRIS INSEE intersecté — contours en base,
    kind iris_insee). None si IRIS ou zone introuvable."""
    row = session.execute(text(
        "SELECT z.zone FROM parcels p "
        "JOIN spatial_layers sl ON sl.kind = 'iris_insee' "
        " AND ST_Intersects(p.geom_2975, sl.geom_2975) "
        "JOIN oll_zonage z ON z.annee = :a AND z.insee = left(p.idu, 5) "
        " AND z.iris = right(coalesce(sl.attrs->>'code_iris', sl.name), 4) "
        "WHERE p.idu = :idu LIMIT 1"), {"idu": idu, "a": ANNEE}).first()
    if row is None:
        return None
    zone = int(row[0])
    r = session.execute(text(
        "SELECT loyer_median, n_obs FROM oll_loyers WHERE annee = :a AND zone = :z "
        "AND type_habitat = 'tous' AND pieces = 'tous'"), {"a": ANNEE, "z": zone}).mappings().first()
    if r is None or r["loyer_median"] is None:
        return None
    return {"zone": zone, "loyer_median_eur_m2": float(r["loyer_median"]),
            "n_obs": r["n_obs"], "annee": ANNEE, "millesime": MILLESIME}
