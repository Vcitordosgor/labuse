"""ÉTAGE 0 — extensions (mandat cascade île, 08/07/2026).

Trois couches découvertes ACTIVES à Saint-Paul (run q_v2) mais jamais committées — l'audit C4
a montré la cascade asymétrique. Ce module les GRAVE dans le code avec EXACTEMENT les règles
observées dans les 51 129 verdicts de Saint-Paul (détails, seuils, poids, kinds) — on étend,
on ne réinvente pas. Preuve : scripts/extend_cascade_ile.py rejoue Saint-Paul en diff ZÉRO.

1. foncier_public  — propriétaire public (DGFiP groupes 1/2/3/4/9) → HARD_EXCLUDE « exclue »
                     (domaine public : non acquérable).
2. emprise_lineaire — délaissé de voirie probable : enveloppe orientée, largeur < 8 m ET
                     allongement > 8× → HARD_EXCLUDE « faux_positif ».
3. residuel_socle  — socle de droits à construire (SDP résiduelle) : barème -25…+30 (poids
                     PROPRE, hors sévérités standard → extra["weight_override"]) ; hors
                     couverture = UNKNOWN honnête (jamais une exclusion).
"""
from __future__ import annotations

from typing import Any

from ..base import Layer, Verdict, hard_exclude, passed, positive, register, soft_flag, unknown
from ...enums import Severity

#: libellés DGFiP des groupes PUBLICS (classification personnes morales, vérifiée sur les
#: verdicts SP — le groupe 2 « Région » n'apparaît qu'une fois mais existe)
GROUPES_PUBLICS: dict[int, str] = {
    1: "État", 2: "Région", 3: "Département", 4: "Commune",
    9: "Établissements publics ou organismes associés",
}

#: barème residuel_socle (bornes SDP m² INCLUSIVES basses, extraites des 32 448 verdicts SP)
SOCLE_TIERS: list[tuple[float, int, str]] = [
    (5000, 30, "opération majeure"),
    (2000, 25, "belle opération"),
    (800, 15, "opération viable"),
    (300, 5, "petit collectif / 2–4 lots"),
    (100, -10, "une maison — hors cible collectif"),
    (0, -25, "rien à construire"),
]

LINEAIRE_LARGEUR_MAX_M = 8.0
LINEAIRE_ALLONGEMENT_MIN = 8.0


@register
class FoncierPublicLayer(Layer):
    """Domaine public — non acquérable (le signal que Vic voyait manquer : rues, écoles,
    parcelles communales classées « opportunités » hors Saint-Paul)."""

    name = "foncier_public"

    def evaluate(self, parcel, ctx, params: dict[str, Any]) -> Verdict:
        own = ctx.owner_pm(parcel.id)
        if not own:
            return passed(self.name, "Propriétaire non public (personne physique ou PM privée).")
        groupe = own.get("groupe")
        if groupe in GROUPES_PUBLICS:
            return hard_exclude(
                self.name,
                f"Propriété publique ({own.get('denomination')}) — non acquérable "
                f"[classification DGFiP groupe {groupe} : {GROUPES_PUBLICS[groupe]}].",
                kind="exclue")
        return passed(self.name,
                      f"Propriétaire PM « {own.get('groupe_label')} » (groupe {groupe}) — acquérable.")


@register
class EmpriseLineaireLayer(Layer):
    """Délaissé de voirie probable — enveloppe ORIENTÉE de la parcelle : largeur < 8 m ET
    allongement > 8× (seuils sur valeurs NON arrondies, affichage arrondi comme à SP)."""

    name = "emprise_lineaire"

    def evaluate(self, parcel, ctx, params: dict[str, Any]) -> Verdict:
        dims = ctx.oriented_envelope_dims(parcel.id)
        if not dims:
            return passed(self.name, "Forme non évaluable (géométrie dégénérée).")
        w, r = dims["largeur_m"], dims["allongement"]
        if w < LINEAIRE_LARGEUR_MAX_M and r > LINEAIRE_ALLONGEMENT_MIN:
            return hard_exclude(
                self.name,
                f"Emprise linéaire — voirie/délaissé probable (largeur {round(w)} m < 8 m "
                f"ET allongement {round(r)}× > 8×).",
                kind="faux_positif")
        return passed(self.name, f"Forme non linéaire (largeur {round(w)} m, allongement {round(r, 1)}×).")


@register
class ResiduelSocleLayer(Layer):
    """Socle « droits à construire » — la SDP résiduelle porte un barème PROPRE (-25…+30,
    extra["weight_override"]) ; hors couverture = UNKNOWN (complétude), JAMAIS une exclusion
    (vérifié à l'audit C4 : le doute « UNKNOWN écarté à tort » est réfuté par construction)."""

    name = "residuel_socle"

    def evaluate(self, parcel, ctx, params: dict[str, Any]) -> Verdict:
        sdp = ctx.residuel_sdp(parcel.id)
        if sdp is None:
            return unknown(self.name,
                           "SDP résiduelle non calculée — droits à construire inconnus (hors "
                           "couverture parcel_residuel) ; à résoudre par extension du calcul, "
                           "pas un signal d'absence de droits.")
        for seuil, socle, phrase in SOCLE_TIERS:
            if sdp >= seuil:
                detail = f"SDP résiduelle {round(sdp)} m² — {phrase} (socle {socle:+d})."
                if socle > 0:
                    v = positive(self.name, detail, bonus_key="residuel_socle",
                                 magnitude=socle / 30.0)
                else:
                    v = soft_flag(self.name, detail, Severity.INFO)
                    v.extra["weight_override"] = float(socle)
                v.data_source_name = None
                v.extra["source_table"] = "parcel_residuel"
                v.extra["source_id"] = str(parcel.id)
                return v
        return unknown(self.name, "SDP résiduelle négative — donnée à vérifier.")
