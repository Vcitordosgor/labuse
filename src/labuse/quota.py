"""M23-E — PORTE DE QUOTA des exports abonné (le stub toujours-vrai, activé).

Plafonds QUOTIDIENS par plan, tous documents abonné confondus (Dossier, Financier,
Argumentaire, Potentiel, Lettre) :
  · Intégral  →  120 exports / jour (plafond d'usage loyal ; décision Vic, LOT G) ;
  · Essentiel →  30 exports / jour (inchangé) ;
  · interne   →  non borné (comptes admin/système, hors facturation).
Le FLASH (paiement unique) est À L'UNITÉ, HORS quota (ni compté, ni bloqué — paiement propre).
E1 (27/08) : l'ancienne offre « Illimité 499 € » est RETIRÉE (offre fantôme, jamais vendue).

Mécanique : compteur dans `usage_compteurs` (jour, sujet, kind, n) — la table de
protection EXISTANTE, aucun schéma nouveau. sujet = "cpt<compte_id>", kind = "export".
Fail-safe PILOTE : requête SANS session utilisateur (dev, golden, QA, rideau pilote)
→ porte PASSANTE, comportement d'avant à l'identique — le quota ne mord que les
comptes réels connectés (cookie « u.<token> », vérité en base).

Dépassement : 429 avec un MESSAGE HONNÊTE (jamais une erreur technique brute) —
le plafond, l'offre, quand ça reprend, et l'alternative Flash (hors quota).

M26 (quota agentique, RAPPORTÉ non codé) : même compteur, kind="agent" + plafond
dédié dans PLAFONDS_JOUR — `porte(request, db, kind="agent")` suffira, aucun
schéma ni nouvelle table à prévoir.
"""
from __future__ import annotations

from fastapi import HTTPException, Request
from sqlalchemy import text

#: plafond « non borné » des comptes internes (admin/système, hors facturation).
_NON_BORNE = 10**9

#: plafonds quotidiens par plan. 'interne'/'illimite' (admin/legacy) ne sont pas bornés.
#: CHIRURGICAL-FIX-DOCS (LOT G, décision Vic) — le plafond Intégral passe de 30 à **120 exports/jour**.
#: Essentiel est PINGLÉ à 30 (inchangé) pour ne pas suivre le défaut par accident. Intégral (349 €/mois)
#: reste au-dessus d'Essentiel (moins cher) : aucune formule moins chère ne dépasse une plus chère.
PLAFONDS_JOUR: dict[str, int] = {"integral": 120, "essentiel": 30,
                                 "interne": _NON_BORNE, "illimite": _NON_BORNE}

#: plan inconnu/legacy → plafond PRUDENT 30 (jamais non borné par accident, et sous Intégral : on ne
#: sur-accorde pas un plan non identifié).
PLAFOND_DEFAUT = 30


def _compte(request: Request, db) -> dict | None:
    """Compte réel de la requête via le cookie session utilisateur — None en pilote/dev."""
    try:
        from .api.auth import session_info
        tok = request.cookies.get("labuse_session") or request.cookies.get("session")
        info = session_info(tok)
        if not info:
            return None
        row = db.execute(text("SELECT id, plan FROM comptes WHERE id = :c"),
                         {"c": info["compte_id"]}).mappings().first()
        return dict(row) if row else None
    except Exception:  # noqa: BLE001 — la porte ne casse jamais un export pilote
        return None


def message_depassement(plan: str, plafond: int) -> str:
    """Message HONNÊTE de dépassement — pas une erreur technique brute : le CHIFFRE du plafond ET
    l'HEURE de remise à zéro (le compteur est journalier, jour Réunion → minuit heure de La Réunion)."""
    return (f"Plafond quotidien d'usage loyal atteint : {plafond} exports aujourd'hui. "
            f"Le compteur se remet à zéro à minuit (00 h 00, heure de La Réunion) — vos exports "
            f"repartent alors. Le rapport Flash à l'unité reste disponible, hors quota. "
            f"Un besoin ponctuel plus large ? Écrivez-nous : contact@labuse.immo.")


def porte_export(request: Request, db, *, kind: str = "export") -> dict:
    """PORTE M23-E : vérifie ET journalise un export abonné. À appeler AVANT le rendu.

    Renvoie {"compte_id", "plan", "utilise", "plafond", "restant"} (ou tout-None en
    pilote/dev sans session). Lève HTTPException(429) au dépassement, message honnête.
    Le Flash ne passe PAS par ici (hors quota, à l'unité)."""
    c = _compte(request, db)
    if c is None:
        return {"compte_id": None, "plan": None, "utilise": None,
                "plafond": None, "restant": None}
    plafond = PLAFONDS_JOUR.get(c["plan"], PLAFOND_DEFAUT)
    sujet = f"cpt{c['id']}"
    n = int(db.execute(text(
        "SELECT n FROM usage_compteurs WHERE jour = CURRENT_DATE AND sujet = :s "
        "AND kind = :k"), {"s": sujet, "k": kind}).scalar() or 0)
    if n >= plafond:
        raise HTTPException(429, message_depassement(c["plan"], plafond))
    db.execute(text(
        "INSERT INTO usage_compteurs (jour, sujet, kind, n) "
        "VALUES (CURRENT_DATE, :s, :k, 1) "
        "ON CONFLICT (jour, sujet, kind) DO UPDATE SET n = usage_compteurs.n + 1"),
        {"s": sujet, "k": kind})
    db.commit()
    return {"compte_id": c["id"], "plan": c["plan"], "utilise": n + 1,
            "plafond": plafond, "restant": plafond - n - 1}


def usage_du_jour(db, compte_id: int, *, kind: str = "export") -> dict:
    """Compteur du jour pour le tableau de bord (F) — lecture seule."""
    n = int(db.execute(text(
        "SELECT n FROM usage_compteurs WHERE jour = CURRENT_DATE AND sujet = :s "
        "AND kind = :k"), {"s": f"cpt{compte_id}", "k": kind}).scalar() or 0)
    return {"utilise": n}
