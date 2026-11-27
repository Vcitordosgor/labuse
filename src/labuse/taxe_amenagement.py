"""K3 (rattrapage KelFoncier) — CALCULETTE de la taxe d'aménagement.

Formule publique (code général des impôts). Assiette = surface taxable × valeur forfaitaire au m²
(+ forfaits d'installations : piscine, PV au sol, stationnement extérieur, éoliennes) ;
abattement de 50 % sur les 100 premiers m² d'une résidence principale et sur les logements aidés ;
taxe = assiette × (part communale + part départementale).

DOCTRINE : aucun taux inventé. Le taux COMMUNAL vient des délibérations (source DGFiP / DELTA) →
si absent, `taux_communal_pct=None` et le total N'EST PAS calculé (l'appelant dit « taux communal non
renseigné, à saisir »). Le taux départemental du 974 est fourni par la configuration datée.
Les valeurs forfaitaires viennent d'une config DATÉE et SOURCÉE (config/taxe_amenagement.yaml).

Résultat DÉTAILLÉ ligne par ligne : un promoteur doit pouvoir vérifier chaque ligne, pas juste un total.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict

from sqlalchemy import text

from .tz import today_reunion   # FIX-ORFEVRE-1 pt 3 (ORF-17) — jour Réunion, jamais le fuseau du process

from .config import load_yaml_config

# TAXE-AMÉNAGEMENT-1 lot C — un taux public non rafraîchi depuis plus d'un an est signalé
# (les taux se votent avant le 1er juillet pour l'année suivante ; DELTA republie 2×/an). Le
# repère est notre date d'INGESTION (maj_at) — un taux voté en 2022 et jamais redélibéré reste
# le taux courant ; ce qui peut vieillir, c'est notre relevé de la source.
_PERIME_JOURS = 365


def _fr_date(d) -> str | None:
    """JJ/MM/AAAA à partir d'un date/datetime/ISO — None si absent."""
    if d is None:
        return None
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d[:10])
        except ValueError:
            return d
    return d.strftime("%d/%m/%Y")

# CIRCUIT-3 lot 6.2 — table des taux COMMUNAUX PUBLICS de taxe d'aménagement (délibérations /
# base publique DGFiP). Seedée VIDE : la doctrine « aucun taux inventé » interdit de deviner un
# taux ; les valeurs viennent de la source officielle (voir docs SOURCES-1). Quand un taux public
# existe pour une commune, la calculette CESSE d'exiger un taux saisi.
_TAUX_DDL = """
CREATE TABLE IF NOT EXISTS taxe_amenagement_taux (
  insee varchar(5) PRIMARY KEY,
  part_communale_pct double precision NOT NULL,
  source text,
  delib_date date,
  maj_at timestamptz NOT NULL DEFAULT now()
)
"""


def ensure_taux_table(engine) -> None:
    with engine.begin() as c:
        c.execute(text(_TAUX_DDL))


# TAXE-FIX-1 point 3 — SECTEURS À TAUX MAJORÉ. La commune peut voter, sur des SECTEURS délimités, un
# taux supérieur au taux général (jusqu'à 20 % — CGI art. 1635 quater E/F). DELTA porte ces secteurs
# au grain PARCELLE (colonnes prefixe/section/parcelle) : le « secteur » est une LISTE de parcelles.
# On les stocke par IDU (la « géométrie » = l'identité cadastrale exacte, jointure sûre, pas une
# intersection approchée). 6 communes du 974 en ont (Saint-Paul 10 %, Saint-Leu 14 %, Trois-Bassins
# 20 %, Les Avirons 10 %, Entre-Deux 8,5 %, Le Port 5 % — relevé DELTA 24/09/2026).
_SECTEUR_DDL = """
CREATE TABLE IF NOT EXISTS taxe_amenagement_secteur (
  idu varchar(14) PRIMARY KEY,
  insee varchar(5) NOT NULL,
  part_communale_pct double precision NOT NULL,
  source text,
  delib_date date,
  maj_at timestamptz NOT NULL DEFAULT now()
)
"""


def ensure_secteur_table(engine) -> None:
    with engine.begin() as c:
        c.execute(text(_SECTEUR_DDL))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_ta_secteur_insee "
                       "ON taxe_amenagement_secteur(insee)"))


def taux_communal_public(db, insee: str | None, *, today: date | None = None) -> dict | None:
    """Le taux communal PUBLIC d'une commune, ou None si inconnu.

    TAXE-AMÉNAGEMENT-1 lot C — SOURCE UNIQUE du millésime et de la fraîcheur : renvoie aussi
    `delib_date` (date d'effet), `maj_at` (notre relevé), un `millesime` humain affichable partout,
    et `perime` (True si non rafraîchi depuis plus d'un an). Toutes les surfaces lisent d'ici."""
    if not insee:
        return None
    try:
        row = db.execute(text(
            "SELECT part_communale_pct, source, delib_date, maj_at FROM taxe_amenagement_taux "
            "WHERE insee = :i"), {"i": str(insee)[:5]}).first()
    except Exception:  # table absente en environnement partiel
        return None
    if not row:
        return None
    delib = row[2]
    maj = row[3]
    maj_d = maj.date() if isinstance(maj, datetime) else maj
    ref = today or today_reunion()
    perime = bool(maj_d is not None and (ref - maj_d).days > _PERIME_JOURS)
    depuis = _fr_date(delib)
    # EXPORTS-REBRANCHEMENT-1 lot 0 — la phrase servie au client dit le FAIT juridique
    # (délibération en vigueur), plus notre plomberie (« source DGFiP/DELTA, relevé le … » =
    # millésime de relevé, interdit côté client depuis PAGE-SOURCES-1 18/09). Les champs
    # structurés (source, delib_date, maj_at, perime) restent servis — admin et sonde de fraîcheur.
    # FIX-4 LOT 5 — « taux AU <date> » et non « en vigueur DEPUIS » : la délibération est une référence
    # HISTORIQUE (date d'effet connue), pas une preuve que le taux est TOUJOURS en vigueur aujourd'hui.
    # « en vigueur depuis » laissait entendre un maintien non établi (recontrôle externe §10). On date
    # la référence sans prolonger sa validité jusqu'à ce jour.
    millesime = "Taux communal"
    if depuis:
        millesime += f" au {depuis} (délibération communale — référence datée, maintien non vérifié)"
    return {"part_communale_pct": float(row[0]), "source": row[1],
            "delib_date": delib.isoformat() if delib else None,
            "maj_at": maj_d.isoformat() if maj_d else None,
            "millesime": millesime, "perime": perime, "secteur_majore": False}


def taux_secteur(db, idu: str | None, *, today: date | None = None) -> dict | None:
    """TAXE-FIX-1 point 3 — le taux du SECTEUR À TAUX MAJORÉ voté pour CETTE parcelle (délibération
    portée par DELTA au grain parcelle), ou None si la parcelle n'est dans aucun secteur. Même
    forme que taux_communal_public, avec `secteur_majore=True` et un millésime qui le dit."""
    if not idu:
        return None
    try:
        row = db.execute(text(
            "SELECT part_communale_pct, source, delib_date, maj_at FROM taxe_amenagement_secteur "
            "WHERE idu = :i"), {"i": str(idu)[:14]}).first()
    except Exception:  # table absente en environnement partiel
        return None
    if not row:
        return None
    delib, maj = row[2], row[3]
    maj_d = maj.date() if isinstance(maj, datetime) else maj
    ref = today or today_reunion()
    perime = bool(maj_d is not None and (ref - maj_d).days > _PERIME_JOURS)
    depuis = _fr_date(delib)
    millesime = "Secteur à taux majoré"
    if depuis:
        millesime += f" au {depuis} (délibération communale — référence datée, maintien non vérifié)"
    return {"part_communale_pct": float(row[0]), "source": row[1],
            "delib_date": delib.isoformat() if delib else None,
            "maj_at": maj_d.isoformat() if maj_d else None,
            "millesime": millesime, "perime": perime, "secteur_majore": True}


def taux_parcelle(db, idu: str | None, *, today: date | None = None) -> dict | None:
    """TAXE-FIX-1 point 3 — LE taux communal applicable à une PARCELLE : le secteur à taux majoré
    s'il en existe un pour cette parcelle, SINON le taux communal général. `secteur_majore` dit
    lequel a servi. C'est le point de résolution unique quand on connaît l'IDU (outil, fiche,
    Dossier) — `taux_communal_public(insee)` reste le taux GÉNÉRAL de la commune."""
    if not idu or len(str(idu)) < 5:
        return None
    sec = taux_secteur(db, idu, today=today)
    if sec:
        return sec
    return taux_communal_public(db, str(idu)[:5], today=today)


def config(idu: str | None = None) -> dict:
    """La config datée (valeurs forfaitaires + plafonds + source/année) — servie telle quelle à l'UI."""
    from .ingestion.exonerations_delta import releve
    cfg = load_yaml_config("taxe_amenagement")
    actuel = releve()
    if not actuel or actuel["annee"] != cfg["meta"]["annee"]:
        return cfg
    votes = {k: v for k, v in actuel.items() if k not in ("secteurs", "formules_locales")}
    if idu in actuel["secteurs"]:
        votes["communes"] = {**votes["communes"], idu[:5]: actuel["secteurs"][idu]}
    return {**cfg, "exonerations_locales": votes,
            "formules_locales": actuel.get("formules_locales", cfg["formules_locales"])}


def _eur(x: float) -> float:
    return round(float(x), 2)


# TAXE-FIX-1 point 1 — exonérations de PLEIN DROIT que l'outil peut rendre SANS deviner (CGI art.
# 1635 quater D, en vigueur 01/01/2026 — https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000050193341,
# lu le 24/09/2026). Une surface EXONÉRÉE ne produit AUCUNE part (0 €), à la différence de
# l'ABATTEMENT (−50 %) qui ne fait que réduire de moitié. Chaque motif porte son numéro dans
# l'article. Retenus (rendables sans convention ni liste réglementaire) : locaux agricoles (3°),
# logements PLAI/LLTS (2°), reconstruction à l'identique < 10 ans après sinistre (9°). Laissés
# (non rendables sans deviner) : service public/utilité publique (1°, engagement + liste par
# décret), centres équestres (4°), OIN/ZAC à équipements à charge des constructeurs (5°/6°, dépend
# de la convention), PUP (7°), aménagements prescrits par un PPR (8°). Petites surfaces < 5 m² = 10°
# (traité plus bas, sur la surface saisie). Cf docs/audit-2026-09/taxe-fix-1/TAXE-FIX-1.md.
_MOTIFS_EXONERATION = {
    "agricole": ("Locaux agricoles", "CGI art. 1635 quater D, 3°"),
    "plai": ("Logements locatifs très sociaux (PLAI)", "CGI art. 1635 quater D, 2°"),
    "reconstruction": ("Reconstruction à l'identique après sinistre (< 10 ans)",
                       "CGI art. 1635 quater D, 9°"),
}

# TAXE-FIX-1 point 2 — redevance d'archéologie préventive « part logement » due pour les travaux
# soumis à AUTORISATION D'URBANISME (permis) : MÊME assiette que la taxe d'aménagement (surface ×
# valeur forfaitaire, abattements ET exonérations inclus — l'assiette exclut déjà les surfaces
# exonérées), taux 0,40 %. TEXTES-1 — référence corrigée : depuis l'ordonnance n° 2022-883 du
# 14/06/2022 (en vigueur 01/09/2022) cette part est gérée par la DGFiP et rattachée au CGI (même
# fait générateur que la taxe d'aménagement, art. 1635 quater F). L'ancien fondement « code du
# patrimoine art. L524-7 » ne porte plus que le régime AU M² (0,69 €/m² en 2026, arrêté du
# 23/12/2025), réservé aux aménagements SANS permis. (Légifrance L524-7 v. 01/09/2022, lu 2026-09-29.)
_RAP_PCT = 0.40
_RAP_SOURCE = ("redevance d'archéologie préventive — 0,40 % de l'assiette de la taxe d'aménagement "
               "(CGI, gestion DGFiP depuis l'ordonnance 2022-883 ; fait générateur art. 1635 quater F)")


class LotTaxe(BaseModel):
    """Logements identiques, surfaces par logement, annexes comprises."""
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    nombre: int = Field(ge=1, le=100_000)
    surface: float = Field(gt=0, le=1_000_000)
    existant: float = Field(default=0, ge=0, le=1_000_000)
    regime: Literal["rp", "ptz", "social", "plai", "plein"]
    monument: bool = False


class SurfaceCategorie(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    categorie: str
    surface: float = Field(gt=0, le=1_000_000)
    surface_principale: float | None = Field(None, gt=0, le=1_000_000)


class ProgrammeTaxe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lots: list[LotTaxe] | None = Field(None, min_length=1, max_length=200)
    surfaces: list[SurfaceCategorie] = Field(min_length=1, max_length=200)


def calculer(
    *,
    lots: list[LotTaxe] | None = None,
    surfaces: list[SurfaceCategorie] | None = None,
    terrain_rehabilite: bool = False,
    commune_projet: str | None = None,
    idu_projet: str | None = None,
    ptz: bool = False,
    monument: bool = False,
    surface_taxable_m2: float = 0.0,
    surface_existante_m2: float = 0.0,
    residence_principale: bool = False,
    logement_aide: bool = False,
    nb_logements: int | None = None,
    surface_exoneree_m2: float = 0.0,
    motif_exoneration: str | None = None,
    piscine_m2: float = 0.0,
    pv_sol_m2: float = 0.0,
    stationnement_ext_places: int = 0,
    forfait_stationnement_eur: int | None = None,
    eoliennes_mats: int = 0,
    taux_communal_pct: float | None = None,
    taux_departemental_pct: float | None = None,
    taux_communal_public_pct: float | None = None,
    taux_communal_public_source: str | None = None,
    taux_communal_public_millesime: str | None = None,
    taux_communal_public_delib_date: str | None = None,
    taux_communal_public_maj_at: str | None = None,
    taux_communal_public_perime: bool | None = None,
    taux_communal_secteur_majore: bool = False,
) -> dict:
    """Renvoie le détail LIGNE PAR LIGNE + total (None si le taux communal manque)."""
    cfg = config(idu_projet) if idu_projet else config()
    vf = float(cfg["valeur_forfaitaire_m2"]["hors_idf"])   # La Réunion = hors IdF
    ab = cfg["abattement"]
    fo = cfg["forfaits"]
    taux = cfg["taux"]
    _station_max = fo.get("stationnement_ext_place_max_delib")
    tarif_stationnement = fo["stationnement_ext_place"]
    if forfait_stationnement_eur is not None:
        if not tarif_stationnement <= forfait_stationnement_eur <= _station_max:
            raise ValueError("Forfait de stationnement hors du barème annuel.")
        tarif_stationnement = forfait_stationnement_eur
    if taux_departemental_pct is None:
        taux_departemental_pct = taux.get("part_departementale_defaut")

    lignes: list[dict] = []
    seuil_exo = float(cfg.get("exoneration_surface_min_m2") or 0)
    plafond_rp = float(ab["plafond_m2_residence_principale"])

    # CHASSE-CALCULS-FIX-1 Lot 1 (E-A1) — l'abattement « 100 premiers m² » de résidence principale est dû
    # LOGEMENT PAR LOGEMENT (CGI art. 1635 quater I, I-2° ; BOFiP BOI-IF-TU-10-30-20 : non mutualisable).
    # Pour un collectif de N résidences principales, l'assiette abattue est min(surface, 100 × N), pas
    # 100 une seule fois. `nb_logements` inconnu → on applique 1 logement (cas maison) et on LE DIT
    # (message + drapeau) ; on ne suppose JAMAIS un collectif sans que le nombre soit saisi.
    nb_rp = None
    nb_logements_precise = bool(nb_logements and int(nb_logements) > 0)
    msg_nb_logements = None
    if residence_principale and not logement_aide:
        nb_rp = int(nb_logements) if nb_logements_precise else 1
        if not nb_logements_precise:
            msg_nb_logements = (
                "Abattement « 100 premiers m² » appliqué pour 1 logement (résidence principale). "
                "Pour un collectif, saisissez le nombre de logements : l'abattement de 50 % vaut sur "
                "les 100 premiers m² de CHAQUE logement (CGI art. 1635 quater I).")

    # 1) surface de construction : valeur forfaitaire, avec abattement 50 % (100 premiers m² par logement RP / aidé).
    surf = max(0.0, float(surface_taxable_m2 or 0))
    regles = cfg["exonerations_locales"]
    commune = regles["communes"].get(commune_projet, {})
    departement = regles["departement"] if commune_projet and commune_projet.startswith("974") else {}
    reductions = [0.0, 0.0]
    formules = cfg["formules_locales"]
    terrain = formules["terrain"]["vote"] if terrain_rehabilite else None
    base_hors_departement = 0.0
    surface_projet = (surf + surface_exoneree_m2 + sum(l.surface * l.nombre for l in lots or [])
                      + sum(l.surface for l in surfaces or []))
    def appliquer_exonerations(base, base_ptz=0, social=False, historique=False, categorie=None,
                               communale_seule=False):
        for index, votes in enumerate((commune, departement)):
            if index == 1 and communale_seule:
                continue
            # Sur une même surface, une exonération ne se cumule pas avec elle-même.
            reductions[index] += max(
                base * votes.get("social", 0) if social else 0,
                base * votes.get("monument", 0) if historique else 0,
                base_ptz * votes.get("ptz", 0),
                base * max(votes.get(categorie, 0), votes.get(terrain, 0)),
            ) / 100

    if lots:
        nb_rp = sum(lot.nombre for lot in lots if lot.regime in ("rp", "ptz"))
        nb_logements_precise, msg_nb_logements = True, None
        assiette_surf = 0.0
        regimes = {"rp": "résidence principale", "ptz": "résidence principale avec PTZ",
                   "social": "logement social aidé", "plai": "PLAI / LLTS", "plein": "au taux plein"}
        for lot in lots:
            reduite = 0.0
            if lot.regime in ("rp", "ptz"):
                reduite = min(lot.surface, max(0, plafond_rp - lot.existant))
            elif lot.regime == "social":
                reduite = lot.surface
            pleine = lot.surface - reduite
            base = lot.nombre * vf * (pleine + reduite * (1 - ab["taux_pct"] / 100))
            if surface_projet <= seuil_exo or lot.regime == "plai":
                base = 0.0
            assiette_surf += base
            appliquer_exonerations(base, lot.nombre * pleine * vf if base and lot.regime == "ptz" else 0,
                                   lot.regime == "social", lot.monument)
            lignes.append({"poste": regimes[lot.regime],
                           "detail": f"{lot.nombre} × {lot.surface:g} m², dont {reduite:g} m² à valeur réduite par logement",
                           "assiette_eur": _eur(base)})
    elif surf > 0 and seuil_exo and surface_projet <= seuil_exo:
        # RV2-V2 — exonération de PLEIN DROIT des petites surfaces (CGI art. 1635 quater D, 10°) :
        # une construction « inférieure OU ÉGALE à 5 m² » de surface taxable n'est pas soumise à la
        # part surface (borne INCLUSIVE : à 5 m² pile l'exonération s'applique — BOFiP BOI-IF-TU-10-20-30-160).
        assiette_surf = 0.0
        lignes.append({"poste": "Surface de construction",
                       "detail": f"{surf:g} m² ≤ {seuil_exo:g} m² — exonérée (CGI 1635 quater D, 10°)",
                       "assiette_eur": 0.0})
    elif surf > 0:
        abattue = 0.0
        pleine = surf
        if logement_aide:
            # logements aidés : abattement de 50 % sur TOUTE la surface (CGI 1635 quater I, I-1°).
            abattue, pleine = surf, 0.0
        elif residence_principale:
            # 100 premiers m² de CHAQUE logement à −50 % (E-A1) : plafond = 100 × nombre de logements.
            abattue = min(surf, max(0.0, plafond_rp * nb_rp - surface_existante_m2))
            pleine = surf - abattue
        taux_ab = float(ab["taux_pct"]) / 100.0
        assiette_surf = pleine * vf + abattue * vf * (1 - taux_ab)
        detail = f"{surf:g} m² × {vf:g} €/m²"
        if abattue:
            if residence_principale and not logement_aide:
                detail += (f" (dont {abattue:g} m² à −{ab['taux_pct']}% : 100 m² × {nb_rp} logement"
                           f"{'s' if nb_rp > 1 else ''})")
            else:
                detail += f" (dont {abattue:g} m² à −{ab['taux_pct']}%)"
        if residence_principale and not logement_aide and surface_existante_m2:
            detail += f" ; {surface_existante_m2:g} m² existants pris en compte pour le plafond"
        lignes.append({"poste": "Surface de construction", "detail": detail, "assiette_eur": _eur(assiette_surf)})
    else:
        assiette_surf = 0.0

    if not lots and surf > 0 and surface_projet > seuil_exo:
        appliquer_exonerations(assiette_surf, pleine * vf if ptz and residence_principale and not logement_aide else 0,
                               logement_aide, monument)

    for local in surfaces or []:
        formule = formules[local.categorie]
        valeur = vf * (1 - ab["taux_pct"] / 100) if formule.get("abattement") else vf
        base = local.surface * valeur if surface_projet > seuil_exo else 0.0
        eligible = local.surface <= formule.get("seuil_surface_inclusif", float("inf"))
        if "seuil_principal_exclusif" in formule:
            eligible = local.surface_principale < formule["seuil_principal_exclusif"]
        communale_seule = formule.get("communale_seule", False)
        if communale_seule:
            base_hors_departement += base
        appliquer_exonerations(base, categorie=formule["vote"] if eligible else None,
                               communale_seule=communale_seule)
        assiette_surf += base
        detail = f"{local.surface:g} m² × {valeur:g} €/m²"
        if not eligible:
            detail += " · exonération locale inapplicable à cette surface"
        elif base:
            detail += f" · exonération votée : commune {commune.get(formule['vote'], 0):g} %"
            if not communale_seule:
                detail += f", département {departement.get(formule['vote'], 0):g} %"
        if communale_seule:
            detail += " · part communale uniquement pour la taxe d’aménagement"
        lignes.append({"poste": formule["label"], "detail": detail, "assiette_eur": _eur(base)})

    # 1 bis) surface EXONÉRÉE de plein droit (CGI 1635 quater D) — locaux agricoles, PLAI,
    # reconstruction à l'identique. 0 € d'assiette, mais une ligne qui NOMME le motif et son article
    # (jamais un simple silence) ; distincte de l'abattement (−50 %), la part surface ne s'ajoute pas.
    surf_exo = max(0.0, float(surface_exoneree_m2 or 0))
    if surf_exo > 0 and motif_exoneration in _MOTIFS_EXONERATION:
        _label, _art = _MOTIFS_EXONERATION[motif_exoneration]
        lignes.append({"poste": f"Surface exonérée — {_label}",
                       "detail": f"{surf_exo:g} m² × {vf:g} €/m² — exonérée de plein droit ({_art})",
                       "assiette_eur": 0.0})

    # 2) installations à forfait spécifique (assiette propre, taxée aux mêmes taux).
    def _forfait(poste: str, qte: float, unit: float, unite: str):
        if qte and qte > 0:
            a = float(qte) * float(unit)
            lignes.append({"poste": poste, "detail": f"{qte:g} {unite} × {unit:g} €", "assiette_eur": _eur(a)})
            return a
        return 0.0

    assiette_forfaits = (
        _forfait("Piscine", piscine_m2, fo["piscine_m2"], "m²")
        + _forfait("Panneaux photovoltaïques au sol", pv_sol_m2, fo["panneau_pv_sol_m2"], "m²")
        + _forfait("Stationnement extérieur", stationnement_ext_places, tarif_stationnement, "place(s)")
        + _forfait("Éolienne(s) (mât > 12 m)", eoliennes_mats, fo["eolienne_mat"], "mât(s)")
    )

    appliquer_exonerations(assiette_forfaits)
    assiette = _eur(assiette_surf + assiette_forfaits)

    # 3) parts communale + départementale.
    # CIRCUIT-3 lot 6.2 — le taux PUBLIC prime quand il existe : la calculette n'exige plus un taux
    # saisi. Si les deux sont présents, on garde le saisi (l'utilisateur peut corriger) et on EXPOSE
    # l'écart saisi↔public comme contrôle de qualité.
    ecart_saisi_public = None
    taux_source = None
    if taux_communal_pct is None and taux_communal_public_pct is not None:
        taux_communal_pct = float(taux_communal_public_pct)
        taux_source = "public"
    elif taux_communal_pct is not None:
        taux_source = "saisi"
        if taux_communal_public_pct is not None:
            ecart_saisi_public = _eur(float(taux_communal_pct) - float(taux_communal_public_pct))
    taux_manquant = taux_communal_pct is None
    part_com = None if taux_manquant else _eur((assiette - _eur(reductions[0])) * float(taux_communal_pct) / 100.0)
    part_dep = None if taux_departemental_pct is None else _eur((assiette - _eur(base_hors_departement + reductions[1])) * float(taux_departemental_pct) / 100.0)
    total = None if (part_com is None or part_dep is None) else _eur((part_com or 0) + (part_dep or 0))

    # 4) TAXE-FIX-1 point 2 — redevance d'archéologie préventive : 0,40 % de la MÊME assiette
    # (art. L524-7 c. patrimoine). Ligne à part, sous le total TA ; ne dépend pas du taux communal.
    rap_eur = _eur(assiette * _RAP_PCT / 100.0)

    # CHASSE-CALCULS-FIX-1 Lot 2 (E-A2) — ce que le barème ne couvre pas (servi à l'outil ET au PDF).
    _non_couvert = [s for s in (
        (f"Stationnement extérieur au tarif majoré sur délibération (jusqu'à {int(_station_max):g} "
         f"€/place au lieu de {int(fo['stationnement_ext_place']):g}) : calcul au forfait national."
         ) if _station_max and forfait_stationnement_eur is None else None,
        "Hors barème : taxe d'aménagement à taux majoré sectoriel (au-delà des secteurs ingérés), "
        "versement pour sous-densité (VSD) et participations d'urbanisme (PVR/PFAC).",
    ) if s]

    return {
        "annee": cfg["meta"]["annee"],
        "source": cfg["meta"]["source"],
        "url": cfg["meta"]["url"],
        "note": cfg["meta"]["note"],
        "valeur_forfaitaire_m2": vf,
        "lignes": lignes,
        "assiette_eur": assiette,
        "exonerations_locales": {"commune": commune, "departement": departement,
                                 "releve_le": regles["releve_le"], "source": regles["source"],
                                 "base_exoneree_communale": _eur(reductions[0]),
                                 "base_exoneree_departementale": _eur(reductions[1])},
        "taux_communal_pct": taux_communal_pct,
        "taux_departemental_pct": taux_departemental_pct,
        "part_departementale_confirmee": bool(taux.get("part_departementale_confirmee_974")
                                              and taux_departemental_pct == taux.get("part_departementale_defaut")),
        "part_communale_eur": part_com,
        "part_departementale_eur": part_dep,
        "total_eur": total,
        # CHASSE-CALCULS-FIX-1 Lot 1 (E-A1) — abattement RP au grain logement.
        "nb_logements": nb_rp,                       # nombre de logements RP retenu (None hors RP)
        "nb_logements_precise": nb_logements_precise,  # True si saisi par l'appelant
        "message_nb_logements": msg_nb_logements,    # invite à saisir si collectif (sinon None)
        # CHASSE-CALCULS-FIX-1 Lot 2 (E-A2) — ce que le barème ne modélise PAS, dit explicitement
        # (même liste servie à l'outil ET au PDF ; une notion, un chemin).
        "non_couvert": _non_couvert,
        # TAXE-FIX-1 point 2 — redevance d'archéologie préventive (0,40 % de l'assiette).
        "rap_pct": _RAP_PCT,
        "rap_eur": rap_eur,
        "rap_source": _RAP_SOURCE,
        "taux_communal_manquant": taux_manquant,
        "taux_communal_source": taux_source,             # 'public' | 'saisi' | None
        "taux_communal_public_pct": taux_communal_public_pct,
        "taux_communal_public_source": taux_communal_public_source,
        # TAXE-AMÉNAGEMENT-1 lot C — millésime affiché + drapeau fraîcheur (taux public seulement).
        "taux_communal_millesime": (taux_communal_public_millesime
                                    if taux_source == "public" else None),
        "taux_communal_delib_date": (taux_communal_public_delib_date
                                     if taux_source == "public" else None),
        "taux_communal_maj_at": taux_communal_public_maj_at if taux_source == "public" else None,
        "taux_communal_perime": (bool(taux_communal_public_perime)
                                 if taux_source == "public" else None),
        # TAXE-FIX-1 point 3 — le taux servi vient-il d'un secteur à taux majoré ? (public seulement)
        "taux_communal_secteur_majore": (bool(taux_communal_secteur_majore)
                                         if taux_source == "public" else None),
        "ecart_saisi_public_pct": ecart_saisi_public,    # contrôle de qualité (lot 6.2)
        "message_taux_communal": (None if not taux_manquant else
            "Taux communal non renseigné pour cette commune — saisissez-le "
            "(il figure dans la délibération de la commune ; l'outil n'invente aucun taux)."),
    }
