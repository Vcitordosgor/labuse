"""CIRCUIT-3 lot 4 — LA QUARANTAINE POUR LES DONNÉES SERVIES EN DIRECT.

Pour une source à portée `live` (dont l'ingestion REMPLACE une table servie), l'ingestion écrit
dans `<table>__attente`, le filtre se joue DESSUS, et l'échange (`ALTER TABLE … RENAME`, dans une
transaction, index conservés par le rename) n'a lieu QUE sur verdict OK ou sur « servir quand même »
de Vic. La version précédente reste sous `<table>__precedente` pour un retour immédiat.

Une injection en quarantaine ne se sert pas : la table servie reste l'ancienne tant que
`<table>__attente` n'a pas passé le filtre.

Ordre des renames (atomique dans la transaction de session) :
  1. si `<table>` existe : `<table>` → `<table>__precedente` (l'ancienne, pour le retour) ;
  2. `<table>__attente` → `<table>` (la nouvelle, servie).
Les index/contraintes suivent la table au rename (PostgreSQL) — ils restent fonctionnels.
"""
from __future__ import annotations

import logging
from dataclasses import replace

from sqlalchemy import text

from . import echantillon
from .cadre import Filtre, Verdict, _ensure_sur_session, _table_existe, jouer, version_servie

log = logging.getLogger("labuse.filtres.quarantaine")

# Alias réservoir (registre) → clé de filtre, quand ils diffèrent.
_ALIAS_RESERVOIR_FILTRE = {
    "cadastre_api_carto": "cadastre_etalab",
    "gpu_plu_api_carto": "gpu_plu",
    "filosofi_carreaux": "filosofi",
    "deal_ppr": "georisques_mvt",
}


def reservoirs_live() -> set[str]:
    """Les réservoirs qui alimentent AU MOINS une donnée à portée `live` (registre = vérité)."""
    from ..registre.donnees import DONNEES
    return {r for d in DONNEES.values() if getattr(d, "portee", "") == "live"
            for r in (d.reservoirs or ())}


def sources_live_registre() -> set[str]:
    """Les CLÉS DE FILTRE correspondant aux réservoirs live (via l'alias)."""
    out = set()
    for r in reservoirs_live():
        out.add(_ALIAS_RESERVOIR_FILTRE.get(r, r))
    return out


def _attente(table: str) -> str:
    return f"{table}__attente"


def _precedente(table: str) -> str:
    return f"{table}__precedente"


def jouer_sur_attente(db, filtre: Filtre, version: str | None = None) -> Verdict | None:
    """Joue le filtre sur `<table>__attente` (la version fraîchement ingérée, pas encore servie)."""
    if not filtre.table:
        return None
    att = _attente(filtre.table)
    if not _table_existe(db, att):
        return None
    f2 = replace(filtre, table=att, propres=[c for c in filtre.propres if c.id != "d_echantillon"])
    # l'échantillon producteur vise la table SERVIE (clé métier) — on le rejoue tel quel sur l'attente
    # via la même clé (les enregistrements témoins existent aussi dans l'attente).
    if echantillon.chemin(filtre.source).exists():
        f2.propres.append(echantillon.controle())
    v = version or (version_servie(db, filtre) + " (attente)")
    return jouer(db, f2, version=v)


def echanger(db, source: str, *, par: str = "cli", force: bool = False,
             motif: str | None = None) -> dict:
    """Joue le filtre sur `<table>__attente` et, si OK (ou `force`=« servir quand même »), échange
    les tables dans la transaction de session. Sinon la nouvelle version reste en QUARANTAINE."""
    from .. import circuit_journal
    from . import get_filtre
    _ensure_sur_session(db)
    filtre = get_filtre(source)
    if not filtre or not filtre.table:
        return {"ok": False, "motif": "source sans table servie"}
    table, att, prec = filtre.table, _attente(filtre.table), _precedente(filtre.table)
    if not _table_existe(db, att):
        return {"ok": False, "motif": f"pas de table d'attente {att} (rien à échanger)"}
    v = jouer_sur_attente(db, filtre)
    if v is None:
        return {"ok": False, "motif": "filtre injouable sur l'attente"}
    if v.verdict == "quarantaine" and not force:
        circuit_journal.journaliser(db, "filtre", source, par, "refuse",
                                    {"echange": "quarantaine", "bloquants_ko": v.bloquants_ko})
        return {"ok": False, "motif": "quarantaine", "verdict": v.verdict,
                "bloquants_ko": v.bloquants_ko}
    # ÉCHANGE atomique (transaction de session ; les renames portent leurs index).
    if _table_existe(db, prec):
        db.execute(text(f"DROP TABLE IF EXISTS {prec} CASCADE"))
    if _table_existe(db, table):
        db.execute(text(f"ALTER TABLE {table} RENAME TO {prec.split('.')[-1]}"))
    db.execute(text(f"ALTER TABLE {att} RENAME TO {table.split('.')[-1]}"))
    circuit_journal.journaliser(db, "filtre", source, par, "ok",
                                {"echange": "servi", "force": force, "motif": motif,
                                 "verdict": v.verdict})
    return {"ok": True, "verdict": v.verdict, "servie": table, "precedente": prec,
            "force": force}


def revenir(db, source: str, *, par: str = "cli") -> dict:
    """Retour immédiat : remet `<table>__precedente` en table servie (geste journalisé)."""
    from .. import circuit_journal
    from . import get_filtre
    filtre = get_filtre(source)
    if not filtre or not filtre.table:
        return {"ok": False, "motif": "source sans table servie"}
    table, prec = filtre.table, _precedente(filtre.table)
    if not _table_existe(db, prec):
        return {"ok": False, "motif": f"pas de version précédente {prec}"}
    # la table servie actuelle repart en attente (récupérable), la précédente redevient servie.
    if _table_existe(db, table):
        db.execute(text(f"DROP TABLE IF EXISTS {_attente(table)} CASCADE"))
        db.execute(text(f"ALTER TABLE {table} RENAME TO {_attente(table).split('.')[-1]}"))
    db.execute(text(f"ALTER TABLE {prec} RENAME TO {table.split('.')[-1]}"))
    circuit_journal.journaliser(db, "revenir", source, par, "ok", {"retour": "version precedente"})
    return {"ok": True, "servie": table}
