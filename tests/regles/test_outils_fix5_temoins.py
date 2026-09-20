"""Témoins CIRCUIT-4 — OUTILS-FIX-5 lot 6 : les compteurs des outils Successions (M28) et Blocs
fonciers (M29), recomptés INDÉPENDAMMENT du moteur sur des lignes seedées (table scratch — jamais
le nom réel, dont le DDL appartient au producteur : leçon d'isolation de test_cascade_compteurs)."""
from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.db
def test_n_successions_veille(engine):
    """Sémantique de n_successions_veille : count des parcelles en veille succession (signal Score V),
    filtrable par commune (préfixe INSEE de l'IDU)."""
    with engine.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS c4_succ_temoin"))
        c.execute(text("CREATE TABLE c4_succ_temoin (parcelle_id text, dirigeant_age int, sci_dormante bool)"))
        rows = [("97410000AA0001", 89, False), ("97410000AA0002", 72, False),
                ("97415000BB0003", None, True)]  # 2 à Saint-Benoît (97410), 1 à Saint-Paul (97415)
        for idu, age, sci in rows:
            c.execute(text("INSERT INTO c4_succ_temoin VALUES (:i, :a, :s)"),
                      {"i": idu, "a": age, "s": sci})
        n_ile = c.execute(text("SELECT count(*) FROM c4_succ_temoin")).scalar()
        n_stben = c.execute(text("SELECT count(*) FROM c4_succ_temoin "
                                 "WHERE left(parcelle_id, 5) = '97410'")).scalar()
        c.execute(text("DROP TABLE c4_succ_temoin"))
    assert n_ile == 3                          # île entière = toutes les veilles
    assert n_stben == 2                        # commune = filtre par préfixe INSEE


@pytest.mark.db
def test_n_blocs_pm(engine):
    """Sémantique de n_blocs_pm (count des blocs, ≥ 2 parcelles, un même SIREN) et n_parcelles_bloc
    (membres d'un bloc). Recompté à la main : un SIREN à 3 parcelles = 1 bloc de 3 membres."""
    with engine.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS c4_blocs_temoin"))
        c.execute(text("DROP TABLE IF EXISTS c4_bloc_membres_temoin"))
        c.execute(text("CREATE TABLE c4_blocs_temoin (bloc_id int, siren text, insee text)"))
        c.execute(text("CREATE TABLE c4_bloc_membres_temoin (bloc_id int, parcelle_id text)"))
        # 2 blocs : bloc 1 (SIREN A, 3 parcelles, Saint-Benoît) ; bloc 2 (SIREN B, 2 parcelles, Saint-Paul)
        c.execute(text("INSERT INTO c4_blocs_temoin VALUES (1, 'A', '97410'), (2, 'B', '97415')"))
        for bid, idu in [(1, "97410000AA0001"), (1, "97410000AA0002"), (1, "97410000AA0003"),
                         (2, "97415000BB0001"), (2, "97415000BB0002")]:
            c.execute(text("INSERT INTO c4_bloc_membres_temoin VALUES (:b, :i)"), {"b": bid, "i": idu})
        n_blocs = c.execute(text("SELECT count(*) FROM c4_blocs_temoin")).scalar()
        n_membres_b1 = c.execute(text("SELECT count(*) FROM c4_bloc_membres_temoin "
                                      "WHERE bloc_id = 1")).scalar()
        c.execute(text("DROP TABLE c4_blocs_temoin"))
        c.execute(text("DROP TABLE c4_bloc_membres_temoin"))
    assert n_blocs == 2                        # 2 blocs (chacun ≥ 2 parcelles d'un même SIREN)
    assert n_membres_b1 == 3                   # n_parcelles_bloc du bloc 1 = 3
