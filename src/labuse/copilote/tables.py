"""M26-A — tables du Copilote (pattern maison : CREATE TABLE IF NOT EXISTS, idempotent).

Trois tables :
  * agent_runs        — un dossier d'instruction (statut = CACHE, recalculable par reduce_run).
  * agent_events      — l'event log APPEND-ONLY, source de vérité unique. UNIQUE (run_id, seq).
  * agent_run_parcels — détail retenues/écartées (les payloads d'événements ne portent que
                        IDs + compteurs + agrégats, jamais les listes complètes).

Propriété du run (décision Vic, GO M26-A Q2) : compte_id (pattern SEC-IDOR de tenant.py,
bucket pilote = NULL) + utilisateur_id nullable. La FK vers comptes est posée en garde
séparée (la table comptes est créée par un autre module — ordre de boot tolérant).
"""
from __future__ import annotations

from sqlalchemy import text

DDL = """
CREATE TABLE IF NOT EXISTS agent_runs (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  compte_id       integer,
  utilisateur_id  integer,
  mission         varchar(24) NOT NULL,
  status          varchar(16) NOT NULL DEFAULT 'interpreting',
  brief_raw       text NOT NULL,
  brief_json      jsonb,
  engine_versions jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  finished_at     timestamptz
);
CREATE INDEX IF NOT EXISTS agent_runs_compte_idx ON agent_runs (compte_id, created_at DESC);
CREATE TABLE IF NOT EXISTS agent_events (
  id         bigserial PRIMARY KEY,
  run_id     uuid NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  seq        integer NOT NULL,
  kind       varchar(32) NOT NULL,
  payload    jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (run_id, seq)
);
CREATE INDEX IF NOT EXISTS agent_events_run_idx ON agent_events (run_id, seq);
CREATE TABLE IF NOT EXISTS agent_run_parcels (
  run_id     uuid NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  parcel_idu varchar(14) NOT NULL,
  verdict    varchar(16) NOT NULL,
  motif      text,
  PRIMARY KEY (run_id, parcel_idu)
);
"""

# Append-only gravé côté base : tout UPDATE sur agent_events est refusé par trigger, pas
# seulement par discipline de code. Le DELETE ligne à ligne n'est PAS bloqué par trigger :
# la suppression d'un run entier (FK ON DELETE CASCADE) doit rester possible — le code ne
# supprime jamais d'événement isolé, et l'API n'expose aucune suppression.
# (Statements séparés — psycopg3 n'accepte pas le multi-statement, et le corps $$…$$
# interdit un split naïf sur « ; ».)
DDL_APPEND_ONLY = (
    """
CREATE OR REPLACE FUNCTION agent_events_append_only() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'agent_events est append-only (M26-A) : % interdit', TG_OP;
END;
$$ LANGUAGE plpgsql
""",
    "DROP TRIGGER IF EXISTS agent_events_no_rewrite ON agent_events",
    """
CREATE TRIGGER agent_events_no_rewrite
  BEFORE UPDATE ON agent_events
  FOR EACH ROW EXECUTE FUNCTION agent_events_append_only()
""",
)


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        from ..db import sql_statements  # FIX-GB-011 : plus de split(';') naif
        for stmt in sql_statements(DDL):
            if stmt.strip():
                c.execute(text(stmt))
    with engine.begin() as c:
        for stmt in DDL_APPEND_ONLY:
            c.execute(text(stmt))
    # FK vers comptes si la table existe déjà (même tolérance d'ordre que tenant.ensure_scoping).
    with engine.begin() as c:
        if c.execute(text("SELECT to_regclass('comptes')")).scalar() is not None:
            c.execute(text(
                "DO $$ BEGIN "
                "  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_agent_runs_compte') THEN "
                "    ALTER TABLE agent_runs ADD CONSTRAINT fk_agent_runs_compte "
                "      FOREIGN KEY (compte_id) REFERENCES comptes(id) ON DELETE CASCADE; "
                "  END IF; "
                "END $$"))
