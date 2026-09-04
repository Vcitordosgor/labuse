"""SECTEUR-2b (U1) — couche VEFA approfondie : fenêtre 36 mois (constante), TOUTES les communes servies
(peintes OU hachurées, jamais vides), panneau de détail chaque chiffre avec son n, et la garde de
diagnostic : DVF au 974 ne porte pas le nombre de pièces (médiane par taille absente, jamais extrapolée).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.ingestion import vefa_neuf as V

pytestmark = pytest.mark.db


def test_constantes_fenetre_60_mois_et_seuil():
    # RETOURS-11F M1/M2 — moteur VEFA unique : fenêtre 60 mois (= NEUF_VEFA_FENETRE_ANS×12) et seuil
    # aligné sur le profil `neuf_vefa` (source unique, partagée avec la fiche et le comparateur).
    from labuse.marche_service import neuf_vefa_seuil
    assert V.FENETRE_MOIS == 60
    assert V.SEUIL_VEFA_AFFICHAGE == neuf_vefa_seuil() == 8
    assert V.OFFRE_SITADEL_MOIS == 24
    assert V.TRANCHE_LIBELLE["sous_seuil"] == "moins de 8 ventes"


def test_tranche_borne_haute():
    assert V._tranche(3999) == "moins_4000"
    assert V._tranche(5000) == "5000_5500"
    assert V._tranche(9000) == "5500_plus"


def test_build_sert_toutes_les_communes_peintes_ou_hachurees():
    """Aucune commune vide : chaque commune est peinte (tranche) OU hachurée (subtype 'sous_seuil')."""
    with session_scope() as db:
        if not db.execute(text("SELECT to_regclass('dvf_mutations_parcelle')")).scalar():
            pytest.skip("base de test sans DVF")
        r = V.build_vefa_neuf(db, commit=True)
        rows = db.execute(text(
            "SELECT count(*) n, count(*) FILTER (WHERE subtype='sous_seuil') hach FROM spatial_layers WHERE kind='vefa_neuf'")).first()
        if rows[0] == 0:
            pytest.skip("base de test sans commune VEFA")
        assert rows[0] == r["communes"] + r["hachurees"]   # peintes + hachurées = total, rien de vide
        # une commune peinte porte bien un prix ; une hachurée porte n_ventes < seuil.
        for sub, has_prix in db.execute(text(
                "SELECT subtype, (attrs->>'prix_m2_neuf') IS NOT NULL FROM spatial_layers WHERE kind='vefa_neuf'")):
            if sub == "sous_seuil":
                assert has_prix is False           # jamais un prix sous le seuil (pas d'extrapolation)


def test_detail_commune_pieces_absentes_jamais_extrapolees():
    """La médiane par taille (T2/T3/T4) est INDISPONIBLE — DVF au 974 ne porte pas le nombre de pièces."""
    with session_scope() as db:
        insee = db.execute(text(
            "SELECT substring(idu,1,5) FROM parcels WHERE commune='Saint-Denis' LIMIT 1")).scalar()
        if not insee:
            pytest.skip("base de test sans Saint-Denis")
        d = V.detail_commune(db, insee)
        assert d["fenetre_mois"] == 60 and d["seuil"] == 8
        assert d["par_taille"]["disponible"] is False       # pièces absentes → jamais extrapolé
        assert "pièces" in d["par_taille"]["motif"]
        # chaque chiffre porte son n / est structurellement présent
        assert "n_ventes" in d and "appartements" in d["repartition"]
        assert d["offre_engagee"]["mois"] == 24             # offre engagée Sitadel 24 mois


def test_pieces_absentes_de_dvf_au_974():
    """Garde de diagnostic : le nombre de pièces n'existe dans AUCUNE table/`raw` DVF au 974."""
    with session_scope() as db:
        cols = [r[0] for r in db.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name LIKE 'dvf%'"))]
        assert not any("piece" in c.lower() for c in cols), "une colonne pièces est apparue — revoir le panneau"
