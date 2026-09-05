"""M73 §1 — accès UNIQUE aux lignes de cascade SERVIES (dryrun) pour les générateurs de documents.

Doctrine (arbitrage Vic) : « le dryrun servi fait foi ». Les 4 documents — premium, dossier,
banquier, fiche écran — lisent la MÊME cascade servie (`dryrun_cascade_results`, run
épinglé), dédupliquée (M46) et arbitrée/libellée (`risques_arbitrage`). Aucun générateur ne lit
plus `cascade_results` (rail legacy, mort) ni `spatial_layers` pour un aléa/PPR/zonage : ce serait
un second point de calcul, cause racine des contradictions du RAPPORT_M73.

`served_cascade_lines` renvoie les lignes brutes (colonnes DB) arbitrées ; chaque générateur les
met en forme. `served_group` regroupe par onglet (regles/risques/marche/proprio) pour les rapports.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import runs
from .risques_arbitrage import arbitrer_risques

# CONNEXIONS-2 Lot 1 (KO-1) : le run servi par défaut est le POINT DE VÉRITÉ UNIQUE versionné
# (config/served_run.txt via Q_A_RUN_LABEL, aujourd'hui q_v11_m137). L'ancien `_DEFAULT_RUN =
# "q_v8_calibre"` (3 runs en arrière) servait des cascades périmées aux exports experts — supprimé.
# score_v_constants n'importe que la stdlib : aucun cycle.


def served_cascade_lines(db: Session, idu: str, run: str | None = None) -> list[dict]:
    """Lignes de cascade servies pour la parcelle : dédupliquées + arbitrées + libellées.

    Colonnes : layer_name, result, severity, weight_applied, detail, source, source_table,
    source_id, evenement. Liste vide si la parcelle n'est pas dans le run servi.
    """
    run = run or runs.current()
    rows = db.execute(text(
        """SELECT cr.layer_name, cr.result, cr.severity, cr.weight_applied, cr.detail,
                  ds.name AS source, cr.source_table, cr.source_id, cr.evenement
           FROM dryrun_cascade_results cr
           LEFT JOIN data_sources ds ON ds.id = cr.data_source_id
           JOIN parcels p ON p.id = cr.parcel_id
           WHERE cr.run_label = :run AND p.idu = :idu
           ORDER BY abs(COALESCE(cr.weight_applied, 0)) DESC, cr.layer_name"""),
        {"run": run, "idu": idu}).mappings().all()
    seen: set = set()
    out: list[dict] = []
    for r in rows:
        k = (r["layer_name"], r["result"], r["detail"])
        if k in seen:
            continue
        seen.add(k)
        out.append(dict(r))
    out = arbitrer_risques(out)
    # ZONE-1 pt2 — garde DE LECTURE : la ligne `residuel_socle` stockée au run a pu être
    # calculée sous l'ancienne zone du centroïde ; si la zone DOMINANTE (celle de l'écran)
    # est A/N, la SDP servie vaut 0 par règle, cause affichée. Le dryrun n'est pas réécrit.
    if any(l["layer_name"] == "residuel_socle" for l in out):
        from ..faisabilite.zone_servie import ligne_residuel_gardee, zone_fam_ecran
        fam, zlib = zone_fam_ecran(db, idu)
        if fam in ("A", "N"):
            out = [ligne_residuel_gardee(l, fam, zlib) if l["layer_name"] == "residuel_socle"
                   else l for l in out]
    # EXPORTS-1 lot 5 — trois gardes de lecture supplémentaires (mêmes principes : le dryrun
    # n'est jamais réécrit, la ligne servie est corrigée au point de service unique).
    out = _gardes_lot5(db, idu, out)
    return out


def _gardes_lot5(db: Session, idu: str, lignes: list[dict]) -> list[dict]:
    """EXPORTS-1 lot 5 (5.2/5.3/5.4) — gardes de lecture des lignes servies.

    - `acces` (5.2) : la couche cascade testait l'INTERSECTION STRICTE avec l'axe BD TOPO —
      une polyligne au milieu de la chaussée ne touche quasi jamais un polygone parcellaire
      (audit A6 : « pas d'accès » sur une parcelle en façade de la Chaussée Royale). LE test
      servi est celui de la viabilisation (voie à ≤ 10 / ≤ 75 m) ; sans donnée de
      viabilisation, la ligne est OMISE (jamais servie telle quelle).
    - `icpe` (5.3, arbitrage Q9) : l'alerte ne vaut que pour une installation CLASSÉE —
      un recensement Géorisques « Non ICPE » (cessation/antériorité) n'alerte plus ; le
      tableau détaillé, lui, garde tout avec le régime.
    - `proprietaire` (5.4) : « non renseigné » stocké au run alors que le fichier PM (la
      même assiette que la carte propriétaire) porte une dénomination → ligne rebranchée."""
    out = []
    for l in lignes:
        nom = l["layer_name"]
        if nom == "acces":
            v = db.execute(text(
                "SELECT voie10, voie75 FROM parcel_viabilisation "
                "WHERE idu = :i"), {"i": idu}).mappings().first() if db.execute(text(
                "SELECT to_regclass('parcel_viabilisation') IS NOT NULL")).scalar() else None
            if v is None:
                continue     # pas de faisceau viabilisation → la ligne intersection-stricte est omise
            l = dict(l)
            if v["voie10"]:
                l.update(result="PASS", severity="INFO", weight_applied=0.0,
                         detail="Accès voirie : voie publique à ≤ 10 m de la parcelle "
                                "(faisceau viabilisation — le test au contact strict de l'axe "
                                "BD TOPO est retiré).")
            elif v["voie75"]:
                l.update(result="SOFT_FLAG", severity="INFO", weight_applied=0.0,
                         detail="Accès voirie : voie publique à ≤ 75 m mais pas au droit de la "
                                "parcelle — accès à vérifier sur site (faisceau viabilisation).")
            else:
                l.update(result="SOFT_FLAG", severity="INFO",
                         detail="Accès voirie : aucune voie publique détectée à moins de 75 m "
                                "(faisceau viabilisation) — enclavement possible, à vérifier.")
        elif nom == "icpe" and l["result"] not in ("PASS",):
            classee = db.execute(text(
                """WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :i)
                   SELECT sl.name, sl.subtype,
                          round(ST_Distance(sl.geom_2975, p.geom_2975))::int AS dist_m
                   FROM spatial_layers sl, p
                   WHERE sl.kind = 'icpe'
                     AND COALESCE(sl.subtype, '') NOT IN ('Non ICPE', '')
                     AND ST_DWithin(sl.geom_2975, p.geom_2975, 500)
                   ORDER BY dist_m LIMIT 1"""), {"i": idu}).mappings().first()
            l = dict(l)
            if classee is None:
                l.update(result="PASS", severity="INFO", weight_applied=0.0,
                         detail="Aucune installation CLASSÉE (ICPE) à moins de 500 m — des sites "
                                "recensés Géorisques non classés peuvent exister (voir tableau, "
                                "avec leur régime).")
            else:
                l.update(detail=f"Installation classée (ICPE) à proximité — {classee['name']}, "
                                f"régime {classee['subtype']}, {classee['dist_m']} m.")
        elif nom == "proprietaire" and "non renseigné" in (l.get("detail") or ""):
            pm = db.execute(text(
                "SELECT denomination FROM parcelle_personne_morale WHERE idu = :i LIMIT 1"),
                {"i": idu}).scalar() if db.execute(text(
                "SELECT to_regclass('parcelle_personne_morale') IS NOT NULL")).scalar() else None
            if pm:
                l = dict(l)
                l.update(result="PASS", severity="INFO",
                         detail=f"Propriétaire personne morale : {pm} (fichier DGFiP — même "
                                "assiette que la carte propriétaire).")
        out.append(l)
    return out


#: rattachement couche → onglet. SOURCE UNIQUE (app.py importe ces deux-là — plus de duplication).
# RETOURS-11F4 (F0 « un fait, une section ») :
#  - `acces` quitte « marche » → pseudo-onglet « reseaux » : le VERDICT d'accès vit uniquement dans
#    la section « Réseaux et accès » (qui lit `acces` via f.lines), plus dans Marché (doublon F0).
#    Aucune section ne rend `ongletLines('reseaux')` → ces lignes ne réapparaissent nulle part ailleurs.
#  - `friche` + `ocs_ge` (occupation du sol / artificialisation ZAN) quittent « marche » → « regles » :
#    rapatriées dans Urbanisme (cible F4 : occupation/ZAN/friche). Marché ne porte plus que du PRIX.
#  - `sup` (assiettes de SUP — PM1/AC1/I4/EL7…) rejoint « risques » (défaut « regles » sinon) :
#    les servitudes d'utilité publique sont rapatriées d'Urbanisme vers « Risques et protections » (F6).
_ONGLET = {
    "regles": {"zonage_plu_gpu", "prescription_plu", "foncier_public", "emprise_lineaire",
               "residuel_socle", "safer", "sar", "surface", "parc_national", "foret_publique",
               "friche", "ocs_ge"},
    "risques": {"risques", "sol_pollue", "cavite", "icpe", "mvt", "pente", "ravine",
                "trait_de_cote", "abf", "ens", "eau", "bruit_route", "cinquante_pas", "sup"},
    "marche": {"dvf", "sitadel", "amenites", "potentiel_foncier_region"},
    "reseaux": {"acces"},
    "proprio": {"proprietaire", "age_dirigeant", "bodacc", "assemblage"},
}
_LAYER_ONGLET = {layer: onglet for onglet, layers in _ONGLET.items() for layer in layers}


def served_group(lines: list[dict], onglet: str) -> list[dict]:
    """Sous-ensemble des lignes servies d'un onglet, contraintes d'abord (HARD/SOFT), PASS ensuite."""
    grp = [l for l in lines if _LAYER_ONGLET.get(l["layer_name"], "regles") == onglet]
    ordre = {"HARD_EXCLUDE": 0, "SOFT_FLAG": 1, "UNKNOWN": 2, "PASS": 3, "POSITIVE": 3}
    return sorted(grp, key=lambda l: ordre.get(l["result"], 4))
