"""VEILLE-FIX-2 · Lot E — rend un DIGEST réel (dry-run) + le MAIL IMMÉDIAT de mise en vente.
Compte de test [VF2-E] (adresse de Vic), base réelle, transport neutralisé (dry_run), tout purgé.
Aucun client réel touché. Sortie : digest.html/.txt + mise-en-vente.html/.txt dans ce dossier.
"""
import datetime as dt
import json
from sqlalchemy import text
from sqlalchemy.orm import Session
from labuse.db import engine
from labuse.api import events as ev
from labuse.pige import digests, veille
from labuse import emails

CAP = "/Users/openclaw/Desktop/labuse-veillefix/docs/audit-2026-09/veille-fix-2/captures"
EMAIL = "kampusreunion+vf2e@gmail.com"
out = {}
eng = engine()
db = Session(bind=eng)
cid = None
biens = []
try:
    ev.ensure_tables(eng)
    from labuse.mailfile import ensure_tables as _mq
    _mq(eng)
    digests._ensure_watermark(db)
    db.execute(text("DELETE FROM pige_watermark WHERE nom=:n"), {"n": digests._WATERMARK_RADAR})
    cid = db.execute(text("INSERT INTO comptes (nom, plan, founding, statut, sieges) "
                          "VALUES ('[VF2-E] compte de test','integral',false,'actif',1) RETURNING id")).scalar()
    db.execute(text("INSERT INTO utilisateurs (compte_id, email, role, statut, echecs_login) "
                    "VALUES (:c,:e,'titulaire','actif',0)"), {"c": cid, "e": EMAIL})
    ev.set_digest_freq(db, cid, "quotidien")
    # T1 — parcelle suivie CY0018 (vente DVF réelle) → parcelle_suivie
    db.execute(text("INSERT INTO watched_parcels (compte_id, idu, created_at) VALUES (:c,'97415000CY0018','2025-01-01')"),
               {"c": cid})
    db.commit()
    ev.evaluer_suivis(db)
    # Radar — veille commune de test + 3 biens (nouvelle, baisse, retrait) + 1 mise en vente (idu suivi)
    com = "ZZVF2E"
    veille.creer(db, compte_id=cid, criteria={"commune": com, "type_bien": "maison"})

    def _bien(commune, statut="active", idu=None, retiree=False, prix=350000):
        bid = db.execute(text(
            "INSERT INTO pige_biens (commune,type_bien,est_copro,statut,a_qualifier,idu,date_premiere_saisie,retiree_le) "
            "VALUES (:c,'maison',false,:s,false,:i, now(), :r) RETURNING bien_id"),
            {"c": commune, "s": statut, "i": idu,
             "r": dt.datetime.now(dt.timezone.utc) if retiree else None}).scalar()
        db.execute(text("INSERT INTO pige_faits (bien_id,prix,type_bien,surface_hab,particulier_pro,valide_at) "
                        "VALUES (:b,:p,'maison',95,'particulier',now())"), {"b": bid, "p": prix})
        db.execute(text("INSERT INTO pige_annonces (bien_id,portail,url_sortante) VALUES (:b,'leboncoin',:u)"),
                   {"b": bid, "u": f"https://leboncoin.fr/vf2e-{bid}"})
        return bid

    b_new = _bien(com); biens.append(b_new)
    b_baisse = _bien(com, prix=320000); biens.append(b_baisse)
    db.execute(text("INSERT INTO pige_prix_historique (bien_id,ancien_prix,nouveau_prix,date_constat) "
                    "VALUES (:b,360000,320000, now())"), {"b": b_baisse})
    b_ret = _bien(com, statut="retiree", retiree=True); biens.append(b_ret)
    b_mev = _bien("ZZMEV-E", idu="97415000CY0018"); biens.append(b_mev)   # rattaché à la parcelle suivie
    db.commit()

    rc = digests.evaluer_radar_cloche(db)
    out["radar_cloche"] = rc

    # DIGEST dry-run (parcelle suivie + radar + baisse + retrait, dans l'ordre de la grille)
    r = ev.envoyer_digests(db, base_url="https://app.labuse.immo", freq="quotidien", force=True, dry_run=True)
    mine = next((d for d in r["details"] if d["compte"] == cid), None)
    out["digest_statut"] = mine
    evs = [e for e in ev._digest_data(db, cid, jours=1)["evenements"] if not e.get("demo")]
    tok = ev._notif_token(db, cid)
    ld = f"https://app.labuse.immo/events/desabonner?c={cid}&t={tok}"
    lp = f"https://app.labuse.immo/events/preferences?c={cid}&t={tok}"
    sujet, corps = emails.digest_notifications(evs, ld, base_url="https://app.labuse.immo",
                                               marche={"total": 0}, periode="hier", lien_prefs=lp, secteurs_ligne="")
    html = emails.digest_html_email(evs, {"total": 0}, [], ld, lp, base_url="https://app.labuse.immo",
                                    periode="hier", secteurs_ligne="")
    out["digest_sujet"] = sujet
    out["digest_ordre"] = [e["kind"] for e in evs]
    open(f"{CAP}/digest.txt", "w").write(sujet + "\n\n" + corps)
    open(f"{CAP}/digest.html", "w").write(html)

    # MAIL IMMÉDIAT de mise en vente (rendu du gabarit dédié)
    sujet2, txt2, html2 = emails.mise_en_vente_email("CY0018", "Saint-Paul", "Maison", "350 000 €",
                                                     lien="https://leboncoin.fr/vf2e-mev", lien_desabo=ld, lien_prefs=lp)
    out["mise_en_vente_sujet"] = sujet2
    open(f"{CAP}/mise-en-vente.txt", "w").write(sujet2 + "\n\n" + txt2)
    open(f"{CAP}/mise-en-vente.html", "w").write(html2)
    # trace mail_queue de la mise en vente (dry-run = en_attente, rien envoyé)
    out["mail_queue"] = [dict(x) for x in db.execute(text(
        "SELECT mail_key, etat FROM mail_queue WHERE compte_id=:c ORDER BY id"), {"c": cid}).mappings().all()]
finally:
    if cid is not None:
        db.execute(text("DELETE FROM mail_queue WHERE compte_id=:c"), {"c": cid})
        db.execute(text("DELETE FROM event_log WHERE compte_id=:c"), {"c": cid})
        db.execute(text("DELETE FROM veilles WHERE compte_id=:c"), {"c": cid})
        db.execute(text("DELETE FROM watched_parcels WHERE compte_id=:c"), {"c": cid})
        db.execute(text("DELETE FROM notif_prefs WHERE compte_id=:c"), {"c": cid})
        db.execute(text("DELETE FROM utilisateurs WHERE compte_id=:c"), {"c": cid})
    if biens:
        db.execute(text("DELETE FROM pige_biens WHERE bien_id = ANY(:b)"), {"b": biens})
    if cid is not None:
        db.execute(text("DELETE FROM comptes WHERE id=:c"), {"c": cid})
    db.execute(text("DELETE FROM pige_watermark WHERE nom=:n"), {"n": digests._WATERMARK_RADAR})
    db.commit()
    open(f"{CAP}/rendu.json", "w").write(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    db.close()
