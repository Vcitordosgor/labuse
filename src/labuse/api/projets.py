"""PROJETS (copilote-projet) — l'objet persistant produit par l'entretien de cadrage.

Doctrine : l'IA REMPLIT la fiche (validée par FICHE_SCHEMA), le serveur DÉRIVE — de
façon déterministe et rejouable — les filtres et les paramètres M22. Aucun chiffre
n'est produit par l'IA : la SDP besoin vient de la formule M22 EXISTANTE
(unités × surface_unité × 1,15 — modules.faisabilite_sens2), les contraintes
rédhibitoires deviennent des exclusions de flags SQL (flags_exclus).

Ouvrir un projet = REJOUER (filtres + programme réappliqués sur les données
actuelles) — jamais un snapshot figé. Le budget foncier reste une donnée de fiche
(aucun prix par parcelle en base → un filtre budget serait menteur ; consigné).
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from jsonschema import ValidationError, validate
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from .ia import FILTER_SCHEMA, SECTEURS

router = APIRouter(prefix="/projets", tags=["projets"])


def get_db():  # branché sur la session app au moment de l'inclusion (cf. app.py)
    from .app import get_db as _g
    yield from _g()


DDL = """
CREATE TABLE IF NOT EXISTS projets (
  id serial PRIMARY KEY,
  nom varchar(160) NOT NULL,
  fiche jsonb NOT NULL DEFAULT '{}'::jsonb,
  filtres jsonb NOT NULL DEFAULT '{}'::jsonb,
  programme jsonb,
  statut varchar(16) NOT NULL DEFAULT 'actif',
  derniere_execution_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE pipeline_entries ADD COLUMN IF NOT EXISTS projet_id integer
  REFERENCES projets(id) ON DELETE SET NULL
"""


def ensure_tables(engine) -> None:
    from sqlalchemy import text as _t
    with engine.begin() as c:
        for stmt in DDL.split(";"):
            if stmt.strip():
                c.execute(_t(stmt))


#: contrainte rédhibitoire (fiche) → couche flag exclue (même vocabulaire que FILTER_SCHEMA.flags)
CONTRAINTE_FLAG = {
    "eviter_ppr": "risques",
    "eviter_pollution": "sol_pollue",
    "eviter_abf": "abf",
    "eviter_icpe": "icpe",
}

TYPE_LABEL = {"logements": "Logements", "etudiant": "Logement étudiant",
              "bureaux": "Bureaux", "autre": "Projet"}

#: hypothèse M22 par défaut (surface_unite_m2 du formulaire M22Programme — la vérité
#: reste le formulaire, pré-rempli et éditable)
M22_SURFACE_UNITE_M2 = 60.0

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
            },
        },
        "perimetre": {
            "type": "object", "additionalProperties": False, "required": ["mode"],
            "properties": {
                "mode": {"enum": ["ile", "secteur", "communes"]},
                "secteur": {"enum": list(SECTEURS)},
                "communes": {"type": "array", "maxItems": 24, "items": {"type": "string"}},
            },
        },
        "contraintes": {"type": "array", "maxItems": 4,
                        "items": {"enum": list(CONTRAINTE_FLAG)}},
        "budget_foncier_eur": {"type": "number", "minimum": 0},
        "criteres_libres": {"type": "string", "maxLength": 500},
    },
}


def _valide_fiche(fiche: dict) -> dict:
    """Garde-fou schéma : clé hors schéma = REJET (l'IA ne peut introduire ni champ ni
    valeur hors vocabulaire). Le périmètre secteur/communes doit être cohérent."""
    try:
        validate(fiche, FICHE_SCHEMA)
    except ValidationError as exc:
        raise HTTPException(422, f"Fiche projet invalide : {exc.message}") from None
    per = fiche.get("perimetre") or {}
    if per.get("mode") == "secteur" and per.get("secteur") not in SECTEURS:
        raise HTTPException(422, "Périmètre secteur sans secteur valide")
    if per.get("mode") == "communes" and not per.get("communes"):
        raise HTTPException(422, "Périmètre communes sans commune")
    return fiche


def derive_sdp_besoin(fiche: dict) -> int | None:
    """SDP besoin (m²) — formule M22 EXISTANTE (unités × surface_unité × 1,15), jamais l'IA.
    `sdp_m2` explicite prime sur `logements`."""
    amp = fiche.get("ampleur") or {}
    if amp.get("sdp_m2") is not None:
        return round(amp["sdp_m2"])
    if amp.get("logements"):
        return round(amp["logements"] * M22_SURFACE_UNITE_M2 * 1.15)
    return None


def derive_filtres(fiche: dict, extra: dict | None = None) -> dict:
    """fiche → filtres (forme FILTER_SCHEMA, celle du front). Déterministe et rejouable.
    `extra` : filtres additionnels de l'entretien (vue mer…), validés FILTER_SCHEMA — les
    clés dérivées de la fiche PRIMENT (la fiche est la vérité du projet)."""
    filtres: dict = {}
    if extra:
        try:
            validate(extra, FILTER_SCHEMA)
        except ValidationError as exc:
            raise HTTPException(422, f"Filtres additionnels invalides : {exc.message}") from None
        filtres.update({k: v for k, v in extra.items() if v is not None})
    per = fiche.get("perimetre") or {}
    filtres.pop("commune", None)
    filtres.pop("communes", None)
    if per.get("mode") == "secteur":
        filtres["communes"] = list(SECTEURS[per["secteur"]])
    elif per.get("mode") == "communes":
        filtres["communes"] = list(per.get("communes") or [])
    sdp = derive_sdp_besoin(fiche)
    if sdp is not None:
        filtres["sdpMin"] = sdp
    flags_x = sorted({CONTRAINTE_FLAG[c] for c in (fiche.get("contraintes") or [])})
    if flags_x:
        filtres["flagsExclus"] = flags_x
    return filtres


def derive_programme(fiche: dict) -> dict | None:
    """fiche → paramètres M22 (ProgrammeIn) quand un programme est définissable
    (type + nombre de logements). Mapping consigné : 1 bâtiment, R+2 (défauts du
    formulaire M22), logements_par_batiment = total → unités = total (la formule
    M22 `unités = bâtiments × logements/bât` est préservée). La vérité reste le
    formulaire M22 pré-rempli, éditable."""
    t = fiche.get("type_programme")
    logements = (fiche.get("ampleur") or {}).get("logements")
    if t in (None, "autre") or not logements:
        return None
    per = fiche.get("perimetre") or {}
    communes = per.get("communes") or []
    return {
        "type": t, "batiments": 1, "niveaux": 2,
        "logements_par_batiment": int(logements),
        "surface_unite_m2": M22_SURFACE_UNITE_M2, "parking": True,
        "commune": communes[0] if per.get("mode") == "communes" and len(communes) == 1 else None,
    }


def derive_nom(fiche: dict) -> str:
    """Nom de repli déterministe (l'IA en propose un meilleur ; toujours éditable)."""
    t = TYPE_LABEL.get(fiche.get("type_programme") or "", "Projet")
    amp = fiche.get("ampleur") or {}
    n = f" ×{amp['logements']}" if amp.get("logements") else ""
    per = fiche.get("perimetre") or {}
    if per.get("mode") == "secteur":
        ou = f"secteur {per['secteur']}"
    elif per.get("mode") == "communes":
        cs = per.get("communes") or []
        ou = cs[0] if len(cs) == 1 else f"{len(cs)} communes"
    else:
        ou = "toute l'île"
    return f"{t}{n} — {ou}"


def _projet_dict(p: models.Projet) -> dict:
    return {
        "id": p.id, "nom": p.nom, "statut": p.statut,
        "fiche": p.fiche or {}, "filtres": p.filtres or {}, "programme": p.programme,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "derniere_execution_at": (p.derniere_execution_at.isoformat()
                                  if p.derniere_execution_at else None),
    }


class ProjetIn(BaseModel):
    fiche: dict
    nom: str | None = None            # proposé par l'IA ; repli déterministe sinon
    filtres_extra: dict | None = None  # filtres additionnels de l'entretien (vue mer…)


class ProjetPatchIn(BaseModel):
    nom: str | None = None
    statut: str | None = None          # actif | archive
    fiche: dict | None = None          # re-dérive filtres + programme


@router.get("")
def projets_list(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(models.Projet).order_by(models.Projet.updated_at.desc()).all()
    return [_projet_dict(p) for p in rows]


@router.post("")
def projet_create(body: ProjetIn, db: Session = Depends(get_db)) -> dict:
    fiche = _valide_fiche(body.fiche or {})
    nom = (body.nom or "").strip()[:160] or derive_nom(fiche)
    p = models.Projet(nom=nom, fiche=fiche,
                      filtres=derive_filtres(fiche, body.filtres_extra),
                      programme=derive_programme(fiche))
    db.add(p)
    db.flush()
    return {"ok": True, "projet": _projet_dict(p)}


@router.get("/{pid}")
def projet_get(pid: int, db: Session = Depends(get_db)) -> dict:
    p = db.get(models.Projet, pid)
    if not p:
        raise HTTPException(404, "Projet inconnu")
    return _projet_dict(p)


@router.patch("/{pid}")
def projet_patch(pid: int, body: ProjetPatchIn, db: Session = Depends(get_db)) -> dict:
    p = db.get(models.Projet, pid)
    if not p:
        raise HTTPException(404, "Projet inconnu")
    if body.nom is not None:
        nom = body.nom.strip()[:160]
        if not nom:
            raise HTTPException(422, "Nom vide")
        p.nom = nom
    if body.statut is not None:
        if body.statut not in ("actif", "archive"):
            raise HTTPException(422, f"Statut invalide : {body.statut}")
        p.statut = body.statut
    if body.fiche is not None:
        p.fiche = _valide_fiche(body.fiche)
        p.filtres = derive_filtres(p.fiche)
        p.programme = derive_programme(p.fiche)
    db.flush()
    return {"ok": True, "projet": _projet_dict(p)}


@router.post("/{pid}/rejouer")
def projet_rejouer(pid: int, db: Session = Depends(get_db)) -> dict:
    """Ouvrir = REJOUER : horodate l'exécution et rend la recette (filtres + programme)
    que le front réapplique sur les données ACTUELLES. Les chiffres peuvent avoir bougé
    depuis le dernier rejeu — c'est le principe (et la matière du futur radar cron)."""
    p = db.get(models.Projet, pid)
    if not p:
        raise HTTPException(404, "Projet inconnu")
    p.derniere_execution_at = datetime.now(timezone.utc)
    db.flush()
    return {"ok": True, "projet": _projet_dict(p)}
