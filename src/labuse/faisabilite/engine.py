"""Calcul de pré-faisabilité : enveloppe constructible + fourchette de capacité.

Principe (Saint-Paul : emprise au sol le plus souvent NON réglementée) → la capacité
est bornée par les RECULS (enveloppe au sol — calculée sur la GÉOMÉTRIE RÉELLE quand
disponible), la HAUTEUR hé (niveaux) et la PLEINE TERRE imposée, puis MODULÉE par les
contraintes réunionnaises (pente/PPR/littoral/SAR).

Deux scénarios de stationnement sont présentés (au sol / sous-sol-silo). Tout est tracé
à sa règle source ; tout résultat est une FOURCHETTE ; toute hypothèse est signalée.
On n'invente jamais d'emprise.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .plu_rules import A_VERIFIER, EXEMPT, ZoneRules

SEUIL_EXIGU_M2 = 5.0  # en deçà, le contour inseté est considéré vidé → "trop exigu"


@dataclass
class Hypotheses:
    etage_m: float = 3.0
    coef_occupation: float = 0.45        # emprise constructible → emprise réellement bâtie au sol
    coef_rendement: float = 0.80         # surface de plancher BRUTE → surface HABITABLE vendable
    logement_m2_bas: float = 65.0
    logement_m2_haut: float = 80.0
    place_m2: float = 25.0
    densite_logts_ha_par_niveau: float = 30.0   # plafond densité = ce taux × niveaux (logts/ha)
    recul_voirie_defaut_m: float = 5.0
    recul_limites_defaut_m: float = 3.0
    # --- Bilan promoteur (PARTIE 1) ---
    # Coûts de construction PRUDENTS pour La Réunion (audit O2) : collectif en contexte
    # insulaire — matériaux importés, normes para-cycloniques/sismiques — les 1 800-2 200 €/m²
    # « métropole » sous-estimaient le coût et SUR-estimaient donc la charge foncière.
    # Le défaut doit être prudent, pas optimiste ; tunable via hypotheses_faisabilite (YAML).
    cout_construction_m2_bas: float = 2300.0    # coût au m² de SURFACE DE PLANCHER (borne basse)
    cout_construction_m2_haut: float = 2800.0   # idem (borne haute)
    # Le coût se rapporte à la surface de PLANCHER, pas à l'habitable vendu (audit O2) :
    # plancher ≈ habitable × 1.15 (circulations, gaines, murs).
    coef_plancher_habitable: float = 1.15
    marge_promoteur_pct: float = 0.09           # marge promoteur (% du CA) — 8–10 %, à affiner
    frais_annexes_pct: float = 0.12             # honoraires, commercialisation, financier, aléas (% du CA)
    dvf_radius_m: float = 1500.0                # rayon de recherche des ventes DVF comparables
    dvf_min_ventes: int = 8                     # en deçà, prix DVF jugé non fiable
    # --- Potentiel résiduel (Lot B) — PLACEHOLDERS ---
    niveaux_bati_existant_defaut: float = 1.0   # niveaux supposés du bâti existant (hauteur BD TOPO non ingérée)
    sous_densite_seuil_pct: float = 40.0        # seuil du taux d'emprise sous lequel = « sous-densité »
    he_defaut_generique_m: float = 9.0          # hé prudent des zones U/AU NON outillées (≈ R+2)
    # --- Prescriptions GPU (Décisions 3.b / 3.c) ---
    pct_lls: float = 0.0              # % de logements aidés (validé Vic : 30 % — Art. 2 règlement PLU)
    prix_m2_lls: float = 0.0          # prix de sortie €/m² des logements aidés (PLACEHOLDER, 0 = non calibré)
    majoration_vrd_pluvial: float = 0.0  # % de majoration du coût (VRD) en zonage eaux pluviales (PLACEHOLDER)
    # Seuils de DÉCLENCHEMENT de la clause de mixité (Art. 2 règlement PLU — SOURCÉS, non placeholder).
    # Clause déclenchée si SDP ≥ seuil OU logements ≥ seuil OU terrain > seuil (logique OU du texte).
    mixite_sdp_seuil_m2: float = 1500.0       # « SDP ≥ 1 500 m² » (bornes 1500/1800 du texte)
    mixite_logements_seuil: float = 20.0      # « programme de 20 logements ou plus »
    mixite_terrain_seuil_m2: float = 6000.0   # « terrain d'habitation de plus de 6 000 m² »

    @classmethod
    def charger(cls) -> "Hypotheses":
        """Hypothèses depuis la section `hypotheses_faisabilite` du YAML (config éditable
        sans toucher au code) ; sinon valeurs par défaut."""
        from .plu_rules import _doc
        h = (_doc().get("hypotheses_faisabilite") or {})
        out = cls()
        for k, v in h.items():
            if hasattr(out, k) and isinstance(v, (int, float)):
                setattr(out, k, float(v))
        return out


@dataclass
class Contraintes:
    pente_pct: float | None = None
    alea_ppr: str | None = None
    bande_littorale: bool = False
    agricole_sar: bool = False
    libelles: list[str] = field(default_factory=list)


@dataclass
class Step:
    label: str
    formule: str
    valeur: str
    source: str
    # Provenance d'AFFICHAGE de la ligne (transparence, n'altère AUCUN calcul) :
    # "sourcee" = donnée réelle (ex. prix DVF) · "estimee" = hypothèse/param calibrable
    # (coût construction, VRD, marge) · "derive" = résultat calculé à partir des lignes ci-dessus
    # · "" = non qualifié (étapes de faisabilité). Sérialisé tel quel pour la fiche.
    prov: str = ""


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
    calibree: bool = True                       # False ⇒ capacité issue de l'estimation générique


_BANDEAU = (
    "Pré-faisabilité indicative sur règlement PLU public — ne remplace pas une "
    "étude de faisabilité réglementaire par un professionnel."
)


def _is_num(x) -> bool:
    return isinstance(x, (int, float))


def _rng(lo: float, hi: float) -> tuple[int, int]:
    return max(0, math.floor(lo)), max(0, math.ceil(hi))


def estimate_capacity(rules: ZoneRules, surface_m2: float,
                      contraintes: Contraintes | None = None,
                      hyp: Hypotheses | None = None,
                      emprise_geo: tuple[float, float] | None = None) -> Faisabilite:
    """emprise_geo = (aire_insetée_m2, recul_utilisé_m) issue de la géométrie réelle ;
    None ⇒ modèle parcelle carrée (repli, tests purs)."""
    hyp = hyp or Hypotheses()
    c = contraintes or Contraintes()
    steps: list[Step] = []
    hypotheses: list[str] = []
    avert: list[str] = []
    modul: list[str] = []

    if not rules.calibree:
        avert.append("Capacité ESTIMÉE — PLU de la commune non outillé (valeurs génériques "
                     "prudentes). Calibrage = ajout d'un YAML PLU communal (config/plu_<commune>.yaml).")

    def fini(constructible, verdict, fourchette):
        return Faisabilite(rules.code, rules.via_renvoi, constructible, verdict,
                           steps, hypotheses, avert, modul, fourchette, _BANDEAU,
                           calibree=rules.calibree)

    if rules.via_renvoi:
        steps.append(Step("Zone (renvoi AU→U)", rules.via_renvoi, rules.code, "Règlement, caractère de zone"))

    if not rules.constructible_neuf:
        return fini(False, "Construction neuve non autorisée — secteur de transition "
                    "(AU*st) : travaux mineurs de mise aux normes, H max 4 m.",
                    {"logements_au_sol": (0, 0), "logements_sous_sol": (0, 0)})

    # reculs (avec hypothèse prudente si "a_verifier")
    if _is_num(rules.recul_voirie_m):
        recul_v, rv_src = float(rules.recul_voirie_m), rules.sources.get("recul_voirie", "Art. 6")
    else:
        recul_v, rv_src = hyp.recul_voirie_defaut_m, "Art. 6 (à_vérifier → hypothèse)"
        avert.append(f"Recul voirie « à_vérifier » pour {rules.code} → hypothèse prudente {recul_v:g} m.")
    if _is_num(rules.recul_limites_sep_m):
        recul_l, rl_src = float(rules.recul_limites_sep_m), rules.sources.get("recul_limites", "Art. 7")
    else:
        recul_l, rl_src = hyp.recul_limites_defaut_m, "Art. 7 (à_vérifier → hypothèse)"
        avert.append(f"Recul limites « à_vérifier » pour {rules.code} → hypothèse {recul_l:g} m.")

    # ---- Emprise constructible au sol ----
    if emprise_geo is not None:
        emprise, recul_used = emprise_geo
        if emprise < SEUIL_EXIGU_M2:
            steps.append(Step("Emprise au sol — reculs (géométrie réelle)",
                              f"contour cadastral inseté de {recul_used:g} m (ST_Buffer 2975)",
                              "≈ 0 m² (contour vidé)", f"{rl_src}"))
            return fini(False, f"Terrain trop exigu compte tenu des reculs ({recul_used:g} m) — "
                        "non constructible en l'état (le contour inseté se vide).",
                        {"logements_au_sol": (0, 0), "logements_sous_sol": (0, 0)})
        steps.append(Step("Emprise au sol — reculs (géométrie réelle)",
                          f"contour cadastral réel inseté de {recul_used:g} m (ST_Buffer, EPSG:2975)",
                          f"~{emprise:.0f} m²", f"{rl_src} (séparatif) ; recul voirie en sus"))
        hypotheses.append("Emprise = contour cadastral réel inseté du recul séparatif (géométrie EPSG:2975).")
        if _is_num(rules.recul_voirie_m) and rules.recul_voirie_m > recul_used:
            avert.append(f"Recul voirie {rules.recul_voirie_m:g} m s'applique en sus sur la façade sur "
                         "rue (bord rue non identifiable au cadastre → non déduit géométriquement).")
    else:
        cote = math.sqrt(max(0.0, surface_m2))
        larg = max(0.0, cote - recul_v - recul_l)
        prof = max(0.0, cote - 2 * recul_l)
        emprise = larg * prof
        hypotheses.append(f"Parcelle modélisée carrée ({cote:.0f}×{cote:.0f} m), 1 façade sur voie (modèle simplifié).")
        steps.append(Step("Emprise au sol — reculs (modèle carré)",
                          f"(√{surface_m2:.0f}−{recul_v:g}−{recul_l:g})×(√{surface_m2:.0f}−2×{recul_l:g})",
                          f"~{emprise:.0f} m²", f"{rv_src} ; {rl_src}"))

    # emprise % réglementée (ex. Usdu)
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
        niveaux = max(1, int((float(rules.hf_m) - hyp.etage_m) // hyp.etage_m))
        avert.append(f"Hauteur égout (hé) non précisée pour {rules.code} : niveaux estimés "
                     f"depuis hf {rules.hf_m:g} m (prudent).")
        steps.append(Step("Niveaux constructibles",
                          f"hé non précisé → (hf {rules.hf_m:g}−{hyp.etage_m:g}) ÷ {hyp.etage_m:g} = {niveaux}",
                          f"R+{max(0, niveaux - 1)}", he_src))
    else:
        return fini(False, "Hauteur non disponible (à_vérifier) — capacité non calculable.",
                    {"logements_au_sol": (0, 0), "logements_sous_sol": (0, 0)})
    hypotheses.append(f"Hauteur d'étage supposée {hyp.etage_m:g} m ; niveaux comptés sur hé (égout), pas hf.")

    # ---- Emprise BÂTIE (on ne remplit pas toute l'enveloppe) ----
    footprint = emprise * hyp.coef_occupation
    steps.append(Step("Emprise bâtie (occupation du gabarit)",
                      f"{emprise:.0f} m² × {hyp.coef_occupation:.0%} (espaces entre bâtiments, accès…)",
                      f"~{footprint:.0f} m²", "hypothèse occupation"))
    hypotheses.append(f"Coefficient d'occupation du gabarit supposé {hyp.coef_occupation:.0%} "
                      "(on ne bâtit pas 100 % de l'emprise constructible).")

    # ---- Surface de plancher BRUTE puis HABITABLE (rendement) ----
    sdp = footprint * niveaux
    steps.append(Step("Surface de plancher brute", f"{footprint:.0f} m² × {niveaux} niveaux",
                      f"~{sdp:.0f} m²", "dérivé occupation×hauteur"))
    shab = sdp * hyp.coef_rendement
    steps.append(Step("Surface habitable (rendement)",
                      f"{sdp:.0f} m² × {hyp.coef_rendement:.0%} (murs, communs, circulations, locaux techniques déduits)",
                      f"~{shab:.0f} m²", "hypothèse rendement"))
    hypotheses.append(f"Coefficient de rendement SDP→habitable supposé {hyp.coef_rendement:.0%}.")

    floor_lo, floor_hi = shab / hyp.logement_m2_haut, shab / hyp.logement_m2_bas
    steps.append(Step("Logements (avant plafonds)",
                      f"{shab:.0f} m² ÷ {hyp.logement_m2_haut:g} à {hyp.logement_m2_bas:g} m²/logt",
                      f"~{floor_lo:.0f} à {floor_hi:.0f}", "hypothèse surface logement"))
    hypotheses.append(f"Surface moyenne par logement supposée {hyp.logement_m2_bas:g}–{hyp.logement_m2_haut:g} m².")

    # ---- Plafond de DENSITÉ (filet de sécurité, remplace le COS) ----
    surface_ha = surface_m2 / 10000.0
    cap_logts_ha = hyp.densite_logts_ha_par_niveau * niveaux
    densite_cap = surface_ha * cap_logts_ha
    steps.append(Step("Plafond de densité (filet de sécurité)",
                      f"{surface_ha:.2f} ha × {cap_logts_ha:.0f} logts/ha "
                      f"({hyp.densite_logts_ha_par_niveau:g}/niveau × {niveaux})",
                      f"≤ {densite_cap:.0f} logts", "hypothèse densité (ex-COS)"))
    hypotheses.append(f"Plafond de densité {hyp.densite_logts_ha_par_niveau:g} logts/ha par niveau "
                      "(filet de sécurité remplaçant le COS).")
    if densite_cap < floor_hi:
        modul.append(f"Plafond de densité {cap_logts_ha:.0f} logts/ha appliqué : le calcul détaillé "
                     f"donnait ~{math.floor(floor_lo)}-{math.ceil(floor_hi)} → borné à "
                     f"~{round(densite_cap)} logts (enveloppe théorique trop optimiste).")
    floor_lo, floor_hi = min(floor_lo, densite_cap), min(floor_hi, densite_cap)

    # ---- Stationnement : 2 scénarios ----
    ppl = rules.places_par_logement()
    sous_lo, sous_hi = floor_lo, floor_hi          # sous-sol/silo : non mangé au sol
    sol_lo, sol_hi = floor_lo, floor_hi
    if _is_num(ppl) and ppl > 0:
        regime = "borne"
        sol_dispo = max(0.0, surface_m2 - footprint - pt_area)
        log_max_park = sol_dispo / (ppl * hyp.place_m2)
        steps.append(Step("Stationnement — scénario au sol",
                          f"{ppl:g} pl./logt × {hyp.place_m2:g} m² ; sol restant {sol_dispo:.0f} m² "
                          f"→ ≤ {log_max_park:.0f} logts", "plafond au sol",
                          rules.sources.get("stationnement", "Art. 12")))
        steps.append(Step("Stationnement — scénario sous-sol/silo",
                          "parking enterré/silo : le sol n'est plus consommé → borné par le plancher",
                          f"~{floor_lo:.0f}–{floor_hi:.0f} logts", rules.sources.get("stationnement", "Art. 12")))
        sol_lo, sol_hi = min(floor_lo, log_max_park), min(floor_hi, log_max_park)
        hypotheses.append(f"1 place de stationnement supposée {hyp.place_m2:g} m² (au sol restant).")
    elif ppl == EXEMPT:
        regime = "exempt"
        avert.append(f"Stationnement non réglementé pour {rules.code} (exemptée, Art. 12) → "
                     "capacité non bornée par le stationnement.")
    else:
        regime = "non_applique"
        if ppl == A_VERIFIER:
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
    modul.extend(c.libelles)

    sol_lo, sol_hi = sol_lo * facteur, sol_hi * facteur
    sous_lo, sous_hi = sous_lo * facteur, sous_hi * facteur

    rp = f"R+{max(0, niveaux - 1)}"
    logt_moyen = (hyp.logement_m2_bas + hyp.logement_m2_haut) / 2.0
    fourch = {"niveaux": rp, "niveaux_max": niveaux,
              # 3.D — hauteur du gabarit (niveaux × hauteur d'étage), pour l'extrusion 3D.
              "hauteur_m": round(niveaux * hyp.etage_m, 1),
              "hauteur_etage_m": hyp.etage_m,
              # Potentiel résiduel (Lot B) : emprise constructible au sol et emprise bâtie MAX
              # (post-occupation), pour croiser avec le bâti existant.
              "emprise_constructible_m2": round(emprise),
              "emprise_batie_max_m2": round(footprint),
              "surface_plancher_m2": round(sdp),
              # surface habitable VENDABLE (post-rendement, plafond densité, modulation) :
              # base du chiffre d'affaires du bilan promoteur.
              "shab_vendable_m2": round((sous_lo + sous_hi) / 2.0 * logt_moyen),
              "logements_au_sol": _rng(sol_lo, sol_hi),
              "logements_sous_sol": _rng(sous_lo, sous_hi),
              "stationnement_regime": regime}

    if facteur == 0.0:
        return fini(False, f"Non constructible en l'état malgré le zonage ({rp} théorique) — "
                    "contrainte rédhibitoire (voir modulation).", fourch)

    if regime == "borne":
        a, b = fourch["logements_au_sol"]
        cc, d = fourch["logements_sous_sol"]
        verdict = f"{rp} · au sol ~{a}-{b} / sous-sol ~{cc}-{d} logts"
    else:
        a, b = fourch["logements_sous_sol"]
        suffix = " — stationnement non réglementé, capacité non bornée" if regime == "exempt" else ""
        verdict = f"{rp} · ~{a} à {b} logts{suffix}"
    return fini(True, verdict, fourch)
