"""Calibration WEB du bilan promoteur — socle de démarrage SOURCÉ (cf RAPPORT_CALIBRATION_WEB.md).

Valeurs de DÉPART crédibles, chacune `sourcee` (source claire) ou `estimee` (déduite d'un ordre de
grandeur national ajusté DOM), pour que le bilan produise une charge foncière défendable AVANT la
calibration terrain. Injectées au secteur GLOBAL ('*') sans JAMAIS écraser un override déjà saisi
(ON CONFLICT DO NOTHING) → Vic garde la main, et affine plus tard avec un promoteur.

⚠ Le détail (valeur retenue, source/URL, date, raisonnement) est tenu à jour dans
`RAPPORT_CALIBRATION_WEB.md`. Ne pas modifier une valeur ici sans mettre à jour le rapport.
"""
from __future__ import annotations

from sqlalchemy import text

# param → (valeur, provenance 'sourcee' | 'estimee')
CALIBRATION: dict[str, tuple[float, str]] = {
    # Recettes
    "prix_m2_neuf": (4900.0, "sourcee"),   # neuf Saint-Paul 2024 ~4 920 €/m² (corroboré marché ~5 200)
    "prix_m2_lls": (2900.0, "estimee"),    # cession VEFA→bailleur ~prix de revient social DOM
    "ratio_vendable": (0.80, "estimee"),   # SDP brute → habitable vendable (standard 0,78-0,85)
    "bonus_vue_mer_pct": (15.0, "estimee"),  # prime vue mer dégagée (balnéaire Réunion, 10-25 %)
    # Coûts
    "cout_construction_m2_sdp": (2100.0, "estimee"),  # bâti seul, collectif DOM (métropole 1340-1480 + surcoût)
    "cout_vrd_base": (90.0, "estimee"),               # VRD/viabilisation €/m² terrain
    "majoration_vrd_pente_pct": (30.0, "estimee"),    # surcoût terrassement pente forte
    "majoration_vrd_assainissement_pct": (25.0, "estimee"),  # surcoût assainissement autonome
    # Frais & marge
    "honoraires_pct": (12.0, "estimee"),       # honoraires techniques + commercialisation, % du CA
    "frais_financiers_pct": (3.0, "estimee"),  # portage financier au taux actuel, % du CA
    # LOT 3 — calé sur la fourchette promoteur réelle 8–10 % (retour terrain). Reste « estimée /
    # à affiner » : dépend des contraintes propres à chaque promoteur, jamais une vérité certaine.
    "marge_cible_pct": (9.0, "estimee"),       # marge cible promoteur, % du CA (8–10 %, à affiner)
}


# prix_m2_neuf VENTILÉ par BASSIN PLU existant (le découpage de l'app, cf RAPPORT_CALIBRATION_WEB.md).
# Chaque valeur sourcée par observatoire/annonces du quartier ; les secteurs absents retombent sur
# le socle commun (4 900). secteur → (valeur, provenance).
SECTEUR_PRIX_NEUF: dict[str, tuple[float, str]] = {
    "Saint-Gilles": (5800.0, "sourcee"),               # balnéaire — médiane appart ~6 029 €/m² (SeLoger)
    "La Saline": (6000.0, "sourcee"),                  # balnéaire — moy. appart ~6 632 €/m² (immo-diffusion)
    "Plateau Caillou": (3500.0, "sourcee"),            # intérieur — moy. appart ~3 417 €/m² (SeLoger)
    "La Plaine-Bois de Nèfles": (3400.0, "sourcee"),   # Hauts — appart ~3 100-3 700 €/m² (consortium/SeLoger)
    "Le Guillaume": (3900.0, "estimee"),               # Hauts — échantillon appart FRAGILE (maison ~3 973)
    # « Saint-Paul Centre » → reste sur le socle commun 4 900 € (neuf Saint-Paul 2024, sourcé).
}


def seed(executor, secteur: str = "*") -> None:
    """Injecte le socle commun (global '*') + la ventilation prix neuf par secteur, sans écraser
    un override existant. `executor` = Session OU Connection. Idempotent (ON CONFLICT DO NOTHING)."""
    for param, (value, prov) in CALIBRATION.items():
        executor.execute(
            text("INSERT INTO bilan_params (secteur, param, value, is_placeholder, provenance, updated_at) "
                 "VALUES (:s, :p, :v, false, :pr, now()) ON CONFLICT (secteur, param) DO NOTHING"),
            {"s": secteur, "p": param, "v": value, "pr": prov},
        )
    for sect, (value, prov) in SECTEUR_PRIX_NEUF.items():
        executor.execute(
            text("INSERT INTO bilan_params (secteur, param, value, is_placeholder, provenance, updated_at) "
                 "VALUES (:s, 'prix_m2_neuf', :v, false, :pr, now()) ON CONFLICT (secteur, param) DO NOTHING"),
            {"s": sect, "v": value, "pr": prov},
        )
