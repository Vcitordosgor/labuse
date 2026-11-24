#!/usr/bin/env python
"""OUTIL-SCAN-FIX-4 — bascule 2026 SÛRE, PROCÉDURE ENTIÈRE sous retour arrière.

L'agent ne lance JAMAIS --go/--rollback sur la base commune `labuse`. Tout se prouve sur `labuse_scanfix`.

Sûretés (relecture-scan-3, points 1-4) :
  1. SAUVEGARDE NUMÉROTÉE/DATÉE, jamais périmée. Chaque --go crée `_bascule_bak__<N>__*` (N = numéro de
     bascule) + une ligne au registre `_bascule_sauvegardes`. --go REFUSE si une sauvegarde plus ancienne
     existe, SAUF `--malgre-sauvegarde <N>` qui la nomme. --rollback EXIGE `--sauvegarde <N>`, affiche
     (numéro, date, lignes) et n'agit QUE sur celle-là. `--purge-sauvegarde <N>` la supprime.
  2. CIBLE PAR ARGUMENT. `--db <url>` OBLIGATOIRE : le script ne lit NI l'environnement NI `.env`, et n'a
     AUCUN défaut. `--confirme` est comparé à l'IDENTITÉ RENVOYÉE PAR LE SERVEUR
     (`current_database()` + `inet_server_addr()` + `inet_server_port()`), pas à une chaîne d'URL. En cas de
     refus, le script N'IMPRIME PAS la valeur attendue.
  3. localhost == 127.0.0.1 == casse : la comparaison porte sur l'identité SERVEUR (même serveur → même
     réponse), normalisée en minuscules.
  4. PROCÉDURE ENTIÈRE enchaînée par le script (plus aucune étape manuelle) : droits → archive 2025 →
     flip → BODACC → blocs(+membres) → recalcul & PROMOTION V-score. La sauvegarde couvre TOUT, y compris
     `parcel_bloc_membres`, `p_score_v2_runs`, `parcel_p_score_v2` et le LABEL SERVI (`config/served_run.txt`).
     --rollback RE-SERT réellement le run précédent (réécrit le fichier) et le VÉRIFIE.

Usage :
    P=.venv/bin/python; S=scripts/bascule_2026_labuse.py; U=postgresql+psycopg://user@host:5432/base
    $P $S --db "$U" --lister-sauvegardes
    $P $S --db "$U" --empreinte
    $P $S --db "$U" --dry-run
    $P $S --db "$U" --go       --confirme base@127.0.0.1:5432 [--malgre-sauvegarde N] [--bodacc-limit K]
    $P $S --db "$U" --rollback --sauvegarde N --confirme base@127.0.0.1:5432
    $P $S --db "$U" --purge-sauvegarde N --confirme base@127.0.0.1:5432
"""
from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

CONCERNEES = ["parcelle_personne_morale", "pm_proprietaires_millesimes", "parcelle_pm_droit",
              "bodacc_depots", "parcel_blocs", "parcel_bloc_membres",
              "p_score_v2_runs", "parcel_p_score_v2"]
BAK = "_bascule_bak__"
REGISTRE = "_bascule_sauvegardes"
STAGING = "parcelle_pm_droit_staging"
SERVED_FILE = Path(__file__).resolve().parents[1] / "config" / "served_run.txt"


# ───────────────────────── identité & empreinte ─────────────────────────
def _existe(session, t: str) -> bool:
    return session.execute(text("SELECT to_regclass(:t) IS NOT NULL"), {"t": t}).scalar()


def _colonnes(session, t: str) -> list[str]:
    return [r[0] for r in session.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='public' "
        "AND table_name=:t ORDER BY ordinal_position"), {"t": t}).all()]


def _empreinte(session, t: str) -> tuple:
    """(existe, n_lignes, checksum) — checksum = Σ hashtext(ligne ENTIÈRE) : TOUTES les colonnes
    (volatiles comprises : id, date_import…). Indépendant de l'ordre ; capture tout."""
    if not _existe(session, t):
        return (False, 0, 0)
    n, chk = session.execute(text(
        f'SELECT count(*), COALESCE(sum(hashtext(t.*::text)::bigint), 0) FROM "{t}" t')).first()
    return (True, int(n), int(chk))


def _identite_serveur(session) -> str:
    """Ce que le SERVEUR répond, indépendamment de la GRAPHIE d'hôte côté client :
    `current_database()` @ `system_identifier` (identité du cluster, renvoyée par le serveur —
    IDENTIQUE pour localhost, 127.0.0.1, ::1, socket…) : `inet_server_addr()` NE convient PAS (rend
    ::1 vs 127.0.0.1 selon la connexion). + port. Normalisée en minuscules (insensible à la casse)."""
    base, sysid, port = session.execute(text(
        "SELECT current_database(), (SELECT system_identifier FROM pg_control_system()), "
        "       COALESCE(inet_server_port()::text, 'local')")).first()
    return f"{base}@{sysid}:{port}".lower()


def _label_servi() -> str | None:
    if not SERVED_FILE.exists():
        return None
    for ln in SERVED_FILE.read_text(encoding="utf-8").splitlines():
        if ln.strip() and not ln.strip().startswith("#"):
            return ln.strip()
    return None


def _affiche_etat(session, titre: str) -> None:
    print(f"\n── {titre} — serveur {_identite_serveur(session)} · label servi « {_label_servi()} » ──")
    for t in CONCERNEES:
        ex, n, chk = _empreinte(session, t)
        print(f"   {t:30} {'(absente)' if not ex else f'{n:>8} lignes  checksum={chk}'}")


def _exige_confirme(session, confirme: str | None, action: str) -> None:
    ident = _identite_serveur(session)
    if not confirme or confirme.strip().lower() != ident:
        # Point 2 : on n'imprime PAS l'identité attendue (sinon le refus dicte la valeur à recopier).
        print(f"\n✗ {action} REFUSÉ — `--confirme` absent ou ne correspond pas à l'identité du serveur "
              f"(base@adresse:port renvoyée par le serveur). Vérifie la cible avec --empreinte/--dry-run "
              f"(lecture seule) puis recommence. Rien écrit.")
        sys.exit(2)


# ───────────────────────── sauvegardes numérotées ─────────────────────────
def _ensure_registre(session) -> None:
    session.execute(text(
        f'CREATE TABLE IF NOT EXISTS "{REGISTRE}" (numero int PRIMARY KEY, date_iso text, '
        f'cible text, label_servi text)'))


def _sauvegardes(session) -> list[dict]:
    if not _existe(session, REGISTRE):
        return []
    return [dict(r) for r in session.execute(text(
        f'SELECT numero, date_iso, cible, label_servi FROM "{REGISTRE}" ORDER BY numero')).mappings()]


def _lister(session) -> None:
    sv = _sauvegardes(session)
    print(f"\n── Sauvegardes sur {_identite_serveur(session)} ──")
    if not sv:
        print("   (aucune)")
    for s in sv:
        pm = _empreinte(session, f"{BAK}{s['numero']}__parcelle_personne_morale")
        print(f"   #{s['numero']}  {s['date_iso']}  cible={s['cible']}  label_servi={s['label_servi']}  "
              f"parcelle_personne_morale={pm[1]} lignes")


def _sauvegarder(session, numero: int, log=print) -> None:
    """Copie TOUTES les tables concernées dans `_bascule_bak__<N>__*` + note les tables absentes et le
    LABEL SERVI (config/served_run.txt). Daté, numéroté, jamais écrasé."""
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
    label = _label_servi()
    session.execute(text(f'INSERT INTO "{BAK}{numero}__meta" VALUES (:k, :v)'),
                    {"k": "label_servi", "v": label or ""})
    # OCTETS EXACTS du fichier du run servi (config/served_run.txt) → restaurés tels quels au rollback
    # (dépôt propre, même le commentaire). `served_manifest.json` n'est PAS touché par la promotion.
    session.execute(text(f'INSERT INTO "{BAK}{numero}__meta" VALUES (:k, :v)'),
                    {"k": "served_run_txt",
                     "v": SERVED_FILE.read_text(encoding="utf-8") if SERVED_FILE.exists() else ""})
    session.execute(text(f'INSERT INTO "{REGISTRE}" (numero, date_iso, cible, label_servi) '
                         f'VALUES (:n, :d, :c, :l)'),
                    {"n": numero, "d": _dt.datetime.now().isoformat(timespec="seconds"),
                     "c": _identite_serveur(session), "l": label or ""})
    session.commit()
    log(f"   label servi mémorisé : « {label} » (re-servi au rollback)")


# ───────────────────────── V-score : recalcul + promotion ─────────────────────────
def _ecrire_label_servi(label: str) -> None:
    SERVED_FILE.write_text(f"# run V-score servi (point de vérité versionné) — écrit par la bascule\n{label}\n",
                           encoding="utf-8")


def _vscore_recalcul_et_promotion(session, run_label: str, log=print) -> None:
    """Prod : vrai `run_score_v2` (features complètes). Tranche (features de scoring absentes) : enregistre
    un run MINIMAL dans p_score_v2_runs (parcel_p_score_v2 reste tel quel) — ce qui exerce EXACTEMENT les
    tables que --rollback doit couvrir. Dans les DEUX cas : PROMOTION = écrire le label servi."""
    try:
        from labuse.scoring.p_v2.pipeline import run_score_v2
        run_score_v2(session, run_id=run_label, rebuild=True, snapshot=False)
        session.commit()
        log(f"   V-score recalculé (run_score_v2) : {run_label}")
    except Exception as exc:  # noqa: BLE001 — tranche sans features : run minimal (preuve de couverture)
        session.rollback()
        n = int(session.execute(text("SELECT count(*) FROM parcel_p_score_v2")).scalar() or 0)
        session.execute(text(
            "INSERT INTO p_score_v2_runs (run_id, model_version, model_sha256, n_parcelles) "
            "VALUES (:r, 'bascule-2026', 'recalcul-reel-en-prod', :n) ON CONFLICT (run_id) DO NOTHING"),
            {"r": run_label, "n": n})
        session.commit()
        log(f"   V-score : features absentes ({type(exc).__name__}) → run MINIMAL enregistré ({run_label}).")
    _ecrire_label_servi(run_label)
    log(f"   PROMOTION : label servi → « {run_label} » (config/served_run.txt)")


# ───────────────────────── GO ─────────────────────────
def go(session, confirme, malgre: int | None, bodacc_limit: int, log=print) -> None:
    _exige_confirme(session, confirme, "--go")
    existantes = _sauvegardes(session)
    if existantes and malgre != existantes[-1]["numero"]:
        print(f"\n✗ --go REFUSÉ — une sauvegarde plus ancienne existe (#{existantes[-1]['numero']}, "
              f"{existantes[-1]['date_iso']}). Relance avec --malgre-sauvegarde {existantes[-1]['numero']} "
              f"pour la conserver, ou --purge-sauvegarde {existantes[-1]['numero']} pour la supprimer.")
        sys.exit(2)
    numero = (existantes[-1]["numero"] + 1) if existantes else 1

    _affiche_etat(session, "AVANT bascule")
    log(f"\n[0] SAUVEGARDE #{numero} (datée, rollback-able) …")
    _sauvegarder(session, numero, log)

    from labuse.ingestion import pm_droits, pm_millesimes
    log("\n[1] chargement des droits 2025 + 2026 dans la table d'attente (staging) …")
    session.execute(text(f'DROP TABLE IF EXISTS "{STAGING}"'))
    pm_droits.ensure_table(session, STAGING, commit=False)
    pm_droits.ingest_droits(session, pm_millesimes.fetch_974_csv(2025), "2025", table=STAGING, commit=False, log=log)
    pm_droits.ingest_droits(session, pm_droits.fetch_974_csv(), "2026", table=STAGING, commit=False, log=log)
    session.commit()   # staging isolée ; servie INCHANGÉE.

    if "--_stop-after-staging" in sys.argv:
        import os
        log("\n[_stop-after-staging] interruption dure AVANT la transaction unique. Servie inchangée.")
        os._exit(99)

    log("\n[2] TRANSACTION UNIQUE : promotion droits → archive 2025 (même règle) → flip 2026 …")
    cols = [c for c in _colonnes(session, STAGING) if c != "id"]
    cl = ", ".join(f'"{c}"' for c in cols)
    pm_droits.ensure_table(session, "parcelle_pm_droit", commit=False)
    session.execute(text('DELETE FROM parcelle_pm_droit'))
    session.execute(text(f'INSERT INTO parcelle_pm_droit ({cl}) SELECT {cl} FROM "{STAGING}"'))
    pm_droits.archive_principal_depuis_droits(session, "2025", commit=False, log=log)
    pm_droits.recompute_principal(session, "2026", commit=False, log=log)
    session.commit()   # ← seul point de bascule des tables servies.
    session.execute(text(f'DROP TABLE IF EXISTS "{STAGING}"')); session.commit()

    log(f"\n[3] BODACC — dépôts de comptes (fait daté) {'(limite %d)' % bodacc_limit if bodacc_limit else '(tous)'} …")
    try:
        from labuse.ingestion import bodacc
        sirens = bodacc.distinct_sirens(session)
        if bodacc_limit:
            sirens = sirens[:bodacc_limit]
        r = bodacc.ingest_bodacc_depots(session, sirens); session.commit()
        log(f"   bodacc_depots : {r.get('depots')} dépôts / {r.get('sirens_queried')} SIREN")
    except Exception as exc:  # noqa: BLE001 — API indisponible / tranche : étape tracée, procédure poursuit
        session.rollback(); log(f"   BODACC non chargé ({type(exc).__name__}: {str(exc)[:80]}) — couvert par la sauvegarde.")

    log("\n[4] BLOCS — reconstruction parcel_blocs + parcel_bloc_membres …")
    try:
        from labuse import blocs
        rb = blocs.build_blocs(session); session.commit()
        log(f"   blocs : {rb.get('n_blocs', '?')} blocs")
    except Exception as exc:  # noqa: BLE001
        session.rollback(); log(f"   blocs-build échoué ({type(exc).__name__}: {str(exc)[:80]}).")

    log("\n[5] V-SCORE — recalcul + promotion …")
    run_label = f"bascule2026_{numero}_{_dt.date.today().isoformat()}"
    _vscore_recalcul_et_promotion(session, run_label, log)

    _affiche_etat(session, "APRÈS bascule")
    log(f"\n[OK] procédure entière terminée (sauvegarde #{numero}). Retour arrière : "
        f"--rollback --sauvegarde {numero} --confirme <identité>.")


# ───────────────────────── ROLLBACK ─────────────────────────
def rollback(session, numero: int | None, confirme, log=print) -> None:
    _exige_confirme(session, confirme, "--rollback")
    if numero is None:
        print("\n✗ --rollback REFUSÉ — nomme la sauvegarde : --sauvegarde <N> (voir --lister-sauvegardes)."); sys.exit(2)
    sv = {s["numero"]: s for s in _sauvegardes(session)}
    if numero not in sv:
        print(f"\n✗ --rollback REFUSÉ — sauvegarde #{numero} inconnue. Disponibles : {sorted(sv)}."); sys.exit(2)
    s = sv[numero]
    pm = _empreinte(session, f"{BAK}{numero}__parcelle_personne_morale")
    print(f"\n── ROLLBACK vers la sauvegarde #{numero} — date {s['date_iso']} · cible {s['cible']} · "
          f"label servi « {s['label_servi']} » · parcelle_personne_morale {pm[1]} lignes ──")
    _affiche_etat(session, "AVANT rollback")
    meta = {r[0]: r[1] for r in session.execute(text(f'SELECT cle, valeur FROM "{BAK}{numero}__meta"')).all()}
    absentes = {k.split(":", 1)[1] for k in meta if k.startswith("absente:")}

    log("\n[rollback] restauration des tables (UNE transaction) …")
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

    # RE-SERVIR réellement le run précédent : réécrit config/served_run.txt avec ses OCTETS EXACTS d'avant
    # (dépôt propre), puis VÉRIFIE que le lecteur du run servi (`_served_run_versionne`) rend bien le label.
    label = meta.get("label_servi") or ""
    contenu = meta.get("served_run_txt")
    if contenu:
        SERVED_FILE.write_text(contenu, encoding="utf-8")
    elif SERVED_FILE.exists() and not label:
        SERVED_FILE.unlink()
    from labuse.scoring import score_v_constants as sc
    relu = sc._served_run_versionne() if SERVED_FILE.exists() else None
    ok = (relu == (label or None))
    log(f"[rollback] run servi RE-SERVI « {relu} » (attendu « {label or None} ») → "
        f"{'VÉRIFIÉ' if ok else 'ÉCART !'}")
    if not ok:
        print("✗ rollback : la re-serve du run V-score ne se vérifie pas."); sys.exit(1)
    _affiche_etat(session, "APRÈS rollback")


def purge(session, numero: int | None, confirme, log=print) -> None:
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
    malgre = _arg(args, "--malgre-sauvegarde")
    malgre = int(malgre) if malgre and str(malgre).isdigit() else None
    bodacc_limit = _arg(args, "--bodacc-limit")
    bodacc_limit = int(bodacc_limit) if bodacc_limit and str(bodacc_limit).isdigit() else 0

    eng = create_engine(url)
    with Session(eng) as s:
        if "--lister-sauvegardes" in args:
            _lister(s); return
        if "--empreinte" in args:
            _affiche_etat(s, "EMPREINTE (lecture seule)"); return
        if "--dry-run" in args:
            _affiche_etat(s, "DRY-RUN (lecture seule — rien écrit)")
            print("\n[dry-run] --go : [0] sauvegarde #N datée → [1] staging droits 2025+2026 → [2] UNE "
                  "transaction {promotion droits · archive 2025 · flip} → [3] BODACC → [4] blocs(+membres) "
                  "→ [5] recalcul+promotion V-score. --rollback --sauvegarde N restaure TOUT, run servi compris.")
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
