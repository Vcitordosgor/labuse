"""FIX-GB-011 — le runner de migrations au boot et sa résilience.

Régression de GB-011 (audit GRAND BALAYAGE) : `courrier.ensure_tables` splittait le DDL sur `;`, ce qui
coupait un `;` PRÉSENT DANS UN COMMENTAIRE SQL → morceaux invalides → la migration courrier avortait à
chaque boot (colonnes n/communes/modele/corps jamais ajoutées), et — pire — sa levée abandonnait tout le
heal restant (cascade : crm_columns, veilles, comptes, scoping IDOR, copilote), le tout masqué par un
/readyz qui affichait schema.ok:true.

Trois garanties testées ici :
  1. un DDL avec des ';' dans les commentaires s'applique intégralement (courrier + principe du runner) ;
  2. un module de heal qui échoue n'empêche pas les suivants (isolation) ;
  3. /readyz reflète l'échec (schema.ok=false + module en cause), il ne ment plus.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db

_COLS_ATTENDUES = {"compte_id", "parcelles", "n", "communes", "modele", "corps", "statut", "updated_at"}


def _colonnes(engine, table: str) -> set[str]:
    with engine.begin() as c:
        rows = c.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = :t"), {"t": table})
        return {r[0] for r in rows}


# ── 1. Un DDL avec des ';' dans des commentaires s'applique ────────────────────────────────

def test_courrier_ensure_applique_le_schema_meme_depuis_une_table_ancienne(engine):
    """Reproduit EXACTEMENT GB-011 : une `courrier_demandes` héritée de l'ANCIEN schéma
    (sujet/idu/motif/texte, sans n/communes/modele/corps). Après ensure_tables, les colonnes
    du nouveau schéma DOIVENT être présentes et le SELECT du handler NE DOIT PAS lever."""
    from labuse import courrier
    # Table dans l'ANCIEN schéma EXACT de la base auditée : sujet/texte NOT NULL SANS défaut (le piège du
    # 2ᵉ volet), + une ligne legacy (statut='a_traiter', corps absent).
    with engine.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS courrier_demandes CASCADE"))
        c.execute(text("""
            CREATE TABLE courrier_demandes (
                id serial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(),
                sujet varchar(64) NOT NULL, idu varchar(14), motif text, texte text NOT NULL,
                statut varchar(24) NOT NULL DEFAULT 'a_traiter')"""))
        c.execute(text("INSERT INTO courrier_demandes (sujet, texte, statut) "
                       "VALUES ('legacy', 'ancien', 'a_traiter')"))

    # Le fix : ensure_tables réconcilie sans casser (idempotent, appelable deux fois).
    courrier.ensure_tables(engine)
    courrier.ensure_tables(engine)

    cols = _colonnes(engine, "courrier_demandes")
    manquantes = _COLS_ATTENDUES - cols
    assert not manquantes, f"colonnes du nouveau schéma non appliquées (bug GB-011) : {manquantes}"

    # Le SELECT du handler `demandes_de` (celui qui levait « column \"n\" does not exist ») passe.
    with engine.connect() as c:
        rows = courrier.demandes_de(c, None)      # ne lève pas ; corps NULL des legacy → filtrées
    assert isinstance(rows, list)

    # Le 2ᵉ volet : l'INSERT du handler (sans sujet/texte) NE VIOLE PLUS le not-null legacy.
    with engine.begin() as c:
        d = courrier.creer_demande(c, compte_id=None, parcelles=["97411000BZ1065"],
                                   communes="Saint-Denis", modele="libre", corps="[test]")
    assert d.get("id") and d.get("n") == 1


def test_le_principe_du_runner_un_point_virgule_en_commentaire_ne_casse_plus(engine):
    """Le point de fond de GB-011, isolé : un `split(";")` naïf CASSE un DDL dont un commentaire
    contient un ';' ; une LISTE de statements (l'approche du fix) l'applique proprement."""
    ddl_piege = (
        "-- création de la table ; note : ce point-virgule est DANS un commentaire\n"
        "CREATE TEMP TABLE gb011_piege (id int)")
    # (a) l'ancien découpage naïf produit un 1er morceau = commentaire tronqué + 2e = 'note : …' invalide
    morceaux = [s for s in ddl_piege.split(";") if s.strip()]
    assert len(morceaux) > 1, "le ';' du commentaire coupe bien le DDL en plusieurs morceaux (le piège)"
    # (b) l'approche du fix (statements en liste, aucun ';' interne) s'applique sans erreur
    with engine.begin() as c:
        for stmt in ("CREATE TEMP TABLE gb011_ok (id int)",):
            c.execute(text(stmt))
        n = c.execute(text("SELECT count(*) FROM gb011_ok")).scalar()
    assert n == 0


def test_sql_statements_ne_coupe_pas_sur_les_pieges():
    """FIX-GB-JAUNES (item 12) — le splitter partagé ne coupe jamais sur un `;` de commentaire, de bloc
    `$$` (partners/DO) ou de littéral. Remplace `DDL.split(';')` dans les 8 autres modules du heal."""
    from labuse.db import sql_statements
    # ';' dans un commentaire de ligne (le bug courrier, généralisé)
    s = sql_statements("-- note ; piège\nCREATE TABLE a(id int);\nCREATE INDEX i ON a(id);")
    assert len(s) == 2 and "CREATE TABLE" in s[0] and "CREATE INDEX" in s[1]
    # ';' internes dans un bloc dollar-quoté $$ … $$
    s = sql_statements("DO $$ BEGIN IF 1=1 THEN NULL; END IF; END $$;\nCREATE TABLE b(id int);")
    assert len(s) == 2 and s[0].startswith("DO") and "CREATE TABLE b" in s[1]
    # ';' dans un littéral chaîne
    s = sql_statements("INSERT INTO t VALUES ('a;b'); SELECT 1;")
    assert len(s) == 2
    # vide / commentaire seul → aucun statement
    assert sql_statements("  ;  -- rien\n") == []


# ── 2. Un module de heal qui échoue n'empêche pas les suivants ─────────────────────────────

def test_run_heal_steps_isole_les_echecs():
    """Cœur de la dé-cascade : le step KO au milieu N'ARRÊTE PAS les suivants ; l'échec est collecté."""
    from labuse.api.app import _run_heal_steps
    ran: list[str] = []

    def _boom():
        raise ValueError("boom")

    journal: list[str] = []
    fails = _run_heal_steps(
        (("a", lambda: ran.append("a")),
         ("courrier", _boom),                 # ← le module fautif de GB-011
         ("crm_columns", lambda: ran.append("crm_columns")),
         ("veilles", lambda: ran.append("veilles"))),
        on_echec=lambda mod, exc: journal.append(mod))

    assert ran == ["a", "crm_columns", "veilles"], "les modules APRÈS le KO doivent tourner (dé-cascade)"
    assert [f["module"] for f in fails] == ["courrier"]
    assert "ValueError: boom" in fails[0]["error"]
    assert journal == ["courrier"], "l'échec est journalisé (log + event_log)"


def test_run_heal_steps_tout_ok_aucune_erreur():
    from labuse.api.app import _run_heal_steps
    assert _run_heal_steps((("a", lambda: None), ("b", lambda: None))) == []


# ── 3. /readyz reflète l'échec (il ne ment plus) ───────────────────────────────────────────

@pytest.fixture
def client():
    from labuse.api.app import app
    return TestClient(app, base_url="https://testserver")


def test_readyz_dit_la_verite_quand_un_heal_a_echoue(client):
    """Avec un heal en échec, /readyz passe ready=false + schema.ok=false + le module en cause,
    et répond 503. Avant le fix il affichait schema.ok:true par-dessus (mensonge par omission)."""
    from labuse.api.app import app
    ancien = getattr(app.state, "schema_heal", None)
    try:
        app.state.schema_heal = {"ok": False, "failures": [
            {"module": "courrier", "error": "ProgrammingError: column \"n\" does not exist"}]}
        r = client.get("/readyz")
        assert r.status_code == 503
        body = r.json()
        assert body.get("ready") is False
        assert body.get("schema", {}).get("ok") is False
        assert "courrier" in body.get("schema", {}).get("heal_failed", [])
        assert body.get("heal", {}).get("ok") is False
    finally:
        app.state.schema_heal = ancien


def test_readyz_ne_force_pas_l_echec_quand_le_heal_est_ok(client):
    """Heal ok → /readyz ne force PAS ready=false (le statut dépend alors de state.readiness)."""
    from labuse.api.app import app
    ancien = getattr(app.state, "schema_heal", None)
    try:
        app.state.schema_heal = {"ok": True, "failures": []}
        body = client.get("/readyz").json()
        # heal ok n'ajoute pas de heal_failed ni de bloc heal d'échec
        assert "heal" not in body or body.get("heal", {}).get("ok") is not False
    finally:
        app.state.schema_heal = ancien


# ── 4. REMISE-1 (Lot A) — un VRAI verrou Postgres tenu pendant le heal → le heal converge, readyz 200 ─

def test_remise1_heal_converge_malgre_un_verrou_tenu_puis_readyz_200(engine, client, monkeypatch):
    """Simule EXACTEMENT l'incident DEPLOY-1028b : un lecteur concurrent TIENT un verrou sur la table
    que le heal doit ALTER (comme `pige_biens` pendant que le job `fiche-commune-cache` lisait). Avec le
    correctif (moteur de heal à `lock_timeout` court + `_run_heal_steps` qui réessaie), l'ALTER échoue
    VITE au 1er essai (verrou tenu) puis CONVERGE une fois le verrou relâché — au lieu de rester bloqué
    → `heal_failed` définitif. Puis on prouve le bout final : heal convergé ⇒ `/readyz` 200."""
    import threading
    import time as _t

    from sqlalchemy import event as _sa_event

    from labuse.api.app import _run_heal_steps, app
    from labuse.db import make_engine

    table = "remise1_heal_cible"
    with engine.begin() as c:
        c.execute(text(f"DROP TABLE IF EXISTS {table}"))
        c.execute(text(f"CREATE TABLE {table} (id int)"))

    # (1) un « lecteur » tient un verrou ACCESS SHARE sur la cible ~2,5 s (conflit avec l'ALTER qui
    #     veut ACCESS EXCLUSIVE), puis le relâche (commit) — comme le job de réchauffage finit par le faire.
    pret = threading.Event()

    def _tenir_verrou():
        with engine.connect() as c, c.begin():
            c.execute(text(f"LOCK TABLE {table} IN ACCESS SHARE MODE"))
            pret.set()
            _t.sleep(2.5)
        # sortie du bloc begin() → COMMIT → verrou relâché

    th = threading.Thread(target=_tenir_verrou, daemon=True)
    th.start()
    assert pret.wait(5), "le verrou lecteur aurait dû être pris"

    # (2) moteur de HEAL dédié avec lock_timeout COURT (1 s) — reproduit `_lifespan`.
    heal_eng = make_engine()

    @_sa_event.listens_for(heal_eng, "connect")
    def _lt(_dbapi, _rec):  # noqa: ANN001
        cur = _dbapi.cursor()
        try:
            cur.execute("SET lock_timeout = '1s'")
        finally:
            cur.close()

    def _alter_pige():
        with heal_eng.begin() as c:
            c.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS retiree_le timestamptz"))

    retries: list[int] = []
    try:
        fails = _run_heal_steps((("pige", _alter_pige),), essais=8, pause_s=0.5,
                                on_retry=lambda _m, t, _e: retries.append(t))
    finally:
        heal_eng.dispose()
    th.join(timeout=5)

    assert fails == [], f"le heal aurait dû CONVERGER après relâche du verrou ; échecs={fails}"
    assert retries, "le 1er ALTER a bien été bloqué par le verrou (≥ 1 réessai) — sinon le test ne prouve rien"
    assert "retiree_le" in _colonnes(engine, table), "la colonne ALTER a fini par être posée"

    # (3) bout final : heal convergé ⇒ /readyz 200. On isole le contrat heal→readyz en rendant
    #     state.readiness « prêt » (la base de test peut manquer de données métier, hors sujet ici).
    from labuse import state
    monkeypatch.setattr(state, "readiness",
                        lambda _s, _n: {"ready": True, "checked_at": "2026-10-28T00:00:00+04:00",
                                        "schema": {"ok": True}})
    ancien = getattr(app.state, "schema_heal", None)
    try:
        app.state.schema_heal = {"ok": not fails, "failures": fails, "total": 1}
        r = client.get("/readyz")
        assert r.status_code == 200, f"heal convergé ⇒ readyz devait être 200, got {r.status_code}"
        assert r.json().get("ready") is True
    finally:
        app.state.schema_heal = ancien
        with engine.begin() as c:
            c.execute(text(f"DROP TABLE IF EXISTS {table}"))
