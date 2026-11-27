"""OUTIL-COMMUNES-FIX-13 — LOT 0 : le FILET. Un test par témoin de la liste « C'est faux » du
rapport ASTRA-10 (`~/Desktop/audit-outils/03-COMMUNES-ASTRA-10.md`). Écrits AVANT correction :
ROUGES maintenant, VERTS une fois les LOTS 1-5 livrés. Chaque point se prouve par ce que l'API
sert réellement (registre de veille, radar parcelle, statut PLU de la fiche commune).

Pièces OUVERTES et vérifiées (date + auteur + objet recopiés dans le rapport) :
  · Recueil Région du 03/10/2025 (wp-content/uploads/2026/07) p.180/182 : DCP2025_0684 =
    « AVIS DE LA RÉGION RÉUNION SUR LE PROJET DE RÉVISION GÉNÉRALE DU PLU DE SAINT-ANDRÉ »,
    favorable sous réserves, publié 10/10/2025. (0683 = Appui AGORAH au SAR ; 0685 = ADIL.)
  · Arrêt du projet DCM250702_003 (p.2) : « Vu la délibération du conseil Municipal en date du
    19 avril 2023 (DCM230419/002) prenant acte du débat … sur les orientations générales du PADD » ;
    projet arrêté (reprise de l'arrêt du 18/12/2024) le 02/07/2025.
  · Saint-Louis PV 29/10/2024 p.65 : « prendre acte de la tenue ce jour … du débat … PADD ».
  · Saint-Leu délib 24/09/2024 : objet « DÉBAT SUR LES ORIENTATIONS GÉNÉRALES DU PADD ».
  · La Plaine délib 18/10/2019 p.2 : « le PADD … a été débattu en conseil municipal … 1er mars 2018 ».
  · Saint-Leu commission d'enquête p.6 : commission DÉFAVORABLE le 18/11/2026 ; État FAVORABLE
    (4 réserves) ; Région DÉFAVORABLE. Recueil Région 27/02/2026 p.231 : DCP2026_0080, défavorable.

Tests `db`/`reel` : lisent la base SERVIE. Hors hook (-m "not db and not reel").
"""
from __future__ import annotations

import pytest


def _served_text(e: dict) -> str:
    """Tout le texte SERVI d'une entrée registre (source + piece_objet + objets de chronologie)."""
    parts = [str(e.get("source") or ""), str(e.get("piece_objet") or "")]
    for p in (e.get("chronologie") or []):
        parts.append(str(p.get("objet") or ""))
    return " ".join(parts)


# ─────────── 1. Saint-André — bonne délibération, recueil ouvrable, pas « inaccessible » ───────────
def test_saint_andre_ref_0684_recueil_ouvrable():
    """97409 : la fiche cite DCP2025_0684 (la VRAIE délibération de l'avis Région), PAS 0685 (ADIL).
    La ligne du 03/10/2025 porte un lien qui ouvre le recueil officiel. Plus de « recueil
    inaccessible »."""
    from labuse import veille_plu

    e = veille_plu.entry("97409") or {}
    txt = _served_text(e)
    assert "DCP2025_0685" not in txt, f"0685 = participation ADIL, PAS l'avis PLU : {txt[:200]!r}"
    assert "DCP2025_0684" in txt, "la bonne délibération de l'avis Région est DCP2025_0684"
    assert "inaccessible" not in txt.lower(), "le recueil est ouvrable (nouvelle URL) : retirer « inaccessible »"
    # la ligne 03/10/2025 a un lien qui ouvre le recueil
    ligne = next((p for p in (e.get("chronologie") or []) if p.get("date") == "2025-10-03"), None)
    assert ligne is not None, "chronologie doit porter la ligne du 03/10/2025"
    url = str(ligne.get("source_url") or "")
    assert url and "recueil" in url.lower() and ".pdf" in url.lower(), (
        f"la ligne 03/10/2025 doit ouvrir le recueil Région (PDF), obtenu {url!r}")


# ─────────── 2. Radar — débats du PADD plus présentés comme « non constatés » ───────────
def test_saint_andre_saint_louis_debat_padd_constate():
    """97409000AD0001 (Saint-André) et 97414000CT0691 (Saint-Louis) : le radar consigne le débat
    PADD TENU (fait daté) et ne dit plus « débat PADD non constaté »."""
    from labuse import veille_plu

    # FIX-14 LOT 5/6 — la date affichée est désormais au format FR (JJ/MM/AAAA), cohérent avec les
    # autres écrans (fmtDateNum). Saint-Louis porte en plus l'autorisation de surseoir (phrase enrichie),
    # mais « Débat PADD tenu le … » reste le préfixe servi.
    for insee, iso, fr in (("97409", "2023-04-19", "19/04/2023"), ("97414", "2024-10-29", "29/10/2024")):
        e = veille_plu.entry(insee) or {}
        assert e.get("debat_padd_tenu") == iso, (
            f"{insee} : débat PADD tenu attendu {iso}, obtenu {e.get('debat_padd_tenu')!r}")
        syn = veille_plu.synthese_commune(insee) or {}
        pe = (syn.get("prochaine_etape") or "")
        assert "PADD non constaté" not in pe, (
            f"{insee} : le radar ne doit plus dire « débat PADD non constaté » : {pe!r}")
        assert ("Débat PADD tenu le " + fr) in pe, (
            f"{insee} : le radar doit dire le débat tenu le {fr} : {pe!r}")


# ─────────── 3. Saint-André — stade « arrêté », plus « prescrite » ───────────
def test_saint_andre_stade_arrete():
    """97409 : le projet a été ARRÊTÉ le 02/07/2025 (reprise de l'arrêt du 18/12/2024). Le stade
    affiché ne doit plus être « prescrite »."""
    from labuse import veille_plu

    e = veille_plu.entry("97409") or {}
    assert e.get("stade") != "prescrite", "Saint-André : projet arrêté, le stade n'est plus « prescrite »"
    syn = veille_plu.synthese_commune("97409") or {}
    assert "prescrite" not in (syn.get("etat") or "").replace("prescrite le", ""), (
        f"l'état servi ne doit plus présenter le stade « prescrite » : {syn.get('etat')!r}")
    assert "arrêté" in (syn.get("etat") or "").lower() or "arret" in (syn.get("etat") or "").lower(), (
        f"l'état doit dire « arrêté » : {syn.get('etat')!r}")


# ─────────── Les quatre autres débats PADD des communes en révision ───────────
def test_debats_padd_des_communes_en_revision():
    """Les communes dont le débat PADD a été OUVERT et prouvé portent `debat_padd_tenu` ; les trois
    autres (Étang-Salé révision allégée, Saint-Denis, Saint-Paul) restent « non trouvé » (ABSENT)."""
    from labuse import veille_plu

    tenus = {"97409": "2023-04-19", "97414": "2024-10-29", "97413": "2024-09-24",
             "97406": "2018-03-01", "97423": "2025-09-04"}
    for insee, d in tenus.items():
        assert (veille_plu.entry(insee) or {}).get("debat_padd_tenu") == d, (
            f"{insee} : débat PADD tenu attendu {d}")
    for insee in ("97404", "97411", "97415"):
        assert (veille_plu.entry(insee) or {}).get("debat_padd_tenu") in ("ABSENT", None), (
            f"{insee} : aucun débat PADD trouvé dans une pièce ouvrable → ABSENT (non trouvé)")
    # le sursis reste un champ DISTINCT, non armé, sur toutes
    for insee in list(tenus) + ["97404", "97411", "97415"]:
        assert (veille_plu.entry(insee) or {}).get("debat_padd") in ("ABSENT", None), (
            f"{insee} : debat_padd (qui arme le sursis) reste ABSENT")


# ─────────── DB/reel : le stade « arrêté » traverse jusqu'à la carte commune ───────────
@pytest.mark.db
@pytest.mark.reel
def test_carte_commune_lit_le_meme_champ_debat_padd():
    """Carte commune (plu_statut) : la chronologie / l'état reflètent le même registre que le radar
    parcelle — pour Saint-André, le débat PADD du 19/04/2023 est consigné et le stade n'est plus
    « prescrite »."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from labuse.api.fiche_commune import plu_statut

    eng = create_engine("postgresql+psycopg://openclaw@localhost:5432/labuse")
    with Session(eng) as db:
        sa = plu_statut(db, "97409", "Saint-André")
    assert sa.get("procedure") and "prescrite" not in (sa.get("procedure") or ""), sa.get("procedure")


# ─────────── LOT 5 — auteur de chaque avis à côté de son sens (Saint-Leu) ───────────
def test_saint_leu_auteur_de_chaque_avis():
    """97413 : les trois avis sont servis avec leur AUTEUR collé à leur SENS (Région défavorable,
    État favorable sous réserves, commission d'enquête défavorable le 18/11/2026)."""
    from labuse import veille_plu

    e = veille_plu.entry("97413") or {}
    chrono = e.get("chronologie") or []
    objets = " || ".join(str(p.get("objet") or "") for p in chrono).lower()
    assert "région" in objets and "défavorable" in objets, f"Région défavorable attendu : {objets!r}"
    assert "état" in objets and "favorable" in objets, f"État favorable sous réserves attendu : {objets!r}"
    assert "commission" in objets and "18/11/2026" in objets, (
        f"commission d'enquête défavorable le 18/11/2026 attendu : {objets!r}")
