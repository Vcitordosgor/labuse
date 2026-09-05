"""CIRCUIT-1 lot 4 — LA SONDE DE COHÉRENCE « Vérifier que tout coule ».

  · 4.1 `verifier_robinets` : pour chaque chiffre servi par ≥ 2 robinets, compare les chemins
    réels sur les TÉMOINS (24 communes — méthode héritée de scripts/inventaire/mesure_fuites.py).
    Écarts → `circuit_ecarts` (dédupliqués par (chiffre, clé, robinets) ; un écart disparu
    passe `statut='solde'` et GARDE sa ligne — 4.4, l'historique que Vic veut voir).
  · 4.2 `verifier_eau_ancienne` : par TAMPON — run ≠ manifeste, millésime servi plus vieux que
    le réservoir. Les six familles de CIRCUIT-0 sont le jeu de contrôle ; après les lots 2-3 il
    doit en rester zéro hors « solaire gelé, étiqueté ».
  · 4.3 `controle` : une ligne de verdict par passage (`circuit_controles`) — la page lit la
    dernière. Lancé par le job wrapper `coherence-robinets`, APRÈS chaque bascule, et au bouton.

0-bis (CIRCUIT-2) — la V1 « fonctions seulement » est DÉPASSÉE : `verifier_chemins_reels`
appelle l'endpoint HTTP de la fiche (TestClient in-process) et l'outil Copilote sur les
témoins EXPORTS-1 (TEMOINS_PARCELLES) ; la famille PDF est portée par le cas
`verifier_exports` (scripts/recette_exports1.py — 24 PDF des 4 témoins, nocturne seulement) ;
`verifier_scission_neuf` verrouille l'arbitrage Q3 (scoring = VEFA à l'acte, bilan = observé) ;
le contrôle « mots interdits » (config/mots_interdits.yaml, versionnée) est un verdict DISTINCT.
"""
from __future__ import annotations

import json
import logging
import time

from sqlalchemy import text

log = logging.getLogger("labuse.sonde_circuit")

DDL = """
CREATE TABLE IF NOT EXISTS circuit_ecarts (
  id bigserial PRIMARY KEY,
  chiffre_id varchar(80) NOT NULL,
  cle text NOT NULL,
  robinet_a varchar(120) NOT NULL,
  valeur_a text,
  robinet_b varchar(120) NOT NULL,
  valeur_b text,
  cause varchar(24),            -- denominateur · perimetre · run · table · millesime · fenetre_temporelle · arrondi · autre
  depuis timestamptz NOT NULL DEFAULT now(),
  statut varchar(12) NOT NULL DEFAULT 'ouvert',   -- ouvert | solde
  solde_le timestamptz,
  commit_solde varchar(64),
  UNIQUE (chiffre_id, cle, robinet_a, robinet_b)
);
CREATE TABLE IF NOT EXISTS circuit_eau_ancienne (
  id bigserial PRIMARY KEY,
  ts timestamptz NOT NULL DEFAULT now(),
  chiffre_id varchar(120) NOT NULL,
  robinet varchar(120) NOT NULL,
  tampon text,
  attendu text,
  mecanisme text,
  statut varchar(12) NOT NULL DEFAULT 'ouvert'    -- ouvert | etiquete (assumé) | solde
);
CREATE TABLE IF NOT EXISTS circuit_controles (
  id bigserial PRIMARY KEY,
  ts timestamptz NOT NULL DEFAULT now(),
  fuites_ouvertes int NOT NULL,
  eau_ancienne int NOT NULL,
  robinets_couverts int NOT NULL,
  robinets_non_couverts int NOT NULL,
  duree_s numeric,
  details jsonb
)
"""


def ensure(db) -> None:
    for stmt in DDL.split(";"):
        if stmt.strip():
            db.execute(text(stmt))


def _upsert_ecart(db, chiffre_id: str, cle: str, ra: str, va, rb: str, vb, cause: str) -> None:
    db.execute(text(
        "INSERT INTO circuit_ecarts (chiffre_id, cle, robinet_a, valeur_a, robinet_b, valeur_b, cause) "
        "VALUES (:c, :k, :ra, :va, :rb, :vb, :ca) "
        "ON CONFLICT (chiffre_id, cle, robinet_a, robinet_b) DO UPDATE SET "
        " valeur_a = EXCLUDED.valeur_a, valeur_b = EXCLUDED.valeur_b, cause = EXCLUDED.cause, "
        " statut = 'ouvert', solde_le = NULL"),
        {"c": chiffre_id, "k": cle, "ra": ra, "va": str(va), "rb": rb, "vb": str(vb), "ca": cause})


def verifier_robinets(db) -> dict:
    """4.1 — les chiffres à ≥ 2 robinets, mesurés par leurs chemins réels sur les témoins.
    Rend {ecarts_trouves, mesures, couverts, non_couverts}."""
    from .registre import CHIFFRES, ROBINETS
    from .registre.moteurs.zonage import parts_zonage_surface

    mesures = 0
    trouves: list[tuple] = []
    verifies: set[tuple[str, str, str, str]] = set()

    # ── témoin 1 : les parts de zonage (LA fuite de CIRCUIT-0) sur les 24 communes ──
    communes = [c for (c,) in db.execute(text(
        "SELECT DISTINCT commune FROM parcels ORDER BY commune")).all()]
    for com in communes:
        parts = parts_zonage_surface(db, com)
        if not parts:
            continue
        # la fiche commune sert le MÊME objet (rebranchée lot 2.1) : re-mesure par le chemin fiche
        from .api.app import _foncier_commune
        try:
            fiche = _foncier_commune(db, com).get("repartition_zonage")
        except Exception:  # noqa: BLE001 — commune sans données de run : la sonde continue
            db.rollback()
            continue
        mesures += 1
        for fam in ("U", "AU", "A", "N"):
            cle = (f"part_zone_{fam}_pct", com, "moteur:zonage", "fiche_commune_zonage")
            verifies.add(cle)
            va = parts["familles"][fam]["pct"]
            vb = (fiche or {}).get("familles", {}).get(fam, {}).get("pct")
            if vb is not None and abs(float(va) - float(vb)) > 0.05:
                trouves.append((f"part_zone_{fam}_pct", com, "moteur:zonage", va,
                                "fiche_commune_zonage", vb, "denominateur"))

    # ── témoin 2 : le compte de sources (3 écrans, unifiés au lot 0.2) ──
    try:
        from . import etats_sources, flux
        n_flux = flux.construire_flux(db)["comptes"]["total"]
        n_arbitre = len(etats_sources.lister_etats(db))
        mesures += 1
        verifies.add(("n_sources", "global", "admin_flux_circuit", "page_sources_client"))
        if n_flux != n_arbitre:
            trouves.append(("n_sources", "global", "admin_flux_circuit", n_flux,
                            "page_sources_client", n_arbitre, "perimetre"))
    except Exception:  # noqa: BLE001
        db.rollback()

    for t in trouves:
        _upsert_ecart(db, *t)
    # 4.4 — solder les écarts re-mesurés ce passage et absents des trouvés
    cles_trouves = {(t[0], t[1], t[2], t[4]) for t in trouves}
    solde = 0
    for v in verifies - cles_trouves:
        n = db.execute(text(
            "UPDATE circuit_ecarts SET statut = 'solde', solde_le = now() "
            "WHERE chiffre_id = :c AND cle = :k AND robinet_a = :ra AND robinet_b = :rb "
            "AND statut = 'ouvert'"),
            {"c": v[0], "k": v[1], "ra": v[2], "rb": v[3]}).rowcount
        solde += n

    multi = {cid for cid, c in CHIFFRES.items()
             if sum(1 for r in ROBINETS.values() if cid in r.chiffres) >= 2}
    couverts = {"part_zone_U_pct", "part_zone_AU_pct", "part_zone_A_pct", "part_zone_N_pct", "n_sources"}
    return {"ecarts_trouves": len(trouves), "mesures": mesures, "soldes": solde,
            "chiffres_multi_robinets": len(multi),
            "couverts": len(couverts & multi) + len(couverts - multi),
            "non_couverts": len(multi - couverts)}


#: 0-bis — les quatre témoins d'EXPORTS-1 ENTRENT dans les parcelles golden de la sonde (mandat
#: CIRCUIT-2, lot 0-bis point 5). Même jeu que scripts/recette_exports1.py (jamais deux listes).
TEMOINS_PARCELLES: tuple[str, ...] = (
    "97415000BO0852", "97401000AD0554", "97416000DY0106", "97411000AV0110")


def _parcel_id(db, idu: str) -> int | None:
    return db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()


def verifier_chemins_reels(db) -> dict:
    """0-bis (dû du 4.1) — la sonde appelle les VRAIS chemins, plus seulement les fonctions :
    endpoint HTTP de la fiche (TestClient in-process), outil Copilote, et la famille PDF (portée
    par le cas recette_exports1, nocturne — jamais « non_couverts » pour ces trois familles).
    Compare sur les témoins EXPORTS-1 : surface (HTTP vs SQL), SDP au sol (HTTP vs moteur
    potentiel), Copilote fiche_parcelle (surface outil vs HTTP), et « Neuf VEFA » ABSENT de la
    fiche (scission 0-bis / arbitrage Q3)."""
    trouves: list[tuple] = []
    mesures = 0
    familles = {"http": 0, "copilote": 0, "pdf": "cas recette_exports1 (nocturne)"}
    try:
        from fastapi.testclient import TestClient

        from .api.app import app
        client = TestClient(app)
    except Exception as exc:  # noqa: BLE001 — app inimportable : la sonde le DIT, jamais muette
        return {"ecarts_trouves": 0, "mesures": 0, "familles": familles,
                "erreur": f"TestClient indisponible : {exc}"}
    for idu in TEMOINS_PARCELLES:
        pid = _parcel_id(db, idu)
        if pid is None:
            continue
        try:
            fiche = client.get(f"/parcels/{idu}").json()
        except Exception:  # noqa: BLE001
            db.rollback()
            continue
        mesures += 1
        familles["http"] += 1
        # surface : HTTP = SQL (passe-plat honnête)
        surf_sql = db.execute(text("SELECT surface_m2 FROM parcels WHERE idu = :i"),
                              {"i": idu}).scalar()
        surf_http = fiche.get("surface_m2")
        if surf_sql is not None and surf_http is not None and \
                abs(float(surf_sql) - float(surf_http)) > 0.5:
            trouves.append(("surface_parcelle_m2", idu, "http:/parcels", surf_http,
                            "sql:parcels.surface_m2", surf_sql, "table"))
        # SDP au sol : HTTP (potentiel_transformation) = moteur potentiel (EXPORTS-1 lot 3)
        try:
            from .faisabilite.potentiel import bloc_potentiel
            bloc = bloc_potentiel(db, pid)
            sdp_moteur = (bloc or {}).get("au_sol", {}).get("sdp_residuelle_m2")
            sdp_http = ((fiche.get("potentiel_transformation") or {})
                        .get("au_sol") or {}).get("sdp_residuelle_m2")
            if sdp_moteur is not None and sdp_http is not None and \
                    abs(float(sdp_moteur) - float(sdp_http)) > 0.5:
                trouves.append(("sdp_residuelle_m2", idu, "http:/parcels", sdp_http,
                                "moteur:potentiel", sdp_moteur, "run"))
        except Exception:  # noqa: BLE001
            db.rollback()
        # scission du neuf (robinet) : le VEFA à l'acte ne se sert plus sous la fiche (Q3)
        if "Neuf VEFA" in json.dumps(fiche, ensure_ascii=False, default=str):
            trouves.append(("prix_neuf_observe_eur_m2", idu, "http:/parcels",
                            "« Neuf VEFA » servi", "scission 0-bis", "id acte réservé au scoring",
                            "perimetre"))
        # outil Copilote : fiche_parcelle (surface outil = surface HTTP)
        try:
            from .copilote_v2 import outils
            res = outils.fiche_parcelle(db, idu=idu)
            familles["copilote"] += 1
            if res.valeur is not None and surf_http is not None and \
                    abs(float(res.valeur) - float(surf_http)) > 0.5:
                trouves.append(("surface_parcelle_m2", idu, "copilote:fiche_parcelle",
                                res.valeur, "http:/parcels", surf_http, "table"))
        except Exception:  # noqa: BLE001
            db.rollback()
    for t in trouves:
        _upsert_ecart(db, *t)
    return {"ecarts_trouves": len(trouves), "mesures": mesures, "familles": familles}


def verifier_scission_neuf(db) -> dict:
    """0-bis point 3 — la sonde vérifie que le SCORING lit le VEFA à l'acte
    (prix_neuf_vefa_acte_eur_m2) et le BILAN le neuf observé (prix_neuf_observe_eur_m2).
    Mesuré sur les témoins : (a) la chaîne bilan résout par resolve_prix_neuf_marche ;
    (b) score_e servi ne porte plus le grain « secteur » (il n'existait que dans le précalcul
    divergent — CIRCUIT-1 2.2) ; jamais l'un sous le libellé de l'autre."""
    trouves: list[tuple] = []
    mesures = 0
    for idu in TEMOINS_PARCELLES:
        pid = _parcel_id(db, idu)
        if pid is None:
            continue
        try:
            from .faisabilite.bilan import resolve_prix_sortie_servi
            from .ingestion.dvf_prix_neuf import resolve_prix_neuf_marche
            servi = resolve_prix_sortie_servi(db, pid)
            brut = resolve_prix_neuf_marche(db, pid)
            mesures += 1
            p_servi = servi.get("prix")
            p_brut = (brut or {}).get("prix") if isinstance(brut, dict) else None
            # le bilan peut ajuster par bilan_params (override secteur) — mais s'il diverge du
            # moteur observé SANS niveau d'override déclaré, c'est une fuite.
            if p_servi is not None and p_brut is not None and \
                    abs(float(p_servi) - float(p_brut)) > 0.5 and \
                    servi.get("niveau") not in ("override_bassin",):
                trouves.append(("prix_neuf_observe_eur_m2", idu,
                                "bilan:resolve_prix_sortie_servi", p_servi,
                                "moteur:resolve_prix_neuf_marche", p_brut, "autre"))
        except Exception:  # noqa: BLE001
            db.rollback()
    # (b) scoring : score_e servi sans grain « secteur » (précalcul divergent mort)
    try:
        if db.execute(text("SELECT to_regclass('score_e')")).scalar():
            n_secteur = db.execute(text(
                "SELECT count(*) FROM score_e WHERE niveau_prix = 'secteur'")).scalar() or 0
            mesures += 1
            if n_secteur:
                trouves.append(("prix_neuf_vefa_acte_eur_m2", "global",
                                "score_e (niveau_prix)", f"{n_secteur} lignes 'secteur'",
                                "moteur:neuf_vefa_commune (live)",
                                "grain secteur = précalcul divergent mort", "table"))
    except Exception:  # noqa: BLE001
        db.rollback()
    for t in trouves:
        _upsert_ecart(db, *t)
    return {"ecarts_trouves": len(trouves), "mesures": mesures}


def verifier_exports(db) -> dict:
    """0-bis point 5 — scripts/recette_exports1.py devient UN CAS DE LA SONDE : génération des
    24 PDF des 4 témoins par les vraies routes, extraction, comparaison à fiche.json — joué au
    passage NOCTURNE (declencheur cron), jamais au bouton (lourd : WeasyPrint + pdftotext).
    Le contrôle « mots interdits » (liste versionnée config/mots_interdits.yaml) est un verdict
    DISTINCT des divergences de grandeurs."""
    import os
    import subprocess
    import sys as _sys
    import tempfile
    from pathlib import Path
    script = Path(__file__).resolve().parents[2] / "scripts" / "recette_exports1.py"
    if not script.exists():
        return {"erreur": f"script absent : {script}"}
    with tempfile.TemporaryDirectory(prefix="sonde-exports-") as tmp:
        jpath = Path(tmp) / "verdict.json"
        env = dict(os.environ)
        env.setdefault("DYLD_FALLBACK_LIBRARY_PATH", "/opt/homebrew/lib")
        env["PYTHONPATH"] = str(script.parents[1] / "src")
        try:
            proc = subprocess.run(
                [_sys.executable, str(script), "--dir", tmp, "--json", str(jpath)],
                capture_output=True, text=True, timeout=1800, env=env)
        except Exception as exc:  # noqa: BLE001 — échec technique DIT, jamais déguisé en absence
            return {"erreur": f"recette injouable : {exc}"}
        if not jpath.exists():
            return {"erreur": f"recette sans verdict (rc={proc.returncode}) : "
                              f"{(proc.stderr or proc.stdout or '')[-400:]}"}
        verdict = json.loads(jpath.read_text())
    for e in verdict.get("erreurs", []):
        if "mot interdit" in e:
            continue           # contrôle distinct ci-dessous
        _upsert_ecart(db, "exports_recette", e[:200], "pdf:recette_exports1", "divergence",
                      "fiche.json / endpoint fiche", "référence écran", "autre")
    for m in verdict.get("mots_interdits", []):
        _upsert_ecart(db, "mots_interdits", m[:200], "pdf:recette_exports1", "présent",
                      "config/mots_interdits.yaml", "0 attendu", "autre")
    return {"n_erreurs_hors_mots": verdict.get("n_erreurs_hors_mots", 0),
            "n_mots_interdits": verdict.get("n_mots_interdits", 0)}


def verifier_eau_ancienne(db) -> dict:
    """4.2 — par tampon : run ≠ manifeste, millésime servi < réservoir. Les six familles de
    CIRCUIT-0 sont contrôlées ; « solaire gelé » sort `etiquete` (assumé), jamais `ouvert`."""
    from . import manifeste

    lignes: list[tuple[str, str, str, str, str, str]] = []
    # 1) division : des lignes hors du run du manifeste encore présentes ? (servies : plus jamais — lot 2.3)
    run_div = manifeste.division_run()
    autres = db.execute(text(
        "SELECT DISTINCT run_label FROM division_or_candidates WHERE run_label <> :r"),
        {"r": run_div}).scalars().all() if db.execute(text(
            "SELECT to_regclass('division_or_candidates')")).scalar() else []
    if autres:
        lignes.append(("divisible_classe", "fiche_parcelle_division",
                       f"runs en base : {sorted(autres)}", f"run servi : {run_div}",
                       "lignes d'anciens runs en base (non servies — scope lot 2.3) ; purge au geste",
                       "etiquete"))
    # 2) DPE : l'amont vu par la sonde est-il plus récent que la donnée en base ?
    try:
        vu = db.execute(text(
            "SELECT v.dernier_vu FROM source_veille v JOIN data_sources d ON d.id = v.source_id "
            "WHERE d.name ILIKE 'DPE ADEME%'")).scalar()
        maxi = db.execute(text("SELECT max(date_etablissement)::text FROM dpe_records")).scalar()
        if vu and maxi and str(vu)[:10] > str(maxi)[:10]:
            lignes.append(("(chiffres DPE)", "fiche parcelle / filtres",
                           f"max(date_etablissement)={maxi}", f"amont vu {str(vu)[:10]}",
                           "cron DPE : saut des communes peuplées (--force pour rafraîchir)", "ouvert"))
    except Exception:  # noqa: BLE001
        db.rollback()
    # 3) isochrones : entrées au-delà du TTL 30 j (plus jamais SERVIES — lot 2.7 — mais à purger)
    try:
        n_vieilles = db.execute(text(
            "SELECT count(*) FROM zone_isochrone_cache "
            "WHERE created_at <= now() - interval '30 days'")).scalar() or 0
        if n_vieilles:
            lignes.append(("population_zone", "outil_etude_zone",
                           f"{n_vieilles} entrées de cache > 30 j", "TTL 30 j (lot 2.7)",
                           "entrées ignorées à la lecture ; purge à la prochaine bascule", "etiquete"))
    except Exception:  # noqa: BLE001
        db.rollback()
    # 4) solaire : gel assumé, étiqueté (jamais « ouvert »)
    lignes.append(("prod_spec_kwh_kwc", "outil_prospection_solaire",
                   "millésime gelé porté en base (bandeau)", "recalcul au geste solaire-build",
                   "gel ASSUMÉ et étiqueté (CIRCUIT-0, famille 3)", "etiquete"))

    for (cid, rob, tampon, attendu, meca, statut) in lignes:
        db.execute(text(
            "INSERT INTO circuit_eau_ancienne (chiffre_id, robinet, tampon, attendu, mecanisme, statut) "
            "VALUES (:c, :r, :t, :a, :m, :s)"),
            {"c": cid, "r": rob, "t": tampon, "a": attendu, "m": meca, "s": statut})
    ouvertes = sum(1 for x in lignes if x[5] == "ouvert")
    return {"lignes": len(lignes), "ouvertes": ouvertes,
            "etiquetees": sum(1 for x in lignes if x[5] == "etiquete")}


def controle(db, *, declencheur: str = "bouton", exports: bool | None = None) -> dict:
    """4.3 — LE passage complet : robinets + eau ancienne + chemins réels (0-bis) + scission du
    neuf (0-bis) + verdict (une ligne circuit_controles). La page Circuit lit la dernière ligne.
    `exports` (0-bis) : le cas recette_exports1 (24 PDF des 4 témoins + mots interdits) est joué
    au passage NOCTURNE seulement (déclencheur cron), jamais au bouton — sauf override explicite."""
    t0 = time.monotonic()
    ensure(db)
    rob = verifier_robinets(db)
    chemins = verifier_chemins_reels(db)
    neuf = verifier_scission_neuf(db)
    eau = verifier_eau_ancienne(db)
    jouer_exports = (declencheur == "cron") if exports is None else exports
    exp = verifier_exports(db) if jouer_exports else {"saute": "hors passage nocturne"}
    fuites_ouvertes = db.execute(text(
        "SELECT count(*) FROM circuit_ecarts WHERE statut = 'ouvert'")).scalar() or 0
    duree = round(time.monotonic() - t0, 2)
    details = {"declencheur": declencheur, "robinets": rob, "eau": eau,
               "chemins_reels": chemins, "scission_neuf": neuf, "exports": exp}
    db.execute(text(
        "INSERT INTO circuit_controles (fuites_ouvertes, eau_ancienne, robinets_couverts,"
        " robinets_non_couverts, duree_s, details) VALUES (:f, :e, :c, :n, :d, :j)"),
        {"f": fuites_ouvertes, "e": eau["ouvertes"], "c": rob["couverts"],
         "n": rob["non_couverts"], "d": duree, "j": json.dumps(details, ensure_ascii=False, default=str)})
    return {"fuites_ouvertes": fuites_ouvertes, "eau_ancienne_ouverte": eau["ouvertes"],
            "eau_etiquetee": eau["etiquetees"], "duree_s": duree, **rob}
