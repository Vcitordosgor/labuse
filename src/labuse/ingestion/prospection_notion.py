"""PROSPECTION-NOTION — LE CSV d'import Notion « Prospection LABUSE », prêt sans retouche.

READ-ONLY sur la base (aucune table créée, zéro touche scoring). Part des déposants actifs
(cf. `deposants_actifs`), puis :
  1. renomme les colonnes aux EN-TÊTES EXACTS de la base Notion (data source e17db1a3…) ;
  2. tague la colonne « Entité publique » (mairie/SEM/EPIC/collectivité…) — on MARQUE, on n'exclut pas ;
  3. suggère un « Segment » heuristique (promoteur/lotisseur/cmi/bailleur/autre_pro) — à corriger à la main ;
  4. enrichit les coordonnées HONNÊTEMENT disponibles en open data via l'API publique
     `recherche-entreprises.api.gouv.fr` (INSEE/INPI, gratuite, sans clé) : adresse + ville du siège.

Le CSV est écrit dans `exports/` (gitignoré) — séparateur VIRGULE, UTF-8 avec BOM, dates ISO,
une ligne par SIREN. Boussole : personne morale uniquement, dirigeants diffusibles (déjà filtrés
en amont par `deposants_actifs`), jamais un particulier nommé, pas d'invention de coordonnées.

LIMITE OPEN DATA ASSUMÉE : l'API publique ne fournit quasiment jamais le téléphone ni l'email
d'une entreprise, et n'expose PAS le site web. Ces colonnes restent donc vides (pistes payantes :
Pappers API, Societeinfo — non utilisées ici, cf. docs/PROSPECTION_IMPORT.md).
"""
from __future__ import annotations

import csv
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:  # le Python du .venv n'a pas toujours le trousseau système ; certifi fournit le bundle CA.
    import certifi

    _SSL_CTX: ssl.SSLContext | None = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # pragma: no cover
    _SSL_CTX = None

from sqlalchemy.orm import Session

from . import deposants_actifs

# En-têtes EXACTS de la data source Notion (casse + accents) — l'ordre = l'ordre des colonnes du CSV.
COLONNES_NOTION = [
    "Dénomination", "SIREN", "Segment", "Nb PC", "Nb PA", "Logements autorisés",
    "Parcelles détenues", "Communes", "Dirigeants", "Dernière autorisation", "Entité publique",
    "Adresse siège", "Ville siège", "Site web",
]

# --- Enrichissement (API publique recherche-entreprises) ---------------------------------------
API_URL = "https://recherche-entreprises.api.gouv.fr/search"
THROTTLE_S = 0.15  # ~6,5 req/s, sous la limite de 7 req/s de l'API
RETRIES = 3
CACHE_PATH = "exports/.prospection_enrichment_cache.json"  # idempotence + reprise si coupure

# --- Détection « Entité publique » -------------------------------------------------------------
# Mots-clés (frontières de mot pour éviter les faux positifs type « ENSEMBLE » ⊃ « SEM »).
_PUBLIC_RX = re.compile(
    r"\b(COMMUNE DE|MAIRIE|C\.?C\.?A\.?S|SEMADER|SIDR|SODIAC|SODEGIS|SEM|"
    r"D[EÉ]PARTEMENT|R[EÉ]GION|EPCI|CIREST|CINOR|CIVIS|TCO|CASUD|OFFICE|EPIC|SYNDICAT)\b"
)

# --- Suggestion « Segment » (heuristique, à corriger à la main dans Notion) ---------------------
# Ordre = priorité. Défaut : autre_pro. Ce sont des SUGGESTIONS, pas une classification prouvée.
_SEGMENTS = [
    ("bailleur", re.compile(r"\bHLM\b|HABITAT|BAILLEUR|LOGEMENT SOCIAL|OFFICE PUBLIC|"
                            r"\bSIDR\b|SEMADER|SODEGIS|SODIAC|\bSHLMR\b")),
    ("lotisseur", re.compile(r"LOTISS|AM[EÉ]NAG|\bFONCI[EÈ]R")),
    ("cmi", re.compile(r"CONSTRUCT|\bMAISON")),
    ("promoteur", re.compile(r"PROMOT|IMMOBILI")),
]


def _suggest_segment(denomination: str) -> str:
    d = (denomination or "").upper()
    for label, rx in _SEGMENTS:
        if rx.search(d):
            return label
    return "autre_pro"


def _load_cache(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")


def _fetch_api(siren: str) -> dict | None:
    """Interroge l'API publique. Renvoie le résultat correspondant au SIREN, ou None si introuvable.
    Lève une exception en cas d'erreur réseau/HTTP (le SIREN n'est alors PAS mis en cache → reprise)."""
    qs = urllib.parse.urlencode({"q": siren, "page": "1", "per_page": "5"})
    req = urllib.request.Request(f"{API_URL}?{qs}", headers={"User-Agent": "labuse-prospection/1.0"})
    with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    for r in data.get("results", []):
        if r.get("siren") == siren:
            return r
    return None


def _extract_enrichment(api_result: dict | None) -> dict:
    """Ne garde que ce qui est HONNÊTEMENT disponible en open data. Site web/tel/email : absents."""
    if not api_result:
        return {"trouve": False, "adresse": "", "ville": "", "site_web": "",
                "public_officiel": False, "nom_complet": "", "nature_juridique": ""}
    siege = api_result.get("siege") or {}
    compl = api_result.get("complements") or {}
    ville = siege.get("libelle_commune") or ""
    cp = siege.get("code_postal") or ""
    nj = str(api_result.get("nature_juridique") or "")
    public_officiel = bool(
        compl.get("est_service_public") or compl.get("est_administration")
        or compl.get("collectivite_territoriale") or compl.get("est_l100_3")
        or nj.startswith("7")
    )
    return {
        "trouve": True,
        "adresse": siege.get("adresse") or "",
        "ville": f"{cp} {ville}".strip(),
        "site_web": "",  # non fourni par l'open data (recherche-entreprises)
        "public_officiel": public_officiel,
        "nom_complet": api_result.get("nom_complet") or "",
        "nature_juridique": nj,
    }


def enrich_rows(rows: list[dict], *, cache_path: str | Path = CACHE_PATH,
                throttle: float = THROTTLE_S, log_fn=None) -> dict:
    """Enrichit chaque SIREN via l'API publique. Idempotent (cache JSON), reprend après coupure,
    throttle respecté. Renvoie un dict {siren: enrichment}. Modifie le cache sur disque au fil de l'eau."""
    cache_path = Path(cache_path)
    cache = _load_cache(cache_path)
    log = log_fn or (lambda *_: None)
    total = len(rows)
    fetched = 0
    for i, r in enumerate(rows, 1):
        siren = r["siren"]
        if siren in cache:
            continue
        for attempt in range(1, RETRIES + 1):
            try:
                cache[siren] = _extract_enrichment(_fetch_api(siren))
                fetched += 1
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:  # rate-limited : backoff exponentiel
                    time.sleep(min(2 ** attempt, 10))
                    continue
                if attempt == RETRIES:
                    log(f"  ! {siren} HTTP {e.code} — laissé vide (reprise au prochain run)")
                time.sleep(1)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                if attempt == RETRIES:
                    log(f"  ! {siren} {type(e).__name__} — laissé vide (reprise au prochain run)")
                time.sleep(1)
        if fetched and fetched % 50 == 0:
            _save_cache(cache_path, cache)
            log(f"  … {i}/{total} traités ({fetched} appels API)")
        time.sleep(throttle)
    _save_cache(cache_path, cache)
    return cache


def build_notion_rows(rows: list[dict], enrichment: dict | None = None) -> list[dict]:
    """Transforme les lignes brutes (extract_deposants) en lignes aux colonnes Notion exactes."""
    enrichment = enrichment or {}
    out = []
    for r in rows:
        siren = r["siren"]
        enr = enrichment.get(siren, {})
        # Dénomination : privilégier le nom normalisé INSEE/INPI si trouvé, sinon le nom SITADEL.
        denom = enr.get("nom_complet") or r.get("denomination") or ""
        public = bool(_PUBLIC_RX.search((denom or "").upper())) or bool(enr.get("public_officiel"))
        out.append({
            "Dénomination": denom,
            "SIREN": siren,
            "Segment": _suggest_segment(denom),
            "Nb PC": r.get("n_pc"),
            "Nb PA": r.get("n_pa"),
            "Logements autorisés": r.get("nb_logements"),
            "Parcelles détenues": r.get("n_parcelles_detenues"),
            "Communes": r.get("communes"),
            "Dirigeants": r.get("dirigeants"),
            "Dernière autorisation": r.get("dernier_depot"),  # déjà ISO YYYY-MM-DD
            "Entité publique": "true" if public else "false",
            "Adresse siège": enr.get("adresse", ""),
            "Ville siège": enr.get("ville", ""),
            "Site web": enr.get("site_web", ""),
        })
    return out


def write_notion_csv(notion_rows: list[dict], path: str | Path) -> Path:
    """CSV d'import Notion : séparateur VIRGULE, UTF-8 avec BOM (accents), une ligne par SIREN."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig = BOM ; QUOTE_MINIMAL protège les champs contenant une virgule (listes de communes).
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLONNES_NOTION, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in notion_rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in COLONNES_NOTION})
    return path


def generate(session: Session, *, out: str | Path, mois: int = deposants_actifs.MOIS_DEFAUT,
             enrich: bool = True, cache_path: str | Path = CACHE_PATH, log_fn=None) -> dict:
    """Bout-à-bout : extraction → enrichissement → transformation → écriture CSV.
    Renvoie des stats pour le rapport (n lignes, n publiques, taux d'enrichissement)."""
    log = log_fn or (lambda *_: None)
    rows = deposants_actifs.extract_deposants(session, mois=mois)  # une ligne par SIREN (dédup SQL)
    log(f"✓ {len(rows)} déposants actifs extraits ({mois} mois)")
    enrichment = {}
    if enrich:
        log("→ enrichissement coordonnées (API publique recherche-entreprises)…")
        enrichment = enrich_rows(rows, cache_path=cache_path, log_fn=log)
    notion_rows = build_notion_rows(rows, enrichment)
    p = write_notion_csv(notion_rows, out)
    n_public = sum(1 for r in notion_rows if r["Entité publique"] == "true")
    n_adresse = sum(1 for r in notion_rows if r["Adresse siège"])
    return {
        "path": str(p),
        "n_lignes": len(notion_rows),
        "n_publiques": n_public,
        "n_adresse": n_adresse,
        "taux_adresse": round(100 * n_adresse / len(notion_rows), 1) if notion_rows else 0.0,
    }
