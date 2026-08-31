"""SECTEUR-1 (S1) — outil « Mon secteur » : les prix DU SECTEUR autour d'une parcelle.

UN SEUL moteur, jamais un calcul parallèle : `sector_price` (le « Marché et secteur » de la fiche
parcelle) pour le bâti, `_ref_local` (la médiane locale de FICHE-COMMUNE-2 C5) par type de bien, et les
annonces Radar actives dans le rayon (avec l'écart demandé/acté du même moteur `badges_pour_biens`).
Chaque chiffre porte sa source, son n et son millésime ; SOUS LE SEUIL de n, le chiffre est ABSENT
(jamais inventé). L'outil s'enrichit seul au fil des dépôts Radar.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/outils", tags=["mon-secteur"])

SEUIL_N = 5   # même honnêteté statistique que le baromètre / les signaux : sous 5 ventes, pas de médiane


def get_db():
    from .app import get_db as _g
    yield from _g()


def _terrain_local(db: Session, idu: str) -> dict | None:
    """Médiane locale du TERRAIN NU autour de la parcelle (ventes DVF sans bâti), rayon adaptatif
    500→1500 m. Miroir de `_ref_local` (bâti) pour le terrain. None sous le seuil (jamais inventé)."""
    for rayon in (500.0, 1000.0, 1500.0):
        r = db.execute(text(
            "SELECT count(*) AS n, "
            "  percentile_cont(0.5) WITHIN GROUP (ORDER BY valeur_fonciere / NULLIF(surface_terrain,0)) AS m, "
            "  to_char(max(date_mutation), 'YYYY') AS millesime "
            "FROM dvf_mutations "
            "WHERE (surface_reelle_bati IS NULL OR surface_reelle_bati = 0) AND surface_terrain > 0 "
            "  AND valeur_fonciere > 0 AND valeur_fonciere / surface_terrain BETWEEN 20 AND 3000 "
            "  AND nature_mutation ILIKE '%vente%' "
            "  AND ST_DWithin(geom::geography, "
            "      (SELECT centroid::geography FROM parcels WHERE idu = :idu), :rad)"),
            {"idu": idu, "rad": rayon}).mappings().first()
        if r and r["m"] and int(r["n"]) >= SEUIL_N:
            return {"eur_m2": round(float(r["m"])), "n": int(r["n"]), "millesime": r["millesime"],
                    "rayon_m": int(rayon), "perimetre": f"terrain nu · {int(rayon)} m autour de la parcelle"}
    return None


def _clean_local(r: dict | None) -> dict | None:
    if not r or not r.get("eur_m2"):
        return None
    return {"eur_m2": round(float(r["eur_m2"])), "n": r.get("n"), "millesime": r.get("millesime"),
            "rayon_m": r.get("rayon_m"), "perimetre": r.get("perimetre")}


@router.get("/mon-secteur")
def mon_secteur(idu: str = Query(..., description="IDU de la parcelle (résolu depuis l'adresse côté front)"),
                db: Session = Depends(get_db)) -> dict:
    """Les prix du secteur autour d'une parcelle : médiane locale DVF par type (maison / appartement /
    terrain nu) avec n + millésime, tendance 12 mois du secteur (bâti), et les annonces Radar actives
    dans le rayon (prix demandé, écart demandé/acté). Rien sous le seuil de n."""
    p = db.execute(text("SELECT id, commune FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not p:
        raise HTTPException(404, f"Parcelle {idu} inconnue")
    pid, commune = p["id"], p["commune"]

    from .export_commun import adresses_ban, format_adresse
    adresse = {i: format_adresse(a) for i, a in adresses_ban(db, [idu]).items()}.get(idu)

    # BÂTI — le moteur « Marché et secteur » de la fiche parcelle (rayon adaptatif, aberrants exclus,
    # récence, indice de fiabilité) + sa tendance 12 mois. Absent si l'échantillon ne tient pas le seuil.
    from ..faisabilite.bilan import sector_price
    from ..faisabilite.engine import Hypotheses
    sp = sector_price(db, pid, Hypotheses.charger(commune))
    secteur_bati = None
    if sp.get("fiable") and sp.get("n") and int(sp["n"]) >= SEUIL_N:
        secteur_bati = {
            "median_eur_m2": sp.get("median"), "q1": sp.get("q1"), "q3": sp.get("q3"),
            "n": sp.get("n"), "rayon_m": sp.get("radius_m"), "type_prix": sp.get("type_prix"),
            "fiabilite": sp.get("fiabilite"), "commune_seule": sp.get("commune_fallback"),
            "periode": sp.get("periode"),
            "tendance_pct": sp.get("tendance_pct"), "tendance": sp.get("tendance"),
        }

    # PAR TYPE — la médiane locale du même type (FICHE-COMMUNE-2 C5), rayon adaptatif, seuil interne.
    from ..pige.signaux import _ref_local
    par_type = {
        "maison": _clean_local(_ref_local(db, idu, "maison")),
        "appartement": _clean_local(_ref_local(db, idu, "appartement")),
        "terrain_nu": _terrain_local(db, idu),
    }

    # RADAR — les annonces actives RATTACHÉES dans le rayon 1500 m, avec l'écart demandé/acté du même
    # moteur `badges_pour_biens` (médiane locale FICHE-COMMUNE-2 C5). L'outil s'enrichit au fil des dépôts.
    biens = [dict(r) for r in db.execute(text(
        "SELECT b.bien_id, b.commune, b.type_bien, b.a_qualifier, b.idu, f.prix, f.surface_hab, f.surface_terrain, "
        "  round(ST_Distance(pb.centroid::geography, "
        "        (SELECT centroid::geography FROM parcels WHERE idu = :idu))) AS dist "
        "FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id "
        "  JOIN parcels pb ON pb.idu = b.idu "
        "WHERE f.valide_at IS NOT NULL AND b.a_qualifier = false AND b.statut IN ('active','en_vente_longue') "
        "  AND ST_DWithin(pb.centroid::geography, "
        "      (SELECT centroid::geography FROM parcels WHERE idu = :idu), 1500) "
        "ORDER BY dist LIMIT 30"), {"idu": idu}).mappings()]
    from ..pige.signaux import badges_pour_biens
    badges = badges_pour_biens(db, biens)
    annonces_radar = []
    for b in biens:
        bd = badges.get(b["bien_id"]) or {}
        annonces_radar.append({
            "commune": b["commune"], "type_bien": b["type_bien"], "prix": b["prix"],
            "distance_m": int(b["dist"]) if b["dist"] is not None else None,
            "prix_m2_affiche": bd.get("affiche_eur_m2"),
            "ecart_pct": bd.get("ecart_pct") if bd.get("calculable") else None,
            "reference_locale": bool(bd.get("reference_locale")),
        })

    return {
        "idu": idu, "commune": commune, "adresse": adresse,
        "secteur_bati": secteur_bati, "par_type": par_type, "annonces_radar": annonces_radar,
        "sources": ["DVF (ventes actées) — médiane locale par type, rayon adaptatif 500→1500 m",
                    "Radar LABUSE — annonces actives rattachées dans le rayon (dépôts humains)"],
        "note": "Chaque chiffre porte son n et son millésime ; sous 5 ventes, il est ABSENT (jamais "
                "inventé). Les annonces Radar s'ajoutent au fil des dépôts.",
    }
