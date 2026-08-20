"""M137-P — l'outil PLU unifié : le « PLU intégral » (pack GPU .zip) ne doit JAMAIS être un bouton mort.

Contrat vérifié (déterministe, aucun appel modèle ni table) :
  - une commune SERVABLE porte un `source_url` (le pack officiel à télécharger) + un `document` ;
  - une commune NON servable (RNU / révision / non ingérée) N'a PAS de source_url MAIS DIT pourquoi
    (`message`) — l'écran affiche le statut, jamais un lien vers rien.
`corpus_status` est monkeypatché : le test porte sur la COMPOSITION de l'endpoint (croisement corpus ×
millésimes), pas sur l'état de la base.
"""
from __future__ import annotations

import pytest

import labuse.ingestion.plu_ingest as plu_ingest
from labuse.api.modules import plu_annuaire_communes

pytestmark = pytest.mark.db

_URL = "https://data.geopf.fr/telechargement/download/pack_plu1/PACK_DU_97401_x/97401_PLU_20241206.zip"
_CORPUS = {"97401": {"insee": "97401", "commune": "Les Avirons", "idurba": "97401_PLU_20241206",
                     "millesime": "2024-12-06", "extraits": 109, "doutes": 0,
                     "pagination_ambigue": False, "documents": "97401_reglement_20241206.pdf",
                     "source_url": _URL}}


def test_plu_integral_servable_telechargeable_sinon_dit_pourquoi(db_session, monkeypatch):
    monkeypatch.setattr(plu_ingest, "corpus_status", lambda db: _CORPUS)
    r = plu_annuaire_communes(db_session)
    assert r["n_communes"] == 24 and r["servables"] == 1
    avirons = next(c for c in r["communes"] if c["insee"] == "97401")
    # le bouton « Télécharger le PLU (.zip) » a une cible réelle (pack GPU) + le nom du règlement
    assert avirons["statut"] == "servable"
    assert avirons["source_url"] == _URL and avirons["document"]
    for c in r["communes"]:
        if c["statut"] == "servable":
            assert str(c.get("source_url", "")).startswith("http"), f"{c['commune']} servable sans source_url (bouton mort)"
        else:
            # RNU / révision / non ingérée : aucune cible, mais un message HONNÊTE affiché à l'écran
            assert not c.get("source_url"), f"{c['commune']} non-servable mais porte un source_url"
            assert c.get("message"), f"{c['commune']} non-servable sans message (écran muet)"
