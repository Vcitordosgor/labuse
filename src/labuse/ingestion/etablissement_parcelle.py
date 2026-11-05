"""KELFONCIER-FIX-1 (Lot H) — rattachement ÉTABLISSEMENT → PARCELLE par l'adresse BAN.

Un `ST_Within` pur du point SIRENE dans l'emprise cadastrale RATE systématiquement (le géocodage
INSEE pointe le centroïde d'adresse, pas l'emprise — 0 sur les 3 témoins de l'audit, alors que des
établissements existent à ~30 m). On rattache donc par la BAN : chaque établissement de précision
« adresse » (qualite_xy 11/12 SEULEMENT — « voie » 21 et « commune » 33 sont trop grossières, JAMAIS
devinées) est accroché à l'adresse BAN la plus proche (`adresses`, index GiST) dans un rayon borné, et
hérite de la PARCELLE de cette adresse (`adresses.idu`). La table matérialisée `etablissement_parcelle`
(idu, siret, precision) est reconstruite par le job mensuel SIRENE (registre CRON unique).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

#: précisions INSEE « adresse » RETENUES (11 = plaque, 12 = interpolée). 21 (voie) / 33 (commune) exclues.
QUALITE_ADRESSE = ("11", "12")
#: rayon d'accroche à la BAN (m) — au-delà, l'établissement n'est PAS rattaché (jamais deviné).
RAYON_ACCROCHE_M = 25.0

DDL = """
CREATE TABLE IF NOT EXISTS etablissement_parcelle (
    siret      varchar(14) PRIMARY KEY,
    idu        varchar(14) NOT NULL,
    precision  varchar(2)  NOT NULL,           -- qualite_xy INSEE (11 | 12)
    distance_m real,                            -- distance à l'adresse BAN accrochée (transparence)
    maj_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS etablissement_parcelle_idu_idx ON etablissement_parcelle (idu);
"""


def ensure_tables(engine) -> None:
    with engine.begin() as cx:
        cx.execute(text(DDL))


def build_etablissement_parcelle(session: Session, *, rayon_m: float = RAYON_ACCROCHE_M) -> dict:
    """(Re)construit la table par accroche BAN. Renvoie {n_etab_adresse, rattaches, non_rattaches}.
    Le nearest-neighbour est accéléré par l'index GiST de `adresses`.

    INJECTION-SOLIDE-2 — passe par `remplacer_servie` : la reconstruction écrit dans une STAGING, est
    contrôlée (non vide : si `adresses`/`sirene_etablissements` sont momentanément vides, on REFUSE et
    on garde l'ancienne table) puis échangée ATOMIQUEMENT. Plus de `TRUNCATE etablissement_parcelle` à
    vif. Table sans géométrie ; unicité (siret)."""
    from . import injection_sure

    def preparer(conn):
        for stmt in DDL.strip().split(";"):
            if stmt.strip():
                conn.execute(text(stmt))

    n_source = session.execute(text(
        "SELECT count(*) FROM sirene_etablissements WHERE actif AND qualite_xy = ANY(:q)"),
        {"q": list(QUALITE_ADRESSE)}).scalar() or 0

    def charger(conn, staging):
        conn.execute(text(
            f"""
            INSERT INTO "{staging}" (siret, idu, precision, distance_m)
            SELECT s.siret, a.idu, s.qualite_xy, a.d
            FROM sirene_etablissements s
            CROSS JOIN LATERAL (
                SELECT ad.idu, ad.geom_2975 <-> ST_Transform(s.geom, 2975) AS d
                FROM adresses ad
                WHERE ad.idu IS NOT NULL
                ORDER BY ad.geom_2975 <-> ST_Transform(s.geom, 2975)
                LIMIT 1
            ) a
            WHERE s.actif AND s.qualite_xy = ANY(:q) AND s.geom IS NOT NULL
              AND a.d <= :r
            ON CONFLICT (siret) DO NOTHING
            """), {"q": list(QUALITE_ADRESSE), "r": rayon_m})

    res = injection_sure.remplacer_servie(
        session, table="etablissement_parcelle", preparer=preparer, charger_staging=charger,
        a_geometrie=False, couverture_974_min=0, delta_max_pct=50.0, like_including="ALL",
        alerter=injection_sure.alerte_injection("etablissement_parcelle", "SIRENE → parcelle (BAN)"))
    rattaches = int(res["mesures"]["comptes_apres"])
    session.commit()
    return {"n_etab_adresse": int(n_source), "rattaches": rattaches,
            "non_rattaches": int(n_source) - rattaches}
