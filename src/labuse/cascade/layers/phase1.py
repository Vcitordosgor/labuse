"""Couches PHASE 1 — géométriques, locales, PostGIS, sur TOUTES les parcelles.

Le moins cher / le plus décisif d'abord (brief §2). Chaque couche lit ses params
dans config/cascade_rules.yaml et rend 0..n Verdicts avec un motif humain.

Convention UNKNOWN vs PASS : si la donnée n'est pas ingérée pour la commune
(ctx.kind_present == False) → UNKNOWN (impacte la complétude). Si la donnée est
présente mais que la parcelle n'est pas contrainte → PASS.
"""
from __future__ import annotations

from typing import Any

from ...enums import Severity
from ..base import Layer, Verdict, hard_exclude, passed, positive, register, soft_flag, unknown
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


def _dominant(intersections) -> Any | None:
    """Entité couvrant la plus grande part de la parcelle."""
    return max(intersections, key=lambda i: i.coverage, default=None)


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
    """SAR — juridiquement SUPÉRIEUR au PLU (brief §3). Couche de premier rang."""

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
        lib = (dom.attrs or {}).get("libelle")
        pct = f" (~{dom.coverage * 100:.0f}% de la parcelle)" if dom.coverage < 0.99 else ""
        if dom.subtype in set(params.get("hard_exclude_subtypes", [])):
            return hard_exclude(
                self.name,
                f"Exclue : SAR « {lib or dom.subtype} » (espace naturel / coupure d'urbanisation — supérieur au PLU).",
                kind="faux_positif",
                source=SRC_SAR,
            )
        if dom.subtype in set(params.get("flag_fort_subtypes", [])):
            return soft_flag(
                self.name,
                f"SAR : vocation à vérifier — {lib or 'espace agricole (risque préemption SAFER)'}{pct} "
                "— possible contrainte régionale (ne vaut ni interdiction ni constructibilité).",
                Severity.FORT,
                source=SRC_SAR,
            )
        return passed(self.name,
                      f"SAR : vocation compatible détectée — {lib or 'territoire urbain'} — à croiser avec PLU/PPR.",
                      source=SRC_SAR)


@register
class ZonagePluGpuLayer(Layer):
    name = "zonage_plu_gpu"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(
                self.name,
                "Zonage PLU/GPU indisponible (document non dématérialisé sur le GPU ? → fallback import).",
                source=SRC_GPU,
            )
        inter = ctx.intersections(parcel.id, kind)
        dom = _dominant(inter)
        if dom is None or dom.coverage <= 0:
            return passed(self.name, "Hors zonage PLU connu.", source=SRC_GPU)
        libelle = (dom.subtype or "").strip()
        up = libelle.upper()
        if libelle in set(params.get("exclude_zones", [])):
            return hard_exclude(
                self.name, f"Exclue : zone PLU « {libelle} » strictement inconstructible.", kind="faux_positif", source=SRC_GPU
            )
        # Constructible (U / AU) EN PREMIER : sinon « AUc/AUs » serait happé par le
        # préfixe agricole « A » (AU commence par A). L'ordre des tests fait foi.
        if any(up.startswith(p) for p in params.get("positive_prefixes", [])):
            return positive(
                self.name,
                f"Zone PLU « {libelle} » (urbaine / à urbaniser — constructible).",
                params.get("positive_bonus_key", "zonage_u_au"),
                source=SRC_GPU,
            )
        # A (agricole) / N (naturelle) : non constructibles au règlement du PLU de Saint-Paul
        # (cf. plu_saint_paul.yaml « zones non constructibles : A, N »). HARD_EXCLUDE (décision
        # Vic : aligner cascade ↔ réalité PLU). Testé APRÈS U/AU (AU commence par « A »).
        if any(up.startswith(p) for p in params.get("hard_exclude_prefixes", [])):
            nature = "agricole" if up.startswith("A") else "naturelle"
            return hard_exclude(
                self.name,
                f"Exclue : zone PLU « {libelle} » ({nature} — non constructible au règlement).",
                kind="faux_positif", source=SRC_GPU,
            )
        if any(up.startswith(p) for p in params.get("flag_fort_prefixes", [])):
            return soft_flag(self.name, f"Zone PLU « {libelle} » (naturelle).", Severity.FORT, source=SRC_GPU)
        if any(up.startswith(p) for p in params.get("flag_prefixes", [])):
            return soft_flag(self.name, f"Zone PLU « {libelle} » (agricole — SAFER).", Severity.MOYEN, source=SRC_GPU)
        return passed(self.name, f"Zone PLU « {libelle} ».", source=SRC_GPU)


@register
class PrescriptionPluLayer(Layer):
    """Prescriptions du PLU (GPU) : emplacement réservé, mixité sociale, EBC, patrimoine bâti,
    OAP, eaux pluviales… De VRAIES servitudes opposables, jusque-là non lues par la cascade.

    PRUDENCE assumée : aucune prescription n'exclut SEULE (ce sont des servitudes/contraintes
    de programme, pas une inconstructibilité de droit). Le libellé GPU est TOUJOURS affiché ;
    le `typepsc` CNIG ne sert qu'à graduer la sévérité (mapping dans cascade_rules.yaml).
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
        seuil = float(params.get("majorite_threshold", 0.5))

        verdicts: list[Verdict] = []
        seen: set[tuple[str | None, str]] = set()
        for i in inter:
            tp = (i.subtype or "").strip()
            lib = ((i.attrs or {}).get("libelle") or i.name or "prescription PLU").strip()
            if (tp, lib) in seen:
                continue
            seen.add((tp, lib))
            pct = f" (~{i.coverage * 100:.0f}% de la parcelle)" if i.coverage >= 0.01 else ""
            # Contraintes DISCRIMINANTES (spécifiques à la parcelle) → SOFT_FLAG pénalisant.
            if tp in er:
                sev = Severity.FORT if i.coverage >= seuil else Severity.MOYEN
                verdicts.append(soft_flag(
                    self.name, f"Emplacement réservé : {lib}{pct} — emprise grevée au profit d'un "
                    "projet public, constructibilité réduite (servitude levable).", sev, source=SRC_GPU))
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
                pct = f" (~{i.coverage * 100:.0f}% de la parcelle)" if i.coverage < 0.99 else ""
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
    """Pente CALCULÉE et AFFICHÉE mais NON excluante (décision produit, brief §2)."""

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
        # ⚠ Même si threshold_enabled, on N'EXCLUT/PÉNALISE PAS par défaut.
        return passed(
            self.name,
            f"Pente {label} (~{float(slope):.0f}%) — calculée, non éliminatoire.",
            source=SRC_ALTI,
            slope_pct=float(slope),
            slope_label=label,
        )

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
