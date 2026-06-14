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
    "marge_cible_pct": (16.0, "estimee"),      # marge cible promoteur, % du CA (à affiner ++)
}


def seed(executor, secteur: str = "*") -> None:
    """Injecte le socle au `secteur` (défaut global '*'), sans écraser un override existant.
    `executor` = Session OU Connection (les deux exposent .execute). Idempotent."""
    for param, (value, prov) in CALIBRATION.items():
        executor.execute(
            text("INSERT INTO bilan_params (secteur, param, value, is_placeholder, provenance, updated_at) "
                 "VALUES (:s, :p, :v, false, :pr, now()) ON CONFLICT (secteur, param) DO NOTHING"),
            {"s": secteur, "p": param, "v": value, "pr": prov},
        )
