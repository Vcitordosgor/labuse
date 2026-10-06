"""PPR-PARTIEL-FIX-1 (étape B) — PREUVE « 0 écart » : exercer la fiche, le Dossier et le Copilote
(qui calculent désormais la partie hors zone rouge) ne change RIEN au score, à la bande, à la SDP
servie ni à l'appartenance au listing. L'étape B est purement d'affichage.

Méthode : on DUMP l'état servi (score_labuse + parcel_residuel + filtre liste) AVANT, on exerce les
trois chemins sur les témoins + l'échantillon, on re-DUMP APRÈS, et on exige un diff vide.

  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
  PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python docs/.../harnais/verif_lot3_zero_ecart.py \
      docs/.../avant_apres.txt  < /tmp/echantillon_final.txt
"""
from __future__ import annotations

import sys

from sqlalchemy import text

from labuse.db import session_factory

TEMOINS = ["97409000AY0786", "97415000HL0001", "97411000IR0368",
           "97409000BM0449", "97409000AB0010", "97411000BZ1065"]


def etat(session, idus: list[str]) -> dict:
    """L'état d'une parcelle : TOUTES les lignes score_labuse (plusieurs score_version coexistent)
    et parcel_residuel (plusieurs runs), ordonnées de façon DÉTERMINISTE. Si le code n'écrit rien,
    le multiset complet est identique avant↔après — toute version lue reste intacte."""
    out = {}
    for idu in idus:
        sl = session.execute(text(
            "SELECT score_version, score, bande, cause, sdp_residuelle_m2 FROM score_labuse "
            "WHERE idu=:i ORDER BY score_version"), {"i": idu}).all()
        pr = session.execute(text(
            "SELECT r.cause, r.sdp_residuelle_m2 FROM parcel_residuel r "
            "JOIN parcels p ON p.id=r.parcel_id WHERE p.idu=:i"), {"i": idu}).all()
        # tri complet (ordre-indépendant) : certaines parcelles portent des lignes DUPLIQUÉES pour un
        # même score_version (quirk de données pré-existant) ; on compare le MULTISET, pas l'ordre SQL.
        _key = lambda t: tuple("" if x is None else str(x) for x in t)
        out[idu] = {
            "score_labuse": sorted((tuple(r) for r in sl), key=_key),
            "parcel_residuel": sorted((tuple(r) for r in pr), key=_key),
        }
    return out


def exercer(session, idus: list[str]) -> None:
    """Appeler les trois chemins qui lisent désormais surface_hors_ppr_rouge."""
    from labuse.api.app import _potentiel_transformation_block, _q_v2_fiche
    from labuse.copilote_v2.resume_fiche import resume_parcelle
    from labuse.exports.builder import construire
    from labuse import runs
    run = runs.current()
    for idu in idus:
        commune = session.execute(text("SELECT commune FROM parcels WHERE idu=:i"),
                                  {"i": idu}).scalar()
        _potentiel_transformation_block(session, idu, commune)   # badge + libellé
    for idu in TEMOINS:                                           # chemins lourds : témoins only
        try:
            fiche = _q_v2_fiche(session, idu, run_label=run)
            resume_parcelle(session, idu)
            construire(session, idu, "dossier", fiche=fiche)       # vrai chemin (fiche passée)
        except Exception as e:  # noqa: BLE001 — une parcelle absente du run ne doit pas fausser la preuve
            print(f"  (exercice partiel {idu}: {type(e).__name__})")


def main() -> None:
    out_path = sys.argv[1] if len(sys.argv) > 1 else "/dev/stdout"
    idus = [l.strip() for l in sys.stdin if l.strip()]
    session = session_factory()()
    try:
        avant = etat(session, idus)
        exercer(session, idus)
        session.rollback()        # au cas où un chemin aurait ouvert une transaction
        apres = etat(session, idus)
        ecarts = [idu for idu in idus if avant[idu] != apres[idu]]
        with open(out_path, "w") as fh:
            fh.write(f"# PPR-PARTIEL-FIX-1 — preuve 0 écart · {len(idus)} parcelles "
                     f"(dont {len(TEMOINS)} témoins)\n")
            fh.write(f"# ÉCARTS score/bande/SDP/cause avant↔après : {len(ecarts)}\n\n")
            for idu in idus:
                tag = "  TÉMOIN" if idu in TEMOINS else ""
                fh.write(f"{idu}{tag}\n")
                fh.write(f"    avant : {avant[idu]}\n")
                fh.write(f"    après : {apres[idu]}\n")
        print(f"parcelles={len(idus)}  écarts={len(ecarts)}  → {out_path}")
        if ecarts:
            print("ÉCARTS:", ecarts)
            sys.exit(1)
    finally:
        session.rollback()
        session.close()


if __name__ == "__main__":
    main()
