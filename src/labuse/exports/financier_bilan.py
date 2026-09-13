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

# RECETTE-6 (E2, BLOQUANT) — GARDE DE VRAISEMBLANCE sur les champs À L'UNITÉ (€/m²). Un bilan absurde
# venait d'un PRIX TOTAL saisi dans un champ « €/m² » (ex. 700 000 dans « Prix de vente prévu (€/m²) »
# → CA multiplié par la surface vendable → charge foncière 97 M€, ×160). TESTS-1 lot 1 : les bornes
# vivent dans la SOURCE UNIQUE (faisabilite/engine.py) — un littéral de coût ici est interdit par
# test_hypotheses_source_unique (motif du bug 2100).
from ..faisabilite.engine import (  # noqa: E402 — après les constantes du module
    MAX_COUT_CONSTRUCTION_M2,
    MAX_PRIX_BAILLEUR_M2,
    MAX_PRIX_SORTIE_M2,
)


def _hors_marche(prix_sortie, cout, prix_bailleur) -> dict | None:
    """RECETTE-6 (E2) — le premier champ à l'unité hors bornes de vraisemblance (probable prix TOTAL
    saisi à la place d'un €/m²), ou None si tout est plausible. Point de vérité unique du garde."""
    for val, borne, champ in (
        (prix_sortie, MAX_PRIX_SORTIE_M2, "Prix de vente prévu des logements"),
        (cout, MAX_COUT_CONSTRUCTION_M2, "Coût de construction"),
        (prix_bailleur, MAX_PRIX_BAILLEUR_M2, "Prix de vente au bailleur social"),
    ):
        if val is not None and float(val) > borne:
            # RECETTE-7 (E8) — la raison NE RÉPÈTE PLUS la valeur (le message l'imprime déjà via
            # « … vaut X €/m² : … ») : elle commence directement par le dépassement.
            return {"champ": champ, "valeur": float(val), "borne": borne,
                    "raison": (f"cela dépasse tout prix de marché (borne {borne:,.0f} €/m²) — "
                               "un PRIX TOTAL a probablement été saisi à la place d'un prix au m².").replace(",", " "),
                    "correction": "Corrigez ce champ (un prix AU M², pas un prix total), puis régénérez le document."}
    # RECETTE-10 T5 — garde RELATIONNELLE de vraisemblance (sur le modèle du prix de sortie) : une
    # vente EN BLOC à un bailleur social est TOUJOURS inférieure au prix de vente libre (décote de
    # commercialisation en bloc). Un prix bailleur > prix libre est invraisemblable → hors marché.
    if prix_sortie is not None and prix_bailleur is not None and float(prix_bailleur) > float(prix_sortie):
        return {"champ": "Prix de vente au bailleur social", "valeur": float(prix_bailleur),
                "borne": float(prix_sortie),
                "raison": (f"il dépasse le prix de vente libre ({float(prix_sortie):,.0f} €/m²) — une "
                           "vente EN BLOC à un bailleur social est toujours inférieure au prix du "
                           "marché libre.").replace(",", " "),
                "correction": "Corrigez le prix au bailleur (il doit rester sous le prix de vente "
                              "libre), puis régénérez le document."}
    return None


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
    # RECETTE-10 T3 — la NATURE d'un poste suit ce qu'EST le montant imprimé, pas l'origine de son
    # entrée. Un montant PRODUIT d'une formule affichée par le bloc (coût = plancher × €/m², honoraires
    # = % × coût, VRD = €/m² × terrain, portage, frais d'acquisition…) est un ƒ DÉRIVÉ — même si le
    # taux qui l'alimente est sourcé (le taux est sourcé, le montant ne l'est pas). Seuls la démolition
    # et la dépollution sont des montants forfaitaires SAISIS tels quels par le porteur → `projet`.
    # La taxe d'aménagement est un produit (taux × surface taxable) : `derive` par défaut ; le bloc la
    # requalifie `projet` si le porteur a saisi le montant lui-même (origine=saisi).
    return {
        "construction": {"montant": construction, "nature": "derive", "ht_ttc": "HT"},
        "honoraires_techniques": {"montant": hono, "nature": "derive", "ht_ttc": "HT"},
        "vrd": {"montant": vrd, "nature": "derive", "ht_ttc": "HT"},
        "stationnement": {"montant": stat, "nature": "derive", "ht_ttc": "HT"},
        "demolition": {"montant": _f(h.get("demolition")), "nature": "projet", "ht_ttc": "HT"},
        "depollution": {"montant": _f(h.get("depollution")), "nature": "projet", "ht_ttc": "HT"},
        "aleas": {"montant": aleas, "nature": "derive", "ht_ttc": "HT"},
        "taxe_amenagement": {"montant": _f(h.get("taxe")), "nature": "derive", "ht_ttc": "HT"},
        "redevance_archeologie": {"montant": rap, "nature": "derive", "ht_ttc": "HT"},
        "portage": {"montant": portage, "nature": "derive", "ht_ttc": "HT"},
        "frais_acquisition": {"montant": frais_acq, "nature": "derive", "ht_ttc": "HT"},
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


def calculer_revente(hyp: dict) -> dict:
    """RECETTE-8 W13bis (C3) — le calcul SIMPLE de la revente en l'état (pas de bilan à rebours) :
    marge = prix de revente − prix d'achat − frais d'acquisition − travaux − coût de portage ;
    taux de marge = marge ÷ prix de revente. Pur, déterministe. `hyp` = hypothèses résolues :
    prix_achat, prix_revente, frais_acq_pct, travaux, duree_portage (mois), taux_apport (%/an).
    Le coût de portage = achat × taux × durée/12 (0 si taux ou durée absents — alors la marge est
    un MAXIMUM, drapeau `maximum`). `etablissable=False` tant que achat OU revente manque."""
    achat = _f(hyp.get("prix_achat"))
    revente = _f(hyp.get("prix_revente"))
    frais_pct = _f(hyp.get("frais_acq_pct"))
    travaux = _f(hyp.get("travaux"))
    duree = _f(hyp.get("duree_portage"))
    taux = _f(hyp.get("taux_apport"))
    frais_acq = (achat * frais_pct / 100) if (achat is not None and frais_pct is not None) else None
    portage = (achat * (taux / 100) * (duree / 12)) if (
        achat is not None and taux is not None and duree is not None) else None
    postes = {"prix_achat": achat, "frais_acquisition": frais_acq,
              "travaux": travaux, "portage": portage, "prix_revente": revente}
    if achat is None or revente is None:
        return {"etablissable": False, "postes": postes}
    cout_total = achat + (frais_acq or 0.0) + (travaux or 0.0) + (portage or 0.0)
    marge = revente - cout_total
    return {
        "etablissable": True, "postes": postes,
        "cout_total": round(cout_total, 2), "marge": round(marge, 2),
        "taux_marge_pct": (round(marge / revente * 100, 1) if revente else None),
        # sans coût de portage chiffré, la marge est SURESTIMÉE → dite « maximum » (jamais un faux exact).
        "maximum": portage is None,
    }


def calculer(prog: dict, hyp: dict) -> dict:
    """Le bilan complet. `prog` = {surface_vendable, surface_plancher, surface_terrain, logements}.
    `hyp` = hypothèses résolues (valeur ou None). Rend postes, CA, charge (3 bornes), sensibilité
    3×3, seuil, prix de revient, écart au prix demandé, drapeau `maximum`."""
    h = dict(hyp)
    h.setdefault("taux", TAUX_TVA_DEFAUT)
    cout = _f(h.get("cout"))
    prix_sortie = _f(h.get("prix_sortie"))
    # RECETTE-6 (E2) — garde de vraisemblance AVANT tout calcul : un champ à l'unité hors bornes rend le
    # bilan HORS MARCHÉ (le bloc n'imprime alors aucun verdict, il nomme le champ). On calcule quand même
    # les postes (pour la traçabilité) mais le résultat porte `hors_marche`.
    hors_marche = _hors_marche(prix_sortie, cout, _f(h.get("prix_bailleur")))
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
        "hors_marche": hors_marche,       # RECETTE-6 (E2) — hypothèse hors bornes → pas de verdict
    }
