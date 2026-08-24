"""FIX-SOURCES — le compte AFFICHÉ == le compte ANNONCÉ (S1), statut normalisé & gardé (S2),
licence dérivée de la base (S6). Verrous de non-régression du mandat FIX-SOURCES."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import sources_catalog as sc
from labuse.sources_catalog import est_affichee, normalize_status

pytestmark = pytest.mark.db


def test_normalize_status_normalise_et_refuse():
    """S2 — la garde d'ingestion normalise la casse et REFUSE tout statut hors enum."""
    assert normalize_status("CONNECTE") == "connecte"
    assert normalize_status(" Manuel ") == "manuel"
    for mauvais in ("bidon", None, ""):
        with pytest.raises(ValueError):
            normalize_status(mauvais)


def test_est_affichee_statut_insensible_casse():
    """S2 — une casse aberrante ('CONNECTE') n'efface plus une source servie ; le statut est
    désormais DANS le prédicat (avant, il n'y était pas → l'endpoint filtrait à part et divergeait)."""
    assert est_affichee("CoSIA", "", "CONNECTE") is True
    assert est_affichee("X", "", "connecte") is True
    assert est_affichee("X", "", "manuel") is True
    assert est_affichee("X", "", "a_faire") is False
    assert est_affichee("X", "", "hub") is False
    assert est_affichee("X", "DOUBLON de Y", "connecte") is False
    assert est_affichee("X", "RETIRÉ — abandon", "connecte") is False


def test_selection_sql_egale_predicat_python(db_session):
    """S1 — les DEUX chemins comptent le MÊME ensemble : le SQL WHERE_AFFICHEES (compteur d'accueil)
    et le prédicat Python est_affichee (endpoint /sources). Page rendue == chiffre annoncé, par
    construction — plus jamais 58 annoncés / 56 montrés. Indépendant du contenu de la base."""
    s = db_session
    sql_n = s.execute(text(f"SELECT count(*) FROM data_sources WHERE {sc.WHERE_AFFICHEES}"),
                      {"masquees": sc.masquees_param()}).scalar()
    rows = s.execute(text("SELECT name, technical_notes, status FROM data_sources")).mappings().all()
    py_n = sum(1 for r in rows if est_affichee(r["name"], r["technical_notes"], r["status"]))
    assert sql_n == py_n and sql_n > 0


def test_endpoint_sources_egale_compteur_accueil(db_session):
    """S1 (bout en bout) — le nombre de lignes rendues par /sources == le compteur 'sources' de
    l'accueil. On appelle les deux fonctions d'endpoint directement sur la même session."""
    from labuse.api.app import list_sources
    from labuse.api import accueil
    accueil._cache["data"] = None                       # neutralise le cache module-level
    servies = list_sources(db=db_session)
    n_accueil = accueil.accueil_chiffres(db=db_session)["sources"]
    assert len(servies) == n_accueil and n_accueil > 0


def test_boot_normalise_un_statut_mal_case(db_session):
    """S2 — la normalisation idempotente répare un 'CONNECTE' déjà en base (posé par un ingester
    bavard via raw SQL qui contourne l'ORM, comme le vrai bug CoSIA), de façon reproductible et sans
    UPDATE manuel. Après réparation : statut 'connecte', source de nouveau AFFICHÉE et comptée."""
    from labuse.models import normalize_data_sources_status
    s = db_session
    s.execute(text("INSERT INTO data_sources (name, category, status) "
                   "VALUES ('_fix_src_maj', 'occupation_sol', 'CONNECTE')"))
    avant = s.execute(text("SELECT status FROM data_sources WHERE name='_fix_src_maj'")).scalar()
    assert avant == "CONNECTE"                          # casse aberrante posée
    n = normalize_data_sources_status(s)
    apres = s.execute(text("SELECT status FROM data_sources WHERE name='_fix_src_maj'")).scalar()
    assert n >= 1 and apres == "connecte"
    assert est_affichee("_fix_src_maj", None, apres) is True


def test_licence_derivee_de_legal_notes(db_session):
    """S6 — la licence est DÉRIVÉE de legal_notes côté serveur (aucune carte par nom). Le libellé clé
    sur le DÉBUT du texte : « … RNE INPI » noyé dans une note DINUM ne se fait PAS passer pour INPI."""
    from labuse.api.app import _source_licence
    assert _source_licence("Licence Ouverte + art. L.112 A LPF : interdiction de reventilation")[
        "license_label"] == "Licence Ouverte — usage encadré (art. L.112 A LPF)"
    assert _source_licence("Licence Ouverte (open data DINUM, agrégat Sirene INSEE / RNE INPI)")[
        "license_label"] == "Licence Ouverte 2.0 (Etalab)"
    assert _source_licence("Licence INPI RNE 2024 (licence spécifique)")[
        "license_label"] == "Licence INPI — réutilisation encadrée (L. 323-2 CRPA)"
    assert _source_licence("Licence à confirmer (proxy RPG)")["license_label"] == "Licence à confirmer"
    assert _source_licence(None)["license_label"] == "Licence à confirmer"
    # le lien officiel accompagne les licences connues, jamais inventé
    assert _source_licence("ODbL 1.0 — attribution OSM")["license_url"].startswith("https://")
