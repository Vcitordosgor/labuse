"""CIRCUIT-5 lot 4 — le verrou des communes : la bonne ligne pour la bonne commune.
Chaque verrou prouvé CASSÉ sur un cas construit (jointure décalée, code fantôme, trou
d'échantillon), puis VERT."""
from __future__ import annotations

import copy
import json

import pytest
from sqlalchemy import text

from labuse import circuit_verrous as CV
from labuse import referentiel_communes as RC
from labuse.filtres import echantillon_communes as EC

pytestmark = pytest.mark.verrous


# ── V4a — la clé étrangère interdit l'entrée ────────────────────────────────────────────

@pytest.mark.db
def test_v4a_un_code_fantome_ne_peut_plus_entrer(db_session):
    """PREUVE VIVANTE : après `poser_fks`, un INSERT avec un code hors référentiel est
    REJETÉ par Postgres (l'avertissement de CIRCUIT-3 est devenu une interdiction)."""
    RC.poser_fks(db_session)
    with pytest.raises(Exception, match="fk_commune_contexte_sru_commune|foreign key"):
        with db_session.begin_nested():
            db_session.execute(text(
                "INSERT INTO commune_contexte_sru (insee, commune, statut) "
                "VALUES ('97499', 'Commune fantôme', 'test')"))


@pytest.mark.db
def test_v4a_le_referentiel_vient_du_code(db_session):
    RC.ensure_referentiel(db_session)
    n = db_session.execute(text("SELECT count(*) FROM communes_referentiel")).scalar()
    noms = db_session.execute(text(
        "SELECT nom FROM communes_referentiel WHERE insee IN ('97410', '97418') ORDER BY insee")).scalars().all()
    assert n == 24
    assert noms == ["Saint-Benoît", "Sainte-Marie"]


def test_v4a_prouve_casse_sur_contrainte_absente(monkeypatch):
    monkeypatch.setattr(RC, "etat_fks", lambda db: {"commune_contexte_sru": "absente"})
    r = CV.verrou_communes_fk(None)
    assert r.verdict == "casse"
    assert any("commune_contexte_sru" in d for d in r.details)


def test_v4a_lignes_heritees_sont_a_decider(monkeypatch):
    monkeypatch.setattr(RC, "etat_fks",
                        lambda db: {"sirene_etablissements": "not_valid (1 ligne(s) fautive(s) héritée(s))"})
    r = CV.verrou_communes_fk(None)
    assert r.verdict == "a_decider"


# ── V4b — permutation : les valeurs de CHACUNE, pas seulement différentes ───────────────

def _payloads_fideles() -> dict[str, dict]:
    return {
        "97410": {"sru": {"insee": "97410", "commune": "Saint-Benoît", "taux_lls": "34.49"},
                  "population": {"habitants": 36124}, "risques": {"catnat_arretes": 17}},
        "97418": {"sru": {"insee": "97418", "commune": "Sainte-Marie", "taux_lls": "18.0"},
                  "population": {"habitants": 34000}, "risques": {"catnat_arretes": 22}},
    }


def test_v4b_prouve_casse_sur_jointure_decalee():
    """PREUVE : servir la ligne de Sainte-Marie sous Saint-Benoît (jointure volontairement
    décalée d'une commune) casse le verrou — l'identité du bloc ET l'attendu producteur
    (CatNat 22 ≠ 17) le disent tous les deux."""
    payloads = _payloads_fideles()
    payloads["97410"] = copy.deepcopy(payloads["97418"])     # le décalage : B servi sous A
    r = CV.verrou_communes_permutation(payloads=payloads)
    assert r.verdict == "casse"
    assert any("insee=97418" in d for d in r.details)
    assert any("carte risques" in d and "97410" in d for d in r.details)


def test_v4b_prouve_casse_sur_premiere_ligne_par_defaut():
    """Un « première ligne » par défaut (la même valeur servie partout) casse : une des deux
    communes ne peut pas porter la valeur attendue de l'autre."""
    payloads = _payloads_fideles()
    payloads["97418"]["risques"]["catnat_arretes"] = 17      # la valeur de 97410 partout
    r = CV.verrou_communes_permutation(payloads=payloads)
    assert r.verdict == "casse"
    assert any("97418" in d and "17" in d for d in r.details)


def test_v4b_vert_quand_chacune_sert_ses_valeurs():
    r = CV.verrou_communes_permutation(payloads=_payloads_fideles())
    assert r.verdict == "ok", r.details


# ── V4c — parcelles frontière ───────────────────────────────────────────────────────────

@pytest.mark.local
def test_v4c_frontiere_sur_la_base_reelle():
    """VERT sur la base réelle ; PREUVE CASSÉ : attendre la commune VOISINE (simule la couche
    collée de l'autre côté de la limite) fait échouer chaque témoin."""
    import os

    from sqlalchemy.orm import sessionmaker

    from labuse import db as db_mod
    real = db_mod.make_engine(os.environ["LABUSE_APP_DATABASE_URL"])
    with sessionmaker(bind=real)() as s:
        r = CV.verrou_communes_frontiere(s)
        assert r.verdict == "ok", r.details

        doc = json.loads((EC.DOSSIER / "frontieres.json").read_text())
        for l in doc["lignes"]:
            l["commune_attendue"], l["voisine"] = l["voisine"], l["commune_attendue"]
        r2 = CV.verrou_communes_frontiere(s, temoins=doc)
        assert r2.verdict == "casse"
        assert len(r2.details) >= 3


# ── V4d — l'échantillon couvre tout ─────────────────────────────────────────────────────

def test_v4d_vert_sur_les_fichiers_livres():
    r = CV.verrou_communes_echantillons()
    assert r.verdict == "ok", r.details[:6]


def test_v4d_prouve_casse_sur_un_trou(monkeypatch):
    """Une commune retirée d'une carte (trou silencieux posé exprès) casse le verrou."""
    vrai = EC.charger

    def _troue(carte):
        doc = copy.deepcopy(vrai(carte))
        if carte == "sru" and doc.get("lignes"):
            doc["lignes"] = [l for l in doc["lignes"] if l["insee"] != "97418"]
        return doc
    monkeypatch.setattr(EC, "charger", _troue)
    r = CV.verrou_communes_echantillons()
    assert r.verdict == "casse"
    assert any("sru" in d and "97418" in d for d in r.details)


def test_rejouer_distingue_ecart_et_ecart_assume():
    """Les deux écarts de définition CONNUS (Saint-Denis Filosofi, Saint-Joseph doublon
    GASPAR) sortent `assume` avec leur note — une dérive NOUVELLE sortirait `ecart`."""
    payloads = {
        "97411": {"population": {"habitants": 130938}},   # Filosofi < légale : assumé
        "97412": {"risques": {"catnat_arretes": 20}},      # doublon producteur : assumé
        "97410": {"risques": {"catnat_arretes": 3}},       # dérive NOUVELLE posée exprès
    }
    res = {(r["carte"], r["insee"]): r for r in EC.rejouer(payloads)}
    assert res[("population", "97411")]["verdict"] == "assume"
    assert res[("risques", "97412")]["verdict"] == "assume"
    assert res[("risques", "97410")]["verdict"] == "ecart"
    assert res[("population", "97411")]["note"]


def test_lire_champ_comprend_les_chemins():
    assert EC._lire_champ({"population": {"habitants": 5}}, "population.habitants") == 5
    assert EC._lire_champ({"qpv": [1, 2]}, "qpv[].len") == 2
    assert EC._lire_champ({}, "population.habitants") is None
