"""VEILLE-FIX-2 · Lot E — le rendu réel des mails de la grille (garde-fous).

Trois vérités que les captures dry-run ont mises au jour :
  · le mail IMMÉDIAT de mise en vente porte bien SON CORPS (pas son sujet recopié) ;
  · le digest ne parle plus de « secteurs » (archivés depuis VEILLE-2 Lot 4) ;
  · la grille du digest sort dans un ORDRE stable : parcelle suivie, puis Radar
    (nouvelle → baisse → retrait).

Les deux premiers sont des fonctions pures (aucune base). Le troisième joue une grille réelle
dry-run, [VF2-E] purgé en fin — aucun client réel touché.
"""
from __future__ import annotations

import datetime as _dt
import uuid

import pytest
from sqlalchemy import text

from labuse import emails


# ── fonctions pures ──────────────────────────────────────────────────────────
def test_mise_en_vente_mail_porte_son_corps_pas_son_sujet():
    """Régression : annonce_email retourne (sujet, corps) — mise_en_vente_email doit garder le CORPS."""
    sujet, txt, html = emails.mise_en_vente_email(
        "CY0018", "Saint-Paul", "Maison", "350 000 €",
        lien="https://leboncoin.fr/x", lien_desabo="https://d", lien_prefs="https://p")
    assert sujet == "LABUSE — votre parcelle CY0018 est mise en vente"
    # le corps texte n'est PAS le sujet recopié : il contient la phrase d'annonce et le lien.
    assert txt.strip() != sujet
    assert "Une annonce vient de paraître" in txt
    assert "CY0018" in txt and "Saint-Paul" in txt and "350 000 €" in txt
    assert "https://leboncoin.fr/x" in txt
    assert txt.lstrip().startswith("Bonjour")
    # le HTML dit la même chose.
    assert "Une annonce vient de paraître" in html


def test_digest_ne_parle_plus_de_secteurs():
    """VEILLE-FIX-2 : secteurs archivés — ni l'intro ni le pied ne les mentionnent."""
    evs = [{"kind": "parcelle_suivie", "titre": "Vente : votre parcelle CY0018 a changé de mains",
            "detail": "Mutation du 2025-12-31", "idu": "97415000CY0018"}]
    sujet, corps = emails.digest_notifications(
        evs, "https://d", periode="hier", base_url="https://app.labuse.immo",
        marche={"total": 0}, lien_prefs="https://p", secteurs_ligne="")
    assert "secteur" not in corps.lower()
    assert "parcelles suivies et vos critères" in corps
    assert "surveillez des critères Radar" in corps


# ── ordre de la grille (base réelle, dry-run, purgé) ─────────────────────────
pytestmark_db = pytest.mark.db


@pytest.mark.db
def test_grille_digest_ordre_stable():
    """parcelle suivie d'abord, puis Radar : nouvelle → baisse → retrait."""
    from labuse.db import session_scope
    from labuse.pige import digests, veille
    from labuse.api import events as ev

    tag = uuid.uuid4().hex[:6]
    com = f"ZZVF2E-{tag}"
    idu = f"97415000CY{tag[:4].upper()}"[:14]
    cid = None
    biens = []
    try:
        with session_scope() as db:
            digests._ensure_watermark(db)
            db.execute(text("DELETE FROM pige_watermark WHERE nom=:n"), {"n": digests._WATERMARK_RADAR})
            cid = db.execute(text("INSERT INTO comptes (nom, plan, founding, statut, sieges) "
                                  "VALUES (:n,'integral',false,'actif',1) RETURNING id"),
                             {"n": f"[VF2-E] {tag}"}).scalar()
            db.execute(text("INSERT INTO utilisateurs (compte_id, email, role, statut, echecs_login) "
                            "VALUES (:c,:e,'titulaire','actif',0)"), {"c": cid, "e": f"e{tag}@vf2e.test"})
            ev.set_digest_freq(db, cid, "quotidien")
            # parcelle suivie qui vient d'être vendue — l'événement majeur de la grille (créé
            # directement : la base de test n'a pas les mutations DVF réelles).
            ev.creer_notification(db, kind="parcelle_suivie", compte_id=cid, source="Mutation", idu=idu,
                                  titre=f"Vente : votre parcelle {idu[8:]} a changé de mains",
                                  detail="Mutation du 2025-12-31 — 2 300 000 € (Vente).",
                                  lien=f"/socle/#parcelle={idu}", dedup=f"suivi:mut:{idu}:{tag}")
            veille.creer(db, compte_id=cid, criteria={"commune": com, "type_bien": "maison"})

            def _bien(commune, statut="active", bidu=None, retiree=False, prix=350000):
                bid = db.execute(text(
                    "INSERT INTO pige_biens (commune,type_bien,est_copro,statut,a_qualifier,idu,"
                    "date_premiere_saisie,retiree_le) VALUES (:c,'maison',false,:s,false,:i, now(), :r) "
                    "RETURNING bien_id"),
                    {"c": commune, "s": statut, "i": bidu,
                     "r": _dt.datetime.now(_dt.timezone.utc) if retiree else None}).scalar()
                db.execute(text("INSERT INTO pige_faits (bien_id,prix,type_bien,surface_hab,particulier_pro,valide_at) "
                                "VALUES (:b,:p,'maison',95,'particulier',now())"), {"b": bid, "p": prix})
                db.execute(text("INSERT INTO pige_annonces (bien_id,portail,url_sortante) VALUES (:b,'leboncoin',:u)"),
                           {"b": bid, "u": f"https://leboncoin.fr/vf2e-{bid}"})
                return bid

            biens.append(_bien(com))
            bb = _bien(com, prix=320000); biens.append(bb)
            db.execute(text("INSERT INTO pige_prix_historique (bien_id,ancien_prix,nouveau_prix,date_constat) "
                            "VALUES (:b,360000,320000, now())"), {"b": bb})
            biens.append(_bien(com, statut="retiree", retiree=True))
            db.commit()

            digests.evaluer_radar_cloche(db)
            evs = [e for e in ev._digest_data(db, cid, jours=1)["evenements"] if not e.get("demo")]
            ordre = [e["kind"] for e in evs]
            # la parcelle suivie ouvre la grille ; les Radar suivent, baisse avant retrait.
            assert ordre and ordre[0] == "parcelle_suivie", ordre
            i_new = ordre.index("radar")
            i_baisse = ordre.index("radar_baisse")
            i_retrait = ordre.index("radar_retrait")
            assert i_new < i_baisse < i_retrait, ordre
    finally:
        with session_scope() as db:
            if biens:
                db.execute(text("DELETE FROM pige_biens WHERE bien_id = ANY(:b)"), {"b": biens})
            if cid:
                db.execute(text("DELETE FROM mail_queue WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM event_log WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM veilles WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM watched_parcels WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM notif_prefs WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM utilisateurs WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM comptes WHERE id=:c"), {"c": cid})
            db.execute(text("DELETE FROM pige_watermark WHERE nom=:n"), {"n": digests._WATERMARK_RADAR})
            db.commit()
