"""Chargement du catalogue des postes du bilan (``declarations/bilan/postes.yaml``).

Le catalogue est la liste figée des 45 postes de charges du modèle de la
promotrice, dans ses 4 blocs et dans son ordre, plus la définition du programme
(une ligne par produit) et les taux de TVA légaux. Il ne contient AUCUNE valeur
chiffrée du bilan : seulement libellés, assiettes, modes, TVA et repère possible.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import yaml

# repo_root/src/labuse/bilan/catalogue.py -> parents[3] == repo_root
_RACINE = pathlib.Path(__file__).resolve().parents[3]
_POSTES_YAML = _RACINE / "declarations" / "bilan" / "postes.yaml"


@dataclass(frozen=True)
class Repere:
    """Un repère LABUSE proposé sur un poste (jamais appliqué d'office)."""

    kind: str  # "registre" (source publique, id) | "ratio_place" (ratio de place)
    registre_id: str | None = None  # id de la source publique à résoudre
    valeur: float | None = None  # valeur proposée pour un ratio de place


@dataclass(frozen=True)
class Poste:
    id: str
    libelle: str
    libelle_modele: str
    ligne_modele: int
    bloc: str
    mode: str  # "pct" | "unit" | "forfait"
    base: str = "ht"  # "ht" (taux sur HT, TVA en sus) | "ttc" (taux sur TTC, HT déduit)
    assiette: str | None = None
    unite: str | None = None
    tva: Any = None  # float (taux) | "a_saisir" | "selon_produit"
    tva_sourcee: bool = False
    repere: Repere | None = None
    alea: bool = False
    besoin_assiette: bool = False
    sub: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class Bloc:
    id: str
    titre: str
    titre_modele: str
    postes: tuple[Poste, ...]


@dataclass(frozen=True)
class Catalogue:
    version: int
    tva_legales: dict[str, float]
    assiettes: dict[str, str]
    produit_modele: dict[str, Any]
    programme: tuple[dict[str, Any], ...]
    calendrier: tuple[dict[str, Any], ...]
    blocs: tuple[Bloc, ...]

    def postes(self) -> list[Poste]:
        """Tous les postes de charges, à plat, dans l'ordre du modèle."""
        return [p for b in self.blocs for p in b.postes]

    def poste(self, pid: str) -> Poste:
        for p in self.postes():
            if p.id == pid:
                return p
        raise KeyError(pid)


# Unité « de nature » d'une assiette (BILAN-2, retour Vic) : une assiette s'affiche
# avec l'unité de ce qu'elle MESURE (m² de surface, nombre de lots, € de montant),
# jamais en € par défaut. Partagé par l'écran (via le front), le PDF et l'Excel.
_ASSIETTE_M2 = {"terrain", "surface_taxable", "suv"}
_ASSIETTE_LOTS = {"lots"}


def assiette_unite(assiette: str | None) -> str | None:
    """'m²' | 'lots' | '€' selon la nature de l'assiette ; None pour un forfait
    (pas d'assiette). Tout le reste (prix, CA, construction, loyers annuels…) est en €."""
    if assiette in _ASSIETTE_M2:
        return "m²"
    if assiette in _ASSIETTE_LOTS:
        return "lots"
    if assiette in (None, "forfait"):
        return None
    return "€"


def _repere(val: Any) -> Repere | None:
    if val is None:
        return None
    if isinstance(val, str):
        return Repere(kind="registre", registre_id=val)
    if isinstance(val, dict):
        return Repere(kind="ratio_place", valeur=float(val["valeur"]))
    raise ValueError(f"repère invalide : {val!r}")


def _poste(bloc_id: str, d: dict[str, Any]) -> Poste:
    return Poste(
        id=d["id"],
        libelle=d["libelle"],
        libelle_modele=d["libelle_modele"],
        ligne_modele=int(d["ligne_modele"]),
        bloc=bloc_id,
        mode=d["mode"],
        base=d.get("base", "ht"),
        assiette=d.get("assiette"),
        unite=d.get("unite"),
        tva=d.get("tva"),
        tva_sourcee=bool(d.get("tva_sourcee", False)),
        repere=_repere(d.get("repere")),
        alea=bool(d.get("alea", False)),
        besoin_assiette=bool(d.get("besoin_assiette", False)),
        sub=d.get("sub"),
        note=d.get("note"),
    )


@lru_cache(maxsize=1)
def charger_catalogue(chemin: str | None = None) -> Catalogue:
    p = pathlib.Path(chemin) if chemin else _POSTES_YAML
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    blocs = tuple(
        Bloc(
            id=b["id"],
            titre=b["titre"],
            titre_modele=b["titre_modele"],
            postes=tuple(_poste(b["id"], d) for d in b["postes"]),
        )
        for b in data["blocs"]
    )
    return Catalogue(
        version=int(data["version"]),
        tva_legales=dict(data["tva_legales"]),
        assiettes=dict(data["assiettes"]),
        produit_modele=dict(data["produit_modele"]),
        programme=tuple(data["programme"]),
        calendrier=tuple(data.get("calendrier", ())),
        blocs=blocs,
    )
