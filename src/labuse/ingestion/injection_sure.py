"""INJECTION-SOLIDE-1 — injecter une table SANS JAMAIS la casser.

Primitive d'injection SÛRE, réutilisable par toute ingestion de référence. Le constat du mandat :
`injection-nuit` lance aujourd'hui chaque ingestion détachée (CLI) et s'en remet, pour la sûreté, à
la robustesse propre de chaque script + au banc de cohérence du LENDEMAIN. Entre les deux, une
livraison vide / à moitié téléchargée / aux colonnes renommées / hors Réunion peut remplacer la table
servie — et n'être vue qu'au matin. La doctrine `autonomie.controler_injection` / `injecter_avec_
rollback` existait (JUGEMENTS purs) mais n'était pas CÂBLÉE à l'écriture réelle.

Cette primitive câble le JUGEMENT à une ÉCRITURE ATOMIQUE :

  1. VERROU consultatif par table (`pg_try_advisory_xact_lock`) : deux injections de la même table en
     même temps → la seconde est REFUSÉE (jamais deux écritures concurrentes sur la table servie).
  2. STAGING : le chargement se fait dans une table de travail `<table>__inj_staging` (jamais
     directement la servie). Le chargeur de l'appelant (`charger_staging`) la remplit.
  3. CONTRÔLES (`autonomie.controler_injection` + périmètre Réunion + doublons) sur la STAGING :
     comptes non nuls, géométries valides, couverture 974, écart sous seuil, aucune géométrie hors
     Réunion, aucun doublon sur la clé déclarée.
  4. SWAP ATOMIQUE : si — et seulement si — tout passe, `DELETE FROM servie; INSERT servie SELECT
     staging` DANS LA MÊME TRANSACTION, sous verrou ACCESS EXCLUSIVE. Un lecteur client ne voit JAMAIS
     une table à moitié remplie : il lit l'ancienne version jusqu'au COMMIT, la nouvelle ensuite.
  5. RETOUR ARRIÈRE : au moindre contrôle en échec OU à la moindre exception (coupure réseau, disque
     plein, colonne absente…), ROLLBACK — la table servie reste rigoureusement INTACTE — et un verdict
     d'échec est rendu (pour le mail/alerte). L'écriture n'est JAMAIS laissée à moitié faite.

« Sur-protéger est bénin, sous-protéger est le bug » : un contrôle qui ne peut pas conclure est un
ÉCHEC (on n'injecte pas), jamais un vert par vacuité.
"""
from __future__ import annotations

from sqlalchemy import text

from .. import autonomie

#: boîte englobante de La Réunion en WGS84 (lon/lat) — large, avec marge côtière (îlots compris).
#: Sert à refuser une livraison qui contient des géométries HORS du territoire (erreur de producteur
#: ou mauvais fichier : un shapefile métropole injecté « sur » une couche réunionnaise).
REUNION_BBOX_4326 = (55.15, -21.45, 55.95, -20.80)  # (min_lon, min_lat, max_lon, max_lat)


class InjectionRefusee(Exception):
    """INJECTION-SOLIDE-2 — levée par `remplacer_servie` quand une livraison est REFUSÉE (contrôle en
    échec) ou INTERROMPUE (exception pendant le chargement). Portée : faire ROULER EN ARRIÈRE la
    transaction de l'appelant (via `session_scope`), donc laisser la table servie RIGOUREUSEMENT
    INTACTE, et porter le `verdict` pour l'alerte/mail. Le verdict a déjà été passé à `alerter` (si
    fourni) AVANT la levée (sur une connexion indépendante, pour qu'il survive au rollback)."""

    def __init__(self, verdict: "autonomie.Verdict", table: str):
        self.verdict = verdict
        self.table = table
        super().__init__(f"injection « {table} » refusée — {verdict.resume()}")


def _staging_nom(table: str) -> str:
    return f"{table}__inj_staging"


def _cle_verrou(table: str) -> int:
    """Clé entière 63 bits stable pour `pg_try_advisory_xact_lock` (hashtext est 32 bits signé)."""
    import hashlib
    h = hashlib.md5(f"injection_sure:{table}".encode(), usedforsecurity=False).hexdigest()
    return int(h[:15], 16)  # 60 bits, positif


def mesurer_staging(conn, table: str, staging: str, *, a_geometrie: bool,
                    geom_col: str, dedup_cols: list[str] | None) -> dict:
    """Mesure la STAGING (et compare à la table servie) pour `autonomie.controler_injection`, plus
    deux mesures spécifiques au mandat : `hors_reunion` (géométries hors boîte Réunion) et `doublons`
    (lignes en double sur la clé déclarée). Lecture seule."""
    def _scalar(sql: str, params: dict | None = None) -> int:
        return int(conn.execute(text(sql), params or {}).scalar() or 0)

    m: dict = {"a_geometrie": a_geometrie}
    m["comptes_apres"] = _scalar(f'SELECT count(*) FROM "{staging}"')
    m["comptes_avant"] = _scalar(f'SELECT count(*) FROM "{table}"')
    if a_geometrie:
        m["geometries_invalides"] = _scalar(
            f'SELECT count(*) FROM "{staging}" WHERE "{geom_col}" IS NOT NULL '
            f'AND NOT ST_IsValid("{geom_col}")')
        # couverture 974 : nombre de communes distinctes (colonne `commune` si présente, sinon 0 →
        # l'appelant qui n'exige pas 974 passe couverture_974_min=0).
        a_commune = conn.execute(text(
            "SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = 'commune'"),
            {"t": staging}).scalar()
        m["communes_974"] = (_scalar(
            f'SELECT count(DISTINCT commune) FROM "{staging}" WHERE commune IS NOT NULL')
            if a_commune else 0)
        # hors Réunion : géométrie (en 4326) n'intersectant pas la boîte englobante du territoire.
        mnlon, mnlat, mxlon, mxlat = REUNION_BBOX_4326
        a_geom = conn.execute(text(
            "SELECT 1 FROM information_schema.columns WHERE table_name=:t AND column_name=:c"),
            {"t": staging, "c": geom_col}).scalar()
        srid = (int(conn.execute(text("SELECT Find_SRID('public', :g, :c)"),
                                 {"g": staging, "c": geom_col}).scalar() or 0) if a_geom else 0)
        g4326 = f'ST_Transform("{geom_col}", 4326)' if srid and srid != 4326 else f'"{geom_col}"'
        m["hors_reunion"] = _scalar(
            f'SELECT count(*) FROM "{staging}" WHERE "{geom_col}" IS NOT NULL AND NOT ST_Intersects('
            f'{g4326}, ST_MakeEnvelope(:a, :b, :c, :d, 4326))',
            {"a": mnlon, "b": mnlat, "c": mxlon, "d": mxlat})
    else:
        m["hors_reunion"] = 0
    if dedup_cols:
        cols = ", ".join(f'"{c}"' for c in dedup_cols)
        m["doublons"] = _scalar(
            f'SELECT COALESCE(sum(n) FILTER (WHERE n > 1), 0) FROM '
            f'(SELECT count(*) AS n FROM "{staging}" GROUP BY {cols}) q')
    else:
        m["doublons"] = 0
    return m


def controler(mesures: dict, *, delta_max_pct: float, couverture_974_min: int,
              autoriser_vide: bool = False) -> autonomie.Verdict:
    """`autonomie.controler_injection` + les deux contrôles du mandat (hors Réunion, doublons)."""
    v = autonomie.controler_injection(mesures, delta_max_pct=delta_max_pct,
                                      couverture_974_min=couverture_974_min,
                                      autoriser_vide=autoriser_vide)
    hr = mesures.get("hors_reunion") or 0
    if hr:
        v.ok = False
        v.echecs.append(f"{hr} géométrie(s) hors de La Réunion — livraison refusée (mauvais territoire)")
    else:
        v.reussis.append("perimetre-reunion")
    db = mesures.get("doublons") or 0
    if db:
        v.ok = False
        v.echecs.append(f"{db} doublon(s) sur la clé d'unicité — livraison refusée")
    else:
        v.reussis.append("sans-doublon")
    return v


def injecter_table_sure(engine, *, table: str, charger_staging,
                        a_geometrie: bool = True, geom_col: str = "geom_2975",
                        couverture_974_min: int = 0, delta_max_pct: float = 35.0,
                        dedup_cols: list[str] | None = None, preparer=None,
                        like_including: str = "DEFAULTS", autoriser_vide: bool = False,
                        alerter=None, log=lambda *_: None) -> dict:
    """Injecte `table` de façon SÛRE (voir le module). `charger_staging(conn, staging)` DOIT remplir la
    table de travail `staging` (déjà créée `LIKE table INCLUDING DEFAULTS`) — il ne touche JAMAIS la
    table servie. Rend `{injecte: bool, verdict: Verdict, mesures: dict, resume: str}`. Sur échec de
    contrôle ou exception : ROLLBACK (table servie intacte) + `alerter(verdict)` si fourni.

    Garanties : (1) deux injections concurrentes de la même table → la 2ᵉ REFUSÉE ; (2) la table servie
    n'est jamais à moitié remplie (swap atomique en une transaction) ; (3) tout échec = retour arrière."""
    staging = _staging_nom(table)
    out: dict = {"injecte": False}
    conn = engine.connect()
    trans = conn.begin()
    try:
        # (1) verrou consultatif lié à la transaction — libéré au commit/rollback.
        pris = conn.execute(text("SELECT pg_try_advisory_xact_lock(:k)"),
                            {"k": _cle_verrou(table)}).scalar()
        if not pris:
            trans.rollback()
            v = autonomie.Verdict(ok=False, echecs=[f"une autre injection de « {table} » est déjà en cours"])
            out["verdict"] = v
            out["resume"] = v.resume()
            if alerter:
                alerter(v)
            return out

        # (2) DDL idempotente de l'appelant (CREATE TABLE IF NOT EXISTS…) DANS la transaction, avant la
        #     staging : la servie doit exister pour un `LIKE`, y compris à la toute première injection.
        if preparer is not None:
            preparer(conn)
        # staging neuve, remplie par l'appelant (jamais la table servie).
        conn.execute(text(f'DROP TABLE IF EXISTS "{staging}"'))
        conn.execute(text(f'CREATE TABLE "{staging}" (LIKE "{table}" INCLUDING {like_including})'))
        charger_staging(conn, staging)

        # (3) contrôles sur la staging.
        mesures = mesurer_staging(conn, table, staging, a_geometrie=a_geometrie,
                                  geom_col=geom_col, dedup_cols=dedup_cols)
        out["mesures"] = mesures
        v = controler(mesures, delta_max_pct=delta_max_pct, couverture_974_min=couverture_974_min,
                      autoriser_vide=autoriser_vide)
        out["verdict"] = v
        out["resume"] = v.resume()

        if not v.ok:
            trans.rollback()  # table servie INTACTE ; staging jetée avec la transaction
            log(f"✗ injection {table} REFUSÉE — {v.resume()}")
            if alerter:
                alerter(v)
            return out

        # (4) SWAP ATOMIQUE : vider+recharger la servie dans la MÊME transaction. On NE POSE PAS de
        #     ACCESS EXCLUSIVE : le DELETE+INSERT prend un verrou ROW EXCLUSIVE (compatible avec les
        #     lectures), et le MVCC garantit qu'un lecteur client voit l'ANCIENNE version ENTIÈRE
        #     jusqu'au COMMIT, la NOUVELLE ensuite — jamais une table à moitié pleine, et sans jamais
        #     BLOQUER les lectures (swap en ligne). La concurrence d'ÉCRITURE est déjà exclue par le
        #     verrou consultatif ci-dessus (une seule injection de cette table à la fois).
        conn.execute(text(f'DELETE FROM "{table}"'))
        conn.execute(text(f'INSERT INTO "{table}" SELECT * FROM "{staging}"'))
        conn.execute(text(f'DROP TABLE IF EXISTS "{staging}"'))
        trans.commit()
        out["injecte"] = True
        log(f"✓ injection {table} servie — {mesures['comptes_avant']} → {mesures['comptes_apres']} lignes")
        return out
    except Exception as exc:  # noqa: BLE001 — toute exception = rollback (jamais de demi-écriture)
        try:
            trans.rollback()
        except Exception:  # noqa: BLE001
            pass
        v = autonomie.Verdict(ok=False, echecs=[f"{type(exc).__name__}: {exc}"])
        out["verdict"] = v
        out["resume"] = v.resume()
        out["erreur"] = f"{type(exc).__name__}: {exc}"
        log(f"✗ injection {table} INTERROMPUE — {out['erreur']} → retour arrière")
        if alerter:
            alerter(v)
        return out
    finally:
        conn.close()


def remplacer_servie(session, *, table: str, charger_staging, preparer=None,
                     a_geometrie: bool = True, geom_col: str = "geom_2975",
                     couverture_974_min: int = 0, delta_max_pct: float = 35.0,
                     dedup_cols: list[str] | None = None, like_including: str = "DEFAULTS",
                     autoriser_vide: bool = False, alerter=None, log=lambda *_: None) -> dict:
    """INJECTION-SOLIDE-2 — variante de `injecter_table_sure` qui travaille DANS la transaction de
    l'appelant (une `Session` ouverte par `session_scope`), au lieu d'ouvrir sa propre connexion.

    C'est le point d'ADOPTION pour les ingestions existantes : elles remplaçaient leur table servie
    par `TRUNCATE … ; INSERT …` ; elles appellent désormais ceci avec un `charger_staging(conn, staging)`
    qui remplit la table de travail (jamais la servie). Mêmes garanties que la primitive :

      1. verrou consultatif par table (2ᵉ injection concurrente → REFUSÉE) ;
      2. `preparer(conn)` (DDL idempotente), puis STAGING `LIKE table` remplie par l'appelant ;
      3. CONTRÔLES sur la staging (comptes, géométries, couverture 974, écart, hors Réunion, doublons) ;
      4. si tout passe → SWAP ATOMIQUE `DELETE servie ; INSERT servie SELECT staging` dans LA MÊME
         transaction (ROW EXCLUSIVE, jamais de table à moitié remplie, lecteurs non bloqués) ;
      5. sinon → `alerter(verdict)` (connexion indépendante) puis **lève `InjectionRefusee`** : la
         transaction de l'appelant ROULE EN ARRIÈRE (`session_scope`) → table servie INTACTE.

    Rend `{injecte: True, verdict, mesures, resume}` en cas de succès. Ne commit PAS : c'est l'appelant
    (`session_scope`) qui valide la transaction, avec tout post-traitement idempotent qui suit."""
    staging = _staging_nom(table)

    def _refuser(v: "autonomie.Verdict"):
        if alerter:
            try:
                alerter(v)          # connexion indépendante → survit au rollback de l'appelant
            except Exception as exc:  # noqa: BLE001 — une alerte qui rate ne doit pas masquer le refus
                log(f"(alerte injection {table} impossible : {type(exc).__name__}: {exc})")
        raise InjectionRefusee(v, table)

    # (1) verrou consultatif lié à la transaction de l'appelant — libéré au commit/rollback.
    pris = session.execute(text("SELECT pg_try_advisory_xact_lock(:k)"),
                           {"k": _cle_verrou(table)}).scalar()
    if not pris:
        _refuser(autonomie.Verdict(
            ok=False, echecs=[f"une autre injection de « {table} » est déjà en cours"]))

    # (2) DDL idempotente puis staging neuve, remplie par l'appelant (jamais la servie).
    if preparer is not None:
        preparer(session)
    session.execute(text(f'DROP TABLE IF EXISTS "{staging}"'))
    session.execute(text(f'CREATE TABLE "{staging}" (LIKE "{table}" INCLUDING {like_including})'))
    try:
        charger_staging(session, staging)
    except InjectionRefusee:
        raise
    except Exception as exc:  # noqa: BLE001 — coupure réseau / disque plein / colonne absente → refus
        _refuser(autonomie.Verdict(ok=False, echecs=[f"{type(exc).__name__}: {exc}"]))

    # (3) contrôles sur la staging.
    mesures = mesurer_staging(session, table, staging, a_geometrie=a_geometrie,
                              geom_col=geom_col, dedup_cols=dedup_cols)
    v = controler(mesures, delta_max_pct=delta_max_pct, couverture_974_min=couverture_974_min,
                  autoriser_vide=autoriser_vide)
    if not v.ok:
        log(f"✗ injection {table} REFUSÉE — {v.resume()}")
        _refuser(v)

    # (4) SWAP ATOMIQUE dans la transaction de l'appelant (voir `injecter_table_sure`).
    session.execute(text(f'DELETE FROM "{table}"'))
    session.execute(text(f'INSERT INTO "{table}" SELECT * FROM "{staging}"'))
    session.execute(text(f'DROP TABLE IF EXISTS "{staging}"'))
    log(f"✓ injection {table} servie — {mesures['comptes_avant']} → {mesures['comptes_apres']} lignes")
    return {"injecte": True, "verdict": v, "mesures": mesures, "resume": v.resume()}


def alerte_injection(table: str, source: str = "", *, engine_factory=None):
    """Fabrique un `alerter(verdict)` qui OUVRE un incident ops (`ops_alertes.signaler`) sur une
    connexion INDÉPENDANTE — il doit survivre au rollback de l'injection refusée. Clé stable par table
    (`injection-refusee:<table>`) : une alerte claire, rappelée au plus une fois par jour, qui pointe le
    Tableau de bord. La version servie reste celle d'avant (le refus n'écrit rien)."""
    def _alerter(verdict):
        from .. import ops_alertes
        from ..db import engine as _engine
        eng = (engine_factory or _engine)()
        quoi = source or table
        with eng.begin() as c:
            ops_alertes.signaler(
                c, f"injection-refusee:{table}",
                f"Injection refusée : {quoi} — version servie conservée",
                f"La livraison de « {quoi} » (table {table}) a été REFUSÉE par le contrôle d'injection "
                f"sûre ; la version servie précédente est CONSERVÉE (rien n'a été remplacé).\n\n"
                f"Motif : {verdict.resume()}\n\n"
                "Ouvre le Tableau de bord → Sources pour voir l'état, puis relance quand la livraison "
                "amont est correcte.", lien="/admin/sources")
    return _alerter
