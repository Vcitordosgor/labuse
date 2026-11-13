"""Endpoint outil « Gabarit réglementaire » — GET /outils/gabarit/{idu}.

Le front n'affiche que ce que l'API sert (doctrine LABUSE : zéro recalcul au front).
Le calcul est porté par le moteur pur `labuse.gabarit.engine`.

- `/outils/gabarit/demo`  → démonstration sur la parcelle FICTIVE (CDC §9), calcul complet
  (conservée pour les tests ; le bouton de démo est retiré du front en GABARIT-2).
- `/outils/gabarit/{idu}` → raccordement RÉEL (GABARIT-2) : cadastre + PLU + classification
  des limites (BD TOPO) + PPR rouge. Calcul complet si tout est réuni ; sinon « Calcul
  incomplet » + motif métier (parcelle sans façade, limite non qualifiée, PLU non validé…).
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..gabarit.builder import build_gabarit_input
from ..gabarit.contract import GabaritResult
from ..gabarit.engine import INCOMPLETE_MESSAGE, compute_gabarit
from ..gabarit.fixtures import demo_gabarit_input

router = APIRouter(prefix="/outils/gabarit", tags=["gabarit"])


def get_db():
    from .app import get_db as _g
    yield from _g()


def _bati_existant(db: Session, idu: str) -> dict | None:
    """GABARIT-6 P4 — le bâti EXISTANT porté par la parcelle : emprise BD TOPO (`spatial_layers`
    kind='batiment') + hauteur LiDAR HD mesurée (`batiment_hauteur_lidar`, au faîtage, par parcelle)
    à défaut la hauteur BD TOPO du bâtiment. C'est un FAIT contextuel (l'outil montre où l'on PEUT
    construire ; ceci montre ce qui est DÉJÀ là) : aucun calcul réglementaire n'en dépend.

    On retient les bâtiments MAJORITAIREMENT sur la parcelle (≥ 50 % de leur emprise) ou d'emprise
    intersectée ≥ 20 m² — écarte les débords de voisins. Emprise entière servie (schéma fidèle).
    Renvoie une FeatureCollection (4326) ou None si la parcelle ne porte aucun bâti."""
    lid = db.execute(text(
        # CHASSE-INVARIANTS-FIX-2 (1) — même borne unique : faîtage ≤ 0 ou > plafond ⇒ NULL (non mesuré).
        "SELECT labuse_hauteur_lidar_m(faitage_m) FROM batiment_hauteur_lidar WHERE idu = :i"),
        {"i": idu}).scalar()
    lidar_faitage = float(lid) if lid is not None else None
    rows = db.execute(text(
        "SELECT ST_AsGeoJSON(ST_Transform(s.geom_2975, 4326)) AS gj, "
        "       (s.attrs->>'hauteur')::float AS h_bdtopo "
        "FROM spatial_layers s JOIN parcels p ON p.idu = :i "
        "WHERE s.kind = 'batiment' AND ST_Intersects(s.geom_2975, p.geom_2975) "
        "  AND (ST_Area(ST_Intersection(s.geom_2975, p.geom_2975)) >= 0.5 * ST_Area(s.geom_2975) "
        "       OR ST_Area(ST_Intersection(s.geom_2975, p.geom_2975)) >= 20.0)"
    ), {"i": idu}).mappings().all()
    feats = []
    for r in rows:
        if not r["gj"]:
            continue
        h_bdtopo = float(r["h_bdtopo"]) if r["h_bdtopo"] is not None else None
        # hauteur mesurée LiDAR (au faîtage) prioritaire ; repli sur la hauteur BD TOPO du bâtiment
        hauteur = lidar_faitage if lidar_faitage is not None else h_bdtopo
        feats.append({
            "type": "Feature",
            "properties": {
                "hauteur_m": round(hauteur, 1) if hauteur is not None else None,
                "h_source": "lidar" if lidar_faitage is not None else ("bdtopo" if h_bdtopo is not None else None),
                # GABARIT-3D-1 (étape 2 bis) — hauteur PROPRE au bâtiment (BD TOPO), indépendante du
                # faîtage LiDAR (par parcelle) : la scène 3D l'utilise pour le volume (jamais la
                # hauteur de parcelle recopiée). Additif : ne change aucun chiffre réglementaire servi.
                "hauteur_bdtopo_m": round(h_bdtopo, 1) if h_bdtopo is not None else None,
            },
            "geometry": json.loads(r["gj"]),
        })
    if not feats:
        return None
    return {"type": "FeatureCollection", "features": feats}


@router.get("/{idu}", response_model=GabaritResult)
def gabarit_detail(idu: str, db: Session = Depends(get_db)) -> GabaritResult:
    if idu == "demo":
        res = compute_gabarit(demo_gabarit_input())
        res.raccordement = {"mode": "fixtures",
                            "avertissement": "Données FICTIVES de démonstration (CDC §9)"}
        return res

    # FAISA-REGLES-1 (D-028) — parcelle disparue du cadastre : l'outil le DIT et ne sert PAS de gabarit
    # complet (comme le fait déjà le PDF). On rend un contour + le message, jamais une enveloppe comme si
    # la parcelle existait encore. (Le PDF refuse en 422 côté route ; l'outil interactif ne doit pas non
    # plus présenter un gabarit sur une référence qui n'existe plus.)
    from .. import cadastre_disparue as _cd
    _disp = _cd.info_disparue(db, idu)
    if _disp:
        _geom = db.execute(text("SELECT ST_AsGeoJSON(geom) FROM parcels WHERE idu = :i"),
                           {"i": idu}).scalar()
        return GabaritResult(
            status="incomplete", message=_cd.phrase_disparue(_disp),
            validationErrors=["parcelle disparue du cadastre"],
            raccordement={"parcelle": {"idu": idu, "commune": _disp.get("commune")},
                          "disparue": _disp},
            contourGeoJSON=(json.loads(_geom) if _geom else None))

    build = build_gabarit_input(db, idu)
    if build is None:
        raise HTTPException(404, f"Parcelle inconnue : {idu}")

    # CHASSE-FIX-1 (C06) — zone AU à ouverture bloquée : l'enveloppe (complète OU incomplète)
    # est dite « après ouverture ». Règle/libellé uniques : faisabilite.au_differe.
    from ..faisabilite.au_differe import LIBELLE_COURT, statut_differe
    _diff = statut_differe(db, idu=idu)
    _racc = build.raccordement
    if _diff is not None:
        _racc = {**(_racc or {}), "au_differe": {**_diff, "libelle": LIBELLE_COURT}}

    if build.blocking:
        # GABARIT-6 lot B : calcul incomplet, mais la parcelle reste VISIBLE. On sert le contour
        # cadastral + la référence/commune (via raccordement.parcelle) pour que la carte centre sur
        # la parcelle et que le panneau l'identifie AU-DESSUS du motif — jamais un écran vide.
        parcel = build.input.parcel if build.input else None
        res = GabaritResult(status="incomplete", message=INCOMPLETE_MESSAGE,
                            validationErrors=build.blocking, raccordement=_racc,
                            contourGeoJSON=parcel.geometry if parcel else None,
                            surfaceParcelleM2=parcel.areaM2 if parcel else None,
                            batiExistantGeoJSON=_bati_existant(db, idu))
        # NU5-FIX-1 (A-O2) — « incomplete » devient « inconstructible » si la parcelle ne peut RIEN
        # recevoir (N/A/AU fermée/habitat interdit) : « inconstructible », pas « donnée manquante ».
        from ..gabarit.builder import appliquer_verdict_constructibilite
        appliquer_verdict_constructibilite(db, idu, res)
        return res

    res = compute_gabarit(build.input)
    res.raccordement = _racc
    # NU5-FIX-1 (A-O1) — garde de constructibilité, lue via potentiel_batir (même robinet que la
    # fiche) : une zone « habitat interdit » (Uem) ou tout verdict inconstructible ne sert JAMAIS
    # d'enveloppe géométrique (« 763 m², R+5 »). Appliquée AVANT le travail 3D/bâti : on sort tôt.
    from ..gabarit.builder import appliquer_verdict_constructibilite
    appliquer_verdict_constructibilite(db, idu, res)
    if res.status == "inconstructible":
        res.batiExistantGeoJSON = _bati_existant(db, idu)
        return res
    # CHASSE-CALCULS-FIX-1 Lot 4 (E-B2) — UNE SEULE zone d'implantation : son AIRE est servie dans le
    # MÊME repère que la Faisabilité (échelle CONTENANCE, règle CONTENANCE-1 C3 = contenance/dessin,
    # identique à ctx.terrain_sur_dessin). La FORME (GeoJSON, reculs, PPR découpé) reste sur le dessin ;
    # seule l'aire scalaire `zoneImplantationM2` est ré-échelonnée → même valeur au m² près que l'outil
    # Faisabilité, fin du doublon (ex. AK0804 : 19 294 → 19 024, = faisabilité). surfaceParcelleM2 est
    # déjà la contenance ; le plafond d'emprise (CES × contenance) l'est aussi → rien d'autre à toucher.
    if res.zoneImplantationM2 and res.surfaceParcelleM2:
        _dessin = db.execute(text("SELECT ST_Area(geom_2975) FROM parcels WHERE idu = :i"),
                             {"i": idu}).scalar()
        if _dessin and float(_dessin) > 0:
            res.zoneImplantationM2 = round(
                float(res.zoneImplantationM2) * float(res.surfaceParcelleM2) / float(_dessin), 1)
    # CHASSE-DOCS-FIX-1 (vérif #3) + FAISA-REGLES-1 (D-025/026) — SOURCE UNIQUE pour la part en zone
    # constructible (zone_servie.zone_dominante, la MÊME que la fiche §PLU / Comparer) : pctPortionZone +
    # surfaceNote. Helper PARTAGÉ avec le builder PDF → écran et PDF portent la même mise en garde à-cheval.
    from ..gabarit.builder import appliquer_note_a_cheval
    appliquer_note_a_cheval(db, idu, res)
    res.batiExistantGeoJSON = _bati_existant(db, idu)
    # RECETTE-OUTILS-3 (S7/S10) — bâti découpé au contour + zone d'implantation déduite du bâti conservé.
    # Référence UNIQUE lue par l'app (2D/3D) ET le PDF (le PDF rappelle la même fonction, cf. construire_gabarit).
    from ..gabarit.builder import deduire_bati_de_zone
    deduire_bati_de_zone(res)
    # CHASSE-DOCS-FIX-1 (E-07) — zone d'implantation NULLE (terrain exigu : rien ne passe après reculs) :
    # le plafond d'emprise et la hauteur n'ont pas d'objet (ils donneraient un gabarit chiffré sur un
    # terrain où rien ne s'implante). On les masque et on le DIT.
    if res.zoneImplantationM2 == 0:
        res.plafondEmpriseM2 = None
        res.hauteurReglementaireM = None
        res.terrainNote = ("Aucune zone d'implantation après reculs (terrain exigu) : plafond "
                           "d'emprise et hauteur sans objet ici.")
        return res
    # CHASSE-CALCULS-FIX-1 Lot 6 (E-C1) — l'extrusion 3D est posée à plat : on le DIT dès qu'une
    # hauteur réglementaire permet un volume (le mode 3D l'affiche).
    if res.hauteurReglementaireM is not None:
        # RECETTE-4 — formulation explicite : la hauteur EST mesurée depuis le terrain naturel (le volume
        # vert part du sol du MNT), mais le SOMMET est représenté à plat (il ne suit pas la pente).
        res.terrainNote = ("Volume 3D indicatif — la hauteur réglementaire est mesurée depuis le terrain "
                           "naturel, mais le sommet est représenté à plat (il ne suit pas la pente du terrain).")
    return res


# ── GABARIT-3D-1 (pilote) — SCÈNE + COUPES ────────────────────────────────────────────────────────
# Réservé aux ADMINS (interrupteur du pilote) : la vue 3D par défaut et les chiffres servis ne
# changent pas. La scène lit le MÊME GabaritResult que l'outil (chiffres identiques) + le fond
# LiDAR 1 m local. Écran (étape 2) et PDF liront la même scène.

def _exiger_admin(request: Request) -> None:
    from . import auth
    auth.exiger_admin(request)


@router.get("/scene/{idu}")
def gabarit_scene(idu: str, request: Request, db: Session = Depends(get_db), frais: bool = False) -> dict:
    """Scène 3D du Gabarit (sol mesuré 0,5 m, limite, zone, bâtiments, règles, 2 coupes, métadonnées).
    `frais=1` (recette) contourne la mémoïsation en mémoire → on observe froid (appel) puis chaud (copie)."""
    _exiger_admin(request)
    from ..gabarit.scene import build_scene
    return build_scene(db, idu, use_cache=not frais).to_dict()


@router.get("/sol/stats")
def gabarit_sol_stats(request: Request) -> dict:
    """GABARIT-3D-3 (LOT 2, recette) — appels EXTÉRIEURS WMS émis + poids/nombre des copies locales.
    Sert à PROUVER que la 2ᵉ ouverture ne fait aucun appel extérieur, et le plafond 1 Go du cache."""
    _exiger_admin(request)
    from ..gabarit import sol
    octets, fichiers = sol.taille_cache()
    return {"appels_wms": sol.appels_wms["n"], "cache_octets": octets, "cache_fichiers": fichiers,
            "cache_max_octets": sol._cache_max()}


def _verif_sid(scene, sid: str | None):
    """Parité (A2) : la coupe/le plan sont servis POUR un identifiant de scène. Si `sid` est fourni et
    ne correspond pas à la scène reconstruite (déterministe) → 409 (scène périmée)."""
    if sid and sid != scene.scene_id:
        raise HTTPException(409, f"Scène périmée (demandé {sid}, servi {scene.scene_id}).")


@router.get("/scene/{idu}/coupe/{axe}.svg")
def gabarit_coupe_svg(idu: str, axe: str, request: Request, theme: str = "sombre", sid: str | None = None,
                      detail: int = 0, w: int = 960, h: int = 520, header: int = 1,
                      db: Session = Depends(get_db)) -> Response:
    """Coupe A (pente dominante) ou B (voie) en SVG serveur, servie pour l'identifiant `sid`.
    detail=1 : vue détaillée (toutes les cotes, bandes, les deux pentes) ; sinon aperçu.
    w/h : dimensions cibles (le front demande la taille de son bandeau ÷ zoom → l'aperçu remplit la place,
    H = V, et les textes atteignent ≥ 11 px une fois affichés). Bornés pour rester sains."""
    _exiger_admin(request)
    from ..gabarit.coupe_svg import coupe_svg
    from ..gabarit.scene import build_scene
    scene = build_scene(db, idu)
    _verif_sid(scene, sid)
    coupe = next((c for c in scene.coupes if c["label"].upper() == axe.upper()), None)
    if coupe is None:
        raise HTTPException(404, f"Coupe « {axe} » indisponible pour {idu}.")
    width = max(360, min(int(w), 3000))
    h_max = max(140, min(int(h), 1600))
    svg = coupe_svg(coupe, theme=theme, adresse=scene.adresse, idu=idu, detail=bool(detail),
                    width=width, h_max=h_max, header=bool(header))
    if not svg:
        raise HTTPException(404, "Relief indisponible sur cette emprise (profil sans point valide).")
    return Response(svg, media_type="image/svg+xml")


@router.get("/scene/{idu}/ortho")
def gabarit_ortho(idu: str, request: Request, sid: str | None = None,
                  db: Session = Depends(get_db)) -> Response:
    """PHOTO AÉRIENNE (étape 3) : orthophoto IGN tirée PAR LE SERVEUR pour le cadre de la scène, mise en
    cache par identifiant de scène. Le navigateur ne contacte jamais l'IGN. Millésime en en-tête. 502 si
    l'IGN est indisponible → la visionneuse reste en relief (jamais chargée à l'ouverture, bouton seulement)."""
    _exiger_admin(request)
    from ..gabarit.ortho import ortho_pour_scene
    from ..gabarit.scene import build_scene
    scene = build_scene(db, idu)
    _verif_sid(scene, sid)
    res = ortho_pour_scene(scene)
    if not res:
        raise HTTPException(502, "Orthophoto IGN indisponible pour cette emprise.")
    headers = {
        "X-Ortho-Millesime": str(res.get("millesime") or ""),
        "X-Ortho-Date": str(res.get("date_vol") or ""),
        "X-Ortho-Source": str(res.get("source") or "IGN"),
        "Access-Control-Expose-Headers": "X-Ortho-Millesime,X-Ortho-Date,X-Ortho-Source",
        "Cache-Control": "private, max-age=86400",
    }
    return Response(res["png"], media_type="image/png", headers=headers)


@router.get("/scene/{idu}/plan.svg")
def gabarit_plan_cle_svg(idu: str, request: Request, theme: str = "sombre", sid: str | None = None,
                         w: int = 380, h: int = 320, db: Session = Depends(get_db)) -> Response:
    """Plan-clé (cadastre + zone + bâti + axes + nord), servi pour l'identifiant `sid`. w/h : le front en
    demande un rendu plus petit que son cadre → affiché en `w-full`, il grandit (textes lisibles)."""
    _exiger_admin(request)
    from ..gabarit.coupe_svg import plan_cle_svg
    from ..gabarit.scene import build_scene
    scene = build_scene(db, idu)
    _verif_sid(scene, sid)
    svg = plan_cle_svg(scene.to_dict(), theme=theme, width=max(160, min(int(w), 600)), height=max(140, min(int(h), 600)))
    if not svg:
        raise HTTPException(404, f"Plan-clé indisponible pour {idu}.")
    return Response(svg, media_type="image/svg+xml")
