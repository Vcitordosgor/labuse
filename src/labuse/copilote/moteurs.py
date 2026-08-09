"""M26-A — exécuteur de moteurs : wrappers FINS autour de l'existant.

Interdiction de dupliquer la logique métier : chaque wrapper APPELLE un moteur existant
(ou LIT ses résultats précalculés — Factor 13), chronomètre, étiquette
(sourcé/estimé/absent) et compacte le résultat pour l'event log. Les listes complètes
vont dans agent_run_parcels, jamais dans les payloads.

Cascade de coût (arbitrage Vic, revue plafond M26-A) :
  criblage (SQL) → filtre_geometrique (SQL, prouvablement conservateur) → faisabilité
  (moteur 11 étapes, TOUS les survivants, parallèle) → risques → charge foncière LIVE
  sur TOUTES les retenues (pas d'hybride score_e : pipeline différent, cf. rapport) →
  filtre budget → tri champion P → restitution top-N.

Le filtre géométrique n'écarte une parcelle QUE si son majorant de SDP — emprise insetée
du recul × niveaux(hé) × coef_occupation, valeurs lues AUX MÊMES SOURCES que le moteur
(plu_rules.resolve_zone + Hypotheses.charger, jamais dupliquées) — reste sous la cible
moins la marge d'arrondi. Preuve 0 faux négatif : vérité terrain complète Saint-Paul
(3 852 retenues), Bras-Panon, Le Port (rapport §9-bis).
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..scoring.score_v_constants import Q_A_RUN_LABEL

#: Ordre de service des tiers du run servi (champion P) — les écartées ne sont jamais criblées.
_TIERS_SERVIS = ("brulante", "chaude", "reserve_fonciere", "a_creuser")

#: Marge d'arrondi du filtre géométrique : le moteur ARRONDIT sa SDP au m² — comparer le
#: majorant à (cible − 1) absorbe le cas limite (8 faux négatifs à SDP = 420 pile sans elle).
MARGE_ARRONDI_M2 = 1.0

#: Formulations imposées (Vic, revue calibrage M26-A) : sur commune non calibrée, JAMAIS
#: « tracée par article ».
MENTION_SDP_CALIBREE = "SDP tracée par article (PLU calibré)"
MENTION_SDP_GENERIQUE = "SDP estimée — règle générique, PLU non calibré"


@dataclass
class StepResult:
    resultat: dict
    etiquette: str = "sourcé"            # sourcé | estimé | absent
    n_avant: int | None = None           # compteur avant→après si l'étape filtre
    n_apres: int | None = None


@dataclass
class Dossier:
    """État de travail d'un run (en mémoire — la vérité persistée est l'event log)."""
    candidats: list[dict] = field(default_factory=list)
    refs: list[dict] = field(default_factory=list)          # mission verifier_adresse
    verdicts: list[dict] = field(default_factory=list)
    calibrage: dict = field(default_factory=dict)           # commune → article_plu | regle_generique

    def retenus(self) -> list[dict]:
        return [c for c in self.candidats if c.get("retenu", True)]

    def examines(self) -> list[dict]:
        return [c for c in self.candidats if c.get("examine", True)]

    def ecarter(self, c: dict, motif: str) -> None:
        c["retenu"] = False
        c["motif_ecarte"] = motif


def _settings():
    from .. import config
    return config.get_settings()


# ── Parallélisation bornée (arbitrage Vic : 4 sessions, fermées en fin d'étape,
#    annulation coupant les travaux en cours) ────────────────────────────────────────────
def _en_parallele(items: list, travail, annule=None, lot_verif: int = 25) -> None:
    """Applique `travail(session, item)` sur chaque item, N sessions dédiées (pool borné).

    Chaque worker ouvre SA session (jamais partagée entre runs ni entre workers) et la
    ferme en `finally`. `annule()` est consulté tous les `lot_verif` items : un run
    annulé coupe les travaux en cours au lieu de les laisser finir.
    """
    from ..db import session_factory
    n_workers = max(1, int(_settings().copilote_sessions_paralleles))
    stop = threading.Event()

    def _lot(sous_liste):
        s = session_factory()()
        try:
            for i, item in enumerate(sous_liste):
                if stop.is_set():
                    return
                if annule is not None and i % lot_verif == 0 and annule():
                    stop.set()
                    return
                travail(s, item)
        finally:
            s.close()

    lots = [items[i::n_workers] for i in range(n_workers)]
    with ThreadPoolExecutor(n_workers) as ex:
        for fut in [ex.submit(_lot, lot) for lot in lots if lot]:
            fut.result()                       # propage la première exception


# ── criblage — LECTURE SEULE du run servi épinglé + couches précalculées ────────────────
def criblage(db: Session, brief: dict, dossier: Dossier) -> StepResult:
    """Candidats = parcelles du run servi (Q_A_RUN_LABEL), tiers non écartés, filtrées par
    les critères du brief. AUCUN score recalculé (décision Vic, GO M26-A Q3). Aucun
    plafond ici : l'exhaustivité de l'examen est la règle, le garde-fou vit au filtre
    géométrique (dernier recours, requalifié)."""
    contraintes = brief.get("contraintes") or {}
    smin = brief.get("surface_min_m2")
    zones = contraintes.get("zones")

    rows = db.execute(text("""
        SELECT p.id AS parcel_id, p.idu, p.commune, round(p.surface_m2) AS surface_m2,
               v.tier, v.rang, v.percentile, z.zone_lib, z.zone_fam,
               -- M-I : PPR rouge GRADUÉ. La cascade n'ÉCARTE (HARD_EXCLUDE) plus que le rouge
               -- >= 50 % de surface → `ppr_rouge` (exclusion) ne cible plus que ces parcelles.
               EXISTS (SELECT 1 FROM cascade_results r
                       WHERE r.parcel_id = p.id AND r.layer_name = 'risques'
                         AND r.result = 'HARD_EXCLUDE' AND r.detail ILIKE '%ppr%') AS ppr_rouge,
               -- Palier 2–50 % : SERVI mais sous vigilance forte (flag, jamais filtré) → surfacé.
               EXISTS (SELECT 1 FROM cascade_results r
                       WHERE r.parcel_id = p.id AND r.layer_name = 'risques'
                         AND r.result = 'SOFT_FLAG' AND r.detail ILIKE '%PPR zone rouge sur%') AS ppr_partiel,
               EXISTS (SELECT 1 FROM cascade_results r
                       WHERE r.parcel_id = p.id AND r.layer_name = 'abf'
                         AND r.result = 'SOFT_FLAG') AS abf
        FROM parcels p
        JOIN parcel_p_score_v2 v ON v.parcelle_id = p.idu AND v.run_id = :run
        LEFT JOIN parcel_zone_plu z ON z.idu = p.idu
        WHERE p.commune = ANY(:communes) AND v.tier = ANY(:tiers)
        ORDER BY array_position(CAST(:tiers AS varchar[]), v.tier), v.rang NULLS LAST, p.idu
        """), {"run": Q_A_RUN_LABEL, "communes": brief["communes"],
               "tiers": list(_TIERS_SERVIS)}).mappings().all()

    n0 = len(rows)
    etapes: dict[str, dict] = {}

    def _filtre(nom: str, rows_in, pred):
        kept = [r for r in rows_in if pred(r)]
        etapes[nom] = {"avant": len(rows_in), "apres": len(kept)}
        return kept

    kept = rows
    if smin:
        kept = _filtre("surface_min", kept,
                       lambda r: (r["surface_m2"] or 0) >= float(smin))
    if zones:
        kept = _filtre("zones", kept, lambda r: r["zone_fam"] in set(zones))
    if contraintes.get("exclure_ppr_rouge", True):
        # M-I : « exclure le PPR rouge » = écarter les terrains MAJORITAIREMENT rouges (>= 50 %,
        # seuls à porter le HARD_EXCLUDE désormais). Les parcelles partiellement rouges (2–50 %)
        # NE sont PAS filtrées : elles restent servies, signalées par `ppr_partiel` (vigilance).
        kept = _filtre("exclure_ppr_rouge", kept, lambda r: not r["ppr_rouge"])
    if contraintes.get("exclure_abf"):
        kept = _filtre("exclure_abf", kept, lambda r: not r["abf"])

    dossier.candidats = [dict(r) | {"retenu": True, "examine": True} for r in kept]
    par_tier: dict[str, int] = {}
    for c in dossier.candidats:
        par_tier[c["tier"]] = par_tier.get(c["tier"], 0) + 1
    return StepResult(
        resultat={"run_servi": Q_A_RUN_LABEL, "n_pool": n0, "filtres": etapes,
                  "n_candidats": len(kept), "par_tier": par_tier},
        etiquette="sourcé", n_avant=n0, n_apres=len(kept))


# ── filtre_geometrique — majorant de SDP prouvablement conservateur (SQL) ───────────────
def _regles_filtre(commune: str, zone_libs: set[str]) -> tuple[dict, str]:
    """zone_lib → (niveaux majorants, recul) depuis LES MÊMES SOURCES que le moteur :
    plu_rules.resolve_zone (YAML calibré ou repli générique) + Hypotheses.charger().
    Renvoie aussi le mode de calibrage de la commune (article_plu | regle_generique).
    Zone sans plafond exploitable (à_vérifier…) → absente du mapping → NON filtrée."""
    from ..faisabilite.engine import Hypotheses
    from ..faisabilite.plu_rules import _calibrated_yaml, resolve_zone

    hyp = Hypotheses.charger()
    calibree = _calibrated_yaml(commune) is not None
    regles: dict[str, tuple[int, float]] = {}
    for lib in zone_libs:
        r = resolve_zone(lib, commune)
        if r is None or not r.constructible_neuf or r.habitat == "interdit":
            # le moteur conclura non-constructible : on laisse la faisabilité le dire
            # (l'attribution de zone d'une parcelle mixte peut différer — jamais d'exclusion ici).
            continue
        # Même dérivation des niveaux que le moteur (engine.py, « Niveaux (hé prioritaire) »).
        if isinstance(r.he_m, (int, float)):
            niveaux = int(float(r.he_m) // hyp.etage_m)
        elif isinstance(r.hf_m, (int, float)):
            niveaux = max(1, int((float(r.hf_m) - hyp.etage_m) // hyp.etage_m))
        else:
            continue                                     # pas de plafond exploitable
        recul = (float(r.recul_limites_sep_m)
                 if isinstance(r.recul_limites_sep_m, (int, float))
                 else hyp.recul_limites_defaut_m)
        regles[lib] = (niveaux, recul)
    return regles, ("article_plu" if calibree else "regle_generique")


def filtre_geometrique(db: Session, brief: dict, dossier: Dossier) -> StepResult:
    """Écarte les parcelles dont la SDP est GÉOMÉTRIQUEMENT hors d'atteinte, quelle que
    soit la règle applicable : majorant = emprise insetée du recul × niveaux(hé) ×
    coef_occupation (le moteur ne peut jamais produire plus). Marge d'arrondi 1 m².
    Puis garde-fou de dernier recours (copilote_max_candidats) : au-delà, les parcelles
    ne sont PAS examinées et le récap est requalifié — jamais présenté comme exhaustif."""
    from ..faisabilite.engine import Hypotheses

    hyp = Hypotheses.charger()
    occ = float(hyp.coef_occupation)                     # même source que le moteur, jamais dupliqué
    cible = float(brief["programme"]["sdp_cible_m2"])
    avant = len(dossier.retenus())

    par_commune: dict[str, set] = {}
    for c in dossier.candidats:
        par_commune.setdefault(c["commune"], set()).add(c["zone_lib"])
    regles_par_commune: dict[str, dict] = {}
    for commune, libs in par_commune.items():
        regles, mode = _regles_filtre(commune, {x for x in libs if x})
        regles_par_commune[commune] = regles
        dossier.calibrage[commune] = mode

    # Emprises insetées par groupe de recul distinct (une requête SQL par valeur).
    a_inspecter: dict[float, list[dict]] = {}
    for c in dossier.candidats:
        r = regles_par_commune[c["commune"]].get(c["zone_lib"] or "")
        if r is None:
            continue                                     # zone sans plafond exploitable → non filtrée
        c["_niveaux_majorant"], recul = r
        a_inspecter.setdefault(recul, []).append(c)
    for recul, cs in a_inspecter.items():
        insets = dict(db.execute(text(
            "SELECT id, ST_Area(ST_Buffer(geom_2975, -:d)) FROM parcels WHERE id = ANY(:ids)"),
            {"d": recul, "ids": [c["parcel_id"] for c in cs]}).all())
        for c in cs:
            majorant = (insets.get(c["parcel_id"]) or 0.0) * c["_niveaux_majorant"] * occ
            if majorant < cible - MARGE_ARRONDI_M2:
                mode = dossier.calibrage[c["commune"]]
                src = ("Sourcé, article PLU" if mode == "article_plu"
                       else "Estimé, règle générique (hé 9 m ≈ 3 niveaux)")
                dossier.ecarter(c, f"capacité géométrique insuffisante "
                                   f"(majorant {majorant:.0f} m² < cible {cible:.0f} m²) — {src}")

    survivants = dossier.retenus()
    dossier._n_apres_geo = len(survivants)             # étage « filtre_geometrique » du récap
    # Garde-fou de DERNIER RECOURS (arbitrage Vic) — ordre déterministe déjà en place
    # (tier puis rang du champion P puis IDU, hérité du criblage).
    plafond = int(_settings().copilote_max_candidats)
    tronque = len(survivants) > plafond
    if tronque:
        for c in survivants[plafond:]:
            c["examine"] = False
            c["retenu"] = False
            c["motif_ecarte"] = (f"non examinée — garde-fou {plafond} parcelles atteint "
                                 "(résultat NON exhaustif, voir récapitulatif)")
    apres = min(len(survivants), plafond)
    etiquette = ("sourcé" if all(m == "article_plu" for m in dossier.calibrage.values())
                 else "estimé")
    return StepResult(
        resultat={"cible_sdp_m2": cible, "coef_occupation": occ,
                  "marge_arrondi_m2": MARGE_ARRONDI_M2,
                  "calibrage": dict(dossier.calibrage),
                  "n_ecartees_geometrie": avant - len(survivants),
                  "garde_fou": {"plafond": plafond, "a_mordu": tronque,
                                "n_non_examinees": max(0, len(survivants) - plafond)},
                  "n_examinees": apres},
        etiquette=etiquette, n_avant=avant, n_apres=apres)


# ── faisabilite — moteur 11 étapes existant, TOUS les survivants, en parallèle ──────────
def faisabilite(db: Session, brief: dict, dossier: Dossier, *, annule=None) -> StepResult:
    """`faisabilite.db.parcel_faisabilite` sur chaque parcelle examinée, pool parallèle
    borné. Entonnoir : SDP estimée < cible → écartée (motif tracé). Non calculable →
    écartée « non vérifiable » (boussole). Étiquette ESTIMÉ ; le mode de calibrage
    (article PLU / règle générique) est porté explicitement (exigence Vic, revue M26-A)."""
    from ..faisabilite.db import parcel_faisabilite

    cible = float(brief["programme"]["sdp_cible_m2"])
    a_examiner = dossier.retenus()
    avant = len(a_examiner)
    lock = threading.Lock()

    def _travail(s: Session, c: dict) -> None:
        res = parcel_faisabilite(s, c["parcel_id"])
        with lock:
            if res is None:
                dossier.ecarter(c, "faisabilité non vérifiable (zone PLU non résolue)")
                return
            _ctx, fai = res
            f = fai.fourchette
            c["faisabilite"] = {
                "constructible": fai.constructible, "verdict": fai.verdict,
                "zone": fai.zone, "sdp_m2": f.get("surface_plancher_m2"),
                "shab_m2": f.get("shab_vendable_m2"),
                "logements": f.get("logements_sous_sol") or f.get("logements_au_sol"),
                "calibree": fai.calibree,
            }
            if not fai.constructible:
                dossier.ecarter(c, f"non constructible en l'état ({fai.verdict})")
            elif (f.get("surface_plancher_m2") or 0) < cible:
                dossier.ecarter(c, f"SDP estimée insuffisante "
                                   f"({f.get('surface_plancher_m2', 0):.0f} m² < cible {cible:.0f} m²)")

    _en_parallele(a_examiner, _travail, annule=annule)
    apres = len(dossier.retenus())
    calibrage = dict(dossier.calibrage)
    mention = (MENTION_SDP_CALIBREE
               if calibrage and all(m == "article_plu" for m in calibrage.values())
               else MENTION_SDP_GENERIQUE)
    return StepResult(
        resultat={"sdp_cible_m2": cible, "n_avant": avant, "n_apres": apres,
                  "n_ecartees": avant - apres,
                  "calibrage": calibrage, "mention_sdp": mention,
                  "sessions_paralleles": int(_settings().copilote_sessions_paralleles)},
        etiquette="estimé", n_avant=avant, n_apres=apres)


# ── risques — LECTURE des verdicts cascade précalculés (Géorisques/ABF/PPR) ─────────────
_LAYERS_RISQUES = ("risques", "abf", "trait_de_cote", "pente", "cinquante_pas")


def risques(db: Session, brief: dict, dossier: Dossier) -> StepResult:
    """Verdicts risques déjà journalisés en cascade_results (Factor 13 : pas de recalcul).
    ABF : signalé, pas exclu (sauf brief contraire, déjà appliqué au criblage)."""
    retenus = dossier.retenus()
    if not retenus:
        return StepResult(resultat={"n_candidats": 0, "flags": {}}, etiquette="sourcé")
    ids = [c["parcel_id"] for c in retenus]
    rows = db.execute(text(
        "SELECT parcel_id, layer_name, result, severity, detail FROM cascade_results "
        "WHERE parcel_id = ANY(:ids) AND layer_name = ANY(:layers) "
        "  AND result IN ('SOFT_FLAG', 'HARD_EXCLUDE')"),
        {"ids": ids, "layers": list(_LAYERS_RISQUES)}).mappings().all()
    par_parcelle: dict[int, list[dict]] = {}
    for r in rows:
        par_parcelle.setdefault(r["parcel_id"], []).append(
            {"couche": r["layer_name"], "verdict": r["result"],
             "severite": r["severity"], "detail": r["detail"]})
    flags_totaux: dict[str, int] = {}
    for c in retenus:
        signaux = par_parcelle.get(c["parcel_id"], [])
        c["risques"] = signaux
        for s in signaux:
            flags_totaux[s["couche"]] = flags_totaux.get(s["couche"], 0) + 1
    return StepResult(
        resultat={"n_candidats": len(retenus), "flags": flags_totaux,
                  "n_sans_signal": sum(1 for c in retenus if not c["risques"])},
        etiquette="sourcé")


# ── marche_dvf — charge foncière LIVE sur TOUTES les retenues + prix probable ───────────
def marche_dvf(db: Session, brief: dict, dossier: Dossier, *, annule=None) -> StepResult:
    """`sector_price` + `compute_bilan` (mêmes fonctions que la fiche) sur CHAQUE retenue,
    en parallèle — PAS d'hybride score_e (pipeline batch différent : bilan à rebours
    « bilan-neuf-v2 », cf. rapport). Prix probable du foncier = médiane terrain
    sectorielle × surface (dvf_secteur_medianes, lecture SQL). NON-BLOQUANT : s'il
    échoue, la note dira « charge foncière non calculable »."""
    from ..faisabilite.bilan import compute_bilan, sector_price, resolve_prix_sortie_servi
    from ..faisabilite.engine import Hypotheses

    hyp = Hypotheses.charger()
    retenus = dossier.retenus()
    # Prix probable (une requête pour tout le lot).
    prix_terrain = dict(db.execute(text(
        "SELECT left(p.idu, 10), max(m.mediane_prix_m2) "
        "FROM parcels p JOIN dvf_secteur_medianes m ON m.secteur = left(p.idu, 10) "
        "WHERE p.id = ANY(:ids) AND m.type_bien = 'terrain' AND m.n_ventes >= 3 "
        "GROUP BY left(p.idu, 10)"),
        {"ids": [c["parcel_id"] for c in retenus]}).all())
    lock = threading.Lock()
    n_ok = [0]

    def _travail(s: Session, c: dict) -> None:
        shab = ((c.get("faisabilite") or {}).get("shab_m2") or 0)
        terrain_m2 = prix_terrain.get(c["idu"][:10])
        prix_probable = (round(terrain_m2 * float(c["surface_m2"] or 0))
                         if terrain_m2 and c["surface_m2"] else None)
        if not shab:
            with lock:
                c["marche"] = {"disponible": False, "motif": "SHAB estimée absente",
                               "prix_probable_eur": prix_probable}
            return
        prix = sector_price(s, c["parcel_id"], hyp)      # comparables DVF (bloc marché, LÉGITIME)
        if not prix or not prix.get("median"):
            with lock:
                c["marche"] = {"disponible": False, "motif": "DVF insuffisant sur le secteur",
                               "prix_probable_eur": prix_probable}
            return
        # MANDAT PRIX SORTIE CONSOMMATEURS (Vic 28/07/2026) — la charge est un bilan NEUF : prix de
        # sortie via le point de résolution PARTAGÉ (plus jamais sector_price/existant). Non
        # calculable (commune social-dominante) → parcelle SERVIE avec la mention, JAMAIS écartée.
        ps = resolve_prix_sortie_servi(s, c["parcel_id"])
        if ps["non_calculable"]:
            with lock:
                c["marche"] = {"disponible": False, "non_calculable": True,
                               "motif": ps["motif"], "prix_m2_median": prix.get("median"),
                               "prix_probable_eur": prix_probable,
                               "provenance": "prix de sortie non calculable (marché non atteignable)"}
                n_ok[0] += 1
            return
        bilan = compute_bilan(float(shab), float(c["surface_m2"] or 0), prix, hyp,
                              bilan_params={"prix_m2_neuf": ps["prix"]})   # prix de sortie NEUF
        cf = (bilan.charge_fonciere or {}).get("central") if bilan else None
        # Indicateur (Vic, revue budget) — PAS un filtre : prix probable > charge
        # supportable = « dans le budget de l'acheteur mais l'opération ne supporte pas
        # son prix ». La parcelle RESTE retenue ; l'utilisateur arbitre. Estimé (comme
        # les deux grandeurs qui le composent).
        au_dessus = (None if cf is None or prix_probable is None
                     else bool(prix_probable > cf))
        with lock:
            c["marche"] = {
                "disponible": True, "prix_m2_median": prix.get("median"),
                "prix_sortie_neuf": ps["prix"], "niveau_prix_neuf": ps["niveau"],
                "prix_neuf_label": ps["label"], "prix_neuf_repli_ile": ps["repli_ile"],
                "fiabilite": getattr(bilan, "fiabilite", None) or prix.get("fiabilite"),
                "charge_fonciere_eur": cf, "prix_probable_eur": prix_probable,
                "au_dessus_charge_supportable": au_dessus,
                "provenance": "calcul live (prix de sortie neuf partagé + compute_bilan)",
            }
            n_ok[0] += 1

    _en_parallele(retenus, _travail, annule=annule)
    n = len(retenus)
    return StepResult(
        resultat={"n_candidats": n, "n_charge_calculable": n_ok[0],
                  "n_indisponible": n - n_ok[0],
                  "n_prix_probable": sum(1 for c in retenus
                                         if (c.get("marche") or {}).get("prix_probable_eur")),
                  "n_au_dessus_charge_supportable": sum(
                      1 for c in retenus
                      if (c.get("marche") or {}).get("au_dessus_charge_supportable")),
                  "provenance": "calcul live — jamais score_e (pipeline distinct)"},
        etiquette="estimé")


# ── filtre_budget — critère du brief, appliqué AVANT toute troncature ───────────────────
def filtre_budget(db: Session, brief: dict, dossier: Dossier) -> StepResult:
    """« Dans le budget » = prix probable du foncier (Estimé, médiane terrain sectorielle
    × surface) ≤ budget_max_eur du brief. Une parcelle SANS prix probable est
    « non estimable — non filtrée », JAMAIS écartée sur une absence (règle Vic)."""
    budget = brief.get("budget_max_eur")
    retenus = dossier.retenus()
    if budget is None:
        return StepResult(resultat={"applique": False, "motif": "aucun budget au brief",
                                    "n_candidats": len(retenus)}, etiquette="sourcé")
    avant = len(retenus)
    n_non_estimable = 0
    for c in retenus:
        prix = (c.get("marche") or {}).get("prix_probable_eur")
        if prix is None:
            c["budget"] = "non estimable — non filtrée"
            n_non_estimable += 1
        elif prix > float(budget):
            dossier.ecarter(c, f"prix probable du foncier ({prix:,.0f} € — Estimé, médiane "
                               f"terrain sectorielle) au-dessus du budget ({budget:,.0f} €)".replace(",", " "))
        else:
            c["budget"] = "dans le budget"
    apres = len(dossier.retenus())
    return StepResult(
        resultat={"applique": True, "budget_max_eur": budget, "n_avant": avant,
                  "n_dans_budget": apres - n_non_estimable,
                  "n_non_estimables_non_filtrees": n_non_estimable,
                  "n_ecartees_budget": avant - apres},
        etiquette="estimé", n_avant=avant, n_apres=apres)


# ── mutation — CHAMPION P, lecture seule du run servi épinglé ───────────────────────────
def mutation(db: Session, brief: dict, dossier: Dossier) -> StepResult:
    """Décision Vic (GO M26-A Q1) : lecture seule des scores/tiers du champion P
    (run servi épinglé), étiquette SOURCÉ. Sa place (revue plafond) : APRÈS la
    faisabilité, pour CLASSER les retenues — jamais pour choisir lesquelles examiner.
    Le Radar Mutation V1 (NON SERVI, RR 0,51) n'est JAMAIS appelé ici."""
    retenus = dossier.retenus()
    if not retenus:
        return StepResult(resultat={"run_servi": Q_A_RUN_LABEL, "n_candidats": 0},
                          etiquette="sourcé")
    rows = db.execute(text(
        "SELECT parcelle_id, tier, rang, percentile FROM parcel_p_score_v2 "
        "WHERE run_id = :run AND parcelle_id = ANY(:idus)"),
        {"run": Q_A_RUN_LABEL, "idus": [c["idu"] for c in retenus]}).mappings().all()
    par_idu = {r["parcelle_id"]: r for r in rows}
    par_tier: dict[str, int] = {}
    for c in retenus:
        r = par_idu.get(c["idu"])
        c["champion_p"] = (None if r is None else
                           {"tier": r["tier"], "rang": r["rang"],
                            "percentile": float(r["percentile"]) if r["percentile"] is not None else None})
        if r is not None:
            par_tier[r["tier"]] = par_tier.get(r["tier"], 0) + 1
    return StepResult(
        resultat={"run_servi": Q_A_RUN_LABEL, "n_candidats": len(retenus),
                  "par_tier": par_tier},
        etiquette="sourcé")


# ── assemblage — tri P, restitution top-N, entonnoir complet, persistance ───────────────
def _persist_parcels(db: Session, run_id: str, dossier: Dossier) -> None:
    for c in dossier.candidats:
        if not c.get("examine", True):
            verdict = "non_examinee"
        elif c.get("retenu", True):
            verdict = "retenue"
        else:
            verdict = "ecartee"
        db.execute(text(
            "INSERT INTO agent_run_parcels (run_id, parcel_idu, verdict, motif) "
            "VALUES (:r, :i, :v, :m) "
            "ON CONFLICT (run_id, parcel_idu) DO UPDATE SET verdict = :v, motif = :m"),
            {"r": run_id, "i": c["idu"], "v": verdict, "m": c.get("motif_ecarte")})


def _entonnoir(dossier: Dossier, n_pool: int, restituees: list[dict]) -> list[dict]:
    """Les six étages, chacun avec compteur et étiquette (exigence Vic, revue plafond) :
    pool → filtre géométrique → examinées → retenues → dans le budget → restituées.
    « Examinées » = réellement passées à la faisabilité : survivantes du filtre
    géométrique MOINS les non-examinées du garde-fou (jamais les écartées du filtre)."""
    retenues = dossier.retenus()
    dans_budget = [c for c in retenues if c.get("budget") != "non estimable — non filtrée"]
    n_non_exam = sum(1 for c in dossier.candidats if not c.get("examine", True))
    apres_geo = getattr(dossier, "_n_apres_geo", len(dossier.candidats))
    return [
        {"etape": "pool", "n": n_pool, "etiquette": "sourcé"},
        {"etape": "filtre_geometrique", "n": apres_geo,
         "etiquette": "sourcé/estimé selon calibrage"},
        {"etape": "examinees", "n": apres_geo - n_non_exam, "etiquette": "sourcé"},
        {"etape": "retenues", "n": len(retenues), "etiquette": "estimé (faisabilité)"},
        {"etape": "dans_budget", "n": len(dans_budget), "etiquette": "estimé (prix probable)"},
        {"etape": "restituees", "n": len(restituees), "etiquette": "sourcé (tri champion P)"},
    ]


_ORDRE_TIER = {t: i for i, t in enumerate(_TIERS_SERVIS)}


def _restitution(dossier: Dossier) -> list[dict]:
    """Tri par champion P (tier puis rang — APRÈS faisabilité, jamais avant), top-N."""
    top_n = int(_settings().copilote_top_restitution)
    tries = sorted(dossier.retenus(),
                   key=lambda c: (_ORDRE_TIER.get((c.get("champion_p") or {}).get("tier")
                                                  or c.get("tier"), 9),
                                  (c.get("champion_p") or {}).get("rang") or c.get("rang") or 10**9,
                                  c["idu"]))
    return tries[:top_n]


def _recap(dossier: Dossier, n_pool: int, *, court: bool = False) -> dict:
    restituees = _restitution(dossier)
    garde_fou_a_mordu = any(not c.get("examine", True) for c in dossier.candidats)
    n_non_exam = sum(1 for c in dossier.candidats if not c.get("examine", True))
    n_exam = (getattr(dossier, "_n_apres_geo", len(dossier.candidats)) - n_non_exam)
    recap = {
        "entonnoir": _entonnoir(dossier, n_pool, restituees),
        "n_retenues": len(dossier.retenus()),
        "n_ecartees": sum(1 for c in dossier.candidats
                          if c.get("examine", True) and not c.get("retenu", True)),
        "n_non_examinees": sum(1 for c in dossier.candidats if not c.get("examine", True)),
        "n_restituees": len(restituees),
        "exhaustif": not garde_fou_a_mordu,
        "calibrage": dict(dossier.calibrage),
        "mention_sdp": (MENTION_SDP_CALIBREE
                        if dossier.calibrage
                        and all(m == "article_plu" for m in dossier.calibrage.values())
                        else MENTION_SDP_GENERIQUE),
        "motifs_ecartement": sorted({c["motif_ecarte"] for c in dossier.candidats
                                     if c.get("motif_ecarte")})[:40],
        # Indicateur (Estimé, jamais un filtre) : dans le budget de l'acheteur mais
        # l'opération ne supporte pas son prix probable — l'utilisateur arbitre.
        "n_au_dessus_charge_supportable": sum(
            1 for c in dossier.retenus()
            if (c.get("marche") or {}).get("au_dessus_charge_supportable")),
    }
    if garde_fou_a_mordu:
        recap["requalification"] = (f"Résultat NON exhaustif : {recap['n_retenues']} retenue(s) "
                                    f"parmi les {n_exam} examinées sur {len(dossier.candidats)} "
                                    "candidates — jamais « aucune opportunité ».")
    if not court:
        recap["restituees"] = [{
            "idu": c["idu"], "commune": c["commune"], "surface_m2": c["surface_m2"],
            "tier": c["tier"], "rang": c.get("rang"), "zone": c.get("zone_lib"),
            "sdp_m2": (c.get("faisabilite") or {}).get("sdp_m2"),
            "n_signaux_risques": len(c.get("risques") or []),
            "charge_fonciere_eur": (c.get("marche") or {}).get("charge_fonciere_eur"),
            "prix_probable_eur": (c.get("marche") or {}).get("prix_probable_eur"),
            "au_dessus_charge_supportable": (c.get("marche") or {}).get("au_dessus_charge_supportable"),
            "budget": c.get("budget"),
        } for c in restituees]
    else:
        recap["restituees_idu"] = [c["idu"] for c in restituees]
    return recap


def _n_pool(dossier: Dossier, brief: dict) -> int:
    # le pool est journalisé au criblage ; ici on retombe sur les candidats connus
    return getattr(dossier, "_n_pool", None) or len(dossier.candidats)


def assemblage(db: Session, brief: dict, dossier: Dossier, *, run_id: str = "") -> StepResult:
    _persist_parcels(db, run_id, dossier)
    recap = _recap(dossier, _n_pool(dossier, brief))
    return StepResult(resultat=recap, etiquette="sourcé",
                      n_avant=len(dossier.candidats), n_apres=recap["n_restituees"])


def assemblage_court(db: Session, brief: dict, dossier: Dossier, *, run_id: str = "") -> StepResult:
    _persist_parcels(db, run_id, dossier)
    recap = _recap(dossier, _n_pool(dossier, brief), court=True)
    return StepResult(resultat=recap, etiquette="sourcé",
                      n_avant=len(dossier.candidats), n_apres=recap["n_restituees"])


# ── scoreur_unitaire — mission verifier_adresse ─────────────────────────────────────────
def scoreur_unitaire(db: Session, brief: dict, dossier: Dossier) -> StepResult:
    """Verdict compact par référence : IDU → lecture directe (mêmes champs que le scoreur
    existant) ; adresse → moteur /scoreur existant (géocodage BAN + verdict)."""
    verdicts = []
    for ref in brief.get("refs", []):
        if ref["type"] == "idu":
            row = db.execute(text(
                "SELECT p.idu, p.commune, round(p.surface_m2) AS surface_m2, "
                "       s2.tier, s2.rang, s2.percentile "
                "FROM parcels p "
                "LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :run "
                "WHERE p.idu = :i"),
                {"run": Q_A_RUN_LABEL, "i": ref["valeur"]}).mappings().first()
            if row is None:
                verdicts.append({"ref": ref["valeur"], "trouvee": False,
                                 "motif": "parcelle absente de la base (non vérifié)"})
            else:
                verdicts.append({"ref": ref["valeur"], "trouvee": True,
                                 "idu": row["idu"], "commune": row["commune"],
                                 "surface_m2": row["surface_m2"], "tier": row["tier"],
                                 "rang": row["rang"]})
        else:  # adresse → scoreur existant (BAN)
            from ..api.scoreur import ScoreurIn, scoreur_adresse
            out = scoreur_adresse(ScoreurIn(q=ref["valeur"]), db)
            if not out.get("ok"):
                verdicts.append({"ref": ref["valeur"], "trouvee": False,
                                 "motif": out.get("message", "adresse non résolue")})
            else:
                verdicts.append({"ref": ref["valeur"], "trouvee": True,
                                 "idu": out["idu"], "commune": out["commune"],
                                 "surface_m2": out["surface_m2"],
                                 "tier": (out.get("verdict") or {}).get("tier"),
                                 "rang": (out.get("verdict") or {}).get("rang")})
    dossier.verdicts = verdicts
    return StepResult(
        resultat={"n_refs": len(verdicts),
                  "n_trouvees": sum(1 for v in verdicts if v["trouvee"])},
        etiquette="sourcé")


def assemblage_verdict(db: Session, brief: dict, dossier: Dossier, *, run_id: str = "") -> StepResult:
    top_n = int(_settings().copilote_top_restitution)
    for v in dossier.verdicts:
        db.execute(text(
            "INSERT INTO agent_run_parcels (run_id, parcel_idu, verdict, motif) "
            "VALUES (:r, :i, :v, :m) "
            "ON CONFLICT (run_id, parcel_idu) DO UPDATE SET verdict = :v, motif = :m"),
            {"r": run_id, "i": (v.get("idu") or v["ref"])[:14],
             "v": "verifiee" if v["trouvee"] else "introuvable",
             "m": v.get("motif") or (f"tier {v.get('tier')}" if v.get("tier") else None)})
    return StepResult(
        resultat={"n_retenues": sum(1 for v in dossier.verdicts if v["trouvee"]),
                  "n_ecartees": sum(1 for v in dossier.verdicts if not v["trouvee"]),
                  "verdicts": dossier.verdicts[:top_n]},
        etiquette="sourcé")


MOTEURS = {
    "criblage": criblage,
    "filtre_geometrique": filtre_geometrique,
    "faisabilite": faisabilite,
    "risques": risques,
    "marche_dvf": marche_dvf,
    "filtre_budget": filtre_budget,
    "mutation": mutation,
    "assemblage": assemblage,
    "assemblage_court": assemblage_court,
    "scoreur_unitaire": scoreur_unitaire,
    "assemblage_verdict": assemblage_verdict,
}

#: Étapes qui persistent le détail parcelles (elles reçoivent run_id en kwarg).
MOTEURS_AVEC_RUN_ID = {"assemblage", "assemblage_court", "assemblage_verdict"}
#: Étapes longues qui acceptent le rappel d'annulation (coupe les sessions en cours).
MOTEURS_AVEC_ANNULE = {"faisabilite", "marche_dvf"}


def appeler(nom: str, db: Session, brief: dict, dossier: Dossier, *, run_id: str,
            annule=None) -> tuple[StepResult, int]:
    """Appelle un moteur, chronomètre (ms). Le retry/l'étiquetage d'échec = exécuteur."""
    fn = MOTEURS[nom]
    t0 = time.monotonic()
    if nom in MOTEURS_AVEC_RUN_ID:
        res = fn(db, brief, dossier, run_id=run_id)
    elif nom in MOTEURS_AVEC_ANNULE:
        res = fn(db, brief, dossier, annule=annule)
    else:
        res = fn(db, brief, dossier)
    if nom == "criblage":
        dossier._n_pool = res.resultat.get("n_pool")
    return res, int((time.monotonic() - t0) * 1000)
