"""Couches ÉTAGE 2 (dry-run) — ACCESSIBILITÉ : « peut-on l'acheter ? ».

- age_dirigeant (INPI) : POINTS (courbe par âge). Âge ABSENT → UNKNOWN (impacte la complétude,
  comme ABF), JAMAIS un malus ni un défaut silencieux (exigence Vic).
- bodacc (procédures collectives) : FLAG 0 point, machine à états sur les LIBELLÉS RÉELS
  (config, pas de valeur devinée). Seul l'état ROUGE (procédure ouverte/aggravée) pose
  evenement='rouge' → bascule « chaude » (étape 3), indépendamment des scores.
- dpe_passoire (DPE F/G maison) : FLAG 0 point « pression réglementaire datée ».

Tous les verdicts portent source_table/source_id (cliquable). Poids/seuils/mapping en config.
"""
from __future__ import annotations

from ...config import opportunity_weights
from ...enums import Severity
from ..base import Layer, Verdict, passed, positive, register, soft_flag, unknown
from ..context import EvalContext, ParcelRef

SRC_INPI = "INPI RNE (dirigeants)"
SRC_BODACC = "BODACC (procédures collectives)"
SRC_DPE = "DPE ADEME (logements existants)"


def _trace(v: Verdict, table: str, source_id, evenement: str | None = None) -> Verdict:
    v.extra = {"source_table": table, "source_id": source_id}
    if evenement:
        v.extra["evenement"] = evenement
    return v


@register
class AgeDirigeantLayer(Layer):
    name = "age_dirigeant"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        pr = ctx.propension(parcel.id)
        age = pr.get("age_max_dirigeant") if pr else None
        # ABSENCE (pas de PM, gigogne plafonnée, non-diffusible…) = « on ne sait pas » → UNKNOWN.
        if age is None:
            return unknown(self.name, "Âge dirigeant inconnu (PM sans dirigeant physique daté).", source=SRC_INPI)
        age = int(age)
        if age < int(params.get("age_min_valide", 18)):
            return unknown(self.name, f"Âge dirigeant {age} ans — fiche RNE incohérente, invalide.", source=SRC_INPI)
        courbe = params["courbe"]                          # {55:4, 65:8, 75:12, 85:14}
        pts = 0
        for seuil in sorted((int(k) for k in courbe), reverse=True):
            if age >= seuil:
                pts = courbe[seuil] if seuil in courbe else courbe[str(seuil)]
                break
        if pts == 0:
            return passed(self.name, f"Gérant {age} ans — pas de signal de transmission.", source=SRC_INPI)
        plafond = float(opportunity_weights()["bonuses"][params["bonus_key"]])
        mag = pts / plafond
        return _trace(positive(self.name, f"Gérant âgé ({age} ans) — horizon de transmission.",
                               params["bonus_key"], magnitude=mag, source=SRC_INPI),
                      "v_foncier_propension_vendre", pr.get("siren"))


@register
class BodaccLayer(Layer):
    name = "bodacc"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        b = ctx.bodacc(parcel.id)
        if not b or not b.get("type_procedure"):
            return passed(self.name, "Aucune procédure collective recensée.", source=SRC_BODACC)
        # Normalisation mojibake (double-encodage UTF-8) vers le libellé propre, PUIS classement.
        libelle = params.get("mojibake", {}).get(b["type_procedure"], b["type_procedure"])
        etat = "neutre"
        for e in ("rouge", "orange", "gris"):
            if libelle in (params["etats"].get(e) or []):
                etat = e
                break
        labels = {"rouge": "procédure collective OUVERTE", "orange": "sous plan (en cours)",
                  "gris": "procédure clôturée", "neutre": "publication procédurale"}
        detail = f"BODACC — {labels[etat]} : « {libelle} »."
        return _trace(soft_flag(self.name, detail, Severity.INFO, source=SRC_BODACC),  # ×0 : flag, pas de points
                      "v_foncier_sous_pression", b.get("siren"),
                      evenement="rouge" if etat == "rouge" else None)


@register
class DpePassoireLayer(Layer):
    name = "dpe_passoire"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        p = ctx.passoire(parcel.id)
        if not p:
            return passed(self.name, "Pas de passoire thermique F/G recensée.", source=SRC_DPE)
        et = p.get("etiquette_dpe")
        detail = (f"Passoire thermique (maison {et}) — pression réglementaire datée : "
                  f"gel des loyers depuis 07/2024, location interdite G en 2028 / F en 2034.")
        return _trace(soft_flag(self.name, detail, Severity.INFO, source=SRC_DPE),  # ×0 : flag d'accessibilité
                      "v_passoire_thermique", parcel.idu)
