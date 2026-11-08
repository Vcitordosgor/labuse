#!/usr/bin/env python3
"""NU5-C — HARNAIS MAILS (modèle MAILS-1) : rendu + contrôles automatiques des 21 e-mails client.

OPS-3 (C) — RÉÉCRIT au modèle MAILS-1. Depuis la refonte, TOUT le contenu des mails vit dans
`mails_contenu.py` et le rendu passe par le gabarit unique `gabarit_mail.py` ; Brevo n'est plus
qu'un TRANSPORT (envoi du HTML rendu, plus de templates Brevo). L'ancien harnais appelait des
fonctions supprimées (`emails.reset_password`, `digest_notifications`, …) et dépendait de templates
Brevo qui 404 — il échouait par construction. Ici on rend les 21 mails EXACTEMENT comme l'app
(`mails_contenu.rendre(clé, params)`), en LECTURE SEULE (aucun réseau, aucun envoi).

Les 21 mails = `mails_contenu.ORDRE_CATALOGUE` (20) + `essai_fin_proche` (rendu par code).

Contrôles automatiques (DURS = code de sortie ≠ 0) :
  · EXPÉDITEUR UNIQUE — un seul `From` sur tout le parc (`settings.mail_from`), bien formé ;
  · LIENS — tous en https, tous vers labuse.immo / app.labuse.immo (ou mailto:contact), 0 lien
    localhost / example / placeholder ;
  · DÉSINSCRIPTION — présente (« Me désinscrire ») partout SAUF sur les mails de sécurité et les
    transactionnels (abonnement / paiement / accès / maintenance), où elle doit être ABSENTE ;
  · PARAMÈTRES — aucun `{{ … }}` / `{% … %}` non substitué, aucun « None » rendu ;
  · BOUTON — un bouton d'action (jeton de charte) présent, sauf pendant une maintenance.

Sortie : docs/audit-2026-11/nu-5/C/mails/<clé>.html + CATALOGUE.md + checks.json.

Lancement : PYTHONPATH=src <venv>/bin/python docs/audit-2026-11/nu-5/C/harnais_mails.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
MAILS = ICI / "mails"
MAILS.mkdir(parents=True, exist_ok=True)

LINK = re.compile(r'https?://[^\s"\'<>)]+')
RAW_PARAM = re.compile(r"\{\{.*?\}\}|\{%.*?%\}")          # param/bloc de template non résolu
PLACEHOLDER_HOSTS = ("localhost", "127.0.0.1", "example.com", "example.org",
                     "ton-email@", "test.test", "labuse.test", "votre-", "xxx")

# Doctrine MAILS-1 (décision Vic, V4) — mêmes ensembles que tests/test_mails_1_gabarit.py :
SECURITE = {"mdp_oublie", "mdp_modifie", "email_change"}
# facturation / accès / rapport acheté : transactionnels comme la sécurité → PAS de désinscription
# (`essai_fin_proche` est un RAPPEL de cycle de vie, désactivable → GARDE sa désinscription).
TRANSACTIONNEL = {"souscription", "relance_carte", "suspension", "retablissement", "resiliation",
                  "flash_pret"}
SANS_DESABO = SECURITE | TRANSACTIONNEL | {"smtp_maintenance"}
SANS_BOUTON = {"smtp_maintenance"}


def _checks(key: str, m, expediteur: str, *, doit_desabo: bool, doit_bouton: bool) -> dict:
    """Contrôles automatiques sur un mail RENDU (`gabarit_mail.Mail`)."""
    import labuse.gabarit_mail as g
    blob = f"{m.sujet}\n{m.html}\n{m.texte}"
    low = m.html.lower()
    links = sorted(set(LINK.findall(blob)))
    durs: list[str] = []

    # expéditeur unique, bien formé
    if not expediteur or "@" not in expediteur:
        durs.append(f"expéditeur absent ou mal formé : {expediteur!r}")

    # liens
    for u in links:
        if not u.startswith("https://"):
            durs.append(f"lien non-https : {u}")
        elif not re.search(r"(^|//|\.)labuse\.immo", u):
            durs.append(f"lien hors-domaine labuse.immo : {u}")
        if any(h in u.lower() for h in PLACEHOLDER_HOSTS):
            durs.append(f"lien placeholder/local : {u}")

    # paramètres non substitués / None
    if RAW_PARAM.findall(blob):
        durs.append(f"paramètre de template non substitué : {RAW_PARAM.findall(blob)[:3]}")
    if "{{" in m.sujet or "None" in m.sujet:
        durs.append("sujet non substitué")
    if "None" in m.html:
        durs.append("« None » rendu dans le HTML")

    # désinscription (doctrine)
    a_desabo = "Me désinscrire" in m.html
    if doit_desabo and not a_desabo:
        durs.append("désinscription attendue (« Me désinscrire ») absente")
    if not doit_desabo and a_desabo:
        durs.append("mail transactionnel/sécurité avec désinscription (interdit)")

    # bouton d'action
    a_bouton = g.BTN_BG in m.html
    if doit_bouton and not a_bouton:
        durs.append("bouton d'action (jeton de charte) absent")
    if not doit_bouton and a_bouton:
        durs.append("bouton présent sur un mail qui ne doit pas en avoir (maintenance)")

    return {"key": key, "sujet": m.sujet, "expediteur": expediteur, "liens": links,
            "a_desinscription": a_desabo, "a_bouton": a_bouton, "ecarts_durs": durs}


def rendre_tous() -> tuple[list[dict], str]:
    """Rend les 21 mails via l'app (`mails_contenu.rendre`) + contrôles. Renvoie (lignes, expéditeur)."""
    from labuse import mails_contenu as mc
    from labuse.config import get_settings

    expediteur = get_settings().mail_from or ""
    tous = mc.ORDRE_CATALOGUE + ["essai_fin_proche"]
    lignes = []
    for key in tous:
        m = mc.rendre(key, mc.SPECIMENS.get(key, {}))
        (MAILS / f"{key}.html").write_text(
            f"<!-- sujet: {m.sujet} -->\n<!-- expéditeur: {expediteur} -->\n{m.html}", encoding="utf-8")
        lignes.append(_checks(key, m, expediteur,
                              doit_desabo=key not in SANS_DESABO,
                              doit_bouton=key not in SANS_BOUTON))
    return lignes, expediteur


def transport_brevo() -> dict | None:
    """Sanity LECTURE SEULE du transport Brevo si `BREVO_API_KEY` est posé : chaque clé gérée par
    l'app est connue du registre de transport. N'échoue PAS sur un template Brevo absent (le contenu
    est désormais rendu par l'app — Brevo ne porte plus que le HTML). None si Brevo non configuré."""
    import os
    if not os.environ.get("BREVO_API_KEY"):
        return None
    try:
        from labuse import brevo, mails_contenu as mc
    except Exception as exc:  # noqa: BLE001
        return {"note": f"brevo indisponible : {exc}"}
    geres = [k for k in (mc.ORDRE_CATALOGUE + ["essai_fin_proche"]) if mc.gere(k)]
    inconnus = [k for k in geres if k not in getattr(brevo, "REGISTRE", {})]
    return {"geres": len(geres), "hors_registre_transport": inconnus}


def main() -> int:
    lignes, expediteur = rendre_tous()
    durs = sum(len(l["ecarts_durs"]) for l in lignes)
    senders = sorted({l["expediteur"] for l in lignes if l["expediteur"]})
    # EXPÉDITEUR UNIQUE : un seul From sur tout le parc.
    if len(senders) > 1:
        durs += 1
        lignes.append({"key": "(parc)", "ecarts_durs": [f"plusieurs expéditeurs : {senders}"]})

    brevo = transport_brevo()
    (ICI / "checks.json").write_text(json.dumps(
        {"total_mails": len([l for l in lignes if l.get("sujet") is not None]),
         "expediteur_unique": senders, "ecarts_durs": durs, "transport_brevo": brevo,
         "lignes": lignes}, ensure_ascii=False, indent=2), encoding="utf-8")

    lg = ["# NU5-C — Catalogue des mails (modèle MAILS-1, rendu par l'app)", "",
          f"- mails rendus : **{len([l for l in lignes if l.get('sujet')])}**",
          f"- expéditeur unique : **{', '.join(senders) or '—'}**",
          f"- écarts DURS : **{durs}**",
          f"- transport Brevo : {brevo if brevo else 'non configuré (BREVO_API_KEY absent)'}", "",
          "| clé | sujet | désinscr. | bouton | écarts durs |",
          "|---|---|:-:|:-:|---|"]
    for l in lignes:
        if l.get("sujet") is None and l["key"] != "(parc)":
            continue
        lg.append("| `{}` | {} | {} | {} | {} |".format(
            l["key"], (l.get("sujet") or "").replace("|", "¦")[:60],
            "oui" if l.get("a_desinscription") else "—",
            "oui" if l.get("a_bouton") else "—",
            "; ".join(l.get("ecarts_durs", [])) or "—"))
    (ICI / "CATALOGUE.md").write_text("\n".join(lg) + "\n", encoding="utf-8")

    print(f"{len([l for l in lignes if l.get('sujet')])} mails rendus (modèle MAILS-1) → {MAILS}")
    print(f"expéditeur unique : {senders}")
    print(f"écarts durs = {durs} — voir CATALOGUE.md / checks.json")
    return 1 if durs else 0


if __name__ == "__main__":
    raise SystemExit(main())
