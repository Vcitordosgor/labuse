"""PROMO-1 (P2) — COLLECTE ASSISTÉE : l'admin colle l'URL du portfolio d'un promoteur, on en tire la
LISTE de ses programmes {nom, commune, URL, année} par le modèle (ai_models.py, jamais en dur). L'admin
corrige et valide LIGNE À LIGNE avant insertion — rien n'entre sans validation (endpoint de validation).

DOCTRINE : on ne relève que des FAITS et le LIEN — jamais les photos ni les textes descriptifs du
promoteur (droit d'auteur). Le prompt l'exige et la sortie est réduite à {nom, commune, url, annee} ;
tout descriptif éventuel est jeté. Anti-invention : un champ absent = null (jamais deviné).

Le fetch est UN geste ADMIN, ponctuel, sur le SITE PROPRE du promoteur (pas un portail d'annonces) — il
n'y a pas de collecte automatisée de portail (doctrine Radar). L'appel modèle est journalisé (leçon S6).
"""
from __future__ import annotations

import json
import logging
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from sqlalchemy.orm import Session

from ..ai import core

log = logging.getLogger("labuse.promo")

FETCH_TIMEOUT = 15.0
MAX_TEXTE = 9000        # on tronque la page (le modèle n'a pas besoin de tout — juste la liste)
MAX_LIENS = 120
_UA = "Mozilla/5.0 (LABUSE veille promoteurs; +https://labuse.immo)"

_PROMPT = """Tu lis le contenu d'une page « portfolio / nos programmes » du SITE PROPRE d'un promoteur
immobilier à La Réunion. Tu EXTRAIS la LISTE de ses programmes immobiliers. Tu n'inventes RIEN : si une
information n'est pas présente sur la page, sa valeur est null. Tu ne déduis pas, tu n'estimes pas.

Tu ne retiens QUE des FAITS et le LIEN — JAMAIS de texte descriptif ni d'accroche marketing.

Réponds UNIQUEMENT par un objet JSON (aucun texte autour) de la forme :
{"programmes": [ {"nom": <str>, "commune": <str|null>, "url": <str|null>, "annee": <int|null>}, ... ]}
- nom : le nom du programme (ex. « Les Terrasses de Bellepierre ») — jamais une phrase ;
- commune : la commune de La Réunion où il se situe, telle qu'écrite, sinon null ;
- url : l'URL de la PAGE INDIVIDUELLE du programme si elle figure dans la liste des liens fournie,
  sinon null (n'invente pas d'URL) ;
- annee : l'année de livraison ou de commercialisation SI elle est écrite, sinon null.
Si la page ne liste aucun programme, réponds {"programmes": []}. N'ajoute aucun autre champ."""


def _domaine(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


class _Extracteur(HTMLParser):
    """Parseur stdlib (aucune dépendance externe) : accumule le TEXTE visible (hors script/style) et les
    LIENS (libellé + href). Sert à donner au modèle la liste des programmes et leurs URL."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.textes: list[str] = []
        self.liens: list[tuple[str, str]] = []
        self._skip = 0
        self._a_href: str | None = None
        self._a_texte: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        elif tag == "a":
            href = dict(attrs).get("href")
            if href:
                self._a_href, self._a_texte = href.strip(), []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1
        elif tag == "a" and self._a_href is not None:
            self.liens.append((" ".join("".join(self._a_texte).split())[:80], self._a_href))
            self._a_href = None

    def handle_data(self, data):
        if self._skip:
            return
        d = data.strip()
        if d:
            self.textes.append(d)
            if self._a_href is not None:
                self._a_texte.append(data)


def fetch_texte(url: str) -> tuple[str | None, list[str], str | None]:
    """Récupère la page (geste admin ponctuel) et en tire (texte_visible_tronqué, liens_absolus, motif).
    `motif` non-None = échec honnête (jamais une invention de contenu). Zéro dépendance externe (stdlib)."""
    try:
        import httpx
    except Exception as exc:  # noqa: BLE001
        return None, [], f"dépendance manquante ({exc})"
    if not re.match(r"^https?://", url or ""):
        return None, [], "URL invalide (doit commencer par http:// ou https://)"
    try:
        r = httpx.get(url, timeout=FETCH_TIMEOUT, follow_redirects=True, headers={"User-Agent": _UA})
        r.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        return None, [], f"page injoignable : {type(exc).__name__}"
    p = _Extracteur()
    try:
        p.feed(r.text)
    except Exception as exc:  # noqa: BLE001
        return None, [], f"page illisible ({type(exc).__name__})"
    texte = re.sub(r"\n{3,}", "\n\n", "\n".join(p.textes)).strip()[:MAX_TEXTE]
    dom = _domaine(url)
    liens: list[str] = []
    seen: set[str] = set()
    for libelle, href in p.liens:
        abs_href = urljoin(url, href)
        if not abs_href.startswith("http") or _domaine(abs_href) != dom or abs_href in seen:
            continue
        seen.add(abs_href)
        liens.append(f"{libelle} → {abs_href}" if libelle else abs_href)
        if len(liens) >= MAX_LIENS:
            break
    return texte, liens, None


def extraire_programmes(db: Session | None, texte: str, liens: list[str]) -> dict:
    """Le modèle tire la liste {nom, commune, url, annee}. Retourne {ok, programmes, motif?}. `ok=False`
    (motif honnête) si pas de clé, dégradé, ou réponse non-JSON — jamais un programme inventé.
    L'appel modèle est journalisé explicitement (leçon S6, EN PLUS du ledger de core.complete)."""
    contexte = "LIENS DE LA PAGE (libellé → URL) :\n" + "\n".join(liens[:MAX_LIENS]) + \
               "\n\nTEXTE VISIBLE DE LA PAGE :\n" + (texte or "")
    log.info("collecte programmes — appel modèle %s (%d liens, %d car.)", core.MODEL_FACTUAL, len(liens), len(texte or ""))
    r = core.complete(db, kind="promo_collecte", system=_PROMPT, context=contexte,
                      model=core.MODEL_FACTUAL, max_tokens=1500)
    if r.degraded:
        log.error("collecte programmes — appel modèle DÉGRADÉ : %s", r.reason)
        return {"ok": False, "motif": r.reason or "IA indisponible"}
    obj = _json_liste(r.text)
    if obj is None:
        return {"ok": False, "motif": "réponse non-JSON — rien extrait (aucun programme inventé)",
                "brut": r.text[:200]}
    progs = []
    for p in obj:
        if not isinstance(p, dict):
            continue
        nom = (p.get("nom") or "").strip()
        if not nom:
            continue                          # sans nom, ce n'est pas un programme exploitable
        url = p.get("url")
        url = url.strip() if isinstance(url, str) and url.strip().startswith("http") else None
        annee = p.get("annee")
        try:
            annee = int(annee) if annee is not None and 1990 <= int(annee) <= 2100 else None
        except (TypeError, ValueError):
            annee = None
        commune = (p.get("commune") or None)
        commune = commune.strip() if isinstance(commune, str) and commune.strip() else None
        # DOCTRINE : on ne garde QUE ces 4 faits — aucun descriptif ni visuel n'est retenu.
        progs.append({"nom": nom[:200], "commune": commune, "url": url, "annee": annee})
    return {"ok": True, "programmes": progs}


def _json_liste(prose: str) -> list | None:
    """Extrait la liste `programmes` d'un objet JSON. None si rien de parsable (jamais de réparation)."""
    s = re.sub(r"^```(?:json)?|```$", "", prose.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    progs = obj.get("programmes") if isinstance(obj, dict) else None
    return progs if isinstance(progs, list) else None
