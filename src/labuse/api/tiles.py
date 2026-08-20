"""Tuiles vectorielles MVT — la carte ÎLE ENTIÈRE (431k parcelles).

Le GeoJSON par commune (26 Mo à Saint-Paul) ne tient pas à l'échelle de l'île : on sert du
MVT depuis une table MATÉRIALISÉE `mvt_parcels` (statuts + propriétés de filtre pré-joints,
géométrie en 3857, GIST) reconstruite après chaque run de scoring (`labuse build-mvt`).
Doctrine perf (R1, revue Vic n°2) : TOUT dès z9 — simplification par palier (z9 : 10 m ≈
3,4 Mo/tuile · z10 : 5 m · z11 : 2 m · z12+ : brut ≈ 850 Ko max), cache LRU + navigateur.
Les propriétés portent EXACTEMENT les clés du GeoJSON commune (idu, status, q_score…) pour
que les expressions de filtre MapLibre soient IDENTIQUES sur les deux sources ; `flags` est
une chaîne CSV (le MVT ne porte pas de tableaux) — l'expression `['in', flag, ['get','flags']]`
fonctionne à l'identique sur chaîne et tableau.
"""
from __future__ import annotations

from collections import OrderedDict

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(tags=["tiles"])

from ..scoring.score_v_constants import Q_A_RUN_LABEL as RUN  # run de référence (bascule centralisée)
_PROMUES = ("chaude", "a_surveiller", "a_creuser")


def get_db():  # branché sur la session app au moment de l'inclusion (cf. app.py)
    from .app import get_db as _g
    yield from _g()


def build_parcel_zone_plu(db: Session) -> int:
    """M6.1 item 1 — table dérivée `parcel_zone_plu` (idu PK, zone_lib, zone_fam) : la zone
    PLU DOMINANTE par surface d'intersection (spatial_layers kind='plu_gpu_zone', dédoublonné
    M6-2b). `zone_lib` = CODE COURT de zone (« U1e », « 1AUc ») dérivé du 1er token de
    `attrs.libelle` (source FIABLE du code fin, alignée sur la faisabilité) ; repli sur l'ancienne
    heuristique `name` quand libelle est absent. Correctif ingestion (arbitrage RE-RUN pt2.4) : le
    `name` GPU est hétérogène (parfois libelong « Zone urbaine… », parfois ID numérique Cilaos) →
    8 communes avaient leur zone_lib réduit à la FAMILLE (U/AU) ou à un ID, rendant la calibration
    au_statut/affichage inerte. `zone_fam` = famille dérivée du typezone (AU* → AU,
    U* → U, A, N, sinon autre). Build one-shot ~20-40 min sous charge — appelée par
    build_mvt_table SI la table est absente, jointe ensuite en LEFT JOIN (une parcelle hors
    zonage GPU n'apparaît pas ici → colonnes NULL côté tuiles/geojson)."""
    db.execute(text("SET statement_timeout = 0"))
    db.execute(text("DROP TABLE IF EXISTS parcel_zone_plu"))
    # ST_MakeValid sur les 5 848 zones (une géométrie GPU invalide ferait échouer
    # ST_Intersection) ; la jointure s'appuie sur idx_parcels_geom_2975 (nested loop côté zones).
    db.execute(text("""
        CREATE TABLE parcel_zone_plu AS
        WITH z0 AS (
            SELECT name, subtype, ST_MakeValid(geom_2975) AS g,
                   rtrim(split_part(btrim(name), ' ', 1), ':') AS tok,
                   -- SOURCE FIABLE du code fin (arbitrage RE-RUN pt2.4/ingestion) : le GPU met le
                   -- code court dans attrs.libelle (Ud, 1AUb, Uf…), alors que `name` est hétérogène
                   -- (parfois le libelong « Zone urbaine mixte… », parfois un ID numérique Cilaos).
                   -- On prend le 1er token du libelle (strip des suffixes OAP/secteur « 1AUa oap3 »
                   -- → « 1AUa », « Nto 1 » → « Nto »). MÊME source que la faisabilité (faisabilite/db.py
                   -- _CTX : COALESCE(attrs->>'libelle',…)) → parcel_zone_plu cesse de diverger d'elle.
                   rtrim(split_part(btrim(attrs->>'libelle'), ' ', 1), ':') AS lib_tok,
                   -- libellé COMPLET conservé (pt3 Vic) : le suffixe OAP (« 1AUa oap3 ») n'est PAS du
                   -- bruit — l'OAP prévaut sur le règlement ; on garde l'info pour le branchement OAP.
                   NULLIF(btrim(attrs->>'libelle'), '') AS lib_full,
                   CASE WHEN subtype ILIKE 'AU%' THEN 'AU'
                        WHEN subtype ILIKE 'U%'  THEN 'U'
                        WHEN subtype = 'A'       THEN 'A'
                        WHEN subtype = 'N'       THEN 'N'
                        ELSE 'autre' END AS fam
            FROM spatial_layers WHERE kind = 'plu_gpu_zone'
        ), z AS (
            SELECT g, CAST(fam AS varchar) AS fam, lib_full,
                   -- libelle (1er token) PRIORITAIRE ; repli sur l'ancienne heuristique name/tok/fam
                   -- (inchangée) quand libelle est absent → aucune régression là où name suffisait.
                   CAST(COALESCE(NULLIF(lib_tok, ''),
                        CASE WHEN name NOT LIKE '% %' THEN name
                             WHEN length(tok) BETWEEN 1 AND 10 AND (
                                  (fam = 'AU' AND tok ~* '^[0-9]{0,2}AU')
                               OR (fam = 'U'  AND tok ~* '^[0-9]{0,2}U')
                               OR (fam = 'A'  AND tok ~* '^A')
                               OR (fam = 'N'  AND tok ~* '^N'))
                             THEN tok ELSE fam END) AS varchar) AS lib
            FROM z0
        )
        SELECT DISTINCT ON (p.idu)
               p.idu, z.lib AS zone_lib, z.fam AS zone_fam, z.lib_full AS zone_libelle,
               -- M99 (arbitrage Vic) : clé NORMALISÉE du filtre, graphie réglementaire MAJUSCULE.
               -- La casse mixte est une graphie de canal d'ingestion (coexistence intra-commune
               -- nulle, règlement toujours en majuscules — AUDIT_M99_ZONAGE.md). zone_lib
               -- d'origine est CONSERVÉ (la fiche affiche la graphie officielle de sa commune) ;
               -- zone_filtre est LE critère servi au filtre — un critère, un endroit (ici).
               upper(z.lib) AS zone_filtre
        FROM parcels p
        JOIN z ON p.geom_2975 && z.g AND ST_Intersects(p.geom_2975, z.g)
        ORDER BY p.idu, ST_Area(ST_Intersection(p.geom_2975, z.g)) DESC
    """))
    db.execute(text("ALTER TABLE parcel_zone_plu ADD PRIMARY KEY (idu)"))
    db.execute(text("ANALYZE parcel_zone_plu"))
    n = db.execute(text("SELECT count(*) FROM parcel_zone_plu")).scalar() or 0
    db.commit()
    return int(n)


def build_parcel_adresse(db: Session) -> int:
    """M6.2 perf — table dérivée `parcel_adresse` (idu PK, ban_voie/ban_cp/ban_commune) : la
    MEILLEURE adresse BAN par parcelle, matérialisée une fois. Élimine le LATERAL par parcelle
    (regexp + tri, ~5,4 s pour 21k parcelles en mode commune) qui pesait sur geojson/liste/CSV.
    Sélection STRICTEMENT identique au lateral (_BAN_ORDER) via DISTINCT ON → mêmes adresses.
    Rebuild rapide (~1,5 s pour 257k) ; à relancer si la BAN est ré-ingérée (build-mvt le fait)."""
    if not db.execute(text("SELECT to_regclass('adresse_parcelles') IS NOT NULL"
                           " AND to_regclass('adresses') IS NOT NULL")).scalar():
        return 0
    db.execute(text("DROP TABLE IF EXISTS parcel_adresse"))
    db.execute(text(r"""
        CREATE TABLE parcel_adresse AS
        SELECT DISTINCT ON (ap.idu) ap.idu,
               trim(concat_ws(' ', a.numero, a.rep, a.voie)) AS ban_voie,
               a.code_postal AS ban_cp, a.commune AS ban_commune
        FROM adresse_parcelles ap JOIN adresses a ON a.id_ban = ap.id_ban
        ORDER BY ap.idu, (ap.source = 'principal') DESC, (a.numero IS NULL),
                 NULLIF(regexp_replace(a.numero, '\D', '', 'g'), '')::int NULLS LAST, a.id_ban
    """))
    db.execute(text("ALTER TABLE parcel_adresse ADD PRIMARY KEY (idu)"))
    db.execute(text("ANALYZE parcel_adresse"))
    n = db.execute(text("SELECT count(*) FROM parcel_adresse")).scalar() or 0
    db.commit()
    return int(n)


def build_mvt_table(db: Session, run_label: str = RUN) -> int:
    """(Re)construit la table matérialisée servie en tuiles. À lancer APRÈS un run de scoring
    (le script d'extension île le fait) ; idempotent, ~1-2 min pour 431k parcelles."""
    # M6.1 : le zonage PLU par parcelle est un prérequis des tuiles — construit une seule fois
    # (long) puis réutilisé tel quel à chaque rebuild (le zonage ne bouge pas avec les runs).
    if not db.execute(text("SELECT to_regclass('parcel_zone_plu')")).scalar():
        build_parcel_zone_plu(db)
    # M6.2 : adresse BAN matérialisée (rapide) — reconstruite à chaque build-mvt (suit la BAN).
    build_parcel_adresse(db)
    db.execute(text("DROP TABLE IF EXISTS mvt_parcels"))
    # correctif M5 (verdict) : tier v2 embarqué dans les tuiles — la carte colore par le
    # verdict effectif (tier v2 quand un run existe, étage 0 du run servi prime).
    # M-L : le run v2 embarqué est ÉPINGLÉ au label servi (Q_A_RUN_LABEL = RUN, source unique
    # de vérité) — MÊME règle que la fiche (`score_v2._served_run`). Plus jamais « le dernier par
    # computed_at » : un run CANDIDAT calculé après le servi bâtirait les tuiles sur le mauvais
    # run et la carte contredirait la fiche. Label absent → échec bruyant, pas de repli silencieux.
    v2run = db.execute(text(
        "SELECT run_id FROM p_score_v2_runs WHERE run_id = :r"), {"r": RUN}).scalar()
    if v2run is None:
        raise RuntimeError(
            f"run servi « {RUN} » absent de p_score_v2_runs — "
            "lancer `labuse score-v2` ou vérifier LABUSE_SERVED_RUN.")
    db.execute(text("""
        CREATE TABLE mvt_parcels AS
        SELECT p.id, p.idu, p.commune, p.surface_m2,
               ST_Transform(p.geom, 3857) AS geom_3857,
               -- M48 (F4) : `matrice_statut` (v1 morte) N'EST PLUS bakée comme `status` — elle
               -- contredisait tier_v2. La carte colore par tier_v2 (+ etage0). `d.status` ci-dessous
               -- reste le statut d'EXCLUSION (exclue/faux_positif) qui alimente etage0, pas la matrice.
               -- M129-B : q/a (matrice morte) retirés des tuiles
               s2.tier AS tier_v2, s2.rang AS rang_v2, s2.mult_base AS mult_v2,
               (d.status IN ('exclue', 'faux_positif_probable'))::int AS etage0,
               d.completeness_score, r.sdp_residuelle_m2, r.sous_densite,
               CASE WHEN ev.parcel_id IS NOT NULL THEN 'rouge' END AS evenement,
               COALESCE(fl.flags, '') AS flags,
               zp.zone_lib, zp.zone_fam
        FROM parcels p
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        LEFT JOIN parcel_zone_plu zp ON zp.idu = p.idu
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        LEFT JOIN (SELECT DISTINCT parcel_id FROM dryrun_cascade_results
                   WHERE run_label = :run AND evenement = 'rouge') ev ON ev.parcel_id = p.id
        LEFT JOIN (SELECT parcel_id, string_agg(DISTINCT layer_name, ',') AS flags
                   FROM dryrun_cascade_results
                   WHERE run_label = :run AND (result = 'SOFT_FLAG'
                         OR (layer_name = 'abf' AND result = 'UNKNOWN'))
                   GROUP BY parcel_id) fl ON fl.parcel_id = p.id
    """), {"run": run_label, "v2run": v2run})
    db.execute(text("CREATE INDEX mvt_parcels_gix ON mvt_parcels USING GIST (geom_3857)"))
    # M-L : index `mvt_parcels_status` SUPPRIMÉ — la colonne `status` n'est plus bakée depuis M48
    # (vestige d'avant M48 ; ce CREATE INDEX aurait levé au rebuild). Aucun index de remplacement :
    # `tier_v2` n'est QUE projeté (propriétés servies), jamais filtré/trié — le seul filtre à la
    # volée est spatial (`geom_3857 && env`), déjà couvert par le GIST ci-dessus.
    db.execute(text("ANALYZE mvt_parcels"))
    n = db.execute(text("SELECT count(*) FROM mvt_parcels")).scalar() or 0
    db.commit()
    _CACHE.clear()
    return int(n)


def build_parcel_flags_table(db: Session, run_label: str = RUN) -> dict:
    """M45 (P2) — DÉNORMALISE les vigilances (non-francs : SOFT_FLAG + abf/UNKNOWN) du run servi
    en une table (run_label, parcel_id, layer_name) INDEXÉE, pour que le filtre `flags` (vigilances
    par type) soit un PROBE indexé — le compteur île entière passait de 4-7 s à sous la barre.

    RUN-SCOPÉE : (re)bâtie dans le geste de bascule (comme les MVT), jamais à la main. GARDE DE
    COHÉRENCE : le compte par couche DOIT égaler la source (dryrun_cascade_results) — tout écart =
    REFUS bruyant (rollback + RuntimeError). Jamais une 2e vérité qui dérive en silence. Idempotent."""
    import time as _time
    t0 = _time.perf_counter()
    db.execute(text("DROP TABLE IF EXISTS parcel_flags"))
    db.execute(text("""
        CREATE TABLE parcel_flags AS
        SELECT DISTINCT CAST(:run AS varchar) AS run_label, parcel_id, layer_name
        FROM dryrun_cascade_results
        WHERE run_label = :run
          AND (result = 'SOFT_FLAG' OR (layer_name = 'abf' AND result = 'UNKNOWN'))
    """), {"run": run_label})
    db.execute(text("CREATE INDEX parcel_flags_probe ON parcel_flags (run_label, layer_name, parcel_id)"))
    db.execute(text("ANALYZE parcel_flags"))
    # ── GARDE DE COHÉRENCE : par couche, parcel_flags == source (DISTINCT parcelle) ──
    src = dict(db.execute(text(
        "SELECT layer_name, count(DISTINCT parcel_id) FROM dryrun_cascade_results "
        "WHERE run_label=:run AND (result='SOFT_FLAG' OR (layer_name='abf' AND result='UNKNOWN')) "
        "GROUP BY 1"), {"run": run_label}).all())
    got = dict(db.execute(text(
        "SELECT layer_name, count(*) FROM parcel_flags WHERE run_label=:run GROUP BY 1"),
        {"run": run_label}).all())
    ecarts = {k: (src.get(k), got.get(k)) for k in set(src) | set(got) if src.get(k) != got.get(k)}
    if ecarts:
        db.rollback()
        raise RuntimeError(f"parcel_flags INCOHÉRENT vs dryrun_cascade_results (couche: source/flags) : {ecarts}")
    n = db.execute(text("SELECT count(*) FROM parcel_flags")).scalar() or 0
    db.commit()
    return {"n": int(n), "couches": len(got), "coherence_ok": True,
            "seconds": round(_time.perf_counter() - t0, 2)}


def rebuild_mvt_servies(db: Session, run_label: str = RUN, log=lambda *_: None) -> dict:
    """GESTE UNIQUE de matérialisation carte (M48) — « un geste = tout ou rien ». À appeler DANS
    chaque bascule du run servi (après le re-score) ET par `labuse build-mvt` : plus jamais un
    re-score sans tuiles à jour (constat M48 : la bascule M39 a régénéré le golden mais PAS les
    tuiles → 4 tiers + 7 854 SDP périmés sur la carte). Reconstruit d'un bloc `mvt_parcels` +
    overlays + `parcel_flags` (M45) + `parcel_renouvellement` (M47) + `score_e` (M50) et enregistre
    `mvt_meta`. Point d'orchestration UNIQUE — le CLI n'en est plus qu'un mince appelant."""
    import time as _t
    from .. import renouvellement as _renouv
    from ..ingestion import score_e as _score_e
    from ..bascule_gardes import (check_coherence_renouvellement, check_peremption_tuiles,
                                  check_coherence_tables_run_scopees, check_sources_declarees,
                                  check_unicite_pm)
    t0 = _t.perf_counter()
    n = build_mvt_table(db, run_label)
    n_ov = build_overlay_mvt(db)
    pf = build_parcel_flags_table(db, run_label)
    log(f"✓ parcel_flags : {pf['n']} paires sur {pf['couches']} couches · cohérence OK · {pf['seconds']} s.")
    rr = _renouv.build(db, run_label=run_label, commit=False)
    cr = check_coherence_renouvellement(session=db)
    log(f"✓ parcel_renouvellement : {rr['n']} parcelles (run {rr['run_label']}) · cohérence {cr['statut']}.")
    # M50 : score_e (bilan CA, run-scopé) rejoint le geste — plus la seule table servie montée par
    # une commande isolée `labuse score-e` (dette M47 : score_e avait servi 428 marges d'un run mort).
    se = _score_e.build_score_e(db, run=run_label, commit=False)
    log(f"✓ score_e : {se['total']} parcelles ({se['estimables']} estimables), run {run_label}.")
    db.execute(text("""CREATE TABLE IF NOT EXISTS mvt_meta
                       (key varchar(48) PRIMARY KEY, value varchar(64), updated_at timestamptz)"""))
    db.execute(text("""INSERT INTO mvt_meta (key, value, updated_at) VALUES ('run_label', :l, now())
                       ON CONFLICT (key) DO UPDATE SET value = :l, updated_at = now()"""), {"l": run_label})
    log(f"✓ mvt_parcels : {n} parcelles · overlays {n_ov} · {round(_t.perf_counter() - t0, 1)} s "
        f"(run {run_label}).")
    # M48 : garde de péremption DANS le point unique → CLI `build-mvt` ET bascules la voient (post-build
    # elle confirme la fraîcheur ; entre deux builds elle crie si un re-score hors geste a eu lieu).
    per = check_peremption_tuiles(session=db)
    # M50 : garde de cohérence de TOUTES les tables servies run-scopées (le point unique les voit
    # toutes) — assertion « plus aucune table servie ne peut être silencieusement périmée ».
    coh = check_coherence_tables_run_scopees(session=db)
    # M-H : garde de traçabilité source ↔ couche (aucune couche spatial_layers sans data_source_id) —
    # dans la MÊME séquence que les autres gardes (bruyante, non bloquante).
    srcs = check_sources_declarees(session=db)
    # M-A : garde d'unicité du lien PM ↔ parcelle (sinon le build V sert un propriétaire arbitraire
    # pour un idu multi-lié) — même séquence, bruyante, non bloquante.
    upm = check_unicite_pm(session=db)
    return {"n": n, "overlays": n_ov, "parcel_flags": pf["n"], "renouvellement": rr["n"],
            "score_e": se["total"], "renouv_coherence": cr["statut"], "peremption_ok": per["ok"],
            "tables_coherence": coh, "sources_declarees": srcs, "unicite_pm": upm,
            "run_label": run_label}


# cache LRU en mémoire (les tuiles sont chères à générer et très re-demandées en navigation)
_CACHE: OrderedDict[tuple, bytes] = OrderedDict()
_CACHE_MAX = 4096
# M6.2 perf : cache navigateur des tuiles (le contenu ne change qu'au build-mvt). Appliqué
# AUSSI au chemin servi depuis le cache LRU serveur — il l'omettait, donc le navigateur
# re-téléchargeait les tuiles CHAUDES à chaque navigation.
# B1.3 : 1 h de fraîcheur + 24 h de grâce (stale-while-revalidate) — les tuiles ne changent
# qu'au build-mvt (post-run) ; le navigateur repeint instantanément et revalide en fond.
_TILE_HEADERS = {"Cache-Control": "public, max-age=3600, stale-while-revalidate=86400"}


def _mvt_has_zone(db: Session) -> bool:
    """La table mvt_parcels SERVIE porte-t-elle zone_lib/zone_fam (build post-M6.1) ?"""
    return bool(db.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'mvt_parcels' AND column_name = 'zone_fam'")).scalar())


@router.get("/map/tiles/meta")
def mvt_tiles_meta(db: Session = Depends(get_db)) -> dict:
    """Capacités des tuiles servies — le front grise la couche « Zonage PLU (parcelles) »
    en mode île tant que mvt_parcels n'embarque pas zone_fam (prochain build-mvt)."""
    run = None
    if db.execute(text("SELECT to_regclass('mvt_meta')")).scalar():
        run = db.execute(text("SELECT value FROM mvt_meta WHERE key = 'run_label'")).scalar()
    return {"run_label": run,
            "zonage_parcelle": _mvt_has_zone(db)
            if db.execute(text("SELECT to_regclass('mvt_parcels')")).scalar() else False}


@router.get("/map/tiles/{z}/{x}/{y}.pbf")
def mvt_tile(z: int, x: int, y: int, db: Session = Depends(get_db)) -> Response:
    """Tuile MVT couche `parcels` — mêmes propriétés que le GeoJSON commune."""
    if z < 9 or z > 22:
        return Response(status_code=204)
    key = (z, x, y)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return Response(content=_CACHE[key], media_type="application/x-protobuf", headers=_TILE_HEADERS)
    exists = db.execute(text("SELECT to_regclass('mvt_parcels')")).scalar()
    if not exists:
        return Response(status_code=204)  # table pas encore construite (run en cours)
    # table d'avant le correctif M5 (sans tier_v2) : repli legacy jusqu'au `labuse build-mvt`
    has_v2 = db.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'mvt_parcels' AND column_name = 'tier_v2'")).scalar()
    # M6.1 : table d'avant l'item 1 (sans zone_lib/zone_fam) : repli — les tuiles embarqueront
    # le zonage au prochain `labuse build-mvt` (bascule q_v5), RIEN ne casse d'ici là.
    has_zone = _mvt_has_zone(db)
    # R1 (revue Vic n°2 : le cadastre d'abord) — TOUTES les parcelles dès z9, simplification
    # par palier pour tenir les poids. BLOC B (B1.3) : paliers recalibrés sur mesure réelle
    # (tuile centrale z9 = 5,6 Mo avec 10 m/4096) — à z9 1 px ≈ 285 m, la tolérance suit le
    # pixel et l'extent descend à 1024 (4 unités/px : les parcelles sub-pixel se quantifient,
    # l'aspect de la trame est inchangé — vérifié capture avant/après). Mesures : z9 5,57 Mo
    # → 0,61 Mo · z10 5,68 → 1,33 · z11 2,73 → 1,59. z12+ inchangé (brut, extent 4096).
    simplify = {9: 60, 10: 30, 11: 15}.get(z, 0)
    extent = 1024 if z <= 11 else 4096
    buffer = max(extent // 64, 8)
    geom_expr = (f"ST_SimplifyPreserveTopology(m.geom_3857, {simplify})" if simplify
                 else "m.geom_3857")
    # z ≤ 11 : tuiles MAIGRES (status + commune seulement — 24 et 4 valeurs distinctes,
    # dédupliquées par l'encodage MVT). Les 13 propriétés complètes (idu unique en tête)
    # pesaient 15 Mo/tuile à z9 ; le clic passe par /parcels/at, le ping vole à z16.
    # tier_v2/etage0 dans les tuiles maigres aussi : c'est la couleur (verdict effectif)
    v2_props = "m.tier_v2, m.etage0, " if has_v2 else ""
    v2_props_full = "m.tier_v2, m.rang_v2, m.mult_v2, m.etage0, " if has_v2 else ""
    # zone_fam dans les tuiles maigres aussi (5 valeurs distinctes, dédupliquées par le MVT) :
    # c'est la COULEUR de la couche « Zonage PLU (parcelles) », visible dès z9 en mode île.
    zone_props = "m.zone_fam, " if has_zone else ""
    zone_props_full = "m.zone_lib, m.zone_fam, " if has_zone else ""
    # M48 (F4) : `m.status` (matrice morte) retiré des propriétés servies — la carte lit tier_v2/etage0.
    props = (f"{v2_props}{zone_props}m.commune" if z <= 11 else
             "m.idu, m.commune, m.surface_m2, "  # M129-B : q/a retirés · M137-D : a_completude aussi (vestige matrice, absent de mvt_parcels)
             f"{v2_props_full}{zone_props_full}"
             "m.completeness_score, m.sdp_residuelle_m2, "
             "m.sous_densite, m.evenement, m.flags")
    data = db.execute(text(f"""
        WITH b AS (SELECT ST_TileEnvelope(:z, :x, :y) AS env),
        mvt AS (
SELECT ST_AsMVTGeom({geom_expr}, b.env, {extent}, {buffer}, true) AS geom,
                 {props}
          FROM mvt_parcels m, b
          WHERE m.geom_3857 && b.env
        )
        SELECT ST_AsMVT(mvt.*, 'parcels', {extent}, 'geom') FROM mvt
    """), {"z": z, "x": x, "y": y}).scalar()
    body = bytes(data) if data else b""
    _CACHE[key] = body
    if len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    return Response(content=body, media_type="application/x-protobuf", headers=_TILE_HEADERS)


# ═══════════ OVERLAYS MVT (R6, revue Vic n°2) — zonage PLU + PPR île entière ═══════════
# 6 306 zones (29 Mo) + 164 PPR (88 Mo, mégapolygones 320k pts) : le GeoJSON île ne tient
# pas → même mécanique matérialisée que mvt_parcels. Reconstruit par `labuse build-mvt`.

OVERLAY_KINDS = ("plu_gpu_zone", "ppr")


def build_overlay_mvt(db: Session) -> int:
    db.execute(text("DROP TABLE IF EXISTS mvt_overlays"))
    db.execute(text("""
        CREATE TABLE mvt_overlays AS
        SELECT id, kind, subtype, name, commune, ST_Transform(geom, 3857) AS geom_3857
        FROM spatial_layers WHERE kind IN ('plu_gpu_zone', 'ppr')"""))
    db.execute(text("CREATE INDEX mvt_overlays_gix ON mvt_overlays USING GIST (geom_3857)"))
    db.execute(text("CREATE INDEX mvt_overlays_kind ON mvt_overlays (kind)"))
    db.execute(text("ANALYZE mvt_overlays"))
    n = db.execute(text("SELECT count(*) FROM mvt_overlays")).scalar() or 0
    db.commit()
    _CACHE.clear()
    return int(n)


@router.get("/map/tiles/ov/{kind}/{z}/{x}/{y}.pbf")
def mvt_overlay_tile(kind: str, z: int, x: int, y: int, db: Session = Depends(get_db)) -> Response:
    """Tuile MVT d'une couche overlay (couche = `kind`) — mode île."""
    if kind not in OVERLAY_KINDS or z < 8 or z > 22:
        return Response(status_code=204)
    key = ("ov", kind, z, x, y)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return Response(content=_CACHE[key], media_type="application/x-protobuf", headers=_TILE_HEADERS)
    if not db.execute(text("SELECT to_regclass('mvt_overlays')")).scalar():
        return Response(status_code=204)
    data = db.execute(text("""
        WITH b AS (SELECT ST_TileEnvelope(:z, :x, :y) AS env),
        mvt AS (
          SELECT ST_AsMVTGeom(m.geom_3857, b.env, 4096, 64, true) AS geom,
                 m.subtype, m.name, m.commune
          FROM mvt_overlays m, b
          WHERE m.kind = :k AND m.geom_3857 && b.env)
        SELECT ST_AsMVT(mvt.*, :k, 4096, 'geom') FROM mvt"""),
        {"z": z, "x": x, "y": y, "k": kind}).scalar()
    body = bytes(data) if data else b""
    _CACHE[key] = body
    if len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    return Response(content=body, media_type="application/x-protobuf", headers=_TILE_HEADERS)
