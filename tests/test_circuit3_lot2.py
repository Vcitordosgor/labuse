"""CIRCUIT-3 lot 2 — LES FILTRES PAR SOURCE : contrôles propres, seuils mesurés.

On teste la LOGIQUE des contrôles propres sur des tables témoins (la base de test est partielle) :
le gardien des comparables DVF, l'aberrance brute, l'étiquette Immeuble, l'aléa non rétrogradé
(RETOURS-13), la clé de Luhn SIREN, le domaine des lettres de zone. Plus la STRUCTURE du registre
(les sources qui pèsent ont des contrôles propres et leur portée).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import filtres
from labuse.filtres import cadre, controles
from labuse.filtres.cadre import Filtre

pytestmark = pytest.mark.db


def test_sources_qui_pesent_ont_des_propres_et_une_portee():
    """Les sources d'impact du lot 2 sont des filtres RICHES (contrôles propres déclarés)."""
    attendus = ["dvf", "gpu_plu", "cadastre_etalab", "sitadel", "dgfip_parcelles_pm", "dpe",
                "georisques_mvt", "sirene_etablissements", "bodacc", "ban", "cosia", "filosofi"]
    reg = filtres.FILTRES()
    for cle in attendus:
        assert cle in reg, f"source du lot 2 absente du registre : {cle}"
    # au moins DVF, Sitadel, MAJIC, Géorisques portent des contrôles propres
    for cle in ("dvf", "sitadel", "dgfip_parcelles_pm", "georisques_mvt"):
        assert reg[cle].propres, f"{cle} n'a aucun contrôle propre"
    # DVF et cadastre sont à portée run (garde pompe)
    assert reg["dvf"].portee_run and reg["cadastre_etalab"].portee_run


def test_dvf_comparable_plage_bloquant_vs_aberrant_brut(db_session):
    """Le gardien des comparables (bloquant) reste vert même quand le BRUT porte des aberrations :
    une Maison à 300 000 €/m² est un artefact, écartée des comparables (borne 12 000), donc jamais
    servie — mais VISIBLE via l'avertissant brut."""
    db_session.execute(text("DROP TABLE IF EXISTS _c3_dvf"))
    db_session.execute(text(
        "CREATE TABLE _c3_dvf (mutation_id varchar, type_local varchar, "
        "valeur_fonciere double precision, surface_reelle_bati double precision)"))
    db_session.execute(text("""
        INSERT INTO _c3_dvf VALUES
        ('m1','Maison', 300000, 1),      -- 300 000 €/m² : artefact BRUT (hors comparables)
        ('m2','Appartement', 250000, 50) -- 5 000 €/m² : comparable sain
    """))
    db_session.commit()
    f = Filtre(source="_c3_dvf", libelle="dvf", table="_c3_dvf", propres=[
        p for p in filtres.get_filtre("dvf").propres
    ])
    # on ne peut pas réutiliser les propres tels quels (ils visent dvf_mutations) → on rejoue les
    # DEUX contrôles à la main via des factories équivalentes sur la table témoin.
    comparable = controles.compte_mauvais(
        "d_comparable_plage", "plage", "bloquant", "cmp", "0",
        "type_local IN ('Maison','Appartement') AND surface_reelle_bati > 0 "
        "AND (valeur_fonciere/surface_reelle_bati) BETWEEN 1000 AND 12000 "
        "AND ((valeur_fonciere/surface_reelle_bati) > 90000)")
    aberrant = controles.compte_mauvais(
        "d_prix_m2_aberrant_brut", "plage", "avertissant", "abr", "0",
        "type_local IN ('Maison','Appartement') AND surface_reelle_bati > 0 "
        "AND (valeur_fonciere/surface_reelle_bati) > 90000")
    f2 = Filtre(source="_c3_dvf", libelle="dvf", table="_c3_dvf", propres=[comparable, aberrant])
    v = cadre.jouer(db_session, f2, version="t1")
    db_session.commit()
    par = {r["controle"]: r for r in v.resultats}
    assert par["d_comparable_plage"]["verdict"] == "ok"      # artefact hors comparables
    assert par["d_prix_m2_aberrant_brut"]["verdict"] == "ko"  # mais visible dans le brut
    assert v.verdict == "avertissements"                      # PAS quarantaine
    db_session.execute(text("DROP TABLE IF EXISTS _c3_dvf"))
    db_session.commit()


def test_georisques_alea_non_retrograde_bloquant(db_session):
    """LE contrôle bloquant qui attrape RETOURS-13 : une zone degré ELEVE servie niveau 'moyen'."""
    db_session.execute(text("DROP TABLE IF EXISTS _c3_alea"))
    db_session.execute(text("CREATE TABLE _c3_alea (id serial, attrs jsonb)"))
    db_session.execute(text("""
        INSERT INTO _c3_alea (attrs) VALUES
        ('{"degre":"TRES_ELEVE","niveau":"moyen"}'::jsonb),
        ('{"degre":"ELEVE","niveau":"fort"}'::jsonb)
    """))
    db_session.commit()
    ctrl = controles.compte_mauvais(
        "d_alea_non_retrograde", "distribution", "bloquant", "alea", "0",
        "upper(coalesce(attrs->>'degre','')) IN ('ELEVE','TRES_ELEVE') "
        "AND lower(coalesce(attrs->>'niveau','')) = 'moyen'")
    f = Filtre(source="_c3_alea", libelle="alea", table="_c3_alea", propres=[ctrl])
    v = cadre.jouer(db_session, f, version="t1")
    db_session.commit()
    par = {r["controle"]: r for r in v.resultats}
    assert par["d_alea_non_retrograde"]["verdict"] == "ko"
    assert par["d_alea_non_retrograde"]["valeur"] == "1"      # la TRES_ELEVE servie moyen
    assert v.verdict == "quarantaine"                          # bloquant
    db_session.execute(text("DROP TABLE IF EXISTS _c3_alea"))
    db_session.commit()


def test_siren_luhn(db_session):
    db_session.execute(text("DROP TABLE IF EXISTS _c3_siren"))
    db_session.execute(text("CREATE TABLE _c3_siren (siren varchar)"))
    # 552081317 (Danone) = Luhn valide ; 123456789 = Luhn invalide ; 'ABC' = hors format (ignoré)
    db_session.execute(text(
        "INSERT INTO _c3_siren VALUES ('552081317'),('123456789'),('ABC')"))
    db_session.commit()
    ctrl = controles.siren_luhn("d_siren_luhn", "siren", "avertissant", "luhn", "0 invalide")
    f = Filtre(source="_c3_siren", libelle="s", table="_c3_siren", propres=[ctrl])
    v = cadre.jouer(db_session, f, version="t1")
    db_session.commit()
    par = {r["controle"]: r for r in v.resultats}
    assert par["d_siren_luhn"]["verdict"] == "ko"
    assert par["d_siren_luhn"]["details"]["luhn_invalides"] == 1  # 123456789
    assert "123456789" in par["d_siren_luhn"]["details"]["exemples"]
    db_session.execute(text("DROP TABLE IF EXISTS _c3_siren"))
    db_session.commit()


def test_zone_famille_registre(db_session):
    """Le domaine des lettres de zone via la fonction canonique est_famille (U/AU/A/N) — NA/NB
    (legacy POS) classent, un radical 'ZZ' sort."""
    from labuse.filtres.sources import _zone_famille_registre
    db_session.execute(text("DROP TABLE IF EXISTS _c3_zone"))
    db_session.execute(text("CREATE TABLE _c3_zone (id serial, attrs jsonb)"))
    db_session.execute(text("""
        INSERT INTO _c3_zone (attrs) VALUES
        ('{"libelle":"AUc"}'::jsonb), ('{"libelle":"NA"}'::jsonb),
        ('{"libelle":"Uc"}'::jsonb), ('{"libelle":"ZZ"}'::jsonb)
    """))
    db_session.commit()
    f = Filtre(source="_c3_zone", libelle="z", table="_c3_zone", propres=[_zone_famille_registre()])
    v = cadre.jouer(db_session, f, version="t1")
    db_session.commit()
    r = {x["controle"]: x for x in v.resultats}["d_zone_famille"]
    assert r["verdict"] == "ko"
    assert r["details"]["hors_domaine"] == ["ZZ"]  # AUc/NA/Uc classent, ZZ non
    db_session.execute(text("DROP TABLE IF EXISTS _c3_zone"))
    db_session.commit()
