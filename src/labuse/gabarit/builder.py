"""Raccordement UNIQUE des vraies données → `GabaritInput` (CDC §11).

C'est le SEUL endroit où le réel entre. `compute_gabarit` reste pur : il ne sait pas
si l'entrée vient d'ici ou d'une fixture. Correspondances (CDC §11) :
  cadastre → parcel · PLU (zonage.py) → setbacks/maxFootprint/maxHeight ·
  PPR (cascade_results + spatial_layers) → exclusions · analyse documentaire →
  applicableRules · dossier documentaire → sources.

⚠ GABARIT-1 : la **classification des limites** (voie/séparative par arête) échoue le
seuil de mesure (cf. A0-RAPPORT.md) → elle est **différée à GABARIT-2**. Le builder
assemble donc tout le réel SAUF les `setbacks` géométriques ; sur une parcelle réelle
le moteur renvoie honnêtement « Calcul incomplet ». Aucune réécriture du moteur/carte/
panneau/3D ne sera nécessaire pour brancher la classification (il suffira de remplir
`setbacks`).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..faisabilite.zonage import resolve_zone
from ..faisabilite.zone_servie import zone_dominante
from .contract import (
    ApplicableRule,
    GabaritInput,
    MaxFootprint,
    MaxHeight,
    ParcelInput,
    RegulatorySource,
)

CADASTRE_PROVIDER = "DGFiP — cadastre (PCI)"
PLU_PROVIDER = "LABUSE — règlement PLU validé (config/plu_destinations)"
PPR_PROVIDER = "DEAL Réunion — PPR (zonage réglementaire)"
# différé : la classification servie devra porter cette source (mesure, pas supposition)
CLASSIF_PROVIDER = "LABUSE — adjacence cadastre + BD TOPO voirie"


@dataclass
class BuildResult:
    input: GabaritInput
    blocking: list[str] = field(default_factory=list)
    raccordement: dict = field(default_factory=dict)


def _num(x) -> Optional[float]:
    """float réel uniquement (None = silence ; 'a_verifier' = ambigu → écarté)."""
    return float(x) if isinstance(x, (int, float)) else None


def build_gabarit_input(session: Session, idu: str) -> Optional[BuildResult]:
    """Assemble l'entrée réelle. Renvoie None si la parcelle est inconnue.
    `BuildResult.blocking` liste les données réglementaires nécessaires manquantes."""
    row = session.execute(text(
        "SELECT id, commune, ST_Area(geom_2975) AS surface_m2, "
        "ST_AsGeoJSON(geom) AS geojson FROM parcels WHERE idu = :i"
    ), {"i": idu}).mappings().first()
    if not row:
        return None
    pid, commune = row["id"], row["commune"]
    surface = float(row["surface_m2"]) if row["surface_m2"] is not None else None
    geom = json.loads(row["geojson"]) if row["geojson"] else None

    blocking: list[str] = []
    racc: dict = {"parcelle": {"idu": idu, "commune": commune,
                              "surface_m2": round(surface, 1) if surface else None}}

    cadastre_src = RegulatorySource(document="Cadastre — parcelle " + idu,
                                    provider=CADASTRE_PROVIDER)
    sources = [cadastre_src]
    applicable: list[ApplicableRule] = []
    max_footprint: Optional[MaxFootprint] = None
    max_height: Optional[MaxHeight] = None

    # --- zone dominante + multi-zones ----------------------------------------
    zs = zone_dominante(session, pid)
    racc["zone"] = {"code": zs.zone, "famille": zs.zone_fam, "a_cheval": zs.a_cheval}
    if zs.a_cheval:
        blocking.append("parcelle à cheval sur ≥ 2 zones PLU : règle non unique (bloquant GABARIT-1)")
    if not zs.zone:
        blocking.append("zone PLU indéterminée")

    # --- règles PLU via zonage.py (validées-only ; propose = bloquant) --------
    if zs.zone:
        zr = resolve_zone(zs.zone, commune)
        if zr is None:
            blocking.append(f"zone {zs.zone} hors calibrage PLU")
        elif getattr(zr, "regle_non_validee", None):
            blocking.append(f"règle PLU non validée (propose) : {zr.regle_non_validee}")
        elif not getattr(zr, "calibree", False):
            blocking.append(f"PLU non calibré pour la zone {zs.zone} (estimation générique)")
        else:
            plu_zone_src = RegulatorySource(document=f"PLU — {commune}", zone=zs.zone,
                                            provider=PLU_PROVIDER)
            sources.append(plu_zone_src)
            emp = _num(getattr(zr, "emprise_sol_pct", None))
            haut = _num(getattr(zr, "hf_m", None))  # faîtage : sert l'extrusion 3D
            egout = _num(getattr(zr, "he_m", None))
            recul_voie = _num(getattr(zr, "recul_voirie_m", None))
            recul_sep = _num(getattr(zr, "recul_limites_sep_m", None))
            racc["plu"] = {"emprise_pct": emp, "hauteur_faitage_m": haut,
                           "hauteur_egout_m": egout, "recul_voie_m": recul_voie,
                           "recul_sep_m": recul_sep, "source": plu_zone_src.document}
            if emp is not None:
                max_footprint = MaxFootprint(ruleId=f"{zs.zone}-emprise", percent=emp,
                                             source=plu_zone_src)
                applicable.append(ApplicableRule(id=f"{zs.zone}-emprise", label="Emprise maximale",
                                                 category="maxFootprint", integrationStatus="integrated",
                                                 detail=f"{emp:g} %", source=plu_zone_src))
            else:
                blocking.append("emprise (CES) non réglementée / non validée")
            if haut is not None:
                max_height = MaxHeight(ruleId=f"{zs.zone}-hauteur", meters=haut, source=plu_zone_src)
                applicable.append(ApplicableRule(id=f"{zs.zone}-hauteur", label="Hauteur maximale",
                                                 category="maxHeight", integrationStatus="integrated",
                                                 detail=f"{haut:g} m", source=plu_zone_src))
            else:
                blocking.append("hauteur réglementaire non validée")
            # les reculs sont RÉELS mais leur application par arête exige la classification (GABARIT-2)
            if recul_voie is not None:
                applicable.append(ApplicableRule(id=f"{zs.zone}-recul-voie", label="Recul voie",
                                                 category="setback", integrationStatus="integrated",
                                                 detail=f"{recul_voie:g} m", source=plu_zone_src))
            if recul_sep is not None:
                applicable.append(ApplicableRule(id=f"{zs.zone}-recul-sep", label="Limites séparatives",
                                                 category="setback", integrationStatus="integrated",
                                                 detail=f"{recul_sep:g} m", source=plu_zone_src))
            # règles connues mais non chiffrées dans LABUSE
            applicable.append(ApplicableRule(id="STAT", label="Stationnement", category="other",
                                             integrationStatus="not_integrated",
                                             detail="Règle connue, non chiffrée", source=plu_zone_src))
            applicable.append(ApplicableRule(id="ESP", label="Espaces libres", category="other",
                                             integrationStatus="not_integrated",
                                             detail="Règle connue, non chiffrée", source=plu_zone_src))

    # --- risques : PPR zone rouge (réglementaire, per-parcelle) ---------------
    ppr = session.execute(text(
        "SELECT result, severity, detail FROM cascade_results "
        "WHERE parcel_id = :pid AND layer_name = 'risques' "
        "ORDER BY (result = 'HARD_EXCLUDE') DESC LIMIT 1"
    ), {"pid": pid}).mappings().first()
    ppr_src = RegulatorySource(document="PPR — zonage réglementaire", provider=PPR_PROVIDER)
    ppr_rouge = bool(ppr and ppr["result"] == "HARD_EXCLUDE" and "PPR zone rouge" in (ppr["detail"] or ""))
    racc["ppr"] = {"result": ppr["result"] if ppr else None,
                   "detail": ppr["detail"] if ppr else None, "rouge": ppr_rouge}
    sources.append(ppr_src)
    # analyse des risques TOUJOURS présente et sourcée (jamais déduite d'un tableau vide)
    applicable.append(ApplicableRule(
        id="PPR", label="PPR — analyse", category="exclusion",
        integrationStatus="integrated" if ppr_rouge else "not_integrated",
        detail=(ppr["detail"] if ppr else "Aucune zone rouge PPR sur la parcelle"),
        source=ppr_src))

    # --- classification des limites : différée (GABARIT-2) --------------------
    blocking.append("classification des limites non servie — voie/séparative par arête "
                    "(différé à GABARIT-2, cf. A0-RAPPORT.md)")
    racc["differe"] = ["classification_limites (setbacks géométriques) → GABARIT-2"]
    racc["classification_provider_prevu"] = CLASSIF_PROVIDER

    inp = GabaritInput(
        parcel=ParcelInput(id=idu, geometry=geom, areaM2=round(surface, 1) if surface else None,
                           source=cadastre_src),
        setbacks=[],  # ⚠ vide en GABARIT-1 (classification différée)
        maxFootprint=max_footprint,
        maxHeight=max_height,
        exclusions=[],  # PPR rouge réel connu (racc["ppr"]) mais non soustrait sans zone servie
        applicableRules=applicable,
        sources=sources,
    )
    return BuildResult(input=inp, blocking=blocking, raccordement=racc)
