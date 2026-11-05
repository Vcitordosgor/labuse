"""SOURCES-5 #15 — INSEE RP2022 fichier détail Logements (EGOUL) : toutes les variables logement.

`anc.ingest_insee_egoul` n'exploitait qu'EGOUL (raccordement) + IPONDL. Ce module fait une passe
sur le MÊME fichier détail national (FD_LOGEMT_2022, 69 variables, ~26 M lignes ; déjà en cache),
filtre le 974 par COMMUNE, et agrège par commune les **distributions pondérées (IPONDL)** de toutes
les variables LOGEMENT : chauffage (CHAU/CHFL/CHOS/CMBL), taille (NBPI/SURF), type (TYPL/TYPC),
période (ACHL/BATI), catégorie/statut (CATL/STOCD), équipements (EAU/ELEC/WC/BAIN/GARL/ASCEN/CLIM/
CUIS/SANI/VOIT/HLML/CATIRIS).

Table de PROVENANCE `rp_logement_commune` (24 lignes, jsonb) — agrégat commune, JAMAIS de ligne
individuelle (RGPD : l'INSEE ne diffuse pas plus fin que l'IRIS). Hors scoring, hors run.
"""
from __future__ import annotations

import csv
import io
import logging
import time
import zipfile
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from .anc import _cfg, _repo_root

log = logging.getLogger("labuse.rp_logement")

#: variables LOGEMENT du fichier détail (dwelling attributes) — les attributs de la personne de
#: référence (SEXEM, DIPLM, TACTM, INPER…) sont hors périmètre « logement ».
DWELLING_VARS = (
    "ACHL", "BATI", "CATL", "CATIRIS", "CHAU", "CHFL", "CHOS", "CMBL", "CLIM", "CUIS",
    "NBPI", "SURF", "TYPL", "TYPC", "STOCD", "HLML", "EAU", "ELEC", "WC", "BAIN",
    "GARL", "ASCEN", "SANI", "VOIT",
)

DDL = """
CREATE TABLE IF NOT EXISTS rp_logement_commune (
    insee          varchar(5) PRIMARY KEY,
    n_logements    real,                    -- somme des poids IPONDL (tous logements)
    distributions  jsonb NOT NULL,          -- {variable: {modalité: poids arrondi}}
    millesime      varchar(32) NOT NULL,
    ingested_at    timestamptz NOT NULL DEFAULT now()
)
"""


def ingest_rp_logement(session: Session, *, fichier: str | None = None, log=print) -> dict:
    """Passe unique sur le fichier détail (cache), agrège les distributions logement par commune 974."""
    session.execute(text(DDL))
    cfg = _cfg()["insee"]
    cache = Path(cfg["cache_dir"])
    cache = cache if cache.is_absolute() else _repo_root() / cache
    zpath = Path(fichier) if fichier else cache / Path(cfg["url_zip"]).name
    if not zpath.exists():
        raise FileNotFoundError(f"fichier détail RP absent du cache : {zpath} "
                                "(lancer d'abord le téléchargement, cf. ingest_insee_egoul)")
    # {insee: {"w": total, "d": {var: {mod: poids}}}}
    acc: dict[str, dict] = {}
    t0 = time.monotonic()
    n_974 = 0
    with zipfile.ZipFile(zpath) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(name) as raw:
            rd = csv.reader(io.TextIOWrapper(raw, encoding="utf-8", newline=""), delimiter=";")
            header = next(rd)
            i_com = header.index("COMMUNE")
            i_w = header.index("IPONDL")
            var_idx = [(v, header.index(v)) for v in DWELLING_VARS if v in header]
            for i, row in enumerate(rd):
                if i and i % 5_000_000 == 0:
                    log(f"  RP logement : {i/1e6:.0f} M lignes, {n_974} au 974 "
                        f"({i/(time.monotonic()-t0):.0f}/s)")
                if not row[i_com].startswith("974"):
                    continue
                n_974 += 1
                com = row[i_com]
                try:
                    w = float(row[i_w].replace(",", "."))
                except (ValueError, IndexError):
                    w = 1.0
                e = acc.setdefault(com, {"w": 0.0, "d": {}})
                e["w"] += w
                for v, j in var_idx:
                    mod = row[j] if j < len(row) else ""
                    dv = e["d"].setdefault(v, {})
                    dv[mod] = dv.get(mod, 0.0) + w
    # INJECTION-SOLIDE-3 — passe par `remplacer_servie` : les 24 communes sont chargées dans une STAGING,
    # contrôlée (non vide, écart sous seuil) puis échangée ATOMIQUEMENT. Un fichier détail vide / à moitié
    # lu est REFUSÉ → la version servie est conservée (`InjectionRefusee`). Plus de `DELETE FROM
    # rp_logement_commune` à vif. Table sans géométrie.
    from . import injection_sure
    import json as _json

    def charger(conn, staging):
        for com, e in acc.items():
            dist = {v: {m: round(p, 1) for m, p in mods.items()} for v, mods in e["d"].items()}
            conn.execute(text(
                f'INSERT INTO "{staging}" (insee, n_logements, distributions, millesime) '
                "VALUES (:i, :n, CAST(:d AS jsonb), :m)"),
                {"i": com, "n": round(e["w"], 1), "d": _json.dumps(dist, ensure_ascii=False),
                 "m": cfg["millesime"]})

    injection_sure.remplacer_servie(
        session, table="rp_logement_commune", charger_staging=charger, a_geometrie=False,
        couverture_974_min=0, delta_max_pct=50.0,
        alerter=injection_sure.alerte_injection(
            "rp_logement_commune", "INSEE RP — fichier détail Logements (EGOUL)"))
    session.flush()
    log(f"  RP logement : {len(acc)} communes 974, {n_974} logements lus, "
        f"{len(DWELLING_VARS)} variables agrégées")
    return {"communes": len(acc), "logements_974": n_974, "variables": len(DWELLING_VARS)}
