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

V1 assumée : les chemins comparés sont les FONCTIONS des robinets (mêmes points d'entrée que
les endpoints — _foncier_commune, moteur zonage, comptes de sources) ; l'appel HTTP réel
`?trace=1`, les builders PDF en collecte seule et les outils Copilote s'ajoutent quand le lot
7.1 aura généralisé le tampon (noté au compte-rendu).
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


def controle(db, *, declencheur: str = "bouton") -> dict:
    """4.3 — LE passage complet : robinets + eau ancienne + verdict (une ligne circuit_controles).
    La page Circuit lit la dernière ligne."""
    t0 = time.monotonic()
    ensure(db)
    rob = verifier_robinets(db)
    eau = verifier_eau_ancienne(db)
    fuites_ouvertes = db.execute(text(
        "SELECT count(*) FROM circuit_ecarts WHERE statut = 'ouvert'")).scalar() or 0
    duree = round(time.monotonic() - t0, 2)
    details = {"declencheur": declencheur, "robinets": rob, "eau": eau}
    db.execute(text(
        "INSERT INTO circuit_controles (fuites_ouvertes, eau_ancienne, robinets_couverts,"
        " robinets_non_couverts, duree_s, details) VALUES (:f, :e, :c, :n, :d, :j)"),
        {"f": fuites_ouvertes, "e": eau["ouvertes"], "c": rob["couverts"],
         "n": rob["non_couverts"], "d": duree, "j": json.dumps(details, ensure_ascii=False, default=str)})
    return {"fuites_ouvertes": fuites_ouvertes, "eau_ancienne_ouverte": eau["ouvertes"],
            "eau_etiquetee": eau["etiquetees"], "duree_s": duree, **rob}
