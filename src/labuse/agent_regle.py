"""CIRCUIT-4 lot 2 — L'AGENT « RÈGLE » : à la demande (et par le job `regles-references`,
désactivé par défaut), jamais en continu.

Un agent = UN appel Claude (surface `agent_regle`, modèle raisonnement, outil web_search natif)
sur la FICHE DE RECHERCHE d'une règle (donnée, formule codée, référence connue : titre/article/
url/version). Mission : RELIRE la référence chez l'éditeur du texte (Légifrance, service-public,
impots.gouv, INSEE, ADEME, DEAL, SDES) et ramener l'extrait, l'URL, la date de version — pour
détecter une VERSION NOUVELLE d'un texte (un article change, un barème est réindexé).

Sortie JSON STRICT :
  {verdict: confirmee|version_nouvelle|introuvable, reference:{titre, article, url, version,
   extrait}, cherche:[…], page_js: oui|non|inconnu}

ANTI-INVENTION (même règle 6.2 que l'agent de source) : `confirmee` et `version_nouvelle`
EXIGENT une reference complète avec un extrait portant une date/version réellement citée —
sinon le verdict est FORCÉ à `introuvable` avec la raison. Une page en JavaScript est notée
`page_js: oui` (« introuvable, navigateur nécessaire »). L'agent n'écrit JAMAIS dans les fiches
(le code est la vérité ; un humain relit et met à jour) : il n'écrit que `regle_agent_rapports`.
Coût au ledger `ia_log`. Chaque passage entre au `circuit_journal` (geste `agent`)."""
from __future__ import annotations

import json
import logging
import re

from sqlalchemy import text

log = logging.getLogger("labuse.agent_regle")

DDL = """
CREATE TABLE IF NOT EXISTS regle_agent_rapports (
  id bigserial PRIMARY KEY,
  ts timestamptz NOT NULL DEFAULT now(),
  donnee_id text NOT NULL,
  verdict varchar(20) NOT NULL,          -- confirmee | version_nouvelle | introuvable
  reference jsonb,                       -- {titre, article, url, version, extrait}
  cherche jsonb,
  page_js varchar(8),
  raison text,
  par varchar(120)
)
"""

SYSTEM = (
    "Tu es l'AGENT DE RÈGLE de LABUSE (La Réunion). MISSION : avec l'outil web_search, RELIRE la "
    "référence externe qui fonde un calcul (article de loi, barème, arrêté, définition INSEE) chez "
    "son éditeur officiel (Légifrance, service-public, impots.gouv/BOFiP, INSEE, ADEME, SDES, "
    "DEAL), vérifier si la version connue est toujours en vigueur, et CITER le passage.\n"
    "RÈGLES ABSOLUES :\n"
    "1. Réponds UNIQUEMENT un objet JSON : verdict (confirmee|version_nouvelle|introuvable), "
    "reference {titre, article, url, version, extrait}, cherche (pistes essayées), "
    "page_js (oui|non|inconnu).\n"
    "2. `confirmee` ou `version_nouvelle` SEULEMENT si tu as LU la page : l'extrait doit être "
    "copié tel quel et la version doit porter une date (« en vigueur au … », date d'article). "
    "Sans passage daté → introuvable, et tu listes ce que tu as cherché.\n"
    "3. `version_nouvelle` = le texte a changé depuis la version connue de la fiche (modification, "
    "abrogation, réindexation d'un barème) — cite le NOUVEAU passage.\n"
    "4. `page_js: oui` si la page utile ne se lit qu'avec JavaScript (tu n'y as pas accès) : le "
    "verdict est alors introuvable, raison « navigateur nécessaire ».\n"
    "5. Tu ne juges JAMAIS la conformité du code (c'est un travail humain) : tu rapportes le texte."
)

#: une date/version reconnaissable dans l'extrait ou la version (2026, 06/2026, « en vigueur »…)
_DATE_RX = re.compile(
    r"(20\d{2}[-/\.]\d{1,2}([-/\.]\d{1,2})?|\d{1,2}[-/\.]20\d{2}|20\d{2}|en vigueur|"
    r"janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)",
    re.IGNORECASE)

VERDICTS = ("confirmee", "version_nouvelle", "introuvable")


def ensure(db) -> None:
    db.execute(text(DDL))


def fiche_de_recherche(donnee_id: str) -> dict | None:
    """La fiche transmise à l'agent : la fiche de règle (formule + référence connue)."""
    from . import regles
    fiches = regles.charger()
    f = fiches.get(donnee_id)
    if f is None:
        return None
    r = f.reference
    return {
        "donnee": donnee_id, "classe": f.classe, "formule_codee": f.formule_codee,
        "reference_connue": ({"titre": r.titre, "article": r.article, "url": r.url,
                              "version": r.version, "lu_le": r.lu_le} if r else None),
        "verifie_le": f.verifie_le,
    }


def _appel_reel(db, fiche: dict) -> str:
    """L'appel API réel (web_search natif, même patron qu'agent_source). Injectable en test."""
    import anthropic

    from .ai import core
    from .ai_models import model_for
    model = model_for("agent_regle")
    client = anthropic.Anthropic(timeout=120, max_retries=1)
    msg = client.messages.create(
        model=model, max_tokens=1200, system=SYSTEM,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
        messages=[{"role": "user", "content": json.dumps(fiche, ensure_ascii=False, default=str)}])
    texte = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    try:
        core._log_cost(db, "agent_regle", model, False,
                       msg.usage.input_tokens, msg.usage.output_tokens)
    except Exception:  # noqa: BLE001 — le ledger ne bloque jamais l'agent
        pass
    return texte


def _valider(brut: str) -> tuple[dict, str | None]:
    """Parse + ANTI-INVENTION : un verdict positif sans référence complète datée est FORCÉ à
    `introuvable` (la raison le dit)."""
    vide = {"verdict": "introuvable", "reference": None, "cherche": [], "page_js": "inconnu"}
    m = re.search(r"\{.*\}", brut, re.S)
    if not m:
        return dict(vide), "sortie non-JSON (aucun objet trouvé)"
    try:
        d = json.loads(m.group(0))
    except Exception:  # noqa: BLE001
        return dict(vide), "JSON invalide"
    d.setdefault("reference", None)
    d.setdefault("cherche", [])
    d.setdefault("page_js", "inconnu")
    if d.get("verdict") not in VERDICTS:
        raison = f"verdict hors énum ({d.get('verdict')!r})"
        d["verdict"] = "introuvable"
        return d, raison
    if d["verdict"] in ("confirmee", "version_nouvelle"):
        r = d.get("reference") or {}
        extrait = str(r.get("extrait") or "")
        version = str(r.get("version") or "")
        if not (r.get("url") and extrait and (_DATE_RX.search(extrait) or _DATE_RX.search(version))):
            raison = ("verdict forcé à introuvable : référence incomplète ou extrait sans date "
                      f"(règle 2 du mandat) — verdict annoncé : {d['verdict']}")
            d["verdict"] = "introuvable"
            return d, raison
    return d, None


def lancer_agent(db, donnee_id: str, *, par: str = "cli", appel=None) -> dict:
    """UN agent sur UNE fiche de règle. Écrit regle_agent_rapports, journalise. N'ÉCRIT JAMAIS
    la fiche (le code est la vérité — un humain relit le rapport et met à jour)."""
    from . import circuit_journal
    ensure(db)
    fiche = fiche_de_recherche(donnee_id)
    if fiche is None:
        return {"ok": False, "motif": f"aucune fiche de règle pour {donnee_id!r}"}
    brut = (appel or _appel_reel)(db, fiche)
    rapport, raison = _valider(brut)
    db.execute(text(
        "INSERT INTO regle_agent_rapports (donnee_id, verdict, reference, cherche, page_js,"
        " raison, par) VALUES (:d, :v, :r, :c, :js, :ra, :par)"),
        {"d": donnee_id, "v": rapport["verdict"],
         "r": json.dumps(rapport.get("reference"), ensure_ascii=False),
         "c": json.dumps(rapport.get("cherche"), ensure_ascii=False),
         "js": rapport.get("page_js"), "ra": raison, "par": par[:120]})
    circuit_journal.journaliser(db, "agent", f"règle {donnee_id}", par, rapport["verdict"],
                                {"raison": raison, "page_js": rapport.get("page_js")})
    return {"ok": True, "donnee": donnee_id, **rapport, "raison_forcage": raison}


def fiches_a_reverifier(plus_de_jours: int = 180) -> list[str]:
    """5.4 — les fiches dont la référence date de plus de N jours (un texte peut changer) :
    la cible du job mensuel `regles-references`."""
    from datetime import date, timedelta

    from . import regles
    fiches = regles.charger()
    seuil = date.today() - timedelta(days=plus_de_jours)
    cibles = []
    for did, f in fiches.items():
        if f.reference is None or did != f.donnees[0]:
            continue                      # une fiche = un passage (sur sa donnée représentative)
        try:
            lu = date.fromisoformat((f.reference.lu_le or f.verifie_le or "")[:10])
        except ValueError:
            cibles.append(did)            # date illisible → à revérifier
            continue
        if lu <= seuil:
            cibles.append(did)
    return sorted(cibles)
