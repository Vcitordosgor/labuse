"""PLU-CALIBRAGE-1 lot 2 — les 23 calibrages PLU, lecteurs du réservoir GPU.

Le réservoir GPU (`gpu_plu_api_carto`) déclare les calibrages de commune comme lecteurs :
la fiche Circuit les liste, et une NOUVELLE version du PLU d'une commune (catalogue idurba
plus récent que celui gravé au calibrage) fait passer ce calibrage « à revérifier ».
"""
from __future__ import annotations

from labuse.plu import destinations as D


def test_gpu_declare_23_calibrages_lecteurs():
    """23 calibrages (les 23 communes dotées d'un PLU ; le RNU de Saint-Philippe exclu),
    chacun avec sa version GPU gravée (identifiant + millésime)."""
    cal = D.calibrages_gpu()
    assert len(cal) == 23, [c["insee"] for c in cal]
    assert "97417" not in {c["insee"] for c in cal}  # Saint-Philippe (RNU) n'est pas un calibrage PLU
    for c in cal:
        assert c["document_gpu"], c["commune"]        # la version calibrée est gravée
        assert c["etat_label"] in ("à jour", "à revérifier", "non calibré")


def test_sources_calibrages_endpoint_cle_par_nom_gpu():
    """L'endpoint /sources/calibrages est keyé par le NOM du réservoir GPU (data_sources.name),
    même forme que /sources/couches — le détail Circuit du réservoir GPU les liste."""
    from labuse.api.app import sources_calibrages
    out = sources_calibrages()
    assert list(out) == ["Urbanisme PLU/GPU (API Carto)"]
    assert len(out["Urbanisme PLU/GPU (API Carto)"]) == 23


def test_nouvelle_version_plu_fait_passer_a_reverifier(monkeypatch):
    """Quand une version de PLU plus récente est servie (catalogue idurba > idurba gravé au
    calibrage), la commune passe « à revérifier » — le lien veille GPU → calibrage."""
    vrai = D._millesimes()
    # Saint-Denis calibré sur 97411_PLU_20260805 → on sert une révision plus récente au catalogue.
    faux = dict(vrai)
    faux["97411"] = {**(vrai.get("97411") or {}), "commune": "Saint-Denis",
                     "idurba": "97411_PLU_20271231", "statut": "a_jour"}
    monkeypatch.setattr(D, "_millesimes", lambda: faux)
    cal = {c["insee"]: c for c in D.calibrages_gpu()}
    assert cal["97411"]["a_reverifier"] is True
    assert cal["97411"]["etat_label"] == "à revérifier"
    assert cal["97411"]["document_gpu_servi"] == "97411_PLU_20271231"
    # les autres communes restent à jour
    assert cal["97401"]["a_reverifier"] is False
