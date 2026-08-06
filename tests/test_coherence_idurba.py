"""M40 — garde de confrontation idurba GPU-vs-mairie (cœur pur, sans DB)."""
from __future__ import annotations

from labuse.bascule_gardes import _confronter_idurba, _idurba_date


def test_idurba_date_parse():
    assert str(_idurba_date("97412_PLU_20240320")) == "2024-03-20"
    assert str(_idurba_date("97409_20190228")) == "2019-02-28"
    assert _idurba_date("97417_rnu") is None
    assert _idurba_date(None) is None


def test_gpu_egal_mairie_aucune_divergence():
    communes = {"97401": {"commune": "Les Avirons", "idurba": "97401_PLU_20241206",
                          "date_mairie": "2024-12-06", "statut": "a_jour"}}
    gpu = {"97401": ["97401_PLU_20241206"]}
    assert _confronter_idurba(communes, gpu) == []


def test_casse_plu_neutralisee():
    # GPU en minuscules, config en majuscules → pas de fausse divergence
    communes = {"97404": {"commune": "L'Étang-Salé", "idurba": "97404_PLU_20250917",
                          "date_mairie": "2025-09-17", "statut": "a_jour"}}
    gpu = {"97404": ["97404_plu_20250917"]}
    assert _confronter_idurba(communes, gpu) == []


def test_residu_saint_joseph_signale():
    # test d'acceptation Vic : le résidu Saint-Joseph DOIT être signalé, avec l'ampleur
    communes = {"97412": {"commune": "Saint-Joseph", "idurba": "97412_PLU_20251210",
                          "date_mairie": "2025-12-10", "statut": "a_jour"}}
    gpu = {"97412": ["97412_PLU_20251210", "97412_PLU_20240320"]}
    div = _confronter_idurba(communes, gpu)
    assert len(div) == 1
    assert div[0]["type"] == "RESIDU"
    assert div[0]["idurba_gpu"] == "97412_PLU_20240320"
    assert div[0]["ampleur_jours"] == 630  # 2024-03-20 → 2025-12-10


def test_manquant_vrai_retard_gpu():
    # le cas que la garde existe pour attraper : mairie a un doc que le GPU ne sert pas
    communes = {"97499": {"commune": "Test", "idurba": "97499_PLU_20260101",
                          "date_mairie": "2026-01-01", "statut": "a_jour"}}
    gpu = {"97499": ["97499_PLU_20240101"]}  # GPU en retard d'un an
    div = _confronter_idurba(communes, gpu)
    types = {d["type"] for d in div}
    assert "MANQUANT" in types
    manq = next(d for d in div if d["type"] == "MANQUANT")
    assert manq["ampleur_jours"] == 731  # ~2 ans... 2024-01-01 → 2026-01-01 (année bissextile)


def test_rnu_ignore():
    communes = {"97417": {"commune": "Saint-Philippe", "idurba": None,
                          "date_mairie": None, "statut": "rnu"}}
    assert _confronter_idurba(communes, {}) == []
