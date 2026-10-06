"""FIX-CARTE — verrous du moteur de tuiles : bornes de zoom alignées sur la source (C2) et
fraîcheur exposée au runtime par /map/tiles/meta (T1).

Tests de CONTRAT (pas de données semées nécessaires) : la borne de zoom est vérifiée AVANT toute
requête SQL, et /map/tiles/meta répond même sans mvt_meta (valeurs nulles / perime=False).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(engine):
    from labuse.api.app import app
    return TestClient(app)


def test_zoom_borne_a_15_comme_la_source(client, engine):
    """C2 — l'endpoint parcelles ne sert que z8-15 (la source front cape à z15) : z16/z22 → 204.
    G1-LOT3 : borne basse z9→z8 (la carte est bornée à minZoom 8, atteignable au dézoom d'un petit
    canvas) → z8 n'est PLUS rejetée par la BORNE (sinon « île noire » quand l'overlay doublon est
    retiré) ; z7 reste 204. La borne est vérifiée AVANT tout SQL (contrat pur : z7/z16/z22)."""
    assert client.get("/map/tiles/16/1/1.pbf").status_code == 204
    assert client.get("/map/tiles/22/1/1.pbf").status_code == 204
    assert client.get("/map/tiles/7/1/1.pbf").status_code == 204    # sous la source (minzoom 8)
    # z8 n'est plus 204 par la borne. Avec données : 8/1/1 (mer) → 200 corps vide. Sans table semée
    # (CI isolée), la route renvoie 204 « table absente » — on ne teste le 200 que si mvt_parcels existe.
    from sqlalchemy import text
    from sqlalchemy.orm import Session
    with Session(engine) as db:
        has_mvt = db.execute(text("SELECT to_regclass('mvt_parcels')")).scalar()
    if has_mvt:
        assert client.get("/map/tiles/8/1/1.pbf").status_code == 200



def test_meta_expose_la_fraicheur(client):
    """T1 — /map/tiles/meta annonce la date de ce que la carte peint + le drapeau de péremption,
    lisible au RUNTIME (et non plus seulement au build)."""
    r = client.get("/map/tiles/meta")
    assert r.status_code == 200
    body = r.json()
    for k in ("run_label", "zonage_parcelle", "carte_le", "amont_le", "perime"):
        assert k in body, f"clé de fraîcheur manquante : {k}"
    assert isinstance(body["perime"], bool)


def _req(if_none_match: str | None = None, accept_encoding: str | None = None):
    """Requête starlette minimale pour tester le contrat ETag sans DB ni serveur."""
    from starlette.requests import Request

    headers = []
    if if_none_match is not None:
        headers.append((b"if-none-match", if_none_match.encode()))
    if accept_encoding is not None:
        headers.append((b"accept-encoding", accept_encoding.encode()))
    return Request({"type": "http", "method": "GET", "headers": headers})


def test_etag_revalidation_conditionnelle():
    """CARTE-VITESSE-2 lot C (R3) — la réponse tuile porte un ETag FORT (hash du contenu) + le
    Cache-Control ; un If-None-Match correspondant → 304 sans corps (0 octet réseau) ; sinon 200."""
    from labuse.api.tiles import _etag, _tile_response

    body = b"\x1a\x2b\x3c parcelle mvt octets"
    etag = _etag(body)

    # 1) Sans If-None-Match → 200, ETag entre guillemets, Cache-Control conservé.
    r = _tile_response(_req(), body, etag)
    assert r.status_code == 200
    assert r.headers["etag"] == f'"{etag}"'
    assert "max-age=3600" in r.headers["cache-control"]

    # 2) If-None-Match = le bon tag → 304, même ETag, pas de corps.
    r304 = _tile_response(_req(f'"{etag}"'), body, etag)
    assert r304.status_code == 304
    assert r304.headers["etag"] == f'"{etag}"'
    assert r304.body == b""

    # 3) Tag FAIBLE (W/"…") et LISTE de tags → toujours 304 (on matche la valeur).
    assert _tile_response(_req(f'W/"{etag}", "autre"'), body, etag).status_code == 304
    # 4) Joker "*" → 304.
    assert _tile_response(_req("*"), body, etag).status_code == 304
    # 5) Tag qui ne correspond pas → 200 (le contenu a changé, on renvoie la tuile).
    assert _tile_response(_req('"perime00000000000000000000000000"'), body, etag).status_code == 200


def test_brotli_sur_les_tuiles_et_repli_gzip():
    """G1 lot 3 — la tuile sort en brotli quand le client l'accepte (Accept-Encoding: br) ; le corps
    est bien brotli (décompresse à l'identique) et `Vary: Accept-Encoding` est posé. Sans br mais
    avec gzip, on NE pose PAS Content-Encoding (c'est le GZipMiddleware qui gzip-e → on retire aussi
    notre Vary pour ne pas le dupliquer). En identity (ni br ni gzip), le Vary est conservé."""
    import brotli

    from labuse.api.tiles import _etag, _tile_response

    body = b"octets de tuile mvt" * 500   # > 0, compressible
    etag = _etag(body)

    # br accepté → Content-Encoding: br, corps brotli, Vary présent
    r = _tile_response(_req(accept_encoding="gzip, br"), body, etag)
    assert r.status_code == 200
    assert r.headers.get("content-encoding") == "br"
    assert r.headers.get("vary") == "Accept-Encoding"
    assert brotli.decompress(r.body) == body          # décompresse à l'identique
    assert len(r.body) < len(body)                     # effectivement compressé

    # gzip seul → pas de Content-Encoding posé par nous, Vary retiré (GZipMiddleware s'en charge)
    rg = _tile_response(_req(accept_encoding="gzip"), body, etag)
    assert rg.status_code == 200
    assert "content-encoding" not in {k.lower() for k in rg.headers}
    assert "vary" not in {k.lower() for k in rg.headers}
    assert rg.body == body                             # corps brut (le middleware gzip-era)

    # identity (aucun encodage accepté) → corps brut + Vary conservé pour les caches partagés
    ri = _tile_response(_req(), body, etag)
    assert "content-encoding" not in {k.lower() for k in ri.headers}
    assert ri.headers.get("vary") == "Accept-Encoding"


def _mvt_layer_name_extent(buf: bytes):
    """Décodeur MVT minimal (sans dépendance) : retourne (name, extent) du 1er layer, ou None."""
    def varint(b, i):
        s = v = 0
        while True:
            x = b[i]; i += 1; v |= (x & 0x7F) << s
            if not x & 0x80:
                return v, i
            s += 7
    i, n = 0, len(buf)
    while i < n:
        key, i = varint(buf, i); field, wt = key >> 3, key & 7
        if field == 3 and wt == 2:          # Tile.layers
            ln, i = varint(buf, i); lb = buf[i:i + ln]; i += ln
            name, extent, j, m = None, 4096, 0, len(lb)
            while j < m:
                k2, j = varint(lb, j); f2, w2 = k2 >> 3, k2 & 7
                if f2 == 1 and w2 == 2:
                    l2, j = varint(lb, j); name = lb[j:j + l2].decode("utf-8", "replace"); j += l2
                elif f2 == 5 and w2 == 0:
                    extent, j = varint(lb, j)
                elif w2 == 0:
                    _, j = varint(lb, j)
                elif w2 == 2:
                    l2, j = varint(lb, j); j += l2
                elif w2 == 5:
                    j += 4
                else:
                    j += 8
            return name, extent
        elif wt == 0:
            _, i = varint(buf, i)
        elif wt == 2:
            l2, i = varint(buf, i); i += l2
        elif wt == 5:
            i += 4
        else:
            i += 8
    return None


def test_layer_parcels_et_extent(engine):
    """G1 lot 1 — GARDE ANTI-RÉGRESSION : la tuile parcelles sort nommée `parcels` (jamais `default`)
    et à l'extent attendu (1024 à z≤11, 4096 à z≥12). Le bug d'origine plaçait l'`ORDER BY` après le
    1er argument de ST_AsMVT → 'parcels'/extent avalés comme clés de tri → layer `default`, extent 4096.
    Skip si mvt_parcels absente/vide (jeu de données non semé en CI)."""
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    from labuse.api import tiles

    with Session(engine) as db:
        if not db.execute(text("SELECT to_regclass('mvt_parcels')")).scalar():
            pytest.skip("mvt_parcels absente")
        ext = db.execute(text("SELECT ST_XMin(e),ST_XMax(e),ST_YMin(e),ST_YMax(e) "
                              "FROM (SELECT ST_Extent(geom_3857) e FROM mvt_parcels) t")).first()
        if not ext or ext[0] is None:
            pytest.skip("mvt_parcels vide")
        W = 20037508.342789244
        # une tuile couvrant l'emprise, à z11 (extent attendu 1024) et z13 (4096)
        for z, want_extent in ((11, 1024), (13, 4096)):
            span = (2 * W) / (2 ** z)
            x = int((ext[0] + W) // span); y = int((W - ext[3]) // span)
            body = tiles._parcel_tile_bytes(db, z, x, y)
            if not body:
                continue
            name, extent = _mvt_layer_name_extent(body)
            assert name == "parcels", f"z{z}: layer={name!r} (attendu 'parcels' — ORDER BY mal placé ?)"
            assert extent == want_extent, f"z{z}: extent={extent} (attendu {want_extent})"
