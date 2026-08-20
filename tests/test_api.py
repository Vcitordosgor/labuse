"""Tests de l'API (TestClient) sur le jeu de démo Saint-Paul (PostGIS réel)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def client(engine):
    from labuse import models
    from labuse.ai import StubProvider
    from labuse.api.app import app
    from labuse.cascade import evaluate_parcels
    from labuse.db import session_scope
    from labuse.ingestion import demo_saint_paul, seed_sources
    from labuse.scoring.score_v_constants import Q_A_RUN_LABEL

    with session_scope() as s:
        seed_sources.seed(s)
        demo_saint_paul.seed_demo(s)
        ids = [r[0] for r in s.execute(select(models.Parcel.id)).all()]
        # LIVE (parcel_evaluations) — feedback terrain, pipeline CRM lisent le live.
        evaluate_parcels(ids, s, persist=True, ai_provider=StubProvider())
        # M91 (seed obsolète) : la fiche lit la cascade dans `dryrun_cascade_results` AU RUN SERVI
        # (app.py:3281, Q_A_RUN_LABEL) — table distincte du live. Sans cette seconde passe, `f["cascade"]`
        # était vide → `len(cascade) > 10` échouait. On matérialise donc AUSSI la cascade sous le run
        # servi pour que la fixture soit représentative (le verdict reste « non_evaluee » : le score v2
        # servi, parcel_p_score_v2, n'est pas peuplé par evaluate_parcels).
        evaluate_parcels(ids, s, persist=True, ai_provider=StubProvider(), dryrun_label=Q_A_RUN_LABEL)
    try:
        yield TestClient(app)
    finally:
        with session_scope() as s:
            demo_saint_paul.reset_demo(s)


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_sources_page(client):
    srcs = client.get("/sources").json()
    assert len(srcs) >= 24
    assert all("status" in s and "reliability_level" in s for s in srcs)
    assert any(s["testable"] for s in srcs)  # au moins un connecteur live


def test_source_test_sans_connecteur(client):
    """Une source sans connecteur live répond proprement (sans réseau).

    M71 BLOC A : /sources ne sert plus que status='connecte' — « Fichiers fonciers (Cerema) »
    (manuel) n'y figure plus. On prend n'importe quelle source SERVIE non testable : même
    intention, sans épingler un nom."""
    srcs = client.get("/sources").json()
    ff = next(s for s in srcs if not s["testable"])
    res = client.post(f"/sources/{ff['id']}/test").json()
    assert res["ok"] is False and "connecteur" in res["message"].lower()


def test_fiche_double_score_et_cascade(client):
    # M34 (dette #14) : le verdict est la TRADUCTION du tier servi. La parcelle de démo n'a
    # pas de ligne au run servi → « non évaluée au run servi », JAMAIS un repli legacy muet
    # (l'ancien verrou attendait le statut cascade « opportunite »).
    f = client.get("/parcels/97415000AB0001").json()
    assert f["verdict"]["status"] == "non_evaluee"
    assert f["verdict"]["label"] == "Non évaluée au run servi"
    # Règle d'or : les DEUX scores (legacy, informatifs) restent présents
    assert f["verdict"]["opportunity_score"] is not None
    assert f["verdict"]["completeness_score"] is not None
    assert len(f["cascade"]) > 10
    assert f["sources_responded"] and f["ai"]["recommended_status"] == "opportunite"
    assert "jamais garanties" in f["disclaimer"]


def test_fiche_verdict_traduit_le_tier_servi(client):
    # Avec une ligne v2 au run servi, le verdict de fiche EST le tier (traduction unique).
    from sqlalchemy import text as sqla_text

    from labuse.db import session_scope
    from labuse.scoring.score_v_constants import Q_A_RUN_LABEL
    with session_scope() as s:
        s.execute(sqla_text(
            "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, "
            "rang, contrib_z, contrib_d, copro, tier, model_version) "
            "VALUES (:r, '97415000AB0001', 0.9, 2.0, 99, 7, 0, 0, false, 'brulante', 'm34-test') "
            "ON CONFLICT (run_id, parcelle_id) DO UPDATE SET tier = 'brulante', rang = 7"),
            {"r": Q_A_RUN_LABEL})
    try:
        f = client.get("/parcels/97415000AB0001").json()
        assert f["verdict"]["status"] == "brulante"
        assert f["verdict"]["label"] == "Priorité" and f["verdict"]["rang"] == 7   # M137 — chip court servi
        assert f["resume"]["statut"] == "brulante"
        assert f["resume"]["synthese"].startswith("Classée Priorité")
    finally:
        with session_scope() as s:
            s.execute(sqla_text(
                "DELETE FROM parcel_p_score_v2 WHERE run_id = :r AND parcelle_id = '97415000AB0001'"),
                {"r": Q_A_RUN_LABEL})


def test_fiche_404(client):
    assert client.get("/parcels/00000000000000").status_code == 404


def test_idu_malforme_404_jamais_500(client):
    # Audit O5 : un octet nul / caractère de contrôle dans l'IDU provoquait un 500 driver.
    for bad in ("%00", "a b", "x" * 25, "..%2F..", "AB-0001"):
        r = client.get(f"/parcels/{bad}")
        assert r.status_code == 404, f"{bad!r} → {r.status_code}"
    assert client.get("/parcels/%00/enrichment").status_code == 404
    assert client.get("/pipeline/parcel/%00").status_code == 404
    assert client.post("/feedback", json={"idu": "\x00", "verdict": "good_lead"}).status_code == 404


def test_demo_endpoint(client):
    # Phase 3 — panneau « Démo guidée » : structure stable, 8 parcelles, pas de 500.
    d = client.get("/demo").json()
    assert {"commune", "parcels", "all_conform"} <= set(d)
    ps = d["parcels"]
    # R1 : la vitrine est désormais BK0023 (VACANTE) ; BP0571 (résidence) attendue en faux positif.
    # M37 : les verdicts démo sont les TIERS SERVIS (rail legacy éteint). BK0023 est servie
    # à creuser, BP0571 (résidence) écartée — ce que voit le client.
    assert len(ps) == 8 and ps[0]["idu"] == "97415000BK0023" and ps[0]["attendu"] == "a_creuser"
    bp = next(p for p in ps if p["idu"] == "97415000BP0571")
    assert bp["attendu"] == "ecartee"
    assert {"ordre", "role", "status", "conforme", "present"} <= set(ps[0])


def test_fiche_core_sans_bloc_promoteur_lazy(client):
    # Phase 1 — la fiche « core » s'ouvre SANS le bloc promoteur (appels externes lents) :
    # il est servi à part en lazy-load. Tout le reste (verdict/scores/cascade/prospection) reste là.
    f = client.get("/parcels/97415000AB0001").json()
    assert "promoteur" not in f
    assert f["verdict"]["status"] and len(f["cascade"]) > 10 and "prospection" in f
    # Correctif R1 : bloc « Occupation » toujours présent — ici couche absente → honnêteté.
    assert f["bati"]["disponible"] is False and "non vérifiée" in f["bati"]["label"]


def test_enrichment_endpoint_lazy(client):
    # Le bloc promoteur a son endpoint dédié : 200, sections présentes, computed_at, jamais 500.
    e = client.get("/parcels/97415000AB0001/enrichment")
    assert e.status_code == 200
    js = e.json()
    assert {"altimetrie", "facade", "plu_detail", "proprietaire", "reseaux"} <= set(js)
    assert "computed_at" in js
    # En test LABUSE_ENRICH_LIVE=0 : altimétrie indisponible PROPREMENT (jamais d'erreur).
    assert js["altimetrie"].get("available") is False
    assert client.get("/parcels/00000000000000/enrichment").status_code == 404


def test_enrichment_cache_persiste(client):
    # 2ᵉ appel servi depuis le cache (parcel_enrichment) → même computed_at, pas de recalcul.
    a = client.get("/parcels/97415000AB0001/enrichment").json()
    b = client.get("/parcels/97415000AB0001/enrichment").json()
    assert a["computed_at"] and a["computed_at"] == b["computed_at"]


def test_export_markdown_et_html(client):
    md = client.get("/parcels/97415000AB0001/export", params={"format": "md"})
    assert md.status_code == 200 and "# LABUSE" in md.text and "Cascade" in md.text
    assert "Résumé opportunité" in md.text  # Phase 2 : l'export reprend le résumé business
    assert "Occupation actuelle" in md.text  # R1 : le signal bâti est exporté
    htmlr = client.get("/parcels/97415000AB0001/export", params={"format": "html"})
    assert htmlr.status_code == 200 and "<table" in htmlr.text and "Résumé opportunité" in htmlr.text


# M31 PC1 : test_discover_classe_les_survivantes RETIRÉ — la route /discover a été supprimée
# au M30 (orphelin, aucun appelant front, remplacée par /parcels + /stats). Le test dormait
# rouge, masqué par les erreurs DB de la famille B (il n'a jamais tourné depuis M30). La
# couverture « classement des opportunités » vit désormais dans les tests /parcels (tri rang P).


def test_feedback(client):
    r = client.post("/feedback", json={"idu": "97415000AB0001", "verdict": "good_lead"})
    assert r.json()["ok"] is True


def test_stats_endpoint(client):
    from labuse.scoring.score_v_constants import Q_A_RUN_LABEL
    # M45 (P1) : `source` REQUISE — le compteur v2 (tiers effectifs), plus le repli mort. La démo
    # Saint-Paul n'a PAS de ligne au run servi (cf. test_fiche_double_score) → total peut être 0
    # sur la fixture : on verrouille la FORME + l'invariant (somme des tiers <= total), pas une
    # magnitude legacy. Le filtrage v2 réel est verrouillé par test_verdict_effectif (données v2 semées).
    s = client.get("/stats", params={"commune": "Saint-Paul", "source": Q_A_RUN_LABEL}).json()
    assert isinstance(s["total"], int) and s["total"] >= 0
    t = s["tiers"]
    assert sum(t[k] for k in ("brulante", "chaude", "reserve_fonciere", "a_creuser", "ecartee")) <= s["total"]


def test_parcels_list_paginated(client):
    """#2 — /parcels est BORNÉ (limit) + structure attendue. M45 : `source` requise."""
    from labuse.scoring.score_v_constants import Q_A_RUN_LABEL
    r = client.get("/parcels", params={"commune": "Saint-Paul", "limit": 3, "source": Q_A_RUN_LABEL})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list) and len(body) <= 3
    if body:
        assert {"idu", "commune", "surface_m2", "status", "tier_v2"} <= set(body[0])
    assert client.get("/parcels", params={"limit": 9999, "source": Q_A_RUN_LABEL}).status_code == 422  # borne dure
    assert client.get("/parcels", params={"limit": 0, "source": Q_A_RUN_LABEL}).status_code == 422


def test_map_geojson(client):
    # M37 : le fallback legacy (parcel_evaluations.status) est SUPPRIMÉ — un seul chemin v2
    # (dryrun, tier servi). La couche de test n'a pas de run dryrun → FC vide mais VALIDE
    # (aucun 500). Le dispatch est couvert par test_api_q_v2, le contenu SQL par le golden.
    r = client.get("/map/parcels.geojson", params={"commune": "Saint-Paul"})
    assert r.status_code == 200
    fc = r.json()
    assert fc["type"] == "FeatureCollection" and isinstance(fc["features"], list)


def test_map_bati_endpoint(client):
    """LOT 2 — taux de bâti par parcelle (mode carte « mutabilité »)."""
    d = client.get("/map/bati", params={"commune": "Saint-Paul"}).json()
    assert "disponible" in d and "ratios" in d
    if d["disponible"]:
        assert isinstance(d["ratios"], dict)
        assert all(0.0 <= v <= 1.0 for v in d["ratios"].values())


def test_assemblage_study_endpoint(client):
    """LOT 2 — étude de faisabilité cumulée sur un ensemble de parcelles."""
    from labuse import models
    from labuse.db import session_scope
    with session_scope() as s:   # 2 IDU réels du jeu de démo
        idus = [r[0] for r in s.execute(select(models.Parcel.idu).limit(2)).all()]
    # garde-fou : < 2 parcelles → 400
    assert client.get("/assemblage/study", params={"idus": idus[0]}).status_code == 400
    r = client.get("/assemblage/study", params={"idus": ",".join(idus)})
    assert r.status_code == 200
    d = r.json()
    assert d["n_parcelles"] == 2
    assert isinstance(d["contigu"], bool)
    assert d["surface_cumulee_m2"] >= 0
    assert "sdp_m2" in d["capacite"] and "logements" in d["capacite"]
    assert "à valider" in d["note"]


def test_shortlist_endpoint(client):
    r = client.get("/shortlist", params={"commune": "Saint-Paul", "limit": 5})
    assert r.status_code == 200
    d = r.json()
    assert {"commune", "count", "candidates_total", "generated_at", "sujets"} <= set(d)
    assert d["count"] <= 5 and len(d["sujets"]) == d["count"]
    if d["sujets"]:
        # rangs 1..N consécutifs et priorité décroissante (logique promoteur, pas le score brut)
        assert [s["rang"] for s in d["sujets"]] == list(range(1, len(d["sujets"]) + 1))
        prios = [s["priority_score"] for s in d["sujets"]]
        assert prios == sorted(prios, reverse=True)
        top = d["sujets"][0]
        assert {"idu", "verdict_status", "score", "surface_m2", "potentiel_assemblage",
                "ca", "charge_fonciere", "blocage_principal", "confiance",
                "proprietaire", "prochaine_action", "badges"} <= set(top)
        assert top["verdict_status"] in ("opportunite", "a_creuser")
        assert "Priorité du jour" in top["badges"]      # le 1er sujet est toujours marqué
        assert isinstance(top["priority_components"], dict)


def test_front_served(client):
    # B2 : plus de mount /app (proto archivé) — la racine redirige, /socle/ sert le React
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert client.get("/app/", headers={"accept": "text/html"}).status_code in (200, 404)


def test_coverage_banner(client):
    cov = client.get("/coverage").json()
    assert {"critical_layers", "missing", "complete", "reliable_ready"} <= set(cov)
    kinds = {x["kind"] for x in cov["critical_layers"]}
    assert kinds == {"sar", "risques", "foret_publique", "ens", "safer", "trait_de_cote", "abf"}
    assert isinstance(cov["reliable_ready"], bool)


def test_limit_negatif_rejete_en_422(client):
    # M3 : un limit négatif doit renvoyer un 422 propre (pas un 500 Postgres).
    assert client.get("/map/parcels.geojson", params={"limit": -5}).status_code == 422
    # M31 PC1 : ligne /discover retirée — route supprimée au M30 (renverrait 404, pas 422).
    # M49 (Lot A) : ligne /signals retirée — route morte supprimée (0 caller prouvé).


def test_feedback_terrain_decote_le_score(client):
    # Retour « faux positif » sur une zone → décote le score d'opportunité (§10, zone).
    idu = "97415000AB0001"
    before = client.get(f"/parcels/{idu}").json()["verdict"]["opportunity_score"]
    client.post("/feedback", json={"idu": idu, "verdict": "false_positive", "comment": "déjà bâti (visite)"})
    after = client.post(f"/parcels/{idu}/evaluate").json()["opportunity_score"]
    assert after < before  # la zone faux-positif décote le score d'opportunité


def test_permit_idu_reconstruction():
    from labuse.ingestion.permits import _idu
    assert _idu("97415", "CV", "984") == "97415000CV0984"
    assert _idu("97415", "AH", "1017") == "97415000AH1017"
    assert _idu("97415", None, "1") is None


def test_watch_snapshot_delta_zonage(client):
    from sqlalchemy import text

    from labuse.db import session_scope
    from labuse.ingestion import signals

    with session_scope() as s:
        r1 = signals.run_watch(s, "Saint-Paul")
    assert r1["baseline"] is True and r1["signals_total"] == 0  # 1er run = photo de référence

    with session_scope() as s:  # simule une révision de zonage PLU (N → U)
        s.execute(text("UPDATE spatial_layers SET subtype='U' WHERE kind='plu_gpu_zone' AND subtype='N'"))

    with session_scope() as s:
        r2 = signals.run_watch(s, "Saint-Paul")
    assert r2["baseline"] is False
    assert r2["zonage_change"] >= 1 and r2["reevaluated"] >= 1  # delta détecté + ré-évaluation
    # M49 (Lot A) : la ROUTE GET /signals est retirée (0 caller) ; la détection reste vérifiée
    # via signals.run_watch + la table parcel_signals (le moteur, pas la route morte).
    with session_scope() as s2:
        sig = [dict(r) for r in s2.execute(text(
            "SELECT s.signal_type, s.payload FROM parcel_signals s JOIN parcels p ON p.id=s.parcel_id "
            "WHERE p.commune='Saint-Paul' AND s.signal_type='zonage_change'")).mappings().all()]
    assert sig and sig[0]["signal_type"] == "zonage_change" and sig[0]["payload"]["to"] == "U"


# ───────────────────────── Pipeline de prospection (Kanban T1) ─────────────────────────

def test_pipeline_meta(client):
    m = client.get("/pipeline/meta").json()
    keys = [c["key"] for c in m["columns"]]
    # workflow prospection (colonnes alignées) — « propriétaire à identifier » présente.
    assert keys[0] == "reperee" and "proprietaire_a_identifier" in keys
    assert keys[-1] == "abandonnee" and "contacte" in keys
    assert len(m["priorities"]) == 3 and m["defaults"]["status"] == "reperee"


def test_pipeline_crud_flow(client):
    # Ajout (statut "Repérée" par défaut) ; la carte porte le verdict/score.
    r = client.post("/pipeline", json={"idu": "97415000AB0002"}).json()
    assert r["ok"] and r["already"] is False
    eid = r["entry"]["id"]
    assert r["entry"]["status"] == "reperee" and r["entry"]["priority"] == "moyenne"
    assert r["entry"]["verdict"]["opportunity_score"] is not None
    # Présente dans la liste et la recherche par parcelle.
    assert any(e["id"] == eid for e in client.get("/pipeline").json())
    look = client.get("/pipeline/parcel/97415000AB0002").json()
    assert look["in_pipeline"] is True and look["entry"]["id"] == eid
    # Édition : statut + priorité + notes + rappel.
    p = client.patch(f"/pipeline/{eid}", json={
        "status": "contacte", "priority": "haute", "notes": "appelé la mairie", "reminder_date": "2026-07-15",
    }).json()
    assert p["entry"]["status"] == "contacte" and p["entry"]["priority"] == "haute"
    assert p["entry"]["notes"] == "appelé la mairie" and p["entry"]["reminder_date"] == "2026-07-15"
    # Effacer le rappel.
    assert client.patch(f"/pipeline/{eid}", json={"reminder_date": ""}).json()["entry"]["reminder_date"] is None
    # Retrait → la parcelle n'est plus suivie (persistance vérifiée par relecture).
    assert client.delete(f"/pipeline/{eid}").json()["ok"] is True
    assert client.get("/pipeline/parcel/97415000AB0002").json()["in_pipeline"] is False


def test_pipeline_move_status_persists(client):
    # Simule un glisser-déposer : changer de colonne via PATCH /pipeline/{id} → persistant en base.
    eid = client.post("/pipeline", json={"idu": "97415000AB0007"}).json()["entry"]["id"]
    assert client.patch(f"/pipeline/{eid}", json={"status": "en_discussion"}).json()["entry"]["status"] == "en_discussion"
    moved = next(e for e in client.get("/pipeline").json() if e["id"] == eid)  # relecture indépendante
    assert moved["status"] == "en_discussion"
    client.delete(f"/pipeline/{eid}")


def test_pipeline_duplicate_returns_existing(client):
    a = client.post("/pipeline", json={"idu": "97415000AB0003"}).json()
    b = client.post("/pipeline", json={"idu": "97415000AB0003"}).json()
    assert b["already"] is True and b["entry"]["id"] == a["entry"]["id"]  # pas de doublon
    client.delete(f"/pipeline/{a['entry']['id']}")


def test_pipeline_validation_jamais_500(client):
    assert client.post("/pipeline", json={"idu": "00000000000000"}).status_code == 404  # parcelle inconnue
    assert client.post("/pipeline", json={"idu": "97415000AB0004", "status": "bogus"}).status_code == 422
    r = client.post("/pipeline", json={"idu": "97415000AB0004"}).json()
    eid = r["entry"]["id"]
    assert client.patch(f"/pipeline/{eid}", json={"status": "pas_une_colonne"}).status_code == 422
    assert client.patch(f"/pipeline/{eid}", json={"reminder_date": "pas-une-date"}).status_code == 422
    assert client.patch("/pipeline/999999", json={"status": "chaud"}).status_code == 404
    assert client.delete("/pipeline/999999").status_code == 404
    client.delete(f"/pipeline/{eid}")


def test_m136_exports_ne_crashent_pas(client):
    """M136 — RÉGRESSION : le bloc matrice Q/A (q_score/a_score) a été retiré du payload en M129-B
    mais les EXPORTS le référençaient encore → 500 (KeyError). Ce verrou casse si un export lève.
    Couvre le PDF premium + la page de partage /p (les DEUX cassaient sur le même q_score)."""
    from sqlalchemy import text as sqla_text

    from labuse.db import session_scope
    from labuse.scoring.score_v_constants import Q_A_RUN_LABEL
    idu = "97415000AB0001"
    top5 = ('[{"bin":"<2a","signe":"+","feature":"permis_bin","libelle":"ancienneté du dernier permis",'
            '"log_hazard":1.3},{"bin":"true","signe":"+","feature":"piscine","libelle":"piscine",'
            '"log_hazard":0.4}]')
    with session_scope() as s:
        s.execute(sqla_text(
            "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, rang, "
            "contrib_z, contrib_d, copro, tier, model_version, top5_contributions) "
            "VALUES (:r, :i, 0.34, 22.1, 99, 7, 0, 0, false, 'brulante', 'm136', CAST(:t AS jsonb)) "
            "ON CONFLICT (run_id, parcelle_id) DO UPDATE SET tier='brulante', p_raw=0.34, "
            "top5_contributions=CAST(:t AS jsonb)"), {"r": Q_A_RUN_LABEL, "i": idu, "t": top5})
        s.execute(sqla_text(
            "INSERT INTO share_links (token, idu, created_by) VALUES ('m136gate', :i, 'm136') "
            "ON CONFLICT (token) DO UPDATE SET idu = :i"), {"i": idu})
    try:
        # 1) le PDF premium : réparé (bloc Q/A → raisons M135). PLUS jamais 500.
        r = client.get(f"/parcels/{idu}/export.pdf?source={Q_A_RUN_LABEL}")
        assert r.status_code == 200 and r.headers["content-type"] == "application/pdf", r.text[:200]
        assert len(r.content) > 5000
        # 2) la page de partage publique : même fiche, même piège q_score — réparée aussi.
        r = client.get("/p/m136gate")
        assert r.status_code == 200, r.text[:200]
        assert "QUALITÉ /100" not in r.text and "CLASSEMENT" in r.text   # plus de bloc mort
    finally:
        with session_scope() as s:
            s.execute(sqla_text("DELETE FROM parcel_p_score_v2 WHERE run_id=:r AND parcelle_id=:i"),
                      {"r": Q_A_RUN_LABEL, "i": idu})
            s.execute(sqla_text("DELETE FROM share_links WHERE token='m136gate'"))
