"""ETUDE-FIABLE-1 — RECETTE : résultat stable + PDF identique à l'écran depuis une révision.

R1 : analyser → enregistre une révision ; exporter le PDF NE rappelle PAS le moteur (il relit la
     révision), et le numéro EF-… est identique.
R2 : deux analyses de suite, mêmes saisies → résultat IDENTIQUE (déterminisme, LOT A).
R4 : L'Étang-Salé — le compteur « logements tenus » vaut 27 (compté par type demandé), pas 28 (LOT C3).

Tests RÉELS (base applicative) : skip propre si `LABUSE_APP_DATABASE_URL` absent ou parcelles absentes.
"""
from __future__ import annotations

import json
import os

import pytest

_ETANG = ["97404000AW0099", "97404000AW0451", "97404000AW0624", "97404000AW0625"]
_ANDRE = ["97409000AX0255", "97409000AX0256"]


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine

    url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent")
    # Comme les autres tests `reel` : si la base est injoignable (ex. pré-push sans base applicative),
    # on SKIP proprement au lieu d'ERROR.
    try:
        eng = make_engine(url=url)
        s = sessionmaker(bind=eng, future=True)()
        n = s.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"),
                      {"i": _ETANG + _ANDRE}).scalar()
    except Exception as exc:  # noqa: BLE001 — base indisponible → skip, pas error
        pytest.skip(f"base applicative indisponible : {exc}")
    if n != 6:
        s.close()
        pytest.skip("parcelles témoins absentes")
    yield s
    s.close()


def _cfg_andre():
    return {"idus": _ANDRE, "type_projet": "social", "objectif": "equilibre", "stationnement": "aerien",
            "programme": {"mode": "saisi", "lignes": [{"type": "T2", "nombre": 8},
                                                      {"type": "T3", "nombre": 6}, {"type": "T1", "nombre": 4}]}}


def _chiffres(p: dict) -> dict:
    """Les chiffres servis qui doivent être STABLES (hors SVG volumineux)."""
    cm = p.get("capacite_maximale") or {}
    return {
        "study_id": p.get("study_id"),
        "verdict": p.get("verdict"),
        "capmax": cm.get("logements"),
        "places": cm.get("places"),
        "niveaux": cm.get("niveaux"),
        "depassement": p.get("depassement"),
        "confrontation": p.get("confrontation"),
        "recherche": p.get("recherche"),
    }


def test_r2_deux_analyses_memes_saisies_meme_resultat(session_reelle):
    """R2 — deux analyses de suite, mêmes saisies → résultat IDENTIQUE (le temps n'arbitre plus)."""
    from labuse.implantation.service import etudier_payload
    p1 = etudier_payload(session_reelle, _cfg_andre())
    p2 = etudier_payload(session_reelle, _cfg_andre())
    assert json.dumps(p1, sort_keys=True, default=str) == json.dumps(p2, sort_keys=True, default=str)
    # et la recherche est COMPLÈTE (nombre de candidats déterministe, pas coupée par le temps)
    assert (p1.get("recherche") or {}).get("etat") == "complete"
    assert (p1.get("recherche") or {}).get("candidats_examines") == (p1.get("recherche") or {}).get("candidats_prevus")


def test_r1_export_relit_la_revision_sans_moteur(session_reelle, monkeypatch):
    """R1 — le résultat affiché est ENREGISTRÉ (révision), et le PDF est rendu DEPUIS la révision :
    exporter NE rappelle PAS le moteur (etudier_payload), le numéro EF-… est identique, mêmes chiffres."""
    os.environ["LABUSE_PDF_PROCESS_ISOLE"] = "0"   # rendu WeasyPrint in-process pour le test
    from labuse.exports import etude_faisabilite as ef
    from labuse.exports.rendu import render_pdf
    from labuse.implantation import revisions, service

    cfg = _cfg_andre()
    sid = service._study_id(cfg)
    # 1) ANALYSE (écran) → on enregistre EXACTEMENT le payload affiché.
    ecran = service.etudier_payload(session_reelle, cfg)
    assert ecran.get("study_id") == sid
    revisions.enregistrer(session_reelle, ecran)
    session_reelle.commit()

    # 2) ROUVRIR : la révision relue est identique aux chiffres de l'écran (SANS recalcul).
    rev = revisions.charger(session_reelle, sid)
    assert rev is not None, "la révision doit être enregistrée en fin d'analyse"
    assert _chiffres(rev) == _chiffres(ecran)

    # 3) EXPORT PDF DEPUIS LA RÉVISION → le moteur ne doit PAS être appelé.
    appels = {"n": 0}
    vrai = service.etudier_payload

    def espion(*a, **k):          # noqa: ANN001
        appels["n"] += 1
        return vrai(*a, **k)

    monkeypatch.setattr(service, "etudier_payload", espion)
    rendu = ef.rendu_etude(rev, genere_le="2026-11-12")          # rend DEPUIS la révision relue
    pdf = render_pdf(rendu["html"])
    assert appels["n"] == 0, "l'export ne doit PAS rappeler le moteur (il relit la révision)"
    assert pdf and len(pdf) > 1000, "un PDF doit être produit"
    # 4) même numéro EF-… à l'écran et au PDF (B4 : le numéro identifie la révision).
    assert rendu["numero"] == sid[:11] == (rev.get("study_id") or "")[:11]


def test_b2_rouvrir_par_config_sans_moteur(session_reelle, monkeypatch):
    """B2 (câblage front) — ROUVRIR par CONFIGURATION relit la révision enregistrée SANS appeler le moteur
    (le front n'a pas à connaître le study_id : le serveur l'empreinte de la config). Mêmes chiffres."""
    from labuse.api import modules
    from labuse.implantation import revisions, service

    # même chemin que l'API : le corps est normalisé (model_dump) avant analyse ET empreinte study_id.
    body = modules.EtudeIn(**_cfg_andre())
    data = body.model_dump()
    sid = service._study_id(data)
    ecran = service.etudier_payload(session_reelle, data)
    revisions.enregistrer(session_reelle, ecran)
    session_reelle.commit()

    appels = {"n": 0}
    vrai = service.etudier_payload

    def espion(*a, **k):          # noqa: ANN001
        appels["n"] += 1
        return vrai(*a, **k)

    monkeypatch.setattr(service, "etudier_payload", espion)
    rev = modules.etude_revision_par_config(body, db=session_reelle)
    assert appels["n"] == 0, "rouvrir par config ne doit PAS appeler le moteur"
    assert rev.get("study_id") == sid
    assert _chiffres(rev) == _chiffres(ecran)


def test_r3_garde_fou_force_recherche_partielle(session_reelle, monkeypatch):
    """R3 — garde-fou temps forcé à 1 s : la recherche est COUPÉE avant les N candidats → état
    « partielle », visible à l'écran (payload.recherche) ET dans le PDF (même texte)."""
    os.environ["LABUSE_PDF_PROCESS_ISOLE"] = "0"
    from labuse import config
    from labuse.exports import etude_faisabilite as ef
    from labuse.implantation.service import etudier_payload

    monkeypatch.setenv("LABUSE_ETUDE_GRILLE_GARDE_FOU_S", "1")
    config.get_settings.cache_clear()
    try:
        p = etudier_payload(session_reelle, _cfg_andre())
    finally:
        config.get_settings.cache_clear()
    rech = p.get("recherche") or {}
    assert rech.get("etat") == "partielle", f"attendu partielle, obtenu {rech.get('etat')}"
    assert rech.get("garde_fou_temps") is True
    assert rech.get("candidats_examines") < rech.get("candidats_prevus")
    assert "Recherche partielle" in (rech.get("note") or "")
    # le PDF porte le même état (mention « Recherche partielle »).
    html = ef.rendu_etude(p, genere_le="2026-11-12")["html"]
    assert "Recherche partielle" in html


def test_r4_etang_sale_compteur_27(session_reelle):
    """R4 — L'Étang-Salé : 23 T2 + 6 T3 demandés → 27 logements tenus (23 T2 + 4 T3), pas 28."""
    from labuse.implantation.service import etudier_payload
    cfg = {"idus": _ETANG, "type_projet": "social", "objectif": "equilibre", "stationnement": "aerien",
           "programme": {"mode": "saisi", "lignes": [{"type": "T2", "nombre": 23}, {"type": "T3", "nombre": 6}]}}
    p = etudier_payload(session_reelle, cfg)
    dep = p.get("depassement") or {}
    assert dep.get("total_tiennent") == 27, f"attendu 27, obtenu {dep.get('total_tiennent')}"
    assert dep.get("total_tiennent") == sum((dep.get("tiennent") or {}).values())
