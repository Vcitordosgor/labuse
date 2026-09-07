"""EXPORTS-2 lot 1.4 — LE VERDICT DE SECTION : une fonction par section, DÉTERMINISTE, phrases
à trous remplies par les ids lus. AUCUN appel IA, aucune prose générée — le même jeu de Valeur
donne toujours la même phrase. Chaque fonction rend `(texte, ton, petit)` (ton : ''|'warn'|
'neutral') ou None quand la section n'a rien de concluant (le bloc omet alors le verdict).

Les verdicts des sections sont ajoutés ici au fil des lots documents (2, 5). Le lot 1 pose le
mécanisme et le verrouille par l'exemple du zonage.
"""
from __future__ import annotations

from ..registre.valeur import Valeur

Verdict = tuple[str, str, str]      # (texte_html, ton, petit_html)

#: familles de zone non constructibles (drapeau warn) — la boussole « jamais un faux constructible ».
_NON_CONSTRUCTIBLE = {"A": "agricole", "N": "naturelle"}
_CONSTRUCTIBLE = {"U": "urbaine, constructible", "AU": "à urbaniser (ouverture sous conditions)"}


def _val(valeurs: dict[str, Valeur], cid: str):
    v = valeurs.get(cid)
    return v.valeur if v is not None else None


def verdict_zonage(valeurs: dict[str, Valeur]) -> Verdict | None:
    """Section 2 — la famille de la zone DOMINANTE (zone_servie) conclut : constructible ou non,
    cause dite. Rien à dire si la zone n'est pas déterminée (le bloc omet le verdict)."""
    fam = _val(valeurs, "zone_plu_famille")
    if not fam:
        return None
    fam = str(fam).upper()
    if fam in _NON_CONSTRUCTIBLE:
        return (f"Zone {fam} — {_NON_CONSTRUCTIBLE[fam]}, <strong>non constructible</strong>. "
                f"Le potentiel de construction est nul par cette règle de zonage.", "warn", "")
    if fam in _CONSTRUCTIBLE:
        return (f"Zone {fam} — {_CONSTRUCTIBLE[fam]}. Le document opposable du Géoportail de "
                f"l'urbanisme fait foi ; les valeurs de règle ci-dessous sont une aide à la lecture.",
                "", "")
    return None


def rendu_verdict(v: Verdict | None) -> str:
    """Le fragment HTML d'un verdict, ou '' si la section n'a rien à conclure."""
    if v is None:
        return ""
    from .rendu import verdict as _box
    texte, ton, petit = v
    return _box(texte, ton, petit)
