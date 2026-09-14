"""SOURCES-4 lot 1 — surfacer les champs qui dormaient dans `raw`.

CatNat : la fiche commune ne servait que le COMPTE d'arrêtés (`catnat_n`). Le détail — péril,
dates de début/fin/arrêté, code national et date de publication au JO — existait en base
(colonnes + `raw`) mais n'avait ni place à l'écran ni identifiant au registre. On garde ici que
`fiche_commune.risques` sert désormais la liste détaillée (`catnat_detail`).
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse.ingestion.catnat import DDL


@pytest.mark.db
def test_catnat_detail_surface_peril_dates_code_national(db_session):
    for stmt in [s for s in DDL.split(";") if s.strip()]:
        db_session.execute(text(stmt))
    db_session.execute(text("DELETE FROM catnat_arretes WHERE insee = '97499'"))
    db_session.execute(text("""
        INSERT INTO catnat_arretes (insee, commune, type_peril, date_arrete, date_debut, date_fin, raw)
        VALUES (:i, 'TestCommune', :p, :a, :d, :f, CAST(:raw AS jsonb))"""),
        {"i": "97499", "p": "Inondations et/ou Coulées de Boue",
         "a": "2024-01-19", "d": "2024-01-13", "f": "2024-01-15",
         "raw": json.dumps({"code_national_catnat": "IOME2401804A", "date_publication_jo": "23/01/2024"})})

    from labuse.api import fiche_commune
    r = fiche_commune.risques(db_session, "TestCommune", "97499")

    assert r["catnat_arretes"] == 1
    assert len(r["catnat_detail"]) == 1
    a = r["catnat_detail"][0]
    assert a["type_peril"] == "Inondations et/ou Coulées de Boue"
    assert a["date_debut"] == "2024-01-13" and a["date_fin"] == "2024-01-15"
    assert a["date_arrete"] == "2024-01-19"
    assert a["code_national"] == "IOME2401804A"          # jusque-là seulement dans raw
    assert a["date_publication_jo"] == "23/01/2024"      # idem


@pytest.mark.db
def test_catnat_detail_liste_declaree_au_registre():
    """La donnée servie doit exister au registre (rien ne s'affiche hors registre)."""
    from labuse.registre import donnees, robinets
    assert "catnat_arretes_liste" in donnees.DONNEES
    assert donnees.DONNEES["catnat_arretes_liste"].type == "liste"
    # servie par le robinet de la fiche commune (mono-robinet)
    serveurs = [rid for rid, r in robinets.ROBINETS.items()
                if "catnat_arretes_liste" in r.chiffres]
    assert serveurs == ["fiche_commune_risques"]


def test_lls_inventaire_n_declare_au_registre():
    """SOURCES-4 lot 2 — l'effectif brut de LLS (inventaire SRU) est déclaré et servi sur la carte
    SRU de la fiche commune (jusque-là seul le taux l'était ; nb_lls dormait dans detail)."""
    from labuse.registre import donnees, robinets
    assert "lls_inventaire_n" in donnees.DONNEES
    d = donnees.DONNEES["lls_inventaire_n"]
    assert d.unite == "logements" and d.reservoirs == ("sru_dhup",)
    serveurs = [rid for rid, r in robinets.ROBINETS.items()
                if "lls_inventaire_n" in r.chiffres]
    assert serveurs == ["fiche_commune_sru"]
