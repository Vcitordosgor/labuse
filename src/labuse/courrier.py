"""Envoi de courrier postal par API (mandat wave-adresses, Lot 2B).

Étude DOM (10/07/2026, sourcée dans NOTES_WAVE_ACI.md) : La Réunion est du courrier
INTÉRIEUR France (≤ 100 g égrené — le vrai différenciateur est l'API, pas le DOM).
Prestataire RETENU : **Merci Facteur PRO** — doc API publique v1.2, sandbox, webhooks
(preuve de dépôt, AR), LRAR incluse, self-service (~2,69 € la lettre verte 3 pages +
19,95 €/mois pour l'API de production). Alternatives documentées : MySendingBox (sans
abonnement), Maileva (garantie OM1 écrite, volume).

Sans compte prestataire (action Vic) : provider « stub » — la mécanique (plafonds,
responsabilité du contenu, tarification coût × marge, suivi) est en place et testée,
AUCUN envoi réel ne part, et le front N'AFFICHE PAS le bouton (jamais de bouton mort).

Facturation à l'usage : FACTURE SÉPARÉE mensuelle (le plus simple — la table
courrier_envois porte coût et prix par envoi ; le metered billing Stripe pourra s'y
brancher quand Stripe sera en production côté Flash).
"""
from __future__ import annotations

import logging

from sqlalchemy import text

from .config import get_settings

log = logging.getLogger("labuse.courrier")

DDL = """
CREATE TABLE IF NOT EXISTS courrier_envois (
  id serial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(),
  sujet varchar(24) NOT NULL,
  idu varchar(14), adresse text NOT NULL,
  statut varchar(16) NOT NULL,              -- 'simule'|'envoye'|'depose'|'distribue'|'erreur'
  provider varchar(16) NOT NULL, provider_ref varchar(64),
  cout_eur numeric(6,2), prix_eur numeric(6,2),
  assume_contenu boolean NOT NULL,          -- case « j'assume le contenu » (responsabilité)
  modele varchar(40)
);
CREATE INDEX IF NOT EXISTS courrier_envois_sujet_idx ON courrier_envois (sujet, ts);
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        for stmt in DDL.strip().split(";"):
            if stmt.strip():
                c.execute(text(stmt))


def provider_actif() -> str:
    """'mercifacteur' si configuré, sinon 'stub' (aucun envoi réel, pas de bouton front)."""
    s = get_settings()
    if s.courrier_provider == "mercifacteur" and s.mercifacteur_api_key:
        return "mercifacteur"
    return "stub"


def tarif() -> dict:
    """Prix affiché au client = coût prestataire × marge (config, défaut × 1,5)."""
    s = get_settings()
    cout = float(s.courrier_cout_lettre_eur)
    return {"cout_prestataire_eur": round(cout, 2),
            "marge": float(s.courrier_marge),
            "prix_client_eur": round(cout * float(s.courrier_marge), 2),
            "provider": provider_actif(),
            "note": "lettre verte 1-3 pages, tarif intérieur France (DOM inclus ≤ 100 g)"}


def envois_du_jour(db, sujet: str) -> int:
    # « Le jour » est ancré sur l'HORLOGE DB (current_date), cohérent avec `ts DEFAULT now()`.
    # NE PAS comparer à un date.today() Python : quand la tz machine ≠ tz DB (ici Réunion +04),
    # ts::date (DB) et date.today() (local) divergent après minuit → le plafond ne compte plus rien.
    return int(db.execute(text(
        "SELECT count(*) FROM courrier_envois WHERE sujet = :s AND ts::date = current_date"),
        {"s": sujet}).scalar() or 0)


def _envoyer_mercifacteur(adresse: str, pdf_contenu: bytes | None) -> tuple[str, str]:
    """Envoi réel via l'API Merci Facteur v1.2 (sendCourrier, mode 'normal').

    Nécessite le compte PRO (LABUSE_MERCIFACTEUR_API_KEY/SECRET) — doc :
    https://www.merci-facteur.com/api/1.2/doc.php. Retourne (statut, référence)."""
    import httpx
    s = get_settings()
    # authentification + création du courrier — squelette conforme à la doc publique ;
    # à valider en SANDBOX à l'ouverture du compte (action Vic) avant toute production.
    resp = httpx.post(
        "https://www.merci-facteur.com/api/1.2/sendCourrier",
        data={"apiKey": s.mercifacteur_api_key, "apiSecret": s.mercifacteur_api_secret,
              "mode": "normal", "adresseDestinataire": adresse},
        files={"document": ("courrier.pdf", pdf_contenu or b"", "application/pdf")},
        timeout=s.http_timeout_s)
    resp.raise_for_status()
    ref = str(resp.json().get("courrierId", ""))
    return "envoye", ref


def envoyer(db, sujet: str, destinataires: list[dict], *, modele: str | None,
            assume_contenu: bool, pdf_contenu: bytes | None = None) -> dict:
    """Crée les envois (plafond/jour, responsabilité du contenu OBLIGATOIRE).

    destinataires : [{idu, adresse}] — adresses BAN normalisées (jamais de nom de
    personne physique : « À l'occupant »). Aucun envoi sans assume_contenu=True.
    """
    s = get_settings()
    if not assume_contenu:
        raise ValueError("Le contenu du courrier est de la responsabilité de l'émetteur — "
                         "case « j'assume le contenu de ce courrier » obligatoire.")
    deja = envois_du_jour(db, sujet)
    if deja + len(destinataires) > max(1, s.courrier_max_jour):
        raise ValueError(f"Plafond d'envois atteint ({s.courrier_max_jour}/jour) : "
                         f"{deja} déjà envoyés aujourd'hui.")
    prov = provider_actif()
    t = tarif()
    crees = []
    for d in destinataires:
        if prov == "mercifacteur":
            try:
                statut, ref = _envoyer_mercifacteur(d["adresse"], pdf_contenu)
            except Exception as exc:  # noqa: BLE001 — un échec d'envoi est un statut, pas un 500
                statut, ref = "erreur", type(exc).__name__
        else:
            statut, ref = "simule", None      # stub : mécanique testable, rien ne part
        row = db.execute(text(
            "INSERT INTO courrier_envois (sujet, idu, adresse, statut, provider, "
            " provider_ref, cout_eur, prix_eur, assume_contenu, modele) "
            "VALUES (:s, :i, :a, :st, :p, :r, :c, :px, true, :m) RETURNING id"),
            {"s": sujet, "i": d.get("idu"), "a": d["adresse"], "st": statut, "p": prov,
             "r": ref, "c": t["cout_prestataire_eur"], "px": t["prix_client_eur"],
             "m": modele}).scalar()
        crees.append({"id": row, "idu": d.get("idu"), "statut": statut})
    log.info("courrier : %d envoi(s) créés (provider=%s, sujet=%s)", len(crees), prov, sujet)
    return {"envois": crees, "provider": prov, "prix_unitaire_eur": t["prix_client_eur"],
            "total_eur": round(t["prix_client_eur"] * len(crees), 2),
            "facturation": "facture séparée mensuelle (voir NOTES_WAVE_ACI.md)"}
