"""Analyse LABUSE V2 — cœur par scénario (ALGO-FIX-1).

Mandat ALGO-FIX-1 (décisions de Vic D1–D10) + spécification
`docs/audit-2026-11/algo-fix-1/LABUSE_DOSSIER_V2/01_SPECIFICATION_ALGORITHME.md`
(§4, 5, 7, 8, 9, 10, 12, 13.2). Ce module est le MOTEUR PUR, miroir fidèle du moteur de
référence pédagogique `04_MOTEUR_REFERENCE.cjs`, adapté au dépôt :

  · aucune base, aucun SIG, aucun modèle ML — `evaluate(record, opts)` est une fonction PURE
    d'un `ScenarioRecord` déjà normalisé (l'adaptateur `scenarios_v2_build` le remplit depuis les
    caches réels) ;
  · deux familles de sorties SÉPARÉES (spec §3) : le Signal de mutation (inchangé, seulement
    rapporté — D6) et le résultat de scénario foncier (statut, cause, quantités, bande,
    vigilances) ;
  · les STATUTS sont exclusifs par scénario et par instantané, dans l'ordre de décision §5.1 ;
  · les BANDES (décision Vic D1/D2) restent — barème de capacité actuel × coefficients pente /
    forme / accès, SANS le coefficient bâti (D2) et SANS le ×0,5 AU (D3, traité en « À différer »
    avant toute bande). Une inconnue qui ferait basculer la bande ⇒ « À vérifier », bande
    provisoire conservée dans le détail (D4).

Ce qui N'est PAS ici (frontières dures du mandat) :
  · le Signal n'est ni recalculé ni modifié — on relaie son état servi (D6, spec §12) ;
  · aucune nouvelle note globale 0–100 (spec §1) : la bande décrit UN scénario, nommée ;
  · aucune règle de taille « >500 m² → NC » (D5, spec §9.3) ni « ×0,65 table rase » (D2).

Déterministe : mêmes entrées ⇒ mêmes sorties. Les constantes de barème viennent de
`config/score_labuse.yaml` (réutilisées via `score_labuse`), jamais réinventées ici.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import score_labuse as sl

VERSION = "ALGO-LABUSE-2-1.0"

# ── statuts exclusifs par scénario (spec §5, décision Vic D3) ─────────────────
# Code interne → libellé client. Les libellés suivent §5 + §11.2 (« à employer »).
LABELS = {
    "ESTIMATED": "Capacité théorique estimée",
    "PRESTUDY": "Préétude à mener",
    "COMPUTE_PENDING": "Calcul à compléter",        # quantités du scénario pas encore calculées
    "TO_VERIFY": "Analyse à compléter",
    "DEFERRED": "À différer",
    "NO_MARGIN": "Aucun ajout identifié",
    "OUTSIDE_OBJECTIVE": "Hors de ce projet",
}
# États de la vue Prospection vente (le Signal domine ; spec §6.3).
SIGNAL_LABELS = {
    "AVAILABLE": "Signal de mutation disponible",
    "TO_VERIFY": "Signal à vérifier",
    "NOT_AVAILABLE": "Signal non évalué",
    "OUT_OF_SCOPE": "Hors du domaine du modèle",
}
# Ordre des groupes en vue « Tous » (spec §10.1). Les inconnues et les différées sont des files
# de travail distinctes, pas des « moins bonnes » : la hiérarchie est AFFICHÉE, pas cachée.
GROUP_ORDER = {
    "ESTIMATED": 0, "PRESTUDY": 0,
    "COMPUTE_PENDING": 1,                            # file de travail « à chiffrer » (≠ données)
    "TO_VERIFY": 2, "DEFERRED": 3, "NO_MARGIN": 4, "OUTSIDE_OBJECTIVE": 5,
}
SIGNAL_GROUP_ORDER = {
    "SIGNAL_AVAILABLE": 0, "SIGNAL_TO_VERIFY": 1,
    "SIGNAL_NOT_AVAILABLE": 2, "SIGNAL_OUT_OF_SCOPE": 3,
}
# Rang des bandes pour le tri potentiel « bande d'abord » (D10). HC n'existe plus en V2 (une
# exclusion dure devient « Hors de ce projet » avec sa preuve) ; « 0 » reste à part.
_BANDE_RANG = {"A": 0, "B": 1, "C": 2, "D": 3, "0": 4, "NC": 5}


# ── helpers numériques (mêmes gardes que le moteur de référence) ─────────────
def _finite(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _nonneg(v) -> bool:
    return _finite(v) and v >= 0


def _present(v) -> bool:
    return v is not None


def _norm_id(v) -> str:
    return v.strip().upper() if isinstance(v, str) else ""


def format_quantite(v) -> str:
    """Spec §10.2 : une petite valeur strictement positive ne s'affiche jamais « 0 m² » par
    arrondi. Valeur absente ≠ zéro (« Non calculé »)."""
    if not _finite(v):
        return "Non calculé"
    if 0 < v < 1:
        return "<1 m²"
    if -1 < v < 0:
        return "−<1 m²"
    return f"{v:,.0f} m²".replace(",", " ")


# ── enregistrement d'entrée (rempli par l'adaptateur depuis les caches réels) ─
@dataclass
class ScenarioRecord:
    """Faits normalisés d'une parcelle, pour UN instantané. L'adaptateur garantit les unités
    (spec §4) ; ce moteur ne lit aucune base. NULL ≠ 0 partout."""
    id: str                                    # IDU (identifiant stable)
    area_m2: float | None = None               # surface terrain (ST_Area)
    perimeter_m: float | None = None           # périmètre (pour la forme en lame)
    geometry_status: str = "valid"             # valid / suspect / unavailable
    # Capacités (spec §4). C_rebuild = capacité totale du nouveau projet ; E = SDP existante ;
    # residual = R = max(0, C − E) (déjà cachée). Toutes en SDP m², base compatible (§4).
    capacity_rebuild_m2: float | None = None   # C_rebuild (= sdp_max du PLU en V2 initiale)
    existing_m2: float | None = None           # E
    residual_m2: float | None = None           # R (résiduel conservation, caché)
    capacity_bounds: object | None = None       # enveloppe documentée {min,max,source} ou None
    existing_bounds: object | None = None
    # Éligibilité logement (spec §4) : scénarios de logement seulement.
    eligibility: str = "allowed"               # allowed / incompatible / unknown
    eligibility_proof: dict | None = None       # {rule, source, portion, date} si incompatible prouvé
    horizon: str = "now"                       # now / deferred / unknown
    future_capacity_m2: float | None = None    # capacité conditionnelle (AU différée)
    # Hauteur critique (bloque une SDP mais pas le repérage division — spec §7.3).
    height_status: str = "present"             # present / missing
    height_required: bool = True
    # Difficultés physiques = points de vigilance SOURCÉS (spec §10.3) — jamais une note cachée.
    slope_deg: float | None = None
    access: str | None = None                  # verdict cascade 'acces' ('PASS' = voie non identifiée)
    access_known: bool = True                  # un verdict d'accès EXISTE (POSITIVE/PASS) vs aucun
    built_coverage_pct: float | None = None    # emprise / plafond (dénominateur explicite, §4)
    calc_reliable: bool = True                 # le calcul d'assiette est fiable (vs chemin de repli)
    calc_doubt_reason: str | None = None       # cause du doute (ex. assiette de repli non découpée)
    # Zonage par portion (spec §9.2 / D9) : quelle portion produit la capacité.
    zone_main: str | None = None
    zone_parts: list | None = None             # [{zone, area_m2}] — portion productive identifiable
    # Signal servi, RELAYÉ tel quel (D6 ; jamais recalculé ici).
    signal_status: str = "NOT_AVAILABLE"       # AVAILABLE / TO_VERIFY / NOT_AVAILABLE / OUT_OF_SCOPE
    signal_p: float | None = None
    signal_niveau: str | None = None           # fort / moyen / faible (servi)
    signal_reason: str | None = None
    # Traçabilité / vigilances déjà connues (capacité estimée, cause moteur brute…).
    capacity_estimated: bool = False
    cause_engine: str | None = None            # cause brute du moteur, pour la traçabilité
    diagnostic: dict | None = None             # diagnostic géométrique (terrain exigu, D5)
    notes: list | None = None                  # vigilances pré-constituées par l'adaptateur
    provenance: str = "cache"                  # 'live' (calcul unique) / 'cache' (run servi)
    assiette_source: str | None = None         # 'gabarit' / 'residuel_legacy', du MÊME calcul


@dataclass
class ScenarioResult:
    id: str
    mode: str
    scenario: str
    status: str
    label: str
    tone: str
    horizon: str
    quantities: dict
    bounds: dict | None
    band: str | None
    score: int | None
    band_provisional: str | None
    cause_codes: list
    vigilance: list
    zone_portion: dict | None
    signal: dict
    rank_value: float | None
    band_rank: int
    analysis_version: str = VERSION
    details: dict = field(default_factory=dict)


# ── options (validation stricte, comme le moteur de référence) ───────────────
def _options(raw: dict | None) -> dict:
    s = dict(raw or {})
    mode = s.get("mode", "potential")
    scenario = s.get("scenario", "keep")
    default_sort = ("signal" if mode == "sale"
                    else "area" if scenario == "divide" else "capacity")
    opts = {"mode": mode, "scenario": scenario, "sort": s.get("sort", default_sort),
            "bareme": s.get("bareme")}
    if opts["mode"] not in ("sale", "potential"):
        raise ValueError("mode invalide")
    if opts["scenario"] not in ("keep", "rebuild", "divide"):
        raise ValueError("scenario invalide")
    if opts["sort"] not in ("signal", "capacity", "gain", "area", "id"):
        raise ValueError("sort invalide")
    if opts["sort"] == "signal" and opts["mode"] != "sale":
        raise ValueError("tri Signal réservé à la prospection")
    if opts["sort"] == "gain" and (opts["mode"] != "potential" or opts["scenario"] != "rebuild"):
        raise ValueError("tri gain net réservé à la reconstruction")
    if opts["sort"] == "capacity" and (opts["mode"] == "sale" or opts["scenario"] == "divide"):
        raise ValueError("tri capacité réservé aux scénarios de capacité")
    return opts


def _bareme(opts: dict) -> dict:
    b = opts.get("bareme")
    if b is None:
        b, _ = sl.charger_bareme()
        opts["bareme"] = b
    return b


# ── bande (décision Vic D1/D2) : barème(quantité) × pente × forme × accès ─────
# PAS de coefficient bâti (D2 : l'existant est déjà soustrait en conservation ; en reconstruction
# la démolition est un point de vigilance chiffré, jamais un malus). PAS de ×0,5 AU (D3).
def _coef_physique(rec: ScenarioRecord, fa: dict) -> tuple[float, dict]:
    f_pente, pente_pct = sl._f_pente(rec.slope_deg, fa)
    f_forme = sl._f_forme(rec.area_m2, rec.perimeter_m, fa)
    f_acces = sl._f_acces(rec.access, fa)
    coef = max(float(fa.get("plancher", 0.4)), f_pente * f_forme * f_acces)
    return coef, {"f_pente": round(f_pente, 4), "f_forme": round(f_forme, 4),
                  "f_acces": round(f_acces, 4), "pente_pct": pente_pct}


def _bande_pour(quantite: float | None, coef: float, bareme: dict) -> tuple[int, str]:
    cap = bareme.get("capacite", {})
    # au_classe=None ⇒ multiplicateur AU neutre (le différé est traité AVANT la bande, D3).
    points, _ = sl._bareme_capacite(quantite, None, cap)
    score = min(100, round(points * coef))
    return score, sl.bande_de_score(score, bareme)


def _inconnues_physiques(rec: ScenarioRecord) -> list[str]:
    """Les facteurs physiques réellement INCONNUS (pas « neutres »), pour D4.

    - **pente** : inconnue si `slope_deg is None` (RGE ALTI non mesuré sur la parcelle).
    - **forme** : inconnue si aire OU périmètre manquent (sinon la lame se calcule — c'est connu).
    - **accès** : inconnu SEULEMENT si aucun verdict de cascade n'existe (`access_known=False`).
      Dans le run servi, CHAQUE parcelle porte un verdict `acces` (POSITIVE = voie identifiée, ou
      PASS = voie « non identifiée ») : « non identifié » (PASS) est un fait MESURÉ, pas une
      inconnue ; l'ensemble « inconnu » (aucun verdict) est donc vide aujourd'hui. On garde
      néanmoins la branche pour rester correct si une couche d'accès partielle apparaissait."""
    inc = []
    if rec.slope_deg is None:
        inc.append("pente")
    if rec.area_m2 is None or rec.perimeter_m is None:
        inc.append("forme")
    if not rec.access_known:
        inc.append("acces")
    return inc


def _bande_sensible_a_inconnue(quantite: float | None, rec: ScenarioRecord,
                               bareme: dict) -> tuple[bool, str, int]:
    """D4 — une inconnue ne fabrique pas une bande. Test de sensibilité avec les valeurs de la
    configuration : on compare la bande en neutralisant les inconnues à la bande calculée en
    remplaçant CHAQUE facteur inconnu (pente, forme, accès) par sa valeur de configuration la plus
    défavorable (les facteurs connus restent tels quels). Si la bande change ⇒ sensible : la ligne
    passe « À vérifier » et la **bande provisoire** (la bande neutre, la mieux documentée possible)
    est conservée au détail. Jamais de valeur défavorable inventée pour un facteur connu (§8.1)."""
    fa = bareme.get("faisabilite", {})
    coef_neutre, _ = _coef_physique(rec, fa)
    score_neutre, bande_neutre = _bande_pour(quantite, coef_neutre, bareme)
    inconnues = _inconnues_physiques(rec)
    if not inconnues:
        return False, bande_neutre, score_neutre
    f_pente = (float(fa.get("pente_au_dela", 0.6)) if "pente" in inconnues
               else sl._f_pente(rec.slope_deg, fa)[0])
    f_forme = (float(fa.get("forme", {}).get("facteur", 0.8)) if "forme" in inconnues
               else sl._f_forme(rec.area_m2, rec.perimeter_m, fa))
    f_acces = (float(fa.get("acces_non_identifie", 0.85)) if "acces" in inconnues
               else sl._f_acces(rec.access, fa))
    coef_defav = max(float(fa.get("plancher", 0.4)), f_pente * f_forme * f_acces)
    _, bande_defav = _bande_pour(quantite, coef_defav, bareme)
    return bande_defav != bande_neutre, bande_neutre, score_neutre


# ── Signal (D6) : relayé, jamais recalculé ; seules les gardes de validité jouent ────────────
def _eval_signal(rec: ScenarioRecord) -> dict:
    st = str(rec.signal_status or "NOT_AVAILABLE").upper()
    base = {"status": st, "p": None, "niveau": None,
            "label": SIGNAL_LABELS.get(st, "Signal non évalué"), "reason": rec.signal_reason}
    if st == "OUT_OF_SCOPE":
        return base
    if st == "NOT_AVAILABLE":
        # Spec §6.3 : une absence simple ne devient pas une probabilité zéro ni « Faible ».
        base["reason"] = rec.signal_reason or "SIGNAL_NON_CALCULE"
        return base
    if st == "TO_VERIFY":
        base["reason"] = rec.signal_reason or "SIGNAL_A_VERIFIER"
        return base
    if st != "AVAILABLE":
        base["status"] = "TO_VERIFY"
        base["label"] = SIGNAL_LABELS["TO_VERIFY"]
        base["reason"] = "SIGNAL_STATUT_INVALIDE"
        return base
    # AVAILABLE : la probabilité servie doit être finie dans [0,1] (spec §6.3). Jamais d'écrêtage
    # silencieux pour « rendre valide » (D8). Absente ⇒ non évalué, pas zéro.
    if not _present(rec.signal_p):
        return {"status": "NOT_AVAILABLE", "p": None, "niveau": None,
                "label": SIGNAL_LABELS["NOT_AVAILABLE"], "reason": "PROBABILITE_SERVIE_ABSENTE"}
    if not _finite(rec.signal_p) or rec.signal_p < 0 or rec.signal_p > 1:
        return {"status": "TO_VERIFY", "p": None, "niveau": None,
                "label": SIGNAL_LABELS["TO_VERIFY"], "reason": "PROBABILITE_SERVIE_INVALIDE"}
    return {"status": "AVAILABLE", "p": rec.signal_p, "niveau": rec.signal_niveau,
            "label": SIGNAL_LABELS["AVAILABLE"], "reason": rec.signal_reason or "PROBABILITE_SERVIE"}


# ── inspection des bornes (enveloppes documentées — spec §8.2) ───────────────
def _inspect_bound(bound, central) -> dict:
    if not _present(bound):
        return {"present": False}
    if isinstance(bound, (list, tuple)):
        bmin, bmax, src, doc = bound[0], bound[1], None, None
    else:
        bmin, bmax = bound.get("min"), bound.get("max")
        src, doc = bound.get("source"), bound.get("documented")
    if not _nonneg(bmin) or not _nonneg(bmax) or bmin > bmax:
        return {"present": True, "error": "BORNES_INVALIDES"}
    if _finite(central) and (central < bmin or central > bmax):
        return {"present": True, "error": "ESTIMATION_CENTRALE_HORS_BORNES"}
    if not src or doc is not True:
        return {"present": True, "error": "BORNES_NON_DOCUMENTEES"}
    return {"present": True, "min": bmin, "max": bmax, "source": src}


# ── portion productive + quantités provisoires (consultables même en « À vérifier ») ─────────
def _zone_portion(rec: ScenarioRecord) -> dict | None:
    """Spec §9.2 / D9 : la portion CONSTRUCTIBLE (U/AU) qui produit la capacité, pas la majoritaire."""
    if rec.zone_parts:
        constr = [p for p in rec.zone_parts if p.get("constructible") and _nonneg(p.get("area_m2"))]
        if constr:
            prod = max(constr, key=lambda p: p.get("area_m2") or 0)
            return {"zone": prod.get("zone"), "area_m2": prod.get("area_m2")}
    if rec.zone_main:
        return {"zone": rec.zone_main, "area_m2": rec.area_m2}
    return None


def evaluate(record, options=None) -> ScenarioResult:
    opts = _options(options)
    rec = record if isinstance(record, ScenarioRecord) else ScenarioRecord(**dict(record or {}))
    bareme = _bareme(opts)
    signal = _eval_signal(rec)
    res = ScenarioResult(
        id=_norm_id(rec.id), mode=opts["mode"], scenario=opts["scenario"],
        status="TO_VERIFY", label=LABELS["TO_VERIFY"], tone="amber",
        horizon=rec.horizon or "unknown",
        quantities={"additional": None, "project_total": None, "existing": None,
                    "net_signed": None, "conditional_future": None},
        bounds=None, band=None, score=None, band_provisional=None,
        cause_codes=[], vigilance=list(rec.notes or []), zone_portion=None,
        signal=signal, rank_value=None, band_rank=_BANDE_RANG["NC"],
        details={"provenance": rec.provenance, "assiette_source": rec.assiette_source})

    def cause(code):
        if code and code not in res.cause_codes:
            res.cause_codes.append(code)

    def vig(msg):
        if msg and msg not in res.vigilance:
            res.vigilance.append(msg)

    def _rank(res_):
        # Spec §10.2 / D10. Valeurs absentes ⇒ None (après les connues), jamais zéro.
        if opts["sort"] == "id":
            return None
        if opts["sort"] == "area":
            return rec.area_m2 if _nonneg(rec.area_m2) else None
        if opts["mode"] == "sale":
            return res_.signal["p"] if res_.signal["status"] == "AVAILABLE" else None
        if opts["scenario"] == "divide":
            return rec.area_m2 if _nonneg(rec.area_m2) else None
        if res_.status == "DEFERRED":
            return None           # la capacité future conditionnelle ne sert pas de tri (spec §9.1)
        if opts["scenario"] == "rebuild":
            return (res_.quantities["net_signed"] if opts["sort"] == "gain"
                    else res_.quantities["project_total"])
        return res_.quantities["additional"]

    def finish(status, code=None, label=None):
        res.status = status
        res.label = label or LABELS.get(status, status)
        res.tone = ("green" if status == "ESTIMATED" else "blue" if status == "PRESTUDY"
                    else "amber" if status in ("TO_VERIFY", "DEFERRED") else "neutral")
        cause(code)
        if status in GROUP_ORDER:
            res.band_rank = _BANDE_RANG.get(res.band, _BANDE_RANG["NC"])
        res.rank_value = _rank(res)
        return res

    # ── Prospection vente (spec §6, D6) : le Signal commande, le foncier n'entre pas ─────────
    if opts["mode"] == "sale":
        # Aucun zonage, SDP ou facteur physique ne change le Signal de cette vue. Une parcelle
        # sans potentiel garde son Signal et reste visible (D6).
        st = signal["status"]
        res.status = "SIGNAL_" + st if st in ("AVAILABLE", "TO_VERIFY", "NOT_AVAILABLE") else "SIGNAL_OUT_OF_SCOPE"
        res.label = signal["label"]
        res.band_rank = SIGNAL_GROUP_ORDER.get(res.status, 3)
        if st == "AVAILABLE":
            res.tone = ("green" if signal["niveau"] == "fort"
                        else "blue" if signal["niveau"] == "moyen" else "neutral")
            res.rank_value = signal["p"]
        else:
            res.tone = "amber" if st == "TO_VERIFY" else "neutral"
            res.rank_value = None
        cause(signal["reason"])
        return res

    # ── Potentiel foncier — décision §5.1, dans l'ordre ──────────────────────────────────────
    # 1. Identifiant, unités, qualité géométrique nécessaire au scénario.
    if not res.id:
        return finish("TO_VERIFY", "ID_ABSENT")
    # Difficultés physiques = vigilances SOURCÉES, jamais un coefficient caché (spec §10.3).
    if rec.slope_deg is None:
        vig("Pente non renseignée ; aucune pente favorable ou défavorable imputée.")
    elif not _nonneg(rec.slope_deg):
        vig("Valeur de pente à vérifier ; aucun coefficient appliqué.")
    elif math.tan(math.radians(rec.slope_deg)) * 100.0 > 30:
        vig("Pente supérieure à 30 % : difficulté physique à étudier.")
    if rec.access == "PASS":
        vig("Accès à la voie non identifié : desserte à vérifier.")
    if rec.capacity_estimated:
        vig("Capacité estimée — zone PLU non calibrée finement.")

    if not _nonneg(rec.area_m2) or rec.area_m2 == 0:
        return finish("TO_VERIFY", "SURFACE_PARCELLE_INVALIDE")
    if rec.geometry_status != "valid":
        # Une grande comme une petite géométrie suspecte est à vérifier (spec §9.3 : pas de règle
        # de taille). Si un diagnostic nomme la cause réelle, on l'ajoute en vigilance.
        if rec.diagnostic:
            res.details["diagnostic"] = rec.diagnostic
            for m in rec.diagnostic.get("constats", []):
                vig(m)
        return finish("TO_VERIFY",
                      "GEOMETRIE_SUSPECTE" if rec.geometry_status == "suspect"
                      else "GEOMETRIE_INDISPONIBLE")

    # Portion productive calculée tôt : disponible pour TOUS les statuts suivants (D9).
    res.zone_portion = _zone_portion(rec)
    if rec.zone_parts:
        res.details["zone_parts"] = rec.zone_parts

    def provisoire():
        """Rend consultables, SANS les servir comme sûres, les quantités et la bande provisoire
        d'une ligne « À vérifier » (avis Astra : chiffre provisoire consultable)."""
        C, E, R = rec.capacity_rebuild_m2, rec.existing_m2, rec.residual_m2
        if _present(C):
            res.quantities["project_total"] = C
        if _present(E):
            res.quantities["existing"] = E
        if _present(C) and _present(E):
            res.quantities["net_signed"] = C - E
        q = (R if _nonneg(R) else (max(0.0, C - E) if _present(C) and _present(E) else None))
        if _nonneg(q):
            res.quantities["additional"] = q
            _, bande, _score = _bande_sensible_a_inconnue(q, rec, bareme)
            res.band_provisional = bande
            res.details["bande_provisoire"] = bande

    # 2. Preuve suffisante d'incompatibilité POUR CE projet (logement). Une simple famille de
    #    zone ou une absence de donnée n'est pas cette preuve (spec §5.1).
    if rec.eligibility == "incompatible":
        if rec.eligibility_proof and rec.eligibility_proof.get("verified"):
            res.details["eligibility_proof"] = rec.eligibility_proof
            return finish("OUTSIDE_OBJECTIVE", "INCOMPATIBILITE_LOGEMENT_PROUVEE",
                          "Hors de ce projet")
        return finish("TO_VERIFY", "PREUVE_INCOMPATIBILITE_NON_VERIFIEE")
    if rec.eligibility != "allowed":
        return finish("TO_VERIFY", "ELIGIBILITE_LOGEMENT_INCONNUE")

    # 3. Horizon. Caractère différé établi (AU fermée) ⇒ « À différer », AVANT toute bande (D3 / §9.1).
    if rec.horizon == "deferred":
        if _present(rec.future_capacity_m2) and not _nonneg(rec.future_capacity_m2):
            cause("CAPACITE_FUTURE_INVALIDE")
            vig("Hypothèse future invalide : quantité non servie ; le caractère différé reste établi.")
        res.quantities["conditional_future"] = (rec.future_capacity_m2
                                                 if _nonneg(rec.future_capacity_m2) else None)
        if _nonneg(rec.existing_m2):
            res.quantities["existing"] = rec.existing_m2
        vig("Capacité conditionnelle ; aucune date d'ouverture ni disponibilité actuelle inventée.")
        return finish("DEFERRED", "DISPONIBILITE_DIFFEREE")
    if rec.horizon != "now":
        provisoire()                      # capacité provisoire + bande provisoire consultables
        return finish("TO_VERIFY", "HORIZON_INCONNU")

    # 8/§7.3. Division pour logement en repérage ⇒ préétude (la hauteur manquante ne bloque pas ;
    # une assiette de repli douteuse ne bloque pas non plus un repérage documentaire).
    if opts["scenario"] == "divide":
        vig("Préétude documentaire : divisibilité, nombre de lots, accès individuels et "
            "viabilisation non calculés.")
        return finish("PRESTUDY", "PREETUDE_DIVISION_DOCUMENTAIRE")

    # 4-bis. Calcul d'assiette douteux (ex. assiette de repli non découpée aux contraintes
    # rédhibitoires partielles) ⇒ À vérifier, quelle que soit la surface (spec §9.3). La quantité
    # est conservée au détail, jamais servie comme une capacité sûre.
    if not rec.calc_reliable:
        if rec.calc_doubt_reason:
            vig(rec.calc_doubt_reason)
        provisoire()                      # chiffre provisoire consultable, jamais servi comme sûr
        return finish("TO_VERIFY", "CALCUL_ASSIETTE_DOUTEUX")

    # 4. Entrées critiques propres au scénario de capacité.
    if rec.height_status == "missing" and rec.height_required is not False:
        return finish("TO_VERIFY", "HAUTEUR_CRITIQUE_ABSENTE")

    # Portion productive déjà posée plus haut (res.zone_portion) — rien à recalculer ici.
    if opts["scenario"] == "keep":
        return _finish_keep(rec, opts, res, bareme, cause, vig, finish)
    return _finish_rebuild(rec, opts, res, bareme, cause, vig, finish)


def _bornes(rec, res, central_c, central_e, scenario, vig):
    """Enveloppes documentées (spec §8.2). Renvoie un code d'erreur bloquant ou None."""
    cb = _inspect_bound(rec.capacity_bounds, central_c)
    eb = _inspect_bound(rec.existing_bounds, central_e)
    if cb.get("error") or eb.get("error"):
        return cb.get("error") or eb.get("error")
    if cb.get("present") and eb.get("present") and "min" in cb and "min" in eb:
        gain = {"min": cb["min"] - eb["max"], "max": cb["max"] - eb["min"]}
        add = {"min": max(0.0, gain["min"]), "max": max(0.0, gain["max"])}
        res.bounds = {
            "additional_interval": [add["min"], add["max"]],
            "gain_interval": [gain["min"], gain["max"]],
            "capacity_interval": [cb["min"], cb["max"]],
            "existing_interval": [eb["min"], eb["max"]],
            "sources": [cb["source"], eb["source"]],
            "kind": "enveloppe_hypotheses_documentee"}
        vig("Enveloppes d'hypothèses documentées ; pas un intervalle de confiance statistique.")
        if scenario == "keep" and gain["min"] <= 0 < gain["max"]:
            return "ENVELOPPE_AJOUT_TRAVERSE_ZERO"
    else:
        vig("Estimation ponctuelle ; incertitude non quantifiée.")
        if cb.get("present") or eb.get("present"):
            vig("Une seule entrée bornée : aucune enveloppe de résultat n'est inventée.")
    return None


def _band_block(rec, res, quantite, bareme, cause, vig):
    """Calcule la bande (D1/D2) et applique la protection D4. Renvoie True si la bande rend la
    ligne « À vérifier » (inconnue déterminante)."""
    sensible, bande, score = _bande_sensible_a_inconnue(quantite, rec, bareme)
    _, facteurs = _coef_physique(rec, bareme.get("faisabilite", {}))
    res.details.update({"bande_brute": bande, "score_brut": score, **facteurs})
    if sensible:
        res.band_provisional = bande
        res.details["bande_provisoire"] = bande
        vig("Bande sensible à une donnée inconnue (pente/accès) : bande provisoire conservée au détail.")
        return True
    res.band, res.score = bande, score
    return False


def _finish_keep(rec, opts, res, bareme, cause, vig, finish):
    # Conservation (D2) : R = max(0, C − E). Le coefficient bâti disparaît (difficulté d'insertion
    # = vigilance). Si C ou E manquent/invalides ⇒ à vérifier (D8). R caché sert de repli.
    C, E = rec.capacity_rebuild_m2, rec.existing_m2
    R = None
    if _present(C) and _present(E):
        if not _nonneg(C):
            return finish("TO_VERIFY", "CAPACITE_INVALIDE")
        if not _nonneg(E):
            return finish("TO_VERIFY", "EXISTANT_INVALIDE")
        res.quantities["project_total"] = C
        res.quantities["existing"] = E
        res.quantities["net_signed"] = C - E
        R = max(0.0, C - E)
    elif _present(rec.residual_m2):
        if not _nonneg(rec.residual_m2):
            return finish("TO_VERIFY", "RESIDUEL_INVALIDE")
        R = rec.residual_m2
    else:
        return finish("TO_VERIFY", "CAPACITE_ABSENTE")
    res.quantities["additional"] = R

    err = _bornes(rec, res, C, E, "keep", vig)
    if err:
        return finish("TO_VERIFY", err)

    vig("Marge par différence : l'insertion avec le bâti conservé reste à vérifier.")
    if R == 0:
        # Spec §7.1 / D3 : « Aucun ajout identifié selon les hypothèses », pas « rien à construire ».
        return finish("NO_MARGIN", "AUCUN_AJOUT_IDENTIFIE", "Aucun ajout identifié selon les hypothèses")
    if _band_block(rec, res, R, bareme, cause, vig):
        return finish("TO_VERIFY", "BANDE_SENSIBLE_INCONNUE")
    return finish("ESTIMATED", "CAPACITE_ADDITIONNELLE_ESTIMEE")


def _finish_rebuild(rec, opts, res, bareme, cause, vig, finish):
    # Reconstruction (D2) : C_rebuild, E, D_net = C_rebuild − E SIGNÉ. Aucun malus de démolition
    # (point de vigilance chiffré). Calculé pour TOUTES les parcelles, y compris saturées.
    C, E = rec.capacity_rebuild_m2, rec.existing_m2
    if not _present(C):
        return finish("TO_VERIFY", "CAPACITE_ABSENTE")
    if not _nonneg(C):
        return finish("TO_VERIFY", "CAPACITE_INVALIDE")
    if not _present(E):
        return finish("TO_VERIFY", "EXISTANT_ABSENT")
    if not _nonneg(E):
        return finish("TO_VERIFY", "EXISTANT_INVALIDE")
    res.quantities["project_total"] = C
    res.quantities["existing"] = E
    res.quantities["net_signed"] = C - E          # signé : une perte reste négative (spec §7.2)
    res.quantities["additional"] = max(0.0, C - E)

    err = _bornes(rec, res, C, E, "rebuild", vig)
    if err:
        return finish("TO_VERIFY", err)

    if E == 0:
        vig("Terrain déjà nu : aucune démolition nécessaire.")
    else:
        vig("Démolition, occupation, protections, relogement et coûts restent à vérifier.")
    if C - E < 0:
        vig("La reconstruction présente une perte théorique de SDP ; ce n'est pas une conclusion "
            "économique.")
    if C == 0:
        return finish("NO_MARGIN", "AUCUNE_CAPACITE_IDENTIFIEE",
                      "Aucune capacité identifiée selon les hypothèses")
    # Bande sur la capacité TOTALE du projet (D2), jamais sur le gain net.
    if _band_block(rec, res, C, bareme, cause, vig):
        return finish("TO_VERIFY", "BANDE_SENSIBLE_INCONNUE")
    return finish("ESTIMATED", "CAPACITE_RECONSTRUCTION_ESTIMEE")


# ── tri déterministe (spec §10 / D10) ────────────────────────────────────────
def order(records, options=None) -> list:
    if not isinstance(records, (list, tuple)):
        raise TypeError("records doit être une liste")
    opts = _options(options)
    _bareme(opts)
    rows = [evaluate(r, opts) for r in records]

    def key(res):
        if opts["mode"] == "sale":
            grp = SIGNAL_GROUP_ORDER.get(res.status, 9)
            band = 0
        else:
            grp = GROUP_ORDER.get(res.status, 9)
            # D10 : en potentiel, bande d'abord (dans le groupe de statut), puis la quantité.
            band = res.band_rank
        known = _finite(res.rank_value)
        # Clés : groupe ↑, bande ↑, (connu avant inconnu), quantité ↓, id ↑.
        return (grp, band, 0 if known else 1,
                -res.rank_value if known else 0.0, res.id)

    return sorted(rows, key=key)


# ── effectifs (spec §2.1 / D9 : tous les statuts dans les comptes) ───────────
def effectifs(rows: list) -> dict:
    """Comptes par statut et par bande pour la sélection. Chaque parcelle a un statut ; le total
    des statuts exclusifs = N_selection (spec §2.1)."""
    par_statut: dict = {}
    par_bande: dict = {}
    for r in rows:
        par_statut[r.status] = par_statut.get(r.status, 0) + 1
        if r.band:
            par_bande[r.band] = par_bande.get(r.band, 0) + 1
    return {"n": len(rows), "par_statut": par_statut, "par_bande": par_bande}
