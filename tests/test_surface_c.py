"""M11 · SURFACE C — l'IA EXPLIQUE un chiffrage de faisabilité (à partir des STEPS tracés).

Tests PURS (sans DB ni modèle) :
  - la provenance d'affichage des steps est dérivée honnêtement du libellé de source ;
  - l'ANCRAGE des chiffres : un chiffre absent des étapes est REJETÉ par le socle (couche 2), y compris
    la faille d'échelle « 9999/1000 ≈ 10,2 » (le 10,2 d'un « Art. 10.2 ») désormais fermée ;
  - un marqueur ⟨src:…⟩ MALFORMÉ ne fuit plus en clair.

Le pipeline complet (steps réels → prose sourcée + honnêteté DVF) est prouvé en live dans SURFACE-C.md.
"""
from labuse.ai import core
from labuse.api.modules import _faisa_step_prov

# ─────────────────────── provenance d'affichage des steps ───────────────────────

def test_step_prov_derivee_du_source():
    assert _faisa_step_prov("Zone U5c, Art. 10.2, p.~223", "") == "sourcee"
    assert _faisa_step_prov("Art. 7 (séparatif)", "") == "sourcee"
    assert _faisa_step_prov("hypothèse occupation", "") == "estimee"
    assert _faisa_step_prov("dérivé occupation×hauteur", "") == "derive"
    # une provenance déjà posée par le moteur (bilan) prime
    assert _faisa_step_prov("n'importe quoi", "sourcee") == "sourcee"


# ─────────────────────── ANCRAGE — un chiffre inventé est rejeté ───────────────────────

def _ctx():
    """Contexte type d'explication de faisabilité : des étapes chiffrées + sources."""
    return {
        "etape_1": {"valeur": "Emprise au sol : ~2223 m² (source : Art. 7)", "provenance": "SOURCE"},
        "etape_4": {"valeur": "Niveaux : R+1 (source : Zone U5c, Art. 10.2)", "provenance": "SOURCE"},
        "etape_6": {"valeur": "Surface de plancher : ~2001 m²", "provenance": "ESTIME"},
        "charge_fonciere": {"valeur": "charge foncière médiane 1500000 €", "provenance": "ESTIME"},
    }


def test_faux_chiffre_rejete():
    chk = core.validate_output("La SDP est de ~9 999 m² ⟨src:etape_6⟩.", _ctx())
    assert chk.ok is False
    assert "9 999" in (chk.reason or "")


def test_faille_echelle_fermee():
    """9999/1000 ≈ 9,999 ≈ 10,2 (« Art. 10.2 ») : ce chiffre inventé NE passe PLUS par la tolérance d'échelle."""
    assert core._number_ok(9999.0, {10.2, 2001.0, 2223.0}) is False
    assert core._number_ok(5000.0, {5.0, 2001.0}) is False


def test_vrai_chiffre_et_arrondi_acceptes():
    chk = core.validate_output("La SDP est d'environ 2 001 m² ⟨src:etape_6⟩.", _ctx())
    assert chk.ok is True
    # arrondi léger toléré (2 000 ≈ 2 001, < 2 %)
    assert core._number_ok(2000.0, {2001.0}) is True


def test_million_euros_reste_ancrable():
    """« 1,5 M€ » (1.5) doit matcher 1 500 000 € via l'échelle — contre une valeur RÉELLEMENT grande."""
    chk = core.validate_output("La charge foncière ressort à ~1,5 M€ ⟨src:charge_fonciere⟩.", _ctx())
    assert chk.ok is True


def test_gros_nombre_invente_rejete():
    chk = core.validate_output("Le coût atteint 9 000 000 € ⟨src:charge_fonciere⟩.", _ctx())
    assert chk.ok is False


# ─────────────────────── un marqueur MALFORMÉ ne fuit pas ───────────────────────

def test_marqueur_malforme_strippe():
    chk = core.validate_output("SDP ~2 001 m² ⟨src:etape_6 / resultat⟩ selon le calcul ⟨src:etape_6⟩.", _ctx())
    assert chk.ok is True
    assert "⟨" not in chk.text and "⟩" not in chk.text   # aucun marqueur brut résiduel
    assert "etape_6" in chk.sources
