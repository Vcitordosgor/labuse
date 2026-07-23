"""Protection anti-scraping (mandat wave-adresses, Lot 3) — Phase 0 : session/IP.

AUCUN système de comptes n'existe (auth pilote = mot de passe unique) : le « sujet »
des quotas est le hash de la session (cookie) sinon de l'IP. Le mandat Auth & Plans
substituera l'identifiant de siège sans changer la mécanique.

Quatre briques :
 1. QUOTA de consultation de fiches parcelle / jour (défaut 300, config) — dépassement
    → 429 + gel des consultations jusqu'à minuit (persisté : usage_compteurs).
 2. RATE LIMITING applicatif (défaut 60 req/min, config) sur les endpoints métier —
    burst → défi arithmétique léger (« captcha ») ; récidive (N bursts/jour) → gel
    du sujet + alerte admin.
 3. DÉTECTION DE PATTERNS (job quotidien `labuse abuse-scan`, cron.d/abuse) → table
    abuse_scores. JAMAIS de blocage automatique sur le score (faux positifs) : le gel
    reste une décision manuelle de Vic.
 4. WATERMARKING des exports : colonne `ref` (HMAC sujet+date) + 2-3 enregistrements
    canari (micro-variations de formatage d'adresses réelles, uniques par sujet) →
    table export_fingerprints pour retrouver la source d'une fuite.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import random
import re
import statistics
import threading
import time
from collections import defaultdict, deque
from datetime import date, datetime, timedelta, timezone

import anyio
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .. import config

log = logging.getLogger("labuse.protection")
router = APIRouter(prefix="/protection", tags=["protection"])

DDL = """
CREATE TABLE IF NOT EXISTS usage_compteurs (
  jour   date NOT NULL,
  sujet  varchar(24) NOT NULL,
  kind   varchar(16) NOT NULL,        -- 'fiche' | 'burst' | 'export' | 'nl' | 'dossier'
  n      integer NOT NULL DEFAULT 0,
  PRIMARY KEY (jour, sujet, kind)
);
CREATE TABLE IF NOT EXISTS consultation_log (
  id bigserial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(),
  sujet varchar(24) NOT NULL, chemin varchar(64), idu varchar(14)
);
CREATE INDEX IF NOT EXISTS consultation_log_ts_idx ON consultation_log (ts, sujet);
CREATE TABLE IF NOT EXISTS acces_gels (
  sujet varchar(24) PRIMARY KEY, motif text, ts timestamptz NOT NULL DEFAULT now(),
  actif boolean NOT NULL DEFAULT true
);
CREATE TABLE IF NOT EXISTS admin_alertes (
  id serial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(),
  kind varchar(24), detail text, vu boolean NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS abuse_scores (
  id serial PRIMARY KEY, jour date NOT NULL, sujet varchar(24) NOT NULL,
  score integer NOT NULL, signaux jsonb NOT NULL DEFAULT '{}'::jsonb,
  computed_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (jour, sujet)
);
CREATE TABLE IF NOT EXISTS export_fingerprints (
  id serial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(),
  sujet varchar(24) NOT NULL, ref varchar(16) NOT NULL, format varchar(16),
  slug varchar(64), n_lignes integer, canaris jsonb NOT NULL DEFAULT '[]'::jsonb
);
CREATE INDEX IF NOT EXISTS export_fingerprints_ref_idx ON export_fingerprints (ref);
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        for stmt in DDL.strip().split(";"):
            if stmt.strip():
                c.execute(text(stmt))


# ── Sujet (session sinon IP) ────────────────────────────────────────────────────────────

def ip_reelle(request: Request) -> str:
    """IP du client. Derrière un proxy de CONFIANCE (config trusted_proxies), l'IP réelle
    est extraite de X-Forwarded-For — 1er hop non-proxy en partant de la DROITE (la gauche
    de l'en-tête est forgeable par le client). Pair inconnu → on garde l'IP du pair :
    jamais de confiance aveugle dans un en-tête."""
    peer = getattr(getattr(request, "client", None), "host", "?") or "?"
    proxies = {p.strip() for p in config.get_settings().trusted_proxies.split(",") if p.strip()}
    if peer in proxies:
        hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",")]
        for hop in reversed(hops):
            if hop and hop not in proxies:
                return hop
    return peer


def sujet_de(request: Request) -> str:
    cookie = request.cookies.get("labuse_session")
    if cookie:
        return "s:" + hashlib.sha256(cookie.encode()).hexdigest()[:20]
    return "ip:" + hashlib.sha256(ip_reelle(request).encode()).hexdigest()[:20]


def _cle_hmac() -> bytes:
    s = config.get_settings()
    return (s.secret_key or "labuse-protection").encode()


# ── État mémoire (rapide) + écriture DB (persistance gel/minuit) ────────────────────────

_lock = threading.Lock()
_fenetres: dict[str, deque] = defaultdict(deque)        # sujet → timestamps (60 s)
_fiches_jour: dict[tuple[str, str], set] = {}           # (jour, sujet) → idus vus (dédup)
_bursts_jour: dict[tuple[str, str], int] = defaultdict(int)   # épisodes de burst du jour
_gels_cache: dict = {"at": 0.0, "sujets": {}}           # TTL 30 s
_defis: dict[str, tuple[int, int, float]] = {}          # sujet → (a, b, expiry) — réponse a+b

#: préfixes des endpoints métier soumis au rate limiting (jamais les statiques/tuiles —
#: une carte qui panne charge des dizaines de tuiles/s, ce n'est pas du scraping).
PREFIXES_PROTEGES = ("/parcels", "/segments", "/discover", "/ia", "/moteurs", "/map/parcels",
                     "/map/mutation", "/map/permits", "/map/layers", "/map/bati", "/dossier",
                     "/pre-dossier", "/courrier")

_FICHE_RE = re.compile(r"^/parcels/([0-9]{5}[0-9A-Z]{9})$")


def _aujourdhui() -> str:
    return date.today().isoformat()


def reset_etat_memoire() -> None:
    """Tests : repartir d'un état mémoire vierge."""
    with _lock:
        _fenetres.clear()
        _fiches_jour.clear()
        _bursts_jour.clear()
        _gels_cache.update(at=0.0, sujets={})
        _defis.clear()


def _db_exec(sql: str, params: dict) -> None:
    from ..db import engine
    with engine().begin() as c:
        c.execute(text(sql), params)


def _incr_compteur(jour: str, sujet: str, kind: str, n: int = 1) -> None:
    _db_exec(
        "INSERT INTO usage_compteurs (jour, sujet, kind, n) VALUES (:j, :s, :k, :n) "
        "ON CONFLICT (jour, sujet, kind) DO UPDATE SET n = usage_compteurs.n + :n",
        {"j": jour, "s": sujet, "k": kind, "n": n})


def compteur(db, sujet: str, kind: str, jour: str | None = None) -> int:
    return int(db.execute(text(
        "SELECT n FROM usage_compteurs WHERE jour = :j AND sujet = :s AND kind = :k"),
        {"j": jour or _aujourdhui(), "s": sujet, "k": kind}).scalar() or 0)


def _fiches_vues(jour: str, sujet: str) -> set:
    """Cache mémoire des fiches vues (dédup rechargée de la base au premier accès du jour)."""
    key = (jour, sujet)
    if key not in _fiches_jour:
        try:
            from ..db import engine
            with engine().connect() as c:
                n = int(c.execute(text(
                    "SELECT n FROM usage_compteurs WHERE jour = :j AND sujet = :s AND kind = 'fiche'"),
                    {"j": jour, "s": sujet}).scalar() or 0)
        except Exception:  # noqa: BLE001 — DB indisponible : ne bloque pas le trafic
            n = 0
        _fiches_jour[key] = set(range(n))     # placeholder : seul le CARDINAL compte
    return _fiches_jour[key]


def _gele(sujet: str) -> str | None:
    """Motif du gel si le sujet est gelé (cache 30 s)."""
    now = time.monotonic()
    if now - _gels_cache["at"] > 30.0:
        try:
            from ..db import engine
            with engine().connect() as c:
                rows = c.execute(text(
                    "SELECT sujet, motif FROM acces_gels WHERE actif")).all()
            _gels_cache.update(at=now, sujets=dict(rows))
        except Exception:  # noqa: BLE001
            _gels_cache["at"] = now
    return _gels_cache["sujets"].get(sujet)


def geler(db, sujet: str, motif: str) -> None:
    db.execute(text(
        "INSERT INTO acces_gels (sujet, motif) VALUES (:s, :m) "
        "ON CONFLICT (sujet) DO UPDATE SET motif = :m, actif = true, ts = now()"),
        {"s": sujet, "m": motif})
    db.execute(text("INSERT INTO admin_alertes (kind, detail) VALUES ('gel', :d)"),
               {"d": f"{sujet} : {motif}"})
    _gels_cache["at"] = 0.0
    log.warning("GEL %s : %s", sujet, motif)


def degeler(db, sujet: str) -> None:
    db.execute(text("UPDATE acces_gels SET actif = false WHERE sujet = :s"), {"s": sujet})
    _gels_cache["at"] = 0.0


# ── Middleware ──────────────────────────────────────────────────────────────────────────

def _actif_sous_pytest() -> bool:
    """Sous pytest, la garde ne s'active QUE si un réglage de protection est posé
    explicitement (les suites existantes martèlent l'API à des cadences irréalistes —
    même précédent que auth.slow_failure)."""
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    return bool(os.environ.get("LABUSE_RATE_LIMIT_RPM")
                or os.environ.get("LABUSE_QUOTA_FICHES_JOUR"))


async def garde_protection(request: Request, call_next):
    """Rate limiting + quota fiches — s'exécute APRÈS l'auth (trafic authentifié)."""
    path = request.url.path
    if request.method == "OPTIONS" or not path.startswith(PREFIXES_PROTEGES) \
            or not _actif_sous_pytest():
        return await call_next(request)
    s = config.get_settings()
    if s.dev_mode:
        # Exemption DEV EXPLICITE (flag d'env, jamais une détection localhost — derrière
        # nginx tout arrive en 127.0.0.1). Quotas + rate-limit court-circuités.
        return await call_next(request)
    # M7 — voie QA prod : IP explicitement allowlistée (golden/monitoring) → exemptée,
    # SANS toucher au régime des autres clients (jamais dev_mode sur une machine publique).
    if s.qa_allowlist and ip_reelle(request) in {x.strip() for x in s.qa_allowlist.split(",") if x.strip()}:
        return await call_next(request)
    sujet = sujet_de(request)
    jour = _aujourdhui()
    now = time.time()

    motif = await anyio.to_thread.run_sync(_gele, sujet)
    if motif:
        return JSONResponse(status_code=429, content={
            "detail": f"Accès suspendu ({motif}). Contactez LABUSE pour le rétablir.",
            "gel": True})

    defi, episode_nouveau, nb_bursts = None, False, 0
    with _lock:
        fen = _fenetres[sujet]
        fen.append(now)
        while fen and fen[0] < now - 60.0:
            fen.popleft()
        if len(fen) > max(1, s.rate_limit_rpm):
            actif = _defis.get(sujet)
            if not actif or actif[2] < now:
                # nouvel ÉPISODE de burst (pas un simple dépassement de plus) : un défi
                # actif = même épisode, on ne recompte pas — sinon 3 requêtes au-dessus
                # du seuil gèleraient un utilisateur légitime un peu pressé.
                _bursts_jour[(jour, sujet)] += 1
                episode_nouveau = True
                _defis[sujet] = (random.randint(3, 19), random.randint(2, 9), now + 600)
            nb_bursts = _bursts_jour[(jour, sujet)]
            a, b, _exp = _defis[sujet]
            defi = f"{a} + {b}"

    if defi is not None:
        if episode_nouveau:
            await anyio.to_thread.run_sync(
                lambda: _incr_compteur(jour, sujet, "burst"))
        if episode_nouveau and nb_bursts >= max(1, s.rate_burst_gel):
            def _gel_recidive():
                from ..db import session_scope
                with session_scope() as db:
                    geler(db, sujet, f"récidive rate-limit ({nb_bursts} bursts le {jour})")
            await anyio.to_thread.run_sync(_gel_recidive)
            return JSONResponse(status_code=429, content={
                "detail": "Trop de rafales de requêtes aujourd'hui — accès suspendu, "
                          "l'équipe LABUSE a été alertée.", "gel": True})
        return JSONResponse(status_code=429, content={
            "detail": f"Trop de requêtes (max {s.rate_limit_rpm}/min). "
                      "Résolvez le défi pour continuer.",
            "defi": defi, "poster": "/protection/defi"})

    m = _FICHE_RE.match(path)
    if m and request.method == "GET":
        idu = m.group(1)
        vues = _fiches_vues(jour, sujet)
        if idu not in vues and len(vues) >= max(1, s.quota_fiches_jour):
            return JSONResponse(status_code=429, content={
                "detail": f"Quota de consultation atteint ({s.quota_fiches_jour} fiches "
                          "parcelle/jour). Les consultations reprennent à minuit.",
                "quota": s.quota_fiches_jour, "gel_jusqua": "minuit"})
        if idu not in vues:
            vues.add(idu)
            def _persiste():
                _incr_compteur(jour, sujet, "fiche")
                _db_exec("INSERT INTO consultation_log (sujet, chemin, idu) "
                         "VALUES (:s, :c, :i)", {"s": sujet, "c": "fiche", "i": idu})
            await anyio.to_thread.run_sync(_persiste)
    elif path.startswith(("/map/parcels", "/parcels/export")):
        # dump massif potentiel : journalisé (signal volume du job abuse-scan)
        await anyio.to_thread.run_sync(
            lambda: _db_exec("INSERT INTO consultation_log (sujet, chemin) VALUES (:s, :c)",
                             {"s": sujet, "c": path[:64]}))
    return await call_next(request)


@router.post("/defi")
async def repondre_defi(request: Request) -> JSONResponse:
    """Défi arithmétique léger (anti-burst) : bonne réponse → 10 min de répit."""
    sujet = sujet_de(request)
    try:
        reponse = int((await request.json()).get("reponse"))
    except Exception:  # noqa: BLE001
        return JSONResponse(status_code=422, content={"detail": "réponse numérique attendue"})
    actif = _defis.get(sujet)
    if not actif or actif[2] < time.time():
        return JSONResponse(status_code=410, content={"detail": "défi expiré — réessayez"})
    if reponse != actif[0] + actif[1]:
        return JSONResponse(status_code=403, content={"detail": "réponse incorrecte"})
    with _lock:
        _defis.pop(sujet, None)     # fin d'épisode : fenêtre purgée, la limite NORMALE
        _fenetres[sujet].clear()    # reprend (jamais de passe-droit prolongé)
    return JSONResponse(content={"ok": True})


# ── Admin (Vic — couvert par l'auth globale comme les routes admin des segments) ────────

@router.get("/admin")
def protection_admin() -> dict:
    """Tableau de bord : alertes récentes, scores du dernier scan, gels actifs."""
    from ..db import session_scope
    with session_scope() as db:
        alertes = [dict(r) for r in db.execute(text(
            "SELECT id, ts, kind, detail, vu FROM admin_alertes "
            "ORDER BY ts DESC LIMIT 50")).mappings()]
        scores = [dict(r) for r in db.execute(text(
            "SELECT jour, sujet, score, signaux FROM abuse_scores "
            "ORDER BY jour DESC, score DESC LIMIT 50")).mappings()]
        gels = [dict(r) for r in db.execute(text(
            "SELECT sujet, motif, ts FROM acces_gels WHERE actif ORDER BY ts DESC")).mappings()]
    return {"alertes": alertes, "scores": scores, "gels": gels,
            "doctrine": "gel MANUEL uniquement — le score n'entraîne jamais de blocage auto"}


@router.post("/admin/gel/{sujet}")
def protection_gel(sujet: str, motif: str = "décision admin") -> dict:
    from ..db import session_scope
    with session_scope() as db:
        geler(db, sujet, motif)
    return {"ok": True, "sujet": sujet, "gele": True}


@router.post("/admin/degel/{sujet}")
def protection_degel(sujet: str) -> dict:
    from ..db import session_scope
    with session_scope() as db:
        degeler(db, sujet)
    return {"ok": True, "sujet": sujet, "gele": False}


# ── Watermarking des exports (Lot 3.4) ──────────────────────────────────────────────────

#: micro-variations de FORMATAGE (jamais de fausse donnée) — chacune survit à Excel.
_ABREV_VOIE = [("Rue ", "R. "), ("Chemin ", "Chem. "), ("Avenue ", "Av. "),
               ("Boulevard ", "Bd "), ("Allée ", "All. "), ("Impasse ", "Imp. ")]


def _variation(valeur: str, mode: int) -> str | None:
    """Applique la micro-variation `mode` à une voie — None si inapplicable."""
    if not valeur:
        return None
    if mode == 0:
        for long_, court in _ABREV_VOIE:
            if valeur.startswith(long_):
                return court + valeur[len(long_):]
        return None
    if mode == 1 and valeur[0].isupper():
        return valeur[0].lower() + valeur[1:]
    if mode == 2 and " " in valeur:
        i = valeur.index(" ")
        return valeur[:i] + "  " + valeur[i + 1:]
    return None


def filigrane_export(db, sujet: str, headers: list[str], rows: list[list],
                     *, slug: str, fmt: str = "csv") -> str:
    """Filigrane un export EN PLACE : colonne `ref` + 2-3 canaris → export_fingerprints.

    Retourne la `ref`. Les canaris sont des lignes RÉELLES dont seule la mise en forme
    de la voie varie (traçable, jamais une fausse adresse). Déterministe par (sujet, jour).
    """
    jour = _aujourdhui()
    ref = hmac.new(_cle_hmac(), f"{sujet}:{jour}".encode(), hashlib.sha256).hexdigest()[:10]
    headers.append("ref")
    for r in rows:
        r.append(ref)
    canaris: list[dict] = []
    try:
        col_voie = next(i for i, h in enumerate(headers) if "Voie" in h or "Adresse" in h)
    except StopIteration:
        col_voie = None
    if col_voie is not None and rows:
        rng = random.Random(ref)                      # déterministe par sujet+jour
        indices = rng.sample(range(len(rows)), min(3, len(rows)))
        for n, i in enumerate(indices):
            v = rows[i][col_voie]
            variee = _variation(str(v or ""), (rng.randint(0, 2) + n) % 3)
            if variee:
                rows[i][col_voie] = variee
                canaris.append({"ligne": i, "idu": str(rows[i][0]),
                                "avant": v, "apres": variee})
    db.execute(text(
        "INSERT INTO export_fingerprints (sujet, ref, format, slug, n_lignes, canaris) "
        "VALUES (:s, :r, :f, :g, :n, :c)"),
        {"s": sujet, "r": ref, "f": fmt, "g": slug, "n": len(rows),
         "c": json.dumps(canaris, ensure_ascii=False)})
    _db_exec("INSERT INTO usage_compteurs (jour, sujet, kind, n) VALUES (:j, :s, 'export', 1) "
             "ON CONFLICT (jour, sujet, kind) DO UPDATE SET n = usage_compteurs.n + 1",
             {"j": jour, "s": sujet})
    return ref


# ── Détection de patterns (Lot 3.3 — job quotidien, JAMAIS de blocage auto) ─────────────

def scan_abus(db, jour: date | None = None) -> dict:
    """Score les sujets du jour (séquences d'IDU, régularité machinale, volume nocturne,
    ratio consultations/exports) → abuse_scores + alerte admin au-delà du seuil."""
    s = config.get_settings()
    jour = jour or (date.today() - timedelta(days=1))
    debut = datetime.combine(jour, datetime.min.time(), tzinfo=timezone.utc)
    rows = db.execute(text(
        "SELECT sujet, ts, idu FROM consultation_log "
        "WHERE ts >= :d AND ts < :f ORDER BY sujet, ts"),
        {"d": debut, "f": debut + timedelta(days=1)}).all()
    par_sujet: dict[str, list] = defaultdict(list)
    for sujet, ts, idu in rows:
        par_sujet[sujet].append((ts, idu))

    resultats: dict[str, dict] = {}
    for sujet, evts in par_sujet.items():
        idus = [i for _, i in evts if i]
        signaux: dict[str, float] = {"volume": len(evts)}
        score = 0
        # a) séquences d'IDU consécutifs (même préfixe section, numéros qui s'incrémentent)
        # IDU = insee(5) + préfixe(3) + section(2) + numéro(4) → numéro à partir de l'index 10
        seq_max, run = 0, 1
        for a, b in zip(sorted(idus), sorted(idus)[1:]):
            if a[:10] == b[:10] and a[10:].isdigit() and b[10:].isdigit() \
                    and int(b[10:]) - int(a[10:]) == 1:
                run += 1
                seq_max = max(seq_max, run)
            else:
                run = 1
        signaux["seq_idu_max"] = seq_max
        if seq_max >= 10:
            score += 35
        elif seq_max >= 5:
            score += 20
        # b) régularité machinale des intervalles (≥ 30 requêtes, écart-type < 20 % de la médiane)
        if len(evts) >= 30:
            gaps = [(b[0] - a[0]).total_seconds() for a, b in zip(evts, evts[1:])]
            med = statistics.median(gaps)
            if med > 0 and statistics.pstdev(gaps) < 0.2 * med:
                signaux["regularite"] = round(statistics.pstdev(gaps) / med, 3)
                score += 30
        # c) volume nocturne (22h-5h à La Réunion = UTC+4)
        nuit = sum(1 for ts, _ in evts if ((ts.astimezone(timezone.utc).hour + 4) % 24) >= 22
                   or ((ts.astimezone(timezone.utc).hour + 4) % 24) < 5)
        if len(evts) >= 50 and nuit / len(evts) > 0.5:
            signaux["part_nocturne"] = round(nuit / len(evts), 2)
            score += 20
        # d) ratio consultations/exports aberrant (beaucoup de fiches, zéro export)
        exports = compteur(db, sujet, "export", jour.isoformat())
        if len(idus) >= 150 and exports == 0:
            signaux["ratio_sans_export"] = len(idus)
            score += 15
        score = min(100, score)
        db.execute(text(
            "INSERT INTO abuse_scores (jour, sujet, score, signaux) "
            "VALUES (:j, :s, :sc, :sig) "
            "ON CONFLICT (jour, sujet) DO UPDATE SET score = :sc, signaux = :sig, "
            "computed_at = now()"),
            {"j": jour, "s": sujet, "sc": score,
             "sig": json.dumps(signaux, ensure_ascii=False)})
        if score >= s.abuse_alert_seuil:
            db.execute(text("INSERT INTO admin_alertes (kind, detail) VALUES ('abuse', :d)"),
                       {"d": f"{sujet} : score {score} le {jour} — {json.dumps(signaux)}. "
                             "Gel MANUEL par Vic si confirmé (pas de blocage auto)."})
        resultats[sujet] = {"score": score, **signaux}
    return {"jour": jour.isoformat(), "sujets": len(resultats), "scores": resultats,
            "alertes": sum(1 for r in resultats.values() if r["score"] >= s.abuse_alert_seuil)}
