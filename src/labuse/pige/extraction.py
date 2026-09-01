"""RADAR P1 · V2 — EXTRACTION d'une capture d'annonce en JSON strict (vision IA).

Doctrine §2 — ANTI-INVENTION ABSOLUE : tout champ non lisible sur la capture = `null`. Le modèle ne
complète pas, ne déduit pas, n'estime pas. Le prompt l'EXIGE et la sortie est validée contre le schéma
(les champs inconnus sont ignorés, jamais un champ inventé n'est retenu). Chaque champ porte sa CONFIANCE
(sous le seuil → « à vérifier », surligné à l'écran V3).

Aucune requête portail ici : on lit une IMAGE déjà fournie par la saisie HUMAINE. Le portail est déduit
du LIEN via `portails.py` (le seul endroit où vivent les noms de portails).
"""
from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from ..ai import core
from . import portails

# Les 11 champs du contrat (mandat V2). Ordre stable pour l'affichage.
CHAMPS = ("prix", "type", "pieces", "surface_hab", "surface_terrain",
          "dpe_classe", "dpe_conso", "dpe_ges", "commune", "particulier_pro", "date_publication")

# En dessous, le champ est marqué « à vérifier » (surligné mauve à la validation).
SEUIL_CONFIANCE = 0.6

_PROMPT = """Tu lis UNE capture d'écran d'une annonce immobilière de VENTE à La Réunion. Tu EXTRAIS des
faits, tu n'en inventes AUCUN. RÈGLE ABSOLUE : si un champ n'est pas LISIBLE sur l'image, sa valeur est
null. Tu ne déduis pas, tu ne complètes pas, tu n'estimes pas. Mieux vaut null qu'un chiffre approché.

Réponds UNIQUEMENT par un objet JSON (aucun texte autour), avec EXACTEMENT ces clés, chacune un objet
{"valeur": <v ou null>, "confiance": <0.0 à 1.0>} :
- prix : prix de vente en euros, entier (sans espaces ni €) ;
- type : un de "maison" | "terrain" | "immeuble" | "appartement" ;
- pieces : nombre de pièces, entier ;
- surface_hab : surface habitable en m², nombre ;
- surface_terrain : surface du terrain en m², nombre ;
- dpe_classe : lettre A..G du DPE ;
- dpe_conso : consommation DPE en kWh/m²/an, entier ;
- dpe_ges : émissions GES DPE, entier ;
- commune : nom de la commune (telle qu'écrite) ;
- particulier_pro : "particulier" ou "pro" (agence) ;
- date_publication : date de mise en ligne au format AAAA-MM-JJ si visible.

La confiance reflète la LISIBILITÉ réelle sur l'image : 0.0 si le champ est absent/illisible (valeur
null), proche de 1.0 si le fait est écrit noir sur blanc. Ne remonte jamais une valeur non nulle avec
une confiance élevée sans l'avoir vue."""

_TYPES_VALIDES = {"maison", "terrain", "immeuble", "appartement"}


def _json_strict(prose: str) -> dict | None:
    """Extrait l'objet JSON de la prose (tolère un bloc ```json). None si rien de parsable — on ne
    RÉPARE jamais une sortie douteuse par de l'invention."""
    s = prose.strip()
    s = re.sub(r"^```(?:json)?|```$", "", s, flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _normaliser(brut: dict) -> tuple[dict, dict]:
    """Ne retient QUE les 11 champs connus (les clés inconnues du modèle sont jetées). Chaque champ →
    (valeur, confiance). Valeur absente/illisible → None, confiance 0. `type` hors énumération → None."""
    faits: dict = {}
    conf: dict = {}
    for champ in CHAMPS:
        cell = brut.get(champ)
        if isinstance(cell, dict):
            v, c = cell.get("valeur"), cell.get("confiance")
        else:
            v, c = (cell, None)   # tolère un modèle qui aurait mis la valeur nue
        if champ == "type" and v is not None and str(v).lower() not in _TYPES_VALIDES:
            v, c = None, 0.0      # type hors énumération = non fiable → null (jamais deviné)
        try:
            c = float(c) if c is not None else (0.9 if v is not None else 0.0)
        except (TypeError, ValueError):
            c = 0.0
        faits[champ] = v
        conf[champ] = 0.0 if v is None else max(0.0, min(1.0, c))
    return faits, conf


def extraire(db: Session | None, image: bytes, media_type: str, lien: str, *,
             max_tokens: int = 900) -> dict:
    """Capture (octets) + lien portail → faits JSON stricts + confiances. Retourne
    {ok, faits, confiances, champs_a_verifier, portail, portail_inconnu, motif?}.
    `ok=False` (avec `motif` honnête) si : pas de clé, image illisible/format/taille, réponse non-JSON.
    """
    portail = portails.slug_pour_url(lien)
    portail_inconnu = portail == "autre"
    r = core.complete(db, kind="vision_pige", system=_PROMPT,
                      context={"lien": lien, "portail": portails.nom(portail)},
                      images=[core.ImagePart(image, media_type)],
                      model=core.model_for("vision_pige"), max_tokens=max_tokens)
    if r.degraded:
        return {"ok": False, "motif": r.reason or "IA indisponible",
                "portail": portail, "portail_inconnu": portail_inconnu}
    brut = _json_strict(r.text)
    if brut is None:
        # sortie non-JSON : on n'invente RIEN, on rend la main avec un motif honnête et reprise possible.
        return {"ok": False, "motif": "réponse non-JSON — rien extrait (aucun champ inventé)",
                "portail": portail, "portail_inconnu": portail_inconnu, "brut": r.text[:200]}
    faits, conf = _normaliser(brut)
    a_verifier = [c for c in CHAMPS if faits[c] is not None and conf[c] < SEUIL_CONFIANCE]
    return {"ok": True, "faits": faits, "confiances": conf, "champs_a_verifier": a_verifier,
            "portail": portail, "portail_inconnu": portail_inconnu}
