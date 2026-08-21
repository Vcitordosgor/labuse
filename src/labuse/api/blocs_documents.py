"""M73-C/M73-D — le rendu PARTAGÉ des blocs ASSAINISSEMENT et RÉHABILITATION pour les documents.

Le texte servi et sa logique d'états sont produits **UNE fois**, sous une forme NEUTRE (`anc_bloc`,
`rehab_bloc` → dict {titre, etat, statut, lignes:[(role, texte)]}). Chaque média se contente de la
POSER : `anc_bloc_html`/`rehab_bloc_html` pour la famille WeasyPrint (dossier/banquier/
argumentaire), et le premium fpdf itère les mêmes `lignes` (aucune reformulation — c'est ce qui a produit
la divergence que M73-C/D réparent). AUCUN recalcul ici : on rend ce que les helpers UNIQUES servent
(`anc_service.statut_anc`, `compute_mode_b`).

La DA (classes, couleurs, filets, gras d'accent) viendra au Volet A — ICI, du CONTENU DA-neutre :
états, maille et millésime EXPLICITES. Doctrine : Sourcé / Sourcé secteur / Absent ; jamais un verdict ;
la maille est NOMMÉE visiblement (pas en note) ; un taux bas n'est pas un feu vert ; un zéro n'est pas
une absence (l'absence de potentiel s'affiche, le bloc ne se masque jamais).
"""
from __future__ import annotations

import html

#: libellé d'état ANC (dérivé du statut servi par anc_service — jamais un verdict).
_ANC_LABEL = {"source": "Sourcé", "source_secteur": "Sourcé secteur",
              "source_commune": "Sourcé commune", "absent": "Absent"}   # M95 — 3e échelle Sourcé

# M73-G — l'HABILLAGE DA des blocs, écrit UNE fois (maquette DA-PDF-v2 .carte/.chef/.past), injecté dans
# les deux points CSS WeasyPrint (rapport.css via report.py, briques_pdf via render_pdf). Cartouche fond
# SURFACE + filet, titre + pastille d'état colorée par le statut (le TEXTE de l'état porte le sens →
# distinguable en N&B), réserves ≥ 8 pt. Utilise les variables déjà définies dans chaque CSS.
BLOC_CSS = """
.bloc { background: var(--surface); border: 1px solid var(--line); border-radius: 6px;
        padding: 9px 12px; margin: 8px 0; break-inside: avoid; }
.bloc-tete { display: flex; align-items: baseline; justify-content: space-between; gap: 10px;
             margin-bottom: 4px; }
.bloc-titre { font-size: 11pt; font-weight: 600; color: var(--txt-hi); }
.bloc-etat { font-family: 'JetBrains Mono', monospace; font-size: 7.5pt; text-transform: uppercase;
             letter-spacing: .05em; padding: 1px 7px; border-radius: 9px; white-space: nowrap;
             color: var(--txt-dim); background: #EEF1EF; }
.bloc-etat[data-etat="source"], .bloc-etat[data-etat="source_secteur"],
.bloc-etat[data-etat="source_commune"],
.bloc-etat[data-etat="dispo"] { color: var(--mint); background: var(--mint-soft); }
.bloc-etat[data-etat="trop_petit"] { color: var(--amber); background: #F6EEDD; }
.bloc-libelle { font-size: 9.5pt; font-weight: 600; color: var(--txt); margin: 3px 0 1px; }
.bloc-maille, .bloc-phrase, .bloc-ligne { font-size: 8.5pt; color: var(--txt-mut);
             line-height: 1.45; margin: 2px 0; }
.bloc-phrase strong { color: var(--txt-hi); font-weight: 600; }
.bloc-source { font-size: 8pt; color: var(--txt-dim); margin: 2px 0; }
"""


# ── FORME NEUTRE (le texte servi, produit une fois) ──────────────────────────────────────────────
def anc_bloc(anc: dict | None) -> dict | None:
    """Structure NEUTRE du bloc assainissement — consommée par HTML ET fpdf. Rend l'état servi par
    `anc_service.statut_anc`, jamais un verdict. Pour le Sourcé secteur, la MAILLE (secteur IRIS nommé
    ou commune) et le MILLÉSIME sont des lignes EXPLICITES, jamais reléguées. Renvoie None seulement si
    `anc` est None (jamais pour Absent — l'absence est un état affiché)."""
    if not anc:
        return None
    statut = str(anc.get("statut", "absent"))
    lignes: list[tuple[str, str]] = []
    if anc.get("libelle"):
        lignes.append(("libelle", str(anc["libelle"])))
    if statut == "source_secteur":                       # maille + millésime NOMMÉS visiblement
        maille = str(anc.get("maille") or "secteur")
        mille = str(anc.get("millesime") or "RP2022")
        lignes.append(("maille", f"Maille : {maille} · millésime : {mille}"))
    elif statut == "source_commune":                     # M95 — échelle COMMUNE dite, jamais confondue
        mille = str(anc.get("millesime") or "")
        lignes.append(("maille", f"Échelle : commune entière · millésime : {mille}"))
    if anc.get("phrase"):
        lignes.append(("phrase", str(anc["phrase"])))
    if anc.get("source"):
        lignes.append(("source", str(anc["source"])))
    return {"cls": "anc", "titre": "Assainissement", "statut": statut,
            "etat": _ANC_LABEL.get(statut, "Absent"), "lignes": lignes}


def rehab_bloc(mode_b: dict | None) -> dict:
    """Structure NEUTRE du bloc réhabilitation — consommée par HTML ET fpdf. Rend `compute_mode_b`,
    jamais recalculé. L'absence de potentiel est un état AFFICHÉ (« Non évaluée »), le bloc ne se masque
    JAMAIS (un zéro n'est pas une absence)."""
    mb = mode_b or {}
    if mb.get("indisponible"):
        # M125 (boussole) — PANNE technique ≠ absence : ne jamais afficher « donnée manquante » quand
        # la cause est une exception. État distinct, rendu en clair sur tous les médias.
        return {"cls": "rehab", "titre": "Réhabilitation", "statut": "indisponible", "etat": "Indisponible",
                "lignes": [("phrase", "Donnée indisponible — erreur technique. Le calcul n'a pas abouti "
                                      "(incident) ; ce n'est pas une absence de donnée.")]}
    if not mb.get("disponible"):
        # M73-E — distinguer le PÉRIMÈTRE MÉTIER (hors population mode B, réservé au bâti déclassé : la
        # réhab est « sans objet », pas un trou) de la donnée manquante (« Absent »). Mesuré : 92 % des
        # parcelles sont hors population (cf. AUDIT_M73E_REHAB) → libellé explicite, jamais masqué.
        motif = str(mb.get("motif") or "").strip()
        hors_pop = "hors population" in motif.lower()
        if hors_pop:
            return {"cls": "rehab", "titre": "Réhabilitation", "statut": "sans_objet", "etat": "Sans objet",
                    "lignes": [("phrase", "Réhabilitation sans objet : cette parcelle n'est pas déclassée "
                                          "pour cause de bâti — la thèse de réhabilitation ne s'y applique pas.")]}
        return {"cls": "rehab", "titre": "Réhabilitation", "statut": "absent", "etat": "Absent",
                "lignes": ([("phrase", str(mb["porte"]))] if mb.get("porte") else [])   # M101 A2
                + [("phrase", motif or "Potentiel de réhabilitation non évaluable (donnée manquante).")]}
    # M101 A2 — la PORTE du mode B (pourquoi cette parcelle est « bâtie » : phrase lisible de
    # compute_mode_b, calée sur la règle mesurée, jamais du jargon) ouvre le bloc quand elle existe.
    porte_ligne: list[tuple[str, str]] = [("phrase", str(mb["porte"]))] if mb.get("porte") else []
    if mb.get("trop_petit"):                              # bâti trop petit → DIT (M59-P1 Q4)
        return {"cls": "rehab", "titre": "Réhabilitation", "statut": "trop_petit", "etat": "Estimé",
                "lignes": porte_ligne
                + [("phrase", str(mb.get("motif", "Bâti trop petit pour une thèse de réhabilitation.")))]}
    lignes: list[tuple[str, str]] = list(porte_ligne)
    if mb.get("negatif"):
        lignes.append(("phrase_forte", str(mb.get("message_negatif", ""))))
    elif mb.get("achat_max_libelle"):
        fonc = f" — le foncier ({mb['surface_parcelle_m2']} m²) s’ajoute" if mb.get("surface_parcelle_m2") else ""
        lignes.append(("phrase", f"Ce que la réhabilitation du bâti justifie (Estimé) : "
                                 f"~{mb['achat_max_libelle']} — hors valeur du terrain{fonc}."))
    tn = mb.get("terrain_nu")
    if tn:
        lignes.append(("ligne", f"Terrain nu au prix du secteur : ~{tn.get('valeur_libelle', '')} "
                                f"({tn.get('prix_m2', '')} €/m² × {tn.get('surface_m2', '')} m² · Estimé)"))
    if mb.get("porte_par_terrain"):
        lignes.append(("phrase_forte", "À ces hypothèses, la valeur de cette parcelle est portée "
                                       "par le terrain, pas par le bâti."))
    return {"cls": "rehab", "titre": "Réhabilitation", "statut": "dispo", "etat": "Estimé", "lignes": lignes}


# ── RENDU HTML (famille WeasyPrint) — pose la forme neutre, sans la reformuler ────────────────────
def _bloc_html(bloc: dict | None) -> str:
    if not bloc:
        return ""
    def e(s):                                            # texte : quote=False (apostrophe lisible)
        return html.escape(str(s), quote=False)
    cls, statut = bloc["cls"], bloc["statut"]
    attr = f'data-{cls}-statut="{e(statut)}"' if cls == "anc" else f'data-rehab="{e(statut)}"'
    out = [f'<div class="bloc bloc-{cls}" {attr}>',
           f'<div class="bloc-tete"><span class="bloc-titre">{e(bloc["titre"])}</span>'
           f'<span class="bloc-etat" data-etat="{e(statut)}">{e(bloc["etat"])}</span></div>']
    for role, texte in bloc["lignes"]:
        if role == "phrase_forte":
            out.append(f'<p class="bloc-phrase"><strong>{e(texte)}</strong></p>')
        else:
            out.append(f'<p class="bloc-{e(role)}">{e(texte)}</p>')
    out.append("</div>")
    return "".join(out)


def anc_bloc_html(anc: dict | None) -> str:
    """Bloc assainissement en HTML (WeasyPrint). '' seulement si `anc` est None."""
    return _bloc_html(anc_bloc(anc))


def rehab_bloc_html(mode_b: dict | None) -> str:
    """Bloc réhabilitation en HTML (WeasyPrint). Jamais vide (l'absence est un état affiché)."""
    return _bloc_html(rehab_bloc(mode_b))
