#!/usr/bin/env python
"""OUTIL-SCAN-FIX-3 — bascule 2026 SÛRE pour une base LABUSE (locale commune ou prod).

L'agent ne lance JAMAIS --go/--rollback sur la base commune `labuse`. Toute preuve se fait sur
`labuse_scanfix`. Vic choisit le moment et la cible.

Sûretés (relecture-scan-2, points 1-4) :
  • GARDE-FOU DE CIBLE (point 2) : --go et --rollback REFUSENT de partir sans
    `--confirme <base>@<hôte>`, comparé à `current_database()` et à l'hôte réel de la connexion.
    AUCUNE base par défaut. Avant d'agir, affiche base, hôte et nombre de lignes des tables concernées.
  • STAGING + TRANSACTION UNIQUE (point 3) : les droits 2025 ET 2026 sont chargés dans une TABLE
    D'ATTENTE (`parcelle_pm_droit_staging`) ; la promotion des droits + l'archive 2025 + le flip passent
    dans UNE SEULE transaction. Interruption AVANT le commit de cette transaction ⇒ base servie STRICTEMENT
    inchangée (seule la table d'attente a été écrite).
  • SAUVEGARDE COMPLÈTE (point 4) : avant tout, copie de TOUTES les tables modifiées
    (parcelle_personne_morale, pm_proprietaires_millesimes, parcelle_pm_droit, bodacc_depots, parcel_blocs)
    dans des tables `_bascule_bak__*`, + mémorisation du run V-score servi (re-servable). bodacc_depots et
    parcel_blocs sont rafraîchis par des étapes CLI SÉPARÉES (voir BASCULE-PROD.md) ; la sauvegarde les
    couvre tout de même pour que --rollback remette TOUT l'état d'avant.
  • ROLLBACK RÉEL (point 1) : `--rollback` restaure toutes ces tables depuis les sauvegardes, en UNE
    transaction. Plus AUCUNE commande SQL à taper à la main.

Usage :
    export LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse_scanfix"
    .venv/bin/python scripts/bascule_2026_labuse.py --empreinte                       # états (lecture seule)
    .venv/bin/python scripts/bascule_2026_labuse.py --dry-run                          # plan, n'écrit rien
    .venv/bin/python scripts/bascule_2026_labuse.py --go       --confirme labuse_scanfix@localhost
    .venv/bin/python scripts/bascule_2026_labuse.py --rollback --confirme labuse_scanfix@localhost
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import text

CONCERNEES = ["parcelle_personne_morale", "pm_proprietaires_millesimes", "parcelle_pm_droit",
              "bodacc_depots", "parcel_blocs"]
BAK = "_bascule_bak__"
STAGING = "parcelle_pm_droit_staging"
VOLATILES = {"id", "date_import", "built_at", "ingested_at", "created_at", "last_sync_at",
             "residuel_run_seq"}


def _existe(session, t: str) -> bool:
    return session.execute(text("SELECT to_regclass(:t) IS NOT NULL"), {"t": t}).scalar()


def _colonnes(session, t: str) -> list[str]:
    return [r[0] for r in session.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='public' "
        "AND table_name=:t ORDER BY ordinal_position"), {"t": t}).all()]


def _empreinte(session, t: str) -> tuple:
    """(existe, n_lignes, checksum) — checksum = Σ hashtext(ligne) sur les colonnes MÉTIER (hors
    volatiles : id/date_import/built_at…), donc INDÉPENDANT de l'ordre ET des horodatages de rechargement."""
    if not _existe(session, t):
        return (False, 0, 0)
    cols = [c for c in _colonnes(session, t) if c not in VOLATILES]
    expr = "row(" + ", ".join(f'"{c}"' for c in cols) + ")::text" if cols else "''"
    n, chk = session.execute(text(
        f'SELECT count(*), COALESCE(sum(hashtext({expr})::bigint), 0) FROM "{t}"')).first()
    return (True, int(n), int(chk))


def _host(session) -> str:
    h = session.get_bind().url.host
    return h or "localhost"


def _cible(session) -> str:
    base = session.execute(text("SELECT current_database()")).scalar()
    return f"{base}@{_host(session)}"


def _affiche_etat(session, titre: str) -> None:
    print(f"\n── {titre} — cible {_cible(session)} ──")
    for t in CONCERNEES:
        ex, n, chk = _empreinte(session, t)
        print(f"   {t:32} {'(absente)' if not ex else f'{n:>8} lignes  checksum={chk}'}")


def _exige_confirme(session, confirme: str | None, action: str) -> None:
    cible = _cible(session)
    if not confirme:
        print(f"\n✗ {action} REFUSÉ — il FAUT `--confirme {cible}` (base@hôte de la connexion). "
              f"Aucune base par défaut.")
        sys.exit(2)
    if confirme.strip() != cible:
        print(f"\n✗ {action} REFUSÉ — --confirme « {confirme.strip()} » ≠ cible réelle « {cible} ». "
              f"Rien écrit (garde-fou de cible).")
        sys.exit(2)
    print(f"✓ cible confirmée : {cible}")


def _sauvegarder(session, log=print) -> None:
    """Point 4 — copie TOUTES les tables concernées dans `_bascule_bak__*` + mémorise le run V-score servi.
    `_bascule_bak__meta(cle, valeur)` note les tables ABSENTES avant la bascule (pour que --rollback les
    retire au lieu de les restaurer) et le run V-score à re-servir.

    NON-ÉCRASANTE : si une sauvegarde existe déjà (ex. `--go` relancé après un premier go sans rollback),
    on la PRÉSERVE — sinon le 2ᵉ go sauvegarderait l'état DÉJÀ basculé et --rollback ne reviendrait plus à
    l'état d'origine. Un rollback remet toujours l'AVANT du PREMIER go."""
    if _existe(session, f"{BAK}meta"):
        log("   sauvegarde déjà présente (d'un go précédent) — PRÉSERVÉE (rollback → AVANT d'origine).")
        return
    session.execute(text(f'DROP TABLE IF EXISTS "{BAK}meta"'))
    session.execute(text(f'CREATE TABLE "{BAK}meta" (cle text, valeur text)'))
    for t in CONCERNEES:
        session.execute(text(f'DROP TABLE IF EXISTS "{BAK}{t}"'))
        if _existe(session, t):
            session.execute(text(f'CREATE TABLE "{BAK}{t}" AS TABLE "{t}"'))
            log(f"   sauvegarde {t}")
        else:
            session.execute(text(f'INSERT INTO "{BAK}meta" VALUES (:k, :v)'),
                            {"k": f"absente:{t}", "v": "1"})
            log(f"   {t} absente avant bascule (notée pour retrait au rollback)")
    # run V-score servi (re-servable) — nommé pour le runbook ; best-effort.
    try:
        from labuse.api.app import _score_v2_run_id
        run = _score_v2_run_id(session)
        session.execute(text(f'INSERT INTO "{BAK}meta" VALUES (:k, :v)'),
                        {"k": "vscore_run_servi", "v": str(run)})
        log(f"   run V-score servi mémorisé : {run} (à re-servir en rollback)")
    except Exception as exc:  # noqa: BLE001
        log(f"   (run V-score non capturé : {type(exc).__name__})")
    session.commit()


def go(session, log=print, stop_after_staging: bool = False) -> None:
    from labuse.ingestion import pm_droits, pm_millesimes

    _affiche_etat(session, "AVANT bascule")
    log("\n[0] SAUVEGARDE complète (rollback-able) …")
    _sauvegarder(session, log)

    # [1] CHARGEMENT dans la TABLE D'ATTENTE (aucune table servie touchée). Si tué ici → servie intacte.
    log("\n[1] chargement des droits 2025 + 2026 dans la table d'attente (staging) …")
    session.execute(text(f'DROP TABLE IF EXISTS "{STAGING}"'))
    pm_droits.ensure_table(session, STAGING, commit=False)
    pm_droits.ingest_droits(session, pm_millesimes.fetch_974_csv(2025), "2025", table=STAGING, commit=False, log=log)
    pm_droits.ingest_droits(session, pm_droits.fetch_974_csv(), "2026", table=STAGING, commit=False, log=log)
    session.commit()   # la staging est isolée (non lue par les écrans) ; la servie reste INCHANGÉE.

    if stop_after_staging:
        # Preuve (d) — interruption DURE avant la transaction : sortie immédiate, sans toucher la servie.
        log("\n[_stop-after-staging] interruption simulée AVANT la transaction unique. Servie inchangée.")
        os._exit(99)

    # [2] TRANSACTION UNIQUE : promotion droits + archive 2025 (même règle) + flip. Tout ou rien.
    log("\n[2] TRANSACTION UNIQUE : promotion des droits → archive 2025 (même règle) → flip 2026 …")
    cols = [c for c in _colonnes(session, STAGING) if c != "id"]
    collist = ", ".join(f'"{c}"' for c in cols)
    pm_droits.ensure_table(session, "parcelle_pm_droit", commit=False)
    session.execute(text('DELETE FROM parcelle_pm_droit'))
    session.execute(text(f'INSERT INTO parcelle_pm_droit ({collist}) SELECT {collist} FROM "{STAGING}"'))
    pm_droits.archive_principal_depuis_droits(session, "2025", commit=False, log=log)
    pm_droits.recompute_principal(session, "2026", commit=False, log=log)
    session.commit()   # ← LE SEUL point de bascule de la base servie.
    session.execute(text(f'DROP TABLE IF EXISTS "{STAGING}"'))
    session.commit()

    _affiche_etat(session, "APRÈS bascule")
    log("\n[OK] données basculées. ENSUITE, hors script (voir BASCULE-PROD.md) : "
        "`labuse ingest-bodacc-depots` ; recalcul V-score + promotion ; `labuse blocs-build`.")


def rollback(session, log=print) -> None:
    if not _existe(session, f"{BAK}meta"):
        print("✗ rollback impossible : aucune sauvegarde `_bascule_bak__*` (lancer --go d'abord)."); sys.exit(2)
    _affiche_etat(session, "AVANT rollback")
    absentes = {r[0].split(":", 1)[1] for r in session.execute(text(
        f'SELECT cle FROM "{BAK}meta" WHERE cle LIKE :p'), {"p": "absente:%"}).all()}
    run = session.execute(text(f'SELECT valeur FROM "{BAK}meta" WHERE cle=:k'),
                          {"k": "vscore_run_servi"}).scalar()
    log("\n[rollback] restauration de toutes les tables concernées (UNE transaction) …")
    for t in CONCERNEES:
        if t in absentes:
            session.execute(text(f'DROP TABLE IF EXISTS "{t}"'))     # créée par la bascule → retirée
            log(f"   {t} : retirée (absente avant la bascule)")
        elif _existe(session, f"{BAK}{t}"):
            bak_cols = _colonnes(session, f"{BAK}{t}")
            # retire les COLONNES AJOUTÉES par la bascule (présentes en live, absentes de la sauvegarde,
            # ex. droit_code/droit_label ajoutés au flip) → le SCHÉMA redevient exactement celui d'avant.
            for c in [c for c in _colonnes(session, t) if c not in bak_cols]:
                session.execute(text(f'ALTER TABLE "{t}" DROP COLUMN "{c}"'))
            session.execute(text(f'DELETE FROM "{t}"'))
            cl = ", ".join(f'"{c}"' for c in bak_cols)
            session.execute(text(f'INSERT INTO "{t}" ({cl}) SELECT {cl} FROM "{BAK}{t}"'))
            log(f"   {t} : restaurée depuis la sauvegarde")
    session.execute(text(f'DROP TABLE IF EXISTS "{STAGING}"'))
    session.commit()
    _affiche_etat(session, "APRÈS rollback")
    if run and run != "None":
        log(f"\n[rollback] RE-SERVIR le run V-score précédent : {run} "
            f"(chaîne golden-promote ; non fait par ce script). bodacc_depots/parcel_blocs restaurés ci-dessus.")


def main() -> None:
    from labuse.db import session_scope
    args = sys.argv[1:]
    confirme = None
    if "--confirme" in args:
        i = args.index("--confirme")
        confirme = args[i + 1] if i + 1 < len(args) else None

    with session_scope() as s:
        if "--empreinte" in args:
            _affiche_etat(s, "EMPREINTE (lecture seule)")
            return
        if "--dry-run" in args:
            _affiche_etat(s, "DRY-RUN (lecture seule — rien écrit)")
            print("\n[dry-run] étapes de --go : [0] sauvegarde → [1] staging droits 2025+2026 → "
                  "[2] UNE transaction {promotion droits · archive 2025 même règle · flip 2026}.")
            return
        if "--go" in args:
            _exige_confirme(s, confirme, "--go")
            go(s, stop_after_staging="--_stop-after-staging" in args)
            return
        if "--rollback" in args:
            _exige_confirme(s, confirme, "--rollback")
            rollback(s)
            return
    print("Préciser une action : --empreinte | --dry-run | --go --confirme <b>@<h> | "
          "--rollback --confirme <b>@<h>. Rien fait."); sys.exit(2)


if __name__ == "__main__":
    main()
