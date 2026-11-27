"""MISE-EN-LIGNE-3 — les modules tiers dont le code SERVI a besoin, déclarés UNE fois.

Leçon (21/11) : `openpyxl` n'était déclaré que dans les extras `[ml]`/`[ci]` → jamais installé en
prod → le Bilan Excel rendait 500 À LA DEMANDE d'un client (import paresseux dans l'endpoint :
l'app boote, la panne attend le clic). Un manque de dépendance doit BLOQUER LE DÉPLOIEMENT
(`jobs selftest`, contrôle 5), jamais surgir chez un client.

Deux listes, exhaustives par construction (le méta-test `tests/test_deps_servies.py` re-balaye
TOUS les imports de `src/labuse` par AST — y compris ceux à l'intérieur des fonctions — et
refuse tout module tiers non classé ici) :

- `MODULES_TIERS_SERVIS` : importés par un chemin servi (API, jobs, exports, moteurs). Le
  selftest du déploiement les importe un à un ; un manque = déploiement refusé.
- `HORS_PROD` : imports délibérément absents du serveur, avec le pourquoi. Ils ne sont JAMAIS
  sur un chemin servi (vérifié 21/11) ; si un développement les y amène, le méta-test ne
  suffira pas — c'est la revue qui doit déplacer le module dans la liste servie ET dans les
  dépendances de série.
"""
from __future__ import annotations

#: importés par un chemin servi — testés par `jobs.selftest()` (contrôle 5) à CHAQUE déploiement.
MODULES_TIERS_SERVIS: tuple[str, ...] = (
    "PIL", "anthropic", "anyio", "argon2", "brotli", "certifi", "cv2", "dotenv", "duckdb",
    "fastapi", "fitz", "fpdf", "geoalchemy2", "httpx", "jinja2", "joblib", "jsonschema",
    "markupsafe", "numpy", "openpyxl", "pandas", "psycopg", "pydantic", "pydantic_settings",
    "affine", "pypdf", "pyproj", "qrcode", "rasterio", "requests", "scipy", "shapefile", "shapely",
    "sklearn", "sqlalchemy", "starlette", "stripe", "typer", "uvicorn", "weasyprint", "yaml",
)

#: imports PRÉSENTS dans src/labuse mais délibérément hors du serveur — motif obligatoire.
HORS_PROD: dict[str, str] = {
    "torch": "ML only (PROPRETE-FIX-0) — jamais installé en prod ; ml/juge_flair, ml/probe",
    "segmentation_models_pytorch": "ML only — ml/juge_flair (détection ortho, hors-ligne)",
    "py7zr": "ingestion cadastre historique (.7z DGFiP), hors-ligne Mac — jamais servie",
    "matplotlib": "implantation/rendu.py (témoins/archives rejouables) — AUCUN appelant servi",
    "protocole": "module local du harnais d'arène (verite_terrain_predictions, exécuté à la main)",
    "scripts": "racine du dépôt (pas un paquet pip) — couverte par les contrôles 3-4 du selftest",
}


def manquants() -> list[str]:
    """Importe chaque module servi ; rend la liste de ceux qui manquent (vide = tout est là)."""
    out: list[str] = []
    for m in MODULES_TIERS_SERVIS:
        try:
            __import__(m)
        except Exception:  # noqa: BLE001 — quel que soit le mode d'échec, le module n'est pas utilisable
            out.append(m)
    return out
