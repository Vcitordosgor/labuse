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
    surface_noyau_m2: float        # PLU-CALIBRAGE-10 pt 3 : surface USUELLE d'un noyau (escalier +
                                   # ascenseur + palier) par niveau et par bâtiment, Estimé.
    max_logements_par_noyau: int
    longueur_max_coursive_par_noyau_m: float
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
    # ETUDE-V6-2 (Lot 3) — surface USUELLE d'une place EN SOUS-SOL, rampes et circulation comprises
    # (Estimé) : sert à chiffrer l'emprise du parking enterré et à la confronter à l'emprise réglementaire.
    m2_par_place_sous_sol: float
    source: dict[str, Any]

    def largeur_module(self, type_logement: str) -> float:
        """Largeur d'un module = surface_m2 / (profondeur - coursive). Déterministe, de la géométrie."""
        m = self.modules[type_logement]
        return m.surface_m2 / (self.profondeur_m - self.largeur_coursive_m)

    def profondeur_logement_m(self) -> float:
        return self.profondeur_m - self.largeur_coursive_m

    def largeur_noyau_m(self) -> float:
        """Largeur de la tranche de noyau, DÉRIVÉE de sa surface usuelle : la tranche traverse la
        profondeur habitable (comme un module), donc largeur = surface_noyau / profondeur habitable.
        Le noyau garde ainsi une SURFACE usuelle (≈ escalier + ascenseur + palier), au lieu d'occuper
        toute la tranche à pleine largeur."""
        return self.surface_noyau_m2 / self.profondeur_logement_m()


def avec_surcharges(conv: Conventions, *, profondeur_m: float | None = None,
                    coef_plancher_habitable: float | None = None,
                    surfaces: dict[str, float] | None = None) -> Conventions:
    """Conventions avec HYPOTHÈSES surchargées (profondeur, plancher→habitable, surface moyenne par
    type). Les bornes gardent la géométrie saine ; ces valeurs restent « Estimé » et ne peuvent
    jamais rendre un contrôle réglementaire « Réussi ». `source` est mis à jour pour transparence."""
    import copy
    from dataclasses import replace

    prof = conv.profondeur_m if profondeur_m is None else max(8.0, min(20.0, float(profondeur_m)))
    coef = (conv.coef_plancher_habitable if coef_plancher_habitable is None
            else max(0.5, min(1.0, float(coef_plancher_habitable))))
    mods = dict(conv.modules)
    if surfaces:
        for t, s in surfaces.items():
            if t in mods and s:
                mods[t] = replace(mods[t], surface_m2=max(20.0, min(160.0, float(s))))

    src = copy.deepcopy(conv.source)
    src.setdefault("batiment", {})["profondeur_m"] = prof
    src["batiment"]["coef_plancher_habitable"] = coef
    for t, m in mods.items():
        src.setdefault("modules", {}).setdefault(t, {})["surface_m2"] = m.surface_m2

    return replace(conv, profondeur_m=prof, coef_plancher_habitable=coef, modules=mods, source=src)


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
        surface_noyau_m2=float(bat["surface_noyau_m2"]),
        max_logements_par_noyau=int(bat["max_logements_par_noyau"]),
        longueur_max_coursive_par_noyau_m=float(bat["longueur_max_coursive_par_noyau_m"]),
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
        m2_par_place_sous_sol=float(st.get("m2_par_place_sous_sol", 25.0)),
        source=raw,
    )
