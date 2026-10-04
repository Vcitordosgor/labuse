"""Score LABUSE V1 (SL-1) — SCORING-6 lot B.

« À quel point cette parcelle mérite-t-elle d'être étudiée comme opportunité foncière ? »
Intérêt foncier intrinsèque, orienté production de logement. Ce N'EST PAS une probabilité de
vente (c'est le Signal de mutation, lot D) : aucune feature de marché ni de propriétaire n'entre
dans le chiffre.

Chaîne (SCORING-5-RAPPORT §2, corrigée par SCORING-5-RETOUR §1) :

    score = clip( barème_capacité(SDP résiduelle) × coef_faisabilité , 0, 100 )

  · barème_capacité : SDP résiduelle (lue de la vue `parcel_residuel` — servie ; elle mangera
    la capacité sur assiette clippée au run q_v15, lot A) → points saturants ; ×0,5 si zone AU
    différée.
  · coef_faisabilité : produit gradué pente × forme × accès × bâti, plancher 0,4. Le bâti n'est
    JAMAIS une exclusion (acquis PALIERS-1) : il pèse sur le coefficient, pas sur l'assiette.
  · contexte : information fiche, HORS calcul (SCORING-5-RETOUR §1 corr. 2).

DÉTERMINISTE : fonction pure des caches par parcelle. Aucun rang, aucun percentile, aucun quota
(contrat §11 du mandat SCORING-5, satisfait par construction). Le barème vit dans
`config/score_labuse.yaml` ; son hash entre dans `score_version` (labuse_v1+<hash8>).

Absence d'une donnée non critique = facteur neutre 1,0 (jamais un malus) + couverture qui baisse.
Entrée critique absente (zone non résolue, règle PLU non validée, donnée/géométrie manquante) →
`non_calculable` avec le motif, JAMAIS 0.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml
from sqlalchemy import text
from sqlalchemy.orm import Session

_CONFIG = Path(__file__).resolve().parents[3] / "config" / "score_labuse.yaml"

# Motifs de non-calculabilité (mandat SCORING-6 lot B).
NC_ZONE = "zone non résolue"
NC_REGLE_PLU = "règle PLU non validée"
NC_DONNEE = "donnée critique absente"
NC_GEOMETRIE = "géométrie"

# Classes AU différées (capacité ×0,5) — mêmes codes que le résiduel/l'écran.
_AU_DIFFEREE = {"declasse_au_fermee", "declasse_au_statut_inconnu"}


@lru_cache(maxsize=1)
def charger_bareme(path: str | None = None) -> tuple[dict, str]:
    """(barème, score_version). Le hash sha256 du fichier YAML entre dans la version :
    `labuse_v1+<hash8>` — changer le barème sans re-lire la version fait échouer un test."""
    p = Path(path) if path else _CONFIG
    raw = p.read_bytes()
    doc = (yaml.safe_load(raw) or {}).get("score_labuse", {})
    h = hashlib.sha256(raw).hexdigest()[:8]
    version = f"{doc.get('version_base', 'labuse_v1')}+{h}"
    return doc, version


@dataclass
class ScoreEntrees:
    """Entrées par parcelle, lues des caches (aucune écriture)."""
    parcel_id: int
    idu: str
    commune: str
    residuel_present: bool
    sdp_residuelle_m2: float | None
    taux_emprise_pct: float | None
    cause: str | None
    capacite_estimee: bool | None
    pente_moy_deg: float | None
    aire_m2: float | None
    perimetre_m: float | None
    faitage_m: float | None
    au_classe: str | None
    acces: str | None            # verdict cascade `acces` (POSITIVE/PASS/…) ou None


@dataclass
class ScoreLabuse:
    parcel_id: int
    idu: str
    commune: str
    score: int | None
    bande: str                   # A / B / C / D / NC
    non_calculable: bool
    cause: str | None
    couverture: dict             # {pct, presentes, manquantes}
    confiance: dict              # {niveau, notes}
    contributions: list          # [{sens: 'hausse'|'baisse', libelle}]
    score_version: str
    run_label: str
    # Décomposition littérale (pour la fiche, les tests, l'explicabilité) — jamais un SHAP.
    details: dict = field(default_factory=dict)


# ── barème capacité ──────────────────────────────────────────────────────────
def _bareme_capacite(sdp: float | None, au_classe: str | None, cap: dict) -> tuple[float, float]:
    """(points de capacité, multiplicateur AU). sdp ≤ 0 → 0. Barème saturant."""
    s = float(sdp or 0.0)
    if s <= 0:
        pts = 0.0
    else:
        pts = float(cap.get("au_dela_points", 100))
        for seuil, points in cap.get("paliers", []):
            if s < float(seuil):
                pts = float(points)
                break
    mult = float(cap.get("au_fermee_mult", 0.5)) if au_classe in _AU_DIFFEREE else 1.0
    return pts * mult, mult


# ── facteurs de faisabilité ──────────────────────────────────────────────────
def _f_pente(pente_deg: float | None, fa: dict) -> tuple[float, float | None]:
    """(facteur, pente %). Pente absente → neutre 1,0 (jamais un malus)."""
    if pente_deg is None:
        return 1.0, None
    pente_pct = math.tan(math.radians(float(pente_deg))) * 100.0
    for seuil, fac in fa.get("pente_pct", []):
        if pente_pct <= float(seuil):
            return float(fac), pente_pct
    return float(fa.get("pente_au_dela", 0.6)), pente_pct


def _f_forme(aire: float | None, perim: float | None, fa: dict) -> float:
    """Parcelle en lame → facteur ; approxime emprise_lineaire (largeur w = 2·aire/périmètre)."""
    conf = fa.get("forme", {})
    if not aire or not perim or perim <= 0:
        return 1.0
    w = 2.0 * aire / perim
    if w <= 0:
        return 1.0
    allong = aire / (w * w)
    if w < float(conf.get("largeur_max_m", 8)) and allong > float(conf.get("allongement_min", 8)):
        return float(conf.get("facteur", 0.8))
    return 1.0


def _f_acces(acces: str | None, fa: dict) -> float:
    """cascade `acces` = PASS (voie desservante ≤10 m non identifiée) → malus ; sinon/absent = neutre."""
    return float(fa.get("acces_non_identifie", 0.85)) if acces == "PASS" else 1.0


def _f_bati(emp: float | None, faitage_m: float | None, fa: dict) -> float:
    """Facteur bâti gradué par emprise + faîtage (≥ R+2). Emprise absente → nu (1,0)."""
    bati = fa.get("bati", {})
    e = float(emp or 0.0)
    r2 = float(faitage_m or 0.0) >= float(bati.get("faitage_r2_m", 9))
    idx = 1 if r2 else 0
    for seuil, paire in bati.get("emprise_pct", []):
        if e <= float(seuil):
            return float(paire[idx])
    return float((bati.get("au_dela", [0.65, 0.65]))[idx])


# ── non-calculabilité ────────────────────────────────────────────────────────
def _cause_nc(e: ScoreEntrees) -> str | None:
    """Motif de non-calculabilité, ou None si le score se calcule (un vrai 0 n'est PAS NC)."""
    if not e.residuel_present:
        return NC_DONNEE
    if not e.aire_m2 or e.aire_m2 <= 0 or not e.perimetre_m or e.perimetre_m <= 0:
        return NC_GEOMETRIE
    c = (e.cause or "")
    if c.startswith("zone_non_resolue") or c == "hors_plu":
        return NC_ZONE
    if c.startswith("regle_plu_non_validee"):     # après merge PLU-CALIBRAGE-6/7 (geste Vic)
        return NC_REGLE_PLU
    return None


def bande_de_score(score: int | None, bareme: dict) -> str:
    """Bande ABSOLUE (décisions Vic, SCORING-7 §1). score None → NC ; score 0 → bande « 0 »
    (à part, jamais D) ; sinon seuils A/B/C puis D (1-29). Un vrai 0 n'est JAMAIS NC (cf.
    `_cause_nc`, qui met NC uniquement quand le score n'est pas calculable) et JAMAIS D."""
    b = bareme.get("bandes", {})
    if score is None:
        return "NC"
    if score == 0:
        return str(b.get("zero", "0"))
    for seuil, lib in b.get("seuils", []):
        if score >= int(seuil):
            return str(lib)
    return str(b.get("au_dessous", "D"))


def libelle_client_bande(bande: str, bareme: dict, cause: str | None = None) -> str:
    """Mot CLIENT d'une bande (décisions Vic, présentation seule). NC porte sa cause lisible
    (« Analyse incomplète — zone non résolue »). Repli sur le code de bande si non gravé."""
    voc = bareme.get("bandes", {}).get("vocabulaire_client", {})
    lib = str(voc.get(bande, bande))
    if bande == "NC" and cause:
        lib = f"{lib} — {cause}"
    return lib


def score_parcelle(e: ScoreEntrees, bareme: dict, version: str, run_label: str) -> ScoreLabuse:
    """Score d'UNE parcelle — fonction PURE (aucune base). Reproductible : mêmes entrées =
    même score, quel que soit le contexte d'appel (contrat §11)."""
    cap = bareme.get("capacite", {})
    fa = bareme.get("faisabilite", {})

    nc = _cause_nc(e)
    # Couverture / confiance se calculent dans tous les cas (info stockée à part du chiffre).
    emp = e.taux_emprise_pct
    couv_present, couv_manq = [], []
    (couv_present if e.pente_moy_deg is not None else couv_manq).append("pente")
    (couv_present if e.acces is not None else couv_manq).append("accès à la voie")
    if (emp or 0) > 0:
        (couv_present if e.faitage_m is not None else couv_manq).append("hauteur du bâti")
    total = len(couv_present) + len(couv_manq)
    couverture = {"pct": round(100 * len(couv_present) / total) if total else 100,
                  "presentes": couv_present, "manquantes": couv_manq}

    notes = []
    if e.capacite_estimee:
        notes.append("capacité estimée — zone PLU non calibrée finement")
    if (emp or 0) > 0 and e.faitage_m is None:
        notes.append("hauteur du bâti non ingérée — cran de démolition par l'emprise seule")
    if e.pente_moy_deg is None:
        notes.append("pente non renseignée")
    niveau = "haute" if not notes else ("faible" if len(notes) >= 2 else "moyenne")
    confiance = {"niveau": niveau, "notes": notes}

    if nc is not None:
        return ScoreLabuse(
            e.parcel_id, e.idu, e.commune, None, "NC", True, nc,
            couverture, confiance,
            [{"sens": "info", "libelle": f"Analyse non calculable : {nc}."}],
            version, run_label,
            details={"non_calculable": nc})

    bareme_cap, au_mult = _bareme_capacite(e.sdp_residuelle_m2, e.au_classe, cap)
    f_pente, pente_pct = _f_pente(e.pente_moy_deg, fa)
    f_forme = _f_forme(e.aire_m2, e.perimetre_m, fa)
    f_acces = _f_acces(e.acces, fa)
    f_bati = _f_bati(emp, e.faitage_m, fa)
    coef = max(float(fa.get("plancher", 0.4)), f_pente * f_forme * f_acces * f_bati)
    score = min(100, round(bareme_cap * coef))

    contributions = []
    sdp = round(float(e.sdp_residuelle_m2 or 0))
    if sdp > 0:
        contributions.append({"sens": "hausse", "libelle": f"{sdp} m² de droits à construire restants"})
    else:
        contributions.append({"sens": "baisse", "libelle": "aucune SDP résiduelle exploitable"})
    if au_mult < 1.0:
        contributions.append({"sens": "baisse", "libelle": "zone AU fermée — capacité différée"})
    if f_pente < 1.0:
        contributions.append({"sens": "baisse", "libelle": f"pente forte ({round(pente_pct)} %)"})
    if f_forme < 1.0:
        contributions.append({"sens": "baisse", "libelle": "parcelle en lame — géométrie contraignante"})
    if f_acces < 1.0:
        contributions.append({"sens": "baisse", "libelle": "accès à la voie non identifié"})
    if f_bati < 1.0:
        contributions.append({"sens": "baisse",
                              "libelle": f"bâti existant sur {round(emp or 0)} % de la parcelle — "
                                         "démolition à prévoir"})

    return ScoreLabuse(
        e.parcel_id, e.idu, e.commune, score, bande_de_score(score, bareme), False, None,
        couverture, confiance, contributions, version, run_label,
        details={"bareme_capacite": round(bareme_cap, 2), "au_mult": au_mult,
                 "f_pente": round(f_pente, 4), "f_forme": round(f_forme, 4),
                 "f_acces": round(f_acces, 4), "f_bati": round(f_bati, 4),
                 "coef": round(coef, 4), "sdp_residuelle_m2": sdp,
                 "taux_emprise_pct": round(emp) if emp is not None else None})


# ── lecture des caches (batch) ───────────────────────────────────────────────
# UNE ligne par parcelle pour CHAQUE cache, par une règle EXPLICITE — jamais « la dernière
# au hasard » (SCORING-8 lot A). Les trois tables nommées ont aujourd'hui une clé primaire sur
# la colonne de jointure (0 doublon mesuré), mais `parcel_residuel` et `dryrun_cascade_results`
# n'ont AUCUNE contrainte d'unicité : la requête se garantit donc elle-même, sans dépendre d'un
# invariant tenu ailleurs. Chaque sous-requête choisit la ligne la plus CONTRAIGNANTE, de sorte
# que le score est le même quel que soit l'ordre des lignes en base.
_ENTREES_SQL = text("""
SELECT p.id, p.idu, p.commune,
       (r.parcel_id IS NOT NULL)                       AS residuel_present,
       r.sdp_residuelle_m2                             AS sdp,
       r.taux_emprise_pct                              AS emp,
       r.cause                                         AS cause,
       r.capacite_estimee                              AS capacite_estimee,
       t.pente_moy_deg                                 AS pente_moy_deg,
       ST_Area(p.geom_2975)                            AS aire,
       ST_Perimeter(p.geom_2975)                       AS perim,
       h.faitage_m                                     AS faitage_m,
       au.classe                                       AS au_classe,
       acc.result                                      AS acces
FROM parcels p
-- résiduel : cache MULTI-CHAMP cohérent (SDP, emprise, cause calculés ensemble) → on prend la
-- ligne COMPLÈTE la plus récente, jamais un mélange de champs de lignes différentes.
LEFT JOIN LATERAL (
    SELECT r0.parcel_id, r0.sdp_residuelle_m2, r0.taux_emprise_pct, r0.cause, r0.capacite_estimee
    FROM parcel_residuel r0 WHERE r0.parcel_id = p.id
    ORDER BY r0.computed_at DESC NULLS LAST, r0.sdp_residuelle_m2 ASC NULLS LAST
    LIMIT 1) r ON TRUE
-- faîtage = MAX des mesures LiDAR de la parcelle (le bâtiment le plus HAUT → cran R+2 déclenché
-- dès qu'un bâtiment ≥ faitage_r2_m, quel que soit l'ordre).
LEFT JOIN LATERAL (
    SELECT max(h0.faitage_m) AS faitage_m FROM batiment_hauteur_lidar h0 WHERE h0.idu = p.idu) h ON TRUE
-- terrain : pente la plus CONTRAIGNANTE (la plus forte) si plusieurs mesures.
LEFT JOIN LATERAL (
    SELECT max(t0.pente_moy_deg) AS pente_moy_deg FROM parcel_terrain t0 WHERE t0.idu = p.idu) t ON TRUE
-- statut AU : le plus CONTRAIGNANT = une classe AU différée (cf. _AU_DIFFEREE, capacité ×0,5)
-- l'emporte sur toute autre ; départage alphabétique pour le déterminisme.
LEFT JOIN LATERAL (
    SELECT au0.classe FROM parcel_au_statut au0 WHERE au0.parcel_id = p.id
    ORDER BY (au0.classe IN ('declasse_au_fermee', 'declasse_au_statut_inconnu')) DESC, au0.classe
    LIMIT 1) au ON TRUE
-- cascade `acces` : verdict le plus DÉFAVORABLE (PASS = voie non identifiée → malus) si plusieurs.
LEFT JOIN LATERAL (
    SELECT d.result FROM dryrun_cascade_results d
    WHERE d.run_label = :clabel AND d.parcel_id = p.id AND d.layer_name = 'acces'
    ORDER BY (d.result = 'PASS') DESC
    LIMIT 1) acc ON TRUE
WHERE p.id = ANY(:ids)
""")


def lire_entrees(session: Session, parcel_ids: list[int],
                 cascade_label: str | None = None) -> dict[int, ScoreEntrees]:
    """Lit les caches pour un ensemble de parcelles. `cascade_label` désigne le run dont on lit
    le verdict `acces` (facteur mineur) ; None → accès neutre (couverture qui baisse)."""
    rows = session.execute(_ENTREES_SQL, {"ids": list(parcel_ids), "clabel": cascade_label or ""})
    out: dict[int, ScoreEntrees] = {}
    for r in rows:
        out[r.id] = ScoreEntrees(
            parcel_id=r.id, idu=r.idu, commune=r.commune,
            residuel_present=bool(r.residuel_present),
            sdp_residuelle_m2=float(r.sdp) if r.sdp is not None else None,
            taux_emprise_pct=float(r.emp) if r.emp is not None else None,
            cause=r.cause, capacite_estimee=r.capacite_estimee,
            pente_moy_deg=float(r.pente_moy_deg) if r.pente_moy_deg is not None else None,
            aire_m2=float(r.aire) if r.aire is not None else None,
            perimetre_m=float(r.perim) if r.perim is not None else None,
            faitage_m=float(r.faitage_m) if r.faitage_m is not None else None,
            au_classe=r.au_classe, acces=r.acces)
    return out


def score_batch(session: Session, parcel_ids: list[int], run_label: str, *,
                cascade_label: str | None = None,
                bareme: dict | None = None, version: str | None = None) -> list[ScoreLabuse]:
    """Score LABUSE d'un sous-ensemble de parcelles (sans cascade ni run complet — le Score se
    calcule à la volée, contrat §8 du rapport). Ordre = celui de `parcel_ids` (jamais un rang)."""
    if bareme is None or version is None:
        bareme, version = charger_bareme()
    entrees = lire_entrees(session, parcel_ids, cascade_label)
    res: list[ScoreLabuse] = []
    for pid in parcel_ids:
        e = entrees.get(pid)
        if e is None:
            continue
        res.append(score_parcelle(e, bareme, version, run_label))
    return res
