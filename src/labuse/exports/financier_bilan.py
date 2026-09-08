"""EXPORTS-2 lot 5 — LE MOTEUR DU BILAN DU FINANCIER. Pur (dicts en entrée/sortie, aucune base,
aucun accès réseau) et DÉTERMINISTE : le même programme + les mêmes hypothèses donnent le même
bilan, reproductible à la main au centime (recette lot 5).

Décision Vic 07/09 — le bilan travaille HT : le prix de sortie DVF est TTC, on le ramène HT par
le taux du régime (8,5 % à La Réunion). Chaque poste porte HT ou TTC. Un poste non chiffré n'est
JAMAIS remplacé par un défaut : il vaut None, et le résultat porte alors la mention « maximum »
(les postes non chiffrés ne peuvent que réduire la charge foncière).

Formules (toutes HT sauf mention) :
  CA_HT = surface libre × prix_sortie ÷ (1+taux)  [part libre, prix de sortie TTC → HT]
        + surface sociale × prix bailleur           [part sociale, au prix bailleur]
  construction = surface de plancher × coût de construction
  honoraires   = honoraires% × construction
  VRD          = VRD €/m² × surface de terrain
  stationnement= logements × coût par place
  aléas        = aléas% × construction
  RAP          = 0,68 €/m² × surface de plancher (redevance d'archéologie préventive)
  portage      = (construction+VRD) × taux × durée/12   [ou forfait 3 % du CA si pas de taux]
  frais d'acq. = frais% × prix demandé                  [coût que l'acquéreur porte]
  marge        = marge% × CA_HT
  charge foncière supportable = CA_HT − Σ(postes chiffrés) − marge
  prix de revient = (foncier retenu + Σ postes) ÷ surface vendable
  seuil de rentabilité = charge foncière (le prix d'achat qui atteint la marge visée)
"""
from __future__ import annotations

TAUX_TVA_DEFAUT = 0.085                     # La Réunion, logement neuf (mandat 5.1)
RAP_EUR_M2 = 0.68                           # redevance d'archéologie préventive (RELECTURE §5.2)
PORTAGE_FORFAIT_PCT = 3.0                   # forfait si le client n'a pas saisi de taux
PRIX_SORTIE_VAR = 0.05                      # ±5 % pour la sensibilité au prix de sortie


def _cout_fourchette() -> tuple[float, float]:
    """Fourchette de coût de construction (bas, haut) DÉRIVÉE de la source unique
    (`hypotheses_faisabilite` du YAML — mandat hypothèses bilan, décision Vic 28/07/2026) : plus
    jamais une constante autonome ici (une fourchette dupliquée = re-création du bug 2100)."""
    from ..faisabilite.engine import Hypotheses
    h = Hypotheses.charger()
    return float(h.cout_construction_m2_bas), float(h.cout_construction_m2_haut)


def _f(v):
    """float ou None (poste non chiffré)."""
    return None if v in (None, "") else float(v)


def _somme(postes: dict) -> tuple[float, bool]:
    """Somme des montants chiffrés ; True si AU MOINS un poste est non chiffré (→ « maximum »)."""
    total = 0.0
    manque = False
    for p in postes.values():
        if p["montant"] is None:
            manque = True
        else:
            total += p["montant"]
    return total, manque


def _ca_ht(prog: dict, prix_sortie: float | None, prix_bailleur: float | None,
           part_sociale_pct: float, taux: float) -> tuple[float | None, float]:
    """CA HT total (part libre HT + part sociale au bailleur) et la surface libre (m²)."""
    vend = _f(prog.get("surface_vendable")) or 0.0
    part = max(0.0, min(100.0, part_sociale_pct or 0.0)) / 100.0
    s_sociale, s_libre = vend * part, vend * (1 - part)
    if prix_sortie is None:
        return None, s_libre
    ca = s_libre * prix_sortie / (1 + taux)
    if s_sociale > 0 and prix_bailleur is not None:
        ca += s_sociale * prix_bailleur
    return ca, s_libre


def _postes(prog: dict, h: dict, cout: float | None, ca: float | None) -> dict:
    """Les postes de coût (hors marge) pour un coût de construction et un CA donnés (sert bornes/
    sensibilité). Chaque poste : {montant|None, nature, ht_ttc}."""
    plancher = _f(prog.get("surface_plancher")) or 0.0
    terrain = _f(prog.get("surface_terrain")) or 0.0
    logements = _f(prog.get("logements")) or 0.0
    construction = (plancher * cout) if cout is not None else None
    hono = (construction * h["honoraires_pct"] / 100) if (construction is not None and h.get("honoraires_pct") is not None) else None
    vrd = (terrain * h["vrd_m2"]) if h.get("vrd_m2") is not None else None
    stat = (logements * h["cout_place"]) if h.get("cout_place") is not None else None
    aleas = (construction * h["aleas_pct"] / 100) if (construction is not None and h.get("aleas_pct") is not None) else None
    rap = plancher * RAP_EUR_M2 if plancher else None
    # portage : durée × taux sur (construction + VRD) si le taux est saisi, sinon forfait % du CA
    # (mandat 5.2) ; sans durée ni taux, non chiffré.
    portage = None
    if h.get("duree_portage") is not None:
        if h.get("taux_apport") is not None and construction is not None:
            portage = (construction + (vrd or 0.0)) * (h["taux_apport"] / 100) * (h["duree_portage"] / 12)
        elif ca is not None:
            portage = ca * PORTAGE_FORFAIT_PCT / 100
    frais_acq = (h["prix_demande"] * h["frais_acq_pct"] / 100) if (h.get("prix_demande") is not None and h.get("frais_acq_pct") is not None) else None
    return {
        "construction": {"montant": construction, "nature": "estime", "ht_ttc": "HT"},
        "honoraires_techniques": {"montant": hono, "nature": "projet", "ht_ttc": "HT"},
        "vrd": {"montant": vrd, "nature": "projet", "ht_ttc": "HT"},
        "stationnement": {"montant": stat, "nature": "projet", "ht_ttc": "HT"},
        "demolition": {"montant": _f(h.get("demolition")), "nature": "projet", "ht_ttc": "HT"},
        "depollution": {"montant": _f(h.get("depollution")), "nature": "projet", "ht_ttc": "HT"},
        "aleas": {"montant": aleas, "nature": "projet", "ht_ttc": "HT"},
        "taxe_amenagement": {"montant": _f(h.get("taxe")), "nature": "estime", "ht_ttc": "HT"},
        "redevance_archeologie": {"montant": rap, "nature": "derive", "ht_ttc": "HT"},
        "portage": {"montant": portage, "nature": "projet", "ht_ttc": "HT"},
        "frais_acquisition": {"montant": frais_acq, "nature": "projet", "ht_ttc": "HT"},
    }


def _charge(prog: dict, h: dict, cout: float | None, prix_sortie: float | None) -> float | None:
    """Charge foncière supportable pour un couple (coût, prix de sortie) : CA_HT − Σ postes − marge.
    None si le CA n'est pas calculable."""
    ca, _ = _ca_ht(prog, prix_sortie, _f(h.get("prix_bailleur")), h.get("part_sociale_pct") or 0.0, h["taux"])
    if ca is None:
        return None
    postes = _postes(prog, h, cout, ca)
    total, _ = _somme(postes)
    marge = ca * (h["marge_pct"] / 100) if h.get("marge_pct") is not None else 0.0
    return ca - total - marge


def calculer(prog: dict, hyp: dict) -> dict:
    """Le bilan complet. `prog` = {surface_vendable, surface_plancher, surface_terrain, logements}.
    `hyp` = hypothèses résolues (valeur ou None). Rend postes, CA, charge (3 bornes), sensibilité
    3×3, seuil, prix de revient, écart au prix demandé, drapeau `maximum`."""
    h = dict(hyp)
    h.setdefault("taux", TAUX_TVA_DEFAUT)
    cout = _f(h.get("cout"))
    prix_sortie = _f(h.get("prix_sortie"))
    ca, _ = _ca_ht(prog, prix_sortie, _f(h.get("prix_bailleur")), h.get("part_sociale_pct") or 0.0, h["taux"])
    postes = _postes(prog, h, cout, ca)
    total_postes, manque_poste = _somme(postes)
    marge = ca * (h["marge_pct"] / 100) if (ca is not None and h.get("marge_pct") is not None) else None
    charge_centrale = _charge(prog, h, cout, prix_sortie)

    # 3 bornes : coût haut × sortie bas (basse) · coût bas × sortie haut (haute) · retenue (centrale)
    cb, ch = _cout_fourchette()
    ps_bas = prix_sortie * (1 - PRIX_SORTIE_VAR) if prix_sortie is not None else None
    ps_haut = prix_sortie * (1 + PRIX_SORTIE_VAR) if prix_sortie is not None else None
    charge = {
        "basse": _charge(prog, h, ch, ps_bas),
        "centrale": charge_centrale,
        "haute": _charge(prog, h, cb, ps_haut),
    }
    # sensibilité DOUBLE 3×3 : coût {bas, retenu, haut} × prix de sortie {bas, retenu, haut}
    couts = [("bas", cb), ("retenu", cout), ("haut", ch)]
    sorties = [("bas", ps_bas), ("retenu", prix_sortie), ("haut", ps_haut)]
    sensibilite = [[{"cout": cn, "sortie": sn, "charge": _charge(prog, h, cv, sv)}
                    for sn, sv in sorties] for cn, cv in couts]

    vend = _f(prog.get("surface_vendable"))
    foncier_retenu = _f(h.get("prix_demande")) if h.get("prix_demande") is not None else charge_centrale
    prix_revient = ((foncier_retenu + total_postes) / vend) if (foncier_retenu is not None and vend) else None
    # face au prix demandé
    ecart = None
    marge_residuelle_pct = None
    if h.get("prix_demande") is not None and charge_centrale is not None and ca:
        ecart = charge_centrale - h["prix_demande"]
        # marge résiduelle si on paie le prix demandé : (CA − postes − prix demandé) / CA
        marge_residuelle_pct = 100 * (ca - total_postes - h["prix_demande"]) / ca

    return {
        "ca_ht": ca, "postes": postes, "marge": marge,
        "charge": charge, "seuil_rentabilite": charge_centrale, "prix_revient": prix_revient,
        "sensibilite": sensibilite, "ecart_prix_demande": ecart,
        "marge_residuelle_pct": marge_residuelle_pct,
        "maximum": manque_poste,          # un poste non chiffré → la charge est un maximum
    }
