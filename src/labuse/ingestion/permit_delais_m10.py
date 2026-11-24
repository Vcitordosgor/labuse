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


def ensure_tables(engine) -> None:
    """FIX-C6 (GB-049) — crée `m10_permit_delais` VIDE au boot (heal), pas seulement à
    l'ingestion M10. Le radar permis `/modules/permis` la LIT en LEFT JOIN : sur une base
    neuve elle manquait → 500 `UndefinedTable`. Idempotent (`IF NOT EXISTS`)."""
    from ..db import sql_statements
    with engine.begin() as c:
        for stmt in sql_statements(_DDL):
            if stmt.strip():
                c.execute(text(stmt))


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


def _valide(dep: date | None, aut: date | None, delai: int | None) -> bool:
    """La règle de VALIDITÉ, en un seul endroit : dépôt ET autorisation présents, délai (mois) ≥ 0,
    ET causalité respectée AU JOUR (autorisation ≥ dépôt).

    ORF-15 (FIX-ORFEVRE-1) — l'ancienne règle (`delai >= 0` seul) laissait passer 127 lignes
    `valide=true` avec `date_autorisation < date_depot` de quelques jours (même mois → delai_mois = 0) :
    un délai négatif, quelle qu'en soit l'échelle, vaut TOUJOURS valide=false. Les médianes (modules
    M10, Flash, repères) filtrent sur `valide` — vérifié."""
    return delai is not None and delai >= 0 and dep is not None and aut is not None and aut >= dep


# ─────────────────── OUTIL-PERMIS-FIX-3/4 — couche VIVANTE, dérivée de sitadel_permits ───────────────────
# OUTIL-PERMIS-FIX-4 (Point 2/3) — le DÉPÔT vient de `raw.an_depot` (= AN_DEPOT, ANNÉE de dépôt du flux
# SDES), PAS de `date_depot` (= DR_DEPOT, corrompu : = date d'autorisation ou postérieur à 62,6 %). Le
# dépôt est donc connu À L'ANNÉE : convention `AAAA-01-01` (comme l'ancienne couche validée par le
# relecteur → médiane 8-9 mois par commune). La couche reste MAINTENUE PAR TRIGGER (suit les MAJ permis).
# Règle de validité : année de dépôt présente, autorisation présente, et autorisation ≥ année de dépôt.
_M10_DEPOT_SQL = "CASE WHEN s.raw->>'an_depot' ~ '^[0-9]{4}$' THEN ((s.raw->>'an_depot')||'-01-01')::date END"
_M10_DELAI_SQL = (
    "(EXTRACT(YEAR FROM s.date)::int - (s.raw->>'an_depot')::int) * 12"
    " + (EXTRACT(MONTH FROM s.date)::int - 1)")
_M10_ACH_SQL = "CASE WHEN s.raw->>'daact' ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}' THEN (left(s.raw->>'daact',10))::date END"
_M10_ROW_SQL = f"""
  s.permit_id, s.commune, s.type AS nature, s.raw->>'famille' AS famille,
  {_M10_DEPOT_SQL} AS date_depot, s.date::date AS date_autorisation,
  {_M10_ACH_SQL} AS date_achevement,
  -- valide ⇔ dépôt (année) connu ET autorisation présente ET autorisation ≥ dépôt (01-01). Le `::int`
  -- du délai n'est évalué QUE dans ce CASE (dépôt non nul = an_depot à 4 chiffres) → jamais d'erreur.
  CASE WHEN COALESCE(s.date::date >= ({_M10_DEPOT_SQL}), false) THEN {_M10_DELAI_SQL} END AS delai_mois,
  COALESCE(s.date::date >= ({_M10_DEPOT_SQL}), false) AS valide
"""

_M10_TRIGGER_FN = f"""
CREATE OR REPLACE FUNCTION m10_permit_delais_sync() RETURNS trigger AS $fn$
BEGIN
    IF to_regclass('m10_permit_delais') IS NULL THEN RETURN COALESCE(NEW, OLD); END IF;
    IF (TG_OP = 'DELETE') THEN
        DELETE FROM m10_permit_delais WHERE permit_id = OLD.permit_id; RETURN OLD;
    END IF;
    DELETE FROM m10_permit_delais WHERE permit_id = NEW.permit_id;
    INSERT INTO m10_permit_delais
      (permit_id, commune, nature, famille, date_depot, date_autorisation,
       date_achevement, delai_mois, valide, computed_at)
    SELECT {_M10_ROW_SQL}, now() FROM sitadel_permits s WHERE s.permit_id = NEW.permit_id;
    RETURN NEW;
END;
$fn$ LANGUAGE plpgsql
"""
_M10_TRIGGER_DROP = "DROP TRIGGER IF EXISTS trg_m10_permit_delais_sync ON sitadel_permits"
_M10_TRIGGER_CREATE = """
CREATE TRIGGER trg_m10_permit_delais_sync
    AFTER INSERT OR UPDATE OR DELETE ON sitadel_permits
    FOR EACH ROW EXECUTE FUNCTION m10_permit_delais_sync()
"""
_M10_RESYNC = f"""
INSERT INTO m10_permit_delais
  (permit_id, commune, nature, famille, date_depot, date_autorisation,
   date_achevement, delai_mois, valide, computed_at)
SELECT {_M10_ROW_SQL}, now() FROM sitadel_permits s
ON CONFLICT (permit_id) DO UPDATE SET
  commune=EXCLUDED.commune, nature=EXCLUDED.nature, famille=EXCLUDED.famille,
  date_depot=EXCLUDED.date_depot, date_autorisation=EXCLUDED.date_autorisation,
  date_achevement=EXCLUDED.date_achevement, delai_mois=EXCLUDED.delai_mois,
  valide=EXCLUDED.valide, computed_at=now()
"""
_M10_PRUNE = ("DELETE FROM m10_permit_delais d "
              "WHERE NOT EXISTS (SELECT 1 FROM sitadel_permits s WHERE s.permit_id = d.permit_id)")


def ensure_delais_vivants(session: Session, resync: bool = True) -> dict:
    """OUTIL-PERMIS-FIX-3 (Point 3) — garantit la couche des délais et son TRIGGER (dérivée de
    `sitadel_permits`, maintenue à chaque mise à jour). `resync=True` recalcule le plein sur la donnée
    SERVIE (réconciliation après un rechargement). À exécuter une fois en prod (cf. compte-rendu)."""
    for stmt in _DDL.strip().split(";\n"):
        if stmt.strip():
            session.execute(text(stmt))
    for stmt in (_M10_TRIGGER_FN, _M10_TRIGGER_DROP, _M10_TRIGGER_CREATE):
        session.execute(text(stmt))
    session.commit()
    if resync:
        session.execute(text(_M10_RESYNC))
        session.execute(text(_M10_PRUNE))
        session.commit()
    n = session.execute(text("SELECT count(*) FROM m10_permit_delais")).scalar()
    return {"m10_permit_delais": int(n or 0)}


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
            # OUTIL-PERMIS-FIX-4 (Point 2) — DÉPÔT = AN_DEPOT (ANNÉE, convention 01-01), PAS DR_DEPOT
            # (corrompu). Même source que le trigger (raw.an_depot). Médiane commune 8-9 mois retrouvée.
            an = (rec.get("AN_DEPOT") or "").strip()
            dep = date(int(an), 1, 1) if an.isdigit() and 2000 <= int(an) <= 2100 else None
            aut = _pdate(rec.get("DATE_REELLE_AUTORISATION"))
            ach = _pdate(rec.get("DATE_REELLE_DAACT"))
            delai = _months(dep, aut)
            # valide = dépôt ET autorisation présents ET causalité respectée AU JOUR (ORF-15).
            valide = _valide(dep, aut, delai)
            if valide:
                stats["valides"] += 1
            elif dep is None:
                stats["sans_depot"] += 1
            elif aut is not None and aut < dep:   # ORF-15 : causalité au jour (couvre delai_mois = 0)
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
