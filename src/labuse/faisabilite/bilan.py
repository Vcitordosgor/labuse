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


def _marche_dynamique(kept: list[dict], q1: float, med: float, q3: float, min_n: int) -> dict:
    """Raffinements marché (DVF) : VOLATILITÉ (dispersion interquartile relative au prix médian)
    + TENDANCE prudente (médiane des ventes récentes vs anciennes). Indicatif, jamais certain :
    la tendance n'est calculée que si l'échantillon le permet, sinon « indéterminée »."""
    vol = round(100 * (q3 - q1) / med) if med else None
    out = {
        "volatilite_pct": vol,
        "volatilite": (None if vol is None else "stable" if vol < 25 else "modérée" if vol <= 50 else "volatile"),
        "tendance_pct": None,
        "tendance": "indéterminée",
    }
    annees = sorted({s["annee"] for s in kept})
    if len(annees) >= 2 and len(kept) >= min_n:
        pivot = statistics.median([s["annee"] for s in kept])
        recent = [s["prix"] for s in kept if s["annee"] >= pivot]
        ancien = [s["prix"] for s in kept if s["annee"] < pivot]
        if len(recent) >= 2 and len(ancien) >= 2:
            mr, ma = statistics.median(recent), statistics.median(ancien)
            if ma:
                tr = round(100 * (mr - ma) / ma)
                out["tendance_pct"] = tr
                out["tendance"] = "hausse" if tr >= 5 else "baisse" if tr <= -5 else "stable"
    return out


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
            **_marche_dynamique(kept, q1, med, q3, min_n),
            "comparables": _comparables(kept, min_n, niveau)}


def _clause_mixite(eco: dict, hyp: Hypotheses) -> dict:
    """Déclenchement de la clause de mixité (Art. 2 règlement PLU) selon le PROGRAMME estimé.
    Logique OU du texte : SDP ≥ seuil OU logements ≥ seuil OU terrain > seuil. Renvoie l'état
    (déclenchée + critère atteint) pour pondérer le CA et l'AFFICHER au promoteur."""
    sdp = float(eco.get("sdp_max_m2") or 0.0)
    logements = float(eco.get("logements_estimes") or 0.0)
    terrain = float(eco.get("terrain_m2") or 0.0)
    s_sdp = float(hyp.mixite_sdp_seuil_m2)
    s_log = float(hyp.mixite_logements_seuil)
    s_ter = float(hyp.mixite_terrain_seuil_m2)
    if sdp >= s_sdp:
        return {"declenchee": True, "critere": f"SDP {sdp:.0f} m² ≥ {s_sdp:.0f} m²",
                "detail": f"programme SDP ~{sdp:.0f} m² ≥ seuil {s_sdp:.0f} m²"}
    if logements >= s_log:
        return {"declenchee": True, "critere": f"{logements:.0f} logements ≥ {s_log:.0f}",
                "detail": f"programme ~{logements:.0f} logements ≥ seuil {s_log:.0f}"}
    if terrain > s_ter:
        return {"declenchee": True, "critere": f"terrain {terrain:.0f} m² > {s_ter:.0f} m²",
                "detail": f"terrain ~{terrain:.0f} m² > seuil {s_ter:.0f} m²"}
    return {"declenchee": False, "critere": None,
            "detail": (f"programme sous les seuils (SDP {sdp:.0f} < {s_sdp:.0f} m², "
                       f"{logements:.0f} < {s_log:.0f} logts, terrain {terrain:.0f} ≤ {s_ter:.0f} m²)")}


def compute_bilan(shab_vendable_m2: float, surface_terrain_m2: float,
                  prix: dict, hyp: Hypotheses, contexte_eco: dict | None = None,
                  bilan_params: dict | None = None) -> Bilan:
    """Cœur pur (testable). Protège le bilan selon la fiabilité du prix.

    `bilan_params` (1.C) = paramètres résolus par SECTEUR (prix neuf override, coût construction,
    VRD base + majorations pente/assainissement, honoraires, frais financiers, marge). Quand fourni,
    ils PILOTENT le bilan ; absents → repli sur les hypothèses YAML (compat tests). `calc` les
    expose pour l'édition + recalcul instantané ; les critiques non calibrés lèvent un bandeau.


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

    # 1.C — paramètres effectifs (secteur si fourni, sinon hypothèses YAML).
    bp = bilan_params or {}

    def _p(key: str, fallback: float) -> float:
        v = bp.get(key)
        return float(v) if v is not None else float(fallback)

    prix_neuf_override = _p("prix_m2_neuf", 0.0)
    cout_m2 = _p("cout_construction_m2_sdp", 0.0)            # 0 → fourchette YAML bas/haut
    vrd_base = _p("cout_vrd_base", 0.0)
    maj_pente = _p("majoration_vrd_pente_pct", 0.0)
    maj_assain = _p("majoration_vrd_assainissement_pct", 0.0)
    honoraires_pct = _p("honoraires_pct", hyp.frais_annexes_pct * 100.0)
    frais_fin_pct = _p("frais_financiers_pct", 0.0)
    marge_pct = _p("marge_cible_pct", hyp.marge_promoteur_pct * 100.0)
    prix_lls = _p("prix_m2_lls", hyp.prix_m2_lls)
    if prix_neuf_override > 0:                                # override du prix de sortie neuf
        q1 = med = q3 = prix_neuf_override
    # 2.B — bonus prix si vue mer dégagée (param PLACEHOLDER, appliqué seulement si vue='oui').
    bonus_vue = _p("bonus_vue_mer_pct", 0.0)
    vue_mer_bonus = ((contexte_eco or {}).get("vue_mer") == "oui") and bonus_vue > 0
    if vue_mer_bonus:
        q1, med, q3 = q1 * (1 + bonus_vue / 100), med * (1 + bonus_vue / 100), q3 * (1 + bonus_vue / 100)
    lieu = "commune entière" if prix.get("commune_fallback") else f"{prix['radius_m']:.0f} m"
    steps: list[Step] = []
    hypotheses: list[str] = []
    avert: list[str] = []

    steps.append(Step("Surface habitable vendable",
                      "issue de la faisabilité (post-rendement, plafond, modulation)",
                      f"~{surf:.0f} m²", "faisabilité", prov="derive"))
    if vue_mer_bonus:
        steps.append(Step("Bonus vue mer (2.B)", f"prix de sortie × (1 + {bonus_vue:g} %) — vue mer dégagée",
                          "appliqué", "param bonus_vue_mer_pct", prov="estimee"))
    detail = (f"{prix['type_prix']} · {prix['n']} ventes ({prix['periode'][0]}-{prix['periode'][1]}) "
              f"dans {lieu}"
              + (f" · {prix['n_exclus']} aberrant(s) exclu(s)" if prix["n_exclus"] else "")
              + (f" · {prix['n_doublons']} doublon(s) écarté(s)" if prix.get("n_doublons") else ""))
    steps.append(Step("Prix de vente (DVF secteur)", detail,
                      f"{q1}–{q3} €/m² (médiane {med} ; min {prix['min']} / max {prix['max']})",
                      f"DVF Région ODS · fiabilité {niveau}", prov="sourcee"))

    eco = contexte_eco or {}
    mixite, pluvial = bool(eco.get("mixite")), bool(eco.get("pluvial"))
    p_lls = min(1.0, max(0.0, float(hyp.pct_lls) / 100.0))
    # Clause de mixité : déclenchée seulement si le PROGRAMME estimé franchit un seuil de l'Art. 2.
    clause = _clause_mixite(eco, hyp) if mixite else None
    declenchee = bool(clause and clause["declenchee"])
    # Pondération du CA = clause déclenchée ET 30 % posé ET prix LLS calibré (jamais de prix fictif).
    pondere = declenchee and p_lls > 0 and prix_lls > 0
    _px = (lambda x: (1.0 - p_lls) * float(x) + p_lls * prix_lls) if pondere \
        else (lambda x: float(x))
    ca_bas, ca_cen, ca_haut = surf * _px(q1), surf * _px(med), surf * _px(q3)
    if mixite:
        lib_sms = eco.get("mixite_libelle") or "logements aidés"
        if not declenchee:
            steps.append(Step("Clause de mixité sociale — non déclenchée",
                              clause["detail"], "pas de quota LLS sur ce programme",
                              "Art. 2 règlement PLU", prov="derive"))
        elif pondere:
            steps.append(Step("CA pondéré — clause de mixité DÉCLENCHÉE",
                              f"{clause['detail']} · prix mixé = (1−{p_lls:.0%})×prix DVF + "
                              f"{p_lls:.0%}×{hyp.prix_m2_lls:.0f} €/m² (LLS)",
                              f"{_px(med):.0f} €/m² (médiane pondérée)",
                              "Art. 2 · pct_lls / prix_m2_lls", prov="estimee"))
        else:  # déclenchée mais prix LLS non calibré → on NE chiffre PAS
            avert.append(
                f"Clause de mixité sociale DÉCLENCHÉE ({clause['critere']}) — {p_lls:.0%} de "
                f"logements aidés imposés ({lib_sms}). Impact non chiffré : prix LLS non calibré "
                "(PLACEHOLDER) → saisir le prix LLS dans le panneau pour pondérer le CA.")
    # Coût de construction rapporté à la SURFACE DE PLANCHER. Coût au m² piloté par secteur
    # (cout_construction_m2_sdp) si calibré ; sinon fourchette YAML bas/haut.
    sdp = surf * hyp.coef_plancher_habitable
    maj_vrd_pluvial = float(hyp.majoration_vrd_pluvial) if pluvial else 0.0
    cm_bas = cout_m2 if cout_m2 > 0 else hyp.cout_construction_m2_bas
    cm_haut = cout_m2 if cout_m2 > 0 else hyp.cout_construction_m2_haut
    cc_bas = sdp * cm_bas * (1.0 + maj_vrd_pluvial / 100.0)
    cc_haut = sdp * cm_haut * (1.0 + maj_vrd_pluvial / 100.0)
    # VRD / viabilisation (1.C + 2.A) : base €/m² terrain, majorée si pente forte (≥ 15 %, seuil
    # faisabilité) et/ou assainissement autonome. La pente ALIMENTE la majoration (2.A).
    pente_pct = float(eco.get("pente_pct") or 0.0)
    maj_pente_eff = maj_pente if pente_pct >= 15.0 else 0.0
    maj_vrd_terrain = maj_pente_eff + maj_assain
    cout_vrd = vrd_base * (1.0 + maj_vrd_terrain / 100.0) * (surface_terrain_m2 or 0.0)
    if vrd_base > 0:
        bits = []
        if maj_pente_eff:
            bits.append(f"pente {pente_pct:.0f} %")
        if maj_assain:
            bits.append("assainissement autonome")
        steps.append(Step("VRD / viabilisation",
                          f"{vrd_base:.0f} €/m² terrain × {surface_terrain_m2:.0f} m²"
                          + (f" × (1 + {maj_vrd_terrain:g} % : {', '.join(bits)})" if maj_vrd_terrain else ""),
                          f"~{_eur(cout_vrd)}", "param cout_vrd_base", prov="estimee"))
    if pluvial:
        lib_pl = eco.get("pluvial_libelle") or "zonage eaux pluviales"
        if maj_vrd_pluvial > 0:
            steps.append(Step("Majoration VRD — eaux pluviales",
                              f"coût construction × (1 + {maj_vrd_pluvial:g} %) — {lib_pl}",
                              "appliquée", "zonage pluvial · param majoration_vrd_pluvial", prov="estimee"))
        else:
            hypotheses.append(
                f"Zonage eaux pluviales ({lib_pl}) : majoration VRD paramétrable "
                "(majoration_vrd_pluvial = 0, PLACEHOLDER) → coût inchangé tant que non calibrée.")
    coef = 1.0 - (marge_pct + honoraires_pct + frais_fin_pct) / 100.0
    cf_bas = ca_bas * coef - cc_haut - cout_vrd
    cf_cen = ca_cen * coef - (cc_bas + cc_haut) / 2 - cout_vrd
    cf_haut = ca_haut * coef - cc_bas - cout_vrd
    par_m2 = cf_cen / surface_terrain_m2 if surface_terrain_m2 else 0.0

    # Si prix fragile : on ARRONDIT (pas de fausse précision).
    rnd = (lambda x: round(x / 100_000) * 100_000) if fragile else (lambda x: round(x))

    ca_formule = (f"{surf:.0f} m² × {_px(q1):.0f}–{_px(q3):.0f} €/m² (prix mixés LLS)"
                  if pondere else f"{surf:.0f} m² × {q1}–{q3} €/m²")
    steps.append(Step("Chiffre d'affaires potentiel", ca_formule,
                      f"~{_eur(ca_bas)} – {_eur(ca_haut)} (médiane {_eur(ca_cen)})", "dérivé", prov="derive"))
    cout_lbl = (f"× {cout_m2:.0f} €/m² (secteur)" if cout_m2 > 0
                else f"× {hyp.cout_construction_m2_bas:.0f}–{hyp.cout_construction_m2_haut:.0f} €/m²")
    steps.append(Step("Coût de construction",
                      f"{sdp:.0f} m² de plancher ({surf:.0f} m² hab. × {hyp.coef_plancher_habitable:.2f}) {cout_lbl}",
                      f"~{_eur(cc_bas)} – {_eur(cc_haut)}",
                      "param cout_construction_m2_sdp" if cout_m2 > 0 else "hypothèse coût (prudente, Réunion)",
                      prov="estimee"))
    steps.append(Step("Marge + frais (déduits du CA)",
                      f"marge {marge_pct:g} % + honoraires {honoraires_pct:g} % + frais financiers {frais_fin_pct:g} %",
                      f"{(1 - coef) * 100:.0f} % du CA", "params marge/honoraires/frais", prov="estimee"))
    # Présentation : la MÉDIANE d'abord (le chiffre de référence), la fourchette ensuite,
    # bas borné à 0 (audit O3 : « entre −0,2 et 8 M€ » n'aide personne à décider).
    steps.append(Step("Charge foncière acceptable (bilan à rebours)",
                      f"CA×{coef:.2f} − coût construction" + (" − VRD" if vrd_base > 0 else ""),
                      f"médiane {_eur(cf_cen)} ≈ {par_m2:.0f} €/m² terrain "
                      f"(fourchette {_eur(max(0, cf_bas))} – {_eur(cf_haut)})",
                      "dérivé", prov="derive"))

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
            "cc_bas": round(cc_bas), "cc_haut": round(cc_haut), "cout_vrd": round(cout_vrd),
            "mixite": mixite, "pluvial": pluvial, "pondere": pondere,
            "pct_lls": float(hyp.pct_lls), "prix_m2_lls": prix_lls,
            "majoration_vrd_pluvial": maj_vrd_pluvial,
            # État de la clause de mixité (info de pilotage promoteur).
            "clause_declenchee": declenchee,
            "clause_critere": (clause or {}).get("critere"),
            "clause_detail": (clause or {}).get("detail")}
    return Bilan(True, niveau, verdict, prix,
                 {"bas": rnd(ca_bas), "central": rnd(ca_cen), "haut": rnd(ca_haut)},
                 # bas borné à 0 pour l'AFFICHAGE (audit O3) ; l'avertissement « charge
                 # foncière négative en bas de fourchette » reste émis quand c'est le cas.
                 {"bas": max(0, rnd(cf_bas)), "central": rnd(cf_cen), "haut": rnd(cf_haut),
                  "par_m2_terrain": round(par_m2)},
                 steps, hypotheses, avert, calc=calc)


# ── CALCULETTE DE CHARGE FONCIÈRE (mandat bilan-calculette) ────────────────────────────────
#: hypothèses métier PAR DÉFAUT, explicitement marquées « à ajuster » côté fiche — LABUSE ne
#: prétend pas les connaître (elles relèvent du jugement du promoteur). Le coût de construction
#: par défaut = milieu de la fourchette prudente Réunion (2300–2800) ; la marge & frais par
#: défaut = marge promoteur (9 %) + frais annexes (12 %) des hypothèses moteur.
CALCULETTE_COUT_DEFAUT_M2 = 2500.0
CALCULETTE_MARGE_FRAIS_DEFAUT_PCT = 21.0


def compute_calculette(shab_vendable_m2: float, surface_terrain_m2: float, prix: dict,
                       cout_construction_m2: float, marge_frais_pct: float,
                       prix_demande_eur: float | None = None) -> dict:
    """Charge foncière supportable — PURE, testable en isolation (aucun accès DB : `prix` est
    fourni). LIGNE ROUGE : les valeurs SOURCÉES (SDP vendable, prix de sortie DVF) viennent du
    moteur ; le coût de construction et la marge sont les HYPOTHÈSES SAISIES par le promoteur —
    jamais estimées par LABUSE. Réutilise `compute_bilan` (pas de ré-écriture de l'arithmétique) :
    on injecte les saisies comme `bilan_params` (coût au m² de plancher, marge+frais en % du CA,
    honoraires/frais financiers neutralisés car agrégés dans « marge & frais »). Le résultat est
    présenté « selon vos hypothèses ». Si `prix_demande_eur` est fourni : verdict d'achat
    (supportable si la charge foncière médiane ≥ prix demandé)."""
    bp = {
        "cout_construction_m2_sdp": float(cout_construction_m2),
        "marge_cible_pct": float(marge_frais_pct),
        "honoraires_pct": 0.0,          # agrégés dans « marge & frais » saisi par l'utilisateur
        "frais_financiers_pct": 0.0,
    }
    b = compute_bilan(float(shab_vendable_m2), float(surface_terrain_m2 or 0), prix, Hypotheses(),
                      bilan_params=bp)
    marche = {"median": prix.get("median"), "fiabilite": prix.get("fiabilite"), "n": prix.get("n")}
    if not b.charge_fonciere:
        # prix insuffisant / surface nulle → on ne fabrique pas de chiffre creux (doctrine)
        return {"calculable": False, "fiabilite": b.fiabilite, "raison": b.verdict, "marche": marche}
    cf = b.charge_fonciere
    out: dict = {
        "calculable": True,
        "fiabilite": b.fiabilite,               # le résultat HÉRITE de la fiabilité du prix (fiable/fragile)
        "inputs": {
            "cout_construction_m2": round(float(cout_construction_m2)),
            "marge_frais_pct": round(float(marge_frais_pct), 1),
            "prix_demande_eur": round(float(prix_demande_eur)) if prix_demande_eur else None,
        },
        "shab_vendable_m2": round(float(shab_vendable_m2)),
        "terrain_m2": round(float(surface_terrain_m2 or 0)),
        "prix_sortie_median": prix.get("median"),
        "ca": b.ca,
        "charge_fonciere": cf,                  # {bas, central, haut, par_m2_terrain}
        "verdict": b.verdict,
        "avertissements": b.avertissements,
        "marche": marche,
    }
    if prix_demande_eur:
        pd = float(prix_demande_eur)
        supportable = cf["central"] >= pd
        ecart = cf["central"] - pd
        out["achat"] = {
            "prix_demande_eur": round(pd),
            "supportable": supportable,
            "ecart_eur": round(ecart),                                  # + = marge, − = surcoût
            "ecart_pct": round(100 * ecart / pd) if pd else None,
        }
    return out
