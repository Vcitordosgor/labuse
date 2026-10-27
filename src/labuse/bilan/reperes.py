"""BILAN-1 — repères et Sourcé du bilan, résolus par parcelle.

Doctrine : on ne pré-remplit que le Sourcé (public, sûr) — surface du terrain
(cadastre), zonage PLU, taux de TVA légaux (dans le catalogue). Le reste est vide,
avec un repère cliquable qui N'ENTRE PAS dans le calcul tant que le client ne
l'adopte pas. **Un repère dont la source ne se résout pas ne s'affiche pas** : toute
résolution est défensive (jamais un 500 sur une parcelle atypique) et renvoie None
en cas d'échec, auquel cas la pastille n'est pas servie.
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from sqlalchemy import text
from sqlalchemy.orm import Session

T = TypeVar("T")


def _sans_poison(db: Session, fn: Callable[[], T]) -> T | None:
    """Exécute une lecture best-effort sous SAVEPOINT : si elle échoue (table
    absente, parcelle atypique), le savepoint est annulé et la transaction de la
    requête reste UTILISABLE (sinon psycopg empoisonne toute la transaction)."""
    try:
        with db.begin_nested():
            return fn()
    except Exception:  # noqa: BLE001
        return None


def _parcelle(db: Session, idu: str) -> tuple[int, str] | None:
    def _q():
        row = db.execute(
            text("SELECT id, commune FROM parcels WHERE idu = :i"), {"i": idu}
        ).one_or_none()
        return (int(row[0]), str(row[1] or "")) if row else None

    return _sans_poison(db, _q)


def _surface(db: Session, idu: str) -> int | None:
    """Surface du terrain, ARRONDIE au m² (le cadastre la sert en flottant).

    CHASSE-DONNEES-FIX-1 (Lot 1) — surface de TERRAIN servie (contenance|dessin), comme la fiche et
    les calculs (CONTENANCE-1) : le repère « terrain » du Bilan lisait le dessin brut (+5,9 % CW0658)."""

    def _q():
        v = db.execute(
            text("SELECT COALESCE(contenance_m2, surface_m2) FROM parcels WHERE idu = :i"), {"i": idu}
        ).scalar()
        return round(float(v)) if v is not None else None

    return _sans_poison(db, _q)


def _zonage_detail(db: Session, parcel_id: int) -> dict | None:
    """Zonage servi : libellé + répartition par zone (parts) + part non
    constructible (familles ≠ U/AU)."""

    def _q():
        from ..faisabilite.zone_servie import FAMILLES_CONSTRUCTIBLES, zone_dominante

        z = zone_dominante(db, parcel_id)
        if not z or not z.zone:
            return None
        parts = [
            {"zone": p["zone"], "fam": p["fam"], "pct": round(float(p["pct"]), 1)}
            for p in (getattr(z, "parts", None) or [])
        ]
        if len(parts) > 1:
            label = " · ".join(f"{p['zone']} {round(p['pct'])} %" for p in parts)
        else:
            label = str(z.zone)
        nc = round(sum(p["pct"] for p in parts if p["fam"] not in FAMILLES_CONSTRUCTIBLES), 1)
        c = round(sum(p["pct"] for p in parts if p["fam"] in FAMILLES_CONSTRUCTIBLES), 1)
        return {"label": label, "parts": parts, "non_constructible_pct": nc, "constructible_pct": c}

    return _sans_poison(db, _q)


def sources_parcelle(db: Session, idu: str) -> dict[str, Any]:
    """Le Sourcé pré-rempli : surface du terrain (cadastre), zonage PLU, commune.
    `prix_achat_dvf` (info, hors calcul) best-effort → None si indisponible."""
    pc = _parcelle(db, idu)
    parcel_id = pc[0] if pc else None
    commune = pc[1] if pc else None
    terrain = _surface(db, idu)  # m² arrondi — Sourcé (cadastre)
    zd = _zonage_detail(db, parcel_id) if parcel_id else None
    nc_pct = zd["non_constructible_pct"] if zd else 0.0
    c_pct = zd["constructible_pct"] if zd else 100.0
    # terrain constructible = terrain × part U/AU, seulement s'il y a du non constructible
    constructible_m2 = (
        round(terrain * c_pct / 100.0)
        if terrain is not None and nc_pct > 0
        else None
    )
    return {
        "idu": idu,
        "parcel_id": parcel_id,
        "commune": commune,
        "terrain": terrain,
        "zonage": zd["label"] if zd else None,  # Sourcé (PLU)
        "zonage_parts": zd["parts"] if zd else [],
        "non_constructible_pct": nc_pct,
        "constructible_m2": constructible_m2,
        "prix_achat_dvf": _prix_achat_dvf(db, parcel_id) if parcel_id else None,
    }


def _prix_achat_dvf(db: Session, parcel_id: int) -> dict | None:
    """Dernier prix d'achat connu de la parcelle (DVF), pour affichage INFO (hors
    calcul, règle validée). Best-effort : None si aucune mutation lisible."""

    def _q():
        row = db.execute(
            text(
                "SELECT valeur_fonciere, date_mutation FROM dvf_mutations m "
                "JOIN dvf_mutation_parcelles mp ON mp.mutation_id = m.id "
                "WHERE mp.parcel_id = :p AND m.valeur_fonciere > 0 "
                "ORDER BY m.date_mutation DESC LIMIT 1"
            ),
            {"p": parcel_id},
        ).one_or_none()
        if not row:
            return None
        return {"valeur": float(row[0]), "date": str(row[1]), "label": "Dernier prix DVF"}

    return _sans_poison(db, _q)


def reperes_publics(db: Session, idu: str, sourcee: dict) -> dict[str, dict]:
    """Repères « registre » (source publique) résolus pour cette parcelle. Clé =
    registre_id du catalogue ; valeur = {valeur, label, source} ou absente si la
    source ne se résout pas (la pastille ne s'affiche alors pas)."""
    out: dict[str, dict] = {}
    parcel_id = sourcee.get("parcel_id")
    commune = sourcee.get("commune")

    # DVF neuf au m² — prix de sortie des produits (source unique LABUSE)
    if parcel_id is not None:

        def _dvf():
            from ..faisabilite.bilan import resolve_prix_sortie_servi

            d = resolve_prix_sortie_servi(db, parcel_id)
            if d and d.get("prix") and not d.get("non_calculable"):
                return {
                    "valeur": float(d["prix"]),
                    "n": d.get("n"),
                    "label": d.get("label") or f"DVF neuf {round(d['prix'])} €/m²",
                    "source": "DVF (ventes de logements neufs)",
                }
            return None

        dvf = _sans_poison(db, _dvf)
        if dvf:
            out["dvf_neuf"] = dvf

    # Outil Taxe — taxe d'aménagement (part communale) au m² de surface taxable
    def _taxe():
        from .. import taxe_amenagement as ta

        cfg = ta.config()
        vf = float(cfg["valeur_forfaitaire_m2"]["hors_idf"])
        tp = ta.taux_parcelle(db, idu)
        pct = tp.get("part_communale_pct") if tp else None
        if not pct:
            return None
        # DOCS-COHERENCE-1 (recette Vic) — taxe d'aménagement = part COMMUNALE + part DÉPARTEMENTALE
        # (2,5 % confirmé pour La Réunion) : on pré-remplit le TOTAL sourcé en disant les deux parts.
        pct_dep = float(cfg["taux"].get("part_departementale_defaut") or 0.0)
        val_com = round(vf * float(pct) / 100.0, 2)
        val_dep = round(vf * pct_dep / 100.0, 2)
        val = round(val_com + val_dep, 2)
        return {
            "valeur": val,
            "label": f"Outil Taxe : {val:g} €/m²",
            "source": (f"taxe d'aménagement = part communale {pct:g} % ({val_com:g} €/m²) + part "
                       f"départementale {pct_dep:g} % ({val_dep:g} €/m²), sur {vf:g} €/m² (La Réunion)"),
        }

    taxe = _sans_poison(db, _taxe)
    if taxe:
        out["outil_taxe"] = taxe

    # Redevance d'archéologie préventive — 0,40 % de la valeur forfaitaire au m²
    def _rap():
        from .. import taxe_amenagement as ta

        cfg = ta.config()
        vf = float(cfg["valeur_forfaitaire_m2"]["hors_idf"])
        val = round(vf * ta._RAP_PCT / 100.0, 2)
        return {
            "valeur": val,
            "label": f"Redevance : {val:g} €/m²",
            "source": "redevance d'archéologie préventive — 0,40 % de la valeur forfaitaire",
        }

    rap = _sans_poison(db, _rap)
    if rap:
        out["redevance_archeologie"] = rap

    # Faisabilité LABUSE — SDP possible reprise de la fiche (repère de SDP pour le Bilan).
    # IMPLANTATION-4 (LOT B) — on NE renvoie PLUS le nombre de logements de l'ancien moteur : le Bilan
    # ne doit pas pré-remplir un nombre de logements depuis la faisabilité estimée (il se pré-remplit
    # « depuis l'Étude » via le pont de l'écran d'étude, ou reste vide/saisi). On ne garde que la SDP.
    if parcel_id is not None:

        def _fais():
            from ..faisabilite.scenarios import faisabilite_scenario

            d = faisabilite_scenario(db, parcel_id)
            sdp = d.get("sdp_possible_m2") if isinstance(d, dict) else None
            if not sdp:
                return None
            return {
                "valeur": float(sdp),
                # IMPLANTATION-4 (LOT C) — SDP de l'ancien moteur = « SDP maximale réglementaire »
                # (jamais « SDP du scénario », réservé à l'Étude) : les deux libellés ne se croisent jamais.
                "label": f"SDP maximale réglementaire {round(float(sdp)):g} m² (estimation)",
                "source": "faisabilité LABUSE (estimation, à confirmer)",
                "parkings": d.get("stationnement_places"),
            }

        fais = _sans_poison(db, _fais)
        if fais:
            out["faisabilite"] = fais

    # Sitadel — délai médian dépôt → autorisation (PC) de la commune
    if commune:

        def _sitadel():
            row = db.execute(
                text(
                    "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY delai_mois) "
                    "FROM m10_permit_delais WHERE commune = :c AND nature = 'PC' "
                    "AND valide AND delai_mois IS NOT NULL"
                ),
                {"c": commune},
            ).scalar()
            if row is None:
                return None
            m = round(float(row))
            return {
                "valeur": float(m),
                "label": f"Sitadel : {m} mois dépôt → PC",
                "source": "Sitadel — délai médian dépôt→autorisation (PC) de la commune",
            }

        sit = _sans_poison(db, _sitadel)
        if sit:
            out["sitadel"] = sit

    # Coût de construction de référence (€/m² SDP) — calibrage par commune
    def _cout():
        from ..faisabilite.engine import Hypotheses

        h = Hypotheses.charger(commune or None)
        bas, haut = h.cout_construction_m2_bas, h.cout_construction_m2_haut
        if bas and haut:
            mid = round((bas + haut) / 2.0)
            return {
                "valeur": float(mid),
                "label": f"Coût de référence {mid} €/m²",
                "source": "calibrage de construction LABUSE",
            }
        return None

    cout = _sans_poison(db, _cout)
    if cout:
        out["cout_construction_ref"] = cout

    return out


def bilan_prefill(db: Session, idu: str) -> dict[str, Any]:
    """DOCS-COHERENCE-1 (recette Vic) — pré-remplissages SOURCÉS du Bilan (PDF = écran) : terrain
    (contenance cadastrale), taxe d'aménagement (part communale + départementale), redevance
    d'archéologie (0,40 %), + métadonnées d'en-tête (adresse BAN, commune, date des données servies).
    Jamais un chiffre inventé : un repère non résolu reste « À renseigner »."""
    from .moteur import SOURCE, SaisiePoste

    sourcee = sources_parcelle(db, idu) or {}
    rp = reperes_publics(db, idu, sourcee) or {}
    postes: dict[str, SaisiePoste] = {}
    taxe = rp.get("outil_taxe")
    if taxe and taxe.get("valeur"):
        postes["txLog"] = SaisiePoste(valeur=float(taxe["valeur"]), etat=SOURCE)
    rap = rp.get("redevance_archeologie")
    if rap and rap.get("valeur"):
        postes["archeo"] = SaisiePoste(valeur=float(rap["valeur"]), etat=SOURCE)
    adresse = None
    try:
        from ..courrier import adresse_ban_parcelle
        adresse = _sans_poison(db, lambda: adresse_ban_parcelle(db, idu))
    except Exception:  # noqa: BLE001
        adresse = None
    try:
        from ..exports.builder import _donnees_labuse_au
        donnees_au = _donnees_labuse_au()
    except Exception:  # noqa: BLE001
        donnees_au = None
    return {
        "terrain": sourcee.get("terrain"),
        "postes": postes,
        "adresse": adresse or "",
        "commune": sourcee.get("commune") or "",
        "donnees_au": donnees_au,
    }
