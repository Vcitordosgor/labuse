"""O4 — TRADUCTEUR DE RÈGLEMENT PLU : « cet article, ça donne quoi sur MA parcelle ? »

Deux couches, du plus sûr au plus souple :
 1. **Application déterministe** (toujours dispo) : les règles CHIFFRÉES de la zone (`resolve_zone`,
    déjà calibrées + sourcées par champ) appliquées à la surface de CETTE parcelle → emprise au sol
    maximale en m², hauteurs, reculs, stationnement, pleine terre. Chaque ligne porte sa source
    (« Art. 10 UA »…). `A_VERIFIER` = signalé, jamais comblé.
 2. **Traduction IA d'un article collé** (optionnelle) : si l'utilisateur colle le texte d'un article,
    le socle (sonnet, `strict_numbers`) l'explique EN CLAIR, ancré sur les faits chiffrés ci-dessus —
    il n'invente aucun nombre ; **refus propre** si l'article ne se rattache à aucun fait connu.

Le texte intégral du règlement n'est PAS ingéré : on ne prétend pas le lire. On fournit le **lien profond**
vers la page/article (`resolve_reglement`) pour vérification. **Jamais un conseil juridique** (disclaimer).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("labuse.traducteur")
router = APIRouter(prefix="/traducteur-plu", tags=["traducteur-plu"])

DISCLAIMER = ("Lecture indicative des règles calibrées LABUSE — ne constitue pas un conseil juridique. "
              "Seul le règlement opposable (lien fourni) fait foi ; vérifiez auprès du service instructeur.")


class TraducteurIn(BaseModel):
    article_texte: str | None = None    # texte d'un article collé par l'utilisateur (optionnel)


def get_db():
    from .app import get_db as _g
    yield from _g()


def _applied(zr, surface: float) -> list[dict]:
    """Règles chiffrées de la zone appliquées à la surface de la parcelle, chacune sourcée."""
    from ..faisabilite.plu_rules import A_VERIFIER
    out: list[dict] = []

    def add(label, value, source, *, note=None, calc=None):
        if value is None:
            return
        if value == A_VERIFIER:
            out.append({"regle": label, "valeur": "à vérifier (règlement ambigu)", "source": source or "—",
                        "a_verifier": True})
            return
        out.append({"regle": label, "valeur": value, "source": source or "—",
                    **({"calcul": calc} if calc else {}), **({"note": note} if note else {})})

    src = zr.sources or {}
    if isinstance(zr.emprise_sol_pct, (int, float)):
        emprise_m2 = round(zr.emprise_sol_pct / 100.0 * surface)
        add("Emprise au sol maximale", f"{emprise_m2} m² ({zr.emprise_sol_pct:g} % de {surface:.0f} m²)",
            src.get("emprise") or src.get("emprise_sol"), calc=f"{zr.emprise_sol_pct:g} % × {surface:.0f} m²")
    elif zr.emprise_sol_pct:
        add("Emprise au sol maximale", zr.emprise_sol_pct, src.get("emprise"))
    add("Hauteur à l'égout / acrotère", f"{zr.he_m} m" if isinstance(zr.he_m, (int, float)) else zr.he_m, src.get("hauteur") or src.get("he"))
    add("Hauteur au faîtage", f"{zr.hf_m} m" if isinstance(zr.hf_m, (int, float)) else zr.hf_m, src.get("hauteur") or src.get("hf"))
    add("Recul sur voirie", f"{zr.recul_voirie_m} m" if isinstance(zr.recul_voirie_m, (int, float)) else zr.recul_voirie_m, src.get("recul_voirie"))
    add("Recul sur limites séparatives", f"{zr.recul_limites_sep_m} m" if isinstance(zr.recul_limites_sep_m, (int, float)) else zr.recul_limites_sep_m, src.get("recul_limites"))
    add("Stationnement", zr.stat_logement, src.get("stationnement") or src.get("stat"))
    if isinstance(zr.pleine_terre_pct, (int, float)):
        pt_m2 = round(zr.pleine_terre_pct / 100.0 * surface)
        add("Pleine terre minimale", f"{pt_m2} m² ({zr.pleine_terre_pct:g} % de {surface:.0f} m²)",
            src.get("pleine_terre"), calc=f"{zr.pleine_terre_pct:g} % × {surface:.0f} m²")
    elif zr.pleine_terre_pct:
        add("Pleine terre minimale", zr.pleine_terre_pct, src.get("pleine_terre"))
    if zr.hauteur_mode == "prospect":
        out.append({"regle": "Hauteur", "valeur": "calculée par prospect (L ≥ H selon la largeur de voirie)",
                    "source": src.get("hauteur") or "règle de prospect", "note": "dépend de la voirie riveraine"})
    return out


_SYSTEM = (
    "Tu es urbaniste. On te donne (1) le texte d'un article de règlement PLU collé par l'utilisateur et "
    "(2) les règles chiffrées DÉJÀ établies pour la parcelle (avec leurs valeurs). Explique EN CLAIR, en 3-5 "
    "phrases, ce que cet article implique CONCRÈTEMENT pour cette parcelle. Règles ABSOLUES : n'invente AUCUN "
    "chiffre ni valeur absent du contexte ; si l'article porte sur un sujet non couvert par les faits fournis, "
    "dis-le explicitement (« cet article n'est pas rattachable aux règles calibrées disponibles ») ; ne donne "
    "jamais de conseil juridique ; reste factuel. Pas de listes, un paragraphe."
)


def _translate(db: Session, article: str, applied: list[dict], zone: str, commune: str) -> dict | None:
    """Traduction IA de l'article collé, ancrée sur les règles chiffrées. None si indispo/rejet."""
    from ..ai import core
    facts = {"zone": core.Fact(f"zone {zone} · commune {commune}", "SOURCE"),
             "article_colle": core.Fact(article[:2000], "SOURCE")}
    for i, a in enumerate(applied):
        facts[f"regle_{i}"] = core.Fact(f"{a['regle']} : {a['valeur']} (source {a['source']})", "SOURCE")
    try:
        ctx = core.build_context(facts, allowed_fields=set(facts))
        res = core.complete(db, kind="traducteur-plu", model=core.MODEL_REASONING, max_tokens=500,
                            system=_SYSTEM, context=ctx, validate=True, require_sources=False,
                            strict_numbers=True)
        if res.degraded:
            return {"disponible": False, "raison": "IA momentanément indisponible (repli sur les règles chiffrées)."}
        if res.rejected:
            return {"disponible": True, "rejet": True,
                    "texte": "Cet article n'est pas rattachable de façon sûre aux règles calibrées disponibles."}
        return {"disponible": True, "rejet": False, "texte": res.text}
    except Exception as exc:  # noqa: BLE001
        log.warning("traduction PLU : %s", exc)
        return {"disponible": False, "raison": type(exc).__name__}


@router.post("/{idu}")
def traducteur_plu(idu: str, body: TraducteurIn, db: Session = Depends(get_db)) -> dict:
    """IDU (+ article collé optionnel) → règles PLU chiffrées appliquées à la parcelle, sourcées, + traduction IA."""
    from ..faisabilite.db import parcel_context
    from ..faisabilite.plu_rules import resolve_zone
    from ..plu_reglement import resolve_reglement

    p = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")
    ctx = parcel_context(db, p["id"])
    if not ctx or not ctx.zone:
        return {"ok": False, "idu": idu,
                "message": "Zone d'urbanisme non résolue pour cette parcelle — règles non applicables.",
                "disclaimer": DISCLAIMER}

    zr = resolve_zone(ctx.zone, ctx.commune)
    if not zr:
        return {"ok": False, "idu": idu, "zone": ctx.zone,
                "message": f"Aucune règle calibrée pour la zone {ctx.zone} — non estimable.",
                "disclaimer": DISCLAIMER}

    applied = _applied(zr, float(ctx.surface_m2 or 0))
    reglement = None
    try:
        reglement = resolve_reglement(ctx.commune, ctx.zone)
    except Exception:  # noqa: BLE001
        pass

    out = {"ok": True, "idu": idu, "commune": ctx.commune, "zone": ctx.zone,
           "zone_calibree": zr.calibree, "surface_m2": round(float(ctx.surface_m2 or 0)),
           "regles_appliquees": applied, "reglement": reglement, "disclaimer": DISCLAIMER}
    if not zr.calibree:
        out["avertissement"] = "Règles issues d'une estimation générique (zone non outillée) — Estimé, à vérifier."
    if body.article_texte and body.article_texte.strip():
        out["traduction"] = _translate(db, body.article_texte.strip(), applied, ctx.zone, ctx.commune)
    return out
