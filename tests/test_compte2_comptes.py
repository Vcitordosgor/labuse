"""COMPTE-2 · Lot 3 — un SEUL compteur de licences actives + masquage des comptes de test.

Fin du « 12 vs 9 » : `comptes.licences_actives` est la source unique (rail, Pilotage, page). Une licence
active = compte 'actif', PAS un essai en cours, PAS un compte interne/de test. Les comptes de recette
(`[CT-TEST]` / `@labuse.test`) et internes sont exclus des chiffres et masquables à l'écran.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import comptes

pytestmark = pytest.mark.db


def test_compte_est_test():
    assert comptes.compte_est_test("[CT-TEST] Client A", "x@labuse.test")
    assert comptes.compte_est_test("Client normal", "vic@labuse.test")     # domaine test
    assert comptes.compte_est_test("[CT-TEST] B", "vic@gmail.com")         # préfixe test
    assert not comptes.compte_est_test("Promoteur SA", "contact@promoteur.re")


def test_licences_actives_compteur_unique(engine):
    with engine.begin() as c:
        base = comptes.licences_actives(c)
        # 1 payante réelle → comptée
        a = c.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES"
                           " ('Promoteur Réel', 'integral', 'actif') RETURNING id")).scalar()
        c.execute(text("INSERT INTO utilisateurs (compte_id, email, statut) VALUES"
                       " (:c, 'reel@promoteur.re', 'actif')"), {"c": a})
        # essai en cours (actif + échéance) → PAS comptée
        c.execute(text("INSERT INTO comptes (nom, plan, statut, essai_expire_at) VALUES"
                       " ('Essai en cours', 'integral', 'actif', now() + interval '2 days')"))
        # compte de test par le NOM → PAS compté
        c.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES"
                       " ('[CT-TEST] Recette', 'integral', 'actif')"))
        # compte de test par le DOMAINE e-mail → PAS compté
        t = c.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES"
                           " ('Client via mail test', 'integral', 'actif') RETURNING id")).scalar()
        c.execute(text("INSERT INTO utilisateurs (compte_id, email, statut) VALUES"
                       " (:c, 'qa@labuse.test', 'actif')"), {"c": t})
        # interne (admin) → PAS compté
        c.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES"
                       " ('LABUSE (admin)', 'interne', 'actif')"))
        # suspendu → PAS compté
        c.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES"
                       " ('Suspendu', 'integral', 'suspendu')"))
        apres = comptes.licences_actives(c)
        c.execute(text("DELETE FROM comptes WHERE nom IN ('Promoteur Réel','Essai en cours',"
                       " '[CT-TEST] Recette','Client via mail test','LABUSE (admin)','Suspendu')"))
    assert apres == base + 1, "seule la licence payante réelle compte (ni essai, ni test, ni interne)"


def test_comptes_actifs_metier_inchange(engine):
    # garde-fou : le compteur MÉTIER « comptes au statut actif » (registre n_comptes_actifs) est intact
    # (il compte tout statut='actif', y compris interne — témoin registre).
    from labuse.registre.moteurs.plateforme import comptes_actifs
    with engine.begin() as c:
        avant = comptes_actifs(c)
        c.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES ('C4 bis', 'interne', 'actif')"))
        apres = comptes_actifs(c)
        c.execute(text("DELETE FROM comptes WHERE nom = 'C4 bis'"))
    assert apres == avant + 1
