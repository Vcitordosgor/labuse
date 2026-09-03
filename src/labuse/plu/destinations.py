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
    """« Saint-Denis » → « saint_denis » (même convention que plu_rules)."""
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


def _millesimes() -> dict:
    """Catalogue des millésimes PLU servis (config/plu_millesimes.yaml)."""
    p = _CONFIG_DIR / "plu_millesimes.yaml"
    return (_load_yaml(str(p)) or {}).get("communes", {}) if p.is_file() else {}


def _rnu_doc() -> dict:
    p = _DEST_DIR / "rnu.yaml"
    return _load_yaml(str(p)) if p.is_file() else {}


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
