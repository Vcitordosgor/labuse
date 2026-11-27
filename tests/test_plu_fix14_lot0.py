"""OUTIL-PLU-FIX-14 — LOT 0 : FILET DES TÉMOINS de l'audit 01-PLU-ASTRA-4 (« C'est faux », 8 points).

PRINCIPE DU TOUR : pour un libellé de zone, l'outil ne sert que des cartes dont le chapitre est RATTACHÉ
à ce libellé (article propre · renvoi exprès cité · zone mère dite comme telle · disposition commune ·
rattachement non établi). Jamais une carte d'un AUTRE chapitre (X), jamais un bandeau qui annonce autre
chose que ce que les cartes contiennent (F). Chaque test affirme une VALEUR lue au PDF officiel.

Appelle la ROUTE réelle `plu_annuaire_search`. Écrits AVANT correction → ROUGES sur le corpus actuel.
Lit le corpus RÉEL servi (base `labuse`) ; SKIP si injoignable/vide (jamais un faux vert).
"""
from __future__ import annotations

import os
import re

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from labuse.api import modules as M
from labuse.ingestion import plu_ingest as P

pytestmark = pytest.mark.reel

_DSN = os.environ.get("LABUSE_PLU_CORPUS_DSN", "postgresql+psycopg://openclaw@localhost:5432/labuse")


@pytest.fixture(scope="module")
def db():
    try:
        s = sessionmaker(bind=create_engine(_DSN))()
        n = s.execute(text("SELECT count(*) FROM plu_reglement_extrait")).scalar()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"corpus PLU injoignable ({_DSN}) : {e}")
    if not n or n < 2000:
        pytest.skip(f"corpus PLU vide/partiel ({n})")
    yield s
    s.close()


def _search(db, q, insee, zone):
    return M.plu_annuaire_search(q=q, insee=insee, zone=zone, limit=25, offset=0, db=db)


def _eff_zone(card: dict) -> str:
    """Zone effective = code lu dans l'en-tête d'article (prime sur l'étiquette générique/bannière)."""
    m = P._ZONE_FROM_ART.match((card.get("article_ref") or "").strip())
    z = P._valid_zone(m.group(1)) if m else None
    return (z or (card.get("zone") or "")).upper()


def _pages(card: dict) -> set:
    return set(card.get("pages_match") or []) | ({card.get("page_match")} if card.get("page_match") else set())


# ───────── Point 1 (bloquant) — règle d'une AUTRE zone sous le filtre (X) ─────────

def test_p1_saint_joseph_U3ar_hauteur_ne_sert_pas_U5(db):
    """U3ar → le chapitre U3 (hauteur p.50). Jamais U5 (p.80), U1, U2 ni U4 — ce sont d'autres zones."""
    r = _search(db, "hauteur", "97412", "U3ar")
    zoned = r["resultats"]
    # U3 10 (hauteur) est p.50 ; U1/U2/U4/U5 10 sont p.21/35/65/80 — aucune de ces pages étrangères.
    servies = set().union(*[_pages(c) for c in zoned]) if zoned else set()
    etr = {80, 21, 35, 65} & servies
    assert not etr, f"U3ar sert la hauteur d'autres zones U (pages {sorted(etr)})"
    assert 50 in servies, "U3ar ne sert pas U3 10 (hauteur, p.50)"


def test_p1_petite_ile_1AU_hauteur_ne_sert_pas_1AUZ(db):
    """1AU ne doit pas servir 1AUZ (zone distincte, p.104). Deux chapitres d'implantation/hauteur séparés."""
    r = _search(db, "hauteur", "97405", "1AU")
    etr = [c for c in r["resultats"] if _eff_zone(c) in ("1AUZ", "1AUZ".upper())]
    assert not etr, f"1AU sert 1AUZ : {[(_eff_zone(c), sorted(_pages(c))) for c in etr]}"


def test_p1_sainte_marie_UC1_pas_de_zone_etrangere(db):
    """UC1 (sous-secteur de UC) ne reçoit pas l'article d'un groupe de secteurs disjoint (UEa/UT…)."""
    r = _search(db, "hauteur", "97418", "UC1")
    for c in r["resultats"]:
        sec = P._secteurs_regis(c)
        # si l'article énumère des secteurs, UC (ou UC1) doit y figurer
        if sec:
            assert any(e == "UC" or e.startswith("UC") for e in sec), \
                f"UC1 reçoit un article de secteurs {sorted(sec)} (UC absente)"


# ───────── Point 2 (bloquant) — bandeau de renvoi FAUX (F) ─────────

def test_p2_le_port_1AUmut_hauteur_18m_et_bandeau_non_umut(db):
    """1AUmut a des dispositions PROPRES (hauteur 18 m, recul 5 m) dans le chapitre 1AU indicée — le
    bandeau ne doit pas annoncer « articles de Umut »."""
    r = _search(db, "hauteur", "97407", "1AUmut")
    note = (r.get("renvoi_note") or "")
    assert "zone Umut" not in note and "de Umut servis" not in note, \
        f"bandeau annonce à tort un renvoi vers Umut : {note!r}"
    assert any("18 mètres" in (c.get("texte_verbatim") or "") for c in r["resultats"]), \
        "1AUmut : hauteur 18 m non servie"


def test_p2_saint_benoit_AUb10_bandeau_coherent(db):
    """AUb10/AUb15 : l'écran sert les articles AU ; le bandeau ne doit pas annoncer « Ub10/Ub15 »."""
    for z in ("AUb10", "AUb15"):
        r = _search(db, "hauteur", "97410", z)
        note = (r.get("renvoi_note") or "")
        assert f"zone U{z[2:]}" not in note and f"de U{z[2:]} servis" not in note, \
            f"{z} : bandeau annonce à tort un renvoi vers U{z[2:]} : {note!r}"


# ───────── Point 3 (bloquant) — règle perdue (A) / chapitre en bloc (C) ─────────

def test_p3_bras_panon_1AUt_stationnement_sert_article_12(db):
    """1AUt « stationnement » doit rendre l'article 12 (pas trois débuts de titre sans la règle)."""
    r = _search(db, "stationnement", "97402", "1AUt")
    zoned = r["resultats"]
    assert zoned, "1AUt : aucun article de stationnement servi"
    assert any(P._art_num(c.get("article_ref")) == 12 or "stationnement" in (c.get("texte_verbatim") or "").lower()
               for c in zoned), "1AUt : l'article 12 (stationnement) n'est pas servi"


def test_p3_saint_louis_1AUc_oap5_implantation_a_la_regle(db):
    """1AUc oap5 « implantation » doit rendre la PHRASE réglementaire, pas seulement des titres."""
    r = _search(db, "implantation", "97414", "1AUc")
    zoned = [c for c in r["resultats"] if not (len("".join((c.get("texte_verbatim") or "").split())) < 60)]
    assert zoned, "1AUc : implantation ne rend que des titres (aucune règle)"


def test_p3_etang_sale_UA_stationnement_isole(db):
    """UA « stationnement » : l'article doit être ISOLÉ (pas un long bloc « ET PAYSAGERES » multi-articles)."""
    r = _search(db, "stationnement", "97404", "UA")
    for c in r["resultats"]:
        span = (c.get("page_fin") or 0) - (c.get("page_debut") or 0)
        assert span < 6, f"UA : chapitre servi en bloc ({span} pages, ref {c.get('article_ref')!r})"


# ───────── Point 4 (bloquant) — filtre U2e laisse passer l'article 6 (X) ─────────

def test_p4_saint_paul_U2e_espaces_sans_article6_p70(db):
    """« espaces » sous U2e ne doit pas rendre l'article 6 (p.70) qui nomme U2a/b/c/d/h — pas U2e."""
    r = _search(db, "espaces", "97415", "U2e")
    mauvais = [c for c in r["resultats"] if P._art_num(c.get("article_ref")) == 6 and 70 in _pages(c)]
    assert not mauvais, f"U2e « espaces » sert l'article 6 p.70 : {[c.get('article_ref') for c in mauvais]}"


# ───────── Point 5 (bloquant) — La Plaine : frontières des dossiers (étiquette correcte) ─────────

def test_p5_la_plaine_UB_modification_etiquettes_coherentes(db):
    """Sous UB « modification », une carte ouvrant la p.150 (couverture février 2019) doit porter
    l'étiquette 2019 — pas « mai 2023 »."""
    r = _search(db, "modification", "97406", "UB")
    for c in r["resultats"] + (r.get("dispositions_communes") or []):
        pd = c.get("page_debut") or 0
        if 150 <= pd <= 176:              # frontière du dossier février 2019 (La Butte) : p.150-176
            dossier = (c.get("dossier") or "")
            assert "2019" in dossier, \
                f"carte p.{pd} étiquetée {dossier!r} (attendu février 2019, p.150-176)"
        # aucun extrait ne doit FRANCHIR une frontière de dossier (p.149/150 ou p.176/177)
        pf = c.get("page_fin") or pd
        for b in (149, 176):
            assert not (pd <= b < pf), \
                f"extrait p.{pd}-{pf} franchit la frontière p.{b}/{b + 1} (ref {c.get('article_ref')!r})"
