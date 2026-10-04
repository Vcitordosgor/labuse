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

import json as _json

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import bati as bati_mod
from .db import parcel_faisabilite
from .engine import Hypotheses


# DONNEES-FIX-1 lot C — hauteur d'étage de référence pour dériver les niveaux depuis l'ÉGOUT mesuré.
# CALIBRÉE : sur 229 615 bâtiments portant un nb d'étages BD TOPO renseigné, `max(1, round(égout/3,0))`
# reproduit le nb d'étages à 75,7 % exact et 98,3 % à ±1 niveau (voir DONNEES-FIX-1.md). 3,0 m est la
# hauteur d'étage standard, déjà utilisée par le repli BD TOPO (hauteur/3).
ETAGE_REF_M = 3.0


def _niveaux_existants(session: Session, parcel_id: int, defaut: float) -> tuple[float, bool, str]:
    """Niveaux du bâti existant. Renvoie (niveaux, reel, source) — `source` ∈ {'lidar','bdtopo','sans'},
    `reel=False` uniquement pour le placeholder ('sans').

    DONNEES-FIX-1 lot C — priorité à l'ÉGOUT LiDAR MESURÉ : `niveaux = max(1, round(égout / 3,0 m))`.
    L'égout (bord de toit), PAS le faîtage : le faîtage inclut le volume de toiture, qui n'est pas un
    niveau habitable → le compter surestimerait l'existant. À défaut de LiDAR (~8 % micro-bâti), le
    chemin BD TOPO actuel est inchangé (étages puis hauteur/3), puis le placeholder prudent."""
    # 1) ÉGOUT LiDAR mesuré (point unique batiment_hauteur_lidar, joint par idu). Table absente
    #    (base sans ingestion LiDAR) → repli BD TOPO, jamais une erreur.
    try:
        egout = session.execute(text(
            "SELECT l.egout_m FROM batiment_hauteur_lidar l JOIN parcels p ON p.idu = l.idu "
            "WHERE p.id = :pid"), {"pid": parcel_id}).scalar()
    except Exception:  # noqa: BLE001 — table/colonnes absentes → repli BD TOPO
        try:
            session.rollback()
        except Exception:  # noqa: BLE001 — session mock/close
            pass
        egout = None
    if egout is not None and float(egout) > 0:
        return max(1.0, float(round(float(egout) / ETAGE_REF_M))), True, "lidar"
    # 2) BD TOPO déclaré (chemin actuel) — nombre d'étages, puis hauteur / 3.
    row = session.execute(text(
        """SELECT max((b.attrs->>'nombre_d_etages')::int)            AS etages,
                  max(NULLIF(b.attrs->>'hauteur','')::float)         AS hauteur
           FROM spatial_layers b JOIN parcels p ON p.id = :pid
           WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)"""),
        {"pid": parcel_id}).first()
    if row and row.etages:
        return float(row.etages), True, "bdtopo"
    if row and row.hauteur:
        return max(1.0, round(float(row.hauteur) / ETAGE_REF_M)), True, "bdtopo"
    return float(defaut), False, "sans"


def _emprise_revelee(session: Session, parcel_id: int) -> float | None:
    """M32 — emprise bâtie RÉVÉLÉE par CoSIA (`max(emprise_cosia_m2)`), là où BD TOPO la rate. POINT
    UNIQUE de cette lecture (isolée pour être stubbable en test, comme `_niveaux_existants`)."""
    rev = session.execute(text(
        "SELECT max(emprise_cosia_m2) FROM parcel_bati_revele WHERE parcel_id = :p"),
        {"p": parcel_id}).scalar()
    return float(rev) if rev is not None else None


# SCORING-6 lot A — emprise bâtie SUR LA PORTION U/AU du contour cadastral. La capacité max
# (`sdp_max`) est clippée sur la seule portion U/AU quand la zone dominante est A/N à cheval
# (parcel_faisabilite, assiette_clippee) ; le bâti RETRANCHÉ doit l'être sur LA MÊME portion,
# sinon on soustrait le bâti debout sur la portion A/N inconstructible d'un plafond calculé sur
# la seule portion U/AU → résiduel faussement nul sur toute parcelle A/N bâtie (le tout-ou-rien
# déguisé, cause du run 4 ≡ run 3). Union U/AU lue de la MÊME source que la cascade.
_BATI_ASSIETTE = text("""
WITH p AS (SELECT commune, geom_2975 AS g FROM parcels WHERE id = :pid),
uau AS (SELECT ST_Union(ST_MakeValid(z.geom_2975)) AS u
        FROM spatial_layers z, p
        WHERE z.kind = :zkind AND z.commune = p.commune
          AND labuse_zone_famille(z.subtype) = ANY(:uau_fams) AND ST_Intersects(z.geom_2975, p.g)),
assiette AS (SELECT CASE WHEN uau.u IS NULL THEN p.g
                         ELSE ST_Intersection(p.g, uau.u) END AS a
             FROM p LEFT JOIN uau ON TRUE)
SELECT COALESCE(SUM(ST_Area(ST_Intersection(ST_MakeValid(b.geom_2975), a.a))), 0.0)
FROM spatial_layers b, assiette a
WHERE b.kind = 'batiment' AND ST_Intersects(b.geom_2975, a.a)
""")


def _emprise_batie_assiette(session: Session, parcel_id: int) -> float:
    """Emprise bâtie (m²) sur la SEULE portion U/AU du contour cadastral — pour rester cohérent
    avec la capacité max clippée sur cette même portion (assiette_clippee). Isolée/stubbable
    comme `_niveaux_existants`/`_emprise_revelee`. Union U/AU lue de cascade_rules (zonage_plu_gpu)."""
    from .db import _layer_params
    zonage = _layer_params("zonage_plu_gpu")
    v = session.execute(_BATI_ASSIETTE, {
        "pid": parcel_id,
        "zkind": zonage.get("spatial_kind", "plu_gpu_zone"),
        "uau_fams": list(zonage.get("positive_prefixes", ["U", "AU"])),
    }).scalar()
    return float(v or 0.0)


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
        # PLU-CALIBRAGE-6 — règle PLU non validée (feuille SDP `propose`) : non calculable, SDP 0
        # (0 = « le moteur ne sait pas », pas un droit ; la zone est portée pour la fiche/M127).
        if code == "regle_plu_non_validee":
            return (f"regle_plu_non_validee:{zone}" if zone else "regle_plu_non_validee"), 0
        return code, 0          # terrain_exigu / redhibitoire / hauteur_indispo / capacite_nulle
    # parcel_faisabilite → None : distinguer « aucune zone » (hors PLU) d'une zone sans règle.
    from .db import parcel_context
    from .zonage import resolve_zone
    ctx = parcel_context(session, parcel_id)
    if ctx is None or not ctx.zone:
        return "hors_plu", None                      # réellement inconnaissable — dit, jamais muet
    if resolve_zone(ctx.zone, ctx.commune) is None:
        return f"zone_non_resolue:{ctx.zone}", 0     # C2 (A/N hors YAML calibré) — sans droits neufs
    return "indetermine", None                       # inattendu : on ne devine pas, NULL + cause


def compute_residuel(session: Session, parcel_id: int,
                     faisa: tuple | None = None,
                     assiette_clippee: bool = False) -> dict:
    """Bloc « potentiel résiduel » d'une parcelle. `faisa` = (ctx, Faisabilite) déjà calculé
    (réutilisé par la fiche pour ne pas relancer le moteur). `disponible=False` quand la
    parcelle n'est pas constructible ou que le bâti n'est pas mesurable — M125 : chaque
    indisponible porte alors sa CAUSE structurée + la SDP à écrire (0 vrai / NULL inconnu).

    SCORING-6 lot A — `assiette_clippee=True` : la capacité est calculée sur l'assiette clippée
    (portion U/AU moins contraintes géométriques certaines) au lieu du tout-ou-rien. OPT-IN :
    inutile pour le servi, requis pour le run résiduel q_v15 (geste de Vic)."""
    if not bati_mod.layer_available(session):
        return {"disponible": False, "raison": "Couche bâtiments (BD TOPO) non ingérée.",
                "cause": "bati_non_ingere", "sdp_ecrite": None}
    res = faisa or parcel_faisabilite(session, parcel_id, assiette_clippee=assiette_clippee)
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
    surface = float(ctx.surface_m2 or 0.0)
    # SCORING-6 lot A — sur une parcelle A/N à cheval clippée, le bâti retranché se mesure sur LA
    # MÊME portion U/AU que la capacité (sinon on soustrait le bâti de la portion A/N d'un plafond
    # U/AU → résiduel toujours 0). OPT-IN : hors assiette_clippee (servi) ou parcelle mono-zone,
    # rien ne change — bâti du contour entier + révélé CoSIA.
    from .db import _pct_constructible
    pct_c = _pct_constructible(ctx) if assiette_clippee else None
    if pct_c is not None and 0 < pct_c < 100:
        emprise_batie = _emprise_batie_assiette(session, parcel_id)   # bâti sur la portion U/AU
    else:
        st = bati_mod.stats_batch(session, [parcel_id]).get(parcel_id, {})
        emprise_batie = float(st.get("bati_ratio", 0.0)) * surface       # emprise au sol bâtie (BD TOPO)
        # Bâti RÉVÉLÉ (M32) : CoSIA voit l'emprise que BD TOPO rate. On retient la mesure la plus
        # grande pour que ces parcelles cessent de s'afficher « terrain nu ». Ces parcelles sont
        # déjà déclassées (declasse_bati_revele) → le résiduel ne les fait pas entrer en tête ; ce
        # correctif est un affichage de fiche (résiduel = cache isolé du scoring, cf. en-tête).
        rev = _emprise_revelee(session, parcel_id)
        if rev and rev > emprise_batie:
            emprise_batie = rev

    # DONNEES-FIX-1 lot C — niveaux depuis l'ÉGOUT LiDAR mesuré (repli BD TOPO), + coefficient de
    # plancher (emprise-toit BD TOPO → emprise de plancher, même convention que `surface_plancher_m2`).
    niveaux_exist, niveaux_reels, hauteur_source = _niveaux_existants(
        session, parcel_id, hyp.niveaux_bati_existant_defaut)
    sdp_existante = emprise_batie * niveaux_exist * hyp.coef_sdp_existante
    sdp_residuelle = max(0.0, sdp_max - sdp_existante)

    # COHERENCE-FIX-1 (lot B) — PLUS DE PLAFOND 999, PLUS DE 0-POUR-ABSENCE. L'ancien
    # `min(999, …) if … else 0.0` servait un « 999 % » (plafond technique lu comme un vrai
    # pourcentage — 2 304 parcelles) et un « 0 % consommé » quand le dénominateur manquait
    # (un zéro à la place d'une absence). La valeur est désormais servie TELLE QUELLE ;
    # au-delà de 300 % les LECTEURS affichent « > 300 % » (seuil produit, cf. rapport) —
    # jamais le moteur qui ment. Dénominateur manquant → None (la garde emprise_max/sdp_max
    # > 0 plus haut rend ce cas théorique — on le dit au lieu de servir 0).
    taux_emprise = (100.0 * emprise_batie / emprise_max) if emprise_max else None
    pct_potentiel = (100.0 * sdp_existante / sdp_max) if sdp_max else None
    seuil = float(hyp.sous_densite_seuil_pct)
    sous_densite = (taux_emprise < seuil) if taux_emprise is not None else None

    # CHASSE-FIX-1 (C06) — le moteur lit parcel_au_statut et POSE LE DRAPEAU « capacité
    # différée » (zone AU à ouverture bloquée) : la SDP est calculée (doctrine « différée,
    # pas exclue », décision Vic) mais aucun lecteur ne la présente comme disponible. Le
    # drapeau n'est PAS stocké au run (un mot un sens : la vérité vit dans parcel_au_statut,
    # relue au service) — il voyage dans le payload du calcul live.
    from .au_differe import statut_differe
    _au_differe = statut_differe(session, parcel_id=parcel_id)

    return {
        "disponible": True,
        "capacite_differee": _au_differe is not None,
        "capacite_differee_detail": _au_differe,
        "taux_emprise_pct": round(taux_emprise) if taux_emprise is not None else None,
        "pct_potentiel": round(pct_potentiel) if pct_potentiel is not None else None,
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
        # DONNEES-FIX-1 lot C — d'où viennent les niveaux existants : 'lidar' (égout mesuré),
        # 'bdtopo' (étages/hauteur déclarés), 'sans' (placeholder prudent). Écrit au run.
        "hauteur_source": hauteur_source,
        "coef_sdp_existante": hyp.coef_sdp_existante,
        # Résumé prudent (le taux d'emprise est réel ; la SDP résiduelle est estimée si la
        # hauteur du bâti n'est pas connue → on le dit).
        "libelle": _libelle(taux_emprise, sdp_residuelle, niveaux_reels),
        "estimation_sdp": not niveaux_reels,
        # Traçabilité capacité : calibré (YAML PLU communal) vs estimation générique.
        "calibree": f.calibree,
        # PLU-CALIBRAGE-5 — une parcelle qui PORTE une exception non modélisée (règle du PLU non
        # déduite, cf. regles_non_modelisees) a une capacité moins certaine : badge « Estimé », jamais
        # « Sourcé », même en zone calibrée. La valeur SDP n'est pas approximée pour autant.
        "capacite_estimee": (not f.calibree) or bool(getattr(ctx, "regles_non_modelisees", None)),
        # GEOMETRIE-1 lot B — provenance de l'assiette : 'gabarit' (zone d'implantation,
        # reculs par côté + PPR rouge découpé) / 'residuel_legacy' (parcelle non servie).
        "assiette_source": fr.get("assiette_source"),
        # DONNEES-FIX-1 point 4 — exceptions PLU présentes sur la zone qu'on ne modélise PAS : la
        # parcelle les porte (« règle non modélisée », avec article/page) au lieu de les approximer.
        "regles_non_modelisees": list(getattr(ctx, "regles_non_modelisees", []) or []),
    }


# M135 — l'écriture cible un RUN versionné (parcel_residuel_runs, clé run_seq+parcel_id),
# jamais la table servie (devenue une VUE). Le run est désigné à l'appel.
_UPSERT = text(
    """INSERT INTO parcel_residuel_runs
         (run_seq, parcel_id, taux_emprise_pct, pct_potentiel, sous_densite, sdp_residuelle_m2,
          capacite_estimee, cause, assiette_source, hauteur_source, regles_non_modelisees, computed_at)
       VALUES (:rs, :p, :t, :pp, :sd, :sr, :ce, :cz, :asrc, :hsrc, :rnm, now())
       ON CONFLICT (run_seq, parcel_id) DO UPDATE SET
         taux_emprise_pct=EXCLUDED.taux_emprise_pct, pct_potentiel=EXCLUDED.pct_potentiel,
         sous_densite=EXCLUDED.sous_densite, sdp_residuelle_m2=EXCLUDED.sdp_residuelle_m2,
         capacite_estimee=EXCLUDED.capacite_estimee, cause=EXCLUDED.cause,
         assiette_source=EXCLUDED.assiette_source, hauteur_source=EXCLUDED.hauteur_source,
         regles_non_modelisees=EXCLUDED.regles_non_modelisees,
         computed_at=now()""")


def compute_residuel_batch(session: Session, parcel_ids: list[int], run_seq: int,
                           log=None, assiette_clippee: bool = False) -> dict:
    """Calcule et CACHE le résiduel dans le RUN `run_seq` (parcel_residuel_runs) pour alimenter
    le filtre carte ET le dataset M127.

    M135 — GARDE-FOU B.4 : écrire dans le run SERVI est une ERREUR (`ServedRunWriteError`), pas un
    warning. `compute_residuel()` (la LOGIQUE) reste byte-identique ; seul le chemin d'écriture
    change (run désigné à l'appel, jamais le servi).

    M125 (arbitrage Vic, Option 1) — le batch écrit TOUTES les parcelles, la vérité de chacune :
      · disponible → valeurs pleines, cause NULL (les lecteurs VIVANTS ne lisent que celles-ci) ;
      · non disponible → cause structurée + sdp 0 (vraie valeur : zone/enveloppe sans droits)
        ou NULL (hors_plu — réellement inconnaissable) ; taux/pct/sous_densite = NULL (sans objet
        hors constructible — le doute ne classe pas) ;
      · exception → COMPTÉE et LOGGÉE, jamais avalée (une exception muette = un manquant sans
        cause, même famille de défaut). Elle n'écrit rien (on ne devine pas une cause).
    Renvoie {"calcules", "causes": {cause: n}, "erreurs", "erreurs_detail": [(pid, msg)…]}."""
    from .residuel_runs import assert_writable
    assert_writable(session, run_seq)   # ERREUR (pas warning) si run_seq == run servi
    res = {"calcules": 0, "causes": {}, "erreurs": 0, "erreurs_detail": []}
    for pid in parcel_ids:
        try:
            r = compute_residuel(session, pid, assiette_clippee=assiette_clippee)
        except Exception as exc:  # noqa: BLE001 - une parcelle ne casse pas le lot, mais SE DIT
            res["erreurs"] += 1
            if len(res["erreurs_detail"]) < 20:
                res["erreurs_detail"].append((pid, f"{type(exc).__name__}: {exc}"))
            if log:
                log(f"  ⚠ résiduel parcel_id={pid} : {type(exc).__name__}: {exc}")
            continue
        if r.get("disponible"):
            rnm = r.get("regles_non_modelisees") or []
            session.execute(_UPSERT, {
                "rs": run_seq, "p": pid, "t": r["taux_emprise_pct"], "pp": r["pct_potentiel"],
                "sd": r["sous_densite"], "sr": r["sdp_residuelle_m2"],
                "ce": r["capacite_estimee"], "cz": None, "asrc": r.get("assiette_source"),
                "hsrc": r.get("hauteur_source"),
                "rnm": (_json.dumps(rnm, ensure_ascii=False) if rnm else None)})
            res["calcules"] += 1
            continue
        cause = r.get("cause") or "indetermine"
        if cause == "bati_non_ingere":     # panne d'environnement, pas un état de parcelle
            res["causes"][cause] = res["causes"].get(cause, 0) + 1
            continue
        session.execute(_UPSERT, {"rs": run_seq, "p": pid, "t": None, "pp": None, "sd": None,
                                  "sr": r.get("sdp_ecrite"), "ce": None, "cz": cause,
                                  "asrc": None, "hsrc": None, "rnm": None})
        res["causes"][cause] = res["causes"].get(cause, 0) + 1
    session.flush()
    return res


def compare_residuel_servi(session: Session, parcel_ids: list[int]) -> list[dict]:
    """M135 — READ-ONLY : compare le calcul FRAIS de `compute_residuel()` au run SERVI
    (vue `parcel_residuel`). Renvoie les écarts [{parcel_id, servi, frais}]. N'écrit RIEN —
    remplace l'ancien rapiéçage in-place de l'audit (la machine à mosaïque, lot 05/08).
    Un écart déclenche la règle de dette §1 (recalcul mesuré, run neuf)."""
    ecarts = []
    for pid in parcel_ids:
        try:
            d = compute_residuel(session, pid)
        except Exception:  # noqa: BLE001 - une parcelle ne casse pas la comparaison
            continue
        frais = d.get("sdp_residuelle_m2") if d.get("disponible") else d.get("sdp_ecrite")
        servi = session.execute(
            text("SELECT sdp_residuelle_m2 FROM parcel_residuel WHERE parcel_id=:p"),
            {"p": pid}).scalar()
        if frais != servi:
            ecarts.append({"parcel_id": pid, "servi": servi, "frais": frais})
    return ecarts


#: COHERENCE-FIX-1 (lot B) — seuil d'AFFICHAGE partagé (fiche, Comparer, Dossier, Copilote —
#: miroir front : format.ts PCT_CONSOMME_SEUIL) : au-delà, le chiffre exact n'apporte rien.
SEUIL_PCT_AFFICHAGE = 300


def fmt_pct_consomme(pct: float | int | None) -> str | None:
    """La PARTIE NOMBRE affichée d'un % de densité consommée : exacte jusqu'à 300, « > 300 »
    au-delà, None si absente (l'appelant écrit l'absence — jamais un 0)."""
    if pct is None:
        return None
    return "> 300" if float(pct) > SEUIL_PCT_AFFICHAGE else str(round(float(pct)))


def _libelle(taux: float | None, sdp_res: float, niveaux_reels: bool) -> str:
    # M36 Lot C (Q1, arbitrage Vic) : au-delà de 100 % on ne plafonne PAS et on ne déduit
    # RIEN (pas d'« antériorité probable ») — libellé factuel seul.
    # COHERENCE-FIX-1 (lot B) : taux None (dénominateur manquant) → on le DIT, jamais « 0 % ».
    if taux is None:
        etat = "taux d'emprise non calculable (emprise constructible inconnue)"
    elif taux > 100:
        # COHERENCE-FIX-1 (lot B) : au-delà de 300 %, le chiffre exact n'apporte rien au client
        # (bâti très au-delà du plafond de zone) — même règle d'affichage que la fiche.
        etat = (f"bâti existant supérieur à l'emprise constructible actuelle "
                f"({'> 300' if taux > 300 else f'~{round(taux)}'} % — à vérifier)")
    elif taux < 2:
        etat = "terrain nu — potentiel quasi intégral"
    else:
        etat = f"bâtie à ~{round(taux)} % de l'emprise constructible"
    suffix = "" if niveaux_reels else " (SDP résiduelle estimée — hauteur du bâti non ingérée)"
    return f"{etat} · SDP résiduelle ~{round(sdp_res)} m²{suffix}"
