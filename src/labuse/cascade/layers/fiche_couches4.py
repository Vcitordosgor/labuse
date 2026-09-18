"""FICHE-COUCHES-4 lot 2 — deux couches de cascade de plus (cimetière = servitude de voisinage,
onglet Risques ; VEFA neuf = contexte marché, onglet Marché). piscine_cosia est branchée à part
(bloc fiscal territoire_fiscal, cf. _territoire_fiscal_block). Même patron que fiche_couches2."""
from __future__ import annotations

from sqlalchemy import text

from ...enums import Severity
from ..base import Layer, Verdict, passed, register, soft_flag, unknown
from ..context import EvalContext, ParcelRef

SRC_CIM = "BD TOPO — cimetières"
SRC_VEFA = "geo-DVF (mutations VEFA, DGFiP) · Sitadel"


def _trace(v: Verdict, source_id) -> Verdict:
    v.extra = {"source_table": "spatial_layers", "source_id": source_id}
    return v


@register
class CimetiereLayer(Layer):
    """Parcelle à MOINS DE 100 m d'un cimetière — servitude de voisinage (salubrité, recul :
    art. L2223-5 / R2223-7 CGCT, interdiction sans autorisation dans le périmètre). SOFT_FLAG faible,
    onglet Risques. Proximité à l'emprise (polygone) via ST_Distance ≤ cap, comme l'ICPE."""

    name = "cimetiere"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Cimetières non ingérés.", source=SRC_CIM)
        cap = float(params.get("cap_m", 100))
        np = ctx.session.execute(text(
            """WITH p AS (SELECT geom_2975 FROM parcels WHERE id = :pid)
               SELECT sl.id, sl.name, ST_Distance(sl.geom_2975, p.geom_2975) AS dist
               FROM spatial_layers sl, p
               WHERE sl.kind = :kind AND ST_DWithin(sl.geom_2975, p.geom_2975, :cap)
               ORDER BY dist LIMIT 1"""),
            {"pid": parcel.id, "kind": kind, "cap": cap}).mappings().first()
        if np is None:
            return passed(self.name, "Aucun cimetière à moins de 100 m.", source=SRC_CIM)
        d = float(np["dist"])
        ou = "au contact de la parcelle" if d <= 5 else f"à ~{d:.0f} m"
        return _trace(soft_flag(
            self.name,
            f"Cimetière {ou} — servitude de voisinage : recul et salubrité (art. L2223-5 / "
            "R2223-7 CGCT, construction encadrée dans le périmètre).",
            Severity(params.get("severity", "faible")), source=SRC_CIM), np["id"])


@register
class VefaNeufLayer(Layer):
    """Contexte MARCHÉ du logement neuf (VEFA) de la commune — aplat COMMUNE (prix médian ou tranche
    « moins de N ventes »). INFO (0 point) : c'est un repère de marché, pas une contrainte. Onglet Marché."""

    name = "vefa_neuf"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Prix du neuf (VEFA) non ingéré.", source=SRC_VEFA)
        inter = [i for i in ctx.intersections(parcel.id, kind) if i.coverage > 0]
        if not inter:
            return passed(self.name, "Commune hors couverture VEFA.", source=SRC_VEFA)
        i = inter[0]
        a = i.attrs or {}
        prix = a.get("prix_m2_neuf")
        tr = a.get("tranche") or "—"
        n = a.get("n_ventes")
        prix_txt = f" — prix médian ~{prix} €/m²" if prix else ""
        n_txt = f" ({n} ventes VEFA / 36 mois)" if n is not None else ""
        return _trace(soft_flag(
            self.name,
            f"Marché du logement neuf (VEFA) sur la commune : {tr}{n_txt}{prix_txt}. "
            "Repère de marché (aplat commune), pas une contrainte de la parcelle.",
            Severity.INFO, source=SRC_VEFA), i.id)
