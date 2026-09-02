"""FLUX-1 — la page « Flux » : matrice exécutable, compteurs Radar, garde de cohérence, bascule.

On sème un minimum (une source + sa veille, quelques biens Radar + une vente DVF) et on gèle :
la fourmilière est bien câblée depuis les métadonnées, les compteurs Radar comptent juste, l'écart
demandé/acté sort par type, la garde de cohérence rend une structure exploitable, et les briques de
bascule (purge des caches A6, refus d'un run incomplet, journal) tiennent. On NE bascule JAMAIS pour
de vrai (ça réécrirait config/served_run.txt) — seules les briques pures/lecture sont exercées.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from labuse import bascule_flux, coherence_flux, flux
from labuse.pige import releves

pytestmark = pytest.mark.db


@pytest.fixture
def seed_source(db_session):
    """Une source DVF affichée + sa veille en « nouvelle_version » (donc orange)."""
    tag = uuid.uuid4().hex[:6]
    nom = f"DVF / valeurs foncières {tag}"
    sid = db_session.execute(text(
        "INSERT INTO data_sources (name, provider, category, status, source_millesime) "
        "VALUES (:n, 'DGFiP', 'marche', 'connecte', '2025-S2') RETURNING id"), {"n": nom}).scalar()
    db_session.execute(text(
        "INSERT INTO source_veille (source_id, methode, dernier_statut, dernier_vu, actif) "
        "VALUES (:i, 'api', 'nouvelle_version', '2026-S1', true)"), {"i": sid})
    return {"id": sid, "name": nom}


def test_fourmiliere_cablee_depuis_metadonnees(db_session, seed_source):
    d = flux.construire_flux(db_session)
    assert set(d) >= {"run", "sources", "moteurs", "surfaces", "comptes", "plus_recentes"}
    # la source DVF est présente, orange (nouvelle_version), et câblée aux bons moteurs
    src = next(s for s in d["sources"] if s["id"] == seed_source["id"])
    assert src["dot"] == "warn" and src["fournisseur"] == "DGFiP"
    assert "sector_price" in src["moteurs"] and "scoring" in src["moteurs"]
    # les moteurs qu'elle alimente la citent en retour (arête bidirectionnelle)
    sp = next(m for m in d["moteurs"] if m["key"] == "sector_price")
    assert seed_source["id"] in sp["sources"]
    # comptage : au moins une nouvelle version détectée
    assert d["comptes"]["nouvelle_version"] >= 1
    # les 15 outils + 6 écrans/exports sont là (17 surfaces run-scopées visibles au minimum)
    assert len(d["surfaces"]) == 21
    assert any(s["key"] == "scoreur-adresse" for s in d["surfaces"])


def test_snapshot_source_millesimes(db_session, seed_source):
    snap = flux.snapshot_source_millesimes(db_session)
    ligne = next(x for x in snap if x["source_id"] == seed_source["id"])
    assert ligne["millesime"] == "2025-S2" and ligne["fournisseur"] == "DGFiP"


def test_circuit_rend_forme_complete(db_session, seed_source):
    """RETOURS-8 (R4.2) — /admin/flux rend TOUJOURS la forme complète (flux/radar/coherence/bascule)
    que le Circuit attend — le nerf de « Chargement… » (une brique manquante bloquait la page).

    RETOURS-9 (Q1) — la charge initiale ne porte PLUS les runs terminés (calcul d'écart ~50 s en
    base réelle → « Chargement… » interminable). `bascule` ne garde que `derniere` (rapide) ; les
    runs arrivent en rendu progressif via /admin/flux/runs (test dédié ci-dessous)."""
    import types
    from labuse.api import auth, dashboard
    _prev = auth.exiger_admin
    auth.exiger_admin = lambda req: None
    try:
        out = dashboard.admin_flux(types.SimpleNamespace(state=types.SimpleNamespace(compte_id=None)))
    finally:
        auth.exiger_admin = _prev
    assert set(out) >= {"flux", "radar", "coherence", "bascule"}
    assert set(out["flux"]) >= {"run", "sources", "moteurs", "surfaces", "comptes"}
    assert set(out["radar"]) >= {"compteurs", "ecart", "courbe"}
    # Q1 — les runs sont SORTIS de la charge initiale (rendu progressif) ; seul `derniere` reste.
    assert "derniere" in out["bascule"] and "runs" not in out["bascule"]


def test_admin_flux_runs_progressif_et_ecart_borne(db_session, seed_source, monkeypatch):
    """RETOURS-9 (Q1) — les runs terminés + écarts sont servis par /admin/flux/runs (2e requête,
    rendu progressif). L'écart (COÛTEUX : `comparer()` + COUNT self-join sur parcel_p_score_v2)
    n'est calculé QUE pour les `limit_ecart` premiers runs non-servis — ceux que la page montre —
    jamais pour tous. Sur la base réelle de Vic cela ramène ~50 s à ~6 s pour le Circuit."""
    import types
    from labuse import bascule_flux
    from labuse.api import auth, dashboard
    # on compte les appels à comparer() : ils doivent être bornés par limit_ecart, pas illimités
    appels = {"n": 0}
    _vrai = bascule_flux.comparer if hasattr(bascule_flux, "comparer") else None
    from labuse import golden_ops
    def _compte(lab):
        appels["n"] += 1
        return {"ok": False}
    monkeypatch.setattr(golden_ops, "comparer", _compte)
    monkeypatch.setattr(auth, "exiger_admin", lambda req: None)
    out = dashboard.admin_flux_runs(types.SimpleNamespace(state=types.SimpleNamespace(compte_id=None)))
    assert "runs" in out and "derniere" in out
    # borne : jamais plus d'appels à comparer() que le plafond (4 par défaut), quel que soit le nb de runs
    assert appels["n"] <= 4
    _ = _vrai


def test_circuit_degrade_si_une_brique_casse(db_session, seed_source, monkeypatch):
    """R4.2 — si UNE brique lève (ici le radar), l'endpoint ne tombe plus : il sert un repli typé
    valide + une note d'erreur, et la page rend au lieu de rester bloquée sur « Chargement… »."""
    import types
    from labuse.api import auth, dashboard
    from labuse.pige import releves as _rel
    def _boom(_s):
        raise RuntimeError("radar cassé (test)")
    monkeypatch.setattr(_rel, "bloc_radar", _boom)
    monkeypatch.setattr(auth, "exiger_admin", lambda req: None)
    out = dashboard.admin_flux(types.SimpleNamespace(state=types.SimpleNamespace(compte_id=None)))
    assert set(out) >= {"flux", "radar", "coherence", "bascule"}      # forme complète malgré la panne
    assert out["radar"]["compteurs"] == {} and out["radar"]["ecart"] == []   # repli typé
    assert out["erreurs"] and any("radar" in e for e in out["erreurs"])      # et ça le DIT


@pytest.fixture
def seed_radar(db_session):
    """Deux biens Radar : un vendu (paire annonce↔DVF, avec prix demandé + acté) + un actif rattaché."""
    tag = uuid.uuid4().hex[:4].upper()
    idu = f"97415{tag}0001"[:14].ljust(14, "0")
    b1 = db_session.execute(text(
        "INSERT INTO pige_biens (commune, type_bien, idu, rattachement_niveau, statut, "
        " vendue_le, vendue_valeur, date_publication) "
        "VALUES ('Saint-Paul', 'maison', :idu, 'source', 'vendue', :vl, 330000, :pub) RETURNING bien_id"),
        {"idu": idu, "vl": date.today() - timedelta(days=40), "pub": date.today() - timedelta(days=400)}).scalar()
    db_session.execute(text("INSERT INTO pige_faits (bien_id, prix, type_bien, valide_at) "
                            "VALUES (:b, 360000, 'maison', now())"), {"b": b1})
    db_session.execute(text("INSERT INTO pige_annonces (bien_id, portail, url_sortante) "
                            "VALUES (:b, 'leboncoin', :u)"), {"b": b1, "u": f"https://x/{tag}-1"})
    b2 = db_session.execute(text(
        "INSERT INTO pige_biens (commune, type_bien, idu, rattachement_niveau, statut) "
        "VALUES ('Saint-Denis', 'terrain', :idu, 'source', 'active') RETURNING bien_id"),
        {"idu": idu[:-1] + "2"}).scalar()
    db_session.execute(text("INSERT INTO pige_annonces (bien_id, portail, url_sortante) "
                            "VALUES (:b, 'seloger', :u)"), {"b": b2, "u": f"https://x/{tag}-2"})
    return {"b1": b1, "b2": b2}


def test_compteurs_radar(db_session, seed_radar):
    c = releves.compteurs(db_session)
    assert c["annonces"] >= 2
    assert c["rattachees"] >= 2          # les deux biens ont un idu
    assert c["paires"] >= 1              # un seul vendu
    assert c["communes"] >= 2 and c["communes_total"] == 24


def test_ecart_par_type_sur_paires(db_session, seed_radar):
    ecarts = releves.ecart_par_type(db_session)
    maison = next(e for e in ecarts if e["type"] == "maison")
    # (330000 acté − 360000 demandé) / 360000 = −8.3 %
    assert maison["ecart_pct"] is not None and maison["ecart_pct"] < 0
    assert maison["n"] >= 1 and maison["fragile"] is True   # 1 paire < seuil → fragile, jamais caché


def test_ecrire_releve_puis_courbe(db_session, seed_radar):
    r = releves.ecrire_releve(db_session)
    assert r["paires"] >= 1
    # idempotent : ré-écrire le même jour ne duplique pas (upsert)
    releves.ecrire_releve(db_session)
    n = db_session.execute(text("SELECT count(*) FROM radar_releves WHERE jour = :j"),
                           {"j": date.today()}).scalar()
    assert n == 1
    courbe = releves.courbe(db_session)
    assert courbe["depuis_le"] == date.today().isoformat()


def test_purger_caches_a6_ne_leve_jamais():
    purges = bascule_flux.purger_caches_run()
    # au moins le cache de config (yaml/settings) est recensé et purgé
    assert any("config" in p for p in purges)
    assert isinstance(purges, list)


def test_run_incomplet_refuse_la_bascule(db_session):
    ok, motif = bascule_flux._run_complet(db_session, "run_qui_nexiste_pas")
    assert ok is False and "absent" in motif.lower()


def test_journal_bascule_ensure_et_vide(engine, db_session):
    bascule_flux.ensure_tables(engine)
    assert bascule_flux.derniere_bascule(db_session) is None   # aucune bascule encore


def test_garde_coherence_structure(db_session):
    res = coherence_flux.verifier(db_session)
    assert set(res) >= {"ok", "checks", "n_surfaces"}
    libelles = [c["libelle"] for c in res["checks"]]
    assert any("run courant" in lib for lib in libelles)
    assert any("Date de valeur" in lib for lib in libelles)
    # base de test sans parcelle scorée : la garde reste applicable (non bloquante), jamais un crash
    assert all(isinstance(c["ok"], bool) for c in res["checks"])
