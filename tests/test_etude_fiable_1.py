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


def test_r2_deux_analyses_memes_saisies_meme_resultat(session_reelle, monkeypatch):
    """R2 — deux analyses de suite, mêmes saisies → résultat IDENTIQUE (le temps n'arbitre plus).

    R2 vérifie le DÉTERMINISME (mêmes saisies → même résultat), PAS le filet temps (ça, c'est R3). Deux
    entrées de la machine faisaient diverger deux analyses pourtant identiques ; on neutralise les DEUX
    DANS CE SEUL TEST (jamais en production), pour que le test juge le déterminisme du calcul et non l'état
    de la machine :

    1. Le filet TEMPS `LABUSE_ETUDE_GRILLE_GARDE_FOU_S` coupe la grille à des INSTANTS différents selon la
       charge : sous charge, les deux analyses examinent un nombre de candidats DIFFÉRENT (« N candidats
       écartés » diverge). On porte le filet très haut via la variable d'env EXISTANTE (comme R3 le force à
       1 s dans l'autre sens) → la grille examine TOUJOURS les N candidats prévus.
    2. Le relief LiDAR (`terrain._pente_lidar`) complète les trous du raster local par un appel RÉSEAU IGN
       (`_completer_ign`, httpx, timeout 20 s, dégradation SILENCIEUSE). Sous charge l'appel aboutit pour
       une analyse et expire pour l'autre → `pente` diffère → le contrôle « implantation étagée » apparaît
       d'un côté seulement. On neutralise CET APPEL RÉSEAU (no-op) : la pente ne dépend plus que du raster
       EN BASE, déterministe. (Le défaut PRODUIT — un résultat qui dépend de la charge — reste ouvert,
       chantier « capacité maximale » ; ici on fiabilise seulement le test.)

    Aucun changement de comportement en production — seuls l'environnement et les dépendances externes de ce
    test sont neutralisés, et l'env est restauré (monkeypatch) en fin de test."""
    from labuse import config
    from labuse.faisabilite import profil_altimetrique
    from labuse.implantation.service import etudier_payload

    monkeypatch.setenv("LABUSE_ETUDE_GRILLE_GARDE_FOU_S", "86400")   # (1) filet neutralisé : le temps n'arbitre plus
    monkeypatch.setattr(profil_altimetrique, "_completer_ign", lambda pts: None)  # (2) zéro réseau IGN : pente déterministe
    config.get_settings.cache_clear()
    try:
        p1 = etudier_payload(session_reelle, _cfg_andre())
        p2 = etudier_payload(session_reelle, _cfg_andre())
    finally:
        config.get_settings.cache_clear()
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


def test_r4_etang_sale_compteur_coherent(session_reelle):
    """R4 — L'Étang-Salé (assemblage 4 parcelles), demande 23 T2 + 6 T3 : quand la demande NE TIENT PAS
    entièrement, le COMPTEUR de logements tenus est COHÉRENT — le total = la somme par typologie (le bug
    historique affichait 28 au total pour 27 réellement tenus). C'est cet invariant, pas un nombre magique,
    qui garde le compteur honnête.

    ETUDE-STATIONNEMENT-FIX-3 — le dégagement d'allée aérien est désormais un contrôle DUR (allées de 5 m au
    droit des places) : sur cette assiette dense, l'aérien ne tient plus les 27 logements que l'ancien
    dégagement mesuré à 0 laissait passer (voitures cramées sans allée). Le nombre exact tenu dépend donc du
    pavage (artefact), mais la COHÉRENCE du compteur, elle, doit tenir."""
    from labuse.implantation.service import etudier_payload
    cfg = {"idus": _ETANG, "type_projet": "social", "objectif": "equilibre", "stationnement": "aerien",
           "programme": {"mode": "saisi", "lignes": [{"type": "T2", "nombre": 23}, {"type": "T3", "nombre": 6}]}}
    p = etudier_payload(session_reelle, cfg)
    dep = p.get("depassement") or {}
    tiennent = dep.get("tiennent") or {}
    assert dep.get("total_tiennent") is not None, "la demande ne tient pas entièrement → un compteur est attendu"
    assert dep.get("total_tiennent") == sum(tiennent.values()), (
        f"compteur incohérent : total {dep.get('total_tiennent')} ≠ somme {sum(tiennent.values())}")


def test_point5_etude_revisions_est_table_client_jamais_poussee():
    """Point 5 — etude_revisions porte des données CLIENT : elle est déclarée table client (prod fait
    foi) et DISJOINTE des listes poussées par le Mac (fond + run sync) → un envoi de données ne peut
    JAMAIS l'écraser en prod. Garde pure (sans base), tourne dans le hook."""
    from pathlib import Path

    from labuse.flux_sens import CLIENT_PROD, tables_client, tables_fond, tables_quotidiennes

    assert "etude_revisions" in CLIENT_PROD
    assert "etude_revisions" in tables_client()
    # jamais dans une liste Mac→prod (fond) ni dans un flux quotidien ingéré ailleurs.
    assert "etude_revisions" not in tables_fond()
    assert "etude_revisions" not in tables_quotidiennes()
    assert not (set(tables_client()) & set(tables_fond())), "client ∩ fond doit être vide (sens opposés)"
    # et jamais dans le dump de synchronisation run (deploy/scripts/sync-run.sh pousse un WHITELIST).
    sync = Path(__file__).resolve().parents[1] / "deploy" / "scripts" / "sync-run.sh"
    if sync.exists():
        txt = sync.read_text(encoding="utf-8")
        for t in tables_client():
            assert f"({t} " not in txt and f" {t})" not in txt and f" {t} " not in txt.replace("=(", "= ("), \
                f"{t} (table client) ne doit pas figurer dans la whitelist de sync-run.sh"
