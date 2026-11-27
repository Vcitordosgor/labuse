"""M-O P2-59 — rebuild NON BLOQUANT d'une table dérivée.

Le piège (déjà diagnostiqué dans division_or._ensure_ddl) : `DROP TABLE`/`ALTER` prennent un
verrou ACCESS EXCLUSIVE tenu JUSQU'AU COMMIT. Un rebuild `DROP + CREATE + INSERT` d'une table lue
en direct par l'API (pc_caducs, defisc_fenetres badges ; score_e) bloque donc toute lecture API en
file pendant TOUTE la durée de l'INSERT (mesuré : defisc 95 s, score_e 13 s).

`rebuild_swap` construit et peuple une table SHADOW HORS-LIGNE (le long INSERT ne prend aucun verrou
sur la table servie), puis SWAP par rename — l'ACCESS EXCLUSIVE n'est tenu que pendant l'échange de
métadonnées (~ms). Prérequis (vérifiés pour les tables visées) : table FEUILLE (aucune vue ni FK
ENTRANTE) et index DÉRIVANT du nom de table (PK auto-nommée `<table>_pkey`) — ils sont renommés au
swap pour libérer les noms shadow au prochain rebuild.
"""
from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.orm import Session


class RebuildWouldEmptyError(RuntimeError):
    """OUTIL-PERMIS-FIX-15 — `rebuild_swap` a REFUSÉ de remplacer une table SERVIE PEUPLÉE par une
    reconstruction VIDE (0 ligne). Cause typique : source transitoirement vide/verrouillée (reload
    concurrent de `sitadel_permits` par un autre worktree, statement_timeout, bascule en cours). La
    table servie est CONSERVÉE telle quelle (aucun swap) — jamais remplacée par du vide en silence.
    Forcer l'effacement volontaire avec `allow_empty=True`."""


def rebuild_swap(session: Session, table: str, ddl: str,
                 populate: Callable[[str], object], *, commit: bool = True,
                 allow_empty: bool = False) -> object:
    """Reconstruit `table` sans bloquer les lecteurs.

    - `ddl` : le `CREATE TABLE IF NOT EXISTS <table> …` canonique — réécrit vers la shadow.
    - `populate(shadow)` : fait le travail LOURD (SELECT + INSERT) dans la table shadow ; sa valeur
      de retour est relayée telle quelle (stats du builder).
    Le SWAP (DROP live + RENAME + rename des index shadow) est la SEULE section sous verrou exclusif.

    OUTIL-PERMIS-FIX-15 — GARDE-FOU VIDE : si la shadow est VIDE (0 ligne) alors que la table servie
    en a, le swap est REFUSÉ (`RebuildWouldEmptyError`) AVANT tout `DROP` de la table servie → elle
    est conservée intacte. C'est la cause des deux disparitions de `pc_caducs` (une reconstruction sur
    source transitoirement vide écrasait les 4 440 lignes par du vide). `allow_empty=True` lève la
    garde pour un effacement volontaire. La garde protège aussi `defisc_fenetres` et `score_e`.
    """
    shadow = f"{table}__rebuild"
    session.execute(text(f'DROP TABLE IF EXISTS "{shadow}"'))          # nettoie un run précédent avorté
    session.execute(text(ddl.replace(f"EXISTS {table}", f'EXISTS "{shadow}"', 1)))
    result = populate(shadow)                                          # HORS-LIGNE : aucun verrou sur `table`
    # ── GARDE-FOU VIDE (avant tout DROP de la table servie : elle reste intacte si on refuse) ──
    if not allow_empty:
        shadow_n = session.execute(text(f'SELECT count(*) FROM "{shadow}"')).scalar() or 0
        if shadow_n == 0:
            live_n = 0
            if session.execute(text("SELECT to_regclass(:t)"), {"t": table}).scalar() is not None:
                live_n = session.execute(text(f'SELECT count(*) FROM "{table}"')).scalar() or 0
            if live_n > 0:
                session.execute(text(f'DROP TABLE IF EXISTS "{shadow}"'))   # nettoie la shadow refusée
                raise RebuildWouldEmptyError(
                    f"{table} : reconstruction VIDE (0 ligne) alors que la table servie en a {live_n} — "
                    "SWAP REFUSÉ, table conservée (source dégradée / verrou / reload concurrent ?). "
                    "Forcer avec allow_empty=True si l'effacement est voulu.")
    # ── SWAP atomique — métadonnées seules, verrou ACCESS EXCLUSIVE de l'ordre de la ms ──
    session.execute(text(f'DROP TABLE IF EXISTS "{table}"'))
    session.execute(text(f'ALTER TABLE "{shadow}" RENAME TO "{table}"'))
    # index/contraintes de la shadow → noms canoniques (les noms d'index sont SCHEMA-uniques :
    # sans ça, le prochain CREATE shadow entrerait en collision).
    for (ix,) in session.execute(text(
            "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND tablename = :t"),
            {"t": table}):
        if ix.startswith(shadow):
            session.execute(text(f'ALTER INDEX "{ix}" RENAME TO "{table + ix[len(shadow):]}"'))
    if commit:
        session.commit()
    return result
