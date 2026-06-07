"""Couches PHASE 2 — coûteuses / externes / IA, UNIQUEMENT sur parcelles promues.

Brief §4 : on ne déclenche les appels lents/chers qu'au moment où une parcelle a
survécu à la phase 1 (pas de HARD_EXCLUDE). Ici, DVF (rayon), SITADEL (appariement),
Potentiel foncier Région (îlot) et propriétaire/indivision.
"""
from __future__ import annotations

from ...enums import Severity
from ..base import Layer, Verdict, passed, positive, register, soft_flag, unknown
from ..context import EvalContext, ParcelRef

SRC_DVF = "DVF / valeurs foncières"
SRC_SITADEL = "SITADEL (autorisations d'urbanisme)"
SRC_POTENTIEL = "data.regionreunion.com — Potentiel foncier"
SRC_FF = "Fichiers fonciers (Cerema)"


@register
class DvfLayer(Layer):
    """Contexte marché par RAYON (jamais par égalité d'IDU), agrégé (R112 A-3 LPF)."""

    name = "dvf"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        if not ctx.table_has_commune("dvf_mutations", parcel.commune):
            return unknown(self.name, "DVF non ingéré pour la commune.", source=SRC_DVF)
        years = params.get("lookback_years", 5)
        for radius in params.get("radii_m", [250, 500, 1000]):
            stats = ctx.dvf_stats(parcel.id, radius, years)
            if stats["count"] > 0:
                med = stats["median_value"]
                med_txt = f"médiane ~{med:,.0f} €".replace(",", " ") if med else "médiane n/d"
                detail = f"Marché DVF : {stats['count']} mutation(s) ≤ {radius} m sur {years} ans, {med_txt}."
                # Liquidité suffisante → signal favorable (bonus).
                if stats["count"] >= 3:
                    return positive(self.name, detail + " Marché liquide.", params.get("bonus_key", "contexte_dvf_favorable"), source=SRC_DVF)
                return passed(self.name, detail, source=SRC_DVF)
        return passed(self.name, "Aucune mutation DVF dans le rayon max.", source=SRC_DVF)


@register
class SitadelLayer(Layer):
    """Appariement SITADEL (§7bis) : rattaché par IDU vs signal de zone (rayon)."""

    name = "sitadel"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        if not ctx.table_has_commune("sitadel_permits", parcel.commune):
            return unknown(self.name, "SITADEL non ingéré pour la commune.", source=SRC_SITADEL)
        radius = params.get("radius_m", 200)
        months = params.get("lookback_months", 36)
        res = ctx.sitadel_near(parcel.id, radius, months)
        if res["matched_idu"] > 0:
            return positive(
                self.name,
                f"{res['matched_idu']} permis récent(s) RATTACHÉ(S) par IDU (≤ {months} mois).",
                params.get("bonus_key", "permis_sitadel_recent_proximite"),
                source=SRC_SITADEL,
            )
        if res["nearby"] > 0:
            return positive(
                self.name,
                f"{res['nearby']} permis récent(s) à ≤ {radius} m — SIGNAL DE ZONE (rayon, pas un fait parcellaire, §7bis).",
                params.get("bonus_key", "permis_sitadel_recent_proximite"),
                source=SRC_SITADEL,
            )
        return passed(self.name, "Aucun permis SITADEL récent à proximité.", source=SRC_SITADEL)


@register
class PotentielFoncierLayer(Layer):
    """Potentiel foncier Région = signal BONUS (brief §1)."""

    name = "potentiel_foncier_region"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        kind = params["spatial_kind"]
        if not ctx.kind_present(kind):
            return passed(self.name, "Potentiel foncier Région non ingéré (signal bonus absent).", source=SRC_POTENTIEL)
        if any(i.coverage > 0 for i in ctx.intersections(parcel.id, kind)):
            return positive(self.name, params["detail"], params.get("bonus_key", "potentiel_foncier_region"), source=SRC_POTENTIEL)
        return passed(self.name, "Hors îlot « Potentiel foncier » Région.", source=SRC_POTENTIEL)


@register
class ProprietaireLayer(Layer):
    """Propriétaire moral/public (bonus) + indivision (flag). Fichiers fonciers, §11.

    Lit le dernier résultat de la source « Fichiers fonciers (Cerema) » pour la
    parcelle (manuel/mock tant que la convention n'est pas branchée). Jamais de
    personne physique nominative.
    """

    name = "proprietaire"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> list[Verdict]:
        res = ctx.latest_source_result(parcel.id, SRC_FF)
        if not res or not res.get("raw_payload"):
            return [unknown(self.name, "Propriétaire inconnu (Fichiers fonciers sous convention non branchés).", source=SRC_FF)]

        payload = res["raw_payload"]
        verdicts: list[Verdict] = []

        nb_droits = payload.get("nb_droits_propriete")
        indivision = payload.get("indivision") or (nb_droits is not None and nb_droits >= params.get("indivision_min_droits", 2))
        if indivision:
            n = f"{nb_droits} droits" if nb_droits else "plusieurs droits"
            verdicts.append(
                soft_flag(
                    self.name,
                    f"Indivision probable ({n} de propriété sur le compte) — bloqueur fréquent à La Réunion.",
                    Severity(params.get("indivision_severity", "fort")),
                    source=SRC_FF,
                )
            )

        if payload.get("personne_morale"):
            categorie = payload.get("categorie", "personne morale/publique")
            verdicts.append(
                positive(
                    self.name,
                    f"Propriétaire {categorie} — publiquement identifiable et potentiellement acquérable.",
                    params.get("bonus_key", "proprietaire_morale_acquerable"),
                    source=SRC_FF,
                )
            )

        if not verdicts:
            verdicts.append(passed(self.name, "Propriétaire renseigné, sans signal particulier.", source=SRC_FF))
        return verdicts
