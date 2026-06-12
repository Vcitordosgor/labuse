"""Bilan promoteur (PARTIE 1) — potentiel économique d'une parcelle.

Prix de sortie = ventes DVF réelles, avec une méthode FIABILISÉE (mission « prix honnête ») :
  - PRIORITÉ PAR TYPE : appartements (comparable d'un collectif neuf) ; repli « appart+maison »
    seulement si trop peu d'appartements, signalé. (VEFA exclue : DVF 974 sans surface bâtie.)
  - RAYON ADAPTATIF : 500 m → 1000 m → 1500 m → commune, on prend le plus serré qui a assez de ventes.
  - ABERRANTS exclus (Tukey IQR + bornes de bon sens), nombre et raison retournés.
  - RÉCENCE : si les ventes sont anciennes → prix « fragile » (jamais « fiable »).
  - INDICE DE FIABILITÉ : fiable / fragile / insuffisant (n, récence, dispersion, type, rayon).
  - DÉDOUBLONNAGE des mutations multi-parcelles.

CA = surface vendable × prix ; charge foncière à rebours = CA−construction−marge−frais.
Si le prix est « fragile » → simulation prudente, montants arrondis, avertissement visible.
Si « insuffisant » → pas de bilan chiffré (on n'invente pas de prix). Cascade/scoring intacts.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from .engine import Hypotheses, Step

_BANDEAU = ("Estimation économique indicative (DVF public + hypothèses) — "
            "ne remplace pas un bilan promoteur professionnel.")
ANNEE_REF = date.today().year


@dataclass
class Bilan:
    fiable: bool
    fiabilite: str                 # "fiable" | "fragile" | "insuffisant"
    verdict: str
    prix_dvf: dict | None
    ca: dict | None
    charge_fonciere: dict | None
    steps: list[Step] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)
    bandeau: str = _BANDEAU
    # Paramètres bruts pour le recalcul instantané côté fiche (mixité sociale, Décision 3.b).
    calc: dict | None = None


def _eur(x: float) -> str:
    ax = abs(x)
    if ax >= 1_000_000:
        return f"{x / 1_000_000:.1f} M€"
    if ax >= 1_000:
        return f"{x / 1_000:.0f} k€"
    return f"{x:.0f} €"


def _quartiles(xs: list[float]) -> tuple[float, float, float]:
    xs = sorted(xs)
    if len(xs) >= 4:
        q1, _m, q3 = statistics.quantiles(xs, n=4)
        return q1, statistics.median(xs), q3
    return (xs[0], statistics.median(xs), xs[-1]) if xs else (0.0, 0.0, 0.0)


def _trim_aberrants(sales: list[dict]) -> tuple[list[dict], int]:
    """Exclut les €/m² aberrants : Tukey (Q1−1,5·IQR ; Q3+1,5·IQR) borné au bon sens
    réunionnais [1000 ; 12000] €/m² — sous 1 000 €/m² bâti, c'est quasi toujours un
    artefact DVF (lot annexe, vente familiale), qui entamait la confiance d'un
    promoteur dans un échantillon dit « fiable » (audit J6). Retourne (gardées, exclues)."""
    prices = [s["prix"] for s in sales]
    if len(prices) < 4:
        return sales, 0
    q1, _m, q3 = _quartiles(prices)
    iqr = q3 - q1
    lo = max(q1 - 1.5 * iqr, 1000.0)
    hi = min(q3 + 1.5 * iqr, 12000.0)
    kept = [s for s in sales if lo <= s["prix"] <= hi]
    return kept, len(sales) - len(kept)


def _fiabilite(kept: list[dict], type_label: str, commune_fallback: bool, min_n: int) -> tuple[str, list[str]]:
    n = len(kept)
    if n < min_n:
        return "insuffisant", [f"seulement {n} vente(s) comparable(s) (< {min_n})"]
    annee_max = max(s["annee"] for s in kept)
    q1, _m, q3 = _quartiles([s["prix"] for s in kept])
    raisons: list[str] = []
    niveau = "fiable"
    age = ANNEE_REF - annee_max
    if age > 3:
        niveau = "fragile"
        raisons.append(f"ventes anciennes (la plus récente : {annee_max}, il y a {age} ans)")
    disp = (q3 / q1) if q1 else 99.0
    if disp > 2.0:
        niveau = "fragile"
        raisons.append(f"forte dispersion des prix (Q3/Q1 = {disp:.1f})")
    if "mixte" in type_label:
        niveau = "fragile"
        raisons.append("appartements insuffisants → repli appartements + maisons (comparable imparfait)")
    if commune_fallback:
        niveau = "fragile"
        raisons.append("rayon élargi à la commune (peu de ventes proches) → prix lissé")
    return niveau, raisons


def _comparables(kept: list[dict], min_n: int, fiabilite: str) -> dict:
    """Décompose le comparable RETENU en neuf (VEFA) vs ancien — pure transparence, sans
    toucher au prix retenu. N'invente aucun écart : une médiane n'est donnée que si son
    sous-échantillon atteint min_n ventes, et l'écart n'est « exploitable » que si les DEUX
    sous-échantillons l'atteignent. Schéma stable (clés toujours présentes) pour API/exports."""
    vefa = [s["prix"] for s in kept if s.get("vefa")]
    ancien = [s["prix"] for s in kept if not s.get("vefa")]
    med_v = round(statistics.median(vefa)) if len(vefa) >= min_n else None
    med_a = round(statistics.median(ancien)) if len(ancien) >= min_n else None
    ecart = round(100 * (med_v / med_a - 1)) if (med_v and med_a) else None
    if not vefa:
        note = "aucune vente VEFA dans le comparable retenu (prix = ancien)"
    elif len(vefa) < min_n:
        note = f"VEFA insuffisant pour comparaison fiable ({len(vefa)} vente(s) < {min_n})"
    elif len(ancien) < min_n:
        note = f"ancien insuffisant pour comparaison fiable ({len(ancien)} vente(s) < {min_n})"
    else:
        note = None
    return {"n_ancien": len(ancien), "mediane_ancien": med_a,
            "n_vefa": len(vefa), "mediane_vefa": med_v,
            "ecart_vefa_ancien_pct": ecart, "exploitable": ecart is not None,
            "note": note, "fiabilite_prix": fiabilite}


def sector_price(db: Session, parcel_id: int, hyp: Hypotheses) -> dict:
    """Prix de sortie €/m² HABITABLE, fiabilisé (type prioritaire, rayon adaptatif, aberrants
    exclus, récence, indice de fiabilité)."""
    rows = db.execute(text(
        "SELECT d.mutation_id AS mid, d.valeur_fonciere AS val, d.surface_reelle_bati AS surf, "
        "  d.valeur_fonciere / d.surface_reelle_bati AS prix, "
        "  CASE WHEN d.type_local ILIKE '%APPARTEMENT%' THEN 'appartement' ELSE 'maison' END AS cat, "
        "  (d.nature_mutation ILIKE '%futur%') AS vefa, "
        "  extract(year FROM d.date_mutation)::int AS annee, "
        "  round(ST_Distance(d.geom::geography, p.centroid::geography)) AS dist "
        "FROM dvf_mutations d, parcels p "
        "WHERE p.id = :pid AND d.commune = p.commune AND d.surface_reelle_bati >= 20 "
        "  AND d.valeur_fonciere > 20000 AND d.nature_mutation ILIKE '%vente%' "
        "  AND d.type_local ILIKE ANY(ARRAY['%APPARTEMENT%','%MAISON%'])"),
        {"pid": parcel_id}).mappings().all()

    # Dédoublonnage par MUTATION RÉELLE (id_mutation DVF). geo-dvf fournit un identifiant
    # fiable : une mutation = une vente. On ne fusionne donc PAS deux ventes identiques
    # mais distinctes (fréquent en VEFA : lots jumeaux au même prix) — l'ancien dédoublonnage
    # (valeur+surface+année), hérité du flux ODS multi-parcelles, les écrasait à tort.
    seen: dict = {}
    sales: list[dict] = []
    for r in rows:
        key = r["mid"] if r["mid"] else (float(r["val"]), float(r["surf"]), int(r["annee"]))
        if key in seen:
            seen[key]["dist"] = min(seen[key]["dist"], float(r["dist"]))
            continue
        d = {"prix": float(r["prix"]), "cat": r["cat"], "annee": int(r["annee"]),
             "dist": float(r["dist"]), "vefa": bool(r["vefa"])}
        seen[key] = d
        sales.append(d)
    n_dup = len(rows) - len(sales)
    min_n = hyp.dvf_min_ventes

    # Priorité : appartement (rayon croissant) → mixte (rayon croissant) → commune.
    plans = ([("appartement", {"appartement"}, r, False) for r in (500.0, 1000.0, 1500.0)]
             + [("mixte (appart+maison)", {"appartement", "maison"}, r, False) for r in (500.0, 1000.0, 1500.0)]
             + [("appartement", {"appartement"}, 1500.0, True),
                ("mixte (appart+maison)", {"appartement", "maison"}, 1500.0, True)])
    chosen = None
    for label, cats, r, commune in plans:
        sub = [s for s in sales if s["cat"] in cats and (commune or s["dist"] <= r)]
        kept, nex = _trim_aberrants(sub)
        if len(kept) >= min_n:
            chosen = (label, kept, nex, r, commune)
            break
    if chosen is None:
        kept, nex = _trim_aberrants(sales)
        chosen = ("mixte (appart+maison)", kept, nex, 1500.0, True)

    label, kept, nex, radius, commune = chosen
    niveau, raisons = _fiabilite(kept, label, commune, min_n)
    base = {"type_prix": label, "n": len(kept), "n_exclus": nex, "n_doublons": n_dup,
            "radius_m": radius, "commune_fallback": commune,
            "fiabilite": niveau, "fiabilite_raisons": raisons}
    if not kept:
        return {**base, "fiable": False, "fiabilite": "insuffisant"}
    prices = [s["prix"] for s in kept]
    annees = [s["annee"] for s in kept]
    pct_appt = round(100 * sum(1 for s in kept if s["cat"] == "appartement") / len(kept))
    q1, med, q3 = _quartiles(prices)
    return {**base, "fiable": niveau != "insuffisant", "pct_appartement": pct_appt,
            "periode": [min(annees), max(annees)],
            "q1": round(q1), "median": round(med), "q3": round(q3),
            "min": round(min(prices)), "max": round(max(prices)),
            "comparables": _comparables(kept, min_n, niveau)}


def compute_bilan(shab_vendable_m2: float, surface_terrain_m2: float,
                  prix: dict, hyp: Hypotheses, contexte_eco: dict | None = None) -> Bilan:
    """Cœur pur (testable). Protège le bilan selon la fiabilité du prix.

    `contexte_eco` (Décisions 3.b/3.c) : {"mixite": bool, "mixite_libelle", "pluvial": bool,
    "pluvial_libelle"}. En secteur de mixité sociale, si `pct_lls` ET `prix_m2_lls` sont
    calibrés (> 0), le CA est PONDÉRÉ : CA = SDP_vendable × [(1−pct_lls)×prix_DVF +
    pct_lls×prix_m2_lls] ; sinon avertissement PLACEHOLDER, CA inchangé. En zonage eaux
    pluviales, `majoration_vrd_pluvial` (%) majore le coût de construction (0 = neutre)."""
    niveau = prix.get("fiabilite", "insuffisant")
    raisons = prix.get("fiabilite_raisons", [])

    if niveau == "insuffisant" or not prix.get("fiable"):
        return Bilan(False, "insuffisant",
                     f"Prix de sortie indisponible — échantillon DVF insuffisant "
                     f"({prix.get('n', 0)} vente(s) comparable(s)) : pas de bilan chiffré "
                     "(on n'invente pas de prix).",
                     prix, None, None, avertissements=raisons)
    if shab_vendable_m2 <= 0:
        return Bilan(False, "insuffisant", "Surface vendable nulle — pas de bilan.", prix, None, None)

    fragile = niveau == "fragile"
    q1, med, q3 = prix["q1"], prix["median"], prix["q3"]
    surf = shab_vendable_m2
    lieu = "commune entière" if prix.get("commune_fallback") else f"{prix['radius_m']:.0f} m"
    steps: list[Step] = []
    hypotheses: list[str] = []
    avert: list[str] = []

    steps.append(Step("Surface habitable vendable",
                      "issue de la faisabilité (post-rendement, plafond, modulation)",
                      f"~{surf:.0f} m²", "faisabilité"))
    detail = (f"{prix['type_prix']} · {prix['n']} ventes ({prix['periode'][0]}-{prix['periode'][1]}) "
              f"dans {lieu}"
              + (f" · {prix['n_exclus']} aberrant(s) exclu(s)" if prix["n_exclus"] else "")
              + (f" · {prix['n_doublons']} doublon(s) écarté(s)" if prix.get("n_doublons") else ""))
    steps.append(Step("Prix de vente (DVF secteur)", detail,
                      f"{q1}–{q3} €/m² (médiane {med} ; min {prix['min']} / max {prix['max']})",
                      f"DVF Région ODS · fiabilité {niveau}"))

    eco = contexte_eco or {}
    mixite, pluvial = bool(eco.get("mixite")), bool(eco.get("pluvial"))
    p_lls = min(1.0, max(0.0, float(hyp.pct_lls) / 100.0))
    pondere = mixite and p_lls > 0 and float(hyp.prix_m2_lls) > 0
    # CA pondéré mixité sociale (Décision 3.b) : part LLS vendue à prix_m2_lls.
    _px = (lambda x: (1.0 - p_lls) * float(x) + p_lls * float(hyp.prix_m2_lls)) if pondere \
        else (lambda x: float(x))
    ca_bas, ca_cen, ca_haut = surf * _px(q1), surf * _px(med), surf * _px(q3)
    if pondere:
        steps.append(Step("CA pondéré — secteur de mixité sociale",
                          f"prix mixé = (1−{p_lls:.0%})×prix DVF + {p_lls:.0%}×{hyp.prix_m2_lls:.0f} €/m² (LLS)",
                          f"{_px(med):.0f} €/m² (médiane pondérée)",
                          "prescription GPU · params pct_lls / prix_m2_lls"))
    elif mixite:
        avert.append(
            f"Secteur de mixité sociale ({eco.get('mixite_libelle') or 'logements aidés'}) : "
            "quota et prix LLS non calibrés (pct_lls / prix_m2_lls = PLACEHOLDER) → CA NON "
            "pondéré. Renseigner ces paramètres (ou les éditer dans le panneau) pour fiabiliser le CA.")
    # Coût rapporté à la SURFACE DE PLANCHER (≈ habitable × coef), pas à l'habitable vendu
    # (audit O2 : compter le coût sur l'habitable sous-estimait la construction).
    sdp = surf * hyp.coef_plancher_habitable
    maj_vrd = float(hyp.majoration_vrd_pluvial) if pluvial else 0.0
    cc_bas = sdp * hyp.cout_construction_m2_bas * (1.0 + maj_vrd / 100.0)
    cc_haut = sdp * hyp.cout_construction_m2_haut * (1.0 + maj_vrd / 100.0)
    if pluvial:
        lib_pl = eco.get("pluvial_libelle") or "zonage eaux pluviales"
        if maj_vrd > 0:
            steps.append(Step("Majoration VRD — eaux pluviales",
                              f"coût construction × (1 + {maj_vrd:g} %) — {lib_pl}",
                              "appliquée", "zonage pluvial · param majoration_vrd_pluvial"))
        else:
            hypotheses.append(
                f"Zonage eaux pluviales ({lib_pl}) : majoration VRD paramétrable "
                "(majoration_vrd_pluvial = 0, PLACEHOLDER) → coût inchangé tant que non calibrée.")
    coef = 1.0 - hyp.marge_promoteur_pct - hyp.frais_annexes_pct
    cf_bas = ca_bas * coef - cc_haut
    cf_cen = ca_cen * coef - (cc_bas + cc_haut) / 2
    cf_haut = ca_haut * coef - cc_bas
    par_m2 = cf_cen / surface_terrain_m2 if surface_terrain_m2 else 0.0

    # Si prix fragile : on ARRONDIT (pas de fausse précision).
    rnd = (lambda x: round(x / 100_000) * 100_000) if fragile else (lambda x: round(x))

    ca_formule = (f"{surf:.0f} m² × {_px(q1):.0f}–{_px(q3):.0f} €/m² (prix mixés LLS)"
                  if pondere else f"{surf:.0f} m² × {q1}–{q3} €/m²")
    steps.append(Step("Chiffre d'affaires potentiel", ca_formule,
                      f"~{_eur(ca_bas)} – {_eur(ca_haut)} (médiane {_eur(ca_cen)})", "dérivé"))
    steps.append(Step("Coût de construction",
                      f"{sdp:.0f} m² de plancher ({surf:.0f} m² hab. × {hyp.coef_plancher_habitable:.2f}) "
                      f"× {hyp.cout_construction_m2_bas:.0f}–{hyp.cout_construction_m2_haut:.0f} €/m²",
                      f"~{_eur(cc_bas)} – {_eur(cc_haut)}", "hypothèse coût (prudente, Réunion)"))
    steps.append(Step("Marge promoteur + frais annexes",
                      f"marge {hyp.marge_promoteur_pct:.0%} + frais {hyp.frais_annexes_pct:.0%} du CA",
                      "déduits du CA", "hypothèse"))
    # Présentation : la MÉDIANE d'abord (le chiffre de référence), la fourchette ensuite,
    # bas borné à 0 (audit O3 : « entre −0,2 et 8 M€ » n'aide personne à décider).
    steps.append(Step("Charge foncière acceptable (bilan à rebours)",
                      f"CA×(1−{hyp.marge_promoteur_pct:.0%}−{hyp.frais_annexes_pct:.0%}) − coût construction",
                      f"médiane {_eur(cf_cen)} ≈ {par_m2:.0f} €/m² terrain "
                      f"(fourchette {_eur(max(0, cf_bas))} – {_eur(cf_haut)})",
                      "dérivé"))

    hypotheses += [
        f"Coût de construction supposé {hyp.cout_construction_m2_bas:.0f}–{hyp.cout_construction_m2_haut:.0f} €/m² "
        f"de surface de plancher (habitable × {hyp.coef_plancher_habitable:.2f}) — hypothèse prudente Réunion.",
        f"Marge promoteur supposée {hyp.marge_promoteur_pct:.0%} du CA ; frais annexes {hyp.frais_annexes_pct:.0%}.",
        f"Prix = ventes DVF {prix['type_prix']} ({prix.get('pct_appartement', '?')}% d'appartements), "
        f"{prix['periode'][0]}-{prix['periode'][1]}, {lieu}.",
        "Le prix de sortie est une donnée de MARCHÉ (DVF) ; le bilan complet reste INDICATIF. "
        "À valider par un professionnel : coût travaux, marge, frais, TVA, VRD, stationnement et aléas.",
    ]
    if fragile:
        avert.insert(0, "Prix de sortie FRAGILE (" + " ; ".join(raisons) + ") — "
                     "simulation à utiliser comme ORDRE DE GRANDEUR uniquement, pas comme bilan ferme.")
    if cf_bas < 0:
        avert.append("Charge foncière NÉGATIVE en bas de fourchette : aux prix bas / coûts hauts, "
                     "l'opération ne dégage pas de valeur pour le terrain.")

    # Le BILAN reste une « simulation indicative » dans tous les cas (il dépend d'hypothèses) ;
    # seule la fiabilité du PRIX DE SORTIE varie (fiable / fragile).
    if fragile:
        verdict = (f"Simulation indicative (prix de sortie fragile) — CA ≈ {_eur(rnd(ca_bas))}–{_eur(rnd(ca_haut))}, "
                   f"charge foncière médiane ≈ {_eur(rnd(cf_cen))} (ordre de grandeur)")
    else:
        verdict = (f"Simulation indicative (prix de sortie fiable) — CA ~{_eur(ca_bas)}–{_eur(ca_haut)} · "
                   f"charge foncière médiane ~{_eur(cf_cen)} "
                   f"(fourchette {_eur(max(0, cf_bas))}–{_eur(cf_haut)})")

    calc = {"surf": round(surf), "terrain_m2": round(surface_terrain_m2 or 0),
            "q1": q1, "median": med, "q3": q3, "coef": round(coef, 4),
            "cc_bas": round(cc_bas), "cc_haut": round(cc_haut),
            "mixite": mixite, "pluvial": pluvial, "pondere": pondere,
            "pct_lls": float(hyp.pct_lls), "prix_m2_lls": float(hyp.prix_m2_lls),
            "majoration_vrd_pluvial": maj_vrd}
    return Bilan(True, niveau, verdict, prix,
                 {"bas": rnd(ca_bas), "central": rnd(ca_cen), "haut": rnd(ca_haut)},
                 # bas borné à 0 pour l'AFFICHAGE (audit O3) ; l'avertissement « charge
                 # foncière négative en bas de fourchette » reste émis quand c'est le cas.
                 {"bas": max(0, rnd(cf_bas)), "central": rnd(cf_cen), "haut": rnd(cf_haut),
                  "par_m2_terrain": round(par_m2)},
                 steps, hypotheses, avert, calc=calc)
