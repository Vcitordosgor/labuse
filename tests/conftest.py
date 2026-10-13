"""Fixtures de test — ISOLÉES de la base applicative (M4).

Les tests tournent sur une base DÉDIÉE (`labuse_test` par défaut, ou
`LABUSE_TEST_DATABASE_URL`) : ils ne touchent JAMAIS la base de l'app. On bascule
TOUT le code (app + tests) vers cette base AVANT tout accès aux settings, de sorte
qu'aucun test ne puisse `TRUNCATE` la base applicative (cf. demo_saint_paul.reset_demo).

Si la base est injoignable, les tests `db` sont SKIPPÉS (pas en échec).
"""
from __future__ import annotations

import glob
import os
import sys

import pytest
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("LABUSE_CONFIG_DIR", "config")
# Fiche « promoteur » : pas d'appels externes (RGE ALTI / GPU) en test → déterministe.
os.environ.setdefault("LABUSE_ENRICH_LIVE", "0")

# M31 PC1 (famille B) : charger le .env AVANT de dériver l'URL de test (ligne ~90). conftest
# s'importe avant labuse.config (qui fait ce load_dotenv), donc sans ceci `LABUSE_DATABASE_URL`
# n'est pas en os.environ ici → repli sur le défaut codé (rôle `labuse` inexistant sur un poste
# à auth peer `openclaw`) → les tests qui ouvrent session_scope() directement ERRORent au lieu
# de skipper. override=False : un LABUSE_DATABASE_URL déjà exporté (CI) reste prioritaire.
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), override=False)
except Exception:  # pragma: no cover - python-dotenv absent : on garde le comportement d'avant
    pass


def _ensure_proj_data() -> None:
    """Garantit que pyproj trouve son répertoire de données PROJ (`proj.db`) AVANT tout
    import géo (Transformer 4326↔2975). Certains wheels pyproj (build source sur macOS 13,
    cf. README_DEV) n'embarquent AUCUN `proj.db` et `PROJ_DATA` n'est pas posé → 69 tests
    cassent au setup sur `pyproj.exceptions.DataDirError`.

    Ordre de recherche (documenté dans docs/TESTS.md) :
      1. `PROJ_DATA` déjà posé et valide → respecté tel quel.
      2. données déjà trouvables par pyproj (wheel avec data embarquée) → rien à faire.
      3. auto-découverte d'un `proj.db` (env conda, homebrew, préfixe courant).
      4. AUCUN trouvé → ÉCHEC BRUYANT et actionnable (jamais un skip silencieux de 69 tests :
         une machine mal configurée — y compris un VPS avec le même wheel — DOIT le savoir).
    """
    def _valid(d: str | None) -> bool:
        return bool(d) and os.path.isfile(os.path.join(d, "proj.db"))

    # 1. PROJ_DATA explicite et valide : la variable prime, on ne la contredit jamais.
    if _valid(os.environ.get("PROJ_DATA")):
        return

    import pyproj

    # 2. pyproj trouve déjà ses données (wheel avec proj.db embarqué) : rien à forcer.
    try:
        if _valid(pyproj.datadir.get_data_dir()):
            return
    except Exception:
        pass  # DataDirError → on passe à l'auto-découverte

    # 3. Auto-découverte, du plus spécifique (env courant) au plus générique.
    home = os.path.expanduser("~")
    candidates: list[str] = [
        os.path.join(sys.prefix, "share", "proj"),
        os.path.join(os.path.dirname(pyproj.__file__), "proj_dir", "share", "proj"),
        "/opt/homebrew/share/proj",
        "/usr/local/share/proj",
        "/usr/share/proj",
    ]
    for pat in ("miniforge3", "miniconda3", "anaconda3", "mambaforge"):
        candidates += sorted(glob.glob(os.path.join(home, pat, "envs", "*", "share", "proj")))
        candidates.append(os.path.join(home, pat, "share", "proj"))

    for d in candidates:
        if _valid(d):
            os.environ["PROJ_DATA"] = d
            pyproj.datadir.set_data_dir(d)
            return

    # 4. Rien trouvé : échec explicite et actionnable (pas de skip masqué).
    raise RuntimeError(
        "Données PROJ (proj.db) introuvables — pyproj ne peut pas reprojeter (4326↔2975).\n"
        "  Le wheel pyproj installé n'embarque pas proj.db et aucun proj.db système n'a été trouvé.\n"
        "  Emplacements cherchés :\n    - " + "\n    - ".join(candidates) + "\n"
        "  Corriger AU CHOIX :\n"
        "    • poser PROJ_DATA vers un dossier contenant proj.db (ex. l'env conda de PostGIS), ou\n"
        "    • réinstaller pyproj avec sa donnée embarquée :  pip install --force-reinstall --no-cache-dir pyproj\n"
        "  ⚠ Prod/VPS : si le serveur porte le même wheel sans proj.db, il aura le MÊME défaut — cf. docs/TESTS.md."
    )


_ensure_proj_data()

# Redirige l'app ET les tests vers une base de test dédiée, AVANT le 1er get_settings().
_APP_URL = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://labuse:labuse@localhost:5432/labuse")
_TEST_URL = os.environ.get("LABUSE_TEST_DATABASE_URL") or (_APP_URL.rsplit("/", 1)[0] + "/labuse_test")
os.environ["LABUSE_DATABASE_URL"] = _TEST_URL
# Base APPLICATIVE d'origine, exposée aux tests qui vérifient l'état SERVI (cohérence du
# run des tuiles) — setdefault : un premier chargement fait foi, les réimports n'écrasent pas.
os.environ.setdefault("LABUSE_APP_DATABASE_URL", _APP_URL)


@pytest.fixture(scope="session")
def engine():
    from sqlalchemy import create_engine, text

    from labuse import config, db, models

    config.get_settings.cache_clear()        # prend en compte la base de test
    db._engine = None                        # force la reconstruction de l'engine app
    db._Session = None

    # Crée la base de test si absente (connexion à la base de maintenance 'postgres').
    try:
        admin_url = _TEST_URL.rsplit("/", 1)[0] + "/postgres"
        dbname = _TEST_URL.rsplit("/", 1)[1]
        admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin.connect() as c:
            if not c.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": dbname}).scalar():
                c.execute(text(f'CREATE DATABASE "{dbname}"'))
        admin.dispose()
    except Exception as exc:  # pragma: no cover - dépend de l'environnement
        pytest.skip(f"Base de test indisponible ({_TEST_URL}) : {exc}")

    eng = db.make_engine()
    try:
        with eng.connect():
            pass
    except Exception as exc:  # pragma: no cover - dépend de l'environnement
        pytest.skip(f"PostGIS injoignable, tests db skippés : {exc}")
    db._engine = eng                         # l'app (session_scope) utilise la MÊME base de test
    db._Session = None
    from labuse.db import ensure_postgis
    ensure_postgis(eng)
    models.create_all(eng)
    # CI-1 (Lot 1) — REPRODUIT LA SÉQUENCE DE HEAL DU BOOT (`api/app.py::_lifespan`, tuple
    # `_heal_steps`) pour qu'une base de test FRAÎCHE porte le MÊME schéma qu'une app fraîchement
    # bootée. Sur un poste, `labuse_test` garde ces tables d'un run à l'autre, ce qui MASQUAIT le
    # trou ; une base vierge (la CI) le révèle (modules/ia/partners/protection/courrier/crm_columns/
    # veilles/copilote_v2/dashboard/promo/zone absents → UndefinedTable en cascade). Tout est
    # idempotent (IF NOT EXISTS). ORDRE identique au boot : comptes+scoping APRÈS les tables des
    # modules (scoping ajoute compte_id à celles-ci), et AVANT crm_columns (FK crm_columns.compte_id).
    from labuse.api.courrier import ensure_tables as _courrier_ens
    from labuse.api.crm_columns import ensure_tables as _crm_columns_ens
    from labuse.api.dashboard import ensure_tables as _dashboard_ens
    from labuse.api.events import ensure_tables as _events_ens
    from labuse.api.ia import ensure_tables as _ia_ens
    from labuse.api.modules import ensure_tables as _modules_ens
    from labuse.api.partners import ensure_tables as _partners_ens
    from labuse.api.projets import ensure_tables as _projets_ens
    from labuse.api.protection import ensure_tables as _protection_ens
    from labuse.api.tenant import ensure_scoping
    from labuse.comptes import ensure_tables as _comptes_ens
    from labuse.copilote_v2.historique import ensure_tables as _copv2_hist_ens
    from labuse.copilote_v2.telemetrie import ensure_tables as _copv2_tel_ens
    from labuse.copilote_v2.veilles import ensure_tables as _veilles_ens
    from labuse.db import session_scope as _ss
    from labuse.pige.tables import ensure_tables as _pige_ens
    from labuse.promo.tables import ensure_tables as _promo_ens
    _modules_ens(eng)
    _ia_ens(eng)
    _events_ens(eng)      # event_log / watched_parcels / saved_searches (créées avec compte_id)
    _partners_ens(eng)    # match_profiles / share_links / api_keys
    _projets_ens(eng)     # M120 — projets (+ migration fiche→cadrage)
    _protection_ens(eng)
    _courrier_ens(eng)
    with _ss() as _s:     # AUDIT PAIEMENT · SEC-IDOR — la TABLE comptes (requise par la FK de
        _comptes_ens(_s)  # crm_columns + l'ALTER comptes de dashboard). Le scoping vient PLUS BAS.
    _crm_columns_ens(eng)
    _veilles_ens(eng)
    _copv2_hist_ens(eng); _copv2_tel_ens(eng)
    _dashboard_ens(eng)
    _pige_ens(eng)        # RADAR (pige) · P0 — schéma isolé pige_*
    _promo_ens(eng)       # PROMO-1 P1 — table programmes
    with _ss() as _s:     # ÉTUDE DE ZONE Z1 — sirene_etablissements + mobpro_commune + cache isochrones
        from labuse.ingestion.mobpro import ensure_tables as _mo_ens
        from labuse.ingestion.sirene_etablissements import ensure_tables as _se_ens
        from labuse.zone import ensure_tables as _iso_ens
        _se_ens(_s); _mo_ens(_s); _iso_ens(_s)
    # CI-1 : ensure_scoping EN DERNIER (pas juste après comptes comme l'ORDRE du boot). Sa partie R9
    # purge les orphelins + pose la FK cascade sur ia_log/share_links/veilles/copilote_conversations…
    # — qui exigent que `compte_id` existe DÉJÀ sur ces tables. En prod, ces colonnes sont posées par
    # des migrations lazy (ex. share_links.compte_id par `_share_colonnes`, appelée à la 1re requête),
    # et scoping ne CONVERGE qu'après, sur plusieurs boots (chaque étape du heal est en try/except).
    # conftest tourne en UNE passe stricte, sans requête → on REPRODUIT l'état convergé : on pose
    # `compte_id` (idempotent) sur toutes les tables R9 existantes AVANT scoping, sinon un seul
    # `DELETE ... WHERE compte_id` sur une table sans la colonne fait rollback de TOUT le scoping.
    with eng.begin() as _c:
        for _t in ("copilote_conversations", "veilles", "veille_reprise", "ia_log", "usage_events",
                   "retours", "licence_mails", "notif_prefs", "notif_canaux", "share_links",
                   "lettre_zonage_refs"):
            if _c.execute(text("SELECT to_regclass(:t)"), {"t": _t}).scalar():
                _c.execute(text(f"ALTER TABLE {_t} ADD COLUMN IF NOT EXISTS compte_id integer"))
    with _ss() as _s:
        ensure_scoping(_s)   # migre compte_id + FK cascade — comme l'état CONVERGÉ du boot
    # CHASSE-FIX-1 (Lot 3) — la base de test sert `parcel_residuel` comme la PROD : une VUE
    # sur parcel_residuel_runs filtrée par le run servi (migration M135, idempotente). Avant,
    # la base de test gardait la TABLE historique vide → les tests ne voyaient jamais le
    # chemin réel (is_served) ; le test de bascule CHASSE-1 l'a prouvé.
    from labuse.faisabilite.residuel_runs import migrate_to_runs as _residuel_migrate
    _residuel_migrate(eng)
    # CHASSE-FIX-1 (Lot 3) — la VUE parcel_residuel est LECTURE SEULE en prod (personne n'y écrit).
    # En base de TEST, de nombreuses fixtures INSÈRENT/SUPPRIMENT dans parcel_residuel : on rend la
    # vue écrivable via des règles INSTEAD OF qui routent vers le run SERVI — échafaudage de test
    # uniquement, le comportement de lecture reste identique à la prod.
    with eng.begin() as _c:
        _c.execute(text("""
          CREATE OR REPLACE RULE _test_pr_ins AS ON INSERT TO parcel_residuel DO INSTEAD
          INSERT INTO parcel_residuel_runs
            (run_seq, parcel_id, taux_emprise_pct, pct_potentiel, sous_densite,
             sdp_residuelle_m2, capacite_estimee, cause, computed_at,
             assiette_source, hauteur_source, regles_non_modelisees)
          VALUES ((SELECT run_seq FROM residuel_runs WHERE is_served LIMIT 1),
             NEW.parcel_id, NEW.taux_emprise_pct, NEW.pct_potentiel, NEW.sous_densite,
             NEW.sdp_residuelle_m2, NEW.capacite_estimee, NEW.cause, COALESCE(NEW.computed_at, now()),
             NEW.assiette_source, NEW.hauteur_source, NEW.regles_non_modelisees)
          ON CONFLICT (run_seq, parcel_id) DO UPDATE SET
             taux_emprise_pct = EXCLUDED.taux_emprise_pct, pct_potentiel = EXCLUDED.pct_potentiel,
             sous_densite = EXCLUDED.sous_densite, sdp_residuelle_m2 = EXCLUDED.sdp_residuelle_m2,
             capacite_estimee = EXCLUDED.capacite_estimee, cause = EXCLUDED.cause"""))
        _c.execute(text("""
          CREATE OR REPLACE RULE _test_pr_del AS ON DELETE TO parcel_residuel DO INSTEAD
          DELETE FROM parcel_residuel_runs
          WHERE parcel_id = OLD.parcel_id
            AND run_seq = (SELECT run_seq FROM residuel_runs WHERE is_served LIMIT 1)"""))
        _c.execute(text("""
          CREATE OR REPLACE RULE _test_pr_upd AS ON UPDATE TO parcel_residuel DO INSTEAD
          UPDATE parcel_residuel_runs SET
             taux_emprise_pct = NEW.taux_emprise_pct, pct_potentiel = NEW.pct_potentiel,
             sous_densite = NEW.sous_densite, sdp_residuelle_m2 = NEW.sdp_residuelle_m2,
             capacite_estimee = NEW.capacite_estimee, cause = NEW.cause
          WHERE parcel_id = OLD.parcel_id
            AND run_seq = (SELECT run_seq FROM residuel_runs WHERE is_served LIMIT 1)"""))
    # F3 (Phase 0 J1) : tables « data-gap » interrogées par l'app mais NON déclarées en ORM (créées
    # hors code en prod par l'ingestion pente). On les matérialise VIDES en base de test → l'app ne
    # casse plus sur « relation inexistante » (le contrat data-gap = 0 ligne, jamais une erreur SQL).
    from labuse.ingestion import rnic
    with eng.begin() as _c:
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS parcel_terrain ("
            "  idu varchar PRIMARY KEY, pente_moy_deg real, pente_max_deg real,"
            "  flag_terrassement_lourd boolean, pente_non_batie_deg real,"
            "  computed_at timestamptz DEFAULT now())"))
        _c.execute(rnic.DDL)   # rnic_coproprietes (+ index) — DDL existante de l'ingesteur
        # M90 — l'ANC (parcel_anc) n'est VOLONTAIREMENT pas matérialisée ici : le flash l'omet déjà
        # proprement via `avail` (test_collect_parcelle_pauvre vérifie cette omission), et le POINT
        # UNIQUE anc_service.statut_anc s'auto-garde désormais sur table absente → « Absent » (un état),
        # jamais un 500. La matérialiser casserait le test d'omission. « selon le cas » : garde-source,
        # pas fixture (mesuré).
        # carreau Filosofi (contexte marché fiche) + parc social RPLS : tables vides suffisent
        # (les requêtes fiche tolèrent 0 ligne → panneau « data-gap », jamais une erreur).
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS filosofi_carreaux_200m ("
            "  geom geometry, ind double precision, men double precision,"
            "  men_pauv double precision, men_prop double precision, ind_snv double precision,"
            # CI-1 : tranches d'âge lues SANS garde par zone.population_zone (part des < 25 ans) —
            # leur absence faisait une ProgrammingError qui abortait la transaction du flash (étude
            # de zone), puis cascade InFailedSqlTransaction. `i_est_200` reste optionnelle (gardée).
            "  ind_0_3 double precision, ind_4_5 double precision, ind_6_10 double precision,"
            "  ind_11_17 double precision, ind_18_24 double precision)"))
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS rpls_commune ("
            "  insee varchar, commune varchar, millesime varchar, nb_logements integer,"
            "  construct_median integer, pct_qpv numeric, surfhab_moy numeric,"
            "  computed_at timestamptz DEFAULT now())"))
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS parcel_adresse ("
            "  idu varchar, ban_voie text, ban_cp varchar, ban_commune varchar)"))
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS parcel_zone_plu ("
            "  idu varchar, zone_lib varchar, zone_fam varchar)"))
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS parcel_viabilisation ("
            "  idu varchar, commune varchar, score integer, band varchar, zone_fam varchar,"
            "  c100 integer, c200 integer, c100_recent integer, c100_acheve integer,"
            "  voie10 boolean, voie75 boolean, bati10 boolean, bati30 boolean, bati75 boolean,"
            "  assainissement_zonage varchar, computed_at timestamptz DEFAULT now())"))
        # M136 — contexte commune (SRU/ANRU/PLH/marché INSEE) interrogé par /communes/{c}/contexte,
        # lui-même appelé par l'export PDF premium. Même contrat data-gap : tables VIDES → l'export
        # ne casse plus sur « relation inexistante » (0 ligne = section « non disponible » sourcée).
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS commune_contexte_sru ("
            "  insee varchar, commune varchar, statut varchar, taux_lls numeric, objectif_pct numeric,"
            "  millesime varchar, detail jsonb, importe_le timestamptz DEFAULT now())"))
        # M137-Z — le Comparateur joint la SRU sur `insee` : l'ajouter aux bases de test antérieures.
        _c.execute(text("ALTER TABLE commune_contexte_sru ADD COLUMN IF NOT EXISTS insee varchar"))
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS commune_insee_logement ("
            "  commune varchar, importe_le timestamptz DEFAULT now())"))
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS anru_quartiers ("
            "  commune varchar, nom varchar, interet varchar, code_qpv varchar,"
            "  source_nom varchar, source_url varchar)"))
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS plh_epci ("
            "  epci varchar, importe_le timestamptz DEFAULT now())"))
        # M137-Z — les tables des OUTILS COMMUNE (Rareté/Vélocité/Marché/Comparateur/Carnet) hors ORM :
        # matérialisées VIDES → les endpoints ne cassent plus sur « relation inexistante » (contrat
        # data-gap = 0 ligne, jamais une erreur SQL). Verrou : test_outils_commune_ne_crashent_pas.
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS m10_permit_delais ("
            "  permit_id varchar PRIMARY KEY, commune varchar, nature varchar, famille varchar,"
            "  date_depot date, date_autorisation date, date_achevement date, delai_mois integer,"
            "  valide boolean NOT NULL DEFAULT false, computed_at timestamptz DEFAULT now())"))
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS commune_conso_enaf ("
            "  insee varchar PRIMARY KEY, commune varchar, conso_2011_2021_m2 double precision,"
            "  conso_2021_2024_m2 double precision, hab_2011_2021_m2 double precision,"
            "  hab_2021_2024_m2 double precision, source_nom text, source_url text,"
            "  millesime varchar, importe_le timestamptz DEFAULT now())"))
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS dvf_prix_sortie_neuf ("
            "  cle varchar, niveau text, prix_m2_neuf integer, n integer, computed_at timestamptz DEFAULT now())"))
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS dvf_mutations_parcelle ("
            "  id bigint, id_mutation text, date_mutation date, nature_mutation text,"
            "  valeur_fonciere double precision, code_commune text, id_parcelle varchar, type_local text,"
            "  surface_reelle_bati double precision, surface_terrain double precision, nature_culture text,"
            "  longitude double precision, latitude double precision, millesime smallint)"))
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS dvf_secteur_medianes ("
            "  secteur varchar, type_bien varchar, n_ventes integer, mediane_valeur integer,"
            "  mediane_prix_m2 integer, fenetre text, computed_at timestamptz DEFAULT now())"))
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS dpe_records ("
            "  id integer, numero_dpe varchar, etiquette_dpe varchar, etiquette_ges varchar,"
            "  type_batiment varchar, surface_habitable double precision, annee_construction integer,"
            "  adresse text, code_insee varchar, code_postal varchar, date_etablissement date,"
            "  lon double precision, lat double precision, geocode_score double precision,"
            "  parcelle_idu varchar, rattachement varchar, raw jsonb, ingested_at timestamptz DEFAULT now())"))
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS parcel_signals ("
            "  id integer, parcel_id integer, signal_type varchar, payload jsonb,"
            "  detected_at timestamptz, notified_at timestamptz)"))
        # TESTS-1 lot 2 (D) — les DEUX tables d'ingestion qui faisaient crasher 9 tests en
        # « relation does not exist » (contrat data-gap : table VIDE = donnée absente, propre ;
        # table ABSENTE = 500). Cassé depuis RECETTE-4 lot 1 (9753b745, la fiche lit le zonage).
        from labuse.ingestion import rei as _rei
        from labuse.ingestion import zonage_abc as _zabc
        _c.execute(text(_zabc.DDL))   # commune_zonage_abc — DDL de l'ingesteur, source unique
        _c.execute(text(_rei.DDL))    # commune_rei (TFPB) — même branchement RECETTE-4
        # batiment_hauteur_lidar (colonnes survol comprises) : son ABSENCE fait qu'hauteur_lidar_servie
        # avale l'erreur par un rollback() de TOUTE la transaction — en test, les seeds du test sautent
        # en silence. Table vide = repli BD TOPO propre, aucun rollback.
        from labuse.faisabilite import hauteur_lidar_dalles as _hld
        _hld.ensure_colonnes_survol(_c)
        # toiture_lidar : toiture_depuis_cache avale « table absente » SANS rollback → la
        # transaction du test reste ABORTED et tout lecteur suivant lit du vide en silence.
        from labuse import solaire_toiture as _st
        _st.ensure_table(_c)
        _c.execute(text(          # parcel_bati_revele — lue SANS garde par bati.le_bien_block
            "CREATE TABLE IF NOT EXISTS parcel_bati_revele ("
            "  parcel_id integer PRIMARY KEY REFERENCES parcels(id),"
            "  idu varchar(14) NOT NULL, emprise_bdtopo_m2 double precision NOT NULL,"
            "  emprise_cosia_m2 double precision NOT NULL, bande varchar(16) NOT NULL,"
            "  motif text NOT NULL, computed_at timestamptz NOT NULL DEFAULT now())"))
        # pc_caducs (site_voisinage:44) — pas d'ensure_tables côté module ; colonnes SANS
        # contrainte : la fixture data-gap donne l'EXISTENCE, pas la rigueur d'ingestion
        # (test_surface_d seed des lignes partielles). DROP d'abord : une version STRICTE
        # laissée par une session antérieure ferait échouer ces seeds.
        _c.execute(text("DROP TABLE IF EXISTS pc_caducs"))
        _c.execute(text(
            "CREATE TABLE IF NOT EXISTS pc_caducs ("
            "  idu varchar(14),"   # pas de PK : test_surface_d seed des doublons d'idu exprès
            "  pc_annee int, caduc_depuis int, n_pc_octroyes int,"
            "  statut_autorisation text DEFAULT 'Sourcé',"
            "  statut_caducite text DEFAULT 'Estimé',"
            "  libelle_court text, detail text,"
            "  updated_at timestamptz DEFAULT now())"))
        # CI-1 (Lot 1) — artefacts posés HORS ORM par l'ingestion (jamais par create_all/boot), que
        # du code requête SANS garde de catalogue → UndefinedTable/Column sur base vierge (la CI).
        # Matérialisés VIDES = contrat data-gap (0 ligne, jamais une erreur SQL), fidèle à la prod.
        # `parcels.cadastre_disparue_le` (SOURCES-MAJ-1) : la garde `cadastre_disparue.colonne_presente`
        # couvre la plupart des lecteurs, mais tiles.py / l'omnibox / le KMZ la lisent en direct.
        _c.execute(text("ALTER TABLE parcels ADD COLUMN IF NOT EXISTS cadastre_disparue_le date"))
        from labuse.ingestion import division_or as _divor   # division_or_candidates (revue divisions)
        _c.exec_driver_sql(_divor.DDL)                        # DDL multi-instructions (CREATE + ALTER)
        _c.execute(text(                                      # mairies (annuaire communes) — ingest-mairies
            "CREATE TABLE IF NOT EXISTS mairies ("
            "  insee text PRIMARY KEY, commune text NOT NULL, nom text, adresse text,"
            "  code_postal text, telephone text, email text, site_officiel text,"
            "  url_annuaire text, source text NOT NULL, date_import timestamptz NOT NULL DEFAULT now())"))
    return eng


@pytest.fixture(autouse=True)
def _clear_mem_caches():
    """Vide les caches mémoire (stats/demo-status #6/#7 + top mutation) AVANT chaque test
    → aucune fuite de résultat mémorisé entre tests."""
    for mod, fn in (("labuse.api.app", "clear_mem_cache"), ("labuse.mutation", "clear_top_cache")):
        try:
            import importlib
            getattr(importlib.import_module(mod), fn)()
        except Exception:
            pass
    yield


@pytest.fixture
def db_session(engine):
    """Session transactionnelle rollback-ée après chaque test (pas de pollution)."""
    connection = engine.connect()
    trans = connection.begin()
    Session = sessionmaker(bind=connection, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()
