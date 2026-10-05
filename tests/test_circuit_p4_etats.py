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
    # source SURVEILLÉE (vraie sonde api/page/entete/temoin active) dont l'agent n'est jamais passé
    # (aucun statut) → jamais vérifiée (gris, jamais jaune). C'est le SEUL cas « jamais vérifiée »
    # automatique (DASHBOARD-FIX-1 point 6 : même prédicat que /admin/sources).
    ({"veille": {"methode": "api", "statut": None, "passage": None}}, ("gris", "jamais vérifiée")),
    # DASHBOARD-FIX-1 (point 6) — source NON surveillée (aucune sonde amont câblée) : plus « jamais
    # vérifiée » (elle n'attend aucun agent) mais « à jour » par construction, comme /admin/sources
    # (non_surveillee, projeté « à jour » côté client).
    ({"veille": {"statut": None, "passage": None}}, ("mint", "à jour")),   # veille sans méthode = non surveillée
    ({}, ("mint", "à jour")),                                              # aucune veille du tout = non surveillée
    ({"veille": {"methode": "rappel", "statut": None}}, ("mint", "à jour")),  # rappel manuel ≠ sonde amont
    # sonde câblée mais DÉSACTIVÉE : non surveillée → à jour (pas « jamais vérifiée »)
    ({"veille": {"methode": "api", "actif": False, "statut": None}}, ("mint", "à jour")),
    # sonde passée, statut ok → à jour
    ({"veille": {"methode": "api", "statut": "ok", "passage": "2026-09-23"}}, ("mint", "à jour")),
    # CIRCUIT-P6 (tâche 2) — sans millésime par nature (OSM/INPI/Coût) : « à jour par construction »,
    # JAMAIS « jamais vérifiée », même sans aucune veille ni date de contrôle (rien à vérifier).
    ({"mode": "sans_millesime"}, ("mint", "à jour")),
    ({"mode": "sans_millesime", "veille": None, "dernier_controle": None}, ("mint", "à jour")),
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


def test_sans_millesime_a_jour_par_construction():
    """CIRCUIT-P6 (tâche 2) — une source SANS MILLÉSIME est « à jour » (mint), jamais « jamais
    vérifiée » (gris), et sa raison écrite est disponible par le nom du réservoir."""
    couleur, libelle = E.etat_reservoir({"mode": "sans_millesime"})
    assert (couleur, libelle) == ("mint", "à jour")
    assert libelle != "jamais vérifiée"
    # la raison écrite, par nom → chacun sa raison (OSM flux continu, INPI sans date, Coût interne)
    assert "flux continu" in E.raison_sans_millesime("OpenStreetMap / Overpass")
    assert "6.2" in E.raison_sans_millesime("INPI RNE (dirigeants)")
    assert "interne" in E.raison_sans_millesime("Coût de construction (EPTB SDES + choix LABUSE)")
    # un nom inconnu retombe sur la raison générique, jamais une erreur
    assert E.raison_sans_millesime("source inconnue") == E.DEFAUT_SANS_MILLESIME
