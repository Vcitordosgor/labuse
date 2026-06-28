"""Exports (Markdown/HTML) — section « Comparables de prix utilisés » (transparence).

Vérifie l'affichage conditionnel et l'absence de faux écart ; fonctions pures (un dict)."""
from labuse.api.export import fiche_html, fiche_markdown

_FORBIDDEN = ["bilan fiable", "rentabilité garantie", "prix certain", "opération validée"]


def _fiche(comparables, prix_dvf, fiable=True):
    return {
        "parcel": {"idu": "97415000BN1351", "commune": "Saint-Paul", "surface_m2": 4552,
                   "section": "BN", "numero": "1351"},
        "verdict": {"status": "À_CREUSER", "opportunity_score": 70, "completeness_score": 60, "reasons": []},
        "cascade": [], "sources_responded": ["DVF"], "sources_silent": [],
        "disclaimer": "Pré-analyse. Rien n'est garanti.",
        "faisabilite": {"bilan": {"fiable": fiable, "comparables": comparables, "prix_dvf": prix_dvf}},
        "ai": None,
    }


def _px(median=5007, fiab="fiable"):
    return {"median": median, "type_prix": "appartement", "n": 34, "periode": [2021, 2025],
            "radius_m": 500.0, "commune_fallback": False, "fiabilite": fiab}


def _no_forbidden(txt):
    low = txt.lower()
    return not any(w in low for w in _FORBIDDEN)


def test_export_md_comparables_exploitable():
    c = {"n_ancien": 17, "mediane_ancien": 3854, "n_vefa": 17, "mediane_vefa": 5398,
         "ecart_vefa_ancien_pct": 40, "exploitable": True, "note": None, "fiabilite_prix": "fiable"}
    md = fiche_markdown(_fiche(c, _px()))
    assert "Comparables de prix utilisés" in md
    assert "Simulation indicative" in md and "à valider" in md.lower()
    assert "3 854 €/m²" in md and "5 398 €/m²" in md and "+40 %" in md
    assert "Prix de marché fiable" in md
    assert _no_forbidden(md)


def test_export_html_comparables_exploitable():
    c = {"n_ancien": 17, "mediane_ancien": 3854, "n_vefa": 17, "mediane_vefa": 5398,
         "ecart_vefa_ancien_pct": 40, "exploitable": True, "note": None, "fiabilite_prix": "fiable"}
    h = fiche_html(_fiche(c, _px()))
    assert "Comparables de prix utilisés" in h and "Simulation indicative" in h
    assert "+40 %" in h and "Prix de marché fiable" in h
    assert _no_forbidden(h)


def test_export_no_false_ecart_when_vefa_insufficient():
    c = {"n_ancien": 22, "mediane_ancien": 3189, "n_vefa": 0, "mediane_vefa": None,
         "ecart_vefa_ancien_pct": None, "exploitable": False,
         "note": "aucune vente VEFA dans le comparable retenu (prix = ancien)", "fiabilite_prix": "fiable"}
    md = fiche_markdown(_fiche(c, _px(median=3189)))
    assert "Comparables de prix utilisés" in md
    assert "%" not in md.split("Écart neuf vs ancien")[1].split("\n")[0]  # pas de faux pourcentage d'écart
    assert "aucune vente VEFA" in md
    assert _no_forbidden(md)


def test_export_skips_block_when_no_bilan():
    md = fiche_markdown(_fiche(None, {}, fiable=False))
    assert "Comparables de prix utilisés" not in md
    h = fiche_html(_fiche(None, {}, fiable=False))
    assert "Comparables de prix utilisés" not in h


def test_html_echappe_les_injections():
    """#8 — fiche_html ÉCHAPPE toute valeur injectée (idu, commune, disclaimer) : pas d'injection HTML/JS."""
    f = _fiche(None, {}, fiable=False)
    f["parcel"]["idu"] = "<script>alert(1)</script>"
    f["parcel"]["commune"] = "<img src=x onerror=alert(2)>"
    f["disclaimer"] = "<b>boom</b>"
    h = fiche_html(f)
    assert "<script>alert(1)</script>" not in h            # payload brut jamais présent
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in h    # … mais échappé
    assert "<img src=x onerror=alert(2)>" not in h
    assert "<b>boom</b>" not in h and "&lt;b&gt;boom&lt;/b&gt;" in h
