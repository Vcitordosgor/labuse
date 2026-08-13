"""Couches ÉTAGE 2 (dry-run) — ACCESSIBILITÉ : « peut-on l'acheter ? ».

- age_dirigeant (INPI) : POINTS (courbe par âge). Âge ABSENT → UNKNOWN (impacte la complétude,
  comme ABF), JAMAIS un malus ni un défaut silencieux (exigence Vic).
- bodacc (procédures collectives) : FLAG 0 point, machine à états sur les LIBELLÉS RÉELS
  (config, pas de valeur devinée). Seul l'état ROUGE (procédure ouverte/aggravée) pose
  evenement='rouge' → bascule « chaude » (étape 3), indépendamment des scores.

Tous les verdicts portent source_table/source_id (cliquable). Poids/seuils/mapping en config.
"""
from __future__ import annotations

from ...config import opportunity_weights
from ...enums import Severity
from ..base import Layer, Verdict, passed, positive, register, soft_flag, unknown
from ..context import EvalContext, ParcelRef

SRC_INPI = "INPI RNE (dirigeants)"
SRC_BODACC = "BODACC (procédures collectives)"


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
        # M70 décision 7 (réserve RGPD P2-34) — le stockage garde l'âge, mais l'AFFICHAGE n'expose
        # plus le nombre exact d'un dirigeant nommé-adjacent : le signal qualitatif suffit. Le score
        # (pts, magnitude) reste calculé sur l'âge réel — seul le libellé change.
        if age < int(params.get("age_min_valide", 18)):
            return unknown(self.name, "Âge dirigeant hors plage plausible — fiche RNE incohérente, invalide.", source=SRC_INPI)
        courbe = params["courbe"]                          # {55:4, 65:8, 75:12, 85:14}
        pts = 0
        for seuil in sorted((int(k) for k in courbe), reverse=True):
            if age >= seuil:
                pts = courbe[seuil] if seuil in courbe else courbe[str(seuil)]
                break
        if pts == 0:
            return passed(self.name, "Gérant en activité — pas de signal de transmission.", source=SRC_INPI)
        plafond = float(opportunity_weights()["bonuses"][params["bonus_key"]])
        mag = pts / plafond
        return _trace(positive(self.name, "Gérant proche de la retraite — horizon de transmission.",
                               params["bonus_key"], magnitude=mag, source=SRC_INPI),
                      "v_foncier_propension_vendre", pr.get("siren"))


@register
class BodaccLayer(Layer):
    name = "bodacc"

    def evaluate(self, parcel: ParcelRef, ctx: EvalContext, params: dict) -> Verdict:
        b = ctx.bodacc(parcel.id)
        if not b or not b.get("type_procedure"):
            # M70 décision 3 — plus d'affirmation nue « aucune procédure ». On consulte le journal
            # de sondage (M71-D) : « sondé le X → rien » (fait), sinon « sondage non concluant »
            # (jamais présumer l'absence quand le siren n'a pas été sondé / n'est pas sondable).
            s = ctx.bodacc_sondage(parcel.id)
            if not s or not s.get("siren"):
                return passed(self.name, "BODACC sans objet — propriétaire non personne morale.", source=SRC_BODACC)
            res = s.get("resultat")
            if res == "rien":
                d = s["sonde_le"].strftime("%d/%m/%Y") if s.get("sonde_le") else "récemment"
                return passed(self.name, f"Aucune procédure collective — propriétaire sondé le {d}.", source=SRC_BODACC)
            return unknown(self.name, "Sondage BODACC non concluant (propriétaire non sondé ou non sondable).", source=SRC_BODACC)
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


# M71 B1 (audits M66/M66-B) : DpePassoireLayer RETIRÉE du scoring — 13 DPE utiles pour
# 431 663 parcelles ne portent pas un signal (l'amont réunionnais authentique ≈ 17 DPE,
# le DPE réglementaire étant neuf en DROM). La donnée reste servie en INFO FICHE seule
# (« DPE connu : … ») depuis dpe_records — jamais en signal de scoring.
