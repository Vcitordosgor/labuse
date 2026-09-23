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


def _terrain_section(db: Session, idu: str) -> dict | None:
    """Médiane du TERRAIN NU du secteur = celle de la SECTION cadastrale (table pré-agrégée
    `dvf_secteur_medianes`, clé `left(idu,10)`), la MÊME que la valeur foi de la fiche parcelle
    (§Marché, `app.py` `_q_v2_fiche`). ETUDIER-BIEN-2 Lot B : UNE seule méthode « terrain nu
    secteur » partout — on abandonne le rayon géographique de l'ancien `_terrain_local` (qui
    divergeait de la fiche, cf. ETUDIER-BIEN-1 §c). None sous le seuil (jamais inventé)."""
    row = db.execute(text(
        "SELECT mediane_prix_m2, n_ventes, fenetre FROM dvf_secteur_medianes "
        "WHERE secteur = substring(:idu FROM 1 FOR 10) "
        "  AND type_bien IN ('terrain', 'terrain à bâtir') "
        "ORDER BY n_ventes DESC NULLS LAST LIMIT 1"),
        {"idu": idu}).mappings().first()
    if not row or row["mediane_prix_m2"] is None or (row["n_ventes"] or 0) < SEUIL_N:
        return None
    return {"eur_m2": round(float(row["mediane_prix_m2"])), "n": row["n_ventes"],
            "millesime": row["fenetre"], "rayon_m": None,
            "perimetre": "terrain nu · section cadastrale", "distribution": None}


def _clean_local(r: dict | None) -> dict | None:
    if not r or not r.get("eur_m2"):
        return None
    return {"eur_m2": round(float(r["eur_m2"])), "n": r.get("n"), "millesime": r.get("millesime"),
            "rayon_m": r.get("rayon_m"), "perimetre": r.get("perimetre"),
            "distribution": r.get("distribution")}


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
        # Écart avec la médiane bâti de la COMMUNE ENTIÈRE (référentiel unique `_dvf_bati`) — une
        # ligne d'explication : le secteur (rayon serré) n'est pas la commune (SECTEUR-2 T1).
        from ..pige.signaux import _dvf_bati
        com = _dvf_bati(db, commune)
        ecart_commune = None
        if com.get("eur_m2") and sp.get("median"):
            cv = round(float(com["eur_m2"]))
            ep = round(100.0 * (sp["median"] - cv) / cv) if cv else None
            ecart_commune = {
                "secteur_eur_m2": sp.get("median"), "rayon_m": int(sp.get("radius_m") or 0),
                "commune_eur_m2": cv, "n_commune": com.get("n"), "ecart_pct": ep,
                "phrase": f"secteur {int(sp.get('radius_m') or 0)} m · commune entière {cv} €/m²"
                          + (f" ({ep:+d} %)" if ep is not None else ""),
            }
        secteur_bati = {
            "median_eur_m2": sp.get("median"), "q1": sp.get("q1"), "q3": sp.get("q3"),
            "n": sp.get("n"), "rayon_m": sp.get("radius_m"), "type_prix": sp.get("type_prix"),
            "fiabilite": sp.get("fiabilite"), "commune_seule": sp.get("commune_fallback"),
            "periode": sp.get("periode"),
            "tendance_pct": sp.get("tendance_pct"), "tendance": sp.get("tendance"),
            "distribution": sp.get("distribution"), "ecart_commune": ecart_commune,
        }

    # PAR TYPE — la médiane locale du même type (FICHE-COMMUNE-2 C5), rayon adaptatif, seuil interne.
    from ..pige.signaux import _ref_local
    par_type = {
        "maison": _clean_local(_ref_local(db, idu, "maison")),
        "appartement": _clean_local(_ref_local(db, idu, "appartement")),
        "terrain_nu": _terrain_section(db, idu),
    }

    # RADAR — les annonces actives RATTACHÉES dans le rayon 1500 m, avec l'écart demandé/acté du même
    # moteur `badges_pour_biens` (médiane locale FICHE-COMMUNE-2 C5). L'outil s'enrichit au fil des dépôts.
    # CONNEXIONS-2 Lot 7 (#12/H5) — drapeau dépôt agence fermé ⇒ les dépôts agence sortent de « Mon
    # secteur » (comme du flux/stats client) : un test admin ne fuit pas dans les annonces autour d'un IDU.
    from .. import reglages
    excl = reglages.exclusion_depot_agence_sql("b")
    biens = [dict(r) for r in db.execute(text(
        "SELECT b.bien_id, b.commune, b.type_bien, b.a_qualifier, b.idu, f.prix, f.surface_hab, f.surface_terrain, "
        "  round(ST_Distance(pb.centroid::geography, "
        "        (SELECT centroid::geography FROM parcels WHERE idu = :idu))) AS dist "
        "FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id "
        "  JOIN parcels pb ON pb.idu = b.idu "
        "WHERE f.valide_at IS NOT NULL AND b.a_qualifier = false AND b.statut IN ('active','en_vente_longue') "
        f"{excl}"
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
        "sources": ["DVF (ventes actées) — bâti maison/appartement : médiane locale au rayon adaptatif "
                    "500→1500 m ; terrain nu : médiane de la section cadastrale (même méthode que la fiche)",
                    "Radar LABUSE — annonces actives rattachées dans le rayon (dépôts humains)"],
        "note": "Chaque chiffre porte son n et son millésime ; sous 5 ventes, il est ABSENT (jamais "
                "inventé). Les annonces Radar s'ajoutent au fil des dépôts.",
    }
