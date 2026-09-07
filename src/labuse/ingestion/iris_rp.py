"""SOURCES-1 lot 6 — recensement INSEE par IRIS (bases infra-communales 2022).

Deux bases officielles (vérifiées live 07/09/2026, parution 16/10/2025, géographie au
01/01/2024 — la même que les Contours IRIS déjà servis) :
· « Logement en 2022 » — base-ic-logement-2022_csv.zip (25 Mo national, 344 IRIS 974) :
  logements, vacants, maison/appart, statut d'occupation (PROP/LOC/HLM), âge du bâti
  (périodes d'achèvement ACH), ménages, personnes des résidences principales ;
· « Population en 2022 » — base-ic-evol-struct-pop-2022_csv.zip (22 Mo, 344 IRIS 974) :
  population par tranches d'âge.

Table `iris_rp` (une ligne par IRIS 974, colonnes CURÉES — la liste vit ici et dans la fiche
de règle regles/iris_quartier.py). Dérivées SERVIES (documentées, jamais recalculées ailleurs) :
taille moyenne des ménages = NPER_RP / RP ; vacance = LOGVAC / LOG ; part bâti ≤ 1990 =
Σ ACH(1919, 1945, 1970, 1990) / ACHTOT ; part 60 ans et + = (POP6074 + POP75P) / POP.
La maille est DITE partout (IRIS, « quartier » INSEE) — l'IRIS AFFINE la commune, il ne la
remplace pas (commune_insee_logement reste la vérité communale).
"""
from __future__ import annotations

import csv
import io
import zipfile

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings

SOURCE_NAME = "INSEE RP2022 — bases IRIS (logement, population)"
URL_LOGEMENT = "https://www.insee.fr/fr/statistiques/fichier/8647012/base-ic-logement-2022_csv.zip"
URL_POPULATION = ("https://www.insee.fr/fr/statistiques/fichier/8647014/"
                  "base-ic-evol-struct-pop-2022_csv.zip")
MILLESIME = "RP2022 (parution 16/10/2025, géographie 01/01/2024)"

#: colonnes INSEE retenues (base logement) → colonne de la table
_LOG_COLS = {
    "P22_LOG": "log", "P22_RP": "rp", "P22_LOGVAC": "logvac",
    "P22_MAISON": "maison", "P22_APPART": "appart",
    "P22_RP_PROP": "rp_prop", "P22_RP_LOC": "rp_loc", "P22_RP_LOCHLMV": "rp_lochlmv",
    "P22_RP_ACHTOT": "ach_tot", "P22_RP_ACH1919": "ach_1919", "P22_RP_ACH1945": "ach_1945",
    "P22_RP_ACH1970": "ach_1970", "P22_RP_ACH1990": "ach_1990", "P22_RP_ACH2005": "ach_2005",
    "P22_RP_ACH2019": "ach_2019",
    "P22_MEN": "men", "P22_NPER_RP": "nper_rp",
}
_POP_COLS = {
    "P22_POP": "pop", "P22_POP0014": "pop_0014", "P22_POP1529": "pop_1529",
    "P22_POP3044": "pop_3044", "P22_POP4559": "pop_4559", "P22_POP6074": "pop_6074",
    "P22_POP75P": "pop_75p",
}

DDL = """
CREATE TABLE IF NOT EXISTS iris_rp (
    iris       varchar(9) PRIMARY KEY,
    insee      varchar(5) NOT NULL,
    millesime  varchar(64) NOT NULL,
    log        double precision, rp double precision, logvac double precision,
    maison     double precision, appart double precision,
    rp_prop    double precision, rp_loc double precision, rp_lochlmv double precision,
    ach_tot    double precision, ach_1919 double precision, ach_1945 double precision,
    ach_1970   double precision, ach_1990 double precision, ach_2005 double precision,
    ach_2019   double precision,
    men        double precision, nper_rp double precision,
    pop        double precision, pop_0014 double precision, pop_1529 double precision,
    pop_3044   double precision, pop_4559 double precision, pop_6074 double precision,
    pop_75p    double precision,
    maj_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_iris_rp_insee ON iris_rp (insee)
"""


def ensure_tables(engine) -> None:
    with engine.begin() as cx:
        for stmt in DDL.strip().split(";"):
            if stmt.strip():
                cx.execute(text(stmt))


def _lire_zip_csv(client: httpx.Client, url: str) -> list[dict]:
    r = client.get(url)
    r.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    nom = next(n for n in zf.namelist() if n.upper().endswith(".CSV") and not n.startswith("meta"))
    with zf.open(nom) as f:
        rows = list(csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"), delimiter=";"))
    return rows


def _num(v):
    try:
        return float(v) if v not in (None, "", "N/A") else None
    except ValueError:
        return None


def ingest_iris_rp(session: Session, *, url_logement: str = URL_LOGEMENT,
                   url_population: str = URL_POPULATION,
                   client: httpx.Client | None = None, log=print) -> dict:
    """Télécharge les deux bases nationales, garde le 974 (COM commence par 974), upsert par
    IRIS. Rend {"iris": n, "communes": n, "sans_pop": n}."""
    own = client is None
    c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 300.0),
                               headers={"User-Agent": constants.USER_AGENT},
                               follow_redirects=True)
    try:
        rows_log = [r for r in _lire_zip_csv(c, url_logement) if (r.get("COM") or "").startswith("974")]
        rows_pop = [r for r in _lire_zip_csv(c, url_population) if (r.get("COM") or "").startswith("974")]
    finally:
        if own:
            c.close()
    pop_par_iris = {r["IRIS"]: r for r in rows_pop}
    n = 0
    for r in rows_log:
        iris = r["IRIS"]
        vals: dict = {"iris": iris, "insee": r["COM"], "millesime": MILLESIME}
        for src, dst in _LOG_COLS.items():
            vals[dst] = _num(r.get(src))
        p = pop_par_iris.get(iris) or {}
        for src, dst in _POP_COLS.items():
            vals[dst] = _num(p.get(src))
        cols = list(vals)
        session.execute(text(
            f"INSERT INTO iris_rp ({', '.join(cols)}, maj_at) "
            f"VALUES ({', '.join(':' + k for k in cols)}, now()) "
            "ON CONFLICT (iris) DO UPDATE SET "
            + ", ".join(f"{k} = :{k}" for k in cols if k != "iris")
            + ", maj_at = now()"), vals)
        n += 1
    session.flush()
    d = session.execute(text(
        "SELECT count(DISTINCT insee), count(*) FILTER (WHERE pop IS NULL) FROM iris_rp")).one()
    log(f"  IRIS RP2022 : {n} IRIS · {d[0]} communes · {d[1]} sans volet population")
    return {"iris": n, "communes": int(d[0]), "sans_pop": int(d[1])}


def _derives(r: dict) -> dict:
    """Dérivées SERVIES (formules de la fiche de règle — un seul point de calcul)."""
    def pct(a, b):
        return round(100.0 * a / b, 1) if (a is not None and b) else None
    taille = (round(r["nper_rp"] / r["rp"], 2)
              if (r.get("nper_rp") is not None and r.get("rp")) else None)
    anciens = sum(v for v in (r.get("ach_1919"), r.get("ach_1945"),
                              r.get("ach_1970"), r.get("ach_1990")) if v is not None)
    return {
        "vacance_pct": pct(r.get("logvac"), r.get("log")),
        "part_bati_avant_1990_pct": pct(anciens if r.get("ach_tot") else None, r.get("ach_tot")),
        "taille_menages": taille,
        "part_60_plus_pct": pct(((r.get("pop_6074") or 0) + (r.get("pop_75p") or 0))
                                if r.get("pop") else None, r.get("pop")),
        "part_locataires_pct": pct(r.get("rp_loc"), r.get("rp")),
        "part_hlm_pct": pct(r.get("rp_lochlmv"), r.get("rp")),
    }


def stats_iris(session: Session, code_iris: str) -> dict | None:
    """Le quartier INSEE (IRIS) : chiffres bruts + dérivées documentées. None si non ingéré."""
    r = session.execute(text("SELECT * FROM iris_rp WHERE iris = :i"),
                        {"i": code_iris}).mappings().first()
    if r is None:
        return None
    r = dict(r)
    nom = session.execute(text(
        "SELECT name FROM spatial_layers WHERE kind = 'iris_insee' AND subtype = :i LIMIT 1"),
        {"i": code_iris}).scalar()
    return {"iris": code_iris, "nom": nom, "millesime": r["millesime"],
            "logements": int(r["log"]) if r.get("log") is not None else None,
            "vacants": int(r["logvac"]) if r.get("logvac") is not None else None,
            "menages": int(r["men"]) if r.get("men") is not None else None,
            "habitants": int(r["pop"]) if r.get("pop") is not None else None,
            **_derives(r),
            "source": "INSEE — recensement de la population, bases IRIS (maille quartier)"}


def iris_de_parcelle(session: Session, idu: str) -> str | None:
    """Le code IRIS de la parcelle (contours IRIS déjà servis, kind iris_insee)."""
    return session.execute(text(
        "SELECT sl.subtype FROM parcels p JOIN spatial_layers sl "
        "ON sl.kind = 'iris_insee' AND ST_Intersects(sl.geom_2975, ST_PointOnSurface(p.geom_2975)) "
        "WHERE p.idu = :i LIMIT 1"), {"i": idu}).scalar()


def quartiers_commune(session: Session, insee: str) -> dict | None:
    """L'AFFINAGE par quartier d'une commune : n IRIS, vacance min/max/médiane (maille DITE).
    Ne remplace jamais la vérité communale (commune_insee_logement)."""
    rows = session.execute(text(
        "SELECT iris, logvac, log FROM iris_rp WHERE insee = :i AND log > 0"),
        {"i": insee}).mappings().all()
    if not rows:
        return None
    vac = sorted(round(100.0 * r["logvac"] / r["log"], 1) for r in rows
                 if r["logvac"] is not None)
    if not vac:
        return None
    return {"n_iris": len(rows), "vacance_min_pct": vac[0], "vacance_max_pct": vac[-1],
            "vacance_mediane_pct": vac[len(vac) // 2],
            "source": "INSEE RP2022 par IRIS — l'affinage par quartier de la vérité communale"}
