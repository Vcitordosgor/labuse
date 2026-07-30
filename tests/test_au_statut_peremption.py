"""Statut d'ouverture AU + péremption (mandat AU-OUVERTURE, arbitrage Vic 30/07).

Couvre le classifieur (générique / dimensions-seules / non marqué) et les seuils de péremption
(WARN 90 j, BLOCAGE 180 j). La garde de bascule et le journal d'ack sont testés en intégration
(script bascule) ; ici on verrouille la logique pure, sans DB.
"""
from __future__ import annotations

from labuse.faisabilite.au_statut import (
    statut_peremption, STATUT_OK, STATUT_WARN, STATUT_BLOCAGE,
    SEUIL_WARN_JOURS, SEUIL_BLOCAGE_JOURS,
    CLASSE_GENERIQUE, CLASSE_DIMENSIONS_SEULES,
)


def test_seuils_peremption():
    assert SEUIL_WARN_JOURS == 90 and SEUIL_BLOCAGE_JOURS == 180
    # frontières exactes : le seuil est inclusif (>= bascule)
    assert statut_peremption(0) == STATUT_OK
    assert statut_peremption(89) == STATUT_OK
    assert statut_peremption(90) == STATUT_WARN
    assert statut_peremption(179) == STATUT_WARN
    assert statut_peremption(180) == STATUT_BLOCAGE
    assert statut_peremption(365) == STATUT_BLOCAGE


def test_classes_distinctes():
    # les deux classes marquées sont bien distinctes (l'une déclasse, l'autre reste servie)
    assert CLASSE_GENERIQUE != CLASSE_DIMENSIONS_SEULES
