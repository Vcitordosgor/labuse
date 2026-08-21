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
    # M128-A1 : format STRICTEMENT identique à api.briques_pdf.eur (M€ à 2 décimales, virgule
    # française) — le bilan (texte des étapes) et le document (bandeau, fourchettes) affichent
    # la MÊME valeur à l'identique ; jamais « 4.5 M€» ici et « 4,47 M€ » là.
    ax = abs(x)
    if ax >= 1_000_000:
        return f"{x / 1_000_000:.2f} M€".replace(".", ",")
    if ax >= 1_000:
        return f"{x / 1_000:.0f} k€"
    return f"{x:.0f} €"


def _plage_txt(bas: float, cen: float, haut: float) -> str:
    """M128-A3 — une fourchette DÉGÉNÉRÉE (bornes égales après arrondi) s'affiche en UNE
    valeur, jamais « 954 k€ – 954 k€ (médiane 954 k€) ». Sinon : bas – haut (médiane cen)."""
    if bas == haut:
        return _eur(cen)
    return f"{_eur(bas)} – {_eur(haut)} (médiane {_eur(cen)})"


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
    promoteur dans un échantillon dit « fiable » (audit J6). Retourne (gardées, exclues).

    P2-48 — ÉCART ASSUMÉ avec le Baromètre (`api/moteurs._BAROMETRE_RETENUE`) : là, le €/m²
    est borné [100 ; 12000] (garde-fou anti-ratio-aberrant seulement) + un filtre ABSOLU
    `valeur_fonciere > 1000 €` pour les prix symboliques. Deux intentions différentes sur la
    MÊME donnée : ici on construit un ÉCHANTILLON DE COMPARABLES robuste pour un bilan financier
    (plancher €/m² serré à 1000) ; le Baromètre OBSERVE tout le marché (plancher €/m² lâche à 100,
    nettoyage des symboliques par le prix absolu). Ne pas aligner l'un sur l'autre sans arbitrage
    produit — les deux planchers sont voulus."""
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
            # M22-F C9 (additif) : les prix RETENUS, un par vente — la bande de points de
            # l'argumentaire les dessine tels quels (aucune agrégation nouvelle).
            "prix_points": sorted(round(p) for p in prices)[:120],
            **_marche_dynamique(kept, q1, med, q3, min_n),
            "comparables": _comparables(kept, min_n, niveau)}


# ── POINT DE RÉSOLUTION PARTAGÉ du prix de sortie neuf (mandat prix sortie consommateurs) ──────
def resolve_prix_sortie_servi(session: Session, parcel_id: int, secteur: str | None = None) -> dict:
    """UN SEUL chemin pour le prix de sortie NEUF servi — cœur (fiche) ET les 6 consommateurs
    (Copilote, Rapport de potentiel, Explication IA, Banquier, Argumentaire, calculette). Décision
    Vic 28/07/2026 : plus jamais de `sector_price` (prix de l'EXISTANT) comme prix de sortie d'un
    bilan NEUF. Préséance dans `resolve_prix_neuf_marche` (override bassin DVF-sourcé > dvf secteur
    local > dvf commune local > repli île > non calculable social-dominant).

    Renvoie {prix, niveau, n, label, motif, non_calculable, repli_ile}. Si `motif` (commune
    social-dominante) : la parcelle est SERVIE avec la mention, jamais écartée (comportement M26-A).
    `secteur` (bassin PLU) peut être fourni si l'appelant l'a déjà résolu (évite une requête)."""
    from . import bilan_params as bpmod
    from ..ingestion.dvf_prix_neuf import resolve_prix_neuf_marche, niveau_prix_label
    if secteur is None:
        from .db import parcel_context
        from .plu_rules import resolve_zone
        ctx = parcel_context(session, parcel_id)
        rules = resolve_zone(ctx.zone, ctx.commune) if ctx and ctx.zone else None
        secteur = (rules.bassin if rules else None) or "Saint-Paul"
    prix, niveau, n, motif = resolve_prix_neuf_marche(
        session, parcel_id, bpmod.resolve(session, secteur).get("prix_m2_neuf"))
    return {"prix": prix, "niveau": niveau, "n": n, "motif": motif,
            "non_calculable": motif is not None,
            "repli_ile": niveau in ("ile_validee", "ile_sans_operation"),
            "label": None if motif is not None else niveau_prix_label(niveau, n)}


def compute_bilan_servi(session: Session, parcel_id: int, fz=None) -> tuple["Bilan | None", dict | None]:
    """LE bilan promoteur SERVI pour une parcelle — SOURCE UNIQUE partagée par le cœur (fiche), le
    Banquier, l'Argumentaire et le Rapport de potentiel. Garantit une charge COHÉRENTE À L'EURO entre
    tous les écrans (mandat prix sortie consommateurs, Vic 28/07/2026) : même capacité, mêmes
    hypothèses résolues par secteur (VRD, honoraires, marge), même prix de sortie neuf, même
    contexte éco (mixité/pluvial). Renvoie (Bilan | None, info_prix_sortie). Non calculable
    (commune social-dominante) → Bilan(fiable=False) SERVI avec la mention, jamais None écarté."""
    from .db import parcel_faisabilite
    from .plu_rules import resolve_zone
    from .engine import Hypotheses
    from . import bilan_params as bpmod
    fz = fz or parcel_faisabilite(session, parcel_id)
    if not fz or not fz[1].constructible:
        return None, None
    ctx, f = fz
    fr = f.fourchette or {}
    shab = fr.get("shab_vendable_m2")
    if not shab:
        return None, None
    hyp = Hypotheses.charger(ctx.commune)   # M-N P1-13 : hypothèses de la COMMUNE servie (mixité, coûts)
    rules = resolve_zone(ctx.zone, ctx.commune) if ctx.zone else None
    secteur = (rules.bassin if rules else None) or "Saint-Paul"
    ps = resolve_prix_sortie_servi(session, parcel_id, secteur)
    if ps["non_calculable"]:
        return Bilan(False, "non_calculable", ps["motif"], None, None, None,
                     avertissements=[ps["motif"]], bandeau=ps["motif"]), ps
    logements_est = max((fr.get("logements_au_sol") or (0, 0))[1],
                        (fr.get("logements_sous_sol") or (0, 0))[1])
    eco = dict(ctx.prescriptions_eco)
    eco.update({"sdp_max_m2": fr.get("surface_plancher_m2"), "logements_estimes": logements_est,
                "terrain_m2": ctx.surface_m2, "pente_pct": ctx.contraintes.pente_pct})
    bp = {k: r["value"] for k, r in bpmod.resolve(session, secteur).items()}
    bp["prix_m2_neuf"] = ps["prix"]
    b = compute_bilan(float(shab), float(ctx.surface_m2 or 0),
                      sector_price(session, parcel_id, hyp), hyp, contexte_eco=eco,
                      bilan_params=bp, prix_neuf=ps)   # M-N P2-47 : fiabilité/dispo du bilan = prix NEUF
    return b, ps


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


def _fiabilite_prix_neuf(niveau: str | None) -> tuple[str, list[str]]:
    """M-N P2-47 — fiabilité du bilan DÉRIVÉE du prix de sortie NEUF résolu (jamais de la dispersion
    de l'ancien). Local observé (secteur/commune) ou bassin sourcé → « fiable » ; repli ÎLE
    (estimation ±12 %) → « fragile » (montants arrondis + avertissement). Renvoie (niveau, raisons)."""
    if niveau in ("override_bassin", "secteur", "commune"):
        return "fiable", []
    if niveau == "ile_validee":
        return "fragile", ["prix de sortie neuf estimé à l'échelle de l'île (± 12 %) — "
                           "montants arrondis"]
    if niveau == "ile_sans_operation":
        return "fragile", ["prix de sortie neuf estimé par repli île — aucune opération de marché "
                           "observée sur cette commune ; ordre de grandeur"]
    return "fragile", ["prix de sortie neuf estimé — fiabilité prudente"]


def compute_bilan(shab_vendable_m2: float, surface_terrain_m2: float,
                  prix: dict, hyp: Hypotheses, contexte_eco: dict | None = None,
                  bilan_params: dict | None = None, prix_neuf: dict | None = None) -> Bilan:
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
    # 1.C — paramètres effectifs (secteur si fourni, sinon hypothèses YAML).
    bp = bilan_params or {}

    def _p(key: str, fallback: float) -> float:
        v = bp.get(key)
        return float(v) if v is not None else float(fallback)

    prix_neuf_override = _p("prix_m2_neuf", 0.0)
    # M-N P2-47 — quand le prix de sortie NEUF est résolu (override présent), c'est LUI qui gouverne
    # la FIABILITÉ et la DISPONIBILITÉ du bilan ; sector_price (prix de l'EXISTANT) redevient
    # purement documentaire (bloc comparables / prix_dvf, plus bas). Avant, un prix neuf parfaitement
    # résolu pouvait se voir refuser son bilan — ou l'étiqueter « fragile » — sur la seule dispersion
    # de l'ancien. Repli EXPLICITE : sans prix neuf (prix_neuf None ou override 0), le comportement
    # historique (fiabilité de sector_price) s'applique inchangé — on ne crée aucun bilan silencieux.
    neuf_actif = prix_neuf is not None and prix_neuf_override > 0
    if neuf_actif:
        niveau, raisons = _fiabilite_prix_neuf(prix_neuf.get("niveau"))
    else:
        niveau = prix.get("fiabilite", "insuffisant")
        raisons = prix.get("fiabilite_raisons", [])

    if not neuf_actif and (niveau == "insuffisant" or not prix.get("fiable")):
        return Bilan(False, "insuffisant",
                     f"Prix de sortie indisponible — échantillon DVF insuffisant "
                     f"({prix.get('n', 0)} vente(s) comparable(s)) : pas de bilan chiffré "
                     "(on n'invente pas de prix).",
                     prix, None, None, avertissements=raisons)
    if shab_vendable_m2 <= 0:
        return Bilan(False, "insuffisant", "Surface vendable nulle — pas de bilan.", prix, None, None)

    fragile = niveau == "fragile"
    # q1/med/q3 portés par l'ancien DVF quand il est exploitable ; en repli (neuf actif + ancien
    # insuffisant) ils sont écrasés juste après par le prix neuf → .get défensif, car sector_price
    # « insuffisant » n'expose ni médiane ni quartiles (sinon KeyError sur un cas désormais servi).
    q1 = prix.get("q1", prix_neuf_override)
    med = prix.get("median", prix_neuf_override)
    q3 = prix.get("q3", prix_neuf_override)
    surf = shab_vendable_m2

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
    lieu = "commune entière" if prix.get("commune_fallback") else f"{prix.get('radius_m', 0):.0f} m"
    steps: list[Step] = []
    hypotheses: list[str] = []
    avert: list[str] = []

    steps.append(Step("Surface habitable vendable",
                      "issue de la faisabilité (post-rendement, plafond, modulation)",
                      f"~{surf:.0f} m²", "faisabilité", prov="derive"))
    if neuf_actif:
        # Prix de SORTIE NEUF servi (mandat 28/07) — q1=med=q3=neuf. Sa fiabilité EST celle du
        # bilan ; l'ancien DVF n'est ici que comparable documentaire (jamais le juge), et peut
        # manquer sans que le bilan disparaisse (M-N P2-47).
        ancien_dispo = prix.get("median") is not None and prix.get("periode")
        note_anc = (f" · comparables ancien : {prix.get('n', 0)} ventes "
                    f"({prix['periode'][0]}-{prix['periode'][1]})" if ancien_dispo
                    else " · comparables ancien indisponibles (échantillon insuffisant)")
        # M128-2-G : le prix de sortie NEUF est une projection DÉRIVÉE (médiane locale ou repli
        # île) → ESTIMÉ. Seul le prix de bassin d'observatoire (override_bassin) est vraiment SOURCÉ.
        _prov_neuf = "sourcee" if prix_neuf.get("niveau") == "override_bassin" else "estimee"
        steps.append(Step("Prix de sortie neuf (marché)",
                          (prix_neuf.get("label") or "prix de sortie neuf") + note_anc,
                          f"{med:g} €/m² (habitable, neuf)",
                          f"prix de sortie neuf · {prix_neuf.get('niveau')}", prov=_prov_neuf))
    else:
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
    # M-N P1-13 — source AFFICHÉE des seuils de mixité : la référence Sourcée SEULEMENT si le YAML
    # de la commune servie la DÉCLARE (mixite_source_ref) ; sinon défaut → jamais l'Art. 2 d'une
    # autre commune (un Estimé emprunté ne se présente pas en Sourcé).
    mixite_src = hyp.mixite_source_ref or "Estimé — seuils de mixité par défaut (Saint-Paul)"
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
                              mixite_src, prov="derive"))
        elif pondere:
            steps.append(Step("CA pondéré — clause de mixité DÉCLENCHÉE",
                              f"{clause['detail']} · prix mixé = (1−{p_lls:.0%})×prix DVF + "
                              f"{p_lls:.0%}×{hyp.prix_m2_lls:.0f} €/m² (LLS)",
                              f"{_px(med):.0f} €/m² (médiane pondérée)",
                              f"{mixite_src} · pct_lls / prix_m2_lls", prov="estimee"))
        elif p_lls > 0:  # taux connu mais prix LLS non calibré → on NE chiffre PAS
            avert.append(
                f"Clause de mixité sociale DÉCLENCHÉE ({clause['critere']}) — {p_lls:.0%} de "
                f"logements aidés imposés ({lib_sms}). Impact non chiffré : prix LLS non calibré "
                "(PLACEHOLDER) → saisir le prix LLS dans le panneau pour pondérer le CA.")
        else:  # M-N P1-13 : taux de logements aidés NON calibré pour cette commune (seuils estimés)
            avert.append(
                f"Secteur de mixité sociale ({lib_sms}) — programme au-dessus des seuils estimés "
                f"({clause['critere']}). Taux de logements aidés non calibré pour cette commune "
                f"(seuils : {mixite_src}) → impact non chiffré.")
    # Coût de construction rapporté à la SURFACE DE PLANCHER. Coût au m² piloté par secteur
    # (cout_construction_m2_sdp) si calibré ; sinon fourchette YAML bas/haut.
    # M128-3-§1 : la SDP RETENUE au bilan = vendable retenu ÷ rendement (coef_rendement, SOURCE UNIQUE
    # partagée avec la faisabilité, config/hypotheses_ile.yaml). On coûte le plancher qui produit le
    # vendable EFFECTIVEMENT valorisé (post plafond de densité), pas le gabarit brut footprint × niveaux
    # (qui surcoûte quand le plafond écrête). Aucun 1,15 / 1,25 en dur ; coef_rendement ∈ ]0,1].
    sdp = surf / hyp.coef_rendement if hyp.coef_rendement else surf
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
    # M128-A1 : le prix fragile est ARRONDI (pas de fausse précision), mais au k€ — jamais aux
    # 100 k€ qui écrasaient une charge de ~40 k€ à « 0 € » (le bandeau disait 0, le texte 40).
    # On calcule les valeurs arrondies UNE fois et on les sert PARTOUT (bandeau, fourchette,
    # texte, Score É) : une seule voix. `_eur` bucketise déjà au k€/M€ à l'affichage.
    rnd = (lambda x: round(x / 1_000) * 1_000) if fragile else (lambda x: round(x))
    ca_bas_r, ca_cen_r, ca_haut_r = rnd(ca_bas), rnd(ca_cen), rnd(ca_haut)
    cf_bas_r, cf_cen_r, cf_haut_r = rnd(cf_bas), rnd(cf_cen), rnd(cf_haut)
    cf_bas_aff = cf_bas_r   # M128-2-D2(a) : borne basse RÉELLE (négative), plus d'écrêtage muet à 0
    par_m2 = round(cf_cen_r / surface_terrain_m2) if surface_terrain_m2 else 0

    ca_formule = (f"{surf:.0f} m² × {_px(q1):.0f}–{_px(q3):.0f} €/m² (prix mixés LLS)"
                  if pondere else f"{surf:.0f} m² × {q1}–{q3} €/m²")
    steps.append(Step("Chiffre d'affaires potentiel", ca_formule,
                      "~" + _plage_txt(ca_bas_r, ca_cen_r, ca_haut_r), "dérivé", prov="derive"))
    cout_lbl = (f"× {cout_m2:.0f} €/m² (secteur)" if cout_m2 > 0
                else f"× {hyp.cout_construction_m2_bas:.0f}–{hyp.cout_construction_m2_haut:.0f} €/m²")
    steps.append(Step("Coût de construction",
                      f"{sdp:.0f} m² de plancher (vendable {surf:.0f} ÷ rendement {hyp.coef_rendement:.0%}) {cout_lbl}",
                      f"~{_eur(cc_bas)} – {_eur(cc_haut)}",
                      "param cout_construction_m2_sdp" if cout_m2 > 0 else "hypothèse coût (prudente, Réunion)",
                      prov="estimee"))
    steps.append(Step("Marge + frais (déduits du CA)",
                      f"marge {marge_pct:g} % + honoraires {honoraires_pct:g} % + frais financiers {frais_fin_pct:g} %",
                      f"{(1 - coef) * 100:.0f} % du CA", "params marge/honoraires/frais", prov="estimee"))
    # M128-2-D1 : la fourchette n'apparaît qu'UNE fois (le sous-tableau BASSE/MÉDIANE/HAUTE du
    # document) — ici, seule la médiane, chiffre de référence. M128-2-E : terme unique « charge
    # foncière supportable ».
    steps.append(Step("Charge foncière supportable (bilan à rebours)",
                      f"CA×{coef:.2f} − coût construction" + (" − VRD" if vrd_base > 0 else ""),
                      f"médiane {_eur(cf_cen_r)} ≈ {par_m2:.0f} €/m² terrain",
                      "dérivé", prov="derive"))

    if neuf_actif:
        prix_desc = (f"Prix de sortie = médiane du NEUF de marché "
                     f"({prix_neuf.get('label') or prix_neuf.get('niveau')}) ≈ {med:g} €/m² habitable ; "
                     "l'ancien DVF ne sert que de comparable documentaire.")
    else:
        prix_desc = (f"Prix = ventes DVF {prix['type_prix']} ({prix.get('pct_appartement', '?')}% "
                     f"d'appartements), {prix['periode'][0]}-{prix['periode'][1]}, {lieu}.")
    hypotheses += [
        f"Coût de construction supposé {hyp.cout_construction_m2_bas:.0f}–{hyp.cout_construction_m2_haut:.0f} €/m² "
        f"de surface de plancher (habitable × {hyp.coef_plancher_habitable:.2f}) — hypothèse prudente Réunion.",
        f"Marge promoteur supposée {hyp.marge_promoteur_pct:.0%} du CA ; frais annexes {hyp.frais_annexes_pct:.0%}.",
        prix_desc,
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
    # seule la fiabilité du PRIX DE SORTIE varie (fiable / fragile). M128-A1 : mêmes valeurs
    # arrondies que le bandeau/la fourchette/le Score É — une seule voix, fourchette dégénérée pliée.
    ca_txt = _eur(ca_bas_r) if ca_bas_r == ca_haut_r else f"{_eur(ca_bas_r)}–{_eur(ca_haut_r)}"
    cf_txt = _eur(cf_cen_r) if cf_bas_aff == cf_haut_r else f"{_eur(cf_cen_r)} (fourchette {_eur(cf_bas_aff)}–{_eur(cf_haut_r)})"
    if fragile:
        verdict = (f"Simulation indicative (prix de sortie fragile) — CA ≈ {ca_txt}, "
                   f"charge foncière médiane ≈ {cf_txt} (ordre de grandeur)")
    else:
        verdict = (f"Simulation indicative (prix de sortie fiable) — CA ~{ca_txt} · "
                   f"charge foncière médiane ~{cf_txt}")

    calc = {"surf": round(surf), "terrain_m2": round(surface_terrain_m2 or 0),
            "q1": q1, "median": med, "q3": q3, "coef": round(coef, 4),
            "sdp": round(sdp),                       # M128-2-F2 : SDP unique (= faisabilité)
            "cm_bas": round(cm_bas), "cm_haut": round(cm_haut),   # M128-2-F1 : fourchette de coût réelle
            "cc_bas": round(cc_bas), "cc_haut": round(cc_haut), "cout_vrd": round(cout_vrd),
            "mixite": mixite, "pluvial": pluvial, "pondere": pondere,
            "pct_lls": float(hyp.pct_lls), "prix_m2_lls": prix_lls,
            "majoration_vrd_pluvial": maj_vrd_pluvial,
            # État de la clause de mixité (info de pilotage promoteur).
            "clause_declenchee": declenchee,
            "clause_critere": (clause or {}).get("critere"),
            "clause_detail": (clause or {}).get("detail")}
    return Bilan(True, niveau, verdict, prix,
                 {"bas": ca_bas_r, "central": ca_cen_r, "haut": ca_haut_r},
                 # bas borné à 0 pour l'AFFICHAGE (audit O3) ; l'avertissement « charge
                 # foncière négative en bas de fourchette » reste émis quand c'est le cas.
                 {"bas": cf_bas_aff, "central": cf_cen_r, "haut": cf_haut_r,
                  "par_m2_terrain": par_m2},
                 steps, hypotheses, avert, calc=calc)


# ── CALCULETTE DE CHARGE FONCIÈRE (mandat bilan-calculette) ────────────────────────────────
#: hypothèses métier PAR DÉFAUT, explicitement marquées « à ajuster » côté fiche — LABUSE ne
#: prétend pas les connaître (elles relèvent du jugement du promoteur). DÉRIVÉES de la source
#: unique (`hypotheses_faisabilite` du YAML, mandat hypothèses bilan — décision Vic
#: 28/07/2026) : coût = milieu de la fourchette auditée (2300–2800 → 2550) ; marge & frais =
#: marge promoteur (9 %) + frais annexes (12 %). Plus jamais de constante autonome ici.


def _defauts_calculette() -> tuple[float, float]:
    h = Hypotheses.charger()
    cout = round((h.cout_construction_m2_bas + h.cout_construction_m2_haut) / 2)
    marge_frais = round((h.marge_promoteur_pct + h.frais_annexes_pct) * 100)
    return float(cout), float(marge_frais)


CALCULETTE_COUT_DEFAUT_M2, CALCULETTE_MARGE_FRAIS_DEFAUT_PCT = _defauts_calculette()


def bilan_params_defaut() -> dict:
    """M22-F C1 — LA source d'hypothèses par défaut, UNIQUE pour tous les documents
    (calculette, Dossier banquier, Argumentaire). Injectée comme `bilan_params` dans
    `compute_bilan` : coût = milieu de la fourchette auditée du YAML (2550 €/m² SDP),
    marge & frais agrégés 21 % du CA (honoraires et frais financiers neutralisés car
    agrégés). Deux documents générés avec ces défauts sur la même parcelle DOIVENT
    porter les mêmes totaux (test l'atteste)."""
    return {
        "cout_construction_m2_sdp": CALCULETTE_COUT_DEFAUT_M2,
        "marge_cible_pct": CALCULETTE_MARGE_FRAIS_DEFAUT_PCT,
        "honoraires_pct": 0.0,
        "frais_financiers_pct": 0.0,
    }


def compute_calculette(shab_vendable_m2: float, surface_terrain_m2: float, prix: dict,
                       cout_construction_m2: float, marge_frais_pct: float,
                       prix_demande_eur: float | None = None, mode: str = "charge") -> dict:
    """Charge foncière supportable — PURE, testable en isolation (aucun accès DB : `prix` est
    fourni). LIGNE ROUGE : les valeurs SOURCÉES (SDP vendable, prix de sortie DVF) viennent du
    moteur ; le coût de construction et la marge sont les HYPOTHÈSES SAISIES par le promoteur —
    jamais estimées par LABUSE. Réutilise `compute_bilan` (pas de ré-écriture de l'arithmétique) :
    on injecte les saisies comme `bilan_params` (coût au m² de plancher, marge+frais en % du CA,
    honoraires/frais financiers neutralisés car agrégés dans « marge & frais »). Le résultat est
    présenté « selon vos hypothèses ». Si `prix_demande_eur` est fourni : verdict d'achat
    (supportable si la charge foncière médiane ≥ prix demandé).

    M22-A — `mode="achat_max"` : la MÊME équation lue à l'envers, « à quel prix MAXIMUM puis-je
    acheter ce terrain pour que l'opération tienne ? ». Le prix d'achat max admissible EST la
    charge foncière supportable (identité arithmétique, AUCUN recalcul) — le mode ne change que
    la PRÉSENTATION : la dérivation ligne à ligne (prix de sortie DVF → CA → − marge & frais →
    − construction → − VRD → = foncier max) est exposée dans `steps`, la fourchette est
    réétiquetée `prix_achat_max` (les trois scénarios de prix de sortie DVF), et l'écart au prix
    demandé est rendu dans le sens de la négociation (demandé − max : + = surcoût, − = marge)."""
    # C1 — même squelette d'hypothèses que tous les documents (source unique), les saisies
    # de l'utilisateur remplacent les deux valeurs par défaut.
    bp = {**bilan_params_defaut(),
          "cout_construction_m2_sdp": float(cout_construction_m2),
          "marge_cible_pct": float(marge_frais_pct)}
    b = compute_bilan(float(shab_vendable_m2), float(surface_terrain_m2 or 0), prix,
                      Hypotheses.charger(), bilan_params=bp)
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
        # M22-F C9 (additif) : termes bruts du bilan (cc_bas/cc_haut, cout_vrd, coef) — le
        # diagramme en cascade de l'argumentaire les dessine sans RIEN recalculer.
        "calc": b.calc,
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
    if mode == "achat_max":
        out["mode"] = "achat_max"
        # Identité arithmétique EXPOSÉE (jamais deux moteurs) : prix d'achat max = charge foncière.
        out["prix_achat_max"] = dict(cf)
        # Dérivation ligne à ligne, dans le sens de la lecture inverse (prix de sortie → foncier).
        steps = [{"label": st.label, "formule": st.formule, "valeur": st.valeur,
                  "source": st.source, "prov": st.prov} for st in (b.steps or [])]
        steps.append({
            "label": "Prix d'achat maximal admissible",
            "formule": "= la charge foncière supportable, lue comme un prix d'achat "
                       "(même équation : CA × (1 − marge & frais) − construction − VRD)",
            "valeur": f"médiane {_eur(cf['central'])} "
                      f"(fourchette {_eur(cf['bas'])} – {_eur(cf['haut'])})",
            "source": "dérivé", "prov": "derive"})
        out["steps"] = steps
        if prix_demande_eur:
            pd = float(prix_demande_eur)
            surcout = pd - cf["central"]                                # demandé − max admissible
            out["ecart_negociation"] = {
                "prix_demande_eur": round(pd),
                "prix_achat_max_eur": cf["central"],
                "demande_moins_max_eur": round(surcout),                # + = surcoût, − = marge
                "demande_moins_max_pct": round(100 * surcout / pd) if pd else None,
                "sens": "surcout" if surcout > 0 else "marge",
            }
    return out


# ═══════════════════ M33 — MODE B : RÉHABILITATION DU BÂTI EXISTANT ═══════════════════
# Lecture de fiche sur la POPULATION mode B (les 2 tiers déclassés bâti : saturé + révélé,
# arbitrage Vic 06/08 — 33 958 parcelles) : « ce bâti existant vaut au plus X à l'achat pour
# une opération de réhabilitation-revente ». MÊME sortie que le mode A (un prix d'achat max),
# mêmes conventions (coef CA = 1 − marge − frais, préséance prix secteur → commune), AUCUN
# tier touché, rien de persisté. Le coût travaux est un PARAMÈTRE CLIENT (aucune source
# Réunion fiable — le produit ne prétend pas le savoir) : le résultat est TOUJOURS Estimé
# (héritage strict : un bilan contenant un Estimé est Estimé — assumé au libellé).

#: paramètre client travaux (€/m² SHAB) — défaut arbitré Vic 06/08, TOUJOURS Estimé.
MODE_B_TRAVAUX_M2_DEFAUT = 1500.0
MODE_B_TRAVAUX_M2_MIN = 500.0
MODE_B_TRAVAUX_M2_MAX = 4000.0
#: tiers de la population mode B (arbitrage Vic 06/08) — zone PLU INFORMATIVE, jamais ABSENT.
MODE_B_TIERS = ("declasse_bati_sature", "declasse_bati_revele")
#: M59-P1 (Q4) — seuil de pertinence : sous cette SHAB, une thèse de réhabilitation n'a pas
#: de sens (bilan travaux/revente sur trop peu de surface). La section ne montre PAS le calcul,
#: elle DIT « bâti trop petit » (mesure P0 : 1 851 parcelles / 5,5 % sous ce seuil).
MODE_B_SHAB_MIN = 50.0


def _prix_bati_local(session: Session, idu: str) -> dict | None:
    """Prix de sortie BÂTI local (€/m² habitable) — médianes DVF maison/appartement,
    préséance SECTEUR → repli COMMUNE (même logique de préséance que le mode A ;
    le niveau retenu est tracé et étiqueté). Seuil d'effectif LU de la config
    (M103 P1 — seuils_effectif.mode_b_prix_local, plus jamais en dur). None si aucun prix."""
    from ..marche_service import seuil_effectif_local
    n_min = seuil_effectif_local("mode_b_prix_local", 3)
    r = session.execute(text(
        "SELECT max(mediane_prix_m2) AS prix FROM dvf_secteur_medianes "
        "WHERE secteur = :s AND type_bien IN ('maison','appartement') AND n_ventes >= :n"),
        {"s": idu[:10], "n": n_min}).mappings().first()
    if r and r["prix"]:
        return {"prix_m2": float(r["prix"]), "niveau": "secteur",
                "libelle": f"médiane DVF maison/appartement du secteur (n ≥ {n_min})"}
    r = session.execute(text(
        "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY mediane_prix_m2) AS prix "
        "FROM dvf_secteur_medianes WHERE left(secteur, 5) = :c "
        "AND type_bien IN ('maison','appartement') AND n_ventes >= :n"),
        {"c": idu[:5], "n": n_min}).mappings().first()
    if r and r["prix"]:
        return {"prix_m2": float(r["prix"]), "niveau": "commune",
                "libelle": "médiane DVF maison/appartement de la commune (repli — pas assez "
                           "de ventes au secteur)"}
    return None


def _prix_terrain_local(session: Session, idu: str) -> dict | None:
    """M59-P1 (Q1) — prix du TERRAIN NU (€/m²) du secteur, MÊME logique de préséance que le bâti
    (secteur → repli commune) mais type_bien='terrain'. Seuil d'effectif LU de la config (M103
    P1). Sert UNIQUEMENT la comparaison « terrain nu au prix du secteur » (jamais le calcul
    réhab, qui reste sur la SHAB). None si aucune médiane terrain locale."""
    from ..marche_service import seuil_effectif_local
    n_min = seuil_effectif_local("mode_b_prix_local", 3)
    r = session.execute(text(
        "SELECT max(mediane_prix_m2) AS prix FROM dvf_secteur_medianes "
        "WHERE secteur = :s AND type_bien = 'terrain' AND n_ventes >= :n"),
        {"s": idu[:10], "n": n_min}).mappings().first()
    if r and r["prix"]:
        return {"prix_m2": float(r["prix"]), "niveau": "secteur",
                "libelle": f"médiane DVF terrain du secteur (n ≥ {n_min})"}
    r = session.execute(text(
        "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY mediane_prix_m2) AS prix "
        "FROM dvf_secteur_medianes WHERE left(secteur, 5) = :c "
        "AND type_bien = 'terrain' AND n_ventes >= :n"),
        {"c": idu[:5], "n": n_min}).mappings().first()
    if r and r["prix"]:
        return {"prix_m2": float(r["prix"]), "niveau": "commune",
                "libelle": "médiane DVF terrain de la commune (repli)"}
    return None


def _porte_mode_b(session: Session, idu: str, tier: str) -> str | None:
    """M101 A2 (arbitrage Vic) — la PORTE réelle du mode B, expliquée en français lisible,
    calée mot à mot sur la règle mesurée (AUDIT_M101 §A1.1), jamais au-delà. POINT UNIQUE :
    la fiche, les 4 documents (rehab_bloc) et l'export lisent cette phrase d'ici. Les caches
    (parcel_bati_revele / parcel_filtre_bati) restent la preuve brute, non réécrite."""
    if tier == "declasse_bati_revele":
        # garde-source M90 : table absente (base de test, install partielle) = pas de phrase
        # inventée, jamais un crash — le garde le DIT par l'absence, au point unique.
        if not session.execute(text("SELECT to_regclass('parcel_bati_revele') IS NOT NULL")).scalar():
            return None
        emprise = session.execute(text(
            "SELECT emprise_cosia_m2 FROM parcel_bati_revele WHERE idu = :i"), {"i": idu}).scalar()
        m2 = f" (~{round(float(emprise))} m²)" if emprise else ""
        return (f"L'image aérienne 2025 montre un bâtiment{m2} que les bases cartographiques "
                "n'ont pas encore enregistré — le terrain n'est pas nu.")
    if tier == "declasse_bati_sature":
        if not session.execute(text("SELECT to_regclass('parcel_filtre_bati') IS NOT NULL")).scalar():
            return None                        # garde-source M90 (cf. ci-dessus)
        row = session.execute(text(
            "SELECT ratio_pct, motif FROM parcel_filtre_bati WHERE idu = :i"),
            {"i": idu}).mappings().first()
        if row is None:
            return None                        # cache absent : pas de phrase inventée
        if (row["motif"] or "").startswith("SDP saturée"):
            return ("La surface constructible autorisée par le PLU est déjà consommée "
                    "par le bâti existant.")
        ratio = round(float(row["ratio_pct"] or 0))
        if ratio > 40:
            return (f"Le bâti existant occupe {ratio} % du terrain (mesuré sur BD TOPO et "
                    "image aérienne 2025) — il ne reste pas d'assiette pour construire.")
        return (f"Le terrain est bâti ({ratio} % d'emprise) d'un bâti récent ou d'année "
                "inconnue, et n'est pas divisible — pas d'assiette exploitable.")
    return None


def compute_mode_b(session: Session, idu: str, *,
                   travaux_m2: float | None = None,
                   run: str | None = None,
                   regime_locatif: str | None = None,
                   loyer_marche_m2: float | None = None,
                   rendement_cible_pct: float | None = None) -> dict:
    """Bilan MODE B d'une parcelle — dict de fiche, jamais persisté.

    `disponible=False` + motif hors population ou données manquantes (ABSENT explicite).
    Bilan négatif au paramètre courant : DIT honnêtement (`negatif=True`, message), jamais
    un prix négatif servi comme actionnable, jamais un masquage silencieux."""
    from ..scoring.score_v_constants import Q_A_RUN_LABEL
    run = run or Q_A_RUN_LABEL
    tier = session.execute(text(
        "SELECT tier FROM parcel_p_score_v2 WHERE run_id = :r AND parcelle_id = :i"),
        {"r": run, "i": idu}).scalar()
    if tier not in MODE_B_TIERS:
        return {"disponible": False,
                "motif": "hors population mode B (réservé aux parcelles déclassées pour "
                         "cause de bâti : saturé ou révélé)"}
    porte = _porte_mode_b(session, idu, tier)   # M101 A2 — la porte réelle, en français lisible
    emprise = session.execute(text(
        "SELECT emprise_bati_m2 FROM p_model_bati WHERE idu = :i"), {"i": idu}).scalar()
    if not emprise or float(emprise) < 20:
        return {"disponible": False, "porte": porte,
                "motif": "Absent — emprise bâtie non mesurable (< 20 m²) : pas de bilan inventé"}
    px = _prix_bati_local(session, idu)
    if px is None:
        return {"disponible": False, "porte": porte,
                "motif": "Absent — aucun prix de sortie bâti local (DVF) : pas de bilan inventé"}

    hyp = Hypotheses.charger()
    pid = session.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
    from .residuel import _niveaux_existants   # POINT UNIQUE du calcul de niveaux (M33)
    niveaux, niveaux_reels = _niveaux_existants(session, pid, hyp.niveaux_bati_existant_defaut)

    travaux_est_defaut = travaux_m2 is None
    travaux = float(travaux_m2) if travaux_m2 is not None else MODE_B_TRAVAUX_M2_DEFAUT
    travaux = min(max(travaux, MODE_B_TRAVAUX_M2_MIN), MODE_B_TRAVAUX_M2_MAX)
    coef_ca = round(1.0 - (hyp.marge_promoteur_pct + hyp.frais_annexes_pct), 4)

    emprise = float(emprise)
    sdp_exist = emprise * niveaux
    shab = sdp_exist / hyp.coef_plancher_habitable

    # M59-P1 (Q4) — seuil de pertinence : sous MODE_B_SHAB_MIN, on NE sert PAS le calcul
    # (thèse de réhabilitation non pertinente) mais on le DIT (jamais un tiroir muet).
    if shab < MODE_B_SHAB_MIN:
        return {"disponible": True, "trop_petit": True, "porte": porte,
                "shab_rehabilitable_m2": round(shab),
                "motif": f"Bâti trop petit (SHAB ~{round(shab)} m²) pour une thèse de réhabilitation."}

    ca = shab * px["prix_m2"] * coef_ca
    cout_travaux = shab * travaux
    achat_max = ca - cout_travaux

    # M59-P1 (Q1) — COMPARAISON terrain nu (calcul existant : DVF terrain secteur × surface,
    # Estimé). N'entre PAS dans achat_max (la formule réhab reste sur la SHAB) : c'est un
    # repère affiché. `porte_par_terrain` = le foncier vaut plus que ce que le bâti justifie.
    surface_parcelle = session.execute(text(
        "SELECT surface_m2 FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
    px_terrain = _prix_terrain_local(session, idu)
    terrain_nu = None
    if px_terrain and surface_parcelle:
        valeur_terrain = round(float(surface_parcelle) * px_terrain["prix_m2"])
        terrain_nu = {
            "valeur_eur": valeur_terrain, "valeur_libelle": _eur(valeur_terrain),
            "prix_m2": round(px_terrain["prix_m2"]), "surface_m2": round(float(surface_parcelle)),
            "niveau": px_terrain["niveau"], "libelle": px_terrain["libelle"],
            "etiquette": "Estimé",
        }
    porte_par_terrain = bool(terrain_nu and terrain_nu["valeur_eur"] > achat_max)

    # M44 — SORTIE LOCATIVE, côte à côte avec la revente, JAMAIS fusionnée (point de calcul unique
    # labuse.faisabilite.defisc). Bilan au plafond réglementaire Sourcé (défaut) ou loyer marché Estimé.
    try:
        from . import defisc
        sortie_locative = defisc.sortie_locative(
            shab, cout_travaux, regime=regime_locatif,
            loyer_marche_m2=loyer_marche_m2, rendement_cible_pct=rendement_cible_pct)
    except Exception:  # noqa: BLE001 — le locatif ne casse jamais le mode B
        sortie_locative = None

    return {
        "disponible": True,
        "trop_petit": False,
        "population_tier": tier,
        "porte": porte,           # M101 A2 — la porte réelle du mode B, en français lisible
        # M59-P1 (Q1) — surface du foncier (toujours servie, pour la ligne « hors valeur du
        # terrain »), repère « terrain nu au prix du secteur » (Estimé) + drapeau « valeur portée
        # par le terrain » (le foncier vaut plus que ce que le bâti justifie).
        "surface_parcelle_m2": round(float(surface_parcelle)) if surface_parcelle else None,
        "terrain_nu": terrain_nu,
        "porte_par_terrain": porte_par_terrain,
        # M44 — sortie LOCATIVE (plafond Sourcé / marché Estimé). None si indisponible. La revente
        # reste au niveau ci-dessous (achat_max_eur) : les deux sorties côte à côte, jamais fusionnées.
        "sortie_locative": sortie_locative,
        # HÉRITAGE STRICT (arbitrage Vic) : le paramètre travaux est TOUJOURS Estimé →
        # le prix d'achat max réhab n'est JAMAIS Sourcé — assumé au libellé.
        "etiquette": "Estimé",
        "achat_max_eur": round(achat_max),
        # M37 Lot 0.1 — POINT DE FORMATAGE UNIQUE du montant mode B : au k€ (un Estimé à
        # l'euro près contredit son étiquette). Toutes les surfaces lisent ce libellé.
        "achat_max_libelle": _eur(achat_max),
        "negatif": achat_max <= 0,
        "message_negatif": ((("bilan négatif au paramètre par défaut — ajuster le coût "
                              "travaux selon l'état constaté") if travaux_est_defaut else
                             (f"bilan négatif à {round(travaux)} €/m² de travaux — le marché "
                              "local n'absorbe pas cette hypothèse"))
                            if achat_max <= 0 else None),
        "composantes": {
            "surface": {
                "emprise_bati_m2": round(emprise),
                "niveaux": round(niveaux, 1),
                "niveaux_reels": niveaux_reels,
                "niveaux_etiquette": ("Sourcé — étages/hauteur BD TOPO"
                                      if niveaux_reels else
                                      "Estimé — 1 niveau supposé (hauteur non mesurée)"),
                "sdp_existante_m2": round(sdp_exist),
                "shab_rehabilitable_m2": round(shab),
                "source_emprise": "max(BD TOPO éd. 2026-06-15, CoSIA PVA 2025)",
                "etiquette_emprise": "Sourcé",
            },
            "prix_sortie": {
                "prix_m2": round(px["prix_m2"]),
                "niveau": px["niveau"], "libelle": px["libelle"],
                "etiquette": "Sourcé (DVF)",
                # M59-P1 (Q3) — périmètre DIT (pas d'harmonisation des moteurs, juste l'honnêteté) :
                # le mode B lit des médianes sectorielles pré-agrégées, SANS rayon adaptatif (≠ le
                # tiroir Marché qui, lui, élargit 500→1500 m).
                "perimetre": "médiane secteur→commune, sans rayon adaptatif",
            },
            "travaux": {
                "hypothese_m2": round(travaux),
                "defaut_m2": round(MODE_B_TRAVAUX_M2_DEFAUT),
                "bornes": [round(MODE_B_TRAVAUX_M2_MIN), round(MODE_B_TRAVAUX_M2_MAX)],
                "etiquette": "ESTIMÉ",
                "libelle": (f"coût travaux : hypothèse ~{round(travaux)} €/m² (ESTIMÉ) — "
                            "à ajuster selon l'état constaté du bâti"),
            },
            "frais_marge": {
                "coef_ca": coef_ca,
                "libelle": f"marge {hyp.marge_promoteur_pct:.0%} + frais {hyp.frais_annexes_pct:.0%} "
                           "du CA (mêmes conventions que le mode A)",
                "etiquette": "Estimé (conventions de bilan)",
            },
        },
        "formule": ("prix d'achat max réhab = SHAB × prix de sortie × coef CA − SHAB × travaux "
                    f"= {round(shab)} × {round(px['prix_m2'])} × {coef_ca} − "
                    f"{round(shab)} × {round(travaux)}"),
        "avertissement": ("Estimé — ni un prix ni une promesse ; sans donnée d'état du bâti, "
                          "l'incertitude est portée par le paramètre travaux. Sortie = revente "
                          "(homogène mode A)."),
    }
