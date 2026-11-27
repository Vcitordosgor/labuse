"""Une nouvelle livraison OSM ne doit pas supprimer les catégories des autres parcours."""
import pytest
from sqlalchemy import text

from labuse.ingestion import amenites


@pytest.mark.db
def test_distances_et_affichage_restant_coherents_sur_la_carte(db_session, monkeypatch):
    db = db_session
    db.execute(text('''CREATE TEMP TABLE tuyau_subdivise ON COMMIT DROP AS SELECT
        kind,subtype,name,commune,attrs,data_source_id,geom_2975 FROM spatial_layers WITH NO DATA'''))
    db.execute(text('''CREATE TEMP TABLE mvt_meta(key text PRIMARY KEY,value text,updated_at timestamptz)
        ON COMMIT DROP'''))
    ville = 'Commune de recette OSM'
    bbox = (55.3, -21.2, 55.5, -21.0)
    element = {'type': 'node', 'id': 1234, 'lat': -21.1, 'lon': 55.4, 'tags': {'name': 'Équipement témoin'}}
    monkeypatch.setattr(amenites, '_overpass', lambda query: {'elements': [element]})
    # Les appels qui utilisaient les triplets du parseur gardent le même format.
    assert list(amenites._points({'elements': [element]})) == [(55.4, -21.1, 'Équipement témoin')]
    amenites.ingest_poi_affichage(db, ville, bbox)
    amenites.ingest_poi_commune(db, ville, bbox)
    amenites.ingest_poi_commune(db, ville, bbox)
    amenites.ingest_poi_affichage(db, ville, bbox)
    for table in ('spatial_layers', 'tuyau_subdivise'):
        result = db.execute(text(f'''SELECT subtype,attrs->>'osm_id' FROM {table}
            WHERE commune=:c AND kind='amenite' '''), {'c': ville}).all()
        assert sorted(result) == sorted((cat, '1234') for cat in {**amenites.CATEGORIES, **amenites.CATEGORIES_AFFICHAGE})
    assert db.execute(text("SELECT value FROM mvt_meta WHERE key='tuyau_rev'")).scalar_one()
    # Overpass peut répondre en HTTP 200 avec une erreur et des résultats tronqués.
    monkeypatch.setattr(amenites, '_overpass', lambda query: {'elements': [], 'remark': 'runtime error: timeout'})
    with pytest.raises(ValueError, match='incomplète'):
        amenites.ingest_poi_commune(db, ville, bbox)
    assert db.execute(text('SELECT count(*) FROM tuyau_subdivise WHERE commune=:c'), {'c': ville}).scalar_one() == 10
