"""Statut d'ouverture AU + péremption (mandat AU-OUVERTURE, arbitrage Vic 30/07).

Couvre le classifieur (générique / dimensions-seules / non marqué) et les seuils de péremption
(WARN 90 j, BLOCAGE 180 j). La garde de bascule et le journal d'ack sont testés en intégration
(script bascule) ; ici on verrouille la logique pure, sans DB.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.faisabilite.au_statut import (
    statut_peremption, STATUT_OK, STATUT_WARN, STATUT_BLOCAGE,
    SEUIL_WARN_JOURS, SEUIL_BLOCAGE_JOURS,
    CLASSE_GENERIQUE, CLASSE_DIMENSIONS_SEULES,
    CLASSES_DECLASSANTES, CLASSES_SERVIES,
)
from labuse.faisabilite.constructibilite import (
    DECLASSE_AU_FERMEE, DECLASSE_AU_STATUT_INCONNU, AU_SOUS_PLANCHER,
)

_WKT = "POLYGON((55.30 -21.00,55.31 -21.00,55.31 -20.99,55.30 -20.99,55.30 -21.00))"


def _parcel(s, idu: str, commune: str = "AUville") -> int:
    return s.execute(text(
        "INSERT INTO parcels (idu, commune, geom, surface_m2, centroid) VALUES "
        "(:idu, :c, ST_GeomFromText(:w,4326), 1000, ST_Centroid(ST_GeomFromText(:w,4326))) "
        "RETURNING id"), {"idu": idu, "c": commune, "w": _WKT}).scalar()


def _mark(s, pid: int, idu: str, classe: str, jours: int) -> None:
    s.execute(text(
        "INSERT INTO parcel_au_statut (parcel_id, idu, classe, zone_lib, motif, computed_at) "
        "VALUES (:p, :idu, :c, 'AUa', 'm', now() - make_interval(days => :j))"),
        {"p": pid, "idu": idu, "c": classe, "j": jours})


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


def test_taxonomies_declassantes_vs_servies():
    """M-S — les deux taxonomies (ancien + affiné) sont bien réparties. `au_sous_plancher` est
    SERVIE, jamais déclassante (sinon elle bloquerait une bascule pour des parcelles servies)."""
    assert CLASSES_DECLASSANTES == {CLASSE_GENERIQUE, DECLASSE_AU_FERMEE, DECLASSE_AU_STATUT_INCONNU}
    assert AU_SOUS_PLANCHER in CLASSES_SERVIES
    assert AU_SOUS_PLANCHER not in CLASSES_DECLASSANTES
    assert CLASSES_DECLASSANTES.isdisjoint(CLASSES_SERVIES)


@pytest.mark.db
def test_peremption_compte_les_deux_taxonomies_pas_les_servies(db_session):
    """La garde compte les classes DÉCLASSANTES des DEUX modèles ; l'âge qui bloque ne regarde QUE
    les déclassantes. Régression visée : une `au_sous_plancher` (SERVIE) vieille de 300 j ne doit
    PAS faire passer le statut en `blocage` — avant M-S, `jours_plus_ancien` prenait le max sur
    TOUTES les classes et une servie ancienne bloquait une bascule à tort."""
    from labuse.faisabilite.au_statut import au_statut_peremption, declassees_perimees
    s = db_session
    # 3 déclassantes JEUNES (10 j) — l'une de chaque taxonomie
    for i, cls in enumerate(sorted(CLASSES_DECLASSANTES)):
        idu = f"AUD{i:011d}"
        _mark(s, _parcel(s, idu), idu, cls, jours=10)
    # 3 servies VIEILLES (300 j) — dont au_sous_plancher
    for i, cls in enumerate(sorted(CLASSES_SERVIES)):
        idu = f"AUS{i:011d}"
        _mark(s, _parcel(s, idu), idu, cls, jours=300)

    per = au_statut_peremption(s)
    assert per["declassees"] == 3            # les 3 déclassantes
    assert per["servies_avec_mention"] == 3  # les 3 servies (dont au_sous_plancher)
    # l'âge de blocage ne voit QUE les déclassantes (jeunes) → OK, malgré des servies à 300 j
    assert per["jours_plus_ancien"] <= 11
    assert per["statut"] == STATUT_OK
    # declassees_perimees (> 180 j) = 0 : les déclassantes sont jeunes, les servies ne comptent pas
    assert declassees_perimees(s, SEUIL_BLOCAGE_JOURS) == 0
    # inversement : une déclassante affinée périmée EST comptée (échappait au compteur avant M-S)
    idu = "AUDPERIMEE001"
    _mark(s, _parcel(s, idu), idu, DECLASSE_AU_FERMEE, jours=200)
    assert declassees_perimees(s, SEUIL_BLOCAGE_JOURS) == 1


@pytest.mark.db
def test_ancien_modele_ignore_les_communes_calibrees(db_session):
    """Préséance (Fix B) : l'ancien modèle N'ÉCRASE PAS une commune calibrée (le modèle affiné y
    prime). Une marque affinée `conditionnelle_operation` posée sur une commune calibrée survit à
    un passage de `build_au_statut_batch` — les deux modèles traitent des communes disjointes."""
    from labuse.faisabilite.au_statut import build_au_statut_batch
    from labuse.faisabilite.au_ouverture import OUVERTURE_CONDITIONNELLE, _config
    s = db_session
    calib = next(iter(_config().keys()))          # une commune calibrée (INSEE)
    idu = f"{calib}000AB0001"                      # 14 caractères
    pid = _parcel(s, idu, commune="Calibrée")
    s.execute(text("INSERT INTO parcel_au_statut (parcel_id, idu, classe, zone_lib, motif) "
                   "VALUES (:p, :idu, :c, 'AUa', 'mention affinée')"),
              {"p": pid, "idu": idu, "c": OUVERTURE_CONDITIONNELLE})
    n = build_au_statut_batch(s, [idu])
    assert n == 0                                 # l'ancien modèle ne touche pas la commune calibrée
    cls = s.execute(text("SELECT classe FROM parcel_au_statut WHERE parcel_id = :p"),
                    {"p": pid}).scalar()
    assert cls == OUVERTURE_CONDITIONNELLE        # marque affinée INTACTE
