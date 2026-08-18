"""Potentiel résiduel (Lot B) — « cette parcelle est bâtie à N % de son potentiel ».

Croise deux choses qui existaient séparément :
  - le BÂTI EXISTANT (BD TOPO, via bati.py) : emprise au sol réellement construite ;
  - la CAPACITÉ MAX (faisabilité) : emprise constructible et SDP maximales.

Métriques :
  - `taux_emprise` = emprise bâtie / emprise constructible max  → RÉEL (aucune hypothèse
    de hauteur) ; sert au filtre « sous-densité ».
  - `sdp_existante` = emprise bâtie × niveaux du bâti existant. Les niveaux viennent de BD
    TOPO (`nombre_d_etages`/`hauteur`) QUAND ils sont ingérés ; sinon hypothèse PLACEHOLDER
    `niveaux_bati_existant_defaut` (prudente) → la SDP résiduelle est alors une ESTIMATION,
    signalée comme telle.
  - `sdp_residuelle` = max(0, SDP max − SDP existante) ; `pct_potentiel` = part déjà bâtie.

Lecture seule, isolée : ne touche ni la cascade ni le scoring.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import bati as bati_mod
from .db import parcel_faisabilite
from .engine import Hypotheses


def _niveaux_existants(session: Session, parcel_id: int, defaut: float) -> tuple[float, bool]:
    """Niveaux du bâti existant. Renvoie (niveaux, reel) — `reel=False` = hypothèse PLACEHOLDER
    (hauteur/étages BD TOPO non ingérés sur ce lot)."""
    row = session.execute(text(
        """SELECT max((b.attrs->>'nombre_d_etages')::int)            AS etages,
                  max(NULLIF(b.attrs->>'hauteur','')::float)         AS hauteur
           FROM spatial_layers b JOIN parcels p ON p.id = :pid
           WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)"""),
        {"pid": parcel_id}).first()
    if row and row.etages:
        return float(row.etages), True
    if row and row.hauteur:
        return max(1.0, round(float(row.hauteur) / 3.0)), True
    return float(defaut), False


def _emprise_revelee(session: Session, parcel_id: int) -> float | None:
    """M32 — emprise bâtie RÉVÉLÉE par CoSIA (`max(emprise_cosia_m2)`), là où BD TOPO la rate. POINT
    UNIQUE de cette lecture (isolée pour être stubbable en test, comme `_niveaux_existants`)."""
    rev = session.execute(text(
        "SELECT max(emprise_cosia_m2) FROM parcel_bati_revele WHERE parcel_id = :p"),
        {"p": parcel_id}).scalar()
    return float(rev) if rev is not None else None


def _cause_indisponible(session: Session, parcel_id: int, f=None) -> tuple[str, int | None]:
    """M125 — cause STRUCTURÉE d'un résiduel non disponible + la valeur de SDP à écrire
    (arbitrage Vic, Option 1 : le 0 n'est pas un doute, c'est la réponse du moteur ;
    seul `hors_plu` est réellement inconnaissable → NULL). MÊMES résolveurs que le moteur
    (parcel_context/resolve_zone) — attribution de cause, jamais une 2e formule."""
    if f is not None:
        code = f.cause or "capacite_nulle"
        zone = (f.zone or "").strip()
        # `zone_transition` est émis à l'UNIQUE branche « constructible_neuf=False » du moteur
        # (engine.fini, zone A/N/AU fermée) — le nom historique est trompeur : on écrit la
        # famille lisible « zone non constructible » + le code de zone réel (nuance fiche/M127).
        if code == "zone_transition":
            return (f"zone_non_constructible:{zone}" if zone else "zone_non_constructible"), 0
        if code == "habitat_interdit":
            return (f"habitat_interdit:{zone}" if zone else "habitat_interdit"), 0
        return code, 0          # terrain_exigu / redhibitoire / hauteur_indispo / capacite_nulle
    # parcel_faisabilite → None : distinguer « aucune zone » (hors PLU) d'une zone sans règle.
    from .db import parcel_context
    from .plu_rules import resolve_zone
    ctx = parcel_context(session, parcel_id)
    if ctx is None or not ctx.zone:
        return "hors_plu", None                      # réellement inconnaissable — dit, jamais muet
    if resolve_zone(ctx.zone, ctx.commune) is None:
        return f"zone_non_resolue:{ctx.zone}", 0     # C2 (A/N hors YAML calibré) — sans droits neufs
    return "indetermine", None                       # inattendu : on ne devine pas, NULL + cause


def compute_residuel(session: Session, parcel_id: int,
                     faisa: tuple | None = None) -> dict:
    """Bloc « potentiel résiduel » d'une parcelle. `faisa` = (ctx, Faisabilite) déjà calculé
    (réutilisé par la fiche pour ne pas relancer le moteur). `disponible=False` quand la
    parcelle n'est pas constructible ou que le bâti n'est pas mesurable — M125 : chaque
    indisponible porte alors sa CAUSE structurée + la SDP à écrire (0 vrai / NULL inconnu)."""
    if not bati_mod.layer_available(session):
        return {"disponible": False, "raison": "Couche bâtiments (BD TOPO) non ingérée.",
                "cause": "bati_non_ingere", "sdp_ecrite": None}
    res = faisa or parcel_faisabilite(session, parcel_id)
    if res is None:
        cause, sdp = _cause_indisponible(session, parcel_id)
        return {"disponible": False, "raison": "Zone hors PLU outillé — capacité non calculable.",
                "cause": cause, "sdp_ecrite": sdp}
    ctx, f = res
    if not f.constructible:
        cause, sdp = _cause_indisponible(session, parcel_id, f=f)
        return {"disponible": False, "raison": "Parcelle non constructible — pas de potentiel résiduel.",
                "cause": cause, "sdp_ecrite": sdp}

    fr = f.fourchette
    emprise_max = float(fr.get("emprise_constructible_m2") or 0.0)
    sdp_max = float(fr.get("surface_plancher_m2") or 0.0)
    if emprise_max <= 0 or sdp_max <= 0:
        return {"disponible": False, "raison": "Capacité max nulle — résiduel non défini.",
                "cause": "capacite_nulle", "sdp_ecrite": 0}

    hyp = Hypotheses.charger(getattr(ctx, "commune", None))   # M-N P1-13 : hypothèses de la commune
    st = bati_mod.stats_batch(session, [parcel_id]).get(parcel_id, {})
    surface = float(ctx.surface_m2 or 0.0)
    emprise_batie = float(st.get("bati_ratio", 0.0)) * surface           # emprise au sol bâtie (BD TOPO)
    # Bâti RÉVÉLÉ (M32) : CoSIA voit l'emprise que BD TOPO rate. On retient la mesure la plus
    # grande pour que ces parcelles cessent de s'afficher « terrain nu ». Ces parcelles sont
    # déjà déclassées (declasse_bati_revele) → le résiduel ne les fait pas entrer en tête ; ce
    # correctif est un affichage de fiche (résiduel = cache isolé du scoring, cf. en-tête).
    rev = _emprise_revelee(session, parcel_id)
    if rev and rev > emprise_batie:
        emprise_batie = rev

    niveaux_exist, niveaux_reels = _niveaux_existants(session, parcel_id, hyp.niveaux_bati_existant_defaut)
    sdp_existante = emprise_batie * niveaux_exist
    sdp_residuelle = max(0.0, sdp_max - sdp_existante)

    taux_emprise = min(999.0, 100.0 * emprise_batie / emprise_max) if emprise_max else 0.0
    pct_potentiel = min(999.0, 100.0 * sdp_existante / sdp_max) if sdp_max else 0.0
    seuil = float(hyp.sous_densite_seuil_pct)
    sous_densite = taux_emprise < seuil

    return {
        "disponible": True,
        "taux_emprise_pct": round(taux_emprise),
        "pct_potentiel": round(pct_potentiel),
        "sous_densite": sous_densite,
        "sous_densite_seuil_pct": round(seuil),
        "emprise_batie_m2": round(emprise_batie),
        "emprise_constructible_m2": round(emprise_max),
        "sdp_max_m2": round(sdp_max),
        "sdp_existante_m2": round(sdp_existante),
        "sdp_residuelle_m2": round(sdp_residuelle),
        "niveaux_max": fr.get("niveaux_max"),
        "niveaux_existants": round(niveaux_exist, 1),
        "niveaux_reels": niveaux_reels,
        # Résumé prudent (le taux d'emprise est réel ; la SDP résiduelle est estimée si la
        # hauteur du bâti n'est pas connue → on le dit).
        "libelle": _libelle(taux_emprise, sdp_residuelle, niveaux_reels),
        "estimation_sdp": not niveaux_reels,
        # Traçabilité capacité : calibré (YAML PLU communal) vs estimation générique.
        "calibree": f.calibree,
        "capacite_estimee": not f.calibree,
    }


_UPSERT = text(
    """INSERT INTO parcel_residuel
         (parcel_id, taux_emprise_pct, pct_potentiel, sous_densite, sdp_residuelle_m2,
          capacite_estimee, cause, computed_at)
       VALUES (:p, :t, :pp, :sd, :sr, :ce, :cz, now())
       ON CONFLICT (parcel_id) DO UPDATE SET
         taux_emprise_pct=EXCLUDED.taux_emprise_pct, pct_potentiel=EXCLUDED.pct_potentiel,
         sous_densite=EXCLUDED.sous_densite, sdp_residuelle_m2=EXCLUDED.sdp_residuelle_m2,
         capacite_estimee=EXCLUDED.capacite_estimee, cause=EXCLUDED.cause, computed_at=now()""")


def compute_residuel_batch(session: Session, parcel_ids: list[int],
                           log=None) -> dict:
    """Calcule et CACHE le résiduel (table parcel_residuel) pour alimenter le filtre carte
    ET le dataset M127.

    M125 (arbitrage Vic, Option 1) — le batch écrit TOUTES les parcelles, la vérité de chacune :
      · disponible → valeurs pleines, cause NULL (les lecteurs VIVANTS ne lisent que celles-ci) ;
      · non disponible → cause structurée + sdp 0 (vraie valeur : zone/enveloppe sans droits)
        ou NULL (hors_plu — réellement inconnaissable) ; taux/pct/sous_densite = NULL (sans objet
        hors constructible — le doute ne classe pas) ;
      · exception → COMPTÉE et LOGGÉE, jamais avalée (une exception muette = un manquant sans
        cause, même famille de défaut). Elle n'écrit rien (on ne devine pas une cause).
    Renvoie {"calcules", "causes": {cause: n}, "erreurs", "erreurs_detail": [(pid, msg)…]}."""
    res = {"calcules": 0, "causes": {}, "erreurs": 0, "erreurs_detail": []}
    for pid in parcel_ids:
        try:
            r = compute_residuel(session, pid)
        except Exception as exc:  # noqa: BLE001 - une parcelle ne casse pas le lot, mais SE DIT
            res["erreurs"] += 1
            if len(res["erreurs_detail"]) < 20:
                res["erreurs_detail"].append((pid, f"{type(exc).__name__}: {exc}"))
            if log:
                log(f"  ⚠ résiduel parcel_id={pid} : {type(exc).__name__}: {exc}")
            continue
        if r.get("disponible"):
            session.execute(_UPSERT, {
                "p": pid, "t": r["taux_emprise_pct"], "pp": r["pct_potentiel"],
                "sd": r["sous_densite"], "sr": r["sdp_residuelle_m2"],
                "ce": r["capacite_estimee"], "cz": None})
            res["calcules"] += 1
            continue
        cause = r.get("cause") or "indetermine"
        if cause == "bati_non_ingere":     # panne d'environnement, pas un état de parcelle
            res["causes"][cause] = res["causes"].get(cause, 0) + 1
            continue
        session.execute(_UPSERT, {"p": pid, "t": None, "pp": None, "sd": None,
                                  "sr": r.get("sdp_ecrite"), "ce": None, "cz": cause})
        res["causes"][cause] = res["causes"].get(cause, 0) + 1
    session.flush()
    return res


def _libelle(taux: float, sdp_res: float, niveaux_reels: bool) -> str:
    # M36 Lot C (Q1, arbitrage Vic) : au-delà de 100 % on ne plafonne PAS et on ne déduit
    # RIEN (pas d'« antériorité probable ») — libellé factuel seul.
    if taux > 100:
        etat = (f"bâti existant supérieur à l'emprise constructible actuelle "
                f"(~{round(taux)} % — à vérifier)")
    elif taux < 2:
        etat = "terrain nu — potentiel quasi intégral"
    else:
        etat = f"bâtie à ~{round(taux)} % de l'emprise constructible"
    suffix = "" if niveaux_reels else " (SDP résiduelle estimée — hauteur du bâti non ingérée)"
    return f"{etat} · SDP résiduelle ~{round(sdp_res)} m²{suffix}"
