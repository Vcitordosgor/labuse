"""Chargement des conventions d'implantation (hypothèses « Estimé », jamais des règles PLU).

Chaque convention porte un nom et une valeur. Le moteur ne lit QUE ce fichier pour ses
hypothèses géométriques ; aucune valeur d'ici ne peut rendre un contrôle réglementaire « Réussi ».
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_DEFAUT = Path(__file__).resolve().parents[3] / "config" / "implantation_conventions.yaml"


@dataclass(frozen=True)
class Module:
    type: str
    surface_m2: float
    pieces: int


@dataclass(frozen=True)
class Conventions:
    version: str
    etiquette: str
    # bâtiment
    profondeur_m: float
    largeur_coursive_m: float
    largeur_noyau_m: float
    hauteur_etage_m: float
    coef_plancher_habitable: float
    retrait_inter_barre_m: float
    inset_zone_m: float
    # modules
    modules: dict[str, Module]
    repartition_equilibre: list[str]
    # stationnement
    place_longueur_m: float
    place_largeur_m: float
    allee_largeur_m: float
    acces_largeur_m: float
    source: dict[str, Any]

    def largeur_module(self, type_logement: str) -> float:
        """Largeur d'un module = surface_m2 / (profondeur - coursive). Déterministe, de la géométrie."""
        m = self.modules[type_logement]
        return m.surface_m2 / (self.profondeur_m - self.largeur_coursive_m)

    def profondeur_logement_m(self) -> float:
        return self.profondeur_m - self.largeur_coursive_m


def charger(path: str | Path | None = None) -> Conventions:
    p = Path(path) if path else _DEFAUT
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    bat = raw["batiment"]
    mods = {k: Module(type=k, surface_m2=float(v["surface_m2"]), pieces=int(v["pieces"]))
            for k, v in raw["modules"].items()}
    st = raw["stationnement"]
    return Conventions(
        version=str(raw["version"]),
        etiquette=str(raw.get("etiquette", "Estimé")),
        profondeur_m=float(bat["profondeur_m"]),
        largeur_coursive_m=float(bat["largeur_coursive_m"]),
        largeur_noyau_m=float(bat["largeur_noyau_m"]),
        hauteur_etage_m=float(bat["hauteur_etage_m"]),
        coef_plancher_habitable=float(bat["coef_plancher_habitable"]),
        retrait_inter_barre_m=float(bat["retrait_inter_barre_m"]),
        inset_zone_m=float(bat.get("inset_zone_m", 0.1)),
        modules=mods,
        repartition_equilibre=list(raw["repartition_equilibre"]),
        place_longueur_m=float(st["place_longueur_m"]),
        place_largeur_m=float(st["place_largeur_m"]),
        allee_largeur_m=float(st["allee_largeur_m"]),
        acces_largeur_m=float(st["acces_largeur_m"]),
        source=raw,
    )
