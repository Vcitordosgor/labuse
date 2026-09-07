"""COMPTE-2 · Lot 1 — REGISTRE UNIQUE des templates Brevo (cycle de vie client).

Un template = un identifiant Brevo (4→19), un nom, une liste de paramètres attendus. Cette table
est la SEULE source de vérité : un ID ne s'écrit qu'ICI (constantes nommées, `REGISTRE`), jamais un
nombre magique éparpillé dans le code. Le runtime peut surcharger l'ID par `.env`
(`LABUSE_BREVO_TPL_*`, comme en prod) mais l'ID CANONIQUE reste la valeur par défaut — l'app connaît
les bons IDs sans aucune configuration.

Vérification : `verifier_templates()` appelle l'API Brevo et compare (existence, actif, nom, params).

Doctrine héritée (inchangée) :
- Identifiants absents / clé API absente → mode « NON CONFIGURÉ » PROPRE : le bouton reste visible,
  la réponse dit pourquoi rien n'est parti, AUCUN envoi silencieux.
- Le contenu se règle chez Brevo ; l'app n'envoie que l'identifiant + les paramètres.
- Le transport (mail.py, file d'attente) reste le SEUL chemin d'envoi (COMPTE-2 Lot 2).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .config import get_settings

log = logging.getLogger("labuse.brevo")

# Endpoint Brevo v3 — la lecture de template est /v3/smtp/templates/{id} (l'ancienne route
# /v3/smtpTemplates/{id} répond 404 « Invalid route » : l'aperçu était cassé, COMPTE-2 Lot 1).
_API = "https://api.brevo.com/v3"


@dataclass(frozen=True)
class Template:
    """Un template Brevo, référencé par sa clé code (stable : sert de valeur `licence_mails.mail_key`)."""
    id: int                       # identifiant CANONIQUE Brevo (source de vérité, un seul endroit)
    nom: str                      # nom Brevo attendu (vérifié par API)
    libelle: str                  # libellé servi au dashboard (boutons/chips)
    params: tuple[str, ...]       # variables SUBSTITUÉES ({{ params.X }}) attendues par le HTML
    flags: tuple[str, ...] = ()   # variables CONDITIONNELLES ({% if params.X %}) — booléens, jamais brutes
    env_champ: str | None = None  # champ Settings (.env LABUSE_BREVO_TPL_*) qui peut surcharger l'ID


#: Table de correspondance UNIQUE (COMPTE-2 Lot 1). Clés stables = valeurs `licence_mails.mail_key`.
#: Les 16 templates du cycle de vie (4→19) sont refaits le 07/09 sur un gabarit unique chez Brevo.
REGISTRE: dict[str, Template] = {
    "essai":          Template(4,  "LABUSE-E-ESSAI-48H",    "Essai 48 h",
                               ("PRENOM", "EMAIL", "MDP_PROVISOIRE", "FIN_ESSAI"), ("RENVOI",),
                               "brevo_tpl_essai"),
    "souscription":   Template(5,  "LABUSE-0-SOUSCRIPTION",  "Lien de souscription",
                               ("PRENOM", "LIEN_SOUSCRIPTION"), ("RENVOI",),
                               "brevo_tpl_souscription"),
    "onboarding1":    Template(6,  "LABUSE-1-BIENVENUE",     "Mail de bienvenue",
                               ("PRENOM", "EMAIL", "MDP_PROVISOIRE"), (),
                               "brevo_tpl_onboarding_1"),
    "onboarding2":    Template(7,  "LABUSE-2-METHODE",       "Relance J+3",
                               ("PRENOM",), ("JAMAIS_CONNECTE",),
                               "brevo_tpl_onboarding_2"),
    "onboarding3":    Template(8,  "LABUSE-3-POINT-ETAPE",   "Dernier rappel J+10",
                               ("PRENOM",), (),
                               "brevo_tpl_onboarding_3"),
    "relance_carte":  Template(9,  "LABUSE-A-CARTE-REFUSEE", "Relance carte refusée",
                               ("PRENOM", "LIEN_PAIEMENT"), (),
                               "brevo_tpl_relance_carte"),
    "suspension":     Template(10, "LABUSE-B-SUSPENSION",    "Suspension",
                               ("PRENOM", "LIEN_PAIEMENT"), (),
                               "brevo_tpl_suspension"),
    "retablissement": Template(11, "LABUSE-C-RETABLI",       "Rétablissement",
                               ("PRENOM",), (),
                               "brevo_tpl_retablissement"),
    "radar_digest":   Template(12, "LABUSE-12-RADAR-DIGEST", "Radar — digest quotidien",
                               ("PRENOM", "DATE", "NB_BIENS", "CARTES"), (),
                               "brevo_tpl_radar_digest"),
    "radar_alerte":   Template(13, "LABUSE-13-RADAR-ALERTE", "Radar — alerte de veille",
                               ("PRENOM", "VEILLE", "NB_BIENS", "CRITERES", "CARTES"), (),
                               "brevo_tpl_radar_alerte"),
    # COMPTE-2 Lot 1 — les six templates ajoutés (14→19). Pas de champ .env dédié : l'ID canonique
    # suffit (le prod peut poser LABUSE_BREVO_TPL_<CLE> pour surcharger, cf. _setting_ou_env).
    "mdp_oublie":     Template(14, "LABUSE-D-MDP-OUBLIE",    "Mot de passe oublié",
                               ("PRENOM", "LIEN_RESET", "VALIDITE"), (),
                               "brevo_tpl_mdp_oublie"),
    "mdp_modifie":    Template(15, "LABUSE-D-MDP-MODIFIE",   "Mot de passe modifié",
                               ("PRENOM", "DATE_HEURE"), (),
                               "brevo_tpl_mdp_modifie"),
    "resiliation":    Template(16, "LABUSE-F-RESILIATION",   "Résiliation",
                               ("PRENOM", "DATE_FIN_ACCES"), (),
                               "brevo_tpl_resiliation"),
    "flash_pret":     Template(17, "LABUSE-G-FLASH-PRET",    "Flash prêt",
                               ("LIEN_PDF", "VALIDITE", "IDU", "COMMUNE"), (),
                               "brevo_tpl_flash_pret"),
    "email_change":   Template(18, "LABUSE-H-EMAIL-CHANGE",  "Adresse e-mail changée",
                               ("PRENOM", "ANCIEN_EMAIL", "NOUVEL_EMAIL"), (),
                               "brevo_tpl_email_change"),
    "retour_traite":  Template(19, "LABUSE-I-RETOUR-TRAITE", "Réponse à un signalement",
                               ("PRENOM", "SON_MESSAGE", "REPONSE"), (),
                               "brevo_tpl_retour_traite"),
}

# RENVOI (4/5) : passé UNIQUEMENT sur un RENVOI d'invitation (le premier envoi ne le passe pas).
# JAMAIS_CONNECTE (7) : passé par la relance J+3. Ce sont des booléens de bloc {% if %}, pas des
# variables substituées — ils n'apparaissent donc pas dans REGISTRE[...].params (mais dans .flags).

#: Rétro-compat — l'ancien mapping clé → champ Settings (lecteurs existants : dashboard, digests).
TEMPLATES: dict[str, str] = {k: t.env_champ for k, t in REGISTRE.items() if t.env_champ}
#: Rétro-compat — libellés servis (source unique = REGISTRE).
LIBELLES: dict[str, str] = {k: t.libelle for k, t in REGISTRE.items()}

# Clé LEGACY 'radar' (ancien digest, ID 12) : retirée du registre canonique (doublon de radar_digest).
# Un appel avec key='radar' est routé vers radar_digest ci-dessous (aucun lecteur ne doit casser).
_ALIAS = {"radar": "radar_digest"}


def _canon(key: str) -> str:
    return _ALIAS.get(key, key)


def template(key: str) -> Template | None:
    return REGISTRE.get(_canon(key))


def template_id(key: str) -> int | None:
    """ID Brevo de `key` : surcharge .env si présente, sinon l'ID CANONIQUE du registre."""
    t = template(key)
    if not t:
        return None
    if t.env_champ:
        v = _setting_ou_env(t.env_champ)
        if v:
            try:
                return int(v)
            except (TypeError, ValueError):
                log.warning("brevo: override .env de %s illisible (%r) — repli sur l'ID canonique %d",
                            key, v, t.id)
    return t.id


def params_attendus(key: str) -> tuple[str, ...]:
    """Variables que le HTML du template attend réellement (substituées ; hors booléens {% if %})."""
    t = template(key)
    return t.params if t else ()


def _api_key() -> str | None:
    """Clé API Brevo : setting préfixé `LABUSE_BREVO_API_KEY` OU repli sans préfixe `BREVO_API_KEY`
    (le .env de prod utilise cette forme, comme `STRIPE_RESTRICTED_KEY`)."""
    import os
    return (getattr(get_settings(), "brevo_api_key", None)
            or os.environ.get("BREVO_API_KEY", "").strip() or None)


def _setting_ou_env(champ: str):
    """Lit un réglage Brevo : setting préfixé (`LABUSE_<CHAMP>`) sinon repli sans préfixe (`<CHAMP>`)."""
    import os
    return getattr(get_settings(), champ, None) or os.environ.get(champ.upper()) or None


def etat_configuration() -> dict:
    """Pour le dashboard : quels templates sont branchés (jamais les IDs eux-mêmes au client)."""
    return {"api": bool(_api_key()),
            "templates": {k: template_id(k) is not None for k in REGISTRE}}


def verifier_templates(timeout: float = 30.0) -> dict:
    """COMPTE-2 Lot 1 — VÉRIFICATION PAR APPEL API : les templates du registre existent chez Brevo,
    sont actifs, portent le nom attendu et exposent les params attendus. Ne lève jamais : renvoie
    {ok, api, expéditeur_unique?, lignes:[{key, id, existe, actif, nom_ok, params_manquants, ...}]}.
    Un template attendu absent / inactif / mal nommé = écart (🔴) signalé, jamais une exception."""
    import re

    import httpx
    out = {"ok": False, "api": bool(_api_key()), "lignes": []}
    api_key = _api_key()
    if not api_key:
        out["raison"] = "Brevo non configuré (BREVO_API_KEY absente)."
        return out
    pat = re.compile(r"\{\{\s*params\.([A-Za-z0-9_]+)")
    senders: set[str] = set()
    lignes = []
    ok_global = True
    for key, t in REGISTRE.items():
        tid = template_id(key)
        ligne = {"key": key, "id": tid, "nom_attendu": t.nom}
        try:
            r = httpx.get(f"{_API}/smtp/templates/{tid}", headers={"api-key": api_key}, timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            ligne.update(existe=False, erreur=f"Brevo injoignable ({type(exc).__name__}).")
            ok_global = False
            lignes.append(ligne)
            continue
        if r.status_code // 100 != 2:
            ligne.update(existe=False, erreur=f"HTTP {r.status_code}")
            ok_global = False
            lignes.append(ligne)
            continue
        data = r.json()
        nom = (data.get("name") or "").strip()
        actif = bool(data.get("isActive"))
        sender = (data.get("sender") or {}).get("email")
        if sender:
            senders.add(sender)
        html = (data.get("subject") or "") + " " + (data.get("htmlContent") or "")
        vus = set(pat.findall(html))
        # nom_ok : le nom Brevo porte le nom attendu (les 14→19 sont préfixés « NN · », toléré).
        nom_ok = t.nom in nom
        manquants = [p for p in t.params if p not in vus]
        ligne.update(existe=True, actif=actif, nom_brevo=nom, nom_ok=nom_ok,
                     expediteur=sender, params_manquants=manquants,
                     params_en_trop=sorted(vus - set(t.params) - set(t.flags)))
        if not (actif and nom_ok and not manquants):
            ok_global = False
        lignes.append(ligne)
    out["lignes"] = lignes
    out["ok"] = ok_global
    out["expediteur_unique"] = (list(senders)[0] if len(senders) == 1 else None)
    out["expediteurs"] = sorted(senders)
    return out


def _evaluer_conditions(txt: str, params: dict) -> str:
    """Évalue les blocs simples {% if params.X %}A{% else %}B{% endif %} (else optionnel) à partir des
    params — pour que l'aperçu RESSEMBLE au rendu Brevo (server-side). Un seul niveau, non imbriqué :
    suffisant pour ces templates ; le vrai rendu reste celui de Brevo. Fonction pure (testable offline)."""
    import re
    motif = re.compile(
        r"\{%\s*if\s+(?:params\.)?([A-Za-z0-9_]+)\s*%\}(.*?)"
        r"(?:\{%\s*else\s*%\}(.*?))?\{%\s*endif\s*%\}", re.S)

    def _rep(m):
        cle, si, sinon = m.group(1), m.group(2), (m.group(3) or "")
        v = params.get(cle)
        return si if (v not in (None, False, "", 0, "0")) else sinon
    for _ in range(3):                        # quelques passes pour des blocs consécutifs
        txt, n = motif.subn(_rep, txt)
        if not n:
            break
    return txt


def apercu_template(key: str, params: dict | None = None) -> dict:
    """APERÇU du mail réel : lit le template chez Brevo (GET /v3/smtp/templates/{id}) et substitue
    naïvement les variables du compte ({{ params.x }} / {{params.x}}). Ne lève JAMAIS : non configuré /
    template absent / Brevo injoignable → {configure:false, raison, params}. Le rendu Brevo étant
    server-side, la substitution ici est indicative (les blocs conditionnels ne sont pas évalués)."""
    params = params or {}
    t = template(key)
    base = {"configure": False, "key": key, "libelle": (t.libelle if t else key), "params": params}
    if not t:
        return {**base, "raison": f"Template inconnu « {key} »."}
    api_key = _api_key()
    if not api_key:
        return {**base, "raison": "Brevo non configuré (BREVO_API_KEY absente)."}
    tpl = template_id(key)
    try:
        import re

        import httpx
        r = httpx.get(f"{_API}/smtp/templates/{tpl}",
                      headers={"api-key": api_key}, timeout=15.0)
        if r.status_code // 100 != 2:
            return {**base, "raison": f"Brevo a refusé la lecture du template (HTTP {r.status_code})."}
        data = r.json()
        subject = data.get("subject") or ""
        html = data.get("htmlContent") or ""

        def _sub(txt: str) -> str:
            txt = _evaluer_conditions(txt, params)
            for k, v in params.items():
                # tolère un filtre Jinja optionnel : {{ params.X }} comme {{ params.X | safe }}.
                txt = re.sub(r"\{\{\s*(?:params\.)?" + re.escape(k) + r"\s*(?:\|[^}]*)?\}\}", str(v), txt)
            return txt
        return {"configure": True, "key": key, "libelle": t.libelle,
                "params": params, "subject": _sub(subject), "html": _sub(html)}
    except Exception as exc:  # noqa: BLE001 — l'aperçu n'échoue jamais en dur
        log.warning("Brevo apercu %s injoignable : %s", key, exc)
        return {**base, "raison": f"Brevo injoignable ({type(exc).__name__})."}


def envoyer_template(to: str, key: str, params: dict | None = None) -> dict:
    """Envoie le template `key` à `to`. Renvoie {envoye: bool, raison?: str, message_id?: str} —
    JAMAIS une levée, JAMAIS un envoi silencieux : non configuré → raison explicite.

    NOTE COMPTE-2 : le point d'entrée applicatif est `mail.envoyer_mail` (file d'attente + journal).
    Cette fonction reste le transport Brevo bas niveau (appelée par la file), suivi de clic DÉSACTIVÉ
    pour les transactionnels (sinon le lien est réécrit vers un domaine que les filtres bloquent)."""
    t = template(key)
    if not t:
        return {"envoye": False, "raison": f"Template inconnu « {key} »."}
    api_key = _api_key()
    if not api_key:
        return {"envoye": False,
                "raison": "Brevo non configuré (BREVO_API_KEY absente) — aucun envoi."}
    tpl = template_id(key)
    try:
        import httpx
        r = httpx.post(
            f"{_API}/smtp/email",
            headers={"api-key": api_key, "content-type": "application/json"},
            json={"templateId": tpl, "to": [{"email": to}], "params": params or {},
                  # suivi de clic/ouverture OFF pour les transactionnels (délivrabilité entreprise).
                  "disableTracking": True},
            timeout=15.0)
        if r.status_code // 100 == 2:
            mid = None
            try:
                mid = r.json().get("messageId")
            except Exception:  # noqa: BLE001
                pass
            return {"envoye": True, "message_id": mid}
        log.warning("Brevo %s → HTTP %s : %s", key, r.status_code, r.text[:200])
        return {"envoye": False, "raison": f"Brevo a refusé l'envoi (HTTP {r.status_code})."}
    except Exception as exc:  # noqa: BLE001 — le dashboard affiche l'échec, jamais un 500
        log.warning("Brevo %s injoignable : %s", key, exc)
        return {"envoye": False, "raison": f"Brevo injoignable ({type(exc).__name__})."}


# `field` importé pour l'API dataclass (défauts mutables éventuels) — gardé pour extensions futures.
_ = field
