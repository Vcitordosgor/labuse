"""AU — traitement AFFINÉ de l'ouverture (GPU-PILOTE, Vic 30/07/2026).

L'ouverture des zones AU a été LUE au règlement (campagne d'extraction GPU-PILOTE). On remplace le
« au statut inconnu » indifférencié par TROIS traitements, selon le régime d'ouverture de la zone :

* **fermée** (AUs/AUst réserve) → `declasse_au_fermee` : déclassement FERME, motif sourcé.
* **conditionnelle_operation** → SERVIE avec mention. SI la parcelle est trop petite pour l'opération
  minimale imposée par le plancher (`min_log ÷ densité`), elle devient `au_sous_plancher` : TOUJOURS
  SERVIE (candidate à l'assemblage — LABUSE porte `/assemblages`), avec mention + surface manquante +
  nombre de voisines contiguës qui permettraient d'atteindre le seuil. **Jamais déclassée** : la
  déclasser ferait l'erreur symétrique (transformer « pas seule » en « pas du tout »).
* **conditionnelle_etat_tiers** (phasage 2AU→1AU) → `declasse_au_statut_inconnu` : vrai inconnu,
  l'ouverture dépend de l'aménagement d'AUTRES zones, non déductible du règlement. Jamais supposée ouverte.

Source de données : `config/calibrage/au_ouverture_planchers.yaml` (par commune INSEE × préfixe de
zone). Une commune/zone absente = non encore calibrée → aucun marquage (comportement d'avant).
"""
from __future__ import annotations

import functools

from .constructibilite import (
    DECLASSE_AU_FERMEE, AU_SOUS_PLANCHER, DECLASSE_AU_STATUT_INCONNU,
)

OUVERTURE_FERMEE = "fermee"
OUVERTURE_CONDITIONNELLE = "conditionnelle_operation"
OUVERTURE_ETAT_TIERS = "conditionnelle_etat_tiers"

# --- Motifs / mentions de fiche (étiquette « Absent » — ni un fait acquis, ni « Estimé ») ---
MOTIF_FERMEE = (
    "Zone AU fermée à l'urbanisation (réserve). Son ouverture est subordonnée à une procédure de "
    "modification ou de révision du PLU — source règlement (voir calibration de la commune).")
MENTION_CONDITIONNELLE = (
    "Zone à urbaniser — ouverture conditionnée à une opération d'aménagement d'ensemble et/ou à une "
    "modification du PLU. Constructibilité à confirmer auprès de la commune avant tout engagement.")
MOTIF_ETAT_TIERS = (
    "Zone à urbaniser dont l'ouverture DÉPEND de l'aménagement préalable d'AUTRES zones AU (phasage "
    "2AU→1AU). Statut non déductible du règlement seul — à vérifier, jamais supposée ouverte.")


def _mention_sous_plancher(min_log: int, densite: float, min_surf_m2: float,
                           surface_m2: float, voisins: int | None) -> str:
    """Mention `au_sous_plancher` — SERVIE, avec le problème ET sa solution (exigence Vic)."""
    manquant = max(0, round(min_surf_m2 - surface_m2))
    txt = (f"Cette parcelle ({round(surface_m2)} m²) est trop petite pour l'opération d'ensemble "
           f"minimale imposée par le règlement ({min_log} logements à {densite:g} log/ha, soit "
           f"{round(min_surf_m2)} m² minimum). Elle n'est pas constructible SEULE — il manque "
           f"{manquant} m² — mais peut l'être en assemblage avec une ou plusieurs parcelles voisines.")
    if voisins:                                    # servir la SOLUTION, pas seulement le problème
        txt += (f" {voisins} parcelle(s) voisine(s) de la même zone permettrai(en)t d'atteindre le "
                f"seuil.")
    return txt


@functools.lru_cache(maxsize=1)
def _config() -> dict:
    from .. import config as _cfg
    return _cfg.load_yaml_config("calibrage/au_ouverture_planchers").get("communes", {}) or {}


def zone_regime(insee: str | None, zone_lib: str | None) -> dict | None:
    """Régime d'ouverture + plancher d'une zone : {ouverture, min_log?, densite_log_ha?}.
    Match par PRÉFIXE de `zone_lib` (le plus long d'abord). None = commune/zone non calibrée."""
    if not insee or not zone_lib:
        return None
    com = _config().get(str(insee))
    if not com:
        return None
    zl = zone_lib.strip()
    zones = com.get("zones", {}) or {}
    # préfixe le plus spécifique (plus long) d'abord — « 1AUa » avant « AUa »
    for pref in sorted(zones, key=len, reverse=True):
        if zl.startswith(pref):
            return zones[pref]
    return com.get("defaut")


def seuil_surface_m2(regime: dict) -> float | None:
    """Surface minimale d'opération = min_log ÷ densité (m²). None si pas de plancher sourcé."""
    ml, d = regime.get("min_log"), regime.get("densite_log_ha")
    if not ml or not d:
        return None
    return float(ml) / float(d) * 10000.0


#: Longueur MINIMALE de frontière commune pour qu'un voisin compte comme assemblable (Vic 30/07) :
#: une contiguïté PONCTUELLE (contact par un coin) n'est pas une contiguïté utile. En mètres (SRID 2975).
CONTIGUITE_MIN_M = 3.0


def voisins_assemblables(session, idu: str, zone_lib: str, seuil_m2: float) -> int:
    """Nombre de voisins CONTIGUS de MÊME zone (frontière commune ≥ CONTIGUITE_MIN_M, pas un contact
    ponctuel) qui, assemblés à la parcelle, permettraient d'atteindre `seuil_m2`. Lecture seule.

    Renvoie 0 si l'assemblage des voisins linéairement contigus n'atteint pas le seuil. La mesure est
    GÉOMÉTRIQUE — elle ne dit rien de l'ACQUÉRABILITÉ (propriété) : cf. dette #11."""
    from sqlalchemy import text
    row = session.execute(text("""
        WITH cible AS (SELECT geom_2975 g, ST_Area(geom_2975) surf FROM parcels WHERE idu=:idu)
        SELECT c.surf,
               COALESCE(SUM(ST_Area(v.geom_2975)), 0) AS voisins_surf,
               count(v.idu) AS n
        FROM cible c
        LEFT JOIN parcel_zone_plu vz ON vz.zone_lib=:zl
        LEFT JOIN parcels v ON v.idu=vz.idu AND v.idu<>:idu
             AND ST_Length(ST_CollectionExtract(ST_Intersection(v.geom_2975, c.g), 2)) >= :minm
        GROUP BY c.surf
    """), {"idu": idu, "zl": zone_lib, "minm": CONTIGUITE_MIN_M}).first()
    if not row:
        return 0
    surf, voisins_surf, n = row
    return int(n) if (surf + voisins_surf) >= seuil_m2 else 0


def classify(insee: str | None, zone_lib: str | None, surface_m2: float | None,
             voisins_assemblables: int | None = None) -> tuple[str | None, str] | None:
    """Classe une parcelle AU en (statut, mention). None = zone non calibrée (pas de marquage).

    - fermée                 → (DECLASSE_AU_FERMEE, motif)
    - conditionnelle + petite → (AU_SOUS_PLANCHER, mention servie avec surface manquante + voisins)
    - conditionnelle + OK     → (OUVERTURE_CONDITIONNELLE, mention servie)  [statut = régime, servie]
    - conditionnelle_etat_tiers → (DECLASSE_AU_STATUT_INCONNU, motif)
    """
    regime = zone_regime(insee, zone_lib)
    if regime is None:
        return None
    ouv = regime.get("ouverture")
    if ouv == OUVERTURE_FERMEE:
        return DECLASSE_AU_FERMEE, MOTIF_FERMEE
    if ouv == OUVERTURE_ETAT_TIERS:
        return DECLASSE_AU_STATUT_INCONNU, MOTIF_ETAT_TIERS
    if ouv == OUVERTURE_CONDITIONNELLE:
        seuil = seuil_surface_m2(regime)
        if seuil is not None and surface_m2 is not None and surface_m2 < seuil:
            return AU_SOUS_PLANCHER, _mention_sous_plancher(
                regime["min_log"], regime["densite_log_ha"], seuil, surface_m2, voisins_assemblables)
        return OUVERTURE_CONDITIONNELLE, MENTION_CONDITIONNELLE      # servie + mention, taille OK
    return None
