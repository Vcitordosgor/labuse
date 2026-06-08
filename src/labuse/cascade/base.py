"""Abstractions de la cascade : Verdict, Layer, registry.

Chaque couche implémente `evaluate()` et renvoie 0..n Verdicts. Le moteur lit
l'ordre, l'activation, la phase et les params dans config/cascade_rules.yaml :
la couche ne connaît que sa logique, pas sa position.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..enums import CascadeVerdict, Severity

if TYPE_CHECKING:
    from .context import EvalContext, ParcelRef


@dataclass
class Verdict:
    """Résultat d'une couche pour une parcelle (→ une ligne cascade_results)."""

    layer_name: str
    result: CascadeVerdict
    detail: str                              # motif humain : POURQUOI (le produit)
    severity: Severity | None = None         # requis pour SOFT_FLAG
    bonus_key: str | None = None             # clé de bonus (POSITIVE) → opportunity_weights
    magnitude: float = 1.0                   # POSITIVE : intensité 0..1 du bonus (×poids config). 1.0 = bonus plein/binaire
    exclude_kind: str | None = None          # "exclue" | "faux_positif" (pour HARD_EXCLUDE)
    data_source_name: str | None = None      # source ayant alimenté ce verdict
    extra: dict[str, Any] = field(default_factory=dict)  # ex. surface_m2, slope_label

    def is_hard_exclude(self) -> bool:
        return self.result == CascadeVerdict.HARD_EXCLUDE


def hard_exclude(layer: str, detail: str, *, kind: str = "faux_positif", source: str | None = None) -> Verdict:
    return Verdict(layer, CascadeVerdict.HARD_EXCLUDE, detail, exclude_kind=kind, data_source_name=source)


def soft_flag(layer: str, detail: str, severity: Severity, *, source: str | None = None) -> Verdict:
    return Verdict(layer, CascadeVerdict.SOFT_FLAG, detail, severity=severity, data_source_name=source)


def positive(layer: str, detail: str, bonus_key: str, *, magnitude: float = 1.0, source: str | None = None) -> Verdict:
    # magnitude ∈ [0,1] : part du poids config réellement attribuée (continu, borné, tracé).
    m = max(0.0, min(1.0, float(magnitude)))
    return Verdict(layer, CascadeVerdict.POSITIVE, detail, bonus_key=bonus_key, magnitude=m, data_source_name=source)


def passed(layer: str, detail: str = "", *, source: str | None = None, **extra) -> Verdict:
    return Verdict(layer, CascadeVerdict.PASS, detail, data_source_name=source, extra=extra)


def unknown(layer: str, detail: str, *, source: str | None = None) -> Verdict:
    return Verdict(layer, CascadeVerdict.UNKNOWN, detail, data_source_name=source)


class Layer:
    """Classe de base d'une couche. `name` doit matcher config/cascade_rules.yaml."""

    name: str = ""

    def evaluate(
        self, parcel: "ParcelRef", ctx: "EvalContext", params: dict[str, Any]
    ) -> Verdict | list[Verdict] | None:
        raise NotImplementedError


REGISTRY: dict[str, Layer] = {}


def register(layer_cls: type[Layer]) -> type[Layer]:
    """Décorateur : enregistre une couche par son `name`."""
    inst = layer_cls()
    if not inst.name:
        raise ValueError(f"{layer_cls.__name__} doit définir un `name`")
    REGISTRY[inst.name] = inst
    return layer_cls
