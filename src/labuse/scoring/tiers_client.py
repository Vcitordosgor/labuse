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

#: REPARATIONS-1 lot 2b — DÉCISION DE VIC, RÉVERSIBLE : le palier « Priorité » CESSE D'ÊTRE
#: SERVI tant qu'aucune validation propre n'existe (×0,52 mesuré en marche avant, 1 vente sur
#: 111, définition mécanique sur une seule variable). « À suivre » porte toute la tête classée.
#: AFFICHAGE SEUL : les runs ne sont pas réécrits, les tiers stockés (brulante / priorite)
#: restent en base — repasser ce drapeau à True restitue le palier tel quel, sans rescoring.
PRIORITE_SERVIE = False

#: le code de palier canonique → (chip court, libellé long). LE domaine, quatre valeurs
#: écrites (l'entrée « priorite » reste pour la réversibilité — non servie tant que
#: PRIORITE_SERVIE est False : code_palier la projette sur « a_suivre »).
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

#: FRONT-CHIFFRES-2 (F13/F29) — LA DA DU PALIER, ICI, une fois. Le front (pastille Projets,
#: badge Outils) ne code plus la correspondance palier→couleur : il lit `jeton` (jeton DA = variable
#: CSS de la charte) et `ton` (les 3 tons du composant Badge : vert/ambre/neutre). À la bascule
#: q_v15, quand les paliers deviennent les bandes A/B/C/D, SEUL cet endroit change — la pastille ET
#: le badge suivent. Aligné sur PALIER_META de la charte (menthe/ambre/gris-vert).
#: `jeton` = clé du registre de jetons DA du front (frontend/src/lib/tokens.ts, le point de
#: définition unique d'une couleur de marque). Le back nomme le jeton par palier ; le front le
#: résout en couleur — il ne code plus la correspondance palier→couleur.
PALIER_DA: dict[str, dict[str, str]] = {
    "priorite":    {"jeton": "stEcartee", "ton": "ambre"},   # corail — non servi tant que PRIORITE_SERVIE False
    "a_suivre":    {"jeton": "stCreuser", "ton": "ambre"},   # ambre
    "sans_signal": {"jeton": "stExclue",  "ton": "neutre"},  # gris neutre DA (sans signal)
    "ecartee":     {"jeton": "stExclue",  "ton": "neutre"},  # gris neutre DA (écartée)
}


def palier_da(tier: str | None) -> dict[str, str] | None:
    """La DA (jeton + ton + libellés) du palier canonique d'un tier — le point unique lu par la
    pastille et le badge. None si tier inconnu/nul (le front rend alors un ton neutre)."""
    code = code_palier(tier)
    if not code:
        return None
    chip, lng = PALIERS_CLIENT[code]
    return {"code": code, "chip": chip, "long": lng, **PALIER_DA[code]}


def paliers_da() -> dict[str, dict[str, str]]:
    """La carte SERVIE au front : chaque palier du domaine → chip, libellé long, jeton DA, ton."""
    return {code: {"chip": PALIERS_CLIENT[code][0], "long": PALIERS_CLIENT[code][1], **PALIER_DA[code]}
            for code in DOMAINE_PALIERS}


def code_palier(tier: str | None) -> str | None:
    """Le CODE canonique d'un tier (nouveau ou ancien) — la correspondance en lecture.
    None si tier inconnu/nul. C'est le seul point qui connaît les anciens codes."""
    if not tier:
        return None
    code = tier if tier in PALIERS_CLIENT else CORRESPONDANCE_LEGACY.get(tier)
    # REPARATIONS-1 lot 2b — Priorité non servie : la tête classée entière porte À suivre.
    if code == "priorite" and not PRIORITE_SERVIE:
        return "a_suivre"
    return code


def court(tier: str | None) -> str | None:
    """Le chip court d'un tier (None si inconnu/nul) — via la correspondance canonique."""
    code = code_palier(tier)
    return PALIERS_CLIENT[code][0] if code else None


def long(tier: str | None) -> str | None:
    """Le libellé long d'un tier (« i » et fiche) — via la correspondance canonique."""
    code = code_palier(tier)
    return PALIERS_CLIENT[code][1] if code else None


def codes_stockes(palier: str) -> tuple[str, ...]:
    """REPARATIONS-1 lot 2b — les codes STOCKÉS (runs jamais réécrits) qui se servent sous ce
    palier. Sert au filtrage : « À suivre » (tête classée entière) = brulante + chaude +
    priorite + a_suivre tant que PRIORITE_SERVIE est False."""
    return tuple(sorted(
        code for code in (*PALIERS_CLIENT, *CORRESPONDANCE_LEGACY)
        if code_palier(code) == palier))


def montre_multiple(tier: str | None) -> bool:
    """Le ×N s'affiche-t-il à côté de ce palier ? (Priorité et À suivre seulement.)"""
    return code_palier(tier) in PALIERS_AVEC_MULTIPLE


#: rétro-compatibilité : d'anciens importeurs lisent `TIERS_CLIENT`. On la garde comme
#: vue dérivée (code → (chip, long)) couvrant nouveaux ET anciens codes, même vocabulaire.
#: dérivée VIA code_palier pour que « Priorité non servie » (lot 2b) s'applique partout.
TIERS_CLIENT: dict[str, tuple[str, str]] = {
    code: PALIERS_CLIENT[code_palier(code)]
    for code in (*PALIERS_CLIENT, *CORRESPONDANCE_LEGACY)
}
