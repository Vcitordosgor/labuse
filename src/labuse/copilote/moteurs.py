"""M26-A — exécuteur de moteurs : wrappers FINS autour de l'existant.

Interdiction de dupliquer la logique métier : chaque wrapper APPELLE un moteur existant
(ou LIT ses résultats précalculés — Factor 13), chronomètre, étiquette
(sourcé/estimé/absent) et compacte le résultat pour l'event log. Les listes complètes
vont dans agent_run_parcels, jamais dans les payloads.

Chaque wrapper reçoit (db, brief, dossier) et renvoie un StepResult ; le `dossier` est
l'état de travail en mémoire (candidats + annotations), muté au fil des étapes.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..scoring.score_v_constants import Q_A_RUN_LABEL

#: Ordre de service des tiers du run servi (champion P) — les écartées ne sont jamais criblées.
_TIERS_SERVIS = ("brulante", "chaude", "reserve_fonciere", "a_creuser")


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

    def retenus(self) -> list[dict]:
        return [c for c in self.candidats if c.get("retenu", True)]

    def ecarter(self, c: dict, motif: str) -> None:
        c["retenu"] = False
        c["motif_ecarte"] = motif


def _max_candidats() -> int:
    from .. import config
    return config.get_settings().copilote_max_candidats


# ── criblage — LECTURE SEULE du run servi épinglé + couches précalculées ────────────────
def criblage(db: Session, brief: dict, dossier: Dossier) -> StepResult:
    """Candidats = parcelles du run servi (Q_A_RUN_LABEL), tiers non écartés, filtrées par
    les critères du brief. AUCUN score recalculé (décision Vic, GO M26-A Q3)."""
    contraintes = brief.get("contraintes") or {}
    smin = brief.get("surface_min_m2")
    zones = contraintes.get("zones")

    rows = db.execute(text("""
        SELECT p.id AS parcel_id, p.idu, p.commune, round(p.surface_m2) AS surface_m2,
               v.tier, v.rang, v.percentile, z.zone_lib, z.zone_fam,
               EXISTS (SELECT 1 FROM cascade_results r
                       WHERE r.parcel_id = p.id AND r.layer_name = 'risques'
                         AND r.result = 'HARD_EXCLUDE' AND r.detail ILIKE '%ppr%') AS ppr_rouge,
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
        kept = _filtre("exclure_ppr_rouge", kept, lambda r: not r["ppr_rouge"])
    if contraintes.get("exclure_abf"):
        kept = _filtre("exclure_abf", kept, lambda r: not r["abf"])

    cap = _max_candidats()
    plafonne = len(kept) > cap
    kept = kept[:cap]

    dossier.candidats = [dict(r) | {"retenu": True} for r in kept]
    par_tier: dict[str, int] = {}
    for c in dossier.candidats:
        par_tier[c["tier"]] = par_tier.get(c["tier"], 0) + 1
    return StepResult(
        resultat={"run_servi": Q_A_RUN_LABEL, "n_pool": n0, "filtres": etapes,
                  "n_candidats": len(kept), "par_tier": par_tier,
                  "plafonne_a": cap if plafonne else None},
        etiquette="sourcé", n_avant=n0, n_apres=len(kept))


# ── faisabilite — moteur 11 étapes existant, par candidat ───────────────────────────────
def faisabilite(db: Session, brief: dict, dossier: Dossier) -> StepResult:
    """`faisabilite.db.parcel_faisabilite` par candidat. Entonnoir : SDP estimée < cible →
    écartée (motif tracé). Non calculable → écartée « non vérifiable » (boussole : jamais
    servi comme faisable ce qui ne l'est pas vérifiablement). Étiquette ESTIMÉ
    (pré-faisabilité sur hypothèses calibrables)."""
    from ..faisabilite.db import parcel_faisabilite

    cible = float(brief["programme"]["sdp_cible_m2"])
    avant = len(dossier.retenus())
    for c in dossier.retenus():
        res = parcel_faisabilite(db, c["parcel_id"])
        if res is None:
            dossier.ecarter(c, "faisabilité non vérifiable (zone PLU non résolue)")
            continue
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
    apres = len(dossier.retenus())
    return StepResult(
        resultat={"sdp_cible_m2": cible, "n_avant": avant, "n_apres": apres,
                  "n_ecartees": avant - apres},
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


# ── marche_dvf — prix de secteur + charge foncière (bilan promoteur existant) ───────────
def marche_dvf(db: Session, brief: dict, dossier: Dossier) -> StepResult:
    """`sector_price` + `compute_bilan` par candidat retenu. NON-BLOQUANT et NON
    éliminatoire : la charge foncière est un ESTIMÉ (jamais un motif d'écartement —
    l'annotation budget est portée à la note, pas tranchée ici)."""
    from ..faisabilite.bilan import compute_bilan, sector_price
    from ..faisabilite.engine import Hypotheses

    hyp = Hypotheses.charger()
    budget = brief.get("budget_max_eur")
    n_ok = 0
    for c in dossier.retenus():
        shab = ((c.get("faisabilite") or {}).get("shab_m2") or 0)
        if not shab:
            c["marche"] = {"disponible": False, "motif": "SHAB estimée absente"}
            continue
        prix = sector_price(db, c["parcel_id"], hyp)
        if not prix or not prix.get("median"):
            c["marche"] = {"disponible": False, "motif": "DVF insuffisant sur le secteur"}
            continue
        bilan = compute_bilan(float(shab), float(c["surface_m2"] or 0), prix, hyp)
        cf = (bilan.charge_fonciere or {}).get("central") if bilan else None
        c["marche"] = {
            "disponible": True, "prix_m2_median": prix.get("median"),
            "fiabilite": getattr(bilan, "fiabilite", None) or prix.get("fiabilite"),
            "charge_fonciere_eur": cf,
            "compatible_budget": (None if budget is None or cf is None
                                  else bool(cf >= float(budget))),
        }
        n_ok += 1
    n = len(dossier.retenus())
    return StepResult(
        resultat={"n_candidats": n, "n_charge_calculable": n_ok,
                  "n_indisponible": n - n_ok, "budget_max_eur": budget},
        etiquette="estimé")


# ── mutation — CHAMPION P, lecture seule du run servi épinglé ───────────────────────────
def mutation(db: Session, brief: dict, dossier: Dossier) -> StepResult:
    """Décision Vic (GO M26-A Q1) : lecture seule des scores/tiers du champion P
    (run servi épinglé), étiquette SOURCÉ. Le Radar Mutation V1 (NON SERVI, RR 0,51)
    n'est JAMAIS appelé ici."""
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


# ── assemblage — récapitulatif du dossier + persistance retenues/écartées ───────────────
def _persist_parcels(db: Session, run_id: str, dossier: Dossier) -> tuple[int, int]:
    retenues = ecartees = 0
    for c in dossier.candidats:
        verdict = "retenue" if c.get("retenu", True) else "ecartee"
        retenues += verdict == "retenue"
        ecartees += verdict == "ecartee"
        db.execute(text(
            "INSERT INTO agent_run_parcels (run_id, parcel_idu, verdict, motif) "
            "VALUES (:r, :i, :v, :m) "
            "ON CONFLICT (run_id, parcel_idu) DO UPDATE SET verdict = :v, motif = :m"),
            {"r": run_id, "i": c["idu"], "v": verdict, "m": c.get("motif_ecarte")})
    return retenues, ecartees


def _recap(dossier: Dossier, *, court: bool = False) -> dict:
    retenus = dossier.retenus()
    recap = {
        "n_retenues": len(retenus),
        "n_ecartees": sum(1 for c in dossier.candidats if not c.get("retenu", True)),
        "retenues_idu": [c["idu"] for c in retenus],
        "motifs_ecartement": sorted({c["motif_ecarte"] for c in dossier.candidats
                                     if c.get("motif_ecarte")}),
    }
    if not court:
        recap["retenues"] = [{
            "idu": c["idu"], "commune": c["commune"], "surface_m2": c["surface_m2"],
            "tier": c["tier"], "zone": c.get("zone_lib"),
            "sdp_m2": (c.get("faisabilite") or {}).get("sdp_m2"),
            "n_signaux_risques": len(c.get("risques") or []),
            "charge_fonciere_eur": (c.get("marche") or {}).get("charge_fonciere_eur"),
        } for c in retenus]
    return recap


def assemblage(db: Session, brief: dict, dossier: Dossier, *, run_id: str = "") -> StepResult:
    retenues, ecartees = _persist_parcels(db, run_id, dossier)
    return StepResult(resultat=_recap(dossier), etiquette="sourcé",
                      n_avant=retenues + ecartees, n_apres=retenues)


def assemblage_court(db: Session, brief: dict, dossier: Dossier, *, run_id: str = "") -> StepResult:
    retenues, ecartees = _persist_parcels(db, run_id, dossier)
    return StepResult(resultat=_recap(dossier, court=True), etiquette="sourcé",
                      n_avant=retenues + ecartees, n_apres=retenues)


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
                  "verdicts": dossier.verdicts[:12]},
        etiquette="sourcé")


MOTEURS = {
    "criblage": criblage,
    "faisabilite": faisabilite,
    "risques": risques,
    "marche_dvf": marche_dvf,
    "mutation": mutation,
    "assemblage": assemblage,
    "assemblage_court": assemblage_court,
    "scoreur_unitaire": scoreur_unitaire,
    "assemblage_verdict": assemblage_verdict,
}

#: Étapes qui persistent le détail parcelles (elles reçoivent run_id en kwarg).
MOTEURS_AVEC_RUN_ID = {"assemblage", "assemblage_court", "assemblage_verdict"}


def appeler(nom: str, db: Session, brief: dict, dossier: Dossier, *, run_id: str) -> tuple[StepResult, int]:
    """Appelle un moteur, chronomètre (ms). Le retry/l'étiquetage d'échec = exécuteur."""
    fn = MOTEURS[nom]
    t0 = time.monotonic()
    if nom in MOTEURS_AVEC_RUN_ID:
        res = fn(db, brief, dossier, run_id=run_id)
    else:
        res = fn(db, brief, dossier)
    return res, int((time.monotonic() - t0) * 1000)
