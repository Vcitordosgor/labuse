"""CIRCUIT-3 — LES FILTRES : la qualité à l'intérieur de chaque source.

Un réservoir = un filtre déclaré en code (règle 1). Ce paquet expose :
  - le cadre (Controle, Filtre, jouer, universels) — `cadre.py`.
  - le registre `FILTRES` : un filtre par source, fusion des filtres RICHES (lot 2, sources.py)
    et d'un filtre par défaut (universels seuls) pour toute source à job de sources_ingestion.yaml.

Lot 1.5 — invariant testé : toute source de sources_ingestion.yaml a un filtre (sinon test rouge).
"""
from __future__ import annotations

import functools
from pathlib import Path

import yaml

from .cadre import (Controle, Filtre, Resultat, Verdict, dernier_verdict,  # noqa: F401
                    en_quarantaine, ensure_tables, jouer, ko, ok, skip, version_servie)
from . import echantillon
from .sources import FILTRES_RICHES

_YAML = Path(__file__).resolve().parents[2].parent / "config" / "sources_ingestion.yaml"


@functools.lru_cache(maxsize=1)
def sources_a_job() -> list[dict]:
    """Les sources à job d'ingestion (label + motif) de sources_ingestion.yaml."""
    p = _YAML
    if not p.exists():  # repo layout alternatif : remonter jusqu'à trouver config/
        for parent in Path(__file__).resolve().parents:
            cand = parent / "config" / "sources_ingestion.yaml"
            if cand.exists():
                p = cand
                break
    data = yaml.safe_load(p.read_text()) or {}
    return list(data.get("commandes", []))


def _defaut(label: str, motif: str) -> Filtre:
    """Filtre par défaut d'une source à job sans définition riche : universels seuls, cadrés
    sur ce que l'on connaît sans risque (le millésime via le motif data_sources)."""
    libelle = motif.replace("%", "").strip() or label
    # le motif YAML utilise `%` comme joker fnmatch ; ILIKE l'accepte tel quel.
    return Filtre(source=label, libelle=libelle, source_motif=motif, a_job=True)


@functools.lru_cache(maxsize=1)
def _registre() -> dict[str, Filtre]:
    reg: dict[str, Filtre] = {}
    # 1) toute source à job a AU MOINS un filtre par défaut (invariant 1.5).
    for cmd in sources_a_job():
        reg[cmd["label"]] = _defaut(cmd["label"], cmd.get("motif", cmd["label"]))
    # 2) les filtres RICHES (lot 2) remplacent le défaut et ajoutent des sources hors-vanne.
    for key, filtre in FILTRES_RICHES.items():
        reg[key] = filtre
    # 3) le contrôle ÉCHANTILLON (lot 3) : un par filtre qui a un fichier producteur (sinon skip).
    ech = echantillon.controle()
    for filtre in reg.values():
        if echantillon.chemin(filtre.source).exists() and \
                not any(cc.id == "d_echantillon" for cc in filtre.propres):
            filtre.propres.append(ech)
    # 4) portée `live` (lot 4) — dérivée du REGISTRE : un filtre dont le réservoir alimente au moins
    #    une donnée à portée `live` passe par la table d'attente (quarantaine avant service).
    for cle in _cles_live():
        if cle in reg:
            reg[cle].live = True
    return reg


# Alias réservoir (registre) → clé de filtre, quand ils diffèrent (partagé avec quarantaine.py).
_ALIAS_RESERVOIR_FILTRE = {
    "cadastre_api_carto": "cadastre_etalab",
    "gpu_plu_api_carto": "gpu_plu",
    "filosofi_carreaux": "filosofi",
    "deal_ppr": "georisques_mvt",
}


def _cles_live() -> set[str]:
    """Clés de filtre dont le réservoir alimente une donnée à portée `live` (registre = vérité)."""
    try:
        from ..registre.donnees import DONNEES
    except Exception:  # pragma: no cover - registre indisponible
        return set()
    res = {r for d in DONNEES.values() if getattr(d, "portee", "") == "live"
           for r in (d.reservoirs or ())}
    return {_ALIAS_RESERVOIR_FILTRE.get(r, r) for r in res}


def FILTRES() -> dict[str, Filtre]:
    return dict(_registre())


def get_filtre(source: str) -> Filtre | None:
    return _registre().get(source)


def sources() -> list[str]:
    return sorted(_registre().keys())


def sources_run() -> list[str]:
    """Sources dont le filtre alimente au moins une donnée à portée `run` (garde pompe 1.4)."""
    return sorted(k for k, f in _registre().items() if f.portee_run)


def sources_live() -> list[str]:
    """Sources dont le filtre alimente au moins une donnée à portée `live` (quarantaine 4.1)."""
    return sorted(k for k, f in _registre().items() if f.live)


def garde_pompe(db) -> list[dict]:
    """Garde de la pompe (1.4) — les sources à portée `run` dont la version SERVIE est en
    quarantaine (bloquant KO, sans « servir quand même »). Vide = la pompe peut calculer/basculer.

    Chaque entrée nomme la source et ses contrôles bloquants KO (message du refus)."""
    from sqlalchemy import text
    blocages: list[dict] = []
    for key in sources_run():
        f = _registre()[key]
        version = version_servie(db, f)
        if not en_quarantaine(db, key, version):
            continue
        kos = db.execute(text(
            "SELECT controle FROM filtre_resultats WHERE source=:s AND version=:v "
            "AND severite='bloquant' AND verdict='ko' ORDER BY controle"),
            {"s": key, "v": version}).scalars().all()
        blocages.append({"source": key, "libelle": f.libelle, "version": version,
                         "controles": list(kos)})
    return blocages
