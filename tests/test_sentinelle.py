"""SENTINELLE-1 — tests de la veille des sources amont.

Couvre : les TROIS méthodes de détection (W2), la comparaison au millésime SERVI (W3.3), la
distinction injoignable ≠ illisible (W3.5), l'écriture DANS source_veille et JAMAIS dans data_sources
(W3.4), la notification admin dédupliquée par (source, millésime) (W4.1), le peuplement idempotent (W5),
les endpoints admin (W4.3), et la NON-RÉGRESSION de l'ancien sentinelle-dvf-cadastre (W2).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse import sentinelle

pytestmark = pytest.mark.db


def _fake_http(reponses: dict):
    """Fabrique une couche HTTP factice : url → (status, headers, body). Absente → lève (→ injoignable)."""
    def _h(url: str, *, methode_http: str = "GET"):
        if url not in reponses:
            raise ConnectionError(f"réseau coupé (test) : {url}")
        return reponses[url]
    return _h


@pytest.fixture
def client(engine):
    from labuse import models
    from labuse.api import events
    from labuse.api.app import app
    models.ensure_source_veille(engine)
    events.ensure_tables(engine)
    return TestClient(app, base_url="https://testserver")


def _source(db, nom: str, millesime: str | None = None) -> int:
    sid = db.execute(text(
        "INSERT INTO data_sources (name, status, source_millesime) VALUES (:n, 'connecte', :m) "
        "ON CONFLICT (name) DO UPDATE SET source_millesime = EXCLUDED.source_millesime RETURNING id"),
        {"n": nom, "m": millesime}).scalar()
    return sid


def _veille(db, sid: int, methode: str, url: str, selecteur=None, entete=None):
    # base de test PERSISTANTE : on remet à zéro la mémoire de notif (dernier_notifie_vu, echecs) pour
    # que chaque test parte propre (sinon un `dernier_notifie_vu` d'un run précédent fausse la dédup).
    db.execute(text(
        "INSERT INTO source_veille (source_id, methode, url_version, selecteur, dernier_entete, actif) "
        "VALUES (:s, :m, :u, :sel, :ent, true) ON CONFLICT (source_id) DO UPDATE SET "
        "methode = EXCLUDED.methode, url_version = EXCLUDED.url_version, selecteur = EXCLUDED.selecteur, "
        "dernier_entete = EXCLUDED.dernier_entete, dernier_notifie_vu = NULL, echecs_consecutifs = 0, "
        "dernier_statut = NULL"),
        {"s": sid, "m": methode, "u": url, "sel": selecteur, "ent": entete})


# ─────────────────────────── W2 · les trois méthodes ───────────────────────────

def test_methode_api_extrait_le_chemin_json():
    http = _fake_http({"http://x/v": (200, {}, '{"meta": {"version": "2026-S1"}}')})
    row = {"methode": "api", "url_version": "http://x/v", "selecteur": "meta.version"}
    s = sentinelle.sonder_ligne(row, servi=None, http=http)
    assert s.statut == "ok" and s.vu == "2026-S1"


def test_methode_page_garde_le_plus_recent():
    corps = "index: 2020/ 2021/ 2024/ 2022/"
    http = _fake_http({"http://x/idx": (200, {}, corps)})
    row = {"methode": "page", "url_version": "http://x/idx", "selecteur": r"20\d{2}"}
    s = sentinelle.sonder_ligne(row, servi=None, http=http)
    assert s.statut == "ok" and s.vu == "2024"   # max, jamais le premier venu


def test_methode_entete_baseline_puis_changement():
    row = {"methode": "entete", "url_version": "http://x/f.gz", "selecteur": None, "dernier_entete": None}
    http1 = _fake_http({"http://x/f.gz": (200, {"last-modified": "Mon, 01 Jan 2026"}, "")})
    s1 = sentinelle.sonder_ligne(row, servi=None, http=http1)
    assert s1.statut == "ok" and s1.entete == "Mon, 01 Jan 2026"   # 1er passage = baseline
    row["dernier_entete"] = s1.entete
    http2 = _fake_http({"http://x/f.gz": (200, {"last-modified": "Wed, 15 Apr 2026"}, "")})
    s2 = sentinelle.sonder_ligne(row, servi=None, http=http2)
    assert s2.statut == "nouvelle_version" and s2.vu == "Wed, 15 Apr 2026"


# ─────────────────────────── W3.3 · comparaison au servi ───────────────────────────

def test_api_millesime_amont_posterieur_au_servi_est_nouvelle_version():
    http = _fake_http({"http://x/v": (200, {}, '{"v": "2026-S1"}')})
    row = {"methode": "api", "url_version": "http://x/v", "selecteur": "v"}
    assert sentinelle.sonder_ligne(row, servi="2025-S2", http=http).statut == "nouvelle_version"
    assert sentinelle.sonder_ligne(row, servi="2026-S1", http=http).statut == "ok"   # égal → pas nouvelle


# ─────────────────────────── W3.5 · injoignable ≠ illisible ───────────────────────────

def test_injoignable_est_distinct_d_illisible():
    row = {"methode": "api", "url_version": "http://x/down", "selecteur": "v"}
    assert sentinelle.sonder_ligne(row, servi=None, http=_fake_http({})).statut == "injoignable"
    bad = _fake_http({"http://x/bad": (200, {}, "pas du json")})
    row2 = {"methode": "api", "url_version": "http://x/bad", "selecteur": "v"}
    assert sentinelle.sonder_ligne(row2, servi=None, http=bad).statut == "illisible"
    row3 = {"methode": "api", "url_version": "http://x/500", "selecteur": "v"}
    assert sentinelle.sonder_ligne(row3, servi=None, http=_fake_http({"http://x/500": (503, {}, "")})).statut == "injoignable"


# ─────────────────────────── W3.4 / W4.1 · passer : écrit source_veille, notif dédupliquée ───────────────────────────

def test_passer_ecrit_source_veille_jamais_data_sources_et_notifie_une_fois(engine):
    from labuse.api import events
    from labuse.db import session_scope
    events.ensure_tables(engine)
    from labuse import models
    models.ensure_source_veille(engine)
    with session_scope() as db:
        sid = _source(db, "TEST DVF sentinelle", millesime="2025-S2")
        _veille(db, sid, "page", "http://x/dvf", selecteur=r"20\d{2}-S[12]")
        db.execute(text("DELETE FROM event_log WHERE dedup LIKE :p"), {"p": "sentinelle-digest:%"})  # base de test persistante
        db.commit()
    dd = f"sentinelle-digest:n:{sid}:2026-S1|e:"   # SENTINELLE-2 — clé du digest pour cette source seule
    http = _fake_http({"http://x/dvf": (200, {}, "2024-S1 2026-S1 2025-S2")})
    with session_scope() as db:
        recap = sentinelle.passer(db, source_ids=[sid], forcer=True, http=http, delai_s=0)
        db.commit()
    assert recap["nouvelles"] == 1 and recap["notifs"] == 1
    with session_scope() as db:
        row = db.execute(text("SELECT dernier_statut, dernier_vu, dernier_notifie_vu FROM source_veille WHERE source_id=:s"),
                         {"s": sid}).mappings().first()
        assert row["dernier_statut"] == "nouvelle_version" and row["dernier_vu"] == "2026-S1"
        assert row["dernier_notifie_vu"] == "2026-S1"   # X5 — le millésime annoncé est mémorisé
        # X6 DOCTRINE — détecter une nouvelle version n'INJECTE JAMAIS : le pont est un clic humain.
        assert db.execute(text("SELECT injection_lancee_at FROM source_veille WHERE source_id=:s"), {"s": sid}).scalar() is None
        # data_sources JAMAIS touché : le millésime servi n'a pas bougé.
        assert db.execute(text("SELECT source_millesime FROM data_sources WHERE id=:s"), {"s": sid}).scalar() == "2025-S2"
        n = db.execute(text("SELECT count(*) FROM event_log WHERE dedup=:d"), {"d": dd}).scalar()
        assert n == 1
    # 2e passage, même millésime amont : dernier_notifie_vu bloque la ré-annonce → AUCUNE nouvelle notif.
    with session_scope() as db:
        recap2 = sentinelle.passer(db, source_ids=[sid], forcer=True, http=http, delai_s=0)
        db.commit()
        n = db.execute(text("SELECT count(*) FROM event_log WHERE dedup=:d"), {"d": dd}).scalar()
    assert recap2["nouvelles"] == 1 and recap2["notifs"] == 0 and n == 1


# ─────────────────────────── X5 · digest quotidien + seuil d'échecs ───────────────────────────

def test_digest_agrege_plusieurs_sources_en_une_seule_cloche(engine):
    """X5.1 — deux sources ont du nouveau le même passage → UNE seule notification « 2 sources ont une
    nouvelle version », pas deux."""
    from labuse.api import events
    from labuse.db import session_scope
    events.ensure_tables(engine)
    from labuse import models
    models.ensure_source_veille(engine)
    with session_scope() as db:
        s1 = _source(db, "TEST digest A", millesime="2025")
        s2 = _source(db, "TEST digest B", millesime="2025")
        _veille(db, s1, "page", "http://x/da", selecteur=r"20\d{2}")
        _veille(db, s2, "page", "http://x/db", selecteur=r"20\d{2}")
        db.execute(text("DELETE FROM event_log WHERE dedup LIKE :p"), {"p": "sentinelle-digest:%"})
        db.commit()
    http = _fake_http({"http://x/da": (200, {}, "2026"), "http://x/db": (200, {}, "2026")})
    with session_scope() as db:
        recap = sentinelle.passer(db, source_ids=[s1, s2], forcer=True, http=http, delai_s=0)
        db.commit()
        row = db.execute(text("SELECT titre, detail FROM event_log WHERE source='Veille sources' "
                              "AND dedup LIKE 'sentinelle-digest:%' ORDER BY id DESC LIMIT 1")).mappings().first()
        n_notifs = db.execute(text("SELECT count(*) FROM event_log WHERE source='Veille sources' "
                                   "AND dedup LIKE 'sentinelle-digest:%'")).scalar()
    assert recap["nouvelles"] == 2 and recap["notifs"] == 1
    assert n_notifs == 1                       # UNE cloche, pas deux
    assert "2 sources" in row["titre"]         # le résumé compte
    assert "TEST digest A" in row["detail"] and "TEST digest B" in row["detail"]   # dépliable


def test_sonde_echec_ne_notifie_qu_apres_trois_passages(engine):
    """X5.2 — une sonde en échec ne notifie NI au 1er NI au 2e passage : seulement au 3e (échecs
    consécutifs). Un ok entre-temps remet le compteur à zéro."""
    from labuse.api import events
    from labuse.db import session_scope
    events.ensure_tables(engine)
    from labuse import models
    models.ensure_source_veille(engine)
    with session_scope() as db:
        sid = _source(db, "TEST echec seuil")
        _veille(db, sid, "api", "http://x/down", selecteur="v")   # url absente → injoignable
        db.execute(text("DELETE FROM event_log WHERE dedup LIKE :p"), {"p": "sentinelle-digest:%"})
        db.commit()
    down = _fake_http({})   # réseau coupé → injoignable à chaque passage
    for passage in (1, 2, 3):
        with session_scope() as db:
            recap = sentinelle.passer(db, source_ids=[sid], forcer=True, http=down, delai_s=0)
            db.commit()
            ec = db.execute(text("SELECT echecs_consecutifs FROM source_veille WHERE source_id=:s"), {"s": sid}).scalar()
        assert ec == passage
        assert recap["notifs"] == (1 if passage == 3 else 0)   # notif PILE au 3e
    # une sonde qui repasse ok remet le compteur à zéro (l'épisode est clos). On repointe l'URL EN
    # PLACE (sans passer par _veille qui réinitialiserait echecs) pour prouver que c'est bien le passage
    # OK — pas le helper — qui remet à zéro.
    with session_scope() as db:
        db.execute(text("UPDATE source_veille SET url_version='http://x/up' WHERE source_id=:s"), {"s": sid})
        sentinelle.passer(db, source_ids=[sid], forcer=True,
                          http=_fake_http({"http://x/up": (200, {}, '{"v": "ok"}')}), delai_s=0)
        db.commit()
        ec = db.execute(text("SELECT echecs_consecutifs FROM source_veille WHERE source_id=:s"), {"s": sid}).scalar()
    assert ec == 0


# ─────────────────────────── W2 · NON-RÉGRESSION sentinelle-dvf-cadastre ───────────────────────────

def test_non_regression_dvf_alerte_comme_l_ancien_job(engine):
    """L'ancien job (heuristique DATE : prochain_millesime_at échu) ET le nouveau passage réel
    déclenchent tous deux une ALERTE pour DVF sur la même donnée — outcome équivalent, mécanique
    améliorée (date-indice → sonde réelle)."""
    from labuse.api import events
    from labuse.db import session_scope
    from labuse.jobs import JobContext
    from labuse import jobs_impl, models
    events.ensure_tables(engine)
    models.ensure_source_veille(engine)
    with session_scope() as db:
        sid = _source(db, "DVF non-reg", millesime="2025-S2")
        db.execute(text("UPDATE data_sources SET prochain_millesime_at = current_date - 1 WHERE id=:s"), {"s": sid})
        _veille(db, sid, "page", "http://x/dvf2", selecteur=r"20\d{2}-S[12]")
        db.commit()
    # ANCIEN : heuristique date → alerte (n_alertes ≥ 1).
    with session_scope() as db:
        ctx = JobContext(db=db, dry_run=True)
        # patch le nom recherché : l'ancien job cible name ILIKE '%DVF%' → notre ligne matche.
        jobs_impl.sentinelle_dvf_cadastre(ctx)
        assert ctx.compteurs["n_alertes"] >= 1
    # NOUVEAU : sonde réelle → nouvelle_version (2026-S1 > 2025-S2).
    http = _fake_http({"http://x/dvf2": (200, {}, "2025-S2 2026-S1")})
    with session_scope() as db:
        recap = sentinelle.passer(db, source_ids=[sid], forcer=True, http=http, delai_s=0)
        db.commit()
    assert recap["nouvelles"] >= 1


# ─────────────────────────── X1-X3 · couverture du catalogue (rattachement par nom EXACT) ───────────────────────────

def test_seed_et_raisons_couvrent_les_64_sources_par_nom_exact():
    """Chaque nom du SEED et des RAISONS existe au catalogue (jamais inventé) ; aucune source n'est à la
    fois surveillée ET déclarée non surveillée ; et l'ensemble seed + raisons + doublons couverts == les
    64 sources (garde anti-dérive : un renommage au catalogue casse ce test avant de casser le semis)."""
    from labuse.ingestion.seed_sources import SOURCES
    noms = {r["name"] for r in SOURCES}
    seed_noms = {e["name"] for e in sentinelle.SEED}
    raison_noms = set(sentinelle.RAISONS_NON_SURVEILLEES)
    assert seed_noms <= noms, f"noms de SEED absents du catalogue : {seed_noms - noms}"
    assert raison_noms <= noms, f"raisons pour des noms absents du catalogue : {raison_noms - noms}"
    assert not (seed_noms & raison_noms), f"sources à la fois surveillées et non surveillées : {seed_noms & raison_noms}"
    # les 2 seuls noms hors seed/raisons = doublons amont couverts par leur canonique (une seule veille).
    doublons_couverts = {"Cadastre Etalab (bulk DGFiP/Etalab)", "RGE ALTI 5 m (IGN)"}
    reste = noms - seed_noms - raison_noms - doublons_couverts
    assert not reste, f"sources non classées (ni surveillées, ni raison, ni doublon couvert) : {reste}"
    # SCORING-3 (L3) — 64 → 65 : la BDNB entre au catalogue (surveillée par la sentinelle,
    # api data.gouv ; ingestion trimestrielle prête, amont sans le 974 au 03/09/2026).
    # CIRCUIT-3 lot 6 — +2 : CatNat (arrêtés GASPAR) et Taxe d'aménagement (taux communaux)
    # entrent par la vanne (raisons non surveillées : interrogées en direct / source à ingérer).
    # RETOURS-13 (R4/R5) — +3 : EDF Réunion HTA (SEED, en-tête du data-file), TCSP OSM
    # (raison : flux Overpass en direct) et Réunion Express (SEED, en-tête de la carte du
    # débat public — le tracé bougera après la clôture du 26/11/2026).
    # RETOURS-14 (S5) — +1 : cadastre d'époque (raison : archives immuables).
    # FUSION fix/retours-12 → main : les deux jeux d'ajouts coexistent au catalogue
    # (base 65 + CIRCUIT-3 2 + RETOURS-13/14 4 = 71) ; aucune source d'un côté ni de l'autre
    # n'est perdue — mesuré sur l'arbre fusionné.
    assert len(noms) == 71


def test_raison_non_surveillee_ne_rend_jamais_un_blanc():
    assert sentinelle.raison_non_surveillee("Radar (pige d'annonces)").startswith("Collecte")
    assert sentinelle.raison_non_surveillee("Nom inconnu au bataillon").strip()   # défaut honnête, jamais vide


# ─────────────────────────── W5 · ensemencement idempotent ───────────────────────────

def test_ensemencer_idempotent_et_preserve_actif(engine):
    from labuse.db import session_scope
    from labuse import models
    models.ensure_source_veille(engine)
    # crée en base les sources du SEED (par nom exact) pour que l'ensemencement les rattache, puis
    # repart d'une table de veille propre pour ces sources (base de test persistante + seed au boot).
    with session_scope() as db:
        for e in sentinelle.SEED:
            _source(db, e["name"])
        db.execute(text("DELETE FROM source_veille WHERE source_id IN "
                        "(SELECT id FROM data_sources WHERE name = ANY(:n))"),
                   {"n": [e["name"] for e in sentinelle.SEED]})
        db.commit()
    with session_scope() as db:
        c1 = sentinelle.ensemencer(db)
        db.commit()
    with session_scope() as db:
        c2 = sentinelle.ensemencer(db)   # 2e passage : rien de neuf
        db.commit()
        # désactive une source, ré-ensemence : le flag actif est PRÉSERVÉ.
        premier = sentinelle.SEED[0]["name"]
        db.execute(text("UPDATE source_veille SET actif=false WHERE source_id=("
                        "SELECT id FROM data_sources WHERE name=:n)"), {"n": premier})
        db.commit()
    with session_scope() as db:
        sentinelle.ensemencer(db)
        db.commit()
        actif = db.execute(text("SELECT actif FROM source_veille WHERE source_id=("
                                "SELECT id FROM data_sources WHERE name=:n)"), {"n": premier}).scalar()
    assert c1 == len(sentinelle.SEED) and c2 == 0 and actif is False


# ─────────────────────────── W4.3 · endpoints admin ───────────────────────────

def test_endpoint_sources_expose_le_bloc_veille(client, engine):
    from labuse.db import session_scope
    with session_scope() as db:
        sid = _source(db, "TEST veille endpoint", millesime="2025")
        _veille(db, sid, "page", "http://x/e", selecteur=r"20\d{2}")
        db.commit()
    data = client.get("/admin/sources").json()
    assert "nouvelle_version" in data["synthese"] and "surveillees" in data["synthese"]
    ligne = next(s for s in data["sources"] if s["id"] == sid)
    assert ligne["veille"]["surveillee"] is True and ligne["veille"]["methode"] == "page"


def test_endpoint_verifier_maintenant_sonde_en_direct(client, engine, monkeypatch):
    from labuse.db import session_scope
    with session_scope() as db:
        sid = _source(db, "TEST verifier now", millesime="2025-S2")
        _veille(db, sid, "page", "http://x/now", selecteur=r"20\d{2}-S[12]")
        db.commit()
    monkeypatch.setattr(sentinelle, "_http", _fake_http({"http://x/now": (200, {}, "2025-S2 2026-S1")}))
    r = client.post(f"/admin/sources/{sid}/veille/verifier").json()
    assert r["ok"] and r["statut"] == "nouvelle_version" and r["millesime_amont"] == "2026-S1"


def test_endpoint_active_toggle(client, engine):
    from labuse.db import session_scope
    with session_scope() as db:
        sid = _source(db, "TEST toggle veille")
        _veille(db, sid, "entete", "http://x/t")
        db.commit()
    assert client.post(f"/admin/sources/{sid}/veille/active", json={"actif": False}).json()["actif"] is False
    with session_scope() as db:
        assert db.execute(text("SELECT actif FROM source_veille WHERE source_id=:s"), {"s": sid}).scalar() is False
    assert client.post(f"/admin/sources/{sid}/veille/active", json={"actif": True}).json()["actif"] is True


# ─────────────────────────── X6 · le pont supervisé « Injecter cette version » ───────────────────────────

def test_x6_injecter_lance_le_job_existant_et_trace_le_geste(client, engine, monkeypatch):
    """X6 — sur clic (endpoint), on lance le JOB D'INGESTION EXISTANT (même commande que le cron) et on
    TRACE le geste (injection_lancee_at + millésime). Le subprocess est stubé : on vérifie qu'il PART."""
    from labuse.db import session_scope
    lance = {}
    class _FakePopen:
        def __init__(self, argv, **kw): lance["argv"] = argv
    monkeypatch.setattr("subprocess.Popen", _FakePopen)   # ne lance rien pour de vrai en test
    with session_scope() as db:
        sid = _source(db, "BODACC (procédures collectives)", millesime="2025")   # matche le motif « BODACC% »
        _veille(db, sid, "api", "http://x/b", selecteur="metas.default.modified")
        db.execute(text("UPDATE source_veille SET dernier_statut='nouvelle_version', dernier_vu='2026' WHERE source_id=:s"), {"s": sid})
        db.commit()
    r = client.post(f"/admin/sources/{sid}/veille/injecter").json()
    assert r["ok"] and r["label"] == "bodacc" and r["millesime"] == "2026"
    assert lance.get("argv"), "le job d'ingestion existant doit être lancé"
    with session_scope() as db:
        row = db.execute(text("SELECT injection_lancee_at, injection_vu FROM source_veille WHERE source_id=:s"),
                         {"s": sid}).mappings().first()
    assert row["injection_lancee_at"] is not None and row["injection_vu"] == "2026"


def test_x6_injecter_404_si_non_surveillee(client, engine):
    from labuse.db import session_scope
    with session_scope() as db:
        sid = _source(db, "TEST x6 non surveillée")
        db.commit()
    assert client.post(f"/admin/sources/{sid}/veille/injecter").status_code == 404


def test_x6_injecter_404_si_aucune_commande_dingestion(client, engine, monkeypatch):
    """Pas de commande mappée = injection MANUELLE : 404 honnête, le front n'affiche pas le bouton
    (mention « injection manuelle »). On stube Popen pour prouver qu'AUCUN lancement n'a lieu."""
    from labuse.db import session_scope
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("ne doit pas lancer")))
    with session_scope() as db:
        sid = _source(db, "TEST x6 sans commande mappée")   # ne matche aucun motif du YAML
        _veille(db, sid, "api", "http://x/z", selecteur="v")
        db.execute(text("UPDATE source_veille SET dernier_statut='nouvelle_version', dernier_vu='2026' WHERE source_id=:s"), {"s": sid})
        db.commit()
    assert client.post(f"/admin/sources/{sid}/veille/injecter").status_code == 404


def test_verifier_maintenant_404_si_non_surveillee(client, engine):
    from labuse.db import session_scope
    with session_scope() as db:
        sid = _source(db, "TEST non surveillee")
        db.commit()
    assert client.post(f"/admin/sources/{sid}/veille/verifier").status_code == 404


# ─────────────────────────── SENTINELLE-3 · Y3 méthode `temoin` ───────────────────────────

def test_methode_temoin_baseline_puis_changement():
    """Y3 — la requête témoin lit une EMPREINTE stable (ici un compte) : 1er passage = baseline (ok,
    mémorise), puis « nouvelle_version » (« la donnée amont a changé ») quand l'empreinte bouge."""
    row = {"methode": "temoin", "url_version": "http://x/q", "selecteur": "results", "dernier_entete": None}
    http1 = _fake_http({"http://x/q": (200, {}, '{"results": 377, "data": []}')})
    s1 = sentinelle.sonder_ligne(row, servi=None, http=http1)
    assert s1.statut == "ok" and s1.vu == "377" and s1.entete == "377"   # baseline
    row["dernier_entete"] = s1.entete
    http2 = _fake_http({"http://x/q": (200, {}, '{"results": 381, "data": []}')})
    s2 = sentinelle.sonder_ligne(row, servi=None, http=http2)
    assert s2.statut == "nouvelle_version" and s2.vu == "381"
    assert "changé" in (s2.message or "")


def test_temoin_empreinte_liste_stable_et_change_au_contenu():
    """Y3 — empreinte d'une réponse ENTIÈRE (selecteur None) : même contenu → même empreinte (ok) ;
    contenu différent → empreinte différente (nouvelle_version). Jamais la réponse brute stockée."""
    corps = '{"casias": [1, 2, 3], "conclusions": []}'
    emp = sentinelle._empreinte({"casias": [1, 2, 3], "conclusions": []})
    row = {"methode": "temoin", "url_version": "http://x/ssp", "selecteur": None, "dernier_entete": emp}
    same = sentinelle.sonder_ligne(row, servi=None, http=_fake_http({"http://x/ssp": (200, {}, corps)}))
    assert same.statut == "ok"   # empreinte identique
    changed = sentinelle.sonder_ligne(row, servi=None,
                                      http=_fake_http({"http://x/ssp": (200, {}, '{"casias": [1, 2, 3, 4], "conclusions": []}')}))
    assert changed.statut == "nouvelle_version"


def test_temoin_jamais_compare_au_millesime_servi():
    """Y3 — un témoin (empreinte, aucune notion de version) NE doit JAMAIS être transformé en
    « nouvelle_version » par la comparaison au servi (réservée aux méthodes à version api/page)."""
    http = _fake_http({"http://x/t": (200, {}, '{"total_count": 283}')})
    row = {"methode": "temoin", "url_version": "http://x/t", "selecteur": "total_count", "dernier_entete": "283"}
    s = sentinelle.sonder_ligne(row, servi="1", http=http)   # "283" > "1" lexicalement, mais témoin
    assert s.statut == "ok"   # PAS nouvelle_version : le servi n'entre pas en jeu pour un témoin


def test_nature_mappe_les_quatre_etats():
    assert sentinelle.nature("api") == "version" and sentinelle.nature("page") == "version"
    assert sentinelle.nature("entete") == "changement" and sentinelle.nature("temoin") == "changement"
    assert sentinelle.nature("rappel") == "rappel"
    assert sentinelle.nature(None) == "non_surveillable" and sentinelle.nature("xxx") == "non_surveillable"


# ─────────────────────────── SENTINELLE-3 · Y4 rappels manuels ───────────────────────────

def test_rappel_n_est_jamais_sonde(engine):
    """Y4 — une ligne 'rappel' (source manuelle) n'est JAMAIS interrogée par le passage de veille : aucun
    appel réseau, aucun changement de statut de sonde. Le http de test lèverait si on l'appelait."""
    from labuse.db import session_scope
    from labuse import models
    models.ensure_source_veille(engine)
    with session_scope() as db:
        sid = _source(db, "TEST rappel non sonde")
        db.execute(text("INSERT INTO source_veille (source_id, methode, cadence_attendue_jours, actif) "
                        "VALUES (:s, 'rappel', 30, true) ON CONFLICT (source_id) DO UPDATE SET "
                        "methode='rappel', cadence_attendue_jours=30, dernier_statut=NULL"), {"s": sid})
        db.commit()
    with session_scope() as db:
        recap = sentinelle.passer(db, forcer=True, http=_fake_http({}), delai_s=0)
        db.commit()
        st = db.execute(text("SELECT dernier_statut FROM source_veille WHERE source_id=:s"), {"s": sid}).scalar()
    assert st is None   # jamais sondée → statut inchangé
    assert not any(d["source"] == "TEST rappel non sonde" for d in recap["details"])


def test_passer_rappels_notifie_apres_depassement_une_seule_fois(engine):
    """Y4 — au-delà de la cadence attendue sans nouvelle ingestion (last_sync_at), UN rappel « donnée
    manuelle non rafraîchie » — une seule fois par dépassement (dédup sur la date de dernière ingestion)."""
    from labuse.api import events
    from labuse.db import session_scope
    from labuse import models
    events.ensure_tables(engine)
    models.ensure_source_veille(engine)
    with session_scope() as db:
        sid = _source(db, "TEST rappel retard")
        # dernière ingestion il y a 400 jours, cadence attendue 365 → dépassement
        db.execute(text("UPDATE data_sources SET last_sync_at = now() - interval '400 days' WHERE id=:s"), {"s": sid})
        db.execute(text("INSERT INTO source_veille (source_id, methode, cadence_attendue_jours, actif) "
                        "VALUES (:s, 'rappel', 365, true) ON CONFLICT (source_id) DO UPDATE SET "
                        "methode='rappel', cadence_attendue_jours=365"), {"s": sid})
        # base de test PERSISTANTE : on vide le feed systeme du jour pour repartir sous le plafond quotidien
        # (kind=systeme/compte NULL est plafonné à 50/j — un run précédent pourrait l'avoir saturé).
        db.execute(text("DELETE FROM event_log WHERE kind='systeme' AND compte_id IS NULL"))
        db.commit()
    with session_scope() as db:
        r1 = sentinelle.passer_rappels(db, source_ids=[sid], notifier=True)
        db.commit()
    assert r1["retards"] == 1 and r1["notifs"] == 1
    # 2e passage, même last_sync_at → dédup : aucune nouvelle cloche.
    with session_scope() as db:
        r2 = sentinelle.passer_rappels(db, source_ids=[sid], notifier=True)
        db.commit()
        n = db.execute(text("SELECT count(*) FROM event_log WHERE dedup LIKE 'sentinelle-rappel:%' "
                            "AND detail LIKE '%TEST rappel retard%'")).scalar()
    assert r2["retards"] == 1 and n == 1   # toujours en retard, mais UNE seule notif


def test_rappel_a_jour_ne_notifie_pas(engine):
    """Y4 — une donnée manuelle rafraîchie DANS la cadence ne déclenche aucun rappel."""
    from labuse.api import events
    from labuse.db import session_scope
    from labuse import models
    events.ensure_tables(engine)
    models.ensure_source_veille(engine)
    with session_scope() as db:
        sid = _source(db, "TEST rappel a jour")
        db.execute(text("UPDATE data_sources SET last_sync_at = now() - interval '10 days' WHERE id=:s"), {"s": sid})
        db.execute(text("INSERT INTO source_veille (source_id, methode, cadence_attendue_jours, actif) "
                        "VALUES (:s, 'rappel', 365, true) ON CONFLICT (source_id) DO UPDATE SET "
                        "methode='rappel', cadence_attendue_jours=365"), {"s": sid})
        db.commit()
    with session_scope() as db:
        r = sentinelle.passer_rappels(db, source_ids=[sid], notifier=True)
    assert r["rappels"] == 1 and r["retards"] == 0 and r["notifs"] == 0


# ─────────────────────────── SENTINELLE-3 · Y5.2 inventaire généré ───────────────────────────

def test_inventaire_markdown_regenere_depuis_le_catalogue():
    """Y5.2 — l'inventaire est GÉNÉRÉ (jamais à la main) : il couvre les 64 sources, distingue les 4
    natures, et son bilan reflète SEED/RAISONS/RAPPELS/DOUBLONS."""
    from labuse.ingestion.seed_sources import SOURCES
    md = sentinelle.inventaire_markdown()
    n_surv = len(sentinelle.SEED)
    assert f"**{n_surv} surveillées**" in md
    assert "`temoin`" in md and "requête témoin" in md   # la nouvelle méthode est visible
    assert "rappel manuel" in md
    # chaque source du catalogue figure au moins par son nom
    for s in SOURCES:
        assert s["name"] in md, f"source absente de l'inventaire généré : {s['name']}"


# ─────────────────────────── SUITE-1 · S4 · second témoin + alerte mail ───────────────────────────

def test_s4_temoin_deux_communes_alerte_si_l_un_change(engine):
    """S4.2 — un témoin sur DEUX chef-lieux (url + url_temoin_2) : l'empreinte combine les deux. Un
    changement de L'UN OU L'AUTRE devient « nouvelle_version » ; identique des deux côtés reste « ok »."""
    from labuse.db import session_scope
    u1, u2 = "http://x/sd", "http://x/sp"
    base = {u1: (200, {}, '{"results":[{"id":1}]}'), u2: (200, {}, '{"results":[{"id":9}]}')}
    with session_scope() as db:
        sid = _source(db, "TEST temoin bicommune")
        _veille(db, sid, "temoin", u1, selecteur="results")
        db.execute(text("UPDATE source_veille SET url_temoin_2=:u2 WHERE source_id=:s"), {"u2": u2, "s": sid})
        db.commit()
        row = db.execute(text("SELECT * FROM source_veille WHERE source_id=:s"), {"s": sid}).mappings().first()
    # baseline
    s0 = sentinelle.sonder_ligne(dict(row), servi=None, http=_fake_http(base))
    assert s0.statut == "ok"
    row = dict(row); row["dernier_entete"] = s0.entete
    # rien ne change → ok
    assert sentinelle.sonder_ligne(row, servi=None, http=_fake_http(base)).statut == "ok"
    # seule Saint-Pierre change → nouvelle_version
    change_sp = {u1: base[u1], u2: (200, {}, '{"results":[{"id":42}]}')}
    assert sentinelle.sonder_ligne(row, servi=None, http=_fake_http(change_sp)).statut == "nouvelle_version"


def test_s4_endpoint_mail_toggle(client, engine):
    """S4.1 — l'endpoint abonne/désabonne une source à l'alerte mail (par défaut off)."""
    from labuse.db import session_scope
    with session_scope() as db:
        sid = _source(db, "TEST mail toggle")
        _veille(db, sid, "entete", "http://x/m")
        db.commit()
    assert client.post(f"/admin/sources/{sid}/veille/mail", json={"mail_alerte": True}).json()["mail_alerte"] is True
    with session_scope() as db:
        assert db.execute(text("SELECT mail_alerte FROM source_veille WHERE source_id=:s"), {"s": sid}).scalar() is True
    # exposé dans /admin/sources
    ligne = next(s for s in client.get("/admin/sources").json()["sources"] if s["id"] == sid)
    assert ligne["veille"]["mail_alerte"] is True


def test_s4_digest_envoie_mail_seulement_si_abonnee(client, engine, monkeypatch):
    """S4.1 — le mail ne part QUE si la source est abonnée (`mail_alerte`) ; l'alerte in-app reste toujours."""
    import labuse.mail as mail_mod
    from labuse.db import session_scope
    envois: list = []
    monkeypatch.setattr(mail_mod, "send_email_async", lambda *a, **k: envois.append(a))
    # source NON abonnée → aucun mail
    with session_scope() as db:
        sid = _source(db, "TEST digest mail off", millesime="2025")
        _veille(db, sid, "page", "http://x/off", selecteur=r"20\d{2}")
        db.commit()
    from labuse.config import get_settings
    monkeypatch.setattr(get_settings(), "admin_email", "ops@labuse.test", raising=False)
    http = _fake_http({"http://x/off": (200, {}, "2026")})
    with session_scope() as db:
        sentinelle.passer(db, source_ids=[sid], forcer=True, http=http, delai_s=0)
    assert envois == []
    # source abonnée → un mail
    with session_scope() as db:
        sid2 = _source(db, "TEST digest mail on", millesime="2025")
        _veille(db, sid2, "page", "http://x/on", selecteur=r"20\d{2}")
        db.execute(text("UPDATE source_veille SET mail_alerte=true WHERE source_id=:s"), {"s": sid2})
        db.commit()
    http2 = _fake_http({"http://x/on": (200, {}, "2026")})
    with session_scope() as db:
        sentinelle.passer(db, source_ids=[sid2], forcer=True, http=http2, delai_s=0)
    assert len(envois) == 1 and "ops@labuse.test" in envois[0]
