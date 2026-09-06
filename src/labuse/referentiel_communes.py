"""CIRCUIT-5 lot 4.1 — LE RÉFÉRENTIEL DES 24 COMMUNES, CONTRAINT EN BASE.

`communes_referentiel` (insee PK, nom UNIQUE) est seedée depuis `REUNION_COMMUNES` (le code
est la vérité) ; chaque table à la maille commune porte une CLÉ ÉTRANGÈRE sur ce référentiel :
un code absent ou hors référentiel ne peut plus ENTRER (les filtres de CIRCUIT-3
l'avertissaient, le verrou l'interdit).

Les FK sont posées `NOT VALID` (bloquent l'ENTRÉE immédiatement, sans juger le passé) puis
VALIDÉES si la table est propre ; une table qui refuse la validation garde sa contrainte
NOT VALID et ses lignes fautives sont NOMMÉES par le verrou V4a — jamais supprimées en
autonomie.

CIRCUIT-5b lot 3 — la SEULE ligne fautive héritée (sirene_etablissements insee='97454', code
inexistant) est une COQUILLE identifiable : adresse « 133 Jules Reydellet » (Saint-Denis) et
point à 3 m des parcelles 97411. Elle est CORRIGÉE (97454 → 97411) avant la validation, jamais
supprimée (`CORRECTIONS_INSEE_HERITEES`). Une coquille NON identifiable resterait fautive
(NOT VALID, nommée par V4a) pour le geste de Vic.
"""
from __future__ import annotations

from sqlalchemy import text

from .ingestion.run_all import REUNION_COMMUNES

#: table à la maille commune → colonne code INSEE (relevé information_schema du 06/09/2026,
#: orphelines exclues — elles partent au schéma poubelle, pas sous contrainte).
TABLES_MAILLE_COMMUNE: dict[str, str] = {
    "adresses": "insee",
    "anc_maille_taux": "insee",
    "anc_office_eau_commune": "insee",
    "anru_quartiers": "insee",
    "catnat_arretes": "insee",
    "commune_conso_enaf": "insee",
    "commune_contacts": "insee",
    "commune_contexte_cache": "insee",
    "commune_contexte_sru": "insee",
    "commune_insee_logement": "insee",
    "commune_pau": "insee",
    "dpe_records": "code_insee",
    "dvf_mutations_histo": "code_commune",
    "dvf_mutations_parcelle": "code_commune",
    "mairies": "insee",
    "mobpro_commune": "insee",
    "parcel_pau": "insee",
    "plu_reglement_extrait": "insee",
    "rnic_coproprietes": "insee",
    "rpls_commune": "insee",
    "sirene_etablissements": "insee",
    "sudocuh_procedures": "insee",
    "taxe_amenagement_taux": "insee",
    "territoire_fiscal_commune": "insee",
}


def nom_contrainte(table: str) -> str:
    return f"fk_{table}_commune"


#: CIRCUIT-5b lot 3 — coquilles INSEE héritées, CORRIGÉES (jamais supprimées) avant validation.
#: Chaque entrée identifie la ligne par une clé stable (siret…) ET l'ancien code (idempotence :
#: rejouée, elle ne touche plus rien une fois corrigée), et porte le motif de l'identification.
CORRECTIONS_INSEE_HERITEES: tuple[dict, ...] = (
    {"table": "sirene_etablissements", "cle_col": "siret", "cle": "83939934200147",
     "col": "insee", "de": "97454", "vers": "97411", "commune": "Saint-Denis",
     "motif": "adresse « 133 Jules Reydellet » (Saint-Denis) + point à 3 m des parcelles 97411 ; "
              "97454 hors référentiel (97401→97424)"},
)


def corriger_coquilles_heritees(db) -> list[str]:
    """CIRCUIT-5b lot 3 — corrige (idempotent) les coquilles INSEE identifiables AVANT la
    validation des FK. Rend la liste des corrections réellement appliquées (rowcount > 0)."""
    faites: list[str] = []
    for c in CORRECTIONS_INSEE_HERITEES:
        if not db.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{c['table']}"}).scalar():
            continue
        sets = f'"{c["col"]}" = :vers'
        params = {"vers": c["vers"], "de": c["de"], "cle": c["cle"]}
        if c.get("commune"):
            sets += ", commune = :commune"
            params["commune"] = c["commune"]
        n = db.execute(text(
            f'UPDATE public."{c["table"]}" SET {sets} '
            f'WHERE "{c["cle_col"]}" = :cle AND "{c["col"]}" = :de'), params).rowcount
        if n:
            faites.append(f"{c['table']} {c['cle_col']}={c['cle']} : {c['de']} → {c['vers']} "
                          f"({c['motif']})")
    return faites


def ensure_referentiel(db) -> None:
    """Pose (idempotent) la table référentiel et la remplit depuis le code."""
    db.execute(text(
        "CREATE TABLE IF NOT EXISTS communes_referentiel ("
        " insee varchar(5) PRIMARY KEY, nom text NOT NULL UNIQUE)"))
    for insee, nom in REUNION_COMMUNES:
        db.execute(text(
            "INSERT INTO communes_referentiel (insee, nom) VALUES (:i, :n) "
            "ON CONFLICT (insee) DO UPDATE SET nom = EXCLUDED.nom"),
            {"i": insee, "n": nom})


def poser_fks(db) -> dict:
    """Pose les FK (NOT VALID) sur chaque table déclarée, puis tente la VALIDATION.
    Rend {posees, validees, non_validees: {table: raison}} — idempotent, jamais un DELETE."""
    ensure_referentiel(db)
    corrections = corriger_coquilles_heritees(db)   # CIRCUIT-5b lot 3 — coquilles avant validation
    posees, validees, non_validees = [], [], {}
    for table, col in TABLES_MAILLE_COMMUNE.items():
        if not db.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar():
            continue
        cname = nom_contrainte(table)
        existe = db.execute(text(
            "SELECT convalidated FROM pg_constraint WHERE conname = :c AND conrelid = "
            "(:t)::regclass"), {"c": cname, "t": f"public.{table}"}).first()
        if existe is None:
            db.execute(text(
                f'ALTER TABLE public."{table}" ADD CONSTRAINT {cname} '
                f'FOREIGN KEY ("{col}") REFERENCES communes_referentiel (insee) NOT VALID'))
            posees.append(table)
            existe = (False,)
        if existe[0] is False:
            try:
                with db.begin_nested():
                    db.execute(text(f'ALTER TABLE public."{table}" VALIDATE CONSTRAINT {cname}'))
                validees.append(table)
            except Exception as e:  # noqa: BLE001 — lignes fautives : la FK reste NOT VALID
                non_validees[table] = str(e).splitlines()[0][:160]
    return {"posees": posees, "validees": validees, "non_validees": non_validees,
            "corrections": corrections}


def etat_fks(db) -> dict:
    """L'état lu (sans rien poser) : {table: 'absente' | 'valide' | 'not_valid (+n fautives)'}."""
    etat: dict[str, str] = {}
    for table, col in TABLES_MAILLE_COMMUNE.items():
        if not db.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar():
            etat[table] = "table absente du schéma"
            continue
        row = db.execute(text(
            "SELECT convalidated FROM pg_constraint WHERE conname = :c AND conrelid = "
            "(:t)::regclass"), {"c": nom_contrainte(table), "t": f"public.{table}"}).first()
        if row is None:
            etat[table] = "absente"
        elif row[0]:
            etat[table] = "valide"
        else:
            n = db.execute(text(
                f'SELECT count(*) FROM public."{table}" t WHERE t."{col}" IS NOT NULL '
                "AND NOT EXISTS (SELECT 1 FROM communes_referentiel r WHERE r.insee = t."
                f'"{col}")')).scalar() or 0
            etat[table] = f"not_valid ({n} ligne(s) fautive(s) héritée(s))"
    return etat
