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
    # RECETTE-7 (E3) — afficher le CODE DE ZONE réel (ex. « Um ») pour qu'il colle aux articles
    # cités plus bas (« Art. Um.9 ») : la FAMILLE (U/AU/A/N) sert la classification
    # constructible/non, mais le libellé montre le secteur exact, jamais un « Zone U » tronqué à
    # côté d'un règlement « Um » — le lecteur ne doit plus se demander s'il lit une autre zone.
    reg = _val(valeurs, "reglement_plu_bloc")
    code = (reg.get("zone") if isinstance(reg, dict) else None) or fam
    lib = f"Zone {code}" + (f" (famille {fam})" if str(code).strip().upper() != fam else "")
    if fam in _NON_CONSTRUCTIBLE:
        return (f"{lib} — {_NON_CONSTRUCTIBLE[fam]}, <strong>non constructible</strong>. "
                f"Le potentiel de construction est nul par cette règle de zonage.", "warn", "")
    if fam in _CONSTRUCTIBLE:
        return (f"{lib} — {_CONSTRUCTIBLE[fam]}. Le document opposable du Géoportail de "
                f"l'urbanisme fait foi ; les valeurs de règle ci-dessous sont une aide à la lecture.",
                "", "")
    return None


def verdict_potentiel(valeurs: dict[str, Valeur]) -> Verdict | None:
    """Section 3 — conclut sur le potentiel à partir du bloc potentiel (moteur). Boussole :
    jamais un faux constructible ; une cause de non-constructibilité prime sur la saturation."""
    p = _val(valeurs, "potentiel_verdict")
    if not isinstance(p, dict):
        return None
    cause, libelle = p.get("cause"), p.get("libelle")
    sdp, pct, niveau = p.get("sdp_residuelle_m2"), p.get("pct_consomme"), p.get("niveau")
    if cause:
        # la cause de non-constructibilité PRIME sur toute sous-densité mesurée (jamais un faux
        # constructible) — on n'imprime pas le libellé brut du modèle qui dirait « fort potentiel ».
        fam = _val(valeurs, "zone_plu_famille")
        z = f" (zone {fam})" if fam else ""
        return (f"Terrain non constructible{z} : le potentiel de construction est nul par la règle "
                f"de zonage.", "warn", "")
    if niveau == "nul" or (sdp is not None and float(sdp) <= 0):
        pct_txt = f" ({pct} %)" if pct else ""
        return (f"Parcelle bâtie et saturée : la surface de plancher autorisée est déjà "
                f"consommée{pct_txt}. La valeur est dans la réhabilitation du bâti ou dans sa "
                f"reconstruction.", "warn", "")
    if libelle:
        return (f"Potentiel de construction : {libelle}.", "", "")
    return None


def verdict_reseaux(valeurs: dict[str, Valeur]) -> Verdict | None:
    """Section 6 — la viabilisation (faisceau d'indices). Confirmée/probable → bonne nouvelle."""
    v = _val(valeurs, "viabilisation_verdict")
    if not isinstance(v, dict) or not v.get("libelle"):
        return None
    # RECETTE-7 (E5) — plus de phrase qui s'affirme et se dément (« viabilisation confirmée —
    # aucun tracé n'est relevé »). On sépare le CONSTAT (le verdict), ce qui n'est PAS constaté
    # (le tracé/capacité exacts) et l'ACTION (DT-DICT).
    confirmee = v.get("band") in ("confirmee", "probable")
    ton = "" if confirmee else "neutral"
    suite = ("le tracé et la capacité exacts des réseaux ne sont pas relevés à cette échelle : à "
             "confirmer auprès des gestionnaires par une DT-DICT" if confirmee else
             "aucun raccordement n'est établi par les indices : réseaux à vérifier auprès des "
             "gestionnaires par une DT-DICT")
    return (f"{v['libelle']} — {suite}.", ton, "")


def rendu_verdict(v: Verdict | None) -> str:
    """Le fragment HTML d'un verdict, ou '' si la section n'a rien à conclure."""
    if v is None:
        return ""
    from .rendu import verdict as _box
    texte, ton, petit = v
    return _box(texte, ton, petit)
