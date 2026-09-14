"""SOURCES-1 lot 5 — fibre Arcep « Ma connexion internet » (maille immeuble, trimestriel).

Source vérifiée live 07/09/2026 : data.arcep.fr sert un DÉCOUPAGE DÉPARTEMENTAL (pas besoin
du national) — `base_imb/last/departement/base_imb_974.csv.gz` (330 051 immeubles, 13,8 Mo)
et `eligibilite/last/departement/actuel_974.csv.gz` (2 859 733 lignes immeuble × opérateur ×
techno, 13,2 Mo). Dernier millésime du répertoire : 2026_T1. Coordonnées `imb_x/imb_y` en
EPSG:3857 (vérifié : x≈6,17 M, y≈−2,38 M sur Saint-Denis).

Table `arcep_immeubles` : un immeuble = raccordable FttH (≥ 1 ligne éligibilité FO) +
opérateurs FO. FttH fiable (IPE) ; les autres technos sont déclaratives (fiche 12) — seul le
FttH est servi. Purge + réinsertion (idempotent).
"""
from __future__ import annotations

import csv
import gzip
import io

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings

SOURCE_NAME = "Fibre Arcep — Ma connexion internet (immeuble)"
URL_BASE_IMB = ("https://data.arcep.fr/fixe/maconnexioninternet/base_imb/last/"
                "departement/base_imb_974.csv.gz")
URL_ELIG = ("https://data.arcep.fr/fixe/maconnexioninternet/eligibilite/last/"
            "departement/actuel_974.csv.gz")
MILLESIME = "2026_T1"

DDL = """
CREATE TABLE IF NOT EXISTS arcep_immeubles (
    imb_id          varchar(64) PRIMARY KEY,
    insee           varchar(5)  NOT NULL,
    commune         varchar(64),
    adresse         text,
    nb_logements    integer,
    ftth            boolean     NOT NULL DEFAULT false,
    operateurs_ftth text[]      NOT NULL DEFAULT '{}',
    geom            geometry(Point, 4326),
    geom_2975       geometry(Point, 2975),
    millesime       varchar(16) NOT NULL,
    maj_at          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_arcep_imb_geom2975 ON arcep_immeubles USING gist (geom_2975);
CREATE INDEX IF NOT EXISTS ix_arcep_imb_insee ON arcep_immeubles (insee);
-- SOURCES-4 lot 2 — on ne gardait que le FttH ; l'Arcep publie TOUTES les technologies (fibre,
-- cuivre/DSL, 4G fixe, satellite) et la CLASSE DE DÉBIT (descendant/montant) par immeuble. On
-- garde les technos disponibles et le meilleur débit descendant (les autres technos restent
-- déclaratives — étiquetées, jamais présentées comme fiables au même titre que le FttH IPE).
ALTER TABLE arcep_immeubles ADD COLUMN IF NOT EXISTS technos text[] NOT NULL DEFAULT '{}';
ALTER TABLE arcep_immeubles ADD COLUMN IF NOT EXISTS debit_descendant_max varchar(8);
ALTER TABLE arcep_immeubles ADD COLUMN IF NOT EXISTS debit_montant_max varchar(8)
"""

# SOURCES-4 lot 2 — ordre des classes de débit Arcep (du meilleur au moins bon) pour retenir le
# MEILLEUR débit disponible par immeuble, toutes technos confondues.
_DEBIT_ORDRE = ("THD1G", "THD100", "THD30", "HD3", "HD05", "BHD8", "INEL")
_DEBIT_RANG = {c: i for i, c in enumerate(_DEBIT_ORDRE)}


def _meilleur_debit(classes: set[str]) -> str | None:
    """La meilleure classe de débit d'un ensemble (rang le plus faible = meilleur)."""
    connues = [c for c in classes if c in _DEBIT_RANG]
    return min(connues, key=lambda c: _DEBIT_RANG[c]) if connues else None


def ensure_tables(engine) -> None:
    with engine.begin() as cx:
        for stmt in DDL.strip().split(";\n"):
            if stmt.strip():
                cx.execute(text(stmt))


def _telecharger(url: str, client: httpx.Client) -> bytes:
    r = client.get(url)
    r.raise_for_status()
    return gzip.decompress(r.content)


def ingest_arcep(session: Session, *, url_imb: str = URL_BASE_IMB, url_elig: str = URL_ELIG,
                 millesime: str = MILLESIME, client: httpx.Client | None = None,
                 log=print) -> dict:
    """Télécharge base immeuble + éligibilité 974, agrège le FttH par immeuble, remplace la
    table (idempotent). Rend {"immeubles", "ftth", "operateurs", "pct_ftth"}."""
    own = client is None
    c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 300.0),
                               headers={"User-Agent": constants.USER_AGENT},
                               follow_redirects=True)
    try:
        brut_elig = _telecharger(url_elig, c)
        brut_imb = _telecharger(url_imb, c)
    finally:
        if own:
            c.close()
    # 1) éligibilité : opérateurs FO par immeuble (FttH fiable) + SOURCES-4 : toutes les technos
    # disponibles et la meilleure classe de débit descendant/montant par immeuble.
    fo: dict[str, set[str]] = {}
    technos: dict[str, set[str]] = {}
    debit_d: dict[str, set[str]] = {}
    debit_m: dict[str, set[str]] = {}
    r = csv.DictReader(io.TextIOWrapper(io.BytesIO(brut_elig), encoding="utf8"), delimiter=";")
    for row in r:
        imb = row["imb_id"]
        techno = (row.get("code_techno") or "").upper()
        if techno:
            technos.setdefault(imb, set()).add(techno)
        if techno == "FO":
            fo.setdefault(imb, set()).add((row.get("code_operateur") or "?").strip())
        if (dd := (row.get("classe_debit_descendant") or "").strip()):
            debit_d.setdefault(imb, set()).add(dd)
        if (dm := (row.get("classe_debit_montant") or "").strip()):
            debit_m.setdefault(imb, set()).add(dm)
    # 2) immeubles : purge + insertion par lots
    session.execute(text("DELETE FROM arcep_immeubles"))
    n = n_ftth = 0
    ops_vus: set[str] = set()
    batch: list[dict] = []

    def _flush():
        if batch:
            session.execute(text(
                "INSERT INTO arcep_immeubles (imb_id, insee, commune, adresse, nb_logements, "
                " ftth, operateurs_ftth, technos, debit_descendant_max, debit_montant_max, "
                " geom, geom_2975, millesime) "
                "VALUES (:id, :insee, :com, :adr, :nb, :ftth, :ops, :technos, :dd, :dm, "
                " ST_Transform(ST_SetSRID(ST_MakePoint(:x, :y), 3857), 4326), "
                " ST_Transform(ST_SetSRID(ST_MakePoint(:x, :y), 3857), 2975), :mil) "
                "ON CONFLICT (imb_id) DO NOTHING"), batch)
            batch.clear()

    r = csv.DictReader(io.TextIOWrapper(io.BytesIO(brut_imb), encoding="utf8"), delimiter=";")
    for row in r:
        imb = row["imb_id"]
        ops = sorted(fo.get(imb, ()))
        adr = " ".join(x for x in (row.get("addr_numero"), row.get("addr_rep"),
                                   row.get("addr_nom_voie") or row.get("addr_nom_ld")) if x)
        try:
            x, y = float(row["imb_x"]), float(row["imb_y"])
        except (TypeError, ValueError):
            continue
        batch.append({"id": imb, "insee": row.get("imb_code_insee") or "?",
                      "com": row.get("addr_nom_commune"), "adr": adr or None,
                      "nb": int(row["imb_nbr_logloc"]) if (row.get("imb_nbr_logloc") or "").isdigit() else None,
                      "ftth": bool(ops), "ops": ops,
                      "technos": sorted(technos.get(imb, ())),
                      "dd": _meilleur_debit(debit_d.get(imb, set())),
                      "dm": _meilleur_debit(debit_m.get(imb, set())),
                      "x": x, "y": y, "mil": millesime})
        n += 1
        if ops:
            n_ftth += 1
            ops_vus.update(ops)
        if len(batch) >= 5000:
            _flush()
    _flush()
    session.flush()
    pct = round(100.0 * n_ftth / n, 1) if n else 0.0
    log(f"  arcep : {n} immeubles, {n_ftth} raccordables FttH ({pct} %), "
        f"opérateurs {sorted(ops_vus)}")
    return {"immeubles": n, "ftth": n_ftth, "pct_ftth": pct, "operateurs": sorted(ops_vus)}


def fibre_parcelle(session: Session, idu: str, rayon_m: float = 100.0) -> dict | None:
    """L'immeuble Arcep le plus proche de la parcelle (≤ rayon) : raccordable FttH, opérateurs,
    DISTANCE DITE (jamais un booléen nu). None si la table est vide (source non ingérée)."""
    if not session.execute(text("SELECT 1 FROM arcep_immeubles LIMIT 1")).scalar():
        return None
    row = session.execute(text(
        "SELECT a.imb_id, a.ftth, a.operateurs_ftth, a.adresse, a.millesime, "
        "       ST_Distance(p.geom_2975, a.geom_2975) AS dist "
        "FROM parcels p JOIN arcep_immeubles a "
        "  ON ST_DWithin(p.geom_2975, a.geom_2975, :r) "
        "WHERE p.idu = :idu ORDER BY p.geom_2975 <-> a.geom_2975 LIMIT 1"),
        {"idu": idu, "r": rayon_m}).mappings().first()
    if row is None:
        return {"etat": "aucun_immeuble",
                "detail": f"aucun immeuble Arcep à moins de {rayon_m:.0f} m",
                "millesime": MILLESIME}
    return {"etat": "servi", "ftth": bool(row["ftth"]),
            "operateurs": list(row["operateurs_ftth"] or []),
            "distance_m": round(float(row["dist"])),
            "adresse": row["adresse"], "millesime": row["millesime"]}
