"""Paramètres du bilan promoteur (1.C) — registre unique + résolution par SECTEUR.

Objectif : rendre la calibration FACILE (Vic fournit les vraies valeurs réunionnaises). Tous les
paramètres du bilan sont déclarés ici une seule fois (libellé, groupe, unité, défaut, placeholder),
éditables en UI et persistés par secteur (bassin PLU). Le code n'invente AUCUNE valeur : les params
non calibrés sont marqués `is_placeholder` et signalés « non calibré » dans la fiche.

Résolution : défaut registre ← override global (secteur='*') ← override secteur. Un override n'est
plus « placeholder » (il a été saisi par Vic).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

SECTEUR_GLOBAL = "*"

# key, libellé, groupe, unité, défaut, is_placeholder, critique
# `critique` = sans calibration, le bilan affiche un bandeau « non fiable ».
PARAMS: list[tuple[str, str, str, str, float, bool, bool]] = [
    # Recettes
    ("prix_m2_neuf", "Prix de vente neuf (override ; 0 = DVF du secteur)", "Recettes", "€/m²", 0.0, True, False),
    ("prix_m2_lls", "Prix de sortie logement aidé (LLS)", "Recettes", "€/m²", 0.0, True, False),
    ("ratio_vendable", "Ratio surface de plancher → habitable vendable", "Recettes", "ratio", 0.80, False, False),
    ("bonus_vue_mer_pct", "Bonus prix si vue mer dégagée (2.B)", "Recettes", "%", 0.0, True, False),
    # Coûts
    ("cout_construction_m2_sdp", "Coût de construction", "Coûts", "€/m² SDP", 2550.0, True, True),
    ("cout_vrd_base", "VRD / viabilisation de base", "Coûts", "€/m² terrain", 0.0, True, False),
    ("majoration_vrd_pente_pct", "Majoration VRD — pente forte", "Coûts", "%", 0.0, True, False),
    ("majoration_vrd_assainissement_pct", "Majoration VRD — assainissement autonome", "Coûts", "%", 0.0, True, False),
    # Frais & marge
    ("honoraires_pct", "Honoraires + commercialisation", "Frais & marge", "% du CA", 12.0, False, False),
    ("frais_financiers_pct", "Frais financiers", "Frais & marge", "% du CA", 0.0, True, False),
    ("marge_cible_pct", "Marge cible promoteur", "Frais & marge", "% du CA", 18.0, False, False),
]
_BY_KEY = {p[0]: p for p in PARAMS}
CRITIQUES = [p[0] for p in PARAMS if p[6]]


def defaults() -> dict[str, float]:
    return {p[0]: p[4] for p in PARAMS}


def registry() -> list[dict]:
    """Description des paramètres pour l'UI (groupés, dans l'ordre)."""
    return [{"key": k, "label": lbl, "groupe": grp, "unite": u,
             "defaut": d, "is_placeholder_defaut": ph, "critique": crit}
            for (k, lbl, grp, u, d, ph, crit) in PARAMS]


def resolve(session: Session, secteur: str | None) -> dict[str, dict]:
    """Params effectifs pour un secteur : {key: {value, is_placeholder, source, provenance}}.
    défaut ← override global ← override secteur. Un override saisi n'est plus placeholder ;
    `provenance` (sourcee|estimee|None) distingue une valeur sourcée d'une estimée à affiner."""
    out: dict[str, dict] = {
        k: {"value": v[4], "is_placeholder": v[5], "source": "défaut", "provenance": None}
        for k, v in _BY_KEY.items()}
    rows = session.execute(text(
        "SELECT secteur, param, value, provenance FROM bilan_params WHERE secteur IN ('*', :s)"),
        {"s": secteur or "*"}).all()
    # appliquer global puis secteur (le secteur prime)
    for sect_target in (SECTEUR_GLOBAL, secteur):
        for sect, param, value, prov in rows:
            if sect == sect_target and param in out:
                out[param] = {"value": float(value), "is_placeholder": False,
                              "source": "global" if sect == SECTEUR_GLOBAL else "secteur",
                              "provenance": prov}
    return out


def values(session: Session, secteur: str | None) -> dict[str, float]:
    return {k: r["value"] for k, r in resolve(session, secteur).items()}


def uncalibrated_critical(resolved: dict[str, dict]) -> list[str]:
    """Libellés des paramètres CRITIQUES encore SANS valeur (→ bandeau « non fiable » DUR)."""
    return [_BY_KEY[k][1] for k in CRITIQUES if resolved.get(k, {}).get("is_placeholder", True)]


# Paramètres dont l'affinage par un vrai promoteur change le plus le bilan (cf rapport).
REFINE_KEYS = list(dict.fromkeys(CRITIQUES + ["marge_cible_pct"]))


def estimated_to_refine(resolved: dict[str, dict]) -> list[str]:
    """Libellés des paramètres clés RENSEIGNÉS mais ESTIMÉS (→ sous-bandeau « à affiner », pas dur)."""
    return [_BY_KEY[k][1] for k in REFINE_KEYS
            if resolved.get(k, {}).get("provenance") == "estimee"]


def save(session: Session, secteur: str, param: str, value: float | None) -> None:
    """Enregistre (ou efface si value=None) un override de param pour un secteur."""
    if param not in _BY_KEY:
        raise ValueError(f"paramètre inconnu : {param}")
    if value is None:
        session.execute(text("DELETE FROM bilan_params WHERE secteur=:s AND param=:p"),
                        {"s": secteur, "p": param})
        return
    session.execute(text(
        """INSERT INTO bilan_params (secteur, param, value, is_placeholder, updated_at)
           VALUES (:s,:p,:v, false, now())
           ON CONFLICT (secteur, param) DO UPDATE SET value=EXCLUDED.value,
             is_placeholder=false, updated_at=now()"""),
        {"s": secteur, "p": param, "v": float(value)})
