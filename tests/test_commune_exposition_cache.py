from unittest.mock import Mock

import pytest
from sqlalchemy import text

from labuse.api.exposition_commune import exposition


@pytest.mark.db
def test_cache_suit_les_parcelles_et_les_couches_limitrophes(db_session):
    # Tables privées à la connexion : les UPDATE gardent le même xmin dans ce test.
    for ddl in (
        "CREATE TEMP TABLE parcels (id int, commune text, vivant boolean)",
        "CREATE TEMP TABLE spatial_layers (id int, kind text, subtype text, forme int)",
        """CREATE TEMP TABLE commune_exposition_cache (
             commune text PRIMARY KEY, empreinte text, ppr_pct float, mvt_pct float,
             parc boolean, repli boolean)""",
        "INSERT INTO parcels VALUES (1, 'Cilaos', true), (2, 'Saint-Paul', true)",
        "INSERT INTO spatial_layers VALUES (1, 'ppr', NULL, 1), (2, 'batiment', NULL, 1)",
    ):
        db_session.execute(text(ddl))

    calcul = Mock(return_value=(50., 25., True, False))

    def lire():
        return exposition(db_session, "Cilaos", calcul)

    assert lire() == lire() == calcul.return_value
    db_session.execute(text("UPDATE spatial_layers SET forme = 2 WHERE kind = 'batiment'"))
    db_session.execute(text("UPDATE parcels SET vivant = false WHERE commune = 'Saint-Paul'"))
    lire()
    assert calcul.call_count == 1
    for sql in (
        "UPDATE parcels SET vivant = false WHERE commune = 'Cilaos'",
        "INSERT INTO spatial_layers VALUES (3, 'georisque_alea', 'mouvement_terrain', 1)",
        "UPDATE spatial_layers SET forme = 3 WHERE kind = 'ppr'",
        "DELETE FROM spatial_layers WHERE kind = 'ppr'",
    ):
        db_session.execute(text(sql))
        lire()
    assert calcul.call_count == 5


@pytest.mark.parametrize("bloc_en_echec", [False, True])
def test_premiere_ouverture_ne_memorise_qu_un_calcul_sans_rollback(monkeypatch, bloc_en_echec):
    from importlib import import_module

    api = import_module("labuse.api.app")
    db = Mock()
    transaction = object()
    db.get_transaction.side_effect = [transaction, object() if bloc_en_echec else transaction]
    db.execute.return_value.mappings.return_value.first.return_value = None
    payload = {"commune": "Cilaos", "insee": "97424"}
    monkeypatch.setattr(api, "_ensure_contexte_cache", Mock())
    monkeypatch.setattr("labuse.fraicheur_caches.empreinte_attendue", lambda _: "version")
    monkeypatch.setattr(api, "_compute_commune_contexte", Mock(return_value=payload))
    enregistrer = Mock()
    monkeypatch.setattr(api, "_enregistrer_contexte_cache", enregistrer)

    assert api.commune_contexte("Cilaos", db) == {**payload, "cache_calcule_le": None}
    if bloc_en_echec:
        enregistrer.assert_not_called()
    else:
        enregistrer.assert_called_once_with(db, "Cilaos", payload, "version")
