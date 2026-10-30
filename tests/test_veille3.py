"""VEILLE-3 — « Modifier » une alerte Radar : remplace les critères EN PLACE (id/created_at/pause
conservés), avec dédup excluant l'alerte en cours d'édition. Teste le module `pige.veille` directement
(les routes PUT /radar/veille/{id} et GET /events/suivis sont couvertes par test_pige_api / m85)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import veille

pytestmark = pytest.mark.db


def _compte(db, nom):
    return db.execute(text("INSERT INTO comptes (nom, plan, founding, statut, sieges) "
                           "VALUES (:n,'integral',false,'actif',1) RETURNING id"), {"n": nom}).scalar()


def test_modifier_remplace_criteres_en_place():
    tag = uuid.uuid4().hex[:6]
    cid = None
    try:
        with session_scope() as db:
            cid = _compte(db, f"[V3] {tag}")
            vid = veille.creer(db, compte_id=cid, criteria={"commune": "Le Tampon", "type_bien": "terrain", "surface_min": 2000})
            db.commit()
            # on remplace les critères (surface 2000 → 2500, +prix_max)
            ok = veille.modifier(db, cid, vid, {"communes": ["Le Tampon"], "type_bien": "terrain", "surface_min": 2500, "prix_max": 400000})
            db.commit()
            assert ok is True
            rows = veille.lister(db, cid)
            assert len(rows) == 1
            r = rows[0]
            # l'id est CONSERVÉ (remplacement en place, pas une suppression/recréation)
            assert r["id"] == vid
            assert r["criteria"].get("surface_min") == 2500
            assert r["criteria"].get("prix_max") == 400000
            assert r["criteria"].get("communes") == ["Le Tampon"]
    finally:
        if cid is not None:
            with session_scope() as db:
                db.execute(text("DELETE FROM veilles WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM utilisateurs WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM comptes WHERE id=:c"), {"c": cid})


def test_modifier_garde_idor_autre_compte():
    """Modifier une alerte d'un AUTRE compte ne touche rien (garde IDOR compte-scopé)."""
    tag = uuid.uuid4().hex[:6]
    a = b = None
    try:
        with session_scope() as db:
            a = _compte(db, f"[V3a] {tag}")
            b = _compte(db, f"[V3b] {tag}")
            vid = veille.creer(db, compte_id=a, criteria={"commune": "Saint-Paul"})
            db.commit()
            # b tente de modifier l'alerte de a → aucune ligne touchée
            ok = veille.modifier(db, b, vid, {"commune": "Cilaos"})
            db.commit()
            assert ok is False
            assert veille.lister(db, a)[0]["criteria"].get("commune") == "Saint-Paul"
    finally:
        with session_scope() as db:
            for cid in (a, b):
                if cid is not None:
                    db.execute(text("DELETE FROM veilles WHERE compte_id=:c"), {"c": cid})
                    db.execute(text("DELETE FROM utilisateurs WHERE compte_id=:c"), {"c": cid})
                    db.execute(text("DELETE FROM comptes WHERE id=:c"), {"c": cid})


def test_existe_identique_exclut_soi_meme():
    """`sauf_id` exclut l'alerte éditée : ré-enregistrer SANS changer les critères n'est PAS un doublon,
    mais dupliquer une AUTRE alerte du compte en est un."""
    tag = uuid.uuid4().hex[:6]
    cid = None
    try:
        with session_scope() as db:
            cid = _compte(db, f"[V3d] {tag}")
            v1 = veille.creer(db, compte_id=cid, criteria={"communes": ["Le Tampon"], "type_bien": "terrain"})
            veille.creer(db, compte_id=cid, criteria={"communes": ["Saint-Paul"], "type_bien": "maison"})
            db.commit()
            crit_v1 = {"communes": ["Le Tampon"], "type_bien": "terrain"}
            # sans sauf_id : v1 EST vu comme doublon de lui-même
            assert veille.existe_identique(db, cid, crit_v1) is True
            # avec sauf_id=v1 : plus de faux doublon (on édite v1 sans changer ses critères)
            assert veille.existe_identique(db, cid, crit_v1, sauf_id=v1) is False
            # mais reprendre EXACTEMENT les critères de l'AUTRE alerte reste un doublon
            assert veille.existe_identique(db, cid, {"communes": ["Saint-Paul"], "type_bien": "maison"}, sauf_id=v1) is True
    finally:
        if cid is not None:
            with session_scope() as db:
                db.execute(text("DELETE FROM veilles WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM utilisateurs WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM comptes WHERE id=:c"), {"c": cid})
