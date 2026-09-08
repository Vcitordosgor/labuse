"""LE MAPPING CLIENT DES TIERS — un seul endroit, un seul vocabulaire (PALIERS-1 Lot C).

Le domaine de `tier_opportunite` est désormais EXACTEMENT quatre valeurs :
    Priorité / À suivre / Sans signal / Écartée.
Plus de brûlante / chaude / réserve / à creuser / déclassé, ni « Long terme / Neutre /
Faible », ni « Score V » : la fiche, la carte, Étudier un bien, Projets, Radar, Veille,
Communes, Densifier, Prospection solaire, les PDF et le Copilote LISENT cette valeur —
aucun écran n'a son propre libellé.

Les runs à politique v2 (PALIERS-1, cf. scoring/p_v2/statuts.py) stockent directement les
codes `priorite / a_suivre / sans_signal / ecartee`. Les ANCIENS runs (codes par rang :
brulante / chaude / reserve_fonciere / a_creuser / declasse_* / ecartee) NE SONT JAMAIS
RÉÉCRITS : une CORRESPONDANCE EN LECTURE les projette sur les quatre valeurs.

Canonique CÔTÉ SERVEUR (PDF, notifications, projets, scoreur, Copilote l'importent). Le front
`frontend/src/lib/status.ts` porte le MÊME mapping ; un test anti-dérive garantit l'égalité.
"""
from __future__ import annotations

#: le code de palier canonique → (chip court, libellé long). LE domaine, quatre valeurs.
PALIERS_CLIENT: dict[str, tuple[str, str]] = {
    "priorite":    ("Priorité",    "À contacter en priorité"),
    "a_suivre":    ("À suivre",    "À suivre de près"),
    "sans_signal": ("Sans signal", "Sans signal de vente à court terme"),
    "ecartee":     ("Écartée",     "Écartée — motif en fiche"),
}

#: CORRESPONDANCE EN LECTURE des anciens codes (runs jamais réécrits) → code canonique.
#: brûlante = tête → Priorité ; chaude = 2e tête → À suivre ; tout le reste des tiers non-tête
#: (à creuser, réserve foncière — désormais un DRAPEAU —, déclassements — désormais des MOTIFS)
#: → Sans signal ; l'étage 0 → Écartée. Aucune valeur « Long terme / Neutre / Faible » ne survit.
CORRESPONDANCE_LEGACY: dict[str, str] = {
    "brulante": "priorite",
    "chaude": "a_suivre",
    "a_creuser": "sans_signal",
    "reserve_fonciere": "sans_signal",
    "declasse_bati_sature": "sans_signal",
    "declasse_non_constructible": "sans_signal",
    "declasse_bati_revele": "sans_signal",
    "declasse_zone_fermee": "sans_signal",
    "declasse_au_statut_inconnu": "sans_signal",
    "declasse_au_fermee": "sans_signal",
    "exclue": "ecartee",
}

#: les quatre valeurs du domaine, ordre d'action décroissant.
DOMAINE_PALIERS = ("priorite", "a_suivre", "sans_signal", "ecartee")
#: le ×N (rapport à la moyenne de la commune) ne s'affiche QU'À côté de ces deux paliers.
PALIERS_AVEC_MULTIPLE = ("priorite", "a_suivre")


def code_palier(tier: str | None) -> str | None:
    """Le CODE canonique d'un tier (nouveau ou ancien) — la correspondance en lecture.
    None si tier inconnu/nul. C'est le seul point qui connaît les anciens codes."""
    if not tier:
        return None
    if tier in PALIERS_CLIENT:
        return tier
    return CORRESPONDANCE_LEGACY.get(tier)


def court(tier: str | None) -> str | None:
    """Le chip court d'un tier (None si inconnu/nul) — via la correspondance canonique."""
    code = code_palier(tier)
    return PALIERS_CLIENT[code][0] if code else None


def long(tier: str | None) -> str | None:
    """Le libellé long d'un tier (« i » et fiche) — via la correspondance canonique."""
    code = code_palier(tier)
    return PALIERS_CLIENT[code][1] if code else None


def montre_multiple(tier: str | None) -> bool:
    """Le ×N s'affiche-t-il à côté de ce palier ? (Priorité et À suivre seulement.)"""
    return code_palier(tier) in PALIERS_AVEC_MULTIPLE


#: rétro-compatibilité : d'anciens importeurs lisent `TIERS_CLIENT`. On la garde comme
#: vue dérivée (code → (chip, long)) couvrant nouveaux ET anciens codes, même vocabulaire.
TIERS_CLIENT: dict[str, tuple[str, str]] = {
    **PALIERS_CLIENT,
    **{legacy: PALIERS_CLIENT[canon] for legacy, canon in CORRESPONDANCE_LEGACY.items()},
}
