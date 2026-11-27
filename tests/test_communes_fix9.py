"""OUTIL-COMMUNES-FIX-9 — filet de régression (pur, AUCUNE base → vu par le hook `-m "not db"`).

LOT C (3) : « ventes » (effectif d'actes, niveau secteur) vs « sections » (repli communal) — jamais
« ventes » pour un comptage de sections ; phrase `note_seuil` rendue. LOT C (4) : précision de date
variable honnête (mois/année) avec la bonne préposition (« au » jour / « en » mois-année).
"""
from __future__ import annotations

from labuse.api.blocs_documents import rehab_bloc
from labuse.api.fiche_commune import _fr_date_au, _fr_date_iso


def _tn(niveau, n, unite, libelle):
    return {"valeur_eur": 145500, "valeur_libelle": "146 k€",
            "valeur_fourchette_libelle": "100 k€ – 190 k€", "incertitude": "fourchette ±30 %",
            "prix_m2": 291, "surface_m2": 500, "niveau": niveau, "libelle": libelle,
            "effectif": n, "effectif_unite": unite, "etiquette": "Estimé"}


def test_repli_communal_dit_sections_jamais_ventes():
    """LOT C (3) — repli communal : l'effectif est un comptage de SECTIONS, rendu « N sections »,
    jamais « N ventes » (défaut ASTRA-6 §3, exemple CD0003 = 291 €/m², 56 sections)."""
    mb = {"disponible": True, "achat_max_libelle": "180 000 €", "surface_parcelle_m2": 500,
          "terrain_nu": _tn("commune", 56, "sections", "médiane DVF terrain de la commune — 56 sections (repli)")}
    ligne = next(t for _, t in rehab_bloc(mb)["lignes"] if "Terrain nu" in t)
    assert "56 sections" in ligne
    assert "vente" not in ligne


def test_secteur_dit_ventes_et_porte_note_seuil():
    """LOT C (3) — secteur : « N ventes » + la phrase d'explication du seuil (Bilan 3 vs affichage 8)."""
    note = "Hypothèse de Bilan fondée sur 7 ventes. Un prix de marché est publié à partir de 8 ventes."
    mb = {"disponible": True, "achat_max_libelle": "180 000 €", "surface_parcelle_m2": 500,
          "terrain_nu": _tn("secteur", 7, "ventes", "médiane DVF terrain du secteur — 7 ventes"),
          "note_seuil": note}
    lignes = rehab_bloc(mb)["lignes"]
    assert "7 ventes" in next(t for _, t in lignes if "Terrain nu" in t)
    assert any(note == t for _, t in lignes)   # la phrase de seuil est rendue telle quelle


def test_date_precision_variable_et_preposition():
    """LOT C (4) — « mai 2025 » (pas 1er mai) / « 2025 » / « 31/12/2024 », préposition correcte."""
    assert _fr_date_iso("2025-05") == "mai 2025"
    assert _fr_date_iso("2025") == "2025"
    assert _fr_date_iso("2024-12-31") == "31/12/2024"
    assert _fr_date_au("2025-05") == "en mai 2025"
    assert _fr_date_au("2025") == "en 2025"
    assert _fr_date_au("2024-12-31") == "au 31/12/2024"
    assert _fr_date_au(None) is None
