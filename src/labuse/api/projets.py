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

from fastapi import APIRouter, Depends, HTTPException, Query
from jsonschema import ValidationError, validate
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import models
from ..scoring.score_v_constants import Q_A_RUN_LABEL as RUN  # run de référence
from .ia import FILTER_SCHEMA, SECTEURS
from .projet_schema import (CONTRAINTE_FLAG, FICHE_SCHEMA, M22_SURFACE_UNITE_M2,
                            TYPE_LABEL, clean_fiche, derive_sdp_besoin)

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


# ─────────────────── arbitrages SOURCÉS (chiffres servis par la base) ───────────────────

@router.get("/reperes")
def projet_reperes(dimension: str = Query("secteur", pattern="^(secteur|commune)$"),
                   db: Session = Depends(get_db)) -> dict:
    """Chiffres SOURCÉS par option d'un choix de l'entretien (secteur ou commune) : nombre
    d'opportunités (q_v2 chaude/à surveiller/à creuser), prix médian du bâti (DVF, €/m²
    habitable) et communes carencées SRU. DÉTERMINISTE, 100 % SQL — l'IA n'en produit AUCUN
    (doctrine : arbitrages sourcés ou tus). Sous les chips : « N opportunités · ~P €/m² ».
    """
    # opportunités par commune (les 3 statuts promus du run premium)
    opp = {r["commune"]: r["n"] for r in db.execute(text(
        "SELECT p.commune, count(*) n FROM parcels p "
        "JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :runref "
        " AND d.matrice_statut IN ('chaude','a_surveiller','a_creuser') "
        "GROUP BY p.commune"), {"runref": RUN}).mappings()}
    # prix médian bâti DVF (€/m² habitable) — bornes anti-aberration comme l'affichage marché
    dvf = {r["commune"]: int(r["m"]) for r in db.execute(text(
        "SELECT commune, percentile_cont(0.5) WITHIN GROUP ("
        "  ORDER BY valeur_fonciere / NULLIF(surface_reelle_bati,0)) m "
        "FROM dvf_mutations WHERE surface_reelle_bati > 0 AND valeur_fonciere > 0 "
        "  AND valeur_fonciere / surface_reelle_bati BETWEEN 200 AND 8000 "
        "GROUP BY commune")).mappings() if r["m"]}
    carencees = {r["commune"] for r in db.execute(text(
        "SELECT commune FROM commune_contexte_sru WHERE statut = 'carencee'")).mappings()}

    def bloc(communes: list[str]) -> dict:
        meds = [dvf[c] for c in communes if c in dvf]
        return {
            "nb_opportunites": sum(opp.get(c, 0) for c in communes),
            "dvf_median_eur_m2": round(sum(meds) / len(meds)) if meds else None,
            "communes_carencees": sorted(c for c in communes if c in carencees),
        }

    if dimension == "secteur":
        options = [{"key": s, "label": s, **bloc(SECTEURS[s])} for s in SECTEURS]
    else:
        options = [{"key": c, "label": c, **bloc([c])}
                   for c in sorted(opp, key=lambda x: -opp[x])]
    return {"dimension": dimension, "options": options,
            "note": "Opportunités : run premium q_v2. Prix médian : DVF bâti (€/m² habitable). "
                    "Carencées : inventaire SRU. Aucun chiffre produit par l'IA."}


def _valide_fiche(fiche: dict) -> dict:
    """Garde-fou schéma : clé hors schéma = REJET (l'IA ne peut introduire ni champ ni
    valeur hors vocabulaire). Le périmètre secteur/communes doit être cohérent."""
    fiche = clean_fiche(fiche)              # null/"" = « pas encore su » → drop (hors enum)
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
    amp = fiche.get("ampleur") or {}
    logements = amp.get("logements")
    if t in (None, "autre") or not logements:
        return None
    per = fiche.get("perimetre") or {}
    communes = per.get("communes") or []
    # gabarit souhaité (R+n) → niveaux M22 ; défaut R+2 (défaut du formulaire) si non exprimé
    niveaux = int(amp["niveaux"]) if amp.get("niveaux") else 2
    return {
        "type": t, "batiments": 1, "niveaux": niveaux,
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


_STATUT_LABEL = {"chaude": "Chaude", "a_surveiller": "À surveiller", "a_creuser": "À creuser"}
#: M5.1 : le TIER v2 est le verdict énoncé au client (l'étage 0 du run servi prime) ;
#: le statut matrice ne sert plus que de repli (item sans run v2).
_TIER_LABEL = {"brulante": "Brûlante v2", "chaude": "Chaude v2",
               "reserve_fonciere": "Réserve foncière", "a_creuser": "À creuser",
               "ecartee": "Écartée"}


def _pourquoi_lignes(item: dict, sdp_besoin: int | None, carencees: set[str]) -> list[str]:
    """Le « pourquoi » d'une parcelle RELIÉ au projet — assemblé depuis les DONNÉES du moteur
    (aucune valeur inventée). Ordre : verdict, capacité vs besoin, hauteur PLU, contexte."""
    out: list[str] = []
    statut = item.get("statut") or item.get("status")   # M22 → statut ; q_v2_list → status
    if item.get("etage0"):
        st = "Écartée (exclusion dure)"
    elif item.get("tier_v2") in _TIER_LABEL:
        st = _TIER_LABEL[item["tier_v2"]]
    else:
        st = _STATUT_LABEL.get(statut, statut or "—")
    if item.get("q_score") is not None:
        out.append(f"{st} · qualité {item['q_score']}/100")
    else:
        out.append(st)
    sdp = item.get("sdp") or item.get("sdp_residuelle_m2")
    if sdp and sdp_besoin:
        pct = round(100 * sdp / sdp_besoin)
        cmp = "couvre le besoin" if sdp >= sdp_besoin else f"{pct} % du besoin"
        out.append(f"SDP résiduelle {round(sdp):,} m² pour {sdp_besoin:,} m² requis — {cmp}"
                   .replace(",", " "))
    elif sdp:
        out.append(f"SDP résiduelle {round(sdp):,} m²".replace(",", " "))
    if item.get("hauteur_plu_m") is not None:
        ok = "vérifiée" if item.get("hauteur_verifiee") else "à instruire"
        out.append(f"Hauteur PLU {item['hauteur_plu_m']:.0f} m ({ok})"
                   + (f", zone {item['zone']}" if item.get("zone") else ""))
    if item.get("commune") in carencees:
        out.append("Commune carencée SRU — forte demande de logement social")
    return out


class ApercuIn(BaseModel):
    fiche: dict
    limit: int = 5


@router.post("/apercu")
def projet_apercu(body: ApercuIn, db: Session = Depends(get_db)) -> dict:
    """Aperçu RELIÉ au projet : compteur SQL + top parcelles avec leur « pourquoi » SORTI DU
    MOTEUR (SDP résiduelle vs besoin, hauteur PLU vérifiée, statut/score, carence SRU). Si un
    programme est défini, le top vient de M22 (sens 2, trié par marge de capacité) ; sinon du
    run q_v2 trié par score. Aucune valeur inventée."""
    fiche = _valide_fiche(body.fiche or {})
    filtres = derive_filtres(fiche)
    programme = derive_programme(fiche)
    sdp_besoin = derive_sdp_besoin(fiche)
    communes = filtres.get("communes")
    carencees = {r[0] for r in db.execute(text(
        "SELECT commune FROM commune_contexte_sru WHERE statut = 'carencee'")).all()}
    lim = max(1, min(body.limit, 20))

    if programme:
        from .modules import ProgrammeIn, faisabilite_sens2
        res = faisabilite_sens2(ProgrammeIn(**programme), db)
        items = res.get("items", [])
        if communes:                                   # secteur : M22 balaie l'île → on restreint
            items = [it for it in items if it["commune"] in communes]
        n = len(items)
        top = items[:lim]
        source = "m22"
    else:
        from .app import _q_v2_list, _q_v2_where
        where, params = _q_v2_where(RUN, ",".join(filtres.get("statuts") or []) or None,
                                    filtres.get("scoreMin"), filtres.get("surfaceMin"),
                                    filtres.get("surfaceMax"), filtres.get("sdpMin"),
                                    bool(filtres.get("evenement")), bool(filtres.get("vueMer")),
                                    ",".join(filtres.get("flags") or []) or None,
                                    ",".join(communes) if communes else None,
                                    ",".join(filtres.get("flagsExclus") or []) or None)
        n = db.execute(text(
            "SELECT count(*) FROM parcels p JOIN dryrun_parcel_evaluations d "
            "ON d.parcel_id = p.id AND d.run_label = :runref "
            "AND d.matrice_statut IN ('chaude','a_surveiller','a_creuser')" + where),
            {**params, "runref": RUN}).scalar() or 0
        top = _q_v2_list(db, None, lim, 0, run_label=RUN,
                         extra_where=where, extra_params=params)
        source = RUN

    top_out = [{
        "idu": it["idu"], "commune": it["commune"],
        "statut": it.get("statut") or it.get("status"),
        "q_score": it.get("q_score"),
        "pourquoi": _pourquoi_lignes(it, sdp_besoin, carencees),
    } for it in top]
    return {"nom": derive_nom(fiche), "n": n, "sdp_besoin_m2": sdp_besoin,
            "programme_defini": programme is not None, "source": source, "top": top_out}


class ProjetIn(BaseModel):
    fiche: dict
    nom: str | None = None            # proposé par l'IA ; repli déterministe sinon
    filtres_extra: dict | None = None  # filtres additionnels de l'entretien (vue mer…)


class ProjetPatchIn(BaseModel):
    nom: str | None = None
    statut: str | None = None          # actif | archive
    fiche: dict | None = None          # re-dérive filtres + programme


@router.post("/derive")
def projet_derive(body: ProjetIn) -> dict:
    """Dérive nom + filtres + programme d'une fiche SANS persister — « Lancer la recherche »
    prévisualise avant que « Enregistrer ce projet » ne crée l'objet. Même dérivation
    déterministe que la création (aucun chiffre produit par l'IA)."""
    fiche = _valide_fiche(body.fiche or {})
    return {
        "nom": (body.nom or "").strip()[:160] or derive_nom(fiche),
        "fiche": fiche,
        "filtres": derive_filtres(fiche, body.filtres_extra),
        "programme": derive_programme(fiche),
        "sdp_besoin_m2": derive_sdp_besoin(fiche),
    }


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


@router.delete("/{pid}")
def projet_delete(pid: int, db: Session = Depends(get_db)) -> dict:
    """Supprime un projet (les pistes CRM rattachées gardent leur parcelle : projet_id → NULL
    par la FK ON DELETE SET NULL)."""
    p = db.get(models.Projet, pid)
    if not p:
        raise HTTPException(404, "Projet inconnu")
    db.delete(p)
    db.flush()
    return {"ok": True}


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


# ───────────────────────── Parcours de sélection (Tinder) — statuts parcelle×projet ─────────────────────────
# Le projet reste piloté par les critères ; ces routes gèrent l'ÉTAT de tri (proposee/retenue/
# ecartee/a_analyser). Zéro re-scoring : les parcelles viennent du run servi, on rattache un statut.

_STATUTS = {"proposee", "retenue", "ecartee", "a_analyser"}
_RETENUE_CRM_STATUS = "contact_a_preparer"    # colonne « Contact à préparer » (cf config/pipeline.yaml)


def _sync_crm_retenue(db: Session, pid: int, parcel_id: int, statut: str, now: datetime) -> None:
    """Auto-CRM + cohérence (Phase 2). `retenue` ⇒ crée l'entrée pipeline liée au projet (à
    contacter) ; quitter `retenue` ⇒ retire l'entrée AUTO-liée à CE projet (une entrée manuelle
    d'un autre projet est préservée : ON CONFLICT DO NOTHING / DELETE ciblé sur projet_id)."""
    if statut == "retenue":
        db.execute(text(
            "INSERT INTO pipeline_entries (parcel_id, status, priority, notes, prospection, "
            "projet_id, created_at, updated_at) VALUES (:pc, :st, 'moyenne', '', '{}'::jsonb, "
            ":pid, :now, :now) ON CONFLICT (parcel_id) DO NOTHING"),
            {"pc": parcel_id, "st": _RETENUE_CRM_STATUS, "pid": pid, "now": now})
    else:
        db.execute(text("DELETE FROM pipeline_entries WHERE parcel_id = :pc AND projet_id = :pid"),
                   {"pc": parcel_id, "pid": pid})


def _projet_or_404(db: Session, pid: int) -> models.Projet:
    p = db.get(models.Projet, pid)
    if not p:
        raise HTTPException(404, "Projet inconnu")
    return p


def _counts(db: Session, pid: int) -> dict:
    """Compteurs par statut (progression + sections)."""
    rows = db.execute(text("SELECT statut, count(*) AS n FROM projet_parcelles "
                           "WHERE projet_id = :p GROUP BY statut"), {"p": pid}).all()
    c = {r.statut: r.n for r in rows}
    return {"counts": {s: c.get(s, 0) for s in ("proposee", "retenue", "ecartee", "a_analyser")}}


def _search_items(db: Session, fiche: dict, limit: int, overrides: dict | None = None) -> list[dict]:
    """RÉUTILISE la recherche existante (M22 si programme, sinon run servi q_v6_m8) — même
    source que /apercu, jamais un re-scoring. Renvoie les items ordonnés (best-first).
    `overrides` assouplit les filtres dérivés (chercher plus : communes=None → île, surfaceMin↓)."""
    filtres = derive_filtres(fiche)
    if overrides:
        filtres = {**filtres, **overrides}      # None efface un filtre (ex. communes → toute l'île)
    programme = derive_programme(fiche)
    communes = filtres.get("communes")
    if programme:
        from .modules import ProgrammeIn, faisabilite_sens2
        res = faisabilite_sens2(ProgrammeIn(**programme), db)
        items = res.get("items", [])
        if communes:                                   # secteur : M22 balaie l'île → on restreint
            items = [it for it in items if it["commune"] in communes]
    else:
        from .app import _q_v2_list, _q_v2_where
        where, params = _q_v2_where(RUN, ",".join(filtres.get("statuts") or []) or None,
                                    filtres.get("scoreMin"), filtres.get("surfaceMin"),
                                    filtres.get("surfaceMax"), filtres.get("sdpMin"),
                                    bool(filtres.get("evenement")), bool(filtres.get("vueMer")),
                                    ",".join(filtres.get("flags") or []) or None,
                                    ",".join(communes) if communes else None,
                                    ",".join(filtres.get("flagsExclus") or []) or None)
        items = _q_v2_list(db, None, limit, 0, run_label=RUN, extra_where=where, extra_params=params)
    return items[:limit]


class ProposerIn(BaseModel):
    limit: int = 24


@router.post("/{pid}/proposer")
def projet_proposer(pid: int, body: ProposerIn, db: Session = Depends(get_db)) -> dict:
    """Propose au projet les parcelles de la recherche (statut `proposee`, best-first). UPSERT
    NON destructif : une parcelle déjà décidée (retenue/ecartee) n'est JAMAIS re-proposée
    (ON CONFLICT DO NOTHING) — une écartée ne ressuscite pas. Rejoue les critères du jour."""
    p = _projet_or_404(db, pid)
    lim = max(1, min(body.limit, 60))
    items = _search_items(db, p.fiche, lim)
    idus = [it["idu"] for it in items]
    id_by_idu = {r.idu: r.id for r in db.execute(
        text("SELECT id, idu FROM parcels WHERE idu = ANY(:idus)"), {"idus": idus})}
    now = datetime.now(timezone.utc)
    for rang, it in enumerate(items):
        pc = id_by_idu.get(it["idu"])
        if not pc:
            continue
        db.execute(text(
            "INSERT INTO projet_parcelles (projet_id, parcel_id, statut, rang, proposee_at, "
            "created_at, updated_at) VALUES (:pj, :pc, 'proposee', :rg, :now, :now, :now) "
            "ON CONFLICT (projet_id, parcel_id) DO NOTHING"),
            {"pj": pid, "pc": pc, "rg": rang, "now": now})
    db.flush()
    return {"ok": True, "propose": len(idus), "n_total": len(items),
            "sdp_besoin_m2": derive_sdp_besoin(p.fiche), **_counts(db, pid)}


@router.get("/{pid}/parcelles")
def projet_parcelles(pid: int, db: Session = Depends(get_db)) -> dict:
    """L'ÉTAT du parcours : les parcelles du projet groupées par statut (proposées best-first),
    avec centroïde pour la carte. Base de la reprise (fermer/rouvrir = relire cet état)."""
    p = _projet_or_404(db, pid)
    from .app import _score_v2_run_id
    v2 = _score_v2_run_id(db)
    rows = db.execute(text(
        """SELECT pp.statut, pp.rang, par.idu, par.commune, d.q_score, s2.tier,
                  ST_X(ST_Transform(ST_Centroid(par.geom_2975), 4326)) AS lng,
                  ST_Y(ST_Transform(ST_Centroid(par.geom_2975), 4326)) AS lat
           FROM projet_parcelles pp
           JOIN parcels par ON par.id = pp.parcel_id
           LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = par.id AND d.run_label = :run
           LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = par.idu AND s2.run_id = :v2
           WHERE pp.projet_id = :pid
           ORDER BY pp.rang NULLS LAST, pp.id"""),
        {"run": RUN, "v2": v2, "pid": pid}).mappings().all()
    groups: dict[str, list] = {s: [] for s in ("proposee", "retenue", "ecartee", "a_analyser")}
    for r in rows:
        groups.setdefault(r["statut"], []).append({
            "idu": r["idu"], "commune": r["commune"], "statut": r["statut"],
            "q_score": r["q_score"], "tier": r["tier"],
            "center": [round(r["lng"], 6), round(r["lat"], 6)] if r["lng"] is not None else None,
        })
    return {"nom": p.nom, "sdp_besoin_m2": derive_sdp_besoin(p.fiche),
            "proposees": groups["proposee"], "retenues": groups["retenue"],
            "ecartees": groups["ecartee"], "a_analyser": groups["a_analyser"], **_counts(db, pid)}


@router.get("/{pid}/carte/{idu}")
def projet_carte_decision(pid: int, idu: str, db: Session = Depends(get_db)) -> dict:
    """Carte de DÉCISION d'une parcelle : adresse, tier, scores + POINTS CLÉS (forces/attentions
    dérivés des facteurs — même logique déterministe que le pack apporteur). Aucune valeur
    inventée : tout vient de `_q_v2_fiche` (run servi). Le front ajoute « voir la fiche complète »."""
    _projet_or_404(db, pid)
    from .app import _q_v2_fiche
    from .partners import _points_cles
    f = _q_v2_fiche(db, idu)
    forces, attentions = _points_cles(f.get("lines") or [])
    sv = f.get("score_v2") or {}
    return {
        "idu": f["idu"], "adresse": f.get("adresse"), "commune": f.get("commune"),
        "surface_m2": f.get("surface_m2"), "tier": sv.get("tier"), "statut": f.get("statut"),
        "q_score": f.get("q_score"), "a_score": f.get("a_score"),
        "completeness": f.get("completeness_score"), "center": f.get("coords"),
        "forces": [{"titre": t, "detail": d} for _, t, d in forces],
        "attentions": [{"titre": t, "detail": d} for _, t, d in attentions],
    }


class StatutIn(BaseModel):
    statut: str


@router.patch("/{pid}/parcelle/{idu}")
def projet_parcelle_statut(pid: int, idu: str, body: StatutIn, db: Session = Depends(get_db)) -> dict:
    """Fixe le statut d'une parcelle dans le projet (le geste Tinder ET la récupération d'une
    écartée). RÉVERSIBLE : repasser en `proposee`/`retenue` depuis `ecartee` ne perd rien."""
    _projet_or_404(db, pid)
    if body.statut not in _STATUTS:
        raise HTTPException(422, f"Statut invalide : {body.statut}")
    pc = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
    if not pc:
        raise HTTPException(404, f"Parcelle {idu} inconnue")
    now = datetime.now(timezone.utc)
    db.execute(text(
        "INSERT INTO projet_parcelles (projet_id, parcel_id, statut, created_at, updated_at) "
        "VALUES (:pj, :pc, :st, :now, :now) "
        "ON CONFLICT (projet_id, parcel_id) DO UPDATE SET statut = :st, updated_at = :now"),
        {"pj": pid, "pc": pc, "st": body.statut, "now": now})
    _sync_crm_retenue(db, pid, pc, body.statut, now)   # auto-CRM + cohérence (Phase 2)
    db.flush()
    return {"ok": True, "idu": idu, "statut": body.statut, **_counts(db, pid)}


# ─── Chercher plus (Phase 2) : élargir la recherche / ajouter une parcelle à la main ───

def _upsert_proposee(db: Session, pid: int, parcel_id: int, rang: int, now: datetime) -> bool:
    """Rattache une parcelle en `proposee` — DÉDUP par la contrainte unique (une parcelle déjà
    dans le projet, quel que soit son statut, n'est PAS re-proposée). True si réellement ajoutée."""
    res = db.execute(text(
        "INSERT INTO projet_parcelles (projet_id, parcel_id, statut, rang, proposee_at, "
        "created_at, updated_at) VALUES (:pj, :pc, 'proposee', :rg, :now, :now, :now) "
        "ON CONFLICT (projet_id, parcel_id) DO NOTHING"),
        {"pj": pid, "pc": parcel_id, "rg": rang, "now": now})
    return res.rowcount == 1


class ChercherPlusIn(BaseModel):
    limit: int = 24
    surface_min: float | None = None    # assouplir la surface minimale
    ile: bool = False                   # élargir le périmètre à toute l'île


@router.post("/{pid}/chercher-plus")
def projet_chercher_plus(pid: int, body: ChercherPlusIn, db: Session = Depends(get_db)) -> dict:
    """Élargit la recherche (critères assouplis) et ajoute les NOUVELLES parcelles en `proposee`
    (dédupliquées). Zéro re-scoring : même moteur que la proposition, filtres relâchés."""
    p = _projet_or_404(db, pid)
    overrides: dict = {}
    if body.ile:
        overrides["communes"] = None
    if body.surface_min is not None:
        overrides["surfaceMin"] = body.surface_min
    lim = max(1, min(body.limit, 60))
    items = _search_items(db, p.fiche, lim, overrides=overrides or None)
    idus = [it["idu"] for it in items]
    id_by_idu = {r.idu: r.id for r in db.execute(
        text("SELECT id, idu FROM parcels WHERE idu = ANY(:idus)"), {"idus": idus})}
    maxr = db.execute(text("SELECT COALESCE(MAX(rang), -1) FROM projet_parcelles WHERE projet_id = :p"),
                      {"p": pid}).scalar() or -1
    now = datetime.now(timezone.utc)
    added = 0
    for i, it in enumerate(items):
        pc = id_by_idu.get(it["idu"])
        if pc and _upsert_proposee(db, pid, pc, maxr + 1 + i, now):
            added += 1
    db.flush()
    return {"ok": True, "n_added": added, "n_search": len(items),
            "elargi": bool(overrides), **_counts(db, pid)}


class AjouterIn(BaseModel):
    idu: str


@router.post("/{pid}/ajouter")
def projet_ajouter(pid: int, body: AjouterIn, db: Session = Depends(get_db)) -> dict:
    """Ajoute UNE parcelle précise (par IDU, ou clic-carte côté front) en `proposee`. Dédupliqué :
    `already=true` si elle est déjà dans le projet (quel que soit son statut)."""
    _projet_or_404(db, pid)
    pc = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": body.idu}).scalar()
    if not pc:
        raise HTTPException(404, f"Parcelle {body.idu} inconnue")
    maxr = db.execute(text("SELECT COALESCE(MAX(rang), -1) FROM projet_parcelles WHERE projet_id = :p"),
                      {"p": pid}).scalar() or -1
    added = _upsert_proposee(db, pid, pc, maxr + 1, datetime.now(timezone.utc))
    db.flush()
    return {"ok": True, "added": added, "already": not added, "idu": body.idu, **_counts(db, pid)}


@router.get("/{pid}/export.pdf")
def projet_export_pdf(pid: int, db: Session = Depends(get_db)):
    """Dossier PROJET en PDF : la fiche de cadrage + les meilleures parcelles avec leur
    « pourquoi » (aperçu recalculé sur les données ACTUELLES). Mécanique fpdf2 existante."""
    from fastapi.responses import Response

    from .export_commun import adresses_ban, format_adresse
    from .pdf_projet import render_projet_pdf
    p = db.get(models.Projet, pid)
    if not p:
        raise HTTPException(404, "Projet inconnu")
    apercu = projet_apercu(ApercuIn(fiche=p.fiche or {}, limit=5), db)
    # M6 2a : adresse postale BAN de chaque parcelle du top (1 requête, page 1 du PDF)
    adrs = adresses_ban(db, [it["idu"] for it in apercu.get("top", [])])
    for it in apercu.get("top", []):
        it["adresse_ban"] = format_adresse(adrs.get(it["idu"]))
    pdf = render_projet_pdf(_projet_dict(p), apercu)
    slug = "".join(c if c.isalnum() else "-" for c in (p.nom or "projet")).strip("-").lower()[:48]
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="projet-{slug or pid}.pdf"'})
