"""VEILLE-AUDIT-2 — harness lecture-seule (objets [VEILLE-AUDIT-2] purgés en fin).
Trace les 4 témoins de bout en bout sur la base RÉELLE, transport neutralisé (dry_run).
Aucun mail réel. Rien de permanent : tout est purgé au finally.
"""
import json, sys, datetime as dt
from sqlalchemy import text
from sqlalchemy.orm import Session
from labuse.db import engine
from labuse.api import events as ev
from labuse.pige import veille as veille_mod
from labuse.pige import digests as dg

CAP = "/Users/openclaw/Desktop/labuse-veille/docs/audit-2026-09/captures/veille-audit2"
MARK = "[VEILLE-AUDIT-2]"
EMAIL = "kampusreunion+va2@gmail.com"   # adresse de Vic (dry-run : rien ne part)
out = {}

eng = engine()
db = Session(bind=eng)
cid = None
bien_id = None
try:
    ev.ensure_tables(eng)
    # ── SETUP : compte actif de test + titulaire + notif_prefs ──────────────────
    cid = db.execute(text(
        "INSERT INTO comptes (nom, plan, statut) VALUES (:n,'pro','actif') RETURNING id"),
        {"n": MARK + " compte de test"}).scalar()
    db.execute(text("INSERT INTO utilisateurs (compte_id, email, role) VALUES (:c,:e,'titulaire')"),
               {"c": cid, "e": EMAIL})
    db.execute(text("INSERT INTO notif_prefs (compte_id, digest_freq) VALUES (:c,'hebdo') "
                    "ON CONFLICT (compte_id) DO NOTHING"), {"c": cid})
    db.commit()
    out["compte_test"] = {"id": cid, "email": EMAIL, "statut": "actif", "digest_freq": "hebdo"}

    # ── T1 : parcelles suivies ──────────────────────────────────────────────────
    # CY0018 = vente DVF réelle 2025-12-31 (2,3 M€) ; BZ1065 = suivie mais SANS événement DVF.
    for idu in ("97415000CY0018", "97411000BZ1065"):
        db.execute(text("INSERT INTO watched_parcels (compte_id, idu, created_at) "
                        "VALUES (:c,:i,'2025-01-01') ON CONFLICT DO NOTHING"),
                   {"c": cid, "i": idu})
    db.commit()
    r1 = ev.evaluer_suivis(db)
    out["T1_evaluer_suivis_compteurs"] = r1
    ev1 = db.execute(text("SELECT id, kind, idu, titre, detail, lien, lu, source FROM event_log "
                          "WHERE compte_id=:c ORDER BY id"), {"c": cid}).mappings().all()
    out["T1_events"] = [dict(x) for x in ev1]
    out["T1_BZ1065_a_un_evenement"] = any(x["idu"] == "97411000BZ1065" for x in ev1)

    # ── T2 : Radar par critères ─────────────────────────────────────────────────
    # (a) bien de test daté AUJOURD'HUI (Saint-Pierre, maison, 350k, 90 m² hab, particulier)
    bien_id = db.execute(text(
        "INSERT INTO pige_biens (commune, type_bien, est_copro, statut, a_qualifier, date_premiere_saisie) "
        "VALUES ('Saint-Pierre','maison',false,'active',false, now()) RETURNING bien_id")).scalar()
    db.execute(text("INSERT INTO pige_faits (bien_id, prix, surface_hab, particulier_pro, valide_at) "
                    "VALUES (:b, 350000, 90, 'particulier', now())"), {"b": bien_id})
    db.execute(text("INSERT INTO pige_annonces (bien_id, portail, url_sortante, date_saisie, list_id, statut_portail) "
                    "VALUES (:b,'leboncoin',:u, now(), :lid,'active')"),
               {"b": bien_id, "u": f"https://test.va2/{bien_id}", "lid": 990000000 + bien_id})
    db.commit()
    # veille QUI MATCHE + veille QUI NE MATCHE PAS
    v_match = veille_mod.creer(db, compte_id=cid,
                               criteria={"communes": ["Saint-Pierre"], "type_bien": "maison", "prix_max": 400000})
    v_nomatch = veille_mod.creer(db, compte_id=cid,
                                 criteria={"communes": ["Saint-Pierre"], "type_bien": "terrain"})
    db.commit()
    # _biens_du_jour : combien AUJOURD'HUI vs le dépôt réel d'hier
    bdj = dg._biens_du_jour(db)
    out["T2_biens_du_jour_count"] = len(bdj)
    out["T2_biens_du_jour_dont_test"] = any(b["bien_id"] == bien_id for b in bdj)
    reels_hier = db.execute(text(
        "SELECT count(*) FROM pige_biens WHERE date_premiere_saisie::date = current_date - 1")).scalar()
    out["T2_biens_reels_hier_26"] = reels_hier
    # matche() direct (contrat) sur le bien de test
    b_test = next((b for b in bdj if b["bien_id"] == bien_id), None)
    out["T2_matche_veille_match"] = veille_mod.matche(
        {"communes": ["Saint-Pierre"], "type_bien": "maison", "prix_max": 400000}, b_test) if b_test else None
    out["T2_matche_veille_nomatch"] = veille_mod.matche(
        {"communes": ["Saint-Pierre"], "type_bien": "terrain"}, b_test) if b_test else None
    # radar-cloche (job réel)
    rc = dg.evaluer_radar_cloche(db)
    out["T2_radar_cloche_compteur"] = rc
    ev_radar = db.execute(text("SELECT id, kind, titre, detail, lien FROM event_log "
                               "WHERE compte_id=:c AND kind='radar' ORDER BY id"), {"c": cid}).mappings().all()
    out["T2_radar_events"] = [dict(x) for x in ev_radar]

    # ── T3 : retrait / baisse de prix ───────────────────────────────────────────
    # baisse de prix sur le bien de test → journal pige.baisse_prix (compte NULL) ? événement client ?
    db.execute(text("INSERT INTO pige_prix_historique (bien_id, ancien_prix, nouveau_prix, date_constat) "
                    "VALUES (:b, 380000, 350000, now())"), {"b": bien_id})
    db.commit()
    out["T3_pige_baisse_events_compte_null"] = db.execute(text(
        "SELECT count(*) FROM event_log WHERE kind LIKE 'pige.%' AND compte_id IS NOT NULL")).scalar()
    out["T3_kinds_pige_visibles_client"] = db.execute(text(
        "SELECT DISTINCT kind FROM event_log WHERE kind LIKE 'pige.%'")).scalars().all()
    # une annonce retirée reste-t-elle candidate au radar-cloche ? (statut IN active/en_vente_longue)
    out["T3_retiree_dans_biens_du_jour"] = "non (statut IN active/en_vente_longue seulement, digests.py:75)"

    # ── T4 : bascule / nouvelle source ──────────────────────────────────────────
    out["T4_bascule_compte_id"] = db.execute(text(
        "SELECT DISTINCT compte_id FROM event_log WHERE kind='bascule' LIMIT 3")).scalars().all()
    out["T4_systeme_compte_id"] = db.execute(text(
        "SELECT DISTINCT compte_id FROM event_log WHERE kind='systeme' LIMIT 3")).scalars().all()

    # ── CLOCHE (payload) : ce que le compte de test voit ────────────────────────
    cloche = db.execute(text(
        "SELECT id, kind, titre, detail, lien, lu FROM event_log WHERE compte_id=:c ORDER BY id"),
        {"c": cid}).mappings().all()
    out["CLOCHE_compte_test"] = [dict(x) for x in cloche]

    # ── DIGEST dry-run (T1 + T2) ────────────────────────────────────────────────
    rd = ev.envoyer_digests(db, base_url="https://app.labuse.immo", freq="quotidien",
                            force=True, dry_run=True)
    mine = [d for d in rd.get("details", []) if d.get("compte") == cid]
    out["T4b_digest_rapport_global"] = {k: rd.get(k) for k in ("envoyes", "ignores", "echecs", "simules")}
    out["DIGEST_compte_test"] = mine
    # ligne mail_queue écrite (dry-run = en_attente, rien envoyé)
    mq = db.execute(text("SELECT id, mail_key, template_id, template_nom, destinataire, etat, prevu_at, dedup "
                         "FROM mail_queue WHERE compte_id=:c ORDER BY id"), {"c": cid}).mappings().all()
    out["MAIL_QUEUE_compte_test"] = [dict(x) for x in mq]
    # rendre le HTML du digest (aperçu réel) pour la pièce jointe §4
    evs = [e for e in ev._digest_data(db, cid, jours=1)["evenements"]
           if not e.get("demo")]
    if evs:
        tok = ev._notif_token(db, cid)
        ld = f"https://app.labuse.immo/events/desabonner?c={cid}&t={tok}"
        lp = f"https://app.labuse.immo/events/preferences?c={cid}&t={tok}"
        from labuse.emails import digest_html_email, digest_notifications
        sujet, corps = digest_notifications(evs, ld, base_url="https://app.labuse.immo",
                                            marche={"total": 0}, periode="hier", lien_prefs=lp, secteurs_ligne="")
        html = digest_html_email(evs, {"total": 0}, [], ld, lp, base_url="https://app.labuse.immo",
                                 periode="hier", secteurs_ligne="")
        out["DIGEST_sujet"] = sujet
        with open(f"{CAP}/digest-compte-test.html", "w") as f:
            f.write(html)
        with open(f"{CAP}/digest-compte-test.txt", "w") as f:
            f.write(sujet + "\n\n" + corps)

finally:
    # ── PURGE totale ────────────────────────────────────────────────────────────
    try:
        if cid is not None:
            db.execute(text("DELETE FROM mail_queue WHERE compte_id=:c"), {"c": cid})
            db.execute(text("DELETE FROM event_log WHERE compte_id=:c"), {"c": cid})
            db.execute(text("DELETE FROM veilles WHERE compte_id=:c"), {"c": cid})
            db.execute(text("DELETE FROM watched_parcels WHERE compte_id=:c"), {"c": cid})
            db.execute(text("DELETE FROM notif_prefs WHERE compte_id=:c"), {"c": cid})
            db.execute(text("DELETE FROM utilisateurs WHERE compte_id=:c"), {"c": cid})
        if bien_id is not None:
            db.execute(text("DELETE FROM pige_biens WHERE bien_id=:b"), {"b": bien_id})  # cascade faits/annonces/histo
        if cid is not None:
            db.execute(text("DELETE FROM comptes WHERE id=:c"), {"c": cid})
        db.commit()
        out["PURGE"] = "ok"
    except Exception as e:
        db.rollback()
        out["PURGE"] = f"ERREUR: {e}"
    with open(f"{CAP}/temoins.json", "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False, default=str)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    db.close()
