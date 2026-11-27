"""OUTIL-COMMUNES-FIX-14 — LOT 0 : le FILET. Un test par témoin de la liste « C'est faux » /
« mieux » du rapport Astra n°11. Chaque test est ROUGE sur la base avant le correctif de son lot ;
il prouve que ce que le CLIENT VOIT (écran / PDF) est corrigé, pas seulement la plomberie.

Périmètre : LOT 1 (la parcelle survit au clic « Vérif procédure »), LOT 2 (le Dossier PDF restitue
le débat PADD), LOT 4 (bloc Urbanisme en panne → « indisponible », jamais badge vert « document
local »), LOT 5 (Saint-Leu plus « ENQUÊTE PUBLIQUE » ; Saint-Louis — autorisation de surseoir citée),
LOT 6 (la source affichée au client n'est plus un nom de tour « FIX-13 » ; recherche infructueuse datée).
"""
import pytest

from labuse import veille_plu


# ─────────── LOT 5 — Saint-Leu : plus de bandeau « ENQUÊTE PUBLIQUE » ───────────
def test_saint_leu_plus_enquete_publique():
    """L'enquête est TERMINÉE (09/10/2026) et la commission a rendu son avis (18/11/2026) : l'état
    servi (fiche parcelle ET vérificateur lisent le MÊME `synthese_commune().etat`) ne doit plus
    titrer « ENQUÊTE PUBLIQUE » (stade dépassé), mais dire le stade RÉEL, factuel, sans préjuger."""
    etat = (veille_plu.synthese_commune("97413") or {}).get("etat") or ""
    assert "ENQUÊTE PUBLIQUE" not in etat, f"Saint-Leu titre encore l'enquête en cours : {etat!r}"
    assert "publique" not in etat.lower(), f"« enquête publique » (stade dépassé) subsiste : {etat!r}"
    assert "terminée" in etat.lower() or "clôtur" in etat.lower(), f"l'état doit dire l'enquête finie : {etat!r}"
    assert "commission" in etat.lower(), f"l'avis de la commission doit figurer : {etat!r}"


# ─────────── LOT 5 — Saint-Louis : autorisation de surseoir (délib. 29/10/2024 art. 2) ───────────
def test_saint_louis_sursis_autorise_cite():
    """Le PV du 29/10/2024 (p.65) porte DEUX décisions : art. 1 = débat PADD, art. 2 = autorisation
    donnée à la maire de surseoir à statuer (L.424-1). Ce fait doit être SERVABLE à côté de « aucune
    décision de sursis connue pour cette parcelle » — les deux s'affichent ensemble."""
    e = veille_plu.entry("97414") or {}
    sa = veille_plu.sursis_autorise(e)
    assert sa, "Saint-Louis : l'autorisation de surseoir (art. 2) doit être servable"
    assert sa.get("date") == "2024-10-29", f"date de la délibération attendue 2024-10-29 : {sa!r}"
    assert "2" in str(sa.get("article") or ""), f"l'article 2 doit être cité : {sa!r}"
    syn = veille_plu.synthese_commune("97414") or {}
    assert syn.get("sursis_autorise"), "la synthèse commune doit porter sursis_autorise (fiche + vérif + PDF)"


# ─────────── LOT 6 — recherche infructueuse DATÉE (Étang-Salé / Saint-Denis / Saint-Paul) ───────────
@pytest.mark.parametrize("insee", ["97404", "97411", "97415"])
def test_debat_recherche_infructueuse_datee(insee):
    """Ces trois communes sont en révision SANS débat PADD retrouvé. La carte dit « vérifié le
    06/08/2026 » ; le débat, lui, a été cherché le 25/11/2026. L'écran doit DATER cette recherche
    infructueuse (« non retrouvée lors de la recherche du 25/11/2026 »), pas juste « non constaté »."""
    e = veille_plu.entry(insee) or {}
    assert e.get("debat_recherche_le") == "2026-11-25", (
        f"{insee} : date de recherche du débat attendue 2026-11-25 : {e.get('debat_recherche_le')!r}")
    syn = veille_plu.synthese_commune(insee) or {}
    pe = syn.get("prochaine_etape") or ""
    assert "25/11/2026" in pe, f"{insee} : la recherche infructueuse doit être datée : {pe!r}"
    assert "retrouv" in pe.lower(), f"{insee} : « non retrouvée lors de la recherche » attendu : {pe!r}"
    assert syn.get("debat_recherche_le") == "2026-11-25", f"{insee} : champ servi au radar"


# ─────────── LOT 4 — bloc Urbanisme en panne → « indisponible », jamais « document local » ───────────
def test_plu_statut_fallback_indisponible():
    """Le repli du bloc Urbanisme (source en échec) portait `statut: "document local"` : la carte
    affichait un BADGE VERT « document local » et « Document local — document local. », lu comme un
    renseignement. Le repli doit se signaler INDISPONIBLE (comme les autres blocs), sans valeur menteuse."""
    from labuse.api.fiche_commune import _FALLBACK
    fb = _FALLBACK["plu_statut"]
    assert fb.get("indisponible") is True, f"le repli doit porter indisponible=True : {fb!r}"
    assert fb.get("statut") != "document local", (
        f"« document local » dans le repli se fait passer pour un statut réel : {fb!r}")


# ─────────── LOT 2 — le Dossier PDF restitue le débat PADD (depuis le MÊME champ que la fiche) ───────────
def test_dossier_bloc_urbanisme_restitue_debat_padd():
    """Le bloc Urbanisme du Dossier lit `fiche['radar_procedure']` (le MÊME champ que la fiche
    parcelle) : procédure en cours, stade, date du débat PADD, sursis. Avant le correctif, le bloc
    règlement ignorait la procédure : la date du débat ne suivait pas jusqu'au PDF remis au client."""
    from labuse.exports import miroir
    fiche = {"idu": "97423000AB0005", "radar_procedure": {
        "synthese": {"etat": "Révision générale du PLU en cours", "debat_padd_tenu": "2025-09-04"},
        "sursis": None, "veille_au": None}}
    html = miroir._bloc_reglement({}, fiche)
    assert "04/09/2025" in html, f"la date du débat PADD doit figurer dans le bloc Urbanisme du PDF : {html!r}"
    assert "PADD" in html, f"le débat PADD doit être nommé : {html!r}"


# ─────────── LOT 6 — la source affichée au client n'est plus un nom de tour « FIX-13 » ───────────
@pytest.mark.db
@pytest.mark.reel
def test_verif_procedure_source_client_sans_nom_de_tour():
    """Le vérificateur affichait `source` BRUT du registre : à Saint-André, « FIX-13 LOT 1 (pièces
    OUVERTES et lues) ». Le client doit lire une CITATION propre (organisme · objet · date · réf ·
    lien), jamais un nom de tour interne. On sert `source_citation` (le même champ propre que la carte)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    eng = create_engine("postgresql+psycopg://openclaw@localhost:5432/labuse")
    from labuse.api import modules
    with Session(eng) as db:
        out = modules.verif_procedure("97409000AB0004", db=db)
    # la preuve que la fuite EXISTAIT : le registre brut porte bien le nom de tour
    assert "FIX-13" in (veille_plu.entry("97409") or {}).get("source", ""), "sanity : source brute = note interne"
    cit = out.get("source_citation")
    assert cit, f"le vérificateur doit servir une citation propre : {out!r}"
    assert "FIX-" not in cit and "LOT " not in cit, f"la citation ne doit pas porter de nom de tour : {cit!r}"
    assert "Saint-André" in cit or "saint-andré" in cit.lower(), f"la citation doit nommer l'organisme : {cit!r}"


# ─────────── LOT 3 — saturation du pool de connexions → 503 clair, jamais 500 ───────────
@pytest.mark.db
def test_route_pool_sature_rend_503_pas_500():
    """Quand les 15 connexions du pool sont TOUTES occupées, l'acquisition expire (QueuePool timeout →
    sqlalchemy.exc.TimeoutError), AVANT la lecture des blocs. La route doit répondre 503 « service
    momentanément chargé » (que l'écran affiche proprement), jamais un 500 brut (constat ASTRA-11 n°3)."""
    import os
    from fastapi.testclient import TestClient
    from sqlalchemy.exc import TimeoutError as SAT
    os.environ["LABUSE_ENV"] = "local"
    from labuse import config
    config.get_settings.cache_clear()
    from labuse.api.app import app, get_db

    def _pool_sature():   # la dépendance DB expire comme un pool saturé
        raise SAT("QueuePool limit of size 5 overflow 10 reached, connection timed out, timeout 30.00")
        yield  # pragma: no cover

    app.dependency_overrides[get_db] = _pool_sature
    try:
        r = TestClient(app).get("/communes/Les%20Trois-Bassins/contexte")
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert r.status_code == 503, f"pool saturé doit rendre 503, pas {r.status_code}"
    assert "chargé" in (r.json().get("detail") or "").lower(), r.json()
