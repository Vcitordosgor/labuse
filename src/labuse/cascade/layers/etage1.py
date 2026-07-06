"""Couches ÉTAGE 1 (dry-run) — QUALITÉ : friches, Géorisques ponctuels, aménités.

Signaux de qualité (bonus/malus/flags) sur les survivants. CHAQUE verdict porte
`extra = {source_table, source_id}` → cliquable jusqu'à l'enregistrement exact (exigence non
négociable). Poids/seuils/bandes en config (cascade_rules.yaml + opportunity_weights.yaml).

Non branché au scoring live — évalué en dry-run (tables dryrun_*).
"""
from __future__ import annotations

from ...enums import Severity
from ..base import Layer, Verdict, passed, positive, register, soft_flag, unknown
from ..context import EvalContext, ParcelRef

SRC_FRICHE = "Cartofriches (Cerema)"
SRC_SOLP = "Géorisques — sites et sols pollués"
SRC_CAVITE = "Géorisques — cavités souterraines"
SRC_ICPE = "Géorisques — ICPE"
SRC_MVT = "Géorisques — mouvements de terrain"
SRC_OSM = "OpenStreetMap / Overpass"


def _trace(v: Verdict, table: str, source_id) -> Verdict:
    """Rend le verdict cliquable : source_table + source_id dans extra (lu par le writer dry-run)."""
    v.extra = {"source_table": table, "source_id": source_id}
    return v


@register
class FricheLayer(Layer):
    name = "friche"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Friches non ingérées.", source=SRC_FRICHE)
        inter = [i for i in ctx.intersections(parcel.id, kind) if i.coverage > 0]
        if not inter:
            return passed(self.name, "Aucune friche recensée.", source=SRC_FRICHE)
        i = max(inter, key=lambda x: x.coverage)
        statut = (i.subtype or "").lower()          # subtype = site_statut ('friche avec projet'…)
        avec = "avec projet" in statut
        mag = params["magnitude_avec_projet"] if avec else params["magnitude_sans_projet"]
        label = i.name or "friche"
        return _trace(positive(self.name, f"Friche {statut or '—'} — reconversion ({label}).",
                               params["bonus_key"], magnitude=mag, source=SRC_FRICHE),
                      "spatial_layers", i.id)


class _NearestFlagLayer(Layer):
    """Base : flag SOFT_FLAG si un POI ponctuel du kind est sous le cap (le plus proche)."""

    src = ""

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, f"Couche {kind} non ingérée.", source=self.src)
        np = ctx.nearest_point(parcel.id, kind)
        if np is None:
            return passed(self.name, "Aucun objet recensé à proximité.", source=self.src)
        sev = self._severity(np["dist"], params)
        detail = f"{params['detail']} ({np.get('name') or kind}, {np['dist']:.0f} m)"
        return _trace(soft_flag(self.name, detail, sev, source=self.src), "spatial_layers", np["id"])

    def _severity(self, dist: float, params: dict) -> Severity:
        return Severity(params.get("severity", "faible"))


@register
class SolPollueLayer(_NearestFlagLayer):
    name = "sol_pollue"
    src = SRC_SOLP


@register
class CaviteLayer(_NearestFlagLayer):
    name = "cavite"
    src = SRC_CAVITE


@register
class MvtLayer(_NearestFlagLayer):
    name = "mvt"
    src = SRC_MVT     # severity 'info' (×0) → flag affiché, 0 point (anti double-compte PPR)


@register
class IcpeLayer(_NearestFlagLayer):
    name = "icpe"
    src = SRC_ICPE

    def _severity(self, dist: float, params: dict) -> Severity:
        b = params["bandes_m"]                        # {fort:50, moyen:150, faible:300}
        if dist <= b["fort"]:
            return Severity.FORT
        if dist <= b["moyen"]:
            return Severity.MOYEN
        return Severity.FAIBLE


@register
class AmenitesLayer(Layer):
    name = "amenites"

    _COLS = {"ecole": "dist_ecole_m", "commerce": "dist_commerce_m",
             "sante": "dist_sante_m", "tcsp": "dist_tcsp_m"}

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        am = ctx.amenites(parcel.id)
        if am is None:
            return unknown(self.name, "Aménités non calculées pour la parcelle.", source=SRC_OSM)
        defo, tcsp_b = params["bandes_defaut_m"], params["bandes_tcsp_m"]
        pond = params["ponderations"]
        mag = 0.0
        for cat, col in self._COLS.items():
            d = am.get(col)
            bands = tcsp_b if cat == "tcsp" else defo
            if d is None:
                prox = 0.0
            elif d <= bands["plein"]:
                prox = 1.0
            elif d <= bands["demi"]:
                prox = 0.5
            else:
                prox = 0.0
            mag += pond[cat] * prox
        def _m(col):
            v = am.get(col)
            return f"{int(v)}m" if v is not None else "—"
        detail = (f"Aménités : école {_m('dist_ecole_m')}, commerce {_m('dist_commerce_m')}, "
                  f"santé {_m('dist_sante_m')}, bus {_m('dist_tcsp_m')} (score {mag:.2f}).")
        return _trace(positive(self.name, detail, params["bonus_key"], magnitude=mag, source=SRC_OSM),
                      "parcel_amenites", parcel.id)
