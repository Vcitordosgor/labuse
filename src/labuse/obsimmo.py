"""Indicateurs de marché Obsimmo — VENTE (LOT 4, option C).

Dataset STATIQUE fourni par le client (extraction manuelle du 2026-06-19) de l'Observatoire de
l'Immobilier Réunionnais® : 78 lignes = 26 secteurs Obsimmo × 3 typologies (appartements /
maisons / terrains constructibles), en VENTE uniquement. Aucune donnée n'est inventée ici : ce
module se contente de charger, indexer et exposer le fichier `data/obsimmo_vente_reunion.json`,
puis d'en dériver un `market_signal` TRANSPARENT (composantes affichées, jamais une valeur
officielle ni notariale).

Règles de fiabilité NON NÉGOCIABLES (cf. brief) :
  • `None` = NS (non significatif / non renseigné) — JAMAIS transformé en 0, jamais moyenné.
  • `active_listings_count` est toujours un entier ; 0 est un vrai zéro (0 bien en vente).
  • les lignes porteuses de `notes` (anomalies Obsimmo) sont à interpréter avec prudence.
  • ces chiffres sont un INDICATEUR de marché Obsimmo, pas une estimation officielle.

Le `market_signal` est un sous-score SÉPARÉ et faiblement pondéré : il n'écrase jamais les
contraintes foncières réelles (PLU, zonage, PPR, accès, pente, servitudes…) et n'est volontairement
PAS injecté dans l'opportunity_score / la shortlist. Commune-agnostique : une commune absente du
dataset renvoie None (on ne fabrique aucun marché).
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

# ── Typage strict (échelles telles qu'affichées par Obsimmo) ──────────────────────────────
PROPERTY_TYPES: tuple[str, ...] = ("appartements", "maisons", "terrains_constructibles")
REGIONS: frozenset[str] = frozenset(
    {"Réunion Ouest", "Réunion Sud", "Réunion Est", "Réunion Nord"}
)
# Pour le foncier (cœur de LA BUSE), la typologie pertinente par défaut est le terrain.
DEFAULT_PROPERTY_TYPE = "terrains_constructibles"

# Échelles qualitatives ORDINALES d'Obsimmo (reprises telles quelles, pas inventées).
_OFFER_SCALE = {"Très faible": 0, "Faible": 1, "Forte": 2, "Très forte": 3}
_OPACITY_SCALE = {"Faible": 0, "Forte": 1, "Très forte": 2}

# Champs numériques : on ne les coerce jamais (None reste None).
_LOCAL_NUM = (
    "local_avg_price_eur", "local_price_m2_min", "local_price_m2_max",
    "local_avg_sale_delay_weeks",
)
_REGIONAL_FIELDS = (
    "regional_avg_price_eur", "regional_price_m2_min", "regional_price_m2_max",
    "regional_avg_sale_delay_weeks", "regional_opacity", "regional_market_share_pct",
    "regional_core_price_segment",
)

_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "obsimmo_vente_reunion.json"

SOURCE: dict[str, str] = {
    "nom": "Observatoire de l'Immobilier Réunionnais®",
    "perimetre": "Vente",
    "extraction": "2026-06-19",
    "provenance": "sourcee",
    "mention": ("Source : Obsimmo / Observatoire de l'Immobilier Réunionnais — données de "
                "marché vente, extraction manuelle 2026-06-19."),
}


def _norm(s: str | None) -> str:
    """Clé de rapprochement tolérante aux accents/casse/séparateurs (« Saint-Paul » == « SAINT PAUL »)."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s.lower() if c.isalnum())


@lru_cache(maxsize=1)
def load() -> list[dict[str, Any]]:
    """Charge le dataset Obsimmo (idempotent + caché). Liste vide si le fichier manque/illisible.

    On ne coerce rien : `json.load` préserve nativement `null`→None et les entiers/flottants.
    """
    try:
        rows = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return rows if isinstance(rows, list) else []


@lru_cache(maxsize=1)
def _index() -> dict[str, dict[tuple[str, str], dict[str, Any]]]:
    """Index (secteur|parent_commune|région, typologie) → ligne, sur clés normalisées."""
    by_sector: dict[tuple[str, str], dict[str, Any]] = {}
    by_parent: dict[tuple[str, str], dict[str, Any]] = {}
    by_region: dict[tuple[str, str], dict[str, Any]] = {}
    for r in load():
        pt = r.get("property_type")
        by_sector[(_norm(r.get("sector")), pt)] = r
        # parent_commune : on PRIVILÉGIE la ligne du secteur « chef-lieu » (sector == parent),
        # sinon la première rencontrée (fallback déterministe car le JSON est ordonné).
        kp = (_norm(r.get("parent_commune")), pt)
        if kp not in by_parent or _norm(r.get("sector")) == _norm(r.get("parent_commune")):
            by_parent[kp] = r
        by_region.setdefault((_norm(r.get("obsimmo_region")), pt), r)
    return {"sector": by_sector, "parent": by_parent, "region": by_region}


# ── Helpers de lecture ────────────────────────────────────────────────────────────────────
def get_market(sector_or_commune: str, property_type: str) -> dict[str, Any] | None:
    """Marché local d'un secteur Obsimmo ; à défaut, repli sur la commune de rattachement."""
    if property_type not in PROPERTY_TYPES:
        return None
    idx = _index()
    key = (_norm(sector_or_commune), property_type)
    row = idx["sector"].get(key) or idx["parent"].get(key)
    return dict(row) if row else None


def get_market_by_parent_commune(parent_commune: str, property_type: str) -> dict[str, Any] | None:
    """Marché de la commune administrative (ligne « chef-lieu » privilégiée)."""
    if property_type not in PROPERTY_TYPES:
        return None
    row = _index()["parent"].get((_norm(parent_commune), property_type))
    return dict(row) if row else None


def get_regional_market(obsimmo_region: str, property_type: str) -> dict[str, Any] | None:
    """Bloc régional (constant sur tous les secteurs d'une même région/typologie)."""
    if property_type not in PROPERTY_TYPES:
        return None
    row = _index()["region"].get((_norm(obsimmo_region), property_type))
    if not row:
        return None
    out: dict[str, Any] = {"obsimmo_region": row.get("obsimmo_region"), "property_type": property_type}
    out.update({f: row.get(f) for f in _REGIONAL_FIELDS})
    return out


def local_disponible(row: dict[str, Any] | None) -> bool:
    """True si Obsimmo affiche un marché LOCAL significatif (≠ NS).

    On se cale sur l'indicateur de tête d'Obsimmo : le prix moyen local. Quand il est NS,
    Obsimmo considère le marché local non significatif — même s'il reste un niveau d'offre ou
    1 bien en vente (cf. Le Port / terrains, explicitement noté NS). On ne fabrique alors rien.
    """
    return bool(row) and row.get("local_avg_price_eur") is not None


# ── Sous-score « market_signal » : SÉPARÉ, transparent, faiblement pondéré ───────────────────
def market_signal(row: dict[str, Any] | None) -> dict[str, Any]:
    """Signal de marché Obsimmo, DÉRIVÉ et transparent (jamais injecté dans le scoring foncier).

    Construit à partir de deux composantes lisibles, ancrées sur les chiffres du dataset :
      • Liquidité = délai de vente LOCAL comparé au délai RÉGIONAL (vendre plus vite = favorable).
      • Offre concurrente = niveau d'offre Obsimmo (peu d'offre = moins de concurrence à la revente).
    L'opacité Obsimmo ne joue PAS sur le sens du score mais sur sa FIABILITÉ. Score nul (None) si
    le local est NS : on ne fabrique aucun signal à partir d'une donnée manquante.
    """
    if not local_disponible(row):
        return {"disponible": False,
                "note": "Marché local affiché en NS sur Obsimmo — aucun signal calculé."}
    assert row is not None
    composantes: list[dict[str, str]] = []
    score = 50  # référence neutre, ajustée par composante, bornée 0–100

    # 1) Liquidité relative (numérique, pur calcul sur le dataset).
    ld, rd = row.get("local_avg_sale_delay_weeks"), row.get("regional_avg_sale_delay_weeks")
    if ld is not None and rd:
        ecart = (rd - ld) / rd  # >0 : vend plus vite que la région
        score += round(max(-1.0, min(1.0, ecart)) * 25)
        sens = "+" if ld < rd else "−" if ld > rd else "="
        loc_s, reg_s = f"{ld:g}".replace(".", ","), f"{rd:g}".replace(".", ",")  # décimal FR
        composantes.append({
            "cle": "Liquidité",
            "valeur": f"{loc_s} sem. local vs {reg_s} sem. région",
            "sens": sens,
        })

    # 2) Offre concurrente (catégoriel Obsimmo) — peu d'offre = léger plus pour une revente.
    off = row.get("local_offer_level")
    if off in _OFFER_SCALE:
        score += {0: 12, 1: 6, 2: -6, 3: -12}[_OFFER_SCALE[off]]
        composantes.append({
            "cle": "Offre concurrente",
            "valeur": off,
            "sens": "+" if _OFFER_SCALE[off] <= 1 else "−",
        })

    if not composantes:  # prix présent mais ni délai ni offre → rien d'assez solide à signaler
        return {"disponible": False,
                "note": "Données locales insuffisantes pour un signal de marché."}

    score = max(0, min(100, score))
    label = "favorable" if score >= 60 else "prudence" if score < 40 else "neutre"

    # Fiabilité : pilotée par l'opacité Obsimmo et la présence d'une note d'anomalie.
    opac = row.get("local_opacity")
    fiab = {0: "bonne", 1: "moyenne", 2: "faible"}.get(_OPACITY_SCALE.get(opac, 2), "faible")
    if row.get("notes"):
        fiab = "faible"

    return {
        "disponible": True,
        "score": score,
        "label": label,
        "composantes": composantes,
        "fiabilite": fiab,
        "note": ("Indicateur de marché Obsimmo (vente), non contraignant — il ne remplace pas les "
                 "contraintes foncières (PLU, zonage, PPR, accès, pente, servitudes)."),
    }


# ── Bloc fiche « Marché Obsimmo » ───────────────────────────────────────────────────────────
def fiche_block(commune: str, sector: str | None = None) -> dict[str, Any] | None:
    """Bloc marché pour la fiche d'une parcelle (None si commune/secteur hors dataset).

    Priorise les `terrains_constructibles` (cœur foncier) ; joint appartements & maisons pour le
    contexte, la comparaison régionale et le signal dérivé. `sector` permet de cibler un secteur
    Obsimmo fin (ex. Saint-Gilles-les-Bains) ; à défaut on retombe sur la commune.
    """
    cible = sector or commune
    principal = get_market(cible, DEFAULT_PROPERTY_TYPE)
    if not principal:  # ni secteur ni commune connus d'Obsimmo → on ne fabrique rien
        return None

    autres = {
        pt: get_market(cible, pt)
        for pt in ("appartements", "maisons")
    }
    region = principal.get("obsimmo_region")
    return {
        "secteur": principal.get("sector"),
        "parent_commune": principal.get("parent_commune"),
        "region": region,
        "principal": principal,                       # terrains constructibles
        "autres": {k: v for k, v in autres.items() if v},
        "comparaison_regionale": get_regional_market(region, DEFAULT_PROPERTY_TYPE) if region else None,
        "signal": market_signal(principal),
        "source": dict(SOURCE),
        "avertissement": ("Indicateur de marché Obsimmo, pas une estimation notariale ni une "
                          "valeur officielle."),
    }


# ── Validation structurelle (santé / tests) ────────────────────────────────────────────────
def validate() -> dict[str, Any]:
    """Contrôle d'intégrité du dataset (78 lignes, 26 secteurs × 3 typologies). Lève si invalide."""
    rows = load()
    if len(rows) != 78:
        raise ValueError(f"Obsimmo : 78 lignes attendues, {len(rows)} trouvées")
    secteurs: dict[str, set[str]] = {}
    for r in rows:
        if r.get("obsimmo_region") not in REGIONS:
            raise ValueError(f"Obsimmo : région inconnue {r.get('obsimmo_region')!r}")
        if not isinstance(r.get("active_listings_count"), int):
            raise ValueError(f"Obsimmo : active_listings_count non entier sur {r.get('sector')!r}")
        secteurs.setdefault(r["sector"], set()).add(r["property_type"])
    if len(secteurs) != 26:
        raise ValueError(f"Obsimmo : 26 secteurs attendus, {len(secteurs)} trouvés")
    for sec, types in secteurs.items():
        if types != set(PROPERTY_TYPES):
            raise ValueError(f"Obsimmo : secteur {sec!r} n'a pas les 3 typologies ({sorted(types)})")
    return {"rows": len(rows), "secteurs": len(secteurs), "typologies": list(PROPERTY_TYPES)}
