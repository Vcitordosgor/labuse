"""MAILS-1 — LE GABARIT UNIQUE des e-mails LABUSE, rendu par l'app.

Un seul modèle, décliné en deux REGISTRES (décision Vic, maquette validée 07/11) :
  · `personnel`  — bienvenue, essai, paiement, résiliation… ton direct, signé « Victor Lagane,
                   fondateur de LABUSE » (encart avatar « VL »), pas d'étiquette.
  · `auto`       — Radar, veille, rapport prêt, maintenance, annonce, mise en vente… une ÉTIQUETTE
                   de couleur selon la nature, les faits en clair, pas de signature personnelle.

Le HTML est volontairement « e-mail safe » : **tableaux** (pas de flex/grid), **styles en ligne**
(pas de classe, Gmail retire le <style>), **largeur 600 px**, lisible sur téléphone (le tableau se
contente de la largeur dispo). Chaque mail a AUSSI une version **texte** (repli multipart, Outlook
en mode texte, délivrabilité). Les couleurs/espacements reprennent la maquette au pixel.

Ce module ne connaît RIEN du métier : il assemble des BLOCS (paragraphe, bouton, étapes, carte,
liste de biens…). Le contenu des 21 mails vit dans `mails_contenu.py`, qui appelle ce gabarit.
Brevo n'est plus qu'un transport (`brevo.envoyer_html`) : le HTML part d'ici, pas d'un template Brevo.
"""
from __future__ import annotations

import html as _html
from dataclasses import dataclass, field

# ───────────────────────── jetons de design (maquette validée) ─────────────────────────
PAGE_BG = "#eef0ee"     # fond de page (gris vert très clair)
CARD_BG = "#ffffff"     # corps du mail
BANNER_BG = "#0b0e0c"   # bandeau sombre
LOGO_WHITE = "#ffffff"  # « LA » du logo
GREEN_LOGO = "#7ee0a0"  # « BUSE » du logo + initiales de l'avatar (vert écran, sur fond sombre)
BASELINE_FG = "#98a39a"  # « Le trésor est sous vos pieds »
TEXT = "#1c201d"        # texte courant
SUB = "#5a665d"         # texte secondaire (sous-titres, détails)
BTN_BG = "#4ade80"      # bouton vert = LE jeton de la charte (`--mint` / bg-mint de l'app)
BTN_FG = "#06301a"      # texte du bouton = `mint-on` de l'app (contraste ≈ 8.9:1 sur #4ade80 → AA)
STEP_BG = "#e6f6ec"     # pastille d'étape / étiquette verte (fond)
STEP_FG = "#1f7a46"     # pastille d'étape / étiquette verte (encre)
FOOT_BG = "#f6f7f6"
FOOT_FG = "#6b776f"
BORDER = "#eef0ee"
CARD_K = "#6b776f"

FONT = "Helvetica, Arial, sans-serif"     # Inter dans la maquette, mais aucune police web en e-mail.
BASELINE = "Le trésor est sous vos pieds"
SIGNATAIRE = "Victor Lagane"
SIGNATURE_TITRE = "Gestionnaire relation entreprise"
TEL = "+262 693 51 71 53"
SIGNATURE_LIGNE = f"{SIGNATURE_TITRE} · {TEL}"
CONTACT = "contact@labuse.immo"
URL_CONFID = "https://labuse.immo/confidentialite/"
URL_MENTIONS = "https://labuse.immo/mentions-legales/"

#: Palette des ÉTIQUETTES (mails automatiques) — une couleur par NATURE (contraste AA sur fond clair).
ETIQUETTES: dict[str, tuple[str, str]] = {
    "radar":       (STEP_BG, STEP_FG),     # Radar / veille / vente — vert « opportunité »
    "rapport":     ("#e7eef7", "#1e557e"),  # rapport prêt — bleu
    "maintenance": ("#fbf0d9", "#8a5a00"),  # maintenance — ambre (service, attention)
    "annonce":     ("#ecefee", "#44514b"),  # nouveauté / source — ardoise neutre
    "securite":    ("#fdecec", "#b0281f"),  # (non utilisé comme étiquette ; réservé)
}


def esc(s: object) -> str:
    """Échappe pour le HTML (le contenu vient de la base : jamais d'injection dans le mail)."""
    return _html.escape(str(s if s is not None else ""), quote=True)


def maj1(s: str) -> str:
    """Majuscule en tête (titre ou phrase) — gère les lettres accentuées (« à » → « À »).
    Idempotent ; laisse tel quel si ça commence déjà par une majuscule, un chiffre ou un symbole."""
    s = s if s is not None else ""
    i = 0
    while i < len(s) and not s[i].isalpha():   # saute une éventuelle ouverture (« , guillemet…)
        i += 1
    if i >= len(s):
        return s
    return s[:i] + s[i].upper() + s[i + 1:]


# ───────────────────────── BLOCS (chaque bloc = (html, texte)) ─────────────────────────
Bloc = tuple[str, str]


def _p_style() -> str:
    return f"margin:0 0 14px;font-family:{FONT};font-size:15px;line-height:1.6;color:{TEXT};"


def paragraphe(texte: str, *, html_brut: str | None = None) -> Bloc:
    """Un paragraphe. `texte` sert au repli texte ; `html_brut` (optionnel) autorise un <b>…</b> déjà
    échappé pour le HTML (sinon `texte` est échappé tel quel)."""
    # Majuscule en tête de phrase (mandat Vic). Pour un `html_brut`, l'appelant garantit la casse.
    corps = html_brut if html_brut is not None else esc(maj1(texte))
    return (f'<p style="{_p_style()}">{corps}</p>', maj1(texte))


def note(texte: str) -> Bloc:
    """Petite note secondaire (style `.sub` de la maquette)."""
    t = maj1(texte)
    return (f'<p style="margin:0 0 14px;font-family:{FONT};font-size:13px;line-height:1.55;'
            f'color:{SUB};">{esc(t)}</p>', t)


def titre_auto(texte: str) -> Bloc:
    """Gros titre des mails automatiques (sous l'étiquette). Majuscule en tête (mandat Vic)."""
    t = maj1(texte)
    return (f'<p style="margin:4px 0 14px;font-family:{FONT};font-size:20px;font-weight:bold;'
            f'line-height:1.3;color:{TEXT};">{esc(t)}</p>', t.upper())


def etiquette(label: str, nature: str = "radar") -> Bloc:
    """Étiquette de couleur (mails automatiques). `nature` ∈ ETIQUETTES."""
    bg, fg = ETIQUETTES.get(nature, ETIQUETTES["annonce"])
    pic = (f'<p style="margin:0 0 4px;font-family:{FONT};"><span style="display:inline-block;'
           f'padding:3px 9px;border-radius:10px;font-family:{FONT};font-size:11px;font-weight:bold;'
           f'letter-spacing:0.06em;background:{bg};color:{fg};">{esc(label)}</span></p>')
    return (pic, f"[{label}]")


def bouton(label: str, href: str) -> Bloc:
    """Bouton d'action principal (vert). Table + bgcolor : rendu fiable jusque dans Outlook."""
    h = esc(href)
    html = (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'style="margin:6px 0 18px;"><tr>'
        f'<td align="center" bgcolor="{BTN_BG}" style="border-radius:6px;">'
        f'<a href="{h}" target="_blank" style="display:inline-block;padding:12px 20px;'
        f'font-family:{FONT};font-size:14px;font-weight:bold;color:{BTN_FG};text-decoration:none;'
        f'border-radius:6px;">{esc(label)}</a></td></tr></table>')
    return (html, f"{label} : {href}")


def lien_secondaire(label: str, href: str) -> Bloc:
    """Lien d'appoint à côté du bouton (ex. « Modifier cette veille »)."""
    h = esc(href)
    return (f'<a href="{h}" target="_blank" style="font-family:{FONT};font-size:14px;color:{STEP_FG};'
            f'font-weight:bold;text-decoration:none;">{esc(label)}</a>'
            f'<div style="height:14px;line-height:14px;font-size:0;">&nbsp;</div>',
            f"{label} : {href}")


def etapes(items: list[tuple[str, str]], *, deux_points: bool = False) -> Bloc:
    """Liste numérotée « 1 / 2 / 3 » (pastille ronde + texte). `items` : (titre_gras, suite).
    `deux_points` : un « : » après l'intitulé en gras (mandat Vic, mail 04)."""
    lignes_html = []
    lignes_txt = []
    for i, (titre, suite) in enumerate(items, 1):
        titre_aff = f"{titre} :" if deux_points else titre
        lignes_html.append(
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="margin:0 0 10px;"><tr>'
            f'<td width="24" valign="top" style="padding-top:2px;">'
            f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
            f'<td width="24" height="24" align="center" valign="middle" bgcolor="{STEP_BG}" '
            f'style="border-radius:12px;font-family:{FONT};font-size:12px;font-weight:bold;'
            f'color:{STEP_FG};">{i}</td></tr></table></td>'
            f'<td style="padding-left:12px;font-family:{FONT};font-size:15px;line-height:1.6;'
            f'color:{TEXT};"><b>{esc(titre_aff)}</b> {esc(suite)}</td></tr></table>')
        lignes_txt.append(f"  {i}. {titre_aff} {suite}")
    return ("".join(lignes_html), "\n".join(lignes_txt))


def ligne_fait(titre: str, detail: str = "", lien: str | None = None, lien_label: str = "voir") -> Bloc:
    """Une ligne de fait (digest des suivis) : titre en gras, détail, lien optionnel."""
    d = f' <span style="color:{SUB};">— {esc(detail)}</span>' if detail else ""
    a = (f' <a href="{esc(lien)}" target="_blank" style="color:{STEP_FG};text-decoration:none;">{esc(lien_label)}</a>'
         if lien else "")
    t = maj1(titre)
    html = f'<p style="{_p_style()}"><b>{esc(t)}</b>{d}{a}</p>'
    txt = f"• {t}" + (f" — {detail}" if detail else "") + (f" ({lien})" if lien else "")
    return (html, txt)


def carte(cle: str, valeur: str) -> Bloc:
    """Encadré gris « clé / valeur » (ex. VOS CRITÈRES)."""
    html = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="margin:0 0 14px;"><tr><td style="background:{FOOT_BG};border-radius:6px;'
            f'padding:14px 16px;font-family:{FONT};">'
            f'<div style="font-size:11px;letter-spacing:0.1em;color:{CARD_K};margin:0 0 6px;">{esc(cle)}</div>'
            f'<div style="font-size:14px;color:{TEXT};line-height:1.5;">{esc(valeur)}</div>'
            f'</td></tr></table>')
    return (html, f"{cle} : {valeur}")


def biens(lignes: list[dict]) -> Bloc:
    """Liste de biens pour l'alerte Radar. Chaque ligne : {titre, detail, prix}.
    Un filet au-dessus de chaque ligne, un filet sous la dernière (maquette)."""
    html_rows = []
    txt_rows = []
    n = len(lignes)
    for i, b in enumerate(lignes):
        bas = f"border-bottom:1px solid {BORDER};" if i == n - 1 else ""
        html_rows.append(
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="border-top:1px solid {BORDER};{bas}"><tr>'
            f'<td style="padding:12px 0;font-family:{FONT};font-size:14px;color:{TEXT};">'
            f'<b>{esc(b.get("titre",""))}</b><br>'
            f'<span style="font-size:12px;color:{SUB};">{esc(b.get("detail",""))}</span></td>'
            f'<td align="right" valign="top" style="padding:12px 0;font-family:{FONT};font-size:14px;'
            f'font-weight:bold;color:{TEXT};white-space:nowrap;">{esc(b.get("prix",""))}</td>'
            f'</tr></table>')
        txt_rows.append(f"  • {b.get('titre','')} — {b.get('detail','')} — {b.get('prix','')}")
    return ("".join(html_rows), "\n".join(txt_rows))


def encadre_info(texte: str, nature: str = "maintenance") -> Bloc:
    """Bandeau d'information mis en évidence (ex. fenêtre de coupure maintenance)."""
    bg, fg = ETIQUETTES.get(nature, ETIQUETTES["maintenance"])
    html = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="margin:0 0 14px;"><tr><td style="background:{bg};border-radius:6px;'
            f'padding:12px 16px;font-family:{FONT};font-size:14px;font-weight:bold;color:{fg};'
            f'line-height:1.5;">{esc(texte)}</td></tr></table>')
    return (html, texte)


# ───────────────────────── PIED de page ─────────────────────────
@dataclass
class Pied:
    """Options du pied (décision Vic : pas d'adresse ; « Mentions légales » rend l'éditeur identifiable ;
    mails de sécurité = pied SANS désinscription)."""
    raison: str = "Vous recevez ce mail parce que vous avez un compte LABUSE."
    lien_prefs: str = ""      # « Gérer mes notifications » (préférences du compte)
    lien_desabo: str = ""     # « Me désinscrire » (1 clic) — absent sur les mails de sécurité
    securite: bool = False    # True → pas de ligne de désinscription (mot de passe, adresse)


def _footer(pied: Pied) -> Bloc:
    liens_html = []
    liens_txt = []
    if pied.lien_prefs:
        liens_html.append(f'<a href="{esc(pied.lien_prefs)}" target="_blank" '
                          f'style="color:{FOOT_FG};text-decoration:underline;">Gérer mes notifications</a>')
        liens_txt.append(f"Gérer mes notifications : {pied.lien_prefs}")
    if pied.lien_desabo and not pied.securite:
        liens_html.append(f'<a href="{esc(pied.lien_desabo)}" target="_blank" '
                          f'style="color:{FOOT_FG};text-decoration:underline;">Me désinscrire</a>')
        liens_txt.append(f"Me désinscrire : {pied.lien_desabo}")
    liens_html.append(f'<a href="{URL_CONFID}" target="_blank" '
                      f'style="color:{FOOT_FG};text-decoration:underline;">Confidentialité</a>')
    liens_txt.append(f"Confidentialité : {URL_CONFID}")
    liens_html.append(f'<a href="{URL_MENTIONS}" target="_blank" '
                      f'style="color:{FOOT_FG};text-decoration:underline;">Mentions légales</a>')
    liens_txt.append(f"Mentions légales : {URL_MENTIONS}")

    html = (
        f'<tr><td style="padding:16px 32px 22px;background:{FOOT_BG};font-family:{FONT};'
        f'font-size:11px;line-height:1.6;color:{FOOT_FG};">'
        f'LABUSE · <a href="mailto:{CONTACT}" style="color:{FOOT_FG};text-decoration:underline;">{CONTACT}</a><br>'
        f'{esc(pied.raison)} ' + " · ".join(liens_html) +
        '</td></tr>')
    txt = ("—\nLABUSE · " + CONTACT + "\n" + pied.raison + "\n" + "\n".join(liens_txt))
    return (html, txt)


def _signature_row() -> str:
    """Encart signature (mails personnels) : avatar « VL » + nom + ligne de contact."""
    return (
        f'<tr><td style="padding:12px 32px 22px;border-top:1px solid {BORDER};">'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
        f'<td width="36" valign="middle">'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
        f'<td width="36" height="36" align="center" valign="middle" bgcolor="{BANNER_BG}" '
        f'style="border-radius:18px;font-family:{FONT};font-size:13px;font-weight:bold;'
        f'color:{GREEN_LOGO};">VL</td></tr></table></td>'
        f'<td style="padding-left:12px;font-family:{FONT};">'
        f'<b style="font-size:14px;color:{TEXT};">{SIGNATAIRE}</b><br>'
        f'<span style="font-size:12px;color:{SUB};">{SIGNATURE_LIGNE}</span>'
        f'</td></tr></table></td></tr>')


def _banniere() -> str:
    return (
        f'<tr><td style="background:{BANNER_BG};padding:18px 32px;">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
        f'<td align="left" style="font-family:{FONT};font-size:16px;font-weight:bold;'
        f'letter-spacing:0.06em;color:{LOGO_WHITE};">LA<span style="color:{GREEN_LOGO};">BUSE</span></td>'
        f'<td align="right" style="font-family:{FONT};font-size:11px;color:{BASELINE_FG};'
        f'letter-spacing:0.02em;">{BASELINE}</td>'
        f'</tr></table></td></tr>')


@dataclass
class Mail:
    """Résultat du gabarit : prêt pour le transport (Brevo /smtp/email ou SMTP)."""
    sujet: str
    html: str
    texte: str
    headers: dict = field(default_factory=dict)


def rendre(*, sujet: str, registre: str, blocs: list[Bloc], pied: Pied,
           apercu: str = "", headers: dict | None = None) -> Mail:
    """Assemble le mail final à partir de BLOCS.

    `registre` : 'personnel' (signature Victor) ou 'auto' (étiquette, pas de signature).
    `blocs`    : liste de (html, texte) produits par les helpers ci-dessus.
    `pied`     : options du pied de page (liens, sécurité).
    `apercu`   : texte d'aperçu (preheader) masqué, affiché par Gmail/Apple Mail après le sujet.
    """
    corps_html = "".join(b[0] for b in blocs)
    sig = _signature_row() if registre == "personnel" else ""
    pied_html, pied_txt = _footer(pied)
    pre = (f'<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;opacity:0;'
           f'color:transparent;height:0;width:0;font-size:1px;line-height:1px;">{esc(apercu)}</div>'
           if apercu else "")

    html = (
        '<!DOCTYPE html>\n'
        '<html lang="fr" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">\n'
        '<head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="X-UA-Compatible" content="IE=edge">'
        '<meta name="color-scheme" content="light only"><meta name="supported-color-schemes" content="light">'
        f'<title>{esc(sujet)}</title>'
        '<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch>'
        '</o:OfficeDocumentSettings></xml></noscript><![endif]-->'
        '</head>'
        f'<body style="margin:0;padding:0;background:{PAGE_BG};">'
        f'{pre}'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="background:{PAGE_BG};"><tr><td align="center" style="padding:32px 12px;">'
        '<!--[if mso]><table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->'
        f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" '
        f'style="width:600px;max-width:600px;background:{CARD_BG};border-radius:8px;overflow:hidden;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.08);">'
        f'{_banniere()}'
        f'<tr><td style="padding:28px 32px 8px;font-family:{FONT};font-size:15px;line-height:1.6;'
        f'color:{TEXT};">{corps_html}</td></tr>'
        f'{sig}'
        f'{pied_html}'
        '</table>'
        '<!--[if mso]></td></tr></table><![endif]-->'
        '</td></tr></table></body></html>')

    # ── version texte (repli) ──
    parts = [BASELINE]
    parts += [b[1] for b in blocs if b[1]]
    if registre == "personnel":
        parts.append(f"— {SIGNATAIRE}, {SIGNATURE_TITRE.lower()} · {TEL}")
    parts.append(pied_txt)
    texte = "\n\n".join(p for p in parts if p).strip() + "\n"

    return Mail(sujet=sujet, html=html, texte=texte, headers=headers or {})

