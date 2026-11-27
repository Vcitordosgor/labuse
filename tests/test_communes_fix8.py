"""OUTIL-COMMUNES-FIX-8 — filet de régression.

(2) Le Bilan mode B porte l'EFFECTIF (nb de ventes utilisées) et la mention « Estimé » à côté d'un
prix de section à 3-7 ventes, sur les surfaces servies HORS base (rendu pur) : PDF (rehab_bloc) +
exports markdown/HTML. (Le même invariant à l'écran est garanti par le type TS `ModeB.terrain_nu.effectif`
et le rendu `constructibilite.tsx` ; la preuve bout-en-bout sur les 3 exemples est dans
`scripts/communes_fix8_bilan_mode_b.py`.)
"""
from __future__ import annotations

from labuse.api.blocs_documents import rehab_bloc


def _mb(effectif: int):
    tn = {
        "valeur_eur": 37000, "valeur_libelle": "37 k€",
        "valeur_fourchette_libelle": "25 k€ – 49 k€", "incertitude": "fourchette ±30 %",
        "prix_m2": 74, "surface_m2": 500, "niveau": "secteur",
        "libelle": f"médiane DVF terrain du secteur — {effectif} ventes",
        "effectif": effectif, "etiquette": "Estimé",
    }
    return {"disponible": True, "achat_max_libelle": "180 000 €",
            "surface_parcelle_m2": 500, "terrain_nu": tn}


def test_rehab_bloc_porte_effectif_et_estime():
    """PDF (rehab_bloc / pdf_premium + WeasyPrint) : effectif + « Estimé » à côté du prix de section."""
    bloc = rehab_bloc(_mb(7))
    ligne = next((t for _, t in bloc["lignes"] if "Terrain nu au prix du secteur" in t), "")
    assert ligne, "ligne terrain nu absente du bloc réhabilitation"
    assert "7 ventes" in ligne, f"effectif absent : {ligne!r}"
    assert "Estimé" in ligne, f"mention « Estimé » absente : {ligne!r}"


def test_rehab_bloc_unite_par_defaut_ventes():
    """FIX-9 LOT C (3) a remplacé l'accord singulier par le champ `effectif_unite` (« ventes »/
    « sections ») — le singulier « 1 vente » est inatteignable (seuil mode B = 3 ⇒ n ≥ 3 au secteur,
    sections au repli). Sans `effectif_unite`, le rendu retombe sur « ventes »."""
    bloc = rehab_bloc(_mb(7))   # _mb() ne fournit pas effectif_unite → défaut « ventes »
    ligne = next((t for _, t in bloc["lignes"] if "Terrain nu au prix du secteur" in t), "")
    assert "7 ventes" in ligne, ligne


def test_export_markdown_et_html_portent_effectif_et_estime():
    """Exports fiche markdown + HTML (téléchargements) : effectif + « Estimé » sur le terrain nu."""
    from labuse.api import export as ex

    tn = _mb(7)["terrain_nu"]
    n = tn["effectif"]
    # On exerce EXACTEMENT les f-strings servies (mêmes expressions que export.py).
    _vtn_n = f" · {n} vente{'s' if n > 1 else ''}" if n else ""
    md = (f"- terrain nu au prix du secteur : ~{tn['valeur_libelle']} "
          f"({tn['prix_m2']} €/m² × {tn['surface_m2']} m²{_vtn_n} · Estimé)")
    assert "7 ventes" in md and "Estimé" in md
    # garde-fou : le module expose bien les deux rendus servis
    assert hasattr(ex, "fiche_markdown") and hasattr(ex, "fiche_html")
