"""DOCS-1 (Lot C) — bloc « Comparatif » : 2 à 3 parcelles EN COLONNES sur les lignes de Comparer, en
page paysage. Aucun calcul : on rend les CompareRow servis par /compare (le MÊME endpoint que l'écran).
Badges Sourcé/Estimé par ligne et ligne « Classement LABUSE » comme à l'écran. CHASSE-INVARIANTS-FIX-1
(Lot 1, E-01) : le « Taux d'occupation du gabarit » passe par le rendu unique `fmt_taux_emprise`
(au-delà de 100 % → « Saturé … », jamais un % brut — c'était le 19 569 % de l'export) ; écran et PDF
rendent donc la même chaîne."""
from __future__ import annotations

import re

from ...faisabilite.residuel import fmt_taux_emprise
from ..registre_fmt import groupe
from ..rendu import chip_span, esc, section

#: DOCS-1 (décision Vic) — un seul format de décimale (virgule) imposé à la sortie du bloc, même motif
#: que le banc détecte (« \d.\d » suivi de m/€/%/m²) : couvre les chaînes SERVIES par /compare (accès &
#: réseaux, assainissement, contrainte majeure) sans dupliquer un formateur par champ.
_RX_DEC_SORTIE = re.compile(r"\b(\d+)\.(\d+)([   ]*(?:m²|m|€|%))\b")


def _virgule_sortie(html: str) -> str:
    return _RX_DEC_SORTIE.sub(lambda m: f"{m.group(1)},{m.group(2)}{m.group(3)}", html)


def _i(v):   # entier groupé (séparateur de milliers)
    return groupe(round(v)) if isinstance(v, (int, float)) else None


def _oui_non(v):
    return None if v is None else ("oui" if v else "non")


def _ref_courte(idu: str) -> str:
    return f"{idu[8:10]} {idu[10:14]}" if idu and len(idu) >= 14 else (idu or "")


def _classement(r) -> str | None:
    # BANDES-UNIFIEES (fix/logements-source-unique) — UN SEUL libellé de bande, celui de la fiche :
    # « lettre · libellé client · Signal X » (vocabulaire_client du barème = BANDE_META front,
    # NIVEAU_LABELS = SIGNAL_META front). Avant : « C · signal faible » (lettre + slug brut) au PDF
    # vs « À étudier » + « Signal faible » à l'écran — deux rendus pour la même donnée.
    bande = r.get("bande")
    if not bande:
        return None
    from ...scoring.signal_mutation import NIVEAU_LABELS
    lib = _libelle_bande(str(bande))
    # DOCS-1 (décision Vic) — une bande « lettre » (A–D) s'écrit « lettre · libellé » ; une bande NON
    # lettre (« 0 » = écartée) ne fait pas précéder son libellé d'un « 0 · » de cuisine (« 0 · Non
    # retenue ») : on affiche le seul libellé client.
    if str(bande).isdigit():
        txt = lib or str(bande)
    else:
        txt = f"{bande} · {lib}" if lib and lib != str(bande) else str(bande)
    sig = NIVEAU_LABELS.get(str(r.get("signal_niveau") or ""))
    return esc(txt + (f" · {sig}" if sig else ""))


def _libelle_bande(bande: str) -> str:
    """Libellé CLIENT d'une bande — la MÊME source que la fiche (barème `vocabulaire_client`,
    miroir de frontend/src/lib/status.ts › BANDE_META). « HC » (écartée en dur, E-10) n'est pas
    au barème (catégorie hors score) : libellé front repris ici, à garder synchrone."""
    if bande == "HC":
        return "Hors classement"
    from ...scoring.score_labuse import charger_bareme, libelle_client_bande
    try:
        bareme, _sha = charger_bareme()
        return libelle_client_bande(bande, bareme)
    except Exception:  # noqa: BLE001 — barème illisible : la lettre seule, jamais un crash de PDF
        return bande


def _m2(r, k):
    x = _i(r.get(k))
    return f"{x} m²" if x else None


_CAUSE_COURT = {
    "terrain_exigu": "terrain exigu", "hors_plu": "hors PLU", "redhibitoire": "rédhibitoire",
    "capacite_nulle": "capacité nulle", "bati_non_ingere": "bâti non estimé",
    "assiette_a_verifier": "assiette à vérifier",   # EXIGU-FIX-1 — ignorance, jamais « trop étroit »
}


def _cause_court(c):
    # RECETTE-PROD-1 (12) — tag COURT de la cause (même règle qu'à l'écran ComparePanel).
    if not c:
        return None
    if c.startswith("zone_non_constructible") or c.startswith("zone_non_resolue"):
        return "zone non constructible"
    return _CAUSE_COURT.get(c, c.replace("_", " "))


def _sdp_residuelle_cause(r):
    # RECETTE-PROD-1 (12) — potentiel résiduel + CAUSE COURTE quand il n'y en a pas (0/None) :
    # « 0 m² · terrain exigu » / « — · zone non constructible » plutôt qu'un « 0 » muet.
    x = _i(r.get("sdp_residuelle_m2"))
    if x:
        return f"{x} m²"
    base = "0 m²" if r.get("sdp_residuelle_m2") == 0 else "—"
    sc = _cause_court(r.get("cause"))
    return esc(f"{base} · {sc}") if sc else (base if base != "—" else None)


def _eur_m2(r, k):
    x = _i(r.get(k))
    return f"{x} €/m²" if x else None


def _terrain_prix_ventes(r):
    """DOCS-COHERENCE-1 (recette Vic) — MÊME règle et MÊME seuil que le Dossier §8 : sous le seuil
    d'échantillon, « — (N ventes, échantillon insuffisant) » et le chiffre €/m² DISPARAÎT ; au-dessus,
    le prix + ses ventes."""
    from ...dvf_mediane import SEUIL_N
    n = r.get("prix_terrain_n")
    if n is not None and int(n) < SEUIL_N:
        return f"— ({_i(n)} ventes, échantillon insuffisant)"
    x = _i(r.get("terrain_zone_eur_m2"))
    if not x:
        return None
    return f"{x} €/m² — {_i(n)} ventes" if n else f"{x} €/m²"


def _eur_m2_ventes(r, k, n_key, rayon_key=None):
    """DOCS-COHERENCE-1 (A8) — prix au m² SUIVI du nombre de ventes qui le fonde (« n ventes à moins
    de R m »), jamais un prix nu. Sans ventes servies, le prix reste seul (pas de « 0 vente » inventé)."""
    x = _i(r.get(k))
    if not x:
        return None
    n = r.get(n_key)
    if n:
        rayon = r.get(rayon_key) if rayon_key else None
        ou = f" à moins de {_i(rayon)} m" if rayon else ""
        return f"{x} €/m² — {_i(n)} vente{'s' if int(n) > 1 else ''}{ou}"
    return f"{x} €/m²"


def _pct(r, k, suffixe="%"):
    x = _i(r.get(k))
    return f"{x} {suffixe}" if x is not None else None


def _bati_existant(r):
    """EXPORTS-FIX-3 LOT 3 (#5) — UNE valeur de bâti, celle de la fiche (etat_bien). Non mesuré
    (trace aérienne seule) → « bâti détecté, à vérifier » (jamais « 1 % » là où la fiche ne mesure
    aucun bâtiment, faute B1). Terrain nu → « aucun ». Mesuré → part du terrain."""
    etat = r.get("bati_etat")
    if etat == "non_mesure":
        return "bâti détecté, à vérifier"
    if etat == "nu":
        return "aucun"
    pct = r.get("bati_existant_pct")
    if pct is None:
        return None
    return "aucun" if pct <= 0 else f"{_i(pct)} % du terrain"


# Les lignes de Comparer, DANS L'ORDRE de l'écran : (label, prov, fn(row)->str|None). prov=None → ligne
# « Classement LABUSE » (aucun badge, comme à l'écran).
# RETOURS-29 (Comparatif v2, maquette 15) — le PDF suit le MÊME CONTENU que l'écran : mêmes lignes (dans
# le même ordre), mêmes badges sourcé/estimé. Plus de classement LABUSE, de prix de marché, de logements.
_PROPRIO = {"morale": "personne morale", "public": "public", "particulier": "particulier",
            "succession": "succession", "indivision": "indivision"}
_LIGNES = [
    # TERRAIN
    ("Surface", "s", lambda r: _m2(r, "surface_m2")),
    ("Bâti existant", "s", lambda r: _bati_existant(r)),
    ("Propriétaire", "s", lambda r: _PROPRIO.get(r.get("proprietaire"))),
    # URBANISME
    ("Hauteur autorisée", "s", lambda r: ((f"R+{max(0, int(r['gabarit_niveaux_max']) - 1)}"
                                           + (" + combles" if r.get("gabarit_combles") else ""))
                                          if r.get("gabarit_niveaux_max") is not None else None)),
    # OUTILS-P1-1 (pt 3) — même règle qu'à l'écran : « PLU sans plafond d'emprise » seulement si une
    # règle est identifiée (silence prouvé), sinon « Règle non renseignée ».
    ("Emprise au sol maximale", "s", lambda r: (_pct(r, "emprise_ces_pct")
        or ("PLU sans plafond d'emprise" if r.get("emprise_ces_etat") == "sans_plafond"
            else "Règle non renseignée"))),
    # POTENTIEL CONSTRUCTIBLE
    ("Plancher possible · bâti conservé", "e", lambda r: _sdp_residuelle_cause(r)),
    ("Plancher possible · reconstruction", "e", lambda r: _m2(r, "sdp_max_m2")),
    ("Part du gabarit déjà occupée", "e", lambda r: esc(fmt_taux_emprise(r.get("taux_emprise_pct")))),
    # CHASSE-DOCS-FIX-1 (Lot 5) — charge foncière NÉGATIVE : chiffre + explication, jamais un « -59 €/m² » nu.
    # EXPORTS-FIX-3 LOT 2 (#7) — la charge foncière DIT sa surface de référence (« par m² de terrain ») ;
    # ses hypothèses sont données en note sous le tableau (sinon on ne l'affiche pas).
    ("Charge foncière", "e", lambda r: ((f"{_i(r.get('charge_fonciere_m2'))} €/m² de terrain"
        + (" — bilan déficitaire : à ces hypothèses, le foncier ne se paie pas"
           if (r.get("charge_fonciere_m2") or 0) < 0 else ""))
        if (r.get("charge_fonciere_m2") is not None and r.get("bilan_hypotheses")) else None)),
    # RISQUES ET CONTRAINTES
    # OUTILS-P1-1 (pt 3) — statistique de SECTEUR préfixée « Secteur : » (comme à l'écran).
    ("Assainissement", "s", lambda r: (f"Secteur : {esc(r.get('assainissement'))}"
                                       if r.get("assainissement") else None)),
    ("Contraintes relevées", "s", lambda r: (" · ".join(esc(c) for c in (r.get("contraintes") or []))
                                             if (r.get("contraintes") or []) else "aucune relevée")),
]

_BADGE = {"s": ("s", "sourcé"), "e": ("e", "estimé")}

# EXPORTS-FIX-3 LOT 2 — lignes de CAPACITÉ / BILAN : sur une parcelle NON CONSTRUCTIBLE (verdict de
# la fiche), elles ne s'affichent pas (« — »). Le mandat : « sans surface de plancher, hauteur, bilan
# ni charge foncière ». La ligne « Emprise au sol maximale » reste (c'est une RÈGLE de zonage, pas une
# capacité). Un verdict « Non constructible — <motif> » est affiché à part (voir `rendu`).
_LIGNES_CAPACITE = {"Hauteur autorisée", "Plancher possible · bâti conservé",
                    "Plancher possible · reconstruction", "Part du gabarit déjà occupée",
                    "Charge foncière"}


def _est_non_constructible(r) -> bool:
    """EXPORTS-FIX-3 LOT 2 — la parcelle est-elle non constructible AU SENS DE LA FICHE ?
    `constructible is False` = verdict ferme de `potentiel_batir` ; None (indéterminé) ne masque rien."""
    return r.get("constructible") is False


def _ligne_verdict(rows) -> str:
    """Ligne « Constructibilité » : « Non constructible — <motif> » (la MÊME raison que la fiche) ou
    « Constructible », sur chaque colonne. Rendue seulement si au moins une parcelle est non
    constructible (sinon le tableau reste comme avant)."""
    if not any(_est_non_constructible(r) for r in rows):
        return ""
    cells = ""
    for r in rows:
        if _est_non_constructible(r):
            motif = esc(r.get("verdict_motif") or r.get("cause_libelle") or "zone non constructible")
            cells += f'<td><strong>Non constructible</strong> — {motif}</td>'
        elif r.get("constructible") is True:
            cells += "<td>Constructible</td>"
        else:
            cells += "<td>—</td>"
    return f'<tr><td class="lbl">Constructibilité</td>{cells}</tr>'


def rendu(rows) -> str:
    rows = list(rows or [])[:3]
    if not rows:
        return section("Comparatif", "<p>Aucune parcelle comparable.</p>")
    # RETOURS-29 (maquette 15) — en-tête : IDU · adresse (aperçu parcelle) · zone + surface, comme l'écran.
    def _col(r):
        idu = esc(r.get("idu", ""))
        adr = esc(r.get("adresse")) if r.get("adresse") else (esc(r.get("commune")) if r.get("commune") else "")
        zs = " · ".join(x for x in [esc(r.get("zone")) if r.get("zone") else None,
                                    (f'{_i(r.get("surface_m2"))} m²' if r.get("surface_m2") is not None else None)] if x)
        sub = (f'<div class="sub">{adr}</div>' if adr else "") + (f'<div class="sub">{zs}</div>' if zs else "")
        return f"<th>{idu}{sub}</th>"
    thead = "<tr><th></th>" + "".join(_col(r) for r in rows) + "</tr>"
    # EXPORTS-FIX-3 LOT 2 — verdict de constructibilité en tête du corps (avant l'urbanisme) : la même
    # raison que la fiche, sans jamais un plancher/bilan flatteur sur une parcelle non constructible.
    body = _ligne_verdict(rows)
    for label, prov, fn in _LIGNES:
        badge = ""
        if prov in _BADGE:
            cls, lib = _BADGE[prov]
            badge = chip_span(cls, lib)
        cells = ""
        for r in rows:
            # EXPORTS-FIX-3 LOT 2 — parcelle non constructible : aucune capacité/bilan dans sa colonne.
            if label in _LIGNES_CAPACITE and _est_non_constructible(r):
                cells += "<td>—</td>"
                continue
            v = fn(r)
            cells += f"<td>{v if v is not None else '—'}</td>"
        body += f'<tr><td class="lbl">{esc(label)}{badge}</td>{cells}</tr>'
    # RECETTE-OUTILS-2 (R18) — la note de bas de page « Maximum réglementaire (gabarit) … (0,46 en
    # surface, 0,40 en logements) » est RETIRÉE du Comparatif PDF, pour être identique à l'outil où elle
    # a déjà été retirée (décision Vic). Le plafond réglementaire reste dit par la fiche / l'Étude.
    # DOCS-1 (décision Vic) — titre + tableau forment UN bloc qui ne se coupe pas : s'il ne tient pas
    # sous la carte en page 1, l'ensemble (jamais le titre seul) passe en page 2 (`.cmp-bloc`).
    corps = f'<table class="cmp"><thead>{thead}</thead><tbody>{body}</tbody></table>'
    # EXPORTS-FIX-3 LOT 2 (#7) — si au moins une charge foncière est affichée, on DONNE ses hypothèses
    # et sa surface de référence (sinon le chiffre ne serait pas interprétable) : note sous le tableau.
    note_bilan = ""
    _avec_charge = [r for r in rows if r.get("charge_fonciere_m2") is not None and r.get("bilan_hypotheses")]
    if _avec_charge:
        hyps = _avec_charge[0].get("bilan_hypotheses") or []
        lis = "".join(f"<li>{esc(str(h))}</li>" for h in hyps)
        note_bilan = ('<p class="anote"><strong>Charge foncière</strong> = résultat du bilan '
                      'promoteur rapporté au m² de terrain (indicatif). Hypothèses du bilan :</p>'
                      f'<ul class="anote">{lis}</ul>')
    bloc = f'<section class="cmp-bloc"><h2>Comparatif</h2>{corps}{note_bilan}</section>'
    return _virgule_sortie(bloc)
