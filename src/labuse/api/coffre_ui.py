"""AUDIT PAIEMENT · PARTIE E — le design system des surfaces d'ENTRÉE (validé par Vic).

Source UNIQUE du dessin (les maquettes docs/mockups/auth/) : tokens en variables CSS (zéro
hex épars dans les pages), DA cockpit, accessibilité AA (contraste, focus visibles, labels
liés, erreurs annoncées, prefers-reduced-motion). onboarding.py ET auth.py rendent leur nuit
Coffre à travers ce module — la mécanique de paiement (auditée) n'est jamais touchée ici.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import time


# ── jeton SIGNÉ de « en instance de paiement » (porte l'écran de bascule Checkout) ──
# Purement un porteur d'identité entre l'acceptation CGV et le POST de paiement : il ne
# touche PAS la mécanique auditée (creer_checkout/webhook/réconciliation inchangés).

def _secret() -> bytes:
    # Même clé que la signature de session (auth.cle_signature) : LABUSE_SECRET_KEY, sinon clé
    # éphémère en 'local' UNIQUEMENT. Plus AUCUNE constante en dur : l'ancien repli
    # « labuse-dev-secret » rendait ce jeton de paiement forgeable (audit 360, P0-3). Hors
    # 'local', la clé est exigée au démarrage (auth.exiger_secret_prod).
    from . import auth
    return auth.cle_signature()


def pay_token(compte_id: int, ttl_s: int = 1800) -> str:
    """Jeton court (30 min) liant l'écran de bascule au compte à payer."""
    payload = f"{compte_id}.{int(time.time()) + ttl_s}"
    sig = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}.{sig}"


def pay_cid(token: str) -> int | None:
    """Jeton → compte_id (None si absent/altéré/expiré)."""
    try:
        cid, exp, sig = token.split(".", 2)
        payload = f"{cid}.{exp}"
        good = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, good) or int(exp) < time.time():
            return None
        return int(cid)
    except (ValueError, TypeError):
        return None

# tokens = variables CSS (mêmes valeurs que la DA de l'app ; on ne pose pas d'hex en dur ailleurs)
CSS = """
:root{
  --bg:#050706; --s1:#0B100D; --s2:#0D120F; --s3:#111814; --line:#1B2620; --line2:#1E2A23;
  /* O3 — le vert du parcours s'aligne sur la maquette validée (et sur l'oiseau, déjà #4ADE80).
     --mint = accent/CTA ; --mint-dim = liens & puces (vert plus sobre, ne porte pas de texte). */
  --mint:#4ADE80; --mint-dim:#2E9E5B; --mint-ink:#04150A; --violet:#B497F0; --or:#C9A961;
  --hi:#ECF5EF; --txt:#C9DCD1; --mut:#8FA69A; --dim:#55605A; --err:#E8695A; --warn:#D6A64A;
  --r:12px; --ease:cubic-bezier(.2,.7,.2,1);
}
*{box-sizing:border-box}
html,body{margin:0;min-height:100%}
/* O1 — le contenu se CENTRE dans la hauteur, le pied reste en bas, plus jamais de grand vide.
   `.bloc` remplit la fenêtre (flex colonne) : `.top` (flex:1) centre le contenu, `.foot` colle en
   bas. Contenu plus grand que l'écran → la page défile naturellement (min-height, pas height). */
body{background:radial-gradient(130% 90% at 50% -8%, rgba(74,222,128,.05), transparent 55%),
  radial-gradient(120% 120% at 50% -10%, #0A100C 0%, var(--bg) 60%);
  color:var(--txt);font:15px/1.6 -apple-system,'Inter',system-ui,sans-serif;min-height:100vh;padding:0}
.bloc{width:100%;max-width:var(--w,412px);min-height:100vh;margin:0 auto;
  display:flex;flex-direction:column;padding:36px 26px 20px}
.top{flex:1;display:flex;flex-direction:column;justify-content:center;min-height:0}
.foot{padding-top:20px;text-align:center;font-size:11px;color:var(--dim);letter-spacing:.02em;
  font-family:'Space Grotesk',system-ui,sans-serif}
.foot a{color:var(--mint-dim)}
.oiseau{display:block;margin:0 auto 20px;height:30px;width:auto;filter:drop-shadow(0 0 16px rgba(74,222,128,.30))}
h1{font:600 15px/1.3 'Space Grotesk',system-ui,sans-serif;letter-spacing:.2em;text-transform:uppercase;color:var(--hi);text-align:center;margin:0 0 4px}
.sub,.sous{text-align:center;font-size:11.5px;color:var(--dim);letter-spacing:.1em;margin:0 0 28px}
.cgvbox{display:flex;gap:11px;align-items:flex-start;margin-top:22px;background:var(--s2);border:1px solid var(--line);border-radius:var(--r);padding:13px;font-size:12.5px;color:var(--txt)}
.cgvbox input{margin-top:2px;width:17px;height:17px;accent-color:var(--mint);flex-shrink:0}
label{display:block;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut);margin:18px 0 7px}
.field{position:relative}
/* E7 mobile — font-size 16px en LONGHAND sur les champs : SOUS 16px, iOS Safari zoome au focus
   (le parcours « saute » sur iPhone). ⚠ l'ancien raccourci `font:15px inherit` était INVALIDE
   (`inherit` n'est pas une font-family de shorthand) → IGNORÉ : l'input tombait au défaut UA
   ~13px, PIRE. En longhand la règle s'applique vraiment. */
input[type=email],input[type=password],input[type=text]{width:100%;background:var(--s2);border:1px solid var(--line2);
  border-radius:var(--r);color:var(--hi);font-size:16px;font-family:inherit;padding:11px 12px;outline:none;
  transition:border-color .15s var(--ease),box-shadow .15s var(--ease)}
input:disabled{color:var(--mut)}
input::placeholder{color:var(--dim)}
input:focus-visible{border-color:var(--mint);box-shadow:0 0 0 3px rgba(92,230,161,.16)}
/* O2 — le bouton d'action ALLUMÉ (par défaut) : vert menthe, texte sombre, ombre portée. */
button,.btn{display:flex;width:100%;align-items:center;justify-content:center;gap:9px;margin-top:24px;
  min-height:56px;background:var(--mint);color:var(--mint-ink);border:0;border-radius:14px;
  font:700 15.5px 'Space Grotesk',system-ui,sans-serif;letter-spacing:.02em;cursor:pointer;
  box-shadow:0 12px 30px -12px rgba(74,222,128,.55);
  transition:filter .15s var(--ease),background .15s,box-shadow .15s,color .15s;text-decoration:none}
button:hover,.btn:hover{filter:brightness(1.06)}
/* O2 — ÉTEINT : un bouton qui ne peut pas agir n'est JAMAIS peint comme un bouton actif.
   Fond sombre, texte gris LISIBLE (contraste ~4:1), bordure discrète, aucune ombre. */
button.off,.btn.off,button[aria-disabled=true]{background:#141A17;color:#7A857E;
  border:1px solid var(--line2);box-shadow:none;filter:none}
button.off:hover,.btn.off:hover,button[aria-disabled=true]:hover{filter:none}
button:disabled,.btn:disabled{background:#141A17;color:#7A857E;cursor:not-allowed;box-shadow:none;filter:none}
button:focus-visible,.btn:focus-visible{outline:2px solid var(--mint);outline-offset:3px}
.off .arr{display:none}
.ghost{background:none;border:1px solid var(--line2);color:var(--txt)}
.linkrow{margin-top:18px;text-align:center;font-size:12.5px}
a{color:var(--mint);text-decoration:none} a:hover{text-decoration:underline}
a:focus-visible{outline:2px solid var(--mint);outline-offset:2px;border-radius:3px}
.note{font-size:11px;color:var(--dim);text-align:center;margin-top:22px;line-height:1.6}
.err{color:var(--err);font-size:12.5px;margin-top:10px;min-height:18px;display:flex;gap:6px;align-items:flex-start}
.spin{width:15px;height:15px;border:2px solid rgba(6,19,12,.35);border-top-color:var(--mint-ink);border-radius:50%;animation:sp .7s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.meter{display:flex;gap:4px;margin-top:9px}
.meter i{height:4px;flex:1;border-radius:2px;background:var(--line2);transition:background .2s}
.meter.faible i:nth-child(1){background:var(--err)}
.meter.moyen i:nth-child(-n+2){background:var(--warn)}
.meter.fort i{background:var(--mint)}
.meterlbl{font-size:11px;color:var(--mut);margin-top:6px}
.consent{display:flex;gap:11px;align-items:flex-start;margin-top:22px;background:var(--s2);
  border:1px solid var(--line);border-radius:var(--r);padding:13px}
.consent input{margin-top:2px;width:17px;height:17px;accent-color:var(--mint);flex-shrink:0}
.consent label{all:unset;font-size:12.5px;color:var(--txt);line-height:1.5;cursor:pointer}
.recap{background:var(--s2);border:1px solid var(--line);border-radius:var(--r);padding:15px;margin-bottom:6px}
.recap .prix{font:700 26px 'Space Grotesk',system-ui,sans-serif;color:var(--hi);font-variant-numeric:tabular-nums}
.recap .quoi{font-size:12.5px;color:var(--mut);margin-top:2px}
.trust{display:flex;flex-direction:column;gap:9px;margin:18px 0 4px}
.trust div{display:flex;gap:9px;align-items:center;font-size:12px;color:var(--mut)}
.trust svg{flex-shrink:0}
.pill{display:inline-flex;align-items:center;gap:6px;border:1px solid rgba(92,230,161,.4);border-radius:999px;
  padding:4px 12px;font-size:12px;color:var(--mint)}
.big{text-align:center;margin:6px 0}
.big .mark{width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 14px;font-size:24px}
.mark.ok{background:rgba(92,230,161,.12);color:var(--mint);border:1px solid rgba(92,230,161,.4)}
.mark.soft{background:rgba(232,180,76,.1);color:var(--warn);border:1px solid rgba(232,180,76,.35)}
/* S3 — LISIBILITÉ des pages légales : longue lecture, pas un bloc centré étroit.
   Le corps se lit du HAUT (pas centré verticalement comme les écrans courts), colonne ~68ch. */
.legalpage .top{justify-content:flex-start;padding-top:4px}
.legalpage .bloc{max-width:760px}
.legal{max-width:68ch;margin:0 auto;text-align:left}
.legal h1{text-align:left;font-size:19px;letter-spacing:.06em;margin:4px 0 4px}
.legal .sous{text-align:left;letter-spacing:.06em;font-size:12px;margin:0 0 6px}
.legal .maj{color:var(--mut);font-size:12.5px;line-height:1.6;margin:0 0 8px}
/* sommaire cliquable (CGV) */
.toc{background:var(--s2);border:1px solid var(--line);border-radius:var(--r);padding:16px 20px;margin:18px 0 6px}
.toc b{display:block;font:600 11px 'Space Grotesk',system-ui,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--mut);margin:0 0 10px}
.toc ol{margin:0;padding-left:20px;columns:2;column-gap:28px}
.toc li{margin:4px 0;font-size:13.5px;break-inside:avoid}
.toc a{color:var(--txt)} .toc a:hover{color:var(--mint)}
/* articles : titre net, filet de séparation, interligne aéré */
.legal h2{color:var(--hi);font:600 16px 'Space Grotesk',system-ui,sans-serif;letter-spacing:.01em;
  margin:34px 0 10px;padding-top:20px;border-top:1px solid var(--line);scroll-margin-top:16px}
.legal p{font-size:14.5px;line-height:1.75;color:var(--txt);margin:0 0 13px}
.legal .haut{display:inline-block;font-size:12px;color:var(--mut);margin:6px 0 0}
.legal .haut:hover{color:var(--mint)}
.card{background:var(--s2);border:1px solid var(--line);border-radius:var(--r);padding:22px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media (max-width:480px){.bloc{padding:28px 18px 16px}.recap .prix{font-size:22px}}
"""

# M83 D — logo LABUSE #4ADE80 (nouvelle marque). Constante UNIQUE réutilisée par tout le tunnel auth
# (auth.py, onboarding.py, app.py 404). Tracé = celui du fichier source frontend/public/marque.
OISEAU = ('<svg class="oiseau" viewBox="0 0 240 82" fill="#4ADE80" aria-hidden="true">'
          '<path d="M2 15 C58 10 100 18 120 27 C140 18 182 10 238 15 C202 29 162 40 135 46 '
          'C127 49 122 53 120 60 C118 53 113 49 105 46 C78 40 38 29 2 15 Z"/></svg>')

# E3 — la barre de robustesse du mot de passe vit désormais dans /parcours.js (fichier
# same-origin, CSP-safe) : l'ancien STRENGTH_JS INLINE était bloqué en prod par script-src 'self'.

LOCK_SVG = ('<svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="var(--mint)" '
            'stroke-width="1.5" aria-hidden="true"><rect x="4" y="9" width="12" height="8" rx="1.5"/>'
            '<path d="M7 9V6.5a3 3 0 0 1 6 0V9"/></svg>')


# Pied de page légal PARTAGÉ (tous les écrans du parcours l'affichent en bas — O1).
FOOTER_LEGAL = ('Radar foncier · La Réunion — <a href="/cgv">CGV</a> · '
                '<a href="/mentions-legales">mentions légales</a> · '
                '<a href="/confidentialite">confidentialité</a>')


def page(titre: str, corps: str, *, w: int | None = None, legal: bool = False,
         head: str = "", foot: str = "") -> str:
    wvar = f"--w:{w}px;" if w else ""
    cls = "legal" if legal else ""
    # S3 — les pages légales sont de LONGS documents : le corps se lit du HAUT (pas centré
    # verticalement) et dans une colonne de lecture confortable (voir CSS `.legalpage`/`.legal`).
    body_cls = ' class="legalpage"' if legal else ""
    # O1 — le contenu vit dans `.top` (centré verticalement), le pied `foot` colle en bas.
    foot_html = f'<div class="foot">{foot}</div>' if foot else ""
    return (f"<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<meta name=\"robots\" content=\"noindex\">"
            # M18 RG-FAV : favicon = logo LABUSE (buse) INLINE en SVG — garanti sur toutes les pages
            # du tunnel, indépendant du service statique /socle/ (les PNG restent en repli).
            f"<link rel=\"icon\" type=\"image/svg+xml\" href=\"data:image/svg+xml,"
            f"%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 82'%3E%3Cpath fill='%234ADE80' "
            f"d='M2 15 C58 10 100 18 120 27 C140 18 182 10 238 15 C202 29 162 40 135 46 C127 49 122 53 "
            f"120 60 C118 53 113 49 105 46 C78 40 38 29 2 15 Z'/%3E%3C/svg%3E\">"
            f"<link rel=\"icon\" type=\"image/png\" sizes=\"32x32\" href=\"/socle/favicon-32.png\">"
            f"<link rel=\"icon\" type=\"image/png\" sizes=\"16x16\" href=\"/socle/favicon-16.png\">"
            f"<title>LABUSE — {html.escape(titre)}</title>"
            f"<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">"
            f"<link href=\"https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&"
            f"family=Inter:wght@400;500;600&display=swap\" rel=\"stylesheet\">"
            f"<style>{CSS}</style>{head}</head>"
            f"<body{body_cls} style=\"{wvar}\"><main class=\"{cls} bloc\" role=\"main\" style=\"{wvar}\">"
            f"<div class=\"top\">{corps}</div>{foot_html}</main></body></html>")
