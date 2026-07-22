"""O11 — OPÉRATIONS & LOTS : rattachement multi-signal (LOT 0 prouvé), porteur PM uniquement.

vendus = Sourcé (déclin de propriété) ; restant = Estimé (caveat DVF ~6 mois) ; confiance selon
l'alignement des 3 signaux. Table absente → liste vide guardée (jamais un crash).
"""
from __future__ import annotations

from labuse.api import operations as o


def _r(**kw):
    base = dict(siren="123", denomination="PROMOTEUR SA", secteur="97415000DE", insee="97415",
                n_peak=20, n_fin=8, lots_cedes=12, n_pa=1, n_pc=30, annee_min=2015, annee_max=2024,
                dvf_ventes=40, v_min=2018, v_max=2024)
    base.update(kw)
    return base


def test_confiance_trois_signaux_elevee():
    # PA≥1 + DVF≥5 + lots_cedes≥3 → élevée
    assert o._confiance(_r(n_pa=1, dvf_ventes=40, lots_cedes=12)) == "élevée"


def test_confiance_deux_signaux_moyenne():
    assert o._confiance(_r(n_pa=0, dvf_ventes=40, lots_cedes=12)) == "moyenne"


def test_confiance_un_signal_faible():
    assert o._confiance(_r(n_pa=0, dvf_ventes=0, lots_cedes=12)) == "faible"


def test_op_sourcee_estime_et_porteur_pm():
    op = o._op(_r())
    assert op["vendus_sourcee"] == 12 and op["restant_estime"] == 8      # déclin = vendus Sourcé ; restant Estimé
    assert op["porteur"]["siren"] == "123" and "denomination" in op["porteur"]
    assert op["permis"]["pa"] == 1 and op["permis"]["annees"] == "2015–2024"


def test_caveat_dvf_et_confidentialite():
    assert "~6 mois" in o.CAVEAT_DVF and "Estimé" in o.CAVEAT_DVF


def test_detect_table_absente_vide(db_session):
    # base de test sans pm_proprietaires_millesimes → liste vide, jamais un crash
    assert o.detect_operations(db_session, commune_insee=None, limit=10) == []


def test_forme_juridique_taguee_pas_exclue():
    # J6 : entités publiques/parapubliques TAGUÉES (badge), jamais exclues (décision Vic)
    op_pub = o._op(_r(forme_juridique="SEM"))
    op_priv = o._op(_r(forme_juridique="SA"))
    op_inconnu = o._op(_r(forme_juridique=None))
    assert op_pub["porteur"]["entite_publique"] is True and op_pub["porteur"]["forme_juridique"] == "SEM"
    assert op_priv["porteur"]["entite_publique"] is False
    assert op_inconnu["porteur"]["entite_publique"] is None      # inconnu ≠ privé (pas d'invention)
    assert "SEM" in o.FORMES_PUBLIQUES and "COM" in o.FORMES_PUBLIQUES and "ETAT" in o.FORMES_PUBLIQUES
