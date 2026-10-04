"""DOCS-1 (Lot C) — bloc « Comparatif » : 2 à 3 parcelles EN COLONNES sur les lignes de Comparer, en
page paysage. Aucun calcul : on rend les CompareRow servis par /compare (le MÊME endpoint que l'écran).
Badges Sourcé/Estimé par ligne et ligne « Classement LABUSE » comme à l'écran. Les valeurs extrêmes de
% sont imprimées BRUTES (le plafond d'affichage « > 300 » de l'écran n'est pas appliqué au tableau :
le test « écran = PDF » compare la valeur servie, pas sa présentation)."""
from __future__ import annotations

from ..registre_fmt import groupe
from ..rendu import chip_span, esc, section


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
    ("Zone PLU", "s", lambda r: esc(r.get("zone")) if r.get("zone") else None),
    ("Classement LABUSE", None, _classement),
    ("Constructible", "s", lambda r: _oui_non(r.get("constructible"))),
    ("SDP max estimée", "e", lambda r: _m2(r, "sdp_max_m2")),
    ("SDP résiduelle", "e", lambda r: _m2(r, "sdp_residuelle_m2")),
    ("Emprise au sol max (PLU)", "s", lambda r: (_pct(r, "emprise_ces_pct") or "non réglementée")),
    ("Taux d'occupation du gabarit", "e", lambda r: _pct(r, "taux_emprise_pct")),
    ("Sous-densité", "e", lambda r: _oui_non(r.get("sous_densite"))),
    ("Charge foncière /m² terrain", "e", lambda r: (f"{_i(r.get('charge_fonciere_m2'))} €/m²" if r.get("charge_fonciere_m2") is not None else None)),
    ("Prix terrain nu zone", "e", lambda r: _eur_m2(r, "terrain_zone_eur_m2")),
    ("Prix bâti (section cadastrale)", "e", lambda r: _eur_m2(r, "prix_secteur_bati_m2")),
    ("Logements possibles", "e", _logements),
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
    return section("Comparatif", f'<table class="cmp"><thead>{thead}</thead><tbody>{body}</tbody></table>')
