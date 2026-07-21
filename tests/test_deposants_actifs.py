"""EXTRACT-DÉPOSANTS-ACTIFS : tests sur FIXTURES SYNTHÉTIQUES uniquement (jamais de données réelles
nominatives en git — précision Vic). Vérifie : fenêtre PC/PA, exclusion des dirigeants non diffusibles,
SIREN invalide écarté, CSV conforme.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion import deposants_actifs as da


def _ensure(s):
    s.execute(text("CREATE TABLE IF NOT EXISTS sitadel_permits (id serial PRIMARY KEY, permit_id text, "
                   "type text, date timestamptz, idu_codes jsonb, commune text, raw jsonb)"))
    s.execute(text("CREATE TABLE IF NOT EXISTS pm_dirigeants (id serial PRIMARY KEY, siren varchar(9), "
                   "nom text, prenoms text, role_entreprise text, actif boolean, diffusible boolean)"))
    s.execute(text("CREATE TABLE IF NOT EXISTS parcelle_personne_morale (idu varchar(14), siren varchar(9))"))


def _permit(s, siren, name, typ="PC", commune="Ville-T", months_ago=3, nb_lgt="4"):
    s.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, commune, raw) VALUES "
        "(:p, :t, now() - make_interval(months => :m), :c, "
        " jsonb_build_object('petitioner_siren', CAST(:s AS text), 'petitioner_name', CAST(:n AS text), "
        "                    'nb_lgt', CAST(:l AS text)))"),
        {"p": f"P{siren}{months_ago}", "t": typ, "m": months_ago, "c": commune, "s": siren, "n": name, "l": nb_lgt})


@pytest.mark.db
def test_extraction_fenetre_et_agregats(db_session):
    s = db_session
    _ensure(s)
    _permit(s, "111111111", "PROMO TEST SA", "PC", "Ville-A", 3)
    _permit(s, "111111111", "PROMO TEST SA", "PA", "Ville-B", 10, nb_lgt="12")
    _permit(s, "111111111", "PROMO TEST SA", "PC", "Ville-A", 40)   # hors fenêtre 24 mois
    _permit(s, "222222222", "AUTRE OPÉRATEUR", "DP", "Ville-A", 2)  # DP : pas un PC/PA → exclu
    rows = da.extract_deposants(s, mois=24)
    assert [r["siren"] for r in rows] == ["111111111"]
    r = rows[0]
    assert r["n_permis"] == 2 and r["n_pc"] == 1 and r["n_pa"] == 1
    assert "Ville-A" in r["communes"] and "Ville-B" in r["communes"]
    assert r["nb_logements"] == 16 and "SITADEL" in r["source"]


@pytest.mark.db
def test_dirigeant_non_diffusible_jamais_dans_le_csv(db_session):
    s = db_session
    _ensure(s)
    _permit(s, "333333333", "SCI FIXTURE")
    s.execute(text("INSERT INTO pm_dirigeants (siren, nom, prenoms, role_entreprise, actif, diffusible) VALUES "
                   "('333333333', 'VISIBLE', 'Jean', '30', true, true), "
                   "('333333333', 'MASQUE', 'Paul', '30', true, false), "     # non diffusible → JAMAIS
                   "('333333333', 'ANCIEN', 'Luc', '30', false, true)"))      # inactif → exclu
    rows = da.extract_deposants(s, mois=24)
    d = rows[0]["dirigeants"]
    assert "VISIBLE" in d and "rôle RNE 30" in d
    assert "MASQUE" not in d and "ANCIEN" not in d


@pytest.mark.db
def test_siren_invalide_ecarte(db_session):
    s = db_session
    _ensure(s)
    _permit(s, "12345", "SIREN COURT")        # pas 9 chiffres → écarté (pas de fausse identité)
    assert da.extract_deposants(s, mois=24) == []


@pytest.mark.db
def test_csv_ecrit_avec_colonnes(db_session, tmp_path):
    s = db_session
    _ensure(s)
    _permit(s, "444444444", "CSV TEST")
    rows = da.extract_deposants(s, mois=24)
    p = da.write_csv(rows, tmp_path / "out.csv")
    lines = p.read_text(encoding="utf-8").splitlines()
    assert lines[0] == ";".join(da.COLONNES) and len(lines) == 2
    assert "444444444" in lines[1]
