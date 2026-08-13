"""M78 · 2e — le VERROU anti-invention du héros, testé (garde-fou du mandat). Fonctions PURES,
aucun appel modèle : on prouve qu'un nombre absent du JSON est rejeté, et le repli gabarit honnête."""
from labuse.copilote_v2 import heros as H

PARCELLE = {
    "idu": "97415000AC0253", "commune": "Saint-Paul", "surface_m2": 1815, "sdp_m2": 920,
    "prix_probable_eur": 350000, "charge_fonciere_eur": 280000, "tier": "chaude",
    "au_dessus_charge_supportable": True, "zone": "U", "n_signaux_risques": 1,
}


def test_verrou_rejette_nombre_invente():
    autor = H._valeurs(PARCELLE, 300000)
    assert not H._phrase_ok("Elle vaudra 999 999 € dans 42 ans.", autor)


def test_verrou_accepte_nombres_source():
    autor = H._valeurs(PARCELLE, 300000)
    # 1815 m², 920 m² SDP, charge 280 000 €, budget 300 k€ — tous présents dans le JSON (+ variante k€)
    assert H._phrase_ok("1 815 m², 920 m² de SDP, charge 280 000 € au-dessus du budget de 300 k€.", autor)


def test_gabarit_deterministe_dit_la_faiblesse():
    g = H._gabarit(PARCELLE)
    assert "97415000AC0253" in g and "1815" in g.replace(" ", "")
    assert "supportable" in g.lower()   # la réserve (au-dessus de la charge) est DITE
