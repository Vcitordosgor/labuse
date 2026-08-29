"""RADAR-HTML (Lot 1) — parseur du bloc `__NEXT_DATA__` d'une page de RÉSULTATS déposée (portail immobilier, structure Next.js).

Doctrine §2 INCHANGÉE : la collecte reste 100 % HUMAINE. AUCUN appel réseau ici — on parse un FICHIER
que Vic a enregistré lui-même (« page web complète », Cmd+S). Ce module remplace l'agent vision : la
page porte, en JSON structuré, tout ce que la capture d'écran jetait (voir docs/PIGE/MANDAT-PIGE-V0.md).

ÉCHEC BRUYANT (mandat) : `__NEXT_DATA__` absent, JSON illisible, chemin absent, `ads` non-liste ou VIDE
lèvent `NextDataError`. Le portail peut changer la structure sans prévenir — un parseur qui renvoie zéro
annonce EN SILENCE est le pire des cas ; on préfère un plantage visible à un faux « rien de neuf ».
"""
from __future__ import annotations

import json
import re

# real_estate_type Leboncoin → notre vocabulaire. Seuls les codes VUS dans l'échantillon de référence
# sont mappés (1/2/3) ; tout autre code donne type=None (conservé dans `brut`, jamais rattaché) plutôt
# qu'un mapping deviné — on n'invente pas une correspondance non observée (immeuble/parking/autre).
_RET = {"1": "maison", "2": "appartement", "3": "terrain"}

# Champs d'attribut conservés (mandat Lot 1 : « tous les champs, y compris ceux dont on ne se sert pas
# encore »). La liste sert de contrat : la structure Leboncoin est réputée changée si aucun n'apparaît.
_ATTRS = (
    "real_estate_type", "square", "land_plot_surface", "rooms", "bedrooms", "building_year",
    "global_condition", "energy_rate", "ges", "price_per_square_meter", "property_tax",
    "estimated_notary_fees", "immo_sell_type", "street_view_url", "heating_mode",
    "real_estate_type_specificities", "orientation",
)

_SCRIPT_RE = re.compile(r'<script[^>]*\bid="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


class NextDataError(RuntimeError):
    """Le bloc `__NEXT_DATA__` est absent ou sa structure a changé — on refuse de deviner."""


def _num(v):
    """Nombre robuste : '265' → 265, '' → None, '3 243' → 3243. None si non convertible."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return v
    s = str(v).replace(" ", "").replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        f = float(s)
        return int(f) if f.is_integer() else f
    except ValueError:
        return None


def extraire_next_data(html: str) -> dict:
    """HTML complet → l'objet `__NEXT_DATA__` (dict). Lève NextDataError si absent/illisible."""
    if not html or "__NEXT_DATA__" not in html:
        raise NextDataError("__NEXT_DATA__ absent du fichier — page incomplète, tronquée, ou format inattendu "
                            "(enregistrer la page en « page web complète », pas « page web seulement »)")
    m = _SCRIPT_RE.search(html)
    if not m:
        raise NextDataError("balise <script id=\"__NEXT_DATA__\"> introuvable — structure du portail changée ?")
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError as exc:
        raise NextDataError(f"__NEXT_DATA__ présent mais JSON illisible ({exc}) — fichier tronqué ?") from exc


def extraire_annonces(html: str) -> list[dict]:
    """HTML → liste des annonces BRUTES (dicts du portail). Chemin exact ; toute déviation = NextDataError.

    Une liste VIDE lève aussi : une page de résultats déposée par un humain porte des annonces ; un zéro
    silencieux trahirait un changement de structure, pas une vraie absence."""
    data = extraire_next_data(html)
    node = data
    for cle in ("props", "pageProps", "searchData"):
        if not isinstance(node, dict) or cle not in node:
            raise NextDataError(f"chemin __NEXT_DATA__ rompu à « {cle} » — structure du portail changée")
        node = node[cle]
    ads = node.get("ads")
    if not isinstance(ads, list):
        raise NextDataError("props.pageProps.searchData.ads n'est pas une liste — structure changée")
    if not ads:
        raise NextDataError("0 annonce dans __NEXT_DATA__ — refus silencieux évité : page vide, "
                            "filtre trop restrictif, ou structure changée (à vérifier à la main)")
    return ads


def aplatir(ad: dict) -> dict:
    """Annonce brute du portail → enregistrement plat, typé, prêt pour l'ingestion. Conserve TOUT
    (y compris les champs inexploités) ; `brut` porte le sous-ensemble d'attributs pour la traçabilité."""
    loc = ad.get("location") or {}
    owner = ad.get("owner") or {}
    at = {a.get("key"): a.get("value") for a in (ad.get("attributes") or []) if isinstance(a, dict)}
    if not any(k in at for k in _ATTRS):
        raise NextDataError(f"annonce {ad.get('list_id')} sans aucun attribut connu — structure changée")
    ret = str(at.get("real_estate_type") or "")
    prix = ad.get("price")
    if isinstance(prix, list):
        prix = prix[0] if prix else None
    brut = {k: at.get(k) for k in _ATTRS if at.get(k) not in (None, "")}
    return {
        "list_id": ad.get("list_id"),
        "url": ad.get("url"),
        "subject": ad.get("subject"),
        "prix": _num(prix),
        "prix_m2": _num(at.get("price_per_square_meter")),
        "type_code": ret or None,
        "type": _RET.get(ret),                                   # None si code non listé (conservé dans brut)
        "surface_hab": _num(at.get("square")),
        "surface_terrain": _num(at.get("land_plot_surface")),
        "pieces": _num(at.get("rooms")),
        "chambres": _num(at.get("bedrooms")),
        "annee_construction": _num(at.get("building_year")),
        "etat_bien": (str(at.get("global_condition")) if at.get("global_condition") not in (None, "") else None),
        "dpe_classe": _classe(at.get("energy_rate")),
        "dpe_ges": _classe(at.get("ges")),
        "taxe_fonciere": _num(at.get("property_tax")),
        "chauffage": (at.get("heating_mode") or None),
        "commune": loc.get("city"),
        "zipcode": loc.get("zipcode"),
        "district": loc.get("district"),
        "lat": loc.get("lat"),
        "lng": loc.get("lng"),
        "source_position": loc.get("source"),                   # address | city — précision de la position
        "owner_type": ("pro" if owner.get("type") == "pro" else "particulier" if owner.get("type") == "private" else None),
        "owner_siren": owner.get("siren"),
        "first_publication_date": ad.get("first_publication_date"),
        "index_date": ad.get("index_date"),
        "expiration_date": ad.get("expiration_date"),
        "statut_portail": ad.get("status"),
        "brut": brut,
    }


def _classe(v) -> str | None:
    """energy_rate / ges du portail : 'n' = non renseigné, sinon lettre A–G. None si absent."""
    if not v or not isinstance(v, str):
        return None
    u = v.strip().upper()
    return u if u in set("ABCDEFG") else None
