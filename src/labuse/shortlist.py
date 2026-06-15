"""Shortlist promoteur — « Quels sujets fonciers traiter aujourd'hui ? ».

Ce module ne contient QUE la logique de priorisation (pure, testable, sans DB ni I/O).
L'endpoint (`api/app.py:/shortlist`) fournit les lignes candidates (mêmes champs que la
couche carte) et enrichit le haut du panier via la fiche existante — aucune donnée inventée :
tout vient d'évaluations déjà calculées. La priorité n'est PAS le score brut : c'est une
lecture promoteur (exploitabilité + fiabilité + densification + poids économique +
actionnabilité propriétaire − risque), puis bonus d'assemblage sur le panier enrichi.
"""

from __future__ import annotations

from typing import Any

# Poids de base par verdict : on travaille les opportunités d'abord, puis les « à creuser ».
VERDICT_BASE = {"opportunite": 120, "a_creuser": 50}
# Familles de propriétaire « actionnables » (un contact est juridiquement préparable).
OWNER_ACTIONABLE = {"public", "prive"}


def priority_score(row: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """Score de priorité promoteur d'une parcelle candidate + ventilation explicable.

    `row` : champs de la couche carte (status, opportunity_score, completeness_score,
    surface_m2, sous_densite, sdp_residuelle_m2, downgrade_reason, owner_famille)."""
    status = row.get("status")
    opp = row.get("opportunity_score") or 0
    cpl = row.get("completeness_score") or 0
    surface = row.get("surface_m2") or 0
    sdp_res = row.get("sdp_residuelle_m2") or 0
    comp: dict[str, float] = {
        "verdict": float(VERDICT_BASE.get(status, 0)),
        "opportunite": float(opp),                              # 0–100 : signal d'opportunité
        "fiabilite": round(cpl * 0.4, 1),                       # 0–40 : complétude = confiance
        "densification": 25.0 if row.get("sous_densite") else 0.0,
        "residuel": round(min(sdp_res / 100.0, 20), 1),         # 0–20 : SDP résiduelle exploitable
        "economique": round(min(surface / 100.0, 30), 1),       # 0–30 : poids économique (taille)
        "proprietaire": 18.0 if row.get("owner_famille") in OWNER_ACTIONABLE else 0.0,
        "risque": -30.0 if row.get("downgrade_reason") else 0.0,
    }
    return round(sum(comp.values()), 1), comp


def rank_candidates(rows: list[dict[str, Any]], pool: int = 12) -> list[dict[str, Any]]:
    """Classe les candidats par priorité promoteur et renvoie le haut du panier (à enrichir).

    Tri stable et déterministe : priorité ↓, puis score d'opportunité ↓, puis IDU ↑."""
    scored = []
    for r in rows:
        s, comp = priority_score(r)
        scored.append({**r, "_priority": s, "_components": comp})
    scored.sort(key=lambda x: (-x["_priority"], -(x.get("opportunity_score") or 0), x.get("idu") or ""))
    return scored[: max(pool, 0)]


def assemblage_bonus(possible: bool, surface_cumulee_m2: float | None, seuil_m2: float = 1000.0) -> float:
    """Bonus de priorité quand l'assemblage débloque une vraie opération (panier enrichi)."""
    if not possible:
        return 0.0
    bonus = 30.0
    if surface_cumulee_m2 and surface_cumulee_m2 >= seuil_m2:
        bonus += 15.0   # franchit le seuil de faisabilité → priorité renforcée
    return bonus


def badges(sujet: dict[str, Any]) -> list[str]:
    """Badges promoteur dérivés des données réelles du sujet (aucune invention)."""
    out: list[str] = []
    asm = sujet.get("potentiel_assemblage") or {}
    prop = sujet.get("proprietaire") or {}
    conf = sujet.get("confiance") or {}
    if asm.get("possible"):
        out.append("Assemblage à vérifier")
    if sujet.get("risque_principal"):
        out.append("Risque fort")
    if prop.get("famille") in OWNER_ACTIONABLE and not prop.get("in_pipeline"):
        out.append("À appeler")
    if sujet.get("verdict_status") == "a_creuser":
        out.append("À surveiller")
    # Données à consolider : faible complétude OU bilan non chiffrable.
    low_conf = (conf.get("score") is not None and conf["score"] < 50)
    if low_conf or sujet.get("ca") is None:
        out.append("Données à consolider")
    return out


def assemble_sujet(rang: int, row: dict[str, Any], fiche: dict[str, Any] | None) -> dict[str, Any]:
    """Compose un sujet de shortlist à partir de la ligne candidate + la fiche enrichie.

    Toute donnée absente reste explicitement nulle (« non disponible » côté UI)."""
    fa = (fiche or {}).get("faisabilite") or {}
    bilan = fa.get("bilan") or {}
    vois = (fiche or {}).get("voisinage") or {}
    asm = vois.get("assemblage") or {}
    resume = (fiche or {}).get("resume") or {}
    prosp = (fiche or {}).get("prospection") or {}
    verdict = (fiche or {}).get("verdict") or {}

    status = row.get("status") or verdict.get("status")
    fourchette = fa.get("fourchette") or {}
    niveaux = fourchette.get("niveaux")
    ca = bilan.get("ca")
    cf = bilan.get("charge_fonciere")

    sujet = {
        "rang": rang,
        "idu": row.get("idu"),
        "commune": row.get("commune") or ((fiche or {}).get("parcel") or {}).get("commune"),
        "verdict_status": status,
        "score": row.get("opportunity_score"),
        "completeness_score": row.get("completeness_score"),
        "surface_m2": row.get("surface_m2"),
        "potentiel_seul": niveaux or (fa.get("zone") if fa.get("zone") else None),
        "constructible": fa.get("constructible"),
        "potentiel_assemblage": {
            "possible": bool(asm.get("possible")),
            "n_interessantes": asm.get("n_interessantes"),
            "surface_cumulee_m2": asm.get("surface_cumulee_m2"),
        },
        "ca": ca,                                   # {bas, central, haut} ou None
        "charge_fonciere": cf,                      # {central, par_m2_terrain, ...} ou None
        "fiabilite_marche": bilan.get("fiabilite"),  # fiable | fragile | insuffisant | None
        "blocage_principal": row.get("downgrade_reason") or _premier(resume.get("vigilance")),
        "risque_principal": row.get("downgrade_reason"),
        "confiance": {"score": row.get("completeness_score"), "label": _confiance_label(row.get("completeness_score"))},
        "proprietaire": {
            "famille": row.get("owner_famille"),
            "statut": prosp.get("statut_label") or (prosp.get("statut") if prosp else None),
            "in_pipeline": bool(prosp.get("in_pipeline")) if prosp else False,
        },
        "prochaine_action": resume.get("prochaine_action") or _action_defaut(status),
        "priority_score": row.get("_priority"),
        "priority_components": row.get("_components"),
    }
    sujet["badges"] = badges(sujet)
    if rang == 1:
        sujet["badges"].insert(0, "Priorité du jour")
    return sujet


def _premier(seq) -> str | None:
    return seq[0] if isinstance(seq, (list, tuple)) and seq else None


def _confiance_label(score) -> str:
    if score is None:
        return "à consolider"
    if score >= 70:
        return "élevée"
    if score >= 50:
        return "moyenne"
    return "faible"


def _action_defaut(status: str | None) -> str:
    if status == "opportunite":
        return "Qualifier et identifier le propriétaire"
    if status == "a_creuser":
        return "Creuser le potentiel avant démarche"
    return "À vérifier"
