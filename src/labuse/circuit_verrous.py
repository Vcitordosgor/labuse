"""CIRCUIT-5 — LES VERROUS. Un verrou = une phrase en français + un test qui la fait
respecter + un endroit sur la page où elle se lit (règle 1 du mandat).

Tous les verrous sont réunis dans UNE commande — `labuse circuit verrous` — qui les joue
dans l'ordre des lots et sort en erreur au premier cassé. Elle est jouée par pytest
(`tests/verrous/`, marque `verrous`), par la sonde de nuit (résultat au Journal), et par
`deploy.sh` avant tout déploiement (règle 2).

Trois verdicts :
  · `ok`        — la phrase est vraie, la preuve le dit ;
  · `casse`     — la phrase est fausse : la commande sort en erreur, le déploiement refuse ;
  · `a_decider` — rien de cassé, mais une question attend le geste de Vic (orphelines à
    purger, réservoirs sans lecteur) : affiché au Résumé, ne bloque jamais un déploiement.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

from sqlalchemy import event, text

# ── le cadre ────────────────────────────────────────────────────────────────────────────


@dataclass
class ResultatVerrou:
    id: str
    phrase: str
    verdict: str                    # ok | casse | a_decider
    preuve: str                     # une ligne lisible (ce qui a été mesuré)
    details: list[str] = field(default_factory=list)   # les éléments en cause, s'il y en a


@dataclass(frozen=True)
class Verrou:
    id: str
    lot: int
    phrase: str
    jouer: Callable[..., ResultatVerrou]    # jouer(db) — db peut être ignoré (verrous statiques)


# ── outillage : les noms de tables dans une requête ─────────────────────────────────────

#: FROM/JOIN/INTO/UPDATE/DELETE FROM <ident> — les faux positifs (imports Python, alias…)
#: sont éliminés en ne retenant que les identifiants qui SONT des relations du schéma.
_RE_TABLE = re.compile(
    r"\b(?:from|join|into|update|delete\s+from)\s+([a-zA-Z_][a-zA-Z0-9_.]*)", re.IGNORECASE)

#: suffixes de l'échange CIRCUIT-3 (quarantaine) : `x__attente`/`x__precedente` appartiennent
#: au même réservoir que `x`.
_SUFFIXES_ECHANGE = ("__attente", "__precedente")


def _normaliser(ident: str) -> str:
    ident = ident.split(".")[-1].strip('"').lower()
    for suf in _SUFFIXES_ECHANGE:
        if ident.endswith(suf):
            ident = ident[: -len(suf)]
    return ident


def tables_citees(texte: str) -> set[str]:
    """Les identifiants candidats (après FROM/JOIN/INTO/UPDATE/DELETE FROM), normalisés."""
    return {_normaliser(m.group(1)) for m in _RE_TABLE.finditer(texte)}


_RE_PREMIER_IDENT = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)")


def table_declaree(champ: str) -> str | None:
    """Le nom de table d'un champ `Donnee.table` — format réel du registre : `parcels.surface_m2`,
    `commune_contexte_sru (objectif_pct, taux_lls)`, `spatial_layers (kind=znieff)`,
    `(web — aucun réservoir…)` (→ None : pas une table)."""
    m = _RE_PREMIER_IDENT.match(champ)
    return _normaliser(m.group(1)) if m else None


def relations_schema(db) -> set[str]:
    """Toutes les relations du schéma public (tables, vues, matérialisations, partitions)."""
    rows = db.execute(text(
        "SELECT c.relname FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'public' "
        "WHERE c.relkind IN ('r', 'm', 'v', 'p')")).scalars().all()
    return {r.lower() for r in rows}


@contextmanager
def journal_requetes(bind) -> Iterator[set[str]]:
    """Capture les tables touchées par TOUTES les requêtes émises pendant le bloc (lecture à
    l'exécution du verrou V1b — le « journal des requêtes de la session » du mandat)."""
    touchees: set[str] = set()

    def _capter(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        touchees.update(tables_citees(statement))

    engine = getattr(bind, "engine", bind)
    event.listen(engine, "before_cursor_execute", _capter)
    try:
        yield touchees
    finally:
        event.remove(engine, "before_cursor_execute", _capter)


# ── LOT 1 — le verrou des tables ────────────────────────────────────────────────────────

_MOTEURS_DIR = Path(__file__).parent / "registre" / "moteurs"


def _carte() -> set[str]:
    from .registre import tables as T
    return {t.lower() for t in T.tables_carte()}


def verrou_tables_statique(db=None, *, sources: list[Path] | None = None,
                           schema: set[str] | None = None) -> ResultatVerrou:
    """V1a — analyse statique : les noms de tables dans les requêtes des moteurs du registre
    et des passe-plats (`Donnee.table`) sont tous dans la carte. Seul un candidat qui EST une
    relation du schéma est une violation (le reste = faux positifs du texte Python : imports,
    prose, tuilages WMTS distants). `sources`/`schema` sont surchargés par le test de preuve
    (une fonction témoin qui lit une table orpheline doit CASSER)."""
    from .registre.donnees import DONNEES

    fichiers = sorted(sources if sources is not None else _MOTEURS_DIR.glob("*.py"))
    if schema is None and db is not None:
        schema = relations_schema(db)
    if schema is None:
        return ResultatVerrou("V1a", PHRASES["V1a"], "casse",
                              "injouable sans schéma (base indisponible)")
    carte = _carte()
    hors_carte: list[str] = []
    for f in fichiers:
        candidats = tables_citees(Path(f).read_text(encoding="utf-8"))
        for t in sorted(candidats):
            if t not in carte and t in schema:
                hors_carte.append(f"{Path(f).name} : {t}")
    # les passe-plats : chaque table déclarée par une donnée doit être dans la carte
    for cid, d in DONNEES.items():
        t = table_declaree(d.table) if d.table else None
        if t and t not in carte and t in schema:
            hors_carte.append(f"donnée {cid} : table déclarée {d.table} hors carte")
    if hors_carte:
        return ResultatVerrou("V1a", PHRASES["V1a"], "casse",
                              f"{len(hors_carte)} lecture(s) hors carte", hors_carte)
    return ResultatVerrou("V1a", PHRASES["V1a"], "ok",
                          f"{len(fichiers)} module(s) moteur + {len(DONNEES)} données passés au crible")


def verrou_tables_execution(db) -> ResultatVerrou:
    """V1b — lecture à l'exécution : un passage de la sonde sur les témoins ne touche aucune
    table hors carte (journal des requêtes de la session)."""
    from . import sonde_circuit

    carte = _carte()
    schema = relations_schema(db)
    with journal_requetes(db.get_bind()) as touchees:
        sonde_circuit.verifier_robinets(db)
    reelles = {t for t in touchees if t in schema}
    hors = sorted(reelles - carte)
    if hors:
        return ResultatVerrou("V1b", PHRASES["V1b"], "casse",
                              f"{len(hors)} table(s) touchée(s) hors carte pendant la sonde", hors)
    return ResultatVerrou("V1b", PHRASES["V1b"], "ok",
                          f"{len(reelles)} tables touchées pendant la sonde, toutes dans la carte")


def verrou_tables_orphelines(db) -> ResultatVerrou:
    """V1c — les orphelines sont connues, listées, et attendent le geste de Vic (jamais un
    DROP). Une orpheline SANS action proposée est un trou de curation : elle est nommée."""
    from .registre import tables as T

    orph = sorted(T.orphelines(relations_schema(db)))
    sans_action = [t for t in orph if t not in T.ACTIONS_PROPOSEES]
    if sans_action:
        return ResultatVerrou("V1c", PHRASES["V1c"], "casse",
                              f"{len(sans_action)} orpheline(s) sans action proposée "
                              f"(docs/CIRCUIT/TABLES-ORPHELINES.md à compléter)", sans_action)
    if orph:
        return ResultatVerrou("V1c", PHRASES["V1c"], "a_decider",
                              f"{len(orph)} orpheline(s) à purger/archiver (labuse tables purger)", orph)
    return ResultatVerrou("V1c", PHRASES["V1c"], "ok", "aucune table orpheline dans le schéma")


def verrou_reservoirs_sans_lecteur(db=None) -> ResultatVerrou:
    """V1d — chaque réservoir de la vitrine est lu par au moins une donnée du registre ; un
    réservoir sans lecteur pose la question « source à retirer, ou lecteur manquant ? »."""
    from .registre import tables as T
    from .registre.donnees import DONNEES

    # un réservoir est LU si une donnée le nomme (reservoirs=), si elle déclare une de ses
    # tables (table=), ou si elle déclare une de ses couches (kind=… dans spatial_layers).
    couche_vers_slugs: dict[str, set[str]] = {}
    for slug, rt in T.RESERVOIR_TABLES.items():
        for k in rt.couches:
            couche_vers_slugs.setdefault(k, set()).add(slug)
    lus = {res for d in DONNEES.values() for res in d.reservoirs}
    for d in DONNEES.values():
        if not d.table:
            continue
        t = table_declaree(d.table)
        if t:
            lus.update(T.reservoirs_de(t))
        for k in re.findall(r"kind=([a-zA-Z_0-9]+)", d.table):
            lus.update(couche_vers_slugs.get(k, ()))
    sans_lecteur = sorted(
        slug for slug, rt in T.RESERVOIR_TABLES.items()
        if rt.tables and rt.note is None and slug not in lus)
    if sans_lecteur:
        return ResultatVerrou("V1d", PHRASES["V1d"], "a_decider",
                              f"{len(sans_lecteur)} réservoir(s) sans lecteur — source à retirer, "
                              "ou lecteur manquant ?", sans_lecteur)
    return ResultatVerrou("V1d", PHRASES["V1d"], "ok",
                          "chaque réservoir servi est lu par au moins une donnée du registre")


# ── le registre des verrous (complété lot par lot) ──────────────────────────────────────

PHRASES: dict[str, str] = {
    "V1a": "Aucun moteur ne lit une table hors de la carte table → réservoir (analyse statique).",
    "V1b": "Pendant un passage de la sonde sur les témoins, aucune table hors carte n'est touchée.",
    "V1c": "Toute table du schéma appartient à la carte, ou est une orpheline listée qui attend le geste de Vic.",
    "V1d": "Chaque réservoir servi est lu par au moins une donnée — aucun réservoir muet ne dort dans la vitrine.",
}

VERROUS: tuple[Verrou, ...] = (
    Verrou("V1a", 1, PHRASES["V1a"], verrou_tables_statique),
    Verrou("V1b", 1, PHRASES["V1b"], verrou_tables_execution),
    Verrou("V1c", 1, PHRASES["V1c"], verrou_tables_orphelines),
    Verrou("V1d", 1, PHRASES["V1d"], verrou_reservoirs_sans_lecteur),
)


def jouer_tous(db, *, arret_premier: bool = False) -> list[ResultatVerrou]:
    """Joue tous les verrous dans l'ordre des lots. `arret_premier` : sort au premier cassé
    (comportement CLI/deploy) ; sinon joue tout (page Circuit, rapport complet)."""
    resultats: list[ResultatVerrou] = []
    for v in VERROUS:
        try:
            r = v.jouer(db)
        except Exception as e:  # un verrou qui ne peut pas se jouer est un verrou cassé
            r = ResultatVerrou(v.id, v.phrase, "casse", f"injouable : {e.__class__.__name__}: {e}")
        resultats.append(r)
        if arret_premier and r.verdict == "casse":
            break
    return resultats
