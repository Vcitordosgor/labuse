"""Contrat d'entrée/sortie unique du Gabarit réglementaire (CDC §2).

Toutes les données — fictives ou réelles — passent par `GabaritInput`. Les champs
sont volontairement optionnels au niveau du type pour représenter un chargement
INCOMPLET ; la rigueur est portée par `validate.py` AVANT tout calcul. Les noms de
champs reprennent EXACTEMENT le contrat du CDC (camelCase) pour que le JSON servi
soit identique côté front.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# GeoJSON transporté tel quel (dict). La forme est vérifiée par validate.py + shapely.
GeoJSON = dict[str, Any]


class RegulatorySource(BaseModel):
    """Provenance réglementaire. `document` non vide est le minimum (CDC §2)."""

    model_config = ConfigDict(extra="forbid")
    document: Optional[str] = None
    zone: Optional[str] = None
    article: Optional[str] = None
    versionDate: Optional[str] = None
    provider: Optional[str] = None


class ParcelInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Optional[str] = None
    geometry: Optional[GeoJSON] = None
    areaM2: Optional[float] = None
    source: Optional[RegulatorySource] = None


class Setback(BaseModel):
    """Un recul associé à une limite classée (voie / séparative latérale / fond)."""

    model_config = ConfigDict(extra="forbid")
    id: Optional[str] = None
    ruleId: Optional[str] = None
    type: Optional[Literal["road", "side", "rear"]] = None
    geometry: Optional[GeoJSON] = None  # LineString (la limite)
    setbackM: Optional[float] = None
    source: Optional[RegulatorySource] = None


class MaxFootprint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ruleId: Optional[str] = None
    percent: Optional[float] = None
    status: Optional[Literal["integrated", "absent"]] = None   # 'absent' = silence prouvé du règlement
    source: Optional[RegulatorySource] = None


class MaxHeight(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ruleId: Optional[str] = None
    meters: Optional[float] = None
    status: Optional[Literal["integrated", "not_integrated"]] = None   # 'not_integrated' = forme non chiffrée (prospect)
    # GABARIT-6 — `meters` porte le FAÎTAGE quand la zone en fixe un, sinon l'ÉGOUT. `basis` dit lequel
    # (jamais un faîtage implicite) ; `egoutMeters` = l'égout quand la règle distingue les deux (sous-ligne).
    basis: Optional[Literal["faitage", "egout"]] = None
    egoutMeters: Optional[float] = None
    source: Optional[RegulatorySource] = None
    # RECETTE-PROD-1 (A7) — hauteur ESTIMÉE : zone à enveloppe calibrée dont la hauteur est une table
    # graphique par secteur (non chiffrable en valeur unique). La valeur est SERVIE et UTILISÉE (volume),
    # mais étiquetée « Estimé » à l'écran et dans les PDF (jamais présentée comme la valeur validée).
    estimee: bool = False


class Exclusion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Optional[str] = None
    ruleId: Optional[str] = None
    type: Optional[str] = None
    label: Optional[str] = None
    geometry: Optional[GeoJSON] = None  # Polygon
    source: Optional[RegulatorySource] = None


RuleCategory = Literal["setback", "maxFootprint", "maxHeight", "exclusion", "other"]


class ApplicableRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Optional[str] = None
    label: Optional[str] = None
    category: Optional[RuleCategory] = None
    integrationStatus: Optional[Literal["integrated", "not_integrated"]] = None
    detail: Optional[str] = None
    source: Optional[RegulatorySource] = None


class GabaritInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parcel: Optional[ParcelInput] = None
    setbacks: list[Setback] = Field(default_factory=list)
    maxFootprint: Optional[MaxFootprint] = None
    maxHeight: Optional[MaxHeight] = None
    exclusions: list[Exclusion] = Field(default_factory=list)
    applicableRules: list[ApplicableRule] = Field(default_factory=list)
    sources: list[RegulatorySource] = Field(default_factory=list)


# ----------------------------------------------------------------------------- sortie


class AppliedRule(BaseModel):
    """Règle EFFECTIVEMENT appliquée, regroupée par (ruleId, valeur, source)."""

    ruleId: str
    category: RuleCategory
    label: str
    value: Optional[float] = None
    unit: Optional[str] = None
    detail: Optional[str] = None
    source: RegulatorySource


class NonIntegratedRule(BaseModel):
    id: Optional[str] = None
    label: str
    detail: Optional[str] = None    # GABARIT-6 — pourquoi non intégrée (souvent avec la citation PLU)
    source: RegulatorySource


class Coverage(BaseModel):
    """Les QUATRE familles de couverture réglementaire (CDC §6). Pas un compte de
    segments ni d'articles PLU."""

    reculs: bool
    hauteur: bool
    emprise: bool
    risques: bool

    @property
    def familles_verifiees(self) -> int:
        return sum((self.reculs, self.hauteur, self.emprise, self.risques))


class GabaritResult(BaseModel):
    """Résultat du moteur. Aucun champ estimatif (logements/étages/sdp/coût/valeur/
    potentiel) — liste noire testée."""

    status: Literal["ok", "incomplete"]
    message: Optional[str] = None
    validationErrors: list[str] = Field(default_factory=list)
    # provenance/diagnostic du raccordement réel (jamais estimatif) — prouve d'où
    # viennent les données réelles et ce qui est différé (ex. classification GABARIT-2)
    raccordement: Optional[dict[str, Any]] = None

    # présents seulement si status == "ok"
    surfaceParcelleM2: Optional[float] = None
    zoneImplantationM2: Optional[float] = None
    # RECETTE-OUTILS-3 (S7, décision Vic) — la zone d'implantation DÉDUIT l'emprise du bâti existant
    # conservé : `zoneImplantationM2` est la valeur APRÈS déduction, `batiDeduitM2` l'emprise retranchée
    # (m²). None si pas de bâti à déduire. Appliqué au service (app + PDF lisent la même géométrie).
    batiDeduitM2: Optional[float] = None
    # FRONT-CHIFFRES-2 (F57/F50) — % de la parcelle dans la zone dominante quand elle est « à cheval »
    # (round(portion / cadastre × 100)), calculé UNE fois au service. Deux sites front (GabaritLine +
    # panneau Gabarit) le recomputaient à l'identique → divergence possible ; ils lisent ce champ. None si non « à cheval ».
    pctPortionZone: Optional[int] = None
    # CHASSE-DOCS-FIX-1 (Lot 5) — sur parcelle à cheval, la surface servie EST la contenance cadastrale ;
    # cette note dit la part en zone constructible (« dont ~X m² en zone Ud »). None hors à-cheval.
    surfaceNote: Optional[str] = None
    plafondEmpriseM2: Optional[float] = None
    plafondEmpriseStatus: Optional[str] = None   # 'absent' → « Non réglementé » (silence prouvé)
    hauteurReglementaireM: Optional[float] = None
    hauteurSource: Optional[RegulatorySource] = None
    hauteurStatus: Optional[str] = None          # 'not_integrated' → « Non chiffrée » (prospect)
    hauteurBase: Optional[str] = None            # 'faitage' | 'egout' — ce que porte hauteurReglementaireM
    hauteurEstimee: bool = False                 # RECETTE-PROD-1 (A7) — hauteur issue d'une table graphique
    #   par secteur → valeur ESTIMÉE (étiquette « Estimé » à l'écran et dans les PDF)
    hauteurEgoutM: Optional[float] = None        # égout, en sous-ligne, quand la règle distingue faîtage/égout
    # CHASSE-CALCULS-FIX-1 Lot 6 (E-C1) — l'extrusion 3D est posée À PLAT (le relief n'entre pas dans
    # le volume) : on le DIT quand une hauteur permet un 3D. `terrainNote` est affichée en mode 3D.
    terrainNote: Optional[str] = None

    coverage: Optional[Coverage] = None
    appliedRules: list[AppliedRule] = Field(default_factory=list)
    nonIntegratedRules: list[NonIntegratedRule] = Field(default_factory=list)

    # géométries pour la carte (GeoJSON 4326) — seulement après validation réussie
    contourGeoJSON: Optional[GeoJSON] = None
    zoneImplantationGeoJSON: Optional[GeoJSON] = None
    retraitsGeoJSON: Optional[GeoJSON] = None
    exclusionsGeoJSON: Optional[GeoJSON] = None
    # GABARIT-6 P4 — bâti EXISTANT (emprise BD TOPO + hauteur LiDAR HD), FAIT contextuel : aucun calcul
    # réglementaire n'en dépend. FeatureCollection (4326), une Feature par bâtiment, propriétés
    # { hauteur_m, h_source: 'lidar'|'bdtopo' }. None si la parcelle ne porte aucun bâti.
    batiExistantGeoJSON: Optional[GeoJSON] = None
