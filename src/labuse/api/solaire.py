"""API du module Habitat Solaire (mandat habitat-solaire, Lots 8-9 backend).

- GET  /solaire/fiche/{idu}     panneau Solaire de la fiche parcelle (parcel_solar + sources)
- GET  /solaire/parkings        vue Parkings APER : table triée par échéance + GeoJSON + CSV
- GET  /solaire/tertiaire       vue Toitures tertiaires (mv_toitures_tertiaires) + CSV
- GET  /solaire/statut          disponibilité de la mesure fine (Lot 8) pour le front
- POST /solaire/mesure/{idu}    Lot 8 CONDITIONNEL — 501 honnête tant que la clé Google
                                n'existe pas (aucun bouton côté front sans statut OK,
                                leçon TANIA) ; cache TTL 30 j + quotas prêts en config.

Sourçage UI (mandat Lot 9.5) : chaque donnée renvoie son libellé de source —
« PVGIS — Commission européenne », « estimation statistique », etc. Pas de sur-promesse.
"""
from __future__ import annotations

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings
from ..ingestion import solaire_tertiaire

router = APIRouter(prefix="/solaire", tags=["solaire"])

SOURCES = {
    "gisement": "PVGIS v5.3 (SARAH3) — Commission européenne, horizon topographique inclus",
    "facture": "Estimation statistique (EDF SEI par commune × surface) — jamais une donnée réelle",
    "azimut": "BD TOPO IGN — grand axe du bâti ; hémisphère sud : le versant NORD est optimal",
    "pv_existant": "Registre national des installations (ODRÉ/EDF SEI) — proxy communal",
    "aper": "Loi n° 2023-175 art. 40 · décrets 2024-1023 et 2025-802 (seuil Réunion 1 000 m²)",
    "amiante": "Bâti pré-1997 (DPE ADEME) — risque amiante toiture À VÉRIFIER, pas un diagnostic",
}


def get_db():
    from .app import get_db as _g
    yield from _g()


@router.get("/fiche/{idu}")
def solaire_fiche(idu: str, db: Session = Depends(get_db)) -> dict:
    row = db.execute(text("""
        SELECT ps.*, p.commune FROM parcel_solar ps JOIN parcels p ON p.idu = ps.idu
        WHERE ps.idu = :idu
    """), {"idu": idu}).mappings().first()
    if row is None:
        raise HTTPException(404, "Parcelle sans données solaires (module Habitat Solaire)")
    parkings = db.execute(text("""
        SELECT payload FROM parcel_signals sg JOIN parcels p ON p.id = sg.parcel_id
        WHERE p.idu = :idu AND sg.signal_type = 'aper_deadline'
    """), {"idu": idu}).scalars().all()
    d = dict(row)
    d.pop("updated_at", None)
    return {
        **d,
        "aper_deadline": list(parkings),
        "mesure_fine_disponible": bool(get_settings().solar_api_key),
        "sources": SOURCES,
    }


@router.get("/parkings", response_model=None)
def solaire_parkings(tranche: str | None = None, fmt: str | None = None,
                     limit: int = Query(500, ge=1, le=2000),
                     db: Session = Depends(get_db)) -> Response | dict:
    """Parkings assujettis APER, triés par échéance (les dépassés d'abord)."""
    where = "WHERE pk.tranche IS NOT NULL"
    params: dict = {"lim": limit}
    if tranche in ("1000_10000", "sup_10000"):
        where += " AND pk.tranche = :tranche"
        params["tranche"] = tranche
    rows = db.execute(text(f"""
        SELECT pk.id, round(pk.surface_m2)::int AS surface_m2, pk.tranche, pk.echeance,
               (pk.echeance < CURRENT_DATE) AS echeance_depassee,
               pk.proprio_pm, pk.proprio_siren, pk.idus, pk.equipe, pk.exempt_probable,
               ST_AsGeoJSON(pk.geom)::json AS geometry,
               ST_X(ST_Centroid(pk.geom)) AS lon, ST_Y(ST_Centroid(pk.geom)) AS lat
        FROM parkings_aper pk
        {where}
        ORDER BY pk.echeance ASC, pk.surface_m2 DESC
        LIMIT :lim
    """), params).mappings().all()
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(["Surface (m²)", "Tranche", "Échéance", "Échéance dépassée",
                    "Propriétaire (PM)", "SIREN", "Parcelles (IDU)"])
        for r in rows:
            w.writerow([r["surface_m2"], r["tranche"], r["echeance"],
                        "OUI" if r["echeance_depassee"] else "non",
                        r["proprio_pm"] or "", r["proprio_siren"] or "",
                        " ".join(r["idus"] or [])])
        return Response(buf.getvalue().encode("utf-8-sig"),
                        media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition":
                                 'attachment; filename="parkings_aper.csv"',
                                 "X-Rows": str(len(rows))})
    items = [{k: r[k] for k in ("id", "surface_m2", "tranche", "echeance",
                                "echeance_depassee", "proprio_pm", "proprio_siren",
                                "idus", "equipe", "exempt_probable", "lon", "lat")}
             for r in rows]
    geojson = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": r["geometry"],
         "properties": {"kind": "lot", "label": f"{r['surface_m2']} m²"}} for r in rows]}
    # `total`/`echeances_depassees` = VRAIS COUNT (mêmes filtres, SANS le LIMIT d'affichage) —
    # le nombre annoncé ne doit jamais être la longueur de la liste tronquée. `affiches` = rendu.
    cnt = db.execute(text(f"SELECT count(*) AS total, "
                          f"count(*) FILTER (WHERE pk.echeance < CURRENT_DATE) AS depasses "
                          f"FROM parkings_aper pk {where}"),
                     {k: v for k, v in params.items() if k != "lim"}).mappings().one()
    return {"total": int(cnt["total"]), "echeances_depassees": int(cnt["depasses"]),
            "affiches": len(items), "items": items,
            "geojson": geojson, "source": SOURCES["aper"],
            "note": "Détection OSM (déclaratif) : volumétrie plancher, pas un recensement. "
                    "Surface mesurée sur le polygone OSM ; exemptions non déduites."}


@router.get("/tertiaire", response_model=None)
def solaire_tertiaire_view(fmt: str | None = None,
                           limit: int = Query(300, ge=1, le=5000),
                           db: Session = Depends(get_db)) -> Response | dict:
    """Grandes toitures × PM × bilan INPI × gisement, triées par potentiel."""
    try:
        if fmt == "csv":
            data = solaire_tertiaire.export_csv(db, limit=limit)
            return Response(data.encode("utf-8-sig"), media_type="text/csv; charset=utf-8",
                            headers={"Content-Disposition":
                                     'attachment; filename="toitures_tertiaires.csv"'})
        rows = db.execute(text(
            "SELECT * FROM mv_toitures_tertiaires ORDER BY potentiel DESC LIMIT :lim"),
            {"lim": limit}).mappings().all()
    except Exception as exc:  # vue absente = module pas encore construit
        raise HTTPException(503, "Vue tertiaire indisponible — lancer "
                                 "`labuse solaire-tertiaire`") from exc
    items = [{k: r[k] for k in ("bat_id", "idu", "commune", "emprise_m2", "usage",
                                "proprio_pm", "proprio_siren", "bilan_annee", "ca",
                                "resultat_net", "prod_spec_kwh_kwc", "score_solaire",
                                "dist_poste_source_m", "lat", "lon")} for r in rows]
    # `total` = VRAI COUNT du gisement (sans le LIMIT d'affichage) ; `affiches` = rendu tronqué.
    total = int(db.execute(text("SELECT count(*) FROM mv_toitures_tertiaires")).scalar() or 0)
    return {"total": total, "affiches": len(items), "items": items,
            "note": "Distance au poste source indisponible : cartographie EDF SEI "
                    "dépubliée (sécurité). Capacité S3REnR restante : 0 MW sur l'île "
                    "(avril 2026) — argument autoconsommation."}


@router.get("/statut")
def solaire_statut(db: Session = Depends(get_db)) -> dict:
    """Statut du module pour le front (dont gating du bouton mesure fine, Lot 8)."""
    s = get_settings()
    n = db.execute(text("SELECT count(score_solaire) FROM parcel_solar")).scalar_one()
    return {
        "score_solaire_parcelles": n,
        "mesure_fine_disponible": bool(s.solar_api_key),
        "mesure_fine_note": None if s.solar_api_key else
            "Google Solar API non activée (quickcheck couverture 974 en attente — Vic). "
            "Two-tier = PVGIS pur.",
    }


@router.post("/mesure/{idu}")
def solaire_mesure(idu: str, db: Session = Depends(get_db)) -> dict:
    """Lot 8 (CONDITIONNEL) : mesure fine du toit via Google Solar API buildingInsights.

    Implémentation volontairement STUB tant que Vic n'a pas confirmé la couverture
    BASE du 974 : sans clé → 501 honnête, jamais de bouton côté front (leçon TANIA).
    Le jour où la clé arrive : flux cache strict (solar_api_cache, TTL 30 j, refresh
    LAZY, jamais de re-scan proactif), quota client 100/j, circuit-breaker global
    350/j (+ hard cap console GCP côté Vic), attribution Google dans l'UI.
    """
    s = get_settings()
    if not s.solar_api_key:
        raise HTTPException(501, "Mesure fine non activée : Google Solar API en attente "
                                 "de validation de couverture 974 (two-tier = PVGIS pur).")
    # Garde-fou : même avec une clé posée, l'implémentation de l'appel sortant
    # appartient à la confirmation du quickcheck (mandat Lot 8 : conditionnel).
    raise HTTPException(501, "Client Google Solar non implémenté (Lot 8 conditionnel — "
                             "confirmer le quickcheck de couverture avec Vic).")


def purge_cache(db: Session, *, aujourd_hui: date | None = None) -> int:
    """Purge ToS : entrées > TTL (30 j). Appelée par le cron mensuel (solaire-cache-purge)."""
    ttl = get_settings().solar_api_cache_ttl_jours
    return db.execute(text(
        "DELETE FROM solar_api_cache WHERE fetched_at < now() - make_interval(days => :d)"),
        {"d": ttl}).rowcount
