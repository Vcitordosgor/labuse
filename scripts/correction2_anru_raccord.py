"""SOURCES-CORRECTION-2 lot 2 — raccord de la couche `anru` à son réservoir RÉEL (idempotent, ré-exécutable).

Contexte : SOURCES-CORRECTION-1 lot 2 a fait passer « DEAL Réunion (WMS/WFS) » en statut `hub`. Or les
lignes `spatial_layers kind='anru'` (8 emprises NPNRU) pointaient encore ce hub par leur `data_source_id`
(héritage M74), alors que le registre (`RESERVOIR_TABLES`) déclare le réservoir **npnru**. Résultat : le
`data_source_id` réel de la couche pointait une source `hub` (hors vitrine) → l'audit couche↔source
tombait à 55/56 (check 2 : « la source réelle est-elle `connecte` ? »).

Ici on corrige le `data_source_id` de ces lignes vers la source réellement lue — par NOM, jamais un id
en dur — comme pour les trois provenances fausses de COUCHES-REGISTRE-2 (axe_structurant/ligne_ht/tva_primo).
Aucune géométrie touchée (colonne `data_source_id` seule). Ne reconstruit aucune tuile.
"""
from labuse.db import session_scope
from sqlalchemy import text

# kind → (source FAUSSE actuelle, source RÉELLE déclarée au registre) — rattachement par nom.
RATTACH = {
    "anru": ("DEAL Réunion (WMS/WFS)", "NPNRU (DEAL Réunion / ANCT)"),
}


def main() -> None:
    with session_scope() as db:
        for kind, (faux_nom, vrai_nom) in RATTACH.items():
            faux_id = db.execute(text("SELECT id FROM data_sources WHERE name = :n"), {"n": faux_nom}).scalar()
            vrai_id = db.execute(text("SELECT id FROM data_sources WHERE name = :n"), {"n": vrai_nom}).scalar()
            if vrai_id is None:
                print(f"[!] {kind}: source réelle « {vrai_nom} » INTROUVABLE — non rattaché"); continue
            # idempotent : ne bouge que les lignes qui pointent encore la fausse source (ou NULL).
            cond = "(data_source_id = :faux OR data_source_id IS NULL)" if faux_id is not None else "data_source_id IS NULL"
            params = {"vrai": vrai_id, "k": kind}
            if faux_id is not None:
                params["faux"] = faux_id
            n = db.execute(text(f"SELECT count(*) FROM spatial_layers WHERE kind=:k AND {cond}"), params).scalar()
            if n:
                db.execute(text(f"UPDATE spatial_layers SET data_source_id=:vrai WHERE kind=:k AND {cond}"), params)
            print(f"[{'+' if n else '='}] {kind}: {n} ligne(s) « {faux_nom} »→ data_source_id={vrai_id} ({vrai_nom})")
        db.commit()

        # contrôle : la source réelle de chaque kind
        for kind, (_, vrai_nom) in RATTACH.items():
            row = db.execute(text(
                "SELECT ds.name, ds.status, count(*) FROM spatial_layers sl "
                "LEFT JOIN data_sources ds ON ds.id=sl.data_source_id WHERE sl.kind=:k "
                "GROUP BY ds.name, ds.status"), {"k": kind}).all()
            print(f"    {kind} → {[(r[0], r[1], r[2]) for r in row]}")


if __name__ == "__main__":
    main()
