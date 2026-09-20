"""Destinations et sous-destinations par zone de PLU — MODULE UNIQUE (DESTINATIONS-1).

Doctrine : une valeur servie est LUE dans le règlement, article et page cités, ou
n'est pas servie. Une commune non calibrée affiche « destination non calibrée sur
cette commune » — jamais un silence, jamais un verdict déduit de la lettre de la zone.

Référentiel : art. R151-27 et R151-28 du code de l'urbanisme, version en vigueur
depuis le 01/07/2023 (décret n° 2023-195 du 22/03/2023) : 5 destinations et
23 sous-destinations. NB mandat : le mandat en annonçait 21 (état pré-2023) ;
la version en vigueur, qui fait foi, en compte 23 (« lieux de culte » et
« cuisine dédiée à la vente en ligne » ajoutées, destination 5 renommée
« … secteurs primaire, secondaire ou tertiaire »).

Calibration : un YAML par commune sous `config/plu_destinations/<insee>_<slug>.yaml`
(même famille que `config/plu_<slug>.yaml` de la constructibilité) + `rnu.yaml`
pour les communes au RNU (Saint-Philippe). Ce module RELAIE le YAML tel quel :
aucune valeur fabriquée, les marqueurs `non_mentionne` / `non_lu` sont propagés.

Statuts d'une (zone, sous-destination) :
  · autorise       — le règlement l'autorise (article/page cités) ;
  · interdit       — le règlement l'interdit (article/page cités) ;
  · sous_condition — autorisée sous condition (condition en clair + seuil éventuel) ;
  · non_mentionne  — le règlement ne la cite pas ; le verdict EFFECTIF découle de la
                     règle de silence de la zone (`silence: autorise|interdit`, elle-même
                     lue dans la structure du règlement et citée) ;
  · non_lu         — pas encore lu (calibration partielle) — distinct de non_mentionne.

Verrou CDAC (X3.1, statique) : au-delà de 1 000 m² de surface de vente, autorisation
d'exploitation commerciale obligatoire — art. L752-1 du code de commerce. Relayé sur
les sous-destinations de commerce dès qu'un seuil autorisé dépasse (ou ne borne pas)
ce plafond.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import yaml

_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
_DEST_DIR = _CONFIG_DIR / "plu_destinations"

# ---------------------------------------------------------------------------
# Référentiel R151-27 / R151-28 (version en vigueur au 01/07/2023)
# ---------------------------------------------------------------------------

REF_SOURCE = ("art. R151-27 et R151-28 du code de l'urbanisme, version en vigueur "
              "depuis le 01/07/2023 (décret n° 2023-195 du 22/03/2023)")

DESTINATIONS: dict[str, str] = {
    "exploitation_agricole_forestiere": "Exploitation agricole et forestière",
    "habitation": "Habitation",
    "commerce_activites_service": "Commerce et activités de service",
    "equipements_interet_collectif": "Équipements d'intérêt collectif et services publics",
    "autres_activites": "Autres activités des secteurs primaire, secondaire ou tertiaire",
}

# slug -> (destination parente, libellé officiel R151-28)
SOUS_DESTINATIONS: dict[str, tuple[str, str]] = {
    "exploitation_agricole": ("exploitation_agricole_forestiere", "Exploitation agricole"),
    "exploitation_forestiere": ("exploitation_agricole_forestiere", "Exploitation forestière"),
    "logement": ("habitation", "Logement"),
    "hebergement": ("habitation", "Hébergement"),
    "artisanat_commerce_detail": ("commerce_activites_service", "Artisanat et commerce de détail"),
    "restauration": ("commerce_activites_service", "Restauration"),
    "commerce_gros": ("commerce_activites_service", "Commerce de gros"),
    "activites_services_clientele": ("commerce_activites_service",
                                     "Activités de services où s'effectue l'accueil d'une clientèle"),
    "cinema": ("commerce_activites_service", "Cinéma"),
    "hotels": ("commerce_activites_service", "Hôtels"),
    "autres_hebergements_touristiques": ("commerce_activites_service", "Autres hébergements touristiques"),
    "locaux_bureaux_administrations": ("equipements_interet_collectif",
                                       "Locaux et bureaux accueillant du public des administrations "
                                       "publiques et assimilés"),
    "locaux_techniques_administrations": ("equipements_interet_collectif",
                                          "Locaux techniques et industriels des administrations "
                                          "publiques et assimilés"),
    "enseignement_sante_action_sociale": ("equipements_interet_collectif",
                                          "Établissements d'enseignement, de santé et d'action sociale"),
    "salles_art_spectacles": ("equipements_interet_collectif", "Salles d'art et de spectacles"),
    "equipements_sportifs": ("equipements_interet_collectif", "Équipements sportifs"),
    "lieux_culte": ("equipements_interet_collectif", "Lieux de culte"),
    "autres_equipements_public": ("equipements_interet_collectif", "Autres équipements recevant du public"),
    "industrie": ("autres_activites", "Industrie"),
    "entrepot": ("autres_activites", "Entrepôt"),
    "bureau": ("autres_activites", "Bureau"),
    "centre_congres_exposition": ("autres_activites", "Centre de congrès et d'exposition"),
    "cuisine_vente_en_ligne": ("autres_activites", "Cuisine dédiée à la vente en ligne"),
}

STATUTS = ("autorise", "interdit", "sous_condition", "non_mentionne", "non_lu")

# X3.1 — verrou CDAC, règle STATIQUE nationale (pas une lecture de PLU).
CDAC_SEUIL_M2 = 1000
CDAC_SOURCE = ("art. L752-1 du code de commerce : autorisation d'exploitation commerciale "
               "obligatoire au-delà de 1 000 m² de surface de vente")
# Sous-destinations où la surface de vente a un sens (champ de la CDAC).
_CDAC_SOUS_DESTINATIONS = {"artisanat_commerce_detail"}

# ---------------------------------------------------------------------------
# Chargement des calibrations (YAML par commune)
# ---------------------------------------------------------------------------


def _slug(commune: str) -> str:
    """« Saint-Denis » → « saint_denis » (même convention que zonage)."""
    s = unicodedata.normalize("NFKD", commune).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()


@lru_cache(maxsize=None)
def _load_yaml(path_str: str) -> dict:
    return yaml.safe_load(Path(path_str).read_text(encoding="utf-8")) or {}


def _fichier_commune(commune: str) -> Path | None:
    """YAML destinations de la commune (par slug ou par insee), None si non calibrée."""
    if not commune:
        return None
    if re.fullmatch(r"974\d\d", commune.strip()):
        hits = sorted(_DEST_DIR.glob(f"{commune.strip()}_*.yaml"))
        return hits[0] if hits else None
    slug = _slug(commune)
    hits = sorted(_DEST_DIR.glob(f"974??_{slug}.yaml"))
    return hits[0] if hits else None


def _doc(commune: str) -> dict | None:
    p = _fichier_commune(commune)
    return _load_yaml(str(p)) if p else None


def reglement_meta(commune: str) -> dict | None:
    """Métadonnée `meta` du règlement de la commune (document, url, millésime, édition), ou None si
    non calibrée. Point d'accès PUBLIC pour que les surfaces (fiche règlement) ne lisent jamais le
    dossier de calibration directement."""
    doc = _doc(commune)
    return (doc.get("meta") or {}) if doc else None


def _millesimes() -> dict:
    """Catalogue des millésimes PLU servis (config/plu_millesimes.yaml)."""
    p = _CONFIG_DIR / "plu_millesimes.yaml"
    return (_load_yaml(str(p)) or {}).get("communes", {}) if p.is_file() else {}


def _rnu_doc() -> dict:
    p = _DEST_DIR / "rnu.yaml"
    return _load_yaml(str(p)) if p.is_file() else {}


def scot_daac(commune: str) -> dict | None:
    """X3.2 — « secteur préférentiel du SCoT : oui / non / non localisé » par commune
    (config/plu_destinations/scot_daac.yaml — extraction PDF citée, aucune géométrie
    ZACOM publiée à La Réunion au 03/09/2026). None si le fichier n'existe pas."""
    p = _DEST_DIR / "scot_daac.yaml"
    if not p.is_file():
        return None
    doc = _load_yaml(str(p))
    communes = doc.get("communes") or {}
    entry = None
    if re.fullmatch(r"974\d\d", (commune or "").strip()):
        entry = communes.get(commune.strip())
    else:
        for _insee, c in communes.items():
            if _slug(c.get("commune", "")) == _slug(commune or ""):
                entry = c
                break
    if entry is None:
        return None
    scot = (doc.get("scots") or {}).get(entry.get("scot")) or {}
    lib = {"oui": "oui", "non": "non", "non_localise": "non localisé"}.get(entry.get("verdict"),
                                                                          entry.get("verdict"))
    return {"verdict": entry.get("verdict"), "libelle": lib, "scot": entry.get("scot"),
            "secteurs": entry.get("secteurs") or [], "note": entry.get("note") or scot.get("note"),
            "daac": scot.get("daac"), "document": scot.get("document"), "url": scot.get("url")}


# ---------------------------------------------------------------------------
# États de calibration (X5.2 / X5.3)
# ---------------------------------------------------------------------------


def etat_commune(commune: str) -> dict:
    """État de calibration destinations d'une commune :
      calibree (millésime lu == millésime servi) · a_relire (nouvelle version de PLU
      servie depuis la lecture) · rnu (calibrée sur le RNU) · non_calibree.
    """
    doc = _doc(commune)
    mills = _millesimes()
    insee = (doc or {}).get("meta", {}).get("insee")
    if not insee and re.fullmatch(r"974\d\d", (commune or "").strip()):
        insee = commune.strip()
    cat = None
    if insee:
        cat = mills.get(insee)
    else:
        for code, c in mills.items():
            if _slug(c.get("commune", "")) == _slug(commune):
                insee, cat = code, c
                break
    if doc is None:
        if cat and cat.get("statut") == "rnu":
            rnu = _rnu_doc()
            if rnu:
                return {"etat": "rnu", "insee": insee, "commune": cat.get("commune"),
                        "millesime": None, "lu_le": rnu.get("meta", {}).get("lu_le"),
                        "document": rnu.get("meta", {}).get("source")}
        return {"etat": "non_calibree", "insee": insee,
                "commune": (cat or {}).get("commune") or commune,
                "millesime": None, "lu_le": None, "document": None}
    meta = doc.get("meta", {})
    etat = "calibree"
    # X5.2 — une nouvelle version de PLU servie (idurba du catalogue ≠ document lu) passe
    # la commune « à relire ». Comparaison sur le nom de document GPU gravé au calibrage ;
    # le sens compte : « à relire » SEULEMENT si le servi est plus récent que le lu (une
    # calibration lue sur un document GPU plus frais que le catalogue n'est pas périmée —
    # c'est le catalogue qui est en retard, dit tel quel).
    idurba_servi = (cat or {}).get("idurba")
    idurba_lu = meta.get("document_gpu")
    note_catalogue = None
    if idurba_servi and idurba_lu and idurba_servi.lower() != idurba_lu.lower():
        d_servi = re.search(r"(\d{8})", idurba_servi)
        d_lu = re.search(r"(\d{8})", idurba_lu)
        if d_servi and d_lu and d_servi.group(1) <= d_lu.group(1):
            note_catalogue = (f"catalogue millésimes en retard ({idurba_servi}) sur le document "
                              f"GPU lu ({idurba_lu})")
        else:
            etat = "a_relire"
    return {"etat": etat, "insee": meta.get("insee") or insee,
            "commune": meta.get("commune") or commune,
            "millesime": meta.get("millesime"), "lu_le": meta.get("lu_le"),
            "document": meta.get("document"), "url": meta.get("url"),
            "document_gpu": idurba_lu, "document_gpu_servi": idurba_servi,
            "note": note_catalogue,
            "zones": sorted((doc.get("zones") or {}).keys())}


def etats_ile() -> list[dict]:
    """Tableau commune × état pour la page admin (X5.3), les 24 communes du catalogue."""
    out = []
    for insee, cat in sorted(_millesimes().items()):
        e = etat_commune(insee)
        e["insee"], e["commune"] = insee, cat.get("commune")
        out.append(e)
    return out


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------


def _norm_zone(code: str) -> str:
    from ..faisabilite.zone_norm import normalize_key
    return normalize_key(code)


def _zone_entry(doc: dict, zone: str) -> tuple[str | None, dict | None]:
    """Entrée de zone du YAML, résolue par clé normalisée ou par renvoi explicite
    (`renvoi: <ZONE>` — le règlement le dit, on ne déduit pas)."""
    zones = doc.get("zones") or {}
    norm = {_norm_zone(z): z for z in zones}
    hit = norm.get(_norm_zone(zone))
    if hit is None:
        return None, None
    v = zones[hit]
    seen = {hit}
    while isinstance(v, dict) and v.get("renvoi"):
        cible = norm.get(_norm_zone(v["renvoi"]))
        if cible is None or cible in seen:
            break
        seen.add(cible)
        hit2 = cible
        v2 = dict(zones[hit2])
        # le renvoi conserve sa propre citation en note
        v2.setdefault("_via_renvoi", f"{hit} → règles de {hit2} ({v.get('renvoi_src', 'renvoi du règlement')})")
        v = v2
    return hit, v


def _cdac(sous_destination: str, statut: str, seuil_m2, seuil_type) -> dict | None:
    """Surcouche CDAC : dite dès que la sous-destination relève de la surface de vente
    et que le régime autorisé peut dépasser 1 000 m²."""
    if sous_destination not in _CDAC_SOUS_DESTINATIONS or statut == "interdit":
        return None
    depasse = (seuil_m2 is None) or (
        isinstance(seuil_m2, (int, float)) and float(seuil_m2) > CDAC_SEUIL_M2
        and (seuil_type in (None, "surface_vente")))
    if statut in ("autorise", "sous_condition", "non_mentionne") and depasse:
        return {"seuil_m2": CDAC_SEUIL_M2, "mention": "soumis à CDAC au-delà de 1 000 m² de surface de vente",
                "source": CDAC_SOURCE}
    return None


def verdict(commune: str, zone: str, sous_destination: str) -> dict:
    """Verdict pour (commune, zone, sous-destination) — LE point de lecture unique.

    Retourne {etat_calibration, statut, statut_effectif, condition, seuil_m2, seuil_type,
    article, page_pdf, citation, millesime, lu_le, silence, cdac, phrase}.
    `statut_effectif` résout `non_mentionne` par la règle de silence de la zone (citée).
    """
    if sous_destination not in SOUS_DESTINATIONS:
        raise ValueError(f"sous-destination inconnue : {sous_destination!r}")
    ec = etat_commune(commune)
    lib = SOUS_DESTINATIONS[sous_destination][1]
    base = {"commune": ec.get("commune") or commune, "zone": zone,
            "sous_destination": sous_destination, "libelle": lib,
            "etat_calibration": ec["etat"], "millesime": ec.get("millesime"),
            "lu_le": ec.get("lu_le"), "document": ec.get("document")}
    if ec["etat"] == "non_calibree":
        return {**base, "statut": None, "statut_effectif": None,
                "phrase": "destination non calibrée sur cette commune"}
    if ec["etat"] == "rnu":
        doc = _rnu_doc()
        entry = (doc.get("sous_destinations") or {}).get(sous_destination) or {}
        return _fabrique_verdict(base, entry, doc.get("silence") or {}, rnu=True)
    doc = _doc(commune) or {}
    zone_hit, zv = _zone_entry(doc, zone)
    if zv is None:
        return {**base, "statut": "non_lu", "statut_effectif": "non_lu",
                "phrase": f"zone {zone} non lue — calibration en cours sur cette commune"}
    base["zone"] = zone_hit
    if zv.get("_via_renvoi"):
        base["via_renvoi"] = zv["_via_renvoi"]
    entry = (zv.get("sous_destinations") or {}).get(sous_destination)
    silence = {"regle": zv.get("silence"), "source": zv.get("silence_src")}
    if entry is None:
        entry = {"statut": "non_lu" if zv.get("etat") == "non_lu" else "non_mentionne"}
    return _fabrique_verdict(base, entry, silence)


def _fabrique_verdict(base: dict, entry: dict, silence: dict, rnu: bool = False) -> dict:
    statut = entry.get("statut") or "non_lu"
    effectif = statut
    if statut == "non_mentionne":
        effectif = silence.get("regle") or "non_lu"
    seuil = entry.get("seuil_m2")
    cdac = _cdac(base["sous_destination"], effectif, seuil, entry.get("seuil_type"))
    out = {**base, "statut": statut, "statut_effectif": effectif,
           "condition": entry.get("condition"), "seuil_m2": seuil,
           "seuil_type": entry.get("seuil_type"),
           "article": entry.get("article"), "page_pdf": entry.get("page_pdf"),
           "citation": entry.get("citation"), "silence": silence if statut == "non_mentionne" else None,
           "cdac": cdac, "rnu": rnu}
    out["phrase"] = _phrase(out)
    return out


def _phrase(v: dict) -> str:
    """Phrase servie (X4.1/X4.4) — même moteur, même phrase sur toutes les surfaces."""
    lib = v["libelle"]
    ref = " — ".join(x for x in (
        f"zone {v['zone']}" if v.get("zone") else None,
        f"art. {v['article']}" if v.get("article") else None,
        f"p. {v['page_pdf']} (PDF)" if v.get("page_pdf") else None,
        f"PLU millésime {v['millesime']}" if v.get("millesime") else ("RNU" if v.get("rnu") else None),
    ) if x)
    eff = v.get("statut_effectif")
    if eff == "non_lu":
        return f"{lib} : calibration en cours sur cette zone"
    if v.get("statut") == "non_mentionne":
        sil = v.get("silence") or {}
        tete = ("autorisée (non mentionnée — silence de la zone : autorisé)" if eff == "autorise"
                else "interdite (non mentionnée — silence de la zone : interdit)")
        ref2 = sil.get("source") or ref
        out = f"{lib} : {tete} — {ref2}"
    elif eff == "interdit":
        out = f"{lib} : interdit — {ref}"
    elif eff == "sous_condition":
        cond = v.get("condition") or "sous condition"
        out = f"{lib} : {cond} — {ref}"
    else:
        out = f"{lib} : autorisé — {ref}"
    if v.get("cdac"):
        out += " · au-delà de 1 000 m² de surface de vente : soumis à CDAC (L752-1 c. commerce)"
    return out


def zone_destinations(commune: str, zone: str) -> dict:
    """Table complète des 23 sous-destinations pour une zone (fiche parcelle, X4.2)."""
    ec = etat_commune(commune)
    lignes = [verdict(commune, zone, sd) for sd in SOUS_DESTINATIONS]
    return {"commune": ec.get("commune") or commune, "zone": zone,
            "etat_calibration": ec["etat"], "millesime": ec.get("millesime"),
            "document": ec.get("document"), "url": ec.get("url"),
            "lignes": lignes,
            "referentiel": REF_SOURCE}


def zone_resume(commune: str, zone: str) -> dict:
    """Résumé d'une zone pour la ligne « Destinations » de la fiche (X4.2) : principales
    autorisées / interdites / sous condition + seuil commerce, dépliable via `lignes`."""
    t = zone_destinations(commune, zone)
    if t["etat_calibration"] == "non_calibree":
        return {"etat_calibration": "non_calibree", "zone": zone,
                "phrase": "destination non calibrée sur cette commune"}
    lignes = t["lignes"]
    if all(l.get("statut_effectif") == "non_lu" for l in lignes):
        return {"etat_calibration": t["etat_calibration"], "zone": zone,
                "millesime": t.get("millesime"),
                "phrase": f"zone {zone} non lue — calibration en cours sur cette commune"}
    grp = {"autorise": [], "interdit": [], "sous_condition": []}
    for l in lignes:
        eff = l.get("statut_effectif")
        if eff in grp:
            grp[eff].append(l["libelle"])
    commerce = next(l for l in lignes if l["sous_destination"] == "artisanat_commerce_detail")
    return {"etat_calibration": t["etat_calibration"], "zone": t["zone"],
            "millesime": t.get("millesime"), "document": t.get("document"), "url": t.get("url"),
            "autorisees": grp["autorise"], "interdites": grp["interdit"],
            "sous_conditions": grp["sous_condition"],
            "seuil_commerce_m2": commerce.get("seuil_m2"),
            "seuil_commerce_type": commerce.get("seuil_type"),
            "commerce_cdac": commerce.get("cdac"),
            "lignes": lignes, "referentiel": t["referentiel"]}


def verdicts_zones_etude(zones: list[dict], sous_destination: str) -> dict:
    """X4.1 — chalandise : verdict de la sous-destination choisie sur chaque zone PLU
    recouverte par la zone d'étude (`zones` = lignes {zone, commune, part_pct, document}
    de contraintes_plu). États : autorisé / sous condition / interdit / en cours de
    calibration (commune non calibrée ou zone non lue)."""
    if sous_destination not in SOUS_DESTINATIONS:
        raise ValueError(f"sous-destination inconnue : {sous_destination!r}")
    out = []
    for z in zones or []:
        v = verdict(z.get("commune") or "", z.get("zone") or "", sous_destination)
        etat = v.get("statut_effectif")
        if v["etat_calibration"] == "non_calibree" or etat == "non_lu":
            etat = "en_cours_de_calibration"
        out.append({"zone": z.get("zone"), "commune": z.get("commune"),
                    "part_pct": z.get("part_pct"), "etat": etat,
                    **{k: v.get(k) for k in ("statut", "condition", "seuil_m2", "seuil_type",
                                             "article", "page_pdf", "millesime",
                                             "etat_calibration", "cdac", "phrase")}})
    # X3.2 — secteur préférentiel du SCoT, par commune recouverte (oui/non/non localisé).
    scots = {}
    for z in out:
        c = z.get("commune")
        if c and c not in scots:
            scots[c] = scot_daac(c)
    return {"sous_destination": sous_destination,
            "libelle": SOUS_DESTINATIONS[sous_destination][1],
            "zones": out, "scot": scots,
            "referentiel": REF_SOURCE, "cdac_regle": CDAC_SOURCE}


_ALIAS = {
    "restaurant": "restauration", "snack": "restauration", "brasserie": "restauration",
    "hotel": "hotels", "boutique": "artisanat_commerce_detail", "magasin": "artisanat_commerce_detail",
    "commerce": "artisanat_commerce_detail", "commerce de detail": "artisanat_commerce_detail",
    "artisanat": "artisanat_commerce_detail", "supermarche": "artisanat_commerce_detail",
    "grossiste": "commerce_gros", "usine": "industrie", "atelier industriel": "industrie",
    "entrepots": "entrepot", "stockage": "entrepot", "bureaux": "bureau",
    "gite": "autres_hebergements_touristiques", "meuble de tourisme": "autres_hebergements_touristiques",
    "chambre d'hotes": "autres_hebergements_touristiques", "camping": "autres_hebergements_touristiques",
    "residence de tourisme": "autres_hebergements_touristiques",
    "ecole": "enseignement_sante_action_sociale", "clinique": "enseignement_sante_action_sociale",
    "creche": "enseignement_sante_action_sociale", "ehpad": "enseignement_sante_action_sociale",
    "salle de sport": "equipements_sportifs", "gymnase": "equipements_sportifs",
    "eglise": "lieux_culte", "mosquee": "lieux_culte", "temple": "lieux_culte",
    "dark kitchen": "cuisine_vente_en_ligne", "coiffeur": "activites_services_clientele",
    "agence": "activites_services_clientele", "banque": "activites_services_clientele",
    "ferme": "exploitation_agricole", "elevage": "exploitation_agricole",
}


def resoudre_sous_destination(texte: str) -> str | None:
    """« restaurant » → restauration, « Hôtels » → hotels… Résolution honnête : slug exact,
    libellé officiel, puis alias usuels ; None si rien ne colle (jamais un slug deviné)."""
    if not texte:
        return None
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii").strip().lower()
    t = re.sub(r"[^a-z0-9' ]+", " ", t).strip()
    if t.replace(" ", "_") in SOUS_DESTINATIONS:
        return t.replace(" ", "_")
    for slug, (_p, lib) in SOUS_DESTINATIONS.items():
        libn = unicodedata.normalize("NFKD", lib).encode("ascii", "ignore").decode("ascii").lower()
        if t == libn:
            return slug
    if t in _ALIAS:
        return _ALIAS[t]
    # singulier/pluriel simple
    if t.rstrip("s") in _ALIAS:
        return _ALIAS[t.rstrip("s")]
    return None


def referentiel() -> dict:
    """Le référentiel servi aux surfaces (sélecteur d'activité)."""
    return {"destinations": [{"slug": k, "libelle": v} for k, v in DESTINATIONS.items()],
            "sous_destinations": [{"slug": k, "destination": p, "libelle": lib}
                                  for k, (p, lib) in SOUS_DESTINATIONS.items()],
            "source": REF_SOURCE}


# ---------------------------------------------------------------------------
# PLU-CALIBRAGE-1 lot 1 — LE SCHÉMA DES RÈGLES CHIFFRÉES PAR ZONE
# ---------------------------------------------------------------------------
# Sœur de `sous_destinations`, la clé `regles:` d'une zone porte les règles CHIFFRÉES
# (les valeurs que le calcul de capacité affiche aujourd'hui « ESTIMÉ »). Cinq rubriques,
# chacune éclatée en FEUILLES nommées. Une feuille = une règle atomique :
#   · soit une valeur lue     : {<valeur…>, formule?, min_m?, article, page_pdf, citation, statut}
#   · soit un silence prouvé  : {absent: true, article, page_pdf, citation, statut}
# Chaque feuille porte OBLIGATOIREMENT article + page_pdf + citation (verrou V6a pour un statut
# `valide`) et un `statut` ∈ {propose, valide}. Le silence du règlement s'écrit `absent: true`
# avec la citation qui le prouve — jamais une feuille vide ambiguë. Rien n'est déduit : une
# règle non trouvée n'est pas écrite (la feuille est absente du YAML, distinct de `absent:true`
# qui affirme, citation à l'appui, que le règlement ne réglemente pas).
#
# Feuilles attendues par rubrique (une zone peut n'en porter qu'une partie — le reste est
# « non lu », c.-à-d. absent du YAML) :
#   hauteur       → faitage · egout · niveaux      (les trois séparément — R151-39/40)
#   emprise_sol   → ces                            (% d'emprise au sol, ou coefficient CES)
#   retraits      → voie · limites_separatives     (chacune : formule texte + min_m)
#   stationnement → par_logement · par_m2_sdp · par_typologie
#   mixite        → feuille plate : seuil_logements|seuil_m2 + quota_pct + portee
REGLES_STATUTS = ("propose", "valide")

REGLES_RUBRIQUES: dict[str, tuple[str, ...]] = {
    "hauteur": ("faitage", "egout", "niveaux"),
    "emprise_sol": ("ces",),
    "retraits": ("voie", "limites_separatives"),
    "stationnement": ("par_logement", "par_m2_sdp", "par_typologie"),
    "pleine_terre": ("pct",),   # PLU-CALIBRAGE-3 : porté par l'ancien système (unification)
    "mixite": (),   # feuille plate (la rubrique EST la feuille)
}

REGLES_RUBRIQUES_LIB: dict[str, str] = {
    "hauteur": "Hauteur",
    "emprise_sol": "Emprise au sol",
    "retraits": "Retraits (implantation)",
    "stationnement": "Stationnement",
    "pleine_terre": "Pleine terre",
    "mixite": "Mixité sociale",
}

# Correspondance des DEUX générations de PLU. Avant la réforme de modernisation (décret
# n° 2015-1783, applicable aux PLU prescrits/révisés à compter du 01/01/2016), le règlement
# numérotait des ARTICLES 1 à 16 par zone ; après, il s'organise en CHAPITRES THÉMATIQUES
# (usage / caractéristiques urbaines, architecturales, environnementales et paysagères /
# équipements et réseaux — art. R151-17 et R151-27 à R151-50). Une rubrique `regles` se lit
# indifféremment dans l'une ou l'autre — la feuille cite l'article/chapitre RÉEL du document.
CORRESPONDANCE_GENERATIONS: dict[str, dict[str, str]] = {
    "hauteur": {"articles_6_16": "art. 10 (hauteur maximale des constructions)",
                "chapitres_2016": "Volumétrie et implantation — hauteur (R151-39/40)"},
    "emprise_sol": {"articles_6_16": "art. 9 (emprise au sol)",
                    "chapitres_2016": "Volumétrie et implantation — emprise au sol (R151-39)"},
    "retraits": {"articles_6_16": "art. 6 (implantation / voies et emprises publiques) "
                                  "+ art. 7 (implantation / limites séparatives)",
                 "chapitres_2016": "Volumétrie et implantation — implantation (R151-39)"},
    "stationnement": {"articles_6_16": "art. 12 (obligations de stationnement)",
                      "chapitres_2016": "Équipements et réseaux — stationnement (R151-44/45)"},
    "mixite": {"articles_6_16": "servitude de mixité sociale (art. 2 / dispositions générales) "
                                "— L151-15, L151-41 4°",
               "chapitres_2016": "Usage des sols et destinations — mixité sociale (L151-15) / OAP"},
}


def _est_feuille_regle(v: object) -> bool:
    """Une feuille de règle = un dict qui porte un `statut` (règle lue ou silence prouvé)."""
    return isinstance(v, dict) and "statut" in v


def iter_regles_feuilles(regles: dict | None):
    """Parcourt un bloc `regles` d'une zone → (chemin, feuille). `chemin` est le tuple
    (rubrique[, feuille]) ; `mixite` est plate (chemin d'un élément)."""
    for rubrique, contenu in (regles or {}).items():
        if _est_feuille_regle(contenu):
            yield (rubrique,), contenu
        elif isinstance(contenu, dict):
            for sous, feuille in contenu.items():
                if _est_feuille_regle(feuille):
                    yield (rubrique, sous), feuille


def regle_feuille_defauts(feuille: dict) -> list[str]:
    """Ce qui manque à une feuille pour être traçable : article, page_pdf, citation (verrou
    V6a). Vaut pour une valeur lue COMME pour un `absent: true` (le silence se prouve aussi)."""
    manques = []
    if not str(feuille.get("article") or "").strip():
        manques.append("article")
    if feuille.get("page_pdf") in (None, ""):
        manques.append("page_pdf")
    if not str(feuille.get("citation") or "").strip():
        manques.append("citation")
    return manques


def _zone_regles_brut(doc: dict, zone: str) -> dict:
    """Le bloc `regles` d'une zone, résolu par clé normalisée. Les règles suivent le `renvoi`
    UNIQUEMENT si la zone n'a pas ses propres règles (un secteur porte souvent ses règles de
    volumétrie propres tout en renvoyant ses destinations à la zone mère)."""
    zones = doc.get("zones") or {}
    norm = {_norm_zone(z): z for z in zones}
    hit = norm.get(_norm_zone(zone))
    if hit is None:
        return {}
    v = zones[hit]
    if isinstance(v, dict) and v.get("regles"):
        return v["regles"]
    seen = {hit}
    while isinstance(v, dict) and v.get("renvoi") and not v.get("regles"):
        cible = norm.get(_norm_zone(v["renvoi"]))
        if cible is None or cible in seen:
            break
        seen.add(cible)
        v = zones[cible]
    return (v.get("regles") if isinstance(v, dict) else None) or {}


def regles_zone(commune: str, zone: str) -> dict:
    """Les règles chiffrées calibrées d'une (commune, zone) — LE point de lecture unique du
    bloc `regles`. {} si la commune n'est pas calibrée, la zone n'existe pas, ou aucune règle
    n'est lue. Ne fabrique rien : relaie le YAML tel quel (feuilles `propose`/`valide`)."""
    doc = _doc(commune)
    if not doc:
        return {}
    return _zone_regles_brut(doc, zone)


def regles_commune(commune: str) -> list[dict]:
    """Toutes les feuilles de règles calibrées d'une commune, à plat (revue, contrôle) :
    [{zone, rubrique, feuille, chemin, statut, absent, article, page_pdf, citation, valeur}]."""
    doc = _doc(commune)
    if not doc:
        return []
    out: list[dict] = []
    for zone in sorted((doc.get("zones") or {}).keys()):
        zv = (doc.get("zones") or {}).get(zone) or {}
        if not isinstance(zv, dict) or not zv.get("regles"):
            continue  # seule la zone qui PORTE ses règles les déclare (pas les renvois)
        for chemin, feuille in iter_regles_feuilles(zv["regles"]):
            out.append({"zone": zone, "rubrique": chemin[0],
                        "feuille": chemin[1] if len(chemin) > 1 else None,
                        "chemin": ".".join(chemin), **feuille})
    return out


def iter_regles_calibrees():
    """Parcourt TOUTES les calibrations (config/plu_destinations/*.yaml) → dict par feuille,
    pour le verrou V6a et les contrôles transverses. `absent` distingue silence prouvé de
    valeur lue ; `fichier` et `insee` situent la feuille."""
    for path in sorted(_DEST_DIR.glob("974??_*.yaml")):
        doc = _load_yaml(str(path))
        insee = (doc.get("meta") or {}).get("insee")
        for zone, zv in (doc.get("zones") or {}).items():
            if not isinstance(zv, dict) or not zv.get("regles"):
                continue
            for chemin, feuille in iter_regles_feuilles(zv["regles"]):
                yield {"fichier": path.name, "insee": insee, "zone": zone,
                       "chemin": ".".join(chemin), **feuille}


# ---------------------------------------------------------------------------
# PLU-CALIBRAGE-1 lot 2 — LES CALIBRAGES, LECTEURS DU RÉSERVOIR GPU
# ---------------------------------------------------------------------------
# Chaque calibration de commune (config/plu_destinations/<insee>_*.yaml) LIT le règlement
# opposable servi par le réservoir GPU (`gpu_plu_api_carto`, qui sert `plu_reglement_extrait`)
# et grave la version calibrée (identifiant GPU `meta.document_gpu` + date `meta.millesime`).
# Ce sont donc 23 LECTEURS de plus sur une source existante — aucun job nouveau. Quand une
# nouvelle version du PLU d'une commune est servie (catalogue `plu_millesimes.yaml` rafraîchi
# par la veille GPU, idurba plus récent que celui gravé au calibrage), `etat_commune` bascule
# la commune en « a_relire » : le calibrage passe « à revérifier » dans le Circuit.
CALIBRAGE_ETAT_LABEL = {
    "calibree": "à jour",
    "a_relire": "à revérifier",
    "non_calibree": "non calibré",
}


def calibrages_gpu() -> list[dict]:
    """Les calibrages PLU (un par commune dotée d'un PLU), lecteurs du réservoir GPU. Le RNU
    (Saint-Philippe) n'est pas un calibrage de règlement PLU — exclu. État repris de
    `etat_commune` : « à jour » / « à revérifier » (nouvelle version GPU) / « non calibré »."""
    out: list[dict] = []
    for e in etats_ile():
        if e.get("etat") == "rnu":
            continue
        insee = e.get("insee")
        out.append({
            "insee": insee,
            "commune": e.get("commune"),
            "etat": e.get("etat"),
            "etat_label": CALIBRAGE_ETAT_LABEL.get(e.get("etat"), e.get("etat")),
            "a_reverifier": e.get("etat") == "a_relire",
            "millesime": e.get("millesime"),
            "document_gpu": e.get("document_gpu"),
            "document_gpu_servi": e.get("document_gpu_servi"),
            "lu_le": e.get("lu_le"),
            "note": e.get("note"),
            "n_zones": len(e.get("zones") or []),
            "n_regles": len(regles_commune(insee or "")),
        })
    return out
