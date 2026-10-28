"""ANNONCE-2 — entrée LIEN de « Analyser une annonce » : lookup Radar D'ABORD, repli fetch.

Le Radar capture chaque soir les annonces de toute l'île. L'outil doit donc lire d'abord ce que LABUSE
a DÉJÀ relevé : extraire l'identifiant (list_id) du lien, chercher le bien parmi les biens capturés, et
— s'il existe — construire le rapport SANS aucun appel à Leboncoin, avec la VRAIE date de capture Radar.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import api

_ROOT = Path(__file__).resolve().parent.parent

# ──────────────────────────── 1 · extraction de l'identifiant (sans base) ────────────────────────────


def test_list_id_sur_formes_url_courantes():
    """Toutes les formes d'URL courantes rendent le MÊME identifiant ; query (?…) et ancre (#…) ignorés."""
    attendu = 3292226092
    for url in (
        "https://www.leboncoin.fr/ad/ventes_immobilieres/3292226092",
        "https://www.leboncoin.fr/ventes_immobilieres/3292226092.htm",
        "https://www.leboncoin.fr/ventes_immobilieres/3292226092.html",
        "https://www.leboncoin.fr/ad/ventes_immobilieres/3292226092/",
        "https://www.leboncoin.fr/ventes_immobilieres/3292226092.htm?utm_source=x&ref=y",
        "https://www.leboncoin.fr/ad/ventes_immobilieres/3292226092#gallery",
        "https://m.leboncoin.fr/ad/ventes_immobilieres/3292226092?a=1#b",
    ):
        assert api._list_id_from_url(url) == attendu, url


def test_list_id_absent_quand_pas_une_annonce():
    """Page de recherche / lien malformé → None (l'appelant bascule alors sur le fetch one-shot)."""
    for url in (
        "https://www.leboncoin.fr/recherche?category=9&locations=r_26",
        "https://www.leboncoin.fr/ventes_immobilieres/offres/reunion/",
        "pas une url du tout",
    ):
        assert api._list_id_from_url(url) is None, url


# ──────────────────────────── 2 · garde-fous de source (sans base) ────────────────────────────


def test_lookup_radar_tente_avant_le_fetch():
    """Dans l'endpoint, le lookup Radar (`_annonce_depuis_radar`) PRÉCÈDE le fetch réseau
    (`_fetch_page_oneshot`) — sinon un bien déjà relevé déclencherait quand même un appel Leboncoin."""
    src = (_ROOT / "src" / "labuse" / "pige" / "api.py").read_text(encoding="utf-8")
    corps = src.split("def radar_annonce_analyser", 1)[1].split("\n@router", 1)[0]
    assert "_annonce_depuis_radar" in corps and "_fetch_page_oneshot" in corps
    assert corps.index("_annonce_depuis_radar") < corps.index("_fetch_page_oneshot"), (
        "le fetch Leboncoin est tenté avant le lookup Radar — le mandat ANNONCE-2 exige l'inverse")


def test_message_echec_front_est_la_phrase_du_mandat():
    """Bien absent du Radar ET fetch bloqué → le front affiche la phrase EXACTE du mandat (pt 4),
    sans aucun code HTTP. La phrase est portée par le code d'erreur `url_bloquee` (seul cas restant :
    le lookup Radar est tenté d'abord, donc `url_bloquee` ⇒ absent du Radar)."""
    tsx = (_ROOT / "frontend" / "src" / "components" / "outils" / "AnalyserAnnonce.tsx").read_text(encoding="utf-8")
    phrase = ("Cette annonce n’a pas encore été relevée par LABUSE et Leboncoin bloque sa lecture "
              "automatique. Entrez l’adresse du bien pour l’analyser.")
    assert phrase in tsx, "la phrase d'échec imposée par le mandat ANNONCE-2 est absente du front"


# ──────────────────────────── 3 · rapport construit depuis le Radar (base) ────────────────────────────


@pytest.mark.db
def test_rapport_depuis_radar_sans_fetch():
    """Un bien DÉJÀ relevé par le Radar → rapport construit depuis pige_annonces → bien → faits, avec la
    date de CAPTURE (date_derniere_confirmation, fuseau Réunion), sans aucun appel réseau."""
    lid = 999000111222
    with session_scope() as db:
        bid = db.execute(text(
            "INSERT INTO pige_biens (commune, type_bien, statut, lat, lng, "
            " date_premiere_saisie, date_derniere_confirmation) "
            "VALUES ('Saint-Paul','maison','active', -21.03, 55.28, "
            " '2026-10-10 08:00:00+04', '2026-10-15 09:00:00+04') RETURNING bien_id")).scalar()
        db.execute(text(
            "INSERT INTO pige_faits (bien_id, prix, pieces, surface_hab, surface_terrain, prix_m2) "
            "VALUES (:b, 285000, 4, 95, 420, 3000)"), {"b": bid})
        db.execute(text(
            "INSERT INTO pige_annonces (bien_id, portail, url_sortante, list_id) "
            "VALUES (:b, 'leboncoin', :u, :l)"),
            {"b": bid, "u": f"https://www.leboncoin.fr/ad/ventes_immobilieres/{lid}", "l": lid})
        db.commit()
    try:
        with session_scope() as db:
            rap = api._annonce_depuis_radar(
                db, lid, f"https://www.leboncoin.fr/ad/ventes_immobilieres/{lid}")
        assert rap is not None and rap["ok"] is True
        a = rap["annonce"]
        assert a["type"] == "maison" and a["prix"] == 285000 and a["commune"] == "Saint-Paul"
        assert a["surface_hab"] == 95.0 and a["surface_terrain"] == 420.0
        assert a["pieces"] == 4 and a["prix_m2"] == 3000
        # VRAIE date = capture Radar (date_derniere_confirmation), jamais le jour courant.
        assert a["releve_le"] == "2026-10-15"
        assert a["titre"] is None          # le Radar ne conserve pas le contenu d'annonce (faits + lien)
    finally:
        with session_scope() as db:
            db.execute(text("DELETE FROM pige_annonces WHERE list_id = :l"), {"l": lid})
            db.execute(text("DELETE FROM pige_faits WHERE bien_id = :b"), {"b": bid})
            db.execute(text("DELETE FROM pige_biens WHERE bien_id = :b"), {"b": bid})
            db.commit()


@pytest.mark.db
def test_lookup_radar_identifiant_inconnu_rend_none():
    """Identifiant absent du Radar → None (l'endpoint bascule alors sur le fetch one-shot = repli ANNONCE-1)."""
    with session_scope() as db:
        assert api._annonce_depuis_radar(db, 123123123123, "https://www.leboncoin.fr/ad/ventes_immobilieres/123123123123") is None
