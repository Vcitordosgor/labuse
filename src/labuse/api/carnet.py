"""O7 — CARNET DE SECTEUR CONSULTABLE : une page de suivi par micro-secteur (préfixe IDU 10).

Un secteur = `left(idu, 10)` = INSEE + « 000 » + section cadastrale. Le carnet agrège, en LECTURE
(zéro donnée nouvelle), tout ce qui bouge sur ce secteur : prix DVF (terrain / sortie neuf), stock
d'opportunités par tier, permis SITADEL récents, signaux de veille (végétation, piscine, ANC, APER),
contexte ZAN de la commune. Chaque bloc est sourcé.

`GET /carnet-secteur` liste les secteurs à suivre (triés par stock d'opportunités) ;
`GET /carnet-secteur/{secteur}` = la page d'UN secteur.

**Décision par défaut documentée (mail hebdo / comptes = POST-M7)** : l'ABONNEMENT à un secteur (envoi
d'un digest hebdomadaire, notion de compte utilisateur) relève du mandat Auth & Plans et n'est PAS livré
ici — le carnet est **consultable à la demande**. Les tables `watch_zones` / `watched_parcels` existent
déjà et seront le point d'ancrage de l'abonnement le moment venu.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..scoring.score_v_constants import Q_A_RUN_LABEL

log = logging.getLogger("labuse.carnet")
router = APIRouter(prefix="/carnet-secteur", tags=["carnet-secteur"])

_SIGNAL_LABELS = {
    "vegetation_haute_limite": "Végétation haute en limite",
    "piscine_detectee": "Piscine détectée (sans PC retrouvé)",
    "anc_mutation": "Assainissement non collectif — mutation",
    "aper_deadline": "APER — échéance photovoltaïque",
}

POST_M7 = ("Abonnement (digest hebdomadaire, compte utilisateur) = post-M7 (mandat Auth & Plans) ; "
           "carnet consultable à la demande. Ancrage futur : watch_zones / watched_parcels.")


def get_db():
    from .app import get_db as _g
    yield from _g()


def _has(db: Session, table: str) -> bool:
    return db.execute(text("SELECT to_regclass(:t)"), {"t": table}).scalar() is not None


@router.get("")
def liste_secteurs(db: Session = Depends(get_db),
                   commune: str | None = None, limit: int = Query(30, ge=1, le=200)) -> dict:
    """Secteurs à suivre, triés par stock d'opportunités (brûlantes + chaudes) du run servi."""
    rows = db.execute(text(
        """SELECT left(s.parcelle_id, 10) AS secteur, p.commune,
                  count(*) FILTER (WHERE s.tier IN ('brulante', 'chaude')) AS opportunites,
                  count(*) FILTER (WHERE s.tier = 'brulante') AS brulantes
           FROM parcel_p_score_v2 s JOIN parcels p ON p.idu = s.parcelle_id
           WHERE s.run_id = :run AND (CAST(:c AS text) IS NULL OR p.commune = :c)
           GROUP BY 1, 2 HAVING count(*) FILTER (WHERE s.tier IN ('brulante', 'chaude')) > 0
           ORDER BY opportunites DESC, brulantes DESC LIMIT :lim"""),
        {"run": Q_A_RUN_LABEL, "c": commune, "lim": limit}).mappings().all()
    return {"secteurs": [dict(r) for r in rows], "n": len(rows), "note": POST_M7}


@router.get("/{secteur}")
def carnet(secteur: str, db: Session = Depends(get_db)) -> dict:
    """Page de suivi d'UN secteur (préfixe IDU 10) : prix, stock, permis, signaux, ZAN — tout sourcé."""
    if len(secteur) != 10:
        raise HTTPException(422, "Le secteur doit faire 10 caractères (INSEE + 000 + section).")
    insee = secteur[:5]
    commune = db.execute(text("SELECT commune FROM parcels WHERE left(idu,10) = :s LIMIT 1"),
                         {"s": secteur}).scalar()
    if not commune:
        raise HTTPException(404, f"Secteur {secteur} inconnu.")

    # stock par tier
    tiers = {r["tier"]: r["n"] for r in db.execute(text(
        "SELECT tier, count(*) AS n FROM parcel_p_score_v2 WHERE run_id = :run AND left(parcelle_id,10) = :s GROUP BY tier"),
        {"run": Q_A_RUN_LABEL, "s": secteur}).mappings()}

    # prix DVF (médianes sectorielles) + prix de sortie neuf
    prix = {}
    if _has(db, "dvf_secteur_medianes"):
        prix = {r["type_bien"]: {"mediane_prix_m2": r["mediane_prix_m2"], "n": r["n_ventes"]} for r in db.execute(text(
            "SELECT type_bien, mediane_prix_m2, n_ventes FROM dvf_secteur_medianes WHERE secteur = :s"),
            {"s": secteur}).mappings()}
    neuf = None
    if _has(db, "dvf_prix_sortie_neuf"):
        neuf = db.execute(text(
            "SELECT prix_m2_neuf, n FROM dvf_prix_sortie_neuf WHERE cle = :s AND niveau = 'secteur'"),
            {"s": secteur}).mappings().first()

    # signaux de veille récents sur les parcelles du secteur
    signaux = []
    if _has(db, "parcel_signals"):
        signaux = [{"type": _SIGNAL_LABELS.get(r["signal_type"], r["signal_type"]), "n": r["n"]} for r in db.execute(text(
            """SELECT sg.signal_type, count(*) AS n FROM parcel_signals sg JOIN parcels p ON p.id = sg.parcel_id
               WHERE left(p.idu,10) = :s GROUP BY sg.signal_type ORDER BY n DESC"""), {"s": secteur}).mappings()]

    # permis SITADEL rattachés au secteur (idu_codes) sur 24 mois
    permis = None
    if _has(db, "sitadel_permits"):
        permis = db.execute(text(
            """SELECT count(*) AS n FROM sitadel_permits sp
               WHERE sp.date >= (CURRENT_DATE - INTERVAL '24 months')
                 AND EXISTS (SELECT 1 FROM jsonb_array_elements_text(sp.idu_codes) e WHERE e LIKE :pref)"""),
            {"pref": secteur + "%"}).scalar()

    zan = None
    if _has(db, "commune_conso_enaf"):
        zan = db.execute(text(
            "SELECT commune, conso_2021_2024_m2, source_nom FROM commune_conso_enaf WHERE insee = :i"),
            {"i": insee}).mappings().first()

    return {
        "secteur": secteur, "commune": commune, "section": secteur[8:10], "insee": insee,
        "stock": {"total": sum(tiers.values()), "par_tier": tiers,
                  "opportunites": tiers.get("brulante", 0) + tiers.get("chaude", 0)},
        "prix": {"dvf": prix or None, "sortie_neuf": (dict(neuf) if neuf else None), "source": "DVF (Sourcé)"},
        "signaux": signaux, "permis_24_mois": permis,
        "zan": (dict(zan) if zan else None),
        "note": POST_M7,
        "avertissement": "Lecture de données déjà en base ; indicateurs sourcés, non recalculés.",
    }
