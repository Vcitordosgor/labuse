"""SOURCES-AUDIT-1 — socle de génération des fiches de complétude.

LECTURE SEULE. Ne modifie rien. Rejouable.

Ce module :
  · charge les constantes de vérité du code SANS importer le paquet labuse (qui tire des
    dépendances lourdes : rasterio, weasyprint…). On EXÉCUTE en isolation les deux fichiers
    de constantes (`circuit_etats.py` : NOM_VERS_SLUG / familles ; `registre/tables.py` :
    RESERVOIR_TABLES) — ils n'importent que `__future__`/`dataclasses`, donc l'exec est sûr.
  · lit la base `labuse` (data_sources, source_veille, registre_*, filtre_resultats,
    spatial_layers) et le graphe du registre (réservoir → chiffre → robinet).

La CARTE de visibilité d'une source est DÉRIVÉE, jamais saisie :
    data_sources.name → slug (NOM_VERS_SLUG) → chiffres (registre_chiffres.reservoirs)
    → robinets (registre_robinets.chiffres) → catégorie + route = où elle se voit.
"""
from __future__ import annotations

import os
import runpy
from pathlib import Path

import psycopg

REPO = Path(__file__).resolve().parents[5]          # …/labuse-etat
SRC = REPO / "src" / "labuse"


def db_url() -> str:
    """URL psycopg depuis .env (on retire le suffixe SQLAlchemy +psycopg)."""
    url = os.environ.get("LABUSE_DATABASE_URL", "")
    if not url:
        env = REPO / ".env"
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("LABUSE_DATABASE_URL="):
                url = line.split("=", 1)[1].strip()
                break
    return url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://")


def connect():
    return psycopg.connect(db_url())


def _exec_isolated(path: Path) -> dict:
    """Exécute un fichier de constantes en isolation et renvoie son espace de noms."""
    return runpy.run_path(str(path))


def charger_constantes() -> dict:
    """NOM_VERS_SLUG, familles, RESERVOIR_TABLES — depuis le code, sans importer labuse."""
    etats = _exec_isolated(SRC / "circuit_etats.py")
    tables = _exec_isolated(SRC / "registre" / "tables.py")
    return {
        "NOM_VERS_SLUG": etats["NOM_VERS_SLUG"],
        "FAMILLE_DE_CATEGORIE": etats["FAMILLE_DE_CATEGORIE"],
        "FAMILLES_ORDRE": etats["FAMILLES_ORDRE"],
        "RESERVOIR_TABLES": tables["RESERVOIR_TABLES"],
        "TABLES_FABRIQUEES": tables["TABLES_FABRIQUEES"],
    }


# ── requêtes base ────────────────────────────────────────────────────────────────────────
DS_COLS = [
    "id", "name", "category", "provider", "access_type", "status", "documentation_url",
    "endpoint_url", "last_sync_at", "reliability_level", "rate_limit", "legal_notes",
    "technical_notes", "source_millesime", "source_horizon_at", "source_cadence",
    "prochain_millesime_at", "fraicheur_statut", "affichage_desactive", "mode_remplissage",
    "cadence_attendue_jours", "cadence_statut", "alias_de", "retiree_le", "retiree_raison",
]


def lire_sources(cur) -> list[dict]:
    cur.execute(f"SELECT {', '.join(DS_COLS)} FROM data_sources ORDER BY id")
    return [dict(zip(DS_COLS, r)) for r in cur.fetchall()]


def lire_veille(cur) -> dict[int, dict]:
    cur.execute(
        "SELECT source_id, methode, dernier_statut, dernier_passage_at, dernier_vu, actif,"
        " cadence_heures, cadence_attendue_jours, echecs_consecutifs, mail_alerte,"
        " convention_echeance FROM source_veille")
    cols = ["source_id", "methode", "dernier_statut", "dernier_passage_at", "dernier_vu",
            "actif", "cadence_heures", "cadence_attendue_jours", "echecs_consecutifs",
            "mail_alerte", "convention_echeance"]
    out = {}
    for r in cur.fetchall():
        d = dict(zip(cols, r))
        out[d["source_id"]] = d
    return out


def lire_chiffres(cur) -> list[dict]:
    cur.execute(
        "SELECT id, libelle, unite, niveau, moteur, calcul, reservoirs, portee, classe_regle,"
        " verdict_regle FROM registre_chiffres")
    cols = ["id", "libelle", "unite", "niveau", "moteur", "calcul", "reservoirs", "portee",
            "classe_regle", "verdict_regle"]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def lire_robinets(cur) -> list[dict]:
    cur.execute(
        "SELECT id, categorie, nom, parent, route, mode_rendu, chiffres, hors_registre"
        " FROM registre_robinets")
    cols = ["id", "categorie", "nom", "parent", "route", "mode_rendu", "chiffres",
            "hors_registre"]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def lire_filtres(cur) -> dict[str, list[dict]]:
    """filtre_resultats groupés par motif source (clé filtre)."""
    cur.execute(
        "SELECT source, version, controle, nature, severite, verdict FROM filtre_resultats")
    cols = ["source", "version", "controle", "nature", "severite", "verdict"]
    out: dict[str, list[dict]] = {}
    for r in cur.fetchall():
        d = dict(zip(cols, r))
        out.setdefault(d["source"], []).append(d)
    return out


def compter_table(cur, table: str) -> int | None:
    """count(*) d'une table si elle existe (to_regclass), sinon None."""
    cur.execute("SELECT to_regclass(%s)", (table,))
    if cur.fetchone()[0] is None:
        return None
    try:
        cur.execute(f"SELECT count(*) FROM {table}")
        return cur.fetchone()[0]
    except Exception:
        return None


def compter_couches(cur) -> dict[str, int]:
    cur.execute("SELECT kind, count(*) FROM spatial_layers GROUP BY kind")
    return {k: n for k, n in cur.fetchall()}


def layers_par_source(cur) -> dict[int, dict]:
    cur.execute(
        "SELECT data_source_id, count(*), array_agg(DISTINCT kind)"
        " FROM spatial_layers WHERE data_source_id IS NOT NULL GROUP BY data_source_id")
    return {r[0]: {"n": r[1], "kinds": r[2]} for r in cur.fetchall()}
