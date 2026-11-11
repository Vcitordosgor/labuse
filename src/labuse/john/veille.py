"""JOHN-TAYLOR-1 — la VEILLE DE NUIT (informe, n'injecte rien).

Le mandat : « Veille, chaque nuit, résultats dans l'onglet et dans le résumé quand ils comptent :
réglementaire (Légifrance et BOFiP : urbanisme, taxe d'aménagement, fiscalité DOM, lois logement ; PLU,
SCOT et PPR de La Réunion) ; sources de données (nouveaux millésimes annoncés, changements d'API) ;
concurrence (KelFoncier, Capaciti et équivalents). Chaque élément porte sa source, sa date et un libellé :
"à intégrer", "source B à valider", "info", "concurrence". La veille informe ; elle n'injecte rien. »

Un passage = UN appel modèle (Haiku, kind john-veille, outil web_search natif — même patron que
l'agent de source) qui rend un JSON strict `{items: [...]}`. ANTI-INVENTION : un item sans source NI
date est écarté (on ne garde que ce qui est daté et cité). Les items sont rangés dans `john_veille`.
Jamais d'injection : la veille pose des FAITS à lire, pas des actions.
"""
from __future__ import annotations

import json
import logging
import re

from sqlalchemy import text

from . import budget

log = logging.getLogger("labuse.john.veille")

DDL = """
CREATE TABLE IF NOT EXISTS john_veille (
  id       bigserial PRIMARY KEY,
  ts       timestamptz NOT NULL DEFAULT now(),
  axe      varchar(16) NOT NULL,        -- reglementaire | sources | concurrence
  titre    text NOT NULL,
  source   text NOT NULL,
  date_vue varchar(40),
  libelle  varchar(24) NOT NULL,        -- à intégrer | source B à valider | info | concurrence
  url      text,
  extrait  text
)
"""

LIBELLES = frozenset({"à intégrer", "source B à valider", "info", "concurrence"})
AXES = frozenset({"reglementaire", "sources", "concurrence"})
_DATE_RX = re.compile(r"20\d{2}|\d{1,2}[-/]20\d{2}|janvier|février|mars|avril|mai|juin|juillet|"
                      r"août|septembre|octobre|novembre|décembre", re.I)

SYSTEME = (
    "Tu es JOHN TAYLOR, le veilleur de LABUSE (foncier à La Réunion). MISSION : avec l'outil web_search, "
    "repérer les nouveautés qui comptent pour LABUSE, sur TROIS axes :\n"
    "1. reglementaire — Légifrance et BOFiP (urbanisme, taxe d'aménagement, fiscalité DOM, lois "
    "logement) ; PLU, SCOT et PPR de La Réunion (modifications, révisions, approbations) ;\n"
    "2. sources — nouveaux millésimes annoncés, changements d'API des producteurs de données ;\n"
    "3. concurrence — KelFoncier, Capaciti et équivalents (nouveautés).\n"
    "RÈGLES ABSOLUES :\n"
    "- Réponds UNIQUEMENT un objet JSON : {\"items\": [{axe, titre, source, date_vue, libelle, url, "
    "extrait}]}. axe ∈ {reglementaire, sources, concurrence}. libelle ∈ {\"à intégrer\", \"source B à "
    "valider\", \"info\", \"concurrence\"}.\n"
    "- Chaque item DOIT porter une source ET une date réelles, citées (extrait avec la date). Sans "
    "date/source vérifiée, n'invente RIEN : n'émets pas l'item.\n"
    "- Tu INFORMES. Tu ne proposes aucune injection ni action."
)


def ensure(db) -> None:
    db.execute(text(DDL))


def _appel_reel(db) -> str:
    import anthropic

    from ..ai import core
    from ..ai_models import est_not_found, model_for, repli_pour
    model = model_for("john-veille")
    client = anthropic.Anthropic(timeout=120, max_retries=1)

    def _tenter(m):
        # pas de `temperature` (haiku-5-5 la refuse) ; repli 4.x si not_found.
        return client.messages.create(
            model=m, max_tokens=1500, system=SYSTEME,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
            messages=[{"role": "user", "content": "Fais la veille de cette nuit pour LABUSE (les 3 axes)."}])
    try:
        msg = _tenter(model)
    except Exception as exc:  # noqa: BLE001
        rep = repli_pour(model)
        if not (rep and est_not_found(exc)):
            raise
        log.warning("john-veille : modèle %s introuvable → repli %s", model, rep)
        model = rep
        msg = _tenter(model)
    texte = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    try:
        core._log_cost(db, "john-veille", model, False, msg.usage.input_tokens, msg.usage.output_tokens)
    except Exception:  # noqa: BLE001
        pass
    return texte


def _parser(brut: str) -> list[dict]:
    """Extrait les items du JSON. ANTI-INVENTION : garde seulement ce qui a source + date reconnue et
    des énumérations valides (axe/libelle normalisés, les inconnus → 'info')."""
    d = None
    m = re.search(r"\{.*\}", brut or "", re.S)
    if m:
        try:
            d = json.loads(m.group(0))
        except Exception:  # noqa: BLE001
            d = None
    items = (d or {}).get("items") if isinstance(d, dict) else None
    out = []
    for it in (items or []):
        if not isinstance(it, dict):
            continue
        source = str(it.get("source") or "").strip()
        date_vue = str(it.get("date_vue") or "").strip()
        titre = str(it.get("titre") or "").strip()
        extrait = str(it.get("extrait") or "")
        if not (titre and source and (date_vue or _DATE_RX.search(extrait))):
            continue                                    # non daté / non sourcé → écarté
        axe = it.get("axe") if it.get("axe") in AXES else "reglementaire"
        lib = it.get("libelle") if it.get("libelle") in LIBELLES else "info"
        out.append({"axe": axe, "titre": titre, "source": source, "date_vue": date_vue or None,
                    "libelle": lib, "url": (it.get("url") or None), "extrait": extrait[:500] or None})
    return out


def lancer(db, *, appel=None, settings=None) -> dict:
    """Un passage de veille. Au plafond → pause (aucun appel). Range les items dans `john_veille`.
    Retourne {ok, pause?, n, items}."""
    if settings is None:
        from ..config import get_settings
        settings = get_settings()
    ensure(db)
    e = budget.etat(db, settings)
    if e.en_pause:
        from .budget import message_pause
        return {"ok": False, "pause": True, "n": 0, "items": [], "message": message_pause(e)}
    appel = appel or _appel_reel
    try:
        brut = appel(db)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "n": 0, "items": [], "erreur": f"{type(exc).__name__}: {exc}"}
    items = _parser(brut)
    for it in items:
        db.execute(text(
            "INSERT INTO john_veille (axe, titre, source, date_vue, libelle, url, extrait) "
            "VALUES (:a, :t, :s, :d, :l, :u, :e)"),
            {"a": it["axe"], "t": it["titre"], "s": it["source"], "d": it["date_vue"],
             "l": it["libelle"], "u": it["url"], "e": it["extrait"]})
    return {"ok": True, "n": len(items), "items": items}


def signaler_retard_source(db, nom: str, millesime_attendu, millesime_servi) -> bool:
    """FRAICHEUR-FIX-1 (point 7) — remonte UNE source en retard à l'onglet veille de John (axe
    « sources »), avec le nom de la source et le millésime attendu. IDEMPOTENT par jour : on ne
    redépose pas le même retard tant qu'il n'a pas changé de millésime attendu (dédup source + date_vue).
    Retourne True si un item a été posé."""
    ensure(db)
    titre = f"{nom} — en retard (millésime attendu {millesime_attendu})"
    deja = db.execute(text(
        "SELECT 1 FROM john_veille WHERE axe = 'sources' AND source = :s "
        "AND date_vue = :d AND ts::date = (now() AT TIME ZONE 'UTC')::date"),
        {"s": nom, "d": str(millesime_attendu)}).scalar()
    if deja:
        return False
    db.execute(text(
        "INSERT INTO john_veille (axe, titre, source, date_vue, libelle, url, extrait) "
        "VALUES ('sources', :t, :s, :d, 'à intégrer', '/sources', :e)"),
        {"t": titre, "s": nom, "d": str(millesime_attendu),
         "e": f"L'amont publie {millesime_attendu} ; LABUSE sert {millesime_servi or 'un millésime non prouvé'}. "
              "À recharger."})
    return True


def recentes(db, n: int = 20) -> list[dict]:
    """Les derniers éléments de veille (pour l'onglet)."""
    ensure(db)
    rows = db.execute(text(
        "SELECT ts, axe, titre, source, date_vue, libelle, url, extrait FROM john_veille "
        "ORDER BY ts DESC LIMIT :n"), {"n": max(1, min(n, 100))}).mappings().all()
    return [{"ts": r["ts"].isoformat(), "axe": r["axe"], "titre": r["titre"], "source": r["source"],
             "date_vue": r["date_vue"], "libelle": r["libelle"], "url": r["url"], "extrait": r["extrait"]}
            for r in rows]
