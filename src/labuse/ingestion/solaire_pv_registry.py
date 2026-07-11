"""Lot 4 Habitat Solaire — parc PV existant + repowering.

Source : Registre national des installations de production et de stockage
d'électricité, extrait « La Réunion » republié par EDF SEI (Data Fair) — même
donnée que le jeu ODRÉ national, déjà filtrée 974 (686 lignes solaires,
millésime 30/06/2026). Schéma du millésime courant :
- installations ≥ 36 kVA : 1 ligne par installation (nbinstallations = 1)…
  mais `nominstallation` = « Confidentiel » et AUCUNE adresse/géométrie →
  le rattachement parcellaire est IMPOSSIBLE sur ce millésime (le code pose
  quand même le flag parcelle si une géolocalisation apparaît un jour) ;
- < 36 kVA : agrégées par commune (nbinstallations = n, date = plus ancienne).

Dérivations :
- `parcel_solar.pv_existant = 'commune_forte_densite'` : communes du top quartile
  en densité de petites installations (pour 1 000 résidences principales INSEE) —
  proxy d'équipement HONNÊTE sur sa granularité communale ;
- `repowering` : mises en service 2006-2013 (boom défisc + contrats d'achat 20 ans
  → échéances 2026-2033), individualisées uniquement. Sans géolocalisation au
  registre, aucun flag parcellaire n'est posé sur ce millésime : le vivier reste
  consultable par commune (voir rapport de fin).
"""
from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings, habitat_solaire
from .habitat_solaire_schema import ensure_schema

DATASET_URL = ("https://opendata-reunion.edf.fr/data-fair/api/v1/datasets/"
               "2ne0caym1gcwtbpsdtb3u511/lines")


def _cfg() -> dict[str, Any]:
    return habitat_solaire()["pv_registry"]


def ingest(session: Session) -> dict[str, Any]:
    ensure_schema(session)
    rows: list[dict] = []
    with httpx.Client(timeout=get_settings().http_timeout_s,
                      headers={"User-Agent": "labuse/habitat-solaire"}) as client:
        data = client.get(DATASET_URL, params={
            "qs": "filiere:(Solaire*)", "size": 1000}).raise_for_status().json()
        rows.extend(data.get("results", []))
        while data.get("next") and len(rows) < 20000:
            data = client.get(data["next"]).raise_for_status().json()
            rows.extend(data.get("results", []))
    session.execute(text("DELETE FROM pv_registry"))
    import json as _json
    for r in rows:
        r.pop("_score", None)
        session.execute(text("""
            INSERT INTO pv_registry (commune, insee, filiere, puissance_kw,
                                     date_mise_service, individualise, raw)
            VALUES (:commune, :insee, :filiere, :puiss, CAST(:dms AS date),
                    :indiv, CAST(:raw AS jsonb))
        """), {"commune": r.get("commune"), "insee": r.get("codeinseecommune"),
               "filiere": r.get("filiere"), "puiss": r.get("puismaxinstallee"),
               "dms": r.get("datemiseenservice"),
               "indiv": int(r.get("nbinstallations") or 0) == 1,
               "raw": _json.dumps(r, ensure_ascii=False)})
    n_indiv = session.execute(text(
        "SELECT count(*) FROM pv_registry WHERE individualise")).scalar_one()
    return {"lignes": len(rows), "individualisees": n_indiv}


def commune_forte_densite(session: Session) -> dict[str, Any]:
    """Top quartile de densité de petites installations / 1 000 rés. principales."""
    q = float(_cfg()["densite_quartile"])
    communes = [c for (c,) in session.execute(text("""
        WITH dens AS (
          SELECT pv.insee,
                 sum((pv.raw ->> 'nbinstallations')::int)
                   FILTER (WHERE NOT pv.individualise) * 1000.0
                   / NULLIF(max(cil.res_principales), 0) AS d
          FROM pv_registry pv
          JOIN commune_insee_logement cil ON cil.insee = pv.insee
          GROUP BY pv.insee
        ),
        seuil AS (SELECT percentile_cont(:q) WITHIN GROUP (ORDER BY d) AS s FROM dens)
        SELECT insee FROM dens, seuil WHERE d >= s AND d IS NOT NULL
    """), {"q": q}).all()]
    n = 0
    if communes:
        n = session.execute(text("""
            INSERT INTO parcel_solar (idu, pv_existant, updated_at)
            SELECT p.idu, 'commune_forte_densite', now()
            FROM parcels p WHERE left(p.idu, 5) = ANY(:communes)
            ON CONFLICT (idu) DO UPDATE
              SET pv_existant = coalesce(parcel_solar.pv_existant, EXCLUDED.pv_existant),
                  updated_at = now()
        """), {"communes": communes}).rowcount
    return {"communes_top_quartile": communes, "parcelles": n}


def repowering(session: Session) -> dict[str, Any]:
    """Fenêtre 2006-2013 (contrats 20 ans → 2026-2033). Le flag PARCELLE ne peut être
    posé que si le registre porte une géométrie (absente au millésime courant)."""
    cfg = _cfg()
    n_reg = session.execute(text(
        "SELECT count(*) FROM pv_registry WHERE individualise"
        " AND date_mise_service BETWEEN CAST(:d1 AS date) AND CAST(:d2 AS date)"),
        {"d1": str(cfg["repowering_debut"]), "d2": str(cfg["repowering_fin"])}).scalar_one()
    n_parc = session.execute(text("""
        INSERT INTO parcel_solar (idu, repowering, updated_at)
        SELECT DISTINCT p.idu, true, now()
        FROM pv_registry pv
        JOIN parcels p ON pv.geom IS NOT NULL
          AND ST_DWithin(p.geom_2975, ST_Transform(pv.geom, 2975), 30)
        WHERE pv.individualise
          AND pv.date_mise_service BETWEEN CAST(:d1 AS date) AND CAST(:d2 AS date)
        ON CONFLICT (idu) DO UPDATE SET repowering = true, updated_at = now()
    """), {"d1": str(cfg["repowering_debut"]), "d2": str(cfg["repowering_fin"])}).rowcount
    return {"installations_fenetre": n_reg, "parcelles_flaggees": n_parc}


def run(session: Session, log=print) -> dict[str, Any]:
    res = ingest(session)
    log(f"  registre 974 solaire : {res}")
    dens = commune_forte_densite(session)
    log(f"  communes forte densité : {dens['communes_top_quartile']}"
        f" → {dens['parcelles']} parcelles")
    rep = repowering(session)
    log(f"  repowering 2006-2013 : {rep['installations_fenetre']} installations"
        f" (parcelles flaggées : {rep['parcelles_flaggees']} — géoloc absente du registre)")
    return {**res, **dens, **rep}
