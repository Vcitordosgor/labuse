"""M-A — garde `check_unicite_pm` (unicité du lien personne morale ↔ parcelle avant service).

Mesuré : `parcelle_personne_morale` a une PK sur `idu` → 0 doublon en prod. La garde est la
vérification EXPLICITE de l'invariant. Test DB réel : on RETIRE la PK dans la transaction du test
(rollback en fin de fixture), on introduit un VRAI doublon, et on vérifie que la garde le détecte —
puis qu'elle dit OK quand l'unicité tient. Régime bruyant, JAMAIS bloquant.
"""
from __future__ import annotations

from sqlalchemy import text

from labuse import bascule_gardes as bg


def _insert_pm(session, idu, siren):
    session.execute(text(
        "INSERT INTO parcelle_personne_morale (idu, siren, date_import) "
        "VALUES (:idu, :siren, now())"), {"idu": idu, "siren": siren})


def test_ok_quand_lien_unique(db_session):
    # base de test : pas de doublon → statut OK, jamais d'exception
    out = bg.check_unicite_pm(session=db_session)
    assert out["statut"] == "OK" and out["n_doublons_idu"] == 0


def test_detecte_doublon_introduit(db_session):
    # on lève la PK LE TEMPS DU TEST (la fixture rollback la rétablit), puis on double un idu
    db_session.execute(text(
        "ALTER TABLE parcelle_personne_morale DROP CONSTRAINT IF EXISTS parcelle_personne_morale_pkey"))
    _insert_pm(db_session, "97415000AA0001", "111111111")
    _insert_pm(db_session, "97415000AA0001", "222222222")   # même idu, 2ᵉ lien = doublon

    out = bg.check_unicite_pm(session=db_session)
    assert out["statut"] == "DOUBLONS"
    assert out["n_doublons_idu"] >= 1
    assert "97415000AA0001" in out["idus"]


def test_garde_ne_leve_jamais(db_session):
    # même avec un doublon, la garde est NON bloquante (retourne, ne lève pas)
    db_session.execute(text(
        "ALTER TABLE parcelle_personne_morale DROP CONSTRAINT IF EXISTS parcelle_personne_morale_pkey"))
    _insert_pm(db_session, "97415000BB0002", "333333333")
    _insert_pm(db_session, "97415000BB0002", "444444444")
    out = bg.check_unicite_pm(session=db_session)   # ne doit pas lever
    assert out["statut"] == "DOUBLONS"
