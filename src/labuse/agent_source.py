"""CIRCUIT-1 lot 6 — LES AGENTS DE SOURCE : à la demande, jamais en cron par défaut.

Un agent = UN appel Claude (surface `agent_source`, modèle raisonnement, outil web_search de
l'API) sur la FICHE DE RECHERCHE d'un réservoir (nom, producteur, URL connue, format du
millésime, dernier vu par la sonde). Sortie JSON STRICT :
  {verdict: a_jour|nouvelle|introuvable|vide, version_trouvee, date_publication,
   preuve:{url, extrait}, cherche:[…], sonde_proposee:{methode, url}|null, page_js: oui|non|inconnu}

ANTI-INVENTION (6.2) : `a_jour` et `nouvelle` EXIGENT une preuve datée (url + extrait portant
une date) réellement citée — sinon le verdict est FORCÉ à `introuvable` avec la raison. Un
agent ne télécharge rien, n'ingère rien : il n'écrit que `source_agent_rapports` et, sur
verdict `nouvelle`, `source_veille.dernier_vu/dernier_statut` (ce qui fait apparaître la
vanne). Coût au ledger `ia_log` (core._log_cost). Chaque passage entre au `circuit_journal`.
"""
from __future__ import annotations

import json
import logging
import re

from sqlalchemy import text

log = logging.getLogger("labuse.agent_source")

DDL = """
CREATE TABLE IF NOT EXISTS source_agent_rapports (
  id bigserial PRIMARY KEY,
  ts timestamptz NOT NULL DEFAULT now(),
  source_id int NOT NULL,
  source_nom text NOT NULL,
  verdict varchar(16) NOT NULL,          -- a_jour | nouvelle | introuvable | vide
  version_trouvee text,
  date_publication text,
  preuve jsonb,                          -- {url, extrait}
  cherche jsonb,                         -- les pistes essayées
  sonde_proposee jsonb,                  -- {methode, url} | null
  page_js varchar(8),                    -- oui | non | inconnu
  raison text,                           -- pourquoi introuvable / verdict forcé
  par varchar(120)
)
"""

SYSTEM = (
    "Tu es l'AGENT DE VEILLE d'une source de données publiques pour LABUSE (La Réunion). "
    "MISSION : trouver, avec l'outil web_search, la DERNIÈRE VERSION publiée par le producteur "
    "de la source décrite, et la comparer au millésime servi. Tu ne télécharges RIEN, tu "
    "n'ingères RIEN : tu constates et tu cites.\n"
    "RÈGLES ABSOLUES :\n"
    "1. Réponds UNIQUEMENT un objet JSON (aucun texte autour) avec les clés : verdict "
    "(a_jour|nouvelle|introuvable|vide), version_trouvee, date_publication, "
    "preuve {url, extrait}, cherche (liste des pistes essayées), sonde_proposee "
    "({methode: api|page|entete|temoin, url} ou null), page_js (oui|non|inconnu).\n"
    "2. `a_jour` ou `nouvelle` SEULEMENT si tu as LU une page qui porte une date/version : "
    "l'extrait cité doit contenir cette date, copiée telle quelle. Sans preuve datée → "
    "introuvable, et tu listes ce que tu as cherché.\n"
    "3. `vide` = le jeu a disparu chez le producteur (page 404/410 constatée).\n"
    "4. `sonde_proposee` : une URL STABLE qui porte le millésime (API JSON de préférence) pour "
    "la sonde de nuit — null si aucune ne convient.\n"
    "5. `page_js: oui` si la page utile ne se lit qu'avec JavaScript (tu n'y as pas accès)."
)

#: une date reconnaissable dans l'extrait (2026, 06/2026, 2026-09-05, « septembre 2026 »…)
_DATE_RX = re.compile(
    r"(20\d{2}[-/\.]\d{1,2}([-/\.]\d{1,2})?|\d{1,2}[-/\.]20\d{2}|20\d{2}|"
    r"janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)",
    re.IGNORECASE)


def ensure(db) -> None:
    db.execute(text(DDL))


def fiche_de_recherche(db, source_id: int) -> dict | None:
    """La fiche transmise à l'agent : catalogue + veille (dernier vu par la sonde)."""
    r = db.execute(text(
        "SELECT d.id, d.name, d.provider, d.source_millesime, d.source_cadence, d.endpoint_url,"
        "       d.documentation_url, v.methode, v.dernier_vu, v.dernier_statut, v.url_version"
        " FROM data_sources d LEFT JOIN source_veille v ON v.source_id = d.id"
        " WHERE d.id = :i"), {"i": source_id}).mappings().first()
    if not r:
        return None
    return {
        "source": r["name"], "producteur": r["provider"],
        "millesime_servi": r["source_millesime"], "cadence_connue": r["source_cadence"],
        "url_producteur_connue": r["endpoint_url"] or r["documentation_url"],
        "sonde_actuelle": ({"methode": r["methode"], "url": r["url_version"],
                            "dernier_vu": r["dernier_vu"], "statut": r["dernier_statut"]}
                           if r["methode"] else None),
    }


def _appel_reel(db, fiche: dict) -> str:
    """L'appel API réel (web_search natif, même patron que copilote recherche_web). Injectable
    en test (paramètre `appel` de lancer_agent) — les fixtures ne touchent jamais le réseau."""
    import anthropic

    from .ai import core
    from .ai_models import model_for
    model = model_for("agent_source")
    client = anthropic.Anthropic(timeout=120, max_retries=1)
    msg = client.messages.create(
        model=model, max_tokens=900, system=SYSTEM,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
        messages=[{"role": "user", "content": json.dumps(fiche, ensure_ascii=False, default=str)}])
    texte = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    try:
        core._log_cost(db, "agent_source", model, False,
                       msg.usage.input_tokens, msg.usage.output_tokens)
    except Exception:  # noqa: BLE001 — le ledger ne bloque jamais l'agent
        pass
    return texte


def _valider(brut: str) -> tuple[dict, str | None]:
    """Parse + ANTI-INVENTION : rend (rapport, raison_forçage|None). Un verdict positif sans
    preuve datée est FORCÉ à `introuvable` (la raison le dit)."""
    m = re.search(r"\{.*\}", brut, re.S)
    if not m:
        return ({"verdict": "introuvable", "cherche": [],
                 "preuve": None, "sonde_proposee": None, "page_js": "inconnu",
                 "version_trouvee": None, "date_publication": None},
                "sortie non-JSON (aucun objet trouvé)")
    try:
        d = json.loads(m.group(0))
    except Exception:  # noqa: BLE001
        return ({"verdict": "introuvable", "cherche": [], "preuve": None,
                 "sonde_proposee": None, "page_js": "inconnu",
                 "version_trouvee": None, "date_publication": None}, "JSON invalide")
    d.setdefault("preuve", None)
    d.setdefault("cherche", [])
    d.setdefault("sonde_proposee", None)
    d.setdefault("page_js", "inconnu")
    d.setdefault("version_trouvee", None)
    d.setdefault("date_publication", None)
    if d.get("verdict") not in ("a_jour", "nouvelle", "introuvable", "vide"):
        d["verdict"] = "introuvable"
        return d, f"verdict hors énum ({d.get('verdict')!r})"
    if d["verdict"] in ("a_jour", "nouvelle"):
        p = d.get("preuve") or {}
        extrait = str(p.get("extrait") or "")
        if not (p.get("url") and extrait and _DATE_RX.search(extrait)):
            raison = ("verdict forcé à introuvable : preuve absente ou extrait sans date "
                      f"(règle 6.2) — verdict annoncé : {d['verdict']}")
            d["verdict"] = "introuvable"
            return d, raison
    return d, None


def lancer_agent(db, source_id: int, *, par: str = "cli", appel=None) -> dict:
    """UN agent sur UN réservoir. Écrit source_agent_rapports (+ source_veille sur `nouvelle`),
    journalise. `appel(db, fiche) -> str` injectable (fixtures de test)."""
    from . import circuit_journal
    ensure(db)
    fiche = fiche_de_recherche(db, source_id)
    if fiche is None:
        return {"ok": False, "motif": f"source {source_id} inconnue"}
    brut = (appel or _appel_reel)(db, fiche)
    rapport, raison = _valider(brut)
    db.execute(text(
        "INSERT INTO source_agent_rapports (source_id, source_nom, verdict, version_trouvee,"
        " date_publication, preuve, cherche, sonde_proposee, page_js, raison, par)"
        " VALUES (:i, :n, :v, :vt, :dp, :pr, :ch, :sp, :js, :ra, :par)"),
        {"i": source_id, "n": fiche["source"], "v": rapport["verdict"],
         "vt": rapport.get("version_trouvee"), "dp": rapport.get("date_publication"),
         "pr": json.dumps(rapport.get("preuve"), ensure_ascii=False),
         "ch": json.dumps(rapport.get("cherche"), ensure_ascii=False),
         "sp": json.dumps(rapport.get("sonde_proposee"), ensure_ascii=False),
         "js": rapport.get("page_js"), "ra": raison, "par": par[:120]})
    if rapport["verdict"] == "nouvelle":
        # la vanne apparaît : la veille porte le millésime VU (jamais servi tel quel — doctrine)
        db.execute(text(
            "UPDATE source_veille SET dernier_vu = :vu, dernier_statut = 'nouvelle_version',"
            " updated_at = now() WHERE source_id = :i"),
            {"vu": str(rapport.get("version_trouvee") or rapport.get("date_publication") or "")[:64],
             "i": source_id})
    circuit_journal.journaliser(db, "agent", fiche["source"], par, rapport["verdict"],
                                {"raison": raison, "page_js": rapport.get("page_js")})
    return {"ok": True, "source": fiche["source"], **rapport, "raison_forcage": raison}


def lancer_agents(db_factory, source_ids: list[int], *, par: str = "cli",
                  appel=None, max_parallel: int = 5) -> list[dict]:
    """6.4 — plusieurs agents, 5 EN PARALLÈLE AU PLUS (ThreadPool), chacun sa session."""
    from concurrent.futures import ThreadPoolExecutor

    def _un(sid: int) -> dict:
        with db_factory() as s:
            out = lancer_agent(s, sid, par=par, appel=appel)
            s.commit()
            return out

    with ThreadPoolExecutor(max_workers=min(max_parallel, 5)) as ex:
        return list(ex.map(_un, source_ids))
