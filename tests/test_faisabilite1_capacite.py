"""FAISABILITE-1 (lot B) — verrous du filtre global « Capacité ».

Le filtre Destination autorisée est traité à l'endpoint /filtre (accès base pour lever les
verdicts plu_destinations), PAS dans `_q_v2_where` (pur). Ces verrous sont DB-free : ils fixent
le contrat (champ query-param, entrée dans le memo, validation du slug, règle « calibration en
cours = non filtrée »). L'effet SQL sur le compteur est prouvé en recette (FAISABILITE-1.md).
"""
from __future__ import annotations

import dataclasses

from labuse.api.app import FiltreCriteres, _destination_interdit_keys
from labuse.plu.destinations import SOUS_DESTINATIONS


def test_destination_est_un_critere_du_filtre():
    """`destination` est un champ de FiltreCriteres → devient un query-param /filtre (comme les
    autres facettes) ; il entre dans la clé de mémorisation (sinon deux destinations partageraient
    le compteur caché)."""
    champs = {f.name for f in dataclasses.fields(FiltreCriteres)}
    assert "destination" in champs
    a = FiltreCriteres(source="q_v10_m129", destination="logement")
    b = FiltreCriteres(source="q_v10_m129", destination="hotels")
    n = FiltreCriteres(source="q_v10_m129")
    assert a.cache_key() != b.cache_key(), "deux destinations = deux compteurs mémorisés"
    assert a.cache_key() != n.cache_key(), "avec/sans destination = clés distinctes"
    assert a.cache_key()[-1] == "logement", "la destination est le dernier élément de la clé"


def test_slug_destination_connu():
    """Le slug par défaut du groupe Capacité (logement) et les sous-destinations filtrables
    existent bien au référentiel R151-28 (sinon l'endpoint renvoie 400)."""
    for slug in ("logement", "hotels", "artisanat_commerce_detail"):
        assert slug in SOUS_DESTINATIONS


def test_interdit_ignore_les_non_calibrees(monkeypatch):
    """Règle du mandat : « calibration en cours » (non calibrée) n'écarte JAMAIS une parcelle —
    seule une zone dont le règlement INTERDIT la destination est exclue. Vérifié sur un faux jeu
    de couples (commune, zone) sans base : verdict stubé, seule l'interdite ressort."""
    import labuse.api.app as app_mod

    class _Row:
        def __init__(self, commune, zone):
            self.commune, self.zone = commune, zone

    class _DB:
        def execute(self, *_a, **_k):
            class _R:
                @staticmethod
                def all():
                    return [_Row("A", "Zi"), _Row("A", "Zc"), _Row("A", "Zx")]
            return _R()

    def _fake_verdict(commune, zone, sd):
        if zone == "Zi":
            return {"etat_calibration": "calibree", "statut_effectif": "interdit"}
        if zone == "Zc":
            return {"etat_calibration": "non_calibree", "statut_effectif": "interdit"}  # non calibrée : ignorée
        return {"etat_calibration": "calibree", "statut_effectif": "autorise"}

    monkeypatch.setattr("labuse.plu.destinations.verdict", _fake_verdict)
    keys = _destination_interdit_keys(_DB(), "logement")
    assert keys == ["A||Zi"], "seule la zone calibrée ET interdite est écartée"
