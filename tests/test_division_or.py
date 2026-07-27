"""O12 — DIVISION EN OR : détecteur conservateur, MASQUÉ jusqu'à validation visuelle Vic (20 cartes).

Faux positif = péché mortel : EXPOSE=False ; seuils conservateurs codés en dur dans _DETECT ;
la métrique d'accès du lot bâti (invalidée) n'est PAS filtrante — champ NULL, revue humaine.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion import division_or as d


def test_expose_false():
    assert d.EXPOSE is False    # masqué tant que Vic n'a pas validé le dossier de revue


def test_seuils_conservateurs_dans_detect():
    q = d._DETECT
    assert "BETWEEN 1000 AND 6000" in q            # parcelle assez grande pour DEUX lots
    assert "BETWEEN 0.08 AND 0.45" in q            # bâti présent mais ne remplit pas
    assert "free_m2 >= 500" in q and "surface_m2 - 400" in q   # les deux lots restent viables
    assert "rad >= 9" in q                          # pas de lanière (largeur ~18 m)
    assert "facade_free >= 12" in q                 # accès voirie indépendant


def test_correctifs_o12_ile_dans_detect():
    """Revue O12-ÎLE (20 cartes Entre-Deux + Bras-Panon) — trois défauts corrigés."""
    q = d._DETECT
    # démembrement ≠ division : le lot ne peut pas emporter plus de la moitié de la parcelle
    assert "free_m2 <= surface_m2 * 0.5" in q
    # division URBAINE : zone dominante du LOT en U/AU ; A et N exclus ; RNU → PAU estimée exigée
    assert "zone = 'U' OR zone LIKE 'AU%'" in q
    assert "zone IS NULL AND ({pau_pred})" in q
    assert "plu_gpu_zone" in q
    # clarté : façade voirie PLAFONNÉE à 30 m (une façade de 465 m = bande linéaire, pas un top candidat)
    assert "LEAST(d.residuel_facade_m, 30)" in d._INSERT


def test_types_de_division_o12_ile_d():
    """O12-ÎLE D — le bâti dans le lot est CLASSÉ (libre / démolition), pas exclu."""
    q = d._DETECT
    # deux variantes : lot nu (tout le bâti retiré) / démolition (seul le PRINCIPAL retiré)
    assert "VALUES ('libre', bat.bgeom), ('demolition', princ.pgeom)" in q
    # le bâtiment principal = plus grande emprise au sol — jamais dans le lot par construction
    assert "ORDER BY id, a DESC" in q
    # garde anti-découpage inversé : bâti à démolir ≤ 1/3 du bâti total (≤ moitié du bâti conservé)
    assert "bati_lot_m2 * 3 <= bat_m2" in q
    # une parcelle qui passe en libre RESTE libre (dédoublonnage, libre prioritaire)
    assert "DISTINCT ON (idu)" in q and "(variante = 'demolition')" in q
    # mono-bâtiment : variante démolition sautée (identique à libre)
    assert "v.variante = 'demolition' AND bat.nb_bat = 1" in q
    # divisions libres prioritaires au tri du dossier de revue
    import inspect
    assert "(type_division = 'demolition'), clarte DESC" in inspect.getsource(d.top_candidates)


def test_metrique_bati_invalidee_pas_filtrante():
    # la métrique façade du lot bâti est NULL (invalidée — finding), jamais un filtre sur un chiffre faux
    assert "NULL::numeric AS bati_facade_m" in d._DETECT
    assert "(facade_parcelle - facade_free) >= 5" not in d._DETECT


@pytest.mark.db
def test_build_commune_vide_et_table_creee(db_session):
    s = db_session
    r = d.build_divisions(s, ["Commune-Inexistante"], commit=False, log=lambda *_: None)
    assert r["total"] == 0 and r["expose"] is False
    # la table masquée existe (DDL passé), vide
    assert s.execute(text("SELECT count(*) FROM division_or_candidates")).scalar() == 0
    assert d.top_candidates(s, limit=5) == []
