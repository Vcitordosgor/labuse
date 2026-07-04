"""Déclassement — volet NON-franc du garde-fou faux positifs (flags QUALITÉ, étage 1).

⚠ FUSION ÉTAGE 0 (refonte scoring, session 1) : les bloquants FRANCS qui vivaient ici
(micro-parcelle < seuil, pente > seuil, équipement OSM ≥ seuil, déjà bâti franc) sont
désormais des COUCHES D'ÉLIMINATION de phase 1 (cascade), au même titre que `eau` — leurs
seuils sont passés en YAML (config/cascade_rules.yaml, couches surface/pente/osm_faux_positif
/bati). Une parcelle franchement fausse est éliminée à l'étage 0, avec un score brut = 0 :
plus de « 78/100 — faux positif probable ». Ce module ne conserve QUE les cas NON-francs,
qui rétrogradent une opportunité en `à creuser` sans l'éliminer (surface réduite mais dans la
bande, pente 40–60 %, OSM 30–50 %, occupation partielle, accès à vérifier). Ils deviendront
des flags de qualité de l'étage 1 (session suivante) — d'ici là, comportement INCHANGÉ.

Le score brut d'opportunité est conservé tel quel (transparence) ; seul le STATUT est nuancé.
On ne REMONTE jamais un statut. Appliqué UNIQUEMENT aux survivants de l'étage 0 (cf. pipeline).
"""
from __future__ import annotations

from ..enums import EvaluationStatus as ES

# ── Seuils NON-francs (tunables). TODO étage 1 : migrer en YAML avec les flags de qualité. ──
# (Les seuils ÉLIMINATOIRES francs ont migré en config/cascade_rules.yaml — cf. docstring.)
SURFACE_MIN_M2 = 250.0      # < : sous le seuil d'un programme → jamais « opportunité »
PENTE_FORTE_PCT = 40.0      # > : aménagement difficile → jamais « opportunité »
OSM_FLAG_COVERAGE = 0.30    # ≥ : recouvre en partie un équipement → « à creuser »
# Accès (audit O1) : aucune voirie BD TOPO à moins de N mètres → enclavement PROBABLE.
# 6 m = demi-largeur de voie (le filaire BD TOPO est un AXE, pas la limite) — même
# tolérance que la façade (FACADE_TOL_M). Jamais une exclusion : une servitude de
# passage ou une desserte non cartographiée reste possible → « à creuser », motif visible.
ACCES_MAX_M = 6.0

# Sévérité croissante : on ne déclasse QUE vers le bas (rang strictement supérieur).
_RANK = {ES.OPPORTUNITE: 0, ES.A_CREUSER: 1, ES.FAUX_POSITIF_PROBABLE: 2, ES.EXCLUE: 3}
_OSM_LABEL = {"parking": "parking", "pitch": "terrain de sport", "sport": "terrain de sport",
              "cemetery": "cimetière", "school": "école"}


def _osm_label(subtype: str | None) -> str:
    return _OSM_LABEL.get((subtype or "").lower(), subtype or "équipement")


def apply_declassement(status: ES, signals: dict) -> tuple[ES, str | None]:
    """Renvoie (statut_nuancé, motif). Motif None si aucun signal NON-franc.

    `signals` : {surface_m2, pente_pct, osm_subtype, osm_coverage, acces_dist_m, bati_*}.
    Volet NON-franc uniquement : ne rétrograde qu'en `à creuser` (les bloquants francs sont
    éliminés à l'étage 0). Ne remonte jamais un statut. Appliqué aux seuls survivants (pipeline).
    """
    blockers: list[tuple[ES, str]] = []

    # TODO étage 1 : surface réduite mais > seuil franc (bande 100–250 m² sur un survivant).
    s = signals.get("surface_m2")
    if s is not None and s < SURFACE_MIN_M2:
        blockers.append((ES.A_CREUSER, f"surface réduite {s:.0f} m² — sous le seuil d'un programme"))

    # TODO étage 1 : pente forte mais aménageable (bande 40–60 % sur un survivant).
    pente = signals.get("pente_pct")
    if pente is not None and pente > PENTE_FORTE_PCT:
        blockers.append((ES.A_CREUSER, f"pente {pente:.0f} % — aménagement difficile"))

    # TODO étage 1 : recouvrement partiel d'un équipement OSM (bande 30–50 % sur un survivant).
    sub, cov = signals.get("osm_subtype"), signals.get("osm_coverage")
    if sub and cov is not None and cov >= OSM_FLAG_COVERAGE:
        blockers.append((ES.A_CREUSER,
                         f"recouvre en partie un {_osm_label(sub)} (OSM, {cov * 100:.0f} %)"))

    # TODO étage 1 — Accès (audit O1) : signal présent UNIQUEMENT si la couche voirie est ingérée
    # (clé absente sinon — jamais d'« enclavée » déduite d'une couche manquante). Non-franc : un
    # enclavement PROBABLE reste « à creuser » (servitude/desserte non cartographiée possible).
    if "acces_dist_m" in signals:
        d = signals["acces_dist_m"]
        if d is None or d > ACCES_MAX_M:
            txt = "aucune voirie cartographiée à proximité" if d is None else f"voirie la plus proche à ~{d:.0f} m"
            blockers.append((ES.A_CREUSER,
                             f"accès non identifié ({txt}, BD TOPO) — desserte ou servitude de passage à vérifier"))

    # TODO étage 1 — Correctif R1 « déjà bâti » : SEUL le cas NON-franc (partiellement bâti →
    # « à creuser ») reste ici. Le cas franc (déjà bâti / ensemble bâti, ex. BP0571) est éliminé
    # à l'étage 0 par la couche `bati` (phase 1) — même source de vérité, labuse/bati.py.
    if signals.get("bati_ratio") is not None:
        from .. import bati as _bati
        cls = _bati.classify(signals.get("bati_ratio"), signals.get("bati_count") or 0,
                             signals.get("bati_max_m2") or 0.0, signals.get("surface_m2"))
        if cls["declasse"] == "a_creuser":
            blockers.append((ES.A_CREUSER, cls["motif"]))

    if not blockers:
        return status, None

    forced = max((b[0] for b in blockers), key=lambda st: _RANK[st])
    final = forced if _RANK[forced] > _RANK[status] else status
    motif = " ; ".join(m for _, m in blockers)
    return final, motif


def compute_declass_signals(session, parcel_ids: list[int]) -> dict[int, dict]:
    """Signaux bloquants (surface, pente max, équipement OSM dominant) en BATCH SQL.

    Une seule requête par signal sur l'ensemble des parcelles (indexé geom_2975).
    Sert au pipeline (évaluation) comme au ré-application sur l'existant.
    """
    from sqlalchemy import text
    if not parcel_ids:
        return {}
    out: dict[int, dict] = {pid: {} for pid in parcel_ids}
    ids = tuple(parcel_ids)

    surf = session.execute(text(
        "SELECT id, ST_Area(geom_2975) FROM parcels WHERE id = ANY(:ids)"), {"ids": list(ids)}).all()
    for pid, a in surf:
        out[pid]["surface_m2"] = float(a) if a is not None else None

    pente = session.execute(text(
        "SELECT p.id, max((pl.attrs->>'slope_pct')::float) "
        "FROM parcels p JOIN spatial_layers pl ON pl.commune = p.commune AND pl.kind = 'pente' "
        "  AND ST_Intersects(pl.geom_2975, p.geom_2975) "
        "WHERE p.id = ANY(:ids) GROUP BY p.id"), {"ids": list(ids)}).all()
    for pid, mx in pente:
        out[pid]["pente_pct"] = float(mx) if mx is not None else None

    osm = session.execute(text(
        "SELECT id, subtype, cov FROM ("
        "  SELECT p.id, s.subtype, "
        "    ST_Area(ST_Intersection(s.geom_2975, p.geom_2975)) / NULLIF(ST_Area(p.geom_2975), 0) cov, "
        "    row_number() OVER (PARTITION BY p.id ORDER BY "
        "      ST_Area(ST_Intersection(s.geom_2975, p.geom_2975)) DESC) rn "
        "  FROM parcels p JOIN spatial_layers s ON s.commune = p.commune AND s.kind = 'osm_faux_positif' "
        "    AND ST_Intersects(s.geom_2975, p.geom_2975) "
        "  WHERE p.id = ANY(:ids)) t WHERE rn = 1"), {"ids": list(ids)}).all()
    for pid, sub, cov in osm:
        out[pid]["osm_subtype"] = sub
        out[pid]["osm_coverage"] = float(cov) if cov is not None else None

    # Correctif R1 : couverture bâtie BD TOPO (batch indexé). Si la couche n'est pas
    # ingérée, on n'émet PAS de signal (bati_ratio absent → aucune décision « vacant »
    # mensongère) — la fiche affichera « occupation non vérifiée ».
    from .. import bati as _bati
    if _bati.layer_available(session):
        for pid, st in _bati.stats_batch(session, list(ids)).items():
            out[pid].update(st)

    # Accès (audit O1) : distance à la voirie la plus proche (batch, index geom_2975).
    # Clé posée UNIQUEMENT si la couche voirie existe ; None = aucune voirie trouvée.
    has_voirie = bool(session.execute(text(
        "SELECT EXISTS(SELECT 1 FROM spatial_layers WHERE kind = 'voirie')")).scalar())
    if has_voirie:
        for pid in ids:
            out[pid].setdefault("acces_dist_m", None)
        for pid, d in session.execute(text(
            """SELECT p.id, round(ST_Distance(p.geom_2975, v.geom_2975))
               FROM parcels p
               CROSS JOIN LATERAL (
                 SELECT geom_2975 FROM spatial_layers
                 WHERE kind = 'voirie' ORDER BY p.geom_2975 <-> geom_2975 LIMIT 1) v
               WHERE p.id = ANY(:ids)"""), {"ids": list(ids)}).all():
            out[pid]["acces_dist_m"] = float(d) if d is not None else None
    return out
