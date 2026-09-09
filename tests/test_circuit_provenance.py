"""RECETTE-7 lot 0 (Z5) — 🔴 LE VERROU : un chiffre non rattaché au registre ne s'imprime plus.

On génère les documents sur les QUATRE témoins (les mêmes que la sonde EXPORTS-1), on passe
CHAQUE nombre imprimé au crible de `exports.provenance`, et tout nombre non rattaché à une donnée
du registre CIRCUIT — ni à la liste blanche des nombres de structure — FAIT ÉCHOUER la
construction. C'est ce test qui ferme le trou de conception : un producteur non déclaré (un calcul
qui fabrique son chiffre dans son coin et l'imprime) devient visible ici, là où la sonde
« lecteurs déclarés » était aveugle.

Marqué `local` : il lit la fiche `/parcels/{idu}` de la BASE RÉELLE (les témoins portent toutes
leurs couches). Joué par `pytest -m local`, par la sonde de nuit et par la porte de déploiement.
Il ne rend PAS le PDF (WeasyPrint) — la mise en page ne change pas les nombres ; il lit le HTML de
`builder.construire`, donc il tourne partout où la base est là.
"""
from __future__ import annotations

import pytest

from labuse.exports import builder, provenance

pytestmark = pytest.mark.local

TEMOINS = ["97415000BO0852", "97401000AD0554", "97416000DY0106", "97411000AV0110"]
#: les documents TOUJOURS rendus (le Financier exige un questionnaire — testé à part).
DOCS_TOUJOURS = ["dossier", "flash", "apporteur"]

#: compte sentinelle pour le questionnaire synthétique du Financier (nettoyé en fin de test).
_COMPTE_TEST = -7770


@pytest.fixture(autouse=True)
def _base_reelle():
    """La conftest redirige l'app vers `labuse_test` ; ce test `local` a besoin des TÉMOINS
    complets de la base APPLICATIVE réelle (toutes leurs couches). On rebranche l'engine de l'app
    sur `LABUSE_APP_DATABASE_URL` le temps du test, puis on restaure (pas de fuite entre tests)."""
    import os

    from labuse import db as db_mod
    app_url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not app_url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent — base applicative réelle inconnue")
    ancien_eng, ancien_sess = db_mod._engine, db_mod._Session
    db_mod._engine = db_mod.make_engine(app_url)
    db_mod._Session = None
    try:
        yield
    finally:
        db_mod._engine, db_mod._Session = ancien_eng, ancien_sess


def _fiche(idu: str) -> dict:
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    return TestClient(app).get(f"/parcels/{idu}").json()


@pytest.mark.parametrize("idu", TEMOINS)
def test_aucun_nombre_hors_registre_dans_les_documents(idu):
    """dossier · flash · apporteur : chaque nombre imprimé se rattache à une donnée du registre."""
    from labuse.db import session_scope
    fiche = _fiche(idu)
    fuites_tot: list[dict] = []
    for doc in DOCS_TOUJOURS:
        with session_scope() as s:
            res = builder.construire(s, idu, doc, fiche=fiche)
        fuites_tot += provenance.fuites(f"{idu}/{doc}", res.valeurs, res.html, res.contexte)
    assert not fuites_tot, "nombres imprimés SANS donnée du registre :\n" + "\n".join(
        f"  {f['document']} : {f['nombre']:g} — « {f['contexte']} »" for f in fuites_tot)


def test_financier_aucun_nombre_hors_registre():
    """Le Financier (bilan à rebours) sur un témoin, avec un questionnaire synthétique COMPLET
    (prix de sortie 4 500 €/m², régime TVA, 6 logements T3) — le bilan dérivé ne doit imprimer
    aucun nombre hors registre. Le questionnaire de test est nettoyé après (compte sentinelle)."""
    from sqlalchemy import text

    from labuse import financier_questionnaire as qf
    from labuse.db import session_scope
    idu = "97411000AV0110"
    fiche = _fiche(idu)
    reponses = {"prix_sortie_saisi_eur_m2": 4500, "regime_tva_saisi": "assujetti",
                "logements_vises_saisi": 6, "typologie_moyenne_saisi": "T3"}
    try:
        with session_scope() as s:
            qf.enregistrer(s, idu, _COMPTE_TEST, reponses)
        with session_scope() as s:
            try:
                res = builder.construire(s, idu, "financier", fiche=fiche, compte_id=_COMPTE_TEST)
            except builder.DocumentNonEtablissable as e:
                pytest.skip(f"Financier non établissable sur ce témoin ({[m['libelle'] for m in e.manques]}) "
                            "— le programme n'est pas chiffrable ; couvert par la recette Lot C/E11.")
        fu = provenance.fuites(f"{idu}/financier", res.valeurs, res.html, res.contexte)
        assert not fu, "Financier — nombres imprimés SANS donnée du registre :\n" + "\n".join(
            f"  {f['nombre']:g} — « {f['contexte']} »" for f in fu)
    finally:
        with session_scope() as s:
            s.execute(text("DELETE FROM questionnaire_financier WHERE compte_id = :c"),
                      {"c": _COMPTE_TEST})


def test_le_crible_casse_bien_sur_un_nombre_invente():
    """Preuve que le verrou MORD : un HTML avec un nombre qu'aucune donnée ne porte est une fuite
    (sinon le test vert ne prouverait rien)."""
    from labuse.registre.valeur import Valeur
    valeurs = {"surface_parcelle_m2": Valeur(valeur=1018, chiffre_id="surface_parcelle_m2",
                                             version_def="x", run=None)}
    html = "<p>Surface 1 018 m² — charge foncière fabriquée 123 456 € au doigt mouillé</p>"
    fu = provenance.fuites("faux/doc", valeurs, html)
    assert any(f["nombre"] == 123456 for f in fu), fu
    assert all(f["nombre"] != 1018 for f in fu)  # 1 018 est ancré (surface), pas une fuite
