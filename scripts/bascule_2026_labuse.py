#!/usr/bin/env python
"""OUTIL-SCAN-FIX-5 — bascule 2026, PÉRIMÈTRE RÉDUIT. Le V-score (recalcul + promotion) NE FAIT PLUS
PARTIE de cette bascule (chantier du nouveau classement). Le script ne touche NI le feature store, NI
`data_sources`, NI `p_score_v2_runs`/`parcel_p_score_v2`, NI `config/served_run.txt`/`served_manifest.json`.

L'agent ne lance JAMAIS --go/--rollback sur la base commune `labuse`. Tout se prouve sur `labuse_scanfix`.

PÉRIMÈTRE (seules tables SERVIES écrites — liste exhaustive, par étape) :
  [1] droits 2025+2026  → `parcelle_pm_droit` (via table d'attente `parcelle_pm_droit_staging`, temp, droppée)
  [2] archive 2025 + flip → `pm_proprietaires_millesimes`, `parcelle_personne_morale`
      (+ colonnes droit_code/droit_label ; swap `injection_sure` via temp `…__inj_staging`, droppée)
  [3] BODACC             → `bodacc_depots`  (le « touch » de fraîcheur `data_sources` est NEUTRALISÉ :
                           snapshot + restauration dans la MÊME transaction → data_sources inchangée)
  [4] blocs              → `parcel_blocs`, `parcel_bloc_membres`  (temp `_blocs_pm`, droppée)
  → 6 tables servies, TOUTES dans CONCERNEES (sauvegarde + --rollback les couvrent).

SÛRETÉS (relecture-scan-3/4) :
  • Cible par ARGUMENT `--db <url>` (zéro env/.env/défaut) ; `--confirme` = identité SERVEUR
    `current_database()@system_identifier:port` (localhost=127.0.0.1=::1=casse) ; refus n'imprime pas la valeur.
  • Sauvegardes NUMÉROTÉES/DATÉES `_bascule_bak__<N>__*` + registre `_bascule_sauvegardes` ; --go refuse une
    sauvegarde ancienne (sauf --malgre-sauvegarde N) ; --rollback exige --sauvegarde N ; --purge-sauvegarde N.
  • Staging + TRANSACTION UNIQUE pour [2]. Toute étape qui ÉCHOUE ARRÊTE la procédure (code ≠ 0) et dit
    « --rollback --sauvegarde N » ; JAMAIS de « [OK] » après un échec.

Usage :
    P=.venv/bin/python; S=scripts/bascule_2026_labuse.py; U=postgresql+psycopg://user@host:5432/base
    $P $S --db "$U" --empreinte | --dry-run | --lister-sauvegardes
    $P $S --db "$U" --go       --confirme base@<system_identifier>:<port> [--malgre-sauvegarde N] [--bodacc-limit K]
    $P $S --db "$U" --rollback --sauvegarde N --confirme base@<system_identifier>:<port>
    $P $S --db "$U" --purge-sauvegarde N --confirme base@<system_identifier>:<port>
"""
from __future__ import annotations

import datetime as _dt
import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

CONCERNEES = ["parcelle_personne_morale", "pm_proprietaires_millesimes", "parcelle_pm_droit",
              "bodacc_depots", "parcel_blocs", "parcel_bloc_membres"]
BAK = "_bascule_bak__"
REGISTRE = "_bascule_sauvegardes"
STAGING = "parcelle_pm_droit_staging"


# ───────────────────────── identité & empreinte ─────────────────────────
def _existe(session, t: str) -> bool:
    return session.execute(text("SELECT to_regclass(:t) IS NOT NULL"), {"t": t}).scalar()


def _colonnes(session, t: str) -> list[str]:
    return [r[0] for r in session.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='public' "
        "AND table_name=:t ORDER BY ordinal_position"), {"t": t}).all()]


def _empreinte(session, t: str) -> tuple:
    """(existe, n_lignes, checksum) — checksum = Σ hashtext(ligne ENTIÈRE) : TOUTES les colonnes
    (volatiles comprises). Indépendant de l'ordre ; capture tout."""
    if not _existe(session, t):
        return (False, 0, 0)
    n, chk = session.execute(text(
        f'SELECT count(*), COALESCE(sum(hashtext(t.*::text)::bigint), 0) FROM "{t}" t')).first()
    return (True, int(n), int(chk))


def _identite_serveur(session) -> str:
    """Identité RENVOYÉE PAR LE SERVEUR, indépendante de la graphie d'hôte côté client :
    `current_database()` @ `system_identifier` (cluster — identique localhost/127.0.0.1/::1/socket) `:` port.
    `inet_server_addr()` NE convient PAS (rend ::1 vs 127.0.0.1). Minuscules (insensible à la casse)."""
    base, sysid, port = session.execute(text(
        "SELECT current_database(), (SELECT system_identifier FROM pg_control_system()), "
        "       COALESCE(inet_server_port()::text, 'local')")).first()
    return f"{base}@{sysid}:{port}".lower()


def _affiche_etat(session, titre: str) -> None:
    print(f"\n── {titre} — serveur {_identite_serveur(session)} ──")
    for t in CONCERNEES:
        ex, n, chk = _empreinte(session, t)
        print(f"   {t:30} {'(absente)' if not ex else f'{n:>8} lignes  checksum={chk}'}")


def _exige_confirme(session, confirme: str | None, action: str) -> None:
    ident = _identite_serveur(session)
    if not confirme or confirme.strip().lower() != ident:
        print(f"\n✗ {action} REFUSÉ — `--confirme` absent ou ≠ identité du serveur "
              f"(base@system_identifier:port). Lis-la avec --empreinte/--dry-run (lecture seule) puis "
              f"recommence. Rien écrit.")
        sys.exit(2)


# ───────────────────────── sauvegardes numérotées ─────────────────────────
def _ensure_registre(session) -> None:
    session.execute(text(
        f'CREATE TABLE IF NOT EXISTS "{REGISTRE}" (numero int PRIMARY KEY, date_iso text, cible text)'))


def _sauvegardes(session) -> list[dict]:
    if not _existe(session, REGISTRE):
        return []
    return [dict(r) for r in session.execute(text(
        f'SELECT numero, date_iso, cible FROM "{REGISTRE}" ORDER BY numero')).mappings()]


def _lister(session) -> None:
    print(f"\n── Sauvegardes sur {_identite_serveur(session)} ──")
    sv = _sauvegardes(session)
    if not sv:
        print("   (aucune)")
    for s in sv:
        pm = _empreinte(session, f"{BAK}{s['numero']}__parcelle_personne_morale")
        print(f"   #{s['numero']}  {s['date_iso']}  cible={s['cible']}  "
              f"parcelle_personne_morale={pm[1]} lignes")


def _sauvegarder(session, numero: int, log=print) -> None:
    _ensure_registre(session)
    session.execute(text(f'DROP TABLE IF EXISTS "{BAK}{numero}__meta"'))
    session.execute(text(f'CREATE TABLE "{BAK}{numero}__meta" (cle text, valeur text)'))
    for t in CONCERNEES:
        session.execute(text(f'DROP TABLE IF EXISTS "{BAK}{numero}__{t}"'))
        if _existe(session, t):
            session.execute(text(f'CREATE TABLE "{BAK}{numero}__{t}" AS TABLE "{t}"'))
            log(f"   sauvegarde #{numero} {t}")
        else:
            session.execute(text(f'INSERT INTO "{BAK}{numero}__meta" VALUES (:k, :v)'),
                            {"k": f"absente:{t}", "v": "1"})
    session.execute(text(f'INSERT INTO "{REGISTRE}" (numero, date_iso, cible) VALUES (:n, :d, :c)'),
                    {"n": numero, "d": _dt.datetime.now().isoformat(timespec="seconds"),
                     "c": _identite_serveur(session)})
    session.commit()


def _arret_echec(session, numero: int, etape: str, exc: Exception) -> None:
    """Une étape a ÉCHOUÉ : on ANNULE la transaction en cours, on dit quoi faire, on sort en ERREUR.
    JAMAIS de « [OK] » après ça."""
    try:
        session.rollback()
    except Exception:  # noqa: BLE001
        pass
    print(f"\n✗ ÉCHEC à l'étape « {etape} » : {type(exc).__name__}: {str(exc)[:200]}")
    print(f"  La base servie peut être partiellement modifiée (étapes déjà committées). REVIENS EN ARRIÈRE :")
    print(f"      --rollback --sauvegarde {numero} --confirme <identité>")
    sys.exit(1)


def _crash_si_demande(etape: str, log) -> None:
    if _arg(sys.argv[1:], "--_crash-at") == etape:
        log(f"\n[_crash-at {etape}] interruption DURE (kill simulé) au milieu de l'étape. Rien committé ici.")
        os._exit(137)


def _fail_si_demande(etape: str) -> None:
    if _arg(sys.argv[1:], "--_fail-at") == etape:
        raise RuntimeError(f"échec forcé (--_fail-at {etape}) pour la preuve du point 2")


# ───────────────────────── GO ─────────────────────────
def go(session, confirme, malgre, bodacc_limit, log=print) -> None:
    _exige_confirme(session, confirme, "--go")
    existantes = _sauvegardes(session)
    if existantes and malgre != existantes[-1]["numero"]:
        print(f"\n✗ --go REFUSÉ — une sauvegarde plus ancienne existe (#{existantes[-1]['numero']}, "
              f"{existantes[-1]['date_iso']}). Relance avec --malgre-sauvegarde {existantes[-1]['numero']} "
              f"(la conserver) ou --purge-sauvegarde {existantes[-1]['numero']} (la supprimer).")
        sys.exit(2)
    numero = (existantes[-1]["numero"] + 1) if existantes else 1

    _affiche_etat(session, "AVANT bascule")
    log(f"\n[0] SAUVEGARDE #{numero} (datée, rollback-able) …")
    _sauvegarder(session, numero, log)

    from labuse.ingestion import pm_droits, pm_millesimes

    # [1] droits → table d'attente (servie INCHANGÉE ; interruption ici = rien côté servi).
    try:
        log("\n[1] droits 2025 + 2026 → table d'attente (staging) …")
        session.execute(text(f'DROP TABLE IF EXISTS "{STAGING}"'))
        pm_droits.ensure_table(session, STAGING, commit=False)
        pm_droits.ingest_droits(session, pm_millesimes.fetch_974_csv(2025), "2025", table=STAGING, commit=False, log=log)
        pm_droits.ingest_droits(session, pm_droits.fetch_974_csv(), "2026", table=STAGING, commit=False, log=log)
        session.commit()
        _crash_si_demande("staging", log)
        _fail_si_demande("droits")
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        _arret_echec(session, numero, "droits (staging)", exc)

    # [2] TRANSACTION UNIQUE : promotion droits + archive 2025 + flip.
    try:
        log("\n[2] TRANSACTION UNIQUE : promotion droits → archive 2025 (même règle) → flip 2026 …")
        cols = [c for c in _colonnes(session, STAGING) if c != "id"]
        cl = ", ".join(f'"{c}"' for c in cols)
        pm_droits.ensure_table(session, "parcelle_pm_droit", commit=False)
        session.execute(text('DELETE FROM parcelle_pm_droit'))
        session.execute(text(f'INSERT INTO parcelle_pm_droit ({cl}) SELECT {cl} FROM "{STAGING}"'))
        pm_droits.archive_principal_depuis_droits(session, "2025", commit=False, log=log)
        _crash_si_demande("flip", log)   # au milieu de la transaction, AVANT le commit → MVCC annule tout
        pm_droits.recompute_principal(session, "2026", commit=False, log=log)
        _fail_si_demande("flip")
        session.commit()                 # ← seul point de bascule des tables [2]
        session.execute(text(f'DROP TABLE IF EXISTS "{STAGING}"')); session.commit()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        _arret_echec(session, numero, "archive+flip", exc)

    # [3] BODACC — écrit bodacc_depots ; le touch data_sources est NEUTRALISÉ (snapshot+restore, même txn).
    try:
        log(f"\n[3] BODACC — dépôts {'(limite %d)' % bodacc_limit if bodacc_limit else '(tous)'} …")
        from labuse.ingestion import bodacc
        avant_ds = session.execute(text(
            "SELECT last_sync_at FROM data_sources WHERE name = :n"), {"n": bodacc.SOURCE_NAME}).scalar()
        sirens = bodacc.distinct_sirens(session)
        if bodacc_limit:
            sirens = sirens[:bodacc_limit]
        r = bodacc.ingest_bodacc_depots(session, sirens)
        # RESTAURE data_sources à sa valeur d'avant → le script ne CHANGE PAS data_sources.
        session.execute(text("UPDATE data_sources SET last_sync_at = :v WHERE name = :n"),
                        {"v": avant_ds, "n": bodacc.SOURCE_NAME})
        _crash_si_demande("bodacc", log)
        _fail_si_demande("bodacc")
        session.commit()
        log(f"   bodacc_depots : {r.get('depots')} dépôts / {r.get('sirens_queried')} SIREN (data_sources inchangée)")
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        _arret_echec(session, numero, "bodacc", exc)

    # [4] BLOCS — parcel_blocs + parcel_bloc_membres (une transaction).
    try:
        log("\n[4] BLOCS — parcel_blocs + parcel_bloc_membres …")
        from labuse import blocs
        rb = blocs.build_blocs(session)
        _crash_si_demande("blocs", log)
        _fail_si_demande("blocs")
        session.commit()
        log(f"   blocs : {rb.get('n_blocs')} blocs / {rb.get('n_membres')} membres")
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        _arret_echec(session, numero, "blocs", exc)

    _affiche_etat(session, "APRÈS bascule")
    log(f"\n[OK] procédure terminée (sauvegarde #{numero}). Retour arrière : "
        f"--rollback --sauvegarde {numero} --confirme <identité>. "
        f"(Le recalcul & la promotion du V-score NE font PAS partie de cette bascule — chantier séparé.)")


# ───────────────────────── ROLLBACK / PURGE ─────────────────────────
def rollback(session, numero, confirme, log=print) -> None:
    _exige_confirme(session, confirme, "--rollback")
    if numero is None:
        print("\n✗ --rollback REFUSÉ — nomme la sauvegarde : --sauvegarde <N> (--lister-sauvegardes)."); sys.exit(2)
    sv = {s["numero"]: s for s in _sauvegardes(session)}
    if numero not in sv:
        print(f"\n✗ --rollback REFUSÉ — sauvegarde #{numero} inconnue. Disponibles : {sorted(sv)}."); sys.exit(2)
    s = sv[numero]
    pm = _empreinte(session, f"{BAK}{numero}__parcelle_personne_morale")
    print(f"\n── ROLLBACK vers la sauvegarde #{numero} — date {s['date_iso']} · cible {s['cible']} · "
          f"parcelle_personne_morale {pm[1]} lignes ──")
    _affiche_etat(session, "AVANT rollback")
    meta = {r[0]: r[1] for r in session.execute(text(f'SELECT cle, valeur FROM "{BAK}{numero}__meta"')).all()}
    absentes = {k.split(":", 1)[1] for k in meta if k.startswith("absente:")}
    log("\n[rollback] restauration des tables concernées (UNE transaction) …")
    for t in CONCERNEES:
        if t in absentes:
            session.execute(text(f'DROP TABLE IF EXISTS "{t}"'))
            log(f"   {t} : retirée (absente dans la sauvegarde #{numero})")
        elif _existe(session, f"{BAK}{numero}__{t}"):
            bak_cols = _colonnes(session, f"{BAK}{numero}__{t}")
            for c in [c for c in _colonnes(session, t) if c not in bak_cols]:
                session.execute(text(f'ALTER TABLE "{t}" DROP COLUMN "{c}"'))
            session.execute(text(f'DELETE FROM "{t}"'))
            cc = ", ".join(f'"{c}"' for c in bak_cols)
            session.execute(text(f'INSERT INTO "{t}" ({cc}) SELECT {cc} FROM "{BAK}{numero}__{t}"'))
            log(f"   {t} : restaurée depuis #{numero}")
    session.execute(text(f'DROP TABLE IF EXISTS "{STAGING}"'))
    session.commit()
    _affiche_etat(session, "APRÈS rollback")


def purge(session, numero, confirme, log=print) -> None:
    _exige_confirme(session, confirme, "--purge-sauvegarde")
    if numero is None:
        print("\n✗ --purge-sauvegarde REFUSÉ — nomme la sauvegarde : --purge-sauvegarde <N>."); sys.exit(2)
    for t in CONCERNEES + ["meta"]:
        session.execute(text(f'DROP TABLE IF EXISTS "{BAK}{numero}__{t}"'))
    if _existe(session, REGISTRE):
        session.execute(text(f'DELETE FROM "{REGISTRE}" WHERE numero = :n'), {"n": numero})
    session.commit()
    log(f"✓ sauvegarde #{numero} supprimée.")


def _arg(args, nom):
    return args[args.index(nom) + 1] if nom in args and args.index(nom) + 1 < len(args) else None


def main() -> None:
    args = sys.argv[1:]
    url = _arg(args, "--db")
    if not url:
        print("✗ --db <url> OBLIGATOIRE (le script ne lit NI l'environnement NI .env, aucun défaut)."); sys.exit(2)
    confirme = _arg(args, "--confirme")
    numero = _arg(args, "--sauvegarde") or _arg(args, "--purge-sauvegarde")
    numero = int(numero) if numero and str(numero).isdigit() else None
    malgre = _arg(args, "--malgre-sauvegarde"); malgre = int(malgre) if malgre and str(malgre).isdigit() else None
    bodacc_limit = _arg(args, "--bodacc-limit"); bodacc_limit = int(bodacc_limit) if bodacc_limit and str(bodacc_limit).isdigit() else 0

    eng = create_engine(url)
    try:
        s = Session(eng)
        s.execute(text("SELECT 1"))          # provoque la connexion ICI pour cadrer l'erreur
    except OperationalError as exc:
        # Point 6 (relecture-4 n°10) — base/serveur injoignable → message cadré, pas de traceback brut.
        msg = str(exc.orig).splitlines()[0] if exc.orig else str(exc).splitlines()[0]
        print(f"✗ connexion impossible à la base passée en --db : {msg}\n"
              f"  Vérifie l'URL --db (base/hôte/port/droits). Rien fait."); sys.exit(2)
    with s:
        if "--lister-sauvegardes" in args:
            _lister(s); return
        if "--empreinte" in args:
            _affiche_etat(s, "EMPREINTE (lecture seule)"); return
        if "--dry-run" in args:
            _affiche_etat(s, "DRY-RUN (lecture seule — rien écrit)")
            print("\n[dry-run] --go : [0] sauvegarde #N → [1] staging droits 2025+2026 → [2] UNE "
                  "transaction {promotion droits · archive 2025 · flip} → [3] BODACC (data_sources "
                  "neutralisée) → [4] blocs(+membres). Une étape qui échoue ARRÊTE (code≠0, pas de « [OK] »). "
                  "Le V-score (recalcul/promotion) n'est PAS dans cette bascule.")
            return
        if "--go" in args:
            go(s, confirme, malgre, bodacc_limit); return
        if "--rollback" in args:
            rollback(s, numero, confirme); return
        if "--purge-sauvegarde" in args:
            purge(s, numero, confirme); return
    print("Action : --lister-sauvegardes | --empreinte | --dry-run | --go | --rollback | --purge-sauvegarde."
          " Toutes exigent --db <url>."); sys.exit(2)


if __name__ == "__main__":
    main()
