"""Calcul de pré-faisabilité : enveloppe constructible + fourchette de capacité.

Principe (Saint-Paul : emprise au sol le plus souvent NON réglementée) → la capacité
est bornée par les RECULS (enveloppe au sol), la HAUTEUR hé (niveaux) et la PLEINE
TERRE imposée, puis MODULÉE par les contraintes réunionnaises (pente/PPR/littoral/SAR).
Tout est tracé à sa règle source ; tout résultat est une FOURCHETTE ; toute hypothèse
est signalée. On n'invente jamais d'emprise.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .plu_rules import A_VERIFIER, ZoneRules


@dataclass
class Hypotheses:
    """Hypothèses de calcul — TOUTES signalées dans le rendu."""
    etage_m: float = 3.0                 # hauteur d'un niveau
    logement_m2_bas: float = 55.0        # petit logement → plus de logements
    logement_m2_haut: float = 75.0       # grand logement → moins
    place_m2: float = 25.0               # 1 place de stationnement (avec circulation)
    recul_voirie_defaut_m: float = 5.0   # quand l'Art. 6 est "a_verifier"
    recul_limites_defaut_m: float = 3.0  # quand l'Art. 7 est "a_verifier"


@dataclass
class Contraintes:
    """Contraintes réunionnaises de la parcelle (issues de la cascade / des couches)."""
    pente_pct: float | None = None
    alea_ppr: str | None = None          # "fort" | "moyen" | "faible" | None
    bande_littorale: bool = False        # trait de côte / loi littoral
    agricole_sar: bool = False           # zonage agricole / protection SAR
    libelles: list[str] = field(default_factory=list)


@dataclass
class Step:
    label: str
    formule: str
    valeur: str
    source: str


@dataclass
class Faisabilite:
    zone: str
    zone_resolue: str | None
    constructible: bool
    verdict: str
    steps: list[Step]
    hypotheses: list[str]
    avertissements: list[str]
    modulation: list[str]
    fourchette: dict
    bandeau: str


_BANDEAU = (
    "Pré-faisabilité indicative sur règlement PLU public — ne remplace pas une "
    "étude de faisabilité réglementaire par un professionnel."
)


def _is_num(x) -> bool:
    return isinstance(x, (int, float))


def estimate_capacity(rules: ZoneRules, surface_m2: float,
                      contraintes: Contraintes | None = None,
                      hyp: Hypotheses | None = None) -> Faisabilite:
    hyp = hyp or Hypotheses()
    c = contraintes or Contraintes()
    steps: list[Step] = []
    hypotheses: list[str] = []
    avert: list[str] = []
    modul: list[str] = []

    def fini(constructible, verdict, fourchette):
        return Faisabilite(rules.code, rules.via_renvoi, constructible, verdict,
                           steps, hypotheses, avert, modul, fourchette, _BANDEAU)

    if rules.via_renvoi:
        steps.append(Step("Zone (renvoi AU→U)", rules.via_renvoi, rules.code, "Règlement, caractère de zone"))

    # Zone AU*st : pas de construction neuve
    if not rules.constructible_neuf:
        return fini(False, "Construction neuve non autorisée — secteur de transition "
                    "(AU*st) : travaux mineurs de mise aux normes, H max 4 m.",
                    {"logements": (0, 0)})

    # ---- Reculs (avec hypothèse prudente si « a_verifier ») ----
    if _is_num(rules.recul_voirie_m):
        recul_v, rv_src = float(rules.recul_voirie_m), rules.sources.get("recul_voirie", "Art. 6")
    else:
        recul_v = hyp.recul_voirie_defaut_m
        rv_src = "Art. 6 (à_vérifier → hypothèse)"
        avert.append(f"Recul voirie « à_vérifier » pour {rules.code} → hypothèse prudente {recul_v:g} m.")
    if _is_num(rules.recul_limites_sep_m):
        recul_l, rl_src = float(rules.recul_limites_sep_m), rules.sources.get("recul_limites", "Art. 7")
    else:
        recul_l = hyp.recul_limites_defaut_m
        rl_src = "Art. 7 (à_vérifier → hypothèse)"
        avert.append(f"Recul limites « à_vérifier » pour {rules.code} → hypothèse {recul_l:g} m.")

    # ---- Emprise constructible au sol (modèle parcelle carrée, 1 façade sur voie) ----
    cote = math.sqrt(max(0.0, surface_m2))
    larg = max(0.0, cote - recul_v - recul_l)   # voie d'un côté, séparative de l'autre
    prof = max(0.0, cote - 2 * recul_l)          # deux limites séparatives
    emprise = larg * prof
    hypotheses.append(f"Parcelle modélisée carrée ({cote:.0f}×{cote:.0f} m), 1 façade sur voie (modèle simplifié).")
    steps.append(Step("Emprise au sol — reculs",
                      f"(√{surface_m2:.0f}−{recul_v:g}−{recul_l:g}) × (√{surface_m2:.0f}−2×{recul_l:g}) "
                      f"= {larg:.0f}×{prof:.0f}", f"~{emprise:.0f} m²", f"{rv_src} ; {rl_src}"))

    # emprise réglementée explicite (ex. Usdu)
    if _is_num(rules.emprise_sol_pct):
        cap = surface_m2 * float(rules.emprise_sol_pct) / 100
        emprise = min(emprise, cap)
        steps.append(Step("Emprise au sol — % réglementé",
                          f"min(reculs, {surface_m2:.0f}×{rules.emprise_sol_pct:g}%)",
                          f"~{emprise:.0f} m²", rules.sources.get("emprise", "Art. 9")))
    else:
        steps.append(Step("Emprise au sol — % réglementé",
                          "non réglementée (Art. 9 « il n'est pas fixé de règle ») → bornée par les reculs",
                          "—", rules.sources.get("emprise", "Art. 9")))

    # pleine terre
    pt_area = 0.0
    if _is_num(rules.pleine_terre_pct):
        pt = float(rules.pleine_terre_pct)
        pt_area = surface_m2 * pt / 100
        cap_pt = surface_m2 * (1 - pt / 100)
        if cap_pt < emprise:
            emprise = cap_pt
        steps.append(Step("Contrainte pleine terre",
                          f"emprise ≤ {surface_m2:.0f}×(1−{pt:g}%) = {cap_pt:.0f} m²",
                          f"~{emprise:.0f} m² retenu", rules.sources.get("pleine_terre", "Art. 13")))
    else:
        avert.append(f"% pleine terre « à_vérifier » pour {rules.code} → non appliqué (Art. 13).")
    emprise = max(0.0, emprise)

    # ---- Niveaux (hé prioritaire) ----
    he_src = rules.sources.get("hauteur", "Art. 10")
    if _is_num(rules.he_m):
        niveaux = int(float(rules.he_m) // hyp.etage_m)
        steps.append(Step("Niveaux constructibles",
                          f"hé {rules.he_m:g} m ÷ {hyp.etage_m:g} m/niveau = {niveaux} niveaux",
                          f"R+{max(0, niveaux - 1)}", he_src))
    elif _is_num(rules.hf_m):
        he_est = float(rules.hf_m) - hyp.etage_m
        niveaux = max(1, int(he_est // hyp.etage_m))
        avert.append(f"Hauteur égout (hé) non précisée pour {rules.code} : niveaux estimés "
                     f"depuis hf {rules.hf_m:g} m (prudent, réserve toiture).")
        steps.append(Step("Niveaux constructibles",
                          f"hé non précisé → (hf {rules.hf_m:g}−{hyp.etage_m:g}) ÷ {hyp.etage_m:g} = {niveaux}",
                          f"R+{max(0, niveaux - 1)}", he_src))
    else:
        return fini(False, "Hauteur non disponible (à_vérifier) — capacité non calculable.",
                    {"logements": (0, 0)})
    hypotheses.append(f"Hauteur d'étage supposée {hyp.etage_m:g} m ; niveaux comptés sur hé (égout), pas hf.")

    # ---- Surface de plancher & logements (fourchette) ----
    sdp = emprise * niveaux
    steps.append(Step("Surface de plancher potentielle",
                      f"{emprise:.0f} m² × {niveaux} niveaux", f"~{sdp:.0f} m²", "dérivé reculs×hauteur"))

    log_bas = sdp / hyp.logement_m2_haut
    log_haut = sdp / hyp.logement_m2_bas
    steps.append(Step("Logements (avant garde-fous)",
                      f"{sdp:.0f} ÷ {hyp.logement_m2_haut:g} à {hyp.logement_m2_bas:g} m²/logt",
                      f"~{log_bas:.0f} à {log_haut:.0f}", "hypothèse surface logement"))
    hypotheses.append(f"Surface moyenne logement supposée {hyp.logement_m2_bas:g}–{hyp.logement_m2_haut:g} m².")

    # garde-fou stationnement
    ppl = rules.places_par_logement()
    if _is_num(ppl) and ppl > 0:
        sol_dispo = max(0.0, surface_m2 - emprise - pt_area)
        log_max_park = sol_dispo / (ppl * hyp.place_m2)
        steps.append(Step("Garde-fou stationnement",
                          f"{ppl:g} pl./logt × {hyp.place_m2:g} m² ; sol restant {sol_dispo:.0f} m² "
                          f"→ ≤ {log_max_park:.0f} logts", "appliqué", rules.sources.get("stationnement", "Art. 12")))
        if log_max_park < log_haut:
            log_haut = log_max_park
            log_bas = min(log_bas, log_max_park)
            modul.append(f"Stationnement plafonne la capacité à ~{log_max_park:.0f} logements.")
        hypotheses.append(f"1 place de stationnement supposée {hyp.place_m2:g} m² ; parking au sol restant.")
    elif ppl == A_VERIFIER:
        avert.append(f"Stationnement « à_vérifier » pour {rules.code} → garde-fou non appliqué (Art. 12).")

    # ---- Modulation réunionnaise ----
    facteur = 1.0
    if c.agricole_sar:
        facteur = 0.0
        modul.append("Zonage agricole / protection SAR → urbanisation non autorisée malgré le zonage U.")
    if c.alea_ppr == "fort":
        facteur = 0.0
        modul.append("Aléa FORT (PPR) → quasi inconstructible : étude/refus spécifique requis.")
    elif c.alea_ppr in ("moyen", "faible"):
        f = 0.6 if c.alea_ppr == "moyen" else 0.85
        facteur = min(facteur, f)
        modul.append(f"Aléa {c.alea_ppr} (PPR) → prescriptions, capacité réduite (~×{f:g}).")
    if c.bande_littorale:
        facteur = min(facteur, 0.0)
        modul.append("Trait de côte / bande littorale → inconstructible ou très restreint.")
    if c.pente_pct is not None:
        if c.pente_pct >= 30:
            facteur = min(facteur, 0.4)
            modul.append(f"Pente forte {c.pente_pct:.0f}% → terrassement lourd, accès difficile (~×0,4).")
        elif c.pente_pct >= 15:
            facteur = min(facteur, 0.7)
            modul.append(f"Pente {c.pente_pct:.0f}% → surcoût, capacité réduite (~×0,7).")
    for lib in c.libelles:
        modul.append(lib)

    log_bas *= facteur
    log_haut *= facteur

    # ---- Verdict ----
    rp = f"R+{max(0, niveaux - 1)}"
    if facteur == 0.0:
        return fini(False, f"Non constructible en l'état malgré le zonage ({rp} théorique) — "
                    "contrainte rédhibitoire (voir modulation).",
                    {"niveaux": rp, "surface_plancher_m2": round(sdp), "logements": (0, 0)})

    lo, hi = math.floor(log_bas), math.ceil(log_haut)
    lo = max(0, lo)
    verdict = f"{rp} · ~{lo} à {hi} logements"
    return fini(True, verdict,
                {"niveaux": rp, "surface_plancher_m2": round(sdp), "logements": (lo, hi)})
