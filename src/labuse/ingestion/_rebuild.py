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


def rebuild_swap(session: Session, table: str, ddl: str,
                 populate: Callable[[str], object], *, commit: bool = True) -> object:
    """Reconstruit `table` sans bloquer les lecteurs.

    - `ddl` : le `CREATE TABLE IF NOT EXISTS <table> …` canonique — réécrit vers la shadow.
    - `populate(shadow)` : fait le travail LOURD (SELECT + INSERT) dans la table shadow ; sa valeur
      de retour est relayée telle quelle (stats du builder).
    Le SWAP (DROP live + RENAME + rename des index shadow) est la SEULE section sous verrou exclusif.
    """
    shadow = f"{table}__rebuild"
    session.execute(text(f'DROP TABLE IF EXISTS "{shadow}"'))          # nettoie un run précédent avorté
    session.execute(text(ddl.replace(f"EXISTS {table}", f'EXISTS "{shadow}"', 1)))
    result = populate(shadow)                                          # HORS-LIGNE : aucun verrou sur `table`
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
