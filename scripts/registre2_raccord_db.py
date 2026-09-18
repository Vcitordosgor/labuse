"""COUCHES-REGISTRE-2 lot 1 — raccord des données au registre (idempotent, ré-exécutable).

1. Crée la ligne data_sources du seed des contours communaux (réservoir `communes_ign`) si absente
   → le compteur vitrine « connecté » bouge (91 → 92).
2. Renseigne le `data_source_id` des lignes `spatial_layers` restées NULL pour parc_national,
   vefa_neuf, tcsp_zone — rattachées à leur source réelle (par NOM, jamais un id en dur).

Aucune géométrie touchée (colonne `data_source_id` seule). Ne reconstruit aucune tuile.
"""
from labuse.db import session_scope
from sqlalchemy import text

COMMUNES_NAME = "Communes La Réunion — contours (IGN ADMIN EXPRESS via geo.api.gouv, seed)"
# kind NULL → nom de la source réelle (rattachement par nom, robuste au ré-ensemencement)
RATTACH = {
    "parc_national": "Parc National de La Réunion (INPN)",
    "vefa_neuf": "DVF / valeurs foncières",
    "tcsp_zone": "TCSP — voies bus en site propre (OSM)",
}


def main() -> None:
    with session_scope() as db:
        # 1) seed des communes
        sid = db.execute(text("SELECT id FROM data_sources WHERE name = :n"), {"n": COMMUNES_NAME}).scalar()
        if sid is None:
            sid = db.execute(text(
                "INSERT INTO data_sources (name, category, provider, access_type, status, "
                "reliability_level, source_millesime, couverture_note) "
                "VALUES (:n, 'administratif', 'IGN / geo.api.gouv', 'seed (référentiel embarqué)', "
                "'connecte', 'verifie', 'ADMIN EXPRESS — contours communaux', "
                "'Contours officiels des 24 communes de La Réunion, embarqués au seed (mvt_communes).') "
                "RETURNING id"), {"n": COMMUNES_NAME}).scalar()
            print(f"[+] data_sources : créé « {COMMUNES_NAME} » (id={sid}, status=connecte) — vitrine +1")
        else:
            print(f"[=] data_sources : « {COMMUNES_NAME} » déjà présent (id={sid})")

        # 2) rattachement des lignes NULL
        for kind, src_name in RATTACH.items():
            ds_id = db.execute(text("SELECT id FROM data_sources WHERE name = :n"), {"n": src_name}).scalar()
            if ds_id is None:
                print(f"[!] {kind}: source « {src_name} » INTROUVABLE — non rattaché"); continue
            n_null = db.execute(text("SELECT count(*) FROM spatial_layers WHERE kind=:k AND data_source_id IS NULL"),
                                {"k": kind}).scalar()
            if n_null:
                db.execute(text("UPDATE spatial_layers SET data_source_id=:d WHERE kind=:k AND data_source_id IS NULL"),
                           {"d": ds_id, "k": kind})
            print(f"[{'+' if n_null else '='}] {kind}: {n_null} ligne(s) NULL → data_source_id={ds_id} ({src_name})")
        db.commit()

        vit = db.execute(text("SELECT count(*) FROM data_sources WHERE status='connecte'")).scalar()
        print(f"vitrine connecté = {vit}")


if __name__ == "__main__":
    main()
