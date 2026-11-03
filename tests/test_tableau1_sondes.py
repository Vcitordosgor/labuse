"""TABLEAU-1 (point 3) — réparations des 6 sondes en panne, en UNITAIRE PUR (aucune base, aucun réseau :
on injecte la couche HTTP). Couvre :
  · `entete` avec repli Content-Length (SIS préfecture : ni ETag ni Last-Modified) ;
  · `temoin` sur réponse NON-JSON via sélecteur « re:… » (OCS GE : flux atom) ;
  · `temoin` sur FeatureCollection VIDE = injoignable transitoire, pas illisible (SCOT geopf sous charge) ;
  · repli sur miroir Overpass quand l'endpoint public échoue (parkings/OSM transport/TCSP).
Le grace « injoignable < 7 jours » lui-même est couvert côté circuit_etats (test_circuit_p4_etats).
"""
from __future__ import annotations

from labuse import sentinelle as S


def _http_map(reponses: dict):
    """Fausse couche HTTP : url → (status, headers, body). Absente → lève (→ injoignable)."""
    def _h(url: str, *, methode_http: str = "GET"):
        if url not in reponses:
            raise ConnectionError(f"réseau coupé (test) : {url}")
        return reponses[url]
    return _h


def test_entete_repli_content_length(monkeypatch):
    url = "https://prefecture/dossier-sis.zip"
    # ni ETag ni Last-Modified (header vide) mais Content-Length présent → empreinte = taille.
    monkeypatch.setattr(S, "_http", _http_map({url: (200, {"last-modified": "", "content-length": "8151737"}, "")}))
    s = S.sonder_entete(url, None)
    assert s.statut == "ok" and s.vu == "taille:8151737"
    # un dossier mis à jour change de taille → nouvelle_version.
    monkeypatch.setattr(S, "_http", _http_map({url: (200, {"content-length": "9001234"}, "")}))
    s2 = S.sonder_entete(url, "taille:8151737")
    assert s2.statut == "nouvelle_version" and s2.vu == "taille:9001234"


def test_entete_sans_rien_reste_illisible(monkeypatch):
    url = "https://x/y.zip"
    monkeypatch.setattr(S, "_http", _http_map({url: (200, {}, "")}))
    assert S.sonder_entete(url, None).statut == "illisible"


def test_temoin_regex_sur_atom_non_json(monkeypatch):
    # OCS GE sert de l'atom+xml, pas du JSON : le sélecteur « re: » lit le <updated> du flux.
    atom = "<feed><updated>2025-04-10T14:59:00+01:00</updated></feed>"
    url = "https://data.geopf.fr/telechargement/resource/OCSGE/x"
    monkeypatch.setattr(S, "_http", _http_map({url: (200, {}, atom)}))
    s = S.sonder_temoin(url, "re:<updated>([^<]+)</updated>", None)
    assert s.statut == "ok" and s.vu == "2025-04-10T14:59:00+01:00"
    # une nouvelle livraison change le <updated> → nouvelle_version.
    atom2 = "<feed><updated>2026-01-02T00:00:00+01:00</updated></feed>"
    monkeypatch.setattr(S, "_http", _http_map({url: (200, {}, atom2)}))
    assert S.sonder_temoin(url, "re:<updated>([^<]+)</updated>", s.vu).statut == "nouvelle_version"


def test_temoin_regex_prend_le_plus_recent(monkeypatch):
    # SCOT : plusieurs gpu_timestamp dans la réponse → on garde le PLUS RÉCENT (max), robuste à l'ordre.
    body = '{"features":[{"properties":{"gpu_timestamp":"2022-10-25T00:00:00Z"}},{"properties":{"gpu_timestamp":"2024-09-17T00:00:00Z"}}]}'
    url = "https://data.geopf.fr/wfs/scot"
    monkeypatch.setattr(S, "_http", _http_map({url: (200, {}, body)}))
    s = S.sonder_temoin(url, 're:"gpu_timestamp":"([^"]+)"', None)
    assert s.statut == "ok" and s.vu == "2024-09-17T00:00:00Z"


def test_temoin_feature_collection_vide_est_injoignable_pas_illisible(monkeypatch):
    # geopf sous charge renvoie parfois 0 feature : creux amont MOMENTANÉ (grace), pas notre lecteur cassé.
    url = "https://data.geopf.fr/wfs/scot"
    monkeypatch.setattr(S, "_http", _http_map({url: (200, {}, '{"type":"FeatureCollection","features":[]}')}))
    s = S.sonder_temoin(url, "features.0.properties.gpu_timestamp", None)
    assert s.statut == "injoignable"   # et NON "illisible" → couvert par le grace < 7 j


def test_overpass_replie_sur_miroir(monkeypatch):
    # l'endpoint public overpass-api.de tombe (502) → on rejoue la MÊME requête sur un miroir connu.
    primaire = "https://overpass-api.de/api/interpreter?data=XXX"
    miroir = "https://overpass.kumi.systems/api/interpreter?data=XXX"
    body = '{"elements":[{"tags":{"total":"42"}}]}'

    def _h(url, *, methode_http="GET"):
        if url == primaire:
            raise OSError("HTTP Error 502: Bad Gateway")
        if url == miroir:
            return (200, {}, body)
        raise ConnectionError(url)
    monkeypatch.setattr(S, "_http", _h)
    s = S.sonder_temoin(primaire, "elements.0.tags.total", None)
    assert s.statut == "ok" and s.vu == "42"


def test_non_overpass_ne_replie_pas(monkeypatch):
    # hors Overpass : pas de miroir (doctrine W3.2) → l'échec reste un échec (injoignable via sonder()).
    url = "https://data.geopf.fr/wfs/scot"

    def _h(u, *, methode_http="GET"):
        raise OSError("boom")
    monkeypatch.setattr(S, "_http", _h)
    try:
        S._http_temoin(url)
        assert False, "aurait dû lever (pas de repli hors Overpass)"
    except OSError:
        pass
