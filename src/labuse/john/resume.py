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

import logging
import re

from sqlalchemy import text

from . import budget

log = logging.getLogger(__name__)

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
    "marin à la rigueur. Reste bref (un court paragraphe ou quelques puces). "
    # OPS-URGENCE-3 — le résumé part dans un MAIL EN TEXTE SIMPLE (Brevo textContent) : toute balise
    # Markdown s'y afficherait telle quelle (le « **URGENT** » qu'on voyait à l'écran). Donc :
    "Écris en TEXTE BRUT, SANS Markdown : pas d'astérisques (* ou **), pas de dièses (#), pas de "
    "backticks. Pour une puce, commence la ligne par « • ». TERMINE toujours tes phrases (jamais de "
    "texte qui s'arrête au milieu)."
)

#: OPS-URGENCE-3 — plafond de jetons du résumé. Généreux (le mandat veut un résumé COMPLET), la
#: consigne « reste bref » borne la longueur réelle ; une sortie quand même coupée (`tronque`) retombe
#: sur le résumé factuel (secours), jamais envoyée telle quelle.
MAX_TOKENS_RESUME = 1200


def _texte_propre(texte: str) -> str:
    """Rend un TEXTE BRUT lisible en mail : retire les balises Markdown que le mail en texte simple
    afficherait littéralement (**gras**, *italique*, #titres, `code`), normalise les puces en « • ».
    Ne touche NI aux chiffres NI aux mots — seulement aux marqueurs de mise en forme."""
    t = (texte or "").replace("\r\n", "\n")
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)                 # **gras**
    t = re.sub(r"__(.+?)__", r"\1", t)                     # __gras__
    t = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", t)        # *italique*
    t = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", t)          # _italique_
    t = t.replace("`", "")
    lignes = []
    for ligne in t.split("\n"):
        l = re.sub(r"^\s*#{1,6}\s+", "", ligne)            # ## titre → titre
        l = re.sub(r"^(\s*)[-*+]\s+", r"\1• ", l)          # - puce / * puce → • puce
        lignes.append(l.rstrip())
    t = "\n".join(lignes)
    t = t.replace("*", "")                                 # astérisque résiduel (emphase orpheline/tronquée)
    return t.strip()


def _generer_defaut(db, facts: dict) -> str:
    """Appel modèle réel via le socle (Opus, kind john-resume). Rend '' si dégradé OU si la sortie a été
    COUPÉE au plafond de jetons (OPS-URGENCE-3 : un résumé tronqué « Radar du 05/ » est inutilisable →
    on laisse partir le secours factuel COMPLET à la place)."""
    from ..ai import core
    from ..ai_models import MODEL_OPUS
    r = core.complete(db, kind="john-resume", system=SYSTEME, context=facts,
                      model=MODEL_OPUS, max_tokens=MAX_TOKENS_RESUME, validate=False)
    if r.degraded:
        return ""
    if r.tronque:
        log.warning("john-resume : sortie coupée au plafond de jetons (max_tokens) — repli sur le "
                    "résumé factuel (secours)")
        return ""
    return r.text or ""


def composer_resume_matin(db, settings=None, generer=None) -> tuple[bool, str, str, dict]:
    """Rend (urgent, sujet, corps, meta). `meta.par` = 'john' ou 'repli' (quel texte est parti)."""
    if settings is None:
        from ..config import get_settings
        settings = get_settings()
    from .. import jobs_impl
    urgent, sujet, corps_base = jobs_impl._resume_matin_texte(db, settings)
    # OPS-URGENCE-3 — le SECOURS (résumé factuel) part en texte propre lui aussi : complet par
    # construction (pas d'appel modèle, jamais tronqué) et sans balise.
    corps_base = _texte_propre(corps_base)

    e = budget.etat(db, settings)
    if e.en_pause:
        return urgent, sujet, corps_base, {"par": "repli", "raison": "plafond atteint — John en pause"}

    generer = generer or _generer_defaut
    try:
        texte = _texte_propre(generer(db, {"resume_factuel": corps_base, "urgent": urgent}) or "")
    except Exception as exc:  # noqa: BLE001 — John échoue → le résumé actuel part tel quel
        return urgent, sujet, corps_base, {"par": "repli", "raison": f"John a échoué ({type(exc).__name__})"}
    if not texte:
        # dégradé (pas de clé/erreur) OU sortie coupée (tronque) → le secours factuel COMPLET part.
        return urgent, sujet, corps_base, {"par": "repli", "raison": "John indisponible (dégradé ou coupé)"}

    from .chat import anti_invention
    ok, raison = anti_invention(texte, [{"resume": corps_base}])
    if not ok:
        return urgent, sujet, corps_base, {"par": "repli", "raison": f"anti-invention ({raison})"}
    return urgent, sujet, texte, {"par": "john"}
