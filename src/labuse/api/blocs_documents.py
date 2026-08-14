"""M73-C — le rendu PARTAGÉ des blocs ASSAINISSEMENT et RÉHABILITATION pour les documents.

Écrit UNE fois (règle commune M73-C) : la famille WeasyPrint (dossier / banquier / argumentaire /
one-pager) appelle ces builders ; le premium fpdf a son propre rendu (même contenu, autre média). AUCUN
recalcul ici — on REND ce que les helpers UNIQUES servent (`anc_service.statut_anc`, `compute_mode_b`).

La DA (classes, couleurs, filets) viendra au Volet A — ICI, du HTML de CONTENU, DA-neutre : états,
maille et millésime EXPLICITES. Doctrine : Sourcé / Sourcé secteur / Absent ; jamais un verdict ; la
maille est NOMMÉE visiblement (pas en note de bas de bloc) ; un taux bas n'est pas un feu vert ; un
zéro n'est pas une absence (l'absence de potentiel s'affiche, le bloc ne se masque jamais).
"""
from __future__ import annotations

import html

#: libellé d'état ANC (dérivé du statut servi par anc_service — jamais un verdict).
_ANC_LABEL = {"source": "Sourcé", "source_secteur": "Sourcé secteur", "absent": "Absent"}


def anc_bloc_html(anc: dict | None) -> str:
    """Bloc assainissement (contenu, DA-neutre). Rend l'état servi par `anc_service.statut_anc` — jamais
    un verdict. Pour le Sourcé secteur, la MAILLE (secteur IRIS nommé ou commune) et le MILLÉSIME sont
    affichés en clair, jamais relégués : un taux de commune et un taux d'IRIS n'ont pas la même valeur,
    le document le dit. Retourne '' seulement si `anc` est None (jamais pour Absent — l'absence est un
    état affiché)."""
    if not anc:
        return ""
    # texte : quote=False (l'apostrophe française reste lisible ; les valeurs d'attribut sont des
    # énumérations contrôlées — statut ∈ {source, source_secteur, absent} — sans caractère spécial).
    def e(s):
        return html.escape(str(s), quote=False)
    statut = str(anc.get("statut", "absent"))
    label = _ANC_LABEL.get(statut, "Absent")
    parts = [f'<div class="bloc bloc-anc" data-anc-statut="{e(statut)}">',
             f'<div class="bloc-tete"><span class="bloc-titre">Assainissement</span>'
             f'<span class="bloc-etat" data-etat="{e(statut)}">{e(label)}</span></div>']
    if anc.get("libelle"):
        parts.append(f'<p class="bloc-libelle">{e(str(anc["libelle"]))}</p>')
    # Sourcé secteur : la maille et le millésime NOMMÉS visiblement (jamais en note).
    if statut == "source_secteur":
        maille = str(anc.get("maille") or "secteur")
        mille = str(anc.get("millesime") or "RP2022")
        parts.append(f'<p class="bloc-maille">Maille : <b>{e(maille)}</b> · millésime : <b>{e(mille)}</b></p>')
    if anc.get("phrase"):
        parts.append(f'<p class="bloc-phrase">{e(str(anc["phrase"]))}</p>')
    if anc.get("source"):
        parts.append(f'<p class="bloc-source">{e(str(anc["source"]))}</p>')
    parts.append("</div>")
    return "".join(parts)


def rehab_bloc_html(mode_b: dict | None) -> str:
    """Bloc réhabilitation (contenu, DA-neutre). Rend `compute_mode_b` — jamais recalculé. L'absence de
    potentiel est AFFICHÉE (un zéro n'est pas une absence) : le bloc ne se masque JAMAIS."""
    mb = mode_b or {}

    def e(s):
        return html.escape(str(s), quote=False)

    def _tete(etat: str) -> str:
        return ('<div class="bloc-tete"><span class="bloc-titre">Réhabilitation</span>'
                f'<span class="bloc-etat" data-etat="{e(etat)}">{e(etat)}</span></div>')

    if not mb.get("disponible"):                                  # non évaluée → DITE, jamais masquée
        return ('<div class="bloc bloc-rehab" data-rehab="indispo">' + _tete("Non évaluée")
                + '<p class="bloc-phrase">Potentiel de réhabilitation non évalué sur cette parcelle.</p></div>')

    parts = ['<div class="bloc bloc-rehab" data-rehab="dispo">', _tete("Estimé")]
    if mb.get("trop_petit"):                                      # bâti trop petit → DIT (M59-P1 Q4)
        parts.append(f'<p class="bloc-phrase">{e(str(mb.get("motif", "Bâti trop petit pour une thèse de réhabilitation.")))}</p>')
        parts.append("</div>")
        return "".join(parts)

    if mb.get("negatif"):
        parts.append(f'<p class="bloc-phrase"><b>{e(str(mb.get("message_negatif", "")))}</b></p>')
    elif mb.get("achat_max_libelle"):
        fonc = f' ({e(str(mb["surface_parcelle_m2"]))} m²)' if mb.get("surface_parcelle_m2") else ""
        parts.append('<p class="bloc-phrase">Ce que la réhabilitation du bâti justifie (Estimé) : '
                     f'<b>~{e(str(mb["achat_max_libelle"]))}</b> — hors valeur du terrain'
                     f'{" — le foncier" + fonc + " s’ajoute" if fonc else ""}.</p>')
    tn = mb.get("terrain_nu")
    if tn:
        parts.append(f'<p class="bloc-ligne">Terrain nu au prix du secteur : ~{e(str(tn.get("valeur_libelle", "")))} '
                     f'({e(str(tn.get("prix_m2", "")))} €/m² × {e(str(tn.get("surface_m2", "")))} m² · Estimé)</p>')
    if mb.get("porte_par_terrain"):
        parts.append('<p class="bloc-ligne"><b>À ces hypothèses, la valeur de cette parcelle est '
                     'portée par le terrain, pas par le bâti.</b></p>')
    parts.append("</div>")
    return "".join(parts)
