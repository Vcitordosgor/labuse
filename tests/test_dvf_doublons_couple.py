"""CHIRURGICAL-FIX-1 (LOT J, complément dvf) — un calcul de PRIX ne doit jamais compter deux fois le
même couple (mutation, parcelle).

`dvf_mutations_parcelle` republie/duplique la même ligne de vente (jusqu'à 327 copies d'un couple,
mesuré sur la base). Trois lecteurs sommaient sur les lignes BRUTES et étaient faussés :
  · faisabilite/bilan.py `_surface_terrain_sujet` (surface bâtie du sujet → pondération Estimer) ;
  · scoring/p_model/sql.py `p_model_mut_l2.s_bati` (pm2_bati = valeur / bâti, feature de prix) ;
  · faisabilite/marche_commune.py `_median_terrain_commune` (médiane €/m² du terrain nu).

Ce test INJECTE des copies d'un couple existant (dans une transaction annulée — AUCUNE écriture
persistée) et vérifie que le résultat du lecteur ne BOUGE PAS. Avant correction il bougeait ; c'est
le test qui échoue si un calcul de prix recompte le même couple. Marqueur `db` (base réelle).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.db

_COLS = ("id_mutation, date_mutation, nature_mutation, valeur_fonciere, code_commune, id_parcelle, "
         "type_local, surface_reelle_bati, surface_terrain, nature_culture, longitude, latitude, millesime")


def _has(conn) -> bool:
    try:
        return bool(conn.execute(text("SELECT 1 FROM dvf_mutations_parcelle LIMIT 1")).scalar())
    except Exception:
        return False


def _dupe_couple(sess: Session, id_mutation: str, id_parcelle: str, fois: int = 40) -> None:
    """Réinjecte `fois` copies des lignes du couple (id auto-incrémenté), comme la republication DVF.

    UN SEUL `INSERT … SELECT … CROSS JOIN generate_series` : Postgres lit les lignes ORIGINALES une
    fois (il ne voit pas ses propres insertions dans le même ordre), donc multiplication EXACTE par
    `fois`. (Une boucle d'`INSERT … SELECT` relirait l'ensemble qui grossit → croissance EXPONENTIELLE.)"""
    sess.execute(text(
        f"INSERT INTO dvf_mutations_parcelle ({_COLS}) "
        f"SELECT {_COLS} FROM dvf_mutations_parcelle CROSS JOIN generate_series(1, :fois) "
        "WHERE id_mutation = :m AND id_parcelle = :p"),
        {"m": id_mutation, "p": id_parcelle, "fois": fois})


def test_median_terrain_commune_invariante_aux_doublons():
    from labuse.db import engine
    from labuse.faisabilite.marche_commune import _median_terrain_commune
    with engine().connect() as conn:
        if not _has(conn):
            pytest.skip("base sans dvf_mutations_parcelle")
        trans = conn.begin()
        sess = Session(bind=conn)
        try:
            # un couple terrain-nu récent d'une commune active
            row = sess.execute(text(
                "WITH mx AS (SELECT max(date_mutation) d FROM dvf_mutations WHERE lower(commune)=lower(:c)) "
                "SELECT dm.id_mutation, dm.id_parcelle FROM dvf_mutations_parcelle dm "
                "JOIN parcels p ON p.idu = dm.id_parcelle, mx "
                "WHERE lower(p.commune)=lower(:c) AND dm.nature_mutation ILIKE 'vente%' "
                "  AND COALESCE(dm.surface_reelle_bati,0)=0 AND dm.surface_terrain>0 "
                "  AND dm.date_mutation > mx.d - make_interval(months => 12) "
                "LIMIT 1"), {"c": "Le Tampon"}).first()
            if not row:
                pytest.skip("pas de vente terrain nu récente à Le Tampon")
            avant, n_avant = _median_terrain_commune(sess, "Le Tampon")
            _dupe_couple(sess, row.id_mutation, row.id_parcelle, fois=40)
            apres, n_apres = _median_terrain_commune(sess, "Le Tampon")
            assert avant == apres, f"médiane €/m² terrain faussée par les doublons : {avant} → {apres}"
            assert n_avant == n_apres, f"n de ventes gonflé par les doublons : {n_avant} → {n_apres}"
        finally:
            trans.rollback()
            sess.close()


def test_surface_terrain_sujet_invariante_aux_doublons():
    from labuse.db import engine
    from labuse.faisabilite.bilan import _surface_terrain_sujet
    with engine().connect() as conn:
        if not _has(conn):
            pytest.skip("base sans dvf_mutations_parcelle")
        trans = conn.begin()
        sess = Session(bind=conn)
        try:
            # une parcelle bâtie dont la dernière mutation est une vente
            row = sess.execute(text(
                "SELECT p.id AS pid, dm.id_mutation, dm.id_parcelle "
                "FROM dvf_mutations_parcelle dm JOIN parcels p ON p.idu = dm.id_parcelle "
                "WHERE dm.type_local IN ('Maison','Appartement') "
                "  AND dm.nature_mutation IN ('Vente','Vente terrain à bâtir') "
                "  AND dm.surface_reelle_bati > 0 LIMIT 1")).first()
            if not row:
                pytest.skip("pas de parcelle bâtie vendue")
            surf_avant, _ = _surface_terrain_sujet(sess, row.pid)
            _dupe_couple(sess, row.id_mutation, row.id_parcelle, fois=40)
            surf_apres, _ = _surface_terrain_sujet(sess, row.pid)
            assert surf_avant == surf_apres, f"surface bâtie sujet faussée par les doublons : {surf_avant} → {surf_apres}"
        finally:
            trans.rollback()
            sess.close()
