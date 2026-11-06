"""NU4-FIX-1 — Lot A (sécurité). Reproductions ROUGE→VERTE des trouvailles du rapport
`docs/audit-2026-11/nu-4/A/RAPPORT.md`.

Couvre :
- M2/M3/Y1/Y2 : les 4 routes qui écrivaient de l'état PARTAGÉ/global hors `/admin` sans garde
  exigent désormais l'admin (403 pour un client non-admin). Régression : les routes sœurs
  déjà gardées (`/parcels/{idu}/evaluate`, `/bilan/params`, `/partners/profiles`,
  `/modules/division/compute`) le restent.
- Garde STRUCTURELLE : toute route mutante hors `/admin` doit être classée (publique-par-conception,
  mutation-globale-gardée-admin, ou tenant-scopée). Une NOUVELLE route non classée fait ÉCHOUER le
  test → on ne peut plus ajouter en douce une écriture « pour tous » sans garde.
- M1 : la limite d'essais 2FA est tenue EN BASE (verrou comme le mot de passe) — rejouer le vieux
  cookie `n=0` ne donne plus des essais illimités ; `/login/2fa` passe sous rate-limit.
- Y3 : le jeton de désinscription se compare en TEMPS CONSTANT (`hmac.compare_digest`).
"""
from __future__ import annotations

import inspect
import re
import uuid
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse import comptes, totp
from labuse.api import auth, events, protection
from labuse.db import session_scope

# ───────────────────────── Lot A — routes sous garde (unitaire, auth simulée) ─────────────────────────

#: routes NON-admin qui écrivent de l'état PARTAGÉ/global → doivent exiger l'admin (403 non-admin).
#: Les 4 premières sont les trouvailles NU4-FIX-1 (M2 ×3, Y2) ; veilles/evaluer = Y1 ;
#: pas-une-piscine = M3 ; les 4 dernières sont les SŒURS déjà gardées (régression).
GARDE_ADMIN_A_PROUVER: dict[str, tuple[str, dict | None]] = {
    "/audit/reference": ("POST", {"section": "AB", "numero": "1"}),
    "/audit/adresse": ("POST", {"q": "3 chemin de la Citerne 97417"}),
    "/audit/polygone": ("POST", {"geometry": {"type": "Polygon", "coordinates": []}}),
    "/sources/1/test": ("POST", None),
    "/api/copilote-v2/veilles/evaluer": ("POST", None),
    "/modules/prospection-piscines/pas-une-piscine": ("POST", {"idu": "974110000A0001", "motif": "x"}),
    "/parcels/974110000A0001/evaluate": ("POST", None),
    "/bilan/params": ("POST", {"secteur": "*", "param": "foncier_pct", "value": 1.0}),
    "/modules/division/compute": ("POST", None),
    "/partners/profiles": ("POST", {"nom": "x", "secteurs": [], "budget_min": 0, "budget_max": 1}),
}


@pytest.fixture
def client_non_admin(monkeypatch):
    """TestClient avec auth ACTIVE (simulée) et une session CLIENT NON-ADMIN posée : exactement la
    posture de prod où un client payant atteint ces routes. En local l'auth est off (tout répond
    200) — on la force ici pour prouver le garde par le code servi, sans prod ni base."""
    from labuse.api.app import app
    monkeypatch.setattr(auth, "enabled", lambda: True)
    monkeypatch.setattr(
        auth, "session_info",
        lambda cookie: ({"utilisateur_id": 1, "compte_id": 1, "role": "titulaire",
                         "statut_compte": "actif", "acces": "complet"} if cookie else None))
    c = TestClient(app, base_url="https://testserver")
    c.cookies.set(auth.COOKIE, "u.session-client-non-admin")
    return c


def test_routes_ecriture_globale_exigent_admin(client_non_admin):
    """ROUGE avant NU4-FIX-1 : un client non-admin passait (200/422/500). VERT : 403 partout."""
    for chemin, (methode, body) in GARDE_ADMIN_A_PROUVER.items():
        r = client_non_admin.request(methode, chemin, json=body)
        assert r.status_code == 403, (
            f"{methode} {chemin} devrait être réservé à l'admin (403), reçu {r.status_code}")


# ───────────────────────── Lot A — garde structurelle (registre des routes mutantes) ─────────────────────────

#: publiques PAR CONCEPTION : sécurité = jeton signé / signature / rate-limit, jamais une session.
_PUBLIQUES = {
    "/login", "/login/2fa", "/logout", "/reset", "/reset-demande", "/invitation",
    "/flash", "/onboarding/paiement", "/stripe/webhook", "/events/desabonner", "/protection/defi",
}
#: préfixes des routes TENANT (scopées `compte_id` / outils analytiques du client, derrière la
#: garde de session). Classées APRÈS les deux ensembles exacts ci-dessus/-dessous (priorité).
_PREFIXES_TENANT = (
    # NU5-FIX-1 (C-F5/F6) — /compte/export + /compte/supprimer agissent UNIQUEMENT sur le compte de la
    # session (compte_ou_401, jamais cross-tenant) → tenant-scopées, pas des mutations globales.
    "/compte",
    "/alertes", "/api/copilote-v2", "/bilan-ratios", "/bilan/", "/courrier",
    "/documents", "/events", "/feedback", "/filters", "/financier", "/ia",
    "/modules", "/moi", "/moteurs", "/onboarding", "/outils", "/parcels",
    "/partners/share", "/pipeline", "/projets", "/radar", "/retours",
    "/scoreur-adresse", "/signalements", "/suggestions", "/traducteur-plu",
    "/usage", "/watch-zones",
)
#: mutation GLOBALE (état partagé) → DOIT être admin. Union des routes prouvées ci-dessus + les
#: siblings à paramètre (partners/profiles) ; `/bilan/params` et `/parcels/.../evaluate` sont
#: des motifs, pas des chemins fixes → repérés par préfixe exact ci-dessous.
_GLOBAL_ADMIN_EXACTS = {
    "/audit/reference", "/audit/adresse", "/audit/polygone",
    "/sources/{source_id}/test", "/api/copilote-v2/veilles/evaluer",
    "/modules/prospection-piscines/pas-une-piscine",
    "/bilan/params", "/parcels/{idu}/evaluate", "/partners/profiles",
    "/modules/division/compute",
}


def _routes_mutantes_hors_admin() -> list[str]:
    from labuse.api.app import app
    from labuse.api.app import _est_chemin_admin
    out = []
    for r in app.router.routes:
        methods = getattr(r, "methods", None) or set()
        if not (methods & {"POST", "PUT", "PATCH", "DELETE"}):
            continue
        p = getattr(r, "path", "")
        if p.startswith("/admin") or _est_chemin_admin(p):
            continue                       # fail-safe middleware : segment /admin déjà gardé
        out.append(p)
    return sorted(set(out))


def _classe(p: str) -> str | None:
    if p in _PUBLIQUES:
        return "publique"
    if p in _GLOBAL_ADMIN_EXACTS:
        return "global-admin"
    for pref in _PREFIXES_TENANT:
        if p == pref or p.startswith(pref):
            return "tenant"
    return None


def test_aucune_route_mutante_non_classee():
    """Garde-cliquet : toute route mutante hors `/admin` doit tomber dans une classe REVUE. Une
    NOUVELLE route non classée casse ce test → l'auteur DOIT la classer (si elle écrit « pour
    tous », elle va dans `_GLOBAL_ADMIN_EXACTS` ET porte `exiger_admin`)."""
    non_classees = [p for p in _routes_mutantes_hors_admin() if _classe(p) is None]
    assert not non_classees, (
        "Routes mutantes hors /admin NON classées (NU4-FIX-1 garde structurelle) — classez-les "
        "(publique-par-conception / tenant-scopée / mutation-globale→exiger_admin) :\n  "
        + "\n  ".join(non_classees))


def test_les_quatre_trouvailles_sont_au_registre_global():
    """M2/M3/Y1/Y2 sont bien marquées comme mutations globales à garder (pas rangées en tenant)."""
    for p in ("/audit/reference", "/audit/adresse", "/audit/polygone",
              "/sources/{source_id}/test", "/api/copilote-v2/veilles/evaluer",
              "/modules/prospection-piscines/pas-une-piscine"):
        assert _classe(p) == "global-admin"


# ───────────────────────── Lot A/Y3 — jeton de désinscription en temps constant ─────────────────────────

class _FakeRes:
    def __init__(self, v):
        self._v = v

    def scalar(self):
        return self._v


class _FakeDB:
    def __init__(self, v):
        self._v = v

    def execute(self, *a, **k):
        return _FakeRes(self._v)


def test_token_desabonnement_compare_digest():
    assert "compare_digest" in inspect.getsource(events._token_ok)   # la primitive est bien celle-là
    assert events._token_ok(_FakeDB("jetonsecret"), 1, "jetonsecret") is True
    assert events._token_ok(_FakeDB("jetonsecret"), 1, "jetonsecreu") is False
    assert events._token_ok(_FakeDB(None), 1, "jetonsecret") is False   # compte sans jeton
    assert events._token_ok(_FakeDB("jetonsecret"), 1, "") is False     # jeton vide


# ───────────────────────── Lot A/M1 — rate-limit sur /login/2fa ─────────────────────────

def test_login_2fa_sous_rate_limit():
    """`/login/2fa` rejoint les préfixes rate-limités (per-IP) : une force brute du TOTP
    (~2,5 essais/s) dépasse le 60/min et déclenche le défi/gel (défense en profondeur)."""
    assert "/login/2fa" in protection.PREFIXES_PROTEGES


# ───────────────────────── Lot A/M1 — limite 2FA tenue EN BASE (verrou serveur) ─────────────────────────

pytestmark_db = pytest.mark.db
MDP = "mot-de-passe-2fa-974"
SECRET_RFC = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


@pytest.fixture
def pilot(monkeypatch):
    from labuse import config
    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "mot-de-passe-pilote")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "clef-de-test-stable")
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.fixture
def client(engine):
    from labuse.api.app import app
    return TestClient(app, base_url="https://testserver")


def _utilisateur_admin() -> tuple[str, int]:
    email = f"test-nu4fix-{uuid.uuid4().hex[:10]}@exemple.test"
    with session_scope() as db:
        comptes.ensure_tables(db)
        inv = comptes.creer_invitation(db, email)
        tok = inv["lien"].split("token=")[1]
        comptes.activer_par_invitation(db, tok, MDP, "2026-07-22")
        db.execute(text("UPDATE comptes SET statut = 'actif' WHERE id = :c"), {"c": inv["compte_id"]})
        db.execute(text("UPDATE utilisateurs SET role = 'admin' WHERE id = :i"),
                   {"i": inv["utilisateur_id"]})
        db.commit()
    return email, int(inv["utilisateur_id"])


def _login(client, email):
    return client.post("/login", content=urlencode({"identifiant": email, "password": MDP}),
                       headers={"content-type": "application/x-www-form-urlencoded"},
                       follow_redirects=False)


def _poster_code(client, code, cookie_2fa):
    client.cookies.clear()
    return client.post("/login/2fa", content=urlencode({"code": code}),
                       headers={"content-type": "application/x-www-form-urlencoded"},
                       cookies={auth.COOKIE_2FA: cookie_2fa}, follow_redirects=False)


@pytest.mark.db
def test_limite_2fa_en_base_rejeu_cookie_zero(client, pilot):
    """ROUGE (audit M1) : rejouer le cookie `n=0` donnait des essais ILLIMITÉS (1000/1000).
    VERT : après `login_echecs_max` échecs, le compte est GELÉ en base ; le même cookie `n=0`
    (toujours structurellement valide) ne sert plus à rien, et même un bon code est refusé."""
    from labuse import config
    email, uid = _utilisateur_admin()

    # enrôlement : login → défi, poser le code d'enrôlement (secret lu sur la page)
    r = _login(client, email)
    assert r.status_code == 303 and r.headers["location"] == "/login/2fa"
    c0 = re.search(r"labuse_2fa=([^;]+)", r.headers["set-cookie"]).group(1)
    page = client.get("/login/2fa")
    secret = re.search(r'id="totp-secret"[^>]*>([^<]+)<', page.text).group(1).replace(" ", "")
    r = _poster_code(client, totp.code_totp(secret), c0)
    assert r.status_code == 200 and "codes de secours" in r.text     # enrôlé + session
    client.get("/logout", follow_redirects=False)

    # re-login → nouveau défi n=0 ; on va REJOUER ce cookie à l'identique (l'attaque M1)
    r = _login(client, email)
    c0 = re.search(r"labuse_2fa=([^;]+)", r.headers["set-cookie"]).group(1)
    assert auth.defi_2fa_lire(c0) == (uid, 0)                        # cookie valide, n=0

    faux = "000000" if totp.code_totp(secret) != "000000" else "000001"
    seuil = config.get_settings().login_echecs_max
    for _ in range(seuil):
        _poster_code(client, faux, c0)          # chaque échec est compté EN BASE (pas le cookie)
        assert auth.defi_2fa_lire(c0) == (uid, 0)   # le cookie rejoué reste « n=0 » — inopérant

    # verrou base atteint : rejouer c0 (n=0) ne relance plus rien → 429
    r = _poster_code(client, faux, c0)
    assert r.status_code == 429
    with session_scope() as db:
        assert comptes.verrou_2fa_restant(db, uid) is True

    # et même le BON code (pas suivant, non rejoué) est refusé tant que le verrou tient
    import time as _t
    bon = totp.code_totp(secret, t=_t.time() + 30)
    r = _poster_code(client, bon, c0)
    assert r.status_code == 429
    assert client.get("/pipeline/meta").status_code == 401           # aucune session ouverte


@pytest.mark.db
def test_verrou_2fa_se_leve_sur_succes(client, pilot):
    """Le compteur/verrou 2FA se remet à zéro sur un succès (comme echecs_login)."""
    email, uid = _utilisateur_admin()
    with session_scope() as db:
        comptes.totp_preparer(db, uid)
        comptes.enregistrer_echec_2fa(db, uid)
        comptes.enregistrer_echec_2fa(db, uid)
        assert db.execute(text("SELECT echecs_2fa FROM totp_2fa WHERE utilisateur_id=:u"),
                          {"u": uid}).scalar() == 2
        comptes.reinit_echec_2fa(db, uid)
        assert db.execute(text("SELECT echecs_2fa FROM totp_2fa WHERE utilisateur_id=:u"),
                          {"u": uid}).scalar() == 0
        assert comptes.verrou_2fa_restant(db, uid) is False
