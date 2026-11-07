"""Textes des e-mails LABUSE — désormais RENDUS PAR LE GABARIT UNIQUE (MAILS-1).

Historiquement, ce module tenait le texte brut des mails techniques (reset, digest, annonce,
maintenance, mise en vente). Depuis MAILS-1, TOUT le contenu vit dans `mails_contenu.py` et le rendu
(HTML e-mail + texte) passe par `gabarit_mail.py`. Ces fonctions restent la FAÇADE attendue par les
appelants historiques (events.py, pige/digests.py) : mêmes signatures, mêmes tuples de retour — mais
elles délèguent au gabarit, pour qu'il n'existe qu'UN SEUL modèle et UN SEUL endroit de contenu.

Brevo n'est plus qu'un transport (`brevo.envoyer_html`) : le HTML part du gabarit, pas d'un template.
"""
from __future__ import annotations

from . import mails_contenu as _mc

_APP = _mc.APP_URL


def _evs_params(evenements, base_url, marche, lien_desabo, lien_prefs):
    """Mappe les événements du digest (kind/titre/detail/idu) vers les params du gabarit."""
    base = (base_url or _APP).rstrip("/")
    evs = []
    for e in evenements or []:
        idu = (e.get("idu") or "").strip()
        lien = f"{base}/socle/#idu={idu}" if idu else ""
        evs.append({"titre": e.get("titre", ""), "detail": (e.get("detail") or "").strip(), "lien": lien})
    return {"EVENEMENTS": evs, "MARCHE": marche or {}, "LIEN_DESABO": lien_desabo or "",
            "LIEN_PREFS": lien_prefs or "", "LIEN_APP": base}


# ── réinitialisation de mot de passe (UN SEUL mail de reset — mandat MAILS-1) ──
def reset_password(lien: str) -> tuple[str, str]:
    m = _mc.rendre("mdp_oublie", {"LIEN_RESET": lien, "VALIDITE": "1 heure"})
    return m.sujet, m.texte


# ── digest de notifications (suivis + veilles) ──
def digest_notifications(evenements: list[dict], lien_desabo: str, *,
                         periode: str = "cette semaine", base_url: str = "",
                         marche: dict | None = None, lien_prefs: str = "",
                         secteurs_ligne: str = "") -> tuple[str, str]:
    m = _mc.rendre("smtp_digest_notifications",
                   _evs_params(evenements, base_url, marche, lien_desabo, lien_prefs))
    return m.sujet, m.texte


def digest_html_email(evenements: list[dict], marche: dict | None, top_chaudes: list[dict],
                      lien_desabo: str, lien_prefs: str, *, base_url: str = "",
                      periode: str = "aujourd'hui", secteurs_ligne: str = "") -> str:
    return _mc.rendre("smtp_digest_notifications",
                      _evs_params(evenements, base_url, marche, lien_desabo, lien_prefs)).html


# ── annonce produit / nouvelle source ──
def annonce_email(titre: str, corps: str, *, lien: str | None = None, lien_desabo: str = "",
                  lien_prefs: str = "") -> tuple[str, str]:
    m = _mc.rendre("smtp_annonce", {"TITRE": titre, "CORPS": corps, "LIEN": lien or _APP,
                                    "LIEN_DESABO": lien_desabo, "LIEN_PREFS": lien_prefs})
    return m.sujet, m.texte


def annonce_html(titre: str, corps: str, *, lien: str | None = None, lien_desabo: str = "",
                 lien_prefs: str = "") -> str:
    return _mc.rendre("smtp_annonce", {"TITRE": titre, "CORPS": corps, "LIEN": lien or _APP,
                                       "LIEN_DESABO": lien_desabo, "LIEN_PREFS": lien_prefs}).html


# ── MISE EN VENTE d'une parcelle SUIVIE (alerte immédiate) ──
def mise_en_vente_email(idu_court: str, commune: str, type_label: str, prix: str, *,
                        lien: str | None = None, lien_desabo: str = "",
                        lien_prefs: str = "") -> tuple[str, str, str]:
    m = _mc.rendre("smtp_mise_en_vente", {"IDU": idu_court, "COMMUNE": commune, "TYPE": type_label,
                                          "PRIX": prix, "LIEN": lien or _APP,
                                          "LIEN_DESABO": lien_desabo, "LIEN_PREFS": lien_prefs})
    return m.sujet, m.texte, m.html


# ── MAINTENANCE (dates/durée en évidence ; JAMAIS de désinscription — service non désactivable) ──
def maintenance_email(titre: str, corps: str, *, debut: str = "", fin: str = "",
                      duree: str = "") -> tuple[str, str, str]:

    def _fr_dt(s: str) -> str:
        """Reformate un horodatage ISO (« 2026-11-02 22:00 ») en français (« 02/11/2026 à 22h00 ») ;
        laisse tel quel si non ISO. L'exploitant saisit l'heure de La Réunion (doctrine tz)."""
        from datetime import datetime as _dt
        try:
            d = _dt.fromisoformat(s.strip().replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return s
        return d.strftime("%d/%m/%Y à %Hh%M")

    fenetre = ""
    if debut or fin or duree:
        parts = []
        if debut:
            parts.append(f"début {_fr_dt(debut)}")
        if fin:
            parts.append(f"fin {_fr_dt(fin)}")
        if duree:
            parts.append(f"durée estimée {duree}")
        suffixe = " (heure de La Réunion)" if (debut or fin) else ""
        fenetre = "Fenêtre de coupure : " + ", ".join(parts) + suffixe + "."
    m = _mc.rendre("smtp_maintenance", {"TITRE": titre, "CORPS": corps, "FENETRE": fenetre})
    return m.sujet, m.texte, m.html
