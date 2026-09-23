"""CIRCUIT-P4 (lot 1) — LA FONCTION D'ÉTAT, ramenée à trois états + un signal technique.

Cinq libellés SEULEMENT : à jour · nouvelle version · échue · jamais vérifiée · sonde en panne.
« À regarder » a disparu. Invariant : chaque source tombe dans une seule case, la somme = la vitrine.
"""
import pytest

from labuse import circuit_etats as E

CAS = [
    # nouvelle version publiée chez le producteur (automatique) → ambre
    ({"veille": {"statut": "nouvelle_version", "passage": "2026-09-23"}}, ("ambre", "nouvelle version")),
    # manuelle échue (échéance dépassée) → ambre
    ({"mode": "depot_manuel", "a_verifier": True, "dernier_controle": "2026-09-09"}, ("ambre", "échue")),
    # manuelle dans son échéance → à jour
    ({"mode": "depot_manuel", "a_verifier": False, "dernier_controle": "2026-09-20"}, ("mint", "à jour")),
    # manuelle jamais alimentée → jamais vérifiée (gris)
    ({"mode": "depot_manuel", "a_verifier": False, "dernier_controle": None}, ("gris", "jamais vérifiée")),
    # sonde en panne : 3 échecs NON-SSL consécutifs → rouge
    ({"veille": {"statut": "injoignable", "passage": "2026-09-20", "echecs_consecutifs": 3}},
     ("rouge", "sonde en panne")),
    # échec SSL (env local) n'est PAS une panne : garde le dernier état confirmé → à jour
    ({"veille": {"statut": "injoignable", "passage": "2026-09-20", "echecs_consecutifs": 9,
                 "dernier_message": "URLError CERTIFICATE_VERIFY_FAILED"}}, ("mint", "à jour")),
    # échec transitoire (< 3) : garde le dernier état confirmé → à jour
    ({"veille": {"statut": "injoignable", "passage": "2026-09-20", "echecs_consecutifs": 1}},
     ("mint", "à jour")),
    # aucun contrôle réussi (sonde jamais passée) → jamais vérifiée (gris, jamais jaune)
    ({"veille": {"statut": None, "passage": None}}, ("gris", "jamais vérifiée")),
    # aucune veille du tout → jamais vérifiée
    ({}, ("gris", "jamais vérifiée")),
    # sonde passée, statut ok → à jour
    ({"veille": {"statut": "ok", "passage": "2026-09-23"}}, ("mint", "à jour")),
]


@pytest.mark.parametrize("r,attendu", CAS)
def test_etat_reservoir(r, attendu):
    assert E.etat_reservoir(r) == attendu


def test_seulement_cinq_libelles():
    """La fonction ne rend JAMAIS un libellé hors des cinq de la maquette."""
    for r, _ in CAS:
        _, lib = E.etat_reservoir(r)
        assert lib in E.ETATS_SOURCE


def test_compter_etats_invariant():
    """La somme des cinq états = le nombre de réservoirs (chaque source dans une seule case)."""
    reservoirs = []
    for r, attendu in CAS:
        reservoirs.append({**r, "etat": list(attendu)})
    c = E.compter_etats(reservoirs)
    assert c["total"] == len(reservoirs)
    assert sum(c[lib] for lib in E.ETATS_SOURCE) == len(reservoirs)


def test_à_regarder_a_disparu():
    """Aucun des cinq libellés n'est « à regarder » (le mot a disparu du vocabulaire des états)."""
    assert "à regarder" not in E.ETATS_SOURCE
    assert all(lib != "à regarder" for lib in E.ETATS_SOURCE)
