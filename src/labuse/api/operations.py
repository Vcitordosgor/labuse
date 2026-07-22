"""O11 — OPÉRATIONS & LOTS : reconstituer les opérations d'aménagement et leur écoulement.

LOT 0 (prouvé, cf. docs/mandats/OUTILS_SUITE.md) : un porteur PERSONNE MORALE qui détient un paquet de
parcelles dans un secteur, un permis PA (aménager) / PC groupé sur ce secteur, et une rafale de ventes DVF
qui suit — les trois signaux s'alignent sur des opérations réelles nommées (CBO Territoria, Alliance…).
DVF n'ayant PAS d'identité vendeur, le rattachement est MULTI-SIGNAL : (a) déclin de propriété du PM
opérateur entre millésimes (lots cédés, Sourcé), (b) permis PA/PC sur le secteur (Sourcé SITADEL),
(c) rafale de ventes DVF sur le secteur/période (Sourcé). Circonstanciel mais convergent.

Fiche d'opération : porteur (SIREN public), secteur, permis, lots au pic, **vendus (Sourcé** = déclin de
propriété), **restant (Estimé** = encore détenu au dernier millésime, **caveat DVF ~6 mois** : les ventes
récentes ne sont pas encore publiées). Personne morale uniquement — jamais un particulier.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("labuse.operations")
router = APIRouter(prefix="/operations", tags=["operations"])

CAVEAT_DVF = ("Restant = Estimé : parcelles encore détenues par le porteur au dernier millésime foncier. "
              "DVF est publié avec ~6 mois de retard — des ventes récentes peuvent ne pas encore apparaître.")

# Détection : PM détenant un paquet (pic ≥ 5) dans un secteur, avec PA (aménager) ou grappe de PC, et déclin.
_DETECT = """
WITH own AS (
  SELECT siren, denomination, left(idu,10) AS secteur, millesime, count(DISTINCT idu) AS n
  FROM pm_proprietaires_millesimes WHERE siren IS NOT NULL GROUP BY 1,2,3,4),
piv AS (
  SELECT siren, denomination, secteur, max(n) AS n_peak,
         (array_agg(n ORDER BY millesime DESC))[1] AS n_fin
  FROM own GROUP BY 1,2,3),
perm AS (
  SELECT left(e,10) AS secteur,
         count(*) FILTER (WHERE type='PA') AS n_pa,
         count(*) FILTER (WHERE type='PC') AS n_pc,
         min(date_part('year', date))::int AS annee_min, max(date_part('year', date))::int AS annee_max
  FROM sitadel_permits sp, jsonb_array_elements_text(sp.idu_codes) e
  WHERE type IN ('PA','PC') GROUP BY 1),
dvf AS (
  SELECT left(id_parcelle,10) AS secteur, count(*) AS n_ventes,
         min(date_part('year', date_mutation))::int AS v_min, max(date_part('year', date_mutation))::int AS v_max
  FROM dvf_mutations_parcelle WHERE nature_mutation='Vente' GROUP BY 1)
SELECT piv.siren, piv.denomination, piv.secteur, left(piv.secteur,5) AS insee,
       piv.n_peak, piv.n_fin, (piv.n_peak - piv.n_fin) AS lots_cedes,
       perm.n_pa, perm.n_pc, perm.annee_min, perm.annee_max,
       coalesce(dvf.n_ventes,0) AS dvf_ventes, dvf.v_min, dvf.v_max,
       fj.forme_juridique
FROM piv JOIN perm ON perm.secteur = piv.secteur
         LEFT JOIN dvf ON dvf.secteur = piv.secteur
         LEFT JOIN LATERAL (SELECT forme_juridique FROM parcelle_personne_morale
                            WHERE siren = piv.siren AND forme_juridique IS NOT NULL
                            LIMIT 1) fj ON true
WHERE piv.n_peak >= 5 AND piv.n_fin < piv.n_peak AND (perm.n_pa >= 1 OR perm.n_pc >= 5)
"""


def get_db():
    from .app import get_db as _g
    yield from _g()


# J6 (post-M7) — formes juridiques DGFiP publiques/parapubliques : TAGUÉES, jamais exclues
# (décision Vic 21/07 : badge visible, le client filtre). SEM/SAM = économie mixte incluse.
FORMES_PUBLIQUES = {"ETAT", "DEPT", "COM", "COLL", "EPA", "EPIC", "SDIS", "SIVU", "SYMI",
                    "SYCO", "CCAS", "CCAM", "HOSP", "GIP", "SEM", "SAM"}


def _confiance(r: dict) -> str:
    """Force du rattachement multi-signal (PA + rafale DVF + déclin marqué → élevée)."""
    signaux = (r["n_pa"] >= 1) + (r["dvf_ventes"] >= 5) + (r["lots_cedes"] >= 3)
    return {3: "élevée", 2: "moyenne"}.get(signaux, "faible")


def _op(r: dict) -> dict:
    fj = (r.get("forme_juridique") or "").strip().upper() or None
    return {
        "porteur": {"siren": r["siren"], "denomination": r["denomination"],   # PM publique, jamais un particulier
                    "forme_juridique": fj,
                    "entite_publique": fj in FORMES_PUBLIQUES if fj else None},
        "secteur": r["secteur"], "insee": r["insee"],
        "permis": {"pa": r["n_pa"], "pc": r["n_pc"], "annees": f"{r['annee_min']}–{r['annee_max']}"},
        "lots_au_pic": r["n_peak"],
        "vendus_sourcee": r["lots_cedes"],           # déclin de propriété du PM = lots cédés (Sourcé millésimes)
        "restant_estime": r["n_fin"],                # encore détenu au dernier millésime (Estimé, caveat DVF)
        "dvf_ventes_secteur": r["dvf_ventes"],
        "periode_ventes": (f"{r['v_min']}–{r['v_max']}" if r.get("v_min") else None),
        "confiance": _confiance(r),
    }


def detect_operations(db: Session, *, commune_insee: str | None = None, limit: int = 100) -> list[dict]:
    if db.execute(text("SELECT to_regclass('pm_proprietaires_millesimes')")).scalar() is None:
        return []
    rows = [dict(r) for r in db.execute(text(_DETECT)).mappings().all()]
    ops = [_op(r) for r in rows if (commune_insee is None or r["insee"] == commune_insee)]
    ordre = {"élevée": 0, "moyenne": 1, "faible": 2}
    ops.sort(key=lambda o: (ordre[o["confiance"]], -o["vendus_sourcee"]))
    return ops[:limit]


@router.get("")
def liste_operations(db: Session = Depends(get_db),
                     commune_insee: str | None = Query(None, description="Filtrer par INSEE commune."),
                     limit: int = Query(100, ge=1, le=1000)) -> dict:
    """Liste des opérations d'aménagement détectées (porteur PM, permis, lots, écoulement), triées par confiance."""
    ops = detect_operations(db, commune_insee=commune_insee, limit=limit)
    return {"operations": ops, "n": len(ops), "caveat_dvf": CAVEAT_DVF,
            "methode": ("Rattachement multi-signal (LOT 0 prouvé) : déclin de propriété du porteur PM + permis PA/PC "
                        "sur le secteur + rafale de ventes DVF. Circonstanciel (DVF sans identité vendeur), convergent."),
            "confidentialite": "Porteurs = personnes morales (SIREN public) uniquement ; jamais un particulier."}


@router.get("/{siren}/{secteur}")
def fiche_operation(siren: str, secteur: str, db: Session = Depends(get_db)) -> dict:
    """Fiche d'UNE opération (porteur SIREN + secteur) : preuves détaillées et écoulement."""
    ops = detect_operations(db, limit=100000)
    op = next((o for o in ops if o["porteur"]["siren"] == siren and o["secteur"] == secteur), None)
    if not op:
        raise HTTPException(404, "Opération non détectée (porteur/secteur inconnus ou sous les seuils).")
    return {**op, "caveat_dvf": CAVEAT_DVF,
            "avertissement": "Rattachement circonstanciel multi-signal ; les faits (permis, propriété, ventes) sont sourcés, "
                             "l'attribution d'une vente précise au porteur n'est pas garantie (DVF sans identité vendeur)."}
