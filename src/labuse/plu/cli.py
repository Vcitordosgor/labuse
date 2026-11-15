"""PLU-CALIBRAGE-1 — la commande `labuse plu` : extraire (agent) et revue (humain).

  labuse plu extraire <insee>   → l'agent lit le règlement opposable, propose les règles
                                  chiffrées des zones U (propose, citations), et MESURE (temps,
                                  coût API, nombre proposé / absent / rejeté).
  labuse plu revue <insee>      → la revue humaine : chaque proposition avec sa citation,
                                  zone par zone, rubrique par rubrique — valider / corriger /
                                  rejeter ; écrit `valide` dans le YAML (verrou V6a).
"""
from __future__ import annotations

import typer

plu_app = typer.Typer(add_completion=False,
                      help="PLU-CALIBRAGE : extraire (agent) et valider les règles chiffrées par zone.")


def _session_ou_none():
    """La session DB si elle répond (pour le ledger de coût) ; None sinon — l'extraction écrit
    le YAML, pas la base : elle ne doit pas échouer faute de base."""
    try:
        from ..db import session_scope
        return session_scope()
    except Exception:  # noqa: BLE001
        return None


@plu_app.command("extraire")
def plu_extraire_cmd(
    insee: str = typer.Argument(..., help="Code INSEE de la commune (ex. 97411 = Saint-Denis)."),
    zone: list[str] = typer.Option([], "--zone", "-z", help="Restreindre à ces zones U (répétable)."),
    par: str = typer.Option("cli", help="Qui lance (journal/ledger)."),
) -> None:
    """L'agent lit le règlement opposable (GPU), le découpe par zone, et propose les cinq
    rubriques de chaque zone U en `propose` (citations obligatoires). A/N hors périmètre."""
    from . import extraction
    cm = _session_ou_none()
    db = cm.__enter__() if cm is not None else None
    try:
        rap = extraction.extraire(insee, db=db, par=par, zones_voulues=list(zone) or None)
        if db is not None:
            try:
                db.commit()
            except Exception:  # noqa: BLE001
                pass
    finally:
        if cm is not None:
            cm.__exit__(None, None, None)

    typer.echo(f"— {rap.commune} ({rap.insee}) · règlement {rap.document} · modèle {rap.modele}")
    typer.echo(f"— {len(rap.zones)} zones U traitées")
    for z in rap.zones:
        rej = f" · {len(z.rejetees)} rejetée(s)" if z.rejetees else ""
        typer.echo(f"   {z.zone:8} {z.proposees:2} proposées · {z.absentes:2} absentes{rej}"
                   f"  ({z.secondes:.1f}s, {z.tokens_in}+{z.tokens_out} tk)")
        for r in z.rejetees:
            typer.echo(f"      ⚠ {r}")
    typer.echo("── mesures ──")
    typer.echo(f"   temps agent   : {rap.secondes:.1f} s")
    typer.echo(f"   coût API      : {rap.cout_eur:.4f} € ({rap.tokens_in} + {rap.tokens_out} tokens)")
    typer.echo(f"   règles propos.: {rap.n_proposees}")
    typer.echo(f"   absences prouv: {rap.n_absentes}")
    typer.echo(f"   rejetées      : {rap.n_rejetees}")


@plu_app.command("revue")
def plu_revue_cmd(
    insee: str = typer.Argument(..., help="Code INSEE de la commune (ex. 97411 = Saint-Denis)."),
    zone: list[str] = typer.Option([], "--zone", "-z", help="Restreindre à ces zones (répétable)."),
    apercu: bool = typer.Option(False, "--apercu", help="Afficher les propositions sans rien écrire."),
) -> None:
    """La revue humaine : chaque proposition avec sa citation, zone par zone, rubrique par
    rubrique — [v]alider / [c]orriger / [r]ejeter. Écrit `valide` dans le YAML (verrou V6a)."""
    from . import revue
    revue.revue_interactive(insee, zones=list(zone) or None, apercu=apercu)


@plu_app.command("verif")
def plu_verif_cmd(
    csv_out: str = typer.Option("", "--csv", help="Écrit le détail (une ligne par règle) dans ce CSV."),
    faux_only: bool = typer.Option(False, "--faux", help="N'affiche que les verdicts non-TROUVE."),
) -> None:
    """PLU-VERIF-1 (Lot D) — relit chaque règle chiffrée calibrée sur la page du PDF du
    règlement servi, cherche l'article + la valeur (dans ses formes), et rend un verdict
    TROUVE / AMBIGU / ABSENT / ILLISIBLE. Rejoué à chaque règle validée ou nouveau millésime
    (sentinelle du Circuit). Le détail alimente l'onglet Cohérence de la page Données."""
    from pathlib import Path

    from . import verif
    rows, counts = verif.verifier()
    tot = sum(counts.values())
    typer.echo(f"— {tot} règles relues sur {len({r['insee'] for r in rows})} communes "
               f"(PDF : {verif.pdf_dir()})")
    for k in ("TROUVE", "AMBIGU", "ABSENT", "ILLISIBLE"):
        typer.echo(f"   {k:9} : {counts[k]:5}")
    if csv_out:
        verif.ecrire_csv(rows, Path(csv_out))
        typer.echo(f"— détail écrit : {csv_out}")
    if faux_only:
        for r in rows:
            if r["verdict"] != "TROUVE":
                typer.echo(f"   {r['verdict']:9} {r['insee']} {r['zone']:10} {r['regle']:28} "
                           f"{r['valeur_labuse']:12} p{r['page']} {r['article']}")


# ═══════════════════════ PLU-VEILLE-FIX-1 — veille PLU/GPU : voir, appliquer, prévenir ═══════════════════════

@plu_app.command("etat")
def plu_etat_cmd(
    live: bool = typer.Option(False, "--live", help="Interroge le Géoportail en direct (sinon catalogue)."),
) -> None:
    """ÉTAT DES LIEUX des 24 communes : document Géoportail face à l'ingéré, couche par couche."""
    from .. import controle_plu
    from ..db import session_scope
    gpu = controle_plu.fetch_gpu_ile() if live else None
    with session_scope() as s:
        tab = controle_plu.tableau_ile(s, gpu_par_insee=gpu)
    n_desync = sum(1 for e in tab if e["etat"] == "desync")
    for e in tab:
        cer = ", ".join(e["couches_en_retard"]) or "—"
        marque = "⚠ " if e["etat"] == "desync" else "  "
        typer.echo(f"{marque}{e['insee']} {e['commune']:<24} {e['etat']:<8} "
                   f"réf={e['reference'] or '—'}  retard=[{cer}]")
    typer.echo(f"\n{n_desync} commune(s) en cours de mise à jour (desync) sur {len(tab)}.")


@plu_app.command("appliquer")
def plu_appliquer_cmd(
    insee: str = typer.Option(..., "--insee", help="Code INSEE de la commune (ex. 97411)."),
    overlay: bool = typer.Option(True, help="Pose l'overlay « À vérifier » sur les parcelles (Analyse)."),
) -> None:
    """LE GESTE UNIQUE : zonage + prescriptions + informations appliqués d'un seul tenant (drapeau
    « règles à recalibrer » seulement si le zonage/les règles ont bougé). Puis l'instantané de veille
    + l'overlay client (proportionnel) sont rafraîchis."""
    from .. import controle_plu
    from ..db import session_scope
    with session_scope() as s:
        bilan = controle_plu.appliquer_plu(s, insee, log=typer.echo)
        controle_plu.rejouer_nuit(s)
        if overlay:
            ov = controle_plu.rafraichir_signal_client(s)
            typer.echo(f"  overlay Analyse : {ov['lignes']} ligne(s) « À vérifier ».")
    note = "Règles à recalibrer." if bilan.get("recalibrage_requis") else \
        "Règles inchangées (prescriptions seules) — recalcule les parcelles portant une prescription."
    typer.echo(f"✓ {bilan['commune']} appliqué → {bilan['reference']} "
               f"(zones {bilan['zonage']}, prescriptions {bilan['prescriptions']}, "
               f"informations {bilan['informations']}). {note}")
    typer.echo("  Prod (couche servie) : rebâtir parcel_zone_plu → `labuse build-mvt` → `promote`.")


@plu_app.command("valider")
def plu_valider_cmd(
    insee: str = typer.Option(..., "--insee", help="Code INSEE de la commune."),
) -> None:
    """Lève le drapeau « règles à recalibrer » (règles relues et validées) : la commune repasse
    « à jour », le bandeau client disparaît, les parcelles sortent de « À vérifier »."""
    from .. import controle_plu
    from ..db import session_scope
    with session_scope() as s:
        ok = controle_plu.valider_recalibrage(s, insee)
        controle_plu.rejouer_nuit(s)
        ov = controle_plu.rafraichir_signal_client(s)
    if ok:
        typer.echo(f"✓ recalibrage validé pour {insee} — {ov['lignes']} ligne(s) restaurée(s).")
    else:
        typer.echo(f"(aucun drapeau de recalibrage en cours pour {insee})")
