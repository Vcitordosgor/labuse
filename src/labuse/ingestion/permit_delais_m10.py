"""M10 — backfill de la DATE DE DÉPÔT des autorisations d'urbanisme (vélocité admin).

CONTEXTE (constat du lot 0 M10) : `sitadel_permits` ne porte QU'UNE date, la
`DATE_REELLE_AUTORISATION`, et la `daact` (achèvement). La date de DÉPÔT
(`DR_DEPOT` — « Date réelle de dépôt de la DAU », type date au flux) EXISTE dans la
source SDES/Dido mais n'a jamais été capturée par le connecteur `permits_sdes`. Le
module M05 « Vélocité » livrait donc un proxy (autorisation→achèvement) en notant
« dépôt→décision non porté par la source » — ce qui n'était pas exact.

Ce module reconstitue le délai RÉEL dépôt→autorisation dans une table ADDITIVE
`m10_permit_delais` (jamais de mutation de `sitadel_permits`, lecture seule). Il
refait les mêmes clés que le connecteur (`permit_id`, commune INSEE→nom, nature
PC/DP/PA/PD) pour être joignable au radar permis.

Qualité de la source (mesurée au backfill 14/07/2026, 51 592 lignes 974) :
  · DR_DEPOT présent à 99,9 %, DATE_REELLE_AUTORISATION à 100 % ;
  · DR_DEPOT est TRONQUÉ AU MOIS (85 % des dépôts au 1er du mois) → le délai n'a de
    sens qu'en MOIS, pas en jours (c'est le libellé du mandat : « X mois ») ;
  · ~15 % des lignes ont dépôt > autorisation (erreur de saisie DR_DEPOT sur de
    l'historique, jusqu'à −157 mois) → `valide = false`, EXCLUES de toute médiane et
    comptées comme taux d'exclusion (jamais silencieusement).

CENSURE (honnêteté) : le fichier Sitadel des autorisations ne contient QUE des
dossiers ACCORDÉS (0 ligne « déposé non tranché »). Le « taux de dossiers en cours »
n'est donc PAS observable ici ; la médiane est conditionnelle à « a fini par être
autorisé ». Biais résiduel mesurable = survie des cohortes récentes (un dépôt 2025
lent n'est pas encore visible) → l'endpoint borne la médiane de tête aux cohortes
mûres. Tout est consigné dans reports/m10-permis/SYNTHESE-M10.md.
"""
from __future__ import annotations

import csv
import io
import time
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from .permits_sdes import DATAFILES, _commune_map, _fetch_csv

_DDL = """
CREATE TABLE IF NOT EXISTS m10_permit_delais (
    permit_id          VARCHAR(64) PRIMARY KEY,
    commune            VARCHAR(64),
    nature             VARCHAR(8),
    famille            VARCHAR(16),
    date_depot         DATE,
    date_autorisation  DATE,
    date_achevement    DATE,
    delai_mois         INTEGER,
    valide             BOOLEAN NOT NULL DEFAULT false,
    computed_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_m10_delais_commune ON m10_permit_delais (commune);
CREATE INDEX IF NOT EXISTS ix_m10_delais_nature ON m10_permit_delais (nature);
CREATE INDEX IF NOT EXISTS ix_m10_delais_valide ON m10_permit_delais (valide);
"""

_UPSERT = text("""
INSERT INTO m10_permit_delais
  (permit_id, commune, nature, famille, date_depot, date_autorisation,
   date_achevement, delai_mois, valide)
VALUES (:pid, :c, :nat, :fam, :dep, :aut, :ach, :delai, :valide)
ON CONFLICT (permit_id) DO UPDATE SET
  commune=EXCLUDED.commune, nature=EXCLUDED.nature, famille=EXCLUDED.famille,
  date_depot=EXCLUDED.date_depot, date_autorisation=EXCLUDED.date_autorisation,
  date_achevement=EXCLUDED.date_achevement, delai_mois=EXCLUDED.delai_mois,
  valide=EXCLUDED.valide, computed_at=now()
""")


def _pdate(s: str | None) -> date | None:
    s = (s or "").strip()
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _months(dep: date | None, aut: date | None) -> int | None:
    """Délai en MOIS (la source ne porte le dépôt qu'au mois — jours non fiables)."""
    if not dep or not aut:
        return None
    return (aut.year - dep.year) * 12 + (aut.month - dep.month)


def build_delais(session: Session, log=print) -> dict:
    """Construit/rafraîchit m10_permit_delais depuis SDES/Dido (backfill complet, idempotent)."""
    t0 = time.time()
    for stmt in _DDL.strip().split(";\n"):
        if stmt.strip():
            session.execute(text(stmt))
    session.commit()

    communes = _commune_map(session)
    stats = {"lignes": 0, "upserts": 0, "sans_id": 0, "valides": 0,
             "exclus_causalite": 0, "sans_depot": 0}
    for fam, df in DATAFILES.items():
        reader = csv.DictReader(io.StringIO(_fetch_csv(df["rid"])), delimiter=";")
        n_file = 0
        for rec in reader:
            stats["lignes"] += 1
            insee = (rec.get("COMM") or "").strip()
            pid = (rec.get(df["num"]) or "").strip()
            if not insee or not pid:
                stats["sans_id"] += 1
                continue
            nature = ((rec.get(df.get("type_col")) or df.get("type_fixe") or "").strip()
                      or None)
            dep = _pdate(rec.get("DR_DEPOT"))
            aut = _pdate(rec.get("DATE_REELLE_AUTORISATION"))
            ach = _pdate(rec.get("DATE_REELLE_DAACT"))
            delai = _months(dep, aut)
            # valide = dépôt ET autorisation présents ET causalité respectée (dépôt ≤ autor.)
            valide = delai is not None and delai >= 0
            if valide:
                stats["valides"] += 1
            elif dep is None:
                stats["sans_depot"] += 1
            elif delai is not None and delai < 0:
                stats["exclus_causalite"] += 1
            session.execute(_UPSERT, {
                "pid": pid, "c": communes.get(insee, insee), "nat": nature, "fam": fam,
                "dep": dep, "aut": aut, "ach": ach, "delai": delai, "valide": valide})
            stats["upserts"] += 1
            n_file += 1
            if n_file % 4000 == 0:
                session.flush()
                log(f"  {fam} : {n_file}…")
        session.flush()
        log(f"  ✓ {fam} : {n_file} lignes")
    session.commit()
    stats["duree_s"] = round(time.time() - t0, 1)
    log(f"✓ M10 délais dépôt→autorisation : {stats}")
    return stats


if __name__ == "__main__":
    from ..config import get_settings
    from ..db import session_scope

    get_settings()  # échoue tôt si l'env DB est absent
    with session_scope() as s:
        build_delais(s)
