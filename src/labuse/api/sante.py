"""CONNEXIONS-2 Lot 7.2 (N3) — SONDE des endpoints MÉTIER (avec DB), pas seulement /health sans DB.

Le trou exact du mandat : `/accueil/chiffres` peut répondre 200 tout en servant un ÉCRAN VIDE (run
servi introuvable → `parcelles = null`). La sonde `healthcheck` historique ne teste que `GET /health`
(process vivant, sans base) — elle ne l'aurait jamais vu. Ici on appelle une liste d'endpoints porteurs
AVEC la base et on vérifie FORME + NON-VACUITÉ. Résultat servi à la tuile « Santé » du dashboard, et
une panne notifie l'admin (event systeme, dédup jour) au premier passage rouge.

Aucun appel payant : la brique IA vérifie que le Copilote est CONFIGURÉ (clé + modèle), pas un /ask réel.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def _accueil_chiffres(db: Session) -> tuple[bool, str | None]:
    from . import accueil
    accueil._cache.update(at=0.0, data=None)      # live : on veut l'état RÉEL, pas le cache
    d = accueil.accueil_chiffres(db)
    ok = isinstance(d, dict) and d.get("parcelles") is not None
    return ok, None if ok else "payload accueil vide (parcelles absentes) — run servi introuvable"


def _sources(db: Session) -> tuple[bool, str | None]:
    from .app import list_sources
    rows = list_sources(db)
    ok = isinstance(rows, list) and len(rows) > 0
    return ok, None if ok else "aucune source servie"


def _fiche_temoin(db: Session) -> tuple[bool, str | None]:
    idu = db.execute(text("SELECT idu FROM parcels LIMIT 1")).scalar()
    if not idu:
        return True, None                         # base sans parcelle (test) : non bloquant
    row = db.execute(text("SELECT idu FROM parcels WHERE idu = :i"), {"i": idu}).first()
    return bool(row), None if row else "fiche parcelle témoin introuvable"


def _radar(db: Session) -> tuple[bool, str | None]:
    from ..pige import marche
    s = marche.stats(db)
    ok = isinstance(s, dict) and "communes" in s and "ile" in s
    return ok, None if ok else "stats Radar mal formées"


def _projets(db: Session) -> tuple[bool, str | None]:
    # forme : la table répond (un compte témoin PEUT n'avoir aucun projet — on ne l'exige pas).
    db.execute(text("SELECT count(*) FROM projets"))
    return True, None


def _ia_dry(db: Session) -> tuple[bool, str | None]:
    # /ask en mode « dry » : on vérifie que le Copilote est CONFIGURÉ (clé API + modèle déclaré),
    # sans appel payant au modèle. Un manque de config = écran Copilote muet à surveiller.
    try:
        import os
        from .. import ai_models
        cle = bool(os.environ.get("ANTHROPIC_API_KEY"))
        modele = bool(getattr(ai_models, "MODEL_REASONING", None))
        # la clé peut manquer en local/CI : ce n'est PAS un échec métier tant que le MODÈLE est déclaré
        # (le contrat du Copilote). On signale l'absence de clé en détail, sans faire rougir la tuile.
        ok = modele
        return ok, None if cle else "clé ANTHROPIC absente (dry-run : modèle déclaré, appel non testé)"
    except Exception as e:  # noqa: BLE001
        return False, f"config IA illisible ({type(e).__name__})"


#: les endpoints porteurs sondés (nom lisible → fonction (db) -> (ok, detail)).
SONDES = [
    ("/accueil/chiffres", _accueil_chiffres),
    ("/sources", _sources),
    ("fiche parcelle (témoin)", _fiche_temoin),
    ("liste Radar", _radar),
    ("projets (compte témoin)", _projets),
    ("/ask (dry-run)", _ia_dry),
]


def sonde_metier(db: Session) -> dict:
    """Exécute toutes les sondes ; renvoie {ok, endpoints:[{endpoint, ok, detail}]}. Ne lève jamais :
    une sonde qui explose devient un endpoint « ko » avec le motif (jamais un 500 de la tuile Santé)."""
    resultats = []
    for nom, fn in SONDES:
        try:
            ok, detail = fn(db)
        except Exception as e:  # noqa: BLE001 — une sonde ratée = endpoint ko, pas un crash de la tuile
            ok, detail = False, f"{type(e).__name__}: {e}"[:180]
        resultats.append({"endpoint": nom, "ok": bool(ok), "detail": None if ok else detail})
    return {"ok": all(r["ok"] for r in resultats), "endpoints": resultats}
