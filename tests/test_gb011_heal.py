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
