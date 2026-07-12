"""Libellés CLIENT des contributions du modèle P (M5.1 lot 3.3).

Le bloc « Pourquoi ce score » servait des paires techniques « libellé [bin] »
(ex. « canopée [≤ 0.4] », « croisement ancienneté dernière mutation × ancienneté
dernier permis [] ») illisibles pour un client. Ce module est la TABLE DE
CORRESPONDANCE VERSIONNÉE feature/bin → phrase en français métier, avec un
fallback propre pour tout bin inconnu (jamais de crochets vides à l'écran).

Règles :
- les bins numériques WoE ("≤ x", "(a, b]", "> x") sont paraphrasés par seuils
  métier par feature (les seuils exacts restent dans la fiche source, pas ici) ;
- « manquant » → « donnée non disponible » (jamais un faux zéro) ;
- les interactions (a*b, bin vide) ont une phrase fixe ;
- fallback : « {libellé} : {bin} » nettoyé — le libellé français de pipeline.py
  reste la base, on n'affiche JAMAIS le nom technique de la feature.

Toute évolution du binning du modèle (interdite hors re-gel M3.6) ou ajout de
feature DOIT incrémenter VERSION et compléter la table.
"""
from __future__ import annotations

import re

VERSION = "2026-07-12.1"

_NUM = re.compile(r"[-+]?\d*\.?\d+(?:e[-+]?\d+)?", re.I)


def _borne_haute(bin_: str) -> float | None:
    """La valeur représentative d'un bin WoE : « ≤ x » → x, « (a, b] » → milieu, « > x » → x."""
    nums = [float(m) for m in _NUM.findall(bin_)]
    if not nums:
        return None
    return (nums[0] + nums[1]) / 2 if len(nums) == 2 else nums[-1]


def _par_seuils(bin_: str, bas: float, haut: float, phrases: tuple[str, str, str]) -> str:
    """Phrase basse / moyenne / haute selon la borne du bin (« > x » compte haut)."""
    v = _borne_haute(bin_)
    if v is None:
        return phrases[1]
    if bin_.strip().startswith(">"):
        return phrases[2]
    if v <= bas:
        return phrases[0]
    if v <= haut:
        return phrases[1]
    return phrases[2]


#: bins catégoriels — phrase exacte par valeur.
_CATEGORIELS: dict[str, dict[str, str]] = {
    "zone_plu": {
        "U": "en zone urbaine (U)",
        "AU": "en zone à urbaniser (AU)",
        "A": "en zone agricole (A)",
        "N": "en zone naturelle (N)",
    },
    "tenure_bin": {
        "<1": "dernière mutation il y a moins d'un an",
        "1-2": "dernière mutation il y a 1 à 2 ans",
        "2-3": "dernière mutation il y a 2 à 3 ans",
        "3+": "dernière mutation il y a plus de 3 ans",
        "inconnu": "date de la dernière mutation inconnue",
    },
    "permis_bin": {
        "<2a": "permis de construire récent (moins de 2 ans)",
        "2-5a": "permis de construire dans les 5 ans",
        "5-10a": "dernier permis entre 5 et 10 ans",
        "10a+": "aucun permis récent (10 ans ou plus)",
        "jamais": "aucun permis connu",
    },
    "nu_constructible": {
        "true": "terrain nu constructible",
        "false": "terrain non nu-constructible",
    },
    "piscine": {"true": "piscine détectée", "false": "pas de piscine détectée"},
    "pv_candidat": {"true": "toiture candidate au photovoltaïque",
                    "false": "pas de candidat photovoltaïque"},
    "friche": {"true": "friche répertoriée", "false": "pas de friche répertoriée"},
    "qpv": {"true": "en quartier prioritaire", "false": "hors quartier prioritaire"},
}

#: interactions (bin vide) — phrase fixe lisible.
_INTERACTIONS: dict[str, str] = {
    "tenure_bin*permis_bin": "mutation et permis récents combinés",
    "tenure_bin*rot_nu": "ancienneté de mutation combinée à la rotation du secteur",
    "tenure_bin*surface_m2": "ancienneté de mutation combinée à la surface",
    "surface_m2*permis_bin": "surface combinée aux permis récents du secteur",
    "ndvi_moyen*zone_plu": "végétation combinée à la zone PLU",
}

#: numériques — (seuil_bas, seuil_haut, (phrase basse, moyenne, haute)).
_NUMERIQUES: dict[str, tuple[float, float, tuple[str, str, str]]] = {
    "canopee_pct": (5, 30, ("parcelle peu boisée", "parcelle moyennement boisée",
                            "parcelle très boisée")),
    "ndvi_moyen": (0.1, 0.2, ("végétation rase", "végétation modérée", "végétation dense")),
    "rot_nu": (0.002, 0.008, ("rotation du foncier nu faible dans le secteur",
                              "rotation du foncier nu modérée dans le secteur",
                              "rotation du foncier nu élevée dans le secteur")),
    "rot_bati": (0.003, 0.01, ("rotation du bâti faible dans le secteur",
                               "rotation du bâti modérée dans le secteur",
                               "rotation du bâti élevée dans le secteur")),
    "dens_bati_secteur": (0.02, 0.1, ("secteur très peu bâti", "secteur moyennement bâti",
                                      "secteur densément bâti")),
    "pct_bati_secteur": (0.35, 0.6, ("peu de parcelles bâties autour",
                                     "voisinage moyennement construit",
                                     "voisinage très construit")),
    "filo_pct_pauv": (0.15, 0.4, ("secteur aisé (peu de ménages pauvres)",
                                  "pauvreté du secteur dans la moyenne",
                                  "secteur à forte pauvreté")),
    "filo_snv_pp": (22_000, 29_000, ("niveau de vie du secteur modeste",
                                     "niveau de vie du secteur dans la moyenne",
                                     "niveau de vie du secteur élevé")),
    "filo_pct_prop": (0.4, 0.65, ("peu de propriétaires occupants",
                                  "part de propriétaires dans la moyenne",
                                  "forte part de propriétaires occupants")),
    "filo_dens_pop": (500, 3000, ("secteur très peu peuplé", "densité de population moyenne",
                                  "secteur très peuplé")),
    "pente_moy_deg": (8, 18, ("terrain plat", "pente marquée", "pente très forte")),
    "sdp_residuelle_m2": (500, 1300, ("droits à bâtir résiduels limités",
                                      "droits à bâtir résiduels notables",
                                      "droits à bâtir résiduels importants")),
    "surface_m2": (900, 5000, ("petite parcelle", "parcelle de taille moyenne",
                               "grande parcelle")),
    "sous_densite": (1, 3, ("densité proche du potentiel", "sous-densité notable",
                            "forte sous-densité")),
    "dormance_droits": (0.3, 0.7, ("droits à bâtir peu dormants", "droits à bâtir dormants",
                                   "droits à bâtir très dormants")),
    "med_pm2_terrain_36m": (150, 400, ("prix du terrain bas dans le secteur",
                                       "prix du terrain moyen dans le secteur",
                                       "prix du terrain élevé dans le secteur")),
    "med_pm2_bati_36m": (1800, 3000, ("prix du bâti bas dans le secteur",
                                      "prix du bâti moyen dans le secteur",
                                      "prix du bâti élevé dans le secteur")),
    "tendance_pm2_bati": (-0.02, 0.02, ("prix du bâti en baisse dans le secteur",
                                        "prix du bâti stables dans le secteur",
                                        "prix du bâti en hausse dans le secteur")),
    "permis_24m_norm": (0.2, 1.0, ("peu de permis dans le secteur (24 mois)",
                                   "activité de permis moyenne dans le secteur",
                                   "beaucoup de permis dans le secteur (24 mois)")),
    "acces_equipements": (0.3, 0.7, ("équipements éloignés", "équipements accessibles",
                                     "équipements très proches")),
    "window_coverage": (0.3, 0.7, ("historique DVF du secteur mince",
                                   "historique DVF du secteur partiel",
                                   "historique DVF du secteur complet")),
}


def phrase_client(feature: str, bin_: str, libelle: str) -> str:
    """La phrase client d'une contribution — fallback PROPRE pour tout bin inconnu."""
    b = (bin_ or "").strip()
    if feature in _INTERACTIONS:
        return _INTERACTIONS[feature]
    if b.lower() in ("manquant", "inconnu", "") and feature not in _CATEGORIELS:
        if b.lower() == "manquant" or not b:
            return f"{libelle} : donnée non disponible"
    cat = _CATEGORIELS.get(feature)
    if cat is not None:
        if b in cat:
            return cat[b]
        if b.lower() == "manquant":
            return f"{libelle} : donnée non disponible"
        return f"{libelle} : {b}" if b else libelle
    num = _NUMERIQUES.get(feature)
    if num is not None:
        if b.lower() == "manquant":
            return f"{libelle} : donnée non disponible"
        return _par_seuils(b, num[0], num[1], num[2])
    # fallback générique : jamais de crochets, jamais le nom technique
    return f"{libelle} : {b}" if b else libelle


def enrichir_contributions(top5: list[dict] | None) -> list[dict] | None:
    """Ajoute `phrase` (français client) à chaque contribution servie — les champs
    techniques (feature, bin, libelle, signe, log_hazard) restent pour l'audit."""
    if not top5:
        return top5
    return [{**c, "phrase": phrase_client(c.get("feature", ""), c.get("bin", ""),
                                          c.get("libelle", c.get("feature", "")))}
            for c in top5]
