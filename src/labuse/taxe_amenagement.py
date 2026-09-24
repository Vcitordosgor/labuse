"""K3 (rattrapage KelFoncier) — CALCULETTE de la taxe d'aménagement.

Formule PUBLIQUE (code de l'urbanisme). Assiette = surface taxable × valeur forfaitaire au m²
(+ forfaits d'installations : piscine, PV au sol, stationnement extérieur, éoliennes) ;
abattement de 50 % sur les 100 premiers m² d'une résidence principale et sur les logements aidés ;
taxe = assiette × (part communale + part départementale).

DOCTRINE : aucun taux inventé. Le taux COMMUNAL vient des délibérations (ni en base ni devinable) →
si absent, `taux_communal_pct=None` et le total N'EST PAS calculé (l'appelant dit « taux communal non
renseigné, à saisir »). Le taux départemental sert le plafond légal 2,5 %, étiqueté « à confirmer ».
Les valeurs forfaitaires viennent d'une config DATÉE et SOURCÉE (config/taxe_amenagement.yaml).

Résultat DÉTAILLÉ ligne par ligne : un promoteur doit pouvoir vérifier chaque ligne, pas juste un total.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import text

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
    ref = today or date.today()
    perime = bool(maj_d is not None and (ref - maj_d).days > _PERIME_JOURS)
    depuis = _fr_date(delib)
    # EXPORTS-REBRANCHEMENT-1 lot 0 — la phrase servie au client dit le FAIT juridique
    # (délibération en vigueur), plus notre plomberie (« source DGFiP/DELTA, relevé le … » =
    # millésime de relevé, interdit côté client depuis PAGE-SOURCES-1 18/09). Les champs
    # structurés (source, delib_date, maj_at, perime) restent servis — admin et sonde de fraîcheur.
    millesime = "Taux communal"
    if depuis:
        millesime += f" en vigueur depuis le {depuis} (délibération communale)"
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
    ref = today or date.today()
    perime = bool(maj_d is not None and (ref - maj_d).days > _PERIME_JOURS)
    depuis = _fr_date(delib)
    millesime = "Secteur à taux majoré"
    if depuis:
        millesime += f" en vigueur depuis le {depuis} (délibération communale)"
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


def config() -> dict:
    """La config datée (valeurs forfaitaires + plafonds + source/année) — servie telle quelle à l'UI."""
    return load_yaml_config("taxe_amenagement")


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

# TAXE-FIX-1 point 2 — redevance (« taxe ») d'archéologie préventive due pour les travaux soumis à
# AUTORISATION D'URBANISME (permis) : MÊME assiette que la taxe d'aménagement (surface × valeur
# forfaitaire, abattements ET exonérations inclus — l'assiette exclut déjà les surfaces exonérées),
# taux 0,40 %. Code du patrimoine art. L524-7 (fait de droit stable). À NE PAS confondre avec le
# régime au m² (0,69 €/m² en 2026, arrêté du 23/12/2025), réservé aux aménagements SANS permis.
_RAP_PCT = 0.40
_RAP_SOURCE = "code du patrimoine art. L524-7 (0,40 % de l'assiette de la taxe d'aménagement)"


def calculer(
    *,
    surface_taxable_m2: float = 0.0,
    residence_principale: bool = False,
    logement_aide: bool = False,
    surface_exoneree_m2: float = 0.0,
    motif_exoneration: str | None = None,
    piscine_m2: float = 0.0,
    pv_sol_m2: float = 0.0,
    stationnement_ext_places: int = 0,
    eoliennes_mats: int = 0,
    taux_communal_pct: float | None = None,
    taux_departemental_pct: float | None = None,
    taux_communal_public_pct: float | None = None,
    taux_communal_public_source: str | None = None,
    taux_communal_public_millesime: str | None = None,
    taux_communal_public_delib_date: str | None = None,
    taux_communal_public_perime: bool | None = None,
    taux_communal_secteur_majore: bool = False,
) -> dict:
    """Renvoie le détail LIGNE PAR LIGNE + total (None si le taux communal manque)."""
    cfg = config()
    vf = float(cfg["valeur_forfaitaire_m2"]["hors_idf"])   # La Réunion = hors IdF
    ab = cfg["abattement"]
    fo = cfg["forfaits"]
    taux = cfg["taux"]
    if taux_departemental_pct is None:
        taux_departemental_pct = taux.get("part_departementale_defaut")

    lignes: list[dict] = []
    seuil_exo = float(cfg.get("exoneration_surface_min_m2") or 0)

    # 1) surface de construction : valeur forfaitaire, avec abattement 50 % (100 premiers m² RP / aidé).
    surf = max(0.0, float(surface_taxable_m2 or 0))
    if surf > 0 and seuil_exo and surf < seuil_exo:
        # RV2-V2 — exonération de PLEIN DROIT des petites surfaces (CGI art. 1635 quater D, 10°) :
        # une construction < 5 m² de surface taxable n'est pas soumise à la part surface.
        assiette_surf = 0.0
        lignes.append({"poste": "Surface de construction",
                       "detail": f"{surf:g} m² < {seuil_exo:g} m² — exonérée (CGI 1635 quater D, 10°)",
                       "assiette_eur": 0.0})
    elif surf > 0:
        abattue = 0.0
        pleine = surf
        if residence_principale or logement_aide:
            # 100 premiers m² à −50 % (RP) ; les logements aidés bénéficient de l'abattement sur toute
            # leur surface. On applique le cas le plus favorable exprimable simplement.
            if logement_aide:
                abattue, pleine = surf, 0.0
            else:
                abattue = min(surf, float(ab["plafond_m2_residence_principale"]))
                pleine = surf - abattue
        taux_ab = float(ab["taux_pct"]) / 100.0
        assiette_surf = pleine * vf + abattue * vf * (1 - taux_ab)
        detail = f"{surf:g} m² × {vf:g} €/m²"
        if abattue:
            detail += f" (dont {abattue:g} m² à −{ab['taux_pct']}%)"
        lignes.append({"poste": "Surface de construction", "detail": detail, "assiette_eur": _eur(assiette_surf)})
    else:
        assiette_surf = 0.0

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
        + _forfait("Stationnement extérieur", stationnement_ext_places, fo["stationnement_ext_place"], "place(s)")
        + _forfait("Éolienne(s) (mât > 12 m)", eoliennes_mats, fo["eolienne_mat"], "mât(s)")
    )

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
    part_com = None if taux_manquant else _eur(assiette * float(taux_communal_pct) / 100.0)
    part_dep = None if taux_departemental_pct is None else _eur(assiette * float(taux_departemental_pct) / 100.0)
    total = None if (part_com is None or part_dep is None) else _eur((part_com or 0) + (part_dep or 0))

    # 4) TAXE-FIX-1 point 2 — redevance d'archéologie préventive : 0,40 % de la MÊME assiette
    # (art. L524-7 c. patrimoine). Ligne à part, sous le total TA ; ne dépend pas du taux communal.
    rap_eur = _eur(assiette * _RAP_PCT / 100.0)

    return {
        "annee": cfg["meta"]["annee"],
        "source": cfg["meta"]["source"],
        "url": cfg["meta"]["url"],
        "note": cfg["meta"]["note"],
        "valeur_forfaitaire_m2": vf,
        "lignes": lignes,
        "assiette_eur": assiette,
        "taux_communal_pct": taux_communal_pct,
        "taux_departemental_pct": taux_departemental_pct,
        "part_departementale_confirmee": bool(taux.get("part_departementale_confirmee_974")),
        "part_communale_eur": part_com,
        "part_departementale_eur": part_dep,
        "total_eur": total,
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
