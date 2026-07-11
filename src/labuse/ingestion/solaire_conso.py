"""Lot 2 Habitat Solaire — facture d'électricité ESTIMÉE : l'argument de vente n° 1.

Baseline : open data EDF SEI Réunion (plateforme Data Fair), jeu « Consommation
annuelle par commune - La Réunion », secteur Résidentiel — conso MWh / nombre de
points de soutirage = kWh/an du logement moyen de la commune, dernier millésime.
La maille IRIS n'existe PAS pour la Réunion (le jeu IRIS national est Enedis,
métropole seulement) → maille commune, documenté dans seed_sources.

Modèle ADDITIF simple et documenté (coefficients en config/habitat_solaire.yaml) :
  conso = baseline_commune × ratio_surface  (+ ECS élec, + clim, + piscine)
  - ratio_surface = surface estimée / surface_ref, borné [0.5, 2.5] ;
    surface estimée = surface DPE si connue, sinon emprise bâtie × 0.9 bornée.
  - Les bonus ECS/clim s'appuient sur des champs DPE ABSENTS de la vague pilote
    (910 DPE sans type ECS ni refroidissement) : ils s'activeront d'eux-mêmes
    quand l'ingestion DPE complète les portera. Piscine : mandat Détection Ortho.
  facture_est_eur_mois = conso × LABUSE_TARIF_ELEC_EUR_KWH / 12, arrondie à la DIZAINE.

AFFICHAGE : toujours « estimation statistique » — jamais une donnée réelle.
"""
from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings, habitat_solaire
from .habitat_solaire_schema import ensure_schema

DATASET_URL = ("https://opendata-reunion.edf.fr/data-fair/api/v1/datasets/"
               "y-lrvrtj10y9rmewc5vigrh-/lines")

DDL_BASELINE = """
CREATE TABLE IF NOT EXISTS conso_baseline_commune (
  insee            varchar(5) PRIMARY KEY,
  commune          varchar(80),
  annee            integer,
  conso_res_mwh    double precision,
  pds_res          integer,
  kwh_an_logement  double precision,
  source           text,
  fetched_at       timestamptz DEFAULT now()
);
"""


def _cfg() -> dict[str, Any]:
    return habitat_solaire()["conso"]


def ingest_baseline(session: Session) -> dict[str, Any]:
    """Télécharge la baseline résidentielle par commune (dernier millésime par commune)."""
    ensure_schema(session)
    session.execute(text(DDL_BASELINE))
    rows: list[dict] = []
    with httpx.Client(timeout=get_settings().http_timeout_s,
                      headers={"User-Agent": "labuse/habitat-solaire"}) as client:
        params = {"qs": 'secteur:("Résidentiel")', "size": 1000}
        r = client.get(DATASET_URL, params=params)
        r.raise_for_status()
        data = r.json()
        rows.extend(data.get("results", []))
        # pagination Data Fair (next) — 24 communes × ~10 ans : une page suffit largement
        while data.get("next") and len(rows) < 5000:
            data = client.get(data["next"]).json()
            rows.extend(data.get("results", []))
    derniers: dict[str, dict] = {}
    for r_ in rows:
        insee = str(r_.get("code_insee") or "")
        if not insee.startswith("974") or not r_.get("nombre_de_pds"):
            continue
        if insee not in derniers or int(r_["annee"]) > int(derniers[insee]["annee"]):
            derniers[insee] = r_
    for insee, r_ in derniers.items():
        kwh = 1000.0 * float(r_["consommation_mwh"]) / int(r_["nombre_de_pds"])
        session.execute(text("""
            INSERT INTO conso_baseline_commune
              (insee, commune, annee, conso_res_mwh, pds_res, kwh_an_logement, source)
            VALUES (:insee, :commune, :annee, :mwh, :pds, :kwh,
                    'EDF SEI — Consommation annuelle par commune - La Réunion')
            ON CONFLICT (insee) DO UPDATE SET
              commune = EXCLUDED.commune, annee = EXCLUDED.annee,
              conso_res_mwh = EXCLUDED.conso_res_mwh, pds_res = EXCLUDED.pds_res,
              kwh_an_logement = EXCLUDED.kwh_an_logement, fetched_at = now()
        """), {"insee": insee, "commune": r_.get("commune"), "annee": int(r_["annee"]),
               "mwh": float(r_["consommation_mwh"]), "pds": int(r_["nombre_de_pds"]),
               "kwh": round(kwh, 1)})
    annees = sorted({int(r_["annee"]) for r_ in derniers.values()}) if derniers else []
    return {"communes": len(derniers), "millesimes": annees}


def compute_conso(session: Session) -> dict[str, Any]:
    """conso_est_kwh_an + facture_est_eur_mois pour les parcelles bâties RÉSIDENTIELLES."""
    cfg = _cfg()
    tarif = get_settings().tarif_elec_eur_kwh
    n = session.execute(text("""
        WITH cible AS (
          SELECT p.idu, left(p.idu, 5) AS insee, rb.emprise_batie_m2,
                 (SELECT d.surface_habitable FROM dpe_records d
                  WHERE d.parcelle_idu = p.idu AND d.surface_habitable > 0
                  ORDER BY d.date_etablissement DESC NULLS LAST LIMIT 1) AS dpe_surface,
                 -- champs DPE absents de la vague pilote : bonus à 0 tant que la
                 -- réingestion complète ne les porte pas (résilient par construction)
                 EXISTS (SELECT 1 FROM dpe_records d WHERE d.parcelle_idu = p.idu
                         AND d.raw ->> 'type_energie_generateur_ecs' ILIKE '%lectri%')
                   AS ecs_elec,
                 EXISTS (SELECT 1 FROM dpe_records d WHERE d.parcelle_idu = p.idu
                         AND coalesce(d.raw ->> 'presence_climatisation',
                                      d.raw ->> 'type_generateur_froid') IS NOT NULL)
                   AS clim
          FROM parcels p
          JOIN parcel_residuel_bati rb ON rb.idu = p.idu AND rb.emprise_batie_m2 > 20
          WHERE EXISTS (SELECT 1 FROM spatial_layers sl
                        WHERE sl.kind = 'batiment' AND sl.attrs ->> 'usage' = 'Résidentiel'
                          AND ST_Intersects(sl.geom_2975, p.geom_2975))
        ),
        modele AS (
          SELECT c.idu,
                 b.kwh_an_logement
                 * LEAST(:rmax, GREATEST(:rmin,
                     LEAST(:smax, GREATEST(:smin,
                       coalesce(c.dpe_surface, c.emprise_batie_m2 * :hcoef))) / :sref))
                 + CASE WHEN c.ecs_elec THEN :ecs ELSE 0 END AS brut,
                 c.clim
          FROM cible c
          JOIN conso_baseline_commune b ON b.insee = c.insee
        )
        INSERT INTO parcel_solar (idu, conso_est_kwh_an, facture_est_eur_mois, updated_at)
        SELECT idu,
               round(brut * CASE WHEN clim THEN 1 + :clim_pct / 100.0 ELSE 1 END)::int,
               (round(brut * CASE WHEN clim THEN 1 + :clim_pct / 100.0 ELSE 1 END
                      * :tarif / 12.0 / 10.0) * 10)::int,
               now()
        FROM modele
        ON CONFLICT (idu) DO UPDATE SET
          conso_est_kwh_an = EXCLUDED.conso_est_kwh_an,
          facture_est_eur_mois = EXCLUDED.facture_est_eur_mois, updated_at = now()
    """), {"rmin": float(cfg["ratio_surface_min"]), "rmax": float(cfg["ratio_surface_max"]),
           "smin": float(cfg["surface_est_min_m2"]), "smax": float(cfg["surface_est_max_m2"]),
           "hcoef": float(cfg["surface_habitable_coef"]), "sref": float(cfg["surface_ref_m2"]),
           "ecs": float(cfg["ecs_electrique_kwh_an"]), "clim_pct": float(cfg["clim_littoral_pct"]),
           "tarif": tarif}).rowcount
    dist = session.execute(text("""
        SELECT min(facture_est_eur_mois),
               percentile_cont(0.5) WITHIN GROUP (ORDER BY facture_est_eur_mois),
               max(facture_est_eur_mois)
        FROM parcel_solar WHERE facture_est_eur_mois IS NOT NULL
    """)).one()
    return {"parcelles": n,
            "facture_min": dist[0], "facture_mediane": float(dist[1] or 0), "facture_max": dist[2]}


def run(session: Session, log=print) -> dict[str, Any]:
    base = ingest_baseline(session)
    log(f"  baseline EDF SEI : {base['communes']} communes, millésimes {base['millesimes']}")
    res = compute_conso(session)
    log(f"  conso estimée : {res['parcelles']} parcelles — facture min/méd/max "
        f"{res['facture_min']}/{res['facture_mediane']:.0f}/{res['facture_max']} €/mois")
    # garde-fou du mandat : médiane grossièrement 80-180 € ; hors [30, 400] = modèle à revoir
    if not 30 <= res["facture_mediane"] <= 400:
        log("  ✗ MÉDIANE HORS PLAGE PLAUSIBLE — revoir le modèle (mandat Lot 2)")
        res["plausible"] = False
    else:
        res["plausible"] = True
    return {**base, **res}
