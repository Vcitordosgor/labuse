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
