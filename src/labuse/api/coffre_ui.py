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

from ..config import get_settings


# ── jeton SIGNÉ de « en instance de paiement » (porte l'écran de bascule Checkout) ──
# Purement un porteur d'identité entre l'acceptation CGV et le POST de paiement : il ne
# touche PAS la mécanique auditée (creer_checkout/webhook/réconciliation inchangés).

def _secret() -> bytes:
    s = get_settings().secret_key or "labuse-dev-secret"
    return s.encode()


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
  --mint:#5CE6A1; --mint-ink:#06130C; --violet:#B497F0; --or:#C9A961;
  --hi:#ECF5EF; --txt:#C9DCD1; --mut:#8FA69A; --dim:#5C7268; --err:#E8695A; --warn:#E8B44C;
  --r:10px; --ease:cubic-bezier(.2,.7,.2,1);
}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{background:radial-gradient(120% 120% at 50% -10%, #0A100C 0%, var(--bg) 60%);
  color:var(--txt);font:15px/1.6 -apple-system,'Inter',system-ui,sans-serif;
  display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px}
.bloc{width:100%;max-width:var(--w,400px)}
.oiseau{display:block;margin:0 auto 14px;height:28px;width:auto;filter:drop-shadow(0 0 14px rgba(201,169,97,.25))}
h1{font:600 15px/1.3 'Space Grotesk',inherit;letter-spacing:.2em;text-transform:uppercase;color:var(--hi);text-align:center;margin:0 0 4px}
.sub,.sous{text-align:center;font-size:11.5px;color:var(--dim);letter-spacing:.1em;margin:0 0 28px}
.cgvbox{display:flex;gap:11px;align-items:flex-start;margin-top:22px;background:var(--s2);border:1px solid var(--line);border-radius:var(--r);padding:13px;font-size:12.5px;color:var(--txt)}
.cgvbox input{margin-top:2px;width:17px;height:17px;accent-color:var(--mint);flex-shrink:0}
label{display:block;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut);margin:18px 0 7px}
.field{position:relative}
input[type=email],input[type=password],input[type=text]{width:100%;background:var(--s2);border:1px solid var(--line2);
  border-radius:var(--r);color:var(--hi);font:15px inherit;padding:11px 12px;outline:none;
  transition:border-color .15s var(--ease),box-shadow .15s var(--ease)}
input:disabled{color:var(--mut)}
input::placeholder{color:var(--dim)}
input:focus-visible{border-color:var(--mint);box-shadow:0 0 0 3px rgba(92,230,161,.16)}
button,.btn{display:flex;width:100%;align-items:center;justify-content:center;gap:8px;margin-top:26px;
  background:var(--mint);color:var(--mint-ink);border:0;border-radius:var(--r);font:600 14px inherit;
  padding:12px;cursor:pointer;transition:filter .15s var(--ease);text-decoration:none}
button:hover,.btn:hover{filter:brightness(1.08)}
button:focus-visible,.btn:focus-visible{outline:2px solid var(--mint);outline-offset:3px}
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
.recap .prix{font:700 26px 'Space Grotesk',inherit;color:var(--hi);font-variant-numeric:tabular-nums}
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
.legal h2{color:var(--hi);font-size:14px;margin:24px 0 6px}
.legal p{font-size:13px;color:var(--txt)}
.legal .maj{color:var(--dim);font-size:11.5px}
.card{background:var(--s2);border:1px solid var(--line);border-radius:var(--r);padding:22px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media (max-width:480px){body{padding:16px;align-items:flex-start}.recap .prix{font-size:22px}}
"""

OISEAU = ('<svg class="oiseau" viewBox="0 0 240 82" fill="var(--or)" aria-hidden="true">'
          '<path d="M2 15 C58 10 100 18 120 27 C140 18 182 10 238 15 C202 29 162 40 135 46 '
          'C127 49 122 53 120 60 C118 53 113 49 105 46 C78 40 38 29 2 15 Z"/></svg>')

# barre de robustesse du mot de passe (invitation, reset) — annonce ARIA live
STRENGTH_JS = """
<script>
function labStrength(v){var m=document.getElementById('meter'),l=document.getElementById('rules');
 if(!m)return;var s=0;if(v.length>=10)s++;if(/[0-9]/.test(v)&&/[a-z]/i.test(v))s++;if(/[^a-z0-9]/i.test(v)&&v.length>=12)s++;
 m.className='meter '+(s>=3?'fort':s==2?'moyen':s==1?'faible':'');
 l.textContent=!v?'10 caractères minimum — mélangez lettres, chiffres et symboles.':
  s>=3?'Robuste — parfait.':s==2?'Correct — un symbole le rendrait robuste.':'Trop simple — allongez-le.';}
</script>"""

LOCK_SVG = ('<svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="var(--mint)" '
            'stroke-width="1.5" aria-hidden="true"><rect x="4" y="9" width="12" height="8" rx="1.5"/>'
            '<path d="M7 9V6.5a3 3 0 0 1 6 0V9"/></svg>')


def page(titre: str, corps: str, *, w: int | None = None, legal: bool = False, head: str = "") -> str:
    wvar = f"--w:{w}px;" if w else ""
    cls = "legal" if legal else ""
    return (f"<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<meta name=\"robots\" content=\"noindex\">"
            f"<title>LABUSE — {html.escape(titre)}</title>"
            f"<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">"
            f"<link href=\"https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&"
            f"family=Inter:wght@400;500;600&display=swap\" rel=\"stylesheet\">"
            f"<style>{CSS}</style>{head}</head>"
            f"<body style=\"{wvar}\"><main class=\"{cls} bloc\" role=\"main\" style=\"{wvar}\">{corps}</main></body></html>")
