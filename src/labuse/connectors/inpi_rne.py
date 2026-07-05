"""Connecteur INPI RNE — dirigeants des personnes morales (Vague A3, signal accessibilité).

API REST publique du Registre National des Entreprises (INPI), croisée par SIREN (comme BODACC).
Auth par jeton : `POST /api/sso/login` {username, password} → JWT, puis
`GET /api/companies/{siren}` avec `Authorization: Bearer <token>`.

⚠ SECRET : les identifiants (compte PORTAIL, distinct du compte SFTP technique) ne sont JAMAIS
en dur — lus depuis l'environnement `INPI_API_USERNAME` / `INPI_API_PASSWORD` (chargés de `.env`,
gitignoré). Le SFTP est abandonné (firewall à liste blanche d'IP côté INPI).

Schéma VÉRIFIÉ le 05/07/2026 sur un enregistrement réel (siren 913037362, SCI ALOE), pas deviné.
Chemins localisés dans le JSON :
  formality.content.personneMorale.identite.entreprise   → siren, denomination, formeJuridique
  formality.content.personneMorale.composition.pouvoirs[] → dirigeants (INDIVIDU | ENTREPRISE)
    individu.descriptionPersonne.dateDeNaissance = "1977-06" (AAAA-MM, mois jamais le jour)
    individu.descriptionPersonne.dateEffetRoleDeclarant → prise de fonction (souvent absente)
  formality.diffusionCommerciale ('True'/'False') → diffusibilité RGPD

RGPD (règle d'archi #2) : personnes morales en open data complet ; données d'une personne
PHYSIQUE conservées uniquement si l'entreprise est DIFFUSIBLE. Signal interne de priorisation,
jamais un export nominatif de masse. ⚠ N'ÉCRIT rien : lecture seule (l'ingestion est ailleurs).
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
from collections.abc import Iterable, Iterator
from datetime import date
from pathlib import Path

from .base import Connector

BASE = "https://registre-national-entreprises.inpi.fr/api"
LOGIN_URL = f"{BASE}/sso/login"
COMPANY_URL = f"{BASE}/companies/{{siren}}"
# Permalien humain vérifiable (fiche entreprise sur le portail RNE).
DATA_URL = "https://data.inpi.fr/entreprises/{siren}"
SOURCE_NAME = "INPI RNE (dirigeants)"

TOKEN_REFRESH_MARGIN_S = 60      # re-login proactif 60 s avant l'expiration du JWT
TOKEN_FALLBACK_TTL_S = 20 * 60   # si l'`exp` du JWT est illisible : re-login toutes les 20 min


class QuotaExceededError(RuntimeError):
    """L'API INPI a refusé pour QUOTA ÉPUISÉ (429 quota_exceeded / QUOTA_SERVICE).

    NON transitoire (le quota ne se réinitialise pas en quelques secondes) → on ARRÊTE FRANC
    au lieu de brûler des minutes en backoff puis de sauter silencieusement (incident 3h muettes)."""


def _is_quota(status: int, body: str) -> bool:
    """Vrai si la réponse est un refus de QUOTA (à distinguer d'un 429 transitoire de rate-limit)."""
    return status == 429 and ("quota_exceeded" in body or "QUOTA_SERVICE" in body)


def _load_env_file() -> None:
    """Charge `.env` (racine du dépôt) dans os.environ si les clés n'y sont pas déjà.

    Léger, sans dépendance (python-dotenv absent). Ne surcharge jamais une variable déjà posée.
    """
    root = Path(__file__).resolve().parents[3]
    env = root / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def _jwt_exp(token: str) -> float | None:
    """Extrait le claim `exp` (epoch s) du JWT sans vérifier la signature. None si illisible."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)               # padding base64url
        data = json.loads(base64.urlsafe_b64decode(payload))
        exp = data.get("exp")
        return float(exp) if exp is not None else None
    except Exception:
        return None


# ───────────────────────── parsing (pur, sans réseau) ─────────────────────────

def _digits(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


def _as_bool(v) -> bool | None:
    """L'API renvoie des booléens tantôt en vrai bool, tantôt en chaîne « True »/« False »/« O »."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "o", "oui", "1"):
            return True
        if s in ("false", "n", "non", "0"):
            return False
    return None


def compute_age(yyyy_mm: str | None, today: date) -> int | None:
    """Âge en années révolues depuis une date de naissance 'YYYY-MM' (jour inconnu → 1er du mois).

    Plancher prudent : tant que le mois d'anniversaire n'est pas atteint dans l'année, on n'ajoute
    pas l'année en cours (±1 an de marge, suffisant pour le signal). None si format invalide.
    """
    if not yyyy_mm:
        return None
    m = re.match(r"^(\d{4})-(\d{2})$", yyyy_mm.strip())
    if not m:
        return None
    y, mo = int(m.group(1)), int(m.group(2))
    if not (1 <= mo <= 12) or y < 1900 or y > today.year:
        return None
    age = today.year - y
    if today.month < mo:
        age -= 1
    return age if 0 <= age <= 130 else None


PROPENSION_BANDS = (  # (âge plancher inclus, libellé) — l'étage 2 posera sa propre courbe
    (75, "tres_eleve"),
    (65, "eleve"),
    (55, "modere"),
    (0, "faible"),
)


def propension_band(age: int | None) -> str | None:
    if age is None:
        return None
    for floor, label in PROPENSION_BANDS:
        if age >= floor:
            return label
    return None


def _parse_prise_fonction(desc: dict) -> date | None:
    """`dateEffetRoleDeclarant` (prise de fonction) — présente seulement si le flag l'indique."""
    if not desc.get("dateEffetRoleDeclarantPresent"):
        return None
    raw = desc.get("dateEffetRoleDeclarant")
    try:
        return date.fromisoformat(raw) if raw else None
    except (TypeError, ValueError):
        return None


def _parse_pouvoir(p: dict, diffusible: bool | None) -> dict | None:
    """Un élément de `composition.pouvoirs[]` → dict dirigeant normalisé. None si inexploitable.

    INDIVIDU : personne physique — nom/prénoms/naissance conservés SEULEMENT si l'entreprise est
    diffusible (RGPD). ENTREPRISE : dirigeant personne morale (open data) → on garde son SIREN
    (`gerant_siren`) pour la mesure du taux « gigogne » (dirigeant-société).
    """
    type_personne = p.get("typeDePersonne")
    representant_id = p.get("representantId")
    role = p.get("roleEntreprise")
    actif = _as_bool(p.get("actif"))
    base = {
        "representant_id": representant_id,
        "type_personne": type_personne,
        "role_entreprise": role,
        "actif": actif,
        "diffusible": diffusible,
        "nom": None, "prenoms": None, "date_naissance": None,
        "date_prise_fonction": None, "gerant_siren": None,
        "raw": p,
    }
    if type_personne == "INDIVIDU":
        desc = (p.get("individu") or {}).get("descriptionPersonne") or {}
        base["date_prise_fonction"] = _parse_prise_fonction(desc)
        # RGPD : n'attacher l'identité/naissance physique que si l'entreprise est diffusible.
        if diffusible:
            base["nom"] = desc.get("nom")
            prenoms = desc.get("prenoms")
            base["prenoms"] = " ".join(prenoms) if isinstance(prenoms, list) else prenoms
            dn = desc.get("dateDeNaissance") if desc.get("dateDeNaissancePresent") else None
            base["date_naissance"] = dn
        return base
    if type_personne == "ENTREPRISE":
        ent = p.get("entreprise") or {}
        base["gerant_siren"] = _digits(ent.get("siren")) or None
        base["nom"] = ent.get("denomination")   # dénomination de la société dirigeante (open data)
        return base
    return None  # type inconnu → ignoré


def parse_company(data: dict) -> dict | None:
    """Réponse `/api/companies/{siren}` → {siren, denomination, forme_juridique, diffusible,
    dirigeants:[...]}. None si le SIREN est introuvable/invalide.

    Le SIREN de tête peut vivre à la racine OU dans identite.entreprise ; on prend le premier
    9-chiffres valide (ne PAS deviner — vérifié sur SCI ALOE).
    """
    if not isinstance(data, dict):
        return None
    formality = data.get("formality") or {}
    content = formality.get("content") or {}
    pm = content.get("personneMorale") or {}
    ent = (pm.get("identite") or {}).get("entreprise") or {}

    siren = _digits(ent.get("siren")) or _digits(data.get("siren")) or _digits(formality.get("siren"))
    if len(siren) != 9:
        return None

    diffusible = _as_bool(formality.get("diffusionCommerciale"))
    pouvoirs = (pm.get("composition") or {}).get("pouvoirs") or []
    dirigeants = [d for d in (_parse_pouvoir(p, diffusible) for p in pouvoirs) if d]

    return {
        "siren": siren,
        "denomination": ent.get("denomination"),
        "forme_juridique": ent.get("formeJuridique") or formality.get("formeJuridique"),
        "date_immat": ent.get("dateImmat"),
        "diffusible": diffusible,
        "dirigeants": dirigeants,
        "url_source": DATA_URL.format(siren=siren),
    }


# ───────────────────────── connecteur (login + token + GET) ─────────────────────────

class InpiRneConnector(Connector):
    """Client RNE authentifié par SIREN. `name` matche data_sources.name.

    Gère le cycle de vie du jeton : login paresseux, refresh proactif avant `exp`, re-login +
    retry sur 401. Poli : throttle entre requêtes, backoff sur 429/5xx. Mono-thread (on s'est
    déjà fait firewaller une fois — on reste ultra-prudent).
    """

    name = SOURCE_NAME
    test_url = None  # le test de connexion réel se fait via login (cf. test_connection)

    def __init__(self, username: str | None = None, password: str | None = None,
                 throttle_s: float = 0.5, timeout: float | None = None):
        super().__init__(timeout)
        if username is None or password is None:
            _load_env_file()
        self._user = username or os.environ.get("INPI_API_USERNAME")
        self._pwd = password or os.environ.get("INPI_API_PASSWORD")
        self.throttle_s = throttle_s
        self._token: str | None = None
        self._token_exp: float = 0.0

    # -- jeton --------------------------------------------------------------

    def _login(self) -> None:
        if not self._user or not self._pwd:
            raise RuntimeError(
                "INPI_API_USERNAME / INPI_API_PASSWORD manquants (compte portail RNE, .env).")
        body = json.dumps({"username": self._user, "password": self._pwd})
        with self._client() as c:
            r = c.post(LOGIN_URL, content=body, headers={"Content-Type": "application/json"})
        if _is_quota(r.status_code, r.text):
            raise QuotaExceededError(f"INPI login refusé — quota épuisé : {r.text[:160]}")
        if r.status_code != 200:
            # message applicatif utile (401 identifiants, 403 accès API non activé…)
            raise RuntimeError(f"INPI login échoué : HTTP {r.status_code} — {r.text[:200]}")
        token = r.json().get("token")
        if not token:
            raise RuntimeError("INPI login : réponse sans token.")
        self._token = token
        exp = _jwt_exp(token)
        self._token_exp = exp if exp is not None else time.time() + TOKEN_FALLBACK_TTL_S

    def _ensure_token(self) -> str:
        if self._token is None or time.time() >= self._token_exp - TOKEN_REFRESH_MARGIN_S:
            self._login()
        return self._token  # type: ignore[return-value]

    # -- lecture ------------------------------------------------------------

    def _get_company(self, siren: str, max_retries: int = 6) -> dict | None:
        """GET une société. None si 404 (SIREN inconnu au RNE). Retry poli sur 429/5xx et
        re-login unique sur 401 (jeton expiré)."""
        url = COMPANY_URL.format(siren=siren)
        last: Exception | None = None
        relogin_done = False
        for attempt in range(max_retries):
            try:
                token = self._ensure_token()
                with self._client() as c:
                    r = c.get(url, headers={"Authorization": f"Bearer {token}"})
                if r.status_code == 404:
                    return None
                if r.status_code == 401 and not relogin_done:  # jeton invalidé côté serveur
                    relogin_done = True
                    self._token = None
                    continue
                if _is_quota(r.status_code, r.text):  # QUOTA épuisé → arrêt franc (pas de backoff inutile)
                    raise QuotaExceededError(f"INPI quota épuisé (société {siren}) : {r.text[:140]}")
                if r.status_code == 429 or r.status_code >= 500:  # transitoire → backoff patient
                    retry_after = r.headers.get("Retry-After")
                    # 429 = rate-limit : backoff EXPONENTIEL (1,2,4,8,16,30 s), plafonné, sinon on
                    # se fait bannir. On respecte Retry-After s'il est fourni.
                    delay = float(retry_after) if (retry_after or "").isdigit() else min(30.0, 2 ** attempt)
                    last = RuntimeError(f"HTTP {r.status_code}")
                    time.sleep(delay)
                    continue
                r.raise_for_status()
                return r.json()
            except QuotaExceededError:
                raise  # non transitoire : ne JAMAIS retenter ni avaler
            except Exception as exc:  # réseau / timeout → retry poli
                last = exc
                time.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"INPI : société {siren} — échec après {max_retries} essais ({last})")

    def fetch_company(self, siren: str) -> dict | None:
        """Une société parsée par SIREN. None si inconnue au RNE (404) ou non parsable. Ne throttle
        PAS (l'appelant gère la cadence) — pratique pour la résolution unitaire (gigogne depth-1)."""
        data = self._get_company(_digits(siren))
        return parse_company(data) if data is not None else None

    def fetch_companies(self, sirens: Iterable[str], throttle_s: float | None = None,
                        ) -> Iterator[dict]:
        """Itère les sociétés parsées pour un ensemble de SIREN (1 requête/SIREN, throttlé).

        Les SIREN inconnus au RNE (404) ou non parsables sont silencieusement sautés.
        """
        throttle = self.throttle_s if throttle_s is None else throttle_s
        for siren in sorted({_digits(s) for s in sirens if _digits(s)}):
            try:
                parsed = self.fetch_company(siren)
            except QuotaExceededError:
                raise            # quota épuisé → arrêt franc et bruyant (pas de skip silencieux)
            except Exception:  # noqa: BLE001 — 429 persistant / réseau : on saute ce SIREN plutôt
                parsed = None   # que de tuer la passe (résumable : réessayé au prochain run)
            if parsed:
                yield parsed
            if throttle:
                time.sleep(throttle)

    def test_connection(self):
        """Test de connexion réel = login (l'endpoint /companies exige déjà un jeton)."""
        from .base import ConnectionTestResult
        try:
            self._login()
            return ConnectionTestResult(self.name, True, "OK (login RNE)", status_code=200)
        except Exception as exc:
            return ConnectionTestResult(self.name, False, f"{type(exc).__name__}: {exc}")
