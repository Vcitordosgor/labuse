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


# ════════════════════════ RADAR-FIX-3 — cohérence des chiffres du Radar ════════════════════════

@pytest.fixture
def seed_fix3(engine):
    """Une commune (Cilaos) avec : 6 maisons EN VENTE qualifiées, 1 maison RETIRÉE, 1 maison À-QUALIFIER,
    1 appartement (copro). Le « en vente » canonique = 6 (hors retirée, hors à-qualifier, hors copro)."""
    tag = uuid.uuid4().hex[:4].upper()
    ids = []
    with session_scope() as s:
        def bien(typ, statut, prix, sh=90, copro=False, aq=False, jours=10):
            bid = s.execute(text(
                "INSERT INTO pige_biens (commune,type_bien,est_copro,rattachement_niveau,statut,"
                " a_qualifier,date_publication,date_premiere_saisie) "
                "VALUES ('Cilaos',:t,:cp,'absent',:st,:aq,current_date-:j,now()-make_interval(days=>:j)) "
                "RETURNING bien_id"),
                {"t": typ, "cp": copro, "st": statut, "aq": aq, "j": jours}).scalar()
            s.execute(text("INSERT INTO pige_faits (bien_id,prix,type_bien,surface_hab,particulier_pro,valide_at) "
                           "VALUES (:b,:p,:t,:sh,'particulier',now())"), {"b": bid, "p": prix, "t": typ, "sh": sh})
            ids.append(bid)
        for p in (300000, 320000, 340000, 360000, 380000, 400000):
            bien("maison", "active", p)
        bien("maison", "retiree", 500000)     # retirée → hors « en vente »
        bien("maison", "active", 999000, aq=True)   # à-qualifier → hors « en vente »
        bien("appartement", "active", 250000, sh=50, copro=True)   # copro → hors compteur
    yield ids
    with session_scope() as s:
        s.execute(text("DELETE FROM pige_biens WHERE bien_id = ANY(:i)"), {"i": ids})


def test_fix3_un_seul_perimetre_en_vente(seed_fix3):
    """Le compteur liste = les 4 chiffres = le tableau = la porte = le n de la médiane demandée, à Cilaos."""
    from labuse.pige import client
    with session_scope() as db:
        t = marche.tableau(db, commune="Cilaos")
        n_liste = client.lister(db, filtres={"commune": "Cilaos"})["n_total"]
        n_porte = client.compter(db, "Cilaos")
        maison = next(l for l in t["par_type"] if l["type"] == "maison")
    assert n_liste == n_porte == t["biens_en_vente"] == 6          # retirée + à-qualifier + copro exclus
    assert maison["en_vente"] == 6                                  # tableau = même nombre
    assert t["prix_demande_median_eur_m2"]["n"] == 6                # n de la médiane demandée = en vente
    assert maison["ecart_n"] == 6


def test_fix3_ecart_niveau_paliers():
    """La règle du seuil, PURE (indépendante des données) : ≥30 des deux côtés → normal ; 5–29 → indicatif ;
    < 5 d'un côté → insuffisant. Le côté acté DVF compte aussi (≥5 exigé)."""
    assert marche._ecart_niveau(35, 999, 30) == "normal"
    assert marche._ecart_niveau(30, 30, 30) == "normal"
    assert marche._ecart_niveau(6, 120, 30) == "indicatif"      # demande 5–29, acté abondant
    assert marche._ecart_niveau(29, 29, 30) == "indicatif"
    assert marche._ecart_niveau(3, 999, 30) == "insuffisant"    # demande < 5
    assert marche._ecart_niveau(50, 3, 30) == "insuffisant"     # acté < 5


def test_fix3_barre_par_commune_egale_tableau(seed_fix3):
    """La barre « écart par commune » = EXACTEMENT la ligne maison du tableau (même calcul maison↔maison) :
    présente et égale si l'écart est servi, absente si le tableau dit « sous le seuil ». Vrai quelle que
    soit l'abondance DVF de la base de test (cohérence structurelle, plus jamais un bâti mélangé divergent)."""
    with session_scope() as db:
        t = marche.tableau(db, commune="Cilaos")
        maison = next(l for l in t["par_type"] if l["type"] == "maison")
        barre = next((e for e in t["ecart_par_commune"] if e["commune"] == "Cilaos"), None)
    assert t["seuil_ecart_n"] == 30 and t["seuil_indicatif_n"] == 5
    assert maison["en_vente"] == 6 and maison["ecart_n"] == 6
    # 4 chiffres (maisons) = ligne maison du tableau (même palier, même écart).
    assert t["ecart_niveau"] == maison["ecart_niveau"] and t["ecart_demande_acte_pct"] == maison["ecart_pct"]
    if maison["ecart_niveau"] == "insuffisant":
        assert barre is None                                    # « sous le seuil » → pas de barre
    else:
        assert barre is not None
        assert barre["ecart_pct"] == maison["ecart_pct"] and barre["niveau"] == maison["ecart_niveau"]


def test_fix3_sup90_par_date_de_publication(engine):
    """« > 90 j » compté sur la date de première publication (pas le statut en_vente_longue, jamais posé)."""
    from labuse.pige import client
    ids = []
    with session_scope() as s:
        for j in (120, 200):   # deux maisons publiées il y a > 90 j, statut simple 'active'
            bid = s.execute(text(
                "INSERT INTO pige_biens (commune,type_bien,est_copro,rattachement_niveau,statut,date_publication) "
                "VALUES ('Salazie','maison',false,'absent','active',current_date-:j) RETURNING bien_id"),
                {"j": j}).scalar()
            s.execute(text("INSERT INTO pige_faits (bien_id,prix,type_bien,surface_hab,valide_at) "
                           "VALUES (:b,300000,'maison',90,now())"), {"b": bid})
            ids.append(bid)
    try:
        with session_scope() as db:
            assert client.compter(db, "Salazie", sup90=True) == 2
            t = marche.tableau(db, commune="Salazie")
        assert t["biens_sup_90j"] == 2
        assert next(l for l in t["par_type"] if l["type"] == "maison")["sup_90j"] == 2
    finally:
        with session_scope() as s:
            s.execute(text("DELETE FROM pige_biens WHERE bien_id = ANY(:i)"), {"i": ids})
