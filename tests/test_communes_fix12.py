"""OUTIL-COMMUNES-FIX-12 — LOT 0 : le FILET. Un test par témoin de la liste « C'est faux » du
rapport ASTRA-9 (`~/Desktop/audit-outils/03-COMMUNES-ASTRA-9.md`). Écrits AVANT correction :
ROUGES maintenant, VERTS une fois les LOTS 1-3 livrés. Chaque point se prouve par ce que l'API
sert réellement (route de faisabilité, registre de veille, radar parcelle).

  1. Cilaos 97424000AC0139 — l'en-tête situe 82 ventes « rayon 1 500 m » alors que le moteur a
     élargi à la COMMUNE entière (commune_fallback=True). La route (`faisabilite_sens1`, marche:1981)
     doit TRANSMETTRE l'indicateur de périmètre pour que l'en-tête affiche « commune entière ».
  2. Les Trois-Bassins 97423 — le débat du PADD du 04/09/2025 est un fait DATÉ (PV, affaire 2.2).
     Le radar parcelle doit le consigner (débat tenu) SANS armer le sursis (debat_padd ABSENT).
  3. Saint-André 97409 — la dernière pièce n'est plus l'avis MRAe du 09/09/2025 : la Région a
     délibéré le 03/10/2025 (DCP2025_0684, avis de consultation PPA), postérieur.

Tests `db`/`reel` : lisent la base SERVIE (route réelle). Hors hook (-m "not db and not reel").
"""
from __future__ import annotations

import pytest


# ─────────────────────────── 1. Cilaos — périmètre transmis ───────────────────────────
@pytest.mark.db
@pytest.mark.reel
def test_cilaos_route_transmet_commune_fallback():
    """97424000AC0139 : la route de faisabilité sert `marche.commune_fallback=True` (82 ventes
    agrégées sur la COMMUNE entière, pas dans les 1 500 m). Avant FIX-12 LOT 1, la clé était
    OMISE du dictionnaire `marche` (whitelist modules.py:1981) → l'en-tête affichait « rayon
    1 500 m » pour un effectif qui n'y est pas."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from labuse.api.modules import faisabilite_sens1

    eng = create_engine("postgresql+psycopg://openclaw@localhost:5432/labuse")
    with Session(eng) as db:
        out = faisabilite_sens1("97424000AC0139", db)
    m = out.get("marche") or {}
    assert m.get("n") == 82, f"effectif attendu 82, obtenu {m.get('n')}"
    assert m.get("radius_m") == 1500, f"radius_m attendu 1500, obtenu {m.get('radius_m')}"
    assert m.get("commune_fallback") is True, (
        "la route doit TRANSMETTRE commune_fallback=True (élargissement commune) — "
        f"obtenu {m.get('commune_fallback')!r} (clé omise = en-tête faux « rayon 1 500 m »)")


# ─────────────────────── 2. Trois-Bassins — débat PADD tenu, sans sursis ───────────────────────
def test_trois_bassins_debat_padd_tenu_sans_sursis():
    """97423 : le radar parcelle consigne « débat PADD tenu le 2025-09-04 » (fait daté) tout en
    laissant le sursis NON armé (debat_padd ABSENT, décision discrétionnaire du maire). Sépare
    « débat tenu » de « sursis applicable »."""
    from labuse import veille_plu

    e = veille_plu.entry("97423") or {}
    assert e.get("debat_padd") in ("ABSENT", None), "sursis NON armé : debat_padd reste ABSENT"
    assert e.get("debat_padd_tenu") == "2025-09-04", (
        f"fait daté « débat PADD tenu le 04/09/2025 » attendu, obtenu {e.get('debat_padd_tenu')!r}")

    radar = veille_plu.radar_parcelle("97423", "chaude") or {}
    assert radar.get("sursis") is None, "le sursis ne doit PAS être armé par un débat PADD seul"
    synth = radar.get("synthese") or {}
    assert synth.get("debat_padd_tenu") == "2025-09-04", (
        f"le radar doit servir la date du débat tenu, obtenu {synth.get('debat_padd_tenu')!r}")


# ─────────────────────── 3. Saint-André — avis Région postérieur ───────────────────────
def test_saint_andre_derniere_piece_region_03_10_2025():
    """97409 : la Région Réunion a délibéré le 03/10/2025 (DCP2025_0684, avis de consultation sur
    la révision générale), postérieur à l'avis MRAe du 09/09/2025. La dernière pièce connue de
    LABUSE n'est plus le 09/09/2025 — distinction consultation ≠ approbation conservée."""
    from labuse import veille_plu

    e = veille_plu.entry("97409") or {}
    assert e.get("etat_source_date") == "2025-10-03", (
        f"dernière pièce = avis Région 03/10/2025, obtenu {e.get('etat_source_date')!r}")
    objet = (e.get("piece_objet") or "").lower()
    assert "région" in objet or "region" in objet, f"piece_objet doit nommer la Région : {objet!r}"
    assert "consultation" in objet or "avis" in objet, (
        f"piece_objet doit dire consultation/avis (pas approbation) : {objet!r}")
    chrono = e.get("chronologie") or []
    dates = [p.get("date") for p in chrono]
    assert "2025-10-03" in dates and "2025-09-09" in dates, (
        f"chronologie doit lister MRAe 09/09 ET Région 03/10, obtenu {dates}")


# ─────────────────────── LOT 4 — libellés plus précis (« ça pourrait être mieux ») ───────────────────────
@pytest.mark.db
@pytest.mark.reel
def test_mixte_seulement_si_vraiment_mixte():
    """« mixte » seulement si le lot retenu contient maisons ET appartements. Saint-Louis CT0691 :
    10 maisons retenues → « maisons (recherche mixte) ». Saint-Paul CD : 8 maisons + 4 appart → mixte."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from labuse import marche_service

    eng = create_engine("postgresql+psycopg://openclaw@localhost:5432/labuse")
    with Session(eng) as db:
        sl = marche_service.marche_dvf(db, "97414000CT0691", profil=marche_service.DVF_BANQUIER_ADAPTATIF)
        cd = marche_service.marche_dvf(db, "97415000CD0003", profil=marche_service.DVF_BANQUIER_ADAPTATIF)
    assert sl["pct_appartement"] == 0 and "maison" in sl["type_prix"] and "mixte (appart+maison)" != sl["type_prix"], (
        f"Saint-Louis CT0691 (10 maisons) ne doit pas être « mixte » : {sl['type_prix']!r}")
    assert cd["pct_appartement"] > 0 and cd["type_prix"] == "mixte (appart+maison)", (
        f"Saint-Paul CD (8 m + 4 a) reste mixte : {cd['type_prix']!r} pct={cd['pct_appartement']}")


@pytest.mark.db
@pytest.mark.reel
def test_la_plaine_dernier_acte_revision_generale():
    """« dernier acte connu de la révision générale » quand la fiche liste des pièces plus récentes
    d'une AUTRE procédure (La Plaine : modif n°3 2023, avancement 2025). Sinon « dernière pièce connue »."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from labuse.api.fiche_commune import plu_statut

    eng = create_engine("postgresql+psycopg://openclaw@localhost:5432/labuse")
    with Session(eng) as db:
        lp = plu_statut(db, "97406", "La Plaine-des-Palmistes")
        sa = plu_statut(db, "97409", "Saint-André")
        tb = plu_statut(db, "97423", "Trois-Bassins")
    assert lp["etat_label"] == "Dernier acte connu de la révision générale", lp["etat_label"]
    assert "dernier acte connu de la révision générale" in lp["source_citation"], lp["source_citation"]
    # pas de pièce postérieure listée → libellé standard
    assert sa["etat_label"] == "Dernière pièce connue de LABUSE", sa["etat_label"]
    assert tb["etat_label"] == "Dernière pièce connue de LABUSE", tb["etat_label"]
