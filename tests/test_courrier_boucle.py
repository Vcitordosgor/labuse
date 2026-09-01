"""CONNEXIONS-2 Lot 4 (KO-6) — la boucle commerciale se ferme : retenue → piste → courrier →
réponse → statut, sans ressaisie, et chaque étape relue partout.

Ce test suit la chaîne au niveau donnée (le cœur de la boucle) :
  1. une piste CRM existe (pipeline_entries) ;
  2. un courrier est demandé RATTACHÉ à la piste (pipeline_entry_id) — sans ressaisie ;
  3. le statut du courrier est RELU par piste (carte Kanban / Mes courriers) ;
  4. LABUSE fait avancer le statut (demande → depose → envoye), vocabulaire UNIQUE ;
  5. la CLIENTE saisit le RETOUR (repondu) — scopé à son compte ;
  6. le KPI dashboard agrège par bucket (à déposer / en cours / clos).

Échoue sur l'ancien code : pas de FK courrier↔piste, « répondu » inexistant, statuts disjoints.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import courrier
from labuse.scoring.score_v_constants import Q_A_RUN_LABEL  # noqa: F401 — cohérence d'import projet


_WKT = "POLYGON((55.47 -20.93,55.471 -20.93,55.471 -20.931,55.47 -20.931,55.47 -20.93))"


def _seed_parcelle(s, idu):
    return s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'Saint-Paul','ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 1000, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": _WKT}).scalar()


@pytest.mark.db
def test_boucle_piste_courrier_reponse(db_session, engine):
    s = db_session
    courrier.ensure_tables(engine)
    idu = "97415000CB0001"
    pid = _seed_parcelle(s, idu)
    # 1) une piste CRM (compte 4242)
    pe_id = s.execute(text(
        "INSERT INTO pipeline_entries (parcel_id, compte_id, status, priority) "
        "VALUES (:p, 4242, 'a_qualifier', 'moyenne') RETURNING id"), {"p": pid}).scalar()

    # 2) courrier demandé RATTACHÉ à la piste (pas de ressaisie : l'IDU vient de la piste)
    d = courrier.creer_demande(s, compte_id=4242, parcelles=[idu], communes="Saint-Paul ×1",
                               modele="standard", corps="Bonjour, au sujet de votre parcelle…",
                               pipeline_entry_id=pe_id, projet_id=None)
    assert d["existing"] is False
    did = d["id"]

    # 3) le statut est RELU PAR PISTE (carte Kanban / Mes courriers)
    m = courrier.statut_par_pipeline_entry(s, 4242, [pe_id])
    assert m[pe_id]["statut"] == "demande" and m[pe_id]["libelle"] == "Demandé"

    # 4) LABUSE fait avancer : demande → depose → envoye (vocabulaire unique ; legacy normalisé)
    assert courrier.set_statut_demande(s, did, "depose")["statut"] == "depose"
    assert courrier.set_statut_demande(s, did, "poste")["statut"] == "envoye"   # alias legacy → envoye

    # 5) la CLIENTE saisit le RETOUR — scopé compte + réservé aux statuts de retour
    with pytest.raises(ValueError):   # un autre compte ne touche pas cette demande
        courrier.set_statut_demande(s, did, "repondu", compte_id=9999, reserve_retour=True)
    with pytest.raises(ValueError):   # depuis le CRM, seuls repondu/sans_reponse sont permis
        courrier.set_statut_demande(s, did, "depose", compte_id=4242, reserve_retour=True)
    r = courrier.set_statut_demande(s, did, "repondu", compte_id=4242, reserve_retour=True)
    assert r["statut"] == "repondu"

    # le statut relu par piste suit
    assert courrier.statut_par_pipeline_entry(s, 4242, [pe_id])[pe_id]["statut"] == "repondu"

    # 6) KPI dashboard : cette demande est CLOSE (répondu), plus « à déposer »
    kpi = courrier.kpi_dashboard(s)
    assert kpi["clos"] >= 1


@pytest.mark.db
def test_backfill_rattache_par_idu_compte_univoque(db_session, engine):
    """Le backfill rattache une demande héritée (sans pipeline_entry_id) quand l'IDU+compte est
    univoque, et laisse NULL quand c'est ambigu (≥2 pistes)."""
    s = db_session
    courrier.ensure_tables(engine)
    idu = "97415000CB0002"
    pid = _seed_parcelle(s, idu)
    pe_id = s.execute(text(
        "INSERT INTO pipeline_entries (parcel_id, compte_id, status, priority) "
        "VALUES (:p, 4243, 'a_qualifier', 'moyenne') RETURNING id"), {"p": pid}).scalar()
    # demande héritée : pipeline_entry_id NULL
    did = s.execute(text(
        "INSERT INTO courrier_demandes (compte_id, parcelles, n, communes, modele, corps, statut) "
        "VALUES (4243, cast(:p AS jsonb), 1, 'Saint-Paul', 'standard', 'corps', 'demande') RETURNING id"),
        {"p": f'["{idu}"]'}).scalar()
    # une DEUXIÈME demande MULTI-IDU (n≥2) est AMBIGUË par construction → NON rattachée (laissée NULL)
    idu2 = "97415000CB0009"
    _seed_parcelle(s, idu2)
    did2 = s.execute(text(
        "INSERT INTO courrier_demandes (compte_id, parcelles, n, communes, modele, corps, statut) "
        "VALUES (4243, cast(:p AS jsonb), 2, 'Saint-Paul', 'standard', 'corps2', 'demande') RETURNING id"),
        {"p": f'["{idu}", "{idu2}"]'}).scalar()
    # backfill sur LA MÊME session (transaction du test, rollback en fin)
    from labuse.courrier import backfill_rattachement_exec
    assert backfill_rattachement_exec(s) >= 1
    # la demande mono-IDU est rattachée (univoque), la multi-IDU reste NULL
    assert s.execute(text("SELECT pipeline_entry_id FROM courrier_demandes WHERE id = :i"), {"i": did}).scalar() == pe_id
    assert s.execute(text("SELECT pipeline_entry_id FROM courrier_demandes WHERE id = :i"), {"i": did2}).scalar() is None
