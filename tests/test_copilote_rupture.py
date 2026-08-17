"""M111 — la rupture de sujet, côté router (_normalise). Tests DÉTERMINISTES (pure, aucun modèle).

Un tour AUTONOME (nouveau_sujet) part de ses seuls paramètres ; une CONTINUATION hérite du fil,
sans JAMAIS sommer, et l'héritage est TRACÉ (le récap le nomme).
"""
from __future__ import annotations

from labuse.copilote_v2.router import _normalise


def test_nouveau_sujet_n_herite_pas():
    r = _normalise({"intent": "QUESTION", "params": {"commune": "Saint-Denis"}, "nouveau_sujet": True},
                   prior_params={"surface_min": 20000, "programme_logements": 30})
    assert r.params == {"commune": "Saint-Denis"}      # aucun « ≥ 20000 » hérité
    assert r.nouveau_sujet and not r.herites


def test_continuation_herite_et_trace():
    r = _normalise({"intent": "RECHERCHE", "params": {"commune": "Cilaos"}, "nouveau_sujet": False},
                   prior_params={"commune": "Saint-Paul", "surface_min": 1000})
    assert r.params == {"commune": "Cilaos", "surface_min": 1000}   # commune remplacée, surface héritée
    assert r.herites == {"surface_min": 1000}          # tracé pour que le récap le nomme
    assert not r.nouveau_sujet


def test_jamais_de_somme():
    r = _normalise({"intent": "RECHERCHE", "params": {"programme_logements": 8}, "nouveau_sujet": False},
                   prior_params={"programme_logements": 30})
    assert r.params["programme_logements"] == 8         # la plus récente (8), JAMAIS 38


def test_defaut_omis_herite_mais_fil_neuf_sans_prior_ne_contamine_pas():
    # champ omis → défaut prudent HÉRITER (protège la clarification) ; mais sans prior, rien à hériter.
    r = _normalise({"intent": "QUESTION", "params": {"commune": "Saint-Leu"}}, prior_params=None)
    assert not r.nouveau_sujet and r.params == {"commune": "Saint-Leu"} and not r.herites
    # avec prior et champ omis → héritage (tracé), jamais muet
    r2 = _normalise({"intent": "QUESTION", "params": {"commune": "Saint-Leu"}},
                    prior_params={"surface_min": 5000})
    assert r2.params == {"commune": "Saint-Leu", "surface_min": 5000} and r2.herites == {"surface_min": 5000}
