"""RADAR P6 · D3 — onglet Marché : agrégats par commune + HONNÊTETÉ STATISTIQUE (n<5 = insuffisant).

On sème peu de biens (< 5) et on gèle : les COMPTES sont servis (faits bruts), mais les MESURES
(médianes, taux, part) restent MASQUÉES (« échantillon insuffisant ») tant que n < 5. Les 24 communes
sont toujours présentes (état de démarrage digne). [RADAR-TEST] purgés en fin.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import marche

pytestmark = pytest.mark.db


@pytest.fixture
def seed(engine):
    tag = uuid.uuid4().hex[:4].upper()
    ids = []
    with session_scope() as s:
        def bien(commune, typ, statut, prix, st=None, sh=None):
            bid = s.execute(text("INSERT INTO pige_biens (commune,type_bien,est_copro,rattachement_niveau,statut,date_publication) "
                                 "VALUES (:c,:t,false,'absent',:s,current_date-10) RETURNING bien_id"),
                            {"c": commune, "t": typ, "s": statut}).scalar()
            s.execute(text("INSERT INTO pige_faits (bien_id,prix,type_bien,surface_terrain,surface_hab,particulier_pro,valide_at) "
                           "VALUES (:b,:p,:t,:st,:sh,'particulier',now())"), {"b": bid, "p": prix, "t": typ, "st": st, "sh": sh})
            ids.append(bid)
            return bid
        # 3 terrains à Cilaos (n=3 < 5) → médiane €/m² terrain MASQUÉE
        for p, st in ((100000, 1000), (120000, 1000), (140000, 1000)):
            bien("Cilaos", "terrain", "active", p, st=st)
    yield ids
    with session_scope() as s:
        s.execute(text("DELETE FROM pige_biens WHERE bien_id = ANY(:i)"), {"i": ids})


def test_les_24_communes_toujours_presentes(seed):
    with session_scope() as db:
        r = marche.stats(db)
    assert len(r["communes"]) == 24 and r["ile"]["commune"] == "Toute l'île"
    assert r["seuil_n"] == 5


def test_comptes_servis_mesures_masquees_sous_5(seed):
    with session_scope() as db:
        r = marche.stats(db)
    cilaos = next(l for l in r["communes"] if l["commune"] == "Cilaos")
    # COMPTE = fait brut, servi : 3 annonces actives
    assert cilaos["actives"] == 3
    # MESURE = masquée car n = 3 < 5 : pas de médiane €/m² terrain, mais le n est dit
    assert cilaos["prix_m2_terrain"]["insuffisant"] is True
    assert cilaos["prix_m2_terrain"]["valeur"] is None and cilaos["prix_m2_terrain"]["n"] == 3


def test_etat_de_demarrage_digne(seed):
    """Une commune sans bien : comptes à 0, mesures insuffisantes — jamais une erreur, jamais un chiffre faux."""
    with session_scope() as db:
        r = marche.stats(db)
    vide = next(l for l in r["communes"] if l["commune"] == "Sainte-Rose")
    assert vide["actives"] == 0 and vide["prix_m2_bati"]["insuffisant"] is True and vide["prix_m2_bati"]["n"] == 0
