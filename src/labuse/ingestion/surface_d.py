"""O10 — SURFACE D : LE MOTEUR de détection de BASCULES par parcelle (événements datés).

Une « bascule » = un changement d'état daté qui rend une parcelle (plus) intéressante MAINTENANT.
Ce module CONSTRUIT le moteur : une table additive `surface_d_events(idu, type, date, detail, source)`
alimentée par les signaux DÉJÀ en base — zéro donnée nouvelle. La NOTIFICATION (alerte, digest) est
**POST-M7** (mandat Auth & Plans) ; ici on livre uniquement le moteur + une CLI de test.

Sources BRANCHÉES (datées, par parcelle) :
  · `entree_fenetre_defisc`  ← `defisc_fenetres` (fenêtre active, année de début)     [badge Phase A-1]
  · `pc_caduc`               ← `pc_caducs` (caducité probable, année)                  [badge Phase A cycle 2]
  · `dpe_passoire`           ← `dpe_records` étiquette F/G (date d'établissement)      [réserve M4.0, sourcé]
  · `permis_octroye`         ← `sitadel_permits` rattachés (idu_codes), 36 mois

Types DÉCLARÉS mais SANS source datée par parcelle à ce jour (extensible, non fabriqués) :
  · `plu_revise` (révision de zonage datée), `bodacc_pm` (événement société du propriétaire),
    `permis_voisin` (permis à proximité, ≠ sur la parcelle). Le moteur les accepte ; on ne les invente pas.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

# Types d'événements connus du moteur (les 4 premiers sont alimentés ; les 3 derniers, déclarés/extensibles).
EVENT_TYPES = ("entree_fenetre_defisc", "pc_caduc", "dpe_passoire", "permis_octroye",
               "plu_revise", "bodacc_pm", "permis_voisin")

DDL = """
CREATE TABLE IF NOT EXISTS surface_d_events (
  id           serial PRIMARY KEY,
  idu          varchar(14) NOT NULL,
  type         text NOT NULL,
  date_evenement date,                 -- date de la bascule (NULL si non datable)
  detail       text NOT NULL,
  source       text NOT NULL,
  computed_at  timestamptz DEFAULT now(),
  UNIQUE (idu, type, date_evenement)
);
CREATE INDEX IF NOT EXISTS ix_surface_d_idu ON surface_d_events (idu);
CREATE INDEX IF NOT EXISTS ix_surface_d_type ON surface_d_events (type, date_evenement DESC);
"""

# Un INSERT par source, guardé par to_regclass (table additive optionnelle). make_date(y,1,1) pour les années.
_SOURCES = {
    "entree_fenetre_defisc": (
        "defisc_fenetres",
        """INSERT INTO surface_d_events (idu, type, date_evenement, detail, source)
           SELECT idu, 'entree_fenetre_defisc', make_date(fenetre_debut, 1, 1),
                  coalesce(libelle_court, 'Entrée en fenêtre de défiscalisation'),
                  coalesce(source_libelle, 'defisc_fenetres')
           FROM defisc_fenetres WHERE fenetre_active AND fenetre_debut IS NOT NULL
           ON CONFLICT (idu, type, date_evenement) DO NOTHING"""),
    "pc_caduc": (
        "pc_caducs",
        """INSERT INTO surface_d_events (idu, type, date_evenement, detail, source)
           SELECT idu, 'pc_caduc', make_date(caduc_depuis, 1, 1),
                  coalesce(libelle_court, 'PC caduc probable'), 'pc_caducs (SITADEL)'
           FROM pc_caducs WHERE caduc_depuis IS NOT NULL
           ON CONFLICT (idu, type, date_evenement) DO NOTHING"""),
    "dpe_passoire": (
        "dpe_records",
        """INSERT INTO surface_d_events (idu, type, date_evenement, detail, source)
           SELECT DISTINCT ON (parcelle_idu) parcelle_idu, 'dpe_passoire', date_etablissement::date,
                  'DPE ' || etiquette_dpe || ' (passoire énergétique)', 'ADEME (dpe_records)'
           FROM dpe_records
           WHERE etiquette_dpe IN ('F', 'G') AND parcelle_idu IS NOT NULL AND date_etablissement IS NOT NULL
             AND parcelle_idu IN (SELECT idu FROM parcels)
           ORDER BY parcelle_idu, date_etablissement DESC
           ON CONFLICT (idu, type, date_evenement) DO NOTHING"""),
    "permis_octroye": (
        "sitadel_permits",
        """INSERT INTO surface_d_events (idu, type, date_evenement, detail, source)
           SELECT e AS idu, 'permis_octroye', sp.date::date,
                  'Permis ' || coalesce(sp.type, 'PC') || ' rattaché', 'SITADEL'
           FROM sitadel_permits sp, jsonb_array_elements_text(sp.idu_codes) e
           WHERE sp.date >= (CURRENT_DATE - INTERVAL '36 months') AND sp.date IS NOT NULL
             AND e IN (SELECT idu FROM parcels)
           ON CONFLICT (idu, type, date_evenement) DO NOTHING"""),
}


def build_events(session: Session, *, commit: bool = True, log=lambda *_: None) -> dict:
    """(Re)construit `surface_d_events` depuis les signaux datés déjà en base. Rebuild complet idempotent."""
    session.execute(text("DROP TABLE IF EXISTS surface_d_events"))
    for stmt in DDL.strip().split(";\n"):
        if stmt.strip():
            session.execute(text(stmt))
    counts: dict[str, int] = {}
    for typ, (table, sql) in _SOURCES.items():
        if session.execute(text("SELECT to_regclass(:t)"), {"t": table}).scalar() is None:
            counts[typ] = 0
            log(f"surface_d {typ} : source {table} absente — 0")
            continue
        session.execute(text(sql))
        counts[typ] = session.execute(text(
            "SELECT count(*) FROM surface_d_events WHERE type = :t"), {"t": typ}).scalar()
        log(f"surface_d {typ} : {counts[typ]}")
    total = session.execute(text("SELECT count(*) FROM surface_d_events")).scalar()
    if commit:
        session.commit()
    log(f"surface_d_events : {total} événements datés")
    return {"total": total, "par_type": counts}


def recent_events(session: Session, *, limit: int = 50, type_filtre: str | None = None) -> list[dict]:
    """CLI/diagnostic : les bascules les plus récentes (moteur seulement — pas de notification ici)."""
    rows = session.execute(text(
        """SELECT idu, type, date_evenement, detail, source FROM surface_d_events
           WHERE (CAST(:t AS text) IS NULL OR type = :t)
           ORDER BY date_evenement DESC NULLS LAST LIMIT :lim"""),
        {"t": type_filtre, "lim": limit}).mappings().all()
    return [dict(r) for r in rows]
