"""Couches PHASE 2 — coûteuses / externes / IA, UNIQUEMENT sur parcelles promues.

Brief §4 : on ne déclenche les appels lents/chers qu'au moment où une parcelle a
survécu à la phase 1 (pas de HARD_EXCLUDE). Ici, DVF (rayon), SITADEL (appariement),
Potentiel foncier Région (îlot) et propriétaire/indivision.
"""
from __future__ import annotations

from ...enums import Severity
from ..base import Layer, Verdict, passed, positive, register, scored, soft_flag, unknown
from ..context import EvalContext, ParcelRef

SRC_DVF = "DVF / valeurs foncières"
SRC_SITADEL = "SITADEL (autorisations d'urbanisme)"
SRC_POTENTIEL = "data.regionreunion.com — Potentiel foncier"
SRC_FF = "Fichiers fonciers (Cerema)"


def _quintile_points(em2: float, bornes: list[float], points: list[int]) -> tuple[int, int]:
    """Quintile-ÎLE du prix €/m² secteur → points (spec §4.2). Renvoie (points, n° de quintile 1..5)."""
    for i, b in enumerate(bornes):
        if em2 < float(b):
            return points[i], i + 1
    return points[-1], len(points)


@register
class DvfLayer(Layer):
    """Marché → QUALITÉ (spec v2 §4.2/4.3). Deux signaux Q + un flag L3 :
    - PRIX : quintile du €/m² secteur calculé À L'ÉCHELLE DE L'ÎLE (comparabilité multi-communes),
      bornes figées en config (méthode secteur-médian) → 0/+2/+4/+7/+10 (poids direct).
    - LIQUIDITÉ : nombre de mutations récentes dans le rayon → 0..+6 (courbe bornée).
    - ÉCOULEMENT (L3) : SDP résiduelle > seuil ET liquidité faible → flag « profondeur de marché à
      vérifier » (0 point : le risque d'absorption est réel mais son coût est inconnu sans étude).
    Le marché SORT de l'accessibilité (A = pur vendeur) — cf. matrice a_layers."""

    name = "dvf"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> list[Verdict]:
        if not ctx.table_has_commune("dvf_mutations", parcel.commune):
            return [unknown(self.name, "DVF non ingéré pour la commune.", source=SRC_DVF)]
        years = params.get("lookback_years", 5)
        liq_ref = float(params.get("liquidity_ref", 8))
        bornes = params.get("quintiles_ile_eur_m2", [976, 1553, 2249, 3407])
        pts = params.get("quintiles_points", [0, 2, 4, 7, 10])
        for radius in params.get("radii_m", [250, 500, 1000]):
            stats = ctx.dvf_stats(parcel.id, radius, years)
            if stats["count"] <= 0:
                continue
            count = stats["count"]
            em2 = stats.get("median_eur_m2")
            verdicts: list[Verdict] = []
            # PRIX (quintile île).
            if em2:
                p, qn = _quintile_points(float(em2), bornes, pts)
                em2_txt = f"{em2:,.0f} €/m²".replace(",", " ")
                verdicts.append(scored(
                    self.name, f"Prix secteur {em2_txt} — quintile île Q{qn}/5 (socle prix {p:+g}).",
                    p, source=SRC_DVF))
            # LIQUIDITÉ (dynamisme du marché).
            liq = max(0.0, min(1.0, count / liq_ref)) if liq_ref > 0 else 0.0
            if liq > 0:
                verdicts.append(positive(
                    self.name, f"Liquidité : {count} mutation(s) ≤ {radius} m / {years} ans.",
                    params.get("liquidity_bonus_key", "liquidite_dvf"), magnitude=liq, source=SRC_DVF))
            # ÉCOULEMENT (garde-fou L3) : grosse SDP dans un secteur peu liquide.
            r = ctx.residuel(parcel.id)
            sdp = r.get("sdp") if r else None
            if sdp is not None and float(sdp) > float(params.get("ecoulement_sdp_min_m2", 2000)) \
                    and count < int(params.get("ecoulement_liquidite_faible", 4)):
                verdicts.append(soft_flag(
                    self.name,
                    f"Profondeur de marché à vérifier : SDP {float(sdp):.0f} m² dans un secteur peu "
                    f"liquide ({count} mutation(s) / {years} ans) — risque d'écoulement, étude à prévoir.",
                    Severity.INFO, source=SRC_DVF))
            return verdicts or [passed(self.name, f"Marché : {count} mutation(s), sans signal.", source=SRC_DVF)]
        return [passed(self.name, "Aucune mutation DVF dans le rayon max.", source=SRC_DVF)]


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
        cov = max((i.coverage for i in ctx.intersections(parcel.id, kind)), default=0.0)
        if cov > 0:
            return positive(
                self.name,
                f"Dans un îlot « Potentiel foncier » Région — recouvrement {round(cov * 100)}% de la parcelle.",
                params.get("bonus_key", "potentiel_foncier_region"),
                magnitude=max(0.0, min(1.0, cov)), source=SRC_POTENTIEL,
            )
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
