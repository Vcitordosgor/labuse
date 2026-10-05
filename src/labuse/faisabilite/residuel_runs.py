"""M135 — versionnement de `parcel_residuel` par run (correctif de fond M134).

`parcel_residuel` cesse d'être une table écrasable (clé `parcel_id` seule) : les
données vivent dans `parcel_residuel_runs` (clé `run_seq, parcel_id`), et
`parcel_residuel` devient une **VUE** filtrée sur le run SERVI. Les ~35 lecteurs SQL
inline ne changent pas d'une ligne (option VUE, arbitrage Vic M135 A.3).

Désignation du run servi : le flag `residuel_runs.is_served` (booléen, résident en
base), JAMAIS un `MAX(run_id)` ni un tri de chaîne (dette §8 M133 : `q_v9 > q_v10`).
`run_seq` est un ENTIER monotone. La bascule est un `UPDATE` atomique, réversible.

Écriture : un run est désigné à l'appel ; écrire dans le run servi est une ERREUR
(`ServedRunWriteError`), pas un warning. Purge : refuse un run servi ou épinglé.
"""
from __future__ import annotations

from sqlalchemy import text

# Colonnes de données exposées par la vue, dans l'ordre EXACT de la table historique
# (computed_at AVANT capacite_estimee — cette dernière ajoutée par ALTER en fin de table ;
# aucun lecteur ne fait SELECT *, mais on expose noms + types + ORDRE à l'identique).
# GEOMETRIE-1 : assiette_source ajoutée EN FIN (CREATE OR REPLACE VIEW n'accepte que ça).
_VIEW_COLS = ("parcel_id", "taux_emprise_pct", "pct_potentiel", "sous_densite",
              "sdp_residuelle_m2", "computed_at", "capacite_estimee", "cause",
              "assiette_source", "hauteur_source", "regles_non_modelisees")


class ServedRunWriteError(RuntimeError):
    """Écrire dans (ou purger) le run SERVI — interdit. Le service est immuable."""


def _regclass_present(conn, nom: str) -> bool:
    """Table/index présent ? `to_regclass` est une LECTURE de catalogue : aucun verrou de table."""
    return conn.execute(text("SELECT to_regclass(:n) IS NOT NULL"), {"n": nom}).scalar() is True


def _colonne_presente(conn, table: str, col: str) -> bool:
    """Colonne présente ? Lecture pure d'`information_schema.columns` : aucun verrou de table."""
    return bool(conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"), {"t": table, "c": col}).scalar())


def ensure_runs_schema(conn) -> None:
    """Crée les tables de versionnement + index (idempotent). N'affecte pas `parcel_residuel`.

    LIENS-1 (lot 0) — BOOT SANS VERROU : chaque DDL est précédé d'un test du CATALOGUE
    (`to_regclass` / `information_schema` : des lectures pures, aucun verrou de table) et n'est
    émis QUE s'il manque vraiment. Sur le chemin nominal (schéma déjà posé) AUCUN DDL n'est
    exécuté → aucun ACCESS EXCLUSIVE : le boot ne se met JAMAIS en file derrière une transaction
    tenant `parcel_residuel_runs`. Vécu le 05/10 : un `ADD COLUMN IF NOT EXISTS assiette_source`
    *no-op* a pris un ACCESS EXCLUSIVE, a attendu derrière une transaction ouverte et a figé toutes
    les lectures du résiduel 8 min. Même recette que `ensure_geom_2975` (commit 70278401) et
    `_col_presente` (models.py), généralisée à CE step — le dernier au boot touchant une table chaude
    qui émettait encore des ALTER non gardés."""
    if not _regclass_present(conn, "parcel_residuel_runs"):
        conn.execute(text("""
            CREATE TABLE parcel_residuel_runs (
              run_seq integer NOT NULL,
              parcel_id integer NOT NULL REFERENCES parcels(id) ON DELETE CASCADE,
              taux_emprise_pct integer, pct_potentiel integer, sous_densite boolean,
              sdp_residuelle_m2 integer, capacite_estimee boolean, cause text,
              computed_at timestamptz NOT NULL DEFAULT now(),
              PRIMARY KEY (run_seq, parcel_id))"""))
    # Trois colonnes additives — l'ALTER n'est émis QUE si la colonne manque (noms issus d'un tuple
    # littéral fermé : pas d'injection). Chacune prendrait sinon un ACCESS EXCLUSIVE no-op à chaque boot.
    #  • assiette_source (GEOMETRIE-1 B) : 'gabarit' (zone d'implantation, reculs par côté + PPR rouge
    #    découpé) ou 'residuel_legacy' (inset uniforme ∩ U/AU). NULL = run antérieur au lot.
    #  • hauteur_source (DONNEES-FIX-1 C) : 'lidar' (égout mesuré) / 'bdtopo' (déclaré) / 'sans'.
    #  • regles_non_modelisees (DONNEES-FIX-1 pt4) : exceptions PLU `modifie_calcul` PORTÉES (JSON texte
    #    : liste de {regle, porte, article, page_pdf}) au lieu d'être approximées. NULL = aucune.
    for col in ("assiette_source", "hauteur_source", "regles_non_modelisees"):
        if not _colonne_presente(conn, "parcel_residuel_runs", col):
            conn.execute(text(f"ALTER TABLE parcel_residuel_runs ADD COLUMN {col} text"))
    # index lecteurs-par-parcelle (les EXISTS/JOIN sur parcel_id) : (parcel_id, run_seq)
    if not _regclass_present(conn, "parcel_residuel_runs_pid"):
        conn.execute(text("CREATE INDEX parcel_residuel_runs_pid "
                          "ON parcel_residuel_runs (parcel_id, run_seq)"))
    if not _regclass_present(conn, "residuel_runs"):
        conn.execute(text("""
            CREATE TABLE residuel_runs (
              run_seq integer PRIMARY KEY,
              label text NOT NULL,
              is_served boolean NOT NULL DEFAULT false,
              is_pinned boolean NOT NULL DEFAULT false,      -- reproductibilité entraînement scoring
              code_commit text, communes text,               -- communes NULL = île entière ; sinon partiel
              computed_at_min timestamptz, computed_at_max timestamptz,
              duree_s integer, note text,
              created_at timestamptz NOT NULL DEFAULT now())"""))
    # AU PLUS UN run servi (index partiel unique) — garantit l'unicité du pointeur.
    if not _regclass_present(conn, "residuel_runs_one_served"):
        conn.execute(text("CREATE UNIQUE INDEX residuel_runs_one_served "
                          "ON residuel_runs (is_served) WHERE is_served"))
    # GEOMETRIE-1 — si la vue existe déjà sans assiette_source, la remettre au niveau
    # (OR REPLACE n'accepte qu'un ajout en fin de liste — c'est le cas). Idempotent.
    relkind = conn.execute(text(
        "SELECT relkind FROM pg_class WHERE relname='parcel_residuel'")).scalar()
    if relkind == "v":
        cols = {r[0] for r in conn.execute(text(
            "SELECT attname FROM pg_attribute WHERE attrelid='parcel_residuel'::regclass "
            "AND attnum > 0 AND NOT attisdropped"))}
        # CREATE OR REPLACE VIEW n'accepte que des AJOUTS en fin de liste : assiette_source,
        # hauteur_source puis regles_non_modelisees sont toutes en fin de `_VIEW_COLS` → OR REPLACE
        # suffit. Idempotent.
        if not {"assiette_source", "hauteur_source", "regles_non_modelisees"} <= cols:
            conn.execute(text(_view_sql(or_replace=True)))


def served_run_seq(conn) -> int:
    """run_seq du run SERVI. PAS de MAX/tri : lecture directe du flag."""
    r = conn.execute(text("SELECT run_seq FROM residuel_runs WHERE is_served")).scalar()
    if r is None:
        raise RuntimeError("Aucun run résiduel servi (residuel_runs.is_served vide) — migration faite ?")
    return int(r)


def _view_sql(or_replace: bool = False) -> str:
    cols = ", ".join(_VIEW_COLS)
    verb = "CREATE OR REPLACE VIEW" if or_replace else "CREATE VIEW"
    return (f"{verb} parcel_residuel AS SELECT {cols} FROM parcel_residuel_runs "
            "WHERE run_seq = (SELECT run_seq FROM residuel_runs WHERE is_served)")


def next_run_seq(conn) -> int:
    """Prochain run_seq = max ENTIER + 1 (numérique, jamais lexical)."""
    return int(conn.execute(text("SELECT COALESCE(max(run_seq), 0) + 1 FROM residuel_runs")).scalar())


def create_run(conn, label: str, *, communes: str | None = None,
               code_commit: str | None = None, note: str | None = None) -> int:
    """Crée un run NEUF (non servi, non épinglé). Renvoie son run_seq entier."""
    seq = next_run_seq(conn)
    conn.execute(text("INSERT INTO residuel_runs (run_seq, label, communes, code_commit, note) "
                      "VALUES (:s, :l, :c, :cc, :n)"),
                 {"s": seq, "l": label, "c": communes, "cc": code_commit, "n": note})
    return seq


def assert_writable(conn, run_seq: int) -> None:
    """Garde-fou B.4 : écrire dans le run servi est une ERREUR."""
    served = conn.execute(text("SELECT run_seq FROM residuel_runs WHERE is_served")).scalar()
    if served is not None and int(served) == int(run_seq):
        raise ServedRunWriteError(
            f"Écriture interdite dans le run SERVI (run_seq={run_seq}). "
            "Créer/cibler un run neuf (create_run) — le service est immuable.")


def set_served(conn, run_seq: int) -> None:
    """BASCULE (geste de Vic). Deux UPDATE dans une transaction — jamais deux servis
    simultanés (l'index partiel unique l'interdirait de toute façon). Réversible : rappeler
    avec le run précédent."""
    if conn.execute(text("SELECT 1 FROM residuel_runs WHERE run_seq=:s"), {"s": run_seq}).scalar() is None:
        raise RuntimeError(f"run_seq={run_seq} inconnu — bascule refusée.")
    conn.execute(text("UPDATE residuel_runs SET is_served=false WHERE is_served"))
    conn.execute(text("UPDATE residuel_runs SET is_served=true WHERE run_seq=:s"), {"s": run_seq})


def purge_run(conn, run_seq: int) -> None:
    """Purge (geste de Vic). REFUSE un run servi ou épinglé — même traitement que l'écriture au servi."""
    row = conn.execute(text("SELECT is_served, is_pinned FROM residuel_runs WHERE run_seq=:s"),
                       {"s": run_seq}).first()
    if row is None:
        raise RuntimeError(f"run_seq={run_seq} inconnu — purge refusée.")
    if row.is_served:
        raise ServedRunWriteError(f"Purge du run SERVI (run_seq={run_seq}) interdite.")
    if row.is_pinned:
        raise RuntimeError(f"Purge du run ÉPINGLÉ (run_seq={run_seq}) interdite — désépingler d'abord.")
    conn.execute(text("DELETE FROM parcel_residuel_runs WHERE run_seq=:s"), {"s": run_seq})
    conn.execute(text("DELETE FROM residuel_runs WHERE run_seq=:s"), {"s": run_seq})


def migrate_to_runs(engine) -> str:
    """Migration ORDONNÉE one-time (idempotente), tout en UNE transaction (service continu) :
      1. schéma cible ; 2. copie de l'existant en run 1 « legacy-mosaïque » servi ;
      3. swap atomique : `parcel_residuel` (table) → `parcel_residuel_base_legacy`, puis VUE.
    Renvoie 'migre' / 'deja_migre' / 'frais'."""
    with engine.begin() as c:
        ensure_runs_schema(c)
        relkind = c.execute(text(
            "SELECT relkind FROM pg_class WHERE relname='parcel_residuel'")).scalar()
        if relkind == "v":
            return "deja_migre"
        if relkind is None:
            # base fraîche : run 1 vide servi + vue (aucune donnée à migrer)
            c.execute(text("INSERT INTO residuel_runs (run_seq, label, is_served, note) "
                           "VALUES (1, 'run-initial', true, 'base fraîche') "
                           "ON CONFLICT (run_seq) DO NOTHING"))
            c.execute(text(_view_sql()))
            return "frais"
        # relkind == 'r' : table de base avec données → migrer
        if c.execute(text("SELECT 1 FROM residuel_runs WHERE run_seq=1")).scalar() is None:
            mn, mx = c.execute(text("SELECT min(computed_at), max(computed_at) FROM parcel_residuel")).first()
            c.execute(text("""INSERT INTO residuel_runs
                  (run_seq, label, is_served, computed_at_min, computed_at_max, note)
                  VALUES (1, 'legacy-mosaïque 29/07·05/08·19/08', true, :mn, :mx,
                          'mosaïque 3 états de code (245319·8032·178312), cf. M134 A.3bis')"""),
                      {"mn": mn, "mx": mx})
            c.execute(text("""INSERT INTO parcel_residuel_runs
                  (run_seq, parcel_id, taux_emprise_pct, pct_potentiel, sous_densite,
                   sdp_residuelle_m2, capacite_estimee, cause, computed_at)
                  SELECT 1, parcel_id, taux_emprise_pct, pct_potentiel, sous_densite,
                         sdp_residuelle_m2, capacite_estimee, cause, computed_at
                  FROM parcel_residuel"""))
        c.execute(text("ALTER TABLE parcel_residuel RENAME TO parcel_residuel_base_legacy"))
        c.execute(text(_view_sql()))
        return "migre"
