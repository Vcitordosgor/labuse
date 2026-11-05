"""DASHBOARD-V1 · D2 — STRIPE EN LECTURE SEULE (Tour de contrôle).

Clé RESTREINTE lecture via .env (LABUSE_STRIPE_RESTRICTED_KEY, repli STRIPE_RESTRICTED_KEY nu —
l'orthographe du mandat) : jamais la clé complète, jamais en dur, jamais le module-global
`stripe.api_key` (facturation.py le pose pour SES écritures ; ici un client DÉDIÉ, isolé).

Sans clé : mode « non configuré » PROPRE — {configure: false, raison} servi au dashboard,
aucun crash, aucun bouton menteur. Erreur API → {configure: true, erreur} tout aussi propre.

Lu : MRR, abonnements actifs, statut par client (active/past_due + période + prochaine
retentative), CA encaissé par mois (6 mois, pour le héros Pilotage), et le RAPPROCHEMENT
Stripe ⇄ comptes app (orphelins des deux sens → alerte ambre sur Licences).

Cache court (5 min, mandat) : le dashboard peut re-rendre sans marteler l'API.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone

from sqlalchemy import text

from .config import get_settings

log = logging.getLogger("labuse.stripe_lecture")

CACHE_TTL_S = 300  # 5 min (mandat)
_CACHE: dict = {"ts": 0.0, "data": None}
# VITESSE-3 (NU-F-005) — un seul rafraîchissement Stripe en vol à la fois (les appels réseau
# synchrones duraient 88 s en prod ET tenaient le thread de requête du Pilotage). Le verrou évite
# que N requêtes concurrentes lancent N fetches ; `apercu_affichage` ne l'ATTEND jamais.
_REFRESH_LOCK = threading.Lock()


def _mode_cle(k: str | None) -> str | None:
    """Mode d'une clé Stripe d'après son préfixe : 'live' | 'test' | None."""
    if not k:
        return None
    if k.startswith(("sk_live_", "rk_live_", "pk_live_")):
        return "live"
    if k.startswith(("sk_test_", "rk_test_", "pk_test_")):
        return "test"
    return None


def cle_restreinte() -> str | None:
    """NU4-FIX-1 (B/T5) — l'admin lit Stripe dans le MÊME MODE que l'app. La clé restreinte (lecture
    seule) n'est utilisée que si elle est du même mode que la clé d'écriture de l'app ; sinon (ex. app
    en TEST, clé restreinte en LIVE) on lit avec la clé de l'app — même mode garanti, aucune écriture
    tentée (le code ne fait que lister). Avant, l'admin voyait le LIVE pendant que l'app facturait en
    TEST : MRR/CA/rapprochement tous faux (comptes de test « sans abo », abonnés live « sans compte »)."""
    s = get_settings()
    app_key = s.stripe_secret_key
    rk = s.stripe_restricted_key or os.environ.get("STRIPE_RESTRICTED_KEY", "").strip() or None
    if not rk:
        return None                            # clé restreinte ABSENTE → « non configuré » (contrat D2)
    if _mode_cle(rk) == _mode_cle(app_key) or not app_key:
        return rk                              # même mode (ou pas de clé app pour comparer) → restreinte
    # clé restreinte PRÉSENTE mais d'un AUTRE mode que l'app (ex. rk_live alors que l'app facture en
    # TEST) → on lit avec la clé de l'app pour refléter le MÊME mode que la facturation (lecture seule).
    log.warning("stripe_lecture : clé restreinte en mode %s ≠ app en mode %s → lecture via la clé de "
                "l'app (lecture seule)", _mode_cle(rk), _mode_cle(app_key))
    return app_key


def _non_configure() -> dict:
    return {
        "configure": False,
        "raison": "Clé Stripe restreinte absente (LABUSE_STRIPE_RESTRICTED_KEY) — "
                  "lecture Stripe désactivée. Le reste du dashboard fonctionne.",
    }


def _mois_iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m")


def _lire_stripe(cle: str) -> dict:
    """Toutes les lectures Stripe en un passage (client dédié, aucune écriture possible avec
    une clé restreinte lecture — et aucune tentée)."""
    from stripe import StripeClient
    client = StripeClient(cle)

    # Abonnements (tous statuts : il faut voir les past_due/canceled pour le rapprochement).
    abos = []
    for sub in client.subscriptions.list(params={"status": "all", "limit": 100,
                                                 "expand": ["data.customer", "data.latest_invoice"]}).auto_paging_iter():
        item = sub["items"]["data"][0] if sub["items"]["data"] else None
        prix = item["price"] if item else None
        montant = (prix["unit_amount"] or 0) / 100 if prix else 0.0
        if prix and prix.get("recurring") and prix["recurring"].get("interval") == "year":
            montant = round(montant / 12, 2)   # MRR : l'annuel se lit en mensuel
        cust = sub.get("customer")
        inv = sub.get("latest_invoice")
        abos.append({
            "subscription_id": sub["id"],
            "customer_id": cust["id"] if isinstance(cust, dict) else cust,
            "email": (cust.get("email") if isinstance(cust, dict) else None),
            "nom_stripe": (cust.get("name") if isinstance(cust, dict) else None),
            "statut": sub["status"],                      # active | past_due | canceled | …
            "montant_eur_mois": montant,
            "depuis": sub.get("start_date"),
            "periode_fin": sub.get("current_period_end"),
            # carte refusée : la prochaine retentative Stripe (smart retries) vit sur la facture
            "prochaine_retentative": (inv.get("next_payment_attempt") if isinstance(inv, dict) else None),
        })

    # CA encaissé par mois (6 derniers mois) — factures PAYÉES, la vérité de l'encaissement.
    depuis = int(time.time()) - 190 * 86400
    ca_mois: dict[str, float] = {}
    for inv in client.invoices.list(params={"status": "paid", "limit": 100,
                                            "created": {"gte": depuis}}).auto_paging_iter():
        m = _mois_iso(inv["created"])
        ca_mois[m] = round(ca_mois.get(m, 0.0) + (inv.get("amount_paid") or 0) / 100, 2)

    actifs = [a for a in abos if a["statut"] in ("active", "trialing")]
    en_echec = [a for a in abos if a["statut"] == "past_due"]
    return {
        "configure": True,
        "mrr_eur": round(sum(a["montant_eur_mois"] for a in actifs), 2),
        "abonnements_actifs": len(actifs),
        "paiements_en_echec": len(en_echec),
        "abonnements": abos,
        "ca_mois": dict(sorted(ca_mois.items())),        # {"2026-03": 698.0, …}
    }


def _rapprocher(data: dict) -> dict:
    """Rapprochement Stripe ⇄ comptes app (orphelins des DEUX sens) — alerte ambre Licences.
    Best-effort : une base indisponible ne casse pas la lecture Stripe."""
    try:
        from .db import engine
        with engine().begin() as c:
            comptes = [dict(r) for r in c.execute(text(
                "SELECT id, nom, statut, stripe_customer_id, stripe_subscription_id "
                "FROM comptes WHERE statut NOT IN ('resilie')")).mappings()]
    except Exception as exc:  # noqa: BLE001
        log.debug("rapprochement : comptes illisibles (%s)", exc)
        return {"comptes_sans_abo": [], "abos_sans_compte": [], "indisponible": True}
    subs_actifs = {a["subscription_id"] for a in data.get("abonnements", [])
                   if a["statut"] in ("active", "trialing", "past_due")}
    custs = {a["customer_id"] for a in data.get("abonnements", [])}
    comptes_sans_abo = [
        {"compte_id": k["id"], "nom": k["nom"], "statut": k["statut"]}
        for k in comptes
        if k["statut"] == "actif" and (k["stripe_subscription_id"] or "") not in subs_actifs
    ]
    lies = {k["stripe_customer_id"] for k in comptes if k["stripe_customer_id"]}
    abos_sans_compte = [
        {"customer_id": a["customer_id"], "email": a["email"], "statut": a["statut"]}
        for a in data.get("abonnements", [])
        if a["statut"] in ("active", "trialing", "past_due") and a["customer_id"] not in lies
    ]
    return {"comptes_sans_abo": comptes_sans_abo, "abos_sans_compte": abos_sans_compte}


def apercu(force: bool = False) -> dict:
    """Vue Stripe complète du dashboard, cachée 5 min. TOUJOURS un dict propre, jamais une levée.

    BLOQUANT par construction (fait les appels réseau Stripe) — réservé au RAFRAÎCHISSEMENT
    (tâche de fond / CLI / `force`). Le chemin de la page passe par `apercu_affichage`
    (VITESSE-3 NU-F-005 : jamais 88 s dans le thread de requête)."""
    cle = cle_restreinte()
    if not cle:
        return _non_configure()
    now = time.time()
    if not force and _CACHE["data"] is not None and now - _CACHE["ts"] < CACHE_TTL_S:
        return _CACHE["data"]
    try:
        data = _lire_stripe(cle)
        data["rapprochement"] = _rapprocher(data)
        data["maj"] = datetime.now(tz=timezone.utc).isoformat()
    except Exception as exc:  # noqa: BLE001 — l'API Stripe en panne ne casse jamais le dashboard
        log.warning("lecture Stripe en échec : %s", exc)
        data = {"configure": True, "erreur": f"Lecture Stripe indisponible ({type(exc).__name__})."}
    _CACHE.update(ts=now, data=data)
    return data


def _refraichir_en_fond() -> None:
    """VITESSE-3 (NU-F-005) — rafraîchit le cache Stripe HORS du thread de requête. Un seul fetch
    en vol (verrou non bloquant) : si un rafraîchissement tourne déjà, on ne relance rien."""
    if not _REFRESH_LOCK.acquire(blocking=False):
        return
    try:
        apercu(force=True)   # fait les appels réseau, remplit `_CACHE`
    except Exception as exc:  # noqa: BLE001 — le fond ne lève jamais vers l'appelant
        log.warning("rafraîchissement Stripe de fond impossible : %s", exc)
    finally:
        _REFRESH_LOCK.release()


def apercu_affichage() -> dict:
    """VITESSE-3 (NU-F-005) — vue Stripe pour LA PAGE : ne fait JAMAIS d'appel réseau dans le thread
    de requête. Sert le dernier cache tel quel (daté par `maj`, affiché avec son heure) et déclenche
    un rafraîchissement EN TÂCHE DE FOND quand il est périmé. Cache jamais encore rempli → marqueur
    `en_cours` (le Pilotage s'affiche tout de suite, la carte Stripe dit « lecture en cours »).

    Identité (mandat) : cache à jour → ce retour est `_CACHE["data"]`, octet pour octet ce que
    `apercu()` renvoie ; seul le MOMENT du fetch (fond, hors requête) change."""
    cle = cle_restreinte()
    if not cle:
        return _non_configure()
    now = time.time()
    data = _CACHE["data"]
    frais = data is not None and now - _CACHE["ts"] < CACHE_TTL_S
    if not frais:
        # périmé OU jamais rempli : on rafraîchit SANS attendre (thread démon, best-effort).
        threading.Thread(target=_refraichir_en_fond, name="stripe-refresh", daemon=True).start()
    if data is not None:
        return data   # dernier état connu, daté (`maj`) — jamais un blocage
    return {"configure": True, "en_cours": True,
            "raison": "Lecture Stripe en cours — les chiffres s'afficheront au prochain rafraîchissement."}


def vider_cache() -> None:
    _CACHE.update(ts=0.0, data=None)
