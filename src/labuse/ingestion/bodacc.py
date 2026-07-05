"""Ingestion BODACC (Vague A1) — procédures collectives des personnes morales foncières.

Croise les SIREN de `parcelle_personne_morale` (propriétaires personnes morales déjà en base)
avec les annonces de procédure collective BODACC → flag « foncier sous pression ».

La donnée d'abord, le scoring ensuite : ce module PEUPLE `bodacc_procedures` et EXPOSE le flag
(vue v_foncier_sous_pression). Il ne touche PAS au calcul de score — l'étage 2 « accessibilité »
le branchera quand les 3 sources de la Vague A seront là (# TODO étage 2).
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.bodacc import BodaccConnector

SOURCE_NAME = "BODACC (procédures collectives)"


def distinct_sirens(session: Session, insee: str | None = None) -> list[str]:
    """SIREN (9 chiffres, dé-doublonnés) des personnes morales foncières.

    `insee` : restreint à une commune via le préfixe d'idu (les parcelles sont préfixées par
    l'INSEE). Les SIREN mal formés (vides, codes non-SIREN) sont écartés — jamais de faux flag.
    """
    sql = "SELECT DISTINCT siren FROM parcelle_personne_morale WHERE siren ~ '^[0-9]{9}$'"
    params: dict = {}
    if insee:
        sql += " AND idu LIKE :pref"
        params["pref"] = f"{insee}%"
    sql += " ORDER BY siren"
    return [r[0] for r in session.execute(text(sql), params).all()]


def ingest_bodacc(session: Session, sirens: list[str], connector: BodaccConnector | None = None,
                  batch_size: int = 40) -> dict:
    """Récupère et UPSERT les procédures collectives des SIREN dans `bodacc_procedures`.

    Idempotent (conflit sur `annonce_id`). Met à jour `data_sources.last_sync_at` (fraîcheur,
    cohérent Vague D). ⚠ ÉCRIT en base — ne pas lancer sur l'île entière sans le feu vert de Vic
    (cf. brief). Retourne des compteurs.
    """
    connector = connector or BodaccConnector()
    n_proc = 0
    sirens_hit: set[str] = set()
    for p in connector.fetch_collective_by_sirens(sirens, batch_size=batch_size):
        session.execute(text(
            "INSERT INTO bodacc_procedures "
            " (annonce_id, siren, type_procedure, famille_jugement, date_annonce, "
            "  date_jugement_txt, tribunal, numero_annonce, publication, url_source, raw) "
            "VALUES (:aid,:s,:tp,:fj,:da,:djt,:tr,:na,:pub,:url, CAST(:raw AS jsonb)) "
            "ON CONFLICT (annonce_id) DO UPDATE SET "
            "  type_procedure=EXCLUDED.type_procedure, famille_jugement=EXCLUDED.famille_jugement, "
            "  date_annonce=EXCLUDED.date_annonce, tribunal=EXCLUDED.tribunal, "
            "  url_source=EXCLUDED.url_source, raw=EXCLUDED.raw"),
            {"aid": p["annonce_id"], "s": p["siren"], "tp": p["type_procedure"],
             "fj": p["famille_jugement"], "da": p["date_annonce"], "djt": p["date_jugement_txt"],
             "tr": p["tribunal"], "na": p["numero_annonce"], "pub": p["publication"],
             "url": p["url_source"], "raw": json.dumps(p["raw"], ensure_ascii=False)})
        n_proc += 1
        sirens_hit.add(p["siren"])
    _touch_source(session)
    session.flush()
    return {"sirens_queried": len(set(sirens)), "procedures": n_proc,
            "sirens_with_procedure": len(sirens_hit)}


def _touch_source(session: Session) -> None:
    """Marque la fraîcheur de la source (last_sync_at). La ligne de catalogue est posée par
    seed_sources ; ici on n'actualise que l'horodatage si elle existe."""
    session.execute(text(
        "UPDATE data_sources SET last_sync_at = now() WHERE name = :n"), {"n": SOURCE_NAME})


def parcelles_sous_pression(session: Session, insee: str | None = None) -> list[dict]:
    """Flag « foncier sous pression » : parcelles dont le propriétaire (personne morale) est sous
    procédure collective. Lit la vue `v_foncier_sous_pression` (croisement SIREN BODACC ↔ PM).

    Structure par parcelle : {idu, siren, denomination, type_procedure, date_annonce, tribunal,
    url_source, source: "BODACC"}. # TODO étage 2 : consommé par le scoring « accessibilité ».
    """
    sql = ("SELECT idu, siren, denomination, type_procedure, date_annonce, tribunal, "
           "url_source, source FROM v_foncier_sous_pression")
    params: dict = {}
    if insee:
        sql += " WHERE idu LIKE :pref"
        params["pref"] = f"{insee}%"
    return [dict(r._mapping) for r in session.execute(text(sql), params).all()]


def sample_report(session: Session, insee: str, connector: BodaccConnector | None = None,
                  n_examples: int = 5) -> dict:
    """Rapport d'ÉCHANTILLON (Livrable 4) — LECTURE SEULE : n'écrit RIEN en base.

    Interroge BODACC pour les SIREN d'une commune et croise EN MÉMOIRE avec les parcelles
    personnes morales (lecture seule). Sert de garde-fou avant la passe île entière : Vic vérifie
    les compteurs et quelques exemples à la main avant tout feu vert.
    """
    connector = connector or BodaccConnector()
    sirens = distinct_sirens(session, insee)
    # SIREN → procédure la plus récente (en mémoire, aucune écriture)
    proc_by_siren: dict[str, dict] = {}
    for p in connector.fetch_collective_by_sirens(sirens):
        cur = proc_by_siren.get(p["siren"])
        if cur is None or (p["date_annonce"] and (cur["date_annonce"] is None
                                                  or p["date_annonce"] > cur["date_annonce"])):
            proc_by_siren[p["siren"]] = p

    # Parcelles de la commune dont le SIREN est sous procédure (lecture seule)
    rows = session.execute(text(
        "SELECT idu, siren, denomination FROM parcelle_personne_morale "
        "WHERE idu LIKE :pref AND siren = ANY(:sirens) ORDER BY idu"),
        {"pref": f"{insee}%", "sirens": list(proc_by_siren)}).all()

    examples = []
    for idu, siren, denom in rows[:n_examples]:
        p = proc_by_siren[siren]
        examples.append({"idu": idu, "siren": siren, "denomination": denom,
                         "type_procedure": p["type_procedure"], "date_annonce": p["date_annonce"],
                         "url_source": p["url_source"]})
    return {
        "insee": insee,
        "sirens_queried": len(sirens),
        "sirens_with_procedure": len(proc_by_siren),
        "parcelles_flaggees": len(rows),
        "examples": examples,
    }
