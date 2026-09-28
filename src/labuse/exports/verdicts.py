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


def zone_libelle(valeurs: dict[str, Valeur]) -> str | None:
    """RECETTE-8 W15 — LE libellé de zone servi à TOUS les documents : « Zone Um (famille U) », le
    CODE réel (secteur) + sa famille, jamais un « Zone U » tronqué (E3). Point unique : le Dossier
    (verdict de zonage) ET l'Apporteur lisent ce même libellé — une donnée, une réponse. None si la
    zone n'est pas déterminée. Le code exact vient de `reglement_plu_bloc.zone`, la famille de
    `zone_plu_famille` (repli : la famille seule si le code n'est pas lisible)."""
    fam = _val(valeurs, "zone_plu_famille")
    if not fam:
        return None
    fam = str(fam).upper()
    reg = _val(valeurs, "reglement_plu_bloc")
    code = (reg.get("zone") if isinstance(reg, dict) else None) or fam
    return f"Zone {code}" + (f" (famille {fam})" if str(code).strip().upper() != fam else "")


def verdict_zonage(valeurs: dict[str, Valeur]) -> Verdict | None:
    """Section 2 — la famille de la zone DOMINANTE (zone_servie) conclut : constructible ou non,
    cause dite. Rien à dire si la zone n'est pas déterminée (le bloc omet le verdict)."""
    fam = _val(valeurs, "zone_plu_famille")
    if not fam:
        return None
    fam = str(fam).upper()
    # RECETTE-7 (E3) / RECETTE-8 (W15) — le CODE DE ZONE réel (ex. « Um ») pour coller aux articles
    # cités (« Art. Um.9 »), via le libellé PARTAGÉ avec l'Apporteur (une donnée, une réponse).
    lib = zone_libelle(valeurs) or f"Zone {fam}"
    if fam in _NON_CONSTRUCTIBLE:
        # EXPORTS-FIX-1 C8 — verdict COHÉRENT avec la liste des destinations : la zone A/N liste des
        # destinations « sous conditions » (logement d'exploitant, etc.). On ne dit donc plus un
        # « potentiel nul » sec qui contredit le tableau ; on dit la restriction réelle.
        return (f"{lib} — {_NON_CONSTRUCTIBLE[fam]}, <strong>non constructible pour un projet "
                f"d'habitat courant</strong>. Seules les destinations liées à la vocation "
                f"{_NON_CONSTRUCTIBLE[fam]} sont admises, et sous conditions (voir la liste "
                f"des destinations ci-dessous).", "warn", "")
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
        # EXPORTS-FIX-1 B1 — la « SDP restante » de la page de garde (sdp_residuelle_m2) est aussi
        # dite au §10, MÊME valeur, avec ce qu'elle mesure : une surface de PLANCHER résiduelle
        # (droits à bâtir non consommés), distincte de la « surface de plancher créée (table rase) ».
        extra = ""
        if sdp is not None and float(sdp) > 0:
            from .registre_fmt import fmt_m2
            extra = f" — SDP résiduelle (droits à bâtir non consommés) ≈ {fmt_m2(float(sdp))}"
        return (f"Potentiel de construction : {libelle}{extra}.", "", "")
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
    # EXPORTS-FIX-1 A8 / BIS point 11 — la viabilisation est un FAISCEAU d'indices (un score, étiqueté
    # « estimé ») : le mot suit l'étiquette → « probable », jamais « confirmée » (un score ne confirme
    # rien). On retire aussi le langage interne « par les faits ».
    lib = (str(v['libelle']).replace(" confirmée par les faits", " probable")
           .replace(" confirmée", " probable"))
    return (f"{lib} — {suite}.", ton, "")


def rendu_verdict(v: Verdict | None) -> str:
    """Le fragment HTML d'un verdict, ou '' si la section n'a rien à conclure."""
    if v is None:
        return ""
    from .rendu import verdict as _box
    texte, ton, petit = v
    return _box(texte, ton, petit)
