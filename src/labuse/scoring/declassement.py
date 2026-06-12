"""Déclassement des FAUX POSITIFS évidents (garde-fou de confiance, post-scoring).

Un score brut élevé ne suffit pas : si une parcelle porte un signal bloquant FRANC
(elle EST un parking/équipement, elle est minuscule, ou en pente non aménageable),
on la déclasse vers `à creuser`, `faux positif probable` ou `exclue`, AVEC UN MOTIF
VISIBLE. Le score brut d'opportunité est conservé tel quel (transparence) ; seul le
STATUT final est corrigé. On ne REMONTE jamais un statut, on ne fait que déclasser.

Calibré sur données réelles (Saint-Paul) pour NE PAS déclasser à tort une grande
parcelle qui ne fait qu'effleurer un équipement (chevauchement de bord) : seuls les
recouvrements FRANCS comptent.
"""
from __future__ import annotations

from ..enums import EvaluationStatus as ES

# ── Seuils (tunables). Pensés pour le promoteur : on ne perd que des cas douteux. ──
SURFACE_FAUX_M2 = 100.0      # < : aucun programme possible → faux positif probable
SURFACE_MIN_M2 = 250.0      # < : sous le seuil d'un programme → jamais « opportunité »
PENTE_FAUX_PCT = 60.0       # > : terrain non aménageable → faux positif probable
PENTE_FORTE_PCT = 40.0      # > : aménagement difficile → jamais « opportunité »
OSM_FAUX_COVERAGE = 0.50    # ≥ : la parcelle EST l'équipement → faux positif probable
OSM_FLAG_COVERAGE = 0.30    # ≥ : recouvre en partie un équipement → « à creuser »

# Sévérité croissante : on ne déclasse QUE vers le bas (rang strictement supérieur).
_RANK = {ES.OPPORTUNITE: 0, ES.A_CREUSER: 1, ES.FAUX_POSITIF_PROBABLE: 2, ES.EXCLUE: 3}
_OSM_LABEL = {"parking": "parking", "pitch": "terrain de sport", "sport": "terrain de sport",
              "cemetery": "cimetière", "school": "école"}


def _osm_label(subtype: str | None) -> str:
    return _OSM_LABEL.get((subtype or "").lower(), subtype or "équipement")


def apply_declassement(status: ES, signals: dict) -> tuple[ES, str | None]:
    """Renvoie (statut_corrigé, motif). Motif None si aucun signal bloquant.

    `signals` : {surface_m2, pente_pct, osm_subtype, osm_coverage} (toutes optionnelles).
    Plusieurs signaux « faux positif » cumulés → `exclue`.
    """
    blockers: list[tuple[ES, str]] = []

    s = signals.get("surface_m2")
    if s is not None:
        if s < SURFACE_FAUX_M2:
            blockers.append((ES.FAUX_POSITIF_PROBABLE, f"micro-parcelle {s:.0f} m² — aucun programme possible"))
        elif s < SURFACE_MIN_M2:
            blockers.append((ES.A_CREUSER, f"surface réduite {s:.0f} m² — sous le seuil d'un programme"))

    pente = signals.get("pente_pct")
    if pente is not None:
        if pente > PENTE_FAUX_PCT:
            blockers.append((ES.FAUX_POSITIF_PROBABLE, f"pente {pente:.0f} % — terrain non aménageable"))
        elif pente > PENTE_FORTE_PCT:
            blockers.append((ES.A_CREUSER, f"pente {pente:.0f} % — aménagement difficile"))

    sub, cov = signals.get("osm_subtype"), signals.get("osm_coverage")
    if sub and cov is not None:
        if cov >= OSM_FAUX_COVERAGE:
            blockers.append((ES.FAUX_POSITIF_PROBABLE,
                             f"{_osm_label(sub)} sur {cov * 100:.0f} % de la parcelle (OSM)"))
        elif cov >= OSM_FLAG_COVERAGE:
            blockers.append((ES.A_CREUSER,
                             f"recouvre en partie un {_osm_label(sub)} (OSM, {cov * 100:.0f} %)"))

    # Correctif R1 « déjà bâti » : couverture bâtiments BD TOPO (cf. labuse/bati.py —
    # classification graduée : la règle « ensemble bâti » attrape les résidences dont le
    # ratio reste sous 30 % à cause des espaces communs, ex. BP0571 = 18 % / 4 bâtiments).
    if signals.get("bati_ratio") is not None:
        from .. import bati as _bati
        cls = _bati.classify(signals.get("bati_ratio"), signals.get("bati_count") or 0,
                             signals.get("bati_max_m2") or 0.0, signals.get("surface_m2"))
        if cls["declasse"] == "faux_positif":
            blockers.append((ES.FAUX_POSITIF_PROBABLE, cls["motif"]))
        elif cls["declasse"] == "a_creuser":
            blockers.append((ES.A_CREUSER, cls["motif"]))

    if not blockers:
        return status, None

    strong = [b for b in blockers if b[0] == ES.FAUX_POSITIF_PROBABLE]
    forced = ES.EXCLUE if len(strong) >= 2 else max((b[0] for b in blockers), key=lambda st: _RANK[st])
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
    return out
