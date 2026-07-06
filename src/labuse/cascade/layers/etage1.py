"""Couches ÉTAGE 1 (dry-run) — QUALITÉ : friches, Géorisques ponctuels, aménités.

Signaux de qualité (bonus/malus/flags) sur les survivants. CHAQUE verdict porte
`extra = {source_table, source_id}` → cliquable jusqu'à l'enregistrement exact (exigence non
négociable). Poids/seuils/bandes en config (cascade_rules.yaml + opportunity_weights.yaml).

Non branché au scoring live — évalué en dry-run (tables dryrun_*).
"""
from __future__ import annotations

from ...enums import Severity
from ..base import Layer, Verdict, passed, positive, register, scored, soft_flag, unknown
from ..context import EvalContext, ParcelRef

SRC_FRICHE = "Cartofriches (Cerema)"
SRC_SOLP = "Géorisques — sites et sols pollués"
SRC_CAVITE = "Géorisques — cavités souterraines"
SRC_ICPE = "Géorisques — ICPE"
SRC_MVT = "Géorisques — mouvements de terrain"
SRC_OSM = "OpenStreetMap / Overpass"
SRC_RESIDUEL = "SDP résiduelle (LABUSE — règlement PLU calibré)"
SRC_VUEMER = "Vue mer (LABUSE — calcul viewshed 974)"
SRC_ASSEMBLAGE = "Assemblage propriétaire (DGFiP + contiguïté)"


def _bande_socle(sdp: float, bandes: list[dict]) -> tuple[float, str]:
    """Barème 4.1 : première bande dont `max` n'est pas dépassé (max=None → tranche haute).
    Bornes = « < max » (SDP 100 tombe dans la bande 100–300, pas dans < 100)."""
    for b in bandes:
        mx = b.get("max")
        if mx is None or sdp < float(mx):
            return float(b["points"]), b.get("lecture", "")
    last = bandes[-1]
    return float(last["points"]), last.get("lecture", "")


def _trace(v: Verdict, table: str, source_id) -> Verdict:
    """Rend le verdict cliquable : source_table + source_id dans extra (lu par le writer dry-run)."""
    v.extra = {"source_table": table, "source_id": source_id}
    return v


@register
class ResiduelSocleLayer(Layer):
    """SOCLE L1 (spec v2 §4.1) — la constructibilité résiduelle est LE facteur Q dominant.

    Barème SIGNÉ −25..+30 par bande de SDP résiduelle (`parcel_residuel`, calibrée sur le
    règlement PLU réel). C'est la loi qui tue les faux positifs « bon emplacement, rien à
    bâtir » (grappe des micro-lots résiduels). NON CALCULÉ (parcelle absente de
    `parcel_residuel`, couverture ~61 %) = UNKNOWN : l'absence de donnée n'est PAS une absence
    de droits — impacte la complétude, JAMAIS −25 (exigence Vic, règle absolue).

    Poids direct via `scored()` (les bandes ±25 dépassent le multiplicateur de sévérité)."""

    name = "residuel_socle"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        r = ctx.residuel(parcel.id)
        if not r or r.get("sdp") is None:
            return unknown(
                self.name,
                "SDP résiduelle non calculée — droits à construire inconnus (hors couverture "
                "parcel_residuel) ; à résoudre par extension du calcul, pas un signal d'absence de droits.",
                source=SRC_RESIDUEL)
        sdp = float(r["sdp"])
        pts, lecture = _bande_socle(sdp, params["bandes"])
        detail = f"SDP résiduelle {sdp:.0f} m² — {lecture} (socle {pts:+g})."
        return _trace(scored(self.name, detail, pts, source=SRC_RESIDUEL), "parcel_residuel", parcel.id)


@register
class VueMerLayer(Layer):
    """Vue mer (spec v2 §4.2) — prime de PRIX DE SORTIE spécifique 974, entre en Q (pas dans le bilan).
    oui → +8 · partielle → +4 · non/absent → 0. Via bonus×magnitude (plafond `bonus_key`)."""

    name = "vue_mer"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        v = ctx.vue_mer(parcel.id)
        vue = (v or {}).get("vue")
        mag = {"oui": 1.0, "partielle": 0.5}.get(vue, 0.0)
        if mag <= 0:
            return passed(self.name, "Pas de vue mer.", source=SRC_VUEMER)
        d = (v or {}).get("distance_cote_m")
        qual = "dégagée" if mag == 1.0 else "partielle"
        detail = f"Vue mer {qual}" + (f" (côte à ~{d} m)" if d else "") + " — prime de prix de sortie."
        return _trace(positive(self.name, detail, params.get("bonus_key", "vue_mer"), magnitude=mag, source=SRC_VUEMER),
                      "parcel_vue_mer", parcel.id)


@register
class AssemblageLayer(Layer):
    """Assemblage même propriétaire adjacent (spec v2 — signal nouveau) → +6 + flag.
    Voisin contigu (≤1 m) partageant le SIREN, avec garde-fou anti-lotissement (détention ≤ N,
    la SCCV à 77 parcelles est le faux positif type). Le contexte a déjà filtré (cf. prime)."""

    name = "assemblage"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        a = ctx.assemblage(parcel.id)
        if not a:
            return passed(self.name, "Pas d'assiette élargissable (propriétaire adjacent).", source=SRC_ASSEMBLAGE)
        n, siren = a["voisins"], a["siren"]
        detail = (f"Assiette élargissable — {n} parcelle(s) contiguë(s) du même propriétaire "
                  f"(SIREN {siren}, détention {a['holding']}) : négociation d'un seul tenant possible.")
        return _trace(positive(self.name, detail, params.get("bonus_key", "assemblage"), source=SRC_ASSEMBLAGE),
                      "parcelle_personne_morale", parcel.idu)


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
    name = "sol_pollue"
    src = SRC_SOLP


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
