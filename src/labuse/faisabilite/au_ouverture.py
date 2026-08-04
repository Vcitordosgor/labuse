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
                           surface_m2: float, voisins: dict | None) -> str:
    """Mention `au_sous_plancher` — SERVIE, avec le problème ET sa solution (exigence Vic). La solution
    distingue voisines LIBRES et voisines nécessitant une DÉMOLITION (dette #4 : le bâti nuance, ne
    disqualifie pas)."""
    manquant = max(0, round(min_surf_m2 - surface_m2))
    txt = (f"Cette parcelle ({round(surface_m2)} m²) est trop petite pour l'opération d'ensemble "
           f"minimale imposée par le règlement ({min_log} logements à {densite:g} log/ha, soit "
           f"{round(min_surf_m2)} m² minimum). Il manque {manquant} m². Elle n'est pas constructible "
           f"SEULE, mais peut l'être en assemblage avec une ou plusieurs parcelles voisines.")
    if voisins:                                    # servir la SOLUTION nuancée, pas seulement le problème
        # trois régimes DISTINCTS (Vic) : libre (constructible directement), peu bâtie (retenue avec
        # réserve, 20-50 %), à démolir (> 50 %). On ne dit JAMAIS « libre » d'une parcelle bâtie.
        seg = [(voisins["libres"], "voisine(s) libre(s)"),
               (voisins["reserve"], "voisine(s) peu bâtie(s)"),
               (voisins["demolition"], "voisine(s) à démolir")]
        sans_demo = [f"{n} {lab}" for n, lab in seg[:2] if n]      # libres + peu bâties
        tous = [f"{n} {lab}" for n, lab in seg if n]
        if sans_demo and voisins.get("atteint_sans_demo"):
            txt += " " + " et ".join(sans_demo) + " de la même zone permettrai(en)t d'atteindre le seuil."
        elif tous:
            txt += " L'atteinte du seuil suppose : " + " et ".join(tous) + "."
    return txt


@functools.lru_cache(maxsize=1)
def _config() -> dict:
    from .. import config as _cfg
    return _cfg.load_yaml_config("calibrage/au_ouverture_planchers").get("communes", {}) or {}


def zone_regime(insee: str | None, zone_lib: str | None) -> dict | None:
    """Régime d'ouverture + plancher d'une zone : {ouverture, min_log?, densite_log_ha?}.
    Match par PRÉFIXE de `zone_lib` (le plus long d'abord). None = commune/zone non calibrée.

    Le match passe par `zone_norm.normalize_key` (POINT DE CALCUL UNIQUE, pt2.2) : insensible à la
    casse / aux accents / aux séparateurs, mais le RANG DE PHASAGE est conservé (1AUb ≠ 2AUb). La
    convention de casse du suffixe varie d'un SIG à l'autre — Saint-Leu stocke AUA/AUB/AUC/AUS là où
    la calibration écrit AUa/AUb/AUc/AUs ; sans normalisation, ses 124 AUS (fermée) retombaient sur le
    défaut « conditionnelle » et étaient servies à tort."""
    if not insee or not zone_lib:
        return None
    com = _config().get(str(insee))
    if not com:
        return None
    from .zone_norm import normalize_key
    zk = normalize_key(zone_lib)
    zones = com.get("zones", {}) or {}
    # préfixe le plus spécifique (plus long, normalisé) d'abord — « 1AUa » avant « AUa »
    for pref in sorted(zones, key=lambda p: len(normalize_key(p)), reverse=True):
        if zk.startswith(normalize_key(pref)):
            return zones[pref]
    return com.get("defaut")


def seuil_surface_m2(regime: dict) -> float | None:
    """Surface minimale d'opération = min_log ÷ densité (m²). None si pas de plancher sourcé."""
    ml, d = regime.get("min_log"), regime.get("densite_log_ha")
    if not ml or not d:
        return None
    return float(ml) / float(d) * 10000.0


def facteur_ponderation(insee: str | None, zone_lib: str | None,
                        surface_m2: float | None) -> float | None:
    """PONDÉRATION option B (arbitrage Vic 04/08) — facteur ×(1 − manque/seuil) appliqué au
    SIGNAL de scoring des parcelles `au_sous_plancher`, jamais à leur statut (elles restent
    SERVIES, candidates à l'assemblage). Un manque de 94 % pèse 94 % (facteur 0,06) ; un manque
    de 10 % pèse 10 % (facteur 0,90). Identité : 1 − manque/seuil = surface/seuil.

    MÊME POINT DE CALCUL que la mention de fiche (zone_regime + seuil_surface_m2, pt2.2) —
    jamais un seuil recopié. None = pas de pondération (zone non calibrée, pas de plancher,
    surface au-dessus du seuil, ou régime non conditionnel) : signal INCHANGÉ."""
    regime = zone_regime(insee, zone_lib)
    if regime is None or regime.get("ouverture") != OUVERTURE_CONDITIONNELLE:
        return None
    seuil = seuil_surface_m2(regime)
    if seuil is None or surface_m2 is None or surface_m2 <= 0 or surface_m2 >= seuil:
        return None
    return max(0.0, min(1.0, float(surface_m2) / seuil))


#: Longueur MINIMALE de frontière commune (contact PONCTUEL par un coin ≠ contiguïté utile). m, SRID 2975.
CONTIGUITE_MIN_M = 3.0
#: Filtre 2 — un DÉLAISSÉ (parcelle résiduelle minuscule) ne compte pas comme voisin assemblable. m².
DELAISSE_MAX_M2 = 50.0
#: Filtre 3 (Option A, mesurée) — la frontière commune doit représenter au moins cette PART du
#: périmètre du VOISIN : un contact de 3,9 m sur un géant de 25 000 m² (ratio ~0,3 %) est marginal ;
#: le même sur 400 m² (~5 %) est une vraie limite mitoyenne. Exclut chirurgicalement les géants-sliver.
FRONTIERE_PART_PERIMETRE_MIN = 0.02
#: Filtre 1 — le bâti ne disqualifie PAS par principe (dette #4), il NUANCE : trois régimes.
BATI_LIBRE_MAX = 0.20        # < 20 % emprise → voisin LIBRE (retenu franchement)
BATI_RESERVE_MAX = 0.50      # 20-50 % → retenu AVEC RÉSERVE ; > 50 % → démolition nécessaire


def voisins_assemblables(session, idu: str, zone_lib: str, seuil_m2: float) -> dict:
    """Répartit les voisins CONTIGUS de même zone en trois régimes de bâti et calcule si l'assemblage
    atteint `seuil_m2`. Filtres : frontière ≥ CONTIGUITE_MIN_M ET ≥ FRONTIERE_PART_PERIMETRE_MIN du
    périmètre du voisin (exclut le géant-sliver) ; délaissés < DELAISSE_MAX_M2 ignorés.

    Renvoie {libres, reserve, demolition, atteint_sans_demo, atteint_avec_demo}. Le bâti ne disqualifie
    pas (dette #4) : > 50 % = « démolition nécessaire », pas un silence. Mesure GÉOMÉTRIQUE — ne dit
    rien de l'ACQUÉRABILITÉ (propriété) : cf. dette #11. Lecture seule."""
    from sqlalchemy import text
    rows = session.execute(text("""
        WITH cible AS (SELECT geom_2975 g, ST_Area(geom_2975) surf FROM parcels WHERE idu=:idu)
        SELECT ST_Area(v.geom_2975) AS vsurf,
               COALESCE((SELECT SUM(ST_Area(ST_Intersection(b.geom_2975, v.geom_2975)))
                         FROM spatial_layers b WHERE b.kind='batiment'
                           AND ST_Intersects(b.geom_2975, v.geom_2975)), 0) AS bati
        FROM cible c
        JOIN parcel_zone_plu vz ON vz.zone_lib=:zl
        JOIN parcels v ON v.idu=vz.idu AND v.idu<>:idu
           AND ST_Length(ST_CollectionExtract(ST_Intersection(v.geom_2975, c.g), 2)) >= :minm
           AND ST_Length(ST_CollectionExtract(ST_Intersection(v.geom_2975, c.g), 2))
               >= :part * ST_Perimeter(v.geom_2975)
           AND ST_Area(v.geom_2975) >= :delaisse
    """), {"idu": idu, "zl": zone_lib, "minm": CONTIGUITE_MIN_M,
           "part": FRONTIERE_PART_PERIMETRE_MIN, "delaisse": DELAISSE_MAX_M2}).all()
    surf = session.execute(text("SELECT ST_Area(geom_2975) FROM parcels WHERE idu=:i"),
                           {"i": idu}).scalar() or 0.0
    libres = reserve = demo = 0
    surf_hors_demo = float(surf); surf_avec_demo = float(surf)
    for vsurf, bati in rows:
        ratio = (bati / vsurf) if vsurf else 0.0
        if ratio < BATI_LIBRE_MAX:
            libres += 1; surf_hors_demo += vsurf; surf_avec_demo += vsurf
        elif ratio <= BATI_RESERVE_MAX:
            reserve += 1; surf_hors_demo += vsurf; surf_avec_demo += vsurf
        else:
            demo += 1; surf_avec_demo += vsurf          # à démolir : compte seulement « avec démo »
    return {"libres": libres, "reserve": reserve, "demolition": demo,
            "atteint_sans_demo": surf_hors_demo >= seuil_m2,
            "atteint_avec_demo": surf_avec_demo >= seuil_m2}


def classify(insee: str | None, zone_lib: str | None, surface_m2: float | None,
             voisins: dict | None = None) -> tuple[str | None, str] | None:
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
                regime["min_log"], regime["densite_log_ha"], seuil, surface_m2, voisins)
        return OUVERTURE_CONDITIONNELLE, MENTION_CONDITIONNELLE      # servie + mention, taille OK
    return None


def build_au_ouverture(session, insee_list: list[str]) -> dict:
    """Peuple `parcel_au_statut` (classe=statut, motif=mention) pour les parcelles AU des communes
    calibrées. Les voisins assemblables ne sont calculés QUE pour les `au_sous_plancher` (coûteux).
    Renvoie le décompte par statut. Lecture/écriture parcel_au_statut UNIQUEMENT (jamais la table
    servie). Point d'arrêt : peupler ≠ basculer."""
    from sqlalchemy import text
    from .constructibilite import AU_SOUS_PLANCHER
    rows = session.execute(text("""
        SELECT p.id, p.idu, substring(p.idu from 1 for 5) AS insee, z.zone_lib,
               ST_Area(p.geom_2975) AS surf
        FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
        WHERE substring(p.idu from 1 for 5) = ANY(:ins)
          AND (z.zone_fam='AU' OR z.zone_lib ~ '^[0-9]?AU')
    """), {"ins": insee_list}).all()
    from collections import Counter
    compte = Counter()
    for pid, idu, insee, zl, surf in rows:
        regime = zone_regime(insee, zl)
        if regime is None:
            continue
        # pré-classement pour savoir s'il faut calculer les voisins (uniquement sous-plancher)
        pre = classify(insee, zl, float(surf) if surf is not None else None)
        vois = None
        if pre and pre[0] == AU_SOUS_PLANCHER:
            seuil = seuil_surface_m2(regime)
            vois = voisins_assemblables(session, idu, zl, seuil)
        res = classify(insee, zl, float(surf) if surf is not None else None, voisins=vois)
        if res is None:
            continue
        statut, motif = res
        compte[statut] += 1
        session.execute(text("""
            INSERT INTO parcel_au_statut (parcel_id, idu, classe, zone_lib, motif)
            VALUES (:pid, :idu, :c, :zl, :m)
            ON CONFLICT (parcel_id) DO UPDATE SET classe=EXCLUDED.classe,
              zone_lib=EXCLUDED.zone_lib, motif=EXCLUDED.motif
        """), {"pid": pid, "idu": idu, "c": statut, "zl": zl, "m": motif})
    return dict(compte)
