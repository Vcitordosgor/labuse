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
        # M91 (finding) — « un zéro n'est pas une absence » : une commune dont le DVF n'est PAS ingéré
        # est UNKNOWN (on n'a pas mesuré), jamais PASS (« aucune vente » affirmerait une mesure). M79
        # avait retiré ce garde en réécrivant le calcul ; restauré ici. Sans impact servi (DVF ingéré
        # pour les 24 communes → le garde ne se déclenche jamais en prod ; golden inchangé), mais
        # rétablit la distinction pour les bases partielles (démo) et le contrat du test.
        if not ctx.table_has_commune("dvf_mutations", parcel.commune):
            return unknown(self.name, "DVF non ingéré pour la commune.", source=SRC_DVF)
        # M79 — POINT DE CALCUL UNIQUE : prix médian de TERRAIN NU du SECTEUR cadastral
        # (dvf_secteur_medianes type='terrain'), JAMAIS un ratio bâti/foncier ni un rayon.
        # L'ancien €/m² « rayon, tous biens » comptait du bâti au m² de terrain (facteur ~2) —
        # supprimé (RAPPORT_M79). Échelle recalée sur la distribution TERRAIN île entière
        # (676 secteurs n≥3, p25=158/p75=323 → plo/phi = 150/325 ; PRE_VOL_ILE.md).
        liq_ref = float(params.get("liquidity_ref", 8))
        plo = float(params.get("price_lo_eur_m2", 150))
        phi = float(params.get("price_hi_eur_m2", 325))
        wl = float(params.get("w_liquidity", 0.5))
        wp = float(params.get("w_price", 0.5))
        n_floor = int(params.get("min_ventes_plancher", 3))    # < plancher → aucun prix affiché
        n_fiable = int(params.get("min_ventes_fiable", 5))     # [plancher, fiable) → prix + fragilité

        sec = ctx.dvf_sector_terrain(parcel.idu)
        if not sec or not sec.get("median_eur_m2"):
            return passed(self.name, "Prix terrain : aucune vente de terrain dans le secteur.", source=SRC_DVF)
        n = sec["n_ventes"]
        em2 = sec["median_eur_m2"]
        fen = sec.get("fenetre") or "période n/d"

        # Plancher dur : une médiane sur < 3 ventes n'est pas une médiane (RAPPORT_M79 Q6 : erreur
        # médiane > 55 % à n≤2). On DIT « échantillon insuffisant », jamais un chiffre présenté robuste.
        if n < n_floor:
            return passed(self.name,
                          f"Prix médian terrain : échantillon insuffisant ({n} vente(s) dans le secteur).",
                          source=SRC_DVF)

        # Libellé nommé : le client sait sur quoi porte la médiane sans ouvrir la doc. Entre plancher
        # et seuil fiable, le chiffre s'affiche AVEC sa mention de fragilité (jamais caché — Vic).
        fragile = "" if n >= n_fiable else " — échantillon fragile (~28 % d'erreur médiane)"
        detail = (f"Prix médian terrain {em2:,.0f} €/m² — {n} ventes, secteur cadastral, {fen}{fragile}."
                  .replace(",", " "))

        # magnitude = mélange borné liquidité (n ventes du secteur) + niveau de prix TERRAIN.
        liq = max(0.0, min(1.0, n / liq_ref)) if liq_ref > 0 else 0.0
        price = max(0.0, min(1.0, (em2 - plo) / (phi - plo))) if phi > plo else 0.0
        mag = max(0.0, min(1.0, wl * liq + wp * price))
        if mag > 0:
            return positive(self.name, detail + " Contexte de marché favorable.",
                            params.get("bonus_key", "contexte_dvf_favorable"), magnitude=mag, source=SRC_DVF)
        return passed(self.name, detail, source=SRC_DVF)


@register
class SitadelLayer(Layer):
    """Appariement SITADEL (§7bis) : rattaché par IDU vs signal de zone (rayon).

    LOT 8 (data-gap) — « dynamique constructive » GRADUÉE : le bonus de zone n'est plus
    binaire, sa magnitude = densité de PC dans le rayon (n / saturation_pc, plafonnée à 1) —
    avec 31 499 parcelles touchées sur Saint-Paul seul, un booléen ne discriminait plus rien.
    Fenêtre élargie 36 → 60 mois, rayon 200 → 400 m, PC seulement (config). Écart au mandat
    documenté : le bonus reste en Stage 2/A (où il vit depuis le Socle V1) plutôt que d'en
    créer un second en Stage 1 qui aurait DOUBLONNÉ le même signal — interdit par le lot."""

    name = "sitadel"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        if not ctx.table_has_commune("sitadel_permits", parcel.commune):
            return unknown(self.name, "SITADEL non ingéré pour la commune.", source=SRC_SITADEL)
        radius = params.get("radius_m", 200)
        months = params.get("lookback_months", 36)
        saturation = max(1, int(params.get("saturation_pc", 15)))
        res = ctx.sitadel_near(parcel.id, radius, months, types=params.get("types"))
        if res["matched_idu"] > 0:
            return positive(
                self.name,
                f"{res['matched_idu']} permis récent(s) RATTACHÉ(S) par IDU (≤ {months} mois).",
                params.get("bonus_key", "permis_sitadel_recent_proximite"),
                source=SRC_SITADEL,
            )
        if res["nearby"] > 0:
            mag = min(1.0, res["nearby"] / saturation)
            # ⚠ CONTRAT : le marqueur « SIGNAL DE ZONE » dans le détail est lu par
            # compute_matrice (dryrun.py) pour exclure ce bonus du test de franchissement
            # « chaude » (a_zone_layers, décision Vic 10/07/2026). Ne pas reformuler.
            return positive(
                self.name,
                f"Dynamique constructive : {res['nearby']} PC à ≤ {radius} m sur {months // 12} ans "
                f"(densité {round(100 * mag)} % du plafond {saturation}) — SIGNAL DE ZONE (§7bis).",
                params.get("bonus_key", "permis_sitadel_recent_proximite"),
                magnitude=mag,
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
