"""OUTIL-ASSEMBLAGE-FIX-7 — le PDF comparatif porte la mixité que le moteur connaît.

Pourquoi le filet FIX-6 était vert alors que le document rendu portait un tiret : AUCUN test de FIX-6
ne rendait le PDF comparatif de bout en bout. Le seul test « comparatif » (test_assemblage_fix3.py
`test_lot1_comparatif_affiche_borne_haute`) appelle `_mixite_txt(r)` avec un `r` FABRIQUÉ À LA MAIN qui
contient déjà `r["mixite"]` — il court-circuite exactement la chaîne où vit le bug (`compare()` →
`fiche_payload()` → `r`). Or `fiche_payload` ne sérialisait PAS la clé `mixite` dans son dict `bilan`,
donc `compare()` posait `mixite=None` et la ligne « Mixité sociale » du comparatif valait « — » pour
toute parcelle.

Ce filet rend le PDF comparatif par la VRAIE chaîne (`fiche_payload` → `_compare_row` →
`construire_comparatif` → `render_pdf`) et relit le texte du PDF réellement produit. Il est ROUGE avant
le correctif (clé `mixite` absente de `fiche_payload`), VERT après.
"""
from __future__ import annotations

import os
import subprocess
import tempfile

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# conftest redirige LABUSE_DATABASE_URL vers la base de TEST (vide) ; les données SERVIES (île
# complète) sont dans LABUSE_APP_DATABASE_URL — c'est elle qu'on lit, en lecture seule.
DBURL = (os.environ.get("LABUSE_APP_DATABASE_URL")
         or os.environ.get("LABUSE_DATABASE_URL")
         or "postgresql+psycopg://openclaw@localhost:5432/labuse")
_ENGINE = create_engine(DBURL, future=True)


@pytest.fixture()
def db():
    s = Session(_ENGINE)
    s.execute(text("SET default_transaction_read_only = on"))
    yield s
    s.rollback()
    s.close()


def _pdftotext(octets: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(octets); path = f.name
    try:
        return subprocess.run(["pdftotext", "-layout", path, "-"],
                              capture_output=True, text=True).stdout
    finally:
        os.unlink(path)


def _comparatif_pdf_text(db, idus: list[str]) -> str:
    """Rend le PDF comparatif par la MÊME chaîne que la route `/comparatif.pdf`, en lecture seule.

    On construit chaque ligne comme `compare()` : `_compare_row(fiche_servie, fiche_payload)`. La
    mixité servie ne dépend QUE du 2ᵉ argument (`fiche_payload`, celui qui porte le bug) ; le 1ᵉʳ
    (fiche q_v2 servie) ne nourrit que les cellules de classement/capacité, qu'on laisse minimales
    pour rester indépendant du run servi (et donc de la base de test vide)."""
    from labuse.api.app import _compare_row
    from labuse.exports import builder
    from labuse.exports.rendu import render_pdf
    from labuse.faisabilite.db import fiche_payload
    rows = []
    for idu in idus:
        db.rollback()
        pid = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
        assert pid is not None, f"parcelle {idu} absente de la base servie"
        rows.append(_compare_row({"idu": idu}, fiche_payload(db, pid)))
    res = builder.construire_comparatif(idus, rows)
    return _pdftotext(render_pdf(res.html))


# AB0006 (Saint-Denis Uavap, scénario servi ~39 logts → clause déclenchée 15 %),
# BZ0824 (Saint-Denis Uh, scénario servi sous le seuil → non déclenchée mais article/page cités),
# CP1639 (Saint-Paul AU3st — OUTIL-ASSEMBLAGE-FIX-9 : zone à urbaniser FERMÉE, plus d'exemption ZAC).
@pytest.mark.reel
def test_comparatif_pdf_porte_la_mixite_du_moteur(db):
    txt = _comparatif_pdf_text(db, ["97411000AB0006", "97411000BZ0824", "97415000CP1639"])

    # AB0006 : l'obligation déclenchée (15 %) + l'article/la page de SA zone (Uavap.2, p. 27).
    assert "Uavap.2" in txt, "le comparatif perd l'article de mixité de AB0006 (Uavap.2)"
    assert "15 %" in txt, "le comparatif perd le taux de mixité de AB0006 (15 %)"

    # BZ0824 : même si la clause n'est pas déclenchée au scénario servi, le comparatif cite
    # l'obligation de la zone (Uh.2) — jamais un tiret muet.
    assert "Uh.2" in txt, "le comparatif perd l'article de mixité de BZ0824 (Uh.2)"

    # CP1639 : OUTIL-ASSEMBLAGE-FIX-9 — l'exemption automatique « ZAC Savane des Tamarins » est RETIRÉE
    # (aucun périmètre officiel prouvé ; AU3st est une zone à urbaniser FERMÉE). La cellule de mixité ne
    # porte donc PLUS « Savane ». (Le verdict « zone à urbaniser fermée » complet est rendu par la route
    # /comparatif.pdf avec la ligne de constructibilité servie — prouvé hors de ce test à lignes minimales.)
    assert "Savane" not in txt, "l'exemption ZAC retirée ne doit plus apparaître pour CP1639 (AU3st)"


@pytest.mark.reel
def test_comparatif_pdf_ne_laisse_plus_la_ligne_mixite_vide(db):
    """La ligne « Mixité sociale » ne doit plus être un simple « — » quand le moteur connaît une
    obligation présentable (charge foncière servie). AB0006 (Saint-Denis) porte l'obligation 15 %."""
    txt = _comparatif_pdf_text(db, ["97411000AB0006", "97415000CP1639"])
    # AB0006 : obligation portée à côté de la charge (régime de zone, 15 %).
    assert ("Obligation" in txt and "15 %" in txt), \
        "la ligne Mixité sociale du comparatif reste vide (— ) malgré une obligation connue du moteur"
