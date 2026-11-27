"""ETUDE-AUDIT-FIX-1 — FILET du mandat : un test ROUGE par défaut du rapport de relecture
(25/11/2026, origin/main 86e338924). Chaque test reproduit le défaut sur le terrain cité ;
il passe au VERT une fois le lot correspondant corrigé.

Terrains (IDU en base `labuse`) :
  - L'Étang-Salé AW 99/451/624/625  97404000AW0099/0451/0624/0625   (zone UA)   défauts 1, 10
  - Saint-André  AX 255/256         97409000AX0255/0256             (zone UC)   défauts 4, 10
  - Saint-Denis  DL 247/248         97411000DL0247/0248             (zone Ui)   défauts 5, 10
  - Saint-Leu    AC 261/264         97413000AC0261/0264             (zone UD)   défauts 3,6,8,10

Marqués `reel` (données servies réelles) → HORS du hook pre-push (famille unitaire). Rejoués via
`LABUSE_APP_DATABASE_URL=… make test-reel`. Les défauts 7 (type « Collectif ») et 9 (compteurs à
zéro en lotissement) sont PUREMENT FRONT → couverts par EtudeV6.test.tsx (vitest), pas ici.
"""
from __future__ import annotations

import os
import re

import pytest

pytestmark = pytest.mark.reel

_AW = ["97404000AW0099", "97404000AW0451", "97404000AW0624", "97404000AW0625"]
_AX = ["97409000AX0255", "97409000AX0256"]
_DL = ["97411000DL0247", "97411000DL0248"]
_AC261, _AC264 = "97413000AC0261", "97413000AC0264"


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine

    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent (base applicative non définie)")
    s = sessionmaker(bind=make_engine(url=url), future=True)()
    yield s
    s.close()


def _skip_si_absent(session, idus):
    from sqlalchemy import text
    n = session.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"),
                        {"i": list(idus)}).scalar()
    if n != len(idus):
        pytest.skip(f"parcelles témoins absentes de la base ({idus})")


def _short(verdict: str | None) -> str:
    v = str(verdict or "")
    if v.startswith("Exploitable"):
        return "Exploitable"
    if v.startswith("Impossible"):
        return "Impossible"
    if v:
        return "À compléter"
    return ""


def _verdict_pdf_page1(html: str) -> str:
    """Le verdict de la 1ʳᵉ page du PDF = le 1ᵉʳ badge `<span class="st …">LABEL</span>`
    (ligne « Votre projet » de la synthèse). C'est ce que l'audit compare à l'écran."""
    m = re.search(r'class="st [^"]*">([^<]+)</span>', html)
    return (m.group(1).strip() if m else "")


# --------------------------------------------------------------------------- défaut 1
def test_defaut_01_verdict_identique_ecran_et_pdf(session_reelle):
    """L'écran dit « Exploitable sous hypothèses », le PDF dit « À vérifier » pour la MÊME
    configuration (Étang-Salé, 23 T2 + 6 T3, sous-sol). Attendu : même verdict des deux côtés."""
    from labuse.api.modules import _attach_garde_fiche
    from labuse.exports.etude_faisabilite import rendu_etude
    from labuse.implantation.service import etudier_payload

    s = session_reelle
    _skip_si_absent(s, _AW)
    data = {"idus": _AW, "type_projet": "social", "objectif": "equilibre",
            "stationnement": "sous_sol", "niveaux_sous_sol": 1, "terrain": "libere",
            "programme": {"demande": {"T2": 23, "T3": 6}}, "hypotheses": None}
    payload = etudier_payload(s, data)
    _attach_garde_fiche(s, payload, _AW)
    # réplique l'annotation du worker (lot 1) : un SEUL verdict/réserves, lu par l'écran ET le PDF.
    try:
        from labuse.implantation.service import annoter_verdicts_affiches
        annoter_verdicts_affiches(payload)
    except Exception:  # pré-lot1 : la fonction n'existe pas encore (test rouge)
        pass
    retenu = next(v for v in payload["variantes"] if not v.get("absente"))
    ecran = retenu.get("verdict_affiche") or _short(retenu.get("verdict"))
    pdf = _verdict_pdf_page1(rendu_etude(payload, genere_le="25/11/2026", scenario_ref=None)["html"])
    assert ecran and pdf, (ecran, pdf)
    assert ecran == pdf, f"verdict écran={ecran!r} != PDF={pdf!r} (le verdict change à l'export)"


# --------------------------------------------------------------------------- défaut 2
def test_defaut_02_recherche_partielle_dit_n_sur_150_jamais_maximum():
    """Une recherche interrompue doit s'écrire « recherche partielle · n sur 150 » et ne JAMAIS
    parler de maximum. Source unique testable `libelle_recherche` (lot 2)."""
    from labuse.implantation.service import libelle_recherche

    note = libelle_recherche(etat="partielle", candidats_examines=16,
                             candidats_prevus=150, logements_dessines=12)
    assert note, "libellé vide"
    low = note.lower()
    assert "partiel" in low, note
    assert "16" in note and "150" in note, f"« n sur 150 » absent : {note!r}"
    assert "maximum" not in low, f"une recherche partielle ne parle pas de maximum : {note!r}"


# --------------------------------------------------------------------------- défaut 3
def test_defaut_03_lots_hors_voirie_intersection_nulle(session_reelle):
    """La voirie ne doit plus mordre sur aucun lot : intersection lot/voirie = 0 m² (AC261 et AC264),
    bilan recalculé depuis la géométrie découpée."""
    from labuse.implantation.lotissement import etudier_lotissement

    s = session_reelle
    for idu in (_AC261, _AC264):
        _skip_si_absent(s, [idu])
        r = etudier_lotissement(s, [idu])
        inter = r["bilan_surfacique"].get("lots_voirie_intersection_m2")
        assert inter is not None, f"{idu} : verrou lots_voirie_intersection_m2 absent du bilan"
        assert inter == pytest.approx(0.0, abs=0.05), f"{idu} : la voirie mord sur les lots ({inter} m²)"


# --------------------------------------------------------------------------- défaut 4
def test_defaut_04_pleine_terre_deux_controles(session_reelle):
    """Saint-André UC 13.1 : 40 % d'espaces libres, DONT au moins la moitié perméable → DEUX contrôles
    distincts, pas un seul seuil comparé à toute la perméabilité."""
    from labuse.implantation.service import etudier_payload

    s = session_reelle
    _skip_si_absent(s, _AX)
    data = {"idus": _AX, "type_projet": "social", "objectif": "equilibre",
            "stationnement": "aerien", "terrain": "libere",
            "programme": {"demande": {"T2": 10, "T3": 6}}, "hypotheses": None}
    payload = etudier_payload(s, data)
    noms = [c["nom"] for v in payload["variantes"] if not v.get("absente")
            for c in (v.get("controles") or [])]
    noms_l = [n.lower() for n in noms]
    a_espaces_libres = any("espace" in n and "libre" in n for n in noms_l)
    a_permeable = any("perm" in n for n in noms_l)
    assert a_espaces_libres and a_permeable, (
        f"deux contrôles distincts (espaces libres + part perméable) attendus — trouvés : {noms}")


# --------------------------------------------------------------------------- défaut 5
def test_defaut_05_recul_voie_quatre_metres_par_defaut(session_reelle):
    """Saint-Denis Ui.6 : recul de 4 m ; 3 m SEULEMENT pour une voie < 3,50 m. Largeur inconnue → 4 m."""
    from labuse.implantation import moteur as M
    from labuse.implantation.conventions import charger as charger_conv

    s = session_reelle
    _skip_si_absent(s, _DL)
    _terrain, regles, zone = M._charger(s, _DL, None, charger_conv(), avec_pente=False)
    assert zone and zone.lower().startswith("ui"), zone
    assert regles.recul_voie.valeur == 4.0, (
        f"recul sur voie = {regles.recul_voie.valeur} m (exception voie étroite appliquée à tort ; "
        "largeur inconnue → 4 m attendu)")


# --------------------------------------------------------------------------- défaut 6
def test_defaut_06_tableau_lots_garde_le_numero_du_polygone(session_reelle):
    """Le tableau des lots doit porter le NUMÉRO du polygone du plan (pas des surfaces triées
    réaffectées à d'autres numéros). AC264."""
    from labuse.implantation.lotissement import etudier_lotissement

    s = session_reelle
    _skip_si_absent(s, [_AC264])
    r = etudier_lotissement(s, [_AC264])
    lignes = r["tableau_lots"].get("lots")
    assert lignes, "tableau_lots['lots'] (numéro + surface par lot) absent"
    geo = {f["properties"]["numero"]: f["properties"]["surface_m2"]
           for f in r["geojson"]["features"] if f["properties"].get("kind") == "lot"}
    assert geo, "aucun lot dans le GeoJSON"
    for row in lignes:
        num = row["numero"]
        assert num in geo, f"numéro {num} du tableau absent du plan"
        assert row["surface_m2"] == pytest.approx(geo[num], abs=1.0), (
            f"lot n°{num} : tableau {row['surface_m2']} m² ≠ polygone {geo[num]} m²")


# --------------------------------------------------------------------------- défaut 8
def test_defaut_08_voirie_sous_minimum_plu_pas_de_decoupage(session_reelle):
    """Une chaussée de 3 m (< 3,50 m, Saint-Leu UD 3.2) ne doit produire AUCUN découpage : message
    avec l'article, valeur lue de la règle de la commune (jamais en dur)."""
    from labuse.implantation.lotissement import etudier_lotissement

    s = session_reelle
    _skip_si_absent(s, [_AC261])
    r = etudier_lotissement(s, [_AC261], voirie_largeur_m=3.0)
    assert r["tableau_lots"]["nombre"] == 0, (
        f"3 m de voirie < 3,50 m : aucun lot attendu, obtenu {r['tableau_lots']['nombre']}")
    raison = (r.get("raison") or "")
    assert ("3,50" in raison or "3.5" in raison), f"largeur minimale (3,50 m) absente du message : {raison!r}"
    assert "UD" in raison or "3.2" in raison, f"article (UD 3.2) absent du message : {raison!r}"


# --------------------------------------------------------------------------- défaut 10
def test_defaut_10_lire_article_lien_officiel_bon_millesime_bonne_page(session_reelle):
    """« Lire l'article » doit ouvrir le règlement officiel du bon millésime à la bonne page.
    À L'Étang-Salé, l'article de hauteur (UA 2.5.2) est page 19 du PDF officiel, pas un lien générique."""
    from labuse.implantation.assiette import _regles_plu_resume

    s = session_reelle
    lignes = _regles_plu_resume(s, "97404", "L'Étang-Salé", "UA", {})
    assert lignes, "aucune règle PLU servie pour L'Étang-Salé UA"
    haut = next((l for l in lignes if "faîtage" in l["nom"].lower() or "égout" in l["nom"].lower()), None)
    assert haut is not None, f"règle de hauteur absente : {[l['nom'] for l in lignes]}"
    url = haut.get("source_url") or ""
    assert url, "lien « Lire l'article » absent (Document PLU officiel non disponible en lien direct)"
    assert "reglement" in url.lower() and ".pdf" in url.lower(), (
        f"le lien doit viser le PDF du règlement officiel, pas un portail générique : {url!r}")
    assert "#page=" in url, f"le lien doit pointer la bonne page : {url!r}"


# ---------------------------------------------------- relecture : aucune implantation (pas de repli 1 logt)
def test_relecture_message_aucune_implantation_nomme_la_contrainte_dominante():
    """Source unique `moteur.message_aucune_implantation` : « Aucune implantation trouvée avec ces
    hypothèses », nombre de candidats EXAMINÉS, et la contrainte qui en écarte le plus (la largeur /
    l'allée de 5 m l'emporte sur la hauteur). Fonction pure — aucun accès base."""
    from types import SimpleNamespace

    from labuse.implantation.moteur import message_aucune_implantation

    cand = (
        [SimpleNamespace(faisable=False,
                         motif="dégagement d'allée ≥ 5.0 m au droit des places; aucun module implantable")] * 40
        + [SimpleNamespace(faisable=False, motif="dépasse la hauteur")] * 5
        + [SimpleNamespace(faisable=True, motif="")] * 1)
    msg = message_aucune_implantation(SimpleNamespace(candidats=cand))
    assert msg.startswith("Aucune implantation trouvée avec ces hypothèses"), msg
    assert "46 candidats examinés" in msg, msg
    assert "largeur insuffisante pour le bâtiment et l'allée de 5 m" in msg, msg
    assert "hauteur" not in msg.lower(), f"la hauteur (5 écartés) ne doit pas l'emporter sur la largeur (40) : {msg!r}"


def test_saint_denis_senior_implantation_dessinee_et_exportable(session_reelle):
    """La recherche de plusieurs orientations retrouve une implantation senior non dégénérée."""
    from labuse.exports import etude_faisabilite as ef
    from labuse.implantation.service import etudier_payload

    s = session_reelle
    _skip_si_absent(s, _DL)
    data = {"idus": _DL, "type_projet": "senior", "stationnement": "aerien", "terrain": "libere",
            "programme": {"mode": "saisi", "lignes": [{"type": "T2", "nombre": 22, "surface_m2": 56}]}}
    payload = etudier_payload(s, data)
    assert not payload["aucune_implantation"]
    variante = next(v for v in payload["variantes"] if v["ref"] == "votre_programme")
    assert not variante["absente"]
    assert variante["programme"]["par_type"]["T2"] >= 9
    assert all(c["ok"] for c in variante["checks_geometriques"])
    assert payload["verdict"] == "À compléter"
    rendu = ef.rendu_etude(payload, genere_le="26/11/2026", scenario_ref=None)
    assert rendu["retenu_ref"] == variante["ref"]
    assert "Aucune implantation trouvée" not in rendu["html"]
