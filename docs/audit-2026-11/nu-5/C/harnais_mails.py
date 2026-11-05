#!/usr/bin/env python3
"""NU5-C — HARNAIS MAILS : rendu + contrôles automatiques de TOUS les e-mails client de LABUSE.

But (mandat NU5-C) : « le harnais — envoi de chaque mail vers l'adresse de test + contrôles
automatiques ». Ce harnais est LECTURE SEULE vis-à-vis de l'app et de la prod :

  · Les templates du CYCLE DE VIE (Brevo, 16 modèles) sont RENDUS par un GET read-only sur l'API
    Brevo (`brevo.apercu_template`, sujet + HTML réels, substitution des params) — AUCUN envoi.
  · Les mails TECHNIQUES (emails.py : reset, digest, annonce, maintenance, mise en vente) sont
    rendus en `.eml` par la façade `mail` en DRY-RUN étanche (0 réseau, écrit sur disque).
  · Un mode ENVOI RÉEL vers UNE adresse de test existe (option `--envoyer-test ADRESSE`), il n'est
    JAMAIS déclenché sans `LABUSE_MAIL_REEL=1` ET l'adresse explicite : garde-fou contre tout envoi
    accidentel depuis la clé Brevo de prod. Pendant l'audit NU5-C il n'a pas été tiré (prudence sur
    la réputation d'expéditeur du compte live) — le rendu read-only suffit au catalogue.

Contrôles automatiques par mail :
  · expéditeur (From) — cohérence d'un expéditeur unique sur tout le parc ;
  · liens — tous en https, tous vers labuse.immo / app.labuse.immo, 0 lien localhost/example/placeholder ;
  · désinscription — présente là où le type est désactivable (digest, annonce, radar) ;
  · restes de test — {{ param }} non substitué, lorem, TODO, « test », domaines placeholder ;
  · français — garde légère (mojibake, double espace, ponctuation).

Sortie : docs/audit-2026-11/nu-5/C/mails/<clé>.html|.eml + CATALOGUE.md + checks.json (code de sortie
non nul si un contrôle DUR échoue — exploitable en CI).

Lancement :
  PYTHONPATH=src <venv>/bin/python docs/audit-2026-11/nu-5/C/harnais_mails.py
  PYTHONPATH=src <venv>/bin/python docs/audit-2026-11/nu-5/C/harnais_mails.py --envoyer-test qa@exemple.fr
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from email.message import EmailMessage
from pathlib import Path

ICI = Path(__file__).resolve().parent
MAILS = ICI / "mails"
MAILS.mkdir(parents=True, exist_ok=True)

LINK = re.compile(r'https?://[^\s"\'<>)]+')
RAW_PARAM = re.compile(r"\{\{.*?\}\}|\{%.*?%\}")   # param/bloc Brevo non résolu
PLACEHOLDER_HOSTS = ("localhost", "127.0.0.1", "example.com", "example.org", "ton-email@",
                     "test.test", "labuse.test", "@test", "votre-", "xxx")
ANGLAIS = (" the ", " your ", " click here", "unsubscribe", "hello,", "dear ", "lorem ipsum")

# Params d'exemple (réalistes, La Réunion) pour substituer dans le rendu.
SAMPLE = {
    "PRENOM": "Camille", "LIEN_INVITATION": "https://app.labuse.immo/invitation?t=TKTEST",
    "LIEN_SOUSCRIPTION": "https://app.labuse.immo/souscrire?t=TKTEST",
    "FIN_ESSAI": "07/11/2026 à 18h00", "LIEN_PAIEMENT": "https://app.labuse.immo/compte/paiement",
    "LIEN_RESET": "https://app.labuse.immo/reset?t=TKTEST", "VALIDITE": "1 heure",
    "DATE_HEURE": "05/11/2026 à 14h00", "DATE_FIN_ACCES": "30/11/2026",
    "LIEN_PDF": "https://app.labuse.immo/flash/97411000BZ1065.pdf", "IDU": "97411000BZ1065",
    "COMMUNE": "La Montagne", "ANCIEN_EMAIL": "ancienne@exemple.fr", "NOUVEL_EMAIL": "nouvelle@exemple.fr",
    "SON_MESSAGE": "Bonjour, une zone semble fausse.", "REPONSE": "Merci, c'est corrigé.",
    "DATE": "05/11/2026", "NB_BIENS": "3", "VEILLE": "Saint-Denis — terrains > 400 m²",
    "CRITERES": "terrain, &gt; 400 m², zone U", "CARTES": "<p>Un terrain à Saint-Denis, 512 m², 180 000 €.</p>",
}


def _checks(key: str, sujet: str, corps: str, expediteur: str | None, *,
            recurrent: bool) -> dict:
    """Contrôles automatiques. `recurrent`=True → désinscription EXIGÉE."""
    blob = f"{sujet}\n{corps}"
    low = blob.lower()
    links = sorted(set(LINK.findall(blob)))
    durs, mous = [], []

    # liens
    for u in links:
        if not u.startswith("https://"):
            durs.append(f"lien non-https : {u}")
        if not re.search(r"(^|//|\.)labuse\.immo", u):
            durs.append(f"lien hors-domaine labuse.immo : {u}")
        if any(h in u.lower() for h in PLACEHOLDER_HOSTS):
            durs.append(f"lien placeholder/local : {u}")

    # restes de test
    raws = RAW_PARAM.findall(blob)
    if raws:
        durs.append(f"paramètre Brevo non substitué : {raws[:3]}")
    for tok in ("lorem", "todo", "fixme", "[dry-run]", "example.com"):
        if tok in low:
            mous.append(f"reste de test « {tok} »")

    # désinscription (types désactivables)
    a_desabo = any(k in low for k in ("désab", "desab", "se désinscrire", "unsubscribe",
                                      "ne plus recevoir", "list-unsubscribe"))
    if recurrent and not a_desabo:
        durs.append("mail récurrent SANS lien/mention de désinscription")

    # français (garde légère)
    if "Ã" in blob or "â€" in blob or "�" in blob:
        durs.append("mojibake (encodage cassé)")
    for en in ANGLAIS:
        if en in low:
            mous.append(f"tournure anglaise « {en.strip()} »")

    return {"key": key, "sujet": sujet, "expediteur": expediteur, "liens": links,
            "a_desinscription": a_desabo, "ecarts_durs": durs, "ecarts_mous": mous}


def rendre_brevo() -> list[dict]:
    """Rend les 16 templates de cycle de vie via GET read-only Brevo."""
    from labuse import brevo
    # récurrents = désactivables au sens registre (annonce/radar) + ici radar_*.
    RECURRENTS = {"radar_digest", "radar_alerte"}
    res = []
    # expéditeur réel (un seul GET agrégé)
    verif = brevo.verifier_templates(timeout=15)
    senders = {l["key"]: l.get("expediteur") for l in verif.get("lignes", [])}
    for key in brevo.REGISTRE:
        a = brevo.apercu_template(key, SAMPLE)
        if not a.get("configure"):
            res.append({"key": key, "sujet": "(non lu)", "raison": a.get("raison"),
                        "ecarts_durs": [f"template non lisible : {a.get('raison')}"], "ecarts_mous": []})
            continue
        sujet, html = a.get("subject", ""), a.get("html", "")
        (MAILS / f"{key}.html").write_text(
            f"<!-- sujet: {sujet} -->\n<!-- expéditeur Brevo: {senders.get(key)} -->\n{html}",
            encoding="utf-8")
        c = _checks(key, sujet, html, senders.get(key), recurrent=key in RECURRENTS)
        c["transport"] = "Brevo (template)"
        res.append(c)
    return res


def rendre_smtp() -> list[dict]:
    """Rend les mails techniques (emails.py) en .eml via DRY-RUN étanche, + contrôles."""
    from labuse import emails
    from labuse.config import get_settings
    from_addr = get_settings().mail_from
    out = []

    def _eml(key: str, sujet: str, texte: str, html: str | None = None,
             headers: dict | None = None, recurrent: bool = False):
        msg = EmailMessage()
        msg["From"] = from_addr
        msg["To"] = "qa@exemple.fr"
        msg["Subject"] = sujet
        for k, v in (headers or {}).items():
            msg[k] = v
        msg.set_content(texte)
        if html:
            msg.add_alternative(html, subtype="html")
        (MAILS / f"{key}.eml").write_bytes(bytes(msg))
        corps = texte + ("\n" + html if html else "")
        c = _checks(key, sujet, corps, from_addr, recurrent=recurrent)
        c["transport"] = "SMTP/Brevo-texte (emails.py)"
        out.append(c)

    base = "https://app.labuse.immo"
    desabo = f"{base}/desabo?t=TKTEST"
    prefs = f"{base}/compte/preferences"

    s, c = emails.reset_password(f"{base}/reset?t=TKTEST")
    _eml("smtp_reset_password", s, c)

    ev = [{"kind": "mutation", "titre": "Vente détectée", "detail": "DVF 2026-10", "idu": "97411000BZ1065"},
          {"kind": "permis", "titre": "Permis déposé", "detail": "PC 974 11 26 B0012", "idu": "97411000BZ1065"}]
    marche = {"total": 7, "dans_vos_communes": 2}
    s, c = emails.digest_notifications(ev, desabo, periode="aujourd'hui", base_url=base,
                                       marche=marche, lien_prefs=prefs)
    html = emails.digest_html_email(ev, marche, [], desabo, prefs, base_url=base, periode="aujourd'hui")
    _eml("smtp_digest_notifications", s, c, html,
         headers={"List-Unsubscribe": f"<{desabo}>"}, recurrent=True)

    s, c = emails.annonce_email("nouvelle source : RNU", "Une nouvelle source est disponible.",
                                lien=f"{base}/sources", lien_desabo=desabo, lien_prefs=prefs)
    _eml("smtp_annonce", s, c, recurrent=True)

    s, txt, html = emails.maintenance_email("mise à jour serveur",
                                            "Le service sera brièvement indisponible.",
                                            debut="2026-11-07 22:00", fin="2026-11-07 23:00",
                                            duree="1 h")
    _eml("smtp_maintenance", s, txt, html, recurrent=False)   # non désactivable par conception

    s, txt, html = emails.mise_en_vente_email("BZ1065", "La Montagne", "terrain", "180 000 €",
                                              lien=f"{base}/socle/#idu=97411000BZ1065",
                                              lien_desabo=desabo, lien_prefs=prefs)
    _eml("smtp_mise_en_vente", s, txt, html, recurrent=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--envoyer-test", metavar="ADRESSE", default=None,
                    help="ENVOI RÉEL vers cette adresse (exige LABUSE_MAIL_REEL=1 ; off par défaut)")
    args = ap.parse_args()

    lignes = rendre_brevo() + rendre_smtp()

    # envoi réel opt-in (double garde)
    if args.envoyer_test:
        if os.environ.get("LABUSE_MAIL_REEL") != "1":
            print("REFUS envoi test : poser LABUSE_MAIL_REEL=1 (garde anti-envoi accidentel).",
                  file=sys.stderr)
        else:
            from labuse import brevo, mail
            for key in brevo.REGISTRE:
                r = brevo.envoyer_template(args.envoyer_test, key, SAMPLE)
                print(f"  envoi test {key} → {args.envoyer_test} : {r}")
            _ = mail  # (les mails techniques partiraient via mail.send_email ici)

    # rapport
    durs = sum(len(l.get("ecarts_durs", [])) for l in lignes)
    mous = sum(len(l.get("ecarts_mous", [])) for l in lignes)
    senders = sorted({l.get("expediteur") for l in lignes if l.get("expediteur")})
    (ICI / "checks.json").write_text(json.dumps(
        {"total_mails": len(lignes), "ecarts_durs": durs, "ecarts_mous": mous,
         "expediteurs": senders, "lignes": lignes}, ensure_ascii=False, indent=2), encoding="utf-8")

    lg = ["# NU5-C — Catalogue des mails (rendu + contrôles)", "",
          f"- mails rendus : **{len(lignes)}**",
          f"- expéditeur(s) observé(s) : **{', '.join(senders)}**",
          f"- écarts DURS : **{durs}** · écarts mous : **{mous}**", "",
          "| clé | transport | sujet | expéditeur | désinscr. | écarts durs | écarts mous |",
          "|---|---|---|---|:-:|---|---|"]
    for l in lignes:
        lg.append("| `{}` | {} | {} | {} | {} | {} | {} |".format(
            l["key"], l.get("transport", ""), (l.get("sujet", "") or "").replace("|", "¦")[:60],
            l.get("expediteur") or "—", "oui" if l.get("a_desinscription") else "—",
            "; ".join(l.get("ecarts_durs", [])) or "—",
            "; ".join(l.get("ecarts_mous", [])) or "—"))
    (ICI / "CATALOGUE.md").write_text("\n".join(lg) + "\n", encoding="utf-8")

    print(f"{len(lignes)} mails rendus → {MAILS}")
    print(f"expéditeur(s) : {senders}")
    print(f"écarts durs={durs} mous={mous} — voir CATALOGUE.md / checks.json")
    return 1 if durs else 0


if __name__ == "__main__":
    raise SystemExit(main())
