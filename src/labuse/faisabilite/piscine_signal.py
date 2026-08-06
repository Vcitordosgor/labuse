"""M39 — le signal « piscine détectée » comme RÈGLE PRODUIT (solde dette #13).

Point de calcul UNIQUE de la règle piscine : la fiche (vigilance informative) ET le geste de
bascule (`scripts/bascule_m39.py`) lisent ICI, jamais un seuil recopié. Config, jamais en dur :
`config/calibrage/piscine_signal.yaml` (bornes [15;60] justifiées par les faux positifs mesurés).

Doctrine (AUDIT4 train 5) : le filtre piscine est une RÈGLE, pas un poids de modèle. Périmètre
C1 (arbitrage Vic) : couche MATÉRIALISÉE seule (précision 90,7 %) ; le V0 colorimétrique seul est
exclu. Honnêteté millésime A1 : « détectée sur imagerie 2025 », jamais « récente » (un seul
millésime en base — datation infabricable). Voir qa/m39/M39_P0_CONSTAT.md.

Pur / testable / sans DB : `signal_actif()` ne dépend que de (surface, tier). La matérialisation
(`parcel_equipements.piscine`) est vérifiée par l'appelant qui lit la base.
"""
from __future__ import annotations

from ..config import load_yaml_config

_TIERS_DEFAUT = ("brulante", "chaude")


def _config() -> dict:
    """Charge la règle (mémo léger via lru non requis : lecture yaml peu fréquente)."""
    return load_yaml_config("calibrage/piscine_signal") or {}


def regle() -> dict:
    """Vue normalisée de la règle : seuils (absolus + part de parcelle), contenance, tiers, motif."""
    cfg = _config()
    seuil = cfg.get("seuil") or {}
    decl = cfg.get("declassement") or {}
    cont = cfg.get("contenance") or {}
    return {
        "surface_min_m2": float(seuil.get("surface_min_m2", 15)),
        "surface_max_m2": float(seuil.get("surface_max_m2", 60)),
        "pct_pool_parcelle_min": float(seuil.get("pct_pool_parcelle_min", 15.0)),
        "centroide_dans_requis": bool(cont.get("centroide_dans_parcelle", True)),
        "ratio_pool_dans_parcelle_min": float(cont.get("ratio_pool_dans_parcelle_min", 0.7)),
        "tiers_source": tuple(decl.get("tiers_source") or _TIERS_DEFAUT),
        "tier_cible": decl.get("tier_cible", "a_creuser"),
        "exige_materialisee": bool(decl.get("exige_materialisee", True)),
        "millesime": str(cfg.get("millesime", "2025")),
        "precision_pct": float(cfg.get("precision_pct", 90.7)),
        "motif_client": cfg.get("motif_client")
        or "Piscine détectée sur imagerie aérienne 2025 — usage du terrain à vérifier.",
    }


def dans_bande(surface_m2: float | None, r: dict | None = None) -> bool:
    """Vrai si la surface détectée tombe dans la bande absolue [min ; max]."""
    if surface_m2 is None:
        return False
    r = r or regle()
    return r["surface_min_m2"] <= float(surface_m2) <= r["surface_max_m2"]


def part_ok(surface_m2: float | None, parcel_surface_m2: float | None, r: dict | None = None) -> bool:
    """Vrai si la piscine occupe assez la parcelle (part ≥ seuil). Un signal négatif surfacique se
    juge en PART de parcelle, pas en surface absolue : la surface mesure l'objet, la part le blocage."""
    if not surface_m2 or not parcel_surface_m2:
        return False
    r = r or regle()
    return (100.0 * float(surface_m2) / float(parcel_surface_m2)) >= r["pct_pool_parcelle_min"]


def contenance_ok(ratio_dans: float | None, centroide_dans: bool | None, r: dict | None = None) -> bool:
    """Vrai si la piscine est bien DANS la parcelle servie (pas celle du voisin) : centroïde dans la
    parcelle ET part de la piscine dans la parcelle ≥ seuil. Le doute (piscine mitoyenne) ne
    déclasse pas."""
    r = r or regle()
    if r["centroide_dans_requis"] and not centroide_dans:
        return False
    if ratio_dans is None:
        return False
    return float(ratio_dans) >= r["ratio_pool_dans_parcelle_min"]


def signal_actif(surface_m2: float | None, tier: str | None, parcel_surface_m2: float | None = None,
                 ratio_dans: float | None = None, centroide_dans: bool | None = None,
                 r: dict | None = None) -> bool:
    """Vrai si le signal piscine DÉCLASSE ce tier — les 3 critères figés (seuil Vic) :
    tier haut · surface en bande [15;60] · part de parcelle ≥ 15 % · contenance (centroïde dans +
    ratio ≥ 0,7). Données spatiales manquantes → False (le doute ne profite pas au déclassement).
    Pur, sans DB : l'appelant fournit surface parcelle, ratio et centroïde (calculés en base)."""
    r = r or regle()
    return (tier in r["tiers_source"]
            and dans_bande(surface_m2, r)
            and part_ok(surface_m2, parcel_surface_m2, r)
            and contenance_ok(ratio_dans, centroide_dans, r))


def vigilance_texte(r: dict | None = None) -> str:
    """Texte de vigilance fiche (informatif) — Sourcé + précision assumée, jamais « certifiée »."""
    r = r or regle()
    return (f"{r['motif_client']} Détection ortho IGN {r['millesime']}, "
            f"fiabilité ~{r['precision_pct']:.1f} % (statistique, non contractuelle).")
