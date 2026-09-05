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

from .cadre import (Controle, Filtre, Resultat, Verdict, _ensure_sur_session,  # noqa: F401
                    dernier_verdict, en_quarantaine, ensure_tables, jouer, ko, ok, skip,
                    version_servie)
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


def etats_servis(db) -> dict[str, dict]:
    """CIRCUIT-3 lot 5.2 — le dernier verdict + les contrôles de CHAQUE source, en 2 requêtes
    (pour la page Circuit ; évite N requêtes par réservoir)."""
    from sqlalchemy import text
    _ensure_sur_session(db)
    versions = {}
    for row in db.execute(text(
        "SELECT DISTINCT ON (source) source, version, verdict, bloquants_ko, avertissants_ko, "
        "servir_quand_meme, joue_le FROM filtre_versions ORDER BY source, joue_le DESC")).all():
        versions[row[0]] = {"version": row[1], "verdict": row[2], "bloquants_ko": row[3],
                            "avertissants_ko": row[4], "servir_quand_meme": row[5],
                            "joue_le": row[6].isoformat() if row[6] else None, "controles": []}
    if versions:
        for r in db.execute(text(
            "SELECT source, version, controle, nature, severite, valeur, seuil, verdict, joue_le "
            "FROM filtre_resultats ORDER BY source, "
            "CASE severite WHEN 'bloquant' THEN 0 ELSE 1 END, controle")).all():
            e = versions.get(r[0])
            if e and r[1] == e["version"]:
                e["controles"].append({"controle": r[2], "nature": r[3], "severite": r[4],
                                       "valeur": r[5], "seuil": r[6], "verdict": r[7],
                                       "joue_le": r[8].isoformat() if r[8] else None})
    return versions


def etat_pour_data_source(db, nom: str) -> dict | None:
    """CIRCUIT-3 lot 5.2 — l'état du filtre d'un réservoir (ligne data_sources) : trouve le filtre
    dont le motif matche le nom, rend son dernier verdict + les contrôles (valeur/seuil/date). Sert
    la page Circuit : « filtre OK / n KO / non filtré » + la fiche du bas."""
    from sqlalchemy import text
    nom_l = (nom or "").lower()
    cible = None
    # motif le plus LONG d'abord (le plus spécifique gagne).
    ordonnes = sorted(_registre().items(),
                      key=lambda kv: len((kv[1].source_motif or "")), reverse=True)
    for cle, f in ordonnes:
        mot = (f.source_motif or "").lower().replace("%", "")
        if mot and mot in nom_l:
            cible = (cle, f)
            break
    if not cible:
        return {"source": None, "verdict": "non_filtre"}
    cle, f = cible
    dv = dernier_verdict(db, cle)
    if not dv:
        return {"source": cle, "verdict": "jamais_joue", "portee_run": f.portee_run, "live": f.live}
    controles = [dict(controle=r[0], nature=r[1], severite=r[2], valeur=r[3], seuil=r[4],
                      verdict=r[5], joue_le=r[6].isoformat() if r[6] else None)
                 for r in db.execute(text(
        "SELECT controle, nature, severite, valeur, seuil, verdict, joue_le "
        "FROM filtre_resultats WHERE source=:s AND version=:v ORDER BY "
        "CASE severite WHEN 'bloquant' THEN 0 ELSE 1 END, controle"),
        {"s": cle, "v": dv["version"]}).all()]
    return {"source": cle, "verdict": dv["verdict"], "version": dv["version"],
            "bloquants_ko": dv["bloquants_ko"], "avertissants_ko": dv["avertissants_ko"],
            "servir_quand_meme": dv["servir_quand_meme"], "joue_le": dv["joue_le"],
            "portee_run": f.portee_run, "live": f.live, "controles": controles}


def servir_quand_meme(db, source: str, par: str, motif: str | None = None) -> dict:
    """CIRCUIT-3 lot 5.2 — le geste de Vic : servir une version malgré sa quarantaine. Marque la
    DERNIÈRE version du filtre (avec qui + pourquoi) ; lève la garde de la pompe et le blocage."""
    from sqlalchemy import text
    from .. import circuit_journal
    _ensure_sur_session(db)
    dv = dernier_verdict(db, source)
    if not dv:
        return {"ok": False, "motif": "aucune version filtrée pour cette source"}
    db.execute(text(
        "UPDATE filtre_versions SET servir_quand_meme = true, servi_par = :p, servi_motif = :m "
        "WHERE source = :s AND version = :v"),
        {"p": par[:120], "m": motif, "s": source, "v": dv["version"]})
    circuit_journal.journaliser(db, "filtre", source, par, "ok",
                                {"servir_quand_meme": True, "version": dv["version"], "motif": motif})
    return {"ok": True, "source": source, "version": dv["version"]}


def quarantaines_anciennes(db, jours: int = 7) -> list[dict]:
    """CIRCUIT-3 lot 5.3 — les versions en QUARANTAINE depuis plus de `jours` jours (sans « servir
    quand même »). Une source qui traîne en quarantaine est un avertissement (healthz)."""
    from sqlalchemy import text
    _ensure_sur_session(db)
    rows = db.execute(text(
        "SELECT DISTINCT ON (source) source, version, joue_le "
        "FROM filtre_versions WHERE verdict='quarantaine' AND servir_quand_meme = false "
        "ORDER BY source, joue_le DESC")).all()
    vieux = []
    from datetime import datetime, timezone, timedelta
    seuil = datetime.now(timezone.utc) - timedelta(days=jours)
    for source, version, joue_le in rows:
        # ne garder que si le DERNIER verdict de la source est bien quarantaine (pas soldé depuis)
        dv = dernier_verdict(db, source)
        if not dv or dv["verdict"] != "quarantaine" or dv["servir_quand_meme"]:
            continue
        if joue_le and joue_le < seuil:
            vieux.append({"source": source, "version": version,
                          "depuis": joue_le.isoformat(), "jours_seuil": jours})
    return vieux


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
