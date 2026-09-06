"""O2 — SCOREUR D'ADRESSE INVERSÉ : « je visite ce terrain, qu'en dit LA BUSE ? »

Entrée : une adresse (+ optionnellement le prix DEMANDÉ, saisi À LA MAIN — jamais scrapé).
Chemin : adresse → BAN (géocodage) → point → parcelle CONTENANT le point (déjà en base, déjà
scorée) → verdict compact. Si un prix est saisi, on le confronte à la charge foncière supportable
et au prix probable du foncier (Score É V2, O0) — sans jamais prétendre que c'est LE prix.

Réutilise l'existant : géocodage BAN via la fonction UNIQUE `geocode.geocode_ban` (partagée avec
`audit.audit_by_address` — CONNEXIONS-2 Lot 9.2, plus deux implémentations divergentes), run servi lu
depuis `Q_A_RUN_LABEL` (config/served_run.txt), table `score_e`. Île entière (pas de restriction
commune-pilote : on lit une parcelle déjà en base, aucune ingestion live). Zéro scraping.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import config
from .. import runs

log = logging.getLogger("labuse.scoreur")
router = APIRouter(prefix="/scoreur-adresse", tags=["scoreur-adresse"])

# M135 — échelle d'action, mapping canonique unique (tiers_client)
# M137 — le CHIP COURT (v[0]) : un seul vocabulaire servi partout, celui des chips.
from ..scoring.tiers_client import TIERS_CLIENT as _TC
_TIER_LABELS = {k: v[0] for k, v in _TC.items()}


class ScoreurIn(BaseModel):
    q: str                              # adresse libre
    prix_demande_eur: float | None = None   # prix affiché/demandé, saisi manuellement
    idu: str | None = None              # M82 (CAS E) : parcelle DÉJÀ résolue par l'autocomplétion interne
    # FUSION « Étudier un bien » (Vic 21/08/2026) : le CONSTAT servi (tier + charge CALIBRÉE + faits
    # sourcés + prix terrain nu de zone). ADDITIF, défaut False → les appelants historiques (copilote
    # v1) ne paient pas le compute_bilan_servi. Le prix probable `score_e` reste servi (legacy), mais
    # l'outil fusionné ne l'affiche pas : il lit `terrain_zone` (référentiel unique).
    with_constat: bool = False


def _geocode(q: str) -> dict:
    """CONNEXIONS-2 Lot 9.2 (KO-13) — délègue au géocodeur BAN UNIQUE (`geocode.geocode_ban`) et
    traduit ses erreurs en HTTP. Plus de client httpx ni de BAN_URL réimplémentés ici."""
    from .. import geocode
    try:
        return geocode.geocode_ban(q, ua="LA-BUSE/0.1 (+scoreur)")
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except geocode.BanIntrouvable as e:
        raise HTTPException(404, str(e)) from e
    except geocode.BanIndisponible as e:
        raise HTTPException(503, str(e)) from e


_AVERT = "Estimé — ni un prix ni une promesse ; hypothèses de bilan génériques."


def _prix_constat(prix: float, charge, prix_probable, surface) -> dict:
    """M128-6-§1 — CONSTAT chiffré nu confronté à un prix SAISI par un tiers. Deux règles :

      - §1 : la `charge` vient de la MÉTHODE DOCUMENTS (bilan à rebours, `compute_bilan`), jamais de
        `score_e` (barème sectoriel, systématiquement optimiste — cf. registre de dette M128).
      - §1.3 : AUCUN verdict, aucune conclusion. « bonne affaire », « au-dessus du marché »,
        « rentable », « validé » sont bannis — on sert les NOMBRES et leur méthode, le lecteur conclut.

    Le prix probable du foncier (médiane terrain sectorielle) est NON divergent : servi tel quel."""
    out: dict = {"prix_saisi_eur": round(prix)}
    if surface and surface > 0:
        out["prix_saisi_m2_terrain"] = round(prix / surface)
    if prix_probable is not None:
        out["prix_probable_foncier_eur"] = round(prix_probable)
        out["ecart_vs_prix_probable_pct"] = (round(100 * (prix - prix_probable) / prix_probable)
                                             if prix_probable else None)
    if charge is not None:
        out["charge_fonciere_supportable_eur"] = round(charge)   # méthode documents (bilan à rebours)
        out["marge_a_ce_prix_eur"] = round(charge - prix)
        out["methode"] = ("Constat chiffré, aucun verdict. Marge à ce prix = charge foncière "
                          "supportable (bilan à rebours, méthode documents) − prix saisi ; repère "
                          "foncier = médiane terrain sectorielle.")
    else:
        out["message"] = ("Charge foncière (méthode documents) non calculable pour cette parcelle — "
                          "marge non chiffrable.")
    out["avertissement"] = _AVERT
    return out


def get_db():
    from .app import get_db as _g
    yield from _g()


@router.post("")
def scoreur_adresse(body: ScoreurIn, db: Session = Depends(get_db)) -> dict:
    """Adresse → parcelle en base → verdict compact (+ confrontation du prix demandé si fourni)."""
    # M82 (CAS E) : si l'autocomplétion interne a DÉJÀ rattaché une parcelle (idu), on l'utilise
    # directement — le re-géocodage BAN du label formaté (« 12 Rue…, Saint-Paul (97460) ») pouvait
    # retomber hors de la parcelle et fabriquer un « aucune parcelle » fantôme.
    _sel = """SELECT p.idu, p.commune, p.section, p.numero, round(p.surface_m2) AS surface_m2,
                     s2.tier, s2.rang, s2.percentile
              FROM parcels p
              LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :run """
    if body.idu:
        label = body.q
        row = db.execute(text(_sel + "WHERE p.idu = :idu LIMIT 1"),
                         {"run": runs.current(), "idu": body.idu}).mappings().first()
    else:
        geo = _geocode(body.q)
        label = geo["label"]
        row = db.execute(text(_sel + "WHERE ST_Contains(p.geom, ST_SetSRID(ST_Point(:lon, :lat), 4326)) "
                              "ORDER BY p.surface_m2 DESC NULLS LAST LIMIT 1"),
                         {"run": runs.current(), "lon": geo["lon"], "lat": geo["lat"]}).mappings().first()
    if not row:
        return {"ok": False, "adresse": label,
                "message": "Aucune parcelle en base à cette adresse — hors périmètre couvert, "
                           "ou terrain non cadastré. Essayez l'audit par référence cadastrale."}

    tier = row["tier"]
    verdict = {"tier": tier, "libelle": _TIER_LABELS.get(tier, "Non évaluée"),
               "rang": row["rang"], "percentile": float(row["percentile"]) if row["percentile"] is not None else None}

    # M128-5-§2 / M128-6-§1 : aucune marge score_e (barème sectoriel) servie à un tiers. Le prix
    # probable du foncier (médiane terrain sectorielle) est NON divergent → lu tel quel dans score_e.
    # La CHARGE, elle, ne vient plus de score_e mais de la MÉTHODE DOCUMENTS (compute_bilan), et
    # seulement si un prix est saisi (§1). Aucun chiffre de marge auto-affiché.
    prix_probable = None
    try:
        if db.execute(text("SELECT to_regclass('score_e')")).scalar() is not None:
            se = db.execute(text(
                "SELECT estimable, prix_probable FROM score_e WHERE idu = :i"),
                {"i": row["idu"]}).mappings().first()
            if se and se["estimable"]:
                prix_probable = se["prix_probable"]
    except Exception:  # noqa: BLE001
        pass

    out = {"ok": True, "adresse": label, "idu": row["idu"], "commune": row["commune"],
           "section": row["section"], "numero": row["numero"], "surface_m2": row["surface_m2"],
           "verdict": verdict,
           "fiche_url": f"/parcels/{row['idu']}"}
    if body.prix_demande_eur is not None:
        # M128-6-§1 : charge = bilan à rebours (compute_bilan), calculé à la volée (37–237 ms mesurés,
        # non prohibitif sur une route déjà géocodante). Éphémère : aucune bascule, aucun rebuild.
        charge = None
        try:
            from ..faisabilite.bilan import compute_bilan_servi
            from ..faisabilite.db import parcel_faisabilite
            pid = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": row["idu"]}).scalar()
            fa = parcel_faisabilite(db, pid) if pid else None
            if fa:
                b, ps = compute_bilan_servi(db, pid, fa)
                if b is not None and not (ps or {}).get("non_calculable"):
                    charge = (b.charge_fonciere or {}).get("central")
        except Exception:  # noqa: BLE001
            pass
        out["prix"] = _prix_constat(float(body.prix_demande_eur), charge, prix_probable, row["surface_m2"])

    if body.with_constat:
        # CONSTAT servi (fusion « Étudier un bien ») : la charge CALIBRÉE (bilan à rebours par
        # secteur — méthode documents, « aux hypothèses calibrées ») + les faits sourcés + le prix
        # terrain nu de zone (référentiel UNIQUE). Éphémère, aucune bascule. Jamais un faux chiffre :
        # capacité non résolue / prix social-dominant → `charge_calibree=None` + motif honnête.
        out["constat"] = _constat_servi(db, row["idu"], row["commune"])
    return out


def _constat_servi(db: Session, idu: str, commune: str | None) -> dict:
    """Le CONSTAT calibré d'une parcelle : verdict déjà porté par le tier (lu en amont), ici la
    charge foncière CALIBRÉE (compute_bilan_servi — par secteur, non réglable) + les faits sourcés
    (SDP vendable, SDP plancher, prix de sortie neuf, terrain) + le prix terrain nu de la ZONE
    (référentiel unique `prix_terrain_nu_zone`). Aucun verdict marché (M128-6 tient)."""
    from ..faisabilite.bilan import compute_bilan_servi, resolve_prix_sortie_servi  # noqa: F401
    from ..faisabilite.db import parcel_faisabilite
    from ..faisabilite.engine import Hypotheses
    from ..faisabilite.marche_commune import prix_terrain_nu_zone
    out: dict = {"charge_calibree": None, "sourced": None, "terrain_zone": None, "motif": None,
                 "dernieres_ventes": []}
    # OUTILS-FIX-4 B3 — DERNIÈRES VENTES DE CETTE PARCELLE : l'historique DVF de la parcelle (mutations
    # actées portant SON idu) existe en base (dvf_mutations_parcelle) mais l'écran ne servait que les
    # médianes de secteur. On le sert — date, prix, surface(s) — servi tel quel (Sourcé, ventes actées),
    # borné aux 6 plus récentes. Hors du try du bilan : l'historique s'affiche même sur une parcelle non
    # constructible (motif capacite_non_resolue), avec un état vide honnête côté écran quand la liste est
    # vide. Aucune médiane, aucun calcul : les lignes brutes de la mutation.
    try:
        out["dernieres_ventes"] = [
            {"date": r["date_mutation"].isoformat() if r["date_mutation"] else None,
             "prix": float(r["valeur_fonciere"]) if r["valeur_fonciere"] is not None else None,
             "surface_bati_m2": round(r["surface_reelle_bati"]) if r["surface_reelle_bati"] else None,
             "surface_terrain_m2": round(r["surface_terrain"]) if r["surface_terrain"] else None,
             "type": r["type_local"], "nature": r["nature_mutation"]}
            for r in db.execute(text(
                # UNE ligne par MUTATION (une vente), pas par type_local : une même vente porte souvent
                # plusieurs lignes DVF (Maison + Dépendance…) — DISTINCT ON garde la plus « bâtie » (le
                # local principal), sinon la vente s'afficherait deux fois. Puis tri par date décroissante.
                "SELECT date_mutation, valeur_fonciere, surface_reelle_bati, surface_terrain, "
                "       type_local, nature_mutation FROM ("
                "  SELECT DISTINCT ON (id_mutation) date_mutation, valeur_fonciere, surface_reelle_bati, "
                "         surface_terrain, type_local, nature_mutation FROM dvf_mutations_parcelle "
                "  WHERE id_parcelle = :i "
                "  ORDER BY id_mutation, surface_reelle_bati DESC NULLS LAST) m "
                "ORDER BY date_mutation DESC NULLS LAST LIMIT 6"),
                {"i": idu}).mappings().all()]
    except Exception:  # noqa: BLE001 — l'historique parcelle est un bonus, jamais un 500
        out["dernieres_ventes"] = []
    try:
        pid = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
        fa = parcel_faisabilite(db, pid) if pid else None
        if not fa or not fa[1].constructible:
            out["motif"] = "capacite_non_resolue"
            return out
        ctx, f = fa
        out["terrain_zone"] = prix_terrain_nu_zone(db, commune, ctx.zone)
        shab = (f.fourchette or {}).get("shab_vendable_m2")
        coef = float(Hypotheses.charger(commune).coef_rendement)
        b, ps = compute_bilan_servi(db, pid, fa)
        out["sourced"] = {
            "shab_vendable_m2": round(shab) if shab else None,
            "sdp_plancher_m2": round(shab / coef) if (shab and coef) else None,
            "coef_rendement": coef,
            "terrain_m2": round(ctx.surface_m2) if ctx.surface_m2 else None,
            "prix_sortie_median": (ps["prix"] if ps and not ps.get("non_calculable") else None),
            "prix_neuf_label": (ps.get("label") if ps else None),
        }
        if ps and ps.get("non_calculable"):
            out["motif"] = "prix_sortie_non_calculable"
        elif b is not None and b.fiable and b.charge_fonciere:
            out["charge_calibree"] = {"central": b.charge_fonciere.get("central"),
                                      "par_m2_terrain": b.charge_fonciere.get("par_m2_terrain"),
                                      "ca_central": (b.ca or {}).get("central")}
    except Exception as exc:  # noqa: BLE001 — le constat est un bonus, jamais un 500
        log.warning("constat servi %s : %s", idu, exc)
        out["motif"] = out["motif"] or "indisponible"
    return out
