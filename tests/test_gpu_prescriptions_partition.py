"""MISE-EN-LIGNE-7 — `ingest_gpu_prescriptions` requête PAR PARTITION du document (DU_<insee>),
plus par bbox : elle reproduit EXACTEMENT le document GPU de la commune, sans aucun objet d'une
commune voisine, pagination comprise. (Le débordement bbox ajoutait des features frontalières —
Saint-Joseph surf-01 : 65 au lieu de 64, +7 ha d'un EBC limitrophe.)"""
from labuse.ingestion import layers_ingest


class _Resp:
    def __init__(self, feats):
        self._feats = feats

    def raise_for_status(self):
        pass

    def json(self):
        return {"features": self._feats}


class _FakeClient:
    """Rend des pages selon `_start`. Chaque page inclut volontairement 1 objet d'une commune VOISINE."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, url, params=None):
        self.calls.append(params or {})
        return _Resp(self.pages.get((params or {}).get("_start", 0), []))


def _feat(part, tp):
    return {"type": "Feature",
            "geometry": {"type": "Point", "coordinates": [55.6, -21.3]},
            "properties": {"partition": part, "typepsc": tp}}


def test_fetch_partition_exclut_les_voisins_et_pagine():
    # page 0 : 1000 (999 du bon doc + 1 voisin) → il reste des pages ; page 1000 : 2 (1 bon + 1 voisin)
    page0 = [_feat("DU_97412", "01") for _ in range(999)] + [_feat("DU_97419", "01")]
    page1 = [_feat("DU_97412", "05"), _feat("DU_97419", "05")]
    c = _FakeClient({0: page0, 1000: page1})

    feats = layers_ingest._fetch_gpu_partition(c, "prescription-surf", "DU_97412")

    assert len(feats) == 1000                                   # 999 + 1, aucun voisin
    assert all(f["properties"]["partition"] == "DU_97412" for f in feats)
    assert [call.get("_start") for call in c.calls] == [0, 1000]  # pagination suivie
    # TOUJOURS par partition, JAMAIS par geom (bbox)
    assert all("partition" in call and "geom" not in call for call in c.calls)


def test_ingest_prescriptions_utilise_la_partition_pas_la_bbox(monkeypatch):
    """La fonction complète, avec insee : interroge par partition et n'insère aucun voisin."""
    pages = {0: [_feat("DU_97402", "01"), _feat("DU_97402", "05"), _feat("DU_97999", "01")]}
    fake = _FakeClient(pages)
    monkeypatch.setattr(layers_ingest, "_client", lambda: fake)
    inserts = []
    monkeypatch.setattr(layers_ingest, "_insert_layer",
                        lambda *a, **k: inserts.append((a, k)))

    n = layers_ingest.ingest_gpu_prescriptions(
        None, bbox=(55.6, -21.3, 55.7, -21.2), commune="Bras-Panon",
        run_id=None, sids={"plu_gpu_prescription": 1}, insee="97402")

    # 3 endpoints (surf/lin/pct) × 2 features propres = 6 ; le voisin DU_97999 est écarté partout
    assert n == 6
    assert all(call.get("partition") == "DU_97402" and "geom" not in call for call in fake.calls)
