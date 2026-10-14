"""DOCS-FIX-1 (Lot 1, P1) — LE GARDE-FOU DU PROXY DEV.

Le trou du proxy Vite (`frontend/vite.config.ts` → `apiPaths`) est réapparu TROIS fois
(EXPORTS-1 /argumentaire, DOCS-1 /gabarit·/comparatif·/etude-zone·/documents, et trois
routes JSON pré-existantes /config·/partners·/vocabulaire). En `npm run dev` une route
d'API non proxifiée sort de la base `/socle/` → 404 / page d'erreur Vite, alors que la prod
(FastAPI même origine) fonctionne : le défaut est INVISIBLE à la prod et se redécouvre à
chaque fois à la main.

Ce test LIT les routes réellement exposées par l'API (app.routes) et ÉCHOUE si l'une d'elles
n'est couverte ni par `apiPaths`, ni par l'allowlist documentée ci-dessous (pages rendues par
le serveur, assets de campagne, auto-doc FastAPI, webhooks — que la SPA ne `fetch` jamais en
dev). Ajouter une route d'API appelée par le front sans l'ajouter au proxy fera ÉCHOUER ce
test — c'est ce qui empêche la quatrième occurrence.

NB : le proxy Vite matche par PRÉFIXE (contexte `proxy['/x']` → toute URL commençant par `/x`) ;
on reproduit exactement ce `startswith`.
"""
from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_VITE = _ROOT / "frontend" / "vite.config.ts"
_APP = _ROOT / "src" / "labuse" / "api" / "app.py"

# Routes exposées par l'API mais que la SPA n'appelle JAMAIS en `fetch` cross-origin en dev :
# pages RENDUES PAR LE SERVEUR (navigations plein écran, mêmes-origine en prod), assets de
# campagne, auto-documentation FastAPI, webhooks serveur→serveur, sondes infra. Chaque entrée
# est un choix CONSCIENT : si l'une devient un appel `fetch` du front, la retirer d'ici et
# l'ajouter à `apiPaths`. (Vérifié par grep du front : aucune de ces racines n'est fetch-ée.)
NON_PROXIFIE = {
    "/",                                   # la SPA elle-même (servie par Vite en dev)
    "/assistant",                          # /assistant/status — sonde ops, pas d'appel front
    "/cgv", "/confidentialite", "/mentions-legales",   # pages légales (liens, rendu serveur)
    "/demo", "/demo-status",               # parcours démo (rendu serveur)
    "/docs", "/redoc", "/openapi.json",    # auto-doc FastAPI
    "/flash", "/flash-retour.js", "/flash-omnibox.js", "/parcours.js",   # campagne Flash (page + scripts servis)
    "/ordinateur.js",                      # CHARGEMENT-1 — script de la porte « ordinateur seulement » (servi, pas fetch)
    "/socle",                              # Socle V1 — montage StaticFiles de la SPA + assets (src/href, jamais un fetch)
    "/invitation", "/login", "/logout",    # auth : navigations plein écran (rendu serveur)
    "/reset", "/reset-demande",            # réinitialisation mot de passe (rendu serveur)
    "/onboarding",                         # bienvenue post-invitation (rendu serveur)
    "/p",                                  # lien court (redirection serveur)
    "/stripe",                             # webhook Stripe (serveur → serveur)
    "/suggestions",                        # non appelé par le front
}


def _api_paths() -> list[str]:
    """Extrait le littéral `apiPaths` de vite.config.ts (commentaires de ligne retirés)."""
    lignes, dedans = [], False
    for ln in _VITE.read_text(encoding="utf-8").splitlines():
        if "const apiPaths" in ln:
            dedans = True
        if dedans:
            code = ln.split("//", 1)[0]     # retire le commentaire de ligne
            lignes.append(code)
            if "]" in code:
                break
    txt = "\n".join(lignes)
    return [p for p in re.findall(r"'([^']+)'", txt) if p.startswith("/")]


def _segments_api() -> set[str]:
    """Première composante de chemin de chaque route montée sur l'app FastAPI."""
    from labuse.api.app import app
    segs: set[str] = set()
    for r in app.routes:
        p = getattr(r, "path", None)
        if not p:
            continue
        segs.add("/" + p.lstrip("/").split("/")[0] if p != "/" else "/")
    return segs


def _mounts_source() -> set[str]:
    """Racines montées par `app.mount(...)` DANS LE CODE, même quand le montage est CONDITIONNEL
    au runtime. `/socle` (StaticFiles de la SPA) n'est monté que si `frontend/dist` existe
    (app.py : `if FRONTEND_DIST.exists()`) : absent du hook local (front non buildé), bien présent
    en prod/CI. Une racine ainsi déclarée dans la source n'est PAS une entrée morte."""
    txt = _APP.read_text(encoding="utf-8")
    return {"/" + m for m in re.findall(r"""\.mount\(\s*["']/([^"'/]+)""", txt)}


def test_apiPaths_bien_lu():
    paths = _api_paths()
    # garde-fou du garde-fou : l'extraction fonctionne (sinon le test serait vide → faux vert).
    assert len(paths) >= 60, f"extraction apiPaths suspecte : {len(paths)} entrées"
    for attendu in ("/dossier", "/gabarit", "/comparatif", "/etude-zone", "/documents"):
        assert attendu in paths, f"{attendu} absent de apiPaths"


def test_toute_route_api_est_proxifiee_ou_allowlistee():
    paths = _api_paths()

    def couverte(seg: str) -> bool:                       # mime le match-préfixe de Vite
        return any(seg == p or seg.startswith(p) for p in paths)

    manquantes = sorted(
        s for s in _segments_api() if not couverte(s) and s not in NON_PROXIFIE)
    assert not manquantes, (
        "Routes d'API non proxifiées en dev (ni dans apiPaths, ni allowlistées) :\n  "
        + "\n  ".join(manquantes)
        + "\n→ ajoute-les à `apiPaths` (frontend/vite.config.ts) si le front les appelle, "
          "ou à NON_PROXIFIE (avec justification) si c'est une page rendue par le serveur.")


def test_allowlist_sans_entree_morte():
    """L'allowlist ne doit pas pourrir : toute racine allowlistée existe encore côté API
    (sauf '/', la SPA). Une entrée morte masquerait une vraie route le jour où elle renaît."""
    # routes vivantes + montages déclarés dans la source (dont les montages CONDITIONNELS comme
    # /socle, présents en prod/CI mais pas dans le hook local sans front buildé).
    segs = _segments_api() | _mounts_source()
    mortes = sorted(s for s in NON_PROXIFIE if s != "/" and s not in segs)
    assert not mortes, f"entrées NON_PROXIFIE sans route API correspondante : {mortes}"
