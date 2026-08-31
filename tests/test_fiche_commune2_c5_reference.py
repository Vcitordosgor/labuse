"""FICHE-COMMUNE-2 (C5) — l'écart demandé/acté du Radar prend une RÉFÉRENCE LOCALE (médiane secteur
autour de la parcelle rattachée) et ne PORTE le verdict « sous le marché » que sur une référence
fiable. Diagnostic : la référence commune ENTIÈRE (médiane DVF du type sur toute la commune, n=1000+)
produisait de faux « sous le marché » (toutes les maisons −24 à −54 %). Tests PURS sur `_badge` /
`_referentiel` (pas de DB) — ils verrouillent le gating et la préférence du local.
"""
from __future__ import annotations

from labuse.pige import signaux as S


def _bati_ref(locale: bool, repli: bool = False) -> dict:
    return {"eur_m2": 3000.0, "n": 1810, "millesime": "2024",
            "perimetre": "maisons", "meme_type": True, "locale": locale, "repli_commune": repli}


def test_bati_reference_commune_ne_porte_pas_le_verdict():
    """Le cas du diagnostic : maison à 1875 €/m² vs référence COMMUNE 3000 (−37,5 %). L'écart est
    montré, mais AUCUN badge « sous le marché » (référence trop large, non fiable)."""
    b = S._badge(375_000, "maison", 200, 300, _bati_ref(locale=False), terrain_ref_eur_m2=None)
    assert b["calculable"] and b["ecart_pct"] == -37.5
    assert b["reference_locale"] is False
    assert b["sous_le_marche"] is False           # « pas de badge sous le seuil » sur référence commune


def test_bati_reference_locale_porte_le_verdict():
    """Même maison, mais la référence est LOCALE (médiane secteur autour de la parcelle) : l'écart est
    fiable → le badge « sous le marché » peut se porter."""
    b = S._badge(375_000, "maison", 200, 300, _bati_ref(locale=True), terrain_ref_eur_m2=None)
    assert b["calculable"] and b["reference_locale"] is True
    assert b["sous_le_marche"] is True


def test_terrain_garde_sa_reference_de_zone():
    """Le terrain a une référence de ZONE (déjà étroite, pas la commune mixte) : le badge y reste."""
    ref = {"eur_m2": 455.0, "n": 200, "perimetre": "terrain nu", "millesime": "2023"}
    b = S._badge(364_000, "terrain", None, 1000, ref, terrain_ref_eur_m2=None)
    assert b["calculable"] and b["ecart_pct"] == -20.0 and b["sous_le_marche"] is True


def test_referentiel_prefere_le_local_puis_replie_commune(monkeypatch):
    """`_referentiel` demande d'ABORD la médiane locale (si idu) ; à défaut, replie sur la commune en
    marquant `repli_commune` (pour que l'affichage le DISE)."""
    # local disponible → il l'emporte
    monkeypatch.setattr(S, "_ref_local", lambda db, idu, tb: {"eur_m2": 2800.0, "n": 27, "locale": True,
                                                              "perimetre": "maisons · 500 m autour de la parcelle"})
    r = S._referentiel(db=None, commune="Sainte-Marie", type_bien="maison", idu="97418000AW0406")
    assert r["locale"] is True and r["eur_m2"] == 2800.0

    # local indisponible (None) → repli commune, marqué
    monkeypatch.setattr(S, "_ref_local", lambda db, idu, tb: None)
    monkeypatch.setattr(S, "_dvf_bati_type", lambda db, c, tb: {"eur_m2": 3000.0, "n": 1810, "meme_type": True,
                                                               "perimetre": "maisons", "millesime": "2024"})
    r2 = S._referentiel(db=None, commune="Saint-Denis", type_bien="maison", idu="97411000AB0001")
    assert r2["locale"] is False and r2["repli_commune"] is True

    # pas d'idu → jamais de tentative locale, jamais repli marqué (aucune parcelle attendue)
    r3 = S._referentiel(db=None, commune="Saint-Denis", type_bien="maison", idu=None)
    assert r3["locale"] is False and r3["repli_commune"] is False
