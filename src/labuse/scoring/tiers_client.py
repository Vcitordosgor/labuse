"""M135 — LE MAPPING CLIENT DES TIERS, un seul endroit (patron libelles_client).

L'échelle SERVIE change de registre : de « brûlante/chaude/à creuser/épuisé » (thermique +
gisement mêlés) à une ÉCHELLE D'ACTION. Deux niveaux : le CHIP court à l'écran, le LIBELLÉ
long au « i » et à la fiche. Les identifiants INTERNES (clés) ne bougent pas — tables, gates,
API partners, seuils : rien ne change, seul l'affichage.

Canonique CÔTÉ SERVEUR (PDF, notifications, projets, scoreur, assistant l'importent). Le front
`frontend/src/lib/status.ts` porte le MÊME mapping ; un test anti-dérive garantit l'égalité
(TS et Python ne partagent pas un littéral). La famille declasse_* (« potentiel épuisé »)
collapse sur UN niveau d'action « Faible » — le détail (motif, état du bien) vit en fiche et
sur le badge d'état M131.
"""
from __future__ import annotations

#: code interne → (chip court, libellé long). ORDRE = échelle d'action décroissante.
TIERS_CLIENT: dict[str, tuple[str, str]] = {
    "brulante":         ("Priorité",   "À contacter en priorité"),
    "chaude":           ("À suivre",   "À suivre de près"),
    "reserve_fonciere": ("Long terme", "À revoir dans 1-2 ans"),
    "a_creuser":        ("Neutre",     "Sans signal particulier"),
    # famille « potentiel épuisé » — un seul niveau d'action (le motif fin est en fiche)
    "declasse_bati_sature":       ("Faible", "Peu de potentiel"),
    "declasse_non_constructible": ("Faible", "Peu de potentiel"),
    "declasse_bati_revele":       ("Faible", "Peu de potentiel"),
    "declasse_zone_fermee":       ("Faible", "Peu de potentiel"),
    "declasse_au_statut_inconnu": ("Faible", "Peu de potentiel"),
    "declasse_au_fermee":         ("Faible", "Peu de potentiel"),
    "ecartee":          ("Écartée",    "Écartée — motif en fiche"),
}


def court(tier: str | None) -> str | None:
    """Le chip court d'un tier (None si tier inconnu/nul)."""
    v = TIERS_CLIENT.get(tier or "")
    return v[0] if v else None


def long(tier: str | None) -> str | None:
    """Le libellé long d'un tier (« i » et fiche)."""
    v = TIERS_CLIENT.get(tier or "")
    return v[1] if v else None
