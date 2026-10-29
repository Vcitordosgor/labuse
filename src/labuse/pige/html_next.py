"""RADAR-HTML (Lot 1) — parseur du bloc `__NEXT_DATA__` d'une page de RÉSULTATS déposée (portail immobilier, structure Next.js).

Doctrine §2 INCHANGÉE : la collecte reste 100 % HUMAINE. AUCUN appel réseau ici — on parse un FICHIER
que Vic a enregistré lui-même (« page web complète », Cmd+S). Ce module remplace l'agent vision : la
page porte, en JSON structuré, tout ce que la capture d'écran jetait (voir docs/PIGE/MANDAT-PIGE-V0.md).

ÉCHEC BRUYANT (mandat) : `__NEXT_DATA__` absent, JSON illisible, chemin absent, `ads` non-liste ou VIDE
lèvent `NextDataError`. Le portail peut changer la structure sans prévenir — un parseur qui renvoie zéro
annonce EN SILENCE est le pire des cas ; on préfère un plantage visible à un faux « rien de neuf ».

RADAR-DEPOT-2 (D1/D2) — TROIS structures reconnues, un seul point d'entrée `analyser()` :
  · VARIANTE A (résultats) — `props.pageProps.searchData.ads` : données RICHES (chemin historique) ;
  · VARIANTE B (résultats) — le portail sert des pages par tests A/B (`libertyData.config.groupName`)
    où `searchData` est ABSENT : les annonces ne vivent plus que dans le DOM des vignettes. On en tire ce
    qui y est (url/list_id/titre/prix/commune/badges) et RIEN DE PLUS — l'enregistrement entre DÉGRADÉ
    (`provenance = dom_degrade`), sans position (donc jamais rattaché), et la date de vignette est une
    date de REMONTÉE (jamais « repéré le », jamais la nouveauté) ;
  · PAGE D'ANNONCE (D2) — `props.pageProps.ad` : une annonce seule, RICHE, qui ENRICHIT un bien connu
    (zone PLU déclarée, drapeaux). Les annonces « similaires » du même JSON sont IGNORÉES.
Aucune structure reconnue ⇒ échec bruyant qui NOMME les trois chemins cherchés (jamais « réseau »).
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata

from . import portails    # module d'affichage (SEUL à nommer un portail) — bâtit l'URL sortante
from .. import communes   # référentiel INSEE↔nom (pur, sans réseau) — résout la commune via l'INSEE

# Provenance des FAITS d'un bien (mandat D1) : rich = tout le JSON structuré ; degrade = DOM seul.
PROV_RICHE = "json_riche"
PROV_DEGRADE = "dom_degrade"

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
    # RATTACHEMENT-V2 — le nombre d'étages sert l'estimation d'emprise au sol (critère C2 : emprise ≈
    # surface habitable / étages). Rarement renseigné, mais gratuit à conserver.
    "nb_floors_house", "is_single_storey",
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
    subject = ad.get("subject") or ""
    return {
        "provenance": PROV_RICHE,                                # JSON structuré complet (variante A / page annonce)
        "list_id": ad.get("list_id"),
        "url": ad.get("url"),
        "subject": ad.get("subject"),
        # RATTACHEMENT-V2 (C6) — piscine : signal binaire très discriminant QUAND il s'applique. Le
        # portail ne porte pas d'attribut piscine dédié → on lit le mot dans le titre (rare, mesuré 0/38).
        "piscine": ("piscine" in subject.lower()),
        "prix": _num(prix),
        "prix_m2": _num(at.get("price_per_square_meter")),
        "type_code": ret or None,
        "type": _RET.get(ret),                                   # None si code non listé (conservé dans brut)
        "surface_hab": _num(at.get("square")),
        "surface_terrain": _num(at.get("land_plot_surface")),
        "pieces": _num(at.get("rooms")),
        "chambres": _num(at.get("bedrooms")),
        "etages": _num(at.get("nb_floors_house")) or (1 if str(at.get("is_single_storey")) == "1" else None),
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
    """energy_rate / ges du portail : 'n' = non renseigné, sinon lettre A–G. None si absent.
    Bien'ici utilise aussi 'NS' (non soumis) / 'VI' (vierge) → None (seule une lettre A–G passe)."""
    if not v or not isinstance(v, str):
        return None
    u = v.strip().upper()
    return u if u in set("ABCDEFG") else None


# ════════════ RADAR-SOURCES-2 · traducteur d'un portail servi en JSON (API realEstateAds) ════════════
# Bien'ici est une application Angular (SPA) : la page HTML est une coquille, les annonces arrivent par
# un appel JSON `realEstateAds.json`. L'extension (session RÉELLE de Vic, doctrine §2 inchangée) fait ce
# fetch même-origine et POSTE le JSON tel quel au serveur — exactement comme elle poste le HTML Leboncoin.
# Ce traducteur alimente le MÊME schéma plat que le traducteur Next.js : une donnée absente reste absente,
# aucun champ n'est deviné. La réponse porte `{total, from, perPage, realEstateAds:[…]}`. Le nom du
# portail ne vit QU'EN COMMENTAIRE et dans le module d'affichage `portails.py` (doctrine §2) : le code
# ci-dessous est neutre (`json_ads`), l'URL sortante est bâtie par `portails.lien_annonce_jsonads`.

# propertyType → notre vocabulaire. Seuls les types SÛRS sont mappés ; les autres (loft, castle,
# townhouse, parking, premises, programme…) donnent type=None (conservé dans `brut`, jamais rattaché) —
# on n'invente pas une correspondance non observée.
_JSON_ADS_TYPE = {"house": "maison", "flat": "appartement", "terrain": "terrain", "building": "immeuble"}

# Champs bruts conservés (contrat de structure : la réponse est réputée changée si AUCUN n'apparaît sur
# une annonce). Miroir du rôle de `_ATTRS` côté Next.js.
_JSON_ADS_ATTRS = (
    "reference", "propertyType", "adType", "transactionType", "price", "priceWithoutFees",
    "pricePerSquareMeter", "surfaceArea", "landSurfaceArea", "roomsQuantity", "bedroomsQuantity",
    "yearOfConstruction", "energyClassification", "greenhouseGazClassification", "accountType",
    "adCreatedByPro", "accountDisplayName", "customerId", "isInCondominium", "hasPool",
    "priceHasDecreased", "addressKnown",
)

# Au-delà de ce rayon de floutage (disque), la position n'est plus « à l'adresse » mais large (≈ commune) :
# le point ne tombe plus dans le rayon de rattachement (150 m) de façon fiable. Mesuré sur l'échantillon :
# 90 % des annonces floutées à 50 m, quelques-unes à 125 m, de rares à 500 m.
_JSON_ADS_RAYON_ADRESSE_M = 150

# Les list_id de ce portail sont des CHAÎNES (« immo-facile-61412190 ») ; la colonne
# `pige_annonces.list_id` est un bigint. On en dérive un entier STABLE (même chaîne → même id, donc
# idempotence) par un hachage 56 bits, et on force le bit 62 pour garantir que cet espace (> 4,6·10¹⁸)
# ne CROISE JAMAIS les list_id numériques Leboncoin (< ~10¹⁰) : aucune fausse collision « même annonce ».
# La chaîne réelle reste dans l'URL sortante (index unique) et dans `brut` pour la traçabilité.
_JSON_ADS_LIST_ID_BIT = 1 << 62


def _list_id_json_ads(id_str) -> int | None:
    if not id_str:
        return None
    h = int(hashlib.blake2b(str(id_str).encode("utf-8"), digest_size=7).hexdigest(), 16)
    return _JSON_ADS_LIST_ID_BIT | h


def _slug(s) -> str:
    """Segment d'URL lisible (sans accents, en minuscules) — jamais vide (défaut « bien »)."""
    t = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-").lower()
    return t or "bien"


def _url_json_ads(ad: dict, typ: str | None, id_str) -> str | None:
    """URL sortante canonique. Le JSON n'embarque PAS d'URL ; on la reconstruit via le module d'affichage
    (qui détient seul le préfixe du portail) sur le patron du site /annonce/vente/{ville}/{type}/{N}pieces/
    {id} — le dernier segment (l'id) résout l'annonce, les segments de tête sont cosmétiques/SEO."""
    if not id_str:
        return None
    tfr = typ if typ in ("maison", "appartement", "terrain", "immeuble") else "bien"
    pieces = ad.get("roomsQuantity")
    seg = f"{int(pieces)}pieces" if isinstance(pieces, (int, float)) and pieces else "bien"
    return portails.lien_annonce_jsonads(_slug(ad.get("city")), tfr, seg, str(id_str))


def aplatir_json_ads(ad: dict) -> dict:
    """Annonce brute d'un portail servi en JSON → enregistrement plat, typé, dans le MÊME schéma plat que
    le traducteur Next.js. Conserve tout ce qui est utile ; `brut` porte le sous-ensemble d'attributs
    tracés. Une donnée absente reste absente (jamais devinée). La commune est résolue via l'INSEE du
    quartier (le champ `city` peut être une LOCALITÉ qui n'est pas une des 24 communes officielles)."""
    ref_id = ad.get("id")
    if not any(k in ad for k in _JSON_ADS_ATTRS):
        raise NextDataError(f"annonce {ref_id} sans aucun attribut connu — structure du portail changée")
    pt = str(ad.get("propertyType") or "")
    typ = _JSON_ADS_TYPE.get(pt)
    blur = ad.get("blurInfo") or {}
    pos = blur.get("position") or blur.get("centroid") or {}
    rayon = _num(blur.get("radius"))
    addr_known = bool(ad.get("addressKnown"))
    # position « à l'adresse » seulement si l'adresse est connue ET le floutage est serré (≤150 m) ;
    # sinon « city » (large). On fournit TOUJOURS lat/lng : le rattachement s'appuie dessus, et une
    # position large ne convergera simplement pas (≥2 critères requis) — jamais un faux positif.
    source_position = "address" if (addr_known and rayon is not None and rayon <= _JSON_ADS_RAYON_ADRESSE_M) else "city"
    district = ad.get("district") or {}
    insee = district.get("code_insee") or district.get("insee_code")
    commune_officielle = communes.nom_officiel(insee) if insee else None
    commune = commune_officielle or ad.get("city")   # officielle d'abord ; sinon la ville brute (jugée hors-périmètre si inconnue)
    pro = ad.get("adCreatedByPro")
    statut = ad.get("status") or {}
    brut = {k: ad.get(k) for k in _JSON_ADS_ATTRS if ad.get(k) not in (None, "")}
    brut.update({"id": ref_id, "blur_radius_m": rayon, "code_insee": insee})
    return {
        "provenance": PROV_RICHE,                                # JSON structuré complet
        "list_id": _list_id_json_ads(ref_id),
        "url": _url_json_ads(ad, typ, ref_id),
        "subject": ad.get("title"),
        "piscine": bool(ad.get("hasPool")),                      # booléen DÉDIÉ (pas de titre deviné)
        "prix": _num(ad.get("price")),
        "prix_m2": _num(ad.get("pricePerSquareMeter")),
        "type_code": pt or None,
        "type": typ,                                             # None si type non listé (conservé dans brut)
        "surface_hab": _num(ad.get("surfaceArea")),
        "surface_terrain": _num(ad.get("landSurfaceArea")),
        "pieces": _num(ad.get("roomsQuantity")),
        "chambres": _num(ad.get("bedroomsQuantity")),
        "etages": None,                                          # Bien'ici ne porte pas le nombre d'étages
        "annee_construction": _num(ad.get("yearOfConstruction")),
        "etat_bien": None,                                       # pas d'équivalent global_condition chez Bien'ici
        "dpe_classe": _classe(ad.get("energyClassification")),   # 'NS'/'VI' → None
        "dpe_ges": _classe(ad.get("greenhouseGazClassification")),
        "taxe_fonciere": None,
        "chauffage": None,
        "commune": commune,
        "zipcode": (ad.get("postalCode") or district.get("postal_code")),
        "district": (district.get("libelle") or district.get("name")),
        "lat": _num(pos.get("lat")),
        "lng": _num(pos.get("lon")),
        "source_position": source_position,
        "owner_type": ("pro" if pro else "particulier" if pro is False else None),
        "owner_siren": None,                                     # Bien'ici ne publie pas de SIREN
        "first_publication_date": ad.get("publicationDate"),
        "index_date": ad.get("modificationDate"),
        "expiration_date": None,
        "statut_portail": ("active" if statut.get("onTheMarket") else ("inactive" if statut else None)),
        # Bien'ici porte un drapeau EXPLICITE « prix en baisse » → badge daté (comme la vignette Leboncoin).
        "baisse_badge": bool(ad.get("priceHasDecreased")),
        "brut": brut,
    }


def extraire_json_ads(contenu: str):
    """Reconnaît un dépôt JSON d'un portail-API (corps de `realEstateAds.json`) et retourne la liste des
    annonces BRUTES, ou None si ce n'est pas ce payload (→ l'appelant tente les chemins Next.js). Détection
    rapide et sûre : une page Next.js est du HTML (« < »), ce payload est un objet JSON (« { ») portant la
    clé `realEstateAds`."""
    s = (contenu or "").lstrip()
    if not s.startswith("{"):
        return None
    try:
        data = json.loads(contenu)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict) or "realEstateAds" not in data:
        return None
    ads = data.get("realEstateAds")
    if not isinstance(ads, list):
        raise NextDataError("`realEstateAds` n'est pas une liste — structure du portail changée")
    return ads


# ════════════════════════ D1 · VARIANTE B — extraction DOM des vignettes ════════════════════════
# Leboncoin sert par tests A/B des pages où `searchData` est absent : les 40 annonces ne vivent que
# dans le DOM des cartes (`<article>` … `href=".../ad/ventes_immobilieres/{id}"`). On en tire le peu
# qui y est, HONNÊTEMENT dégradé : ni position (pas de rattachement), ni date de première publication.

_VIGN_ART_RE = re.compile(r"<article\b.*?</article>", re.S)
_VIGN_ID_RE = re.compile(r"/ad/ventes_immobilieres/(\d+)")
_VIGN_URL_RE = re.compile(r'href="(https?://[^"]*?/ad/ventes_immobilieres/\d+[^"]*)"')
_VIGN_TITRE_RE = re.compile(r'title="Voir l[’\']annonce:\s*([^"]+)"')
_VIGN_PRIX_RE = re.compile(r"Prix:\s*([\d\s \xa0 ]+?)&nbsp;€")
# « Située à … » (bâti) OU la première ligne « Commune 97XXX Quartier » (terrain) : commune + CP + quartier.
_VIGN_LOC_RE = re.compile(r'aria-label="Situ[ée]+ à\s*([^"\.]+?)\.?"')
_VIGN_LOC2_RE = re.compile(r'([A-ZÉÈÀ][\wÀ-ÿ \'\-]+?\s\d{5}[^<"]*?)(?=<|"|\.|$)')
_VIGN_CP_RE = re.compile(r"^(.+?)\s+(\d{5})\b\s*(.*)$")
# titre : « Terrain · 585m² » | « Maison · 7 pièces · 179m² » | « Maison, 5 pièces, 104 mètres carrés. »
_TITRE_TYPE = {"terrain": "terrain", "maison": "maison", "appartement": "appartement",
               "immeuble": "immeuble"}
_TITRE_PIECES_RE = re.compile(r"(\d+)\s*pi[èe]ce", re.I)
_TITRE_SURF_RE = re.compile(r"(\d[\d\s \xa0]*)\s*(?:m²|m2|m\s*²|m[eè]tres?\s+carr[ée]s)", re.I)


def _int_fr(s) -> int | None:
    """Nombre depuis un texte de vignette : ne garde que les chiffres. '305 823' → 305823."""
    if s is None:
        return None
    ds = re.sub(r"[^\d]", "", str(s))
    return int(ds) if ds else None


def _titre_bits(titre: str) -> dict:
    """Décompose un titre de vignette en type / pièces / surface (habitable si bâti, terrain sinon).
    Ne DEVINE pas : un mot de type non listé donne type=None (jamais un mapping inventé)."""
    t = titre or ""
    low = t.lower()
    typ = next((v for k, v in _TITRE_TYPE.items() if k in low), None)
    mp = _TITRE_PIECES_RE.search(t)
    ms = _TITRE_SURF_RE.search(t)
    pieces = int(mp.group(1)) if mp else None
    surf = _int_fr(ms.group(1)) if ms else None
    return {"type": typ, "pieces": pieces, "surface": surf}


def _vignette(bloc: str) -> dict | None:
    """Une carte DOM → enregistrement DÉGRADÉ (même schéma qu'`aplatir`, la plupart des champs à None).
    None si la carte ne porte pas d'annonce exploitable (pas de list_id) — jamais une ligne vide."""
    mid = _VIGN_ID_RE.search(bloc)
    if not mid:
        return None
    list_id = int(mid.group(1))
    murl = _VIGN_URL_RE.search(bloc)
    mtitre = _VIGN_TITRE_RE.search(bloc)
    titre = mtitre.group(1).strip() if mtitre else None
    bits = _titre_bits(titre or "")
    typ = bits["type"]
    prix = _int_fr(_VIGN_PRIX_RE.search(bloc).group(1)) if _VIGN_PRIX_RE.search(bloc) else None
    # localisation : « Commune 97XXX Quartier » (jamais une position GPS — la vignette n'en porte pas).
    mloc = _VIGN_LOC_RE.search(bloc) or _VIGN_LOC2_RE.search(bloc)
    commune = zipcode = district = None
    if mloc:
        mcp = _VIGN_CP_RE.match(mloc.group(1).strip())
        if mcp:
            commune, zipcode, district = mcp.group(1).strip(), mcp.group(2), (mcp.group(3).strip() or None)
    pro = ("pro-store-name" in bloc) or ("Vendeur professionnel" in bloc)
    return {
        "provenance": PROV_DEGRADE,          # DOM seul — champs manquants assumés, jamais inventés
        "list_id": list_id,
        "url": murl.group(1) if murl else None,
        "subject": titre,
        "piscine": bool(titre and "piscine" in titre.lower()),
        "prix": prix,
        "prix_m2": None,
        "type_code": None,
        "type": typ,
        "surface_hab": (bits["surface"] if typ in ("maison", "appartement", "immeuble") else None),
        "surface_terrain": (bits["surface"] if typ == "terrain" else None),
        "pieces": bits["pieces"],
        "chambres": None,
        "etages": None,
        "annee_construction": None,
        "etat_bien": None,
        "dpe_classe": None,
        "dpe_ges": None,
        "taxe_fonciere": None,
        "chauffage": None,
        "commune": commune,
        "zipcode": zipcode,
        "district": district,
        "lat": None, "lng": None,            # PAS de position → non rattachée, aucune tentative (mandat D1)
        "source_position": None,
        "owner_type": ("pro" if pro else "particulier"),   # badge « Pro » — seul détail vendeur exploitable
        "owner_siren": None,
        # date de VIGNETTE = date de REMONTÉE (jamais first_publication) : on ne la garde PAS comme date
        # de vérité. Un bien vu seulement en B a pour première vue la date du dépôt (date_premiere_saisie).
        "first_publication_date": None,
        "index_date": None,
        "expiration_date": None,
        "statut_portail": None,
        "baisse_badge": ("Baisse de prix" in bloc),        # badge affiché — indice, jamais un historique
        "brut": {},
    }


def extraire_vignettes(html: str) -> list[dict]:
    """VARIANTE B — enregistrements DÉGRADÉS depuis le DOM des vignettes. Liste (éventuellement vide :
    le dispatcher décide si c'est un échec). N'exige PAS `__NEXT_DATA__` (la donnée est dans le DOM)."""
    out = []
    for m in _VIGN_ART_RE.finditer(html or ""):
        rec = _vignette(m.group(0))
        if rec is not None:
            out.append(rec)
    return out


# ════════════════════════ D2 · PAGE D'ANNONCE — faits déclarés (zone PLU, drapeaux) ════════════════════════
# La page d'une annonce seule porte un `body` (texte vendeur). Doctrine : on ne STOCKE ni n'AFFICHE ce
# texte — on en EXTRAIT des FAITS DÉCLARÉS (déclaratif vendeur, pas du calibré LABUSE). Le HTML brut
# part à l'archive privée comme les autres dépôts ; le body n'entre jamais en base.

# Zone PLU : « Zone UJ », « zone Um du plan local », « Zone PLU : UH », « zone UBc », « zone UD ». Large
# sur les formulations, mais le code doit RESSEMBLER à une zone (U/A/N + suffixe court) — on refuse
# « zone urbaine / recherchée / de la Mare » (mots courants) via la borne de mot après un code court.
_ZONE_RE = re.compile(
    r"\bzones?\s+(?:PLU\s*:?\s*|du\s+PLU\s*:?\s*)?"
    r"([0-9]{0,2}(?:AU|U|A|N)[A-Za-z]{0,2}[0-9]?)\b")
_COS_RE = re.compile(r"\b(COS|CES|coefficient d[’']?(?:occupation|emprise))\b[^\d%]{0,20}?"
                     r"([0-9]+(?:[.,][0-9]+)?)\s*%?", re.I)
_EMPRISE_RE = re.compile(r"emprise au sol[^\d%]{0,20}?([0-9]+(?:[.,][0-9]+)?)\s*%", re.I)
_LOTI_NOM_RE = re.compile(r"lotissement\s+(?:«\s*|\"|dit\s+|nomm[ée]\s+)?([A-ZÉÈÀ][\wÀ-ÿ '\-]{2,40}?)"
                          r"(?=\s*[»\".,;:\n]|\s+(?:à|de|sur|situé|pour)\b)", re.I)


def _zones_plu(body: str) -> list[str]:
    """Codes de zone PLU cités dans le texte, dédoublonnés, dans l'ordre d'apparition (jamais inventés :
    un « zone urbaine » sans code ne produit rien)."""
    vus: list[str] = []
    for m in _ZONE_RE.finditer(body or ""):
        z = m.group(1)
        # écarte les faux positifs de mot courant : un code de zone est court (≤ 4) et pas « tout minuscule »
        if len(z) > 4 or z.islower():
            continue
        if z not in vus:
            vus.append(z)
    return vus


def _drapeau(body: str, motifs: str) -> bool:
    return re.search(motifs, body or "", re.I) is not None


def extraire_faits_declares(body: str) -> dict:
    """Faits DÉCLARÉS par le vendeur dans le corps de l'annonce (D2). Aucun texte conservé — que des
    faits : zone(s) PLU, COS/CES, emprise au sol %, et des drapeaux booléens. Rendu tel quel, étiqueté
    « déclaré dans l'annonce » à l'affichage (déclaratif, jamais du calibré LABUSE)."""
    b = body or ""
    zones = _zones_plu(b)
    mcos = _COS_RE.search(b)
    memp = _EMPRISE_RE.search(b)
    mloti = _LOTI_NOM_RE.search(b)
    lotissement = _drapeau(b, r"\blotissement\b")
    return {
        "zone_plu": zones,
        "cos_ces": ({"type": mcos.group(1).upper()[:3], "valeur": mcos.group(2).replace(",", ".")}
                    if mcos else None),
        "emprise_sol_pct": (float(memp.group(1).replace(",", ".")) if memp else None),
        "drapeaux": {
            "a_renover": _drapeau(b, r"à\s+r[ée]nover|\brénovation\b|\brenover\b"),
            "a_demolir": _drapeau(b, r"à\s+d[ée]molir|\bd[ée]molir\b|\bd[ée]molition\b"),
            "succession": _drapeau(b, r"\bsuccession\b"),
            "lotissement": lotissement,
            "lotissement_nom": (mloti.group(1).strip() if (lotissement and mloti) else None),
            "viabilise": _drapeau(b, r"viabilis[ée]e?s?\b"),
        },
    }


def extraire_page_annonce(html: str) -> dict | None:
    """PAGE D'ANNONCE (D2) — `props.pageProps.ad` UNIQUEMENT (les « similaires » du JSON sont ignorés).
    Retourne {rec: enregistrement aplati RICHE, declaratif: faits déclarés} ou None si pas une page
    d'annonce (pas de `ad`). L'`ad` a la même structure qu'une annonce de résultats → `aplatir` la traite."""
    data = extraire_next_data(html)
    node = data
    for cle in ("props", "pageProps"):
        if not isinstance(node, dict) or cle not in node:
            return None
        node = node[cle]
    ad = node.get("ad")
    if not isinstance(ad, dict) or not ad.get("list_id"):
        return None
    rec = aplatir(ad)
    rec["declaratif"] = extraire_faits_declares(ad.get("body") or "")
    return {"rec": rec, "declaratif": rec["declaratif"]}


# ════════════════════════ DISPATCHER — un seul point d'entrée pour le dépôt ════════════════════════

def analyser(html: str) -> dict:
    """Reconnaît la structure du fichier déposé et rend des enregistrements APLATIS prêts à l'ingestion.

    Retour : {"mode": "resultats"|"annonce", "provenance": PROV_*, "records": [rec, …]}.
    Ordre de détection (une page d'annonce porte aussi des vignettes « similaires » dans son DOM — la
    page d'annonce est donc testée AVANT les vignettes, sinon on ingérerait les similaires) :
      1. `searchData.ads` (variante A) ;
      2. `pageProps.ad` (page d'annonce, D2) ;
      3. vignettes DOM (variante B) ;
      4. sinon échec bruyant NOMMANT les trois chemins.
    RADAR-SOURCES-2 — un dépôt JSON d'un portail-API (corps de `realEstateAds.json`) est reconnu AVANT
    tout : ce n'est pas du HTML Next.js, le traducteur `aplatir_json_ads` l'alimente dans le même schéma.
    """
    ads_json = extraire_json_ads(html)
    if ads_json is not None:
        if not ads_json:
            raise NextDataError("0 annonce dans le JSON déposé — refus silencieux évité : page vide, "
                                "filtre trop restrictif, ou structure du portail changée (à vérifier à la main)")
        return {"mode": "resultats", "provenance": PROV_RICHE, "records": [aplatir_json_ads(a) for a in ads_json]}

    data = extraire_next_data(html)                     # lève NextDataError si __NEXT_DATA__ absent/illisible
    pp = data
    for cle in ("props", "pageProps"):
        pp = pp.get(cle) if isinstance(pp, dict) else None
    pp = pp if isinstance(pp, dict) else {}

    sd = pp.get("searchData")
    if isinstance(sd, dict) and "ads" in sd:
        ads = sd.get("ads")
        if not isinstance(ads, list):
            raise NextDataError("props.pageProps.searchData.ads n'est pas une liste — structure changée")
        if not ads:
            raise NextDataError("0 annonce dans __NEXT_DATA__ [variante A] — refus silencieux évité : page "
                                "vide, filtre trop restrictif, ou structure changée (à vérifier à la main)")
        return {"mode": "resultats", "provenance": PROV_RICHE, "records": [aplatir(a) for a in ads]}

    page = extraire_page_annonce(html)
    if page is not None:
        return {"mode": "annonce", "provenance": PROV_RICHE, "records": [page["rec"]]}

    vignettes = extraire_vignettes(html)
    if vignettes:
        return {"mode": "resultats", "provenance": PROV_DEGRADE, "records": vignettes}

    raise NextDataError(
        "aucune structure d'annonce reconnue : ni searchData [variante A], ni page d'annonce "
        "[props.pageProps.ad], ni vignettes DOM [variante B] — structure du portail changée, ou "
        "fichier incomplet (enregistrer en « page web complète », pas « page web seulement »)")
