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
    # CHIRURGICAL-FIX-1 (E104) — le modèle doit porter le MÊME verdict que la fiche, lu au point
    # unique `potentiel_batir`. La part non constructible par famille (A/N) ne suffit pas : une
    # parcelle en famille U mais non constructible pour une AUTRE raison (habitat interdit en UE,
    # PPR zone rouge) était présentée 100 % constructible. Si le verdict FERME la parcelle, le
    # modèle la porte 100 % non constructible et NOMME le motif.
    # CHIRURGICAL-FIX-1 (LOT I 1f) — SATURATION N'EST PAS INTERDICTION : une parcelle CONSTRUCTIBLE
    # mais sans surface résiduelle (`rien_a_batir` alors que `constructible=True`, IS0448 : SDP 0)
    # reste constructible — elle NE passe PAS à 100 % non constructible (c'était un motif vide, faux).
    # Seule une non-constructibilité RÉELLE (`constructible=False`) ferme la parcelle.
    non_constructible_motif = None
    if parcel_id is not None:
        try:
            from ..faisabilite.potentiel_batir import potentiel_batir
            pb = potentiel_batir(db, idu)
            if pb and not pb.get("constructible", True):
                nc_pct = 100.0
                c_pct = 0.0
                non_constructible_motif = pb.get("motif")
        except Exception:  # noqa: BLE001 — enrichissement additif, jamais bloquant
            pass
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
        "non_constructible_motif": non_constructible_motif,
        "constructible_m2": constructible_m2,
        "prix_achat_dvf": _prix_achat_dvf(db, parcel_id) if parcel_id else None,
    }


def garde_fou_bilan(db: Session, idu: str, sdp_saisie: float | None = None,
                    postes_saisis: set[str] | None = None,
                    programme_saisi: bool = True,
                    suv_saisie: float | None = None) -> dict[str, Any]:
    """CHIRURGICAL-FIX-1 (LOT K 2b / LOT L 2 / LOT M 3) — le GARDE-FOU en tête du Bilan. Un Bilan chiffre
    un programme ; s'il contredit ce que le Dossier retient, on le dit EN TÊTE, avec le motif :
      · parcelle non constructible / habitat interdit → motif de la fiche, et AUCUNE « surface à retenir »
        (le Dossier ne donne pas de capacité résidentielle : on ne cite JAMAIS une ancienne simulation) ;
      · la SDP SAISIE dépasse la **surface À RETENIR du Dossier** (la règle unique `surface_a_retenir`,
        prudente — PAS l'estimation haute « table rase ») → on compare au MÊME seuil que l'Excel ;
      · scénario « terrain libéré » (démolition) → on le DIT en tête, et si aucun **coût de démolition**
        n'est saisi, on le signale (le bilan sous-estime alors les dépenses).
    `programme_saisi` = False quand le Bilan est livré SANS programme (l'outil le produit de lui-même) :
    le bandeau dira « aucun programme », pas « programme saisi ». Renvoie
    `{alertes, surface_a_retenir, terrain_libere, non_constructible, sdp_saisie, programme_saisi}`."""
    src = sources_parcelle(db, idu) or {}
    motif_nc = src.get("non_constructible_motif")
    sar_val = None
    terrain_libere = False
    try:
        from ..faisabilite.surface_retenue import estimation_rapide_m2, surface_a_retenir
        from ..exports.etude_faisabilite import scenario_etude_persiste
        est = estimation_rapide_m2(db, idu)
        scn = scenario_etude_persiste(db, idu)
        bati = bool(_emprise_batie(db, idu))
        if est not in (None, "") or scn is not None:
            sar = surface_a_retenir(est, scn, bati=bati, copropriete=False)
            sar_val = sar.get("valeur_m2")
            # « terrain libéré » = la surface retenue suppose la DÉMOLITION du bâti existant.
            terrain_libere = bati and "terrain libéré" in (sar.get("phrase") or "").lower()
    except Exception:  # noqa: BLE001 — surface à retenir non résolue : on garde le reste du garde-fou
        pass
    # LOT M 3 — habitat interdit / non constructible : le Dossier ne donne AUCUNE capacité résidentielle.
    # On écarte toute « surface à retenir » (sinon on citait 8 125 m² d'une ancienne simulation d'AM0838)
    # et le scénario « terrain libéré » (pas de logements à y construire) : seul le motif reste.
    if motif_nc:
        sar_val = None
        terrain_libere = False
    # LOT N 3 — la capacité « bâti conservé » du Dossier (SDP résiduelle, §3) : IS0448 = 0 m² en l'état,
    # ~85 m² en terrain libéré. Le bandeau « Aucun programme » reprend CETTE distinction (jamais un faux
    # « aucune capacité à bâtir »).
    cap_batie_conservee = None
    if not motif_nc:
        try:
            pid = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
            if pid:
                cap_batie_conservee = db.execute(text(
                    "SELECT sdp_residuelle_m2 FROM parcel_residuel WHERE parcel_id = :p"), {"p": pid}).scalar()
        except Exception:  # noqa: BLE001 — lecture annexe, jamais bloquante
            cap_batie_conservee = None
    cap_terrain_libere = sar_val if terrain_libere else None
    alertes: list[str] = []
    if motif_nc:
        alertes.append(motif_nc)
    if terrain_libere:
        alertes.append("Scénario « terrain libéré » : le potentiel suppose la démolition du bâti existant.")
        if not (postes_saisis and "demol" in postes_saisis):
            alertes.append("Coût de démolition non renseigné — les dépenses sont sous-estimées.")
    # LOT M 3 — MÊME seuil que l'Excel (`SDP > round(surface_à_retenir)`), au mètre près : plus d'écart
    # d'un mètre entre le PDF (ancien `round(sar)+1`) et le tableur.
    if (sdp_saisie and isinstance(sdp_saisie, (int, float)) and isinstance(sar_val, (int, float))
            and round(sdp_saisie) > round(sar_val)):
        alertes.append(
            f"La surface de plancher saisie ({round(sdp_saisie)} m²) dépasse la surface à retenir du "
            f"Dossier ({round(sar_val)} m²).")
    # LOT N 2 — COHÉRENCE surface vendable / surface de plancher, dans le garde-fou → affichée DANS LE
    # PDF **et** dans l'Excel (bandeau), comme à l'écran. Comparaison sur les DÉCIMALES (pas d'arrondi :
    # 595,1 > 595 alerte) ; une surface vendable positive avec une SDP nulle ou vide est aussi incohérente.
    if (isinstance(suv_saisie, (int, float)) and suv_saisie > 0
            and suv_saisie > (sdp_saisie if isinstance(sdp_saisie, (int, float)) else 0.0)):
        _sdp_txt = f"{round(sdp_saisie)} m²" if isinstance(sdp_saisie, (int, float)) and sdp_saisie else "nulle / non renseignée"
        alertes.append(
            f"Surface vendable ({round(suv_saisie)} m²) supérieure à la surface de plancher "
            f"({_sdp_txt}) — incohérent (le chiffre d'affaires est surestimé).")
    return {"alertes": alertes, "surface_a_retenir": sar_val, "terrain_libere": terrain_libere,
            "non_constructible": bool(motif_nc), "sdp_saisie": sdp_saisie,
            "programme_saisi": programme_saisi,
            "capacite_batie_conservee_m2": cap_batie_conservee, "capacite_terrain_libere_m2": cap_terrain_libere}


def bandeau_sans_programme(gf: dict[str, Any]) -> tuple[str, str]:
    """CHIRURGICAL-FIX-1 (LOT N 3) — titre + texte du bandeau d'un Bilan livré SANS programme, PARTAGÉ
    par le PDF et l'Excel. Il reprend la DISTINCTION du Dossier (0 m² bâti conservé / ~85 m² terrain
    libéré sur IS0448) au lieu d'un faux « aucune capacité à bâtir »."""
    titre = "Aucun programme — parcelle écartée par LABUSE"
    base = ("Aucun programme n'a été saisi : ce bilan ne porte que les repères de la parcelle "
            "(terrain, taxes).")
    cons = gf.get("capacite_batie_conservee_m2")
    libere = gf.get("capacite_terrain_libere_m2")
    if gf.get("non_constructible"):
        capacite = "LABUSE n'y retient aucune capacité résidentielle"
    elif isinstance(libere, (int, float)) and libere:
        # le Dossier distingue le bâti conservé (SDP résiduelle, souvent 0) et le terrain libéré.
        capacite = (f"Le Dossier distingue {round(cons) if isinstance(cons, (int, float)) else 0} m² en "
                    f"l'état (bâti conservé) et ~{round(libere)} m² estimés en terrain libéré (démolition)")
    elif isinstance(cons, (int, float)):
        capacite = f"Le Dossier retient {round(cons)} m² (bâti conservé)"
    else:
        capacite = "LABUSE n'y retient pas de capacité à bâtir exploitable"
    bas = f"{base} {capacite} — le résultat reste « non calculable »."
    return titre, bas


def _emprise_batie(db: Session, idu: str) -> float | None:
    """Emprise bâtie (m²) de la parcelle — pour savoir si un scénario est « terrain libéré ». Lue de
    `p_model_bati` (BD TOPO), la même source que la fiche. Best-effort (jamais un bloqueur)."""
    try:
        return db.execute(text(
            "SELECT emprise_bati_m2 FROM p_model_bati WHERE idu = :i"), {"i": idu}).scalar()
    except Exception:  # noqa: BLE001
        return None


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
                # IMPLANTATION-4 (LOT C) — SDP de l'ancien moteur = « surface de plancher estimée »
                # (jamais « SDP du scénario », réservé à l'Étude) : les deux libellés ne se croisent jamais.
                # CAPACITE-1 (B1) — ce n'est PAS un maximum réglementaire (occupation = hypothèse) :
                # on la nomme « estimée », jamais « maximale réglementaire ».
                "label": f"Surface de plancher estimée {round(float(sdp)):g} m²",
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
