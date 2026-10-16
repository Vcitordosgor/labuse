"""Règles PLU de la zone, avec le VERROU de validation.

Une règle n'est utilisable pour un contrôle « Réussi » que si elle est `validee` (statut
« valide » au règlement) ET porte une citation. Toute règle absente ou `propose` reste non
validée → le contrôle correspondant sera « Non effectué », jamais « Réussi ».

Généralisé (IMPLANTATION-1BIS) pour servir plusieurs communes sans réglage par terrain :
barème stationnement scalaire (par_logement validé) ou par typologie (pièces OU surface de
plancher) ; mixité à seuil en m² OU en logements ; emprise / pleine terre optionnelles ;
hauteur à l'égout sinon au faîtage.
"""
from __future__ import annotations

import math
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
        return f"{tete} — « {self.citation} »" if self.citation else (tete or None)


@dataclass(frozen=True)
class LigneBareme:
    places: float
    pieces_min: Optional[int] = None
    pieces_max: Optional[int] = None
    sdp_min: Optional[float] = None
    sdp_max: Optional[float] = None
    destination: str = "collectif"
    libelle: str = ""


@dataclass(frozen=True)
class BaremeStationnement:
    validee: bool
    mode: str                 # 'par_logement' | 'par_typologie' | 'absent'
    base: Optional[str]       # 'pieces' | 'surface_plancher' | None
    arrondi: str              # 'inferieur' | 'superieur'
    flat_places: Optional[float]
    lignes: tuple[LigneBareme, ...]
    article: Optional[str]
    page_pdf: Optional[int]
    citation: Optional[str]

    def places_pour(self, *, pieces: int, sdp_m2: float, destination: str = "collectif") -> Optional[float]:
        if not self.validee:
            return None
        if self.mode == "par_logement":
            return self.flat_places
        for l in self.lignes:
            if l.destination != destination:
                continue
            if l.pieces_min is not None and pieces < l.pieces_min:
                continue
            if l.pieces_max is not None and pieces > l.pieces_max:
                continue
            if l.sdp_min is not None and sdp_m2 < l.sdp_min:
                continue
            if l.sdp_max is not None and sdp_m2 >= l.sdp_max:
                continue
            return l.places
        return None

    def arrondir(self, total: float) -> int:
        return int(math.floor(total + 1e-9)) if self.arrondi == "inferieur" else int(math.ceil(total - 1e-9))

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
        return f"{t} — « {self.citation} »" if self.citation else (t or None)


@dataclass(frozen=True)
class Mixite:
    validee: bool
    seuil_m2: Optional[float]
    seuil_logements: Optional[int]
    quota_pct: Optional[float]
    article: Optional[str]
    page_pdf: Optional[int]
    citation: Optional[str]

    @property
    def citation_complete(self) -> Optional[str]:
        if not self.validee:
            return None
        t = []
        if self.article:
            t.append(f"PLU art. {self.article}")
        if self.page_pdf is not None:
            t.append(f"p. {self.page_pdf}")
        tete = " · ".join(t)
        return f"{tete} — « {self.citation} »" if self.citation else (tete or None)


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
    mixite: Mixite
    stationnement: BaremeStationnement
    prospect: Optional[Regle] = None   # règle de hauteur RELATIVE non chiffrable (ex. L ≥ h/2)

    @property
    def hauteur_plafond(self) -> Regle:
        """La hauteur qui borne les niveaux : l'égout si validé, sinon le faîtage."""
        if self.hauteur_egout.validee:
            return self.hauteur_egout
        return self.hauteur_faitage

    @property
    def hauteur_non_chiffrable(self) -> bool:
        """Vrai s'il existe une règle de hauteur que le moteur ne sait pas chiffrer (prospect L>H).
        Règle générale : une telle règle ne laisse jamais l'étude exploitable."""
        return self.prospect is not None


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
        article=leaf.get("article"), page_pdf=leaf.get("page_pdf"), citation=leaf.get("citation"),
    )


def _bareme(stat: dict) -> BaremeStationnement:
    pl = stat.get("par_logement") or {}
    pt = stat.get("par_typologie") or {}
    # 1) par_logement scalaire validé
    if pl.get("statut") == "valide" and isinstance(pl.get("places"), (int, float)):
        return BaremeStationnement(
            validee=True, mode="par_logement", base=None, arrondi="superieur",
            flat_places=float(pl["places"]), lignes=(),
            article=pl.get("article"), page_pdf=pl.get("page_pdf"), citation=pl.get("citation"))
    # 2) par_typologie validé (pièces OU surface de plancher)
    if pt.get("statut") == "valide" and pt.get("detail"):
        lignes = []
        for d in pt["detail"]:
            if not isinstance(d, dict) or d.get("places") is None:
                continue
            lignes.append(LigneBareme(
                places=float(d["places"]),
                pieces_min=d.get("pieces_min"), pieces_max=d.get("pieces_max"),
                sdp_min=d.get("sdp_min"), sdp_max=d.get("sdp_max"),
                destination=d.get("destination") or "collectif", libelle=d.get("tranche") or d.get("typologie") or ""))
        if lignes:
            return BaremeStationnement(
                validee=True, mode="par_typologie", base=pt.get("base") or "pieces",
                arrondi=pt.get("arrondi") or "superieur", flat_places=None, lignes=tuple(lignes),
                article=pt.get("article"), page_pdf=pt.get("page_pdf"), citation=pt.get("citation"))
    return BaremeStationnement(False, "absent", None, "superieur", None, (), None, None, None)


def _detect_prospect(reg: dict) -> Optional[Regle]:
    """Prospect / hauteur relative (ex. « L ≥ h/2 ») : règle liant distance et HAUTEUR, que le
    moteur ne sait pas chiffrer. Détectée dans les formules/citations de reculs ou de hauteur."""
    marqueurs = ("h/2", "h / 2", "différence d'altitude", "l ≥ h", "l > h", "l>h", "≥ h/")
    for grp in ("retraits", "hauteur"):
        for leaf in (reg.get(grp) or {}).values():
            if not isinstance(leaf, dict):
                continue
            txt = " ".join(str(leaf.get(f) or "") for f in ("formule", "citation")).lower()
            if any(m in txt for m in marqueurs):
                return Regle(nom="prospect (hauteur relative)", valeur=None, unite="", validee=False,
                             article=leaf.get("article"), page_pdf=leaf.get("page_pdf"),
                             citation=leaf.get("citation") or leaf.get("formule"))
    return None


def charger(insee: str, zone: str) -> ReglesZone:
    from labuse.plu.destinations import regles_zone

    reg = regles_zone(insee, zone) or {}
    hauteur = reg.get("hauteur") or {}
    emprise = reg.get("emprise_sol") or {}
    retraits = reg.get("retraits") or {}
    pleine = reg.get("pleine_terre") or {}
    mix = reg.get("mixite") or {}

    mix_valide = mix.get("statut") == "valide"
    mixite = Mixite(
        validee=bool(mix_valide and mix.get("quota_pct") is not None),
        seuil_m2=mix.get("seuil_m2") if mix_valide else None,
        seuil_logements=mix.get("seuil_logements") if mix_valide else None,
        quota_pct=float(mix["quota_pct"]) if (mix_valide and mix.get("quota_pct") is not None) else None,
        article=mix.get("article"), page_pdf=mix.get("page_pdf"), citation=mix.get("citation"))

    return ReglesZone(
        insee=insee, zone=zone,
        hauteur_egout=_leaf_val(hauteur.get("egout"), "m", "hauteur à l'égout", "m"),
        hauteur_faitage=_leaf_val(hauteur.get("faitage"), "m", "hauteur au faîtage", "m"),
        emprise_ces=_leaf_val(emprise.get("ces"), "pct", "emprise au sol (CES)", "%"),
        recul_voie=_leaf_val(retraits.get("voie"), "min_m", "recul sur voie", "m"),
        recul_separatives=_leaf_val(retraits.get("limites_separatives"), "min_m",
                                    "recul sur limites séparatives", "m"),
        pleine_terre=_leaf_val(pleine.get("pct"), "pct", "pleine terre (perméabilité)", "%"),
        mixite=mixite,
        stationnement=_bareme(reg.get("stationnement") or {}),
        prospect=_detect_prospect(reg),
    )
