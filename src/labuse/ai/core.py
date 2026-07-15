"""M11 · SOCLE 0 — Service IA CENTRAL UNIQUE.

Point d'entrée unique de TOUTE la couche IA de LABUSE. Remplace la duplication constatée
(audit `reports/m11-ia/AUDIT-EXISTANT-IA.md`) : 3-4 modules instanciaient chacun leur détection
de clé, leur client Anthropic, leurs stubs. Ici, un seul de chaque.

Doctrine (inchangée, cf. CADRE-M11 §0) : l'IA n'accède JAMAIS à la base et ne calcule JAMAIS un
score/chiffre. Elle reçoit un CONTEXTE AUTORISÉ (liste blanche, provenance étiquetée) et FORMULE.

Ce module fournit aux surfaces :
  1. `has_key()` / `provider_status()` — un seul point de vérité sur la clé Anthropic.
  2. `complete(...)` — l'appel modèle unique (routeur haiku/sonnet, timeout/retries centralisés,
     repli `degraded` flaggé, sérialisation SÛRE `default=str` → plus de 500 Decimal, log de coût).
  3. Le contrat de GROUNDING : `Fact` / `build_context(...)` (liste blanche OBLIGATOIRE + provenance).
  4. La VALIDATION DE SORTIE hybride 1+3 : `validate_output(...)` (sources forcées + vérif mécanique
     des chiffres, HORS IA).
  5. Le CACHE `(idu, run_label, question)` : `cache_get` / `cache_put`.

Aucun accès scoring/cascade/étage 0 ici. Le module ne lit la base QUE pour le log de coût et le cache.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

# ── Modèles (routeur par TÂCHE, jamais codé en dur chez l'appelant) ───────────────────────────
MODEL_FACTUAL = "claude-haiku-4-5-20251001"    # extraction, factuel, acronymes, filtres NL
MODEL_REASONING = "claude-sonnet-4-6"          # raisonnement explicite (faisabilité expliquée, synthèse)
#: €/Mtoken (approx, log indicatif — pas la tarification officielle live)
PRICE = {MODEL_FACTUAL: (1.0, 5.0), MODEL_REASONING: (3.0, 15.0)}
ENV_KEY = "ANTHROPIC_API_KEY"

# Défauts centralisés (un seul endroit — plus de valeurs dispersées dans chaque appelant)
DEFAULT_TIMEOUT = 25.0
DEFAULT_RETRIES = 2
DEFAULT_TEMPERATURE = 0.0        # comportement STABLE (QA réelle)

Provenance = Literal["SOURCE", "ESTIME", "ABSENT"]

#: dernier échec provider (diagnostic bandeau) — None = dernier appel OK
_LAST_ERROR: str | None = None


# ═════════════════════════ 1. Clé & statut (source unique) ═════════════════════════
def has_key() -> bool:
    """Vrai si la clé Anthropic est présente. SEUL point de vérité (les modules l'importent d'ici)."""
    from .. import config as _cfg  # noqa: F401 — garantit load_dotenv(.env racine), quel que soit le lanceur
    return bool(os.environ.get(ENV_KEY, "").strip())


def _note_error(exc: Exception) -> None:
    global _LAST_ERROR
    name = type(exc).__name__
    if "Authentication" in name or "401" in str(exc):
        _LAST_ERROR = "clé invalide (authentification refusée par l'API Anthropic)"
    elif "Permission" in name or "403" in str(exc):
        _LAST_ERROR = "clé refusée (permissions insuffisantes)"
    else:
        _LAST_ERROR = f"erreur API Anthropic ({name})"


def _note_success() -> None:
    global _LAST_ERROR
    _LAST_ERROR = None


def last_error() -> str | None:
    return _LAST_ERROR


def provider_status() -> dict:
    """État provider unifié (repris par /ia/status)."""
    key = has_key()
    return {
        "provider": "anthropic" if key else "stub",
        "raison": (None if (key and not _LAST_ERROR)
                   else _LAST_ERROR if key
                   else "ANTHROPIC_API_KEY absente de l'environnement (.env racine non chargé ou clé non posée)"),
        "modeles": {"factuel": MODEL_FACTUAL, "raisonnement": MODEL_REASONING},
        "doctrine": "l'IA ne calcule ni ne modifie aucun score ; aucun accès base ; sortie validée (sources + chiffres)",
    }


def _log_cost(db: Session | None, kind: str, model: str, stub: bool, tin: int = 0, tout: int = 0) -> None:
    if db is None:
        return
    pin, pout = PRICE.get(model, (0, 0))
    db.execute(text("CREATE TABLE IF NOT EXISTS ia_log ("
                    " id serial PRIMARY KEY, ts timestamptz DEFAULT now(), kind varchar(24), model varchar(64),"
                    " stub boolean, tokens_in integer, tokens_out integer, cout_eur numeric(8,5))"))
    db.execute(text("INSERT INTO ia_log (kind, model, stub, tokens_in, tokens_out, cout_eur) "
                    "VALUES (:k, :m, :s, :ti, :to, :c)"),
               {"k": kind[:24], "m": model[:64], "s": stub, "ti": tin, "to": tout,
                "c": (tin * pin + tout * pout) / 1_000_000})


# ═════════════════════════ 2. Contrat de GROUNDING (entrée) ═════════════════════════
@dataclass
class Fact:
    """Une donnée autorisée à être envoyée au modèle, avec sa provenance (jamais inventée)."""
    value: Any
    provenance: Provenance = "SOURCE"

    def to_json(self) -> dict:
        return {"valeur": self.value, "provenance": self.provenance}


def build_context(facts: dict[str, Fact], *, allowed_fields: set[str]) -> dict[str, Any]:
    """Construit le CONTEXTE AUTORISÉ envoyé au modèle. LISTE BLANCHE OBLIGATOIRE :
    tout champ hors `allowed_fields` est REFUSÉ (jamais « toute la fiche sérialisée »)."""
    illegal = set(facts) - set(allowed_fields)
    if illegal:
        raise ValueError(f"grounding: champs hors liste blanche refusés : {sorted(illegal)}")
    return {k: f.to_json() for k, f in facts.items()}


def context_values(context: dict[str, Any]) -> list[Any]:
    """Aplatit toutes les valeurs présentes dans un contexte autorisé (pour la vérif de sortie)."""
    out: list[Any] = []

    def _walk(o: Any) -> None:
        if isinstance(o, dict):
            for v in o.values():
                _walk(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                _walk(v)
        else:
            out.append(o)
    _walk(context)
    return out


def context_field_keys(context: dict[str, Any]) -> set[str]:
    """Clés de champ disponibles pour référencement `⟨src:...⟩` (niveau 1 de racine + sous-clés)."""
    keys: set[str] = set()

    def _walk(o: Any, prefix: str) -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("valeur", "provenance"):
                    continue
                path = f"{prefix}.{k}" if prefix else k
                keys.add(path)
                keys.add(k)
                _walk(v, path)
    _walk(context, "")
    return keys


# ═════════════════════════ 3. VALIDATION DE SORTIE (hybride 1 + 3) ═════════════════════════
_SRC_MARKER = re.compile(r"⟨src:([a-zA-Z0-9_.\-]+)⟩")
# nombres : entiers/décimaux, séparateurs FR (espaces, virgule), pas les années isolées gérées à part
_NUM_RE = re.compile(r"-?\d[\d  .]*\d|-?\d")


@dataclass
class OutputCheck:
    ok: bool
    text: str
    sources: list[str] = field(default_factory=list)
    reason: str | None = None
    stripped: list[str] = field(default_factory=list)


def _norm_number(s: str) -> float | None:
    """Normalise un nombre écrit FR (« 1 640 », « 834,0 ») → float, sinon None."""
    cleaned = s.replace(" ", "").replace(" ", "").replace(",", ".")
    # « 1.640 » (millier FR) vs « 834.0 » : on retire les points de milliers seulement si >1 point
    if cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _numbers_in_context(context: dict[str, Any]) -> set[float]:
    nums: set[float] = set()
    for v in context_values(context):
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            nums.add(float(v))
        elif isinstance(v, str):
            for m in _NUM_RE.findall(v):
                n = _norm_number(m)
                if n is not None:
                    nums.add(n)
    return nums


def _number_ok(n: float, allowed: set[float], *, tol_ratio: float = 0.02) -> bool:
    """Un nombre de la réponse est admis s'il figure au contexte (tolérance arrondi/format), ou s'il
    dérive trivialement (ex. arrondi k€) d'une valeur du contexte. Les petits entiers 0-12 (numéros de
    liste, R+n, nb logements) sont tolérés (bruit rédactionnel non factuel)."""
    if n in allowed:
        return True
    if 0 <= n <= 12 and float(n).is_integer():
        return True
    for a in allowed:
        if a == 0:
            continue
        if abs(n - a) / abs(a) <= tol_ratio:
            return True
        # arrondi k€ / M€ : 834 ~ 834000, 2.9 ~ 2960000…
        for scale in (1_000.0, 1_000_000.0):
            if abs(n * scale - a) / abs(a) <= tol_ratio or abs(n / scale - a) / max(abs(a), 1e-9) <= tol_ratio:
                return True
    return False


def validate_output(prose: str, context: dict[str, Any], *, require_sources: bool = True) -> OutputCheck:
    """VALIDATION DE SORTIE — deux couches mécaniques (HORS IA), appliquées AVANT de renvoyer au client.

    Couche 1 (sources forcées) : chaque marqueur `⟨src:champ⟩` doit pointer un champ RÉELLEMENT présent
      dans le contexte autorisé. Un marqueur invalide → réponse rejetée.
    Couche 2 (chiffres) : tout nombre de la réponse doit figurer (à tolérance de format) dans les valeurs
      du contexte. Un chiffre inventé (hallucination numérique, le pire cas) → réponse rejetée.

    En cas de rejet : `ok=False` + `reason`. L'appelant N'AFFICHE PAS la prose douteuse (règle : en cas
    de doute, on n'affiche pas). Les `sources` valides alimentent les étiquettes UI « Sourcé · … »."""
    valid_keys = context_field_keys(context)
    markers = _SRC_MARKER.findall(prose)
    for src in markers:
        if src not in valid_keys and src.split(".")[-1] not in valid_keys:
            return OutputCheck(False, prose, reason=f"source invalide « {src} » (champ absent du contexte)")
    if require_sources and not markers:
        return OutputCheck(False, prose, reason="aucune source citée (⟨src:…⟩ requis)")

    allowed_nums = _numbers_in_context(context)
    for m in _NUM_RE.findall(prose):
        n = _norm_number(m)
        if n is None:
            continue
        if not _number_ok(n, allowed_nums):
            return OutputCheck(False, prose, reason=f"chiffre non sourcé « {m.strip()} » (absent du contexte)")

    # nettoyage : on retire les marqueurs du texte affiché, on les renvoie comme sources structurées
    clean = _SRC_MARKER.sub("", prose)
    clean = re.sub(r"[ \t]+", " ", clean).strip()
    return OutputCheck(True, clean, sources=sorted(set(markers)))


# ═════════════════════════ 4. CACHE (idu, run_label, question) ═════════════════════════
def _ensure_cache_table(db: Session) -> None:
    db.execute(text(
        "CREATE TABLE IF NOT EXISTS ia_cache ("
        " idu varchar(14) NOT NULL, run_label varchar(64) NOT NULL, question_hash varchar(64) NOT NULL,"
        " kind varchar(24), question text, response jsonb NOT NULL, computed_at timestamptz DEFAULT now(),"
        " PRIMARY KEY (idu, run_label, question_hash))"))


# ── VERSION DU CONTEXTE de grounding (FAIT PARTIE de la clé de cache) ──────────────────────────
# La réponse cachée dépend du CONTEXTE envoyé au modèle (Facts construits par _ask_context :
# quels champs, quel mapping, quelle structure). Le run_label capture le changement de DONNÉES ;
# CONTEXT_VERSION capture le changement de CODE du contexte. Les deux salent le hash de cache.
#
# ⇒ RÈGLE : tout changement de `fiche_ask._ask_context` (nouveau champ, correction de mapping,
#   structure de Fact, changement du _SYSTEM qui altère la forme de réponse) DOIT bumper ce nombre.
#   Effet : tous les `question_hash` changent → les réponses cachées AVANT le changement deviennent
#   automatiquement inatteignables (cache miss → régénération avec le code corrigé), SANS purge
#   manuelle. C'est le garde-fou contre le « bugfix masqué par le cache » (incident zonage 15/07).
#
# Historique :
#   v1 — contexte initial de la barre de fiche (M11 surface A).
#   v2 — fix zonage /ask : multi-zones joint depuis reglement_plu.zones (commit 234c978, 15/07).
CONTEXT_VERSION = 2


def normalize_question(q: str) -> str:
    """Normalise une question pour maximiser les hits de cache (casse, espaces, ponctuation de bord)."""
    q = (q or "").strip().lower()
    q = re.sub(r"\s+", " ", q)
    return q.strip(" ?!.,;:")


def _qhash(q: str) -> str:
    # le sel de version orphelinise tout le cache antérieur à un changement de contexte (cf. CONTEXT_VERSION)
    salted = f"ctx{CONTEXT_VERSION}|{normalize_question(q)}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()[:32]


def cache_get(db: Session, idu: str, run_label: str, question: str) -> dict | None:
    _ensure_cache_table(db)
    return db.execute(text("SELECT response FROM ia_cache WHERE idu=:i AND run_label=:r AND question_hash=:h"),
                      {"i": idu, "r": run_label, "h": _qhash(question)}).scalar()


def cache_put(db: Session, idu: str, run_label: str, question: str, response: dict, *, kind: str = "") -> None:
    _ensure_cache_table(db)
    db.execute(text(
        "INSERT INTO ia_cache (idu, run_label, question_hash, kind, question, response, computed_at) "
        "VALUES (:i, :r, :h, :k, :q, CAST(:resp AS jsonb), now()) "
        "ON CONFLICT (idu, run_label, question_hash) DO UPDATE SET response=EXCLUDED.response, computed_at=now()"),
        {"i": idu, "r": run_label, "h": _qhash(question), "k": kind[:24], "q": question,
         "resp": json.dumps(response, ensure_ascii=False, default=str)})


# ═════════════════════════ Appel modèle UNIQUE ═════════════════════════
@dataclass
class IAResult:
    text: str
    model: str
    degraded: bool = False          # repli stub (clé absente / erreur) — jamais silencieux
    reason: str | None = None
    sources: list[str] = field(default_factory=list)
    rejected: bool = False          # validation de sortie a rejeté la prose
    raw: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0


def complete(db: Session | None, *, kind: str, system: str, context: dict[str, Any] | str,
             model: str = MODEL_FACTUAL, max_tokens: int = 700,
             temperature: float = DEFAULT_TEMPERATURE, timeout: float = DEFAULT_TIMEOUT,
             history: list[dict] | None = None,
             validate: bool = False, require_sources: bool = True) -> IAResult:
    """Appel modèle UNIQUE (routeur haiku/sonnet via `model`). Sérialisation SÛRE (`default=str`) →
    plus jamais de 500 Decimal. Repli `degraded` flaggé si pas de clé. Log de coût centralisé.

    Si `validate=True` : la sortie passe la validation hybride 1+3 avant d'être renvoyée ; en cas de
    rejet, `rejected=True` et `text` porte un message honnête (jamais l'affirmation douteuse)."""
    user_content = context if isinstance(context, str) else json.dumps(context, ensure_ascii=False, default=str)
    if not has_key():
        return IAResult(text="", model=model, degraded=True, reason="no_key")

    import anthropic
    client = anthropic.Anthropic(timeout=timeout, max_retries=DEFAULT_RETRIES)
    msgs = list(history or []) + [{"role": "user", "content": user_content}]
    try:
        msg = client.messages.create(model=model, max_tokens=max_tokens, temperature=temperature,
                                     system=system, messages=msgs)
    except Exception as exc:  # noqa: BLE001
        _note_error(exc)
        return IAResult(text="", model=model, degraded=True, reason=last_error())
    _note_success()
    prose = "".join(getattr(b, "text", "") for b in msg.content).strip()
    tin, tout = msg.usage.input_tokens, msg.usage.output_tokens
    _log_cost(db, kind, model, False, tin, tout)

    if validate:
        if isinstance(context, str):
            raise ValueError("validate=True exige un contexte structuré (dict), pas une chaîne")
        chk = validate_output(prose, context, require_sources=require_sources)
        if not chk.ok:
            return IAResult(text="Je ne peux pas répondre de façon sourcée sur ce point.",
                            model=model, reason=chk.reason, rejected=True, raw=prose,
                            tokens_in=tin, tokens_out=tout)
        return IAResult(text=chk.text, model=model, sources=chk.sources, raw=prose,
                        tokens_in=tin, tokens_out=tout)
    return IAResult(text=prose, model=model, tokens_in=tin, tokens_out=tout)
