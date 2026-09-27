"""KELFONCIER-FIX-1 (Lot F) — Petites Villes de Demain (PVD) branchées comme dispositif de commune.

`_dispositif_commune_ort` = un dispositif de fiche §7 lu par la MÊME fonction que la fiche commune
(`ingestion.ort.ort_commune`, table commune_ort DGALN/ANCT). Ajouté à `dispositifs_dom` → rendu §7
ET, comme le zonage A/B/C et la TVA, miroir au Dossier (`_r_territoire` rend tous les dispositifs).
"""
from __future__ import annotations


def test_dispositif_commune_ort_pvd(monkeypatch):
    import labuse.ingestion.ort as ort_mod
    from labuse.api.app import _dispositif_commune_ort
    monkeypatch.setattr(ort_mod, "ort_commune", lambda db, insee: {
        "statut": "pvd", "ort_signee": True, "date_signature": "2021-10-05",
        "millesime": "table DGALN vivante (grist)", "denormandie": "éligible sous conditions"})
    d = _dispositif_commune_ort(None, "97421")
    assert d is not None
    assert "Petites Villes de Demain (PVD)" in d["libelle"]
    assert "ORT signée" in d["libelle"] and "2021-10-05" in d["libelle"]
    assert "DGALN/ANCT" in d["source"]


def test_dispositif_commune_ort_acv(monkeypatch):
    import labuse.ingestion.ort as ort_mod
    from labuse.api.app import _dispositif_commune_ort
    monkeypatch.setattr(ort_mod, "ort_commune", lambda db, insee: {
        "statut": "acv", "ort_signee": True, "date_signature": None,
        "millesime": "m", "denormandie": "éligible sous conditions"})
    d = _dispositif_commune_ort(None, "97407")
    assert d and "Action Cœur de Ville (ACV)" in d["libelle"]


def test_dispositif_commune_ort_hors_dispositif(monkeypatch):
    """Commune hors ACV/PVD et sans ORT signée → AUCUNE ligne (jamais un dispositif inventé)."""
    import labuse.ingestion.ort as ort_mod
    from labuse.api.app import _dispositif_commune_ort
    monkeypatch.setattr(ort_mod, "ort_commune", lambda db, insee: {
        "statut": "hors", "ort_signee": False, "denormandie": "non éligible"})
    assert _dispositif_commune_ort(None, "97422") is None
    # table non ingérée (None) → None aussi
    monkeypatch.setattr(ort_mod, "ort_commune", lambda db, insee: None)
    assert _dispositif_commune_ort(None, "97422") is None


def test_miroir_dossier_rend_tous_les_dispositifs_dom():
    """Le Dossier miroir rend zonage A/B/C, TVA DOM ET Petites Villes de Demain (plus le seul zonage)."""
    from labuse.exports.miroir import _r_territoire
    from labuse.registre.valeur import Valeur
    val = Valeur(valeur="x", chiffre_id="perimetres_dispositifs_liste", version_def="x", run=None)
    tf = {"dispositifs_dom": [
        {"libelle": "Zonage d'investissement locatif : B1"},
        {"libelle": "TVA outre-mer : 8,5 % · 2,1 % logement locatif social"},
        {"libelle": "Petites Villes de Demain (PVD) · ORT signée"},
    ]}
    html = _r_territoire(tf, val)   # (apostrophes échappées en HTML → on teste des fragments sûrs)
    assert "Zonage du logement" in html and "investissement locatif : B1" in html
    assert "TVA outre-mer" in html
    assert "Petites Villes de Demain (PVD)" in html
