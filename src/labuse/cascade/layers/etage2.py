"""Couches ÉTAGE 2 (dry-run) — ACCESSIBILITÉ : « peut-on l'acheter ? ».

- age_dirigeant (INPI) : POINTS (courbe par âge). Âge ABSENT → UNKNOWN (impacte la complétude,
  comme ABF), JAMAIS un malus ni un défaut silencieux (exigence Vic).
- bodacc (procédures collectives) : FLAG 0 point, machine à états sur les LIBELLÉS RÉELS
  (config, pas de valeur devinée). Seul l'état ROUGE (procédure ouverte/aggravée) pose
  evenement='rouge' → bascule « chaude » (étape 3), indépendamment des scores.

Tous les verdicts portent source_table/source_id (cliquable). Poids/seuils/mapping en config.
"""
from __future__ import annotations

from ...enums import Severity
from ..base import Layer, Verdict, passed, register, soft_flag, unknown
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
        # FIX-AGE-DIRIGEANT (décision Vic, I4 AUDIT-INTEGRATION-OUTILS) — l'âge du dirigeant N'ENTRE
        # PLUS dans le score : la cascade s'aligne sur le Score V (le backtest daté montre que le
        # dirigeant 70-75 ne vend quasiment jamais). L'information RESTE affichée comme CONTEXTE
        # (renseignée, NON scorante) : flag INFO à 0 point (Severity.INFO = ×0), jamais un `positive`.
        # Les bornes de `courbe` (toutes à 0) ne servent plus qu'à choisir le LIBELLÉ (« en activité »
        # vs « fin de carrière »). Le tag veille_succession du Score V est un autre moteur, non
        # concerné. Masquage RGPD (M70) inchangé : signal qualitatif, jamais le nombre exact.
        seuil_contexte = min(int(k) for k in params["courbe"])
        if age >= seuil_contexte:
            return _trace(soft_flag(self.name,
                          "Gérant proche de la retraite — information de contexte (n'entre pas dans le score).",
                          Severity.INFO, source=SRC_INPI),
                          "v_foncier_propension_vendre", pr.get("siren"))
        return passed(self.name, "Gérant en activité — pas de signal de transmission.", source=SRC_INPI)


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
