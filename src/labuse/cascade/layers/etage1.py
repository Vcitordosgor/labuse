"""Couches ÉTAGE 1 (dry-run) — QUALITÉ : friches, Géorisques ponctuels, aménités.

Signaux de qualité (bonus/malus/flags) sur les survivants. CHAQUE verdict porte
`extra = {source_table, source_id}` → cliquable jusqu'à l'enregistrement exact (exigence non
négociable). Poids/seuils/bandes en config (cascade_rules.yaml + opportunity_weights.yaml).

Non branché au scoring live — évalué en dry-run (tables dryrun_*).
"""
from __future__ import annotations

from ...enums import Severity
from ..base import Layer, Verdict, passed, positive, register, soft_flag, unknown
from ..context import EvalContext, ParcelRef

SRC_FRICHE = "Cartofriches (Cerema)"
SRC_SOLP = "Géorisques — sites et sols pollués"
SRC_CAVITE = "Géorisques — cavités souterraines"
SRC_ICPE = "Géorisques — ICPE"
SRC_MVT = "Géorisques — mouvements de terrain"
SRC_OSM = "OpenStreetMap / Overpass"


def _trace(v: Verdict, table: str, source_id) -> Verdict:
    """Rend le verdict cliquable : source_table + source_id dans extra (lu par le writer dry-run)."""
    v.extra = {"source_table": table, "source_id": source_id}
    return v


@register
class FricheLayer(Layer):
    name = "friche"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Friches non ingérées.", source=SRC_FRICHE)
        inter = [i for i in ctx.intersections(parcel.id, kind) if i.coverage > 0]
        if not inter:
            return passed(self.name, "Aucune friche recensée.", source=SRC_FRICHE)
        i = max(inter, key=lambda x: x.coverage)
        statut = (i.subtype or "").lower()          # subtype = site_statut ('friche avec projet'…)
        avec = "avec projet" in statut
        mag = params["magnitude_avec_projet"] if avec else params["magnitude_sans_projet"]
        label = i.name or "friche"
        return _trace(positive(self.name, f"Friche {statut or '—'} — reconversion ({label}).",
                               params["bonus_key"], magnitude=mag, source=SRC_FRICHE),
                      "spatial_layers", i.id)


class _NearestFlagLayer(Layer):
    """Base : flag SOFT_FLAG si un POI ponctuel du kind est sous le cap (le plus proche)."""

    src = ""

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, f"Couche {kind} non ingérée.", source=self.src)
        np = ctx.nearest_point(parcel.id, kind)
        if np is None:
            return passed(self.name, "Aucun objet recensé à proximité.", source=self.src)
        sev = self._severity(np["dist"], params)
        detail = f"{params['detail']} ({np.get('name') or kind}, {np['dist']:.0f} m)"
        return _trace(soft_flag(self.name, detail, sev, source=self.src), "spatial_layers", np["id"])

    def _severity(self, dist: float, params: dict) -> Severity:
        return Severity(params.get("severity", "faible"))


@register
class SolPollueLayer(_NearestFlagLayer):
    """LOT 2 (data-gap) — deux règles distinctes, tracées séparément :
      1. parcelle ∩ PÉRIMÈTRE SIS (subtype 'sis', MultiPolygon réglementaire) → SOFT_FLAG
         MOYEN : coût de dépollution potentiel, étude de sol obligatoire à la mutation
         (art. L.556-2 CE) — mention explicite en fiche via le détail du verdict ;
      2. site CASIAS / instruction sur la parcelle ou à MOINS DE 100 m → SOFT_FLAG FAIBLE
         (héritage vague B, rayon élargi 50 → 100 m par le mandat)."""

    name = "sol_pollue"
    src = SRC_SOLP

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, f"Couche {kind} non ingérée.", source=self.src)
        # 1) périmètre SIS intersecté (prime sur la proximité simple)
        sis = [i for i in ctx.intersections(parcel.id, kind)
               if (i.subtype or "") == "sis" and i.coverage > 0]
        if sis:
            i = max(sis, key=lambda x: x.coverage)
            return _trace(soft_flag(
                self.name,
                f"Parcelle dans un périmètre SIS ({i.name or 'secteur pollué'}) — coût de "
                "dépollution potentiel, étude de sol obligatoire à la mutation (L.556-2 CE).",
                Severity(params.get("severity_sis", "moyen")), source=self.src),
                "spatial_layers", i.id)
        # 2) site CASIAS / instruction ≤ proximite_m (100 m)
        return super().evaluate(parcel, ctx, params)


SRC_SUP = "SUP — assiettes GPU (API Carto)"

#: LOT 4 (data-gap) — sévérité par catégorie de SUP intersectée. Les catégories DÉJÀ scorées
#: par une autre couche sont neutralisées (info ×0) : pm* = PPR (couche risques), ac1/ac2 =
#: monuments/sites (couche abf), el10 = parc national (couche parc_national).
SUP_SEVERITES = {
    "t4": "moyen", "t5": "fort", "t7": "moyen",         # servitudes aéronautiques
    "i4": "moyen",                                       # lignes électriques HT/THT
    "i1": "moyen", "i1bis": "moyen", "i3": "moyen",      # hydrocarbures / gaz
    "pm1": "info", "pm2": "info", "pm3": "info",         # PPR — déjà scoré (risques)
    "ac1": "info", "ac2": "info",                        # MH / sites — déjà scoré (abf)
    "el10": "info",                                      # parc national — déjà scoré
}
SUP_DEFAUT = "faible"


@register
class SupLayer(Layer):
    """LOT 4 (data-gap) — parcelle ∩ assiette de SUP : flag par TYPE de servitude + liste en
    fiche. Malus Stage 1 selon la catégorie (SUP_SEVERITES) ; la plus sévère porte le verdict,
    toutes sont listées dans le détail. Anti-double-compte : cf. SUP_SEVERITES."""

    name = "sup"

    _ORDRE = {"fort": 3, "moyen": 2, "faible": 1, "info": 0}

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Assiettes SUP non ingérées.", source=SRC_SUP)
        inter = [i for i in ctx.intersections(parcel.id, kind) if i.coverage > 0]
        if not inter:
            return passed(self.name, "Aucune servitude d'utilité publique recensée.", source=SRC_SUP)
        types: dict[str, str] = {}
        for i in inter:
            st = (i.subtype or "?").lower()
            types.setdefault(st, i.name or st)
        sev_of = lambda st: SUP_SEVERITES.get(st, SUP_DEFAUT)  # noqa: E731
        pire = max(types, key=lambda st: self._ORDRE[sev_of(st)])
        liste = " ; ".join(f"{st.upper()} ({nom})" for st, nom in sorted(types.items()))
        i_ref = next(i for i in inter if (i.subtype or "?").lower() == pire)
        detail = (f"Servitude(s) d'utilité publique sur la parcelle : {liste}."
                  + (" Catégorie déjà couverte par une autre couche (0 pt, anti-double-compte)."
                     if sev_of(pire) == "info" else ""))
        return _trace(soft_flag(self.name, detail, Severity(sev_of(pire)), source=SRC_SUP),
                      "spatial_layers", i_ref.id)


SRC_BRUIT = "Classement sonore ITT (Cerema)"


@register
class BruitRouteLayer(Layer):
    """LOT 3 (data-gap) — parcelle dans un SECTEUR AFFECTÉ PAR LE BRUIT (bande matérialisée du
    classement sonore, R.571-32 CE : isolement acoustique renforcé obligatoire). Malus Stage 1 :
    catégories 1-2 (grands axes, secteurs 250-300 m) → moyen ; 3-5 → faible. Le PEB (zones
    A/B/C/D aérodromes) est BLOQUÉ (pas de SIG open data 974) — ceci n'en est pas un substitut."""

    name = "bruit_route"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return unknown(self.name, "Classement sonore non ingéré.", source=SRC_BRUIT)
        inter = [i for i in ctx.intersections(parcel.id, kind) if i.coverage > 0]
        if not inter:
            return passed(self.name, "Hors secteurs affectés par le bruit routier.", source=SRC_BRUIT)
        pire = min(inter, key=lambda i: int((i.attrs or {}).get("categorie") or 9))
        cat = int((pire.attrs or {}).get("categorie") or 0)
        sev = "moyen" if cat in (1, 2) else "faible"
        return _trace(soft_flag(
            self.name,
            f"Secteur affecté par le bruit routier (classement sonore cat. {cat}, bande "
            f"{(pire.attrs or {}).get('sect_bruit_m')} m) — isolement acoustique renforcé "
            "obligatoire (R.571-32 CE).",
            Severity(sev), source=SRC_BRUIT), "spatial_layers", pire.id)


@register
class CaviteLayer(_NearestFlagLayer):
    name = "cavite"
    src = SRC_CAVITE


@register
class MvtLayer(_NearestFlagLayer):
    name = "mvt"
    src = SRC_MVT     # severity 'info' (×0) → flag affiché, 0 point (anti double-compte PPR)


@register
class IcpeLayer(_NearestFlagLayer):
    name = "icpe"
    src = SRC_ICPE

    def _severity(self, dist: float, params: dict) -> Severity:
        b = params["bandes_m"]                        # {fort:50, moyen:150, faible:300}
        if dist <= b["fort"]:
            return Severity.FORT
        if dist <= b["moyen"]:
            return Severity.MOYEN
        return Severity.FAIBLE


@register
class AmenitesLayer(Layer):
    name = "amenites"

    _COLS = {"ecole": "dist_ecole_m", "commerce": "dist_commerce_m",
             "sante": "dist_sante_m", "tcsp": "dist_tcsp_m"}

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        am = ctx.amenites(parcel.id)
        if am is None:
            return unknown(self.name, "Aménités non calculées pour la parcelle.", source=SRC_OSM)
        defo, tcsp_b = params["bandes_defaut_m"], params["bandes_tcsp_m"]
        pond = params["ponderations"]
        mag = 0.0
        for cat, col in self._COLS.items():
            d = am.get(col)
            bands = tcsp_b if cat == "tcsp" else defo
            if d is None:
                prox = 0.0
            elif d <= bands["plein"]:
                prox = 1.0
            elif d <= bands["demi"]:
                prox = 0.5
            else:
                prox = 0.0
            mag += pond[cat] * prox
        def _m(col):
            v = am.get(col)
            return f"{int(v)}m" if v is not None else "—"
        detail = (f"Aménités : école {_m('dist_ecole_m')}, commerce {_m('dist_commerce_m')}, "
                  f"santé {_m('dist_sante_m')}, bus {_m('dist_tcsp_m')} (score {mag:.2f}).")
        return _trace(positive(self.name, detail, params["bonus_key"], magnitude=mag, source=SRC_OSM),
                      "parcel_amenites", parcel.id)
