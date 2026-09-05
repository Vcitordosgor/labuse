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
import re
from dataclasses import dataclass, field, replace

from .plu_rules import A_VERIFIER, EXEMPT, NON_MODELISABLE, ZoneRules

SEUIL_EXIGU_M2 = 5.0  # en deçà, le contour inseté est considéré vidé → "trop exigu"

# hé prudent (~R+2) des zones U/AU des communes NON outillées (config/plu_<commune>.yaml absent).
# SOURCE UNIQUE du défaut générique (M-N P1-13) : partagée par le champ de dataclass ci-dessous ET
# par plu_rules._zone_generique, pour que l'estimation d'une commune sans YAML ne LISE JAMAIS le
# YAML Saint-Paul (emprunt à la commune la mieux calibrée = faux « générique »).
HE_DEFAUT_GENERIQUE_M = 9.0


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
    # VRD / viabilisation de base (€/m² de terrain) — hypothèse par défaut DITE de la calculette
    # (source unique YAML, comme le coût/la marge), jamais un 0 silencieux. La fiche servie garde SA
    # VRD calibrée par secteur (registre bilan_params) ; cette valeur-ci ne pilote QUE les défauts
    # de la calculette/Banquier/Argumentaire (générique, « estimée, à confirmer par devis local »).
    cout_vrd_base_m2: float = 90.0
    dvf_radius_m: float = 1500.0                # rayon de recherche des ventes DVF comparables
    dvf_min_ventes: int = 8                     # en deçà, prix DVF jugé non fiable
    # --- Potentiel résiduel (Lot B) — PLACEHOLDERS ---
    niveaux_bati_existant_defaut: float = 1.0   # niveaux supposés du bâti existant (hauteur BD TOPO non ingérée)
    sous_densite_seuil_pct: float = 40.0        # seuil du taux d'emprise sous lequel = « sous-densité »
    he_defaut_generique_m: float = HE_DEFAUT_GENERIQUE_M   # hé prudent des zones U/AU NON outillées (≈ R+2)
    # --- Prescriptions GPU (Décisions 3.b / 3.c) ---
    pct_lls: float = 0.0              # % de logements aidés (validé Vic : 30 % — Art. 2 règlement PLU)
    prix_m2_lls: float = 0.0          # prix de sortie €/m² des logements aidés (PLACEHOLDER, 0 = non calibré)
    majoration_vrd_pluvial: float = 0.0  # % de majoration du coût (VRD) en zonage eaux pluviales (PLACEHOLDER)
    # Seuils de DÉCLENCHEMENT de la clause de mixité (Art. 2 règlement PLU — SOURCÉS, non placeholder).
    # Clause déclenchée si SDP ≥ seuil OU logements ≥ seuil OU terrain > seuil (logique OU du texte).
    mixite_sdp_seuil_m2: float = 1500.0       # « SDP ≥ 1 500 m² » (bornes 1500/1800 du texte)
    mixite_logements_seuil: float = 20.0      # « programme de 20 logements ou plus »
    mixite_terrain_seuil_m2: float = 6000.0   # « terrain d'habitation de plus de 6 000 m² »
    # --- Provenance D'AFFICHAGE (M-N P1-13, n'altère AUCUN calcul) ---
    # commune servie (traçabilité) et RÉFÉRENCE SOURCÉE des seuils de mixité : renseignée UNIQUEMENT
    # si le YAML de la commune la DÉCLARE explicitement (`mixite_source_ref`, ex. « Art. 2 règlement
    # PLU »). La seule présence des NOMBRES (souvent recopiés de Saint-Paul dans les YAML communaux)
    # ne suffit pas à en faire un Sourcé : None → étiquette « Estimé — seuils par défaut », JAMAIS
    # l'Art. 2 d'une autre commune (un Estimé emprunté présenté en Sourcé est interdit — boussole).
    commune: str | None = None
    mixite_source_ref: str | None = None
    # M94 — source de la conversion place→m² : renseignée UNIQUEMENT si le YAML de la commune la
    # DÉCLARE au règlement (ex. Cilaos « 1 place = 25 m² »). Sinon place_m2 (=25) est de la MODÉLISATION
    # (Estimé), jamais une norme locale déguisée. Voyage avec la valeur (marquage M-PLU-REF-B).
    place_m2_source_ref: str | None = None

    @classmethod
    def charger(cls, commune: str | None = None) -> "Hypotheses":
        """Hypothèses depuis la section `hypotheses_faisabilite` du YAML PLU de la COMMUNE (config
        éditable sans toucher au code).

        M-N P1-13 — `commune` est propagée par les appelants (paramètre optionnel, back-compat) :
          - `commune=None` → Saint-Paul (comportement historique : pilote & tests) ;
          - commune OUTILLÉE (config/plu_<slug>.yaml) → SA section `hypotheses_faisabilite` ;
          - commune SANS YAML → DÉFAUTS DU DATACLASS, JAMAIS Saint-Paul (plus d'emprunt silencieux
            des seuils/coûts de la commune la mieux calibrée).
        On mémorise la provenance des seuils de mixité (`mixite_source`) pour l'affichage."""
        from .plu_rules import _hypotheses_faisabilite, _hypotheses_ile
        h = _hypotheses_faisabilite(commune)
        out = cls()
        out.commune = commune
        # M-PLU-REF — BASE île-générique (source neutre `hypotheses_ile.yaml`), PUIS override commune
        # (commune-spécifique + toute valeur calibrée par la commune). Valeurs identiques aux défauts →
        # AUCUN calcul ne bouge (correction de chemin, golden = baseline).
        for k, v in {**_hypotheses_ile(), **h}.items():
            if hasattr(out, k) and isinstance(v, (int, float)):
                setattr(out, k, float(v))
        # Source AFFICHÉE des seuils de mixité : « Art. 2 » SEULEMENT si le YAML de la commune la
        # DÉCLARE (mixite_source_ref) — des nombres recopiés de Saint-Paul ne sont pas un Sourcé.
        _ref = h.get("mixite_source_ref")
        out.mixite_source_ref = _ref.strip() if isinstance(_ref, str) and _ref.strip() else None
        # M94 — idem pour la conversion place→m² : Sourcé SEULEMENT si le règlement de la commune le dit.
        _pref = h.get("place_m2_source_ref")
        out.place_m2_source_ref = _pref.strip() if isinstance(_pref, str) and _pref.strip() else None
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
    # Cause STRUCTURÉE de non-constructibilité (None si constructible). Deux familles :
    #   A « zone fermée au règlement » : {"zone_transition", "habitat_interdit"} — réversible
    #     (une 2AU peut être ouverte par modification du PLU).
    #   B « parcelle inconstructible » : {"terrain_exigu", "redhibitoire", "hauteur_indispo"} —
    #     contrainte physique/donnée, pas un interdit de zone.
    cause: str | None = None


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
        # M73 C2 : ne plus affirmer « commune non outillée » (la calibration couvre 23/24 communes) —
        # ici c'est la ZONE qui n'est pas calibrée finement. Aucun chemin de config côté client.
        avert.append("Capacité ESTIMÉE — zone non calibrée finement : hypothèses génériques "
                     "prudentes (reculs et hauteurs par défaut).")

    def fini(constructible, verdict, fourchette, cause=None):
        return Faisabilite(rules.code, rules.via_renvoi, constructible, verdict,
                           steps, hypotheses, avert, modul, fourchette, _BANDEAU,
                           calibree=rules.calibree, cause=cause)

    if rules.via_renvoi:
        steps.append(Step("Zone (renvoi AU→U)", rules.via_renvoi, rules.code, "Règlement, caractère de zone"))

    if not rules.constructible_neuf:
        # M58-P1 (Q2) : NE PLUS hardcoder « secteur de transition (AU*st), H max 4 m » pour TOUT
        # cas non constructible — c'était un faux positif (affiché même en zone A/N). Le verdict
        # cite la ZONE RÉELLE lue sur la parcelle (rules.code), sans inventer de code de secteur
        # ni de hauteur. Une valeur servie ne s'invente pas.
        return fini(False, f"Construction neuve non autorisée en zone {rules.code}.",
                    {"logements_au_sol": (0, 0), "logements_sous_sol": (0, 0)},
                    cause="zone_transition")

    # M6 2b (A-03) : zone à vocation économique — l'habitat y est interdit au règlement
    # (exceptions résiduelles type logement de gardiennage/fonction, hors cible produit).
    if rules.habitat == "interdit":
        return fini(False, "Habitat interdit au règlement — zone à vocation économique/"
                    "activités (seules exceptions : gardiennage/logement de fonction). "
                    "Aucune capacité logement calculée.",
                    {"logements_au_sol": (0, 0), "logements_sous_sol": (0, 0)},
                    cause="habitat_interdit")

    # EXPORTS-1 lot 6 — les références des YAML calibrés portent des marqueurs internes
    # (« (doctrine a) »…) : purgés AU SERVICE, jamais dans les données de calibration.
    _marqueurs_internes = re.compile(r"\s*\((?:doctrine|deja_bati|reglt)[^)]*\)")
    rules = replace(rules, sources={k: _marqueurs_internes.sub("", v) if isinstance(v, str) else v
                                    for k, v in (rules.sources or {}).items()})

    # reculs (avec hypothèse prudente si non calibrés) — EXPORTS-1 (3.4) : reculs NOMMÉS,
    # plus jamais le jargon interne « à_vérifier » dans un texte servi.
    if _is_num(rules.recul_voirie_m):
        recul_v, rv_src = float(rules.recul_voirie_m), rules.sources.get("recul_voirie", "Art. 6")
    else:
        recul_v, rv_src = hyp.recul_voirie_defaut_m, "Art. 6 (non calibré → hypothèse prudente)"
        avert.append(f"Recul voirie non calibré pour la zone {rules.code} → "
                     f"hypothèse prudente {recul_v:g} m.")
    if _is_num(rules.recul_limites_sep_m):
        recul_l, rl_src = float(rules.recul_limites_sep_m), rules.sources.get("recul_limites", "Art. 7")
    else:
        recul_l, rl_src = hyp.recul_limites_defaut_m, "Art. 7 (non calibré → hypothèse prudente)"
        avert.append(f"Recul limites séparatives non calibré pour la zone {rules.code} → "
                     f"hypothèse prudente {recul_l:g} m.")

    # ---- Emprise constructible au sol ----
    if emprise_geo is not None:
        emprise, recul_used = emprise_geo
        if emprise < SEUIL_EXIGU_M2:
            steps.append(Step("Emprise au sol — reculs (géométrie réelle)",
                              f"contour cadastral réel inseté du recul limites séparatives ({recul_used:g} m)",
                              "≈ 0 m² (contour vidé)", f"{rl_src}"))
            return fini(False, f"Terrain trop exigu compte tenu des reculs ({recul_used:g} m) — "
                        "non constructible en l'état (le contour inseté se vide).",
                        {"logements_au_sol": (0, 0), "logements_sous_sol": (0, 0)},
                        cause="terrain_exigu")
        steps.append(Step("Emprise au sol — reculs (géométrie réelle)",
                          f"contour cadastral réel inseté du recul limites séparatives ({recul_used:g} m)",
                          f"~{emprise:.0f} m²", f"{rl_src} (séparatif) ; recul voirie en sus"))
        hypotheses.append("Emprise = contour cadastral réel inseté du recul limites séparatives "
                          "(géométrie réelle, projection métrique).")
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
        avert.append(f"% pleine terre non calibré pour la zone {rules.code} → non appliqué (Art. 13).")
    emprise = max(0.0, emprise)

    # ---- Niveaux (hé prioritaire) ----
    he_src = rules.sources.get("hauteur", "Art. 10")
    if _is_num(rules.he_m):
        niveaux = int(float(rules.he_m) // hyp.etage_m)
        steps.append(Step("Niveaux constructibles",
                          f"hauteur d'égout retenue {rules.he_m:g} m ÷ {hyp.etage_m:g} m/niveau = {niveaux} niveaux",
                          f"R+{max(0, niveaux - 1)}", he_src))
    elif _is_num(rules.hf_m):
        niveaux = max(1, int((float(rules.hf_m) - hyp.etage_m) // hyp.etage_m))
        avert.append(f"Hauteur égout (hé) non précisée pour {rules.code} : niveaux estimés "
                     f"depuis hf {rules.hf_m:g} m (prudent).")
        steps.append(Step("Niveaux constructibles",
                          f"hauteur d'égout non précisée → (hauteur faîtage {rules.hf_m:g}−{hyp.etage_m:g}) ÷ {hyp.etage_m:g} = {niveaux}",
                          f"R+{max(0, niveaux - 1)}", he_src))
    else:
        return fini(False, "Hauteur de zone non calibrée — capacité non calculable.",
                    {"logements_au_sol": (0, 0), "logements_sous_sol": (0, 0)},
                    cause="hauteur_indispo")
    hypotheses.append(f"Hauteur d'étage supposée {hyp.etage_m:g} m ; niveaux comptés sur hé (égout), pas hf.")

    # ---- Emprise BÂTIE (on ne remplit pas toute l'enveloppe) ----
    footprint = emprise * hyp.coef_occupation
    steps.append(Step("Emprise bâtie (occupation du gabarit)",
                      f"{emprise:.0f} m² × {hyp.coef_occupation:.0%} (espaces entre bâtiments, accès…)",
                      f"~{footprint:.0f} m²", "hypothèse occupation"))
    hypotheses.append(f"Coefficient d'occupation du gabarit supposé {hyp.coef_occupation:.0%} "
                      "(on ne bâtit pas 100 % de l'emprise constructible).")
    # M-PLU-REF-B — MARQUAGE ZONE-AWARE et VRAI (mesuré AUDIT_PLU_REF_B : emprise chiffrée 64 %, non
    # réglementée 35 %, densité réglementée NULLE PART). `coef_occupation` est un facteur de MODÉLISATION
    # (occupation du gabarit), PAS l'emprise réglementaire (`rules.emprise_sol_pct`, consommée l.255 si
    # chiffrée). On dit donc le SILENCE du règlement quand l'emprise n'est pas chiffrée, jamais une dette
    # « non calibrée » (le marquage commune-uniforme M-PLU-REF sonnait à tort même sur une zone chiffrée).
    if not _is_num(rules.emprise_sol_pct):
        _com = hyp.commune or "cette commune"
        hypotheses.append(f"Emprise au sol non réglementée par le PLU de {_com} (silence du règlement) : "
                          f"occupation du gabarit ~{hyp.coef_occupation:.0%} posée par hypothèse de "
                          "modélisation ; la capacité est bornée par les reculs, la hauteur et la pleine terre.")

    # ---- Surface de plancher BRUTE puis HABITABLE (rendement) ----
    sdp = footprint * niveaux
    steps.append(Step("Surface de plancher brute", f"{footprint:.0f} m² × {niveaux} niveaux",
                      f"~{sdp:.0f} m²", "dérivé occupation×hauteur"))
    shab = sdp * hyp.coef_rendement
    steps.append(Step("Surface habitable (rendement)",
                      f"{sdp:.0f} m² × {hyp.coef_rendement:.0%} (murs, communs, circulations, locaux techniques déduits)",
                      f"~{shab:.0f} m²", "hypothèse rendement"))
    hypotheses.append(f"Coefficient de rendement SDP→habitable supposé {hyp.coef_rendement:.0%}.")

    # M128-5-§1 : le VENDABLE suit un chemin CENTRAL unique (habitable ÷ taille MOYENNE de logement),
    # jamais la moyenne de la fourchette de COMPTES (shab/haut … shab/bas), qui surestimait le vendable
    # de ~1 % par inégalité arithmético-harmonique — l'aller-retour compte↔surface ne se compensait pas.
    # La fourchette 65–80 m²/logt reste AFFICHÉE (étapes ci-dessous) mais ne pilote plus le vendable :
    # sans plafond, vendable = habitable PAR CONSTRUCTION (aucun min() contre le gabarit nécessaire).
    logt_moyen = (hyp.logement_m2_bas + hyp.logement_m2_haut) / 2.0
    floor_central = shab / logt_moyen
    floor_lo, floor_hi = shab / hyp.logement_m2_haut, shab / hyp.logement_m2_bas
    # EXPORTS-1 (3.3) : l'étape « avant plafond ~8 à 10 » n'est PLUS imprimée comme fourchette —
    # elle se lisait comme LE résultat à côté du « 7 à 9 » retenu (audit A3). Seule la fourchette
    # APRÈS plafond de densité et stationnement sort ; l'hypothèse de surface reste dite.
    hypotheses.append(f"Surface moyenne par logement supposée {hyp.logement_m2_bas:g}–{hyp.logement_m2_haut:g} m².")

    # ---- Plafond de DENSITÉ (filet de sécurité, remplace le COS) ----
    # M58-P1 (Q1) : CALCUL INCHANGÉ (le cap = min(fourchette, densite_cap), assigné plus bas). Seul
    # l'AFFICHAGE change : l'étape « après plafond » cite la fourchette RETENUE (capée), pas seulement
    # le seuil « ≤ N » — pour lever l'apparente contradiction avant/après plafond.
    surface_ha = surface_m2 / 10000.0
    cap_logts_ha = hyp.densite_logts_ha_par_niveau * niveaux
    densite_cap = surface_ha * cap_logts_ha
    capped_lo, capped_hi = min(floor_lo, densite_cap), min(floor_hi, densite_cap)
    capped_central = min(floor_central, densite_cap)     # M128-5-§1 : le central subit le MÊME plafond
    steps.append(Step(f"Logements — après plafond de densité (≤ {densite_cap:.0f} logts)",
                      f"{surface_ha:.2f} ha × {cap_logts_ha:.0f} logts/ha "
                      f"({hyp.densite_logts_ha_par_niveau:g}/niveau × {niveaux})",
                      f"~{capped_lo:.0f} à {capped_hi:.0f}", "hypothèse densité (ex-COS)"))
    hypotheses.append(f"Plafond de densité {hyp.densite_logts_ha_par_niveau:g} logts/ha par niveau : "
                      "filet de MODÉLISATION (ex-COS) — le PLU ne fixe aucune densité (mesuré : aucune "
                      "commune, aucune zone), la capacité reste bornée par reculs, hauteur et pleine terre.")
    if densite_cap < floor_hi:
        # M144 Lot 5.3 — séparateur unifié « à » (comme §3 « Ce que le terrain permet ») : l'écart
        # 121/122 n'est pas une divergence d'arrondi mais le PLAFOND (pré-cap → borné), dit explicitement.
        modul.append(f"Plafond de densité {cap_logts_ha:.0f} logts/ha appliqué : le calcul détaillé "
                     f"donnait ~{math.floor(floor_lo)} à {math.ceil(floor_hi)} → borné à "
                     f"~{round(densite_cap)} logts (enveloppe théorique trop optimiste).")
    floor_lo, floor_hi = capped_lo, capped_hi
    floor_central = capped_central

    # ---- Stationnement : 2 scénarios ----
    ppl = rules.places_par_logement()
    sous_lo, sous_hi = floor_lo, floor_hi          # sous-sol/silo : non mangé au sol
    sous_central = floor_central
    sol_lo, sol_hi = floor_lo, floor_hi
    sol_central = floor_central                    # M144 Lot 1 — le central du scénario RETENU (au sol)
    if _is_num(ppl) and ppl > 0:
        regime = "borne"
        sol_dispo = max(0.0, surface_m2 - footprint - pt_area)
        log_max_park = sol_dispo / (ppl * hyp.place_m2)
        steps.append(Step("Stationnement — scénario au sol",
                          f"sol restant = terrain {surface_m2:.0f} − emprise bâtie {footprint:.0f} "
                          f"− pleine terre {pt_area:.0f} = {sol_dispo:.0f} m² ; "
                          f"{ppl:g} pl./logt × {hyp.place_m2:g} m² → ≤ {log_max_park:.0f} logts",
                          "plafond au sol", rules.sources.get("stationnement", "Art. 12")))
        steps.append(Step("Stationnement — scénario sous-sol/silo",
                          "parking enterré/silo : le sol n'est plus consommé → borné par le plancher",
                          f"~{floor_lo:.0f}–{floor_hi:.0f} logts", rules.sources.get("stationnement", "Art. 12")))
        sol_lo, sol_hi = min(floor_lo, log_max_park), min(floor_hi, log_max_park)
        sol_central = min(floor_central, log_max_park)   # M144 Lot 1 — le central plafonné au sol
        if hyp.place_m2_source_ref:
            hypotheses.append(f"1 place de stationnement = {hyp.place_m2:g} m² (Sourcé — {hyp.place_m2_source_ref}).")
        else:
            hypotheses.append(f"1 place de stationnement supposée {hyp.place_m2:g} m² au sol (Estimé — "
                              "modélisation, non réglementée pour cette commune).")
    elif ppl == EXEMPT:
        regime = "exempt"
        avert.append(f"Stationnement non réglementé pour {rules.code} (exemptée, Art. 12) → "
                     "capacité non bornée par le stationnement.")
    else:
        regime = "non_applique"
        if ppl == A_VERIFIER:
            avert.append(f"Stationnement non calibré pour la zone {rules.code} → garde-fou non appliqué (Art. 12).")
        elif ppl == NON_MODELISABLE:
            # M94 — norme PRÉSENTE mais pas par logement (par m² SDP / chambre / %SHON) : on le DIT,
            # jamais un défaut déguisé en local. Distinct de « absente » ci-dessous.
            avert.append(f"Norme de stationnement présente mais NON MODÉLISABLE pour {rules.code} "
                         "(exprimée par m² de plancher, par chambre ou en %, pas par logement — Art. 12) : "
                         "capacité au sol non bornée, aucune valeur inventée.")
        else:  # ppl is None → norme non extraite / absente pour cette zone
            # M94 — ne plus rester SILENCIEUX : la norme est absente de l'extraction, on le signale.
            avert.append(f"Norme de stationnement non renseignée pour {rules.code} "
                         "(absente du règlement extrait) → garde-fou au sol non appliqué (Art. 12).")

    # ---- Modulation réunionnaise ----
    facteur = 1.0
    if c.agricole_sar:
        facteur = 0.0
        modul.append("Parcelle déclarée agricole (RPG) — usage agricole à confirmer au PLU (indicatif, n'emporte pas d'interdiction automatique).")
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
    sol_central = sol_central * facteur            # M144 Lot 1 — le central retenu subit la MÊME modulation
    sous_lo, sous_hi = sous_lo * facteur, sous_hi * facteur
    sous_central = sous_central * facteur          # M128-5-§1 : le central subit la MÊME modulation

    # M128-2-I1 : ligne FINALE de logements = EXACTEMENT la fourchette portée au bandeau et au bilan
    # (plafond de densité ∩ stationnement au sol, puis modulation, arrondie plancher/plafond comme
    # `_rng`). Sans elle, le bandeau « 2 à 4 » ne se déduisait d'aucune ligne (le tableau montrait ~3,
    # arrondi au plus proche — deux conventions d'arrondi pour un même nombre).
    _fin_lo, _fin_hi = _rng(sol_lo, sol_hi)
    _mod_note = " (après modulation réunionnaise)" if facteur < 1.0 else ""
    steps.append(Step("Logements retenus au sol",
                      f"plafond de densité ∩ stationnement au sol{_mod_note}",
                      f"~{_fin_lo} à {_fin_hi}", "dérivé"))

    rp = f"R+{max(0, niveaux - 1)}"     # logt_moyen défini plus haut (chemin central du vendable, §1)
    fourch = {"niveaux": rp, "niveaux_max": niveaux,
              # 3.D — hauteur du gabarit (niveaux × hauteur d'étage), pour l'extrusion 3D.
              "hauteur_m": round(niveaux * hyp.etage_m, 1),
              "hauteur_etage_m": hyp.etage_m,
              # Potentiel résiduel (Lot B) : emprise constructible au sol et emprise bâtie MAX
              # (post-occupation), pour croiser avec le bâti existant.
              "emprise_constructible_m2": round(emprise),
              "emprise_batie_max_m2": round(footprint),
              "surface_plancher_m2": round(sdp),
              # surface habitable VENDABLE — base du CA du bilan promoteur. M144 Lot 1 : le vendable
              # est celui du scénario RETENU (au sol, `sol_central` = plafond densité ∩ stationnement au
              # sol, modulé) — le MÊME scénario que « Logements retenus au sol ». Le bilan ne chiffre plus
              # le silo optimiste (`sous_central`) sans en payer le parking enterré : une seule source de
              # scénario, faisabilité et bilan alignés (corrige le mélange encaissé sans son coût).
              "shab_vendable_m2": round(sol_central * logt_moyen),
              # vendable du scénario SILO (parking en ouvrage) — sert la MENTION de prose du bilan
              # (« porterait la surface vendable à ~X m² »), jamais chiffré sans son coût (doctrine).
              "shab_vendable_silo_m2": round(sous_central * logt_moyen),
              "logements_au_sol": _rng(sol_lo, sol_hi),
              "logements_sous_sol": _rng(sous_lo, sous_hi),
              "stationnement_regime": regime}

    if facteur == 0.0:
        return fini(False, f"Non constructible en l'état malgré le zonage ({rp} théorique) — "
                    "contrainte rédhibitoire (voir modulation).", fourch,
                    cause="redhibitoire")

    if regime == "borne":
        a, b = fourch["logements_au_sol"]
        cc, d = fourch["logements_sous_sol"]
        verdict = f"{rp} · au sol ~{a}-{b} / sous-sol ~{cc}-{d} logts"
    else:
        a, b = fourch["logements_sous_sol"]
        suffix = " — stationnement non réglementé, capacité non bornée" if regime == "exempt" else ""
        verdict = f"{rp} · ~{a} à {b} logts{suffix}"
    return fini(True, verdict, fourch)
