"""Règles PLU de la zone, avec le VERROU de validation.

Une règle n'est utilisable pour un contrôle « Réussi » que si elle est `validee` (statut
« valide » au règlement) ET porte une citation. Toute règle absente ou `propose` reste non
validée → le contrôle correspondant sera « Non effectué », jamais « Réussi ».

Lecture depuis le fichier PLU de la commune via `labuse.plu.destinations.regles_zone`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class Regle:
    nom: str
    valeur: Optional[float]
    unite: str
    validee: bool
    article: Optional[str] = None
    page_pdf: Optional[int] = None
    citation: Optional[str] = None

    @property
    def citation_complete(self) -> Optional[str]:
        if not self.validee:
            return None
        bout = []
        if self.article:
            bout.append(f"PLU art. {self.article}")
        if self.page_pdf is not None:
            bout.append(f"p. {self.page_pdf}")
        tete = " · ".join(bout)
        return f"{tete} — « {self.citation} »" if self.citation else tete or None


@dataclass(frozen=True)
class BaremeStationnement:
    validee: bool
    article: Optional[str]
    page_pdf: Optional[int]
    citation: Optional[str]
    # liste de (pieces_min, pieces_max|None, places, destination, libelle)
    lignes: tuple[tuple[Optional[int], Optional[int], float, str, str], ...]

    def places_pour(self, pieces: int, destination: str = "collectif") -> Optional[float]:
        """Minimum de places imposé pour un logement de `pieces` pièces. Déterministe."""
        if not self.validee:
            return None
        for pmin, pmax, places, dest, _lib in self.lignes:
            if dest != destination:
                continue
            if pmin is not None and pieces < pmin:
                continue
            if pmax is not None and pieces > pmax:
                continue
            return places
        return None

    @property
    def citation_complete(self) -> Optional[str]:
        if not self.validee:
            return None
        tete = []
        if self.article:
            tete.append(f"PLU art. {self.article}")
        if self.page_pdf is not None:
            tete.append(f"p. {self.page_pdf}")
        t = " · ".join(tete)
        return f"{t} — « {self.citation} »" if self.citation else t or None


@dataclass(frozen=True)
class ReglesZone:
    insee: str
    zone: str
    hauteur_egout: Regle
    hauteur_faitage: Regle
    emprise_ces: Regle
    recul_voie: Regle
    recul_separatives: Regle
    pleine_terre: Regle
    mixite_seuil_m2: Optional[float]
    mixite_quota_pct: Optional[float]
    mixite: Regle
    stationnement: BaremeStationnement
    source_doc: dict[str, Any]


def _leaf_val(leaf: Optional[dict], key: str, nom: str, unite: str) -> Regle:
    if not isinstance(leaf, dict):
        return Regle(nom=nom, valeur=None, unite=unite, validee=False)
    valide = leaf.get("statut") == "valide" and not leaf.get("absent")
    v = leaf.get(key)
    return Regle(
        nom=nom,
        valeur=float(v) if (valide and isinstance(v, (int, float))) else None,
        unite=unite,
        validee=bool(valide and isinstance(v, (int, float))),
        article=leaf.get("article"),
        page_pdf=leaf.get("page_pdf"),
        citation=leaf.get("citation"),
    )


def charger(insee: str, zone: str) -> ReglesZone:
    from labuse.plu.destinations import regles_zone

    reg = regles_zone(insee, zone) or {}
    hauteur = reg.get("hauteur") or {}
    emprise = reg.get("emprise_sol") or {}
    retraits = reg.get("retraits") or {}
    pleine = reg.get("pleine_terre") or {}
    stat = reg.get("stationnement") or {}
    mix = reg.get("mixite") or {}

    # stationnement : barème par typologie (feuille validée)
    pt = stat.get("par_typologie") or {}
    pt_valide = pt.get("statut") == "valide"
    lignes = []
    for d in (pt.get("detail") or []):
        if not isinstance(d, dict) or d.get("places") is None:
            continue
        lignes.append((
            d.get("pieces_min"), d.get("pieces_max"), float(d["places"]),
            d.get("destination") or "collectif", d.get("typologie") or "",
        ))
    bareme = BaremeStationnement(
        validee=bool(pt_valide and lignes),
        article=pt.get("article"), page_pdf=pt.get("page_pdf"), citation=pt.get("citation"),
        lignes=tuple(lignes),
    )

    # mixité : validée si statut valide ; seuil + quota numériques
    mix_valide = mix.get("statut") == "valide"
    seuil = mix.get("seuil_m2") if mix_valide else None
    quota = mix.get("quota_pct") if mix_valide else None
    regle_mix = Regle(
        nom="mixité sociale",
        valeur=float(quota) if (mix_valide and isinstance(quota, (int, float))) else None,
        unite="%", validee=bool(mix_valide and quota is not None),
        article=mix.get("article"), page_pdf=mix.get("page_pdf"), citation=mix.get("citation"),
    )

    return ReglesZone(
        insee=insee, zone=zone,
        hauteur_egout=_leaf_val(hauteur.get("egout"), "m", "hauteur à l'égout", "m"),
        hauteur_faitage=_leaf_val(hauteur.get("faitage"), "m", "hauteur au faîtage", "m"),
        emprise_ces=_leaf_val(emprise.get("ces"), "pct", "emprise au sol (CES)", "%"),
        recul_voie=_leaf_val(retraits.get("voie"), "min_m", "recul sur voie", "m"),
        recul_separatives=_leaf_val(retraits.get("limites_separatives"), "min_m",
                                    "recul sur limites séparatives", "m"),
        pleine_terre=_leaf_val(pleine.get("pct"), "pct", "pleine terre (perméabilité)", "%"),
        mixite_seuil_m2=float(seuil) if isinstance(seuil, (int, float)) else None,
        mixite_quota_pct=float(quota) if isinstance(quota, (int, float)) else None,
        mixite=regle_mix,
        stationnement=bareme,
        source_doc={},
    )
