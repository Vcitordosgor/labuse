"""ETUDE-PLAFOND-1 — l'état de la recherche ne ment jamais quand le 2ᵉ passage est sauté.

Le 2ᵉ passage (« faisable-probable ») ne fait qu'AJOUTER des faisables quand le 1ᵉʳ n'en a trouvé
aucun. S'il est SAUTÉ faute de temps (enveloppe de calcul épuisée, fréquent sur une machine lente),
le résultat peut être plus bas que sur une machine rapide — l'état DOIT alors être « partielle »,
jamais « complete » ni « non_aboutie » (= impossible établie).
"""
from __future__ import annotations

import os

import pytest

_ANDRE = ["97409000AX0255", "97409000AX0256"]


def _cfg_andre():
    return {"idus": _ANDRE, "type_projet": "social", "objectif": "equilibre", "stationnement": "aerien",
            "programme": {"mode": "saisi", "lignes": [{"type": "T2", "nombre": 8},
                                                      {"type": "T3", "nombre": 6}, {"type": "T1", "nombre": 4}]}}


# ─────────────────────────── garde PURE (sans base) : la décision d'état ───────────────────────────

def test_etat_partielle_quand_2e_passage_saute_sans_resultat():
    """Cœur du mandat — recherche INTERROMPUE (garde-fou temps) + 2ᵉ passage sauté → AUCUN résultat
    trouvé : l'état est « partielle » (plancher machine-dépendant), JAMAIS « non_aboutie »."""
    from labuse.implantation.service import _etat_recherche
    assert _etat_recherche(garde_fou=True, complete=False, a_un_resultat=False) == "partielle"


def test_etat_partielle_quand_interrompu_avec_resultat():
    from labuse.implantation.service import _etat_recherche
    assert _etat_recherche(garde_fou=True, complete=False, a_un_resultat=True) == "partielle"


def test_etat_non_aboutie_seulement_si_recherche_entiere_sans_resultat():
    """« non_aboutie » (impossible établie) UNIQUEMENT si la grille s'est déroulée JUSQU'AU BOUT."""
    from labuse.implantation.service import _etat_recherche
    assert _etat_recherche(garde_fou=False, complete=True, a_un_resultat=False) == "non_aboutie"


def test_etat_complete():
    from labuse.implantation.service import _etat_recherche
    assert _etat_recherche(garde_fou=False, complete=True, a_un_resultat=True) == "complete"


# ─────────────────────────── garde RÉELLE (base applicative) : bout en bout ───────────────────────────

@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine

    url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent")
    try:
        eng = make_engine(url=url)
        s = sessionmaker(bind=eng, future=True)()
        n = s.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"), {"i": _ANDRE}).scalar()
    except Exception as exc:  # noqa: BLE001 — base indisponible → skip, pas error
        pytest.skip(f"base applicative indisponible : {exc}")
    if n != 2:
        s.close()
        pytest.skip("parcelles témoins absentes")
    yield s
    s.close()


def test_saut_2e_passage_etat_partielle_bout_en_bout(session_reelle, monkeypatch):
    """On FORCE le saut du 2ᵉ passage : enveloppe de calcul = 0 (plus aucun temps pour le repli) ET
    filet temps du 1ᵉʳ passage minuscule (grille coupée d'emblée). La recherche est donc INCOMPLÈTE.
    L'état servi au payload (écran + PDF) doit être « partielle », jamais « complete » : le filet
    temps est signalé et moins de candidats que prévu ont été examinés."""
    from labuse import config
    from labuse.implantation import moteur
    from labuse.implantation.service import etudier_payload

    monkeypatch.setattr(moteur, "_ENVELOPPE_CALCUL_S", 0.0)          # restant < 4 → repli TOUJOURS sauté
    monkeypatch.setenv("LABUSE_ETUDE_GRILLE_GARDE_FOU_S", "0.01")    # 1ᵉʳ passage coupé tout de suite
    config.get_settings.cache_clear()
    try:
        p = etudier_payload(session_reelle, _cfg_andre())
    finally:
        config.get_settings.cache_clear()

    rech = p.get("recherche") or {}
    assert rech.get("etat") == "partielle", f"attendu partielle, obtenu {rech.get('etat')}"
    assert rech.get("etat") != "complete"
    assert rech.get("garde_fou_temps") is True
    # la recherche a bien été coupée AVANT d'examiner tous les candidats prévus (preuve du saut).
    assert rech.get("candidats_examines") < rech.get("candidats_prevus")
    # le libellé affiché reste honnête (« Recherche partielle », jamais « non aboutie »).
    assert (rech.get("note") or "").startswith("Recherche partielle")
