"""SECTEUR-1 (S3) — outil « Veille promoteurs » : les permis déposés par des promoteurs / bailleurs /
SEM, et pour chacun ses acquisitions foncières récentes (Scan patrimoine, MÊME SIREN).

DIAGNOSTIC (rendu au compte-rendu) : l'ingestion Sitadel porte DÉJÀ le demandeur (`permits_sdes.py` :
DENOM_DEM / SIREN_DEM / SIRET_DEM → `raw.petitioner_*`), mais l'OPEN SDES ne le peuple que ~0,5 % (PM
anonymisées). Le linkage FIABLE = le PROPRIÉTAIRE FONCIER personne morale de la parcelle du permis
(`parcelle_personne_morale` via idu), qui porte dénomination + SIREN + groupe MAJIC (la catégorie) — et
c'est le MÊME SIREN que les acquisitions de Scan patrimoine. Chiffres = comptes SQL, millésime affiché.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/outils/veille-promoteurs", tags=["veille-promoteurs"])

# groupe MAJIC → catégorie « promoteur / bailleur / SEM » (diagnostic S3 : les labels de la base).
CATEGORIES = {
    "promoteur": {"groupes": [0], "label": "Promoteur / société privée"},
    "bailleur": {"groupes": [5], "label": "Bailleur social (Office HLM)"},
    "sem": {"groupes": [6], "label": "Société d'économie mixte (SEM)"},
}
_GROUPE_CAT = {0: "promoteur", 5: "bailleur", 6: "sem"}
_TOUS_GROUPES = [0, 5, 6]
PLAFOND = 200


def get_db():
    from .app import get_db as _g
    yield from _g()


@router.get("")
def veille_promoteurs(commune: str | None = Query(None), categorie: str | None = Query(None),
                      depuis: str | None = Query(None, description="AAAA-MM-JJ — période de dépôt"),
                      limit: int = Query(100), db: Session = Depends(get_db)) -> dict:
    """Les permis (≥ 1 logement) dont la parcelle est détenue par un promoteur / bailleur / SEM.
    Filtrable par commune, catégorie, période. Comptes SQL, millésime = dernier dépôt vu."""
    groupes = CATEGORIES.get(categorie, {}).get("groupes", _TOUS_GROUPES) if categorie else _TOUS_GROUPES
    where = ["(s.raw->>'nb_lgt') ~ '^[0-9]+$'", "(s.raw->>'nb_lgt')::int >= 1", "pm.groupe = ANY(:groupes)"]
    params: dict = {"groupes": groupes, "lim": min(max(limit, 1), PLAFOND)}
    if commune:
        where.append("s.commune = :commune"); params["commune"] = commune
    if depuis:
        where.append("s.date_depot >= :depuis"); params["depuis"] = depuis
    w = " AND ".join(where)
    rows = db.execute(text(
        f"SELECT DISTINCT ON (s.id) s.permit_id, s.commune, s.date_depot, "
        f"  (s.raw->>'nb_lgt')::int AS nb_lgt, s.raw->>'etat' AS etat, s.raw->>'destination' AS destination, "
        f"  j.idu, pm.denomination, pm.siren, pm.groupe "
        f"FROM sitadel_permits s "
        f"JOIN LATERAL jsonb_array_elements_text(s.idu_codes) j(idu) ON true "
        f"JOIN parcelle_personne_morale pm ON pm.idu = j.idu "
        f"WHERE {w} "
        f"ORDER BY s.id, s.date_depot DESC NULLS LAST "), params).mappings().all()
    # tri final par date desc + plafond explicite
    permis = sorted(rows, key=lambda r: (r["date_depot"] is not None, r["date_depot"]), reverse=True)
    tronquee = len(permis) > params["lim"]
    permis = permis[:params["lim"]]
    n_total = db.execute(text(
        f"SELECT count(DISTINCT s.id) FROM sitadel_permits s "
        f"JOIN LATERAL jsonb_array_elements_text(s.idu_codes) j(idu) ON true "
        f"JOIN parcelle_personne_morale pm ON pm.idu = j.idu WHERE {w}"), params).scalar() or 0
    millesime = db.execute(text("SELECT max(date_depot) FROM sitadel_permits")).scalar()
    return {
        "n_total": int(n_total), "n_servi": len(permis), "tronquee": tronquee, "plafond": PLAFOND,
        "categories": [{"cle": k, "label": v["label"]} for k, v in CATEGORIES.items()],
        "millesime": millesime.isoformat() if millesime else None,
        "permis": [{
            "permit_id": r["permit_id"], "commune": r["commune"],
            "date_depot": r["date_depot"].isoformat() if r["date_depot"] else None,
            "nb_lgt": r["nb_lgt"], "etat": r["etat"], "destination": r["destination"], "idu": r["idu"],
            "denomination": r["denomination"], "siren": r["siren"],
            "categorie": _GROUPE_CAT.get(r["groupe"], "promoteur"),
        } for r in permis],
        "note": "Le demandeur est le PROPRIÉTAIRE FONCIER personne morale de la parcelle (Scan patrimoine, "
                "même SIREN) — l'open Sitadel n'identifie le pétitionnaire que ~0,5 % du temps.",
    }


@router.get("/{siren}/acquisitions")
def promoteur_acquisitions(siren: str, db: Session = Depends(get_db)) -> dict:
    """Les acquisitions foncières récentes du promoteur (Scan patrimoine, MÊME SIREN) : son patrimoine
    parcellaire actuel par commune. Comptes SQL — jamais une estimation."""
    denom = db.execute(text(
        "SELECT denomination FROM parcelle_personne_morale WHERE siren = :s AND denomination IS NOT NULL LIMIT 1"),
        {"s": siren}).scalar()
    par_commune = db.execute(text(
        "SELECT p.commune, count(*) AS n FROM parcelle_personne_morale pm JOIN parcels p ON p.idu = pm.idu "
        "WHERE pm.siren = :s GROUP BY p.commune ORDER BY 2 DESC LIMIT 20"), {"s": siren}).mappings().all()
    n_total = db.execute(text("SELECT count(*) FROM parcelle_personne_morale WHERE siren = :s"), {"s": siren}).scalar() or 0
    exemples = db.execute(text(
        "SELECT pm.idu, p.commune FROM parcelle_personne_morale pm JOIN parcels p ON p.idu = pm.idu "
        "WHERE pm.siren = :s ORDER BY pm.idu LIMIT 12"), {"s": siren}).mappings().all()
    return {
        "siren": siren, "denomination": denom, "n_parcelles": int(n_total),
        "par_commune": [{"commune": r["commune"], "n": int(r["n"])} for r in par_commune],
        "exemples": [{"idu": r["idu"], "commune": r["commune"]} for r in exemples],
        "note": "Patrimoine parcellaire détenu par ce SIREN (Scan patrimoine, DGFiP PM). Constat, hors scoring.",
    }
