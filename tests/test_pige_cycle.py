"""RADAR P5 · D2 — cycle de vie automatisé (en_vente_longue, a_reverifier, vendue DVF, retiree_sans_vente).

On sème des biens [RADAR-TEST] datés + des mutations DVF, et on gèle : les bascules par ancienneté, le
rapprochement DVF **Sourcé uniquement** (avec écart de prix), l'absence de rapprochement sur un Estimé,
la qualification retiree_sans_vente (rattachée + 12 mois + zéro vente DVF) et la GARDE (jamais d'un lien
mort). [RADAR-TEST] purgés en fin.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import cycle

pytestmark = pytest.mark.db

INSEE = "97415"


@pytest.fixture
def seed(engine):
    tag = uuid.uuid4().hex[:4].upper()
    ids: dict[str, int] = {}
    idu_src = f"{INSEE}0{tag}0001"[:14].ljust(14, "0")
    idu_est = f"{INSEE}0{tag}0002"[:14].ljust(14, "0")
    idu_ret = f"{INSEE}0{tag}0003"[:14].ljust(14, "0")   # parcelle SANS mutation DVF (jamais vendue)
    with session_scope() as s:
        def bien(statut, niv, idu, prix, pub_jours, conf_jours, retiree_mois=None):
            bid = s.execute(text(
                "INSERT INTO pige_biens (commune,type_bien,est_copro,idu,rattachement_niveau,statut,"
                "date_publication,date_derniere_confirmation,retiree_le) "
                "VALUES ('Saint-Paul','maison',false,:idu,:n,:s, "
                " (now() AT TIME ZONE 'Indian/Reunion')::date - CAST(:pub AS int), now() - make_interval(days => CAST(:conf AS int)), "
                " CASE WHEN CAST(:rm AS int) IS NULL THEN NULL ELSE now() - make_interval(months => CAST(:rm AS int)) END) RETURNING bien_id"),
                {"idu": idu, "n": niv, "s": statut, "pub": pub_jours, "conf": conf_jours, "rm": retiree_mois}).scalar()
            s.execute(text("INSERT INTO pige_annonces (bien_id,portail,url_sortante) VALUES (:b,'leboncoin',:u)"),
                      {"b": bid, "u": f"https://www.leboncoin.fr/rt-{tag}-{bid}"})
            s.execute(text("INSERT INTO pige_faits (bien_id,prix,type_bien,valide_at) VALUES (:b,:p,'maison',now())"),
                      {"b": bid, "p": prix})
            return bid
        ids["longue"] = bien("active", "source", idu_src, 300000, pub_jours=120, conf_jours=1)   # >90j pub
        ids["reverif"] = bien("active", "absent", None, 250000, pub_jours=10, conf_jours=70)      # >60j conf
        ids["vendable"] = bien("active", "source", idu_src, 349000, pub_jours=400, conf_jours=1)  # Sourcé, DVF à venir
        ids["estime"] = bien("active", "estime", idu_est, 200000, pub_jours=400, conf_jours=1)    # Estimé → jamais vendue
        ids["retire"] = bien("retiree", "source", idu_ret, 280000, pub_jours=500, conf_jours=1, retiree_mois=13)
        ids["retire_recent"] = bien("retiree", "source", idu_ret, 280000, pub_jours=100, conf_jours=1, retiree_mois=2)
        # une mutation DVF « Vente » ~12 mois après la publication du bien vendable (Sourcé, idu_src)
        s.execute(text(
            "INSERT INTO dvf_mutations_parcelle (id_mutation,date_mutation,nature_mutation,valeur_fonciere,id_parcelle,code_commune,millesime) "
            "VALUES (:m, (now() AT TIME ZONE 'Indian/Reunion')::date - 40, 'Vente', 330000, :idu, :insee, "
            " extract(year from (now() AT TIME ZONE 'Indian/Reunion')::date - 40)::smallint)"),
            {"m": f"MUT-{tag}", "idu": idu_src, "insee": INSEE})
    yield ids
    with session_scope() as s:
        s.execute(text("DELETE FROM pige_biens WHERE bien_id = ANY(:i)"), {"i": list(ids.values())})
        s.execute(text("DELETE FROM dvf_mutations_parcelle WHERE id_parcelle IN (:a,:b,:c)"), {"a": idu_src, "b": idu_est, "c": idu_ret})
        s.execute(text("DELETE FROM event_log WHERE kind IN ('pige.statut_change','pige.vendue_dvf')"))


def _statut(bid: int) -> str:
    with session_scope() as db:
        return db.execute(text("SELECT statut FROM pige_biens WHERE bien_id=:b"), {"b": bid}).scalar()


def test_bascule_en_vente_longue_et_a_reverifier(seed):
    with session_scope() as db:
        cycle.marquer_en_vente_longue(db)
        cycle.marquer_a_reverifier(db)
    assert _statut(seed["longue"]) == "en_vente_longue"
    assert _statut(seed["reverif"]) == "a_reverifier"


def test_dvf_vendue_source_avec_ecart_prix(seed):
    with session_scope() as db:
        n = cycle.matcher_dvf(db)
    assert n >= 1
    with session_scope() as db:
        row = db.execute(text("SELECT statut, vendue_valeur, vendue_ecart_prix, vendue_delai_j "
                              "FROM pige_biens WHERE bien_id=:b"), {"b": seed["vendable"]}).mappings().first()
    assert row["statut"] == "vendue"
    assert row["vendue_valeur"] == 330000 and row["vendue_ecart_prix"] == 349000 - 330000   # affiché − acté
    assert row["vendue_delai_j"] and row["vendue_delai_j"] > 0
    # événement pige.vendue_dvf émis
    with session_scope() as db:
        assert db.execute(text("SELECT count(*) FROM event_log WHERE kind='pige.vendue_dvf'")).scalar() >= 1


def test_estime_jamais_rapproche_dvf(seed):
    with session_scope() as db:
        cycle.matcher_dvf(db)
    assert _statut(seed["estime"]) == "active"   # Estimé → jamais vendue (un Estimé ne suffit pas)


def test_retiree_sans_vente_qualifie_et_garde(seed):
    with session_scope() as db:
        n = cycle.qualifier_retiree_sans_vente(db)
    assert n >= 1
    assert _statut(seed["retire"]) == "retiree_sans_vente"       # rattachée, 13 mois, aucune vente DVF
    assert _statut(seed["retire_recent"]) == "retiree"          # retirée depuis 2 mois → PAS encore qualifiée
