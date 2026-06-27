"""LA BUSE — Score Mutation V1 (Radar Mutation foncière).

Score 0-100 qui mesure le **potentiel de TRANSFORMATION** d'une parcelle (grand terrain
sous-exploité, presque-seuil, foncier public/morale acquérable, marché actif), **distinct
du verdict d'opportunité** (« à prospecter maintenant »).

Garanties de ce module :
- **Lecture seule** : il ne touche NI le scoring d'opportunité, NI le verdict, NI la DB
  (l'assemblage des features ne fait que des SELECT). Aucune écriture, aucun cache.
- **Moteur pur** : `compute_mutation_score(features)` n'a aucun effet de bord (entrée gelée).
- **Wording prudent** : « potentiel à étudier », jamais « constructible » / « va muter ».

Spécification : docs/product/RADAR_MUTATION_PHASE1_SPEC.md (Phase 1). Phase 2A = ce moteur,
sans endpoint ni UI.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ── Pondérations & seuils V1 — PLACEHOLDER, à caler terrain (cf. spec §3/§4) ──────────────
W_SOUS_EXPLOITATION = 30
W_INTENSITE_LATENTE = 25
W_ZONAGE_FAVORABLE = 15
W_POTENTIEL_REGIONAL = 15
W_MARCHE_ACTIF = 10
W_FONCIER_ACQUERABLE = 8
MALUS_CONTRAINTE_FORTE = 15

SEUIL_PRIORITAIRE = 70
SEUIL_FORTE = 55
SEUIL_SURVEILLER = 40
CONFIANCE_FLOOR = 50            # règle d'or : sous ce seuil, jamais « prioritaire »/« forte »

SURFACE_PLANCHER_M2 = 500.0     # en deçà : aucun bonus surface
SURFACE_SATURATION_M2 = 5000.0  # courbe saturante (une parcelle géante ne gagne pas mécaniquement)
BATI_PLAFOND = 0.30            # ≥ 30 % bâti : plus de sous-exploitation

AVERTISSEMENT = "Potentiel de mutation à étudier — ni constructibilité ni vente garanties."


@dataclass(frozen=True)
class MutationFeatures:
    """Entrées du moteur, déjà extraites en amont (le moteur reste PUR et sans DB)."""
    statut: str                          # verdict opportunité : 'a_creuser', 'opportunite', …
    opportunity_score: int               # 0-100 (LU seulement — jamais modifié)
    completeness_score: int              # 0-100 → sert de confiance
    surface_m2: float
    bati_ratio: Optional[float] = None   # None = couche bâti indisponible → jamais un faux « vacant »
    zone_u_au: bool = False
    potentiel_regional: bool = False
    marche_dvf: bool = False
    proprietaire: Optional[dict] = None  # {'public': bool|None, 'label': str} ou None
    contrainte_forte: bool = False       # PPR fort / pente forte


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _sous_exploitation(surface_m2: float, bati_ratio: Optional[float]):
    """Grand terrain peu bâti → potentiel de restructuration. Courbe saturante × (1 − bâti)."""
    if bati_ratio is None:
        return 0, None, "occupation non vérifiée (couche bâti absente)"   # jamais un faux « vacant »
    surf_f = _clamp((surface_m2 - SURFACE_PLANCHER_M2) / (SURFACE_SATURATION_M2 - SURFACE_PLANCHER_M2), 0.0, 1.0)
    bati_f = _clamp(1.0 - (bati_ratio / BATI_PLAFOND), 0.0, 1.0)
    pts = round(W_SOUS_EXPLOITATION * surf_f * bati_f)
    if pts <= 0:
        return 0, None, None
    detail = f"grand terrain peu bâti : {round(100 * bati_ratio)} % bâti sur {round(surface_m2)} m²"
    badge = "Grand terrain sous-exploité" if pts >= 15 else None
    return pts, badge, detail


def _intensite_latente(statut: str, score: int):
    """« Presque opportunité » (à creuser proche du seuil 65) > « déjà opportunité »."""
    if statut == "a_creuser":
        if 55 <= score <= 64:
            return W_INTENSITE_LATENTE, "Presque opportunité", f"à creuser, score {score}/65 (presque-seuil)"
        if 45 <= score <= 54:
            return 15, None, f"à creuser, score {score} (potentiel moyen)"
        return 8, None, "à creuser (base latente)"
    if statut == "opportunite":
        return 5, None, "déjà opportunité au verdict (potentiel mutation faible)"
    return 0, None, None   # faux positif / exclue : pas de potentiel de mutation


def compute_mutation_score(f: MutationFeatures) -> dict:
    """Moteur PUR : MutationFeatures → structure explicable. Aucune DB, aucun effet de bord."""
    raisons: list[dict] = []
    badges: list[str] = []

    def add(cle: str, pts: int, badge: Optional[str], detail: Optional[str]) -> None:
        if pts:
            raisons.append({"cle": cle, "points": pts, "detail": detail})
        if badge:
            badges.append(badge)

    pts, badge, detail = _sous_exploitation(f.surface_m2, f.bati_ratio)
    add("sous_exploitation", pts, badge, detail)
    pts, badge, detail = _intensite_latente(f.statut, f.opportunity_score)
    add("intensite_latente", pts, badge, detail)
    if f.zone_u_au:
        add("zonage_favorable", W_ZONAGE_FAVORABLE, None, "zone U/AU (constructible)")
    if f.potentiel_regional:
        add("potentiel_regional", W_POTENTIEL_REGIONAL, None, "recouvre un îlot de potentiel foncier régional")
    if f.marche_dvf:
        add("marche_actif", W_MARCHE_ACTIF, None, "marché DVF actif à proximité")
    if f.proprietaire:
        public = bool(f.proprietaire.get("public"))
        badge = ("Foncier public stratégique" if public
                 else "Propriétaire personne morale (acquisition facilitée)")
        add("foncier_acquerable", W_FONCIER_ACQUERABLE, badge,
            f.proprietaire.get("label") or ("foncier public" if public else "personne morale"))

    base = sum(r["points"] for r in raisons)
    malus = MALUS_CONTRAINTE_FORTE if f.contrainte_forte else 0
    if malus:
        raisons.append({"cle": "contrainte_forte", "points": -malus,
                        "detail": "PPR fort / pente forte — vigilance, à confirmer"})
        badges.append("Vigilance contrainte forte")

    score = int(_clamp(base - malus, 0, 100))
    confiance = int(_clamp(f.completeness_score, 0, 100))
    niveau = _niveau(score)
    # Règle d'or : données trop minces → on ne déclare jamais un fort potentiel « ferme ».
    if confiance < CONFIANCE_FLOOR and niveau in ("prioritaire", "forte"):
        niveau = "surveiller"

    limites = [AVERTISSEMENT]
    if confiance < CONFIANCE_FLOOR:
        limites.append("Données incomplètes (confiance faible) — niveau plafonné.")
    if f.contrainte_forte:
        limites.append("Contrainte forte (PPR/pente) à confirmer.")

    return {
        "score_mutation": score,
        "niveau": niveau,
        "confiance": confiance,
        "confiance_bande": _bande_confiance(confiance),
        "badges": badges,
        "raisons": raisons,
        "limites": limites,
    }


def _niveau(score: int) -> str:
    if score >= SEUIL_PRIORITAIRE:
        return "prioritaire"
    if score >= SEUIL_FORTE:
        return "forte"
    if score >= SEUIL_SURVEILLER:
        return "surveiller"
    return "faible"


def _bande_confiance(c: int) -> str:
    return "forte" if c >= 80 else "moyenne" if c >= 50 else "faible"


# ── Assemblage LECTURE SEULE (ponctuel) — pas de run massif (cf. constrainte Phase 2A) ───

def features_for_parcels(session, parcel_ids: list[int]) -> dict[int, MutationFeatures]:
    """Construit les MutationFeatures depuis la DB en **LECTURE SEULE** pour un PETIT lot.

    N'écrit RIEN (que des SELECT) ; réutilise `bati.stats_batch` (read-only). Pour un usage
    massif (24 communes), un service batché viendra en Phase 2B — ici on borne le lot."""
    from sqlalchemy import text

    from . import bati, proprietaire_type

    ids = [int(i) for i in parcel_ids]
    if not ids:
        return {}
    if len(ids) > 2000:
        raise ValueError("features_for_parcels : lot > 2000 — usage ponctuel uniquement (pas de run massif V1).")

    base = {r["id"]: r for r in session.execute(text(
        """
        SELECT p.id, p.surface_m2, e.status, e.opportunity_score, e.completeness_score
        FROM parcels p
        LEFT JOIN LATERAL (
            SELECT status, opportunity_score, completeness_score
            FROM parcel_evaluations WHERE parcel_id = p.id
            ORDER BY evaluated_at DESC, id DESC LIMIT 1) e ON true
        WHERE p.id = ANY(:ids)
        """), {"ids": ids}).mappings()}

    def latest_layer(layer: str) -> dict:
        return {r["parcel_id"]: r for r in session.execute(text(
            """
            SELECT DISTINCT ON (parcel_id) parcel_id, result, severity
            FROM cascade_results WHERE parcel_id = ANY(:ids) AND layer_name = :ln
            ORDER BY parcel_id, evaluated_at DESC, id DESC
            """), {"ids": ids, "ln": layer}).mappings()}

    zon, pot, dvf, rsq, pen = (latest_layer(l) for l in
                               ("zonage_plu_gpu", "potentiel_foncier_region", "dvf", "risques", "pente"))

    morale: dict[int, dict] = {}
    for r in session.execute(text(
        """
        SELECT p.id pid, m.groupe, m.forme_juridique, m.denomination
        FROM parcels p JOIN parcelle_personne_morale m ON m.idu = p.idu
        WHERE p.id = ANY(:ids)
        """), {"ids": ids}).mappings():
        morale[r["pid"]] = proprietaire_type.classify_dgfip(r["groupe"], r["forme_juridique"], r["denomination"])

    bati_ok = bati.layer_available(session)
    bati_stats = bati.stats_batch(session, ids) if bati_ok else {}

    def is_pos(d, pid):
        return pid in d and d[pid]["result"] in ("POSITIVE", "SOFT_FLAG")

    def is_fort(d, pid):
        return pid in d and d[pid]["severity"] == "fort"

    out: dict[int, MutationFeatures] = {}
    for pid in ids:
        b = base.get(pid)
        if not b or b["status"] is None:
            continue
        mo = morale.get(pid)
        out[pid] = MutationFeatures(
            statut=b["status"],
            opportunity_score=int(b["opportunity_score"] or 0),
            completeness_score=int(b["completeness_score"] or 0),
            surface_m2=float(b["surface_m2"] or 0.0),
            bati_ratio=(bati_stats.get(pid, {}).get("bati_ratio") if bati_ok else None),
            zone_u_au=(pid in zon and zon[pid]["result"] == "POSITIVE"),
            potentiel_regional=is_pos(pot, pid),
            marche_dvf=is_pos(dvf, pid),
            proprietaire=({"public": mo.get("public"), "label": mo.get("label")} if mo else None),
            contrainte_forte=(is_fort(rsq, pid) or is_fort(pen, pid)),
        )
    return out


def mutation_for_parcels(session, parcel_ids: list[int]) -> dict[int, dict]:
    """Score Mutation explicable pour un petit lot de parcelles (LECTURE SEULE)."""
    return {pid: compute_mutation_score(f) for pid, f in features_for_parcels(session, parcel_ids).items()}
