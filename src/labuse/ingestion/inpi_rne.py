"""Ingestion INPI RNE (Vague A3) — dirigeants des personnes morales foncières.

Croise les SIREN de `parcelle_personne_morale` avec l'API RNE → table `pm_dirigeants`, d'où la
vue `v_pm_propension_vendre` calcule le signal « âge dirigeant » (aîné des dirigeants physiques).

La donnée d'abord, le scoring ensuite : ce module PEUPLE `pm_dirigeants` et EXPOSE le signal.
Il ne touche PAS au calcul de score — l'étage 2 « accessibilité » le branchera quand les sources
de la Vague A seront là (# TODO étage 2).

RGPD (règle d'archi #2) : n'ingère les données d'une personne PHYSIQUE que si l'entreprise est
diffusible (géré au parsing) ; signal INTERNE de priorisation, jamais un export nominatif de masse.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.inpi_rne import SOURCE_NAME, InpiRneConnector

# Groupes de la classification PM manifestement NON marchands (collectivités / établissements
# publics) → exclus d'emblée. « Dans le doute, garder » : les formes mal classées en groupe 0
# (SIVU/CCAS parfois) et les groupes 5-8 (HLM, SEM, copro, associés) sont CONSERVÉS.
GROUPES_PUBLICS_EXCLUS = (1, 2, 3, 4, 9)  # État, Région, Département, Commune, Établissements publics


def eligible_sirens(session: Session, insee: str | None = None) -> list[str]:
    """SIREN (9 chiffres, dé-doublonnés) des personnes morales foncières MARCHANDES.

    Écarte les SIREN mal formés et les groupes publics évidents (cf. GROUPES_PUBLICS_EXCLUS).
    `insee` : restreint à une commune via le préfixe d'idu.
    """
    # GROUPES_PUBLICS_EXCLUS est une constante d'entiers du module (aucune entrée externe) →
    # interpolation directe sûre, plus simple qu'un bindparam expanding.
    grp = ",".join(str(int(g)) for g in GROUPES_PUBLICS_EXCLUS)
    sql = ("SELECT DISTINCT siren FROM parcelle_personne_morale "
           "WHERE siren ~ '^[0-9]{9}$' "
           f"AND (groupe IS NULL OR groupe NOT IN ({grp}))")
    params: dict = {}
    if insee:
        sql += " AND idu LIKE :pref"
        params["pref"] = f"{insee}%"
    sql += " ORDER BY siren"
    return [r[0] for r in session.execute(text(sql), params).all()]


_UPSERT = text(
    "INSERT INTO pm_dirigeants "
    " (siren, representant_id, type_personne, nom, prenoms, date_naissance, role_entreprise, "
    "  date_prise_fonction, gerant_siren, actif, diffusible, raw) "
    "VALUES (:siren,:rid,:tp,:nom,:pre,:dn,:role,:dpf,:gs,:actif,:diff, CAST(:raw AS jsonb)) "
    "ON CONFLICT (siren, representant_id) DO UPDATE SET "
    "  type_personne=EXCLUDED.type_personne, nom=EXCLUDED.nom, prenoms=EXCLUDED.prenoms, "
    "  date_naissance=EXCLUDED.date_naissance, role_entreprise=EXCLUDED.role_entreprise, "
    "  date_prise_fonction=EXCLUDED.date_prise_fonction, gerant_siren=EXCLUDED.gerant_siren, "
    "  actif=EXCLUDED.actif, diffusible=EXCLUDED.diffusible, raw=EXCLUDED.raw, "
    "  ingested_at=now()")


def _store_dirigeants(session: Session, company: dict) -> int:
    """UPSERT les dirigeants d'une société. Idempotent (conflit sur (siren, representant_id))."""
    siren = company["siren"]
    n = 0
    for d in company["dirigeants"]:
        if not d.get("representant_id"):
            continue  # sans identifiant stable, on ne peut pas dédupliquer proprement → sauté
        session.execute(_UPSERT, {
            "siren": siren, "rid": d["representant_id"], "tp": d["type_personne"],
            "nom": d["nom"], "pre": d["prenoms"], "dn": d["date_naissance"],
            "role": d["role_entreprise"], "dpf": d["date_prise_fonction"],
            "gs": d["gerant_siren"], "actif": d["actif"], "diff": d["diffusible"],
            "raw": json.dumps(d["raw"], ensure_ascii=False)})
        n += 1
    return n


def ingest_inpi_rne(session: Session, sirens: list[str],
                    connector: InpiRneConnector | None = None,
                    throttle_s: float | None = None) -> dict:
    """Récupère et UPSERT les dirigeants des SIREN dans `pm_dirigeants`. Retourne des compteurs.

    Idempotent. Met à jour `data_sources.last_sync_at`. ⚠ ÉCRIT en base et FAIT DES APPELS RÉSEAU —
    ne pas lancer sur l'île entière sans le feu vert de Vic (cf. brief : échantillon d'abord).
    """
    connector = connector or InpiRneConnector()
    n_diri = 0
    sirens_hit: set[str] = set()
    for company in connector.fetch_companies(sirens, throttle_s=throttle_s):
        added = _store_dirigeants(session, company)
        if added:
            n_diri += added
            sirens_hit.add(company["siren"])
    _touch_source(session)
    session.flush()
    return {"sirens_queried": len({s for s in sirens}), "dirigeants": n_diri,
            "sirens_with_dirigeant": len(sirens_hit)}


def sample_report(session: Session, insee: str, today: date | None = None,
                  n_examples: int = 5) -> dict:
    """Rapport de validation (échantillon commune) à partir de `pm_dirigeants` DÉJÀ ingérée.

    Ne fait AUCUN appel réseau : lit la base. Fournit compteurs, distribution des bandes d'âge,
    TAUX GIGOGNE (SIREN sans aucun dirigeant individu daté) et `n_examples` exemples vérifiables.
    """
    today = today or date.today()

    # SIREN de la commune présents dans pm_dirigeants (croisement via la vue parcelle).
    rows = session.execute(text(
        "SELECT DISTINCT siren, propension_band, age_source, age_max_dirigeant, "
        "       nb_dirigeants, nb_individus "
        "FROM v_foncier_propension_vendre "
        "WHERE idu LIKE :pref"), {"pref": f"{insee}%"}).mappings().all()

    bandes = Counter(r["propension_band"] for r in rows)
    sources = Counter(r["age_source"] for r in rows)
    ages = [r["age_max_dirigeant"] for r in rows if r["age_max_dirigeant"] is not None]
    n_siren = len(rows)
    n_gigogne = sources.get("aucun_individu", 0)

    # Parcelles à gérant âgé (bande élevé/très élevé) sur la commune.
    n_parc_age = session.execute(text(
        "SELECT count(*) FROM v_foncier_propension_vendre "
        "WHERE idu LIKE :pref AND propension_band IN ('eleve','tres_eleve')"),
        {"pref": f"{insee}%"}).scalar()

    # Exemples vérifiables : parcelle + SIREN + âge de l'aîné + dénomination.
    ex = session.execute(text(
        "SELECT idu, siren, denomination, age_max_dirigeant, propension_band, age_source "
        "FROM v_foncier_propension_vendre "
        "WHERE idu LIKE :pref AND age_max_dirigeant IS NOT NULL "
        "ORDER BY age_max_dirigeant DESC LIMIT :n"),
        {"pref": f"{insee}%", "n": n_examples}).mappings().all()

    return {
        "insee": insee,
        "sirens_avec_dirigeant": n_siren,
        "distribution_bandes": dict(bandes),
        "distribution_age_source": dict(sources),
        "taux_gigogne": round(n_gigogne / n_siren, 3) if n_siren else None,
        "n_gigogne": n_gigogne,
        "age_min": min(ages) if ages else None,
        "age_max": max(ages) if ages else None,
        "age_median": sorted(ages)[len(ages) // 2] if ages else None,
        "parcelles_gerant_age": n_parc_age,
        "exemples": [dict(e) for e in ex],
    }


def _touch_source(session: Session) -> None:
    """Marque la fraîcheur de la source (last_sync_at) si la ligne de catalogue existe."""
    session.execute(text(
        "UPDATE data_sources SET last_sync_at = now() WHERE name = :n"), {"n": SOURCE_NAME})
