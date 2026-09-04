"""RETOURS-11F M1/M2 — LE moteur VEFA est unique : la fiche (marche_service), la couche carte
(`vefa_neuf` / detail_commune) et le tableau Communes (comparateur) servent la MÊME médiane, au MÊME
seuil, sur la MÊME fenêtre. Ce test grave la non-contradiction : il ÉCHOUE si un consommateur se remet
à lire un précalcul divergent (`dvf_prix_sortie_neuf`) ou à utiliser un seuil/fenêtre propre.
"""
from __future__ import annotations

import datetime as dt
import inspect

import pytest
from sqlalchemy import text

from labuse.ingestion import vefa_neuf
from labuse.ingestion.dvf_marche import NEUF_VEFA_FENETRE_ANS, neuf_vefa_commune
from labuse.marche_service import DVF_NEUF_VEFA, marche_dvf, neuf_vefa_seuil

VEFA = "Vente en l'état futur d'achèvement"


def test_fenetre_et_seuil_sont_uniques():
    # M2 — une seule fenêtre : 60 mois = 5 ans, la carte est calée sur le moteur (plus de 36 vs 60).
    assert NEUF_VEFA_FENETRE_ANS == 5
    assert vefa_neuf.FENETRE_MOIS == NEUF_VEFA_FENETRE_ANS * 12 == 60
    # M1 — un seul seuil : la carte ne peut pas hachurer à 10 pendant que la fiche sert dès 8.
    assert vefa_neuf.SEUIL_VEFA_AFFICHAGE == neuf_vefa_seuil()


def test_comparateur_et_carnet_ne_lisent_plus_le_precalcul_divergent():
    # Le tableau Communes et le carnet secteur NE lisent plus `dvf_prix_sortie_neuf` pour le NEUF —
    # sinon la divergence mesurée (Saint-Paul précalc 4 730 vs live 5 003) revient.
    from labuse.api import carnet, comparateur
    comp_src = inspect.getsource(comparateur)
    carnet_src = inspect.getsource(carnet)
    # comparateur : plus aucune LECTURE SQL de dvf_prix_sortie_neuf ; il appelle le moteur live.
    assert "FROM dvf_prix_sortie_neuf" not in comp_src
    assert "neuf_vefa_commune" in comp_src
    # carnet : le NEUF passe par le moteur live commune (le précalcul secteur est plus fin que servable).
    assert "neuf_vefa_commune" in carnet_src
    assert "dvf_prix_sortie_neuf WHERE cle = :s AND niveau = 'secteur'" not in carnet_src


@pytest.mark.db
def test_convergence_fiche_table_carte_a_l_euro_pres(engine):
    """Seed 10 ventes VEFA dans une commune fictive → fiche == carte/detail == moteur, à l'euro près."""
    from labuse.db import session_scope
    insee = "97499"          # commune de test, hors des 24 réelles
    with session_scope() as db:
        db.execute(text("DELETE FROM dvf_mutations_parcelle WHERE code_commune = :i"), {"i": insee})
        base = dt.date.today() - dt.timedelta(days=180)
        # 10 mutations VEFA, bâti renseigné, prix étalés autour de 5000 €/m² → médiane calculable.
        for k in range(10):
            bati = 60.0
            prix_m2 = 4800 + k * 40          # 4800..5160, médiane ~4980
            db.execute(text(
                "INSERT INTO dvf_mutations_parcelle (id, id_mutation, date_mutation, nature_mutation, "
                "valeur_fonciere, code_commune, id_parcelle, type_local, surface_reelle_bati, millesime) VALUES "
                "(:id, :m, :d, :n, :v, :c, :p, 'Appartement', :b, 2026)"),
                {"id": 990000 + k, "m": f"T{insee}{k}", "d": base, "n": VEFA, "v": prix_m2 * bati,
                 "c": insee, "p": f"{insee}000AA{k:04d}", "b": bati})
        db.flush()
        moteur = neuf_vefa_commune(db, insee)
        detail = vefa_neuf.detail_commune(db, insee)
        # la fiche appelle marche_dvf(DVF_NEUF_VEFA), qui n'utilise que idu[:5] (grain commune).
        fiche = marche_dvf(db, f"{insee}000AA0001", profil=DVF_NEUF_VEFA)
        assert moteur["n"] == 10
        assert moteur["mediane_prix_m2_bati"] == detail["mediane_eur_m2"]
        assert moteur["mediane_prix_m2_bati"] == fiche["mediane_prix_m2_bati"]
        db.execute(text("DELETE FROM dvf_mutations_parcelle WHERE code_commune = :i"), {"i": insee})
