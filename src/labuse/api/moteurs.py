"""MOTEURS (Vague 4) — M15 simulateur PLU · M16 assemblage · M17 ZAN · M18 baromètre.

Doctrine inchangée : rien n'est persisté dans le scoring, tout est étiqueté (estimation /
à instruire / indicatif). Les simulations sont des recalculs À BLANC en mémoire.
"""
from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/moteurs", tags=["moteurs"])
from ..scoring.score_v_constants import Q_A_RUN_LABEL as RUN  # run de référence (bascule centralisée)


def get_db():
    from .app import get_db as _g
    yield from _g()


def _v2run(db: Session) -> str | None:
    """Run scoring v2 servi (M5.1 lot 3.1) — import différé (cycle app ↔ moteurs)."""
    from .app import _score_v2_run_id
    return _score_v2_run_id(db)


# ───────────────────────── M15 — SIMULATEUR PLU ─────────────────────────
# « Et si cette zone AU passait en U ? » — recalcul À BLANC, JAMAIS persisté.
# Méthode (documentée, honnête) : ESTIMATION PAR ANALOGIE — la SDP estimée des parcelles AU
# = surface × ratio médian (SDP résiduelle / surface) observé sur les parcelles U de la commune
# qui ont un résiduel calculé. Périmètre V1 : une commune, un zonage à la fois.

@router.get("/simulplu/zones")
def simulplu_zones(commune: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(text("""
        SELECT sl.subtype AS zone, count(*) AS n_ilots
        FROM spatial_layers sl WHERE sl.kind = 'plu_gpu_zone' AND (CAST(:c AS text) IS NULL OR sl.commune = :c)
          AND upper(sl.subtype) LIKE 'AU%'
        GROUP BY sl.subtype ORDER BY n_ilots DESC"""), {"c": commune}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/simulplu")
def simulplu(zone: str, commune: str | None = None, db: Session = Depends(get_db)) -> dict:
    # PERF : le zonage par parcelle est DÉJÀ résolu dans les lignes de cascade du run (detail
    # « Zone PLU « X » … ») → zéro jointure spatiale (l'ancienne version : 2 min 33 s ; celle-ci < 2 s).
    ratio = db.execute(text("""
        SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY r.sdp_residuelle_m2 / NULLIF(p.surface_m2, 0))
        FROM dryrun_cascade_results cr
        JOIN parcels p ON p.id = cr.parcel_id AND (CAST(:c AS text) IS NULL OR p.commune = :c)
        JOIN parcel_residuel r ON r.parcel_id = p.id AND r.sdp_residuelle_m2 > 0
        WHERE cr.run_label = :run AND cr.layer_name = 'zonage_plu_gpu'
          AND cr.detail LIKE 'Zone PLU « U%'"""),
        {"c": commune, "run": RUN}).scalar() or 0.0
    rows = db.execute(text("""
        SELECT p.idu, round(p.surface_m2) AS surface_m2, d.matrice_statut AS statut_actuel, d.q_score,
               s2.tier AS tier_v2, s2.rang AS rang_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0,
               ST_AsGeoJSON(ST_Transform(p.geom_2975, 4326)) AS g
        FROM dryrun_cascade_results cr
        JOIN parcels p ON p.id = cr.parcel_id AND (CAST(:c AS text) IS NULL OR p.commune = :c)
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        WHERE cr.run_label = :run AND cr.layer_name = 'zonage_plu_gpu'
          AND cr.detail LIKE ('%« ' || :z || ' »%') AND p.surface_m2 >= 300
        ORDER BY p.surface_m2 DESC LIMIT 400"""),
        {"c": commune, "z": zone, "run": RUN, "v2run": _v2run(db)}).mappings().all()
    items = []
    bascules = 0
    for r in rows:
        sdp_est = round(float(r["surface_m2"] or 0) * float(ratio))
        # bandes du socle v2 : ≥300 m² = un signal positif s'ouvre (bascule potentielle)
        bascule = sdp_est >= 300 and r["statut_actuel"] in ("ecartee", "a_creuser")
        bascules += bascule
        items.append({"idu": r["idu"], "surface_m2": r["surface_m2"], "statut_actuel": r["statut_actuel"],
                      "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"], "etage0": bool(r["etage0"]),
                      "q_actuel": r["q_score"], "sdp_estimee_m2": sdp_est, "bascule_potentielle": bascule,
                      "geom": json.loads(r["g"])})
    return {
        "zone": zone, "commune": commune or "Toute l'île", "ratio_analogie": round(float(ratio), 3),
        "methode": ("SIMULATION À BLANC (rien n'est persisté) — SDP estimée par ANALOGIE : "
                    f"surface × ratio médian SDP/surface des parcelles U de {commune or 'toute l’île'} "
                    f"({round(float(ratio), 3)}). Le vrai recalcul = règlement U appliqué au moteur "
                    "de faisabilité (prochain cycle)."),
        "n_parcelles": len(items), "bascules_potentielles": bascules,
        "sdp_totale_estimee_m2": sum(i["sdp_estimee_m2"] for i in items),
        "items": items,
    }


# ───────────────────────── M16 — ASSEMBLAGE MULTI-PARCELLES ─────────────────────────

class AssemblageIn(BaseModel):
    idus: list[str]


@router.post("/assemblage")
def assemblage(body: AssemblageIn, db: Session = Depends(get_db)) -> dict:
    idus = [i.strip().upper() for i in body.idus if i.strip()][:30]
    if len(idus) < 2:
        raise HTTPException(422, "Sélectionnez au moins 2 parcelles")
    rows = db.execute(text("""
        SELECT p.id, p.idu, round(p.surface_m2) AS surface_m2, r.sdp_residuelle_m2,
               d.matrice_statut AS statut, d.q_score,
               s2.tier AS tier_v2, s2.rang AS rang_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0,
               COALESCE(pm.denomination, 'particulier / personne physique') AS proprietaire
        FROM parcels p
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        LEFT JOIN parcelle_personne_morale pm ON pm.idu = p.idu
        WHERE p.idu = ANY(:idus)"""), {"idus": idus, "run": RUN, "v2run": _v2run(db)}).mappings().all()
    if len(rows) < 2:
        raise HTTPException(404, f"{len(rows)} parcelle(s) trouvée(s) sur {len(idus)}")
    # contiguïté : graphe des adjacences (≤ 1 m) → l'assiette est-elle d'un seul tenant ?
    ids = [r["id"] for r in rows]
    pairs = db.execute(text("""
        SELECT a.id AS a, b.id AS b FROM parcels a JOIN parcels b
          ON a.id < b.id AND ST_DWithin(a.geom_2975, b.geom_2975, 1)
        WHERE a.id = ANY(:ids) AND b.id = ANY(:ids)"""), {"ids": ids}).all()
    adj: dict[int, set[int]] = {i: set() for i in ids}
    for a, b in pairs:
        adj[a].add(b)
        adj[b].add(a)
    seen, stack = {ids[0]}, [ids[0]]
    while stack:
        for nb in adj[stack.pop()]:
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    contigu = len(seen) == len(ids)
    owners = sorted({r["proprietaire"] for r in rows})
    surface = sum(r["surface_m2"] or 0 for r in rows)
    sdp = sum(r["sdp_residuelle_m2"] or 0 for r in rows)
    # score d'assemblage simple : d'un seul tenant + peu de propriétaires + SDP cumulée
    score = round(min(100, (45 if contigu else 10) + 25 * min(1, 2 / max(1, len(owners)))
                  + 30 * min(1, sdp / 3000)))
    return {
        "n": len(rows), "contigu": contigu, "surface_totale_m2": round(surface),
        "sdp_cumulee_m2": round(sdp),
        "note_sdp": "SDP cumulée = SOMME des résiduels parcellaires — le règlement d'ensemble "
                    "(assiette fusionnée) est à instruire : la vraie SDP peut différer.",
        "proprietaires": owners, "n_proprietaires": len(owners),
        "score_assemblage": score,
        "items": [{**{k: r[k] for k in ("idu", "surface_m2", "sdp_residuelle_m2", "statut", "q_score", "proprietaire")},
                   "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"], "etage0": bool(r["etage0"])}
                  for r in rows],
    }


# ───────────────────────── M17 — SIMULATEUR ZAN ─────────────────────────

@router.get("/zan")
def zan(db: Session = Depends(get_db)) -> dict:
    communes = db.execute(text("""
        SELECT sl.commune, count(*) FILTER (WHERE sl.subtype = 'artificialise') AS ilots_artif,
               round(sum(ST_Area(sl.geom_2975)) FILTER (WHERE sl.subtype = 'artificialise') / 10000) AS ha_artif,
               round(sum(ST_Area(sl.geom_2975)) / 10000) AS ha_couverts
        FROM spatial_layers sl WHERE sl.kind = 'ocs_ge' AND sl.commune IS NOT NULL
        GROUP BY sl.commune ORDER BY ha_artif DESC NULLS LAST"""), ).mappings().all()
    # parcelles « ZAN-compatibles » : artificialisées NON bâties, promues (bonus ocs_ge > 0 au run)
    rows = db.execute(text("""
        SELECT p.idu, round(p.surface_m2) AS surface_m2, d.matrice_statut AS statut, d.q_score,
               s2.tier AS tier_v2, s2.rang AS rang_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0,
               ST_AsGeoJSON(ST_Transform(p.geom_2975, 4326)) AS g
        FROM dryrun_cascade_results cr
        JOIN parcels p ON p.id = cr.parcel_id
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        WHERE cr.run_label = :run AND cr.layer_name = 'ocs_ge' AND cr.weight_applied > 0
          AND d.matrice_statut IN ('chaude', 'a_surveiller', 'a_creuser')
        ORDER BY d.q_score DESC LIMIT 400"""), {"run": RUN, "v2run": _v2run(db)}).mappings().all()
    return {
        "bandeau": ("Quotas SAR/SCOT en attente de données officielles — lecture INDICATIVE. "
                    "OCS GE partiel (communes ingérées uniquement). Construire sur de l'artificialisé "
                    "= zéro dette ZAN."),
        "communes": [dict(r) for r in communes],
        "zan_compatibles": [{**{k: r[k] for k in ("idu", "surface_m2", "statut", "q_score")},
                             "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"], "etage0": bool(r["etage0"]),
                             "geom": json.loads(r["g"])} for r in rows],
    }


# ───────────────────────── M18 — BAROMÈTRE FONCIER ─────────────────────────

#: Critère P1-03 (M6 Phase 2a) : une mutation n'entre dans le Baromètre — médianes ET
#: volumes affichés — que si elle est une VENTE au sens strict. Voir `_barometre_data`.
_BAROMETRE_RETENUE = """nature_mutation = 'Vente'
                 AND valeur_fonciere > 1000
                 AND valeur_fonciere / NULLIF(surface_reelle_bati, 0) BETWEEN 100 AND 12000"""


def _barometre_data(db: Session) -> dict:
    """Baromètre foncier M18 — séries DVF et Sitadel, île entière (JSON + PDF marketing).

    Critère outliers (P1-03, audit M6 §1.1b BLOC B) — appliqué aux MÉDIANES ET AUX
    VOLUMES (`_BAROMETRE_RETENUE`) ; avant P1-03 les volumes n'avaient AUCUN filtre :

    - ``nature_mutation = 'Vente'`` : écarte la VEFA (du neuf — comparable à part, pas
      la même série de prix que l'ancien : médiane VEFA ~4 700-5 300 €/m² contre ~2 800
      servis), les adjudications, échanges, expropriations et « vente terrain à bâtir »
      (hors-objet d'une médiane €/m² bâti) ;
    - ``valeur_fonciere > 1000`` € : prix symboliques — donations déguisées, apports,
      régularisations (211 mutations ≤ 1 € au grain source, 31 ≤ 1 000 € dans la table).
      Seuil 1 000 € retenu car (a) déjà la convention du module marché (`dvf_marche.py`,
      « ventes à 1 € symbolique écartées ») et (b) creux net de la distribution : 18
      mutations ≤ 100 €, 13 entre 100 et 1 000 €, puis reprise (77 entre 1 et 5 k€) —
      aucun bien bâti réel ne se vend sous 1 000 € ;
    - ``€/m² ∈ [100, 12 000]`` : garde-fou historique contre les ratios aberrants
      (surfaces mal agrégées résiduelles). La cause principale — lignes d'un même local
      répétées par nature de culture et SOMMÉES (1 440 surfaces ×2,6) — est corrigée à
      la racine dans `_geo_dvf_aggregate` (layers_ingest.py) + re-fabrication SQL
      `reports/m6-audit/sql/p1_03_dvf_surfaces_fix.sql` (rollback fourni).

    Transparence : chaque trimestre porte `ecartees` (mutations hors critère) et le
    payload global `ecartees` ventile la fenêtre entière — « médiane sur N ventes,
    M écartées (VEFA, prix symboliques…) ».
    """
    dvf = db.execute(text(f"""
        SELECT to_char(date_trunc('quarter', date_mutation), 'YYYY"T"Q') AS trimestre,
               count(*) FILTER (WHERE {_BAROMETRE_RETENUE}) AS mutations,
               (count(*) - count(*) FILTER (WHERE {_BAROMETRE_RETENUE}))::int AS ecartees,
               round(percentile_cont(0.5) WITHIN GROUP (
                 ORDER BY valeur_fonciere / NULLIF(surface_reelle_bati, 0))
                 FILTER (WHERE {_BAROMETRE_RETENUE}))::int AS median_eur_m2_bati
        FROM dvf_mutations WHERE date_mutation IS NOT NULL
        GROUP BY 1 ORDER BY 1 DESC LIMIT 8"""), ).mappings().all()
    permis = db.execute(text("""
        SELECT to_char(date_trunc('quarter', date), 'YYYY"T"Q') AS trimestre, count(*) AS permis
        FROM sitadel_permits GROUP BY 1 ORDER BY 1 DESC LIMIT 8"""), ).mappings().all()
    top_communes = db.execute(text(f"""
        SELECT commune, count(*) AS mutations,
               round(percentile_cont(0.5) WITHIN GROUP (
                 ORDER BY valeur_fonciere / NULLIF(surface_reelle_bati, 0)))::int AS median_eur_m2
        FROM dvf_mutations WHERE {_BAROMETRE_RETENUE}
        GROUP BY commune HAVING count(*) >= 100
        ORDER BY median_eur_m2 DESC NULLS LAST LIMIT 8"""), ).mappings().all()
    ecartees = db.execute(text(f"""
        SELECT (count(*) - count(*) FILTER (WHERE {_BAROMETRE_RETENUE}))::int AS total,
               count(*) FILTER (WHERE nature_mutation = 'Vente en l''état futur d''achèvement')::int AS vefa,
               count(*) FILTER (WHERE nature_mutation NOT IN
                 ('Vente', 'Vente en l''état futur d''achèvement'))::int AS autres_natures,
               count(*) FILTER (WHERE nature_mutation = 'Vente'
                 AND (valeur_fonciere IS NULL OR valeur_fonciere <= 1000))::int AS prix_symboliques,
               count(*) FILTER (WHERE nature_mutation = 'Vente' AND valeur_fonciere > 1000
                 AND (surface_reelle_bati IS NULL OR surface_reelle_bati <= 0
                      OR valeur_fonciere / NULLIF(surface_reelle_bati, 0)
                         NOT BETWEEN 100 AND 12000))::int AS ratio_hors_bande
        FROM dvf_mutations"""), ).mappings().one()
    return {"perimetre": "île entière (24 communes DVF, flux Sitadel régional)",
            "criteres": ("Ventes strictes uniquement (P1-03) : nature 'Vente', prix > 1 000 €, "
                         "€/m² bâti dans [100, 12 000] — médianes ET volumes. Écartées : VEFA (neuf), "
                         "adjudications/échanges/expropriations, prix symboliques, ratios aberrants."),
            "dvf_trimestres": [dict(r) for r in dvf], "permis_trimestres": [dict(r) for r in permis],
            "top_communes_prix": [dict(r) for r in top_communes], "ecartees": dict(ecartees)}


@router.get("/barometre")
def barometre(db: Session = Depends(get_db)) -> dict:
    return _barometre_data(db)


@router.get("/barometre.pdf")
def barometre_pdf(db: Session = Depends(get_db)) -> Response:
    """Rapport trimestriel auto-généré — le canal marketing. Palette impression (blanc)."""
    from fpdf import FPDF

    from .pdf_premium import FONTS, LINE, MINT, SURFACE, TXT, TXT_DIM, TXT_HI, TXT_MUT

    d = _barometre_data(db)
    pdf = FPDF(format="A4")
    pdf.add_font("inter", fname=str(FONTS / "Inter-Regular.ttf"))
    pdf.add_font("mono", fname=str(FONTS / "JetBrainsMono-Regular.ttf"))
    pdf.add_font("grotesk", fname=str(FONTS / "SpaceGrotesk-Bold.ttf"))
    pdf.set_margins(16, 14, 16)
    pdf.add_page()
    pdf.set_draw_color(*MINT)
    pdf.set_line_width(0.6)
    pdf.line(16, 10, pdf.w - 16, 10)
    pdf.set_font("grotesk", size=16)
    pdf.set_text_color(*MINT)
    pdf.cell(0, 9, "BAROMÈTRE FONCIER — LA RÉUNION", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("inter", size=8)
    pdf.set_text_color(*TXT_DIM)
    pdf.cell(0, 5, f"LABUSE · rapport auto-généré du {date.today().isoformat()} · {d['perimetre']}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    def table(titre: str, headers: list[str], rows: list[list], widths: list[int]) -> None:
        pdf.set_font("mono", size=8)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(0, 6, titre, new_x="LMARGIN", new_y="NEXT")
        pdf.set_fill_color(*SURFACE)
        pdf.set_font("inter", size=7.5)
        pdf.set_text_color(*TXT_MUT)
        for h, w in zip(headers, widths):
            pdf.cell(w, 6, h, fill=True)
        pdf.ln()
        pdf.set_text_color(*TXT)
        pdf.set_draw_color(*LINE)
        for row in rows:
            for v, w in zip(row, widths):
                pdf.cell(w, 5.6, str(v if v is not None else "—"), border="B")
            pdf.ln()
        pdf.ln(4)

    table("MARCHÉ DVF PAR TRIMESTRE (VENTES STRICTES)", ["Trimestre", "Ventes", "Écartées", "Médiane €/m² bâti"],
          [[r["trimestre"], r["mutations"], r["ecartees"], r["median_eur_m2_bati"]] for r in d["dvf_trimestres"]],
          [40, 35, 30, 55])
    table("PERMIS (SITADEL) PAR TRIMESTRE", ["Trimestre", "Permis"],
          [[r["trimestre"], r["permis"]] for r in d["permis_trimestres"]], [50, 40])
    table("PRIX PAR COMMUNE (TOP)", ["Commune", "Mutations", "Médiane €/m²"],
          [[r["commune"], r["mutations"], r["median_eur_m2"]] for r in d["top_communes_prix"]],
          [70, 40, 50])
    pdf.set_font("inter", size=6.5)
    pdf.set_text_color(*TXT_DIM)
    pdf.set_text_color(*TXT_HI)
    pdf.set_text_color(*TXT_DIM)
    e = d["ecartees"]
    pdf.multi_cell(0, 4, f"Périmètre DVF : ventes strictes uniquement — {e['total']} mutations écartées "
                         f"de la fenêtre (VEFA {e['vefa']}, adjudications/échanges/expropriations "
                         f"{e['autres_natures']}, prix ≤ 1 000 € {e['prix_symboliques']}, "
                         f"€/m² hors bande 100-12 000 : {e['ratio_hors_bande']}).")
    pdf.multi_cell(0, 4, "Données publiques (DVF, Sitadel régional) — indicateurs indicatifs, "
                         "ne valent pas expertise. © LABUSE")
    return Response(bytes(pdf.output()), media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="barometre_labuse.pdf"'})
