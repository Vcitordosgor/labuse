"""DOCS-1 (Lot C) — bloc « Comparatif » : 2 à 3 parcelles EN COLONNES sur les lignes de Comparer, en
page paysage. Aucun calcul : on rend les CompareRow servis par /compare (le MÊME endpoint que l'écran).
Badges Sourcé/Estimé par ligne et ligne « Classement LABUSE » comme à l'écran. CHASSE-INVARIANTS-FIX-1
(Lot 1, E-01) : le « Taux d'occupation du gabarit » passe par le rendu unique `fmt_taux_emprise`
(au-delà de 100 % → « Saturé … », jamais un % brut — c'était le 19 569 % de l'export) ; écran et PDF
rendent donc la même chaîne."""
from __future__ import annotations

from ...faisabilite.residuel import fmt_taux_emprise
from ..registre_fmt import groupe
from ..rendu import chip_span, esc, note, section


def _i(v):   # entier groupé (séparateur de milliers)
    return groupe(round(v)) if isinstance(v, (int, float)) else None


def _oui_non(v):
    return None if v is None else ("oui" if v else "non")


def _ref_courte(idu: str) -> str:
    return f"{idu[8:10]} {idu[10:14]}" if idu and len(idu) >= 14 else (idu or "")


def _logements(r) -> str | None:
    hi, lo = r.get("logements_possibles"), r.get("logements_min")
    if hi is None:
        return None
    if lo is not None and lo != hi:
        return f"{int(lo)} à {int(hi)}"
    return str(int(hi))


def _classement(r) -> str | None:
    bande = r.get("bande")
    if not bande:
        return None
    sig = r.get("signal_niveau")
    return f"{esc(bande)}" + (f" · signal {esc(sig)}" if sig else "")


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
    ("SDP max estimée", "e", lambda r: _m2(r, "sdp_max_m2")),
    ("SDP résiduelle", "e", lambda r: _sdp_residuelle_cause(r)),
    ("Emprise au sol max (PLU)", "s", lambda r: (_pct(r, "emprise_ces_pct") or "non réglementée")),
    ("Taux d'occupation du gabarit", "e", lambda r: esc(fmt_taux_emprise(r.get("taux_emprise_pct")))),
    ("Sous-densité", "e", lambda r: _oui_non(r.get("sous_densite"))),
    ("Charge foncière /m² terrain", "e", lambda r: (f"{_i(r.get('charge_fonciere_m2'))} €/m²" if r.get("charge_fonciere_m2") is not None else None)),
    ("Prix terrain nu zone", "e", lambda r: _eur_m2(r, "terrain_zone_eur_m2")),
    ("Prix bâti (section cadastrale)", "e", lambda r: _eur_m2(r, "prix_secteur_bati_m2")),
    ("Logements possibles (max.)", "e", _logements),
    ("Bâti existant", "s", lambda r: (f"{_i(r.get('bati_existant_pct'))} % du terrain" if r.get("bati_existant_pct") is not None else None)),
    ("Gabarit max", "s", lambda r: (f"R+{max(0, int(r['gabarit_niveaux_max']) - 1)}" if r.get("gabarit_niveaux_max") is not None else None)),
    ("Accès & réseaux", "s", lambda r: esc(r.get("acces_reseaux")) if r.get("acces_reseaux") else None),
    ("Assainissement", "e", lambda r: esc(r.get("assainissement")) if r.get("assainissement") else None),
    ("Propriétaire", "s", lambda r: {"morale": "personne morale", "particulier": "particulier"}.get(r.get("proprietaire"))),
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
    # FIX-PRIX-ET-OPPORTUNITES (lot 3) — SDP max / logements possibles = plafond réglementaire ; les
    # permis réels en utilisent ~½ en médiane (volet D). Note mesurée sous le tableau.
    from ...capacite_max import MENTION as _CAP
    corps = f'<table class="cmp"><thead>{thead}</thead><tbody>{body}</tbody></table>' + note(_CAP)
    return section("Comparatif", corps)
