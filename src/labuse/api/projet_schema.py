"""Vocabulaire PARTAGÉ du copilote-projet — fiche de cadrage + schémas.

Module NEUTRE (n'importe ni ia ni projets) pour casser le cycle : ia.py (l'entretien)
et projets.py (le CRUD + la dérivation) importent tous deux d'ici. La fiche a un
vocabulaire FERMÉ (enums) → le garde-fou schéma empêche l'IA d'injecter un champ ou une
valeur hors périmètre.
"""
from __future__ import annotations

#: type de programme → libellé (l'IA choisit une CLÉ, jamais un texte libre)
TYPE_LABEL = {"logements": "Logements", "etudiant": "Logement étudiant",
              "bureaux": "Bureaux", "autre": "Projet"}

#: contrainte rédhibitoire (fiche) → couche flag exclue (vocabulaire de FILTER_SCHEMA.flags)
CONTRAINTE_FLAG = {
    "eviter_ppr": "risques",
    "eviter_pollution": "sol_pollue",
    "eviter_abf": "abf",
    "eviter_icpe": "icpe",
}
CONTRAINTE_LABEL = {
    "eviter_ppr": "hors zone à risque (PPR)",
    "eviter_pollution": "sol non pollué",
    "eviter_abf": "hors périmètre ABF",
    "eviter_icpe": "hors nuisance industrielle (ICPE)",
}

#: les 4 microrégions (les communes de chacune vivent dans ia.SECTEURS)
SECTEUR_KEYS = ["Nord", "Ouest", "Sud", "Est"]

#: hypothèse M22 par défaut (surface_unite_m2 du formulaire M22Programme — la vérité reste
#: le formulaire, pré-rempli et éditable) ; +15 % de circulations comme faisabilite_sens2
M22_SURFACE_UNITE_M2 = 60.0
M22_CIRCULATION = 1.15

#: la fiche de cadrage — ce que le promoteur A DIT (validé, vocabulaire fermé). Tous les
#: champs sont OPTIONNELS : l'entretien construit la fiche par touches successives.
FICHE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "type_programme": {"enum": list(TYPE_LABEL)},
        "ampleur": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "logements": {"type": "integer", "minimum": 1, "maximum": 2000},
                "sdp_m2": {"type": "number", "minimum": 50, "maximum": 200000},
                # P1.2 (revue Vic n°3) — gabarit souhaité : R+n. Irrigue le paramètre `niveaux`
                # de M22 (derive_programme). C'est la donnée du promoteur, pas un calcul.
                "niveaux": {"type": "integer", "minimum": 1, "maximum": 30},
            },
        },
        "perimetre": {
            "type": "object", "additionalProperties": False, "required": ["mode"],
            "properties": {
                "mode": {"enum": ["ile", "secteur", "communes"]},
                "secteur": {"enum": SECTEUR_KEYS},
                "communes": {"type": "array", "maxItems": 24, "items": {"type": "string"}},
            },
        },
        "contraintes": {"type": "array", "maxItems": 4,
                        "items": {"enum": list(CONTRAINTE_FLAG)}},
        "budget_foncier_eur": {"type": "number", "minimum": 0},
        "criteres_libres": {"type": "string", "maxLength": 500},
    },
}


def clean_fiche(fiche: dict) -> dict:
    """Retire les valeurs « inconnu » avant validation : l'IA émet parfois `type_programme:
    null` ou `criteres_libres: ""` pour une dimension pas encore renseignée — un null n'est
    pas dans l'enum et casserait le schéma. On DROP null / "" / [] / {} récursivement (0 reste
    une valeur). Idempotent."""
    def vide(v) -> bool:
        return v is None or v == "" or v == [] or v == {}
    out: dict = {}
    for k, v in (fiche or {}).items():
        if isinstance(v, dict):
            v = clean_fiche(v)
        if not vide(v):
            out[k] = v
    return out


def relocate_niveaux(fiche: dict) -> dict:
    """`niveaux` (gabarit R+n) est une donnée LÉGITIME du cadrage, mais elle vit DANS `ampleur`.
    Le modèle la place parfois à la RACINE de la fiche (« R+3 » → fiche.niveaux au lieu de
    fiche.ampleur.niveaux) → le garde-fou schéma la rejetterait (additionalProperties:false).
    On la REMET dans `ampleur` plutôt que de la perdre. N'écrase pas une valeur déjà bien placée.
    Idempotent, non destructif (retourne une copie)."""
    if not isinstance(fiche, dict) or "niveaux" not in fiche:
        return fiche
    fiche = dict(fiche)
    niveaux = fiche.pop("niveaux")
    amp = dict(fiche.get("ampleur") or {}) if isinstance(fiche.get("ampleur"), dict) else {}
    amp.setdefault("niveaux", niveaux)
    fiche["ampleur"] = amp
    return fiche


def prune_to_schema(data, schema, _path: str = "") -> tuple[object, list[str]]:
    """Retire RÉCURSIVEMENT les propriétés qu'un schéma à `additionalProperties:false` refuse,
    au lieu de laisser la validation ÉCHOUER sur un champ inattendu du modèle. Robustesse du
    cadrage : un champ hors vocabulaire ne doit PAS faire tomber tout l'entretien — on le retire
    proprement (et on le journalise via la liste renvoyée). Ne touche JAMAIS une valeur légitime :
    seuls les champs hors `properties` d'un objet fermé sont écartés. Gère objets et tableaux
    d'objets. Retourne (donnée nettoyée, chemins des champs retirés)."""
    dropped: list[str] = []
    if isinstance(data, dict) and schema.get("type") == "object":
        props = schema.get("properties", {})
        ferme = schema.get("additionalProperties", True) is False
        out: dict = {}
        for k, v in data.items():
            child = props.get(k)
            if child is not None:
                sub, d = prune_to_schema(v, child, f"{_path}.{k}".lstrip("."))
                out[k] = sub
                dropped += d
            elif ferme:
                dropped.append(f"{_path}.{k}".lstrip("."))
            else:
                out[k] = v
        return out, dropped
    if isinstance(data, list) and schema.get("type") == "array" and isinstance(schema.get("items"), dict):
        out_l = []
        for i, v in enumerate(data):
            sub, d = prune_to_schema(v, schema["items"], f"{_path}[{i}]")
            out_l.append(sub)
            dropped += d
        return out_l, dropped
    return data, dropped


def derive_sdp_besoin(fiche: dict) -> int | None:
    """SDP besoin (m²) — formule M22 EXISTANTE (unités × surface_unité × 1,15), jamais l'IA.
    `sdp_m2` explicite prime sur `logements`."""
    amp = fiche.get("ampleur") or {}
    if amp.get("sdp_m2") is not None:
        return round(amp["sdp_m2"])
    if amp.get("logements"):
        return round(amp["logements"] * M22_SURFACE_UNITE_M2 * M22_CIRCULATION)
    return None
