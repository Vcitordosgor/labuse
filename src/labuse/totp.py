"""2FA ADMIN (VPS · AC-025) — TOTP RFC 6238 en STDLIB PUR (hmac/struct/base64/time).

Pourquoi pas pyotp : la primitive tient en 30 lignes auditables, et chaque dépendance
d'authentification est une surface d'attaque supply-chain — pour un secret de porte
admin, on garde le code sous les yeux. Paramètres = ceux que Google Authenticator &
co. supposent par défaut (SHA-1, pas de 30 s, 6 chiffres) : tout autre choix casserait
silencieusement les apps clientes.

L'anti-rejeu (un code ne sert qu'une fois) ne vit PAS ici : `verifier_code` renvoie le
PAS DE TEMPS accepté, et c'est la couche comptes (colonne dernier_pas) qui refuse un
pas déjà consommé — la primitive reste pure et testable sur les vecteurs RFC.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

PERIODE_S = 30      # pas de temps RFC 6238 (défaut universel des apps TOTP)
CHIFFRES = 6        # longueur du code (idem)


def generer_secret() -> str:
    """Secret partagé : 160 bits d'aléa CSPRNG, encodés base32 (l'alphabet que les
    apps TOTP savent saisir/scanner). 160 bits = la taille du bloc SHA-1 (RFC 4226 §4)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def _cle(secret: str) -> bytes:
    # tolère les secrets recopiés à la main : casse/espaces/padding négligés
    s = secret.strip().replace(" ", "").upper()
    s += "=" * (-len(s) % 8)
    return base64.b32decode(s)


def code_totp(secret: str, t: float | None = None) -> str:
    """Code à 6 chiffres pour l'instant t (défaut : maintenant) — HOTP(SHA-1) sur le
    compteur t//30, troncature dynamique RFC 4226 §5.3."""
    pas = int((time.time() if t is None else t) // PERIODE_S)
    return _code_au_pas(secret, pas)


def _code_au_pas(secret: str, pas: int) -> str:
    mac = hmac.new(_cle(secret), struct.pack(">Q", pas), hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    entier = struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(entier % 10 ** CHIFFRES).zfill(CHIFFRES)


def verifier_code(secret: str, code: str, fenetre: int = 1,
                  t: float | None = None) -> int | None:
    """Le code est-il valable à ±`fenetre` pas (tolérance d'horloge) ? Renvoie le PAS
    accepté (pour l'anti-rejeu : l'appelant refuse tout pas ≤ dernier_pas consommé),
    None sinon. Comparaison en temps constant — un oracle de timing sur 6 chiffres
    se brute-force en minutes."""
    code = (code or "").strip().replace(" ", "")
    if len(code) != CHIFFRES or not code.isdigit():
        return None
    pas_courant = int((time.time() if t is None else t) // PERIODE_S)
    for delta in range(-fenetre, fenetre + 1):
        pas = pas_courant + delta
        if pas >= 0 and hmac.compare_digest(_code_au_pas(secret, pas), code):
            return pas
    return None


def uri_otpauth(secret: str, email: str) -> str:
    """URI de provisionnement (format Google Authenticator, standard de fait) — c'est
    ELLE qui part dans le QR d'enrôlement."""
    return (f"otpauth://totp/LABUSE:{quote(email)}"
            f"?secret={secret}&issuer=LABUSE")


def qr_svg(donnees: str) -> str:
    """QR en SVG inline (lib `qrcode`, sortie SvgPathImage : un seul <path>, zéro PIL,
    zéro fichier temporaire) — s'insère tel quel dans la page d'enrôlement."""
    import io

    import qrcode
    from qrcode.image.svg import SvgPathImage

    img = qrcode.make(donnees, image_factory=SvgPathImage, box_size=14)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode("utf-8")
    # la déclaration <?xml …?> est invalide EN PLEIN HTML — on ne garde que la balise <svg>
    return svg[svg.index("<svg"):]
