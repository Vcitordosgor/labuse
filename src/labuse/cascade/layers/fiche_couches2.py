"""FICHE-COUCHES-2 — couches manquantes branchées à la fiche (intersection parcelle × couche).

Suite de l'inventaire FICHE-COUCHES-1 : le tuyau sert 55 couches (56 avant DONNEES-1 lot 2.1 —
piscine partie en Prospection solaire), la fiche n'en croisait que
40. Ce module ajoute des couches de cascade (dry-run, onglet servi) pour les couches dont le
THÈME était déjà croisé mais pas la couche elle-même (lot 1), puis deux couches à enjeu foncier
(lot 2). Même patron que etage1 : intersection via `ctx.intersections`, verdict tracé
(`source_table`/`source_id`), sévérité en enum. Rien de neuf côté scoring/carto.
"""
from __future__ import annotations

from ...enums import Severity
from ..base import Layer, Verdict, passed, register, soft_flag, unknown
from ..context import EvalContext, ParcelRef

SRC_ZNIEFF = "INPN — ZNIEFF (inventaire du patrimoine naturel)"
SRC_TRI = "DEAL Réunion — TRI (scénarios d'inondation)"
SRC_BRUIT_CARTE = "Cartes de bruit stratégiques (CBS) — dépassements"
SRC_ENDIG = "DEAL Réunion — systèmes d'endiguement"


def _trace(v: Verdict, source_id) -> Verdict:
    v.extra = {"source_table": "spatial_layers", "source_id": source_id}
    return v


def _pct(coverage: float | None) -> str:
    # COHERENCE-FIX-1 (lot D) — recouvrement non mesuré → « part non mesurée », jamais « < 1 % »
    # (l'ancien `coverage or 0.0` transformait une absence en petit pourcentage plausible).
    if coverage is None:
        return "part non mesurée"
    p = round(coverage * 100)
    return f"{p} %" if p >= 1 else "< 1 %"


# ───────────────────────── LOT 1 — extensions (thème déjà croisé) ─────────────────────────

@register
class ZnieffLayer(Layer):
    """ZNIEFF (type I & II) — inventaire du patrimoine naturel. Le thème « environnement » est déjà
    croisé (ENP/parc/zones humides) ; la ZNIEFF ne l'était pas. Ce n'est pas une protection
    réglementaire directe, mais un signal à intégrer au projet → SOFT_FLAG faible (type I un cran
    au-dessus : zones les plus remarquables)."""

    name = "znieff"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "ZNIEFF non ingérées.", source=SRC_ZNIEFF)
        inter = [i for i in ctx.intersections(parcel.id, kind) if i.coverage > 0]
        if not inter:
            return passed(self.name, "Hors ZNIEFF.", source=SRC_ZNIEFF)
        i = max(inter, key=lambda x: x.coverage)
        typ = (i.subtype or "ZNIEFF")
        sev = Severity.MOYEN if "i" == (typ.split()[-1].lower() if typ else "") else Severity.FAIBLE
        return _trace(soft_flag(
            self.name,
            f"Parcelle en ZNIEFF {typ} ({i.name or '—'}) — {_pct(i.coverage)} de la parcelle : "
            "inventaire du patrimoine naturel (à intégrer au projet ; ce n'est pas, à elle seule, "
            "une protection réglementaire opposable).",
            sev, source=SRC_ZNIEFF), i.id)


_TRI_SEV = {"frequent": Severity.MOYEN, "moyen": Severity.FAIBLE, "extreme": Severity.FAIBLE}


@register
class TriZoneLayer(Layer):
    """TRI — zones inondables (scénarios fréquent / moyen / extrême). Le thème « inondation » est déjà
    croisé (PPR + aléas Géorisques) ; les scénarios TRI de la directive inondation, plus fins, ne
    l'étaient pas. Sévérité selon le scénario le plus contraignant intersecté (fréquent = le plus
    probable). Complète le PPR, ne le remplace pas."""

    name = "tri_zone"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Zones TRI non ingérées.", source=SRC_TRI)
        inter = [i for i in ctx.intersections(parcel.id, kind) if i.coverage > 0]
        if not inter:
            return passed(self.name, "Hors zone inondable TRI.", source=SRC_TRI)
        scen = {(i.subtype or "").lower() for i in inter}
        pire = "frequent" if "frequent" in scen else "moyen" if "moyen" in scen else "extreme"
        i = max((x for x in inter if (x.subtype or "").lower() == pire), key=lambda x: x.coverage)
        return _trace(soft_flag(
            self.name,
            f"Zone inondable TRI — scénario {pire} ({_pct(i.coverage)} de la parcelle) : "
            "cartographie de la directive inondation (submersion modélisée) ; complète le PPR.",
            _TRI_SEV.get(pire, Severity.FAIBLE), source=SRC_TRI), i.id)


@register
class BruitCarteLayer(Layer):
    """Cartes de bruit stratégiques (CBS) — zones de DÉPASSEMENT des seuils Lden/Ln. Le thème « bruit »
    est déjà croisé (classement sonore `bruit_route`, qui impose l'isolement) ; les dépassements CBS,
    distincts (constat de nuisance, pas une obligation d'isolement), ne l'étaient pas → SOFT_FLAG faible."""

    name = "bruit_carte"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Cartes de bruit non ingérées.", source=SRC_BRUIT_CARTE)
        inter = [i for i in ctx.intersections(parcel.id, kind) if i.coverage > 0]
        if not inter:
            return passed(self.name, "Hors zone de dépassement de bruit.", source=SRC_BRUIT_CARTE)
        i = max(inter, key=lambda x: x.coverage)
        return _trace(soft_flag(
            self.name,
            f"Dépassement de bruit (carte stratégique) : {i.name or '—'} — {_pct(i.coverage)} de la "
            "parcelle : constat de nuisance sonore (≠ classement sonore, qui impose l'isolement).",
            Severity.FAIBLE, source=SRC_BRUIT_CARTE), i.id)


@register
class EndiguementLayer(Layer):
    """Systèmes d'endiguement — la parcelle est dans une ZONE PROTÉGÉE derrière une digue. Le thème
    « inondation » est déjà croisé (PPR/aléas) ; l'inondation RÉSIDUELLE derrière l'ouvrage (défaillance
    ou dépassement du niveau de protection) ne l'était pas → SOFT_FLAG moyen. On flague l'appartenance
    à une zone protégée (subtype `zone_protegee`), pas le tracé de la digue elle-même."""

    name = "endiguement"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Systèmes d'endiguement non ingérés.", source=SRC_ENDIG)
        zones = [i for i in ctx.intersections(parcel.id, kind)
                 if (i.subtype or "") == "zone_protegee" and i.coverage > 0]
        if not zones:
            return passed(self.name, "Hors zone protégée par un système d'endiguement.", source=SRC_ENDIG)
        i = max(zones, key=lambda x: x.coverage)
        a = i.attrs or {}
        det = f" (classe {a.get('classe')})" if a.get("classe") else ""
        return _trace(soft_flag(
            self.name,
            f"Parcelle protégée par un système d'endiguement — {i.name or 'ouvrage'}{det} : "
            "inondation RÉSIDUELLE en cas de défaillance ou de dépassement du niveau de protection.",
            Severity.MOYEN, source=SRC_ENDIG), i.id)


# ───────────────────────── LOT 2 — deux couches à enjeu foncier ─────────────────────────

SRC_BV = "BD TOPO / BD Carthage — bassins versants (hydrographie)"
SRC_ZA = "BD TOPO — zones d'activité ou d'intérêt"


@register
class BassinVersantLayer(Layer):
    """Bassin versant — nouveau handler (le thème hydrographie n'était pas croisé). CONTEXTE
    hydrographique : l'urbanisation amont pèse sur le ruissellement/la submersion en aval, un
    facteur de décision. La donnée est une DÉLIMITATION (code hydro), sans attribut de risque
    par bassin → sévérité INFO (ligne de contexte affichée, 0 point ; pas une alerte graduée)."""

    name = "bassin_versant"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Bassins versants non ingérés.", source=SRC_BV)
        inter = [i for i in ctx.intersections(parcel.id, kind) if i.coverage > 0]
        if not inter:
            return passed(self.name, "Hors bassin versant cartographié.", source=SRC_BV)
        i = max(inter, key=lambda x: x.coverage)
        code = (i.attrs or {}).get("code_hydro")
        ref = f"code hydro {code}" if code else (i.name or "bassin")
        return _trace(soft_flag(
            self.name,
            f"Bassin versant ({ref}) — {_pct(i.coverage)} de la parcelle : contexte hydrographique "
            "(ruissellement amont/aval, submersion). L'urbanisation en amont pèse sur l'aval — à "
            "considérer avec les aléas et scénarios d'inondation.",
            Severity.INFO, source=SRC_BV), i.id)


@register
class ZoneActiviteLayer(Layer):
    """Zone d'activité ou d'intérêt (BD TOPO) — nouveau handler à enjeu FONCIER : la destination
    économique de la zone (industrielle, commerciale, équipement…) pèse sur la valeur, les
    nuisances et les règles propres. SOFT_FLAG faible, servi à l'onglet Marché (served_cascade)."""

    name = "zone_activite"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Zones d'activité non ingérées.", source=SRC_ZA)
        inter = [i for i in ctx.intersections(parcel.id, kind) if i.coverage > 0]
        if not inter:
            return passed(self.name, "Hors zone d'activité.", source=SRC_ZA)
        i = max(inter, key=lambda x: x.coverage)
        nature = i.subtype or "zone d'activité"
        nom = f" « {i.name} »" if i.name and i.name != nature else ""
        return _trace(soft_flag(
            self.name,
            f"Parcelle dans une zone d'activité ou d'intérêt — {nature}{nom} ({_pct(i.coverage)} "
            "de la parcelle) : destination économique à considérer (valeur, nuisances éventuelles, "
            "règles propres à la zone).",
            Severity.FAIBLE, source=SRC_ZA), i.id)
