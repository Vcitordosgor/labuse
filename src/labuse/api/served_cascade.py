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
