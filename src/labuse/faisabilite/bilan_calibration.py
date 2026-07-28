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
    # `prix_m2_neuf` GLOBAL 4900 RETIRÉ (décision Vic 28/07/2026, mandat calibration estimées —
    # back-test contre le réel). C'était un prix de neuf SAINT-PAULOIS servi comme socle à toute
    # l'île, dans le sens généreux : il gonflait la charge foncière (symétrique du bug 2100). Le
    # prix de sortie vient désormais de `dvf_prix_sortie_neuf` (appartements de marché, hors
    # bailleurs sociaux, N_MIN ≥ 10) résolu par commune, ou « non calculable ». Seuls survivent
    # les overrides de BASSIN sourcés (SECTEUR_PRIX_NEUF ci-dessous), en tête de préséance.
    "prix_m2_lls": (2900.0, "estimee"),    # cession VEFA→bailleur ~prix de revient social DOM
    # ratio_vendable RETIRÉ (Vic 28/07/2026) : paramètre mort — aucun moteur ne le lisait.
    # Coûts — PAS de cout_construction_m2_sdp ici (mandat hypothèses bilan, décision Vic
    # 28/07/2026) : le 2100 « estimé » du 14/06 était ancré sur la fourchette YAML PÉRIMÉE
    # (avant-audit O2) et dupliquait la source unique. Le coût vient de la fourchette
    # auditée du YAML (2300-2800, repli cout=0) ; seul un override SECTORIEL sourcé est légitime.
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
# MANDAT PRIX SORTIE CONSOMMATEURS (décision Vic 28/07/2026) — les 5 overrides de bassin sont
# DÉMOTÉS en `estimee` (is_placeholder=true, HORS préséance). Motif : **observatoire de l'existant,
# non confirmé par DVF neuf — en attente de confirmation**. Ils viennent tous de la calibration web
# du 14/06 (`f25e8cc`, même famille que le socle 2100), sourcés d'un OBSERVATOIRE de l'EXISTANT
# (SeLoger/consortium), jamais confirmés par du DVF neuf de marché. RÈGLE DE PRÉSÉANCE GRAVÉE : un
# override de bassin ne prime sur la médiane communale DVF que s'il est fondé sur du DVF NEUF de
# marché ≥ N_MIN ; un observatoire de l'existant n'est jamais une entrée de calcul (déclinaison au
# bassin de « DVF, un seul référentiel »). `resolve_prix_neuf_marche` n'honore que la provenance
# `sourcee` → ces bassins sortent de la préséance et les parcelles résolvent sur le DVF (secteur
# local / commune / repli île). Le signal n'est pas perdu : visible en placeholder, remonte dans
# `bilan-params-perimes`, redevient candidat dès qu'un bassin franchit N_MIN en ventes neuves.
# LIMITE CONNUE : la commune Saint-Paul (4 730 DVF) peut SUR-évaluer les Hauts face à l'observatoire
# (~3 400-3 800) ; condition de levée = confirmation DVF neuf sur ces bassins.
SECTEUR_PRIX_NEUF: dict[str, tuple[float, str]] = {
    "Saint-Gilles": (5800.0, "estimee"),               # balnéaire — observatoire ~6 029 €/m² (SeLoger) — à confirmer DVF
    "La Saline": (6000.0, "estimee"),                  # balnéaire — observatoire ~6 632 €/m² — à confirmer DVF
    "Plateau Caillou": (3500.0, "estimee"),            # Hauts — observatoire ~3 417 €/m² (SeLoger) — à confirmer DVF
    "La Plaine-Bois de Nèfles": (3400.0, "estimee"),   # Hauts — observatoire ~3 100-3 700 €/m² — à confirmer DVF
    "Le Guillaume": (3900.0, "estimee"),               # Hauts — échantillon appart FRAGILE (déjà placeholder)
    # Hors bassin sourcé DVF → résolution DVF (secteur local / commune Saint-Paul 4 730 / repli île).
}


def seed(executor, secteur: str = "*") -> None:
    """Injecte le socle commun (global '*') + la ventilation prix neuf par secteur, sans écraser
    un override existant. `executor` = Session OU Connection. Idempotent (ON CONFLICT DO NOTHING)."""
    # Une valeur « estimee » est INSÉRÉE placeholder=true (décision Vic 28/07/2026) : elle reste
    # visible aux bandeaux tant qu'elle n'est pas confirmée (cf. `labuse bilan-params-perimes`).
    for param, (value, prov) in CALIBRATION.items():
        executor.execute(
            text("INSERT INTO bilan_params (secteur, param, value, is_placeholder, provenance, updated_at) "
                 "VALUES (:s, :p, :v, :ph, :pr, now()) ON CONFLICT (secteur, param) DO NOTHING"),
            {"s": secteur, "p": param, "v": value, "ph": prov == "estimee", "pr": prov},
        )
    for sect, (value, prov) in SECTEUR_PRIX_NEUF.items():
        executor.execute(
            text("INSERT INTO bilan_params (secteur, param, value, is_placeholder, provenance, updated_at) "
                 "VALUES (:s, 'prix_m2_neuf', :v, :ph, :pr, now()) ON CONFLICT (secteur, param) DO NOTHING"),
            {"s": sect, "v": value, "ph": prov == "estimee", "pr": prov},
        )
