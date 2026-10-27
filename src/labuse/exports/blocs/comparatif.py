"""DOCS-1 (Lot C) — bloc « Comparatif » : 2 à 3 parcelles EN COLONNES sur les lignes de Comparer, en
page paysage. Aucun calcul : on rend les CompareRow servis par /compare (le MÊME endpoint que l'écran).
Badges Sourcé/Estimé par ligne et ligne « Classement LABUSE » comme à l'écran. CHASSE-INVARIANTS-FIX-1
(Lot 1, E-01) : le « Taux d'occupation du gabarit » passe par le rendu unique `fmt_taux_emprise`
(au-delà de 100 % → « Saturé … », jamais un % brut — c'était le 19 569 % de l'export) ; écran et PDF
rendent donc la même chaîne."""
from __future__ import annotations

from ...faisabilite.residuel import fmt_taux_emprise
from ..registre_fmt import groupe
from ..rendu import chip_span, esc, section


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


# Les lignes de Comparer, DANS L'ORDRE de l'écran : (label, prov, fn(row)->str|None). prov=None → ligne
# « Classement LABUSE » (aucun badge, comme à l'écran).
_LIGNES = [
    ("Surface", "s", lambda r: _m2(r, "surface_m2")),
    # DOCS-FIX-1 (P5) — jamais « — » : la zone vient de zone_dominante (servie par /compare, comme la
    # fiche) ; si aucune zone PLU ne couvre la parcelle, on écrit la RAISON en clair, pas un tiret.
    ("Zone PLU", "s", lambda r: esc(r.get("zone")) if r.get("zone") else "hors zonage PLU"),
    ("Classement LABUSE", None, _classement),
    # RECETTE-PROD-1 (12) — « Constructible : oui/non » (verdict faisabilité) mentait (zone
    # constructible mais 0 potentiel résiduel = « oui » trompeur). On sert la constructibilité de
    # ZONE (famille ∉ A/N), le potentiel vivant sur la ligne « SDP résiduelle » suffixée de sa cause.
    ("Zone constructible", "s", lambda r: _oui_non(r.get("zone_constructible"))),
    # IMPLANTATION-4 (LOT C) — SDP de l'ancien moteur = « SDP maximale réglementaire » (jamais « du
    # scénario », réservé à l'Étude) ; même libellé qu'à l'écran Comparer.
    # DOCS-COHERENCE-1 (A9) — libellés COMPLETS : ce que mesure chaque SDP (comme le §10 du Dossier).
    ("SDP maximale réglementaire, terrain libéré", "e", lambda r: _m2(r, "sdp_max_m2")),
    ("SDP résiduelle, bâti conservé", "e", lambda r: _sdp_residuelle_cause(r)),
    ("Emprise au sol max (PLU)", "s", lambda r: (_pct(r, "emprise_ces_pct") or "non réglementée")),
    ("Taux d'occupation du gabarit", "e", lambda r: esc(fmt_taux_emprise(r.get("taux_emprise_pct")))),
    ("Sous-densité", "e", lambda r: _oui_non(r.get("sous_densite"))),
    # CHASSE-DOCS-FIX-1 (Lot 5) — charge foncière NÉGATIVE : on garde le chiffre mais on DIT ce qu'il
    # signifie (« le foncier ne se paie pas » à ces hypothèses), jamais un « -59 €/m² » nu et énigmatique.
    ("Charge foncière /m² terrain", "e", lambda r: ((f"{_i(r.get('charge_fonciere_m2'))} €/m²"
        + (" — Bilan déficitaire : à ces hypothèses, le foncier ne se paie pas"
           if (r.get("charge_fonciere_m2") or 0) < 0 else ""))
        if r.get("charge_fonciere_m2") is not None else None)),
    # DOCS-COHERENCE-1 (A8) — prix lus de l'id de la fiche (secteur autour de la parcelle), comme le
    # Dossier §8 et l'Étude de zone ; plus aucun calcul de prix propre au Comparatif.
    ("Prix du terrain (secteur)", "e", _terrain_prix_ventes),
    ("Prix du bâti (secteur)", "e", lambda r: _eur_m2_ventes(r, "prix_secteur_bati_m2", "prix_bati_n", "prix_bati_rayon_m")),
    # IMPLANTATION-4 (LOT B) + FIX-ORFEVRE-1 (décision Vic 18/10/2026) — aucun nombre de logements de
    # l'ancien calcul (fourchette estimate_capacity) : la ligne renvoie à l'Étude de faisabilité, seule
    # à compter des logements. prov=None → aucun badge, comme « Classement LABUSE » (un renvoi, pas une
    # donnée). La note « capacité maximale » reste sous le tableau.
    ("Logements possibles", None, lambda r: "voir l'Étude de faisabilité"),
    ("Bâti existant", "s", lambda r: (f"{_i(r.get('bati_existant_pct'))} % du terrain" if r.get("bati_existant_pct") is not None else None)),
    ("Gabarit max", "s", lambda r: (f"R+{max(0, int(r['gabarit_niveaux_max']) - 1)}" if r.get("gabarit_niveaux_max") is not None else None)),
    ("Accès & réseaux", "s", lambda r: esc(r.get("acces_reseaux")) if r.get("acces_reseaux") else None),
    ("Assainissement", "e", lambda r: esc(r.get("assainissement")) if r.get("assainissement") else None),
    ("Propriétaire", "s", lambda r: {"morale": "personne morale", "particulier": "particulier",
                                      "succession": "succession", "indivision": "indivision"}.get(r.get("proprietaire"))),
    ("Contrainte majeure", "s", lambda r: esc(r.get("contrainte_majeure")) if r.get("contrainte_majeure") else (f"{r.get('n_contraintes')} signalée(s)" if r.get("n_contraintes") else "aucune")),
]

_BADGE = {"s": ("s", "sourcé"), "e": ("e", "estimé")}


def rendu(rows) -> str:
    rows = list(rows or [])[:3]
    if not rows:
        return section("Comparatif", "<p>Aucune parcelle comparable.</p>")
    # en-tête : une colonne par parcelle (référence cadastrale + commune).
    thead = "<tr><th></th>" + "".join(
        f'<th>{esc(_ref_courte(r.get("idu", "")))}'
        + (f'<div class="sub">{esc(r.get("commune"))}</div>' if r.get("commune") else "") + "</th>"
        for r in rows) + "</tr>"
    body = ""
    for label, prov, fn in _LIGNES:
        badge = ""
        if prov in _BADGE:
            cls, lib = _BADGE[prov]
            badge = chip_span(cls, lib)
        cells = ""
        for r in rows:
            v = fn(r)
            cells += f"<td>{v if v is not None else '—'}</td>"
        body += f'<tr><td class="lbl">{esc(label)}{badge}</td>{cells}</tr>'
    # RECETTE-OUTILS-2 (R18) — la note de bas de page « Maximum réglementaire (gabarit) … (0,46 en
    # surface, 0,40 en logements) » est RETIRÉE du Comparatif PDF, pour être identique à l'outil où elle
    # a déjà été retirée (décision Vic). Le plafond réglementaire reste dit par la fiche / l'Étude.
    corps = f'<table class="cmp"><thead>{thead}</thead><tbody>{body}</tbody></table>'
    return section("Comparatif", corps)
