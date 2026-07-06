"""Couches PHASE 1 — géométriques, locales, PostGIS, sur TOUTES les parcelles.

Le moins cher / le plus décisif d'abord (brief §2). Chaque couche lit ses params
dans config/cascade_rules.yaml et rend 0..n Verdicts avec un motif humain.

Convention UNKNOWN vs PASS : si la donnée n'est pas ingérée pour la commune
(ctx.kind_present == False) → UNKNOWN (impacte la complétude). Si la donnée est
présente mais que la parcelle n'est pas contrainte → PASS.
"""
from __future__ import annotations

import re
from typing import Any

from ...enums import Severity
from ..base import Layer, Verdict, hard_exclude, passed, positive, register, scored, soft_flag, unknown
from ..context import EvalContext, ParcelRef

# Noms canoniques des sources (doivent matcher le catalogue data_sources, §6).
SRC_BDTOPO = "BD TOPO IGN"
SRC_PARC = "Parc National de La Réunion (INPN)"
SRC_FORET = "Forêts publiques (ONF)"
SRC_SAR = "SAR Réunion (PEIGEO)"
SRC_GPU = "Urbanisme PLU/GPU (API Carto)"
SRC_SAFER = "Zonage SAFER (DAAF)"
SRC_GEORISQUES = "Géorisques"
SRC_TRAIT = "DEAL Réunion — trait de côte"
SRC_ALTI = "RGE ALTI (altimétrie)"
SRC_ABF = "ABF / Monuments historiques"
SRC_ENS = "ENS (Département)"
SRC_OCSGE = "OCS GE (IGN)"
SRC_OSM = "OpenStreetMap / Overpass"
SRC_DGFIP = "Parcellaire propriétaires PM (DGFiP)"
SRC_CADASTRE = "Géométrie parcellaire (cadastre)"


def _dominant(intersections) -> Any | None:
    """Entité couvrant la plus grande part de la parcelle."""
    return max(intersections, key=lambda i: i.coverage, default=None)


_OSM_LABEL = {"parking": "parking", "pitch": "terrain de sport", "sport": "terrain de sport",
              "cemetery": "cimetière", "school": "école"}


def _osm_label(subtype: str | None) -> str:
    return _OSM_LABEL.get((subtype or "").lower(), subtype or "équipement")


_ER_RE = re.compile(r"^ER\s*(\S+)\s*[-–—:]\s*(.+)$", re.IGNORECASE)


def _er_split(libelle: str) -> tuple[str | None, str]:
    """« ER 81 - Aménagement… » → ('81', 'Aménagement…') ; sinon (None, libellé entier)."""
    m = _ER_RE.match((libelle or "").strip())
    return (m.group(1), m.group(2).strip()) if m else (None, (libelle or "").strip())


@register
class EauLayer(Layer):
    name = "eau"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        inter = ctx.intersections(parcel.id, params["spatial_kind"])
        on_centroid = ctx.centroid_in(parcel.id, params["spatial_kind"])
        majority = max((i.coverage for i in inter), default=0.0)
        if on_centroid or majority >= params.get("majority_threshold", 0.5):
            return hard_exclude(self.name, params["detail_exclude"], kind="exclue", source=SRC_BDTOPO)
        if majority > 0:
            return soft_flag(
                self.name,
                f"Traversée/bordée par de l'eau (~{majority*100:.0f}% de surface).",
                Severity.MOYEN,
                source=SRC_BDTOPO,
            )
        return passed(self.name, "Hors hydrographie.", source=SRC_BDTOPO)


@register
class ParcNationalLayer(Layer):
    name = "parc_national"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Couche Parc National non ingérée.", source=SRC_PARC)
        inter = ctx.intersections(parcel.id, kind)
        coeur = params.get("coeur_subtype", "coeur")
        adhesion = params.get("adhesion_subtype", "adhesion")
        if any(i.subtype == coeur and i.coverage > 0 for i in inter):
            return hard_exclude(
                self.name,
                "Exclue : intersecte le cœur du Parc National (UNESCO « Pitons, cirques et remparts »).",
                kind="exclue",
                source=SRC_PARC,
            )
        if any(i.subtype == adhesion for i in inter):
            sev = Severity(params.get("adhesion_severity", "moyen"))
            return soft_flag(
                self.name,
                "Aire d'adhésion du Parc National — contraintes de charte.",
                sev,
                source=SRC_PARC,
            )
        return passed(self.name, "Hors Parc National.", source=SRC_PARC)


@register
class ForetPubliqueLayer(Layer):
    name = "foret_publique"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Couche forêts publiques non ingérée.", source=SRC_FORET)
        inter = ctx.intersections(parcel.id, kind)
        dom = _dominant(inter)
        if dom is None or dom.coverage <= 0:
            return passed(self.name, "Hors forêt publique.", source=SRC_FORET)
        is_domaniale = dom.subtype == params.get("domaniale_subtype", "domaniale")
        if is_domaniale and params.get("mode_default", "hard_exclude") == "hard_exclude":
            return hard_exclude(
                self.name, "Exclue : forêt domaniale (domaine public — terrain inacquérable).", kind="exclue", source=SRC_FORET
            )
        return soft_flag(
            self.name, f"Forêt publique ({dom.subtype or 'non précisée'}).", Severity.FORT, source=SRC_FORET
        )


@register
class SarLayer(Layer):
    """SAR — DÉCISION 2 (directive post-1.A) : la seule donnée disponible est un PROXY de
    vocation (potentiel foncier Région), pas le SAR réglementaire → couche INFORMATIVE,
    badge « SAR (proxy indicatif) ». ZÉRO pouvoir d'exclusion : ne produit plus jamais de
    HARD_EXCLUDE ni de SOFT_FLAG (la donnée est conservée et affichée).

    Émet un WARNING de divergence (PASS « ⚠ … », sans effet score/statut) quand le proxy
    « naturel/agricole » contredit un zonage PLU U/AU — sur zone AU, c'est une info de
    risque réelle (ouverture à l'urbanisation moins probable), remontée en vigilance."""

    name = "sar"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Zonage SAR non ingéré.", source=SRC_SAR)
        inter = ctx.intersections(parcel.id, kind)
        dom = _dominant(inter)
        if dom is None or dom.coverage <= 0:
            # Couverture SAR partielle (proxy de vocation) : « hors îlot » N'équivaut PAS à
            # « aucune contrainte SAR ». On ne conclut pas à la compatibilité.
            return passed(self.name,
                          "SAR : hors îlot cartographié — aucune contrainte SAR déduite automatiquement.",
                          source=SRC_SAR)
        lib = (dom.attrs or {}).get("libelle") or dom.subtype
        pct = f" (~{dom.coverage * 100:.0f}% de la parcelle)" if dom.coverage < 0.99 else ""
        if dom.subtype in set(params.get("divergent_subtypes", [])):
            zone = self._zone_uau(parcel, ctx, params)
            if zone:
                au = zone.upper().startswith("AU")
                return passed(
                    self.name,
                    "⚠ proxy SAR divergent du PLU — vigilance en cas de révision : "
                    f"SAR (proxy indicatif) « {lib} »{pct} sur zone PLU « {zone} »"
                    + (" — zone AU : ouverture à l'urbanisation moins probable." if au else "."),
                    source=SRC_SAR,
                )
            return passed(
                self.name,
                f"SAR (proxy indicatif) : « {lib} »{pct} — information de vocation, sans effet sur "
                "le score (proxy : ne vaut ni interdiction ni constructibilité).",
                source=SRC_SAR,
            )
        if dom.subtype in set(params.get("info_subtypes", [])):
            return passed(
                self.name,
                f"SAR (proxy indicatif) : « {lib} »{pct} — vocation sans a priori constructif (information).",
                source=SRC_SAR,
            )
        return passed(self.name,
                      f"SAR : vocation compatible détectée — {lib or 'territoire urbain'} — à croiser avec PLU/PPR.",
                      source=SRC_SAR)

    @staticmethod
    def _zone_uau(parcel: ParcelRef, ctx: EvalContext, params: dict) -> str | None:
        """Libellé de la zone PLU dominante si U/AU (sinon None — pas de divergence à signaler :
        un proxy « naturel » sur une zone N est cohérent, le zonage PLU fait déjà foi)."""
        plu_kind = params.get("plu_kind", "plu_gpu_zone")
        if not ctx.kind_present(plu_kind):
            return None
        dom = _dominant(ctx.intersections(parcel.id, plu_kind))
        if dom is None or dom.coverage <= 0:
            return None
        zone = (dom.subtype or "").strip()
        prefixes = tuple(params.get("uau_prefixes", ["U", "AU"]))
        return zone if any(zone.upper().startswith(p) for p in prefixes) else None


@register
class ZonagePluGpuLayer(Layer):
    """Zonage PLU — DÉCISION 1 (directive post-1.A) : exclusion A/N SENSIBLE AU RECOUVREMENT.

    - part A+N ≥ `an_hard_exclude_pct` (PLACEHOLDER 90 %) → HARD_EXCLUDE ;
    - zonage mixte (part A/N ≥ `an_mixte_min_pct` + part U/AU) → SOFT_FLAG « zonage mixte »
      + bonus U/AU réduit à la part U/AU ; l'emprise constructible est clippée à la portion
      U/AU dans la pré-faisabilité (faisabilite/db.py) ;
    - liséré A/N < `an_mixte_min_pct` (artefact géométrique GPU) → ignoré.
    STECAL : pas de traitement v1 (exception future via plu_saint_paul.yaml)."""

    name = "zonage_plu_gpu"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> list[Verdict]:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return [unknown(
                self.name,
                "Zonage PLU/GPU indisponible (document non dématérialisé sur le GPU ? → fallback import).",
                source=SRC_GPU,
            )]
        inter = [i for i in ctx.intersections(parcel.id, kind) if i.coverage > 0]
        if not inter:
            return [passed(self.name, "Hors zonage PLU connu.", source=SRC_GPU)]
        for i in inter:
            lib = (i.subtype or "").strip()
            if lib in set(params.get("exclude_zones", [])):
                return [hard_exclude(
                    self.name, f"Exclue : zone PLU « {lib} » strictement inconstructible.",
                    kind="faux_positif", source=SRC_GPU,
                )]

        # Constructible (U / AU) testé EN PREMIER : sinon « AUc/AUs » serait happé par le
        # préfixe agricole « A » (AU commence par A). L'ordre des tests fait foi.
        pos_p = tuple(params.get("positive_prefixes", []))
        an_p = tuple(params.get("hard_exclude_prefixes", []))

        def classe(libelle: str) -> str:
            up = libelle.upper()
            if any(up.startswith(p) for p in pos_p):
                return "uau"
            if any(up.startswith(p) for p in an_p):
                return "an"
            return "autre"

        uau = [i for i in inter if classe((i.subtype or "").strip()) == "uau"]
        an = [i for i in inter if classe((i.subtype or "").strip()) == "an"]
        an_cov = min(1.0, sum(i.coverage for i in an))
        uau_cov = min(1.0, sum(i.coverage for i in uau))
        seuil = float(params.get("an_hard_exclude_pct", 90)) / 100.0
        plancher = float(params.get("an_mixte_min_pct", 5)) / 100.0

        if an and an_cov >= seuil:
            lib = (_dominant(an).subtype or "").strip()
            return [hard_exclude(
                self.name,
                f"Zone {lib} PLU — inconstructible (recouvrement {an_cov * 100:.0f} %).",
                kind="faux_positif", source=SRC_GPU,
            )]

        verdicts: list[Verdict] = []
        mixte = bool(an) and an_cov >= plancher and bool(uau)
        if mixte:
            lib_an = (_dominant(an).subtype or "").strip()
            verdicts.append(soft_flag(
                self.name,
                "Zonage mixte — constructibilité limitée à l'emprise U/AU "
                f"(« {lib_an} » inconstructible sur ~{an_cov * 100:.0f} % ; emprise clippée en pré-faisabilité).",
                Severity.MOYEN, source=SRC_GPU,
            ))
        if uau:
            lib = (_dominant(uau).subtype or "").strip()
            mag = uau_cov if mixte else 1.0
            verdicts.append(positive(
                self.name,
                f"Zone PLU « {lib} » (urbaine / à urbaniser — constructible"
                + (f" sur ~{uau_cov * 100:.0f} % de la parcelle" if mixte else "") + ").",
                params.get("positive_bonus_key", "zonage_u_au"),
                magnitude=mag, source=SRC_GPU,
            ))
            return verdicts
        if an:
            # Part A/N sous le seuil SANS part U/AU (bordure de couverture PLU — non observé
            # à Saint-Paul) : prudence sans exclure.
            lib = (_dominant(an).subtype or "").strip()
            return [soft_flag(
                self.name,
                f"Zone {lib} PLU sur ~{an_cov * 100:.0f} % de la parcelle (couverture PLU partielle) "
                "— constructibilité à vérifier.",
                Severity.FORT, source=SRC_GPU,
            )]
        libelle = (_dominant(inter).subtype or "").strip()
        up = libelle.upper()
        if any(up.startswith(p) for p in params.get("flag_fort_prefixes", [])):
            return [soft_flag(self.name, f"Zone PLU « {libelle} » (naturelle).", Severity.FORT, source=SRC_GPU)]
        if any(up.startswith(p) for p in params.get("flag_prefixes", [])):
            return [soft_flag(self.name, f"Zone PLU « {libelle} » (agricole — SAFER).", Severity.MOYEN, source=SRC_GPU)]
        return [passed(self.name, f"Zone PLU « {libelle} ».", source=SRC_GPU)]


@register
class PrescriptionPluLayer(Layer):
    """Prescriptions du PLU (GPU) : emplacement réservé, mixité sociale, EBC, patrimoine bâti,
    OAP, eaux pluviales… De VRAIES servitudes opposables, jusque-là non lues par la cascade.

    DÉCISION 3.a (directive post-1.A) : un ER couvrant ≥ `er_hard_exclude_pct` (PLACEHOLDER
    50 %) de la parcelle EXCLUT (emprise majoritairement grevée) ; en deçà → SOFT_FLAG et la
    surface ER est déduite de l'emprise constructible en pré-faisabilité (faisabilite/db.py).
    Les autres prescriptions n'excluent jamais seules. Le libellé GPU est TOUJOURS affiché ;
    le `typepsc` CNIG ne sert qu'à graduer le traitement (mapping dans cascade_rules.yaml).
    Peut émettre PLUSIEURS verdicts (une parcelle peut cumuler ER + mixité + eaux pluviales)."""

    name = "prescription_plu"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> list[Verdict]:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return [unknown(self.name, "Prescriptions PLU/GPU non ingérées.", source=SRC_GPU)]
        # lin/pct ont une couverture surfacique ~0 mais intersectent réellement (présence).
        inter = [i for i in ctx.intersections(parcel.id, kind)
                 if i.coverage > 0 or (i.attrs or {}).get("geom_kind") in ("lin", "pct")]
        if not inter:
            return [passed(self.name, "Aucune prescription PLU sur la parcelle.", source=SRC_GPU)]

        er = set(params.get("emplacement_reserve_typepsc", []))
        ebc = set(params.get("boise_classe_typepsc", []))
        mixite = set(params.get("mixite_sociale_typepsc", []))
        patrimoine = set(params.get("patrimoine_bati_typepsc", []))
        oap = set(params.get("oap_typepsc", []))
        eaux = set(params.get("eaux_pluviales_typepsc", []))
        er_seuil = float(params.get("er_hard_exclude_pct", 50)) / 100.0

        verdicts: list[Verdict] = []
        seen: set[tuple[str | None, str]] = set()
        for i in inter:
            tp = (i.subtype or "").strip()
            lib = ((i.attrs or {}).get("libelle") or i.name or "prescription PLU").strip()
            if (tp, lib) in seen:
                continue
            seen.add((tp, lib))
            pct = f" (~{i.coverage * 100:.0f}% de la parcelle)" if i.coverage >= 0.01 else ""
            # Contraintes DISCRIMINANTES (spécifiques à la parcelle).
            if tp in er:
                num, objet = _er_split(lib)
                if i.coverage >= er_seuil:
                    titre = f"Emplacement réservé {num}" if num else "Emplacement réservé"
                    verdicts.append(hard_exclude(
                        self.name,
                        f"{titre} : {objet} ({i.coverage * 100:.0f} %) — emprise majoritairement "
                        "grevée au profit d'un projet public (servitude levable : à réévaluer si "
                        "l'ER est abandonné).",
                        kind="faux_positif", source=SRC_GPU))
                else:
                    verdicts.append(soft_flag(
                        self.name, f"Emplacement réservé : {lib}{pct} — emprise grevée au profit "
                        "d'un projet public ; surface ER déduite de l'emprise constructible "
                        "(pré-faisabilité).", Severity.MOYEN, source=SRC_GPU))
            elif tp in ebc:
                verdicts.append(soft_flag(
                    self.name, f"Espace boisé classé (EBC) : {lib}{pct} — toute construction interdite "
                    "sur l'emprise boisée (Art. L113-1 CU).", Severity.FORT, source=SRC_GPU))
            elif tp in patrimoine:
                verdicts.append(soft_flag(
                    self.name, f"Élément bâti protégé (Art. L151-19 CU) : {lib} — démolition/modification "
                    "encadrée (frein à la restructuration).", Severity.MOYEN, source=SRC_GPU))
            # Contraintes de PROGRAMME / quasi communales (mixité 92 %, eaux pluviales 96 %, OAP) :
            # RÉELLES mais NON discriminantes → PASS informatif (recensé, tracé, AUCUNE pénalité,
            # pas de bruit dans la vigilance). L'impact mixité est porté par le bilan, pas le score.
            elif tp in mixite:
                verdicts.append(passed(
                    self.name, f"Secteur de mixité sociale : {lib} — quota de logements aidés imposé "
                    "(impacte le bilan, pas la constructibilité).", source=SRC_GPU))
            elif tp in oap:
                verdicts.append(passed(
                    self.name, f"Orientation d'aménagement (OAP) : {lib} — secteur de projet encadré "
                    "(principes d'aménagement à respecter).", source=SRC_GPU))
            elif tp in eaux:
                verdicts.append(passed(
                    self.name, f"Zonage des eaux pluviales : {lib} — rétention/infiltration imposée "
                    "(impacte la conception, pas la constructibilité).", source=SRC_GPU))
            else:
                verdicts.append(soft_flag(
                    self.name, f"Prescription PLU : {lib}{pct} — à vérifier au règlement.",
                    Severity.FAIBLE, source=SRC_GPU))
        return verdicts


@register
class SaferLayer(Layer):
    name = "safer"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Zonage SAFER (DAAF) non ingéré.", source=SRC_SAFER)
        inter = ctx.intersections(parcel.id, kind)
        if any(i.coverage > 0 for i in inter):
            return soft_flag(self.name, params["detail"], Severity(params.get("severity", "moyen")), source=SRC_SAFER)
        return passed(self.name, "Hors zonage SAFER.", source=SRC_SAFER)


@register
class RisquesLayer(Layer):
    """Géorisques + PPR. Peut émettre PLUSIEURS verdicts (PPR + aléas)."""

    name = "risques"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> list[Verdict]:
        kind_ppr = params["spatial_kind_ppr"]
        kind_alea = params["spatial_kind_alea"]
        if not ctx.kind_present(kind_ppr) and not ctx.kind_present(kind_alea):
            return [unknown(self.name, "Risques Géorisques/PPR non ingérés.", source=SRC_GEORISQUES)]

        verdicts: list[Verdict] = []
        red = set(params.get("ppr_red_subtypes", []))
        for i in ctx.intersections(parcel.id, kind_ppr):
            if i.coverage <= 0:
                continue
            if i.subtype in red:
                verdicts.append(
                    hard_exclude(self.name, "Exclue : PPR zone rouge (inconstructible).", kind="exclue", source=SRC_GPU)
                )
            else:
                # Assiette PPR (servitude PM1) : on connaît le PÉRIMÈTRE réglementaire, pas le
                # zonage rouge/bleue interne → flag fort PRUDENT, jamais une exclusion automatique.
                risque = (i.attrs or {}).get("risque") or "risque naturel"
                cov_pct = i.coverage * 100
                pct = f" (~{cov_pct:.0f}% de la parcelle)" if i.coverage < 0.99 else ""
                # Étape A (quick-win PPR v2) : une intersection MARGINALE du périmètre PM1 (couverture
                # < min_coverage_pct) ne suffit pas à présumer une contrainte forte — on ignore si la
                # parcelle est en rouge ou bleu, et un bord rogné est rarement la zone critique → note
                # INFORMATIVE faible (jamais un flag fort bloquant). Le rouge/bleu réglementaire reste
                # géré séparément (Étape B) ; le seuil de scoring n'est pas modifié.
                min_cov = float(params.get("min_coverage_pct", 0))
                if cov_pct < min_cov:
                    verdicts.append(soft_flag(
                        self.name,
                        f"Périmètre PPR {risque}{pct} — intersection marginale (< {min_cov:.0f} %) : "
                        "à vérifier au règlement, sans présomption de contrainte forte.",
                        Severity.FAIBLE, source=SRC_GPU))
                else:
                    verdicts.append(soft_flag(
                        self.name,
                        f"Périmètre PPR {risque}{pct} — servitude réglementaire approuvée ; prescriptions "
                        "applicables, zonage rouge/bleue à vérifier au règlement (constructibilité non garantie).",
                        Severity.FORT, source=SRC_GPU))

        sev_map = params.get("alea_severity_map", {})
        for i in ctx.intersections(parcel.id, kind_alea):
            if i.coverage <= 0:
                continue
            niveau = (i.attrs or {}).get("niveau", "moyen")
            sev = Severity(sev_map.get(niveau, niveau if niveau in ("faible", "moyen", "fort") else "moyen"))
            alea_type = (i.attrs or {}).get("type", i.subtype or "aléa")
            verdicts.append(soft_flag(self.name, f"Aléa {alea_type} — niveau {niveau}.", sev, source=SRC_GEORISQUES))

        if not verdicts:
            verdicts.append(passed(self.name, "Aucun risque PPR/aléa intersecté.", source=SRC_GEORISQUES))
        return verdicts


@register
class RavineLayer(Layer):
    """Proximité d'une ravine (BD TOPO, Lot C1). À La Réunion, les ravines sont des thalwegs
    au régime de crue brutal : la proximité impose recul/risque → SOFT_FLAG, jamais une
    exclusion seule (le PPR/risques tranche, lui). Distance paramétrable (buffer)."""

    name = "ravine"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Réseau hydrographique (ravines) non ingéré.", source=SRC_BDTOPO)
        buffer_m = float(params.get("buffer_m", 10))
        d_axe = ctx.min_distance_m(parcel.id, kind)
        if d_axe is None:   # aucune ravine dans le rayon de garde → pas de flag (évite de confondre
            return passed(self.name, "Hors voisinage immédiat d'une ravine.", source=SRC_BDTOPO)
        # 2.C — la ravine est proche : si une SURFACE en eau (son lit/berge) existe, on mesure au BORD
        # (plus proche que l'axe sur une ravine large) ; sinon à l'AXE du tronçon.
        d_berge = None
        for bk in params.get("berge_kinds", []):
            db = ctx.min_distance_m(parcel.id, bk)
            if db is not None and (d_berge is None or db < d_berge):
                d_berge = db
        eff = min(d_axe, d_berge) if d_berge is not None else d_axe
        if eff > buffer_m:
            return passed(self.name, "Hors voisinage immédiat d'une ravine.", source=SRC_BDTOPO)
        sev = Severity(params.get("severity", "moyen"))
        au_bord = d_berge is not None and (d_axe is None or d_berge <= d_axe)
        if au_bord:
            base = ("au contact de la berge" if d_berge < 1.0 else f"berge à ~{d_berge:.0f} m")
            mesure = "mesuré AU BORD de la surface en eau"
        else:
            base = ("traversée par l'axe" if d_axe < 1.0 else f"à ~{d_axe:.0f} m de l'axe du tronçon")
            mesure = "mesuré à l'AXE (sur une ravine large, la berge est plus proche — recul réel à vérifier)"
        return soft_flag(
            self.name,
            f"Proximité d'une ravine ({base}, seuil {buffer_m:.0f} m) — {mesure} ; recul et risque "
            "de crue à vérifier (BD TOPO hydrographie).", sev, source=SRC_BDTOPO)


@register
class TraitDeCoteLayer(Layer):
    name = "trait_de_cote"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Recul du trait de côte non ingéré.", source=SRC_TRAIT)
        inter = ctx.intersections(parcel.id, kind)
        subtypes = {i.subtype for i in inter if i.coverage > 0}
        if subtypes & set(params.get("exclude_subtypes", [])):
            return hard_exclude(
                self.name, "Exclue : bande de précaution du recul du trait de côte.", kind="faux_positif", source=SRC_TRAIT
            )
        if subtypes & set(params.get("flag_subtypes", [])):
            return soft_flag(
                self.name, "Zone de recul du trait de côte (bande d'anticipation).", Severity(params.get("flag_severity", "moyen")), source=SRC_TRAIT
            )
        return passed(self.name, "Hors zone de recul du trait de côte.", source=SRC_TRAIT)


@register
class PenteLayer(Layer):
    """Pente CALCULÉE (RGE ALTI). 2.A : SOFT_FLAG au-delà du seuil (param, défaut 30 %, PLACEHOLDER) —
    sur une île montagneuse, la pente forte est un driver de coût (terrassement) et un risque, jamais
    une exclusion seule. En deçà du seuil : affichée, non pénalisante."""

    name = "pente"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        # Source de pente : couche raster/vecteur pré-calculée (kind='pente').
        if not ctx.kind_present("pente"):
            return unknown(
                self.name, "Pente non calculée (RGE ALTI non ingéré).", source=SRC_ALTI
            )
        inter = ctx.intersections(parcel.id, "pente")
        slope = max(((i.attrs or {}).get("slope_pct", 0) for i in inter), default=0)
        label = self._label(float(slope), params.get("slope_labels", {}))
        # ÉTAGE 0 (bloquant FRANC) : pente non aménageable → élimination en phase 1 (fusion du
        # déclassement). Testé AVANT le flag : au-delà du seuil franc, c'est un faux positif, pas
        # un simple surcoût. En deçà, la pente reste un flag/PASS (drivers de coût).
        seuil_fp = params.get("seuil_faux_positif_pct")
        if seuil_fp is not None and float(slope) > float(seuil_fp):
            return hard_exclude(
                self.name,
                f"Pente {float(slope):.0f} % (> {float(seuil_fp):.0f} %) — terrain non aménageable.",
                kind="faux_positif", source=SRC_ALTI)
        # GRADUÉE (spec v2 §4.4) : le terrassement se chiffre → MALUS signé par bande (L3), via
        # weight_override (les bandes −16..0 dépassent le multiplicateur de sévérité). Défaut :
        # 0–10 %→0 · 10–25 %→−4 · 25–40 %→−10 · 40–60 %→−16 (au-delà : exclu ci-dessus).
        bandes = params.get("bandes", [{"max": 10, "points": 0}, {"max": 25, "points": -4},
                                       {"max": 40, "points": -10}, {"max": 60, "points": -16}])
        pts = 0
        for b in bandes:
            if float(slope) <= float(b["max"]):
                pts = int(b["points"])
                break
        else:
            pts = int(bandes[-1]["points"])
        if pts == 0:
            return passed(
                self.name, f"Pente {label} (~{float(slope):.0f}%) — faible, non pénalisante.",
                source=SRC_ALTI, slope_pct=float(slope), slope_label=label)
        return scored(
            self.name,
            f"Pente {label} (~{float(slope):.0f}%) — terrassement chiffrable ({pts:+g}).",
            pts, source=SRC_ALTI, slope_pct=float(slope), slope_label=label)

    @staticmethod
    def _label(slope_pct: float, labels: dict) -> str:
        for name, hi in sorted(labels.items(), key=lambda kv: kv[1]):
            if slope_pct <= hi:
                return name
        return "tres_fort"


@register
class AbfLayer(Layer):
    name = "abf"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Périmètres ABF non ingérés.", source=SRC_ABF)
        if any(i.coverage > 0 for i in ctx.intersections(parcel.id, kind)):
            # Tampon 500 m qui sur-couvre → covisibilité NON instruite = INCERTITUDE, pas malus.
            if params.get("as_unknown"):
                return unknown(self.name, params["detail"], source=SRC_ABF)
            return soft_flag(self.name, params["detail"], Severity(params.get("severity", "faible")), source=SRC_ABF)
        return passed(self.name, "Hors périmètre ABF.", source=SRC_ABF)


@register
class EnsLayer(Layer):
    name = "ens"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Espaces Naturels Sensibles non ingérés.", source=SRC_ENS)
        if any(i.coverage > 0 for i in ctx.intersections(parcel.id, kind)):
            return soft_flag(self.name, params["detail"], Severity(params.get("severity", "moyen")), source=SRC_ENS)
        return passed(self.name, "Hors ENS.", source=SRC_ENS)


@register
class OcsGeLayer(Layer):
    name = "ocs_ge"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "OCS GE non ingéré.", source=SRC_OCSGE)
        dom = _dominant(ctx.intersections(parcel.id, kind))
        if dom is None or dom.coverage <= 0:
            return passed(self.name, "Occupation du sol non couverte ici.", source=SRC_OCSGE)
        if dom.subtype in set(params.get("naturel_subtypes", [])):
            return soft_flag(
                self.name, f"Sol {dom.subtype} (logique ZAN — artificialisation à justifier).", Severity(params.get("severity", "faible")), source=SRC_OCSGE
            )
        # ARTIFICIALISÉ non bâti (spec v2 §4.x) : ZAN-compatible → BONUS. Le bâti est déjà exclu à
        # l'étage 0, donc « artificialisé » survivant = terrain constructible sans dette ZAN.
        # Cumul PLAFONNÉ à `pair_cap_points` avec la vue mer (signaux distincts mais corrélés
        # géographiquement : littoral artificialisé) — la vue mer est prioritaire, l'OCS complète.
        if dom.subtype in set(params.get("artificialise_subtypes", ["artificialise"])):
            plein = int(params.get("artificialise_points", 4))
            cap = int(params.get("pair_cap_points", 10))
            vm = ctx.vue_mer(parcel.id)
            vue_pts = {"oui": 8, "partielle": 4}.get((vm or {}).get("vue"), 0)
            pts = max(0, min(plein, cap - vue_pts))
            if pts == 0:
                return passed(self.name, "Sol artificialisé (ZAN-compatible) — bonus déjà plafonné par la vue mer.",
                              source=SRC_OCSGE)
            return scored(self.name,
                          f"Sol artificialisé non bâti (ZAN-compatible — pas de dette d'artificialisation) ({pts:+g}).",
                          pts, source=SRC_OCSGE)
        return passed(self.name, f"Sol déjà {dom.subtype or 'artificialisé'}.", source=SRC_OCSGE)


@register
class OsmFauxPositifLayer(Layer):
    """Signal complémentaire OSM — jamais vérité juridique (brief §11)."""

    name = "osm_faux_positif"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        thr = params.get("coverage_threshold", 0.3)
        inter = [i for i in ctx.intersections(parcel.id, kind) if i.coverage >= thr]
        he = set(params.get("hard_exclude_subtypes", []))
        ff = set(params.get("flag_fort_subtypes", []))
        for i in inter:
            if i.subtype in he:
                return hard_exclude(
                    self.name, f"Exclue : {i.subtype} sur la parcelle (faux positif géométrique OSM).", kind="faux_positif", source=SRC_OSM
                )
        # ÉTAGE 0 (bloquant FRANC, fusion du déclassement) : un équipement OSM couvrant ≥ le seuil
        # franc (quel que soit le subtype) → la parcelle EST l'équipement → élimination. Au-delà de
        # `coverage_threshold` mais en deçà du seuil franc, pitch/parking restent un flag.
        faux_cov = params.get("faux_positif_coverage")
        if faux_cov is not None:
            strong = max(inter, key=lambda i: i.coverage, default=None)
            if strong is not None and strong.coverage >= float(faux_cov):
                return hard_exclude(
                    self.name,
                    f"{_osm_label(strong.subtype)} sur {strong.coverage * 100:.0f} % de la parcelle "
                    "(faux positif géométrique OSM).",
                    kind="faux_positif", source=SRC_OSM)
        for i in inter:
            if i.subtype in ff:
                return soft_flag(self.name, f"OSM : {i.subtype} sur la parcelle (à vérifier).", Severity.FORT, source=SRC_OSM)
        return passed(self.name, "Aucun faux positif géométrique OSM.", source=SRC_OSM)


@register
class AccesLayer(Layer):
    name = "acces"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Voirie (BD TOPO) non ingérée.", source=SRC_BDTOPO)
        # voirie qui touche/intersecte directement la parcelle = accès direct
        if any(i.coverage >= 0 for i in ctx.intersections(parcel.id, kind)):
            return positive(
                self.name, "Accès direct à la voirie (tronçon au contact de la parcelle).", params.get("bonus_key", "acces_direct_voirie"), source=SRC_BDTOPO
            )
        return passed(self.name, "Pas d'accès direct évident à la voirie.", source=SRC_BDTOPO)


@register
class SurfaceLayer(Layer):
    """Surface CALCULÉE et AFFICHÉE mais PAS de seuil dur (décision produit)."""

    name = "surface"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        s = parcel.surface_m2
        if s is None:
            return unknown(self.name, "Surface non calculée.")
        # ÉTAGE 0 (bloquant FRANC, fusion du déclassement) : sous le seuil franc, aucun programme
        # n'est possible → micro-parcelle → élimination en phase 1. Distinct du seuil dur de
        # valorisation ci-dessous (désactivé) : ici on élimine, on ne pénalise pas.
        faux_max = params.get("faux_positif_max_m2")
        if faux_max is not None and float(s) < float(faux_max):
            return hard_exclude(
                self.name,
                f"Micro-parcelle {float(s):.0f} m² (< {float(faux_max):.0f} m²) — aucun programme possible.",
                kind="faux_positif")
        # Seuil dur présent mais DÉSACTIVÉ par défaut (décision produit) :
        if params.get("threshold_enabled") and params.get("penalize"):
            mini = params.get("min_surface_m2_vierge", 0)
            if s < mini:
                return soft_flag(self.name, f"Surface {s:.0f} m² < seuil {mini} m².", Severity.MOYEN)
        # Bonus surface via COURBE SATURANTE (magnitude 0..1) : monte de lo→hi puis plafonne.
        lo = float(params.get("sweet_spot_lo_m2", 400))
        hi = float(params.get("sweet_spot_hi_m2", 2500))
        mag = 0.0 if hi <= lo else max(0.0, min(1.0, (float(s) - lo) / (hi - lo)))
        if mag > 0:
            return positive(
                self.name,
                f"Surface utile {s:.0f} m² — gisement (valorisation {round(mag * 100)}%, plafond {hi:.0f} m²).",
                params.get("bonus_key", "surface_utile"), magnitude=mag,
            )
        return passed(self.name, f"Surface {s:.0f} m² — sous le seuil de valorisation ({lo:.0f} m²).", surface_m2=round(float(s), 1))


@register
class BatiLayer(Layer):
    """Occupation bâtie FRANCHE (correctif R1 « déjà bâti ») → élimination phase 1.

    Réutilise `bati.classify` (source unique de vérité, partagée avec la fiche « Occupation »).
    Seul le cas FRANC (`declasse == 'faux_positif'` : déjà bâti / ensemble bâti, ex. la résidence
    BP0571) élimine ici, au même titre que `eau` ou `osm_faux_positif`. Le cas NON-franc
    (partiellement bâti → « à creuser ») reste un flag qualité du déclassement (étage 1).

    Les signaux bâtis (ratio/nb/plus grand bâtiment) sont lus dans `ctx.declass_signals`
    (batch, calculés une seule fois par le pipeline via compute_declass_signals) — la couche
    `kind='batiment'` est volontairement exclue du prime() de la cascade (coût overlay). Si la
    couche bâtiments n'est pas ingérée, aucun signal → UNKNOWN (jamais un faux « vacant »)."""

    name = "bati"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        from ... import bati as _bati  # import local : la couche batiment est lourde, découplée

        sig = ctx.declass_signals.get(parcel.id, {})
        ratio = sig.get("bati_ratio")
        if ratio is None:
            return unknown(self.name, "Couche bâtiments (BD TOPO) non ingérée — occupation non vérifiée.",
                           source=_bati.SOURCE)
        surface = sig.get("surface_m2")
        cls = _bati.classify(ratio, sig.get("bati_count") or 0, sig.get("bati_max_m2") or 0.0,
                             surface if surface is not None else parcel.surface_m2)
        if cls["declasse"] == "faux_positif":
            return hard_exclude(self.name, cls["motif"], kind="faux_positif", source=_bati.SOURCE)
        return passed(self.name, cls["label"], source=_bati.SOURCE)


@register
class FoncierPublicLayer(Layer):
    """G1 (spec v2 §3) — foncier public NON ACQUÉRABLE → HARD_EXCLUDE.

    Propriétaire = personne morale de droit public non marchande (classification DGFiP) :
    groupes 1 État, 2 Région, 3 Département, 4 Commune, 9 Établissements publics.
    HLM (5) et SEM (6) sont MARCHANDS — contreparties acquérables, futur segment bailleur —
    donc VOLONTAIREMENT préservés (jamais dans `groupes_exclus`). Absence de PM = propriétaire
    physique/privé → PASS. Motif humain nominatif, tracé DGFiP."""

    name = "foncier_public"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        pm = ctx.personne_morale(parcel.id)
        if not pm or pm.get("groupe") is None:
            return passed(self.name, "Propriétaire non public (personne physique ou PM privée).", source=SRC_DGFIP)
        groupe = int(pm["groupe"])
        label = (pm.get("groupe_label") or "").strip()
        if groupe in {int(g) for g in params.get("groupes_exclus", [])}:
            denom = (pm.get("denomination") or label or "personne publique").strip()
            return hard_exclude(
                self.name,
                f"Propriété publique ({denom}) — non acquérable "
                f"[classification DGFiP groupe {groupe} : {label}].",
                kind="exclue", source=SRC_DGFIP)
        return passed(self.name, f"Propriétaire PM « {label} » (groupe {groupe}) — acquérable.", source=SRC_DGFIP)


@register
class EmpriseLineaireLayer(Layer):
    """G2 (spec v2 §3) — emprise linéaire (rue, délaissé, chemin) → HARD_EXCLUDE.

    Rectangle englobant orienté à la fois TRÈS ALLONGÉ (ratio L/l > `ratio_min`) ET ÉTROIT
    (largeur < `largeur_max_m`) — les DEUX conditions cumulées. La jambe « largeur » protège
    les drapeaux (corps large + lanière d'accès : leur enveloppe fait la largeur du corps),
    validé sur échantillon Saint-Paul (0 / 3 831 drapeaux flaggés ; 2 / 1 183 flaggées à SDP≥300).
    Sous ces seuils la parcelle EST une lanière → faux positif géométrique."""

    name = "emprise_lineaire"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        f = ctx.forme(parcel.id)
        if not f or not f.get("larg"):
            return passed(self.name, "Forme non mesurable (parcelle dégénérée).", source=SRC_CADASTRE)
        larg = float(f["larg"])
        ratio = float(f["ratio"])
        larg_max = float(params.get("largeur_max_m", 8))
        ratio_min = float(params.get("ratio_min", 8))
        if larg < larg_max and ratio > ratio_min:
            return hard_exclude(
                self.name,
                f"Emprise linéaire — voirie/délaissé probable (largeur {larg:.0f} m < {larg_max:.0f} m "
                f"ET allongement {ratio:.0f}× > {ratio_min:.0f}×).",
                kind="faux_positif", source=SRC_CADASTRE)
        return passed(
            self.name,
            f"Forme non linéaire (largeur {larg:.0f} m, allongement {ratio:.1f}×).", source=SRC_CADASTRE)
