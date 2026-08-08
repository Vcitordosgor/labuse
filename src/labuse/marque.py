"""M23-A — MARQUE DU CLIENT sur les documents ABONNÉ.

Le logo + la marque (raison sociale, coordonnées, mention libre) vivent SUR LE COMPTE
(colonnes additives de `comptes`). Ils apparaissent sur les exports ABONNÉ uniquement
(Dossier, Financier, Argumentaire, Potentiel, Lettre) — JAMAIS sur le Flash 79 €
(produit LABUSE : le chemin flash/report.py ne charge jamais ce module).
Le wordmark LABUSE reste présent partout + mention « Généré via LABUSE » dans le bloc
client (A3 : ne jamais laisser croire que le client a produit la donnée).
Règle M22-C4 : champ vide → RIEN ne s'imprime (aucun libellé orphelin).

Upload : png/jpg/svg, ≤ 512 Ko, signature de fichier VÉRIFIÉE (pas le mime déclaré).
"""
from __future__ import annotations

import base64
import re

from sqlalchemy import text

MAX_LOGO_OCTETS = 512 * 1024
FORMATS = {"image/png": b"\x89PNG", "image/jpeg": b"\xff\xd8\xff"}  # + svg (texte, testé à part)

MENTION_LABUSE = "Généré via LABUSE — données et analyses LABUSE"


def ensure_colonnes(db) -> None:
    """Colonnes additives sur comptes (idempotent)."""
    for ddl in ("ALTER TABLE comptes ADD COLUMN IF NOT EXISTS logo bytea",
                "ALTER TABLE comptes ADD COLUMN IF NOT EXISTS logo_mime text",
                "ALTER TABLE comptes ADD COLUMN IF NOT EXISTS marque jsonb"):
        db.execute(text(ddl))


def valider_logo(contenu: bytes, mime_declare: str) -> str:
    """Valide taille + FORMAT RÉEL (signature). Renvoie le mime retenu ; ValueError sinon."""
    if len(contenu) > MAX_LOGO_OCTETS:
        raise ValueError(f"Logo trop lourd ({len(contenu) // 1024} Ko > 512 Ko).")
    if not contenu:
        raise ValueError("Fichier vide.")
    for mime, magic in FORMATS.items():
        if contenu.startswith(magic):
            return mime
    tete = contenu[:256].lstrip().lower()
    if tete.startswith(b"<svg") or (tete.startswith(b"<?xml") and b"<svg" in contenu[:2048].lower()):
        bas = contenu.lower()
        # M-C (F6) — durcissement SVG : au-delà de <script>, refuser les autres vecteurs
        # d'exécution. Sans risque aujourd'hui (SVG en base64 dans WeasyPrint) mais requis AVANT
        # tout affichage INLINE (le SVG inline exécute onload=/<foreignObject>/URIs javascript:).
        if b"<script" in bas:                        # SVG : jamais de script embarqué
            raise ValueError("SVG refusé : contenu actif (<script>) interdit.")
        if b"<foreignobject" in bas:                 # embarque du HTML (donc du JS) dans le SVG
            raise ValueError("SVG refusé : <foreignObject> (HTML embarqué) interdit.")
        if b"javascript:" in bas:                    # URI active (href/xlink:href)
            raise ValueError("SVG refusé : URI javascript: interdite.")
        if re.search(rb"\son[a-z]+\s*=", bas):       # gestionnaires onload=/onerror=/onclick=…
            raise ValueError("SVG refusé : gestionnaire d'événement (on…=) interdit.")
        return "image/svg+xml"
    raise ValueError("Format non reconnu — png, jpg ou svg uniquement.")


def charger(db, request) -> dict | None:
    """Marque du compte de la requête (session utilisateur) — None en pilote/dev ou si
    RIEN n'est configuré (M22-C4 : on n'imprime pas un bloc vide)."""
    try:
        from .api.tenant import current_compte   # M-K (P2-65) : chemin unique de résolution du compte
        cid = current_compte(request)
        if cid is None:
            return None
        row = db.execute(text(
            "SELECT logo, logo_mime, marque FROM comptes WHERE id = :c"),
            {"c": cid}).mappings().first()
        if not row:
            return None
        m = row["marque"] or {}
        out = {k: (m.get(k) or "").strip() for k in ("raison_sociale", "coordonnees", "mention")}
        out = {k: v for k, v in out.items() if v}   # M22-C4 : vide → absent
        if row["logo"]:
            out["logo_data_uri"] = (f"data:{row['logo_mime']};base64,"
                                    + base64.b64encode(row["logo"]).decode())
        return out or None
    except Exception:  # noqa: BLE001 — la marque ne casse jamais un export
        return None


def bloc_html(marque: dict | None) -> str:
    """Bloc « édité pour » de la page de garde des documents ABONNÉ — chaîne vide si
    rien de configuré. Toujours accompagné de la mention LABUSE (A3)."""
    if not marque:
        return ""
    from .api.briques_pdf import esc
    lignes = []
    if marque.get("logo_data_uri"):
        lignes.append(f"<img src='{marque['logo_data_uri']}' alt='' "
                      f"style='max-height:38px;max-width:150px;display:block'/>")
    if marque.get("raison_sociale"):
        lignes.append(f"<div style='font-weight:600'>{esc(marque['raison_sociale'])}</div>")
    if marque.get("coordonnees"):
        lignes.append(f"<div>{esc(marque['coordonnees'])}</div>")
    if marque.get("mention"):
        lignes.append(f"<div style='font-style:italic'>{esc(marque['mention'])}</div>")
    lignes.append(f"<div style='opacity:.65;margin-top:3px'>{MENTION_LABUSE}</div>")
    return ("<div class='marque-client' style='position:absolute;top:10mm;right:12mm;"
            "text-align:right;font-size:8pt;line-height:1.45;color:#333;max-width:62mm'>"
            + "".join(lignes) + "</div>")
