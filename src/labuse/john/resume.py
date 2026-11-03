"""JOHN-TAYLOR-1 — le RÉSUMÉ DU MATIN, écrit par John.

Le mandat : « Résumé du matin à 07h30 Réunion, écrit par John à partir des faits du résumé actuel : ce
qui s'est passé, pourquoi, ce que Vic doit faire, ou "rien n'attend votre décision". Envoyé par mail et
affiché dans l'onglet. Si John échoue, le résumé actuel part tel quel. »

On part donc des FAITS déjà calculés par `jobs_impl._resume_matin_texte` (le résumé actuel), John les
réécrit en clair. Deux filets : (a) si John est en pause (plafond) ou échoue, le résumé actuel part tel
quel ; (b) anti-invention — un nombre du texte de John doit figurer dans les faits (sinon on retombe sur
le résumé actuel). Le préfixe [URGENT]/[INFO] du sujet est conservé (il porte « un geste attendu »).
"""
from __future__ import annotations

from sqlalchemy import text

from . import budget

DDL = """
CREATE TABLE IF NOT EXISTS john_resume (
  id      bigserial PRIMARY KEY,
  jour    date NOT NULL DEFAULT (now() AT TIME ZONE 'Indian/Reunion')::date,
  ts      timestamptz NOT NULL DEFAULT now(),
  urgent  boolean NOT NULL DEFAULT false,
  sujet   text NOT NULL,
  corps   text NOT NULL,
  par     varchar(12) NOT NULL DEFAULT 'john'   -- john | repli
)
"""


def ensure(db) -> None:
    db.execute(text(DDL))


def enregistrer_resume(db, *, urgent: bool, sujet: str, corps: str, par: str) -> None:
    ensure(db)
    db.execute(text(
        "INSERT INTO john_resume (urgent, sujet, corps, par) VALUES (:u, :s, :c, :p)"),
        {"u": urgent, "s": sujet, "c": corps, "p": par[:12]})


def dernier_resume(db) -> dict | None:
    ensure(db)
    r = db.execute(text(
        "SELECT ts, urgent, sujet, corps, par FROM john_resume ORDER BY ts DESC LIMIT 1")).mappings().first()
    if not r:
        return None
    return {"ts": r["ts"].isoformat(), "urgent": r["urgent"], "sujet": r["sujet"],
            "corps": r["corps"], "par": r["par"]}

SYSTEME = (
    "Tu es JOHN TAYLOR, le second de bord de LABUSE. Réécris le résumé d'exploitation du matin pour Vic, "
    "en français simple et direct. Structure : ce qui s'est passé cette nuit, pourquoi, et CE QUE VIC "
    "DOIT FAIRE — ou, si rien n'attend sa décision, dis-le clairement (« rien n'attend votre décision »). "
    "N'invente AUCUN fait ni chiffre : tu ne te sers QUE des faits fournis. Pas de folklore ; un mot de "
    "marin à la rigueur. Reste bref (un court paragraphe ou quelques puces)."
)


def _generer_defaut(db, facts: dict) -> str:
    """Appel modèle réel via le socle (Opus, kind john-resume). Rend '' si dégradé (pas de clé/erreur)."""
    from ..ai import core
    from ..ai_models import MODEL_OPUS
    r = core.complete(db, kind="john-resume", system=SYSTEME, context=facts,
                      model=MODEL_OPUS, max_tokens=700, validate=False)
    return "" if r.degraded else (r.text or "")


def composer_resume_matin(db, settings=None, generer=None) -> tuple[bool, str, str, dict]:
    """Rend (urgent, sujet, corps, meta). `meta.par` = 'john' ou 'repli' (quel texte est parti)."""
    if settings is None:
        from ..config import get_settings
        settings = get_settings()
    from .. import jobs_impl
    urgent, sujet, corps_base = jobs_impl._resume_matin_texte(db, settings)

    e = budget.etat(db, settings)
    if e.en_pause:
        return urgent, sujet, corps_base, {"par": "repli", "raison": "plafond atteint — John en pause"}

    generer = generer or _generer_defaut
    try:
        texte = (generer(db, {"resume_factuel": corps_base, "urgent": urgent}) or "").strip()
    except Exception as exc:  # noqa: BLE001 — John échoue → le résumé actuel part tel quel
        return urgent, sujet, corps_base, {"par": "repli", "raison": f"John a échoué ({type(exc).__name__})"}
    if not texte:
        return urgent, sujet, corps_base, {"par": "repli", "raison": "John indisponible (dégradé)"}

    from .chat import anti_invention
    ok, raison = anti_invention(texte, [{"resume": corps_base}])
    if not ok:
        return urgent, sujet, corps_base, {"par": "repli", "raison": f"anti-invention ({raison})"}
    return urgent, sujet, texte, {"par": "john"}
