"""VEILLE-FIX-2 · Lot A — le Radar ne rate plus le dépôt du soir.

`radar-cloche` regardait « les annonces d'aujourd'hui ». La capture se faisant le SOIR, au passage du
matin les annonces étaient datées de la veille → jamais vues. La fenêtre est désormais « depuis le
dernier passage du job » (horodatage persistant, repli J-1 au premier passage).

Preuve : des annonces déposées HIER SOIR (date_premiere_saisie = hier) → présentes dans la cloche au
passage du matin. [VF2-A] purgés en fin.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import digests, veille

pytestmark = pytest.mark.db


def _compte_actif(db, nom: str, email: str) -> int:
    cid = db.execute(text("INSERT INTO comptes (nom, plan, founding, statut, sieges) "
                          "VALUES (:n,'integral',false,'actif',1) RETURNING id"), {"n": nom}).scalar()
    db.execute(text("INSERT INTO utilisateurs (compte_id, email, role, statut, echecs_login) "
                    "VALUES (:c,:e,'titulaire','actif',0)"), {"c": cid, "e": email})
    return cid


def _bien_hier_soir(db, commune: str, prix: int, surf: int) -> int:
    """Une annonce déposée HIER à 22h (heure Réunion) — hors de la fenêtre « aujourd'hui »."""
    bid = db.execute(text(
        "INSERT INTO pige_biens (commune,type_bien,est_copro,statut,a_qualifier,date_premiere_saisie) "
        "VALUES (:c,'maison',false,'active',false, "
        " ((now() AT TIME ZONE 'Indian/Reunion')::date - 1 + time '22:00') AT TIME ZONE 'Indian/Reunion') "
        "RETURNING bien_id"), {"c": commune}).scalar()
    db.execute(text("INSERT INTO pige_faits (bien_id,prix,type_bien,surface_hab,particulier_pro,valide_at) "
                    "VALUES (:b,:p,'maison',:s,'particulier',now())"), {"b": bid, "p": prix, "s": surf})
    db.execute(text("INSERT INTO pige_annonces (bien_id,portail,url_sortante) VALUES (:b,'leboncoin',:u)"),
               {"b": bid, "u": f"https://leboncoin.fr/vf2a-{bid}"})
    return bid


def test_depot_du_soir_vu_le_lendemain():
    tag = uuid.uuid4().hex[:6]
    com = f"ZZVF2A-{tag}"
    biens: list[int] = []
    cid = None
    try:
        with session_scope() as db:
            digests._ensure_watermark(db)
            # pas de watermark pour ce job dans ce test → repli J-1 : hier soir EST dans la fenêtre.
            db.execute(text("DELETE FROM pige_watermark WHERE nom = :n"), {"n": digests._WATERMARK_RADAR})
            cid = _compte_actif(db, f"[VF2-A] {tag}", f"vf2a-{tag}@labuse.immo")
            veille.creer(db, compte_id=cid, criteria={"commune": com, "type_bien": "maison"})
            # 3 annonces déposées HIER SOIR dans la commune surveillée
            for i in range(3):
                biens.append(_bien_hier_soir(db, com, 300000 + i, 90 + i))
            db.commit()

            # AVANT le fix, _biens_du_jour() sans borne (aujourd'hui) ne les voit pas :
            duj = [b for b in digests._biens_du_jour(db) if b["commune"] == com]
            assert duj == [], "hier soir n'est pas 'du jour' (c'est justement le bug corrigé)"

            # radar-cloche (fenêtre « depuis le dernier passage », repli J-1) → les 3 annonces remontent
            r = digests.evaluer_radar_cloche(db)
            assert r["radar"] == 3, f"les 3 dépôts du soir doivent remonter, obtenu {r}"
            n = db.execute(text("SELECT count(*) FROM event_log WHERE compte_id=:c AND kind='radar'"),
                           {"c": cid}).scalar()
            assert n == 3

            # un 2ᵉ passage immédiat ne recrée rien (watermark avancé + dédup)
            r2 = digests.evaluer_radar_cloche(db)
            assert r2["radar"] == 0, "le watermark a avancé : rien de neuf au 2ᵉ passage"
    finally:
        with session_scope() as db:
            if biens:
                db.execute(text("DELETE FROM pige_biens WHERE bien_id = ANY(:b)"), {"b": biens})
            if cid:
                db.execute(text("DELETE FROM event_log WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM veilles WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM utilisateurs WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM comptes WHERE id=:c"), {"c": cid})
            db.execute(text("DELETE FROM pige_watermark WHERE nom=:n"), {"n": digests._WATERMARK_RADAR})
            db.commit()
