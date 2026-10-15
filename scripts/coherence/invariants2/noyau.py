"""CHASSE-INVARIANTS-2 — noyau partagé : spec déclarative + exécuteur lecture seule.

L'idée de la vague 2 : on ne passe pas à 1 000 règles en en écrivant 900 de plus, on les GÉNÈRE
depuis ce que l'app sait d'elle-même (schéma, registre, routes, règlements), puis on les exécute
sur toute l'île servie. Une règle générée vaut une règle écrite si elle est VRAIE PAR CONSTRUCTION ;
une règle qui n'a pas de sens est écartée AVANT de tourner (famille.ecartees), jamais après.

Contrat commun à toutes les familles :

    RuleSpec = une règle. Deux formes :
      · SQL        : `sql_violations` COMPTE les lignes qui violent la règle (0 attendu). La règle
                     passe si count == 0, sinon ECART avec le compte + 3 exemples concrets
                     (via `exemples_sql`, sinon dérivé). C'est la forme de F1/F2/F4/F6.
      · callable   : `check(cx, api) -> (statut, message)` pour ce qui ne s'exprime pas en un seul
                     count (métamorphiques F3, robustesse API F5). Style des gardes de la vague 1.

    run_specs(cx, specs, api) exécute une liste de specs, défensif (toute surprise = SKIP, jamais
    un crash), et rend une liste de Resultat (spec, statut, message, exemples).

Lecture seule STRICTE : connexion `read_only`, `statement_timeout` posé, aucun INSERT/UPDATE/DDL.
Réutilise l'infra de la vague 1 (Cx, garde, run servi, helper API) — ne la redéfinit pas.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from typing import Any, Callable, Optional

# ── on s'appuie sur le banc de la vague 1 (ne DOUBLONNE pas son infra) ───────────────────────
_RACINE = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_RACINE / "scripts"))
from coherence.chasse_invariants import (  # noqa: E402
    Cx,
    TIMEOUT_MS,
    _api_code,
    _served_run,
    garde,
)
from coherence.lib import _dsn_defaut  # noqa: E402

RACINE = _RACINE

GRAVITES = ("FAUX-CLIENT", "INCOHERENT", "ROBUSTESSE")


# ───────────────────────────── la spec déclarative ──────────────────────────────────────────
@dataclasses.dataclass
class RuleSpec:
    """Une règle générée, traçable à sa famille et à sa source.

    id            identifiant stable (ex. 'F1.parcels.surface_m2.non_negatif')
    famille       'F1'…'F6'
    source        d'où la règle a été générée (table.colonne, chiffre du registre, route, zone PLU…)
    libelle       une ligne lisible (l'invariant en français)
    gravite       FAUX-CLIENT / INCOHERENT / ROBUSTESSE (cf. ECARTS-2.md)
    attendu       ce qu'on attend (ex. '0 ligne', 'capacité ≥', '≠ 500')

    Forme SQL (sql_violations renseigné) :
      sql_violations  SELECT count(*) des lignes QUI VIOLENT la règle (0 = règle tenue)
      exemples_sql    SELECT rendant jusqu'à 3 lignes-témoins de la violation (facultatif)
      params          paramètres psycopg (tuple) injectés dans les deux SQL
    Forme callable (check renseigné) :
      check           f(cx, api) -> (statut, message) ; statut ∈ OK/ECART/SKIP
    """

    id: str
    famille: str
    source: str
    libelle: str
    gravite: str = "INCOHERENT"
    attendu: str = "0 ligne"
    sql_violations: Optional[str] = None
    exemples_sql: Optional[str] = None
    params: tuple = ()
    check: Optional[Callable[[Any, Optional[str]], tuple]] = None

    def __post_init__(self):
        if self.gravite not in GRAVITES:
            raise ValueError(f"gravité inconnue : {self.gravite}")
        if (self.sql_violations is None) == (self.check is None):
            raise ValueError(f"{self.id} : exactement une forme (sql_violations XOR check)")


@dataclasses.dataclass
class Ecartee:
    """Une règle candidate ÉCARTÉE avant de tourner (traçabilité : générée ≠ retenue)."""

    id: str
    famille: str
    source: str
    raison: str


@dataclasses.dataclass
class Resultat:
    spec: RuleSpec
    statut: str          # OK / ECART / SKIP
    message: str
    exemples: list = dataclasses.field(default_factory=list)


# ───────────────────────────── exécuteur lecture seule ──────────────────────────────────────
def _exemples(cx, sql: str, params: tuple, k: int = 3) -> list:
    """Jusqu'à k lignes-témoins d'une violation (pour la revérification à la main)."""
    try:
        with cx.conn.cursor() as cur:
            cur.execute(sql, params) if params else cur.execute(sql)
            cols = [d[0] for d in cur.description] if cur.description else []
            out = []
            for row in cur.fetchmany(k):
                out.append(dict(zip(cols, row)))
            return out
    except Exception:
        cx.rollback()
        return []


def executer_une(cx, spec: RuleSpec, api: Optional[str] = None) -> Resultat:
    """Exécute UNE règle, défensif : toute surprise de schéma/perm/timeout = SKIP (jamais un crash)."""
    try:
        if spec.check is not None:
            statut, msg = spec.check(cx, api)
            return Resultat(spec, statut, msg, [])
        n = cx.scalar(spec.sql_violations, spec.params or None)
        n = int(n or 0)
        if n == 0:
            return Resultat(spec, "OK", f"{spec.attendu} tenu (0 violation)", [])
        exs = []
        if spec.exemples_sql:
            exs = _exemples(cx, spec.exemples_sql, spec.params)
        return Resultat(spec, "ECART", f"{n} violation(s) — attendu {spec.attendu}", exs)
    except Exception as e:  # noqa: BLE001 — un banc ne crashe jamais sur une règle
        cx.rollback()
        return Resultat(spec, "SKIP", f"{spec.id} indisponible : {type(e).__name__}: {e}", [])


def run_specs(cx, specs: Iterable[RuleSpec], api: Optional[str] = None) -> list:
    """Exécute une liste de specs, une par une (jamais deux requêtes lourdes en parallèle)."""
    return [executer_une(cx, s, api) for s in specs]


def bilan(resultats: list) -> dict:
    d = {"OK": 0, "ECART": 0, "SKIP": 0}
    for r in resultats:
        d[r.statut] = d.get(r.statut, 0) + 1
    return d


# ───────────────────────────── introspection du schéma (F1) ─────────────────────────────────
_NUM_TYPES = {
    "smallint", "integer", "bigint", "decimal", "numeric", "real",
    "double precision", "money",
}
_DATE_TYPES = {"date", "timestamp without time zone", "timestamp with time zone"}


@dataclasses.dataclass
class Colonne:
    table: str
    nom: str
    type_sql: str
    nullable: bool

    @property
    def numerique(self) -> bool:
        return self.type_sql in _NUM_TYPES

    @property
    def date_like(self) -> bool:
        return self.type_sql in _DATE_TYPES

    @property
    def texte(self) -> bool:
        return self.type_sql in ("text", "character varying", "character", "citext")


def table_existe(cx, table: str) -> bool:
    return bool(cx.scalar(
        "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s",
        (table,)))


def colonnes(cx, table: str) -> list:
    """Colonnes d'une table (nom, type, nullable)."""
    with cx.conn.cursor() as cur:
        cur.execute(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position", (table,))
        return [Colonne(table, n, t, (nu == "YES")) for (n, t, nu) in cur.fetchall()]


def toutes_les_tables(cx) -> list:
    with cx.conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY 1")
        return [r[0] for r in cur.fetchall()]


# ───────────────────────────── le registre (F2) ─────────────────────────────────────────────
def registre_chiffres(cx) -> list:
    with cx.conn.cursor() as cur:
        cur.execute("SELECT id, libelle, unite, niveau, moteur, reservoirs, portee FROM registre_chiffres ORDER BY id")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def registre_robinets(cx) -> list:
    with cx.conn.cursor() as cur:
        cur.execute("SELECT id, categorie, nom, parent, route, mode_rendu, chiffres, hors_registre "
                    "FROM registre_robinets ORDER BY id")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


# ───────────────────────────── échantillon stratifié (F2/F6) ────────────────────────────────
def echantillon_stratifie(cx, n: int = 2000, vivantes_seulement: bool = True) -> list:
    """n idu stratifiés par commune (proportionnel), DÉTERMINISTE (ordre md5, aucun aléa de session).

    Chaque commune reçoit ceil(n · part_commune) idu, pris dans l'ordre md5(idu) : même échantillon à
    chaque exécution, rejouable par la garde de nuit. Lecture seule (aucun TABLESAMPLE non déterministe).
    """
    filtre = "WHERE cadastre_disparue_le IS NULL" if vivantes_seulement else ""
    sql = f"""
        WITH base AS (
            SELECT idu, commune,
                   row_number() OVER (PARTITION BY commune ORDER BY md5(idu)) AS rn,
                   count(*)     OVER (PARTITION BY commune)                   AS c,
                   count(*)     OVER ()                                       AS tot
            FROM parcels {filtre}
        )
        SELECT idu FROM base
        WHERE rn <= ceil({int(n)}::numeric * c / tot)
        ORDER BY commune, rn
    """
    with cx.conn.cursor() as cur:
        cur.execute(sql)
        return [r[0] for r in cur.fetchall()]


# ───────────────────────────── helper API (F2/F5/F6) ────────────────────────────────────────
def api_json(base: str, path: str, timeout: int = 30):
    """(status, payload|None). Jamais une exception : un échec réseau = (code|'ERR', None)."""
    try:
        with urllib.request.urlopen(base + path, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return "ERR", None


def api_dispo(base: str) -> bool:
    return _api_code(base, "/healthz") == 200


# ───────────────────────────── served run (vague 1) ─────────────────────────────────────────
def run_servi():
    """(scoring_run, residuel_run_seq, cascade_run) depuis le manifeste vivant."""
    return _served_run()


# ───────────────────────────── connexion ────────────────────────────────────────────────────
def connexion() -> Cx:
    return Cx(_dsn_defaut())


__all__ = [
    "RuleSpec", "Ecartee", "Resultat", "GRAVITES", "Colonne",
    "run_specs", "executer_une", "bilan",
    "table_existe", "colonnes", "toutes_les_tables",
    "registre_chiffres", "registre_robinets", "echantillon_stratifie",
    "api_json", "api_dispo", "run_servi", "connexion",
    "Cx", "garde", "TIMEOUT_MS", "RACINE",
]
