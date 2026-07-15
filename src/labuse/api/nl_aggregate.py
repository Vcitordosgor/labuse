"""M11 · SURFACE B2 — questions AGRÉGÉES de /ia/search (compter/classer, PAS filtrer).

Un agrégat n'est pas une liste filtrée : le client demande un NOMBRE (« combien de brûlantes à
Saint-Paul ? », « quelle commune en a le plus ? »). Boussole (Vic), deux règles de fer :

  1. Le chiffre vient TOUJOURS d'une requête SQL réelle sur le run servi (q_v6_m8), JAMAIS du modèle.
     Le résultat SQL devient le CONTEXTE AUTORISÉ (chiffres étiquetés SOURCÉ) ; l'IA se contente de
     FORMULER (« Saint-Paul compte 28 parcelles brûlantes »).
  2. La couche 2 du socle (`validate_output`) vérifie mécaniquement que chaque chiffre de la réponse
     figure au contexte SQL. Un compte inventé/arrondi/halluciné = REJET (rien de faux servi).

Le tier « brûlante/chaude/… » est défini EXACTEMENT comme la carte et la liste : `parcel_p_score_v2.tier`
du run v2 servi, hors étage 0 dur (`dryrun_parcel_evaluations.status`). Aucune redéfinition du scoring.
"""
from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ai import core
from ..scoring.score_v_constants import Q_A_RUN_LABEL

# ── détection d'INTENTION agrégée : mots de quantité/superlatif absents d'une requête de filtre ──
# « chaudes à Saint-Pierre » (filtre) ≠ « COMBIEN de chaudes à Saint-Pierre » (agrégat).
_AGG_RE = re.compile(
    r"combien|nombre\s+de|quelles?\s+communes?|le\s+plus\s+de|la\s+plus\b|les\s+plus\b|"
    r"r[ée]partition|ventilation|classement|top\s+\d|total\s+de|moyenne", re.I)

# tier v2 → (code base, libellé fr). Mêmes mots que le stub NL (cohérence).
_TIERS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"br[ûu]lant", re.I), "brulante", "brûlante"),
    (re.compile(r"chaude", re.I), "chaude", "chaude"),
    (re.compile(r"r[ée]serve\s*fonci|surveill", re.I), "reserve_fonciere", "réserve foncière"),
    (re.compile(r"[àa]\s*creuser", re.I), "a_creuser", "à creuser"),
]
_ALL_TIERS = ["brulante", "chaude", "reserve_fonciere", "a_creuser"]

# base identique au builder de liste/stats (étage 0 dur du run servi prime)
_E0 = "(d.status IN ('exclue', 'faux_positif_probable'))"
_BASE = ("FROM parcels p "
         "LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run "
         "LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run")

_SYSTEM = (
    "Tu es l'assistant foncier de LA BUSE. On te donne le RÉSULTAT DÉJÀ CALCULÉ d'une requête "
    "(des comptes RÉELS de parcelles). Formule une réponse française courte (1 à 2 phrases) qui "
    "ÉNONCE ces chiffres, clairement.\n"
    "RÈGLES ABSOLUES :\n"
    "- Tu ne CALCULES rien. N'invente, n'arrondis, n'additionne AUCUN chiffre.\n"
    "- Chaque nombre que tu écris DOIT venir des données fournies et être suivi de sa source au format "
    "⟨src:champ⟩ (ex. « Saint-Paul compte 28 parcelles brûlantes ⟨src:nombre⟩ »).\n"
    "- Pour un classement/superlatif, nomme la ou les communes de tête et cite ⟨src:classement⟩.\n"
    "- N'ajoute aucune donnée hors du contexte."
)


def is_aggregate(query: str) -> bool:
    """Vrai si la question demande un compte/agrégat (≠ une recherche filtrable)."""
    return bool(_AGG_RE.search(query or ""))


def _run_params(db: Session) -> dict | None:
    v2 = db.execute(text("SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1")).scalar()
    if not v2:
        return None
    return {"run": Q_A_RUN_LABEL, "v2run": v2}


def _detect_tiers(low: str) -> list[tuple[str, str]]:
    return [(code, lab) for rx, code, lab in _TIERS if rx.search(low)]


def answer_aggregate(db: Session, query: str) -> dict | None:
    """Traduit une question agrégée → SQL déterministe → réponse SOURCÉE validée par le socle.

    Renvoie un dict {aggregate:True, texte, sources, provenance, classement?, data} ou None si la
    question n'est pas exploitable (→ l'appelant retombe sur le flux normal de filtres)."""
    low = (query or "").lower()
    from .ia import _detect_commune  # import tardif : ia.py importe ce module (évite le cycle)

    params = _run_params(db)
    if params is None:
        return None

    commune = _detect_commune(low)
    tiers = _detect_tiers(low)
    tier_codes = [c for c, _ in tiers] or _ALL_TIERS
    tier_label = " + ".join(lab for _, lab in tiers) if tiers else "opportunité (tous tiers)"

    superlatif = bool(re.search(r"quelles?\s+communes?|le\s+plus|la\s+plus|les\s+plus|classement|top\s+\d", low))
    distribution = bool(re.search(r"r[ée]partition|ventilation|par\s+commune", low))

    # ── CAS 1 : compte simple d'un tier dans UNE commune ──
    if commune and not superlatif and not distribution:
        n = db.execute(text(f"SELECT count(*) {_BASE} "
                            f"WHERE p.commune = :c AND s2.tier = ANY(:tiers) AND NOT {_E0}"),
                       {**params, "c": commune, "tiers": tier_codes}).scalar() or 0
        facts = {"commune": core.Fact(commune, "SOURCE"),
                 "tier": core.Fact(tier_label, "SOURCE"),
                 "nombre": core.Fact(int(n), "SOURCE")}
        data = {"kind": "count", "commune": commune, "tier": tier_label, "nombre": int(n)}

    # ── CAS 2/3 : classement / répartition par commune ──
    else:
        rows = db.execute(text(f"SELECT p.commune, count(*) AS n {_BASE} "
                               f"WHERE s2.tier = ANY(:tiers) AND NOT {_E0} "
                               "GROUP BY p.commune ORDER BY n DESC, p.commune"),
                          {**params, "tiers": tier_codes}).all()
        classement = [{"commune": r[0], "nombre": int(r[1])} for r in rows if r[1]]
        if not classement:
            return None
        facts = {"tier": core.Fact(tier_label, "SOURCE"),
                 # le classement complet est SOURCÉ ; le modèle nomme la tête et cite ⟨src:classement⟩
                 "classement": core.Fact(classement[:15], "SOURCE")}
        data = {"kind": "superlative" if superlatif else "distribution",
                "tier": tier_label, "classement": classement}

    # ── grounding + validation socle (couche 2 : chiffres sourcés, sinon rejet) ──
    ctx = core.build_context(facts, allowed_fields=set(facts))
    res = core.complete(db, kind="ia-aggregate", model=core.MODEL_FACTUAL, max_tokens=320,
                        system=_SYSTEM, context={"question": query, "donnees": ctx},
                        validate=True, require_sources=True)
    if res.degraded:
        return None  # API indispo → l'appelant gère le repli
    if res.rejected:
        # un chiffre non sourçable a été produit → on N'AFFICHE PAS (règle : dans le doute, rien)
        return {"aggregate": True, "rejected": True, "reason": res.reason, "data": data,
                "texte": "Je ne peux pas produire ce compte de façon fiable pour l'instant.",
                "sources": [], "provenance": {}}
    texte = re.sub(r"\s+([.,;:!?%])", r"\1", res.text).strip()   # espace avant ponctuation (artefact retrait ⟨src⟩)
    return {"aggregate": True, "rejected": False, "texte": texte,
            "sources": res.sources, "provenance": {k: "SOURCE" for k in res.sources},
            "data": data}
