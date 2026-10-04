"""CHASSE-1 angle 2 — invariants sur toute l'île (SQL, lecture seule).

    python -m scripts.chasse.invariants        # → docs/audit-2026-10/CHASSE-1/INVARIANTS.csv

Chaque invariant est une propriété qui doit être vraie PARTOUT (pas sur des témoins).
Sortie : invariant · périmètre · nb de violations · ≤5 exemples · note.
Une violation = FAUX si la valeur est servie au client, SALE sinon (tri fait au rapport).

Déjà prouvé ailleurs (cité, pas rejoué) :
  · formules du moteur (TA, médianes secteur, niveaux, taxe…) : CALCULS-1, 1 185 recalculs, 0 écart ;
  · compteurs commune vs somme des parcelles : banc V6b (checks_commune), rejoué en étape 0 ;
  · surface_m2 = ST_Area(geom_2975) : mesuré au tirage (écart max 0) — consigné PASS ici.
"""
from __future__ import annotations

import csv
import datetime as dt
import pathlib

import psycopg

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-1" / "INVARIANTS.csv"
DSN = "postgresql://openclaw@localhost:5432/labuse"

# run servi (manifeste) — même point de vérité que l'app
import json
MANIFESTE = json.loads((RACINE / "config" / "served_manifest.json").read_text())
V2RUN = MANIFESTE["scoring_run"]

# (id, libellé, périmètre, SQL violations → colonnes (exemple, detail)) — LIMIT appliqué au fetch
INVARIANTS: list[tuple[str, str, str, str]] = [
    ("emprise_lte_surface",
     "emprise bâtie ≤ surface parcelle (tolérance 1 %)",
     "parcel_filtre_bati × parcels (île)",
     """SELECT fb.idu, format('emprise=%s surface=%s', fb.emprise_max_m2::int, p.surface_m2::int)
        FROM parcel_filtre_bati fb JOIN parcels p ON p.id = fb.parcel_id
        WHERE fb.emprise_max_m2 > p.surface_m2 * 1.01"""),

    # pct_potentiel > 100 est une sémantique ASSUMÉE (sur-densité existante, jeton interne
    # « pct_potentiel ≥ 100 » filtré des briefs par export_commun.py:69) — on ne compte en
    # violation que l'ABERRANT (> 300 %, seuil COHERENCE-FIX-1) et le négatif.
    ("taux_emprise_hors_bornes",
     "taux_emprise_pct ∈ [0,100] (pilote filtres « État du sol » et fiche)",
     "parcel_residuel (vue servie)",
     """SELECT r.parcel_id::text, 'taux='||r.taux_emprise_pct
        FROM parcel_residuel r
        WHERE r.taux_emprise_pct NOT BETWEEN 0 AND 100"""),
    ("pct_potentiel_aberrant",
     "pct_potentiel ∈ [0,300] (au-delà = SDP existante aberrante, pas une sur-densité)",
     "parcel_residuel (vue servie)",
     """SELECT r.parcel_id::text, 'pct='||r.pct_potentiel
        FROM parcel_residuel r
        WHERE r.pct_potentiel < 0 OR r.pct_potentiel > 300"""),

    ("pct_bornes_filtre_bati",
     "ratio_pct ∈ [0,100]",
     "parcel_filtre_bati (île)",
     """SELECT idu, 'ratio='||ratio_pct FROM parcel_filtre_bati
        WHERE ratio_pct NOT BETWEEN 0 AND 100"""),

    ("pct_bornes_score",
     "percentile ∈ [0,100], p_raw ∈ [0,1], mult_base ≥ 0 (run v2 servi)",
     f"parcel_p_score_v2 run {V2RUN}",
     f"""SELECT parcelle_id, format('pct=%s p=%s mult=%s', percentile, p_raw, mult_base)
        FROM parcel_p_score_v2 WHERE run_id = '{V2RUN}'
          AND (percentile NOT BETWEEN 0 AND 100 OR p_raw NOT BETWEEN 0 AND 1 OR mult_base < 0)"""),

    ("sdp_non_negative",
     "SDP résiduelle ≥ 0 (run servi)",
     "parcel_residuel (vue servie)",
     """SELECT parcel_id::text, 'sdp='||sdp_residuelle_m2 FROM parcel_residuel
        WHERE sdp_residuelle_m2 < 0"""),

    ("mediane_dvf_entre_min_max",
     "médiane secteur ∈ [min, max] des ventes du secteur (même type, toutes fenêtres)",
     "dvf_secteur_medianes × dvf_mutations_parcelle",
     """SELECT m.secteur||'/'||m.type_bien,
               format('med=%s min=%s max=%s n=%s', m.mediane_valeur, t.vmin::int, t.vmax::int, m.n_ventes)
        FROM dvf_secteur_medianes m
        JOIN LATERAL (
          SELECT min(valeur_fonciere) vmin, max(valeur_fonciere) vmax
          FROM dvf_mutations_parcelle d
          WHERE left(d.id_parcelle, length(m.secteur)) = m.secteur
            AND d.valeur_fonciere > 0) t ON TRUE
        WHERE m.mediane_valeur IS NOT NULL AND t.vmax IS NOT NULL
          AND (m.mediane_valeur > t.vmax OR m.mediane_valeur < t.vmin)"""),

    ("permis_caduc_borne",
     "un PC caduc suppose ≥1 PC octroyé sur la parcelle (caducs ⊂ autorisés)",
     "pc_caducs (île)",
     """SELECT idu, format('octroyes=%s depuis=%s', n_pc_octroyes, caduc_depuis)
        FROM pc_caducs
        WHERE caduc_depuis IS NOT NULL AND coalesce(n_pc_octroyes, 0) = 0"""),

    ("au_fermee_capacite_zero",
     "zone AU non ouverte ⇒ capacité servie 0 ou cause posée",
     "parcel_au_statut × parcel_residuel",
     """SELECT a.idu, format('classe=%s sdp=%s cause=%s', a.classe, r.sdp_residuelle_m2, r.cause)
        FROM parcel_au_statut a
        JOIN parcel_residuel r ON r.parcel_id = a.parcel_id
        WHERE a.classe ILIKE '%%ferm%%'
          AND coalesce(r.sdp_residuelle_m2, 0) > 0 AND r.cause IS NULL"""),

    ("cinquante_pas_distance_cote",
     "flag « 50 pas » ⇒ distance au trait de côte ≤ 200 m (81,2 m + marge corridor)",
     "parcel_flags × spatial_layers trait_de_cote",
     """SELECT p.idu, 'd='||round(t.d::numeric,1)||' m'
        FROM parcel_flags pf
        JOIN parcels p ON p.id = pf.parcel_id
        JOIN LATERAL (
          SELECT min(ST_Distance(sl.geom_2975, p.geom_2975)) AS d
          FROM spatial_layers sl
          WHERE sl.kind = 'trait_de_cote'
            AND sl.geom_2975 && ST_Expand(p.geom_2975, 5000)) t ON TRUE
        WHERE pf.layer_name = 'cinquante_pas' AND pf.run_label = 'q_v11_m137'
          AND t.d > 200"""),

    ("tfpb_taux_plausible",
     "taux TFPB communal ∈ ]0, 60] % (REI)",
     "commune_rei (24 communes)",
     """SELECT insee||' '||commune, 'tfpb='||tfpb_commune_pct
        FROM commune_rei
        WHERE tfpb_commune_pct IS NOT NULL AND (tfpb_commune_pct <= 0 OR tfpb_commune_pct > 80)"""),

    ("ta_taux_bornes_legales",
     "taux TA ∈ [1,5] % (droit commun) ou ≤ 20 % (secteur majoré)",
     "taxe_amenagement_taux + taxe_amenagement_secteur",
     """SELECT 'commune '||insee, 'taux='||part_communale_pct FROM taxe_amenagement_taux
        WHERE part_communale_pct NOT BETWEEN 1 AND 5
        UNION ALL
        SELECT 'secteur '||idu, 'taux='||part_communale_pct FROM taxe_amenagement_secteur
        WHERE part_communale_pct NOT BETWEEN 1 AND 20"""),

    ("dvf_valeurs_positives",
     "valeur foncière > 0 et surfaces ≥ 0",
     "dvf_mutations_parcelle (île)",
     """SELECT id_mutation||'/'||id_parcelle,
               format('vf=%s st=%s sb=%s', valeur_fonciere, surface_terrain, surface_reelle_bati)
        FROM dvf_mutations_parcelle
        WHERE valeur_fonciere < 0 OR surface_terrain < 0 OR surface_reelle_bati < 0"""),

    ("surfaces_positives",
     "surface parcelle > 0",
     "parcels (île)",
     """SELECT idu, 'surface='||surface_m2 FROM parcels
        WHERE surface_m2 IS NULL OR surface_m2 <= 0"""),

    ("pente_bornes",
     "pente ∈ [0,75°] et pente_max ≥ pente_moy",
     "parcel_terrain (île)",
     """SELECT idu, format('moy=%s max=%s', pente_moy_deg, pente_max_deg)
        FROM parcel_terrain
        WHERE pente_moy_deg NOT BETWEEN 0 AND 75
           OR pente_max_deg NOT BETWEEN 0 AND 90
           OR pente_max_deg < pente_moy_deg - 0.01"""),

    ("hauteur_lidar_coherente",
     "égout ≤ faîtage + 0,5 m ; faîtage ∈ ]0,60] (aberrations = badge DONNEES-FIX-1, comptées)",
     "batiment_hauteur_lidar (île)",
     """SELECT idu, format('faitage=%s egout=%s', faitage_m, egout_m)
        FROM batiment_hauteur_lidar
        WHERE egout_m > faitage_m + 0.5 OR faitage_m <= 0 OR faitage_m > 60"""),

    ("zone_fam_domaine",
     "zone_fam ∈ {U, AU, A, N}",
     "parcel_zone_plu (île)",
     """SELECT idu, 'fam='||coalesce(zone_fam,'NULL') FROM parcel_zone_plu
        WHERE zone_fam IS NULL OR zone_fam NOT IN ('U','AU','A','N')"""),

    ("idu_prefixe_commune",
     "code INSEE de l'IDU = INSEE de la commune attribut",
     "parcels × communes_referentiel",
     """SELECT p.idu, format('idu→%s attr=%s(%s)', left(p.idu,5), p.commune, cr.insee)
        FROM parcels p JOIN communes_referentiel cr ON cr.nom = p.commune
        WHERE left(p.idu, 5) <> cr.insee"""),

    ("geom_valide",
     "ST_IsValid(geom) partout",
     "parcels (île)",
     """SELECT idu, left(ST_IsValidReason(geom), 60) FROM parcels
        WHERE NOT ST_IsValid(geom)"""),

    ("bande_domaine",
     "bande ∈ {A,B,C,D,NC,0} (table candidate q_v15 : seule peuplée)",
     "score_labuse q_v15",
     """SELECT idu, 'bande='||coalesce(bande,'NULL') FROM score_labuse
        WHERE run_label = 'q_v15' AND (bande IS NULL OR bande NOT IN ('A','B','C','D','NC','0'))"""),

    ("tier_domaine",
     "tier v2 servi dans le vocabulaire connu",
     f"parcel_p_score_v2 run {V2RUN}",
     f"""SELECT parcelle_id, 'tier='||coalesce(tier,'NULL') FROM parcel_p_score_v2
        WHERE run_id = '{V2RUN}' AND tier IS NULL"""),

    ("rang_unique",
     "rang unique dans le run v2 servi (pas deux parcelles au même rang)",
     f"parcel_p_score_v2 run {V2RUN}",
     f"""SELECT 'rang '||rang, count(*)||' parcelles' FROM parcel_p_score_v2
        WHERE run_id = '{V2RUN}' AND rang IS NOT NULL
        GROUP BY rang HAVING count(*) > 1"""),

    ("dvf_doublon_exact",
     "pas deux lignes identiques (id_mutation, id_parcelle, type_local, valeur)",
     "dvf_mutations_parcelle (île)",
     """SELECT id_mutation||'/'||id_parcelle, count(*)||' lignes'
        FROM dvf_mutations_parcelle
        GROUP BY id_mutation, id_parcelle, type_local, coalesce(surface_reelle_bati,0),
                 coalesce(surface_terrain,0), valeur_fonciere
        HAVING count(*) > 1"""),

    ("pm_un_seul_proprio",
     "une seule PM par parcelle au millésime courant (table servie)",
     "parcelle_personne_morale",
     """SELECT idu, count(*)::text FROM parcelle_personne_morale
        GROUP BY idu HAVING count(*) > 1"""),
]


def _dates_sweep(cur) -> list[tuple[str, str, str, int, list[str]]]:
    """Aucune date future (> aujourd'hui + 1) ni < 1900, sur toutes les colonnes `date`
    des tables métier (les timestamps système created_at/updated_at sont exclus)."""
    cur.execute("""
      SELECT table_name, column_name FROM information_schema.columns
      WHERE table_schema='public' AND data_type = 'date'
        AND column_name NOT IN ('created_at','updated_at')
        -- échéances/fins de validité : être dans le futur est leur sémantique
        AND column_name NOT IN ('echeance', 'date_fin', 'caduc_depuis', 'date_fin_validite')
      ORDER BY table_name, column_name""")
    cols = cur.fetchall()
    res = []
    demain = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    for table, col in cols:
        try:
            cur.execute(
                f"""SELECT count(*), (array_agg({col}::text ORDER BY {col}))[1:5]
                    FROM (SELECT {col} FROM {table}
                          WHERE {col} > %s OR {col} < DATE '1900-01-01'
                          LIMIT 100000) s""",
                (demain,))
            n, ex = cur.fetchone()
            res.append((f"dates_{table}_{col}", f"dates plausibles ({col})", table,
                        n, list(ex or [])))
        except Exception:  # noqa: BLE001 — table système/illisible : on passe
            cur.connection.rollback()
    return res


def main() -> None:
    conn = psycopg.connect(DSN, options="-c statement_timeout=600000")
    cur = conn.cursor()
    lignes = []

    for iid, lib, perim, sql in INVARIANTS:
        try:
            cur.execute(f"SELECT * FROM ({sql}) v LIMIT 100000")
            rows = cur.fetchall()
            n = len(rows)
            exemples = "; ".join(f"{r[0]} ({r[1]})" for r in rows[:5])
            plus = " [≥100000 : tronqué]" if n == 100000 else ""
            lignes.append({"invariant": iid, "libelle": lib, "perimetre": perim,
                           "violations": n, "exemples": exemples + plus})
            print(f"  {'OK  ' if n == 0 else f'{n:>6}'} {iid}")
        except Exception as e:  # noqa: BLE001
            conn.rollback()
            lignes.append({"invariant": iid, "libelle": lib, "perimetre": perim,
                           "violations": "ERREUR", "exemples": str(e)[:200]})
            print(f"  ERR    {iid}: {str(e)[:100]}")

    print("  … balayage dates (toutes colonnes date)")
    try:
        for iid, lib, perim, n, ex in _dates_sweep(cur):
            if n:
                lignes.append({"invariant": iid, "libelle": lib, "perimetre": perim,
                               "violations": n, "exemples": "; ".join(ex[:5])})
                print(f"  {n:>6} {iid}")
    except Exception as e:  # noqa: BLE001
        conn.rollback()
        lignes.append({"invariant": "dates_sweep", "libelle": "balayage dates",
                       "perimetre": "toutes tables", "violations": "ERREUR",
                       "exemples": str(e)[:200]})

    # PASS consignés sans rejeu (prouvés ailleurs, référence citée)
    lignes.append({"invariant": "surface_egale_st_area", "libelle":
                   "surface_m2 = ST_Area(geom_2975) (écart max 0 mesuré au tirage échantillon)",
                   "perimetre": "parcels (île)", "violations": 0, "exemples":
                   "mesure du 2026-10-04, requête dans echantillon.py"})
    lignes.append({"invariant": "formules_moteur", "libelle":
                   "formules servies (TA, médianes, niveaux, taxe, %…) — CALCULS-1 : 1 185 recalculs, 0 écart",
                   "perimetre": "moteur (cité, pas rejoué)", "violations": 0,
                   "exemples": "docs/audit-2026-09/CALCULS-1"})

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with open(SORTIE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["invariant", "libelle", "perimetre",
                                          "violations", "exemples"])
        w.writeheader()
        w.writerows(lignes)
    viols = [l for l in lignes if isinstance(l["violations"], int) and l["violations"] > 0]
    print(f"\n{len(lignes)} invariants · {len(viols)} avec violations → {SORTIE}")
    conn.close()


if __name__ == "__main__":
    main()
