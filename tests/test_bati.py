"""Tests correctif R1 « déjà bâti » : classification graduée, signaux, déclassement, fiche.

Verrouille le cas d'audit : une résidence (plusieurs bâtiments, ratio < 30 % à cause des
espaces communs — BP0571 réel : 18 %, 4 bâtiments, max 418 m²) DOIT être déclassée par la
règle « ensemble bâti », sans sur-corriger les parcelles peu bâties ou restructurables.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import bati
from labuse.enums import EvaluationStatus as ES
from labuse.scoring.declassement import apply_declassement

pytestmark = pytest.mark.db


# ───────────────────────── Classification pure ─────────────────────────

def test_classify_paliers():
    assert bati.classify(0.0, 0, 0, 1000)["code"] == "vacant"
    assert bati.classify(0.04, 1, 30, 1000)["code"] == "vacant"
    assert bati.classify(0.08, 1, 60, 1000)["code"] == "peu_bati"
    assert bati.classify(0.08, 1, 60, 1000)["declasse"] is None          # pas de déclassement
    assert bati.classify(0.20, 1, 120, 1000)["code"] == "partiellement_bati"
    assert bati.classify(0.20, 1, 120, 1000)["declasse"] == "a_creuser"
    assert bati.classify(0.35, 2, 200, 1000)["code"] == "deja_bati_probable"
    assert bati.classify(0.35, 2, 200, 1000)["declasse"] == "faux_positif"
    assert bati.classify(0.62, 3, 300, 1000)["code"] == "deja_bati"
    assert bati.classify(0.62, 3, 300, 1000)["declasse"] == "faux_positif"


def test_classify_ensemble_bati_cas_bp0571():
    # Le cas d'audit : 18 % / 4 bâtiments / max 418 m² → la règle ratio seule (≥30 %)
    # raterait la résidence ; « ensemble bâti » l'attrape.
    c = bati.classify(0.18, 4, 418.0, 9222.0)
    assert c["code"] == "ensemble_bati" and c["declasse"] == "faux_positif"
    assert "ensemble bâti" in c["motif"] and "BD TOPO" in c["motif"]
    # Variante « grand bâtiment seul » (1 bâtiment de 500 m², 20 %)
    c2 = bati.classify(0.20, 1, 500.0, 2500.0)
    assert c2["code"] == "ensemble_bati" and "grand bâtiment" in c2["motif"]


def test_classify_ne_sur_corrige_pas():
    # 3 cabanons sur une GRANDE parcelle → ratio minuscule → pas d'ensemble bâti.
    assert bati.classify(0.006, 3, 60.0, 10000.0)["code"] == "vacant"
    # Grande parcelle peu bâtie → restructuration potentielle (label, pas de déclassement).
    c = bati.classify(0.08, 2, 200.0, 8000.0)
    assert c["declasse"] is None and "restructuration" in c["label"].lower()


def test_classify_motifs_affiches_jamais_supprimes():
    c = bati.classify(0.45, 5, 350.0, 3000.0)
    assert "45 %" in c["motif"] and "5 bâtiment" in c["motif"]


# ───────────────────────── Intégration déclassement ─────────────────────────

def test_apply_declassement_deja_bati():
    st, motif = apply_declassement(ES.OPPORTUNITE, {"surface_m2": 5000.0, "bati_ratio": 0.55,
                                                    "bati_count": 6, "bati_max_m2": 400.0})
    assert st == ES.FAUX_POSITIF_PROBABLE and "déjà bâtie" in motif


def test_apply_declassement_ensemble_bati():
    st, motif = apply_declassement(ES.OPPORTUNITE, {"surface_m2": 9222.0, "bati_ratio": 0.18,
                                                    "bati_count": 4, "bati_max_m2": 418.0})
    assert st == ES.FAUX_POSITIF_PROBABLE and "ensemble bâti" in motif


def test_apply_declassement_partiellement_bati_a_creuser():
    st, motif = apply_declassement(ES.OPPORTUNITE, {"surface_m2": 1000.0, "bati_ratio": 0.20,
                                                    "bati_count": 1, "bati_max_m2": 150.0})
    assert st == ES.A_CREUSER and "occupation à vérifier" in motif


def test_apply_declassement_peu_bati_inchange():
    st, motif = apply_declassement(ES.OPPORTUNITE, {"surface_m2": 1000.0, "bati_ratio": 0.08,
                                                    "bati_count": 1, "bati_max_m2": 60.0})
    assert st == ES.OPPORTUNITE and motif is None


def test_apply_declassement_sans_signal_bati_inchange():
    # Couche absente → bati_ratio absent → aucun verdict « vacant » mensonger.
    st, motif = apply_declassement(ES.OPPORTUNITE, {"surface_m2": 1000.0})
    assert st == ES.OPPORTUNITE and motif is None


def test_apply_declassement_ne_remonte_jamais():
    st, _ = apply_declassement(ES.EXCLUE, {"surface_m2": 5000.0, "bati_ratio": 0.0,
                                           "bati_count": 0, "bati_max_m2": 0.0})
    assert st == ES.EXCLUE


# ───────────────────────── Accès / enclavement (audit O1) ─────────────────────────

def test_acces_non_identifie_a_creuser():
    # voirie à 12 m (> seuil 6 m) → enclavement PROBABLE → à creuser, jamais faux positif.
    st, motif = apply_declassement(ES.OPPORTUNITE, {"surface_m2": 2000.0, "acces_dist_m": 12.0})
    assert st == ES.A_CREUSER and "accès non identifié" in motif and "servitude" in motif


def test_acces_aucune_voirie_a_creuser():
    st, motif = apply_declassement(ES.OPPORTUNITE, {"surface_m2": 2000.0, "acces_dist_m": None})
    assert st == ES.A_CREUSER and "aucune voirie" in motif


def test_acces_voirie_proche_inchange():
    st, motif = apply_declassement(ES.OPPORTUNITE, {"surface_m2": 2000.0, "acces_dist_m": 0.0})
    assert st == ES.OPPORTUNITE and motif is None


def test_acces_cle_absente_aucun_signal():
    # Couche voirie non ingérée → clé absente → jamais d'« enclavée » déduite du vide.
    st, motif = apply_declassement(ES.OPPORTUNITE, {"surface_m2": 2000.0})
    assert st == ES.OPPORTUNITE and motif is None


def test_compute_declass_signals_inclut_acces(db_session):
    from labuse.scoring.declassement import compute_declass_signals
    pid = _parcel(db_session, "BT0000000000D4", x0=55.60)
    # voirie au CONTACT de la parcelle (ligne traversante)
    db_session.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, geom, commune) VALUES "
        "('voirie','route','voie test', ST_GeomFromText('LINESTRING(55.5995 -20.9995, 55.6015 -20.9995)',4326), 'BatiTest')"))
    db_session.flush()
    sig = compute_declass_signals(db_session, [pid])[pid]
    assert "acces_dist_m" in sig and sig["acces_dist_m"] is not None and sig["acces_dist_m"] <= 6.0


# ───────────────────────── DB : signaux batch + fiche ─────────────────────────

def _parcel(db, idu, x0=55.30, w=0.001):
    wkt = (f"POLYGON(({x0} -21.0,{x0 + w} -21.0,{x0 + w} -20.999,{x0} -20.999,{x0} -21.0))")
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, geom, surface_m2, centroid) VALUES "
        "(:i,'BatiTest', ST_GeomFromText(:w,4326), 10000, ST_Centroid(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": wkt}).scalar()


def _building(db, x0, y0, w, h):
    wkt = (f"POLYGON(({x0} {y0},{x0 + w} {y0},{x0 + w} {y0 + h},{x0} {y0 + h},{x0} {y0}))")
    db.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, geom, commune) VALUES "
        "('batiment','Indifférenciée','bâtiment', ST_GeomFromText(:w,4326), 'BatiTest')"), {"w": wkt})


def test_stats_batch_et_fiche_block(db_session):
    pid = _parcel(db_session, "BT0000000000A1")
    # un bâtiment couvrant ~60 % de la parcelle (0.0006/0.001 de large, pleine hauteur)
    _building(db_session, 55.3001, -21.0, 0.0006, 0.001)
    db_session.flush()
    st = bati.stats_batch(db_session, [pid])[pid]
    assert 0.50 <= st["bati_ratio"] <= 0.70 and st["bati_count"] == 1
    fb = bati.fiche_block(db_session, pid, 10000.0)
    assert fb["disponible"] is True and fb["code"] == "deja_bati"
    assert "déjà bâtie" in fb["label"].lower() or "Parcelle déjà bâtie" in fb["label"]
    assert fb["source"].startswith("BD TOPO")


def test_fiche_block_sans_couche_dit_non_verifie(db_session):
    pid = _parcel(db_session, "BT0000000000B2", x0=55.40)
    db_session.flush()
    if bati.layer_available(db_session):           # une autre insertion du même run de tests
        pytest.skip("couche batiment présente dans cette session de test")
    fb = bati.fiche_block(db_session, pid, 10000.0)
    assert fb["disponible"] is False and "non vérifiée" in fb["label"]
    assert fb["confiance"] == "indisponible"


def test_compute_declass_signals_inclut_bati(db_session):
    from labuse.scoring.declassement import compute_declass_signals
    pid = _parcel(db_session, "BT0000000000C3", x0=55.50)
    _building(db_session, 55.5001, -21.0, 0.0006, 0.001)
    db_session.flush()
    sig = compute_declass_signals(db_session, [pid])[pid]
    assert sig.get("bati_ratio") and sig["bati_ratio"] > 0.4
    assert sig.get("bati_count") == 1
