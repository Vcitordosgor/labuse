"""Pagination voirie/water BD TOPO (correctif plafond WFS 5 000) — mock WFS, AUCUNE base, AUCUN réseau.

Le serveur Géoplateforme cape une réponse GetFeature à 5 000 entités. `ingest_bdtopo` doit PAGINER
(count/startIndex + tri stable cleabs) jusqu'à une page incomplète, sans doublon, avec garde-fou
anti-boucle. Ces tests verrouillent ce comportement et la NON-régression du bâti (déjà paginé).
Tout est mocké : `WfsConnector` (zéro réseau) et `_insert_layer` (zéro écriture base).
"""
from __future__ import annotations

from labuse.ingestion import layers_ingest


def _install_mocks(monkeypatch, page_counts, nature="Route"):
    """Remplace WfsConnector (réseau) et _insert_layer (base). `page_counts` : liste de tailles de
    page OU callable(idx)->taille. `nature` : valeur de l'attribut BD TOPO `nature` posée sur chaque
    feature mockée (ex. « Ravine » pour la régression ravines, filtrée sur `nature=='Ravine'`).
    Renvoie la liste des appels fetch_layer (pour les assertions)."""
    calls: list[dict] = []
    inserted: list[str] = []

    class FakeWfs:
        def __init__(self, *a, **k):
            pass

        def fetch_layer(self, endpoint_key, typename, bbox=None, max_features=1000,
                        start_index=0, sort_by=None):
            calls.append({"start_index": start_index, "sort_by": sort_by, "max_features": max_features})
            idx = start_index // max_features if max_features else 0
            cnt = page_counts(idx) if callable(page_counts) else (page_counts[idx] if idx < len(page_counts) else 0)
            feats = [{"geometry": {"type": "Point", "coordinates": [55.0 + start_index + i, -21.0]},
                      "properties": {"nature": nature, "cleabs": f"BDTOPO{start_index:07d}_{i}"}}
                     for i in range(cnt)]
            return {"features": feats}

    monkeypatch.setattr(layers_ingest, "WfsConnector", FakeWfs)
    # _insert_layer no-op qui enregistre la géométrie insérée (pour vérifier l'absence de doublon).
    monkeypatch.setattr(layers_ingest, "_insert_layer",
                        lambda session, kind, subtype, name, geom, src, commune, run_id, attrs:
                        inserted.append(str(geom)))
    return calls, inserted


def _voirie(monkeypatch, page_counts, **kw):
    calls, inserted = _install_mocks(monkeypatch, page_counts)
    n = layers_ingest.ingest_bdtopo(None, (0, 0, 1, 1), "Test", 1, {},
                                    "voirie", "BDTOPO_V3:troncon_de_route", **kw)
    return n, calls, inserted


# ── Pagination : récupère TOUTES les pages ────────────────────────────────────
def test_une_page_sous_5000(monkeypatch):
    n, calls, _ = _voirie(monkeypatch, [3000])
    assert n == 3000                         # tout récupéré
    assert len(calls) == 1                   # une seule requête (page incomplète → stop)


def test_deux_pages_5000_plus_1200(monkeypatch):
    n, calls, _ = _voirie(monkeypatch, [5000, 1200])
    assert n == 6200                         # AU-DELÀ du plafond 5 000 → preuve de pagination
    assert len(calls) == 2
    assert [c["start_index"] for c in calls] == [0, 5000]


def test_multiple_exact_de_5000(monkeypatch):
    # 10 000 pile : 2 pages pleines puis une page vide (len 0 < page_size) → stop.
    n, calls, _ = _voirie(monkeypatch, [5000, 5000])
    assert n == 10000
    assert len(calls) == 3
    assert [c["start_index"] for c in calls] == [0, 5000, 10000]


def test_arret_sur_page_vide_directe(monkeypatch):
    n, calls, _ = _voirie(monkeypatch, [0])
    assert n == 0 and len(calls) == 1        # page vide d'emblée → un appel, stop


# ── Tri stable + absence de doublon (fenêtres startIndex non chevauchantes) ───
def test_tri_stable_cleabs_sur_chaque_page(monkeypatch):
    _, calls, _ = _voirie(monkeypatch, [5000, 5000, 100])
    assert all(c["sort_by"] == "cleabs" for c in calls)        # tri stable obligatoire


def test_pas_de_doublon_fenetres_non_chevauchantes(monkeypatch):
    n, calls, inserted = _voirie(monkeypatch, [5000, 1200])
    # startIndex 0 puis 5000 (pages disjointes) + tri stable → aucune géométrie en double.
    starts = [c["start_index"] for c in calls]
    assert starts == sorted(set(starts))                       # strictement croissant, sans répétition
    assert len(inserted) == len(set(inserted)) == n            # 0 doublon inséré


# ── Garde-fou anti-boucle ─────────────────────────────────────────────────────
def test_garde_fou_anti_boucle(monkeypatch):
    # Serveur « pathologique » qui renvoie TOUJOURS une page pleine : sans garde-fou = boucle infinie.
    n, calls, _ = _voirie(monkeypatch, lambda idx: 5000, page_size=5000, max_total=15000)
    assert n == 15000                        # s'arrête au plafond max_total
    assert len(calls) == 3                   # 0, 5000, 10000 puis start=15000 >= max_total → stop


# ── Régression : bâti déjà paginé NE DOIT PAS être cassé ──────────────────────
def test_regression_batiment_pagine(monkeypatch):
    calls, inserted = _install_mocks(monkeypatch, [5000, 1200])
    n = layers_ingest.ingest_batiments(None, (0, 0, 1, 1), "Test", 1, {})
    assert n == 6200                         # bâti toujours paginé (inchangé)
    assert len(calls) == 2 and all(c["sort_by"] == "cleabs" for c in calls)


def test_regression_ravines_paginees(monkeypatch):
    # ravines : page_size 1000 → 1000 + 1000 + 300 = 2300, 3 pages. `ingest_ravines` filtre
    # `nature == 'Ravine'` → on pose nature="Ravine" sur les features mockées (sinon tout est écarté).
    calls, _ = _install_mocks(monkeypatch, [1000, 1000, 300], nature="Ravine")
    n = layers_ingest.ingest_ravines(None, (0, 0, 1, 1), "Test", 1, {})
    assert n == 2300
    assert [c["start_index"] for c in calls] == [0, 1000, 2000]
