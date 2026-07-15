"""M11 · SURFACE A — Recherche IA par fiche (barre conversationnelle).

Le client pose une question LIBRE sur LA parcelle affichée ; l'IA répond en langage clair, SOURCÉ,
à partir des SEULES données autorisées de cette fiche. Tout passe par le socle `labuse.ai.core` :
liste blanche en entrée, validation de sortie (sources + chiffres) en sortie. Aucune invention.

Décisions Vic (CADRE-M11 §1) appliquées ici :
 - Fiche source = PREMIUM (`_q_v2_fiche`) + agrégation FAISABILITÉ (legacy) — catalogue `_ask_context`.
 - Quota = 20 questions / fiche / jour / sujet (hit cache ne décompte pas).
 - Modèle = haiku par défaut, sonnet UNIQUEMENT pour les questions de faisabilité/montage.
 - Validation = celle du socle (hybride 1+3), jamais réimplémentée.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ai import core
from ..scoring.score_v_constants import Q_A_RUN_LABEL as RUN

router = APIRouter(tags=["ia"])

QUOTA_JOUR = 20  # questions / fiche / jour / sujet (plafond souple ; usage normal ≪ 20)

# Mots-clés → routage sonnet (raisonnement faisabilité/montage). UN SEUL point de décision.
_FAISA_KEYWORDS = re.compile(
    r"combien|construi|constructi|sdp|surface de plancher|faisabilit|rentab|charge fonci|"
    r"logement|densit|gabarit|r\+\d|bilan|marge|prix de sortie|monter|op[ée]ration",
    re.I)


def get_db():
    from .app import get_db as _g
    yield from _g()


def _choose_model(question: str) -> str:
    """haiku (restitution factuelle) par défaut ; sonnet SEULEMENT pour la faisabilité/montage."""
    return core.MODEL_REASONING if _FAISA_KEYWORDS.search(question or "") else core.MODEL_FACTUAL


# ───────────────────── Catalogue liste blanche (fiche premium + faisabilité) ─────────────────────
def _F(value, prov="SOURCE"):
    """Fabrique un Fact ; None → provenance ABSENT (l'IA dira « non disponible »)."""
    return core.Fact(value, "ABSENT" if value in (None, "", [], {}) else prov)


def _ask_context(db: Session, idu: str) -> tuple[dict, dict]:
    """Construit le CONTEXTE AUTORISÉ (Facts étiquetés) + les deep-links. Base premium + faisabilité.

    Retourne (facts, deeplinks). Défensif : un bloc manquant devient ABSENT, jamais une erreur."""
    from .app import _q_v2_fiche
    f = _q_v2_fiche(db, idu)  # fiche PREMIUM (ce que le client voit)

    regl = f.get("reglement_plu") or {}
    via = f.get("viabilisation") or {}
    pot = f.get("potentiel_transformation") or {}
    icd = f.get("icd") or {}
    dvf = f.get("dvf_parcelle") or {}
    # risques + motif d'exclusion : extraits des lignes de cascade tracées
    risques = [ln.get("detail") for ln in (f.get("lines") or [])
               if (ln.get("layer_name") or "") in ("risques", "georisque_alea")
               and ln.get("detail")]
    motifs_exclusion = [ln.get("detail") for ln in (f.get("lines") or [])
                        if ln.get("result") == "HARD_EXCLUDE" and ln.get("detail")]

    # Agrégation FAISABILITÉ (legacy) — pour « combien je peux construire »
    faisa = None
    try:
        pid = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
        if pid is not None:
            from ..faisabilite.db import fiche_payload
            fp = fiche_payload(db, pid) or {}
            fr = fp.get("fourchette") or fp.get("capacite") or {}
            bil = fp.get("bilan") or {}
            faisa = {
                "zone_resolue": fp.get("zone_resolue") or fp.get("zone"),
                "niveaux": fr.get("niveaux"), "hauteur_m": fr.get("hauteur_m"),
                "surface_plancher_m2": fr.get("surface_plancher_m2"),
                "logements_au_sol": fr.get("logements_au_sol"),
                "charge_fonciere_centrale": (bil.get("charge_fonciere") or {}).get("central")
                if isinstance(bil.get("charge_fonciere"), dict) else None,
                "bilan_fiable": bil.get("fiable"),
            }
    except Exception:  # noqa: BLE001 — la faisabilité ne casse jamais la fiche
        faisa = None

    # ── ZONAGE PLU : le bloc premium = {"zones": [{"zone","articles":[{regle,reference,url}], "url"...}]}.
    # MULTI-ZONES : on JOINT toutes les zones (une parcelle bizone affiche « U4b + UD », jamais une seule
    # présentée comme certaine). DEEP-LINK : 1re URL RÉELLEMENT présente (article puis document), sinon aucun.
    zones = regl.get("zones") or []
    zone_labels = [z.get("zone") for z in zones if z.get("zone")]
    zone_str = " + ".join(dict.fromkeys(zone_labels)) or None   # dédup en gardant l'ordre
    regles_zones = [{"zone": z.get("zone"), "regle": a.get("regle"), "reference": a.get("reference")}
                    for z in zones for a in (z.get("articles") or [])
                    if a.get("regle") or a.get("reference")] or None
    reglement_url = None
    for z in zones:                                            # deep-link VÉRIFIÉ mécaniquement, jamais mort
        for a in (z.get("articles") or []):
            if a.get("url"):
                reglement_url = a["url"]
                break
        if reglement_url:
            break
    if not reglement_url:
        reglement_url = next((z.get("url") for z in zones if z.get("url")), None)

    facts: dict[str, core.Fact] = {
        # ── identité / zonage (SOURCÉ) ──
        "idu": _F(f.get("idu")),
        "commune": _F(f.get("commune")),
        "surface_m2": _F(f.get("surface_m2")),
        "statut_tier": _F(f.get("statut")),
        "zone_plu": _F(zone_str),                     # toutes les zones jointes (« U4b + UD » si bizone)
        "reglement_regles": _F(regles_zones),         # règles + références par zone
        # ── viabilisation M-VIA (SOURCÉ) ──
        "viabilisation_indice": _F(via.get("band") or via.get("score")),
        "viabilisation_eau": _F((via.get("contributions") or {}).get("eau") if isinstance(via.get("contributions"), dict) else None),
        "viabilisation_assainissement": _F(via.get("assainissement_zonage") or (via.get("contributions") or {}).get("assainissement") if isinstance(via.get("contributions"), dict) else via.get("assainissement_zonage")),
        "viabilisation_elec": _F((via.get("contributions") or {}).get("elec") if isinstance(via.get("contributions"), dict) else None),
        "viabilisation_cout_raccordement": _F(via.get("cout_raccordement")),
        # ── risques (SOURCÉ) ──
        "risques": _F(risques or None),
        # ── potentiel de transformation (ESTIMÉ) ──
        "potentiel_niveau": _F(pot.get("niveau"), "ESTIME"),
        "sdp_residuelle_m2": _F(pot.get("sdp_residuelle_m2") or pot.get("sdp_residuelle"), "ESTIME"),
        "pct_consomme": _F(pot.get("pct_consomme"), "ESTIME"),
        "sous_densite": _F(pot.get("sous_densite"), "ESTIME"),
        # ── ICD / score P (SOURCÉ, lecture seule) ──
        "icd_bande": _F(icd.get("bande") or icd.get("libelle")),
        "icd_manquants": _F(icd.get("manquants")),
        # ── DVF (SOURCÉ) ──
        "dvf_prix_m2_bati": _F(dvf.get("prix_m2_bati")),
        "dvf_derniere_mutation": _F(dvf.get("date")),
        # ── motif d'exclusion (SOURCÉ) ──
        "motif_exclusion": _F(motifs_exclusion or None),
        # ── faisabilité (ESTIMÉ) ──
        "faisabilite": _F(faisa, "ESTIME"),
    }
    deeplinks = {}
    if reglement_url:   # SEULEMENT si une URL existe réellement — jamais de lien mort côté client.
        # rattaché aux clés que le modèle cite pour le PLU (zone / règles) → étiquette « Sourcé · … ↗ »
        deeplinks["zone_plu"] = reglement_url
        deeplinks["reglement_regles"] = reglement_url
    return facts, deeplinks


_ALLOWED = None


def _allowed_fields(facts: dict) -> set[str]:
    return set(facts)  # la liste blanche EST le catalogue construit ci-dessus (rien d'autre n'existe)


_SYSTEM = (
    "Tu es l'assistant foncier de LA BUSE. Le client pose une question sur UNE parcelle précise. "
    "Tu réponds en français, court, clair, ton d'expert prudent, à partir UNIQUEMENT du JSON de contexte "
    "fourni (données déjà calculées de cette parcelle).\n"
    "RÈGLES ABSOLUES :\n"
    "- N'utilise QUE les valeurs du contexte. N'invente AUCUN chiffre, règle, risque, prix ou donnée absente.\n"
    "- Chaque affirmation factuelle DOIT être suivie de sa source au format ⟨src:cle⟩ où `cle` est la clé "
    "exacte du champ du contexte (ex. « Zone 1AUb ⟨src:zone_plu⟩ »). Un chiffre DOIT venir d'un champ du contexte.\n"
    "- Un champ de provenance ABSENT (valeur nulle) = donnée NON disponible : réponds explicitement « cette "
    "information n'est pas disponible pour cette parcelle », ne DÉDUIS jamais une valeur.\n"
    "- Distingue SOURCÉ (donnée réelle) et ESTIMÉ (capacité/SDP/bilan — dis « estimé »).\n"
    "- Si la question sort du périmètre de la fiche (ex. amiante, diagnostic non couvert), dis-le franchement : "
    "« cette information n'est pas disponible pour cette parcelle ».\n"
    "- FORME : réponds en phrases simples, SANS titres (##), SANS listes (-), SANS citations (>). "
    "Gras (**…**) au besoin uniquement, pour un chiffre ou un terme clé. Pas d'autre Markdown.\n"
    "Réponse : 1 à 4 phrases maximum."
)


class AskIn(BaseModel):
    question: str


def _sujet(request: Request) -> str:
    try:
        from .protection import sujet_de
        return sujet_de(request)
    except Exception:  # noqa: BLE001
        return (request.client.host if request.client else "anon")[:64]


def _quota_used(db: Session, sujet: str, idu: str) -> int:
    db.execute(text("CREATE TABLE IF NOT EXISTS ia_ask_quota ("
                    " sujet varchar(64), idu varchar(14), jour date DEFAULT current_date, n integer DEFAULT 0,"
                    " PRIMARY KEY (sujet, idu, jour))"))
    return db.execute(text("SELECT n FROM ia_ask_quota WHERE sujet=:s AND idu=:i AND jour=current_date"),
                      {"s": sujet, "i": idu}).scalar() or 0


def _quota_inc(db: Session, sujet: str, idu: str) -> None:
    db.execute(text("INSERT INTO ia_ask_quota (sujet, idu, jour, n) VALUES (:s,:i,current_date,1) "
                    "ON CONFLICT (sujet, idu, jour) DO UPDATE SET n = ia_ask_quota.n + 1"),
               {"s": sujet, "i": idu})


@router.post("/parcels/{idu}/ask")
def parcel_ask(idu: str, body: AskIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Barre de fiche : question libre → réponse sourcée, groundée sur la fiche de CETTE parcelle."""
    question = (body.question or "").strip()
    if not question:
        return {"error": "question vide"}

    # 1. CACHE (ne décompte pas le quota) — clé (idu, run servi, question normalisée)
    hit = core.cache_get(db, idu, RUN, question)
    if hit is not None:
        return {**hit, "cached": True}

    # 2. QUOTA — 20 / fiche / jour / sujet ; seuls les VRAIS appels comptent
    sujet = _sujet(request)
    if _quota_used(db, sujet, idu) >= QUOTA_JOUR:
        return {"quota_atteint": True,
                "texte": "Vous avez atteint la limite de questions pour cette parcelle aujourd'hui.",
                "sources": []}

    # 3. CONTEXTE AUTORISÉ (liste blanche) — rien hors catalogue n'est envoyé au modèle
    facts, deeplinks = _ask_context(db, idu)
    ctx = core.build_context(facts, allowed_fields=_allowed_fields(facts))

    # 4. ROUTAGE modèle + appel socle avec VALIDATION DE SORTIE (sources + chiffres)
    model = _choose_model(question)
    res = core.complete(
        db, kind="fiche_ask", model=model, max_tokens=400,
        system=_SYSTEM,
        context={"question": question, "parcelle": ctx},
        validate=True, require_sources=True)

    if res.degraded:
        return {"degraded": True, "texte": "Assistant IA momentanément indisponible — réessayez.",
                "sources": [], "reason": res.reason}

    _quota_inc(db, sujet, idu)  # un vrai appel a eu lieu → décompte (rejeté compris)

    if res.rejected:
        # sortie non sourçable (question hors-données type « amiante », ou chiffre non ancré) :
        # on N'AFFICHE PAS l'affirmation douteuse — message honnête « non disponible ».
        out = {"texte": "Cette information n'est pas disponible de façon sourcée pour cette parcelle.",
               "sources": [], "deeplinks": {}, "provenance": {}, "absent": True,
               "model": res.model, "rejected": True, "cached": False}
    else:
        # sources valides (⟨src:...⟩) → étiquettes + deep-links pour l'UI
        liens = {s: deeplinks[s] for s in res.sources if s in deeplinks}
        out = {"texte": res.text, "sources": res.sources, "deeplinks": liens,
               "provenance": {k: facts[k].provenance for k in res.sources if k in facts},
               "model": res.model, "rejected": False, "cached": False}

    # cache déterministe (temp 0) : validé OU rejeté → une question répétée ne rappelle plus le modèle
    core.cache_put(db, idu, RUN, question, out, kind="fiche_ask")
    return out
